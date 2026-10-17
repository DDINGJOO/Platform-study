# dl-06 같은 키로 동시에 들어오는 "없으면 넣기" 다섯 패턴

MySQL 교착 시리즈 6편 "같은 요청이 동시에 두 번 올 때 없으면 넣기를 교착 없이 짜는 다섯 가지 방법"의 실습입니다.

같은 키로 요청 4건을 동시에(배리어로 출발을 맞춰) 보내는 라운드를 90번 돌립니다(360건). 연결 4개는 풀을 공유하지 않아
서로 다른 앱 인스턴스에 도착한 재전송을 흉내 냅니다. 요청 하나는 트랜잭션 하나이고, 패턴이 스스로 내린 판정
(SAVED 내가 넣었다 / DUPLICATE 이미 있었다)을 실제로 행을 넣은 요청(`inserted_by`)과 대조해 채점합니다.

| 이름 | 패턴 | 판정 근거 |
|---|---|---|
| `p1` | ① `INSERT IGNORE` 다음 같은 행 `SELECT … FOR UPDATE` | INSERT IGNORE 반환값 1/0 |
| `p2` | ② `INSERT … ON DUPLICATE KEY UPDATE payload=payload` (Connector/J 기본값) | 반환값 1이면 저장 |
| `p2a` | ② 와 같고 `useAffectedRows=true` | 반환값 1이면 저장 |
| `p3` | ③ 일반 `INSERT`, 1062 를 잡아 중복 | 예외 여부 |
| `p4` | ④ 잠금 없는 조회 → 없으면 `INSERT` → 1062 면 롤백 후 새 트랜잭션에서 다시 읽어 같은 값인지 확인 | 조회 결과 |
| `p4b` | ④ 와 같지만 1062 뒤 **같은 트랜잭션**에서 다시 읽는다(RR 스냅숏 함정 확인용) | 조회 결과 |
| `p5` | ⑤ 없는 행에 `SELECT … FOR UPDATE` 먼저, 없으면 `INSERT` | 조회 결과 |

표는 `visit(id PK auto, user_key 보조 유니크, payload, inserted_by)` 이고, 무작위 키 1000행을 미리 채워 새 키가 아무 갭에나 떨어지게 합니다.

## 실행

```bash
./scripts/build.sh        # JDK 21 이상. app/build/libs/upsert.jar
./scripts/run_all.sh      # MySQL 8.4(127.0.0.1:39060)를 띄우고 세 바퀴(약 5분)
python3 scripts/summarize.py   # out/ → results/summary.txt
docker compose down -v
```

모드는 하나씩 돌릴 수도 있습니다(스택이 떠 있어야 함).

| 모드 | 내용 |
|---|---|
| `bench <p> <RR\|RC> <라운드>` | 재시도 없이 4건 동시 |
| `retry <p> <RR\|RC> <라운드>` | 같은 요청을 Spring `RetryTemplate` 으로 **트랜잭션 바깥**에서 재시도(1213·1205, 최대 3번 더, 20ms+지터 10ms) |
| `footprint <p> <RR\|RC>` | 세션 하나가 새 키 / 이미 있는 키에서 커밋 직전까지 잡는 잠금(`performance_schema.data_locks`) |
| `deadlock <p1\|p5> <RR\|RC>` | 세션 2~3개가 정해진 순서로 문장을 보내며 교착 직전 잠금을 찍는다. 시드 행 `k100 k200 k300` 사이에 `k150` 을 넣는다 |
| `spring <plain\|retry> <라운드>` | ① 을 `JdbcTemplate` + `@Transactional`(+ `@Retryable`)로. 실패한 예외 클래스 이름을 센다 |
| `order` | 같은 메서드에 `@Retryable` 과 `@Transactional` 을 붙이고 첫 시도만 실패시켜, 시도마다 트랜잭션이 새로 열리는지 본다 |

`compose.yaml` 에서 `innodb_lock_wait_timeout` 을 10초로 줄였습니다(기본 50초). 이 실습의 정상 대기는 수 ms 라 결과에 영향이 없습니다.

## 결과

- `results/summary.txt`: 패턴 × 격리 수준 × 세 바퀴. `failed` 예외로 끝난 요청, `wrong` 판정이 실제와 다른 요청,
  `ok_rounds` 4건이 모두 맞게 판정하고 행이 1개인 라운드, `dl` 은 `INNODB_METRICS` 의 `lock_deadlocks` 증가분
- `results/bench-RR-r1.txt`: 첫 바퀴 RR 원출력(글의 실행 화면)
- `results/deadlock-*.txt`, `results/footprint-*.txt`: 잠금 덤프. footprint 의 "existing key" 단계에서 세션 이름이 `?` 로
  찍힌 것은 라벨을 `information_schema.innodb_trx` 와 트랜잭션 id 로 붙이는데 그 단계에서 조인이 비었기 때문입니다.
  세션이 하나뿐이므로 전부 S1 의 잠금입니다
- `results/order.txt`: `@Retryable` + `@Transactional` 순서
- `Innodb_deadlocks` 상태 변수는 MySQL 8.4.11 에 없었습니다(`SHOW GLOBAL STATUS` 가 빈 결과, 출력의 -1)
- `out/` 은 원자료(실행 시각 포함)라 커밋하지 않습니다

버전: MySQL 8.4.11, Spring Boot 4.1.1(Spring Framework 7.0.9), Connector/J 9.7.0, Java 25.0.3, Docker 29.5.3.
