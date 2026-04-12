"""Check if 岩手 jockeys are in NAR jockey knowledge."""
import sys, json
sys.path.insert(0, "/opt/dlogic/backend")

# Load the NAR jockey knowledge file directly
import os
jockey_file = "/opt/dlogic/backend/data/local_jockey_knowledge.json"
real_path = os.path.realpath(jockey_file)
print(f"Loading {real_path}...")

with open(jockey_file) as f:
    data = json.load(f)

# Top-level structure
print(f"Top keys: {list(data.keys())[:10]}")
if isinstance(data, dict):
    jockeys = data.get("jockeys") or data
    print(f"Total: {len(jockeys)} jockeys")
    
    # Sample
    keys = list(jockeys.keys())[:5]
    print(f"Sample: {keys}")
    
    # Check specific jockeys
    test_jockeys = ["坂井瑛音", "小林凌", "斉藤友香", "菅原辰徳", "佐原秀泰", "林悠翔"]
    for j in test_jockeys:
        if j in jockeys:
            jd = jockeys[j]
            races = jd.get("races", [])
            if isinstance(races, list):
                print(f"  {j}: {len(races)} races")
            else:
                print(f"  {j}: FOUND ({type(jd).__name__})")
                if isinstance(jd, dict):
                    print(f"    keys: {list(jd.keys())[:10]}")
        else:
            print(f"  {j}: NOT FOUND")
