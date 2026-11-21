#!/usr/bin/env bash
# CrashLoopBackOff 중인 파드의 STATUS 열·phase·Ready·컨테이너 상태를 watch 로 바뀔 때마다 기록하고, restartPolicy 별 phase(Always·OnFailure·Never), 스케줄할 수 없는 파드의 PodScheduled 시각 필드, 노드 kubelet 의 백오프 설정을 함께 확인 (Mac 에서 실행)
# 실습 저장소 루트에서 실행한다(./lab kubectl). 네임스페이스 blog-81 만 쓰고 지운다. 노드 설정은 읽기만 한다.
K="./lab kubectl"; NS=blog-81; N=k8s-worker3; DUR=150
now(){ perl -MTime::HiRes=time -e 'printf "%.1f", time'; }
TMP=$(mktemp -d)
echo "# 81 CrashLoopBackOff 를 watch 로 보기 ($(date '+%F %T %Z')), 노드 $N"
$K create ns $NS >/dev/null

echo; echo "## A. 노드 kubelet 의 백오프 관련 설정과 기능 게이트 (configz, metrics 를 읽기만 함)"
$K get --raw /api/v1/nodes/$N/proxy/configz | python3 -c 'import json,sys; c=json.load(sys.stdin)["kubeletconfig"]; print("  syncFrequency=%s crashLoopBackOff=%s featureGates=%s" % (c.get("syncFrequency"), c.get("crashLoopBackOff"), c.get("featureGates")))'
$K get --raw /api/v1/nodes/$N/proxy/metrics | grep -E 'kubernetes_feature_enabled\{name="(KubeletCrashLoopBackOffMax|ReduceDefaultCrashLoopBackOffDecay|EventedPLEG|ContainerRestartRules)"' | sed 's/^/  /'

T0=$(now)
stamp(){ while IFS= read -r l; do printf '  +%5.1fs %s %s\n' "$(echo "$(now) - $T0" | bc)" "$1" "$l"; done; }
$K get pods -n $NS -l run=crashy -w --request-timeout=$((DUR+2))s --output-watch-events --no-headers 2>/dev/null | stamp "[STATUS열]" > $TMP/table &
$K get pods -n $NS -l run=crashy -w --request-timeout=$((DUR+2))s --no-headers \
  -o custom-columns='PHASE:.status.phase,READY:.status.conditions[?(@.type=="Ready")].status,RESTARTS:.status.containerStatuses[0].restartCount,WAITING:.status.containerStatuses[0].state.waiting.reason,TERMINATED:.status.containerStatuses[0].state.terminated.reason,FINISHED:.status.containerStatuses[0].state.terminated.finishedAt,RUNNING_SINCE:.status.containerStatuses[0].state.running.startedAt' 2>/dev/null | stamp "[필드]" > $TMP/fields &
sleep 2
$K run crashy -n $NS --image=busybox:1.37 --restart=Always --overrides="{\"spec\":{\"nodeName\":\"$N\"}}" --command -- sh -c 'sleep 2; exit 1' >/dev/null
for rp in OnFailure Never; do
  $K run $(echo $rp | tr A-Z a-z) -n $NS --image=busybox:1.37 --restart=$rp --overrides="{\"spec\":{\"nodeName\":\"$N\"}}" --command -- sh -c 'sleep 2; exit 1' >/dev/null
done
$K run nonode -n $NS --image=busybox:1.37 --overrides='{"spec":{"nodeSelector":{"lab/none":"true"}}}' --command -- sleep 3600 >/dev/null
wait   # 두 watch 는 --request-timeout 으로 DUR+2 초 뒤 스스로 끝난다

echo; echo "## B. restartPolicy Always, 2초 뒤 exit 1 (watch 이벤트마다 한 줄, 경과는 Mac 시계, 약 ${DUR}초)"
echo "  [STATUS열] = kubectl get 기본 표(EVENT NAME READY STATUS RESTARTS AGE)"
echo "  [필드]     = phase  Ready  restartCount  state.waiting.reason  state.terminated.reason  state.terminated.finishedAt  state.running.startedAt"
cat $TMP/table $TMP/fields | sort -t+ -k2,2n -s
echo; echo "  컨테이너가 끝난 시각 → 다시 시작한 시각 (위 [필드] 의 finishedAt 과 startedAt 을 짝지음, 초 단위)"
python3 - "$TMP/fields" <<'PY'
import sys, re, datetime as d
fin, st = [], []
for l in open(sys.argv[1], encoding='utf-8'):
    ts = re.findall(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ', l)
    cols = l.split()
    for t in ts:
        idx = cols.index(t)
        (fin if idx == len(cols) - 2 else st).append(t)
p = lambda t: d.datetime.strptime(t, '%Y-%m-%dT%H:%M:%SZ')
fin = sorted(set(fin), key=p); st = sorted(set(st), key=p)
for f in fin:
    nxt = [x for x in st if p(x) >= p(f)]
    if nxt:
        print('    %s → %s  %3d초' % (f, nxt[0], (p(nxt[0]) - p(f)).seconds))
    else:
        print('    %s → (관찰 시간 안에 다시 시작하지 않음)' % f)
PY
echo; echo "  BackOff 이벤트: $($K get events -n $NS --field-selector involvedObject.name=crashy,reason=BackOff -o jsonpath='{range .items[*]}count={.count} first={.firstTimestamp} last={.lastTimestamp}{end}')"

echo; echo "## C. 같은 컨테이너를 restartPolicy 만 바꿔 실행한 파드 (생성 약 ${DUR}초 뒤)"
$K get pods -n $NS onfailure never --no-headers -o wide | awk '{print "  [STATUS열] "$1, $2, $3, "restarts="$4}'
for p in onfailure never; do
  echo "  [필드] $p phase=$($K get pod $p -n $NS -o jsonpath='{.status.phase} Ready={.status.conditions[?(@.type=="Ready")].status} restartCount={.status.containerStatuses[0].restartCount} lastExit={.status.containerStatuses[0].lastState.terminated.exitCode} exit={.status.containerStatuses[0].state.terminated.exitCode}')"
done

echo; echo "## D. 스케줄할 수 없는 파드의 conditions (모든 필드)"
$K get pod nonode -n $NS -o jsonpath='{range .status.conditions[*]}  type={.type} status={.status} reason={.reason} lastProbeTime={.lastProbeTime} lastTransitionTime={.lastTransitionTime}{"\n"}{end}'
echo "  phase=$($K get pod nonode -n $NS -o jsonpath='{.status.phase}')"

$K delete ns $NS --wait=true >/dev/null
rm -rf $TMP
echo; echo "  정리: $($K get ns $NS --no-headers 2>&1)"
