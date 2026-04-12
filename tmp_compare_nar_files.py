import json, os

files = [
    "/opt/dlogic/backend/data/nankan_unified_knowledge_20260310.json",
    "/opt/dlogic/backend/data/all_nar_unified_knowledge_20260310.json",
]

for fp in files:
    print(f"\n=== {fp} ===")
    print(f"  Size: {os.path.getsize(fp)/1024/1024:.1f}MB")
    with open(fp) as f:
        data = json.load(f)
    
    print(f"  Top-level keys: {list(data.keys())[:10]}")
    
    # Check for horses
    horses = data.get("horses", {})
    if horses:
        print(f"  'horses' key: {len(horses)} entries")
        sample_key = list(horses.keys())[0]
        print(f"  Sample horse key: {sample_key}")
        sample = horses[sample_key]
        print(f"  Sample horse structure: {list(sample.keys())[:15]}")
    else:
        # Maybe the data is directly keyed by horse name
        keys = list(data.keys())
        if keys and isinstance(data[keys[0]], dict):
            print(f"  No 'horses' wrapper. Top-level has {len(keys)} items")
            sample = data[keys[0]]
            if isinstance(sample, dict):
                print(f"  Sample '{keys[0]}' structure: {list(sample.keys())[:15]}")
        else:
            print(f"  No horses found")
    
    # Check for metadata
    meta = data.get("metadata") or data.get("meta")
    if meta:
        print(f"  Metadata: {json.dumps(meta, ensure_ascii=False, indent=2)[:300]}")
