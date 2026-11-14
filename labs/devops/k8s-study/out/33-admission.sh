#!/usr/bin/env bash
# 33편: 어드미션. mutating 플러그인이 요청을 고치고 validating 플러그인이 거절하는 모습, 그리고 그 순서.
# w32 네임스페이스 안에서만 만들고(ResourceQuota·LimitRange·파드·네임스페이스 라벨) 끝에 네임스페이스째 지운다.
# 실습 저장소 루트(./lab 이 있는 곳)에서 bash <이 스크립트> 로 실행
set -u
K="./lab kubectl"
echo "# 33편: 어드미션 ($(date '+%F %T %Z'), Mac 에서 실습 저장소 루트로 bash 33-admission.sh 실행, w32 네임스페이스만 쓰고 지움)"

# 파드 매니페스트: pod <이름> [메모리 requests=limits]
pod() {
  if [ -n "${2:-}" ]; then res="resources: {requests: {memory: $2}, limits: {memory: $2}}"; else res=""; fi
  printf 'apiVersion: v1\nkind: Pod\nmetadata: {name: %s, namespace: %s}\nspec:\n%s  containers:\n  - name: c\n    image: nginx:1.25.1-alpine\n    %s\n' "$1" "${NS:-w32}" "${EXTRA:-}" "$res"
}
# kubectl 이 받은 HTTP 상태 줄만 뽑는다
status() { grep -o 'verb="[A-Z]*" url="[^"?]*[^"]*" status="[^"]*"' | sed -E 's/url="https:\/\/[^/]*/url="/; s/\?[^"]*"/"/' | tail -1; }

echo; echo "## 1. 우리 클러스터에 붙은 어드미션 웹훅과 정책"
for r in mutatingwebhookconfigurations validatingwebhookconfigurations mutatingadmissionpolicies validatingadmissionpolicies; do
  printf '  %-34s %s개\n' "$r" "$($K get $r --no-headers 2>/dev/null | wc -l | tr -d ' ')"
done

echo; echo "## 2. 기본으로 켜지는 플러그인: v1.37.2 바이너리 --help 와 문서(Kubernetes 1.37) 목록 비교"
BIN=$($K -n kube-system exec kube-apiserver-k8s-master -- kube-apiserver --help 2>/dev/null | grep -E -- '--enable-admission-plugins strings' | grep -oE 'default enabled ones \([^)]*\)' | sed 's/default enabled ones (//; s/)$//' | tr ',' '\n' | sed 's/^ *//')
# 문서 목록: https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/#which-plugins-are-enabled-by-default (2026-11-14 확인, 1.37)
DOC="CertificateApproval CertificateSigning CertificateSubjectRestriction DefaultIngressClass DefaultStorageClass DefaultTolerationSeconds LimitRanger MutatingAdmissionPolicy MutatingAdmissionWebhook NamespaceLifecycle PersistentVolumeClaimResize PodSecurity Priority ResourceQuota RuntimeClass ServiceAccount StorageObjectInUseProtection TaintNodesByCondition ValidatingAdmissionPolicy ValidatingAdmissionWebhook"
echo "  바이너리 --help 의 기본 목록 $(echo "$BIN" | wc -l | tr -d ' ')개 (적힌 순서):"
echo "$BIN" | paste -sd' ' - | fold -s -w 120 | sed 's/^/    /'
echo "  문서 목록 $(echo $DOC | wc -w | tr -d ' ')개"
echo "  바이너리에만 있는 것: $(comm -23 <(echo "$BIN" | sort) <(echo $DOC | tr ' ' '\n' | sort) | paste -sd' ' -)"
echo "  문서에만 있는 것: $(comm -13 <(echo "$BIN" | sort) <(echo $DOC | tr ' ' '\n' | sort) | paste -sd' ' - )(없음이면 빈칸)"
echo "  --help 의 플래그 설명 끝 문장: $($K -n kube-system exec kube-apiserver-k8s-master -- kube-apiserver --help 2>/dev/null | grep -E -- '--enable-admission-plugins strings' | grep -oE 'The order of plugins[^.]*\.')"
echo "  kubeadm 이 더 켠 것: $($K -n kube-system get pod kube-apiserver-k8s-master -o jsonpath='{range .spec.containers[0].command[*]}{@}{"\n"}{end}' | grep -E -- '--(enable|disable)-admission-plugins')"

$K create namespace w32 >/dev/null
T=$(mktemp)   # kubectl -v=6 로그를 잠깐 담는 파일

echo; echo "## 3. mutating: 이름과 이미지만 보낸 파드가 저장 직전에 어떻게 바뀌나 (--dry-run=server)"
echo "mac\$ cat bare.yaml"; pod bare | sed 's/^/  /'
echo "mac\$ kubectl apply -f bare.yaml --dry-run=server -o json   (어드미션이 붙인 칸만 골라 봄)"
pod bare | $K apply -f - --dry-run=server -o json | python3 -c '
import json,sys;p=json.load(sys.stdin)["spec"]
print("  serviceAccountName :", p.get("serviceAccountName"))
print("  volumes            :", [v["name"] for v in p.get("volumes",[])])
print("  volumeMounts       :", [(m["name"],m["mountPath"]) for m in p["containers"][0].get("volumeMounts",[])])
print("  tolerations        :", [(t["key"],t["effect"],t.get("tolerationSeconds")) for t in p.get("tolerations",[])])
print("  priority           :", p.get("priority"))
print("  resources          :", p["containers"][0].get("resources"))'

echo; echo "## 4. 어드미션이 거절하는 예 두 가지 (소스상 둘 다 mutating 단계의 Admit 에서 거절)"
echo "mac\$ kubectl apply -f <(serviceAccountName: nobody 를 넣은 파드) --dry-run=server"
EXTRA="  serviceAccountName: nobody
" pod sa-missing | $K apply -f - --dry-run=server 2>&1
echo "mac\$ kubectl apply -f <(namespace: w32-none 인 파드) --dry-run=server"
NS=w32-none pod ns-missing | $K apply -f - --dry-run=server 2>&1

echo; echo "## 5. ResourceQuota(validating) 와 LimitRange(mutating) 의 순서"
echo "mac\$ kubectl -n w32 create quota mem --hard=requests.memory=256Mi,limits.memory=256Mi"
$K -n w32 create quota mem --hard=requests.memory=256Mi,limits.memory=256Mi
echo "mac\$ kubectl create -f bare.yaml -v=6   # 메모리를 적지 않은 파드"
pod bare | $K create -f - -v=6 2>&1 | tee $T | grep -E '^(Error|Warning|pod/)'
echo "  HTTP: $(status < $T)"; : > $T
echo
echo "mac\$ kubectl -n w32 create -f limitrange.yaml   # 컨테이너 기본값 limits 128Mi, requests 64Mi, 최대 192Mi"
cat <<'Y' | $K create -f -
apiVersion: v1
kind: LimitRange
metadata: {name: mem-default, namespace: w32}
spec:
  limits:
  - type: Container
    default: {memory: 128Mi}
    defaultRequest: {memory: 64Mi}
    max: {memory: 192Mi}
Y
echo "mac\$ kubectl create -f bare.yaml   # 같은 파드를 다시"
pod bare | $K create -f - 2>&1
echo "mac\$ kubectl -n w32 get pod bare -o jsonpath='{.spec.containers[0].resources} {.metadata.annotations}'"
echo "  $($K -n w32 get pod bare -o jsonpath='{.spec.containers[0].resources}')"
echo "  $($K -n w32 get pod bare -o jsonpath='{.metadata.annotations}')"
echo "mac\$ kubectl -n w32 get quota mem"
$K -n w32 get quota mem
echo
echo "mac\$ kubectl create -f big.yaml   # requests=limits 160Mi (LimitRange 최대 192Mi 안쪽, 남은 쿼터 128Mi 바깥)"
pod big 160Mi | $K create -f - -v=6 2>&1 | tee $T | grep -E '^(Error|Warning|pod/)'
echo "  HTTP: $(status < $T)"; : > $T
echo "mac\$ kubectl create -f huge.yaml   # requests=limits 300Mi (LimitRange 최대 192Mi 바깥)"
pod huge 300Mi | $K create -f - 2>&1
echo "mac\$ kubectl -n w32 get pods   # 읽기 요청은 어드미션을 거치지 않는다"
$K -n w32 get pods

echo; echo "## 6. PodSecurity(validating): 네임스페이스 라벨 하나로 거절 기준이 바뀐다"
echo "mac\$ kubectl label ns w32 pod-security.kubernetes.io/enforce=restricted"
$K label ns w32 pod-security.kubernetes.io/enforce=restricted 2>&1
echo "mac\$ kubectl apply -f bare2.yaml --dry-run=server -v=6"
pod bare2 | $K apply -f - --dry-run=server -v=6 2>&1 | tee $T | grep -E '^(Error|Warning|pod/)'
echo "  HTTP: $(status < $T)"; : > $T

echo; echo "## 7. 정리"
rm -f "$T"
$K delete namespace w32 --wait=true
