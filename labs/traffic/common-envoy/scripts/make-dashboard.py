"""실습 대시보드 JSON 을 만든다. 패널 정의는 실습 디렉터리의 dashboard.py 에 있다.
사용: python3 make-dashboard.py <실습 디렉터리>   → <실습 디렉터리>/grafana/lab.json"""
import json, runpy, sys, os

d = sys.argv[1]
spec = runpy.run_path(os.path.join(d, "dashboard.py"))
panels = []
for i, p in enumerate(spec["PANELS"]):
    panels.append({
        "id": i + 1, "type": "timeseries", "title": p["title"],
        "gridPos": {"x": 0, "y": i * 8, "w": 24, "h": 8},
        "datasource": {"type": "prometheus", "uid": "prometheus"},
        "fieldConfig": {"defaults": {"unit": p.get("unit", "short"), "min": 0,
                                     **({"max": p["max"]} if "max" in p else {}),
                                     "custom": {"lineWidth": 2, "showPoints": "never",
                                                "drawStyle": p.get("draw", "line"),
                                                "lineInterpolation": "stepAfter" if p.get("step") else "linear"}},
                        "overrides": []},
        "options": {"legend": {"displayMode": "list", "placement": "bottom"}, "tooltip": {"mode": "multi"}},
        "targets": [{"refId": chr(65 + j), "expr": e, "legendFormat": lg,
                     "datasource": {"type": "prometheus", "uid": "prometheus"}}
                    for j, (e, lg) in enumerate(p["targets"])],
    })
dash = {"uid": spec["UID"], "title": spec["TITLE"], "schemaVersion": 41, "refresh": "5s",
        "time": {"from": "now-15m", "to": "now"}, "timezone": "browser", "panels": panels}
os.makedirs(os.path.join(d, "grafana"), exist_ok=True)
json.dump(dash, open(os.path.join(d, "grafana", "lab.json"), "w"), ensure_ascii=False, indent=2)
print(os.path.join(d, "grafana", "lab.json"))
