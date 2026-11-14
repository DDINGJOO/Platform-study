#!/usr/bin/env bash
# 아키텍처 그림 읽기: ① 모든 구성 요소는 API 서버(6443)에만 붙고 etcd(2379)에는 API 서버만 붙는다 ② 요청 하나가 거치는 인증·인가·어드미션 (Mac 에서 실행)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"
echo "# E20 허브 구조와 인증·인가·어드미션 ($(date '+%F %T %Z'))"
echo; echo "## 1. 누가 누구에게 TCP 로 붙어 있나 (마스터·worker1 의 ss, 프로세스별 상대 포트)"
for n in master 1; do
  echo "[$( [ $n = master ] && echo k8s-master || echo k8s-worker1 )]"
  ./lab ssh $n -- sudo sh -c "ss -tnpH state established | awk '{print \$3, \$4, \$5}'" | python3 -c '
import sys,re,collections
c=collections.Counter()
for l in sys.stdin:
    loc,peer,proc=(l.split()+["",""])[:3]
    m=re.search(r"\(\(\"([^\"]+)\"",proc)
    if not m: continue
    name=m.group(1); lp=loc.rsplit(":",1)[1]; pp=peer.rsplit(":",1)[1]
    if pp in ("6443","2379","10250"): c[(name,"→ :"+pp)]+=1
    elif lp in ("6443","2379","10250") and name in ("kube-apiserver","etcd","kubelet"): c[(name,":"+lp+" ← 받는 쪽")]+=1
for (name,d),v in sorted(c.items()): print(f"  {name:24s} {d:18s} 연결 {v}개")'
done
echo; echo "## 2. 인증(Authentication): 인증서 없이 API 서버에 요청"
echo "  curl -k https://192.168.104.1:6443/api/v1/namespaces/default/pods → $(./lab ssh 1 -- curl -sk -o /dev/null -w '%{http_code}' https://192.168.104.1:6443/api/v1/namespaces/default/pods) (anonymous 로 들어가 인가에서 막힘이면 403, 인증 실패면 401)"
echo "  응답 본문: $(./lab ssh 1 -- curl -sk https://192.168.104.1:6443/api/v1/namespaces/default/pods | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d.get("code"), d.get("reason"), "|", d.get("message"))')"
echo "  API 서버 플래그: $($K -n kube-system get pod kube-apiserver-k8s-master -o jsonpath='{range .spec.containers[0].command[*]}{@}{"\n"}{end}' | grep -E '^--(client-ca-file|authorization-mode|enable-admission-plugins|anonymous-auth|service-account-key-file)=' | paste -sd' ' -)"
echo; echo "## 3. 인가(Authorization, RBAC): 인증은 됐지만 권한이 없는 사용자"
echo "  kubectl auth can-i list pods --as=system:serviceaccount:default:default → $($K auth can-i list pods --as=system:serviceaccount:default:default 2>&1)"
echo "  kubectl get pods --as=system:serviceaccount:default:default → $($K get pods --as=system:serviceaccount:default:default 2>&1 | cut -c1-150)"
echo "  kubectl auth can-i list pods (관리자 kubeconfig) → $($K auth can-i list pods)"
echo "  관리자 kubeconfig 의 사용자: $($K auth whoami -o jsonpath='{.status.userInfo.username} groups={.status.userInfo.groups}' 2>&1)"
echo; echo "## 4. 어드미션(Admission): 저장 전에 API 서버가 요청을 고치고(mutating) 검사함 (--dry-run=server)"
cat > /tmp/e20-pod.yaml <<'Y'
apiVersion: v1
kind: Pod
metadata: {name: admission-demo}
spec:
  containers: [{name: c, image: nginx:1.25.1-alpine}]
Y
echo "  내가 보낸 spec: containers 하나(name, image)만"
$K apply -f /tmp/e20-pod.yaml --dry-run=server -o json | python3 -c '
import json,sys;p=json.load(sys.stdin)["spec"]
print("  저장될 spec 에 붙은 것 (어드미션 플러그인이 붙인 것):")
print("   [ServiceAccount]           serviceAccountName =", p.get("serviceAccountName"), "| volumes =", [v["name"] for v in p.get("volumes",[])])
print("   [DefaultTolerationSeconds] tolerations =", [(t["key"].split("/")[-1], t["effect"], t.get("tolerationSeconds")) for t in p.get("tolerations",[])])
print("   [Priority]                 priority =", p.get("priority"))
print("  (그 밖에 API 기본값으로 채워진 것: imagePullPolicy =", p["containers"][0].get("imagePullPolicy"), ", enableServiceLinks =", p.get("enableServiceLinks"), ", preemptionPolicy =", p.get("preemptionPolicy"), ")")'
echo "  API 서버 기본 어드미션 플러그인 목록 (kube-apiserver --help 의 --enable-admission-plugins 설명):"
$K -n kube-system exec kube-apiserver-k8s-master -- kube-apiserver --help 2>/dev/null | grep -E -- '--enable-admission-plugins strings' | grep -oE 'default enabled ones \([^)]*\)' | sed 's/default enabled ones (//; s/)$//' | tr ',' '\n' | sed 's/^ *//' | paste -sd' ' - | fold -s -w 140 | sed 's/^/   /'
rm -f /tmp/e20-pod.yaml
