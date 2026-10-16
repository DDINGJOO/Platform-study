# auto-01-idempotent: 절차서를 그대로 옮긴 스크립트와 멱등한 스크립트를 두 번씩 돌린다

운영 자동화 시리즈 실습-1 의 코드. 신규 고객사 등록 절차(DB 행 추가 → nginx 에 location 추가 → 설정 반영)를
두 가지로 옮겨 놓고 같은 조건에서 돌려 차이를 센다.

| 스크립트 | 모양 |
|---|---|
| `ops/naive.sh` | 절차서 그대로. 맨 앞에서 "이미 있으면 중단", `INSERT`, `>>` 로 한 줄 덧붙이기, `nginx -s stop` 후 `nginx` |
| `ops/idem.sh` | 수렴형. `flock -n`, UNIQUE 인덱스 + `ON CONFLICT DO NOTHING`, DB 목록으로 설정 파일 전체 생성(임시 파일 + rename), 반영된 내용과 다르면 `nginx -t` 후 `reload`, 끝에 200 확인. `DRY_RUN=1`, `LOCK=0`, `APPLIED=file` 로 변형을 고른다 |
| `ops/reset.sh`, `ops/check.sh` | 처음 상태로 되돌리기, 불일치 세기(중복 행, 중복 location, 응답 없는 경로, DB 에 없는 경로, nginx 살아 있나) |

## 구성

```
load(초당 100건, 요청마다 새 연결 + 1초짜리 요청 4개 동시) → web(nginx) → app(파이썬)
                                                             └ /ops 스크립트 → db(PostgreSQL)
```

## 돌리는 법

포트는 36000번대만 쓴다(web 36080).

```bash
cd labs/devops/auto-01-idempotent
docker compose up -d --build
./scripts/run_all.sh              # e1~e5 전부(e2b, e3b, e3c 포함). 하나만: ./scripts/run_all.sh e2
python3 scripts/summarize.py      # out/ → results/summary.md
docker compose down -v
```

| 실험 | 내용 | 원자료 |
|---|---|---|
| e1 | 같은 고객사를 차례로 두 번 | `out/e1-seq.txt` |
| e2 | 같은 고객사를 동시에 두 번, 변형마다 20회 | `out/e2-concurrent.txt` |
| e2b | 다른 고객사 둘(t1, t2)을 동시에, 변형마다 20회 | `out/e2b-concurrent-diff.txt` |
| e3 | 부하 중 반영: naive(stop/start) 대 idem(reload), 각 5회 | `out/e3-*.csv`, `*.marks` (커밋 안 함) |
| e3b | 틀린 설정(중복 location)을 `nginx -s stop`+시작, reload, `kill -TERM`+시작으로 반영 | `out/e3b-*` (커밋 안 함) |
| e3c | 문법은 맞고 적용 단계에서 실패하는 설정(없는 주소에 listen)을 `nginx -t` 와 reload 로 | `out/e3c-bind.txt` |
| e4 | 단계마다 kill -9 로 끊고 다시 돌리기 | `out/e4-crash.txt` |
| e5 | 드라이런, DB 조회 실패 때 빈 목록 막기 | `out/e5-dryrun.txt` |

`out/*.csv`, `out/*.marks` 에는 유닉스 시각이 들어 있어 커밋하지 않는다. 요약(`results/summary.md`)은 반영 시작 기준 상대 초만 남긴다.

## 고친 것 (2026-10-16)

- `web` 에 `init: true`. PID 1 이 `tail` 이라 멈춘 nginx 마스터가 좀비로 남았고, `pgrep -x nginx` 가 좀비를 세서
  `reset.sh` 의 "내려갈 때까지 기다림"이 끝나지 않았다. 그때 본 것(그 실행은 버렸다):
  `docker ps` 에서 web 이 Up 7 minutes 인데 `out/e1-seq.txt` 가 0바이트였고, 컨테이너 안 `ps -o pid,ppid,stat,args` 는
  ```
      1       0 Ss   tail -f /dev/null
      8       1 Zs   [nginx] <defunct>
     24       0 Ss   /bin/bash /ops/reset.sh
  ```
- `naive.sh` 와 e3b 의 기다림에 10초 상한. `nginx -s stop` 은 신호를 보내기 전에 설정을 읽으므로 설정이 틀리면
  stop 자체가 실패하고(종료 코드 1) nginx 는 계속 돈다. 상한이 없으면 영원히 기다린다. stop 종료 코드도 남긴다.
- e5 출력의 컨테이너 IP 를 가린다.
