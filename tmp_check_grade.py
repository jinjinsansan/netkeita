import sys
sys.path.insert(0, "/opt/dlogic/backend")
from services.viewlogic_data_manager import get_viewlogic_data_manager

dm = get_viewlogic_data_manager()

# Check a G3 horse
hd = dm.get_horse_data("ゾンニッヒ")
if hd and hd.get("races"):
    print("=== ゾンニッヒ (open class) ===")
    for r in hd["races"][:5]:
        gc = r.get("GRADE_CODE", "MISSING")
        rname = r.get("KYOSOMEI_HONDAI", "?")
        rb = r.get("RACE_BANGO", "?")
        print(f"  GRADE_CODE='{gc}' RACE={rname} RACE_BANGO={rb}")

# Check a maiden horse
hd2 = dm.get_horse_data("フェルアフリーゼ")
if hd2 and hd2.get("races"):
    print("\n=== フェルアフリーゼ (maiden) ===")
    for r in hd2["races"][:5]:
        gc = r.get("GRADE_CODE", "MISSING")
        rname = r.get("KYOSOMEI_HONDAI", "?")
        rb = r.get("RACE_BANGO", "?")
        # Also check JOKEN or condition codes
        joken = [k for k in r.keys() if "JOKEN" in k.upper() or "JOUKEN" in k.upper() or "CLASS" in k.upper()]
        print(f"  GRADE_CODE='{gc}' RACE={rname} RACE_BANGO={rb} joken_keys={joken}")
