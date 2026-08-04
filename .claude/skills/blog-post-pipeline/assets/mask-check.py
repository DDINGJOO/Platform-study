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

원칙: 값을 지우지 말고 **자리표시자로 바꿔 모양이 보이게** 한다.
`repo:{조직}@{조직ID}/{저장소}@{저장소ID}` 는 실제 값보다 독자에게 더 유용하다.
"""
import argparse
import re
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--extra", help="조직 고유 목록 파일 (저장소 밖에 둘 것)")
    ap.add_argument("--apply", action="store_true", help="자리표시자로 치환한다")
    a = ap.parse_args()

    extra = load_extra(a.extra) if a.extra else []
    found_any = False

    for f in a.files:
        h = open(f, encoding="utf-8").read()
        hits = []

        for label, pat in GENERIC:
            for m in set(re.findall(pat, h)):
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
