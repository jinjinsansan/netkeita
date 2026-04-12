#!/bin/bash
python3 <<'PY'
import json, collections
d = json.load(open("/opt/dlogic/linebot/data/prefetch/races_20260405.json"))
c = collections.Counter(r.get("track_condition","") for r in d["races"])
print(c)
# Sample from each category
seen = set()
for r in d["races"]:
    tc = r.get("track_condition","")
    if tc not in seen:
        print(f"  {tc!r}: {r['venue']} {r['race_number']}R is_local={r.get('is_local')}")
        seen.add(tc)
PY
