import json, urllib.request

BASE = "https://bot.dlogicai.in/nk"
race_id = "20260405-%E4%B8%AD%E5%B1%B1-11"

# 1. Get race entries
url = f"{BASE}/api/race/{race_id}/entries"
entries = json.loads(urllib.request.urlopen(url).read().decode("utf-8"))
print("=== ENTRIES (first 3) ===")
for e in entries.get("entries", [])[:3]:
    print(f"  {e}")

# 2. Check what the matrix endpoint's _build_prediction_scores produces
# by calling the predictions API indirectly - let's check the raw matrix response
url2 = f"{BASE}/api/race/{race_id}/matrix"
matrix = json.loads(urllib.request.urlopen(url2).read().decode("utf-8"))

print("\n=== MATRIX: first 5 horses full scores ===")
for h in matrix["horses"][:5]:
    print(f"  #{h['horse_number']} {h['horse_name']}")
    print(f"    scores: {h['scores']}")
    print(f"    ranks:  {h['ranks']}")
