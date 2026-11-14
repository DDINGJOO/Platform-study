#!/usr/bin/env bash
# 35편: 구성 요소가 어디서 연결을 받고, 누가 먼저 연결을 열고, 어떤 형식과 신원으로 API 서버에 붙는지 조회만 해서 모은다.
# 실습 저장소 루트(./lab 이 있는 곳)에서 실행한다. 클러스터의 어떤 객체도 만들거나 고치지 않는다.
set -u
echo "# 구성 요소의 연결 지도: 받는 주소, 먼저 여는 쪽, 요청 형식, 신원 ($(date '+%F %T %Z'))"

echo
echo "## 1. 노드마다 TCP 연결을 받는 주소 (ss -tlnp, sshd·systemd-resolved 는 뺌)"
for n in master 1 2 3; do
./lab ssh $n -- sudo bash -s <<'R'
H=$(hostname | sed 's/^lima-//')
echo "[$H]"
ss -tlnpH | awk '{print $4, $6}' | sed -E 's/users:\(\("([^"]+)".*/\1/' | grep -vE 'sshd|systemd-resolve' \
  | sort -k2,2 -k1,1 | awk '{printf "  %-18s %s\n", $2, $1}'
R
done

echo
echo "## 2. 받는 주소를 정한 설정"
./lab ssh master -- sudo bash -s <<'R'
M=/etc/kubernetes/manifests
echo "[k8s-master 정적 파드 매니페스트]"
grep -hE -- '- --(advertise-address|secure-port|bind-address|listen-client-urls|listen-peer-urls|listen-metrics-urls)=' $M/kube-apiserver.yaml | sed 's/^ */  kube-apiserver          /'
grep -hE -- '- --(bind-address)=' $M/kube-scheduler.yaml | sed 's/^ */  kube-scheduler          /'
grep -hE -- '- --(bind-address)=' $M/kube-controller-manager.yaml | sed 's/^ */  kube-controller-manager /'
grep -hE -- '- --(listen-client-urls|listen-peer-urls|listen-metrics-urls)=' $M/etcd.yaml | sed 's/^ */  etcd                    /'
echo "  etcd 피어 포트 2380 에 맺어진 연결: $(ss -tnH state established '( sport = :2380 or dport = :2380 )' | wc -l)개"
R
./lab ssh 1 -- sudo bash -s <<'R'
echo "[k8s-worker1]"
echo "  kubelet → containerd:  $(grep containerRuntimeEndpoint /var/lib/kubelet/config.yaml | sed 's/^ *//')"
echo "  containerd 의 CRI 스트리밍 서버 설정: $(containerd config dump 2>/dev/null | grep -E '^ *stream_server_(address|port)' | sed 's/^ *//' | tr '\n' ' ')"
R
echo "[kube-proxy ConfigMap]"
./lab kubectl -n kube-system get cm kube-proxy -o jsonpath='{.data.config\.conf}' | grep -E '^(metricsBindAddress|healthzBindAddress):' | sed 's/^/  /'

echo
echo "## 3. API 서버가 먼저 여는 연결 (k8s-master 의 kube-apiserver 프로세스, 자기 6443 이 아닌 쪽에서 나간 연결의 상대 포트별 개수)"
./lab ssh master -- sudo bash -s <<'R'
ss -tnpH state established | grep '"kube-apiserver"' | awk '{split($3,l,":"); split($4,p,":"); if (l[length(l)] != "6443") print ":" p[length(p)]}' | sort | uniq -c | awk '{printf "  kube-apiserver → %-7s %s개\n", $2, $1}'
echo "  kubelet 관련 플래그:"
grep -hE -- '- --kubelet-' /etc/kubernetes/manifests/kube-apiserver.yaml | sed 's/^ */    /'
grep -q -- '--kubelet-certificate-authority' /etc/kubernetes/manifests/kube-apiserver.yaml && echo "    (--kubelet-certificate-authority 있음)" || echo "    (--kubelet-certificate-authority 없음)"
R
echo "  웹훅 설정: validating $(./lab kubectl get validatingwebhookconfigurations --no-headers 2>/dev/null | wc -l | tr -d ' ')개, mutating $(./lab kubectl get mutatingwebhookconfigurations --no-headers 2>/dev/null | wc -l | tr -d ' ')개"
echo "  API 서버 밖으로 넘기는 APIService(SERVICE 가 Local 이 아닌 것): $(./lab kubectl get apiservices --no-headers 2>/dev/null | awk '$2 != "Local"' | wc -l | tr -d ' ')개"

echo
echo "## 4. API 서버에 보내는 요청 본문 형식"
./lab ssh master -- sudo bash -s <<'R'
export KUBECONFIG=/etc/kubernetes/admin.conf
echo "[kubectl get svc kubernetes -v=8 의 Accept 헤더]"
kubectl get svc kubernetes -v=8 2>&1 | grep -m1 -o 'Accept: .*' | sed 's/^/  /'
echo "[같은 REST 경로를 Accept 만 바꿔 요청 (kubectl proxy 경유, GET 만)]"
kubectl proxy --port=18035 >/dev/null 2>&1 &
P=$!; sleep 1
U=http://127.0.0.1:18035/api/v1/namespaces/default/services/kubernetes
for A in application/json application/vnd.kubernetes.protobuf; do
  printf '  Accept: %-36s → 응답 앞 16바이트(od -c):%s\n' "$A" "$(curl -s -H "Accept: $A" $U | head -c 16 | od -An -c | tr -s ' ' | head -1)"
done
kill $P
R
echo "[kubelet 이 실제로 쓰는 설정 (k8s-worker1 의 /configz)]"
./lab kubectl get --raw /api/v1/nodes/k8s-worker1/proxy/configz | python3 -c 'import json,sys; c=json.load(sys.stdin)["kubeletconfig"]; print("  contentType:", c.get("contentType"))'
echo "[kube-proxy ConfigMap 의 clientConnection.contentType]"
./lab kubectl -n kube-system get cm kube-proxy -o jsonpath='{.data.config\.conf}' | awk '/^clientConnection:/{f=1;next} f && /^[^ ]/{f=0} f && /contentType/' | sed 's/^ */  /'

echo
echo "## 5. 신원: kubeconfig 와 인증서의 주인, 그리고 API 서버가 그 요청을 누구로 보나 (kubectl auth whoami)"
./lab ssh master -- sudo bash -s <<'R'
cd /etc/kubernetes
for f in admin.conf scheduler.conf controller-manager.conf; do
  s=$(grep 'client-certificate-data' $f | awk '{print $2}' | base64 -d | openssl x509 -noout -subject -nameopt compat | sed 's/^subject=//')
  w=$(kubectl --kubeconfig=$f auth whoami -o jsonpath='{.status.userInfo.username} {.status.userInfo.groups}')
  printf '  %-24s 인증서 %-50s → whoami %s\n' "$f" "$s" "$w"
done
s=$(openssl x509 -noout -subject -nameopt compat -in /var/lib/kubelet/pki/kubelet-client-current.pem | sed 's/^subject=//')
w=$(kubectl --kubeconfig=kubelet.conf auth whoami -o jsonpath='{.status.userInfo.username} {.status.userInfo.groups}')
printf '  %-24s 인증서 %-50s → whoami %s\n' "kubelet.conf" "$s" "$w"
for c in apiserver-etcd-client apiserver-kubelet-client; do
  printf '  pki/%-20s %s\n' "$c.crt" "$(openssl x509 -noout -subject -issuer -nameopt compat -in pki/$c.crt | tr '\n' ' ')"
done
R
./lab ssh 1 -- sudo bash -s <<'R'
echo "  [k8s-worker1] kubelet 클라이언트 인증서 $(openssl x509 -noout -subject -nameopt compat -in /var/lib/kubelet/pki/kubelet-client-current.pem)"
echo "  [k8s-worker1] kubelet 서버 인증서(10250) $(openssl x509 -noout -subject -issuer -nameopt compat -in /var/lib/kubelet/pki/kubelet.crt | tr '\n' ' ')"
R

echo
echo "## 6. 신원에 권한을 붙이는 ClusterRoleBinding (roleRef ← subjects)"
for b in system:kube-scheduler system:volume-scheduler system:kube-controller-manager kubeadm:node-proxier kubeadm:apiserver-kubelet-client kubeadm:cluster-admins system:node calico-node calico-kube-controllers system:coredns; do
  ./lab kubectl get clusterrolebinding "$b" -o jsonpath='{.metadata.name}{"|"}{.roleRef.name}{"|"}{range .subjects[*]}{.kind}:{.namespace}{"/"}{.name}{" "}{end}' 2>/dev/null \
    | awk -F'|' '{s=$3; if (s=="") s="(subjects 없음)"; printf "  %-34s %-34s ← %s\n", $1, $2, s}'
  echo
done | sed '/^$/d'
./lab kubectl get clusterrolebinding -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.subjects[0].kind}{" "}{.subjects[0].namespace}{"\n"}{end}' \
  | awk '$1 ~ /^system:controller:/ {n++; k[$2" "$3]++} END {printf "  system:controller:* 바인딩 %d개, subject 종류:", n; for (x in k) printf " %s %d개", x, k[x]; print ""}'

echo
echo "## 7. 컨트롤 플레인 정적 파드가 노드에서 쓸 수 있는 경로 (미러 파드 spec 의 hostPath 마운트, readOnly 여부)"
./lab kubectl -n kube-system get pod -l tier=control-plane -o json | python3 -c '
import json, sys
for p in json.load(sys.stdin)["items"]:
    vols = {v["name"]: v["hostPath"]["path"] for v in p["spec"]["volumes"] if "hostPath" in v}
    rw, ro = [], []
    for c in p["spec"]["containers"]:
        for m in c.get("volumeMounts", []):
            if m["name"] in vols:
                (ro if m.get("readOnly") else rw).append(vols[m["name"]])
    print("  %-36s 쓰기 가능: %s" % (p["metadata"]["name"], ", ".join(rw) if rw else "없음"))
    print("  %-36s 읽기 전용: %s" % ("", ", ".join(ro) if ro else "없음"))
'
