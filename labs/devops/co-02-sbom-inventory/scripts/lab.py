#!/usr/bin/env python3
"""소스 코드 관찰 실습-2 드라이버: 서비스 열 개에서 취약한 logback-core 를 쓰는 곳을 찾는다.

  python3 scripts/lab.py prepare   # 작업 저장소(CO02_WORK)에 커밋 두 개를 만들고 jar·POM·이미지를 빌드
  python3 scripts/lab.py deploy    # 서비스 열 개를 docker run 으로 띄운다(s04 만 첫 커밋 이미지)
  python3 scripts/lab.py query     # 질의 네 가지(Git HEAD 빌드 파일, POM, SBOM, 런타임)를 돌려 비교
  python3 scripts/lab.py trace s04 # 운영 중인 서비스에서 소스 한 줄까지 거슬러 올라간다
  python3 scripts/lab.py down      # 컨테이너, 이미지, 볼륨 정리

질의 대상: logback-core 가 FIXED(기본 1.5.13, CVE-2024-12798 수정 버전)보다 낮은 서비스.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.environ.get("CO02_WORK", "/tmp/co-02-work")
RESULTS = os.path.join(HERE, "results")
FIXED = tuple(int(x) for x in os.environ.get("FIXED", "1.5.13").split("."))
BASE_PORT = int(os.environ.get("BASE_PORT", "30100"))
SERVICES = [f"s{i:02d}" for i in range(1, 11)]
JAVA_OPTS = "-Xmx72m -Xss512k -XX:+UseSerialGC -XX:TieredStopAtLevel=1"

_log = None


def log(line=""):
    print(line, flush=True)
    if _log:
        _log.write(line + "\n")
        _log.flush()


def sh(cmd, cwd=HERE, check=True, quiet=False):
    t = time.time()
    p = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True)
    out = (p.stdout or "") + (p.stderr or "")
    if not quiet:
        log(f"$ {cmd}    # {time.time() - t:.1f}s, exit {p.returncode}")
    if check and p.returncode != 0:
        log(out[-4000:])
        raise SystemExit("command failed")
    return out


def get(url, timeout=10):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read()


def ver(s):
    m = re.match(r"(\d+)\.(\d+)\.(\d+)", s or "")
    return tuple(int(x) for x in m.groups()) if m else None


def verdict(v):
    """버전 문자열 하나를 vuln / ok / unknown / none 으로 판정한다."""
    if v is None:
        return "none"
    t = ver(v)
    if t is None or "+" in v or "[" in v or "(" in v:
        return "unknown"
    return "vuln" if t < FIXED else "ok"


# ---------------------------------------------------------------------------
# prepare: 작업 저장소와 커밋 두 개, 빌드 산출물

def git(args, check=True):
    return sh(f"git -c user.name=lab -c user.email=lab {args}", cwd=WORK, check=check, quiet=True)


def gradle(tasks):
    return sh(f"docker compose run --rm -T gradle gradle -q --console=plain {tasks}")


def collect(commit, services):
    out = os.path.join(WORK, "out", commit)
    os.makedirs(out, exist_ok=True)
    for s in services:
        shutil.copy(os.path.join(WORK, s, "build/libs", f"{s}.jar"), out)
        shutil.copy(os.path.join(WORK, s, "build/publications/maven/pom-default.xml"), os.path.join(out, f"{s}.pom"))
    extra = os.path.join(WORK, "build/extra")
    if os.path.isdir(extra):
        shutil.copytree(extra, os.path.join(out, "extra"), dirs_exist_ok=True)


def image(service, commit):
    out = os.path.join(WORK, "out", commit)
    df = os.path.join(HERE, "docker", "Dockerfile.s06" if service == "s06" else "Dockerfile")
    sh(f"docker build -q -f {df} --build-arg SERVICE={service} --build-arg REVISION={commit} "
       f"-t co02/{service}:{commit[:7]} {out}")


def cmd_prepare():
    if os.path.exists(WORK):
        shutil.rmtree(WORK)
    shutil.copytree(os.path.join(HERE, "services"), WORK)
    s04 = os.path.join(WORK, "s04", "build.gradle")
    original = open(s04, encoding="utf-8").read()

    # 커밋 1: s04 에 핀이 살아 있다
    open(s04, "w", encoding="utf-8").write(original.replace("//PIN ", ""))
    git("init -q -b main")
    git("add -A")
    git("commit -q -m 'c1: s04 pins logback 1.5.12'")
    c1 = git("rev-parse HEAD").strip()
    log(f"commit 1 = {c1[:7]} (s04 에 logback 1.5.12 핀)")
    gradle(":s04:bootJar :s04:generatePomFileForMavenPublication")
    collect(c1, ["s04"])

    # 커밋 2: s04 의 핀을 지운다. s04 는 이 커밋으로 다시 배포되지 않는다
    open(s04, "w", encoding="utf-8").write(
        "\n".join(l for l in original.splitlines() if not l.startswith("//PIN")) + "\n")
    git("commit -q -am 'c2: s04 drops the logback pin'")
    c2 = git("rev-parse HEAD").strip()
    log(f"commit 2 = {c2[:7]} (s04 핀 제거)")
    tasks = " ".join(f":{s}:bootJar :{s}:generatePomFileForMavenPublication" for s in SERVICES)
    gradle(tasks + " :opsExtraJars")
    collect(c2, SERVICES)

    image("s04", c1)
    for s in SERVICES:
        if s != "s04":
            image(s, c2)
    json.dump({"c1": c1, "c2": c2}, open(os.path.join(WORK, "commits.json"), "w"))


# ---------------------------------------------------------------------------
# deploy

def commits():
    return json.load(open(os.path.join(WORK, "commits.json")))


def wait_up(port, timeout=180):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            if b"UP" in get(f"http://localhost:{port}/actuator/health", timeout=2):
                return time.time() - t0
        except Exception:
            pass
        time.sleep(1)
    return None


def cmd_deploy():
    """한 번에 하나씩 띄운다. 같은 Docker 를 쓰는 다른 실습의 측정에 CPU 를 한꺼번에 몰지 않으려고."""
    c = commits()
    for i, s in enumerate(SERVICES, 1):
        commit = c["c1"] if s == "s04" else c["c2"]
        sh(f"docker rm -f co02-{s}", check=False, quiet=True)
        sh(f"docker run -d --name co02-{s} --label lab.co02=1 -m 256m "
           f"-e JAVA_TOOL_OPTIONS='{JAVA_OPTS}' -e SPRING_APPLICATION_NAME={s} "
           f"-p {BASE_PORT + i}:8080 co02/{s}:{commit[:7]}", quiet=True)
        t = wait_up(BASE_PORT + i)
        log(f"{s} ({commit[:7]}) " + (f"UP {t:.1f}s" if t is not None else "NOT READY"))


# ---------------------------------------------------------------------------
# query

def discover():
    """플랫폼에 묻는다: 지금 떠 있는 컨테이너와 그 포트, 이미지 라벨."""
    out = sh("docker ps --filter label=lab.co02=1 --format '{{.Names}} {{.Ports}} {{.Image}}'", quiet=True)
    found = {}
    for line in out.splitlines():
        name, rest = line.split(" ", 1)
        m = re.search(r":(\d+)->8080", rest)
        found[name.replace("co02-", "")] = {"port": int(m.group(1)), "image": rest.split()[-1]}
    return found


def method_git_head():
    """A. Git HEAD 의 빌드 파일에 적힌 logback 좌표를 읽는다."""
    res = {}
    for s in SERVICES:
        text = open(os.path.join(WORK, s, "build.gradle"), encoding="utf-8").read()
        code = "\n".join(l.split("//")[0] for l in text.splitlines())
        found = re.findall(r"ch\.qos\.logback:logback-(core|classic)(?::([^'\"\s]+))?['\"]", code)
        core = [v for a, v in found if a == "core"]
        if core:
            res[s] = core[0] or "(버전 없음)"
        elif found:
            res[s] = "(core 없음, classic " + (found[0][1] or "버전 없음") + ")"
        else:
            res[s] = None
    return res


def method_pom():
    """B. 배포된 커밋에서 만든 POM 을 Maven 으로 해소한다(표준 메타데이터만 보는 도구의 시선)."""
    c = commits()
    script = " ; ".join(
        f"echo '== {s}' ; mvn -B -q -f /work/out/{c['c1'] if s == 's04' else c['c2']}/{s}.pom "
        f"dependency:list -DincludeScope=runtime -DoutputFile=/tmp/{s}.txt >/tmp/{s}.log 2>&1 "
        f"|| echo FAILED ; grep -E 'logback-core' /tmp/{s}.txt 2>/dev/null || echo none"
        for s in SERVICES)
    out = sh(f"docker compose run --rm -T maven sh -c \"{script}\"", check=False)
    res, cur = {}, None
    for line in out.splitlines():
        if line.startswith("== "):
            cur = line[3:].strip()
        elif cur and line.strip() == "FAILED":
            res[cur] = "(해소 실패)"
        elif cur and cur not in res:
            m = re.search(r"logback-core:jar:([^:]+)", line)
            res[cur] = m.group(1) if m else None
    return res


def method_sbom(found):
    """C. 실행 중인 서비스의 /actuator/sbom/application 에서 logback-core 를 찾는다."""
    res = {}
    for s, info in found.items():
        try:
            doc = json.loads(get(f"http://localhost:{info['port']}/actuator/sbom/application"))
            core = [x.get("version") for x in doc.get("components", []) if x.get("name") == "logback-core"]
            res[s] = core[0] if core else None
        except Exception as e:
            res[s] = f"error {e}"
    return res


def method_runtime(found):
    """정답. 실행 중인 JVM 이 logback-core 클래스를 읽은 jar 이름에서 버전을 뽑는다."""
    res, raw = {}, {}
    for s, info in found.items():
        doc = json.loads(get(f"http://localhost:{info['port']}/lab/logback"))
        raw[s] = doc
        m = re.search(r"logback-core-([0-9][^/!]*?)\.jar", doc.get("core", ""))
        res[s] = m.group(1) if m else (None if doc.get("core") == "none" else doc.get("core"))
    return res, raw


def score(name, answers, truth):
    tp = fp = fn = tn = unk = 0
    for s in SERVICES:
        t = verdict(truth.get(s)) == "vuln"
        v = answers.get(s)
        if v is None or str(v).startswith("(core 없음"):
            a = "none"
        elif str(v).startswith("(") or str(v).startswith("error"):
            a = "unknown"
        else:
            a = verdict(v)
        if a == "unknown":
            unk += 1
            if t:
                fn += 1
            continue
        hit = a == "vuln"
        tp += hit and t
        fp += hit and not t
        fn += (not hit) and t
        tn += (not hit) and (not t)
    log(f"  {name:<28} 정탐 {tp}  오탐 {fp}  미탐 {fn}  맞게 제외 {tn}  판정 불가 {unk}")
    return tp, fp, fn, tn, unk


def cmd_query():
    t = time.time()
    found = discover()
    t_discover = time.time() - t
    log(f"플랫폼 질의(docker ps, 라벨 lab.co02=1): {len(found)}개 서비스, {t_discover:.2f}s")

    t = time.time(); a = method_git_head(); t_a = time.time() - t
    t = time.time(); b = method_pom(); t_b = time.time() - t
    t = time.time(); c = method_sbom(found); t_c = time.time() - t
    t = time.time(); d, raw = method_runtime(found); t_d = time.time() - t

    log(f"\n질의: logback-core < {'.'.join(map(str, FIXED))} 인 서비스\n")
    log(f"  {'서비스':<6} {'A. Git HEAD 빌드 파일':<24} {'B. POM→Maven':<14} {'C. SBOM':<10} {'정답(런타임)':<12}")
    for s in SERVICES:
        log(f"  {s:<6} {str(a.get(s)):<24} {str(b.get(s)):<14} {str(c.get(s)):<10} {str(d.get(s)):<12}")
    log("")
    score("A. Git HEAD 빌드 파일", a, d)
    score("B. 배포본 POM 을 Maven 으로", b, d)
    score("C. 실행 중 SBOM", c, d)
    log(f"\n걸린 시간: A {t_a:.2f}s, B {t_b:.1f}s(Maven 컨테이너 기동 포함), C {t_c:.2f}s, 정답 {t_d:.2f}s")
    log("\n런타임 원자료(logback-core 를 읽은 위치):")
    for s in SERVICES:
        log(f"  {s}: core={raw[s].get('core')}")
        log(f"       classic={raw[s].get('classic')}")
    json.dump({"A": a, "B": b, "C": c, "truth": d, "raw": raw}, open(os.path.join(RESULTS, "query.json"), "w"),
              ensure_ascii=False, indent=1)


def cmd_trace():
    s = sys.argv[2] if len(sys.argv) > 2 else "s04"
    found = discover()
    port = found[s]["port"]
    log(f"1) 플랫폼: docker ps 에서 {s} -> 이미지 {found[s]['image']}, 포트 {port}")
    rev = sh(f"docker inspect --format '{{{{index .Config.Labels \"org.opencontainers.image.revision\"}}}}' co02-{s}",
             quiet=True).strip()
    log(f"   이미지 라벨 org.opencontainers.image.revision = {rev[:12]}")
    info = json.loads(get(f"http://localhost:{port}/actuator/info"))
    commit = info.get("git", {}).get("commit", {}).get("id")
    log(f"2) 앱: GET /actuator/info -> git.commit.id = {commit}, branch = {info.get('git', {}).get('branch')}")
    full = git(f"rev-parse {commit}").strip()
    head = git("rev-parse HEAD").strip()
    log(f"3) 저장소: {commit} -> {full[:12]}, HEAD 는 {head[:12]} (같은가: {full == head})")
    log(f"4) 소스: git show {commit}:{s}/build.gradle 에서 logback 줄")
    for line in git(f"show {commit}:{s}/build.gradle").splitlines():
        if "logback" in line:
            log("     " + line)
    log(f"   HEAD 의 같은 파일에서 logback 줄")
    lines = [l for l in git(f"show HEAD:{s}/build.gradle").splitlines() if "logback" in l]
    log("     " + ("\n     ".join(lines) if lines else "(없음)"))
    log("   그 사이 커밋:")
    log("     " + git(f"log --oneline {commit}..HEAD -- {s}").strip().replace("\n", "\n     "))


def cmd_down():
    sh("docker ps -aq --filter label=lab.co02=1 | xargs docker rm -f", check=False)
    sh("docker images 'co02/*' -q | sort -u | xargs docker rmi -f", check=False)
    sh("docker compose --profile tools down -v", check=False)


def main():
    global _log
    if len(sys.argv) < 2:
        print(__doc__)
        return
    name = sys.argv[1]
    fn = globals().get("cmd_" + name)
    if not fn:
        raise SystemExit("unknown command " + name)
    os.makedirs(RESULTS, exist_ok=True)
    if name in ("prepare", "query", "trace"):
        _log = open(os.path.join(RESULTS, name + ".txt"), "w", encoding="utf-8")
    fn()


if __name__ == "__main__":
    main()
