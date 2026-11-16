#!/usr/bin/env bash
# minReadySeconds·progressDeadlineSeconds·httpGet.host 를 API 서버는 어떻게 설명하나: kubectl explain (Mac 에서 실행)
# 실습 저장소 루트에서 실행한다(./lab kubectl). 조회만 한다.
K="./lab kubectl"
echo "# 62 Deployment·프로브 필드 설명 ($(date '+%F %T %Z'))"
for f in deployment.spec.minReadySeconds deployment.spec.progressDeadlineSeconds pod.spec.containers.readinessProbe.httpGet.host; do
  echo; echo "## kubectl explain $f"
  $K explain $f | sed -n '/DESCRIPTION/,$p' | sed 's/^/  /'
done
