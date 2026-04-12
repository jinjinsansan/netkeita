"""Verify that the updated KEIBAJO_MAP captures overseas races correctly."""
import psycopg2, json

KEIBAJO_MAP = {
    '01': '札幌', '02': '函館', '03': '福島', '04': '新潟',
    '05': '東京', '06': '中山', '07': '中京', '08': '京都',
    '09': '阪神', '10': '小倉',
    'A4': 'アメリカ', 'A6': 'イギリス(アスコット等)',
    'A8': 'イギリス(ニューマーケット等)', 'B2': 'アイルランド',
    'B6': 'オーストラリア', 'B8': 'カナダ',
    'C0': 'イタリア', 'C2': 'ドイツ',
    'C7': 'UAE(ドバイ)', 'F0': '韓国',
    'G0': '香港', 'K6': 'サウジアラビア',
    'M8': 'カタール', 'N2': 'バーレーン',
}

conn = psycopg2.connect(host="127.0.0.1", port="5432", database="pckeiba", user="postgres", password="postgres")
cur = conn.cursor()

# Find horses with overseas races in their most recent 9 runs
cur.execute("""
    WITH ranked AS (
        SELECT se.bamei, se.keibajo_code, se.kaisai_nen, se.kaisai_tsukihi,
               se.kakutei_chakujun, ra.kyosomei_hondai,
               ROW_NUMBER() OVER (PARTITION BY se.bamei ORDER BY se.kaisai_nen DESC, se.kaisai_tsukihi DESC) as rn
        FROM jvd_se se
        JOIN jvd_ra ra ON (
            se.kaisai_nen = ra.kaisai_nen
            AND se.kaisai_tsukihi = ra.kaisai_tsukihi
            AND se.keibajo_code = ra.keibajo_code
            AND se.race_bango = ra.race_bango
        )
        WHERE se.kaisai_nen >= '2019'
          AND se.ketto_toroku_bango != '0000000000'
          AND se.bamei IS NOT NULL AND se.bamei != ''
          AND se.kakutei_chakujun IS NOT NULL AND se.kakutei_chakujun != ''
          AND CAST(se.kakutei_chakujun AS INTEGER) > 0
    )
    SELECT bamei, keibajo_code, kaisai_nen, kaisai_tsukihi, kakutei_chakujun,
           TRIM(kyosomei_hondai) as race_name
    FROM ranked
    WHERE rn <= 9
      AND keibajo_code ~ '^[A-Z]'
    ORDER BY bamei, kaisai_nen DESC, kaisai_tsukihi DESC
    LIMIT 30
""")

print("=== 直近9走に海外成績を持つ馬 (サンプル) ===\n")
current_horse = None
for row in cur.fetchall():
    horse = row[0].strip()
    code = row[1]
    venue = KEIBAJO_MAP.get(code, f"不明({code})")
    date = f"{row[2]}/{row[3]}"
    pos = row[4]
    race = row[5]
    if horse != current_horse:
        if current_horse:
            print()
        current_horse = horse
        print(f"  {horse}:")
    print(f"    {date} {venue} {pos}着 {race}")

# Count how many horses would gain overseas data
cur.execute("""
    WITH ranked AS (
        SELECT se.bamei, se.keibajo_code,
               ROW_NUMBER() OVER (PARTITION BY se.bamei ORDER BY se.kaisai_nen DESC, se.kaisai_tsukihi DESC) as rn
        FROM jvd_se se
        WHERE se.kaisai_nen >= '2019'
          AND se.ketto_toroku_bango != '0000000000'
          AND se.bamei IS NOT NULL AND se.bamei != ''
          AND se.kakutei_chakujun IS NOT NULL AND se.kakutei_chakujun != ''
          AND CAST(se.kakutei_chakujun AS INTEGER) > 0
    )
    SELECT COUNT(DISTINCT bamei)
    FROM ranked
    WHERE rn <= 9
      AND keibajo_code ~ '^[A-Z]'
""")
count = cur.fetchone()[0]
print(f"\n=== 直近9走に海外成績を持つ馬: {count}頭 ===")

# Count unmapped codes
cur.execute("""
    SELECT DISTINCT se.keibajo_code
    FROM jvd_se se
    WHERE se.kaisai_nen >= '2019'
      AND se.keibajo_code NOT IN %s
      AND se.ketto_toroku_bango != '0000000000'
    ORDER BY se.keibajo_code
""", (tuple(KEIBAJO_MAP.keys()),))
unmapped = [row[0] for row in cur.fetchall()]
if unmapped:
    print(f"\n⚠ マッピングされていないコード: {unmapped}")
else:
    print(f"\n✅ 全コードがマッピング済み (JRA用途)")

cur.close()
conn.close()
