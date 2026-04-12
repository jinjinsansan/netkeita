path = "/opt/dlogic/backend/services/viewlogic_engine.py"
with open(path, "r") as f:
    content = f.read()

old = """    def _get_grade_name(self, grade_code: str) -> str:
        \"\"\"グレードコードを分かりやすい表記に変換\"\"\"
        grade_map = {
            'A': 'G1',
            'B': 'G2', 
            'C': 'G3',
            'D': 'リステッド',
            'E': 'オープン',
            'F': '3勝',
            'G': '2勝', 
            'H': '1勝',
            'I': '未勝利',
            'J': '新馬'
        }
        return grade_map.get(grade_code, '')"""

new = """    def _get_grade_name(self, grade_code: str) -> str:
        \"\"\"グレードコードを分かりやすい表記に変換\"\"\"
        grade_map = {
            'A': 'G1',
            'B': 'G2', 
            'C': 'G3',
            'D': 'リステッド',
            'E': 'オープン',
            'F': '3勝',
            'G': '2勝', 
            'H': '1勝',
            'I': '未勝利',
            'J': '新馬',
            'L': 'リステッド',
        }
        return grade_map.get(grade_code.strip(), '')"""

if old in content:
    content = content.replace(old, new)
    with open(path, "w") as f:
        f.write(content)
    print("PATCHED: added L mapping + strip()")
else:
    print("ERROR: old block not found")
