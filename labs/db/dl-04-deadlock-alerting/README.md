# dl-04 교착 알람: 무엇으로 세고 어떤 규칙을 거나

MySQL 8.4 에서 교착 수를 얻을 수 있는 네 자리(INNODB_METRICS `lock_deadlocks`, SHOW GLOBAL STATUS, 에러 로그, 클라이언트 1213)를
교착 한 건씩 대조하고, 실제 카운터와 시뮬레이션한 카운터에 알람 규칙 네 개를 적용해 알람 수와 실제 교착 수를 비교한다.

| 규칙 | 내용 |
|---|---|
| R1 연속형 | 5분 창 증가 >= 1 인 구간이 3번 연속 (5분마다 평가) |
| R2 버스트 | 5분 창 증가 >= 3 (1분마다) |
| R3 지속 | 6시간 창 증가 >= 6 (5분마다) |
| R4 존재 | 24시간 창 증가 >= 1 (1시간마다) |

알람 수는 꺼짐 → 켜짐 전이 수다. 증가량은 값이 줄어든 표본(재시작)을 리셋으로 보고 그 표본 값을 증가로 친다(`scripts/rules.py`).

## 실행

```bash
./scripts/run_all.sh                       # MySQL 8.4(127.0.0.1:39040), 단계 대조 + 13분 시계열 + 재시작 (약 15분)
STEPS_ONLY=1 RUN=r2 ./scripts/run_all.sh   # 단계 대조만 다시
python3 scripts/eval_timeline.py           # results/timeline.csv 에 규칙 적용 (1초 = 1분으로 읽는다)
python3 scripts/simulate.py                # MySQL 없이 비율별, 장면별 시뮬레이션 (seed 1~20 고정, 결정적)
docker compose down -v
```

- `scripts/deadlock_once.sh`: 두 세션이 행 1, 2 를 반대 순서로 잠가 교착 1건. `LOCK_WAIT=3` 이면 세션 lock_wait_timeout 3초
- `run_all.sh` 의 `errlog=` 는 머리말(MY-012468) 줄 수다. verbosity 2 에서 남는 본문은 세지 않는다
- `scripts/probe.sh`: 관련 설정, INNODB_METRICS 잠금 카운터, `SHOW GLOBAL STATUS LIKE '%dead%'`
- `scripts/timeline.py`: 0~180초 시간당 8건 꼴(지수분포 간격, seed 4, 최소 1.5초) 24건, 240/440/640초에 1건씩. 1초마다 `lock_deadlocks` 를 찍는다

## 결과 (results/)

| 파일 | 내용 |
|---|---|
| `probe.txt`, `probe-after-1.txt` | 새 컨테이너, 교착 1건 전후 |
| `steps.txt`, `steps-r2.txt` | 설정별 교착 1건 대조 (두 번 실행, 증가량 같음) |
| `timeline.csv`, `timeline-run.txt`, `eval_timeline.txt` | 13분 시계열과 규칙 적용 결과 |
| `restart.txt` | 재시작 전후 카운터와 SET GLOBAL 값 |
| `errlog-count.txt` | 에러 로그 머리말·본문 줄 수 (verbosity 2 구간과 전체) |
| `simulate.txt` | 시뮬레이션 전체 출력 |

핵심 숫자: `innodb_print_all_deadlocks=ON`, `log_error_verbosity=2`(기본값)에서는 에러 로그에 트랜잭션·잠금 본문(`TRANSACTION …` 2줄, `RECORD LOCKS …` 4줄)만
시각 없이 남고, 머리말(`[Note] [MY-012468] … Transactions deadlock detected`)·소제목·`WE ROLL BACK` 줄은 0. 3 으로 올리면 머리말까지 남는다(`results/errlog-count.txt`).
소스(mysql-server 8.4 `storage/innobase/lock/lock0lock.cc` 의 `Deadlock_notifier`): 머리말·소제목·희생자 줄은 `ib::info()`(verbosity 필터 대상),
본문은 `trx_print_low(stderr, …)`, `lock_rec_print(stderr, …)` 로 stderr 에 직접 쓴다.
교착 감지 OFF 에서는 `lock_deadlocks` 그대로, `lock_timeouts` +2, 두 세션 모두 1205.
13분 시계열에서 교착 27건 = `lock_deadlocks` 증가 27 = 클라이언트 1213 27 = 에러 로그 머리말 27(verbosity 3).
재시작하면 `lock_deadlocks` 31 → 0.

버전: MySQL 8.4.11(`mysql:8.4` 이미지), Python 3.9(표준 라이브러리만), Docker 29.5.3(Docker Desktop). `out/` 은 원자료(컨테이너 로그 포함)라 커밋하지 않는다.
