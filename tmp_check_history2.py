import json
import sys
sys.path.insert(0, "/opt/dlogic/backend")
from services.viewlogic_engine import ViewLogicEngine

e = ViewLogicEngine()
h = e.get_horse_history("ゾンニッヒ")
if h.get("races"):
    print("=== FIRST RACE (all keys) ===")
    print(json.dumps(h["races"][0], ensure_ascii=False, indent=2))
    print("\n=== RUNNING STYLE ===")
    print(h.get("running_style", "N/A"))
    print(f"\n=== TOTAL RACES: {len(h.get('races', []))} ===")
else:
    print("No races found")
    print(json.dumps(h, ensure_ascii=False, indent=2))
