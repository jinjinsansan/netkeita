import sys, json
sys.path.insert(0, "/opt/dlogic/backend")
from services.viewlogic_data_manager import get_viewlogic_data_manager

dm = get_viewlogic_data_manager()

# Check ゾンニッヒ's G3 race (キーンランドカップ)
hd = dm.get_horse_data("ゾンニッヒ")
if hd and hd.get("races"):
    print("=== ゾンニッヒ G3 race (race 3) ===")
    r = hd["races"][2]  # キーンランドカップ
    for k in sorted(r.keys()):
        v = r[k]
        if v and str(v).strip():
            print(f"  {k}: {v}")

    # Check all 5 races for TIME_SA and related
    print("\n=== All 5 races: timing data ===")
    for i, r in enumerate(hd["races"][:5]):
        name = str(r.get("KYOSOMEI_HONDAI", "")).strip() or f"Race {i}"
        time_sa = r.get("TIME_SA", "")
        soha = r.get("SOHA_TIME", "")
        kohan = r.get("KOHAN_3F", "")
        zenhan = r.get("ZENHAN_3F", "")
        race_kohan = r.get("RACE_KOHAN_3F", "")
        tosu = r.get("DOCHAKU_TOSU", "")
        print(f"  {name}: TIME_SA={time_sa} SOHA={soha} ZENHAN={zenhan} KOHAN={kohan} RACE_KOHAN={race_kohan} TOSU={tosu}")
