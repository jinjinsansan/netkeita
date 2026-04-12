python3 << 'PYEOF'
import json, glob
files = sorted(glob.glob("/opt/dlogic/linebot/data/prefetch/internet_predictions_*.json"), reverse=True)
for f in files:
    d = json.load(open(f))
    print(f"File: {f}")
    print(f"Keys: {list(d.keys())}")
    print(f"race_name: {d.get('race_name','')}")
    dt = d.get("display_text","")
    print(f"display_text (first 400 chars):\n{dt[:400]}")
    yt = d.get("youtube",{})
    ks = d.get("keiba_site",{})
    print(f"YouTube horses: {len(yt.get('horses',[]))}")
    print(f"Keiba site horses: {len(ks.get('horses',[]))}")
PYEOF
