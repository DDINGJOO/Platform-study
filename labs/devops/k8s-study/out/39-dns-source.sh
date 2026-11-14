#!/usr/bin/env bash
# 실습 저장소의 shared/components/14-dns-source.sh 를 옮긴 것. 실습 저장소 루트에서 실행한다.
# DNS 기록은 어디서 오나: Service 를 만들면 etcd 키 → API 서버 → CoreDNS(kubernetes 플러그인, watch) → 이름 풀이 (Mac 에서 실행)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"; ts(){ date '+%T.%3N' 2>/dev/null || date '+%T'; }
E=(-n kube-system exec etcd-k8s-master -- etcdctl --endpoints=https://127.0.0.1:2379 --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt --key=/etc/kubernetes/pki/etcd/server.key)
echo "# DNS 기록의 출처 ($(date '+%F %T %Z'))"
echo; echo "## 1. CoreDNS 설정: kubernetes 플러그인 (etcd 플러그인 없음)"
$K -n kube-system get cm coredns -o jsonpath='{.data.Corefile}' | grep -nE 'kubernetes|etcd|forward|cache' | sed 's/^/  /'
$K -n kube-system get cm coredns -o jsonpath='{.data.Corefile}' | grep -nE 'disable|ttl' | sed 's/^/  /'
echo "  CoreDNS 가 붙는 곳(11-apiserver-clients.txt): 10.96.0.1:443(=API 서버). 2379(etcd)에 붙는 건 kube-apiserver 뿐(09-etcd-clients.txt)"
echo; echo "## 2. Service 하나를 만들고 etcd 키와 DNS 응답을 같이 봄"
$K run dns-probe --image=busybox:1.36.1 --restart=Never -- sleep 300 >/dev/null; $K wait --for=condition=Ready pod/dns-probe --timeout=90s >/dev/null
q(){ $K exec dns-probe -- nslookup dns-src-demo.default.svc.cluster.local 2>&1 | awk '/^Name:/{f=1} f&&/^Address/{print $2; exit} /NXDOMAIN/{print "NXDOMAIN"; exit}'; }
echo "$(date +%T) 만들기 전: etcd 키 $($K "${E[@]}" get /registry/services/specs/default/dns-src-demo --keys-only | grep -c dns-src-demo)개 | DNS → $(q)"
$K create service clusterip dns-src-demo --tcp=80:80 >/dev/null; echo "$(date +%T) kubectl create service clusterip dns-src-demo  (ClusterIP $($K get svc dns-src-demo -o jsonpath='{.spec.clusterIP}'))"
for i in 1 2 3; do echo "$(date +%T) etcd 키 $($K "${E[@]}" get /registry/services/specs/default/dns-src-demo --keys-only | grep -c dns-src-demo)개 | DNS → $(q)"; sleep 1; done
$K delete svc dns-src-demo >/dev/null; echo "$(date +%T) kubectl delete svc dns-src-demo"
for i in 1 2 3; do echo "$(date +%T) etcd 키 $($K "${E[@]}" get /registry/services/specs/default/dns-src-demo --keys-only | grep -c dns-src-demo)개 | DNS → $(q)"; sleep 1; done
$K delete pod dns-probe --now >/dev/null
