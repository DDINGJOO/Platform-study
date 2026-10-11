"""Argo Rollouts 의 web 지표 공급자가 부르는 카나리 판정 서버.

GET /judge?control=<해시>&experiment=<해시>[&window=300][&step=10][&end=<유닉스초>][&label=...]

  control, experiment  파드의 rollouts-pod-template-hash 값(프로메테우스 라벨 hash)
  window               판정에 쓸 구간(초). 기본 300
  step                 표본 하나의 간격(초). 기본 10. 구간/간격 = 표본 수
  end                  구간의 끝. 기본은 지금

지표마다 두 집단의 시계열을 프로메테우스 query_range 로 가져와(간격마다 값 하나),
Kayenta 와 같은 방식으로 Mann-Whitney 분류를 하고 그룹 가중 점수를 낸다.
"""
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mannwhitney import classify, score  # noqa: E402

PROM = os.environ.get("PROM_URL", "http://prometheus:9090")
RATE_WINDOW = os.environ.get("RATE_WINDOW", "30s")

# Kayenta 의 canary config 에 해당하는 부분. {h} 자리에 해시가 들어간다
METRICS = [
    {
        "name": "error_ratio", "group": "errors", "direction": "increase", "critical": True,
        # 500 이 한 번도 없으면 분자 시계열이 아예 없어서 NaN(=Nodata) 이 된다. 0 으로 채운다
        "query": '(sum(rate(demo_requests_total{{hash="{h}",code="500"}}[{w}])) '
                 'or sum(rate(demo_requests_total{{hash="{h}"}}[{w}])) * 0) '
                 '/ sum(rate(demo_requests_total{{hash="{h}"}}[{w}]))',
    },
    {
        "name": "latency_mean_ok", "group": "latency", "direction": "increase",
        "query": 'sum(rate(demo_request_seconds_sum{{hash="{h}",code="200"}}[{w}])) '
                 '/ sum(rate(demo_request_seconds_count{{hash="{h}",code="200"}}[{w}]))',
    },
    {
        "name": "latency_p99_ok", "group": "latency", "direction": "increase",
        "query": 'histogram_quantile(0.99, sum by (le) '
                 '(rate(demo_request_seconds_bucket{{hash="{h}",code="200"}}[{w}])))',
    },
]


def series(query, start, end, step):
    qs = urllib.parse.urlencode({"query": query, "start": start, "end": end, "step": step})
    with urllib.request.urlopen(f"{PROM}/api/v1/query_range?{qs}", timeout=10) as r:
        data = json.load(r)["data"]["result"]
    if not data:
        return []
    out = []
    for _, v in data[0]["values"]:
        f = float(v)
        out.append(f if math.isfinite(f) else float("nan"))
    return out


def judge(control, experiment, window=300, step=10, end=None, pass_t=95, marginal_t=75):
    end = float(end or time.time())
    start = end - window
    # 집계 창은 step 과 같게(최소 RATE_WINDOW). step 이 창보다 길면 점 사이 요청을 버리게 된다
    w = f"{max(step, int(RATE_WINDOW.rstrip('s')))}s"
    results = []
    for m in METRICS:
        q = m["query"]
        c = series(q.format(h=control, w=w), start, end, step)
        e = series(q.format(h=experiment, w=w), start, end, step)
        r = classify(c, e, m["direction"], critical=m.get("critical", False))
        r.update(name=m["name"], group=m["group"])
        cm = [v for v in c if not math.isnan(v)]
        em = [v for v in e if not math.isnan(v)]
        r["control_mean"] = sum(cm) / len(cm) if cm else None
        r["experiment_mean"] = sum(em) / len(em) if em else None
        results.append(r)
    s, reason = score(results)
    verdict = "Pass" if s >= pass_t else ("Marginal" if s >= marginal_t else "Fail")
    return {"score": s, "verdict": verdict, "reason": reason, "control": control, "rate_window": w,
            "experiment": experiment, "window": window, "step": step, "end": end,
            "metrics": results}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path != "/judge":
            self.send_response(404)
            self.end_headers()
            return
        q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        try:
            res = judge(q["control"], q["experiment"], int(q.get("window", 300)),
                        int(q.get("step", 10)), q.get("end"))
            res["label"] = q.get("label", "")
            code = 200
        except Exception as ex:  # 판정 실패는 Argo 쪽에서 Error 로 보이게 둔다
            res, code = {"error": str(ex)}, 500
        body = json.dumps(res, default=lambda o: None if isinstance(o, float) and math.isnan(o) else o)
        body = body.replace("NaN", "null")
        print(json.dumps({"t": time.time(), **({"label": q.get("label", "")}),
                          "score": res.get("score"), "verdict": res.get("verdict"),
                          "metrics": [(m["name"], m["classification"], m.get("n_control"),
                                       m.get("n_experiment"), m.get("control_mean"),
                                       m.get("experiment_mean")) for m in res.get("metrics", [])]},
                         default=str), flush=True)
        b = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
