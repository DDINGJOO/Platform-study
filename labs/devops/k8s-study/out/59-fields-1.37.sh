#!/usr/bin/env bash
# 1.37.2 API 에 파드 생명주기 관련 필드가 있는가 (Mac 에서 실행)
cd "$(dirname "$0")/../.."
K="./lab kubectl"
echo "# 00 파드 생명주기 관련 필드 확인 ($(date '+%F %T %Z')), 서버 $($K version -o json | grep -m1 gitVersion | tr -d ' ",' | cut -d: -f2)"
for f in pod.spec.initContainers.restartPolicy \
         pod.spec.containers.restartPolicyRules \
         pod.spec.containers.lifecycle.preStop.sleep \
         pod.spec.containers.lifecycle.stopSignal \
         pod.spec.containers.startupProbe \
         pod.spec.terminationGracePeriodSeconds \
         pod.status.observedGeneration; do
  if out=$($K explain $f 2>&1); then
    echo; echo "## $f : 있음"; echo "$out" | sed -n '/^DESCRIPTION:/,/^$/p' | sed -n '2,4p' | sed 's/^/  /'
  else
    echo; echo "## $f : 없음 ($(echo "$out" | head -1))"
  fi
done
