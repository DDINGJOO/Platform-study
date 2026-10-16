"""out/*.jsonl 을 표로 정리해 out/summary.txt 에 쓴다."""
import json, math, pathlib, statistics as st
OUT = pathlib.Path(__file__).parent / "out"
L = []
def rows(n):
    f = OUT / f"{n}.jsonl"
    return [json.loads(l) for l in open(f)] if f.exists() else []

for r in rows("checks"):
    L.append(f"\n[C] 검사 종류, r1 상태 = {r['fault']}, {r['seconds']}초, listen마다 초당 {r['rate_per_listen']}건 (최대 공백 {r['max_gap_s']}s)")
    L.append(" listen        보냄   실패   실패율    마지막 실패(s)  HAProxy DOWN 판정(s)")
    for k, v in r["listens"].items():
        L.append(f" {k:12s} {v['sent']:5d} {v['failed']:6d}  {v['fail_ratio']*100:6.2f}%   {v['last_fail_s']}   {v['hap_marked_down_s']}")

fo = rows("failover")
for fault in ("down", "hang"):
    rs = [r for r in fo if r["fault"] == fault]
    if not rs: continue
    L.append(f"\n[B] 액티브-스탠바이 전환, a 상태 = {fault}, 시행 {len(rs)}번, listen마다 초당 {rs[0]['rate_per_listen']}건 (최대 공백 {max(r['max_gap_s'] for r in rs)}s)")
    L.append(" listen                 실패 건수(최소/중앙/최대)   마지막 실패 s(최소/중앙/최대)   DOWN 판정 s(최소/중앙/최대)")
    for l in rs[0]["listens"]:
        f = [r["listens"][l]["failed"] for r in rs]
        lf = [r["listens"][l]["last_fail_s"] for r in rs if r["listens"][l]["last_fail_s"] is not None]
        dn = [r["listens"][l]["hap_marked_down_s"] for r in rs if r["listens"][l]["hap_marked_down_s"] is not None]
        fmt = lambda xs: f"{min(xs):.2f}/{st.median(xs):.2f}/{max(xs):.2f}" if xs else "-"
        L.append(f" {l:22s} {min(f):4d}/{st.median(f):6.1f}/{max(f):4d}        {fmt(lf):20s}        {fmt(dn)}  (DOWN {len(dn)}/{len(rs)})")

for r in rows("shared"):
    a, b = r["noretry_9201"], r["retry_9202"]
    L.append(f"\n[A] beta={r['beta']} Q={r['Q']} 슬롯 {r['slots']}개 x {r['slot_ms']}ms (최대 공백 {r['max_gap_s']}s, 슬롯 지연 최대 {r['slot_overrun_ms_max']}ms)")
    L.append(f"   이론 가용성 {r['theory_availability']*100:.3f}%   실제 일정: 하나라도 산 슬롯 {r['slot_any_up_ratio']*100:.3f}%, 공통 원인 슬롯 {r['slot_ccf_ratio']*100:.2f}%, 복제본별 다운 {[round(x*100,2) for x in r['slot_replica_down_ratio']]}")
    for name, x in (("재시도 없음 9201", a), ("retry-on+redispatch 9202", b)):
        h = 1.96 * math.sqrt(x['success'] * (1 - x['success']) / x['requests'])
        L.append(f"   {name:24s} 요청 {x['requests']:6d}  성공 {x['success']*100:7.3f}% ±{h*100:.3f}  하나라도 산 동안 성공 {x['success_when_any_up']*100:7.3f}%  모두 죽은 동안 성공 {x['success_when_all_down']*100:.2f}%")
txt = "\n".join(L)
(OUT / "summary.txt").write_text(txt + "\n")
print(txt)
