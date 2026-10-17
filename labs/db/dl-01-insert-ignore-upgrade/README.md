# dl-01: INSERT IGNORE 다음 SELECT … FOR UPDATE 가 교착을 만드는 이유

MySQL 교착 시리즈 1편의 실습입니다. 세션 두세 개를 mysql 클라이언트로 열어 두고, 정해진 순서로
한 문장씩 보내며 단계마다 `performance_schema.data_locks` 를 찍습니다.

필요한 것: Docker(Compose v2), python3(표준 라이브러리만). 호스트 포트 `127.0.0.1:39010`.

```bash
./scripts/run_all.sh                       # 시나리오 11개 x RR/RC x 테이블 2개 x 세 바퀴(132번), 약 40분
SCN="exists-2s other-member" ./scripts/run_all.sh   # 일부만
python3 scripts/sessions.py list           # 시나리오 목록
python3 scripts/sessions.py exists-2s RC   # 하나만 돌려 보기 (스택이 떠 있어야 한다)
docker compose down -v
```

## 테이블

| 이름 | 키 |
|---|---|
| `first_visit` | `id` AUTO_INCREMENT 기본 키 + `member_id` 보조 유니크 키 |
| `first_visit_pk` | `member_id` 가 기본 키 |

## 시나리오

| 이름 | 무엇을 하나 |
|---|---|
| `exists-2s` | 행이 있다. 두 세션이 INSERT IGNORE 후 같은 행을 SELECT … FOR UPDATE |
| `exists-2s-update` | 위와 같고 FOR UPDATE 대신 UPDATE |
| `absent-3s-commit` | 행이 없다. 세 세션이 INSERT IGNORE, 먼저 넣은 S1 이 COMMIT, 나머지가 FOR UPDATE |
| `absent-3s-rollback` | 행이 없다. 세 세션이 INSERT IGNORE, 먼저 넣은 S1 이 ROLLBACK |
| `absent-2s-commit` | 대조군: 행이 없다. 두 세션만, S1 COMMIT 뒤 S2 가 FOR UPDATE |
| `absent-2s-rollback` | 대조군: 행이 없다. 두 세션만, S1 ROLLBACK |
| `other-member` | 곁가지: S1 의 중복 INSERT IGNORE 가 커밋되기 전에 S2 가 다른 회원을 넣는다 |
| `fix-forupdate-first` | 행이 있다. INSERT IGNORE 없이 FOR UPDATE 부터 |
| `fix-nolock-read` | 행이 있다. INSERT IGNORE 다음 잠그지 않는 SELECT |
| `fix-commit-first` | 행이 있다. INSERT IGNORE 를 먼저 커밋한 뒤 새 트랜잭션에서 FOR UPDATE |
| `absent-forupdate-first` | 참고(6편): 행이 없다. FOR UPDATE 먼저, 그다음 INSERT |

단계 사이 대기는 `WAIT`(기본 1초)입니다. 그 안에 끝나지 않은 문장은 잠금을 기다리는 중으로 표시합니다.

## 결과

- `results/summary.txt`: 실행마다 한 줄. `1213=` 은 ERROR 1213 을 받은 세션과 단계, `lock_deadlocks+=` 는
  `information_schema.INNODB_METRICS` 의 `lock_deadlocks` 증가분, `rows=` 는 끝난 뒤 행 수
- `results/steps/`: 글이 인용한 시나리오의 단계별 출력(1바퀴째)
- `out/`: 전체 단계별 원출력(git 에 넣지 않음)

## 결과 요약 (MySQL 8.4.11, 세 바퀴 모두 같았다)

| 시나리오 | RR (가) | RR (나) | RC (가) | RC (나) |
|---|---|---|---|---|
| exists-2s, exists-2s-update | 0/3 (대기) | 3/3 | 3/3 | 3/3 |
| absent-3s-commit, absent-3s-rollback | 3/3 | 3/3 | 3/3 | 3/3 |
| absent-2s-commit, absent-2s-rollback | 0/3 | 0/3 | 0/3 | 0/3 |
| fix-forupdate-first, fix-nolock-read, fix-commit-first | 0/3 | 0/3 | 0/3 | 0/3 |
| absent-forupdate-first | 3/3 | 3/3 | 0/3 | 0/3 |
| other-member | 0/3 (S1 커밋까지 대기) | 0/3 | 0/3 | 0/3 |

(가) = `first_visit`, (나) = `first_visit_pk`. 칸은 1213 이 난 바퀴 수.

처음 전체 실행 한 번은 버렸다. `data_locks` 의 `THREAD_ID` 로 세션을 붙였더니, S1 이 넣은 새 행의 X 잠금이
S2 이름으로 찍혔다. data_locks 문서는 `THREAD_ID` 를 "the session that created the lock",
`ENGINE_TRANSACTION_ID` 를 "the owner of the lock" 으로 설명한다. 지금은 `ENGINE_TRANSACTION_ID` 를
`INNODB_TRX.trx_id` 와 맞춰 세션을 찾는다.

실행 환경은 `results/env.txt`(MySQL 버전·격리 수준·교착 감지·lock wait timeout, Docker 버전),
교착 카운터 확인은 `results/counters.txt`(`SHOW GLOBAL STATUS LIKE 'Innodb_deadlocks'` 는 빈 결과,
`INNODB_METRICS` 의 `lock_deadlocks` 는 enabled).
