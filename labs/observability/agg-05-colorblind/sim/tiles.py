"""stat 패널의 /api/cart 칸과 /api/checkout 칸 배경색을 같은 상대 위치에서 뽑아 색차를 잰다.
위치는 capture.py --height 800 --top 60 --clip-height 570 으로 찍은 이미지(2배 해상도) 기준이다.
./sim/run.sh 가 simulate.py 다음에 돌린다."""
import numpy as np
from PIL import Image

PTS = {"cart": (60, 395), "checkout": (200, 395)}  # CSS 픽셀 (x, y)


def lab1(rgb):
    from math import cbrt
    def lin(c):
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(v) for v in rgb)
    X = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    Y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    Z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = lambda t: cbrt(t) if t > 0.008856 else 7.787 * t + 16 / 116
    return np.array([116 * f(Y) - 16, 500 * (f(X) - f(Y)), 200 * (f(Y) - f(Z))])


for name in ("before", "before-dark"):
    for kind in ("normal", "deutan", "protan", "tritan", "gray"):
        path = f"sim/in/{name}.png" if kind == "normal" else f"sim/out/{name}-{kind}.png"
        im = np.array(Image.open(path).convert("RGB")).astype(float)
        c = {k: im[y * 2 - 4:y * 2 + 4, x * 2 - 4:x * 2 + 4].reshape(-1, 3).mean(0) for k, (x, y) in PTS.items()}
        de = float(np.linalg.norm(lab1(c["cart"]) - lab1(c["checkout"])))
        hexs = {k: "#%02X%02X%02X" % tuple(int(round(v)) for v in c[k]) for k in c}
        print(f"{name:<12}{kind:<8} cart {hexs['cart']}  checkout {hexs['checkout']}  색차 {de:5.1f}")
