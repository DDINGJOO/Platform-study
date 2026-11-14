#!/usr/bin/env bash
# 36편: 매니페스트의 front-proxy 플래그(--requestheader-*, --proxy-client-*)가 지금 쓰이고 있는지 본다.
# 이 플래그들은 확장 API 서버(API 애그리게이션)와 어드미션 웹훅을 부를 때 쓰인다. 조회만 한다.
# 실습 저장소 루트(./lab 이 있는 곳)에서 bash <이 스크립트> 로 실행
set -u
K="./lab kubectl"
echo "# front-proxy 플래그를 쓰는 곳이 있나 ($(date '+%F %T %Z'))"
echo; echo "## 1. APIService: SERVICE 가 Local 이면 API 서버 자신이 처리, 서비스 이름이면 확장 API 서버로 넘김"
$K get apiservices --no-headers | awk '{print $2}' | sort | uniq -c | sed 's/^/  /'
echo; echo "## 2. 어드미션 웹훅 설정 수"
echo "  mutating: $($K get mutatingwebhookconfigurations --no-headers 2>/dev/null | wc -l | tr -d ' ')  validating: $($K get validatingwebhookconfigurations --no-headers 2>/dev/null | wc -l | tr -d ' ')"
echo; echo "## 3. API 서버가 확장 API 서버에게 공개하는 인증 정보 (kube-system/extension-apiserver-authentication 의 키 이름만)"
$K -n kube-system get cm extension-apiserver-authentication -o json | python3 -c '
import json,sys
d=json.load(sys.stdin)["data"]
for k in sorted(d): print("  %-40s %s" % (k, "(PEM 인증서 %d개)" % d[k].count("BEGIN CERTIFICATE") if "BEGIN" in d[k] else d[k]))'
