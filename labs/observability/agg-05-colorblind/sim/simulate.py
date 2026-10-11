"""캡처한 대시보드 이미지에 색각 이상 시뮬레이션을 걸고, 팔레트 색끼리의 색차를 계산한다.

- 2형(deutan), 1형(protan): Machado, Oliveira, Fernandes (2009) 의 심한 정도 1.0 행렬.
  저자 페이지 Table 1 의 값을 그대로 옮겼고, sRGB 를 선형 RGB 로 푼 뒤 곱한다.
- 3형(tritan): Machado 모델은 3형에 잘 맞지 않아서 DaltonLens 의 Brettel(1997) 구현을 쓴다.
- 흑백: 선형 RGB 의 상대 휘도 Y 를 다시 sRGB 로.
- 교차 확인: 직접 곱한 Machado 결과를 DaltonLens 의 Simulator_Machado2009 결과와 픽셀 단위로 비교한다.

사용: ./sim/run.sh  (실습 디렉터리에서. python:3.12-slim 컨테이너에서 돈다)
입력: sim/in/*.png   출력: sim/out/<이름>-<유형>.png, sim/out/<이름>-grid.png, 표준 출력에 색차 표
"""
import glob, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from daltonlens import simulate

MACHADO = {
    "protan": np.array([[0.152286, 1.052583, -0.204868],
                        [0.114503, 0.786281, 0.099216],
                        [-0.003882, -0.048116, 1.051998]]),
    "deutan": np.array([[0.367322, 0.860646, -0.227968],
                        [0.280085, 0.672501, 0.047413],
                        [-0.011820, 0.042940, 0.968881]]),
}


def to_linear(srgb):  # 0~255 -> 0~1 선형
    c = srgb / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def to_srgb(lin):
    c = np.clip(lin, 0, 1)
    return np.round(np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - 0.055) * 255).astype(np.uint8)


def machado(rgb, kind):
    return to_srgb(to_linear(rgb.astype(float)) @ MACHADO[kind].T)


BRETTEL = simulate.Simulator_Brettel1997()
DL_MACHADO = simulate.Simulator_Machado2009()


def tritan(rgb):
    return BRETTEL.simulate_cvd(rgb, simulate.Deficiency.TRITAN, severity=1.0)


def gray(rgb):
    y = to_linear(rgb.astype(float)) @ np.array([0.2126, 0.7152, 0.0722])
    g = to_srgb(y)
    return np.stack([g, g, g], axis=-1)


SIMS = {"deutan": lambda x: machado(x, "deutan"), "protan": lambda x: machado(x, "protan"),
        "tritan": tritan, "gray": gray}
LABEL = {"normal": "normal", "deutan": "deutan (Machado 1.0)", "protan": "protan (Machado 1.0)",
         "tritan": "tritan (Brettel 1997)", "gray": "grayscale"}


def labeled(img, text):
    font = ImageFont.load_default(size=36)
    out = Image.new("RGB", (img.width, img.height + 56), "white")
    out.paste(img, (0, 56))
    ImageDraw.Draw(out).text((16, 8), text, fill=(40, 40, 40), font=font)
    return out


def grid(tiles, cols=2):
    w, h = tiles[0].size
    rows = (len(tiles) + cols - 1) // cols
    g = Image.new("RGB", (w * cols + 24 * (cols - 1), h * rows + 24 * (rows - 1)), "white")
    for i, t in enumerate(tiles):
        g.paste(t, ((i % cols) * (w + 24), (i // cols) * (h + 24)))
    return g


def lab(hexes):
    rgb = np.array([[int(h[i:i + 2], 16) for i in (1, 3, 5)] for h in hexes], dtype=float)
    lin = to_linear(rgb)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = lin @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[:, 1] - 16, 500 * (f[:, 0] - f[:, 1]), 200 * (f[:, 1] - f[:, 2])], axis=1)


def sim_hex(h, kind):
    px = np.array([[[int(h[i:i + 2], 16) for i in (1, 3, 5)]]], dtype=np.uint8)
    out = SIMS[kind](px)[0, 0]
    return "#%02X%02X%02X" % tuple(int(v) for v in out)


def delta_e(a, b):
    la, lb = lab([a, b])
    return float(np.linalg.norm(la - lb))


def palette_report():
    # 그라파나 Classic palette 앞 여섯 이름은 테마마다 hex 가 다르다(createVisualizationColors.ts 의
    # getLightHues / getDarkHues). 이번 캡처는 라이트 테마라 라이트 값이 화면에 찍힌다.
    grafana_light = {"green": "#56A64B", "semi-dark-yellow": "#E0B400", "blue": "#3274D9",
                     "orange": "#FF780A", "red": "#E02F44", "purple": "#A352CC"}
    grafana_dark = {"green": "#73BF69", "semi-dark-yellow": "#F2CC0C", "blue": "#5794F2",
                    "orange": "#FF9830", "red": "#F2495C", "purple": "#B877D9"}
    okabe = {"orange": "#E69F00", "skyblue": "#56B4E9", "bluishgreen": "#009E73", "yellow": "#F0E442",
             "blue": "#0072B2", "vermillion": "#D55E00", "reddishpurple": "#CC79A7"}
    def contrast(a, b):
        ya, yb = (float(to_linear(np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], dtype=float))
                        @ np.array([0.2126, 0.7152, 0.0722])) for h in (a, b))
        hi, lo = max(ya, yb), min(ya, yb)
        return (hi + 0.05) / (lo + 0.05)

    print("[WCAG 대비] 흰 배경 #FFFFFF(라이트 패널) / #181B1F(다크 패널)")
    for title, pal in (("그라파나 라이트", grafana_light), ("그라파나 다크", grafana_dark), ("오카베-이토", okabe)):
        print("  " + title + ": " + ", ".join(f"{n} {h} {contrast(h, '#FFFFFF'):.2f}/{contrast(h, '#181B1F'):.2f}"
                                             for n, h in pal.items()))
    print(f"  그라파나 라이트 green-red 휘도 대비 {contrast(grafana_light['green'], grafana_light['red']):.2f}")

    for title, pal in (("그라파나 Classic palette 라이트 테마 (이번 캡처)", grafana_light),
                       ("그라파나 Classic palette 다크 테마", grafana_dark), ("오카베-이토", okabe)):
        print(f"\n[{title}] 색  정상 / deutan / protan / tritan")
        for n, h in pal.items():
            print(f"  {n:<17}{h}  {sim_hex(h, 'deutan')}  {sim_hex(h, 'protan')}  {sim_hex(h, 'tritan')}")
        names = list(pal)
        rows = []
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a, b = pal[names[i]], pal[names[j]]
                rows.append((min(delta_e(sim_hex(a, k), sim_hex(b, k)) for k in ("deutan", "protan", "tritan")),
                             names[i], names[j], delta_e(a, b),
                             *[delta_e(sim_hex(a, k), sim_hex(b, k)) for k in ("deutan", "protan", "tritan", "gray")]))
        rows.sort()
        print(f"  색차(CIE76) 가장 가까워지는 쌍 5개      정상  deutan  protan  tritan   흑백")
        for r in rows[:5]:
            print(f"  {r[1]+' - '+r[2]:<36}{r[3]:6.1f}{r[4]:8.1f}{r[5]:8.1f}{r[6]:8.1f}{r[7]:7.1f}")


def main():
    os.makedirs("sim/out", exist_ok=True)
    for path in sorted(glob.glob("sim/in/*.png")):
        name = os.path.splitext(os.path.basename(path))[0]
        rgb = np.array(Image.open(path).convert("RGB"))
        tiles = [labeled(Image.fromarray(rgb), LABEL["normal"])]
        for kind, fn in SIMS.items():
            out = fn(rgb)
            Image.fromarray(out).save(f"sim/out/{name}-{kind}.png")
            if kind in ("deutan", "protan"):
                ref = DL_MACHADO.simulate_cvd(rgb, getattr(simulate.Deficiency, kind.upper()), severity=1.0)
                diff = np.abs(out.astype(int) - ref.astype(int))
                print(f"{name} {kind}: DaltonLens Machado 와 채널 차이 최대 {diff.max()}, 평균 {diff.mean():.3f}")
            if kind != "gray":
                tiles.append(labeled(Image.fromarray(out), LABEL[kind]))
        grid(tiles).save(f"sim/out/{name}-grid.png")
    palette_report()


main()
