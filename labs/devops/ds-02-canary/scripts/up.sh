#!/usr/bin/env bash
# kind 클러스터 ds-02 를 만들고 Argo Rollouts, 프로메테우스, judge, 앱을 올린다
set -euo pipefail
cd "$(dirname "$0")/.."
ROLLOUTS=v1.10.0
kind get clusters | grep -qx ds-02 || kind create cluster --config kind.yaml
docker build -q -t obs-lab/ds-02-canary:dev app
docker build -q -t obs-lab/ds-02-canary-judge:dev judge
# 클러스터 안에서 받지 않도록 미리 받아서 넣는다. 여러 플랫폼이 든 이미지를 kind load docker-image 로
# 넣으면 "content digest ... not found" 로 실패해서, 노드 플랫폼 하나만 tar 로 저장해 넣는다
TMP=$(mktemp -d)
for i in obs-lab/ds-02-canary:dev obs-lab/ds-02-canary-judge:dev \
         quay.io/argoproj/argo-rollouts:$ROLLOUTS prom/prometheus:v3.15.0 grafana/k6:2.3.0; do
  docker image inspect "$i" >/dev/null 2>&1 || docker pull -q "$i"
  f="$TMP/$(echo "$i" | tr '/:' '__').tar"
  docker save --platform "linux/$(docker version -f '{{.Server.Arch}}')" -o "$f" "$i"
  kind load image-archive --name ds-02 "$f"
done
rm -rf "$TMP"
K="kubectl --context kind-ds-02"
$K create namespace argo-rollouts --dry-run=client -o yaml | $K apply -f -
# CRD 가 커서 client-side apply 는 last-applied 주석 256KiB 제한에 걸린다
$K apply --server-side -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/download/$ROLLOUTS/install.yaml
# 컨트롤러도 리더 선출을 끈다(복제본 하나)
$K -n argo-rollouts patch deploy argo-rollouts --type json \
  -p '[{"op":"add","path":"/spec/template/spec/containers/0/args","value":["--leader-elect=false"]}]'
$K -n argo-rollouts rollout status deploy/argo-rollouts --timeout=300s
$K apply -f k8s/00-base.yaml
$K apply -f k8s/analysis.yaml
$K -n ds02 rollout status deploy/prometheus --timeout=300s
$K -n ds02 rollout status deploy/judge --timeout=120s
