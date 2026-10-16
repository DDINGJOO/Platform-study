"""압축한 하루가 끝난 시점에 Prometheus 로 SLI 를 분모별로 다시 계산한다. 표준 라이브러리만.

  python3 prom_sli.py --prom http://localhost:32190 --at <하루가 끝난 unix 초> [--range 24m]

카운터(lab_http_requests_total)는 스택을 다시 띄우지 않으면 하루 전 것까지 누적이라,
increase(...[24m]) 로 그 하루만 잘라 낸다.
"""
import argparse
import json
import urllib.parse
import urllib.request

ap = argparse.ArgumentParser()
ap.add_argument("--prom", default="http://localhost:32190")
ap.add_argument("--at", type=float, required=True)
ap.add_argument("--range", default="24m")
a = ap.parse_args()

M = "lab_http_requests_total"
R = a.range
DEFS = {
    "모든 요청":                f'{M}',
    "헬스체크 제외":             f'{M}{{client!="probe"}}',
    "헬스체크·봇 제외":          f'{M}{{client="user"}}',
    "사용자, API 경로만(기준)":   f'{M}{{client="user",route="/api/checkout"}}',
}


def q(expr):
    url = a.prom + "/api/v1/query?" + urllib.parse.urlencode({"query": expr, "time": a.at})
    r = json.load(urllib.request.urlopen(url))["data"]["result"]
    return float(r[0]["value"][1]) if r else 0.0


for name, sel in DEFS.items():
    bad_sel = sel[:-1] + ',code=~"5.."}' if sel.endswith("}") else sel + '{code=~"5.."}'
    total = q(f"sum(increase({sel}[{R}]))")
    bad = q(f"sum(increase({bad_sel}[{R}]))")
    print(f"{name:20s} 1 - sum(increase({bad_sel}[{R}])) / sum(increase({sel}[{R}]))")
    print(f"{'':20s} = 1 - {bad:.1f} / {total:.1f} = {100 * (1 - bad / total):.4f}%")
