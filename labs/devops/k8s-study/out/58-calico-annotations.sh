#!/usr/bin/env bash
# managedFields 의 calico 작성자가 파드에 쓰는 칸은 무엇인가: coredns 파드의 annotations 키 (Mac 에서 실행)
# 실습 저장소 루트에서 실행한다. 조회만 한다. 값(IP·컨테이너 ID)은 출력하지 않고 키만 본다.
K="./lab kubectl"
echo "# 58 calico 작성자가 쓰는 칸 ($(date '+%F %T %Z'))"
$K get pod -n kube-system -l k8s-app=kube-dns -o json --show-managed-fields | python3 -c '
import json,sys
p=json.load(sys.stdin)["items"][0]
print("  파드:", p["metadata"]["name"])
for m in p["metadata"]["managedFields"]:
    if m["manager"]=="calico":
        keys=[k[2:] for k in m["fieldsV1"]["f:metadata"]["f:annotations"] if k.startswith("f:")]
        print("  manager=calico operation=%s subresource=%s annotations=%s" % (m["operation"], m.get("subresource","-"), ", ".join(keys)))
'
