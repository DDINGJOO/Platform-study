#!/usr/bin/env bash
# 32편: 관문 1(인증)과 관문 2(인가). ServiceAccount 토큰 하나로 401 → 403 → 200 이 어디서 갈리는지 본다.
# w32 네임스페이스 안에서만 만들고 끝에 네임스페이스째 지운다. 클러스터 범위 리소스는 만들지 않는다.
# 실습 저장소 루트(./lab 이 있는 곳)에서 bash <이 스크립트> 로 실행
set -u
K="./lab kubectl"
echo "# 32편: ServiceAccount 토큰과 RBAC ($(date '+%F %T %Z'), Mac 에서 실습 저장소 루트로 bash 32-rbac-sa.sh 실행, w32 네임스페이스만 쓰고 지움)"

echo; echo "## 1. 준비: 네임스페이스 w32 와 ServiceAccount reader (권한은 아직 주지 않음)"
echo "mac\$ kubectl create namespace w32; kubectl -n w32 create serviceaccount reader"
$K create namespace w32
$K -n w32 create serviceaccount reader
TOKEN=$($K -n w32 create token reader --duration=10m)
# 서명 부분을 뒤집어 '모양은 맞지만 서명이 틀린' 토큰을 만든다
BADSIG=$(python3 -c 'import sys;h,p,s=sys.argv[1].split(".");print(h+"."+p+"."+s[::-1])' "$TOKEN")
echo "mac\$ TOKEN=\$(kubectl -n w32 create token reader --duration=10m)   # 토큰 원문은 출력하지 않음"

echo; echo "## 2. 토큰만 실어 보낸다 (worker1 에서, 클라이언트 인증서 없음)"
./lab ssh 1 -- env TOKEN="$TOKEN" BADSIG="$BADSIG" bash -s <<'R'
API=https://192.168.104.1:6443
CA=/etc/kubernetes/pki/ca.crt
echo "worker1\$ kubectl --kubeconfig=/dev/null --server=$API --certificate-authority=$CA --token=\$TOKEN auth whoami"
kubectl --kubeconfig=/dev/null --server=$API --certificate-authority=$CA --token="$TOKEN" auth whoami -o jsonpath='Username {.status.userInfo.username}{"\n"}Groups   {.status.userInfo.groups}{"\n"}'
show() { python3 -c 'import json,sys;d=json.load(sys.stdin);print(d.get("code"),d.get("reason"),"|",d.get("message")) if d.get("kind")=="Status" else print(200,d.get("kind"),"| items",len(d.get("items",[])))'; }
echo "worker1\$ curl --cacert $CA -H \"Authorization: Bearer \$TOKEN\" $API/api/v1/namespaces/w32/pods"
curl -s --cacert $CA -H "Authorization: Bearer $TOKEN" $API/api/v1/namespaces/w32/pods | show
echo "worker1\$ curl ... -H \"Authorization: Bearer \$BADSIG\" ...   # 같은 토큰에서 서명 부분만 뒤집은 것"
curl -s --cacert $CA -H "Authorization: Bearer $BADSIG" $API/api/v1/namespaces/w32/pods | show
R

echo; echo "## 3. 관리자가 reader 로 가장해서 묻기 (kubectl auth can-i --as)"
for q in "list pods -n w32" "get pods -n w32" "delete pods -n w32"; do
  echo "mac\$ kubectl auth can-i $q --as=system:serviceaccount:w32:reader → $($K auth can-i $q --as=system:serviceaccount:w32:reader 2>&1)"
done
echo "mac\$ kubectl auth can-i --list -n w32 --as=system:serviceaccount:w32:reader   (권한을 주기 전, 기본으로 받은 것)"
$K auth can-i --list -n w32 --as=system:serviceaccount:w32:reader

echo; echo "## 4. Role 과 RoleBinding 을 w32 안에만 만든다"
echo "mac\$ kubectl -n w32 create role pod-reader --verb=get,list,watch --resource=pods"
$K -n w32 create role pod-reader --verb=get,list,watch --resource=pods
echo "mac\$ kubectl -n w32 create rolebinding reader-can-read-pods --role=pod-reader --serviceaccount=w32:reader"
$K -n w32 create rolebinding reader-can-read-pods --role=pod-reader --serviceaccount=w32:reader
$K -n w32 get rolebinding reader-can-read-pods -o wide

echo; echo "## 5. 같은 질문을 다시"
for q in "list pods -n w32" "delete pods -n w32" "list secrets -n w32" "list pods -n default"; do
  echo "mac\$ kubectl auth can-i $q --as=system:serviceaccount:w32:reader → $($K auth can-i $q --as=system:serviceaccount:w32:reader 2>&1)"
done
./lab ssh 1 -- env TOKEN="$TOKEN" bash -s <<'R'
API=https://192.168.104.1:6443
CA=/etc/kubernetes/pki/ca.crt
show() { python3 -c 'import json,sys;d=json.load(sys.stdin);print(d.get("code"),d.get("reason"),"|",d.get("message")) if d.get("kind")=="Status" else print(200,d.get("kind"),"| items",len(d.get("items",[])))'; }
echo "worker1\$ curl --cacert $CA -H \"Authorization: Bearer \$TOKEN\" $API/api/v1/namespaces/w32/pods"
curl -s --cacert $CA -H "Authorization: Bearer $TOKEN" $API/api/v1/namespaces/w32/pods | show
echo "worker1\$ curl --cacert $CA -H \"Authorization: Bearer \$TOKEN\" $API/api/v1/namespaces/default/pods"
curl -s --cacert $CA -H "Authorization: Bearer $TOKEN" $API/api/v1/namespaces/default/pods | show
R

echo; echo "## 6. 정리"
echo "mac\$ kubectl delete namespace w32"
$K delete namespace w32 --wait=true
