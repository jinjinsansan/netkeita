"""Patch: Remove [:5] limit from calculate_meta_scores in metalogic_engine.py"""

filepath = "/opt/dlogic/backend/services/metalogic_engine.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Replace the [:5] limit - return all results instead
old = "        meta_results.sort(key=lambda x: x[1], reverse=True)\n        return meta_results[:5]"
new = "        meta_results.sort(key=lambda x: x[1], reverse=True)\n        return meta_results"

if old not in content:
    print("WARNING: Could not find meta_results[:5] marker, checking alternatives...")
    # Try with different whitespace
    import re
    pattern = r'meta_results\.sort\(key=lambda x: x\[1\], reverse=True\)\s+return meta_results\[:5\]'
    if re.search(pattern, content):
        content = re.sub(
            r'(meta_results\.sort\(key=lambda x: x\[1\], reverse=True\)\s+return meta_results)\[:5\]',
            r'\1',
            content
        )
        print("OK: Removed [:5] limit (regex match)")
    else:
        print("ERROR: Could not find meta_results[:5] in any form")
        import sys; sys.exit(1)
else:
    content = content.replace(old, new)
    print("OK: Removed [:5] limit from calculate_meta_scores")

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
