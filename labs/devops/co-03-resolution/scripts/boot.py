#!/usr/bin/env python3
"""쓰지 않는 starter 가 jar 크기, 기동 시간, 빈 수, 매핑 수를 얼마나 바꾸는지 잰다.

실습 디렉터리에서 ./scripts/lab.sh boot 로 돌린다. 결과는 표준출력과 results/boot-*.json.
변형 넷:
  plain         webmvc + actuator, 코드는 /hello 하나
  plain-unused  위 + data-rest + data-jpa + h2 (코드에서 쓰지 않음)
  audit         webmvc + actuator + data-jpa + h2, 감사 로그 Repository 를 내부에서만 씀
  audit-rest    위 + data-rest (코드에서 쓰지 않음)
"""
import json, os, re, subprocess, sys, time, urllib.request, urllib.error, zipfile

RUNS = int(os.environ.get("RUNS", "4"))   # 첫 회는 디스크 캐시 예열로 보고 따로 표시한다
PORT = 31081
BASE = f"http://localhost:{PORT}"
VARIANTS = [
    ("plain", "plain", ""),
    ("plain-unused", "plain", "-Punused"),
    ("audit", "audit", ""),
    ("audit-rest", "audit", "-Prest"),
]


def sh(cmd, check=True):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and r.returncode != 0:
        print(r.stdout[-3000:], r.stderr[-3000:], file=sys.stderr)
        raise SystemExit(f"failed: {cmd}")
    return r.stdout.strip()


def http(method, path):
    req = urllib.request.Request(BASE + path, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")
    except Exception as e:  # 아직 안 떴다
        return None, str(e)


def build():
    os.makedirs("boot/out", exist_ok=True)
    script = "set -e; cd boot; mvn -q -DskipTests install -N; "
    for name, module, prof in VARIANTS:
        script += (f"mvn -q -DskipTests clean package -pl {module} {prof}; "
                   f"cp {module}/target/{module}-1.0.jar out/{name}.jar; ")
    sh(f'docker compose --profile tools run --rm mvn bash -c "{script}"')


def jar_stats(path):
    with zipfile.ZipFile(path) as z:
        libs = [n for n in z.namelist() if n.startswith("BOOT-INF/lib/") and n.endswith(".jar")]
    return os.path.getsize(path), len(libs), sorted(os.path.basename(l) for l in libs)


def one_run(name):
    cid = sh(f"docker compose --profile boot run -d --service-ports -e JAR=boot/out/{name}.jar boot")
    try:
        t0 = time.time()
        while time.time() - t0 < 120:
            st, body = http("GET", "/actuator/health")
            if st == 200:
                break
            time.sleep(0.3)
        else:
            raise SystemExit(f"{name}: health 가 120초 안에 UP 이 아님\n" + sh(f"docker logs {cid}", False))
        logs = sh(f"docker logs {cid} 2>&1", False)
        m = re.search(r"Started \w+ in ([\d.]+) seconds \(process running for ([\d.]+)\)", logs)
        started, process = (float(m.group(1)), float(m.group(2))) if m else (None, None)
        _, beans_body = http("GET", "/actuator/beans")
        beans = sum(len(c["beans"]) for c in json.loads(beans_body)["contexts"].values())
        _, map_body = http("GET", "/actuator/mappings")
        preds = []
        for ctx in json.loads(map_body)["contexts"].values():
            for lst in ctx["mappings"].get("dispatcherServlets", {}).values():
                preds += [x["predicate"] for x in lst]
        probes = {}
        for method, path in [("GET", "/"), ("GET", "/profile"), ("GET", "/auditLogs"),
                             ("DELETE", "/auditLogs/1"), ("GET", "/auditLogs")]:
            st, body = http(method, path)
            key = f"{method} {path}"
            if key in probes:
                key += " (DELETE 뒤)"
            n = None
            if st == 200 and "auditLogs" in path:
                try:
                    n = len(json.loads(body)["_embedded"]["auditLogs"])
                except Exception:
                    pass
            probes[key] = (st, n)
        return dict(started=started, process=process, beans=beans, mappings=len(preds),
                    predicates=sorted(preds), probes=probes)
    finally:
        sh(f"docker rm -f {cid}", False)


def main():
    if "--no-build" not in sys.argv:
        build()
    summary = {}
    for name, _, _ in VARIANTS:
        size, nlibs, libs = jar_stats(f"boot/out/{name}.jar")
        runs = [one_run(name) for _ in range(RUNS)]
        summary[name] = dict(size=size, nlibs=nlibs, libs=libs, runs=runs)
        with open(f"results/boot-{name}.json", "w") as f:
            json.dump(summary[name], f, ensure_ascii=False, indent=1)
        st = [r["started"] for r in runs]
        print(f"{name:13s} jar={size/1e6:.1f}MB libs={nlibs} beans={runs[-1]['beans']} "
              f"mappings={runs[-1]['mappings']} started(s)={st} (첫 회 제외 범위 {min(st[1:])}~{max(st[1:])})")
        for k, v in runs[-1]["probes"].items():
            print(f"    {k:28s} -> {v[0]}" + (f" 항목 {v[1]}개" if v[1] is not None else ""))
    base, unused = summary["plain"], summary["plain-unused"]
    print("plain-unused 에만 있는 매핑:")
    for p in sorted(set(unused["runs"][-1]["predicates"]) - set(base["runs"][-1]["predicates"])):
        print("   ", p)
    print("audit-rest 에만 있는 매핑:")
    for p in sorted(set(summary["audit-rest"]["runs"][-1]["predicates"]) - set(summary["audit"]["runs"][-1]["predicates"])):
        print("   ", p)


if __name__ == "__main__":
    main()
