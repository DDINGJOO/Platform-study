"""1편 계산: 9의 개수별 허용 다운타임을 기간 기준별로 직접 계산한다 (표준 라이브러리만 사용)."""

def fmt(minutes):
    s = round(minutes * 60, 1)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    out = []
    if h: out.append(f"{int(h)}시간")
    if m: out.append(f"{int(m)}분")
    if sec or not out: out.append(f"{sec:g}초")
    return " ".join(out)

periods = [("1일", 1), ("28일", 28), ("30일", 30), ("360일", 360), ("365일", 365)]
targets = [99.0, 99.5, 99.9, 99.95, 99.99, 99.999]
print("목표       " + "  ".join(f"{p:>16}" for p, _ in periods))
for t in targets:
    row = []
    for _, d in periods:
        row.append(fmt(d * 1440 * (1 - t / 100)))
    print(f"{t:<9}  " + "  ".join(f"{r:>16}" for r in row))

print()
print("검산: 99.9% 연간 = 365일", fmt(365 * 1440 * 0.001), "/ 360일", fmt(360 * 1440 * 0.001))
print("검산: 99.9% 월간 = 30일", fmt(30 * 1440 * 0.001), "/ 28일", fmt(28 * 1440 * 0.001), "/ 31일", fmt(31 * 1440 * 0.001))

# 1년에 한 번 300분(5시간) 멈춘 경우를 창 길이별로 본다
for label, d in [("365일 창", 365), ("30일 창", 30), ("28일 창", 28), ("7일 창", 7), ("1일 창", 1)]:
    total = d * 1440
    if total < 300:
        print(f"5시간 장애, {label}: 창보다 장애가 길다 (창 안에서는 0%)")
        continue
    print(f"5시간 장애, {label}: 가용성 {100 * (1 - 300 / total):.3f}%")

# 30일 창과 31일 달력 월: 같은 43.2분 장애
for d in (28, 30, 31):
    print(f"43.2분 장애를 {d}일로 나누면 {100 * (1 - 43.2 / (d * 1440)):.4f}%")
