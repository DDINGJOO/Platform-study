"""timeline.csv(기본 results/timeline.csv, 실행 원본은 out/) 에 규칙 R1~R4 를 적용한다(1초 = 1분으로 읽는다)."""
import csv, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rules import RULES, increments, episodes, first_true

path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "results", "timeline.csv")
rows = list(csv.DictReader(open(path)))
cnt = [int(r["lock_deadlocks"]) for r in rows]
app = [int(r["app_errors"]) for r in rows]
inc = increments(cnt)
a_dead = sum(inc[:181]); b_dead = sum(inc[181:])
print("표본 %d개 (1초 = 1분, %d분 분량)" % (len(cnt), len(cnt) - 1))
print("lock_deadlocks 증가: 전체 %d  구간A(0~180) %d  구간B(181~) %d   앱 1213 예외 %d" % (sum(inc), a_dead, b_dead, app[-1]))
print()
print("%-44s %8s %8s %12s" % ("규칙", "A 알람", "B 알람", "B 켜진 평가"))
for name, fn in RULES:
    times, states = fn(inc)
    a = [(t, s) for t, s in zip(times, states) if t <= 180]
    b = [(t, s) for t, s in zip(times, states) if t > 180]
    ea = episodes([s for _, s in a])
    # B 는 A 에서 켜진 상태가 이어진 경우를 빼고 새로 켜진 횟수
    eb = episodes([a[-1][1] if a else False] + [s for _, s in b]) - (1 if a and a[-1][1] else 0)
    onb = sum(1 for _, s in b if s)
    print("%-44s %8d %8d %8d/%-4d" % (name, ea, eb, onb, len(b)))
