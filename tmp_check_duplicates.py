"""Check raw knowledge data for duplicates and mismatches."""
import sys, json
sys.path.insert(0, "/opt/dlogic/backend")
from services.viewlogic_engine import ViewLogicEngine
from services.viewlogic_data_manager import get_viewlogic_data_manager

e = ViewLogicEngine()
dm = e.data_manager

# Problem horses
problem_horses = [
    "タイムトゥヘヴン",    # Same race x3
    "ウィザードオブマリ",  # Same race x2
    "エコロセレナ",        # Same race x2
]

for name in problem_horses:
    print(f"\n{'='*60}")
    print(f"=== {name} ===")

    # 1. Raw knowledge data
    hd = dm.get_horse_data(name)
    if hd and hd.get("races"):
        races = hd["races"]
        print(f"\nRAW DATA: {len(races)} races")
        for i, r in enumerate(races):
            date = f"{r.get('KAISAI_NEN','')}/{r.get('KAISAI_GAPPI','')}"
            venue_code = str(r.get('KEIBAJO_CODE', '?')).strip()
            race_name = str(r.get('KYOSOMEI_HONDAI', '')).strip()
            rb = str(r.get('RACE_BANGO', '')).strip()
            finish = str(r.get('KAKUTEI_CHAKUJUN', '?')).strip()
            race_code = str(r.get('RACE_CODE', '')).strip()
            print(f"  {i+1}. {date} venue={venue_code} {race_name or rb+'R'} 着順={finish} CODE={race_code}")
    else:
        print(f"  No raw data found")

    # 2. get_horse_history output
    h = e.get_horse_history(name)
    if h.get("races"):
        print(f"\nFORMATTED DATA: {len(h['races'])} races")
        for i, r in enumerate(h["races"]):
            date = r.get("開催日", "?")
            venue = r.get("競馬場", "?")
            race_name = r.get("レース", "?")
            finish = r.get("着順", "?")
            print(f"  {i+1}. {date} {venue} {race_name} {finish}")
