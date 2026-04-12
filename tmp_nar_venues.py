import psycopg2
conn = psycopg2.connect(host="127.0.0.1", port="5432", database="pckeiba", user="postgres", password="postgres")
cur = conn.cursor()
cur.execute("""
    SELECT se.keibajo_code, COUNT(*) as cnt
    FROM jvd_se se
    WHERE se.keibajo_code NOT IN ('01','02','03','04','05','06','07','08','09','10')
      AND se.keibajo_code !~ '^[A-Z]'
      AND se.kaisai_nen >= '2023'
      AND se.kakutei_chakujun IS NOT NULL AND se.kakutei_chakujun != ''
    GROUP BY se.keibajo_code
    ORDER BY cnt DESC
""")
for row in cur.fetchall():
    print(f"  {row[0]} : {row[1]:,}")
cur.close()
conn.close()
