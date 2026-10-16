"""신뢰성 설계 4편(가용성은 더하지 않고 곱한다)의 계산과 검산.

python3 calc_concept.py > out/concept-04.txt
표준 라이브러리만 쓴다. 몬테카를로는 시드를 고정했다.
"""
import math, random
from math import comb

random.seed(20261012)
P = print

P("== 1. 직렬: 곱 ==")
r = 0.95 * 0.96 * 0.97
P(f"0.95 x 0.96 x 0.97 = {r:.6f} -> {r*100:.4f}%  (반올림 88.46%)")
for n in range(1, 7):
    P(f"0.99^{n} = {0.99**n:.6f}")
for n in (10, 20, 50):
    P(f"0.999^{n} = {0.999**n:.6f}   0.9999^{n} = {0.9999**n:.6f}")

P("\n== 2. 곱과 비가용성 합의 차이 ==")
for avail, n in ((0.99, 6), (0.999, 10), (0.99999, 5), (0.9, 6)):
    prod = avail ** n
    approx = 1 - n * (1 - avail)
    P(f"{avail} x {n}개: 곱 {prod:.8f}  1-합 {approx:.8f}  차이 {prod-approx:.2e}")
own = 0.9999
deps = 0.99999 ** 5
P(f"자기 99.99% x 의존 99.999%^5 = {own*deps:.6%}")
year = 365 * 24 * 60
P(f"연 365일 분: {year}, 0.01% = {year*0.0001:.1f}분, 0.005% = {year*0.00005:.1f}분")

P("\n== 3. 병렬과 k-out-of-n ==")
P(f"1-(0.1)^3 = {1-0.1**3:.6f}")
def kofn(k, n, R):
    return sum(comb(n, i) * R**i * (1-R)**(n-i) for i in range(k, n+1))
def kofn_nocoef(k, n, R):
    return sum(R**i * (1-R)**(n-i) for i in range(k, n+1))
for k in (1, 2, 3):
    P(f"{k}-out-of-3, R=0.9: {kofn(k,3,0.9):.6f}   이항계수 없이: {kofn_nocoef(k,3,0.9):.6f}")
for R in (0.99, 0.999):
    P(f"R={R}: 1/3 {kofn(1,3,R):.8f}  2/3 {kofn(2,3,R):.8f}  3/3 {kofn(3,3,R):.8f}  단일 {R}")
# 검산: 몬테카를로
N = 1_000_000
cnt = {1: 0, 2: 0, 3: 0}
for _ in range(N):
    up = sum(random.random() < 0.9 for _ in range(3))
    for k in cnt:
        if up >= k: cnt[k] += 1
P("몬테카를로 100만 회(R=0.9): " + ", ".join(f"{k}/3 {cnt[k]/N:.5f}" for k in cnt))

P("\n== 4. MTBF, MTTR, 가용성 ==")
period = 30 * 24 * 60  # 분
outages = [40, 40, 40]
down = sum(outages); up = period - down; f = len(outages)
mtbf = up / f; mttr = down / f
P(f"30일 {period}분, 장애 {f}번 x 40분")
P(f"MTBF(가동 시간 합/횟수) = {mtbf:.1f}분, MTTR = {mttr:.1f}분")
P(f"MTBF/(MTBF+MTTR) = {mtbf/(mtbf+mttr):.6f}  실제 가동 비율 = {up/period:.6f}")
mtbf_wrong = period / f
P(f"기간/횟수 = {mtbf_wrong:.1f}분 -> 식에 넣으면 {mtbf_wrong/(mtbf_wrong+mttr):.6f}")
# 장애 시작 간격으로 센 MTBF (MTTF+MTTR) 를 식에 넣는 실수
mtbf_cycle = mtbf + mttr
P(f"장애 시작 간격 평균 = MTTF+MTTR = {mtbf_cycle:.1f}분 -> 식에 넣으면 {mtbf_cycle/(mtbf_cycle+mttr):.6f}, 올바른 식 (간격-MTTR)/간격 = {(mtbf_cycle-mttr)/mtbf_cycle:.6f}")
# 같은 가용성, 다른 모양
for f2, d2 in ((1, 120), (12, 10), (120, 1)):
    P(f"30일에 {f2}번 x {d2}분: 가용성 {1-f2*d2/period:.6f}, MTBF {(period-f2*d2)/f2:.0f}분")

P("\n== 5. 재시도가 곱을 되돌리는 정도 (홉당 성공 0.99, 시도마다 독립) ==")
p = 0.99
def chain_no_retry(n):
    return p ** n
def chain_edge_retry(n, r=1):
    s = p ** n
    succ = 1 - (1 - s) ** (r + 1)
    # 맨 끝 홉이 받는 요청 수 기대값(사용자 요청 1개당)
    # 시도 한 번이 홉 n 까지 도달할 확률 p^(n-1), 시도 횟수 기대값 1 + (1-s) (r=1)
    attempts = sum((1 - s) ** i for i in range(r + 1))
    return succ, attempts, attempts * p ** (n - 1)
def chain_hop_retry(n, r=1):
    # 홉 k 는 자기 실패(1-p)를 먼저 판정하고, 살아 있으면 다음 홉 호출을 최대 r+1 번 시도
    # S[k]: 홉 k 로 들어온 요청 하나의 성공 확률, C[k]: 그 요청 하나가 맨 끝 홉에 만드는 요청 수 기대값
    S = [0.0] * (n + 2); C = [0.0] * (n + 2)
    S[n] = p; C[n] = 1.0
    for k in range(n - 1, 0, -1):
        d = S[k + 1]
        att = sum((1 - d) ** i for i in range(r + 1))   # 다음 홉 호출 횟수 기대값(살아 있을 때)
        S[k] = p * (1 - (1 - d) ** (r + 1))
        C[k] = p * att * C[k + 1]
    # 홉 1 이 받는 요청 수는 1, 각 홉이 받는 요청 수 기대값
    recv = [0.0] * (n + 2); recv[1] = 1.0
    for k in range(1, n):
        d = S[k + 1]
        att = sum((1 - d) ** i for i in range(r + 1))
        recv[k + 1] = recv[k] * p * att
    return S[1], recv[1:n + 1]
P(" N  재시도없음   끝에서1회(성공, 시도 수)   홉마다1회(성공, 홉별 받은 요청 수)")
for n in range(1, 7):
    a = chain_no_retry(n)
    b, att, _ = chain_edge_retry(n)
    c, recv = chain_hop_retry(n)
    P(f"{n:2d}  {a:.6f}   {b:.6f} x{att:.4f}         {c:.6f}  " + " ".join(f"{x:.4f}" for x in recv) + f"  합 {sum(recv)/n:.4f}배")
# 고장이 지속형이면(같은 인스턴스가 계속 실패) 재시도는 무력
P(f"지속형 고장: 홉마다 시간의 1% 동안 완전히 죽어 있으면 재시도 1회 후에도 그 1%는 그대로 실패 -> 0.99^6 = {0.99**6:.6f}")

P("\n== 6. 재시도 몬테카를로(N=6, 100만 요청, 홉마다 1회) ==")
def sim_hop(k, n, cnt):
    cnt[k] += 1
    if random.random() >= p: return False
    if k == n: return True
    for _ in range(2):
        if sim_hop(k + 1, n, cnt): return True
    return False
cnt = [0] * 8; ok = 0; M = 1_000_000
for _ in range(M):
    ok += sim_hop(1, 6, cnt)
P(f"성공 {ok/M:.6f}, 홉별 받은 요청 수/사용자 요청: " + " ".join(f"{c/M:.4f}" for c in cnt[1:7]))

P("\n== 7. 섞인 구성: 게이트웨이 99.95% -> 앱 3대 중 2대 필요(각 99%) -> DB 99.95% ==")
gw, db = 0.9995, 0.9995
app2 = kofn(2, 3, 0.99)
app1 = kofn(1, 3, 0.99)
P(f"앱 계층 2-out-of-3 = {app2:.6f}, 전체 = {gw*app2*db:.6f}")
P(f"앱 계층을 1-out-of-3로 잘못 셌을 때 = {gw*app1*db:.6f}")
P(f"게이트웨이와 DB만의 곱 = {gw*db:.6f}  -> 전체 비가용성 중 앱 계층 몫 = {(1-app2)/(1-gw*app2*db):.1%}")
P(f"팬아웃: 위젯 10개를 모두 받아야 페이지 성공, 각 99% -> 0.99^10 = {0.99**10:.6f}")
