import re, subprocess, sys
repo, rev = sys.argv[1], sys.argv[2]
files = subprocess.run(["git","-C",repo,"ls-tree","-r","--name-only",rev,"--","src/main/java"],capture_output=True,text=True).stdout.split()
pat = re.compile(r'LettuceAssert\.(\w+)\(\s*([A-Za-z_]\w*)\s*,\s*"([A-Za-z]\w*)')
out=[]
for f in files:
    if not f.endswith(".java"): continue
    for i,l in enumerate(subprocess.run(["git","-C",repo,"show",f"{rev}:{f}"],capture_output=True,text=True).stdout.splitlines()):
        m=pat.search(l)
        if not m: continue
        var,subj=m.group(2),m.group(3)
        if var.lower() not in subj.lower() and subj.lower() not in var.lower():
            out.append((f,i+1,var,subj,l.strip()))
print("mismatch:",len(out))
for o in out:
    if o[2] in ("to","reauthenticateBehavior") or "Reuth" in o[3]: print("HIT",o)
import collections
print(collections.Counter((o[2],o[3]) for o in out).most_common(8))
