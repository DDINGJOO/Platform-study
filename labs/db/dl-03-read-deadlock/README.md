# dl-03 LATEST DETECTED DEADLOCK 읽기와 data_locks 로 원인 확정하기

MySQL 교착 시리즈 3편의 실습. MySQL 8.4 공식 이미지 하나와 `mysql` 클라이언트 세션 몇 개로,
교착 두 종류를 일부러 내고 그때마다 `SHOW ENGINE INNODB STATUS`, 에러 로그,
`performance_schema.data_locks` / `data_lock_waits` 가 무엇을 보여 주는지 남긴다. 호스트에 JDK 나 빌드 도구는 필요 없다.

```bash
scripts/run_all.sh        # MySQL(127.0.0.1:39030) 을 띄우고 세 바퀴, 약 1분
docker compose down -v
```

## 한 바퀴(scripts/run.sh)에서 하는 일

| 단계 | 내용 |
|---|---|
| 준비 | 이 바퀴 시작 시점의 `innodb_print_all_deadlocks` 등을 찍고 ON 으로 켠다. `log_error_verbosity` 는 2 로 되돌린다 |
| A | 1편과 같은 교착. 세 세션이 `INSERT IGNORE` 로 같은 `user_key` 를 넣고 `SELECT … FOR UPDATE`. 첫 세션이 커밋하기 전 대기 상태에서 data_locks 를 찍는다 |
| A 직후 | STATUS 의 LATEST DETECTED DEADLOCK 절 저장 |
| B | `log_error_verbosity=3` 으로 올린 뒤, 두 세션이 `acct` 의 id 1, 2 를 서로 반대 순서로 UPDATE. 대기 상태에서 data_locks 를 찍는다 |
| B 직후 | STATUS 다시 저장(A 가 덮어써졌는지 본다), `lock_deadlocks` 카운터 |
| C | 교착 없이 갭 잠금, 삽입 의도 잠금을 만들어 STATUS 표기와 data_locks.LOCK_MODE 를 대조 (`innodb_status_output_locks=ON`) |
| 끝 | 이 바퀴 동안의 에러 로그(`docker compose logs`) 저장 |

## 결과

- `results/summary.txt`: 세 바퀴 요약 (`scripts/summarize.py` 가 out/ 에서 뽑는다)
- `results/r1-*.txt`, `results/r3-C-locks.txt`: 글이 인용하는 원문. OS 스레드 핸들, 읽기 전용 트랜잭션 번호,
  8자리 이상 숫자가 든 레코드 hex 는 자리표시자로 바꿨다
- `out/`: 원자료 전체(.gitignore)

## 실행 환경과 버린 실행

MySQL 8.4.11(mysql:8.4 이미지), Docker 29.5.3, Apple Silicon. 기본 격리 수준 REPEATABLE-READ.
같은 컨테이너에서 스크립트를 고치며 시험 바퀴 두 번(r0, r9)을 먼저 돌렸고 버렸다. 그래서 `lock_deadlocks`
카운터는 r1 시작 때 이미 4다. 글은 바퀴마다의 증가분(2)만 쓴다. 같은 이유로 r1~r3 의 `00-settings.txt` 첫 칸은 `print_all_deadlocks=1` 이다(시험 바퀴가 이미 켰다). 서버 기본값 OFF 는 매뉴얼 기준이고, 처음 원자료에 붙은 "## 기본값" 이름표는 틀렸던 것이라 지금 스크립트는 "이 바퀴 시작 시점 값"으로 찍는다. r0 에서 `data_lock_waits` 를 THREAD_ID 로 조인하면
막는 쪽이 엉뚱한 스레드로 나오는 것을 보고, 트랜잭션 ID 기준 조인을 추가했다(두 조인을 모두 남긴다).
