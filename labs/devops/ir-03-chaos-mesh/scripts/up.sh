#!/usr/bin/env bash
# kind 클러스터 ir-03 을 만들고 Chaos Mesh, 프로메테우스, 실험 대상 서비스를 올린다
set -euo pipefail
cd "$(dirname "$0")/.."
CM=2.8.4            # Chaos Mesh
HELM=3.22.0         # helm 은 설치하지 않고 컨테이너로 템플릿만 그린다
K="kubectl --context kind-ir-03"

kind get clusters | grep -qx ir-03 || kind create cluster --config kind.yaml
docker build -q -t obs-lab/ir-03-chaos-mesh:dev app

# 여러 플랫폼이 든 이미지를 kind load docker-image 로 넣으면 "content digest ... not found" 로
# 실패한다(배포 안전성 실습에서 겪었다). 노드 플랫폼 하나만 tar 로 저장해 넣는다
ARCH=$(docker version -f '{{.Server.Arch}}')
TMP=$(mktemp -d)
for i in obs-lab/ir-03-chaos-mesh:dev prom/prometheus:v3.15.0 \
         ghcr.io/chaos-mesh/chaos-mesh:v$CM ghcr.io/chaos-mesh/chaos-daemon:v$CM; do
  docker image inspect "$i" >/dev/null 2>&1 || docker pull -q --platform "linux/$ARCH" "$i"
  f="$TMP/$(echo "$i" | tr '/:' '__').tar"
  docker save --platform "linux/$ARCH" -o "$f" "$i"
  kind load image-archive --name ir-03 "$f"
done
rm -rf "$TMP"

# Chaos Mesh: 공식 차트를 helm template 으로 그려서 넣는다
#  - kind 노드의 런타임은 containerd 다. 차트 기본값(docker)으로 두면 chaos-daemon 이 컨테이너를 못 찾는다
#  - 컨트롤러는 하나만, 리더 선출 끔, 대시보드는 쓰지 않는다
#  - enableFilterNamespace=true: chaos-mesh.org/inject=enabled 주석이 붙은 네임스페이스에만 주입된다
mkdir -p .cache
[ -f .cache/chaos-mesh-$CM.tgz ] || curl -sfL -o .cache/chaos-mesh-$CM.tgz https://charts.chaos-mesh.org/chaos-mesh-$CM.tgz
docker run --rm -v "$PWD/.cache:/apps" alpine/helm:$HELM template chaos-mesh /apps/chaos-mesh-$CM.tgz \
  --namespace chaos-mesh --include-crds \
  --set chaosDaemon.runtime=containerd \
  --set chaosDaemon.socketPath=/run/containerd/containerd.sock \
  --set controllerManager.replicaCount=1 \
  --set controllerManager.leaderElection.enabled=false \
  --set controllerManager.enableFilterNamespace=true \
  --set dashboard.create=false \
  > .cache/chaos-mesh-$CM.yaml
$K create namespace chaos-mesh --dry-run=client -o yaml | $K apply -f -
# CRD 가 커서 client-side apply 는 last-applied 주석 256KiB 제한에 걸린다
$K apply --server-side -f .cache/chaos-mesh-$CM.yaml
$K -n chaos-mesh rollout status deploy/chaos-controller-manager --timeout=300s
$K -n chaos-mesh rollout status ds/chaos-daemon --timeout=300s

$K apply -f k8s/00-base.yaml
$K annotate namespace ir03 chaos-mesh.org/inject=enabled --overwrite
for d in prometheus stock front loadgen; do $K -n ir03 rollout status deploy/$d --timeout=180s; done
echo "프로메테우스: $K -n ir03 port-forward svc/prometheus 29090:9090"
