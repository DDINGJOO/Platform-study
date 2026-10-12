# 첫 주입 때 프록시가 멈춘 기록 (gameday-1, 버림)

시각은 첫 주입 명령(`gd.py inject 900 300`)을 T+0 으로 둔 상대 시간. 출력은 그 자리에서 친 명령의 결과를 옮겼다(원본 로그는 사설 IP 가 있어 raw/ 에만 둔다).

- T+0      `gd.py inject 900 300` 의 POST /proxies/inventory/toxics 가 10초 클라이언트 타임아웃까지 응답 없음 (`socket.timeout: timed out`)
- T+약20s  `GET /proxies` → `"toxics":[]` (독이 목록에 없음)
- T+약25s  `gd.py diag` → 주문 서버 p99 1.469s, 재고 서버 자체 p99 0.008s, 재고 호출 결과/초 ok 8.8, timeout 1.29
- T+약1분  같은 POST 를 curl 로 다시 → 0.009초 만에 성공(곧바로 삭제), 이어서 python 으로 추가·삭제 두 번 → 각각 0.006초, 0.001초
- T+약2분30초 `gd.py diag` → 실패율 1.000, 재고 호출 결과/초 ok 0.0, timeout 20.0, 재고 서버 자체 p99 = 값 없음(요청이 안 옴)
- 같은 때 `GET /proxies` → `"toxics":[]`
- 같은 때 order 컨테이너 안에서: inventory:8080 직접 호출 0.007초 성공, toxiproxy:28666 경유 5초 타임아웃
- `docker compose restart toxiproxy` 후 정상

독이 하나도 없는데 프록시 경유 경로만 막혀 있었다. Toxiproxy 저장소의 열린 이슈
#558(Toxiproxy control port hangs on removing a toxic), #428(Deadlock on writing last buffer to dead output) 과 증상이 같은 계열이다.
같은 조건(초당 20건, 클라이언트 1초 타임아웃, latency 900ms jitter 300ms)으로 독 추가·삭제를 되풀이한 시도(delete.jsonl, gameday 실행들)에서는 다시 나지 않았다.
