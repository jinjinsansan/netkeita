import psycopg2
from collections import defaultdict

conn = psycopg2.connect(host="127.0.0.1", port="5432", database="pckeiba", user="postgres", password="postgres")
cur = conn.cursor()

NAR_CODES = {
    '83': '帯広', '30': '門別', '35': '盛岡', '36': '水沢',
    '45': '浦和', '43': '船橋', '42': '大井', '44': '川崎',
    '46': '金沢', '47': '笠松', '48': '名古屋',
    '50': '園田', '51': '姫路', '54': '高知', '55': '佐賀',
}
nar_tuple = tuple(NAR_CODES.keys())

# 1. 月別のレース数
print("=== NAR 月別レース数 (2024-2026) ===")
cur.execute("""
    SELECT LEFT(kaisai_nen || kaisai_tsukihi, 6) as ym, COUNT(*) as races
    FROM jvd_ra
    WHERE keibajo_code IN %s AND kaisai_nen >= '2024'
    GROUP BY ym ORDER BY ym
""", (nar_tuple,))
for row in cur.fetchall():
    print(f"  {row[0][:4]}/{row[0][4:]}: {row[1]:>4} races")

# 2. 場別の最新データ日
print("\n=== NAR 場別 最新データ日 ===")
cur.execute("""
    SELECT keibajo_code, MAX(kaisai_nen || kaisai_tsukihi) as latest, COUNT(*) as total
    FROM jvd_ra
    WHERE keibajo_code IN %s AND kaisai_nen >= '2024'
    GROUP BY keibajo_code ORDER BY total DESC
""", (nar_tuple,))
for row in cur.fetchall():
    code = row[0]
    name = NAR_CODES.get(code, '?')
    latest = row[1]
    print(f"  {name}({code}): 最新={latest[:4]}/{latest[4:6]}/{latest[6:]}  計{row[2]}R")

# 3. 全体のカバレッジ推定
# 2025年の地方競馬は年間約15,000レース (15場 × 約1,000R)
# PC-KEIBAにある2025年のレース数
cur.execute("""
    SELECT COUNT(*) FROM jvd_ra
    WHERE keibajo_code IN %s AND kaisai_nen = '2025'
""", (nar_tuple,))
nar_2025 = cur.fetchone()[0]
print(f"\n2025年 NAR レース数 (PC-KEIBA): {nar_2025}")
print(f"推定カバレッジ: {nar_2025}/~15000 = {nar_2025/15000*100:.0f}%")

cur.close()
conn.close()
