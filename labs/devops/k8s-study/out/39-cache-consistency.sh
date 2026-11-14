#!/usr/bin/env bash
# 실습 저장소의 shared/components/13-cache-consistency.sh 를 옮긴 것. 실습 저장소 루트에서 실행한다.
# 캐시가 오래된 값을 가질 때 쿠버네티스가 버티는 장치: API 서버 watch cache, 오래된 resourceVersion 으로 watch → 410, 오래된 버전으로 쓰기 → 409 (Mac 에서 실행)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"
echo "# 캐시와 일관성 ($(date '+%F %T %Z'))"
echo; echo "## 1. API 서버 안의 watch cache (etcd 를 watch 해서 메모리에 들고 있는 사본)"
$K get --raw /metrics | grep -E '^apiserver_watch_cache_resource_version\{.*resource="(pods|deployments\.apps|services|nodes|leases\.coordination\.k8s\.io)"' | sed -E 's/apiserver_watch_cache_resource_version//' | sed 's/^/  /'
echo "  etcd 의 현재 revision: $($K -n kube-system exec etcd-k8s-master -- etcdctl --endpoints=https://127.0.0.1:2379 --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt --key=/etc/kubernetes/pki/etcd/server.key endpoint status -w json | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["Status"]["header"]["revision"])')"
echo "  관련 기능 게이트(kubernetes_feature_enabled):"
$K get --raw /metrics | grep -E '^kubernetes_feature_enabled\{name="(ConsistentListFromCache|WatchList|ListFromCacheSnapshot)"' | sed 's/^/    /'
echo; echo "## 2. 너무 오래된 resourceVersion 부터 watch 하겠다고 하면 (22편 때 rv 103241, 이미 compaction 됨)"
timeout 5 $K get --raw '/api/v1/namespaces/default/pods?watch=true&resourceVersion=103241' 2>&1 | head -c 400 | sed 's/^/  /'; echo
echo; echo "## 3. 오래된 사본으로 고치려 하면 (낙관적 잠금 → 409)"
$K get deploy myweb -o json > /tmp/old.json
$K annotate deploy myweb demo/touch="$(date +%s)" --overwrite >/dev/null
python3 - <<'P'
import json; d=json.load(open('/tmp/old.json')); d['metadata'].setdefault('annotations',{})['demo/stale']='yes'; json.dump(d,open('/tmp/old.json','w'))
P
echo "  먼저 읽어 둔 사본의 resourceVersion: $(python3 -c 'import json;print(json.load(open("/tmp/old.json"))["metadata"]["resourceVersion"])'), 지금: $($K get deploy myweb -o jsonpath='{.metadata.resourceVersion}')"
$K replace -f /tmp/old.json 2>&1 | sed 's/^/  /'
$K annotate deploy myweb demo/touch- >/dev/null; rm -f /tmp/old.json
