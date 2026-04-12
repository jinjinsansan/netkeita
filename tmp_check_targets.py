import json

with open(r"E:\dev\Cusor\netkeita\scripts\jra_race_level_20260406.json", "r", encoding="utf-8") as f:
    data = json.load(f)

targets = [
    ("20251019", "東京", "ブラジル", "3/12", "6/12"),
    ("20251206", "阪神", "鳴尾記念", "0/14", "1/14"),
    ("20250809", "新潟", "関越", "2/13", "3/13"),
    ("20250629", "函館", "函館記念", "1/14", "4/14"),
]

print("=== 自前DB vs ネット競馬 ===\n")
for date, venue, name, nk_win, nk_place in targets:
    for key, val in data.items():
        if date in key and venue in key and name in val.get("race_name", ""):
            rn = val["race_name"].strip()
            db_win = f"{val['win_count']}/{val['win_total']}"
            db_place = f"{val['place_count']}/{val['place_total']}"
            print(f"{val['date']} {venue} {rn}")
            print(f"  netkeiba: win={nk_win}  place={nk_place}")
            print(f"  自前DB:   win={db_win}  place={db_place}")
            print(f"  level: {val['level']}")
            win_ok = nk_win == db_win
            place_ok = nk_place == db_place
            print(f"  判定: win={'OK' if win_ok else 'NG'}  place={'OK' if place_ok else 'NG'}")
            print()
            break
