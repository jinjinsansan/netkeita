path = "/opt/dlogic/backend/services/viewlogic_engine.py"
with open(path, "r") as f:
    content = f.read()

old = """                # クラス名の取得（GRADE_CODEから変換）
                grade_code = race.get('GRADE_CODE', '')
                class_name = self._get_grade_name(grade_code) if grade_code else ''"""

new = """                # クラス名の取得（GRADE_CODEから変換）
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

if old in content:
    content = content.replace(old, new)
    with open(path, "w") as f:
        f.write(content)
    print("PATCHED: class_name fallback from RACE_CODE")
else:
    print("ERROR: old block not found")
