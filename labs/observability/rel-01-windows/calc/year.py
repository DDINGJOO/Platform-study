"""실습-1 3절: 합성 1년 장애 기록을 네 가지 창으로 판정한다 (표준 라이브러리만).

- 2025년(평년) 365일, 하루 단위로 '나쁜 분'(다운타임 분)을 쌓는다.
- 장애는 시드 고정 난수로 만든다: 하루마다 발생 확률 p_day, 길이는 로그정규(중앙값 MEDIAN분).
- SLO: 시간 기준 99.9%. 창 길이 L일이면 허용 다운타임 = L*1440*0.001 분.
- 판정
  달력 월: 각 달이 끝난 날 한 번 판정 (12번)
  롤링 28/30일: 매일 자정에 직전 L일을 판정. 위반 '구간'(연속 위반 일)의 개수와 시작일을 센다.
    첫 L-1일은 창이 덜 찼으므로 판정하지 않는다(1월 1일 이전 기록이 없다고 가정).
  365일: 연말에 한 번
"""
import datetime as dt, math, random, sys, json

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 7
P_DAY = 0.05        # 하루에 장애가 날 확률 (연 평균 약 18건)
MEDIAN = 6.0        # 장애 길이 중앙값(분)
SIGMA = 1.0         # 로그정규 모양

rnd = random.Random(SEED)
start = dt.date(2025, 1, 1)
days = [start + dt.timedelta(i) for i in range(365)]
bad = [0.0] * 365
incidents = []
for i in range(365):
    if rnd.random() < P_DAY:
        m = round(rnd.lognormvariate(math.log(MEDIAN), SIGMA), 1)
        bad[i] += m
        incidents.append((days[i].isoformat(), m))

SLO = 0.999

def budget(ndays):
    return ndays * 1440 * (1 - SLO)

res = {"seed": SEED, "incidents": incidents, "total_bad_min": round(sum(bad), 1)}

# 달력 월
months = []
for mth in range(1, 13):
    idx = [i for i, d in enumerate(days) if d.month == mth]
    b = sum(bad[i] for i in idx)
    cum, hit = 0.0, None
    for i in idx:
        cum += bad[i]
        if hit is None and cum > budget(len(idx)):
            hit = days[i].isoformat()
    months.append({"month": mth, "days": len(idx), "bad_min": round(b, 1),
                   "budget_min": round(budget(len(idx)), 2), "violated": b > budget(len(idx)),
                   "exceeded_on": hit})
res["calendar"] = months

def rolling(L):
    states = []
    for i in range(L - 1, 365):
        b = sum(bad[i - L + 1:i + 1])
        states.append((days[i], b > budget(L), b))
    episodes, prev = [], False
    for d, v, b in states:
        if v and not prev:
            episodes.append({"start": d.isoformat(), "days": 0})
        if v:
            episodes[-1]["days"] += 1
        prev = v
    return {"window": L, "judged_days": len(states), "violation_days": sum(1 for s in states if s[1]),
            "episodes": episodes}

res["rolling28"] = rolling(28)
res["rolling30"] = rolling(30)
res["year"] = {"bad_min": round(sum(bad), 1), "budget_min": round(budget(365), 1),
               "availability_pct": round(100 * (1 - sum(bad) / (365 * 1440)), 4),
               "violated": sum(bad) > budget(365)}

print(f"seed={SEED} 장애 {len(incidents)}건, 다운타임 합 {sum(bad):.1f}분")
print("장애 목록:", ", ".join(f"{d}({m}분)" for d, m in incidents))
print("\n[달력 월] 위반", sum(m["violated"] for m in months), "번")
for m in months:
    print(f"  {m['month']:2d}월 {m['days']}일  다운타임 {m['bad_min']:6.1f}분 / 허용 {m['budget_min']:5.2f}분  {'위반 (예산 초과일 ' + m['exceeded_on'] + ')' if m['violated'] else ''}")
for key in ("rolling28", "rolling30"):
    r = res[key]
    print(f"\n[{r['window']}일 롤링] 판정 {r['judged_days']}일 중 위반 {r['violation_days']}일, 위반 구간 {len(r['episodes'])}개")
    for e in r["episodes"]:
        print(f"  {e['start']} 부터 {e['days']}일")
y = res["year"]
print(f"\n[365일] 다운타임 {y['bad_min']}분 / 허용 {y['budget_min']}분, 가용성 {y['availability_pct']}%  {'위반' if y['violated'] else '지킴'}")
json.dump(res, open(f"out/year-seed{SEED}.json", "w"), ensure_ascii=False, indent=1)
