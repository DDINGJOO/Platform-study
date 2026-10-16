"""신뢰성 설계 5편(이중화의 곱셈은 고장이 서로 모를 때만 성립한다)의 계산과 검산.

python3 calc_concept.py > out/concept-05.txt
표준 라이브러리만 쓴다. 몬테카를로는 시드를 고정했다.
"""
import random
from math import comb
random.seed(5)
P = print

P("== 1. 베타 인자 모형: 복제본 n개, 한 대의 비가용성 Q, 그중 공통 원인 비율 beta ==")
P("공통 원인 사건 확률 = beta*Q (일어나면 n대 모두 다운)")
P("독립 고장 확률 q 는 한 대의 비가용성이 정확히 Q 가 되게 맞춘다: q = (Q - beta*Q)/(1 - beta*Q)")
P("시스템 비가용성 = beta*Q + (1 - beta*Q) * q^n")
def sys_unavail(Q, beta, n=3):
    c = beta * Q
    q = (Q - c) / (1 - c)
    return c + (1 - c) * q ** n, q
def nureg(Q, beta, n=3):
    # NUREG/CR-5485 의 근사형: 독립 (1-beta)Q, 공통 beta*Q, 희귀 사건 근사로 더한다
    return beta * Q + ((1 - beta) * Q) ** n
for Q in (0.1, 0.01, 0.001):
    P(f"\nQ = {Q} (한 대 가용성 {1-Q:.3%}), n = 3")
    P(" beta    시스템 가용성   (근사형)     9의 개수 감소")
    import math
    base = sys_unavail(Q, 0)[0]
    for beta in (0, 0.01, 0.05, 0.1, 0.2, 0.5, 1.0):
        u, q = sys_unavail(Q, beta)
        P(f" {beta:<5}  {1-u:.6%}   ({1-nureg(Q,beta):.6%})   비가용성 {u/base:,.1f}배")
# 몬테카를로 검산 (Q=0.1, beta=0.1)
Q, beta, n = 0.1, 0.1, 3
c = beta * Q; q = (Q - c) / (1 - c)
M = 2_000_000; alldown = 0; one = 0
for _ in range(M):
    if random.random() < c:
        alldown += 1; one += 1; continue
    s = [random.random() < q for _ in range(n)]
    one += s[0]
    alldown += all(s)
P(f"\n몬테카를로 {M:,}회 (Q=0.1, beta=0.1): 한 대 비가용성 {one/M:.5f}, 시스템 비가용성 {alldown/M:.6f}, 식 {sys_unavail(0.1,0.1)[0]:.6f}")

P("\n== 2. 감지 시간: HAProxy inter x fall ==")
P("고장 시점은 검사 주기 안에서 균일하게 떨어진다고 가정. 첫 실패 검사까지 0~inter, 그 뒤 (fall-1)번 더 실패해야 DOWN")
P("fastinter 를 주면 '내려가는 중' 상태의 간격이 fastinter 가 된다")
for inter, fall, fast in ((2.0, 3, None), (1.0, 3, None), (2.0, 3, 0.5), (1.0, 2, None), (0.5, 3, None), (5.0, 3, None)):
    step = fast if fast else inter
    lo = (fall - 1) * step; hi = inter + (fall - 1) * step; mean = inter / 2 + (fall - 1) * step
    P(f" inter {inter}s fall {fall} fastinter {fast}: 감지 {lo:.1f} ~ {hi:.1f}초, 평균 {mean:.2f}초")

P("\n== 3. 감지 시간이 가용성에 주는 영향 ==")
month = 30 * 24 * 3600
budget = month * 0.0001
P(f"30일 99.99% 예산 = {budget:.0f}초 = {budget/60:.2f}분")
for fails_per_month, detect, frac, label in (
        (3, 5, 1.0, "액티브-스탠바이, 고장마다 전체 트래픽"),
        (3, 5, 1/3, "액티브-액티브 3대, 고장 난 한 대 몫"),
        (3, 30, 1.0, "액티브-스탠바이, 감지 30초"),
        (1, 20*60, 1/3, "회색 고장: TCP 검사가 못 잡아 사람이 20분 뒤 발견, 3대 중 1대"),
):
    lost = fails_per_month * detect * frac
    P(f" {label}: 실패 요청 비중 환산 {lost:.1f}초 = 예산의 {lost/budget:.1%}")

P("\n== 4. 용량 전제: 3대 중 몇 대가 있어야 피크를 받나 (한 대 가용성 0.99) ==")
def kofn(k, n, R):
    return sum(comb(n, i) * R**i * (1-R)**(n-i) for i in range(k, n+1))
for k in (1, 2, 3):
    P(f" {k}대 필요: {kofn(k,3,0.99):.6%}")
P(f" 4대 중 3대 필요: {kofn(3,4,0.99):.6%}   5대 중 3대 필요: {kofn(3,5,0.99):.6%}")

P("\n== 5. 셀: 셀 10개, 셀 하나가 배포로 깨질 때 ==")
for cells in (1, 4, 10):
    P(f" 셀 {cells}개: 나쁜 배포가 첫 셀에서 멈추면 영향 받는 요청 {1/cells:.0%}")
P(" 셔플 샤딩: 워커 8대에서 2대씩 고르는 조합 수 =", comb(8, 2), "-> 한 조합의 몫 1/28 = %.2f%%" % (100/28))
