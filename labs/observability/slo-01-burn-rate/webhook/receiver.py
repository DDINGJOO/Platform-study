"""Alertmanager webhook 을 받아 받은 시각과 요지를 한 줄씩 찍는 수신기. 표준 라이브러리만 쓴다."""
import json, sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

class H(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        now = datetime.now(timezone.utc).strftime("%H:%M:%S")
        for a in body["alerts"]:
            print(f"{now} {self.path:8} {body['status']:9} {a['labels'].get('alertname')} "
                  f"severity={a['labels'].get('severity')} startsAt={a['startsAt'][11:19]} "
                  f"endsAt={a['endsAt'][11:19] if a['status']=='resolved' else '-'}", flush=True)
        self.send_response(200); self.end_headers()
    def log_message(self, *a):
        pass

print("webhook receiver on :8080", flush=True)
HTTPServer(("", 8080), H).serve_forever()
