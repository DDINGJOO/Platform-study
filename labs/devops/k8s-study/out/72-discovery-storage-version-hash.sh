#!/usr/bin/env bash
# 확인: discovery 문서의 preferredVersion·storageVersionHash로 "여러 버전으로 서빙되지만 저장은 한 버전"을 읽는다. 조회만 한다 (Mac 에서 실행)
# 실행: bash shared/why/08-api-versions-deprecation/01-discovery-storage-version-hash.sh | tee shared/why/08-api-versions-deprecation/01-discovery-storage-version-hash.txt
set -u
cd /Users/dding/orca/workspaces/k8s/tang
K="./lab kubectl"
hash(){ python3 -c 'import hashlib,base64,sys; print(base64.b64encode(hashlib.sha256(sys.argv[1].encode()).digest()[:8]).decode())' "$1"; }
svh(){ $K get --raw "$1" | python3 -c 'import json,sys; n=sys.argv[1]; print(next((r.get("storageVersionHash","") for r in json.load(sys.stdin)["resources"] if r["name"]==n),"(없음)"))' "$2"; }

echo "# 01 discovery의 preferredVersion과 storageVersionHash ($(date '+%F %T %Z'))"

echo; echo "## 1. API 서버 버전과 emulation / min-compatibility 버전 (/version)"
$K get --raw /version | python3 -c 'import json,sys; v=json.load(sys.stdin); print("  gitVersion", v["gitVersion"], "| emulation", v["emulationMajor"]+"."+v["emulationMinor"], "| minCompatibility", v["minCompatibilityMajor"]+"."+v["minCompatibilityMinor"])'

echo; echo "## 2. autoscaling 그룹: 두 버전을 서빙하고 그중 하나가 preferredVersion (/apis/autoscaling)"
$K get --raw /apis/autoscaling | python3 -c 'import json,sys; g=json.load(sys.stdin); print("  versions:", [v["groupVersion"] for v in g["versions"]]); print("  preferredVersion:", g["preferredVersion"]["groupVersion"])'

echo; echo "## 3. 같은 리소스를 다른 버전·다른 그룹 경로로 물어도 storageVersionHash는 같다"
echo "   (해시 = base64(sha256(\"<group>/<version>/<Kind>\")[:8]), v1.37.2 storageversionhash.go)"
printf '  %-60s %s\n' "discovery 경로 / 리소스" "storageVersionHash"
for row in "/apis/autoscaling/v1 horizontalpodautoscalers" "/apis/autoscaling/v2 horizontalpodautoscalers" \
           "/api/v1 events" "/apis/events.k8s.io/v1 events"; do
  set -- $row; printf '  %-60s %s\n' "$1  $2" "$(svh $1 $2)"
done
echo "  직접 계산:"
for g in "autoscaling/v1/HorizontalPodAutoscaler" "autoscaling/v2/HorizontalPodAutoscaler" "/v1/Event" "events.k8s.io/v1/Event"; do
  printf '    %-58s %s\n' "$g" "$(hash $g)"
done
echo "  → HPA는 v1으로 물어도 v2로 물어도 autoscaling/v2로 저장. events.k8s.io/v1 Event는 core v1 Event와 같은 저장소(/registry/events)를 쓴다."

echo; echo "## 4. '서빙하지 않는 beta 버전'으로 저장되는 리소스: 1.37에 GA 된 것(Rule #4b) + CRD 객체 자체(1.22에 v1beta1 서빙 중단)"
printf '  %-50s %-14s %-14s %s\n' "리소스" "discovery" "v1 해시" "v1beta1 해시"
for row in "/apis/storagemigration.k8s.io/v1 storageversionmigrations storagemigration.k8s.io StorageVersionMigration" \
           "/apis/certificates.k8s.io/v1 podcertificaterequests certificates.k8s.io PodCertificateRequest" \
           "/apis/certificates.k8s.io/v1 clustertrustbundles certificates.k8s.io ClusterTrustBundle" \
           "/apis/apiextensions.k8s.io/v1 customresourcedefinitions apiextensions.k8s.io CustomResourceDefinition"; do
  set -- $row
  printf '  %-50s %-14s %-14s %s\n' "$3/$2" "$(svh $1 $2)" "$(hash $3/v1/$4)" "$(hash $3/v1beta1/$4)"
done
echo "  그 beta 버전 경로는 서빙되지 않는다:"
for p in /apis/storagemigration.k8s.io/v1beta1 /apis/certificates.k8s.io/v1beta1 /apis/apiextensions.k8s.io/v1beta1 /apis/scheduling.k8s.io/v1beta1; do
  printf '    GET %-42s → %s\n' "$p" "$($K get --raw $p 2>&1 | head -1 | sed 's/^Error from server //')"
done

echo; echo "## 5. 저장 버전·마이그레이션 관련 feature gate (kube-apiserver /metrics의 kubernetes_feature_enabled)"
$K get --raw /metrics | grep -E '^kubernetes_feature_enabled\{name="(StorageVersionAPI|StorageVersionHash|StorageVersionMigrator|APIServerIdentity)"' | sed 's/^/  /'
echo "  storagemigration.k8s.io 리소스:"; $K api-resources --api-group=storagemigration.k8s.io | sed 's/^/    /'
