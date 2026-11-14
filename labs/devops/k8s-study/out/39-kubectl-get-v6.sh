#!/usr/bin/env bash
# 39편을 쓰며 새로 만든 조회 전용 스크립트. 실습 저장소 루트(./lab 이 있는 곳)에서 실행한다 (Mac). 클러스터에 아무것도 쓰지 않는다.
# kubectl get 이 API 서버에 보내는 목록 요청에 resourceVersion 이 붙는지 본다 (-v=6 은 요청 URL 을 찍는다)
echo "# kubectl get 의 요청 URL ($(date '+%F %T %Z'), 조회만)"
./lab kubectl get pods -A -v=6 2>&1 >/dev/null | grep -o '"Response" verb="[A-Z]*" url="[^"]*" status="[^"]*"' | sed -E 's#https://[^/]+#https://<API서버>#'
