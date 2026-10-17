"""알람 규칙 평가. 입력은 1분 간격 누적 카운터 표본 리스트(재시작으로 0 이 되면 리셋으로 본다).

규칙은 모두 '창 안의 증가량'으로 계산한다. 누적값 자체에 임계를 걸지 않는다.
알람 횟수는 '꺼짐 → 켜짐' 전이 수(에피소드)다. 켜진 채 이어지는 동안은 한 번으로 센다.
"""


def increments(samples):
    """누적 표본 → 분당 증가량. 값이 줄면(재시작, 리셋) 그 표본 값 자체를 증가로 본다."""
    out = [0]
    for prev, cur in zip(samples, samples[1:]):
        out.append(cur - prev if cur >= prev else cur)
    return out


def naive_increments(samples):
    return [0] + [cur - prev for prev, cur in zip(samples, samples[1:])]


def window_sum(inc, end, width):
    return sum(inc[max(0, end - width + 1):end + 1])


def episodes(states):
    n, prev = 0, False
    for s in states:
        if s and not prev:
            n += 1
        prev = s
    return n


def first_true(states, times):
    for s, t in zip(states, times):
        if s:
            return t
    return None


def rule_consecutive(inc, win=5, n=3, threshold=1):
    """R1: win분 창(겹치지 않게 win분마다 평가)의 증가 >= threshold 가 n 구간 연속이면 켜진다."""
    times, states, streak = [], [], 0
    for end in range(win - 1, len(inc), win):
        hit = window_sum(inc, end, win) >= threshold
        streak = streak + 1 if hit else 0
        times.append(end)
        states.append(streak >= n)
    return times, states


def rule_window(inc, win, threshold, step):
    """창 win분의 증가 >= threshold 이면 켜진다. step분마다 평가(슬라이딩)."""
    times, states = [], []
    for end in range(0, len(inc), step):   # 시작 직후는 덜 찬 창(그 전은 0건으로 본다)
        times.append(end)
        states.append(window_sum(inc, end, win) >= threshold)
    return times, states


RULES = [
    ("R1 연속형: 5분 창 >=1 이 3구간 연속", lambda inc: rule_consecutive(inc, 5, 3, 1)),
    ("R2 버스트: 5분 창 >=3", lambda inc: rule_window(inc, 5, 3, 1)),
    ("R3 지속: 6시간 창 >=6 (시간당 1건 이상 지속)", lambda inc: rule_window(inc, 360, 6, 5)),
    ("R4 존재: 24시간 창 >=1 (티켓)", lambda inc: rule_window(inc, 1440, 1, 60)),
]
