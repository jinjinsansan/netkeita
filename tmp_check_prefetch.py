import json
d = json.load(open("/root/dlogic-agent/data/prefetch/races_20260404.json"))
r = d["races"][0]
print("race_id:", r.get("race_id"))
print("race_id_netkeiba:", r.get("race_id_netkeiba"))
print("venue:", r.get("venue"))
print("race_number:", r.get("race_number"))
# Show all top-level keys
print("keys:", list(r.keys())[:20])
