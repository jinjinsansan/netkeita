path = "/opt/dlogic/backend/services/viewlogic_engine.py"
with open(path, "r") as f:
    content = f.read()

# Remove the broken RACE_CODE fallback
old = """                # クラス名の取得（GRADE_CODEから変換）
                grade_code = race.get('GRADE_CODE', '').strip()
                class_name = self._get_grade_name(grade_code) if grade_code else ''
                # GRADE_CODEが空の場合、RACE_CODEの4桁目から推定
                if not class_name:
                    rc = str(race.get('RACE_CODE', ''))
                    if len(rc) >= 4:
                        rc4 = rc[3]
                        rc_map = {'A': 'G1', 'B': 'G2', 'C': 'G3', 'D': 'リステッド',
                                  'E': 'オープン', 'F': '3勝', 'G': '2勝', 'H': '1勝',
                                  'I': '未勝利', 'J': '新馬', 'L': 'リステッド'}
                        class_name = rc_map.get(rc4, '')"""

new = """                # クラス名の取得（GRADE_CODEから変換）
                grade_code = race.get('GRADE_CODE', '').strip()
                class_name = self._get_grade_name(grade_code) if grade_code else ''
                # GRADE_CODEが空でレース名も空の場合 → 下級条件戦
                if not class_name:
                    barei = str(race.get('BAREI', '')).strip()
                    rb = int(str(race.get('RACE_BANGO', '0')).strip() or '0')
                    if rb <= 6:
                        class_name = '未勝利' if barei != '02' else '新馬'
                    elif rb <= 9:
                        class_name = '1勝'"""

if old in content:
    content = content.replace(old, new)
    with open(path, "w") as f:
        f.write(content)
    print("PATCHED: class_name fallback from RACE_BANGO")
else:
    print("ERROR: old block not found")
    # Debug
    idx = content.find("GRADE_CODEが空の場合")
    if idx >= 0:
        print(repr(content[idx-100:idx+300]))
