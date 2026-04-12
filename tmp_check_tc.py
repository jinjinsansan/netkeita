import json
with open("/root/dlogic-agent/data/prefetch/races_20260405.json") as f:
    d = json.load(f)

# Samples
for r in d["races"]:
    v = r.get("venue")
    tc = r.get("track_condition")
    is_local = r.get("is_local", False)
    print(f"{'NAR' if is_local else 'JRA'} {v}: track_condition={repr(tc)}")
    if is_local:
        # Check one more
        break

# Check how many races have meaningful track_condition
jra_tc = set()
nar_tc = set()
for r in d["races"]:
    if r.get("is_local"):
        nar_tc.add(r.get("track_condition", ""))
    else:
        jra_tc.add(r.get("track_condition", ""))
print(f"\nJRA track_conditions: {jra_tc}")
print(f"NAR track_conditions: {nar_tc}")
