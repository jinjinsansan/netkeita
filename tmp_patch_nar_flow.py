#!/usr/bin/env python3
"""Patch LocalViewLogicEngineV2._calculate_flow_matching to produce
JRA-compatible 40-85 range flow scores using corner position data."""
import re
import sys

TARGET = "/opt/dlogic/backend/services/local_viewlogic_engine_v2.py"

NEW_METHOD = '''    def _calculate_flow_matching(self, horses_data: List[Dict], pace_prediction: Dict) -> Dict[str, float]:
        """展開適性マッチング (NAR版: 40-85スケール、コーナー通過順から脚質指数を推定)"""
        from statistics import mean as _mean

        flow_scores = {}
        pace = pace_prediction.get('calculation_pace', pace_prediction.get('pace', 'ミドルペース'))

        def _style_index(races):
            diffs = []
            for race in races[:5]:
                c1_raw = race.get('CORNER1_JUNI') or race.get('CORNER2_JUNI')
                c4_raw = race.get('CORNER4_JUNI')
                try:
                    c1 = int(c1_raw) if c1_raw else 0
                    c4 = int(c4_raw) if c4_raw else 0
                except (ValueError, TypeError):
                    continue
                if not c1 or not c4:
                    continue
                if c1 <= 2:
                    s = -4
                elif c1 <= 4:
                    s = -2
                elif c1 <= 7:
                    s = 0
                elif c1 <= 10:
                    s = 2
                else:
                    s = 4
                if c4 < c1 - 2:
                    s += 1
                elif c4 > c1 + 2:
                    s -= 1
                diffs.append(max(-5, min(5, s)))
            return _mean(diffs) if diffs else 0

        for horse in horses_data:
            horse_name = horse.get('horse_name', '不明')
            if 'races' not in horse or not horse['races']:
                flow_scores[horse_name] = 50.0
                continue

            style_index = _style_index(horse['races'])
            base = 60.0

            if 'ハイ' in pace:
                if style_index > 0:
                    score = base * (1.2 + style_index * 0.04)
                else:
                    score = base * (0.85 + style_index * 0.03)
            elif 'スロー' in pace:
                if style_index < 0:
                    score = base * (1.15 - style_index * 0.03)
                else:
                    score = base * (0.9 - style_index * 0.02)
            else:
                adjustment = (5 - abs(style_index)) * 3 + style_index * 0.5
                score = base + adjustment

            flow_scores[horse_name] = round(min(85, max(40, score)), 1)

        return flow_scores

'''

with open(TARGET, "r", encoding="utf-8") as f:
    src = f.read()

# Find the method by its signature, then locate the next method at same indent
lines = src.split("\n")
start = None
end = None
for i, line in enumerate(lines):
    if line.startswith("    def _calculate_flow_matching(self, horses_data: List[Dict], pace_prediction: Dict) -> Dict[str, float]:"):
        start = i
        # scan forward for next method at same indent
        for j in range(i+1, len(lines)):
            if lines[j].startswith("    def "):
                end = j
                break
        break

if start is None or end is None:
    print("ERROR: method not located", file=sys.stderr)
    sys.exit(1)

print(f"Replacing lines {start+1}..{end} (total {end-start} lines)", file=sys.stderr)
new_lines = lines[:start] + NEW_METHOD.rstrip("\n").split("\n") + [""] + lines[end:]
new_src = "\n".join(new_lines)

# Sanity: make sure still valid Python
import ast
try:
    ast.parse(new_src)
except SyntaxError as e:
    print(f"ERROR: syntax error after patch: {e}", file=sys.stderr)
    sys.exit(2)

with open(TARGET, "w", encoding="utf-8") as f:
    f.write(new_src)

print(f"patched: {len(src)} -> {len(new_src)} chars")
