import psycopg2, json

conn = psycopg2.connect(host="127.0.0.1", port="5432", database="pckeiba", user="postgres", password="postgres")
cur = conn.cursor()

cur.execute("""
    SELECT se.keibajo_code,
           array_agg(DISTINCT LEFT(TRIM(ra.kyosomei_hondai), 40)) as race_samples,
           COUNT(DISTINCT se.bamei) as horse_count
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
result = {}
for row in cur.fetchall():
    samples = [s.strip() for s in row[1][:5] if s and s.strip()]
    result[row[0]] = {"horses": row[2], "samples": samples}

cur.close()
conn.close()

with open("E:\\dev\\Cusor\\netkeita\\tmp_overseas_codes.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print("Done")
