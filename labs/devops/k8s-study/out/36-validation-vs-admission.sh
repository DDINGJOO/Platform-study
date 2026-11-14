#!/usr/bin/env bash
# 실습 저장소의 shared/components/08-validation-vs-admission.sh 를 옮긴 것. 실습 저장소 루트에서 실행한다.
# "데이터 유효성 검사"는 두 겹: 스키마 검증(형식이 틀리면 422 Invalid) 과 어드미션(규칙에 안 맞으면 403 Forbidden, 또는 요청을 고침) (Mac 에서 실행)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"
echo "# 유효성 검사와 어드미션 ($(date '+%F %T %Z'))"
$K create ns adm-demo >/dev/null
echo; echo "## 1. 형식이 틀린 파드 (컨테이너 이름에 대문자·밑줄) → API 서버의 스키마 검증"
cat <<Y | $K -n adm-demo apply -f - 2>&1 | sed 's/^/  /'
apiVersion: v1
kind: Pod
metadata: {name: bad-name}
spec: {containers: [{name: Bad_Name, image: registry.k8s.io/pause:3.10.2}]}
Y
echo; echo "## 2. 형식은 맞지만 규칙(ResourceQuota: 파드 1개)에 걸리는 파드 → validating 어드미션"
$K -n adm-demo create quota one-pod --hard=pods=1 >/dev/null
$K -n adm-demo run p1 --image=registry.k8s.io/pause:3.10.2 >/dev/null && echo "  p1 생성 OK"
$K -n adm-demo run p2 --image=registry.k8s.io/pause:3.10.2 2>&1 | sed 's/^/  /'
echo; echo "## 3. 통과한 요청은 저장 전에 고쳐짐 → mutating 어드미션 (--dry-run=server 로 결과만 봄)"
$K -n adm-demo delete quota one-pod >/dev/null
$K -n adm-demo run p3 --image=registry.k8s.io/pause:3.10.2 --dry-run=server -o json | python3 -c '
import json,sys
p=json.load(sys.stdin)["spec"]
print("  serviceAccountName =", p.get("serviceAccountName"), " ← ServiceAccount 플러그인")
print("  volumes =", [v["name"] for v in p.get("volumes",[])], " ← ServiceAccount 플러그인(토큰 볼륨)")
print("  tolerations =", [(t["key"].split("/")[-1], t.get("tolerationSeconds")) for t in p.get("tolerations",[])], " ← DefaultTolerationSeconds")
print("  priority =", p.get("priority"), " ← Priority")'
$K delete ns adm-demo --wait=false >/dev/null; echo; echo "(adm-demo 네임스페이스 삭제)"
