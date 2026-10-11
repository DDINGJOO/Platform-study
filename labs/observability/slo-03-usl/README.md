# SLO와 경고 실습-3: 동시성을 올려 가며 USL 곡선을 맞춘다

경합(σ)과 일관성 비용(κ)을 손잡이로 만든 스프링 부트 앱 하나에 k6 로 **닫힌 부하**(VU N개가 쉬지 않고 요청)를 걸고,
N = 1 ~ 64 열한 단계에서 처리량을 세 번씩 잰다. 그 점들에 범용 확장성 법칙(USL)

    X(N) = λN / (1 + σ(N−1) + κN(N−1))

을 비선형 최소제곱(scipy `curve_fit`)으로 맞추고, 정점 예측 N* = √((1−σ)/κ) 를 실측과 비교한다.
`fit.py` 는 기본으로 σ, κ 를 0~1 로 묶는다. `--free-sigma` 를 주면 σ 하한을 −1 로 푼다(글에는 두 결과를 함께 적었다).

## 앱이 하는 일 (`app/`)

`GET /work` 한 번 =

1. **병렬 구간**: `PARALLEL_US`(기본 20ms) 동안 잠든다. 요청끼리 서로 막지 않는다
2. **CPU 구간**: `CPU_US` 동안(벽시계) 또는 `CPU_LOOPS` 번(일의 양 고정) CPU 를 쓴다(기본 0, CPU 시나리오에서만)
3. **직렬 구간**: 전역 `ReentrantLock` 을 잡고 `SERIAL_US` 동안 머문다 → 경합
   락을 잡은 채로 `지금 서버 안에 있는 다른 요청 수 × COHERENCY_US` 만큼 더 머문다 → 일관성

`POST /config?parallelUs=&serialUs=&coherencyUs=&cpuUs=&cpuLoops=&spinSerial=&expRandom=` 로 재시작 없이 바꾸고,
`GET /stats` 는 요청 수·락 대기·락 보유·같이 있던 요청 수의 누적값을 준다.

## 돌리기

```bash
cd labs/observability/slo-03-usl
docker compose up -d --build app                 # 앱 http://localhost:22080 (APP_PORT 로 변경)
docker compose --profile fit build fit           # numpy·scipy·matplotlib 이미지

bash scripts/run-all.sh       # contention, coherency (각 11단계 × 3회, 약 30분)
bash scripts/run-rest.sh      # contention-exp, coherency-exp, cpu (약 45분)
bash scripts/run-extra.sh     # cpu-fixed, coherency-fine (약 25분)
bash scripts/cpu-throttle.sh  # 할당량 아래에서 동시성별 CFS 스로틀링 통계 → results/cpu-throttle.txt (약 2분, 끝나면 cpus 4 로 되돌림)
bash scripts/sleep-serial.sh  # 직렬 구간을 잠으로 채웠을 때(N = 1, 32) → results/sleep-serial.csv
bash scripts/cpu-cpuset.sh    # cpu-fixed 와 같은 계산을 코어 두 개 고정·할당량 없이 (약 10분)

docker compose --profile fit run --rm fit contention.csv --train-max 8  --out contention.png
docker compose --profile fit run --rm fit coherency.csv  --train-max 16 --extra coherency-fine.csv --out coherency.png
docker compose --profile fit run --rm fit coherency.csv  --train-max 16 --free-sigma          # σ 제약 없이
docker compose --profile fit run --rm --entrypoint python fit /fit/plot_cpu.py      # cpu-compare.png
docker compose --profile fit run --rm --entrypoint python fit /fit/sim_degeneracy.py 1 2 3 7 11   # 5편 모의 실험 → results/sim-degeneracy.txt

docker compose --profile load --profile fit down -v
```

`sweep.sh` 는 `results/<이름>.csv` 에 **덧붙인다.** 저장소에 든 결과 위에 다시 재려면 그 CSV 를 먼저 지우거나 다른 이름을 쓴다.
시나리오 하나만 돌리려면 설정을 바꾸고 `sweep.sh` 를 부른다.

```bash
curl -XPOST 'localhost:22080/config?parallelUs=20000&serialUs=500&coherencyUs=50&cpuUs=0&spinSerial=true&expRandom=false'
rm -f results/coherency.csv
bash scripts/sweep.sh coherency 3
STEPS="16 17 18 19 20 21 22 23 24" bash scripts/sweep.sh coherency-fine 2
```

결과 CSV 열: `n`(VU 수), `x_rps`(측정 20초 동안의 처리량), `avg_ms`·`p50_ms`·`p99_ms`(k6 가 잰 응답 시간),
`lock_wait_ms`·`lock_hold_ms`·`peers_avg`(서버 쪽, 워밍업 5초 포함 평균), `loadavg1`(도커 VM 1분 로드 애버리지).

## 시나리오

| 이름 | 설정 | 무엇을 보나 |
|---|---|---|
| `contention` | 병렬 20ms, 직렬 1ms | 경합만. 천장은 1/1ms = 초당 1,000건 |
| `coherency` | 병렬 20ms, 직렬 0.5ms, 다른 요청당 0.05ms | 경합 + 일관성. 정점 뒤로 처리량이 줄어야 한다 |
| `contention-exp`, `coherency-exp` | 위와 같되 병렬·직렬 길이를 지수 분포에서 뽑음 | 처리 시간이 흔들리면 곡선과 맞춤이 달라지나 |
| `cpu` | 벽시계로 2ms 돌기, `APP_CPUS=2`(CFS 할당량) | 코어 수가 천장. 다른 컨테이너의 CPU 사용에 흔들리나 |
| `cpu-fixed` | 계산 180만 번(동시성 1에서 약 1.8ms), `APP_CPUS=2` | 일의 양을 고정하면 어떻게 되나 |
| `cpu-cpuset` | `cpu-fixed` 와 같은 계산, 할당량 없이 `cpuset: "0,1"` (`compose.cpuset.yaml`) | 할당량과 코어 고정의 차이 |
| `coherency-fine` | `coherency` 와 같음, N = 16~24 를 1씩 2회 | 단계 사이에 숨은 실제 정점 |

## 버전

Spring Boot 4.1.1(실행 당시 Java 21.0.12, 이미지 태그는 `eclipse-temurin:21-jre`), k6 2.3.0, Python 3.13.16(`python:3.13-slim`, 실행 당시) · numpy 2.3.3 · scipy 1.16.2 · matplotlib 3.10.6,
Docker Desktop(linuxkit 6.12.76, VM CPU 15개·메모리 8GB), 앱 컨테이너 `cpus: 4`(CPU 시나리오만 2), `mem_limit: 512m`, `-Xmx256m`

## 결과 요약 (results/*.csv, 2026-10-11)

| 시나리오 | 실측 | 모든 점으로 맞춘 USL |
|---|---|---|
| contention | 24 이후 초당 977~981 에서 수평 | σ = 0(하한), κ = 0.000587, N* = 41.3 (실측엔 하락 없음) / 제약 없음: σ = −0.004, κ = 0.00062, N* = 40.2 |
| contention-exp | 24 에서 911, 32 이후 975~987 | σ = 0, κ = 0.000536 |
| coherency | 16 에서 705, 64 에서 275 | σ = 0(하한), κ = 0.00264, N* = 19.5, 정점 585, R² 0.92 / 제약 없음: σ = −0.055, κ = 0.0030, N* = 18.8, 정점 674, R² 0.99 |
| coherency-fine | 정점 N = 18, 747~749 | (맞춤에 안 씀) |
| coherency, N ≤ 16 만 | | κ = 0.00004, N* = 158.5 / 제약 없음: N* = 65.5 |
| coherency, N ≤ 24 만 | | N* = 24.8 / 제약 없음: N* = 18.2 |
| cpu | 64 에서 평균 1,269, 최대 1,372 (이론 천장 1,000 초과) | |
| cpu-fixed | N = 2 에서 1,079, 24 이후 720 대 | R² 0.47 |
| cpu-cpuset | 6~64 에서 1,110~1,130 수평 | σ = 0.51, κ = 0.0014, N* = 18.8 |

`cpu-throttle.sh` (cpus: 2, 계산 고정, `results/cpu-throttle.txt`): N = 2 에서 253 주기 중 81 번 스로틀링, N ≥ 4 는 거의 모든 주기.
CPU 사용은 1.96~2.01 코어로 같은데 처리량이 1,083 → 733 으로 줄었다(요청당 CPU 1.81 → 2.74ms). 왜 늘었는지는 확인하지 못했다.
`throttled_usec` 는 CPU 별로 멈춘 시간을 더한 값이라 25초 측정에서 249초까지 나온다.

## 함정 (돌리다 만난 것)

- **직렬 구간을 잠으로 채우면 1ms 가 1.8ms 가 된다.** Docker Desktop 커널은 `CONFIG_HZ=1000` 이고
  `CONFIG_HIGH_RES_TIMERS` 가 꺼져 있어(`/proc/config.gz`) `parkNanos` 가 1ms 틱 단위로 깬다.
  50µs 를 요청하면 774µs, 1ms 를 요청하면 1,824µs 동안 락을 잡고 있었다(`results/timer-resolution.txt`).
  그래서 직렬 구간은 CPU 를 돌려 채운다(`spinSerial=true`, 기본값). 병렬 구간 20ms 는 잠이라 실제로는 약 22ms 다.
  잠으로 채운 채 경합 시나리오를 돌리면 N = 32 에서 초당 504건에서 멈췄다(`results/sleep-serial.csv`, 락 보유 평균 1.96ms).
- **경합만 있는 앱인데 맞추면 σ = 0, κ > 0 이 나온다.** 처리 시간이 일정한 시스템은 직선으로 오르다 천장에서
  꺾이는데, USL 의 σ 항은 그렇게 날카로운 무릎을 못 만든다. 회귀가 κ 로 무릎을 흉내 낸다. 계수는 원인이 아니라 모양이다.
- **꺾이기 전 점만으로는 정점을 예측하지 못한다.** `coherency` 에서 N ≤ 16 으로 맞추면 예측 정점이 158(제약 없이 65)이었다. 실제는 18.
- **σ = 0 은 하한에 붙은 값이다.** 제약을 풀면 무릎이 날카로운 곡선에서 σ 가 음수로 나온다(측정 오류가 아니다).
- **일을 "시간"으로 흉내 내면 처리량이 부푼다.** `cpuUs` 는 벽시계 기준이라 코어를 뺏긴 동안에도 시간이 가서
  요청 하나의 실제 계산이 줄어든다. 이론 천장 1,000 을 넘어 1,372 까지 나왔고, VM 이 바쁠수록 더 높았다. 그래서 `cpuLoops` 를 만들었다.
- **CFS 할당량(`cpus: 2`)은 일관성 비용 없이도 처리량을 끌어내린다.** 코어 고정(`cpuset`)으로 바꾸면 수평이 된다.
  컨테이너 안 `cpu.max` 가 `200000 100000`(100ms 마다 200ms)이고, p99 가 주기 길이 근처(50~100ms)로 뛴다.
- 대기 루프를 `pgrep -f run-extra.sh` 로 짜면 그 루프의 셸 명령줄도 걸려서 끝나지 않는다. 결과 CSV 줄 수로 기다린다.
- k6 요약에 시나리오별 값을 남기려면 그 서브메트릭에 임계값이 하나 있어야 한다(`step.js` 의 `thresholds`).
  처리량은 서브메트릭의 `rate` 가 아니라 `count / 측정 초` 로 계산한다. `rate` 는 워밍업을 포함한 전체 시간으로 나눈다.
- 다른 실습과 도커 VM 을 같이 쓰는 동안 잰 값이다. 각 행의 `loadavg1` 이 그때 VM 부하이고, 흔들림은 같은 단계의 세 번 측정으로 본다.
