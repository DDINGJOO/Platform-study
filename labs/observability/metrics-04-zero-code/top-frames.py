"""Pyroscope render API 에서 플레임 그래프 데이터를 받아 self 상위 함수와, 이름에 KEY 가 든 프레임의 total 을 찍는다.
사용: python3 top-frames.py http://localhost:21440 '<프로파일 타입>{service_name="shop"}' <from> <until> [N] [KEY]
  from/until 은 유닉스 초 또는 now-5m 같은 상대값. total 은 한 스택에 같은 함수가 두 번 나오면 두 번 센다."""
import json, sys, urllib.parse, urllib.request
base, q, frm, until = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
n = int(sys.argv[5]) if len(sys.argv) > 5 else 15
url = f"{base}/pyroscope/render?" + urllib.parse.urlencode({"query": q, "from": frm, "until": until})
d = json.load(urllib.request.urlopen(url))
fb = d["flamebearer"]; names = fb["names"]; levels = fb["levels"]
selfs, totals = {}, {}
for lvl in levels:
    for i in range(0, len(lvl), 4):
        off, tot, slf, ni = lvl[i:i+4]
        nm = names[ni]
        selfs[nm] = selfs.get(nm, 0) + slf
        totals[nm] = totals.get(nm, 0) + tot
T = fb["numTicks"]
print("numTicks", T, "units", d.get("metadata", {}).get("units"), "sampleRate", d.get("metadata", {}).get("sampleRate"))
print("-- self top")
for nm, v in sorted(selfs.items(), key=lambda x: -x[1])[:n]:
    print(f"{v/T*100:6.2f}%  {nm}")
key = sys.argv[6] if len(sys.argv) > 6 else "lab.zc"
print(f"-- total for frames containing {key}")
for nm, v in sorted(totals.items(), key=lambda x: -x[1]):
    if key in nm: print(f"{v/T*100:6.2f}%  {nm}")
