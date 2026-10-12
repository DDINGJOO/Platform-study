"""클러스터 안에서 stock Service 를 50ms 마다 직접 불러, 요청마다 어느 파드가 받았는지/어떻게 실패했는지 남긴다.
loadgen 파드 안에서 돌린다:  kubectl exec -i deploy/loadgen -- python - < scripts/probe.py
출력: 시작부터 경과 초, 결과(파드 이름 또는 실패 종류), 걸린 ms"""
import socket, threading, time, urllib.request, urllib.error, sys
DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 20
t0 = time.time()
lock = threading.Lock()
def one():
    s = time.time()
    try:
        with urllib.request.urlopen("http://stock/stock", timeout=1.0) as r:
            out = r.read().decode().split()[-1]
    except Exception as e:
        reason = getattr(e, "reason", e)
        out = "timeout" if "timed out" in str(reason) else type(reason).__name__
    with lock:
        print(f"{s - t0:6.2f}\t{out}\t{(time.time() - s) * 1000:.0f}", flush=True)
while time.time() - t0 < DUR:
    threading.Thread(target=one, daemon=True).start()
    time.sleep(0.05)
time.sleep(1.2)
