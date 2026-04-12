"""Check how recent_runs data maps to jvd_ra/jvd_se for race level lookup."""
import psycopg2

conn = psycopg2.connect(host="127.0.0.1", port="5432", database="pckeiba", user="postgres", password="postgres")
cur = conn.cursor()

# How many JRA races in jvd_ra from 2020-2026?
cur.execute("""
    SELECT COUNT(*) FROM jvd_ra
    WHERE keibajo_code IN ('01','02','03','04','05','06','07','08','09','10')
      AND kaisai_nen >= '2020'
""")
total = cur.fetchone()[0]
print(f"JRA races (2020+): {total:,}")

# Check uniqueness of date+venue+race_name
cur.execute("""
    SELECT COUNT(*), COUNT(DISTINCT (kaisai_nen || kaisai_tsukihi || keibajo_code || TRIM(kyosomei_hondai)))
    FROM jvd_ra
    WHERE keibajo_code IN ('01','02','03','04','05','06','07','08','09','10')
      AND kaisai_nen >= '2020'
""")
row = cur.fetchone()
print(f"Total: {row[0]:,}, Unique by date+venue+name: {row[1]:,}")

# Sample duplicate: same date+venue+race_name but different race_bango
cur.execute("""
    SELECT kaisai_nen, kaisai_tsukihi, keibajo_code, TRIM(kyosomei_hondai), COUNT(*) as cnt
    FROM jvd_ra
    WHERE keibajo_code IN ('01','02','03','04','05','06','07','08','09','10')
      AND kaisai_nen >= '2024'
    GROUP BY kaisai_nen, kaisai_tsukihi, keibajo_code, TRIM(kyosomei_hondai)
    HAVING COUNT(*) > 1
    ORDER BY cnt DESC
    LIMIT 10
""")
dups = cur.fetchall()
print(f"\nDuplicate date+venue+name (top 10):")
for d in dups:
    print(f"  {d[0]}/{d[1]} venue={d[2]} name={d[3]} count={d[4]}")

cur.close()
conn.close()
