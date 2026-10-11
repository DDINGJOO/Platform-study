"""대시보드 두 개를 만든다. 같은 쿼리 네 개를 두 가지로 그린다.
  before.json : 그라파나 기본값에 가깝게. 색만으로 선·상태·결과를 나눈다
  after.json  : 같은 데이터를 색 말고도 나눈다(선 모양, 굵기, 범례 표, 임계 영역, 글자)
실행: python3 grafana/make-dashboards.py  (실습 디렉터리에서)"""
import json

DS = {"type": "prometheus", "uid": "prometheus"}
API = 'uri=~"/api/.*"'
ERR = (f'sum by (uri) (rate(http_server_requests_seconds_count{{{API},outcome="SERVER_ERROR"}}[1m]))'
       f' / sum by (uri) (rate(http_server_requests_seconds_count{{{API}}}[1m]))')
P99 = f'histogram_quantile(0.99, sum by (uri, le) (rate(http_server_requests_seconds_bucket{{{API}}}[1m])))'
OUT = f'sum by (outcome) (rate(http_server_requests_seconds_count{{{API}}}[1m]))'
ROUTES = ["/api/checkout", "/api/order", "/api/search", "/api/cart", "/api/login"]
# 오카베-이토 팔레트(R palette.colors 의 값)
OI = {"/api/checkout": "#0072B2", "/api/order": "#E69F00", "/api/search": "#009E73",
      "/api/cart": "#CC79A7", "/api/login": "#56B4E9"}
STYLE = {"/api/checkout": {"fill": "solid"}, "/api/order": {"fill": "dash", "dash": [10, 6]},
         "/api/search": {"fill": "dot", "dash": [0, 6]}, "/api/cart": {"fill": "dash", "dash": [20, 6, 4, 6]},
         "/api/login": {"fill": "dash", "dash": [4, 4]}}


def target(expr, legend, ref="A"):
    return {"refId": ref, "expr": expr, "legendFormat": legend, "datasource": DS}


def panel(pid, kind, title, grid, targets, defaults=None, overrides=None, options=None):
    return {"id": pid, "type": kind, "title": title, "gridPos": grid, "datasource": DS, "targets": targets,
            "fieldConfig": {"defaults": defaults or {}, "overrides": overrides or []}, "options": options or {}}


def by_name(name, props):
    return {"matcher": {"id": "byName", "options": name}, "properties": props}


def thresholds(*steps):
    return {"mode": "absolute", "steps": [{"value": v, "color": c} for v, c in steps]}


def dash(uid, title, panels):
    return {"uid": uid, "title": title, "schemaVersion": 41, "editable": True,
            "time": {"from": "now-10m", "to": "now"}, "panels": panels}


G = lambda x, y, w, h: {"x": x, "y": y, "w": w, "h": h}

# ---------- before: 색만으로 나눈다 ----------
before = dash("cvd-before", "실습-5 기본값 대시보드", [
    panel(1, "timeseries", "엔드포인트별 에러 비율", G(0, 0, 12, 9), [target(ERR, "{{uri}}")],
          {"unit": "percentunit"}),
    panel(2, "timeseries", "엔드포인트별 p99 지연", G(12, 0, 12, 9), [target(P99, "{{uri}}")],
          {"unit": "s"}),
    panel(3, "stat", "SLO 상태 (에러 비율 1% 미만)", G(0, 9, 12, 6), [target(ERR, "{{uri}}")],
          {"unit": "percentunit", "decimals": 1, "color": {"mode": "thresholds"},
           "thresholds": thresholds((None, "green"), (0.01, "red"))},
          options={"colorMode": "background", "textMode": "value_and_name", "graphMode": "none",
                   "reduceOptions": {"calcs": ["lastNotNull"]}}),
    panel(4, "timeseries", "응답 결과 (초당)", G(12, 9, 12, 6), [target(OUT, "{{outcome}}")],
          {"unit": "reqps", "custom": {"stacking": {"mode": "normal"}, "fillOpacity": 70}},
          [by_name("SUCCESS", [{"id": "color", "value": {"mode": "fixed", "fixedColor": "green"}}]),
           by_name("SERVER_ERROR", [{"id": "color", "value": {"mode": "fixed", "fixedColor": "red"}}])]),
])

# ---------- after: 색 말고도 나눈다 ----------
def route_overrides(width_main=3):
    out = []
    for r in ROUTES:
        props = [{"id": "color", "value": {"mode": "fixed", "fixedColor": OI[r]}},
                 {"id": "custom.lineStyle", "value": STYLE[r]},
                 {"id": "custom.lineWidth", "value": width_main if r == "/api/checkout" else 2}]
        out.append(by_name(r, props))
    return out


legend_table = {"legend": {"displayMode": "table", "placement": "right", "calcs": ["lastNotNull", "max"],
                           "sortBy": "Last *", "sortDesc": True}, "tooltip": {"mode": "multi", "sort": "desc"}}
after = dash("cvd-after", "실습-5 고친 대시보드", [
    panel(1, "timeseries", "엔드포인트별 에러 비율 (점선 영역 = SLO 1% 초과)", G(0, 0, 12, 9), [target(ERR, "{{uri}}")],
          {"unit": "percentunit", "custom": {"lineWidth": 2, "thresholdsStyle": {"mode": "dashed+area"}},
           "thresholds": thresholds((None, "transparent"), (0.01, "#D55E00"))},
          route_overrides(), legend_table),
    panel(2, "timeseries", "엔드포인트별 p99 지연 (점선 영역 = 300ms 초과)", G(12, 0, 12, 9), [target(P99, "{{uri}}")],
          {"unit": "s", "custom": {"lineWidth": 2, "thresholdsStyle": {"mode": "dashed+area"}},
           "thresholds": thresholds((None, "transparent"), (0.3, "#D55E00"))},
          route_overrides(), legend_table),
    panel(3, "stat", "SLO 상태 (에러 비율 1% 미만)", G(0, 9, 12, 6), [target(ERR, "{{uri}}")],
          {"unit": "percentunit", "decimals": 1, "color": {"mode": "thresholds"},
           "thresholds": thresholds((None, "#56B4E9"), (0.01, "#D55E00")),
           "mappings": [{"type": "range", "options": {"from": 0, "to": 0.0099999,
                                                       "result": {"text": "✓ 정상"}}},
                        {"type": "range", "options": {"from": 0.01, "to": 1,
                                                       "result": {"text": "✕ 초과"}}}]},
          options={"colorMode": "background", "textMode": "value_and_name", "graphMode": "none",
                   "reduceOptions": {"calcs": ["lastNotNull"]}}),
    panel(4, "timeseries", "응답 결과 (초당, 에러는 오른쪽 축의 점)", G(12, 9, 12, 6), [target(OUT, "{{outcome}}")],
          {"unit": "reqps", "min": 0, "custom": {"fillOpacity": 25}},
          [by_name("SUCCESS", [{"id": "color", "value": {"mode": "fixed", "fixedColor": "#56B4E9"}},
                               {"id": "displayName", "value": "성공 (면)"}]),
           by_name("SERVER_ERROR", [{"id": "color", "value": {"mode": "fixed", "fixedColor": "#D55E00"}},
                                    {"id": "displayName", "value": "에러 (점, 오른쪽 축)"},
                                    {"id": "custom.drawStyle", "value": "points"},
                                    {"id": "custom.pointSize", "value": 9},
                                    {"id": "custom.axisPlacement", "value": "right"},
                                    {"id": "custom.fillOpacity", "value": 0}])]),
])

for name, d in (("before", before), ("after", after)):
    with open(f"grafana/dashboards/{name}.json", "w") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
print("ok")
