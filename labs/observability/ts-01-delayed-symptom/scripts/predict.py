"""쿼리 변경 3분 뒤에 지금까지의 지표만으로 증상이 언제 올지 예측한다. 결과는 증상이 오기 전에 파일로 남긴다.
모델: 조회 한 번의 처리 시간 S 는 테이블 행 수 N 에 비례한다(S = a*N). DB 는 코어 하나(cpus: 1.0).
      이용률 rho = 초당 조회 수 * S.  M/M/1 에서 응답 시간 p99 = S * ln(100) / (1 - rho).
사용: python3 scripts/predict.py <시작 유닉스 시각>"""
import json, math, os, sys, time, urllib.parse, urllib.request

P = f"http://localhost:{os.environ.get('PROM_PORT', '34090')}"
start = int(sys.argv[1])

def q(expr):
    url = P + "/api/v1/query?" + urllib.parse.urlencode({"query": expr})
    r = json.load(urllib.request.urlopen(url))["data"]["result"]
    return float(r[0]["value"][1]) if r else float("nan")

U = 'uri="/orders/recent"'
N = q('pg_stat_user_tables_n_live_tup{relname="orders"}')
g = q('deriv(pg_stat_user_tables_n_live_tup{relname="orders"}[2m])')
rps = q(f'sum(rate(http_server_requests_seconds_count{{{U}}}[1m]))')
S = q(f'sum(rate(http_server_requests_seconds_sum{{{U}}}[1m])) / sum(rate(http_server_requests_seconds_count{{{U}}}[1m]))')
rows_per_scan = q('rate(pg_stat_user_tables_seq_tup_read{relname="orders"}[1m]) / rate(pg_stat_user_tables_seq_scan{relname="orders"}[1m])')
a = S / N
now = int(time.time())

def at(rows):
    return (now - start) + (rows - N) / g

rho_now = rps * S
# p99 > 0.3 초가 되는 행 수와 rho = 1 이 되는 행 수
n_slo = next(n for n in range(int(N), int(N) * 100, 1000) if rps * a * n >= 1 or a * n * math.log(100) / (1 - rps * a * n) > 0.3)
n_sat = 1 / (rps * a)
print(f"예측 시각(시작 기준 초)   {now - start}")
print(f"orders 행 수 N           {N:.0f}")
print(f"행 증가 속도             {g:.1f} 행/초")
print(f"초당 조회                {rps:.1f}")
print(f"조회당 평균 시간 S        {S*1000:.2f} ms")
print(f"스캔 한 번에 읽은 행      {rows_per_scan:.0f}")
print(f"행 하나당 비용 a          {a*1e9:.0f} ns")
print(f"지금 이용률 rho          {rho_now:.3f}")
print(f"p99 300ms 를 넘는 행 수   {n_slo}  → 시작 기준 {at(n_slo):.0f}초 ({at(n_slo)/60:.1f}분)")
print(f"rho = 1 이 되는 행 수     {n_sat:.0f}  → 시작 기준 {at(n_sat):.0f}초 ({at(n_sat)/60:.1f}분)")
