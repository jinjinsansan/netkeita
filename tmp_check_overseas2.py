import psycopg2

conn = psycopg2.connect(host="127.0.0.1", port="5432", database="pckeiba", user="postgres", password="postgres")
cur = conn.cursor()

# 英字で始まる海外コードのみ調査
print("=== 海外競馬場コード詳細 (英字コード) ===")
cur.execute("""
    SELECT se.keibajo_code,
           ra.kyosomei_hondai,
           se.kaisai_nen || '/' || se.kaisai_tsukihi as race_date,
           se.bamei,
           se.kakutei_chakujun,
           ra.kyori
    FROM jvd_se se
    JOIN jvd_ra ra ON (
        se.kaisai_nen = ra.kaisai_nen
        AND se.kaisai_tsukihi = ra.kaisai_tsukihi
        AND se.keibajo_code = ra.keibajo_code
        AND se.race_bango = ra.race_bango
    )
    WHERE se.keibajo_code ~ '^[A-Z]'
      AND se.kaisai_nen >= '2023'
      AND se.kakutei_chakujun IS NOT NULL
      AND CAST(se.kakutei_chakujun AS INTEGER) > 0
    ORDER BY se.keibajo_code, se.kaisai_nen DESC, se.kaisai_tsukihi DESC
""")
seen = {}
for row in cur.fetchall():
    code = row[0]
    if code not in seen:
        seen[code] = []
    if len(seen[code]) < 3:
        seen[code].append(row)

for code in sorted(seen.keys()):
    print(f"\n--- {code} ---")
    for row in seen[code]:
        # Encode as UTF-8 for console
        race_name = row[1].strip() if row[1] else "?"
        horse = row[3].strip() if row[3] else "?"
        print(f"  {row[2]} | {horse} | {row[4]}着 | {race_name} | {row[5]}m")

# JRA-VAN の海外競馬場コード表があるか jvd_um テーブルをチェック
print("\n=== 海外コード → レース名パターン (コード別集約) ===")
cur.execute("""
    SELECT se.keibajo_code,
           array_agg(DISTINCT LEFT(TRIM(ra.kyosomei_hondai), 30)) as race_samples,
           COUNT(DISTINCT se.bamei) as horse_count,
           MIN(se.kaisai_nen || se.kaisai_tsukihi) as earliest,
           MAX(se.kaisai_nen || se.kaisai_tsukihi) as latest
    FROM jvd_se se
    JOIN jvd_ra ra ON (
        se.kaisai_nen = ra.kaisai_nen
        AND se.kaisai_tsukihi = ra.kaisai_tsukihi
        AND se.keibajo_code = ra.keibajo_code
        AND se.race_bango = ra.race_bango
    )
    WHERE se.keibajo_code ~ '^[A-Z]'
      AND se.kaisai_nen >= '2019'
    GROUP BY se.keibajo_code
    ORDER BY horse_count DESC
""")
for row in cur.fetchall():
    samples = [s for s in row[1][:5] if s]
    print(f"  {row[0]}: {row[2]}頭 | {row[3]}~{row[4]} | {samples}")

cur.close()
conn.close()
