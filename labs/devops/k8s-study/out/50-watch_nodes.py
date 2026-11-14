#!/usr/bin/env python3
# 실습 저장소의 shared/why/01-node-heartbeat-and-eviction-timeouts/watch_nodes.py 를 옮긴 것. 50-evict-30-vs-300.sh 와 50-three-workers-down.sh 가 실습 저장소에서 부르는 감시 스크립트다.
# 노드 Lease·Ready 조건·taint 와 지정한 네임스페이스 파드를 1초마다 보고, 바뀐 것만 "정지 후 +N초" 로 찍는다.
# 사용: watch_nodes.py <정지 시각 epoch> <최대 초> <네임스페이스> <노드1,노드2,...> [끝 조건: evict:<deploy접두어> | none]
import json, subprocess, sys, time, datetime
T0=float(sys.argv[1]); MAX=int(sys.argv[2]); NS=sys.argv[3]; NODES=sys.argv[4].split(','); END=sys.argv[5] if len(sys.argv)>5 else "none"
def k(*a):
    r=subprocess.run(["./lab","kubectl",*a,"-o","json"],capture_output=True,text=True)
    return json.loads(r.stdout) if r.returncode==0 and r.stdout.strip() else {"items":[]}
def rel(ts):
    if not ts: return "-"
    t=datetime.datetime.fromisoformat(ts.replace("Z","+00:00")).timestamp()
    return "%+.0fs" % (t-T0)
prev={}
def show(key,val,el):
    if prev.get(key)!=val:
        print("  +%5.1fs  %-34s %s" % (el,key,val), flush=True); prev[key]=val
start=time.time()
while True:
    el=time.time()-T0
    leases={l["metadata"]["name"]:l for l in k("-n","kube-node-lease","get","lease")["items"]}
    nodes={n["metadata"]["name"]:n for n in k("get","node")["items"]}
    for n in NODES:
        ls=leases.get(n,{}).get("spec",{}); show(n+" Lease renewTime", rel(ls.get("renewTime")), el)
        nd=nodes.get(n,{})
        rc=[c for c in nd.get("status",{}).get("conditions",[]) if c["type"]=="Ready"]
        if rc: show(n+" Ready", "%s (%s, 전이 %s)" % (rc[0]["status"], rc[0].get("reason",""), rel(rc[0].get("lastTransitionTime"))), el)
        tt=sorted("%s:%s(%s)" % (t["key"].split("/")[-1],t["effect"],rel(t.get("timeAdded"))) for t in nd.get("spec",{}).get("taints",[]) if "node.kubernetes.io" in t["key"])
        show(n+" taints", " ".join(tt) or "(없음)", el)
    pods=k("-n",NS,"get","pod")["items"]
    for p in pods:
        nm=p["metadata"]["name"]; dt=p["metadata"].get("deletionTimestamp")
        show("pod "+nm, "node=%s phase=%s 생성=%s 삭제표시=%s" % (p["spec"].get("nodeName","-"), p["status"].get("phase"), rel(p["metadata"]["creationTimestamp"]), rel(dt) if dt else "-"), el)
    if END.startswith("evict:"):
        pre=END[6:]
        if any(p["metadata"]["name"].startswith(pre) and p["metadata"].get("deletionTimestamp") for p in pods): print("  (끝 조건: %s* 파드에 삭제 표시)" % pre); break
    if time.time()-start>MAX: print("  (최대 %d초 도달)" % MAX); break
    time.sleep(max(0,1-(time.time()-T0-el)))
