# ir-01-alert-noise: 경고 폭풍을 Alertmanager로 묶고 누른다

장애 대응 시리즈 실습-1 의 코드. 하위 의존성(`db`) 하나를 멈춰 경고 31개를 한꺼번에 울리고,
Alertmanager 설정을 바꿔 가며 **사람에게 간 알림 수**와 **첫 알림까지 걸린 시간**을 잰다.

## 구성

| 경로 | 내용 |
|---|---|
| `app/app.py` | 표준 라이브러리만 쓴 파이썬 서버. `ROLE=db` 는 하위 의존성, `ROLE=app` 은 초당 10건씩 db 를 부르는 서비스 인스턴스(타임아웃 1초) |
| `compose.yaml` | db 1개 + 서비스 5개 × 인스턴스 2개 + Prometheus + Alertmanager + 웹훅 수신기 |
| `prometheus/rules.yml` | 경고 네 종류(`DBDown` 1개, `DependencyDown`·`HighErrorRate`·`HighLatency` 각 10개). 모두 `summary`, `description`, `runbook_url` 주석 |
| `alertmanager/*.yml` | 시나리오별 설정. A 기본값, B 묶지 않음, C 이름으로 묶음, D 억제, E 우선순위 라우팅, G 반복 간격 |
| `runbooks/` | 경고 규칙의 `runbook_url` 이 가리키는 절차서 예시(경고 이름 = 파일 이름) |
| `webhook/receiver.py` | 알림 한 통마다 JSON 한 줄을 `results/raw/<시나리오>.jsonl` 에 남긴다 |
| `scripts/run_scenario.py` | Alertmanager 를 새 설정으로 다시 띄우고, db 를 `docker compose pause` 로 멈췄다가 되살리며 2초마다 경고 상태를 기록 |
| `scripts/summarize.py` | 원자료를 db 를 멈춘 순간 기준 상대 시간으로 바꿔 `results/<시나리오>.txt` 로 요약. 믿을 수 없는 실행에는 `!!` 줄을 찍는다 |
| `scripts/run_all.sh`, `scripts/rerun.sh` | 시나리오 전부 돌리기 / `!!` 가 나온 시나리오를 깨끗해질 때까지 다시 돌리기(macOS 에서는 덮개가 열렸거나 전원이 꽂힌 상태가 3분 이어져야 시작) |
| `scripts/stale_group.py` | Docker 없이 Alertmanager 바이너리 하나로, 앞 장애에서 풀린 경고가 새 장애의 첫 알림을 늦추는지 확인 |
| `results/` | 글에 쓴 실행의 요약. `results/aborted/` 는 버린 실행, `results/raw/` 는 유닉스 시각이 들어 있어 커밋하지 않는다 |

## 버전

| 구성 요소 | 버전 | 메모 |
|---|---|---|
| Alertmanager | 0.34.1 | 2026-09-17 릴리스, 지금 최신 안정판 |
| Prometheus | 3.15.0 | 스크레이프·규칙 평가 5초, 스크레이프 타임아웃 2초 |
| Python | 3.13 (alpine) | 앱, db, 웹훅 수신기 |
| 실행 환경 | Docker Desktop (메모리 8GB), Apple M5 Pro | 스택 전체가 메모리 300MB 안팎 |

## 돌리는 법

포트는 27000번대만 쓴다(Prometheus 27090, Alertmanager 27093).

```bash
cd labs/devops/ir-01-alert-noise
docker compose up -d                                   # 기본 설정은 c-group.yml
docker compose pause db                                # 장애 주입: db 프로세스를 멈춘다
docker compose unpause db                              # 복구
docker compose logs -f webhook                         # 받은 알림

# 글에 쓴 시나리오 전부(약 90분). caffeinate 는 macOS 에서 잠들지 않게(덮개를 닫고 배터리로 돌면 못 막는다)
caffeinate -s -i ./scripts/run_all.sh
caffeinate -s -i ./scripts/rerun.sh                    # !! 가 나온 시나리오만 다시
# 하나만: 이름, 설정 파일, 멈춘 시간(초), 복구 뒤 관찰(초)
python3 scripts/run_scenario.py d-inhibit d-inhibit.yml 360 420
python3 scripts/summarize.py d-inhibit

docker compose down -v
```

## 결과 (글에 쓴 실행, 시나리오마다 한 번)

| 시나리오 | 사람에게 간 알림 | 장애 중 / 복구 뒤 | 첫 알림 | 요약 파일 |
|---|---|---|---|---|
| A 기본값(group_by 없음 = 묶음 하나) | 3 | 2 / 1 | 48.8s | `results/a-defaults.txt` |
| B 묶지 않음(`['...']`) | 62 | 31 / 31 | 47.2s | `results/b-nogroup.txt` |
| C `group_by: [alertname]` | 8 | 4 / 4 | 53.2s | `results/c-group.txt` |
| D C + 억제 | 4 | 1 / 3 | 49.5s | `results/d-inhibit.txt` |
| E D + 등급별 라우팅 | page 2 | 1 / 1 | 30.2s | `results/e-route.txt` |
| G group_interval 1m, repeat_interval 90s (db 8분 멈춤) | 20 | 16 / 4 | 48.1s | `results/g-repeat.txt` |

- D: db 를 되살리고 32.5초 뒤 `HighLatency` 10개가 억제에서 풀려 나갔다(원인 경고가 증상 경고보다 56초 먼저 풀림)
- G: 같은 묶음의 firing 알림 사이 간격 12번이 모두 120초(90초가 group_interval 1분의 배수로 올림). 나머지 4번은 마지막 firing 에서 resolved 까지의 간격이라 반복과 무관
- C: `HighErrorRate` 첫 알림이 울린 지 264초 뒤. 앞 시나리오(B)에서 풀린 같은 이름의 경고가 원인으로 보인다.
  B 에서 함께 풀린 다른 세 이름은 늦지 않았다(반례). `stale_group.py` 로 group_interval 5분에서 30초 → 144초가 됐지만,
  경고 1개(`stale-group-n1-*`)나 60초 간격(`...-gap60-gi2m.txt`)에서는 늦지 않았다.
  소스로 세운 추론: 풀린 경고로 생긴 묶음은 바로 flush 되고 목록을 읽은 순간의 경고만 지운다. 한 요청의 경고 일부가
  그 뒤에 들어오면 묶음이 살아남아 group_interval 주기로 돌고, 새 firing 경고는 타이머를 건드리지 않고 거기에 붙는다
  (`dispatch/dispatch.go`, `store/store.go` 의 `DeleteIfNotModified`). 이 경쟁이 실제로 일어났는지는 측정하지 못했다

```bash
# stale_group.py 는 Alertmanager 바이너리만 있으면 된다(포트 27094, 27081)
GAP=36 GI=5m python3 scripts/stale_group.py /path/to/alertmanager
```

## 함정 (돌리다 만난 것)

- 알파인 이미지의 busybox `wget` 으로 `localhost:8080` 을 부르면 `Connection refused` 가 난다. `localhost` 가 IPv6(`::1`)로 풀리는데
  서버는 IPv4 에만 묶여 있다. `127.0.0.1` 로 부른다.
- `promtool check config` 를 다른 경로에 마운트해 돌리면 `rule_files` 의 절대 경로를 못 찾는다. `/etc/prometheus` 에 그대로 마운트해 검사한다.
- **Alertmanager 를 `--force-recreate` 로 다시 띄워도 알림 기록이 남는다.** 이미지가 `/alertmanager` 를 익명 볼륨으로 선언하고,
  compose 는 컨테이너를 다시 만들 때 익명 볼륨을 그대로 붙인다. 그 안의 알림 기록(nflog)이 이어져서, 앞 실행에서 firing 으로
  보낸 묶음의 resolved 알림이 다음 실행 시작 직전에 나왔다. 같은 묶음 키(`group_by: [alertname]`, 수신자 `human`)를 쓰는 C 와 D 에서 생겼다.
  지금 스크립트는 시나리오마다 `docker compose rm -sfv alertmanager webhook` 으로 익명 볼륨째 지우고 새로 띄운다.
- 첫 실행(`results/aborted/`)은 세 가지 이유로 버렸다. B 는 db 를 멈추기 28초 전에 Docker 가 잠깐 멈춰 지연이 튀었고
  `HighLatency` 가 이미 pending 이었다. C 와 D 는 실행 중 호스트가 멈춰 2초 폴링이 6분, 17분씩 끊겼고, 위의 nflog 흔적도 섞였다.
  재실행에서도 B 의 첫 시도가 호스트 잠듦으로 버려졌다(`results/aborted/run2-b-nogroup.txt`).
  `summarize.py` 는 이런 실행에 `!!` 줄을 찍는다(폴링 공백, 주입 전 경고, 주입 전 알림). `run_scenario.py` 는 정상 상태 30초 동안
  경고가 생기면 풀릴 때까지 기다렸다가 다시 30초를 센다.
