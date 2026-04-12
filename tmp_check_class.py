import json, sys
sys.path.insert(0, "/opt/dlogic/backend")
from services.viewlogic_engine import ViewLogicEngine

e = ViewLogicEngine()

# Check a lower-class horse
h = e.get_horse_history("フェルアフリーゼ")
if h.get("races"):
    print("=== フェルアフリーゼ ===")
    for r in h["races"][:3]:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        print("---")

# Also check the raw data keys from engine
from services.viewlogic_data_manager import get_viewlogic_data_manager
dm = get_viewlogic_data_manager()
hd = dm.get_horse_data("フェルアフリーゼ")
if hd and hd.get("races"):
    print("\n=== RAW KEYS ===")
    raw = hd["races"][0]
    grade_keys = [k for k in raw.keys() if "GRADE" in k.upper() or "CLASS" in k.upper() or "JOUKEN" in k.upper() or "JOKEN" in k.upper() or "条件" in k]
    for k in grade_keys:
        print(f"  {k}: {raw[k]}")
    # Show all keys for reference
    print(f"\n  ALL KEYS: {sorted(raw.keys())}")
