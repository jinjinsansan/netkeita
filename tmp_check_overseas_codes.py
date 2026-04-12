import psycopg2

conn = psycopg2.connect(host="127.0.0.1", port="5432", database="pckeiba", user="postgres", password="postgres")
cur = conn.cursor()

# 1. 海外競馬場コード一覧 (2019年以降)
print("=== 海外競馬場コード (keibajo_code NOT IN 01-10) ===")
cur.execute("""
    SELECT se.keibajo_code, COUNT(*) as cnt
    FROM jvd_se se
    WHERE se.keibajo_code NOT IN ('01','02','03','04','05','06','07','08','09','10')
      AND se.kaisai_nen >= '2019'
      AND se.bamei IS NOT NULL AND se.bamei != ''
    GROUP BY se.keibajo_code
    ORDER BY cnt DESC
""")
for row in cur.fetchall():
    print(f"  {row[0]} : {row[1]:,} rows")

# 2. 海外レースのサンプル (着順があるもの)
print("\n=== 海外レースサンプル (着順あり, 最新5件) ===")
cur.execute("""
    SELECT se.bamei, se.keibajo_code, se.kaisai_nen, se.kaisai_tsukihi,
           se.kakutei_chakujun, ra.kyosomei_hondai, ra.kyori, ra.track_code
    FROM jvd_se se
    JOIN jvd_ra ra ON (
        se.kaisai_nen = ra.kaisai_nen
        AND se.kaisai_tsukihi = ra.kaisai_tsukihi
        AND se.keibajo_code = ra.keibajo_code
        AND se.race_bango = ra.race_bango
    )
    WHERE se.keibajo_code NOT IN ('01','02','03','04','05','06','07','08','09','10')
      AND se.kaisai_nen >= '2019'
      AND se.kakutei_chakujun IS NOT NULL AND se.kakutei_chakujun != ''
      AND CAST(se.kakutei_chakujun AS INTEGER) > 0
    ORDER BY se.kaisai_nen DESC, se.kaisai_tsukihi DESC
    LIMIT 10
""")
for row in cur.fetchall():
    print(f"  {row[0]} | 場:{row[1]} | {row[2]}/{row[3]} | 着:{row[4]} | {row[5]} | {row[6]}m | track:{row[7]}")

# 3. 海外レースの着順有無の分布
print("\n=== 海外レースの着順分布 ===")
cur.execute("""
    SELECT
      CASE
        WHEN se.kakutei_chakujun IS NULL OR se.kakutei_chakujun = '' THEN 'NULL/empty'
        WHEN CAST(se.kakutei_chakujun AS INTEGER) = 0 THEN '0 (unknown)'
        ELSE 'valid (1+)'
      END as status,
      COUNT(*) as cnt
    FROM jvd_se se
    WHERE se.keibajo_code NOT IN ('01','02','03','04','05','06','07','08','09','10')
      AND se.kaisai_nen >= '2019'
    GROUP BY status
    ORDER BY cnt DESC
""")
for row in cur.fetchall():
    print(f"  {row[0]} : {row[1]:,}")

cur.close()
conn.close()
