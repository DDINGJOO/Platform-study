#!/usr/bin/env python3
"""실습-3 측정 도구. 클러스터 상태를 0.2초 간격으로 읽어 '바꾼 순간부터 몇 초 뒤에 돌아왔나'를 잰다.

사용법 (labs/devops/ds-03-gitops 에서):
  python3 scripts/lab.py drift-scale [횟수] [간격초]   kubectl scale 로 replicas 를 바꾸고 selfHeal 이 되돌리는 시간
  python3 scripts/lab.py selfheal-off                selfHeal 을 끄면 손으로 바꾼 값이 남는지
  python3 scripts/lab.py drift-misc                  라벨 추가, ConfigMap 수정, Deployment 삭제, 손으로 만든 리소스
  python3 scripts/lab.py git-change [횟수]            git 에 replicas 를 바꿔 push 하고 클러스터에 반영되는 시간
  python3 scripts/lab.py webhook on|off              gitea 저장소 웹훅을 켜고 끈다
  python3 scripts/lab.py prune                       git 에서 Service 를 지웠을 때 prune 끔/켬 비교
  python3 scripts/lab.py waves                       PreSync 훅과 sync wave 순서를 첫 등장 시각으로 기록
  python3 scripts/lab.py bad-commit                  없는 이미지 태그를 커밋하고 git revert 로 되돌린다

결과는 out/<실험>.txt 에 상대 시각으로 남긴다(벽시계 시각과 IP 는 남기지 않는다).
"""
import json, os, subprocess, sys, time

CTX = "kind-ds-03"
WORK = os.environ.get("DS03_WORK", "/tmp/ds-03-work")
GITEA = "http://localhost:26030"
AUTH = ("lab", "lab-password-123")
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "out")
LOG = []
EMAIL = "lab@" + "example.com"   # 실습용 주소(예약 도메인)


def sh(cmd, check=True):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise SystemExit(f"실패: {cmd}\n{r.stderr}")
    return r.stdout.strip()


def k(args, check=True):
    return sh(f"kubectl --context {CTX} {args}", check)


def log(msg):
    print(msg, flush=True)
    LOG.append(msg)


def save(name):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name + ".txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(LOG) + "\n")


def app():
    return json.loads(k("-n argocd get application web -o json"))


def app_state():
    a = app()
    st = a.get("status", {})
    return st.get("sync", {}).get("status"), st.get("health", {}).get("status")


def wait_until(pred, timeout=400, step=0.2):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        v = pred()
        if v:
            return time.monotonic() - t0, v
        time.sleep(step)
    return None, None


def replicas():
    out = k("-n demo get deploy web -o jsonpath={.spec.replicas}", check=False)
    return int(out) if out.isdigit() else None


def git(cmd):
    return sh(f"git -C {WORK} -c user.name=lab -c user.email={EMAIL} {cmd}")


def set_policy(prune=None, self_heal=None):
    auto = {}
    if prune is not None:
        auto["prune"] = prune
    if self_heal is not None:
        auto["selfHeal"] = self_heal
    patch = json.dumps({"spec": {"syncPolicy": {"automated": auto}}})
    k(f"-n argocd patch application web --type merge -p '{patch}'")


def heal_count():
    st = app().get("status", {}).get("operationState", {})
    return st.get("operation", {}).get("sync", {}).get("autoHealAttemptsCount", 0)


# ---------------------------------------------------------------- 실험들

def iso(ts):
    import datetime
    return datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc).timestamp()


def drift_scale(n=6, gap=1.0):
    """replicas 를 5 로 바꾸고 git 값으로 돌아올 때까지. 돌아온 뒤 gap 초 쉬고 다시.
    단계별로 기록한다: OutOfSync 를 처음 본 시각, 되돌리는 sync 의 startedAt/finishedAt(초 단위), replicas 복구 시각."""
    want = replicas()
    log(f"# drift-scale: git 의 replicas={want}, 손으로 5 로 바꾼 뒤 되돌아오기까지 (복구 후 {gap}s 쉬고 다음 회차)")
    log("회차  OutOfSync감지  sync시작  sync끝  replicas복구   직전sync끝부터  autoHealAttemptsCount")
    for i in range(1, n + 1):
        prev_fin = iso(app()["status"]["operationState"]["finishedAt"])
        k("-n demo scale deploy web --replicas=5")
        t0 = time.time()
        t_out = t_back = None
        while time.time() - t0 < 400:
            a = app()
            st = a["status"]
            now = time.time() - t0
            if t_out is None and st["sync"]["status"] == "OutOfSync":
                t_out = now
            if t_back is None and replicas() == want:
                t_back = now
            op = st.get("operationState", {})
            if t_back is not None and op.get("finishedAt") and iso(op["finishedAt"]) > prev_fin:
                break
            time.sleep(0.2)
        op = app()["status"]["operationState"]
        ts, tf = iso(op["startedAt"]) - t0, iso(op["finishedAt"]) - t0
        cnt = op["operation"]["sync"].get("autoHealAttemptsCount", 0)
        fmt = lambda v: f"{v:6.1f}" if v is not None else "   -  "
        log(f"{i:>3}   {fmt(t_out)}      {ts:6.0f}   {tf:6.0f}   {fmt(t_back)}      {t0 - prev_fin:6.0f}         {cnt}")
        time.sleep(gap)


def drift_misc():
    log("# drift-misc: 손으로 바꾼 것 중 무엇이 드리프트로 잡히나")
    log(f"시작 시 autoHealAttemptsCount={heal_count()}")
    # 1. Git 에 없는 라벨 추가
    k("-n demo label deploy web owner=me --overwrite")
    time.sleep(15)
    lab = k("-n demo get deploy web -o jsonpath={.metadata.labels.owner}")
    log(f"라벨 owner=me 추가: 15초 뒤 app={app_state()}, 라벨 남음={lab!r}")
    k("-n demo label deploy web owner-")
    # 2. Git 에 있는 ConfigMap 값 수정
    k("""-n demo patch configmap web-config --type merge -p '{"data":{"GREETING":"edited by hand"}}'""")
    t, _ = wait_until(lambda: k("-n demo get cm web-config -o jsonpath={.data.GREETING}") == "hello from git")
    log(f"ConfigMap GREETING 수정: {t:.1f}초 뒤 git 값으로 복구 (autoHealAttemptsCount={heal_count()})")
    time.sleep(60)   # selfHeal 백오프(앞 시도 횟수에 따라 최대 300초)가 다음 측정에 끼지 않게 쉰다
    # 3. Deployment 삭제
    uid0 = k("-n demo get deploy web -o jsonpath={.metadata.uid}")
    k("-n demo delete deploy web --wait=false")
    t, _ = wait_until(lambda: (lambda u: u and u != uid0)(k("-n demo get deploy web -o jsonpath={.metadata.uid}", check=False)))
    log(f"Deployment 삭제: {t:.1f}초 뒤 새 uid 로 다시 생성 (autoHealAttemptsCount={heal_count()})")
    t2, _ = wait_until(lambda: k("-n demo get deploy web -o jsonpath={.status.readyReplicas}/{.spec.replicas}", check=False)
                       in ("2/2", "3/3"))
    log(f"  두 파드 Ready 까지는 삭제 후 {t + t2:.1f}초")
    # 4. Git 에 없는 리소스를 손으로 생성
    k("-n demo create configmap made-by-hand --from-literal=a=b")
    time.sleep(15)
    exists = k("-n demo get cm made-by-hand -o name", check=False)
    log(f"손으로 만든 ConfigMap: 15초 뒤 app={app_state()}, 남아 있음={bool(exists)}")
    k("-n demo delete cm made-by-hand")


def selfheal_off():
    log("# selfheal-off: selfHeal 을 끄고 replicas 를 손으로 바꾼다")
    set_policy(self_heal=False)
    time.sleep(5)
    want = replicas()
    k("-n demo scale deploy web --replicas=5")
    t, _ = wait_until(lambda: app_state()[0] == "OutOfSync", timeout=60)
    log(f"OutOfSync 표시까지 {t:.1f}초")
    time.sleep(60)
    log(f"60초 뒤: app={app_state()}, replicas={replicas()} (git 값 {want})")
    set_policy(self_heal=True)
    t, _ = wait_until(lambda: replicas() == want, timeout=400)
    log(f"selfHeal 을 다시 켜고 {t:.1f}초 뒤 replicas={want} 로 복구")


def git_change(n=3):
    log(f"# git-change: replicas 를 커밋·푸시하고 클러스터에 반영되기까지 (웹훅 {'켬' if hook_id() else '끔'})")
    log("회차  새 리비전 인식(초)  replicas 반영(초)")
    for i in range(1, n + 1):
        path = os.path.join(WORK, "apps/web/deployment.yaml")
        s = open(path).read()
        cur = int(s.split("replicas: ", 1)[1].split()[0])   # git 에 적힌 값
        new = 3 if cur == 2 else 2
        s = s.replace(f"replicas: {cur}\n", f"replicas: {new}\n", 1)
        open(path, "w").write(s)
        git(f"commit -qam 'web: replicas {new}'")
        git("push -q origin main")
        rev = git("rev-parse HEAD")
        t0 = time.monotonic()
        t_rev = t_rep = None
        while time.monotonic() - t0 < 400 and (t_rev is None or t_rep is None):
            now = time.monotonic() - t0
            if t_rev is None and app().get("status", {}).get("sync", {}).get("revision") == rev:
                t_rev = now
            if t_rep is None and replicas() == new:
                t_rep = now
            time.sleep(0.2)
        f = lambda v: f"{v:8.1f}" if v is not None else "  시간 초과"
        log(f"{i:>3}   {f(t_rev)}           {f(t_rep)}")
        time.sleep(5)


def hook_id():
    out = sh(f"curl -sf -u {AUTH[0]}:{AUTH[1]} {GITEA}/api/v1/repos/lab/demo/hooks")
    hooks = json.loads(out or "[]")
    return hooks[0]["id"] if hooks else None


def webhook(on):
    hid = hook_id()
    if on and not hid:
        body = json.dumps({"type": "gitea", "active": True, "events": ["push"],
                           "config": {"url": "http://argocd-server.argocd.svc/api/webhook",
                                      "content_type": "json"}})
        sh(f"curl -sf -u {AUTH[0]}:{AUTH[1]} -H 'Content-Type: application/json' -d '{body}' "
           f"{GITEA}/api/v1/repos/lab/demo/hooks")
    if not on and hid:
        sh(f"curl -sf -X DELETE -u {AUTH[0]}:{AUTH[1]} {GITEA}/api/v1/repos/lab/demo/hooks/{hid}")
    print("webhook", hook_id())


def prune():
    log("# prune: git 에서 service.yaml 을 지웠을 때")
    set_policy(prune=False)
    git("rm -q apps/web/service.yaml")
    git("commit -qm 'web: remove service'")
    git("push -q origin main")
    rev = git("rev-parse HEAD")
    t, _ = wait_until(lambda: app().get("status", {}).get("sync", {}).get("revision") == rev)
    time.sleep(5)
    a = app()
    svc = [r for r in a["status"]["resources"] if r["kind"] == "Service"]
    log(f"prune=false: {t:.1f}초 뒤 새 커밋 인식. app={app_state()}, Service 리소스 상태={svc}")
    log(f"  클러스터에 Service 남음: {bool(k('-n demo get svc web -o name', check=False))}")
    set_policy(prune=True)
    t, _ = wait_until(lambda: not k("-n demo get svc web -o name", check=False))
    log(f"prune=true 로 바꾸고 {t:.1f}초 뒤 Service 삭제. app={app_state()}")
    # 원상 복구
    git("revert --no-edit HEAD")
    git("push -q origin main")
    wait_until(lambda: k("-n demo get svc web -o name", check=False))
    set_policy(prune=False)


WAVES = """apiVersion: batch/v1
kind: Job
metadata:
  name: db-migrate
  annotations:
    argocd.argoproj.io/hook: PreSync
    argocd.argoproj.io/hook-delete-policy: BeforeHookCreation
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: migrate
          image: busybox:1.37
          command: ["sh", "-c", "echo migrating; sleep 5"]
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: w-config
  annotations:
    argocd.argoproj.io/sync-wave: "-1"
data: {k: v}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: w-app
  annotations:
    argocd.argoproj.io/sync-wave: "0"
spec:
  replicas: 1
  selector: {matchLabels: {app: w-app}}
  template:
    metadata: {labels: {app: w-app}}
    spec:
      containers:
        - name: whoami
          image: traefik/whoami:v1.12.0
          readinessProbe: {httpGet: {path: /health, port: 80}, periodSeconds: 2}
---
apiVersion: v1
kind: Service
metadata:
  name: w-svc
  annotations:
    argocd.argoproj.io/sync-wave: "1"
spec:
  selector: {app: w-app}
  ports: [{port: 80}]
"""

WAVES_APP = """apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: waves
  namespace: argocd
spec:
  project: default
  source: {repoURL: "http://gitea.gitea.svc:3000/lab/demo.git", targetRevision: main, path: apps/waves}
  destination: {server: "https://kubernetes.default.svc", namespace: waves}
  syncPolicy:
    automated: {}
    syncOptions: [CreateNamespace=true]
"""


def waves():
    log("# waves: PreSync 훅(5초 걸리는 Job) → wave -1 ConfigMap → wave 0 Deployment → wave 1 Service")
    os.makedirs(os.path.join(WORK, "apps/waves"), exist_ok=True)
    open(os.path.join(WORK, "apps/waves/all.yaml"), "w").write(WAVES)
    git("add apps/waves")
    if sh(f"git -C {WORK} status --porcelain"):
        git("commit -qm 'waves demo'")
        git("push -q origin main")
    # 다시 돌릴 때를 위해 앞선 waves 앱과 네임스페이스를 지운다
    k("-n argocd delete application waves --ignore-not-found --wait=true")
    k("delete namespace waves --ignore-not-found --wait=true")
    p = subprocess.run(f"kubectl --context {CTX} apply -f -", shell=True, input=WAVES_APP, text=True, capture_output=True)
    t0 = time.monotonic()
    seen = {}
    names = {"job.batch/db-migrate": "Job db-migrate (PreSync)", "configmap/w-config": "ConfigMap (wave -1)",
             "deployment.apps/w-app": "Deployment (wave 0)", "service/w-svc": "Service (wave 1)"}
    ready_at = None
    job_done = None
    while time.monotonic() - t0 < 180 and len(seen) < 4:
        out = k("-n waves get job,cm,deploy,svc -o name", check=False).split()
        now = time.monotonic() - t0
        for n in out:
            if n in names and n not in seen:
                seen[n] = now
        if job_done is None and "job.batch/db-migrate" in seen:
            if k("-n waves get job db-migrate -o jsonpath={.status.succeeded}", check=False) == "1":
                job_done = now
        if ready_at is None and "deployment.apps/w-app" in seen:
            if k("-n waves get deploy w-app -o jsonpath={.status.readyReplicas}", check=False) == "1":
                ready_at = now
        time.sleep(0.2)
    log("Application 생성 후 첫 등장 시각(초)")
    for n, label in names.items():
        log(f"  {seen.get(n, float('nan')):>6.1f}  {label}")
    log(f"  {job_done if job_done else float('nan'):>6.1f}  Job 성공 확인")
    log(f"  {ready_at if ready_at else float('nan'):>6.1f}  Deployment Ready 확인")


def bad_commit():
    log("# bad-commit: 없는 이미지 태그를 커밋한 뒤 git revert 로 되돌린다 (웹훅 켬 상태)")
    path = os.path.join(WORK, "apps/web/deployment.yaml")
    s = open(path).read()
    open(path, "w").write(s.replace("traefik/whoami:v1.12.0", "traefik/whoami:v9.9.9"))
    git("commit -qam 'web: bump image to v9.9.9 (없는 태그)'")
    git("push -q origin main")
    rev = git("rev-parse HEAD")
    t0 = time.monotonic()
    states = []
    last = None
    while time.monotonic() - t0 < 120:
        a = app()
        st = a.get("status", {})
        cur = (st.get("sync", {}).get("status"), st.get("health", {}).get("status"),
               st.get("sync", {}).get("revision", "")[:7], st.get("operationState", {}).get("phase"))
        if cur != last:
            log(f"  {time.monotonic() - t0:6.1f}s  sync={cur[0]} health={cur[1]} rev={cur[2]} op={cur[3]}")
            last = cur
        if cur[1] == "Degraded":
            break
        time.sleep(0.5)
    ready = k("-n demo get deploy web -o jsonpath={.status.readyReplicas}/{.status.replicas}")
    pods = k("-n demo get pods -o custom-columns=NAME:.metadata.name,IMAGE:.spec.containers[0].image,"
             "READY:.status.containerStatuses[0].ready,WAIT:.status.containerStatuses[0].state.waiting.reason")
    log(f"  준비된 파드/전체: {ready}")
    log("  " + pods.replace("\n", "\n  "))
    # argocd CLI 의 --core 모드는 kubeconfig 의 현재 네임스페이스에서 argocd-cm 을 찾는다. 임시 kubeconfig 로 argocd 를 지정한다
    r = subprocess.run("T=$(mktemp); kind get kubeconfig --name ds-03 > $T; "
                       "kubectl --kubeconfig $T config set-context --current --namespace=argocd >/dev/null; "
                       "KUBECONFIG=$T argocd app rollback web --core 2>&1; rm -f $T",
                       shell=True, capture_output=True, text=True)
    msg = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    try:
        msg = json.loads(msg).get("msg", msg)
    except ValueError:
        pass
    log("  argocd app rollback 시도: " + msg)
    git("revert --no-edit HEAD")
    git("push -q origin main")
    t1 = time.monotonic()
    tt, _ = wait_until(lambda: app_state() == ("Synced", "Healthy")
                       and "v9.9.9" not in k("-n demo get deploy web -o jsonpath={.spec.template.spec.containers[0].image}"),
                       timeout=300)
    log(f"git revert 푸시 후 {tt:.1f}초 만에 Synced/Healthy (이미지 v1.12.0)")
    log(f"git log: " + git("log --oneline -3").replace("\n", " | "))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "drift-scale":
        drift_scale(int(sys.argv[2]) if len(sys.argv) > 2 else 6, float(sys.argv[3]) if len(sys.argv) > 3 else 1.0)
        save(f"drift-scale-gap{sys.argv[3] if len(sys.argv) > 3 else '1'}")
    elif cmd == "selfheal-off":
        selfheal_off(); save("selfheal-off")
    elif cmd == "drift-misc":
        drift_misc(); save("drift-misc")
    elif cmd == "git-change":
        git_change(int(sys.argv[2]) if len(sys.argv) > 2 else 3)
        save("git-change-" + ("webhook" if hook_id() else "poll"))
    elif cmd == "webhook":
        webhook(sys.argv[2] == "on")
    elif cmd == "prune":
        prune(); save("prune")
    elif cmd == "waves":
        waves(); save("waves")
    elif cmd == "bad-commit":
        bad_commit(); save("bad-commit")
    else:
        print(__doc__)
