# 실습-2 대시보드 패널. ../common-envoy/scripts/make-dashboard.py 가 grafana/lab.json 으로 만든다
UID = "tm02"
TITLE = "트래픽 실습-2 빨리 실패하는 서버"
PANELS = [
    {"title": "인스턴스별 초당 요청 수 (앱 지표, 503 포함)", "unit": "reqps",
     "targets": [('sum by (app) (rate(http_server_requests_seconds_count{uri="/work"}[10s]))', "{{app}}")]},
    {"title": "Envoy가 돌려준 응답 중 5xx 비율", "unit": "percentunit", "max": 1,
     "targets": [('sum(rate(envoy_cluster_upstream_rq_xx{envoy_cluster_name="backend",envoy_response_code_class="5"}[10s])) / sum(rate(envoy_cluster_upstream_rq_xx{envoy_cluster_name="backend"}[10s]))', "5xx 비율")]},
    {"title": "outlier detection: 지금 빠져 있는 서버 수 (ejections_active)", "unit": "short", "step": True,
     "targets": [('envoy_cluster_outlier_detection_ejections_active{envoy_cluster_name="backend"}', "ejections_active")]},
    {"title": "outlier detection 누적 카운터", "unit": "short", "step": True,
     "targets": [('envoy_cluster_outlier_detection_ejections_detected_consecutive_5xx{envoy_cluster_name="backend"}', "detected_consecutive_5xx"),
                 ('envoy_cluster_outlier_detection_ejections_enforced_consecutive_5xx{envoy_cluster_name="backend"}', "enforced_consecutive_5xx"),
                 ('envoy_cluster_outlier_detection_ejections_overflow{envoy_cluster_name="backend"}', "overflow")]},
]
