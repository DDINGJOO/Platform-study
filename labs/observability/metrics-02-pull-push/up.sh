#!/usr/bin/env bash
# 메트릭 수집 실습-2: kind 클러스터를 만들고 앱 이미지를 올린 뒤 전부 배포한다.
# kubectl 은 항상 --context 로 이 클러스터만 가리킨다. kind 가 바꾼 현재 컨텍스트는 원래대로 돌려놓는다.
set -euo pipefail
cd "$(dirname "$0")"
CTX=kind-obs-lab-metrics-02
PREV=$(kubectl config current-context 2>/dev/null || true)
kind create cluster --config kind.yaml
[ -n "$PREV" ] && kubectl config use-context "$PREV" >/dev/null
docker build -t obs-lab/metrics-02-pull-push:dev app
kind load docker-image --name obs-lab-metrics-02 obs-lab/metrics-02-pull-push:dev
k() { kubectl --context "$CTX" "$@"; }
k apply -f k8s/prometheus.yaml -f k8s/otel-collector.yaml
k -n obs create configmap grafana-dashboards \
  --from-file=provider.yaml=k8s/grafana-provider.yaml --from-file=dashboard.json=k8s/dashboard.json
k apply -f k8s/grafana.yaml -f k8s/apps.yaml
k -n obs wait --for=condition=available deploy --all --timeout=600s
echo "Prometheus http://localhost:21290  Grafana http://localhost:21200 (대시보드: pull과 push가 조용해지는 방식)"
