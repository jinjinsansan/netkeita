import psycopg2
conn = psycopg2.connect(host="127.0.0.1", port="5432", database="pckeiba", user="postgres", password="postgres")
cur = conn.cursor()

NAR_CODES = {
    '83': '帯広', '30': '門別', '35': '盛岡', '36': '水沢',
    '45': '浦和', '43': '船橋', '42': '大井', '44': '川崎',
    '46': '金沢', '47': '笠松', '48': '名古屋',
    '50': '園田', '51': '姫路', '54': '高知', '55': '佐賀',
}

cur.execute("""
    SELECT keibajo_code, COUNT(*) as races,
           MIN(kaisai_nen||kaisai_tsukihi) as earliest,
           MAX(kaisai_nen||kaisai_tsukihi) as latest
    FROM jvd_ra
    WHERE kaisai_nen >= '2024'
      AND keibajo_code IN ('83','30','35','36','42','43','44','45','46','47','48','50','51','54','55')
    GROUP BY keibajo_code
    ORDER BY races DESC
""")

print("NAR coverage in PC-KEIBA (2024+):")
print(f"{'Code':<6} {'Venue':<8} {'Races':>6} {'Earliest':>12} {'Latest':>12}")
for row in cur.fetchall():
    venue = NAR_CODES.get(row[0], '?')
    print(f"{row[0]:<6} {venue:<8} {row[1]:>6} {row[2]:>12} {row[3]:>12}")

cur.close()
conn.close()
