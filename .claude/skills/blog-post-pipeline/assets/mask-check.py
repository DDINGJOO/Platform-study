#!/usr/bin/env python3
"""발행 전 정보 노출 검사 — 공개 블로그에 나가면 안 되는 값을 찾는다.

두 종류를 본다.
  1) 무설정 일반 위험 패턴 — 계정 ID, 토큰 접두사, 이메일, 전역 고유 이름 등
  2) --extra 로 넘긴 조직 고유 목록 — 회사명·내부 저장소명처럼 이 스크립트가 알 수 없는 것

조직 고유 목록은 **저장소에 커밋하지 않는다.** 그 파일 자체가 노출이 된다.
`~/.config/blog-mask.txt` 처럼 저장소 밖에 두고 경로로 넘긴다.
형식은 줄 단위 `찾을문자열=자리표시자` (자리표시자 생략 시 검사만 하고 치환은 안 한다).

    python3 mask-check.py 글.html                          # 일반 패턴만 검사
    python3 mask-check.py 글.html --extra ~/.config/blog-mask.txt
    python3 mask-check.py 글.html --extra ... --apply      # 치환까지
    python3 mask-check.py --staged --extra ...             # pre-commit: 스테이징된 내용 + 경로
    python3 mask-check.py --all --extra ...                # 추적 중인 전 파일 + 경로

--staged / --all 은 **경로도 검사한다.** 폴더명에 조직 약어가 남아 공개된 적이 있다(f11ab62).
PNG 같은 바이너리는 내용을 읽을 수 없으므로 경로만 본다.

오탐(임계값·날짜 등)은 저장소의 `.mask-allow` 에 한 줄씩 적어 통과시킨다.
허용 목록은 [일반] 패턴에만 적용된다. 조직 목록(--extra) 적중은 언제나 막는다.

원칙: 값을 지우지 말고 **자리표시자로 바꿔 모양이 보이게** 한다.
`repo:{조직}@{조직ID}/{저장소}@{저장소ID}` 는 실제 값보다 독자에게 더 유용하다.
"""
import argparse
import os
import re
import subprocess
import sys

# 무설정으로 도는 일반 위험 패턴. 오탐이 있어도 사람이 판정하면 되므로 넓게 잡는다.
GENERIC = [
    ("AWS 계정 ID(12자리)", r"(?<!\d)\d{12}(?!\d)"),
    ("8자리 이상 연속 숫자(조직·저장소 ID 가능)", r"(?<!\d)\d{8,}(?!\d)"),
    ("GitHub 토큰", r"\bgh[pousr]_[A-Za-z0-9]{16,}"),
    ("AWS 액세스 키", r"\bAKIA[0-9A-Z]{16}\b"),
    ("이메일", r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b"),
    ("S3 버킷 ARN", r"arn:aws:s3:::[\w.-]+"),
    ("사설 IP", r"\b(?:10|172|192)\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
    ("내부 URL(notion/atlassian/slack)", r"https?://[\w.-]*(?:notion|atlassian|slack)[\w./?=-]*"),
]


def load_extra(path):
    pairs = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        needle, _, placeholder = line.partition("=")
        pairs.append((needle.strip(), placeholder.strip() or None))
    return pairs


def load_allow(path):
    if not path or not os.path.exists(path):
        return set()
    return {l.split("#")[0].strip() for l in open(path, encoding="utf-8")} - {""}


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, check=True).stdout


def git_sources(staged):
    """(경로, 내용 또는 None) 을 낸다. 내용이 None 이면 바이너리라 경로만 본다."""
    if staged:
        paths = git("diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR")
    else:
        paths = git("ls-files", "-z")
    for p in paths.decode("utf-8").split("\0"):
        if not p:
            continue
        raw = git("show", f":{p}") if staged else open(p, "rb").read()
        try:
            yield p, raw.decode("utf-8")
        except UnicodeDecodeError:
            yield p, None


def scan(text, extra, allow):
    hits = []
    for label, pat in GENERIC:
        for m in sorted(set(re.findall(pat, text)) - allow):
            hits.append(f"  [일반] {label}: {m}")
    for needle, placeholder in extra:
        n = text.count(needle)
        if n:
            hits.append(f"  [조직] {needle}: {n}회  -> {placeholder or '(자리표시자 미지정)'}")
    return hits


def main_git(a, extra, allow):
    found_any = False
    for path, text in git_sources(a.staged):
        hits = [h.replace("  [", "  [경로·", 1) for h in scan(path, extra, allow)]
        if text is not None:
            hits += scan(text, extra, allow)
        if hits:
            found_any = True
            print(f"\n[{path}]")
            print("\n".join(hits))
    if found_any:
        print("\n※ 막았다. 자리표시자로 바꾸거나, 오탐이면 .mask-allow 에 값을 추가할 것.")
        sys.exit(1)
    print("마스킹 검사 통과")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--extra", help="조직 고유 목록 파일 (저장소 밖에 둘 것)")
    ap.add_argument("--apply", action="store_true", help="자리표시자로 치환한다")
    ap.add_argument("--staged", action="store_true", help="스테이징된 내용과 경로를 검사한다")
    ap.add_argument("--all", action="store_true", help="추적 중인 전 파일과 경로를 검사한다")
    ap.add_argument("--allow", default=".mask-allow", help="[일반] 오탐 허용 목록")
    a = ap.parse_args()

    extra = load_extra(a.extra) if a.extra else []
    allow = load_allow(a.allow)

    if a.staged or a.all:
        return main_git(a, extra, allow)
    if not a.files:
        ap.error("파일을 주거나 --staged / --all 을 쓸 것")

    found_any = False

    for f in a.files:
        h = open(f, encoding="utf-8").read()
        hits = []

        for label, pat in GENERIC:
            for m in sorted(set(re.findall(pat, h)) - allow):
                hits.append(f"  [일반] {label}: {m}")

        changed = h
        for needle, placeholder in extra:
            n = changed.count(needle)
            if not n:
                continue
            if a.apply and placeholder:
                changed = changed.replace(needle, placeholder)
                hits.append(f"  [치환] {needle} -> {placeholder} ({n}회)")
            else:
                mark = placeholder or "(자리표시자 미지정)"
                hits.append(f"  [조직] {needle}: {n}회  -> {mark}")

        print(f"\n[{f.split('/')[-1][:48]}]")
        if hits:
            found_any = True
            print("\n".join(hits))
        else:
            print("  깨끗함")

        if a.apply and changed != h:
            open(f, "w", encoding="utf-8").write(changed)
            print(f"  => 저장됨 ({len(h):,}자 -> {len(changed):,}자)")

    if found_any and not a.apply:
        print("\n※ [일반] 항목은 오탐일 수 있다 (버전 번호, 타임스탬프 등). 사람이 판정할 것.")
        sys.exit(1)


if __name__ == "__main__":
    main()
