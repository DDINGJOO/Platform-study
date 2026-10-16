"""Alertmanager 웹훅을 받아 app 을 재시작하는 자동 복구기.
MODE=unbounded  경고 한 건(같은 fingerprint + startsAt)마다 한 번 재시작. 횟수 제한 없음
MODE=capped     같은 일을 하되
                 - WINDOW_S(기본 1800초) 안에서 MAX_ACTIONS(기본 3)번까지만
                 - 직전 조치 뒤 EFFECT_S(기본 600초) 안에 다시 울리면 그 조치를 '효과 없음'으로 센다
                 - 상한에 닿으면 조치를 멈추고 사람을 부른다(escalate 이벤트 한 번)
모든 수신과 판단을 /out/events.jsonl 에 남긴다."""
import json, os, threading, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODE = os.environ.get("MODE", "unbounded")
MAX_ACTIONS = int(os.environ.get("MAX_ACTIONS", "3")); WINDOW_S = float(os.environ.get("WINDOW_S", "1800"))
EFFECT_S = float(os.environ.get("EFFECT_S", "600"))
seen, actions, lock = set(), [], threading.Lock()
escalated = False

def log(**kw):
    kw["t"] = round(time.time(), 3); kw["mode"] = MODE
    with open("/out/events.jsonl", "a") as f:
        f.write(json.dumps(kw, ensure_ascii=False) + "\n")
    print(json.dumps(kw, ensure_ascii=False), flush=True)

def restart():
    try:
        req = urllib.request.Request("http://app:8080/admin/restart", method="POST")
        return urllib.request.urlopen(req, timeout=3).status
    except Exception as e:
        return type(e).__name__

def handle(alert):
    global escalated
    if alert["status"] != "firing" or alert["labels"].get("remediation") != "restart":
        return
    key = (alert["fingerprint"], alert["startsAt"])
    now = time.time()
    with lock:
        if key in seen:
            log(type="skip", reason="이미 처리한 경고(같은 startsAt)", startsAt=alert["startsAt"]); return
        seen.add(key)
        if MODE == "capped":
            if actions and now - actions[-1] < EFFECT_S:
                log(type="no_effect", since_last_action_s=round(now - actions[-1], 1))
            recent = [a for a in actions if now - a < WINDOW_S]
            if len(recent) >= MAX_ACTIONS:
                if not escalated:
                    escalated = True
                    log(type="escalate", reason=f"{WINDOW_S:.0f}초 안에 자동 재시작 {len(recent)}번, 그래도 재발. 사람을 부른다",
                        startsAt=alert["startsAt"])
                else:
                    log(type="skip", reason="상한 도달, 이미 사람을 불렀다", startsAt=alert["startsAt"])
                return
        actions.append(now)
        n = len(actions)
    code = restart()
    log(type="action", n=n, result=code, startsAt=alert["startsAt"])

class H(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        log(type="notification", status=body["status"],
            alerts=[{"status": a["status"], "startsAt": a["startsAt"], "endsAt": a["endsAt"]} for a in body["alerts"]])
        self.send_response(200); self.end_headers()
        for a in body["alerts"]:
            handle(a)
    def log_message(self, *a):
        pass

log(type="start", max_actions=MAX_ACTIONS, window_s=WINDOW_S)
ThreadingHTTPServer(("", 8080), H).serve_forever()
