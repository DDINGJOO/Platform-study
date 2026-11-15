from pathlib import Path
import json
r=Path(__file__).resolve().parent
rows=[json.loads(x) for x in (r/'keepalive.jsonl').read_text().splitlines()]
a=json.loads((r/'results.json').read_text())
lines=['Persistent HTTP connection (one TCP source port)']
for x in rows:lines.append(f"request={x['i']:02d} elapsed={x['time']-rows[0]['time']:.3f}s status={x['status']} source_port={x['local'][1]}")
lines+=['','New TCP connections after ingress deny:']
for x in a:
 if x['phase'] in ['deny-new-a','deny-new-b']:lines.append(f"{x['phase']}: exit={x['exit']} (blocked)")
(r/'connection-summary.txt').write_text('\n'.join(lines)+'\n')
lines=['NetworkPolicy result matrix (observed exit codes)','phase                                    exit  success']
for x in a:lines.append(f"{x['phase']:40} {x['exit']:>4}  {str(x['observed_success']):>7}")
(r/'policy-matrix.txt').write_text('\n'.join(lines)+'\n')
