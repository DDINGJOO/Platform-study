# capped 실행 요약 (시각은 장애 시작 기준 초)

- 장애 지속: 600초, 그 동안 요청 12003건, 실패 4565건 (38.0%)
- 자동 재시작 3번, 사람 호출(escalate) T+266.2
- 경고 firing 214초 / 꺼져 있던 시간 171초 (장애가 계속되는 동안)
- 경고가 꺼져 있는 동안 난 실패 1736건 (전체 실패의 38.0%)
- 실패 덩어리 4개
- 사람이 원인을 지운 시각 T+386.6. 위 firing/꺼짐 초는 장애 시작부터 이 시각까지
- 재시작 시각(T+): [26.2, 106.2, 186.2]
- 재시작 간격(초): [80.0, 80.0]
- 알림 수신 9건(firing 5, resolved 4), 기록 종류별 {'notification': 9, 'action': 3, 'no_effect': 3, 'escalate': 1, 'skip': 1}
- 실패 나눔: escalate 전 2158, escalate~원인 제거 2407, 원인 제거 뒤 0

## 첫 번째 순환

| 사건 | T+초 |
|---|---|
| 첫 실패 응답 | 0.0 |
| 경고 pending (1초 해상도) | 7 |
| 경고 firing (1초 해상도) | 22 |
| firing 알림 수신 | 26.2 |
| 재시작 요청 | 26.2 |
| 첫 실패 덩어리의 마지막 실패 | 26.7 |

## 실패 덩어리

| # | 시작 | 끝 | 길이(초) | 실패 |
|---|---|---|---|---|
| 1 | 0.0 | 26.7 | 26.7 | 534 |
| 2 | 73.1 | 106.6 | 33.5 | 541 |
| 3 | 152.3 | 186.6 | 34.3 | 545 |
| 4 | 232.4 | 386.5 | 154.1 | 2945 |

## 경고 firing 구간

| # | 시작 | 끝 | 길이(초) |
|---|---|---|---|
| 1 | 22 | 51 | 30 |
| 2 | 102 | 131 | 30 |
| 3 | 182 | 211 | 30 |
| 4 | 262 | 416 | 155 |

## 자동 복구기 기록

| T+초 | 종류 | 내용 |
|---|---|---|
| 26.2 | notification | {"status": "firing", "alerts": ["firing"]} |
| 26.2 | action | {"n": 1, "result": 202, "startsAt": "2026-10-16T02:30:03.403Z"} |
| 56.2 | notification | {"status": "resolved", "alerts": ["resolved"]} |
| 106.2 | notification | {"status": "firing", "alerts": ["firing"]} |
| 106.2 | no_effect | {"since_last_action_s": 80.0} |
| 106.2 | action | {"n": 2, "result": 202, "startsAt": "2026-10-16T02:31:23.403Z"} |
| 136.2 | notification | {"status": "resolved", "alerts": ["resolved"]} |
| 186.2 | notification | {"status": "firing", "alerts": ["firing"]} |
| 186.2 | no_effect | {"since_last_action_s": 80.0} |
| 186.2 | action | {"n": 3, "result": 202, "startsAt": "2026-10-16T02:32:43.403Z"} |
| 216.2 | notification | {"status": "resolved", "alerts": ["resolved"]} |
| 266.2 | notification | {"status": "firing", "alerts": ["firing"]} |
| 266.2 | no_effect | {"since_last_action_s": 80.0} |
| 266.2 | escalate | {"reason": "1800초 안에 자동 재시작 3번, 그래도 재발. 사람을 부른다", "startsAt": "2026-10-16T02:34:03.403Z"} |
| 356.2 | notification | {"status": "firing", "alerts": ["firing"]} |
| 356.2 | skip | {"reason": "이미 처리한 경고(같은 startsAt)", "startsAt": "2026-10-16T02:34:03.403Z"} |
| 416.2 | notification | {"status": "resolved", "alerts": ["resolved"]} |
