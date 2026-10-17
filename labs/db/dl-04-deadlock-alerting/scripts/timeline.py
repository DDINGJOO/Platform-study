"""실제 MySQL 에 교착을 일정표대로 내면서 lock_deadlocks 를 1초마다 찍는다.

시간 축은 1초 = 1분으로 줄였다(13분 실행 = 13시간 분량).
 - 구간 A (0~180초, '3시간'): 시간당 8건 꼴, 도착 간격은 지수분포(seed 고정)
 - 구간 B (180~780초, '10시간'): 시간당 0.3건 꼴, 200초마다 1건(3건)
출력: out/timeline.csv (sec,lock_deadlocks,app_errors), out/deadlocks.log
"""
import os, random, subprocess, sys, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out")
TOTAL = int(os.environ.get("TOTAL", "780"))


def schedule(seed=4):
    rnd, t, times = random.Random(seed), 0.0, []
    while True:
        t += max(rnd.expovariate(8 / 60.0), 1.5)   # 시간당 8건 = 분당 8/60, 1초=1분
        if t >= 180:
            break
        times.append(round(t, 1))
    times += [240.0, 440.0, 640.0]
    return times


def q_count():
    r = subprocess.run(["docker", "exec", "dl04-mysql", "mysql", "-uroot", "-plabroot", "-N", "-e",
                        "SELECT COUNT FROM information_schema.INNODB_METRICS WHERE NAME='lock_deadlocks'"],
                       capture_output=True, text=True)
    return int(r.stdout.strip())


def main():
    os.makedirs(OUT, exist_ok=True)
    plan = schedule()
    app_errors = [0]
    log = open(os.path.join(OUT, "deadlocks.log"), "w")
    t0 = time.time()

    def trigger(at):
        time.sleep(max(0, at - (time.time() - t0)))
        r = subprocess.run([os.path.join(HERE, "deadlock_once.sh")], capture_output=True, text=True)
        errs = [l for l in r.stdout.splitlines() if "ERROR" in l]
        app_errors[0] += len(errs)
        log.write("t=%.1f planned=%.1f errors=%d %s\n" % (time.time() - t0, at, len(errs), " | ".join(errs)))
        log.flush()

    def run_all():
        for at in plan:
            trigger(at)

    th = threading.Thread(target=run_all, daemon=True)
    th.start()
    with open(os.path.join(OUT, "timeline.csv"), "w") as f:
        f.write("sec,lock_deadlocks,app_errors\n")
        base = q_count()
        for sec in range(TOTAL + 1):
            time.sleep(max(0, sec - (time.time() - t0)))
            f.write("%d,%d,%d\n" % (sec, q_count() - base, app_errors[0]))
            f.flush()
    th.join(timeout=30)
    print("planned deadlocks:", len(plan), "phaseA:", sum(1 for p in plan if p < 180), "phaseB:", sum(1 for p in plan if p >= 180))
    print("app errors (1213 lines):", app_errors[0])


if __name__ == "__main__":
    main()
