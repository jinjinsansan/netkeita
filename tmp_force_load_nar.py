import sys, os
sys.path.insert(0, "/opt/dlogic/backend")

from services.local_dlogic_raw_data_manager_v2 import local_dlogic_manager_v2 as dm

print(f"Initial: total_horses={dm.get_total_horses()}")
print(f"Diagnostics: {dm.get_diagnostics()}")

# Force load
print("\nForcing load via get_horse_data()...")
data = dm.get_horse_data("パワームーブ")
print(f"パワームーブ: {bool(data)}")
if data:
    print(f"  races: {len(data.get('races', []))}")

print(f"\nAfter load: total_horses={dm.get_total_horses()}")
print(f"Diagnostics: {dm.get_diagnostics()}")

# Also test horses from all venues
test_horses = [
    ("パワームーブ", "水沢"),
    ("メイショウヨンク", "高知"),
    ("モズグランプリ", "佐賀"),
    ("ソウルロックス", "大井"),
]
for name, venue in test_horses:
    d = dm.get_horse_data(name)
    print(f"  {name}({venue}): {'OK' if d else 'NOT FOUND'}")
