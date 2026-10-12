#!/usr/bin/env python3
"""시나리오 하나를 돌린다: Alertmanager 를 새 설정으로 새로 띄우고, db 를 멈췄다가 되살리며 상태를 기록한다.

    python3 scripts/run_scenario.py <이름> <alertmanager 설정 파일> [멈춘 시간 초=360] [복구 뒤 관찰 초=420]

기록(results/raw/, 커밋하지 않음. 유닉스 시각이 들어 있다):
  <이름>.jsonl         웹훅 수신기가 받은 알림 한 통마다 한 줄
  <이름>-poll.jsonl    2초마다 Prometheus 와 Alertmanager 가 본 경고 상태
  <이름>-events.json   db 를 멈춘 시각(t0)과 되살린 시각(t1)
요약은 scripts/summarize.py 가 상대 시간으로 바꿔 results/<이름>.txt 에 쓴다.
"""
import json, os, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROM = f"http://localhost:{os.environ.get('PROM_PORT', '27090')}"
AM = f"http://localhost:{os.environ.get('AM_PORT', '27093')}"
RAW = os.path.join(HERE, "results", "raw")


def get(url):
    with urllib.request.urlopen(url, timeout=5) as r:
        return json.loads(r.read())


def compose(*args, env=None):
    subprocess.run(["docker", "compose", *args], cwd=HERE, check=True, env=env)


def prom_alerts():
    return get(PROM + "/api/v1/alerts")["data"]["alerts"]


def snapshot():
    p = [{"name": a["labels"]["alertname"], "instance": a["labels"].get("instance", ""),
          "state": a["state"], "activeAt": a.get("activeAt")} for a in prom_alerts()]
    m = [{"name": a["labels"]["alertname"], "instance": a["labels"].get("instance", ""),
          "state": a["status"]["state"], "inhibitedBy": a["status"]["inhibitedBy"]}
         for a in get(AM + "/api/v2/alerts")]
    return p, m


def wait_until(cond, what, limit=600):
    t = time.time()
    while time.time() - t < limit:
        try:
            if cond():
                return
        except Exception:
            pass
        time.sleep(2)
    sys.exit(f"시간 초과: {what}")


def main():
    name, conf = sys.argv[1], sys.argv[2]
    outage = int(sys.argv[3]) if len(sys.argv) > 3 else 360
    after = int(sys.argv[4]) if len(sys.argv) > 4 else 420
    os.makedirs(RAW, exist_ok=True)
    for f in (f"{name}.jsonl", f"{name}-poll.jsonl"):
        open(os.path.join(RAW, f), "w").close()

    env = dict(os.environ, SCENARIO=name, AM_CONFIG=conf)
    state = subprocess.run(["docker", "compose", "ps", "db", "--format", "{{.State}}"], cwd=HERE,
                           capture_output=True, text=True).stdout
    if "paused" in state:
        compose("unpause", "db", env=env)
    compose("up", "-d", env=env)
    # Alertmanager 이미지는 /alertmanager 를 익명 볼륨으로 선언한다. --force-recreate 만 하면 그 볼륨(알림 기록 nflog)이
    # 이어져서, 앞 시나리오에서 firing 으로 보낸 묶음의 resolved 알림이 다음 시나리오에 새어 나온다.
    # 컨테이너를 익명 볼륨째 지우고(-v) 새로 띄운다. --renew-anon-volumes 는 옛 볼륨을 고아로 남긴다
    compose("rm", "-sfv", "alertmanager", "webhook", env=env)
    compose("up", "-d", "alertmanager", "webhook", env=env)

    wait_until(lambda: urllib.request.urlopen(AM + "/-/ready", timeout=3).status == 200, "alertmanager 준비")
    wait_until(lambda: len(get(PROM + "/api/v1/targets?state=active")["data"]["activeTargets"]) == 11
               and all(t["health"] == "up" for t in get(PROM + "/api/v1/targets")["data"]["activeTargets"]),
               "모든 타깃 up")
    wait_until(lambda: not prom_alerts(), "이전 경고가 모두 풀림")
    # 정상 상태 30초. 그 사이 pending 경고가 생기면(Docker 가 잠깐 멈추는 등) 풀릴 때까지 기다렸다가 다시 30초
    for attempt in range(10):
        print(f"[{name}] 준비 완료, 30초 정상 상태", flush=True)
        time.sleep(30)
        if not prom_alerts():
            break
        print(f"[{name}] 정상 상태 중에 경고가 생겼다. 풀릴 때까지 기다린다", flush=True)
        wait_until(lambda: not prom_alerts(), "정상 상태 경고가 풀림")
    else:
        sys.exit("정상 상태를 만들지 못했다")

    poll = open(os.path.join(RAW, f"{name}-poll.jsonl"), "a")
    t0 = time.time()
    compose("pause", "db")
    print(f"[{name}] db 멈춤", flush=True)
    t1 = None
    stalls, last = [], t0   # 폴링 간격이 10초를 넘으면(호스트가 잠들거나 멈춤) 기록한다. 그런 실행은 버린다
    while True:
        now = time.time()
        if now - last > 10:
            stalls.append([round(last - t0, 1), round(now - last, 1)])
            print(f"[{name}] 경고: 폴링이 {now - last:.0f}초 멈췄다", flush=True)
        last = now
        if t1 is None and now - t0 >= outage:
            compose("unpause", "db")
            t1 = time.time()
            print(f"[{name}] db 되살림", flush=True)
        if t1 is not None and now - t1 >= after:
            break
        try:
            p, m = snapshot()
            poll.write(json.dumps({"t": round(now, 3), "prom": p, "am": m}) + "\n")
            poll.flush()
        except Exception as e:
            print("poll 실패", e, flush=True)
        time.sleep(2)
    json.dump({"scenario": name, "config": conf, "t0": t0, "t1": t1, "outage_s": outage, "after_s": after,
               "stalls": stalls},
              open(os.path.join(RAW, f"{name}-events.json"), "w"))
    print(f"[{name}] 끝", flush=True)


if __name__ == "__main__":
    main()
