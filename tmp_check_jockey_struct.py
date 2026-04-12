import json

with open("/opt/dlogic/backend/data/all_nar_jockey_knowledge_20260310.json") as f:
    data = json.load(f)

jockeys = data["jockeys"]
print(f"Total: {len(jockeys)}")

# Sample jockey full structure
for name in ["佐原秀泰", "林悠翔", "坂井瑛音"]:
    if name in jockeys:
        j = jockeys[name]
        print(f"\n=== {name} ===")
        print(f"  Keys: {list(j.keys())}")
        for k, v in j.items():
            if isinstance(v, (list, dict)):
                print(f"  {k}: {type(v).__name__} len={len(v)}")
                if isinstance(v, dict) and len(v) > 0:
                    sample_key = list(v.keys())[0]
                    print(f"    Sample key: {sample_key} = {v[sample_key]}")
                elif isinstance(v, list) and len(v) > 0:
                    print(f"    Sample[0]: {v[0]}")
            else:
                print(f"  {k}: {v}")

# Also check what fields are at top-level for jockeys with actual data
print("\n=== Finding jockey with data ===")
for name, j in list(jockeys.items())[:20]:
    if isinstance(j, dict):
        # Look for any non-empty list/dict field
        for k, v in j.items():
            if isinstance(v, list) and len(v) > 0:
                print(f"  {name}.{k}: list with {len(v)} items")
                break
            elif isinstance(v, dict) and len(v) > 0:
                print(f"  {name}.{k}: dict with {len(v)} keys")
                break
