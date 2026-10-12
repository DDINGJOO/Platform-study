"""Alertmanager 웹훅 수신기. 받은 알림을 /out/notifications.jsonl 에 한 줄씩 쌓는다(받은 시각 포함)."""
import json, time
from http.server import BaseHTTPRequestHandler, HTTPServer

class H(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        rec = {"received": time.time(), "status": body["status"],
               "alerts": [{"alertname": a["labels"].get("alertname"), "status": a["status"],
                           "severity": a["labels"].get("severity"),
                           "startsAt": a["startsAt"], "endsAt": a["endsAt"],
                           "summary": a["annotations"].get("summary"),
                           "runbook_url": a["annotations"].get("runbook_url")} for a in body["alerts"]]}
        with open("/out/notifications.jsonl", "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(json.dumps(rec, ensure_ascii=False), flush=True)
        self.send_response(200); self.end_headers()
    def log_message(self, *a):
        pass

HTTPServer(("", 8080), H).serve_forever()
