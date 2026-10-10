# 메트릭 수집 실습-3: StatsD는 UDP 패킷을 말없이 버린다

글: `posts/CS/Observability/metrics-pipeline/08_실습-3 - StatsD는 UDP 패킷을 말없이 버린다.html`

StatsD 줄(`lab.sent:1|c`)을 UDP 패킷 하나씩 보내고, statsd_exporter 가 받은 수(`lab_sent`)와
받는 쪽 커널이 버린 수(`/proc/net/snmp` 의 `Udp: RcvbufErrors`)를 비교한다.

## 구성

| 경로 | 내용 |
|---|---|
| `sender/send.py` | 보내는 쪽. 보낸 수를 직접 세서 `:8000/metrics` 로 내보낸다. `RATE`, `SECONDS`, `STEPS`, `UNIX_SOCKET`, `NONBLOCK` |
| `compose.yaml` | statsd_exporter, `kernel`(statsd 와 네트워크 네임스페이스를 같이 쓰는 node_exporter, netstat 수집기만), Prometheus, Grafana, sender(profile `send`) |
| `run.sh` | statsd 를 새로 띄워 0 으로 만들고, 한 번 보내고, `count.sh` 로 받은 쪽 숫자를 찍는다 |
| `pause-test.sh` | statsd 를 `docker pause` 로 멈춘 채 보내서 수신 버퍼에 몇 개 들어가는지 본다 |
| `ramp.sh` | statsd CPU 0.25개, 보내는 속도를 30초마다 올린다(Grafana 대시보드용) |
| `count.sh` | statsd_exporter 지표와 커널 카운터를 한 줄로 |

호스트 포트: Grafana 21300, Prometheus 21390, statsd_exporter 지표 21302.

## 돌리기

```bash
cd labs/observability/metrics-03-statsd
docker compose up -d
RATE=1000 SECONDS_TO_SEND=30 ./run.sh                    # 유실 0
RATE=0 SECONDS_TO_SEND=10 ./run.sh                       # 최대 속도: 4% 안팎 유실
RATE=0 SECONDS_TO_SEND=10 READ_BUFFER=8388608 ./run.sh   # 8MB 요청 → 실제 416KB
RATE=0 SECONDS_TO_SEND=10 READ_BUFFER=4096 ./run.sh      # 실제 8KB
./pause-test.sh                                          # 버퍼에 238개
./ramp.sh                                                # Grafana "StatsD UDP 유실" 대시보드
RATE=0 SECONDS_TO_SEND=10 STATSD_CPUS=0.25 ./run.sh
UNIX_SOCKET=/sock/statsd.sock RATE=0 SECONDS_TO_SEND=10 STATSD_CPUS=0.25 ./run.sh
UNIX_SOCKET=/sock/statsd.sock NONBLOCK=1 RATE=0 SECONDS_TO_SEND=10 STATSD_CPUS=0.25 ./run.sh
docker compose --profile send down -v      # ramp.sh 가 남긴 sender 컨테이너까지 지운다
```

## 버전

| 부품 | 버전 |
|---|---|
| statsd_exporter | 0.31.0 |
| node_exporter | 1.12.1 |
| Prometheus | 3.15.0 |
| Grafana | 13.2.3 |
| sender | python:3.13-alpine |

실행 환경: Docker Desktop(리눅스 6.12 linuxkit), `net.core.rmem_default` = `rmem_max` = 212992.

## 함정 (돌리다 만난 것)

- 커널 카운터는 네트워크 네임스페이스마다 따로다. 호스트나 다른 컨테이너의 `netstat -su` 로는 안 보인다.
  그래서 node_exporter 를 `network_mode: service:statsd` 로 붙였다.
- `--statsd.read-buffer` 는 `rmem_max` 에 걸려 조용히 줄어든다(8MB 요청 → 425984). 로그에 경고가 없다.
  `ss -uamn` 의 `rb` 로 확인한다. 컨테이너에 `--sysctl net.core.rmem_max=...` 를 주면 permission denied 로 뜨지 않는다.
- `ramp.sh` 는 끝에 sender 컨테이너를 지운다. `docker compose run` 으로 띄운 sender 는 서비스 이름(`sender`)으로 DNS 에 잡히지 않아 Prometheus 가 못 긁는다.
  Grafana 에 보낸 쪽 선이 필요하면 `ramp.sh` 처럼 `docker compose up sender` 로 띄운다.
- statsd_exporter 이미지는 nobody 로 돌아서 볼륨에 유닉스 소켓을 못 만든다(`bind: permission denied`). `user: "0"` 으로 띄웠다.
- 커널 `InDatagrams` 는 같은 네임스페이스의 다른 UDP(디버그 컨테이너의 DNS 응답 등)까지 센다. 받은 수는 exporter 지표로 본다.
