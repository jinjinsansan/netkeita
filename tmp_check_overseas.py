import sys, json
sys.path.insert(0, "/opt/dlogic/backend")
from services.viewlogic_data_manager import get_viewlogic_data_manager

dm = get_viewlogic_data_manager()

# Check horses that likely have overseas runs
# ダービー卿の出走馬で海外経験がありそうな馬を調査
test_horses = [
    "ゾンニッヒ",        # 中山11R
    "マテンロウオリオン",  # 中山11R - G1級馬
    "ファーヴェント",      # 中山11R
    "ジュンブロッサム",    # 中山11R
]

for name in test_horses:
    hd = dm.get_horse_data(name)
    if not hd:
        print(f"=== {name}: データなし ===")
        continue
    races = hd.get("races", [])
    print(f"\n=== {name}: {len(races)}走 ===")
    for i, r in enumerate(races):
        venue_code = r.get("KEIBAJO_CODE", "?")
        venue_name = r.get("track_name", "")
        race_name = str(r.get("KYOSOMEI_HONDAI", "")).strip()
        date = f"{r.get('KAISAI_NEN','')}/{r.get('KAISAI_GAPPI','')}"
        finish = r.get("KAKUTEI_CHAKUJUN", "?")
        grade = r.get("GRADE_CODE", "?").strip()
        print(f"  {i+1}. {date} {venue_name}({venue_code}) {race_name or 'R'+str(r.get('RACE_BANGO',''))} G={grade} 着順={finish}")
