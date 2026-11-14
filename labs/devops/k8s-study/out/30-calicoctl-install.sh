#!/usr/bin/env bash
# 마스터에 calicoctl v3.33.0(클러스터의 Calico 와 같은 버전) 설치 (마스터 VM 안에서 sudo 로 실행)
set -euo pipefail
V=v3.33.0; A=$(uname -m); case $A in aarch64) A=arm64;; x86_64) A=amd64;; esac
URL=https://github.com/projectcalico/calico/releases/download/$V/calicoctl-linux-$A
echo "다운로드: $URL"
curl -fsSL -o /usr/local/bin/calicoctl "$URL"
chmod +x /usr/local/bin/calicoctl
ls -l /usr/local/bin/calicoctl | awk '{print $1, $5, $NF}'
