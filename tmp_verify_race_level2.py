"""Verify with different definitions of 'place'."""
import psycopg2

conn = psycopg2.connect(host="127.0.0.1", port="5432", database="pckeiba", user="postgres", password="postgres")
cur = conn.cursor()

VENUE_MAP = {
    '01': '札幌', '02': '函館', '03': '福島', '04': '新潟',
    '05': '東京', '06': '中山', '07': '中京', '08': '京都',
    '09': '阪神', '10': '小倉',
}
VENUE_REVERSE = {v: k for k, v in VENUE_MAP.items()}


def calc_variants(race_date, venue_name, race_name_part, expected):
    venue_code = VENUE_REVERSE.get(venue_name, '')
    date_str = race_date.replace('/', '')
    kaisai_nen = date_str[:4]
    kaisai_tsukihi = date_str[4:]

    cur.execute("""
        SELECT ra.race_bango, TRIM(ra.kyosomei_hondai)
        FROM jvd_ra ra
        WHERE ra.kaisai_nen = %s AND ra.kaisai_tsukihi = %s
          AND ra.keibajo_code = %s AND TRIM(ra.kyosomei_hondai) LIKE %s
    """, (kaisai_nen, kaisai_tsukihi, venue_code, f'%{race_name_part}%'))
    races = cur.fetchall()
    if not races:
        print(f"  Not found")
        return
    race_bango = races[0][0]

    cur.execute("""
        SELECT se.bamei, se.ketto_toroku_bango, se.kakutei_chakujun
        FROM jvd_se se
        WHERE se.kaisai_nen = %s AND se.kaisai_tsukihi = %s
          AND se.keibajo_code = %s AND se.race_bango = %s
          AND se.ketto_toroku_bango != '0000000000'
          AND se.bamei IS NOT NULL AND se.bamei != ''
          AND se.kakutei_chakujun IS NOT NULL AND se.kakutei_chakujun != ''
    """, (kaisai_nen, kaisai_tsukihi, venue_code, race_bango))

    horses = []
    for h in cur.fetchall():
        try:
            pos = int(h[2])
            if pos > 0:
                horses.append((h[0].strip(), h[1], pos))
        except (ValueError, TypeError):
            pass

    total = len(horses)

    # Method A: All subsequent races - win and place (current)
    win_all = 0
    place_all = 0
    # Method B: Next race only
    win_next = 0
    place_next = 0
    # Method C: All subsequent, but 複勝 = 勝った馬 (not 3着以内)
    # Method D: 次走で勝ったか、次走で複勝圏
    # Method E: 勝ち上がり = 1着取った馬, 複勝 = 次走で3着以内に入った馬
    place_next_only = 0

    for horse_name, ketto_id, _ in horses:
        cur.execute("""
            SELECT se.kakutei_chakujun
            FROM jvd_se se
            WHERE se.ketto_toroku_bango = %s
              AND (se.kaisai_nen > %s OR (se.kaisai_nen = %s AND se.kaisai_tsukihi > %s))
              AND se.kakutei_chakujun IS NOT NULL AND se.kakutei_chakujun != ''
            ORDER BY se.kaisai_nen, se.kaisai_tsukihi
        """, (ketto_id, kaisai_nen, kaisai_nen, kaisai_tsukihi))

        subsequent = cur.fetchall()

        # All subsequent
        has_won_ever = False
        has_placed_ever = False
        for (pos_str,) in subsequent:
            try:
                pos = int(pos_str)
                if pos == 1:
                    has_won_ever = True
                    has_placed_ever = True
                elif pos <= 3:
                    has_placed_ever = True
            except:
                pass

        if has_won_ever:
            win_all += 1
        if has_placed_ever:
            place_all += 1

        # Next race only
        if subsequent:
            try:
                next_pos = int(subsequent[0][0])
                if next_pos == 1:
                    win_next += 1
                    place_next += 1
                elif next_pos <= 3:
                    place_next += 1
            except:
                pass

    print(f"  Expected (netkeiba):          win {expected['win']}, place {expected['place']}")
    print(f"  Method A (all subsequent):    win {win_all}/{total}, place {place_all}/{total}")
    print(f"  Method B (next race only):    win {win_next}/{total}, place {place_next}/{total}")


test_races = [
    ("2025/12/06", "阪神", "鳴尾記念",  {"win": "0/14", "place": "1/14"}),
    ("2025/08/09", "新潟", "関越",      {"win": "2/13", "place": "3/13"}),
    ("2025/06/29", "函館", "函館記念",  {"win": "1/14", "place": "4/14"}),
]

print("=" * 70)
print("Method comparison")
print("=" * 70)

for date, venue, name, expected in test_races:
    print(f"\n--- {date} {venue} {name} ---")
    calc_variants(date, venue, name, expected)

cur.close()
conn.close()
