"""year.py 를 시드 1~N 으로 돌려 창마다 판정이 갈리는 빈도를 센다."""
import json, subprocess, sys, collections, os
N = int(sys.argv[1]) if len(sys.argv) > 1 else 200
rows = []
for s in range(1, N + 1):
    subprocess.run([sys.executable, "calc/year.py", str(s)], capture_output=True, check=True)
    r = json.load(open(f"out/year-seed{s}.json"))
    os.remove(f"out/year-seed{s}.json")
    rows.append({"seed": s,
                 "calendar": sum(m["violated"] for m in r["calendar"]),
                 "r28": len(r["rolling28"]["episodes"]), "r30": len(r["rolling30"]["episodes"]),
                 "r28_days": r["rolling28"]["violation_days"], "r30_days": r["rolling30"]["violation_days"],
                 "year": r["year"]["violated"], "avail": r["year"]["availability_pct"]})
def n(f): return sum(1 for x in rows if f(x))
print(f"합성 1년 {N}개 (시드 1~{N})")
print("365일 판정 위반한 해:", n(lambda x: x["year"]))
print("달력 월 위반이 1번 이상인 해:", n(lambda x: x["calendar"] > 0))
print("28일 롤링 위반이 1번 이상인 해:", n(lambda x: x["r28"] > 0))
print("30일 롤링 위반이 1번 이상인 해:", n(lambda x: x["r30"] > 0))
print("달력 월은 0번인데 28일 롤링은 위반한 해:", n(lambda x: x["calendar"] == 0 and x["r28"] > 0))
print("달력 월은 0번인데 30일 롤링은 위반한 해:", n(lambda x: x["calendar"] == 0 and x["r30"] > 0))
print("세 판정(달력·28·30)의 위반 횟수가 모두 같은 해:", n(lambda x: x["calendar"] == x["r28"] == x["r30"]))
print("위반 횟수 합계  달력 %d / 28일 %d / 30일 %d" % (sum(x["calendar"] for x in rows), sum(x["r28"] for x in rows), sum(x["r30"] for x in rows)))
print("위반 상태였던 날 합계  28일 %d / 30일 %d" % (sum(x["r28_days"] for x in rows), sum(x["r30_days"] for x in rows)))
av = sorted(x["avail"] for x in rows)
print("연 가용성 최소 %.4f%%, 중앙 %.4f%%, 최대 %.4f%%" % (av[0], av[len(av)//2], av[-1]))
json.dump(rows, open("out/year-many.json", "w"), indent=0)
