"""Patch viewlogic_analysis.py to return full recent-runs data."""
import re

path = "/opt/dlogic/backend/api/v2/viewlogic_analysis.py"
with open(path, "r") as f:
    content = f.read()

old_block = '''                    runs.append({
                        "date": r.get("date", r.get("開催日", r.get("KAISAI_NENGAPPI", ""))),
                        "venue": r.get("venue", r.get("競馬場", r.get("KEIBAJO_MEI", ""))),
                        "distance": r.get("distance", r.get("距離", r.get("KYORI", ""))),
                        "finish": finish_raw,
                        "jockey": r.get("jockey", r.get("騎手", r.get("KISHUMEI_RYAKUSHO", ""))),
                        "odds": odds_raw,
                    })'''

new_block = '''                    # Parse additional fields
                    popularity_raw = r.get("popularity", r.get("人気", r.get("TANSHO_NINKIJUN", "")))
                    if isinstance(popularity_raw, str):
                        _m2 = _re.search(r"(\\d+)", str(popularity_raw))
                        popularity_raw = int(_m2.group(1)) if _m2 else 0

                    time_raw = r.get("time", r.get("タイム", r.get("SOHA_TIME", "")))
                    agari_raw = r.get("agari", r.get("上り", r.get("KOHAN_3F", "")))
                    corner_raw = r.get("corner", r.get("コーナー", ""))
                    weight_raw = r.get("weight", r.get("馬体重", r.get("BATAIJU", "")))
                    race_name_raw = r.get("race_name", r.get("レース", r.get("KYOSOMEI_HONDAI", "")))
                    class_raw = r.get("class", r.get("クラス", r.get("GRADE_CODE", "")))
                    track_condition_raw = r.get("track_condition", r.get("馬場", r.get("BABA_JOTAI", "")))
                    headcount_raw = r.get("headcount", r.get("頭数", r.get("TOSU", "")))
                    if isinstance(headcount_raw, str):
                        _m3 = _re.search(r"(\\d+)", str(headcount_raw))
                        headcount_raw = int(_m3.group(1)) if _m3 else 0

                    runs.append({
                        "date": r.get("date", r.get("開催日", r.get("KAISAI_NENGAPPI", ""))),
                        "venue": r.get("venue", r.get("競馬場", r.get("KEIBAJO_MEI", ""))),
                        "distance": r.get("distance", r.get("距離", r.get("KYORI", ""))),
                        "finish": finish_raw,
                        "jockey": r.get("jockey", r.get("騎手", r.get("KISHUMEI_RYAKUSHO", ""))),
                        "odds": odds_raw,
                        "race_name": str(race_name_raw).strip() if race_name_raw else "",
                        "class_name": str(class_raw).strip() if class_raw else "",
                        "time": str(time_raw).strip() if time_raw else "",
                        "agari": str(agari_raw).strip().replace("秒", "") if agari_raw else "",
                        "popularity": popularity_raw,
                        "corner": str(corner_raw).strip() if corner_raw else "",
                        "weight": str(weight_raw).strip().replace("kg", "") if weight_raw else "",
                        "track_condition": str(track_condition_raw).strip() if track_condition_raw else "",
                        "headcount": headcount_raw,
                    })'''

if old_block in content:
    content = content.replace(old_block, new_block)
    with open(path, "w") as f:
        f.write(content)
    print("PATCHED successfully")
else:
    print("ERROR: old_block not found")
    # Debug: show what's around runs.append
    idx = content.find("runs.append({")
    if idx >= 0:
        print(f"Found 'runs.append' at index {idx}")
        print(repr(content[idx:idx+500]))
