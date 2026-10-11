# 집계와 분포 실습-5: 같은 대시보드를 색각 이상의 눈으로 본다

엔드포인트 다섯 개(`/api/checkout`, `order`, `search`, `cart`, `login`)를 가진 앱 하나에 k6 로 초당 50건을 8분 동안 주고,
3분째에 `checkout` 의 에러율과 지연을 올린다. 같은 쿼리 네 개를 두 대시보드로 그린다.

| 대시보드 | 무엇을 바꿨나 |
|---|---|
| `before` (「실습-5 기본값 대시보드」) | 그라파나 기본값. Classic palette, 선 굵기 1, 범례 목록, stat 패널 초록/빨강, 성공·에러 누적 면 초록/빨강 |
| `after` (「실습-5 고친 대시보드」) | 오카베-이토 색 + 선 모양(실선·파선·점선) + 범례 표(마지막 값 내림차순), 임계값을 점선 + 영역으로, stat 패널은 파랑/주홍 + "✓ 정상" "✕ 초과" 글자, 에러는 오른쪽 축의 점 |

대시보드 JSON 은 `grafana/make-dashboards.py` 가 만든다. 캡처한 이미지에 `sim/simulate.py` 가 색각 이상 시뮬레이션을 건다.

## 돌리기

```bash
cd labs/observability/agg-05-colorblind
docker compose up -d --build
date +%s > out/start.txt
docker compose --profile load run --rm load > out/k6.log 2>&1 &     # 초당 50건, 8분
sleep 180
curl -X POST "localhost:21081/admin/route?name=checkout&err=0.05&base=200"   # 장애 주입: 에러 5%, 지연 200~400ms
sleep 300; date +%s > out/end.txt

# 캡처 (저장소 루트에서. Playwright 와 시스템 Chrome 필요)
F=$(( $(cat labs/observability/agg-05-colorblind/out/start.txt) + 60 ))000; T=$(cat labs/observability/agg-05-colorblind/out/end.txt)000
for d in before after; do
  python labs/observability/scripts/capture.py labs/observability/agg-05-colorblind/sim/in/$d.png \
    "http://localhost:21000/d/cvd-$d?orgId=1&from=$F&to=$T&kiosk" --wait 8 --height 800 --top 60 --clip-height 570
done
python labs/observability/scripts/capture.py labs/observability/agg-05-colorblind/sim/in/before-dark.png \
  "http://localhost:21000/d/cvd-before?orgId=1&from=$F&to=$T&kiosk&theme=dark" --wait 8 --height 800 --top 60 --clip-height 570

# 시뮬레이션 (실습 디렉터리에서)
./sim/run.sh                  # sim/out/<이름>-{deutan,protan,tritan,gray,grid}.png, 표준 출력에 색차 표
docker compose --profile load down -v
```

- Grafana http://localhost:21000 , Prometheus http://localhost:21090 , 앱 http://localhost:21081
- 포트는 `GRAFANA_PORT`, `PROM_PORT`, `APP_PORT` 로 바꾼다
- 이번 실행의 숫자: `out/sim.txt`(시뮬레이션 교차 확인, 팔레트 색차, stat 칸 색차), `out/k6-summary.txt`

## 시뮬레이션 방법

- 2형(deutan), 1형(protan): Machado, Oliveira, Fernandes (2009, IEEE TVCG) 의 심한 정도 1.0 행렬. 저자 페이지
  (https://www.inf.ufrgs.br/~oliveira/pubs_files/CVD_Simulation/CVD_Simulation.html) Table 1 값을 옮겼고, sRGB 를 선형 RGB 로 푼 뒤 곱한다.
  DaltonLens 0.1.5 의 `Simulator_Machado2009` 결과와 채널 값 차이가 최대 1 이었다(반올림).
- 3형(tritan): Machado 모델은 3형에 잘 맞지 않는다는 DaltonLens 의 정리를 따라 `Simulator_Brettel1997` 을 쓴다.
- 색차는 CIE76 ΔE(Lab 거리). 흑백은 선형 RGB 의 상대 휘도.
- 팔레트 색차와 WCAG 대비는 그라파나 **라이트 테마** hex(`getLightHues`: green #56A64B, semi-dark-yellow #E0B400, blue #3274D9,
  orange #FF780A, red #E02F44, purple #A352CC)로 계산한다. 캡처에 실제로 찍힌 값이다. 다크 테마 hex 는 참고용으로 같이 찍는다.

## 버전

Spring Boot 4.1.1 (Micrometer 1.17.1), Prometheus 3.15.0, Grafana 13.2.3, k6 2.3.0,
Python 3.12 + numpy 2.3.4 + Pillow 12.0.0 + daltonlens 0.1.5 (컨테이너 안에서만 설치). 실행 환경 Docker Desktop, Apple M5 Pro.

## 돌리다 만난 함정

- **`@GetMapping("/api/{name}")` 으로 쓰면 `uri` 태그가 전부 `/api/{name}` 하나가 된다.** 스프링은 경로 템플릿을 태그로 쓴다.
  엔드포인트마다 선을 그리려고 경로를 다섯 개 따로 적었다.
- **Classic palette 는 시리즈 순서대로 색을 준다.** Prometheus 결과가 `uri` 알파벳 순이라 cart 가 초록, checkout 이 노랑,
  search 가 빨강이 됐다. 장애가 난 checkout 은 노랑이고 빨간 선은 멀쩡한 search 였다.
- **값 매핑으로 stat 칸에 "✕ 초과"를 쓰면 숫자가 사라진다.** 매핑 결과 글자가 값을 대신한다. 숫자는 위쪽 시계열 범례 표에서 읽는다.
- **누적 면 위의 에러는 색과 상관없이 안 보인다.** 초당 50건 중 0.4건이라 같은 축에서는 바닥에 붙는다. `after` 는 에러를 오른쪽 축으로 뺐다.
- `thresholdsStyle` 의 `line+area` 는 실선, `dashed+area` 가 점선이다.
- **그라파나는 테마마다 같은 색 이름에 다른 hex 를 쓴다.** 처음에 다크 테마 값(#73BF69 등)으로 색차와 대비를 계산했다가,
  캡처 픽셀에는 라이트 값(#56A64B 등)만 있다는 걸 확인하고 다시 계산했다.
