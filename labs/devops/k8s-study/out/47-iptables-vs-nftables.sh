#!/usr/bin/env bash
# 실습 저장소의 shared/why/05-kube-proxy-modes/02-iptables-vs-nftables.sh 를 옮긴 것. 실습 저장소 루트에서 실행한다.
# kube-proxy iptables 모드와 nftables 모드: Service 1000개에서 규칙 크기·전체 동기화·엔드포인트 변경 반영 시간, 모드를 바꿨다 되돌리기 (Mac 에서 실행)
# kube-proxy ConfigMap 의 mode 를 nftables 로 바꿨다가 iptables 로 되돌린다(중간에 끊겨도 trap 이 되돌림). 네임스페이스 w5-proxy 만 쓰고 지운다.
cd "$(dirname "$0")/../../.."   # 실습 저장소 루트
K="./lab kubectl"; ts(){ date '+%T'; }; NS=w5-proxy; NSVC=1000
now(){ python3 -c 'import time;print("%.1f"%time.time())'; }
setmode(){ $K -n kube-system get cm kube-proxy -o yaml | sed -E "s/^(    mode: ).*/\1$1/" | $K replace -f - >/dev/null
  $K -n kube-system rollout restart ds kube-proxy >/dev/null; $K -n kube-system rollout status ds kube-proxy --timeout=180s >/dev/null; }
curmode(){ $K -n kube-system get cm kube-proxy -o jsonpath='{.data.config\.conf}' | awk '/^mode:/{print $2}'; }
trap '[ "$(curmode)" != iptables ] && { echo "  (trap) mode 를 iptables 로 되돌림"; setmode iptables; }' EXIT
km(){ ./lab ssh worker1 -- sudo bash -s <<'R'
curl -s 127.0.0.1:10249/metrics | grep 'ip_family="IPv4"' | grep -E '^kubeproxy_(sync_(full_|partial_)?proxy_rules_duration_seconds_(sum|count)|network_programming_duration_seconds_(sum|count))' | sed 's/{ip_family="IPv4"}//'
R
}
kd(){ python3 - "$1" "$2" <<'P'
import sys
def ld(s): return {l.split()[0]:float(l.split()[1]) for l in s.strip().splitlines() if l.strip()}
a,b=ld(sys.argv[1]),ld(sys.argv[2])
for k,lab in [("kubeproxy_sync_full_proxy_rules_duration_seconds","전체 동기화"),("kubeproxy_sync_partial_proxy_rules_duration_seconds","부분 동기화"),("kubeproxy_sync_proxy_rules_duration_seconds","동기화 전체"),("kubeproxy_network_programming_duration_seconds","변경→규칙 반영(network programming)")]:
    c=b.get(k+"_count",0)-a.get(k+"_count",0); s=b.get(k+"_sum",0)-a.get(k+"_sum",0)
    print("    %-38s %3d번, 평균 %s" % (lab, c, ("%.1fms" % (s/c*1000)) if c else "-"))
P
}
rules(){ ./lab ssh worker1 -- sudo bash -s <<'R'
echo "    iptables nat 줄 수 $(iptables-save -t nat 2>/dev/null | wc -l), KUBE-SVC 체인 $(iptables-save -t nat 2>/dev/null | grep -c '^:KUBE-SVC-'), KUBE-SEP 체인 $(iptables-save -t nat 2>/dev/null | grep -c '^:KUBE-SEP-')"
if nft list table ip kube-proxy >/dev/null 2>&1; then
  echo "    nft table ip kube-proxy: $(nft list table ip kube-proxy | wc -l)줄, 맵 $(nft list table ip kube-proxy | grep -cE '^\s+map ')개, service-ips 원소 $(nft list map ip kube-proxy service-ips 2>/dev/null | grep -o ' : goto ' | wc -l)개"
else echo "    nft table ip kube-proxy: 없음"; fi
R
}
probe(){ ip=$($K -n $NS get svc svc-0001 -o jsonpath='{.spec.clusterIP}')
  echo "    master\$ curl http://$ip (svc-0001) 20번 → $(./lab ssh master -- bash -s <<R | sort | uniq -c | tr -s ' ' | tr '\n' ' '
for i in \$(seq 1 20); do curl -s -m 2 -o /dev/null -w '%{http_code}\n' http://$ip; done
R
)"; }
slices(){ # 엔드포인트가 $1 개인 EndpointSlice 가 NSVC 개가 될 때까지 기다리고 걸린 시간
  local t0=$(now); until [ "$($K -n $NS get endpointslices -o json | python3 -c "import json,sys;print(sum(1 for s in json.load(sys.stdin)['items'] if len([e for e in (s.get('endpoints') or []) if e.get('conditions',{}).get('ready')])==$1))")" -ge $NSVC ]; do sleep 2; done
  echo "    EndpointSlice ${NSVC}개가 모두 엔드포인트 $1개로 바뀌기까지 $(python3 -c "print(int($(now)-$t0))")초 (컨트롤러 매니저 쪽)"; }
syncstate(){ ./lab ssh worker1 -- sudo bash -s <<'R'
crictl logs $(crictl ps --name kube-proxy -q | head -1) 2>&1 | grep -i -E 'Using .*Proxier|proxier' | head -3 | cut -c1-170 | sed 's/^/    /'
R
}
echo "# kube-proxy iptables vs nftables, Service ${NSVC}개 ($(date '+%F %T %Z'), 측정 노드 worker1)"
echo; echo "## 0. 시작: mode=$(curmode)"; rules
$K create ns $NS >/dev/null
$K -n $NS create deployment bulk --image=nginx:1.25.1-alpine --replicas=2 >/dev/null
$K -n $NS rollout status deploy/bulk --timeout=120s >/dev/null
F=$(mktemp); python3 - $NSVC > $F <<'P'
import sys
for i in range(1,int(sys.argv[1])+1):
    print("---\napiVersion: v1\nkind: Service\nmetadata: {name: svc-%04d}\nspec: {selector: {app: bulk}, ports: [{port: 80}]}" % i)
P
T0=$(now); $K -n $NS create -f $F >/dev/null; rm -f $F
echo; echo "## 1. iptables 모드, Service ${NSVC}개 생성 ($(python3 -c "print(int($(now)-$T0))")초, 각각 nginx 파드 2개를 가리킴)"
slices 2; sleep 20
rules; probe

echo; echo "## 2. iptables 모드 kube-proxy 재시작 → 처음 한 번의 전체 동기화"
T0=$(now); setmode iptables; echo "  $(ts) 재시작 끝 ($(python3 -c "print(int($(now)-$T0))")초)"; sleep 20
M0=$(echo "kubeproxy_sync_full_proxy_rules_duration_seconds_sum 0"); M1=$(km); kd "$M0" "$M1" | head -1; syncstate

echo; echo "## 3. iptables 모드에서 엔드포인트 변경: bulk 2→3 (Service ${NSVC}개 모두의 엔드포인트가 바뀜)"
A=$(km); $K -n $NS scale deploy bulk --replicas=3 >/dev/null; $K -n $NS rollout status deploy/bulk --timeout=120s >/dev/null; slices 3; sleep 10; B=$(km); kd "$A" "$B"; rules; probe

echo; echo "## 4. nftables 모드로 전환"
T0=$(now); setmode nftables; echo "  $(ts) mode=$(curmode), 재시작 끝 ($(python3 -c "print(int($(now)-$T0))")초)"; sleep 20
M1=$(km); kd "$M0" "$M1" | head -1; syncstate; rules; probe

echo; echo "## 5. nftables 모드에서 엔드포인트 변경: bulk 3→2"
A=$(km); $K -n $NS scale deploy bulk --replicas=2 >/dev/null; slices 2; sleep 10; B=$(km); kd "$A" "$B"; rules; probe

echo; echo "## 6. iptables 모드로 되돌림"
T0=$(now); setmode iptables; echo "  $(ts) mode=$(curmode), 재시작 끝 ($(python3 -c "print(int($(now)-$T0))")초)"; sleep 20
syncstate; rules; probe

echo; echo "## 7. 정리"
T0=$(now); $K delete ns $NS --wait=true >/dev/null; echo "  $(ts) 네임스페이스 $NS 삭제 ($(python3 -c "print(int($(now)-$T0))")초)"; sleep 10; rules
echo "  calico-node: $($K -n kube-system get ds calico-node -o jsonpath='{.status.numberReady}/{.status.desiredNumberScheduled} ready'), kube-proxy: $($K -n kube-system get ds kube-proxy -o jsonpath='{.status.numberReady}/{.status.desiredNumberScheduled} ready'), mode=$(curmode)"
