#!/usr/bin/env python3
"""Select actual output lines; replace only a lab Pod IP and normalize spaces."""
from pathlib import Path
import json, re

r=Path(__file__).resolve().parent
records=json.loads((r/'commands.json').read_text())
snapshot=next(json.loads(x['stdout']) for x in records if ' kubectl get pods -n calico-blog-53 -o json' in x['command'])
target=next(p['status']['podIP'] for p in snapshot['items'] if p['metadata']['name']=='target')
parts=[];mapping={}
for n in [1452,1453]:
    p=r/f'06-ping-{n}.txt';lines=p.read_text().splitlines()
    selected=[i for i,x in enumerate(lines) if i>=2 and not x.startswith('rtt ')]
    parts.append('\n'.join(lines[i] for i in selected))
    mapping[p.name]=[i+1 for i in selected]
(r/'capture-mtu.txt').write_text('\n\n'.join(parts).replace(target,'{대상 Pod IP}')+'\n')
p=r/'07-isolated-pmtud.txt';lines=p.read_text().splitlines()
start=next(i for i,x in enumerate(lines) if x.startswith('=== ICMP fragmentation'))
end=next(i for i,x in enumerate(lines) if x.startswith('=== source capture'))
selected=[]
for i in range(start,end):
    x=lines[i]
    if (x.startswith(('===','PING','108 bytes','1 packets','http=','received=','exit_code='))
        or ('DROP' in x and not x.startswith('$')) or 'cache expires' in x):
        selected.append(i)
out=[]
for i in selected:
    line=lines[i]
    if 'DROP' in line: line=re.sub(r'\s+',' ',line).strip()
    out.append(line)
(r/'capture-pmtud.txt').write_text('\n'.join(out)+'\n')
mapping[p.name]=[i+1 for i in selected]
(r/'capture-line-map.json').write_text(json.dumps(mapping,indent=2)+'\n')
