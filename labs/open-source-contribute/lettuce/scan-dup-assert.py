import re, subprocess, sys
repo, rev = sys.argv[1], sys.argv[2]
files = subprocess.run(["git","-C",repo,"ls-tree","-r","--name-only",rev,"--","src/main/java"],capture_output=True,text=True).stdout.split()
pat = re.compile(r'^\s*LettuceAssert\.(\w+)\(\s*([\w.()]+?)\s*,')
blocks=[]; staged=0
for f in files:
    if not f.endswith(".java"): continue
    src = subprocess.run(["git","-C",repo,"show",f"{rev}:{f}"],capture_output=True,text=True).stdout.splitlines()
    cur=[]
    for i,l in enumerate(src+[""]):
        m=pat.match(l)
        if m: cur.append((i+1,m.group(1),m.group(2),l.strip())); continue
        if len(cur)>1:
            seen={}
            for ln,meth,arg,txt in cur: seen.setdefault(arg,[]).append((ln,meth,txt))
            for arg,hits in seen.items():
                if len(hits)>1:
                    meths=[h[1] for h in hits]
                    same = len(set(meths))<len(meths)
                    blocks.append((f,arg,hits,same))
        cur=[]
print("blocks with repeated identifier:",len(blocks))
print("  of which same method repeated (e.g. notNull twice):",sum(1 for b in blocks if b[3]))
for f,arg,hits,same in blocks:
    if same: print("SAME", f, arg, [h[0] for h in hits]); [print("    ",h[2]) for h in hits]
