#!/usr/bin/env bash
# YAML 리스트는 순서가 의미 있나: initContainers 실행 순서와 env 의 $(VAR) 참조 (Mac 에서 실행)
# 실습 저장소 루트에서 실행한다. 네임스페이스 blog-59 만 만들고 지운다.
K="./lab kubectl"; NS=blog-59
echo "# 59 리스트의 순서 ($(date '+%F %T %Z'))"
$K create ns $NS >/dev/null
cat <<'Y' | tee /dev/stderr | $K apply -n $NS -f - >/dev/null
apiVersion: v1
kind: Pod
metadata: {name: order-demo}
spec:
  volumes: [{name: work, emptyDir: {}}]
  initContainers:
  - name: init-a            # 먼저 적었고 2초 걸린다
    image: busybox:1.37
    command: ["sh", "-c", "sleep 2; echo init-a >> /work/order"]
    volumeMounts: [{name: work, mountPath: /work}]
  - name: init-b            # 나중에 적었고 바로 끝난다
    image: busybox:1.37
    command: ["sh", "-c", "echo init-b >> /work/order"]
    volumeMounts: [{name: work, mountPath: /work}]
  containers:
  - name: app
    image: busybox:1.37
    env:
    - {name: BEFORE, value: "hello-$(NAME)"}   # NAME 보다 앞에서 참조
    - {name: NAME,   value: "k8s"}
    - {name: AFTER,  value: "hello-$(NAME)"}   # NAME 보다 뒤에서 참조
    command: ["sh", "-c", "echo order: $(cat /work/order | tr '\\n' ' '); echo BEFORE=$BEFORE; echo AFTER=$AFTER; sleep 3600"]
    volumeMounts: [{name: work, mountPath: /work}]
Y
$K wait pod/order-demo -n $NS --for=condition=Ready --timeout=120s >/dev/null
echo; echo "## app 로그"
$K logs order-demo -n $NS -c app | sed 's/^/  /'
echo; echo "## initContainerStatuses (시작 · 끝)"
$K get pod order-demo -n $NS -o jsonpath='{range .status.initContainerStatuses[*]}  {.name}  started={.state.terminated.startedAt}  finished={.state.terminated.finishedAt}  exit={.state.terminated.exitCode}{"\n"}{end}'
echo; echo "## 저장된 env 는 보낸 문자열 그대로다 (치환은 kubelet 이 컨테이너를 만들 때)"
$K get pod order-demo -n $NS -o jsonpath='{range .spec.containers[0].env[*]}  {.name}={.value}{"\n"}{end}'
$K delete ns $NS --wait=false >/dev/null
