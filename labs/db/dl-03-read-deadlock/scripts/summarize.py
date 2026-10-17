#!/usr/bin/env python3
"""out/r1..r3 원자료에서 글이 인용하는 숫자와 사실만 뽑는다."""
import re, pathlib, sys
base = pathlib.Path(__file__).resolve().parent.parent / "out"
rounds = sorted(p for p in base.glob("r[0-9]") if p.name in ("r1", "r2", "r3"))

def victim(prefix, d):
    hit = [f.stem for f in sorted(d.glob(prefix + "-s*.txt")) if "ERROR 1213" in f.read_text()]
    return ",".join(hit) or "없음"

def roll(text):
    m = re.search(r"WE ROLL BACK TRANSACTION \((\d)\)", text); return m.group(1) if m else "?"

def modes(text):
    return sorted(set(re.findall(r"trx id \d+ (lock[ _]mode [^\n]+)", text)))

for d in rounds:
    st = (d / "00-settings.txt").read_text()
    cnt = re.findall(r"lock_deadlocks \|\s+(\d+)", st)
    has_status_var = "Innodb_deadlocks" in st
    a, b = (d / "A-status.txt").read_text(), (d / "B-status.txt").read_text()
    log = (d / "errorlog.txt").read_text()
    print(f"== {d.name}")
    print(f"  1213 받은 세션    A: {victim('A', d)}   B: {victim('B', d)}")
    print(f"  WE ROLL BACK      A: ({roll(a)})   B: ({roll(b)})")
    print(f"  lock_deadlocks    시작 {cnt[0]} -> 끝 {cnt[-1]}   SHOW STATUS 'Innodb_deadlocks' 행 있음: {has_status_var}")
    print(f"  A 직후 STATUS 에 visit: {'visit' in a}   B 직후 STATUS 에 visit: {'visit' in b}  (덮어써졌으면 False)")
    print(f"  에러 로그 TRANSACTION 블록 {log.count('TRANSACTION ')}개, 'deadlock detected' {log.count('deadlock detected')}회,"
          f" 'WE ROLL BACK' {log.count('WE ROLL BACK')}회, '(1) HOLDS' {log.count('(1) HOLDS')}회")
    print(f"  A 표기: {modes(a)}")
    print(f"  B 표기: {modes(b)}")
    w = (d / "A-waiting.txt").read_text()
    sec = w.split("(THREAD_ID 기준, 함정)")[1].split("##")[0]
    rows = re.findall(r"^\|\s+(\d+) \| S .*?\|\s+(\d+) \| X,REC_NOT_GAP", sec, re.M)
    print(f"  A THREAD_ID 기준 조인 (req_thr, blk_thr): {rows}")
    sec2 = w.split("(트랜잭션 기준)")[1].split("##")[0]
    rows2 = re.findall(r"^\|\s+(\d+) \| S .*?\|\s+(\d+) \| X,REC_NOT_GAP", sec2, re.M)
    print(f"  A 트랜잭션 기준 조인 (req_conn, blk_conn): {rows2}")
    print(f"  A 막는 쪽 이력에 INSERT IGNORE: {'INSERT IGNORE' in w.split('문장 이력')[1]}")
    print(f"  B 막는 쪽 이력에 'WHERE id = 2': {'WHERE id = 2' in (d / 'B-waiting.txt').read_text().split('문장 이력')[1]}")
c = (rounds[-1] / "C-locks.txt").read_text()
print("== C (마지막 바퀴) data_locks LOCK_MODE:", sorted(set(re.findall(r"RECORD \| (\S+)\s+\|", c))))
print("   STATUS 표기:", sorted(set(re.findall(r"trx id \d+ (lock[ _]mode [^\n]+)", c))))
