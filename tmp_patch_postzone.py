path = "/opt/dlogic/backend/api/v2/viewlogic_analysis.py"
with open(path, "r") as f:
    content = f.read()

old = """        for i, jname in enumerate(jockeys):
            if not jname:
                continue
            post = posts[i] if i < len(posts) else 0
            if post <= 6:
                post_zone = "内枠（1-6）"
            elif post <= 12:
                post_zone = "中枠（7-12）"
            else:
                post_zone = "外枠（13-18）"
"""

new = """        horse_numbers = request.horse_numbers or []
        for i, jname in enumerate(jockeys):
            if not jname:
                continue
            umaban = horse_numbers[i] if i < len(horse_numbers) else 0
            if umaban <= 6:
                post_zone = "内枠（1-6）"
            elif umaban <= 12:
                post_zone = "中枠（7-12）"
            else:
                post_zone = "外枠（13-18）"
"""

if old in content:
    content = content.replace(old, new)
    with open(path, "w") as f:
        f.write(content)
    print("PATCHED: post -> horse_number for post_zone")
else:
    print("ERROR: old block not found")
