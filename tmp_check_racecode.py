import sys
sys.path.insert(0, "/opt/dlogic/backend")
from services.viewlogic_data_manager import get_viewlogic_data_manager

dm = get_viewlogic_data_manager()

for name in ["フェルアフリーゼ", "ゾンニッヒ"]:
    hd = dm.get_horse_data(name)
    if hd and hd.get("races"):
        print(f"=== {name} ===")
        for r in hd["races"][:3]:
            gc = r.get("GRADE_CODE", "?")
            rc = r.get("RACE_CODE", "?")
            rn = r.get("KYOSOMEI_HONDAI", "?").strip()
            rb = r.get("RACE_BANGO", "?")
            print(f"  GRADE='{gc}' RACE_CODE='{rc}' RACE={rn or rb+'R'}")
