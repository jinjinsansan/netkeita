import psycopg2
conn = psycopg2.connect(host="127.0.0.1", port="5432", database="pckeiba", user="postgres", password="postgres")
cur = conn.cursor()

# What venue codes on 2026/03/05 for NAR?
cur.execute("""
    SELECT keibajo_code, COUNT(*) FROM jvd_ra
    WHERE kaisai_nen='2026' AND kaisai_tsukihi='0305'
      AND keibajo_code NOT IN ('01','02','03','04','05','06','07','08','09','10')
    GROUP BY keibajo_code
""")
print("2026/03/05 NAR venue codes:")
for row in cur.fetchall():
    print(f"  code={row[0]} count={row[1]}")

# Check sample race names on that date
cur.execute("""
    SELECT keibajo_code, race_bango, TRIM(kyosomei_hondai) FROM jvd_ra
    WHERE kaisai_nen='2026' AND kaisai_tsukihi='0305'
      AND keibajo_code NOT IN ('01','02','03','04','05','06','07','08','09','10')
    ORDER BY keibajo_code, race_bango
    LIMIT 20
""")
print("\nRaces on 2026/03/05:")
for row in cur.fetchall():
    print(f"  code={row[0]} R{row[1]} {row[2].strip()}")

cur.close()
conn.close()
