"""Alertmanager 웹훅을 받아 한 건(=사람에게 간 알림 한 통)마다 JSON 한 줄을 남기는 수신기.

경로가 수신자 이름이다: /page(사람을 깨운다), /ticket(업무 시간에 본다), /log(기록만), /human(라우팅 없는 기본 수신자).
받은 시각은 유닉스 시각으로 적는다. 요약 스크립트가 주입 시각을 빼서 상대 시간으로 바꾼다.
"""
import json, os, time
from http.server import BaseHTTPRequestHandler, HTTPServer

OUT = os.environ.get("OUT", "/results/raw/notifications.jsonl")


class H(BaseHTTPRequestHandler):
    def do_POST(self):
        now = time.time()
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        alerts = body.get("alerts", [])
        rec = {
            "recv": round(now, 3),
            "receiver": self.path.strip("/"),
            "status": body.get("status"),
            "groupKey": body.get("groupKey"),
            "groupLabels": body.get("groupLabels"),
            "truncatedAlerts": body.get("truncatedAlerts", 0),
            "firing": sum(1 for a in alerts if a["status"] == "firing"),
            "resolved": sum(1 for a in alerts if a["status"] == "resolved"),
            "alerts": [
                {
                    "name": a["labels"].get("alertname"),
                    "instance": a["labels"].get("instance", ""),
                    "severity": a["labels"].get("severity"),
                    "status": a["status"],
                    "startsAt": a["startsAt"],
                    "runbook_url": a.get("annotations", {}).get("runbook_url"),
                    "summary": a.get("annotations", {}).get("summary"),
                }
                for a in alerts
            ],
            "commonAnnotations": body.get("commonAnnotations", {}),
            "externalURL": body.get("externalURL"),
        }
        with open(OUT, "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"{time.strftime('%H:%M:%S')} /{rec['receiver']:6} {rec['status']:8} "
              f"firing={rec['firing']} resolved={rec['resolved']} group={rec['groupLabels']}", flush=True)
        self.send_response(200)
        self.end_headers()

    def log_message(self, *a):
        pass


print(f"webhook receiver on :8080 -> {OUT}", flush=True)
HTTPServer(("", 8080), H).serve_forever()
