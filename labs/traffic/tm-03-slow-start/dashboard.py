# 실습-3 대시보드 패널. ../common-envoy/scripts/make-dashboard.py 가 grafana/lab.json 으로 만든다
UID = "tm03"
TITLE = "트래픽 실습-3 새 인스턴스와 slow start"
PANELS = [
    {"title": "인스턴스별 초당 요청 수", "unit": "reqps",
     "targets": [('sum by (app) (rate(http_server_requests_seconds_count{uri="/work"}[6s]))', "{{app}}")]},
    {"title": "인스턴스별 p99 (앱이 잰 처리 시간)", "unit": "s",
     "targets": [('histogram_quantile(0.99, sum by (app, le) (rate(http_server_requests_seconds_bucket{uri="/work"}[6s])))', "{{app}}")]},
    {"title": "JIT 컴파일에 쓴 시간 (초당 ms, jvm_compilation_time_ms_total)", "unit": "ms",
     "targets": [('rate(jvm_compilation_time_ms_total[6s]) * 1', "{{app}}")]},
    {"title": "프로세스 CPU 사용률 (컨테이너 한도 0.5 CPU 기준이 아님, 호스트 코어 기준)", "unit": "percentunit",
     "targets": [('process_cpu_usage', "{{app}}")]},
]
