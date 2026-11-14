#!/usr/bin/env bash
# etcd 가 클러스터의 단일 진실 공급원(SSOT)인지 확인: kubectl 이 보는 값 = etcd 에 저장된 값 (Mac 에서 실행)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"; ts(){ date '+%T'; }
E=(-n kube-system exec etcd-k8s-master -- etcdctl --endpoints=https://127.0.0.1:2379
   --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt --key=/etc/kubernetes/pki/etcd/server.key)
J=/tmp/e6.json
echo "# E6 etcd 는 정말 단일 진실 공급원인가 ($(date '+%F %T %Z'))"
echo; echo "## 1. etcd 상태 (etcd 파드 안의 etcdctl, API 서버와 같은 인증서 사용)"
$K "${E[@]}" endpoint status -w table
echo; echo "## 2. etcd 에 저장된 키 (/registry 아래)"
$K "${E[@]}" get /registry --prefix --keys-only > /tmp/e6-keys.txt
echo "키 개수: $(grep -c '^/registry' /tmp/e6-keys.txt)"
echo "종류별 개수 (상위 15):"; grep '^/registry' /tmp/e6-keys.txt | awk -F/ '{print $3}' | sort | uniq -c | sort -rn | head -15
echo "myweb 관련 키 (이벤트 $(grep -c '/events/default/myweb' /tmp/e6-keys.txt)개는 생략):"; grep -E '/default/myweb' /tmp/e6-keys.txt | grep -v /events/
echo; echo "## 3. kubectl 의 resourceVersion = etcd 의 mod_revision"
rv(){ $K get deploy myweb -o jsonpath='{.metadata.resourceVersion}'; }
mr(){ $K "${E[@]}" get /registry/deployments/default/myweb -w json > $J; python3 -c "import json;print(json.load(open('$J'))['kvs'][0]['mod_revision'])"; }
echo "$(ts) kubectl resourceVersion=$(rv) | etcd mod_revision=$(mr)"
echo "$(ts) mac\$ kubectl scale deploy myweb --replicas=6"; $K scale deploy myweb --replicas=6 >/dev/null; sleep 2
echo "$(ts) kubectl resourceVersion=$(rv) | etcd mod_revision=$(mr)"
echo "$(ts) mac\$ kubectl scale deploy myweb --replicas=5"; $K scale deploy myweb --replicas=5 >/dev/null; sleep 2
echo "$(ts) kubectl resourceVersion=$(rv) | etcd mod_revision=$(mr)"
echo; echo "## 4. 저장 형식: 기본 리소스는 protobuf(k8s\\0 접두어), CRD 는 JSON"
$K "${E[@]}" get /registry/deployments/default/myweb -w json > $J
python3 -c "import json,base64;v=base64.b64decode(json.load(open('$J'))['kvs'][0]['value']);print('Deployment myweb 앞 24바이트:',v[:24])"
IPK=$(grep -m1 '^/registry/crd.projectcalico.org/ippools/' /tmp/e6-keys.txt)
$K "${E[@]}" get "$IPK" -w json > $J
python3 -c "import json,base64;v=base64.b64decode(json.load(open('$J'))['kvs'][0]['value']);print('$IPK 앞 80바이트:',v[:80])"
echo; echo "## 5. Secret 은 etcd 에 어떻게 저장되나 (실습용 가짜 값으로)"
echo "API 서버 암호화 설정 플래그: $($K -n kube-system get pod kube-apiserver-k8s-master -o jsonpath='{.spec.containers[0].command}' | tr ',' '\n' | grep -c encryption-provider-config)개"
$K create secret generic ssot-demo --from-literal=password=hello-ssot >/dev/null
echo "kubectl get secret ssot-demo -o jsonpath='{.data.password}' → $($K get secret ssot-demo -o jsonpath='{.data.password}') (base64)"
$K "${E[@]}" get /registry/secrets/default/ssot-demo -w json > $J
python3 -c "import json,base64;v=base64.b64decode(json.load(open('$J'))['kvs'][0]['value']);i=v.find(b'hello-ssot');print('etcd 원본에 hello-ssot 평문이', '있음' if i>=0 else '없음', v[max(0,i-12):i+10] if i>=0 else '')"
$K delete secret ssot-demo >/dev/null && echo "$(ts) ssot-demo 삭제"
echo "$(ts) 삭제 뒤 etcd 조회 결과 키 개수: $($K "${E[@]}" get /registry/secrets/default/ssot-demo --keys-only | grep -c ssot-demo)"
rm -f $J /tmp/e6-keys.txt
