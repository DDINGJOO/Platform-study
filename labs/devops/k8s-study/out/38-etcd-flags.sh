#!/usr/bin/env bash
# 38편을 쓰며 새로 만든 조회 전용 스크립트. 실습 저장소 루트(./lab 이 있는 곳)에서 실행한다 (Mac). 클러스터에 아무것도 쓰지 않는다.
# etcd 매니페스트의 플래그 전체와, 그 가운데 자동 컴팩션(--auto-compaction-*)·watch 진행 알림 관련 플래그가 있는지 본다
M=/etc/kubernetes/manifests/etcd.yaml
echo "# etcd 매니페스트의 플래그 ($(date '+%F %T %Z'), master $M, 조회만)"
./lab ssh master -- sudo grep -n -E -- '- --' $M
echo "  --auto-compaction 으로 시작하는 플래그 수: $(./lab ssh master -- sudo grep -c -- '--auto-compaction' $M)"
echo "  --watch-progress-notify-interval: $(./lab ssh master -- sudo grep -o -- '--watch-progress-notify-interval=[^ ]*' $M)"
