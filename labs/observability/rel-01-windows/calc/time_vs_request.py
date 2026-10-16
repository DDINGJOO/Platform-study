"""1편 계산: 같은 하루에 장애를 어느 시각에 넣느냐에 따라 시간 기준과 요청 기준 가용성이 어떻게 갈리나."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loadgen"))
from curve import ratio

STEP = 1 / 60  # 1분 단위 적분
def requests(h0, h1):
    n = int(round((h1 - h0) / STEP))
    return sum(ratio(h0 + (k + 0.5) * STEP) for k in range(n)) * STEP

day = requests(0, 24)
print(f"하루 요청량(피크 1시간 = 1.00 단위): {day:.3f}, 하루 평균/피크 = {day/24:.3f}")
for name, h0, h1 in [("새벽 1시~2시, 60분", 1, 2), ("새벽 3시~4시, 60분", 3, 4), ("오후 2시~2시 10분, 10분", 14, 14 + 10/60),
                     ("오후 2시~3시, 60분", 14, 15)]:
    lost = requests(h0, h1)
    t = 100 * (1 - (h1 - h0) / 24)
    r = 100 * (1 - lost / day)
    print(f"{name:24s} 시간 기준 {t:7.3f}%   요청 기준 {r:7.3f}%   잃은 요청 비율 {100*lost/day:.3f}%")
