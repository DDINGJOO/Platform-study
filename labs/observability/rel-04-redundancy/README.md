# rel-04-redundancy

신뢰성 설계 실습-4 「복제본 셋이 같은 것에 기대면 이중화가 사라진다」의 코드.
개념 글은 5편 「이중화의 곱셈은 고장이 서로 모를 때만 성립한다」. 글의 숫자는 전부 여기서 돌린 결과다.

## 구성

| 서비스 | 하는 일 |
|---|---|
| `r1` ~ `r3` | 같은 이미지(`app/replica.py`). `/work` 마다 공유 Redis 의 `mode` 키를 읽고 `bad` 면 500 |
| `a`, `b` | 액티브와 backup. 같은 이미지 |
| `redis` | 공유 설정 저장소. `mode=bad` 로 바꾸면 모든 복제본이 함께 실패한다(공통 원인) |
| `haproxy` | 실험마다 listen 하나(`haproxy/haproxy.cfg`). A 9201~9202, B 9301~9307, C 9401~9403, 통계 8404 |
| `load` | `app/experiment.py`. 상태를 주입하고, 부하를 주고, HAProxy 통계 CSV 로 DOWN 판정 시각을 남긴다 |

복제본 상태(`POST /admin/state?s=`): `up`, `down`(모든 응답 503, 포트는 열림), `gray`(`/work` 500, `/health` 200), `hang`(30초 무응답).

## 돌리기

```bash
cd labs/observability/rel-04-redundancy
docker compose up -d --build
docker compose --profile load run --rm load python experiment.py checks   --seconds 30          # C. 약 1.5분
docker compose --profile load run --rm load python experiment.py failover --trials 8            # B. 약 4분
docker compose --profile load run --rm load python experiment.py failover --trials 4 --fault hang
docker compose --profile load run --rm load python experiment.py shared   --betas 0 --slots 6000 # A. 10분
docker compose --profile load run --rm load python experiment.py shared   --betas 0.1,0.5,1 --slots 3000
python3 summarize.py                     # out/*.jsonl -> out/summary.txt
docker compose down -v
```

HAProxy 통계 화면: http://localhost:33404/stats . 계산(컨테이너 없이): `python3 calc_concept.py > out/concept-05.txt`

## 버전

| 부품 | 버전 | 비고 |
|---|---|---|
| HAProxy | 3.4.6 | 최신 LTS(2026-06 출시). 설정 매뉴얼 3.4 판 기준 |
| Redis | 8.10.2 | 저장 끔(`--save ""`, `--appendonly no`) |
| Python (이미지) | 3.14.8-slim | 표준 라이브러리만 |
| 실행 환경 | Docker Desktop, Apple M5 Pro | |

## 결과 파일

| 파일 | 내용 |
|---|---|
| `out/concept-05.txt` | 5편 계산(베타 인자 모형, inter x fall, 예산 환산, k-out-of-n, 셀) |
| `out/shared.jsonl` | A. beta 별 이론값, 실제 슬롯 일정, listen 별 성공률(하나라도 산 동안 / 모두 죽은 동안) |
| `out/failover.jsonl` | B. 시행마다 listen 별 실패 건수, 마지막 실패, HAProxy DOWN 판정 시각 |
| `out/checks.jsonl` | C. down / gray 고장에서 listen 별 실패 |
| `out/raw/*.csv.gz` | 요청 원자료(보낸 시각, 포트, 상태, 지연) |
| `out/summary.txt` | `summarize.py` 출력 |

## 함정 (돌리다 만난 것)

- **파이썬 `http.server` 에 요청마다 약 40ms 가 붙는다.** 실습-3에서 찾았다. 핸들러에 `disable_nagle_algorithm = True`.
- **공식 이미지는 haproxy 사용자로 돈다.** `stats socket /var/run/haproxy.sock` 을 넣으면 권한 때문에 막힐 수 있어서 빼고 통계 CSV(`/stats;csv`)를 읽는다.
- **액티브-스탠바이에서 `retry-on` + `option redispatch` 는 백업으로 가지 않는다.** backup 은 백업 아닌 서버가 모두 쓸 수 없을 때만 쓰인다. 실측에서도 재시도 없는 listen 과 실패 건수가 같았다.
- **같은 서버로 재시도할 때 min(`timeout connect`, 1s) 를 기다린다.** 100ms 슬롯 실험이 흐려지지 않게 `timeout connect 50ms` 로 줄였다.
- **`hang` 고장의 실패 건수는 믿지 않는다.** listen 마다 스레드 4개라 멈춘 서버로 간 요청이 `timeout server`(5초) 동안 스레드를 붙잡아 보내려던 요청을 못 보냈다. 그 시행은 DOWN 판정 시각만 쓴다.
- **beta=0.1, 3000 슬롯에서 공통 원인 슬롯이 기대값 30개 대신 16개 뽑혔다.** 드문 사건은 짧은 실행에서 크게 흔들린다. 결과는 실제 일정(`slot_any_up_ratio`)과 비교한다.
- `observe layer7` + `on-error mark-down` 은 헬스 경로가 200 인 회색 고장에서 2초(`rise 2` x `inter 1s`)마다 DOWN/UP 을 반복했다.
