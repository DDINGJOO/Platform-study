# 실습-1 대시보드 패널. ../common-envoy/scripts/make-dashboard.py 가 grafana/lab.json 으로 만든다
UID = "tm01"
TITLE = "트래픽 실습-1 느린 서버 한 대"
PANELS = [
    {"title": "인스턴스별 초당 요청 수", "unit": "reqps",
     "targets": [('sum by (app) (rate(http_server_requests_seconds_count{uri="/work"}[10s]))', "{{app}}")]},
    {"title": "인스턴스별 p99 (앱이 잰 처리 시간, 줄 선 시간 포함)", "unit": "s",
     "targets": [('histogram_quantile(0.99, sum by (app, le) (rate(http_server_requests_seconds_bucket{uri="/work"}[10s])))', "{{app}}")]},
    {"title": "Envoy가 본 전체 p99 (upstream_rq_time)", "unit": "ms",
     "targets": [('histogram_quantile(0.99, sum by (le) (rate(envoy_cluster_upstream_rq_time_bucket{envoy_cluster_name="backend"}[10s])))', "전체 p99")]},
    {"title": "요청이 도착했을 때 이미 처리 중이던 요청 수 p99", "unit": "short",
     "targets": [('histogram_quantile(0.99, sum by (app, le) (rate(lab_inflight_at_arrival_bucket[10s])))', "{{app}}")]},
]
