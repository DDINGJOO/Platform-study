#!/usr/bin/env bash
# 실습 저장소의 shared/components/15-etcd-watch-registry.sh 를 옮긴 것. 실습 저장소 루트에서 실행한다.
# etcd 동작: nginx 파드 하나가 /registry/pods/default/nginx 키로 몇 번 쓰이나(etcd 를 직접 watch), 컨트롤 플레인 중 상태(데이터 볼륨)를 가진 건 누구인가 (Mac 에서 실행)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"
E=(-n kube-system exec etcd-k8s-master -- etcdctl --endpoints=https://127.0.0.1:2379 --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt --key=/etc/kubernetes/pki/etcd/server.key)
echo "# etcd 동작 ($(date '+%F %T %Z'))"
echo; echo "## 1. etcd 를 직접 watch 하면서 nginx 파드 생성 → Running → 삭제"
( timeout 25 $K "${E[@]}" watch /registry/pods/default/nginx -w json 2>/dev/null | python3 -c '
import sys,json
for line in sys.stdin:
    try: d=json.loads(line)
    except: continue
    for ev in d.get("Events",[]):
        kv=ev["kv"]; t=ev.get("type","PUT") if isinstance(ev.get("type"),str) else ("DELETE" if ev.get("type")==1 else "PUT")
        import base64
        key=base64.b64decode(kv["key"]).decode()
        print("   etcd watch:", t, key, "mod_revision=%s version=%s" % (kv.get("mod_revision"), kv.get("version","-")))' ) &
sleep 2
$K run nginx --image=nginx:1.25.1-alpine --restart=Never >/dev/null; echo "  \$ kubectl run nginx --image=nginx:1.25.1-alpine"
$K wait --for=condition=Ready pod/nginx --timeout=60s >/dev/null; echo "  Ready: $($K get pod nginx -o jsonpath='{.spec.nodeName} {.status.podIP} rv={.metadata.resourceVersion}')"
echo "  \$ etcdctl get /registry/pods/default/nginx --keys-only → $($K "${E[@]}" get /registry/pods/default/nginx --keys-only | head -1)"
sleep 2; $K delete pod nginx >/dev/null; echo "  \$ kubectl delete pod nginx"
wait
echo; echo "## 2. 컨트롤 플레인 중 데이터를 디스크에 두는 건 누구인가 (정적 파드 매니페스트의 hostPath 볼륨)"
./lab ssh master -- sudo python3 - <<'P'
import yaml,glob,os
for f in sorted(glob.glob('/etc/kubernetes/manifests/*.yaml')):
    d=yaml.safe_load(open(f)); c=d['spec']['containers'][0]
    mounts={m['name']:(m['mountPath'],m.get('readOnly',False)) for m in c.get('volumeMounts',[])}
    rw=[f"{v[0]}" for k,v in mounts.items() if not v[1]]
    print(f"  {os.path.basename(f):30s} 쓰기 가능한 마운트: {rw or '없음'}")
P
