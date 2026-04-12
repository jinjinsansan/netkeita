"""Fix _parse_danwa in stable_comment.py on VPS - using index-based replacement."""
import re

filepath = '/opt/dlogic/linebot/scrapers/stable_comment.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Find function boundaries
start = content.find('def _parse_danwa(text: str) -> dict:')
if start == -1:
    print('ERROR: function not found')
    exit(1)

# Find the next function or end
end = content.find('\ndef fetch_race_id_map', start)
if end == -1:
    end = content.find('\ndef ', start + 10)
if end == -1:
    print('ERROR: could not find end of function')
    exit(1)

old_section = content[start:end]
print('Old function found, length:', len(old_section))
print('First 100 chars:', repr(old_section[:100]))

new_func = '''def _parse_danwa(text: str) -> dict:
    """Parse a danwa cell text into structured data.

    Handles two formats:
    Format 1: "mark horse_name(status)\\n trainer\u2015\u2015comment"
    Format 2: "mark horse_name\u3010trainer\u3011comment"
    """
    mark = ""
    status = ""
    trainer = ""
    comment = ""

    # Extract mark (first char if it's a special symbol)
    if text and text[0] in "\u25ce\u25cb\u25b2\u25b3\u00d7\u2606":
        mark = text[0]
        text = text[1:]

    # Extract status from parentheses (round brackets)
    m_status = re.search(r"[\\(\uff08](.+?)[\\)\uff09]", text)
    if m_status:
        status = m_status.group(1)

    # Try Format 2 first: \u3010trainer\u3011comment
    m_bracket = re.search(r"\u3010(.+?)\u3011(.+)", text, re.DOTALL)
    if m_bracket:
        trainer = m_bracket.group(1).strip()
        comment = m_bracket.group(2).strip().replace("\\n", " ").replace("\u3000", " ")
    else:
        # Fallback to Format 1: trainer\u2015\u2015comment
        m_comment = re.search(r"[\\s\u3000]+(.+?)(?:\u2015\u2015|\u30fc{2}|\u2500\u2500)(.+)", text, re.DOTALL)
        if m_comment:
            trainer = m_comment.group(1).strip()
            comment = m_comment.group(2).strip().replace("\\n", " ").replace("\u3000", " ")

    return {"mark": mark, "status": status, "trainer": trainer, "comment": comment}

'''

new_content = content[:start] + new_func + content[end:]

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(new_content)

print('SUCCESS: File updated')

# Verify
with open(filepath, 'r', encoding='utf-8') as f:
    verify = f.read()
if '【(.+?)】' in verify:
    print('VERIFIED: New parser pattern found in file')
else:
    print('WARNING: New pattern not found - check file')
