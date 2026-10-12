# 타임라인: run-1

시각은 장애 주입을 T+00:00 으로 둔 상대 시간. 자동 생성(scripts/timeline.py).

| 시각 | 출처 | 사건 |
|---|---|---|
| T-00:30.2 | 명령 기록 | [start] run-1 |
| T+00:00.0 | 명령 기록 | [inject] inventory 경로 latency=900ms jitter=300ms |
| T+00:02.8 | Prometheus | 503 카운터가 처음 늘어난 스크레이프(영향 시작) |
| T+00:12.8 | Prometheus | OrderLatencyHigh pending 시작 |
| T+00:22.8 | Prometheus | OrderErrorRatioHigh pending 시작 |
| T+00:22.8 | Prometheus | 실패율 기록 규칙이 5% 를 넘음 |
| T+01:21.8 | Prometheus | OrderErrorRatioHigh pending 마지막 관측 |
| T+01:22.8 | Prometheus | OrderErrorRatioHigh firing 시작 |
| T+01:53.3 | 웹훅 수신 | OrderErrorRatioHigh firing (page) startsAt=T+01:22.4 |
| T+01:57.0 | 명령 기록 | [declare] OrderErrorRatioHigh page 수신. 장애 선언, IC 겸 운영 담당 1인 |
| T+01:57.1 | 명령 기록 | [diagnose] 주문 실패율(1m)=0.304, 주문 서버 p99(s)=1.489, order가 본 재고 호출 p99(s)=1.489, 재고 서버 자체 p99(s)=0.005, 재고 호출 결과/초={'ok': 13.86, 'timeout': 6.1, 'error': 0.0} |
| T+02:00.9 | 명령 기록 | [decide] 절차서 2단계 표 1행: 재고 서버는 5ms인데 order가 본 호출은 1.5s. 가는 길이 느림 → 3-A 완화 |
| T+02:01.0 | 명령 기록 | [mitigate] order fallback 켬(재고 확인 보류) |
| T+02:02.8 | Prometheus | 503 카운터가 마지막으로 늘어난 스크레이프(영향 끝) |
| T+02:06.6 | 명령 기록 | [comms] [조사 중] 주문 일부가 실패하고 있습니다. 재고 확인을 보류하는 완화를 적용했고, 주문은 '확인 보류' 상태로 접수됩니다. 다음 공지 15분 뒤. |
| T+02:11.8 | Prometheus | OrderLatencyHigh pending 마지막 관측 |
| T+02:12.8 | Prometheus | OrderLatencyHigh firing 시작 |
| T+02:43.4 | 웹훅 수신 | OrderLatencyHigh firing (ticket) startsAt=T+02:12.4 |
| T+03:01.8 | Prometheus | OrderErrorRatioHigh firing 마지막 관측 |
| T+03:01.8 | Prometheus | OrderLatencyHigh firing 마지막 관측 |
| T+03:02.8 | Prometheus | 실패율 기록 규칙이 5% 아래로 |
| T+03:21.8 | 명령 기록 | [diagnose] 주문 실패율(1m)=0.000, 주문 서버 p99(s)=0.005, order가 본 재고 호출 p99(s)=nan, 재고 서버 자체 p99(s)=nan, 재고 호출 결과/초={'ok': 0.0, 'timeout': 0.0, 'error': 0.0} |
| T+03:28.3 | 명령 기록 | [note] 완화 후 재고 호출이 0건이라 절차서 5단계의 'order가 본 재고 호출 p99' 를 볼 수 없음. 경로를 직접 찔러 확인하기로 |
| T+03:28.4 | 명령 기록 | [repair] inventory 경로 지연 독 제거 |
| T+03:29.2 | 명령 기록 | [probe] 경로 직접 호출 10건(ms): [7.9, 2.1, 0.9, 0.7, 0.6, 0.6, 0.6, 0.5, 0.6, 0.5] |
| T+03:32.4 | 명령 기록 | [restore] order fallback 끔(정상 경로) |
| T+05:02.6 | 명령 기록 | [diagnose] 주문 실패율(1m)=0.000, 주문 서버 p99(s)=0.005, order가 본 재고 호출 p99(s)=0.005, 재고 서버 자체 p99(s)=0.005, 재고 호출 결과/초={'ok': 19.97, 'timeout': 0.0, 'error': 0.0} |
| T+05:02.6 | 명령 기록 | [resolved] fallback 끄고 90초간 실패율 0. 정상 경로 복귀 |
| T+06:53.7 | 웹훅 수신 | OrderErrorRatioHigh resolved (page) startsAt=T+01:22.4, endsAt=T+03:02.4 |
| T+07:43.8 | 웹훅 수신 | OrderLatencyHigh resolved (ticket) startsAt=T+02:12.4, endsAt=T+03:02.4 |

## 측정값 (초)

- run: run-1
- 주입→영향 시작(첫 503 스크레이프): 2.8
- 주입→실패율 기준 초과: 22.8
- 주입→pending: 22.8
- 주입→firing: 82.8
- 주입→page 알림 수신 (TTD): 113.3
- page 알림→완화 명령: 7.7
- 주입→완화 명령: 121.0
- 주입→영향 끝(마지막 503 스크레이프) (TTM): 122.8
- 주입→정상 경로 복귀 명령 (TTR): 212.4
- 실패한 주문(503) 건수: 747
- 영향 구간(첫~마지막 503 스크레이프) 전체 주문 건수: 2500
- 재고 확인 보류로 받은 주문 건수: 1825
- 실패율 최고값(1m 창): 0.328
- 점검: 스크레이프 수 / 기대값(5초 간격): 106 / 106
- 점검: 주문 요청률 최저(30s 창, 건/초): 19.0
