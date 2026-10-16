#!/usr/bin/env python3
"""git bisect run 이 커밋마다 부르는 시험. 저장소 밖에 두고 절대 경로로 부른다.

종료 코드: 0 정상, 1 고장, 125 시험 불가(빌드가 깨진 커밋).

환경변수
  CHECK_LOG     호출마다 "커밋번호 판정" 한 줄을 덧붙일 파일(단계 수를 세는 데 쓴다)
  FLAKE_P       시험이 거짓말할 확률(기본 0)
  FLAKE_MODE    sym       정상/고장 어느 쪽이든 p 확률로 뒤집힌다
                good-only 정상 커밋만 p 확률로 잘못 실패한다(흔한 flaky 테스트)
  VOTE          1(기본) | maj3 (세 번 돌려 다수결) | all3 (세 번 모두 실패해야 고장)
  TRIAL         난수 시드의 일부. 같은 TRIAL·같은 커밋이면 같은 결과가 나온다(재현용)
  APPLY_FIX     "rounding" 이면 시험 전에 반올림 회귀를 고친 채로 시험한다
                (첫 번째 원인을 고친 상태로 두 번째 원인을 찾을 때)
"""
import hashlib, os, re, sys

here = os.getcwd()
src = open(os.path.join(here, "src/pricing.py")).read()
commit_no = int(open(os.path.join(here, "src/COMMIT_NO")).read())
build = open(os.path.join(here, "src/BUILD")).read().strip()
log = os.environ.get("CHECK_LOG")


def record(verdict):
    if log:
        with open(log, "a") as f:
            f.write(f"{commit_no} {verdict}\n")


if build != "ok":
    record("skip")
    sys.exit(125)

if os.environ.get("APPLY_FIX") == "rounding":
    src = re.sub(r'ROUNDING = "\w+"', 'ROUNDING = "half_up"', src)

ns = {}
exec(src, ns)
truly_bad = ns["amount"](1999, 3) != 6597   # 1999원 x 3개 + 부가세 10% = 6596.7 -> 6597

p = float(os.environ.get("FLAKE_P", "0"))
mode = os.environ.get("FLAKE_MODE", "sym")
trial = os.environ.get("TRIAL", "0")


def one_run(attempt):
    """시험 한 번. 흔들림이 있으면 커밋·시도·trial 로 정해지는 난수로 결과를 뒤집는다."""
    h = hashlib.sha256(f"{trial}:{commit_no}:{attempt}".encode()).digest()
    u = int.from_bytes(h[:8], "big") / 2**64
    flip = u < p
    if mode == "good-only":
        return True if truly_bad else flip          # 고장이면 늘 실패, 정상이면 가끔 실패
    return (not truly_bad) if flip else truly_bad    # 양쪽 다 뒤집힐 수 있다


vote = os.environ.get("VOTE", "1")
if vote == "1":
    bad = one_run(0)
else:
    runs = [one_run(i) for i in range(3)]
    bad = sum(runs) >= 2 if vote == "maj3" else all(runs)

record("bad" if bad else "good")
sys.exit(1 if bad else 0)
