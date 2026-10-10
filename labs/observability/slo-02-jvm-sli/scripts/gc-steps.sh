#!/usr/bin/env bash
# payments 에 GC 압박을 세 단계로 넣고 되돌린다. 단계마다 2~3분씩 둔다.
# 사용: bash scripts/gc-steps.sh   (PAYMENTS_URL 기본 http://localhost:24181)
set -euo pipefail
U=${PAYMENTS_URL:-http://localhost:24181}
step() { echo "$(date -u +%T) $1"; curl -s -X POST "$U/chaos?$2"; echo; }
step "1) 버려지는 객체만 초당 300MB"            "allocMbPerSec=300";              sleep 120
step "2) 붙잡아 두는 데이터 90MB 추가"           "retainMb=90";                    sleep 120
step "3) 붙잡는 데이터 118MB, 할당 초당 600MB"    "retainMb=118&allocMbPerSec=600"; sleep 180
step "4) 되돌림"                                "retainMb=0&allocMbPerSec=0"
