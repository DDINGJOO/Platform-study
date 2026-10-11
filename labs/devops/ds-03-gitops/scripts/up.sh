#!/usr/bin/env bash
# kind 클러스터 ds-03 + gitea + Argo CD 를 띄우고, 실습 저장소를 밀어 넣고, Application 을 만든다.
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/env.sh

kind create cluster --config cluster/kind.yaml
k apply -f cluster/gitea.yaml

k create namespace argocd
# Argo CD 3.x CRD 는 커서 client-side apply 의 annotation 한도를 넘는다. 공식 문서대로 server-side 로 넣는다.
k apply -n argocd --server-side --force-conflicts \
  -f "https://raw.githubusercontent.com/argoproj/argo-cd/${ARGOCD_VERSION}/manifests/install.yaml"
# 실습이라 TLS 를 끄고(웹훅을 http 로 받기 위해) NodePort 로 연다
k -n argocd patch configmap argocd-cmd-params-cm --type merge -p '{"data":{"server.insecure":"true"}}'
k -n argocd patch svc argocd-server --type merge \
  -p '{"spec":{"type":"NodePort","ports":[{"name":"http","port":80,"targetPort":8080,"nodePort":30080},{"name":"https","port":443,"targetPort":8080,"nodePort":30443}]}}'
# 메모리를 아끼려고 이번 실습에 안 쓰는 부품은 끈다
k -n argocd scale deploy argocd-dex-server argocd-notifications-controller argocd-applicationset-controller --replicas=0
k -n argocd rollout restart deploy argocd-server

k -n gitea rollout status deploy/gitea --timeout=180s
# INSTALL_LOCK 으로 설치 화면을 건너뛰면 첫 요청 전까지 DB 테이블이 없다. 먼저 migrate 한다.
k -n gitea exec deploy/gitea -- gitea migrate >/dev/null
k -n gitea exec deploy/gitea -- gitea admin user create --username "$GITEA_USER" \
  --password "$GITEA_PASS" --email "$LAB_EMAIL" --admin --must-change-password=false
until curl -sf -o /dev/null "$GITEA_URL/api/v1/version"; do sleep 3; done   # NodePort 로 응답이 올 때까지
curl -sf -u "$GITEA_USER:$GITEA_PASS" -H 'Content-Type: application/json' \
  -d '{"name":"demo","private":false,"default_branch":"main"}' "$GITEA_URL/api/v1/user/repos" >/dev/null

rm -rf "$WORK" && mkdir -p "$WORK" && cp -R repo-seed/. "$WORK/"
git -C "$WORK" init -q -b main
git -C "$WORK" add -A
git -C "$WORK" -c user.name=lab -c user.email="$LAB_EMAIL" commit -qm "web v1: replicas 2"
git -C "$WORK" remote add origin "http://$GITEA_USER:$GITEA_PASS@localhost:26030/$GITEA_USER/demo.git"
git -C "$WORK" push -q origin main

k -n argocd rollout status deploy/argocd-repo-server --timeout=300s
k -n argocd rollout status statefulset/argocd-application-controller --timeout=300s
k -n argocd rollout status deploy/argocd-server --timeout=300s
k apply -f cluster/app.yaml
echo "Argo CD UI: http://localhost:26080  (admin / $(k -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d))"
