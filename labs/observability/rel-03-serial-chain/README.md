# rel-03-serial-chain

신뢰성 설계 실습-3 「의존 서비스를 한 줄로 이으면 성공률이 곱으로 준다」의 코드.
개념 글은 4편 「가용성은 더하지 않고 곱한다」. 글의 숫자는 전부 여기서 돌린 결과다.

## 구성

| 서비스 | 하는 일 |
|---|---|
| `h1` ~ `h6` | 같은 이미지(`app/hop.py`). `h1 -> h2 -> ... -> h6` 로 이어진다. 길이 N 체인은 `h(7-N)` 로 들어간다 |
| `r1` ~ `r3`, `pf` | 병렬 묶음. `pf` 가 세 복제본 중 하나를 무작위 순서로 부르다가 성공하면 멈춘다 |
| `load` | `app/experiment.py`. 부하를 주고, 홉마다 `/stats` 를 모아 `out/*.jsonl` 로 남긴다 |

홉은 요청을 받으면 **자기 실패를 먼저 판정하고**(503), 살아 있으면 다음 홉을 부른다(실패하면 502).
실패율·재시도·실패 방식은 실행 중에 `POST /config` 로 바꾼다. 표준 라이브러리만 쓴다.

- `mode=random` : 요청마다 독립적으로 `fail_rate` 확률로 실패
- `mode=slotted` : 시간을 `slot_ms` 단위로 자르고, 슬롯마다 `fail_rate` 확률로 그 슬롯 전체가 실패(홉끼리는 독립)
- `retries=1` : 다음 홉 호출이 실패하면 한 번 더 부른다(홉마다 재시도)
- 사용자 쪽 재시도는 `load` 가 한다(`--retry edge`)

## 돌리기

```bash
cd labs/observability/rel-03-serial-chain
docker compose up -d --build
docker compose --profile load run --rm load                       # 글에 실은 측정 전부(약 25분)
docker compose --profile load run --rm load python experiment.py chain --retry hop --requests 20000
docker compose --profile load run --rm load python experiment.py parallel --pick failover --requests 100000
python3 summarize.py                                              # out/*.jsonl -> out/summary.txt
docker compose down -v
```

계산(컨테이너 없이): `python3 calc_concept.py > out/concept-04.txt`

## 버전

| 부품 | 버전 |
|---|---|
| Python (이미지) | 3.14.8-slim |
| 실행 환경 | Docker Desktop, Apple M5 Pro |

## 결과 파일

| 파일 | 내용 |
|---|---|
| `out/concept-04.txt` | 4편 계산(직렬·병렬·k-out-of-n·MTBF·재시도) |
| `out/chain.jsonl` | 체인 측정. random 은 N=1~6 x 재시도 3종 x 10만 건, slotted 는 N=6 240초(초당 1,000건) + 닫힌 고리 120초 |
| `out/extra/chain.jsonl` | slotted 추가 실행(지연 분위수 기록) |
| `out/split/chain.jsonl` | slotted 추가 실행. 요청을 보낸 순간의 홉 상태로 성공률을 나눴다 |
| `out/parallel.jsonl` | 병렬 3중화 30만 건 x 2 |
| `out/discarded.jsonl` | 부하 생성기 간격이 30초 넘게 빈 실행(버림, 같은 조건으로 다시 돌렸다) |
| `out/summary.txt` | `summarize.py` 출력 |

## 함정 (돌리다 만난 것)

- **요청마다 약 40ms 가 붙었다.** 처리량이 체인 길이와 상관없이 초당 380~390건에 묶였다(맥에서 컨테이너 없이 돌리면 수천 건).
  `http.server` 가 헤더와 본문을 따로 쓰면서 Nagle 과 지연 ACK 가 맞물린 것으로 보고, 핸들러에
  `disable_nagle_algorithm = True` 를 넣자 20배 넘게 빨라졌다. 패킷 캡처로 확인하지는 않았다.
- **부하 생성기가 성공률을 바꾼다.** slotted 모드에서 응답 즉시 다음 요청을 보내면(닫힌 고리) 실패가 빨리 끝나는
  동안 요청이 몰려 성공률이 시간 기준보다 낮게, 일정 속도로 보내도 재시도로 실패가 느려지면 장애 중 요청이 줄어
  높게 나온다. 그래서 slotted 실행은 `--rate` 로 속도를 고정하고, 해시로 다시 계산한 일정(`time_all_up`)과
  보낸 순간 상태별 성공률(`success_sent_some_down`)을 같이 남긴다.
- `max_gap_s` 가 30초를 넘는 실행은 버린다(맥이 잠들거나 다른 작업에 밀린 것). 사용자 쪽 재시도 N=6 첫 실행이
  932초 비어서 다시 돌렸다.
- 홉의 `reconnect` 카운터가 0 이 아니면 keep-alive 연결이 끊겨 요청을 다시 보낸 것이니 결과를 의심한다(이번 측정은 모두 0).
