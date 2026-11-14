#!/usr/bin/env bash
# etcd 백업 파일에도 Secret 이 평문으로 들어가나, 암호화(EncryptionConfiguration)를 켜면 etcd 에 어떻게 저장되나, 그리고 되돌리기 (Mac 에서 실행)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"; ts(){ date '+%T'; }
E=(-n kube-system exec etcd-k8s-master -- etcdctl --endpoints=https://127.0.0.1:2379 --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt --key=/etc/kubernetes/pki/etcd/server.key)
raw(){ $K "${E[@]}" get /registry/secrets/default/$1 -w json | python3 -c '
import json,sys,base64
v=base64.b64decode(json.load(sys.stdin)["kvs"][0]["value"])
print("앞 30바이트:", v[:30], "| 평문 %s 포함:" % sys.argv[1], sys.argv[1].encode() in v)' "$2"; }
waitapi(){ for i in $(seq 1 60); do sleep 2; $K get --raw /readyz >/dev/null 2>&1 && { echo "$(ts) API 서버 /readyz ok"; return; }; done; echo "$(ts) API 서버가 120초 안에 돌아오지 않음"; }
echo "# E26 etcd 백업과 Secret 암호화 ($(date '+%F %T %Z'))"
$K delete secret enc-before enc-after --ignore-not-found >/dev/null
echo; echo "## 1. 암호화 전: Secret 하나 만들기"
$K create secret generic enc-before --from-literal=password=plain-before >/dev/null
echo "$(ts) kubectl create secret generic enc-before --from-literal=password=plain-before"
echo "  etcd 원본 → $(raw enc-before plain-before)"
echo; echo "## 2. etcd 스냅숏(백업) 파일에도 평문으로 들어가나"
$K "${E[@]}" snapshot save /var/lib/etcd/snapshot-e26.db 2>&1 | tail -1
$K -n kube-system exec etcd-k8s-master -- etcdutl snapshot status /var/lib/etcd/snapshot-e26.db -w table 2>&1
echo "  스냅숏 파일 안에서 'plain-before' 문자열: $(./lab ssh master -- sudo sh -c 'grep -c -a plain-before /var/lib/etcd/snapshot-e26.db') 줄"
echo "  스냅숏 파일 권한: $(./lab ssh master -- sudo stat -c '%A %U %s' /var/lib/etcd/snapshot-e26.db)"
./lab ssh master -- sudo rm -f /var/lib/etcd/snapshot-e26.db && echo "  (스냅숏 파일 지움)"
echo; echo "## 3. 암호화 켜기: aescbc 키 + identity, API 서버 매니페스트에 플래그와 볼륨 추가"
./lab ssh master -- sudo bash -s <<'R'
set -e
mkdir -p /etc/kubernetes/enc /root/arch-exp-backup
KEY=$(head -c 32 /dev/urandom | base64)
cat > /etc/kubernetes/enc/enc.yaml <<Y
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources: [secrets]
    providers:
      - aescbc:
          keys:
            - name: key1
              secret: $KEY
      - identity: {}
Y
chmod 600 /etc/kubernetes/enc/enc.yaml
echo "  /etc/kubernetes/enc/enc.yaml (키 값은 출력하지 않음):"; sed 's/secret: .*/secret: <32바이트 키, base64>/' /etc/kubernetes/enc/enc.yaml | sed 's/^/    /'
cp /etc/kubernetes/manifests/kube-apiserver.yaml /root/arch-exp-backup/kube-apiserver.yaml.pre-enc
python3 - <<'P'
p='/etc/kubernetes/manifests/kube-apiserver.yaml'
s=open(p).read()
s=s.replace('    - kube-apiserver\n','    - kube-apiserver\n    - --encryption-provider-config=/etc/kubernetes/enc/enc.yaml\n',1)
s=s.replace('    volumeMounts:\n','    volumeMounts:\n    - mountPath: /etc/kubernetes/enc\n      name: enc\n      readOnly: true\n',1)
s=s.replace('  volumes:\n','  volumes:\n  - hostPath:\n      path: /etc/kubernetes/enc\n      type: DirectoryOrCreate\n    name: enc\n',1)
open(p+'.tmp','w').write(s)
import os; os.replace(p+'.tmp',p)
P
echo "  바뀐 줄:"; diff /root/arch-exp-backup/kube-apiserver.yaml.pre-enc /etc/kubernetes/manifests/kube-apiserver.yaml | sed 's/^/    /'
R
T0=$(date +%s); echo "$(ts) 매니페스트 저장 → kubelet 이 API 서버를 다시 띄움"; sleep 5; waitapi; echo "  API 서버가 다시 응답하기까지 약 $(( $(date +%s) - T0 ))초"
echo "  API 서버 플래그: $($K -n kube-system get pod kube-apiserver-k8s-master -o jsonpath='{range .spec.containers[0].command[*]}{@}{"\n"}{end}' | grep encryption)"
echo; echo "## 4. 암호화를 켠 뒤 만든 Secret"
$K create secret generic enc-after --from-literal=password=hello-enc >/dev/null
echo "$(ts) kubectl create secret generic enc-after --from-literal=password=hello-enc"
echo "  etcd 원본 enc-after  → $(raw enc-after hello-enc)"
echo "  etcd 원본 enc-before → $(raw enc-before plain-before)   (켜기 전에 쓴 것은 그대로)"
echo "  kubectl 로 읽으면: enc-after=$($K get secret enc-after -o jsonpath='{.data.password}' | base64 -d), enc-before=$($K get secret enc-before -o jsonpath='{.data.password}' | base64 -d)"
echo; echo "## 5. 켜기 전 Secret 다시 쓰기 (문서의 kubectl get … | kubectl replace -f -)"
$K get secret enc-before -o json | $K replace -f - >/dev/null && echo "$(ts) kubectl get secret enc-before -o json | kubectl replace -f -"
echo "  etcd 원본 enc-before → $(raw enc-before plain-before)"
echo "  /registry/secrets 전체 중 k8s:enc: 로 시작하는 값: $($K "${E[@]}" get /registry/secrets --prefix -w json | python3 -c '
import json,sys,base64
kv=json.load(sys.stdin).get("kvs",[]); n=sum(base64.b64decode(k["value"]).startswith(b"k8s:enc:") for k in kv); print(n, "/", len(kv))')"
echo; echo "## 6. 되돌리기 (문서의 해제 순서: identity 를 맨 앞에 → Secret 전부 다시 쓰기 → 설정 제거)"
$K delete secret enc-before enc-after >/dev/null && echo "$(ts) 실험용 Secret 두 개 삭제"
./lab ssh master -- sudo python3 - <<'P'
p='/etc/kubernetes/enc/enc.yaml'; s=open(p).read()
a=s.index('      - aescbc:'); b=s.index('      - identity: {}')
s=s[:a]+'      - identity: {}\n'+s[a:b]
open(p,'w').write(s)
P
echo "$(ts) providers 순서를 identity 먼저로 바꿈 → 설정은 시작할 때 읽으므로 API 서버 컨테이너를 멈춰 kubelet 이 다시 띄우게 함"
./lab ssh master -- sudo crictl stop $(./lab ssh master -- sudo crictl ps --name kube-apiserver -q) >/dev/null 2>&1; sleep 5; waitapi
$K get secrets -A -o json | $K replace -f - >/dev/null 2>&1; echo "$(ts) kubectl get secrets -A -o json | kubectl replace -f -  (전부 identity 로 다시 씀)"
LEFT=$($K "${E[@]}" get /registry/secrets --prefix -w json | python3 -c '
import json,sys,base64
kv=json.load(sys.stdin).get("kvs",[]); n=sum(base64.b64decode(k["value"]).startswith(b"k8s:enc:") for k in kv); print(n, "/", len(kv))')
echo "  /registry/secrets 전체 중 k8s:enc: 로 시작하는 값: $LEFT"
[ "${LEFT%% *}" = 0 ] || { echo "!! 아직 암호화된 Secret 이 남아 있어 설정을 지우지 않고 멈춤"; exit 1; }
./lab ssh master -- sudo sh -c 'cp /root/arch-exp-backup/kube-apiserver.yaml.pre-enc /etc/kubernetes/manifests/kube-apiserver.yaml && rm -rf /etc/kubernetes/enc /root/arch-exp-backup/kube-apiserver.yaml.pre-enc'
echo "$(ts) 매니페스트를 원래대로 복원, 키 파일 삭제"; sleep 5; waitapi
echo "  API 서버 플래그에 encryption: $($K -n kube-system get pod kube-apiserver-k8s-master -o jsonpath='{.spec.containers[0].command}' | grep -c encryption)개"
echo "  노드: $($K get nodes --no-headers | awk '{print $1"="$2}' | paste -sd' ' -)"
