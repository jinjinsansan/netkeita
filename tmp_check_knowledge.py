import json

with open("/tmp/unified_knowledge_cache.json") as f:
    d = json.load(f)

# Metadata
m = d.get("metadata", {})
print("=== Metadata ===")
for k, v in m.items():
    print(f"  {k}: {v}")

# Check a horse with known overseas record
horses = d.get("horses", {})
print(f"\n=== Total horses: {len(horses)} ===")

# マテンロウオリオン - went to Hong Kong Mile 2022
for key in list(horses.keys())[:5]:
    print(f"Sample key: '{key}'")

# Find マテンロウオリオン
for key in horses:
    if "マテンロウオリオン" in key:
        h = horses[key]
        races = h.get("races", [])
        print(f"\n=== マテンロウオリオン (key='{key}'): {len(races)} races ===")
        for i, r in enumerate(races):
            venue_code = r.get("KEIBAJO_CODE", "?")
            date = f"{r.get('KAISAI_NEN','')}/{r.get('KAISAI_GAPPI','')}"
            race_name = str(r.get("KYOSOMEI_HONDAI", "")).strip()
            print(f"  {i+1}. {date} venue={venue_code} {race_name or 'R'+str(r.get('RACE_BANGO',''))}")
        break
