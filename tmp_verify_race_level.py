"""Verify self-calculated race level against netkeiba master course data.

Target races from screenshot:
- ブラジルC (2025/10/19 東京) → netkeiba: 勝ち 3/12, 複勝 6/12
- 鳴尾記念  (2025/12/06 阪神) → netkeiba: 勝ち 0/14, 複勝 1/14
- 関越S     (2025/08/09 新潟) → netkeiba: 勝ち 2/13, 複勝 3/13
- 函館記念  (2025/06/29 函館) → netkeiba: 勝ち 1/14, 複勝 4/14
"""
import psycopg2
import json

conn = psycopg2.connect(host="127.0.0.1", port="5432", database="pckeiba", user="postgres", password="postgres")
cur = conn.cursor()

# JRA venue code mapping
VENUE_MAP = {
    '01': '札幌', '02': '函館', '03': '福島', '04': '新潟',
    '05': '東京', '06': '中山', '07': '中京', '08': '京都',
    '09': '阪神', '10': '小倉',
}
VENUE_REVERSE = {v: k for k, v in VENUE_MAP.items()}

def calc_race_level(race_date, venue_name, race_name_part):
    """Calculate win/place stats for a specific race.
    
    1. Find the race in jvd_ra by date + venue + race name
    2. Get all horses that ran in that race
    3. For each horse, check subsequent races for wins (1st) and places (1st-3rd)
    """
    venue_code = VENUE_REVERSE.get(venue_name, '')
    date_str = race_date.replace('/', '')
    kaisai_nen = date_str[:4]
    kaisai_tsukihi = date_str[4:]
    
    # Find the race
    cur.execute("""
        SELECT ra.race_bango, TRIM(ra.kyosomei_hondai), ra.kyori
        FROM jvd_ra ra
        WHERE ra.kaisai_nen = %s
          AND ra.kaisai_tsukihi = %s
          AND ra.keibajo_code = %s
          AND TRIM(ra.kyosomei_hondai) LIKE %s
    """, (kaisai_nen, kaisai_tsukihi, venue_code, f'%{race_name_part}%'))
    
    races = cur.fetchall()
    if not races:
        print(f"  Race not found: {race_date} {venue_name} {race_name_part}")
        return None
    
    race_bango = races[0][0]
    full_race_name = races[0][1]
    print(f"  Found: {full_race_name} (R{race_bango})")
    
    # Get all horses in that race (with valid finish position)
    cur.execute("""
        SELECT se.bamei, se.ketto_toroku_bango, se.kakutei_chakujun
        FROM jvd_se se
        WHERE se.kaisai_nen = %s
          AND se.kaisai_tsukihi = %s
          AND se.keibajo_code = %s
          AND se.race_bango = %s
          AND se.ketto_toroku_bango != '0000000000'
          AND se.bamei IS NOT NULL AND se.bamei != ''
          AND se.kakutei_chakujun IS NOT NULL AND se.kakutei_chakujun != ''
    """, (kaisai_nen, kaisai_tsukihi, venue_code, race_bango))
    
    horses = cur.fetchall()
    # Filter valid finishers
    valid_horses = []
    for h in horses:
        try:
            pos = int(h[2])
            if pos > 0:
                valid_horses.append((h[0].strip(), h[1], pos))
        except (ValueError, TypeError):
            pass
    
    total = len(valid_horses)
    print(f"  Total runners: {total}")
    
    win_count = 0
    place_count = 0
    
    for horse_name, ketto_id, _ in valid_horses:
        # Check for subsequent wins and places
        cur.execute("""
            SELECT se.kakutei_chakujun
            FROM jvd_se se
            WHERE se.ketto_toroku_bango = %s
              AND (se.kaisai_nen > %s OR (se.kaisai_nen = %s AND se.kaisai_tsukihi > %s))
              AND se.kakutei_chakujun IS NOT NULL AND se.kakutei_chakujun != ''
            ORDER BY se.kaisai_nen, se.kaisai_tsukihi
        """, (ketto_id, kaisai_nen, kaisai_nen, kaisai_tsukihi))
        
        subsequent = cur.fetchall()
        has_won = False
        has_placed = False
        
        for (pos_str,) in subsequent:
            try:
                pos = int(pos_str)
                if pos == 1:
                    has_won = True
                    has_placed = True
                    break
                elif pos <= 3:
                    has_placed = True
            except (ValueError, TypeError):
                pass
        
        if has_won:
            win_count += 1
        if has_placed:
            place_count += 1
    
    return {
        'win_count': win_count,
        'win_total': total,
        'place_count': place_count,
        'place_total': total,
        'win_rate': round(win_count / total * 100, 1) if total > 0 else 0,
        'place_rate': round(place_count / total * 100, 1) if total > 0 else 0,
    }


# Test cases from screenshot
test_races = [
    ("2025/10/19", "東京", "ブラジルC",   {"win": "3/12", "place": "6/12"}),
    ("2025/12/06", "阪神", "鳴尾記念",    {"win": "0/14", "place": "1/14"}),
    ("2025/08/09", "新潟", "関越",        {"win": "2/13", "place": "3/13"}),
    ("2025/06/29", "函館", "函館記念",    {"win": "1/14", "place": "4/14"}),
]

print("=" * 70)
print("自前DB計算 vs ネット競馬マスターコース 突合検証")
print("=" * 70)

for date, venue, name, expected in test_races:
    print(f"\n--- {date} {venue} {name} ---")
    print(f"  ネット競馬: 勝ち {expected['win']}頭, 複勝 {expected['place']}頭")
    
    result = calc_race_level(date, venue, name)
    if result:
        print(f"  自前DB:     勝ち {result['win_count']}/{result['win_total']}頭, "
              f"複勝 {result['place_count']}/{result['place_total']}頭")
        
        # Compare
        nk_win = expected['win']
        db_win = f"{result['win_count']}/{result['win_total']}"
        nk_place = expected['place']
        db_place = f"{result['place_count']}/{result['place_total']}"
        
        win_match = nk_win == db_win
        place_match = nk_place == db_place
        
        if win_match and place_match:
            print(f"  >>> MATCH (exact)")
        else:
            print(f"  >>> MISMATCH - win: {'OK' if win_match else f'NG ({nk_win} vs {db_win})'}, "
                  f"place: {'OK' if place_match else f'NG ({nk_place} vs {db_place})'}")

cur.close()
conn.close()
