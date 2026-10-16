"""out/chain.jsonl, out/parallel.jsonl 을 표로 정리해 out/summary.txt 에 쓴다."""
import json, math, pathlib
OUT = pathlib.Path(__file__).parent / "out"
lines = []
def ci(p, n):
    h = 1.96 * math.sqrt(p * (1 - p) / n)
    return h
rows = [json.loads(l) for l in open(OUT / "chain.jsonl")] if (OUT / "chain.jsonl").exists() else []
for mode in ("random", "slotted"):
    for retry in ("none", "hop", "edge"):
        rs = [r for r in rows if r["mode"] == mode and r["retry"] == retry]
        if not rs: continue
        lines.append(f"\n[{mode}] retry={retry}")
        lines.append(" N   요청      성공률     ±95%     0.99^N    홉별 받은 요청/사용자 요청        재연결  최대공백s  rps")
        for r in rs:
            lines.append(f" {r['N']}  {r['users']:7d}  {r['success']*100:8.3f}%  {ci(r['success'], r['users'])*100:5.3f}  {r['theory_no_retry']*100:7.3f}%  "
                         f"{' '.join(f'{x:.4f}' for x in r['received_per_user']):<45} {r['reconnect']:4d}  {r['max_gap_s']:6.3f}  {r['rps']}")
            if mode == "slotted":
                lines.append(f"      속도 제한 {r.get('rate_limit')} rps, 슬롯 {r.get('slots')}개, 일정상 모든 홉이 살아 있던 시간 {r.get('time_all_up', 0)*100:.3f}%")
                lines.append(f"      홉별 다운 시간 비율 {r.get('time_down_ratio')}  요청 기준 자기 실패 비율 {r['own_fail_ratio']}  시도/사용자 요청 {r['attempts']/r['users']:.4f}")
prs = [json.loads(l) for l in open(OUT / "parallel.jsonl")] if (OUT / "parallel.jsonl").exists() else []
if prs:
    lines.append("\n[parallel] 복제본 3개 각 실패율 0.1")
    lines.append(" pick       요청      실패   성공률      ±95%    복제본 호출/요청  복제본 실제 실패 비율")
    for r in prs:
        lines.append(f" {r['pick']:9s} {r['users']:7d} {r['fail_count']:6d}  {r['success']*100:8.4f}%  {ci(r['success'], r['users'])*100:6.4f}  {r['replica_calls_per_user']:.4f}  {r['replica_fail_ratio']}")
txt = "\n".join(lines)
(OUT / "summary.txt").write_text(txt + "\n")
print(txt)

# 추가 실행: out/extra (지연 기록), out/split (보낸 순간의 상태로 나눈 성공률)
for sub in ("extra", "split"):
    f = OUT / sub / "chain.jsonl"
    if not f.exists(): continue
    lines.append(f"\n[{sub}] slotted, N=6, 1000 rps")
    lines.append(" retry  slot_ms  성공률    일정상 전부 산 시간  전부 산 순간에 보낸 비율  그때 보낸 요청 성공률  다운 중 보낸 요청 성공률  p99/p999/max ms")
    for l in open(f):
        r = json.loads(l)
        sp = (f"{r['sent_while_all_up']*100:8.3f}%  {r['success_sent_all_up']*100:8.3f}%  {r['success_sent_some_down']*100:7.2f}% ({r['sent_some_down']}건)"
              if "sent_while_all_up" in r else "      -          -          -")
        lines.append(f" {r['retry']:5s}  {r['slot_ms']:6d}  {r['success']*100:7.3f}%  {r['time_all_up']*100:8.3f}%  {sp}  "
                     f"{r['lat_ms']['p99']}/{r['lat_ms']['p999']}/{r['lat_ms']['max']}")
txt = "\n".join(lines)
(OUT / "summary.txt").write_text(txt + "\n")
print(txt)
