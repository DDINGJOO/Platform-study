#!/usr/bin/env bash
# 명령형으로 YAML 뼈대를 뽑는 법(--dry-run=client -o yaml)과 kubectl create 로 만들 수 없는 종류 (Mac 에서 실행)
# 실습 저장소 루트에서 실행한다. 네임스페이스 blog-59 만 만들고 지운다.
K="./lab kubectl"; NS=blog-59
echo "# 59 명령형으로 뼈대 뽑기 ($(date '+%F %T %Z'), kubectl $($K version --client -o json | grep -m1 gitVersion | tr -d ' ",' | cut -d: -f2))"
$K create ns $NS >/dev/null

echo; echo "## 1. kubectl create deployment web --image=nginx:1.27-alpine --replicas=2 --dry-run=client -o yaml"
$K create deployment web -n $NS --image=nginx:1.27-alpine --replicas=2 --dry-run=client -o yaml | sed 's/^/  /'

echo; echo "## 2. kubectl run tmp --image=busybox:1.37 --restart=Never --dry-run=client -o yaml -- sleep 3600"
$K run tmp -n $NS --image=busybox:1.37 --restart=Never --dry-run=client -o yaml -- sleep 3600 | sed 's/^/  /'

$K create deployment web -n $NS --image=nginx:1.27-alpine --replicas=2 >/dev/null
echo; echo "## 3. kubectl autoscale: --cpu-percent 와 --cpu (둘 다 --dry-run=client)"
echo "  --cpu-percent=50:"; $K autoscale deploy web -n $NS --cpu-percent=50 --min=1 --max=3 --dry-run=client -o yaml 2>&1 | grep -E 'deprecated|apiVersion: autoscaling|averageUtilization' | sed 's/^/    /'
echo "  --cpu=50%:";        $K autoscale deploy web -n $NS --cpu=50% --min=1 --max=3 --dry-run=client -o yaml 2>&1 | grep -E 'deprecated|apiVersion: autoscaling|averageUtilization' | sed 's/^/    /'

echo; echo "## 4. kubectl create 의 하위 명령 (여기 없는 종류는 명령형으로 만들 수 없다)"
$K create --help | sed -n '/^Available Commands:/,/^$/p' | awk 'NR>1 && NF {print $1}' | paste -sd' ' - | fold -s -w 110 | sed 's/^/  /'
echo; echo "## 5. 명령이 없는 종류의 예: 위 목록에 있나"
for k in daemonset statefulset persistentvolumeclaim networkpolicy; do
  printf '  %-22s %s\n' "$k" "$($K create --help | sed -n '/^Available Commands:/,/^$/p' | awk '{print $1}' | grep -qx "$k" && echo 있음 || echo 없음)"
done
$K delete ns $NS --wait=false >/dev/null
