#!/usr/bin/env python3
"""C 시나리오에서 HighErrorRate 첫 알림이 group_wait(30초)가 아니라 264초 뒤에 온 이유를 따로 재 본다.

가설: 앞 시나리오에서 풀린 같은 라벨의 경고를 Prometheus 가 15분 동안(resolvedRetention) 1분마다 다시 보내고,
그 resolved 경고가 Alertmanager 안에 묶음을 먼저 만들어 둔다. 새 장애의 firing 경고는 그 묶음에 붙어서
group_wait 가 아니라 묶음의 다음 group_interval 차례에 나간다.

Docker 없이 Alertmanager 바이너리 하나와 이 스크립트만으로 돈다. Prometheus 대신 이 스크립트가 API 로 경고를 넣는다.

    N=10 GAP=36 GI=5m python3 scripts/stale_group.py <alertmanager 바이너리 경로>

  N   한 요청에 담는 경고 수(기본 10)
  GAP 마지막 resolved 재전송과 firing 사이 간격 초(기본 60)
  GI  group_interval(기본 2m). group_wait 는 30s 고정

두 경우를 차례로 돌린다(각각 Alertmanager 를 새로 띄운다).
  control : 처음 보는 경고를 firing 으로 넣는다
  stale   : 같은 라벨의 경고를 "8분 전에 풀림" 으로 1분마다 넣은 뒤, 같은 라벨로 firing 을 넣는다
결과는 results/stale-group-n<N>-gap<GAP>-gi<GI>.txt (시각은 firing 을 처음 넣은 순간 기준).
"""
import json, os, subprocess, sys, tempfile, threading, time, urllib.request
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AM_PORT, HOOK_PORT = 27094, 27081
AM = f"http://127.0.0.1:{AM_PORT}"
CONFIG = lambda: f"""route:
  receiver: human
  group_by: [alertname]
  group_wait: 30s
  group_interval: {GI}
  repeat_interval: 4h
receivers:
  - name: human
    webhook_configs:
      - url: http://127.0.0.1:{HOOK_PORT}/human
"""
N = int(os.environ.get("N", "10"))
GAP = int(os.environ.get("GAP", "60"))
GI = os.environ.get("GI", "2m")          # group_interval   # 마지막 resolved 재전송과 firing 사이 간격(초). C 에서는 약 36초였다   # 실습처럼 인스턴스 10개 경고를 한 요청에 담아 보낸다
LABELS = [{"alertname": "HighErrorRate", "instance": f"app-{i}:8080", "env": "lab"} for i in range(1, N + 1)]
received = []


class Hook(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        received.append((time.time(), body["status"], len(body["alerts"])))
        self.send_response(200); self.end_headers()

    def log_message(self, *a):
        pass


def iso(t):
    return t.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def post(starts, ends):
    data = json.dumps([{"labels": l, "annotations": {"summary": "lab"},
                        "startsAt": iso(starts), "endsAt": iso(ends)} for l in LABELS]).encode()
    req = urllib.request.Request(AM + "/api/v2/alerts", data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=5).read()


def groups():
    with urllib.request.urlopen(AM + "/api/v2/alerts/groups?active=true&silenced=true&inhibited=true", timeout=5) as r:
        return len(json.loads(r.read()))


def run_case(binary, case, out):
    received.clear()
    d = tempfile.mkdtemp()
    open(os.path.join(d, "am.yml"), "w").write(CONFIG())
    am = subprocess.Popen([binary, f"--config.file={d}/am.yml", f"--storage.path={d}/data",
                           f"--web.listen-address=127.0.0.1:{AM_PORT}", "--cluster.listen-address="],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                urllib.request.urlopen(AM + "/-/ready", timeout=1); break
            except Exception:
                time.sleep(0.2)
        log = []
        if case == "stale":
            # Prometheus 처럼: 풀린 경고를 1분마다 다시 보낸다. 시작 10분 전에 울렸고 8분 전에 풀렸다
            start = time.time()
            now = datetime.now(timezone.utc)
            while time.time() - start < 181:
                post(now - timedelta(minutes=10), now - timedelta(minutes=8))
                log.append((time.time(), "resolved 다시 보냄", groups()))
                time.sleep(1)
                log.append((time.time(), "  1초 뒤", groups()))
                time.sleep(59 if time.time() - start < 180 else GAP - 1)
        t0 = time.time()
        first = datetime.now(timezone.utc)
        # 이제 같은 라벨로 새 장애. Prometheus 처럼 1분마다 endsAt 을 앞으로 밀며 보낸다
        while time.time() - t0 < 400:
            post(first, datetime.now(timezone.utc) + timedelta(minutes=4))
            log.append((time.time(), "firing 보냄", groups()))
            if received and received[-1][1] == "firing" and received[-1][0] >= t0:
                break
            time.sleep(10)
        out.append(f"[{case}]")
        for t, what, g in log:
            out.append(f"  {t - t0:7.1f}s  {what:12}  그때 Alertmanager 의 묶음 수 {g}")
        for t, status, n in received:
            out.append(f"  {t - t0:7.1f}s  알림 받음: {status}, 경고 {n}개")
        firing = [t for t, s, _ in received if s == "firing" and t >= t0]
        out.append(f"  => firing 을 넣고 첫 알림까지 {firing[0] - t0:.1f}초" if firing else "  => 400초 안에 알림 없음")
    finally:
        am.terminate(); am.wait()


def main():
    binary = sys.argv[1]
    srv = HTTPServer(("127.0.0.1", HOOK_PORT), Hook)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    out = [f"경고 {N}개를 한 요청에 담아 보냄, 마지막 resolved 재전송 {GAP}초 뒤 firing. 앞 장애에서 풀린 경고가 새 장애의 첫 알림을 늦추는지 (Alertmanager 0.34.1, group_wait 30s, group_interval {GI})",
           "시각은 각 경우에서 firing 경고를 처음 넣은 순간 기준. 묶음 수는 /api/v2/alerts/groups 가 돌려준 묶음 개수", ""]
    for case in ("control", "stale"):
        run_case(binary, case, out)
        out.append("")
    text = "\n".join(out) + "\n"
    open(os.path.join(HERE, "results", f"stale-group-n{N}-gap{GAP}-gi{GI}.txt"), "w").write(text)
    print(text)


if __name__ == "__main__":
    main()
