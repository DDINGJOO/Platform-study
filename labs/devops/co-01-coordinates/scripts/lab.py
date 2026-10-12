#!/usr/bin/env python3
"""소스 코드 관찰 실습-1 실험 드라이버.

같은 좌표(그룹:이름:버전, 이미지:태그)가 다른 바이너리를 가리키는 순간을 만들고 잰다.
결과는 results/<실험>.txt 에 남긴다. 실행 위치는 이 실습 디렉터리다.

  python3 scripts/lab.py up
  python3 scripts/lab.py snapshot      # SNAPSHOT 두 번 게시, 캐시가 다른 소비자 다섯이 받은 jar
  python3 scripts/lab.py release       # 릴리스 재게시 거부
  python3 scripts/lab.py tag           # 같은 태그 재푸시 전후 다이제스트
  python3 scripts/lab.py dynamic       # 2.10.+, latest.release, Maven 범위·RELEASE, 잠금
  python3 scripts/lab.py rebuild       # 같은 소스를 두 번 빌드했을 때 jar·이미지가 같은가
  python3 scripts/lab.py down
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(HERE, "results")
REPO = "http://localhost:" + os.environ.get("REPO_PORT", "30080")
REG = "localhost:" + os.environ.get("REGISTRY_PORT", "30500")

_log = None
_t0 = time.time()


def log(line=""):
    print(line, flush=True)
    if _log:
        _log.write(line + "\n")
        _log.flush()


def sh(cmd, check=True, quiet=False):
    """명령을 실행하고 (종료코드, 출력)을 돌려준다. 출력은 그대로 로그에도 남긴다."""
    t = time.time()
    p = subprocess.run(cmd, cwd=HERE, shell=isinstance(cmd, str), capture_output=True, text=True)
    out = (p.stdout or "") + (p.stderr or "")
    if not quiet:
        log(f"$ {cmd if isinstance(cmd, str) else ' '.join(cmd)}    # {time.time() - t:.1f}s, exit {p.returncode}")
    if check and p.returncode != 0:
        log(out)
        raise SystemExit(f"command failed: {cmd}")
    return p.returncode, out


def gradle(box, project, args, check=True):
    return sh(f"docker compose run --rm -T {box} gradle -q --console=plain -p /work/{project} {args}", check=check)


def maven(box, project, args, check=True):
    return sh(f"docker compose run --rm -T {box} mvn -B -q -f /work/{project}/pom.xml {args}", check=check)


def http(url, method="GET", data=None, auth=False):
    req = urllib.request.Request(url, method=method, data=data)
    if auth:
        import base64
        req.add_header("Authorization", "Basic " + base64.b64encode(b"lab:lab-secret-123").decode())
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def publish(aid, ver, content, box="gradle-ci", check=True):
    return gradle(box, "lib", f"clean publish -Paid={aid} -Pver={ver} -Pcontent={content}", check=check)


def gradle_resolved(box, deps, extra=""):
    _, out = gradle(box, "consumer-gradle", f"resolved '-Pdeps={deps}' {extra}", check=False)
    lines = [l for l in out.splitlines() if l.startswith("RESOLVED")]
    if not lines:
        lines = [l for l in out.splitlines() if l.strip()][-6:]
    for l in lines:
        log("    " + l)
    return lines


def maven_resolved(box, aid, ver, extra=""):
    # 호스트 셸을 거치지 않게 리스트로 넘긴다($(...) 가 호스트에서 풀리지 않도록)
    script = (f"mvn -B -f /work/consumer-maven/pom.xml dependency:list -Ddep.aid={aid} '-Ddep.ver={ver}' "
              f"-DoutputAbsoluteArtifactFilename=true {extra} > /tmp/out.txt 2>&1; "
              "grep -E '^.INFO.    lab:|ERROR.*lab' /tmp/out.txt | head -3 | sed 's/^.INFO. *//'; "
              "for f in $(grep -o '/root/.m2/[^ ]*[.]jar' /tmp/out.txt); do "
              "echo sha256=$(sha256sum $f | cut -c1-16); done")
    cmd = ["docker", "compose", "run", "--rm", "-T", box, "sh", "-c", script]
    _, out = sh(cmd, check=False)
    lines = [l for l in out.splitlines() if l.strip()]
    for l in lines[-8:]:
        log("    " + l)
    return lines


def wait_repo():
    for _ in range(90):
        try:
            code, _ = http(REPO + "/")
            if code == 200:
                return
        except Exception:
            pass
        time.sleep(2)
    raise SystemExit("reposilite did not start")


def show_metadata(path):
    code, body = http(f"{REPO}/{path}")
    log(f"  GET /{path} -> {code}")
    for l in body.decode(errors="replace").splitlines():
        if l.strip():
            log("    " + l)


# ---------------------------------------------------------------------------

def cmd_up():
    sh("docker compose up -d reposilite registry")
    wait_repo()
    log("reposilite ready: " + REPO)


def cmd_down():
    sh("docker compose --profile tools down -v")


def set_preserve(flag):
    """Reposilite 스냅숏 저장소의 preserveSnapshots 설정을 바꾼다(관리 API)."""
    _, body = http(f"{REPO}/api/settings/domain/maven", auth=True)
    cfg = json.loads(body)
    for r in cfg["repositories"]:
        if r["id"] == "snapshots":
            r["preserveSnapshots"] = flag
    req = urllib.request.Request(f"{REPO}/api/settings/domain/maven", method="PUT",
                                 data=json.dumps(cfg).encode())
    import base64
    req.add_header("Authorization", "Basic " + base64.b64encode(b"lab:lab-secret-123").decode())
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=20) as r:
        log(f"  preserveSnapshots={flag} -> {r.status}")


def cmd_snapshot():
    log("# SNAPSHOT 을 두 번 게시하고, 캐시 상태가 다른 소비자가 무엇을 받는지 본다")
    log("# gradle-a, gradle-b, maven-a, maven-b 는 각자 캐시를 가진 '개발자 PC'다. gradle-ci 는 게시만 한다")
    dep = "lab:lib:1.0.0-SNAPSHOT"
    log("\n## 1. 첫 게시 (content=build-1)")
    publish("lib", "1.0.0-SNAPSHOT", "build-1")
    show_metadata("snapshots/lab/lib/1.0.0-SNAPSHOT/maven-metadata.xml")
    _, md = http(f"{REPO}/snapshots/lab/lib/1.0.0-SNAPSHOT/maven-metadata.xml")
    m = re.search(r"<value>([^<]+)</value>", md.decode())
    first_unique = m.group(1) if m else None
    log(f"  첫 게시의 실제 파일 버전: {first_unique}")
    log("\n## 2. 첫 게시 직후 소비자 두 대가 받는다")
    log("  gradle-a:")
    gradle_resolved("gradle-a", dep)
    log("  maven-a:")
    maven_resolved("maven-a", "lib", "1.0.0-SNAPSHOT")

    log("\n## 3. 같은 좌표로 다시 게시 (content=build-2)")
    publish("lib", "1.0.0-SNAPSHOT", "build-2")
    show_metadata("snapshots/lab/lib/1.0.0-SNAPSHOT/maven-metadata.xml")
    _, listing = http(f"{REPO}/api/maven/details/snapshots/lab/lib/1.0.0-SNAPSHOT")
    try:
        files = [f["name"] for f in json.loads(listing).get("files", [])]
        log("  저장소의 파일 목록: " + ", ".join(sorted(files)))
    except Exception:
        log("  (파일 목록 API 응답을 읽지 못함) " + listing[:200].decode(errors="replace"))

    log("\n## 4. 두 번째 게시 뒤 다섯 소비자가 같은 좌표를 받는다")
    log("  gradle-a (캐시 있음, 옵션 없음):")
    gradle_resolved("gradle-a", dep)
    log("  gradle-b (캐시 없음):")
    gradle_resolved("gradle-b", dep)
    log("  gradle-a --refresh-dependencies:")
    gradle_resolved("gradle-a", dep, "--refresh-dependencies")
    log("  maven-a (로컬 저장소 있음, 옵션 없음):")
    maven_resolved("maven-a", "lib", "1.0.0-SNAPSHOT")
    log("  maven-b (로컬 저장소 없음):")
    maven_resolved("maven-b", "lib", "1.0.0-SNAPSHOT")
    log("  maven-a -U:")
    maven_resolved("maven-a", "lib", "1.0.0-SNAPSHOT", "-U")
    if first_unique:
        log(f"  gradle-ci, 첫 게시의 시각이 붙은 버전 {first_unique} 를 직접 적으면:")
        gradle_resolved("gradle-ci", f"lab:lib:{first_unique}", "--refresh-dependencies")
        code, _ = http(f"{REPO}/snapshots/lab/lib/1.0.0-SNAPSHOT/lib-{first_unique}.jar")
        log(f"  GET lib-{first_unique}.jar -> {code}")

    log("\n## 5. 스냅숏 저장소의 preserveSnapshots 를 켜고 같은 일을 반복 (artifact lib-p)")
    set_preserve(True)
    publish("lib-p", "1.0.0-SNAPSHOT", "build-1")
    _, md = http(f"{REPO}/snapshots/lab/lib-p/1.0.0-SNAPSHOT/maven-metadata.xml")
    m = re.search(r"<value>([^<]+)</value>", md.decode())
    pin = m.group(1)
    publish("lib-p", "1.0.0-SNAPSHOT", "build-2")
    _, listing = http(f"{REPO}/api/maven/details/snapshots/lab/lib-p/1.0.0-SNAPSHOT")
    files = sorted(f["name"] for f in json.loads(listing).get("files", []) if f["name"].endswith(".jar"))
    log("  저장소의 jar: " + ", ".join(files))
    log(f"  {pin} 를 직접 적으면:")
    gradle_resolved("gradle-ci", f"lab:lib-p:{pin}", "--refresh-dependencies")
    log("  1.0.0-SNAPSHOT 으로 적으면:")
    gradle_resolved("gradle-ci", "lab:lib-p:1.0.0-SNAPSHOT", "--refresh-dependencies")
    set_preserve(False)


def cmd_release():
    log("# 릴리스 버전 1.0.0 을 게시하고, 같은 좌표에 다른 내용을 다시 게시한다")
    publish("lib", "1.0.0", "release-1")
    jar = "releases/lab/lib/1.0.0/lib-1.0.0.jar"
    code, body = http(f"{REPO}/{jar}")
    import hashlib
    first = hashlib.sha256(body).hexdigest()[:16]
    log(f"  GET {jar} -> {code}, sha256={first}")
    log("\n## Gradle 로 재게시 (content=release-2)")
    rc, out = publish("lib", "1.0.0", "release-2", check=False)
    for l in out.splitlines():
        if re.search(r"(?i)status code|could not|failed|409|conflict|error", l):
            log("    " + l.strip())
    log("\n## curl 과 같은 방식으로 직접 PUT (같은 경로, 다른 바이트)")
    code, body = http(f"{REPO}/{jar}", method="PUT", data=b"not the same jar", auth=True)
    log(f"  PUT {jar} -> {code} {body[:200].decode(errors='replace')}")
    code, body = http(f"{REPO}/{jar}")
    log(f"  GET {jar} -> {code}, sha256={hashlib.sha256(body).hexdigest()[:16]} (처음 것과 같나: {hashlib.sha256(body).hexdigest()[:16] == first})")
    log("\n## 메타데이터 파일도 막히나")
    code, body = http(f"{REPO}/releases/lab/lib/maven-metadata.xml", method="PUT",
                      data=b"<metadata/>", auth=True)
    log(f"  PUT releases/lab/lib/maven-metadata.xml -> {code} {body[:120].decode(errors='replace')}")
    show_metadata("releases/lab/lib/maven-metadata.xml")


def digest(repo, tag):
    req = urllib.request.Request(f"http://{REG}/v2/{repo}/manifests/{tag}", method="HEAD")
    req.add_header("Accept", ", ".join([
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
        "application/vnd.oci.image.manifest.v1+json",
        "application/vnd.docker.distribution.manifest.v2+json"]))
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.headers.get("Docker-Content-Digest")


def cmd_tag():
    log("# 같은 태그로 두 번 푸시한다. 그 사이에 띄운 컨테이너와 그 뒤에 띄운 컨테이너를 비교한다")
    img = f"{REG}/lab/app:1.0"
    sh(f"docker build -q --build-arg CONTENT=v1 -t {img} projects/image")
    sh(f"docker push -q {img}")
    d1 = digest("lab/app", "1.0")
    log(f"  첫 푸시 뒤 레지스트리의 1.0 -> {d1}")
    sh(f"docker run -d --name co01-node-a {img}")

    sh(f"docker build -q --build-arg CONTENT=v2 -t {img} projects/image")
    sh(f"docker push -q {img}")
    d2 = digest("lab/app", "1.0")
    log(f"  두 번째 푸시 뒤 레지스트리의 1.0 -> {d2}")
    sh(f"docker run -d --name co01-node-b {img}")
    time.sleep(1)

    for c in ["co01-node-a", "co01-node-b"]:
        _, cfg = sh(f"docker inspect --format '{{{{.Config.Image}}}} {{{{.Image}}}}' {c}", quiet=True)
        _, logs = sh(f"docker logs {c}", quiet=True)
        log(f"  {c}: 요청한 이미지/실제 이미지 ID = {cfg.strip()}, 내용 = {logs.strip()}")
    _, ps = sh("docker ps --filter name=co01-node --format '{{.Names}}  IMAGE={{.Image}}'", quiet=True)
    log("  docker ps:")
    for l in ps.splitlines():
        log("    " + l)
    log("\n## 옛 다이제스트로는 여전히 받을 수 있나")
    sh(f"docker rmi -f {img}", check=False, quiet=True)
    rc, out = sh(f"docker pull -q {REG}/lab/app@{d1}", check=False)
    log("    " + out.strip().splitlines()[-1] if out.strip() else "    (출력 없음)")
    sh("docker rm -f co01-node-a co01-node-b", check=False, quiet=True)


def cmd_dynamic():
    log("# 동적 버전: 2.10.+, latest.release, Maven 범위와 RELEASE, 그리고 잠금")
    log("\n## 1. 게시 순서: 2.9.0 -> 2.10.9 -> 2.10.10 -> 2.11.0-rc1, util 1.0.0")
    for v in ["2.9.0", "2.10.9", "2.10.10", "2.11.0-rc1"]:
        publish("dyn", v, "dyn-" + v)
    publish("util", "1.0.0", "util-1.0.0")
    show_metadata("releases/lab/dyn/maven-metadata.xml")

    log("\n## 2. Gradle (gradle-ci, 캐시 비우기 위해 --refresh-dependencies)")
    for d, extra in [("lab:dyn:2.10.+", ""), ("lab:dyn:latest.release", ""),
                     ("lab:dyn:latest.release", "-PnoRc"), ("lab:dyn:[2.10,2.11)", "")]:
        log(f"  {d} {extra}")
        gradle_resolved("gradle-ci", d, "--refresh-dependencies " + extra)

    log("\n## 3. Maven (maven-b, -U)")
    for v in ["[2.10,2.11)", "RELEASE", "LATEST"]:
        log(f"  lab:dyn:{v}")
        maven_resolved("maven-b", "dyn", v, "-U")

    log("\n## 4. 잠금 파일을 쓴다 (consumer-locked, -Plock --write-locks)")
    lockfile = os.path.join(HERE, "projects/consumer-locked/gradle.lockfile")
    if os.path.exists(lockfile):
        os.remove(lockfile)
    gradle("gradle-ci", "consumer-locked", "dependencies --configuration runtimeClasspath -Plock --write-locks --refresh-dependencies")
    for l in open(lockfile, encoding="utf-8"):
        if l.startswith("lab:"):
            log("    " + l.rstrip())
    log("  잠금 없는 빌드와 잠금 있는 빌드의 해소 결과(새 버전 게시 전):")
    _, a = gradle("gradle-ci", "consumer-locked", "resolved --refresh-dependencies")
    _, b = gradle("gradle-ci", "consumer-locked", "resolved -Plock --refresh-dependencies")
    before_unlocked = sorted(l for l in a.splitlines() if l.startswith("RESOLVED"))
    before_locked = sorted(l for l in b.splitlines() if l.startswith("RESOLVED"))
    log("    unlocked: " + ", ".join(before_unlocked))
    log("    locked  : " + ", ".join(before_locked))

    log("\n## 5. 새 버전 게시: dyn 2.10.11 (rc 다음에 낸 핫픽스), util 1.1.0")
    publish("dyn", "2.10.11", "dyn-2.10.11")
    publish("util", "1.1.0", "util-1.1.0")
    show_metadata("releases/lab/dyn/maven-metadata.xml")
    log("  Maven RELEASE / LATEST 를 다시 받는다 (maven-b, -U)")
    maven_resolved("maven-b", "dyn", "RELEASE", "-U")
    maven_resolved("maven-b", "dyn", "LATEST", "-U")
    log("  Gradle latest.release 를 다시 받는다")
    gradle_resolved("gradle-ci", "lab:dyn:latest.release", "--refresh-dependencies")

    log("\n## 6. 같은 소스를 다시 빌드: 잠금 없음 / 잠금 있음")
    _, a = gradle("gradle-ci", "consumer-locked", "resolved --refresh-dependencies")
    _, b = gradle("gradle-ci", "consumer-locked", "resolved -Plock --refresh-dependencies")
    after_unlocked = sorted(l for l in a.splitlines() if l.startswith("RESOLVED"))
    after_locked = sorted(l for l in b.splitlines() if l.startswith("RESOLVED"))
    log("    unlocked: " + ", ".join(after_unlocked))
    log("    locked  : " + ", ".join(after_locked))
    ch_u = len(set(after_unlocked) - set(before_unlocked))
    ch_l = len(set(after_locked) - set(before_locked))
    log(f"  두 빌드 사이 해소 버전이 바뀐 모듈 수: 잠금 없음 {ch_u}/2, 잠금 있음 {ch_l}/2")
    log("\n## 7. 잠금 상태에서 빌드 파일만 고치면 (dyn 을 2.11.+ 로)")
    path = os.path.join(HERE, "projects/consumer-locked/build.gradle")
    src = open(path, encoding="utf-8").read()
    try:
        open(path, "w", encoding="utf-8").write(src.replace("lab:dyn:2.10.+", "lab:dyn:2.11.+"))
        rc, out = gradle("gradle-ci", "consumer-locked", "resolved -Plock", check=False)
        for l in out.splitlines():
            if re.search(r"(?i)lock|did not resolve|constraint|failed|rejected", l):
                log("    " + l.strip())
    finally:
        open(path, "w", encoding="utf-8").write(src)


def cmd_rebuild():
    log("# 같은 소스를 두 번 빌드했을 때 결과물이 같은가 (재빌드 승격이 왜 위험한지)")
    import hashlib

    def jar_sha(rel):
        return hashlib.sha256(open(os.path.join(HERE, rel), "rb").read()).hexdigest()[:16]

    log("\n## Gradle 9.8.1 jar (기본 설정)")
    shas = []
    for i in range(2):
        gradle("gradle-ci", "lib", "clean jar -Pver=1.0.0 -Pcontent=same")
        shas.append(jar_sha("projects/lib/build/libs/lib-1.0.0.jar"))
        log(f"  build {i + 1}: {shas[-1]}")
        time.sleep(3)
    log(f"  같은가: {shas[0] == shas[1]}")

    log("\n## Gradle, preserveFileTimestamps=true 로 되돌리면")
    shas = []
    for i in range(2):
        gradle("gradle-ci", "lib", "clean jar -Pver=1.0.0 -Pcontent=same -PkeepTimestamps")
        shas.append(jar_sha("projects/lib/build/libs/lib-1.0.0.jar"))
        log(f"  build {i + 1}: {shas[-1]}")
        time.sleep(3)
    log(f"  같은가: {shas[0] == shas[1]}")

    log("\n## Maven 3.10.0 jar (기본 설정)")
    shas = []
    for i in range(2):
        maven("maven-b", "maven-lib", "clean package")
        shas.append(jar_sha("projects/maven-lib/target/maven-lib-1.0.0.jar"))
        log(f"  build {i + 1}: {shas[-1]}")
        time.sleep(3)
    log(f"  같은가: {shas[0] == shas[1]}")

    log("\n## Maven, project.build.outputTimestamp=x (재현 가능 빌드 끔)")
    shas = []
    for i in range(2):
        maven("maven-b", "maven-lib", "clean package -Dproject.build.outputTimestamp=x")
        shas.append(jar_sha("projects/maven-lib/target/maven-lib-1.0.0.jar"))
        log(f"  build {i + 1}: {shas[-1]}")
        time.sleep(3)
    log(f"  같은가: {shas[0] == shas[1]}")

    log("\n## 컨테이너 이미지: 같은 Dockerfile 을 캐시 없이 두 번")
    ids = []
    for i in range(2):
        _, out = sh("docker build -q --no-cache --build-arg CONTENT=same projects/image")
        ids.append(out.strip().splitlines()[-1])
        log(f"  build {i + 1}: {ids[-1]}")
        time.sleep(3)
    log(f"  같은가: {ids[0] == ids[1]}")

    log("\n## 컨테이너 이미지: SOURCE_DATE_EPOCH 와 rewrite-timestamp")
    ids = []
    for i in range(2):
        tag = f"{REG}/lab/repro:{i + 1}"
        sh(f"docker buildx build -q --no-cache --build-arg SOURCE_DATE_EPOCH=0 --build-arg CONTENT=same "
           f"--output type=registry,name={tag},rewrite-timestamp=true,registry.insecure=true projects/image",
           check=False)
        try:
            ids.append(digest("lab/repro", str(i + 1)))
        except Exception as e:
            ids.append(f"(실패: {e})")
        log(f"  build {i + 1}: {ids[-1]}")
        time.sleep(3)
    log(f"  같은가: {ids[0] == ids[1]}")

    log("\n## 컨테이너 이미지: 위와 같고 --provenance=false (buildx 기본 출처 증명 첨부를 끔)")
    ids = []
    for i in range(2):
        tag = f"{REG}/lab/repro:np{i + 1}"
        sh(f"docker buildx build -q --no-cache --provenance=false --build-arg SOURCE_DATE_EPOCH=0 "
           f"--build-arg CONTENT=same "
           f"--output type=registry,name={tag},rewrite-timestamp=true,registry.insecure=true projects/image",
           check=False)
        ids.append(digest("lab/repro", f"np{i + 1}"))
        log(f"  build {i + 1}: {ids[-1]}")
        time.sleep(3)
    log(f"  같은가: {ids[0] == ids[1]}")


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
    if name not in ("up", "down"):
        _log = open(os.path.join(RESULTS, name + ".txt"), "w", encoding="utf-8")
    fn()
    log(f"\n(총 {time.time() - _t0:.0f}초)")


if __name__ == "__main__":
    main()
