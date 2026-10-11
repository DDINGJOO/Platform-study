# 메트릭 수집 실습-5: 지수가중이동평균이 잊어 가는 속도를 잰다

글: `posts/CS/Observability/metrics-pipeline/11_실습-5 - 지수가중이동평균이 잊어 가는 속도를 잰다.html`
(개념: 같은 시리즈 6편 "1분, 5분, 15분은 어디서 왔나")

드롭위저드 `Meter` 에 계단식 부하(0 → 초당 100건 → 0)를 넣고 m1/m5/m15 가 오르고 내려오는 곡선을
1초마다 기록해 이론 곡선 `100·(1 - e^(-t/τ))` 과 겹쳐 본다. 같은 사건을 마이크로미터 STEP 카운터와
"최근 60초 창" 비율로도 세서 세 가지 1분 비율을 비교한다. 리눅스 `/proc/loadavg` 도 같은 감쇠를 보이는지 따로 잰다.

## 구성

| 경로 | 내용 |
|---|---|
| `app/EwmaLab.java` | 드롭위저드 Meter 둘(`early`: 앱 기동 때 생성, `late`: 부하가 처음 들어올 때 생성), 마이크로미터 `SimpleMeterRegistry`(STEP, 60초) Counter 하나. 10ms 마다 mark. 1초마다 `data/samples.csv`, `:8080/metrics` 로 Prometheus 형식 |
| `app/Dockerfile` | 메이븐 센트럴에서 jar 를 받아 `javac` 로 빌드(Gradle 없음) |
| `compose.yaml` | app, Prometheus(5초 간격), Grafana(대시보드 "EWMA 감쇠") |
| `plot/plot_ewma.py` | `samples.csv` 로 그림 세 장(`step-response.png`, `three-1m-rates.png`, `early-vs-late.png`)과 글의 숫자 |
| `plot/prom_ewma.py` | Prometheus 에 남은 누적 카운트만으로 m1/m5/m15 를 다시 계산해 Meter 가 낸 값과 비교(표준 라이브러리만) |
| `plot/resample_ewma.py` | 1초 간격 카운트를 5·30·60초로 솎아 α 를 간격에 맞춰 다시 잡고 m1/m5/m15 를 재계산 |
| `plot/plot_loadavg.py` | `loadavg.csv` 로 리눅스 로드 애버리지 그림과 갱신 간격 |
| `plot/infer_loadavg.py` | 1분값의 변화로 커널이 넣은 표본 n 을 거꾸로 구해 5분·15분값을 다시 계산한다. 커널 상수(2014, 2037)와 이론값 e^(-5.001/τ)를 비교 |
| `loadavg/probe.py`, `loadavg/run.sh` | `/proc/loadavg` 를 10ms 마다 읽어 바뀐 순간만 기록. 중간에 CPU 를 태우는 프로세스를 띄웠다 죽인다 |
| `results/` | 글에 쓴 실행의 CSV(`samples.csv`, `loadavg.csv`)와 스크립트 출력(`*.txt`) |

호스트 포트: 앱 23080, Prometheus 23390, Grafana 23300.

## 돌리기

```bash
cd labs/observability/metrics-05-ewma
docker compose up -d --build                 # 2분 쉬고, 30분 초당 100건, 30분 0건 (SCHEDULE 로 바꾼다)
# 62분 기다린다. Grafana: http://localhost:23300 → 대시보드 "EWMA 감쇠"
docker build -t obs-lab/metrics-05-ewma-plot:dev plot
docker run --rm -v "$PWD:/work" obs-lab/metrics-05-ewma-plot:dev plot/plot_ewma.py data/samples.csv out/
python3 plot/prom_ewma.py                    # 누적 카운트로 m1/m5/m15 다시 계산
python3 plot/resample_ewma.py results/samples.csv   # 긁는 간격 5·30·60초 비교
docker compose down -v

./loadavg/run.sh                             # 2분 기록, CPU 태우기 8개 10분, 끄고 15분 (BASE/ON/OFF/BURN)
docker run --rm -v "$PWD:/work" obs-lab/metrics-05-ewma-plot:dev plot/plot_loadavg.py data/loadavg.csv out/
python3 plot/infer_loadavg.py data/loadavg.csv
```

짧게 확인만 하려면 `SCHEDULE=10:0,20:100,10:0 docker compose up -d app` (초:초당건수, 쉼표로 이어 붙임).

## 버전

| 부품 | 버전 | 비고 |
|---|---|---|
| Dropwizard Metrics | 4.2.40 | `com.codahale.metrics`. 5.0.8(`io.dropwizard.metrics5`)도 `EWMA.java` 는 같은 코드 |
| Micrometer | 1.17.1 | `SimpleMeterRegistry`, `CountingMode.STEP` |
| JDK | Eclipse Temurin 21 | |
| Prometheus | 3.15.0 | |
| Grafana | 13.2.3 | |
| 그림 | python:3.13-slim + matplotlib 3.11.2 + fonts-nanum | |

실행 환경: Docker Desktop(리눅스 6.12.76 linuxkit, `CONFIG_HZ=1000`, CPU 15개), Apple M5 Pro.

## 함정 (돌리다 만난 것)

- 드롭위저드 Meter 는 첫 tick 에서 평균을 0 에서 올리지 않고 첫 5초의 비율로 바로 시작한다(`EWMA.tick()` 의 `initialized` 분기).
  부하가 들어오는 중에 만든 Meter 는 15분비가 5초 만에 평소 값이 된다. 그래서 Meter 를 둘(`early`, `late`) 둔다.
- 4.x 의 Meter 에는 5초마다 도는 스레드가 없다. `mark()` 나 `getXxxRate()` 가 불릴 때 밀린 tick 을 한꺼번에 돌린다.
  이 앱은 1초마다 값을 읽으니 tick 이 늦지 않는다.
- 컨테이너 안의 `/proc/loadavg` 는 Docker VM 전체 값이다. 다른 컨테이너의 부하가 섞이므로 CPU 태우기 프로세스를 넉넉히(8개) 띄우고, 시작 전 2분을 기준선으로 잡는다.
- 마이크로미터 `SimpleMeterRegistry` 의 STEP 카운터는 `count()` 가 "직전에 끝난 1분"의 건수다. 진행 중인 1분은 보이지 않는다.
- 이번 실행에서는 같은 VM 에서 다른 실습이 부하 시험을 돌려 `/proc/loadavg` 1분값이 26까지 튀었다. 곡선 모양 비교는 포기하고,
  갱신 간격(5.001초)과 `infer_loadavg.py` 의 재현 오차로 확인했다. 잡음은 표본 n 에 같이 들어가므로 재현 검사에는 영향이 없다.
- `probe.py` 는 CSV 를 프로세스가 끝날 때 한 번에 쓴다(버퍼). 도중에 파일이 비어 보여도 정상이다.
- 누적 카운트로 m1/m5/m15 를 되살리는 계산(`prom_ewma.py`)은 시작 상태가 같아서 성립했다. Prometheus 기록과 `early` Meter 가
  둘 다 무부하 2분 안에서 시작했고, 62분 동안 리셋·재시작·긁기 실패가 없었다. 시작 상태를 모르면 m15 기준 약 69분의 앞 구간이 필요하고,
  생성 시각을 모르는 `late` Meter 는 재현할 수 없다.
- `resample_ewma.py` 에서 60초 간격도 5초와 같은 결과가 나온 건 부하가 간격 안에서 일정한 계단이었기 때문이다. 들쭉날쭉한 부하는 재지 않았다.
- `infer_loadavg.py` 의 이론값 비교도 n 은 커널 1분 상수(1884/2048)로 역산한다. 5분·15분 상수만 바꾼 비교다.
