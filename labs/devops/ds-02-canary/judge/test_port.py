"""Kayenta 테스트 스위트의 기대값과 파이썬 이식본을 대조한다.
사용: python3 test_port.py <kayenta 저장소 경로>
"""
import re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mannwhitney import mann_whitney_u_test, classify

root = sys.argv[1]
mw = open(f"{root}/kayenta-mannwhitney/src/test/scala/com/netflix/kayenta/mannwhitney/MannWhitneySuite.scala").read()
cl = open(f"{root}/kayenta-judge/src/test/scala/com/netflix/kayenta/judge/ClassifierSuite.scala").read()

def arrays(block):
    return {m.group(1): [float(v) for v in re.split(r"[,\s]+", m.group(2).strip()) if v]
            for m in re.finditer(r"val (\w+) = Array\(([^)]*)\)", block)}

def tests(src):
    parts = re.split(r'\n  test\("', src)[1:]
    return {p.split('"')[0]: p for p in parts}

ok = fail = 0
for name, body in tests(mw).items():
    a = arrays(body)
    exp = re.findall(r"val r(CiLow|CiHigh|Est) = ([-\d.E]+)", body)
    if "experimentData" in a:
        x, y = a["experimentData"], a["controlData"]
    elif "experiment" in a and "control" in a:
        x, y = a["experiment"], a["control"]
    else:
        continue
    conf = 0.98 if "confidenceLevel = 0.98" in body else 0.95
    lo, hi, est = mann_whitney_u_test(x, y, conf)
    if exp:
        want = dict(exp)
        good = abs(lo - float(want["CiLow"])) < 1e-6 and abs(hi - float(want["CiHigh"])) < 1e-6 and abs(est - float(want["Est"])) < 1e-4
    else:
        nums = [float(v) for v in re.findall(r"assertEquals\(([-\d.E]+), result", body)]
        good = abs(lo - nums[0]) < 1e-6 and abs(hi - nums[1]) < 1e-6 and abs(est - nums[2]) < 1e-6
    print(("OK  " if good else "FAIL"), name, round(lo, 6), round(hi, 6), round(est, 6))
    ok += good; fail += not good

for name, body in tests(cl).items():
    a = arrays(body)
    if "experimentData" not in a:
        continue
    m = re.search(r"new MannWhitneyClassifier\((.*)\)\s*\n", body)
    if not m:
        continue
    args = m.group(1)
    tol = float(re.search(r"tolerance = ([\d.]+)", args).group(1))
    conf = float(re.search(r"confLevel = ([\d.]+)", args).group(1))
    es = re.search(r"effectSizeThresholds = \(([\d.]+), ([\d.]+)\)", args)
    if "cles" in args or "criticalThresholds" in args or "isCriticalMetric" in body or "true)" in body:
        continue  # CLES 와 critical 경로는 이식하지 않았다
    lo_t, hi_t = (float(es.group(1)), float(es.group(2))) if es else (1.0, 1.0)
    d = re.search(r"MetricDirection\.(\w+)", body).group(1).lower()
    want = re.search(r"result\.classification == (\w+)", body).group(1)
    got = classify(a["controlData"], a["experimentData"], d, tol, conf, hi_t, lo_t)["classification"]
    good = got == want
    print(("OK  " if good else "FAIL"), name, "want", want, "got", got)
    ok += good; fail += not good
print("ok", ok, "fail", fail)
