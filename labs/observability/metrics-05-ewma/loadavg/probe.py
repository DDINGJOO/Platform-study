"""리눅스 /proc/loadavg 가 언제, 얼마씩 바뀌는지 기록하고, 중간에 CPU 를 태우는 프로세스 N 개를 띄운다.

10ms 마다 /proc/loadavg 를 읽어 값이 바뀐 순간만 CSV 로 남긴다(커널이 로드를 다시 계산한 순간).
BASE 초 동안 그냥 기록 -> BURN 개의 무한 루프 프로세스를 ON 초 동안 -> 모두 죽이고 OFF 초 동안 기록.
컨테이너 안에서 읽는 /proc/loadavg 는 컨테이너가 아니라 Docker VM 전체 값이다.
"""
import os, time, signal, csv, sys

BASE = int(os.environ.get("BASE", 120)); ON = int(os.environ.get("ON", 600)); OFF = int(os.environ.get("OFF", 900))
BURN = int(os.environ.get("BURN", 8)); OUT = os.environ.get("OUT", "/data/loadavg.csv")

def burn():
    while True:
        pass

t0 = time.monotonic(); kids = []; phase = "base"
w = csv.writer(open(OUT, "w", newline="")); w.writerow(["t", "phase", "l1", "l5", "l15", "running", "total"])
last = None
while True:
    t = time.monotonic() - t0
    if phase == "base" and t >= BASE:
        phase = "on"
        for _ in range(BURN):
            pid = os.fork()
            if pid == 0:
                burn()
            kids.append(pid)
        print(f"{t:.1f}s: started {BURN} burners", flush=True)
    elif phase == "on" and t >= BASE + ON:
        phase = "off"
        for pid in kids:
            os.kill(pid, signal.SIGKILL); os.waitpid(pid, 0)
        print(f"{t:.1f}s: killed burners", flush=True)
    elif phase == "off" and t >= BASE + ON + OFF:
        break
    with open("/proc/loadavg") as f:
        v = f.read().split()
    if v[:3] != last:
        last = v[:3]
        r, tot = v[3].split("/")
        w.writerow([f"{t:.3f}", phase, v[0], v[1], v[2], r, tot])
    time.sleep(0.01)
print("done", flush=True)
