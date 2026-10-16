# unbounded 실행 요약 (시각은 장애 시작 기준 초)

- 장애 지속: 600초, 그 동안 요청 12004건, 실패 4012건 (33.4%)
- 자동 재시작 8번, 사람 호출 없음
- 경고 firing 240초 / 꺼져 있던 시간 359초 (장애가 계속되는 동안)
- 경고가 꺼져 있는 동안 난 실패 3156건 (전체 실패의 78.7%)
- 실패 덩어리 8개
- 재시작 시각(T+): [29.4, 109.4, 184.4, 264.4, 339.4, 414.4, 494.4, 569.4]
- 재시작 간격(초): [80.0, 75.0, 80.0, 75.0, 75.0, 80.0, 75.0]
- 알림 수신 16건(firing 8, resolved 8), 기록 종류별 {'notification': 16, 'action': 8}

## 첫 번째 순환

| 사건 | T+초 |
|---|---|
| 첫 실패 응답 | 0.0 |
| 경고 pending (1초 해상도) | 10 |
| 경고 firing (1초 해상도) | 25 |
| firing 알림 수신 | 29.4 |
| 재시작 요청 | 29.4 |
| 첫 실패 덩어리의 마지막 실패 | 29.9 |

## 실패 덩어리

| # | 시작 | 끝 | 길이(초) | 실패 |
|---|---|---|---|---|
| 1 | 0.0 | 29.9 | 29.8 | 598 |
| 2 | 75.7 | 109.9 | 34.2 | 542 |
| 3 | 155.1 | 184.9 | 29.8 | 448 |
| 4 | 231.8 | 264.8 | 33.0 | 541 |
| 5 | 312.1 | 339.8 | 27.7 | 448 |
| 6 | 385.5 | 414.9 | 29.3 | 456 |
| 7 | 461.2 | 494.9 | 33.6 | 541 |
| 8 | 540.7 | 569.8 | 29.1 | 438 |

## 경고 firing 구간

| # | 시작 | 끝 | 길이(초) |
|---|---|---|---|
| 1 | 25 | 54 | 30 |
| 2 | 105 | 134 | 30 |
| 3 | 180 | 209 | 30 |
| 4 | 260 | 289 | 30 |
| 5 | 335 | 364 | 30 |
| 6 | 410 | 439 | 30 |
| 7 | 490 | 519 | 30 |
| 8 | 565 | 594 | 30 |

## 자동 복구기 기록

| T+초 | 종류 | 내용 |
|---|---|---|
| 29.4 | notification | {"status": "firing", "alerts": ["firing"]} |
| 29.4 | action | {"n": 1, "result": 202, "startsAt": "2026-10-16T02:18:48.403Z"} |
| 59.4 | notification | {"status": "resolved", "alerts": ["resolved"]} |
| 109.4 | notification | {"status": "firing", "alerts": ["firing"]} |
| 109.4 | action | {"n": 2, "result": 202, "startsAt": "2026-10-16T02:20:08.403Z"} |
| 139.4 | notification | {"status": "resolved", "alerts": ["resolved"]} |
| 184.4 | notification | {"status": "firing", "alerts": ["firing"]} |
| 184.4 | action | {"n": 3, "result": 202, "startsAt": "2026-10-16T02:21:23.403Z"} |
| 214.4 | notification | {"status": "resolved", "alerts": ["resolved"]} |
| 264.4 | notification | {"status": "firing", "alerts": ["firing"]} |
| 264.4 | action | {"n": 4, "result": 202, "startsAt": "2026-10-16T02:22:43.403Z"} |
| 294.4 | notification | {"status": "resolved", "alerts": ["resolved"]} |
| 339.4 | notification | {"status": "firing", "alerts": ["firing"]} |
| 339.4 | action | {"n": 5, "result": 202, "startsAt": "2026-10-16T02:23:58.403Z"} |
| 369.4 | notification | {"status": "resolved", "alerts": ["resolved"]} |
| 414.4 | notification | {"status": "firing", "alerts": ["firing"]} |
| 414.4 | action | {"n": 6, "result": 202, "startsAt": "2026-10-16T02:25:13.403Z"} |
| 444.4 | notification | {"status": "resolved", "alerts": ["resolved"]} |
| 494.4 | notification | {"status": "firing", "alerts": ["firing"]} |
| 494.4 | action | {"n": 7, "result": 202, "startsAt": "2026-10-16T02:26:33.403Z"} |
| 524.4 | notification | {"status": "resolved", "alerts": ["resolved"]} |
| 569.4 | notification | {"status": "firing", "alerts": ["firing"]} |
| 569.4 | action | {"n": 8, "result": 202, "startsAt": "2026-10-16T02:27:48.403Z"} |
| 599.4 | notification | {"status": "resolved", "alerts": ["resolved"]} |
