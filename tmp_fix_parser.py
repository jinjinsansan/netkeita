"""Fix _parse_danwa in stable_comment.py on VPS."""
import re

filepath = '/opt/dlogic/linebot/scrapers/stable_comment.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_func = '''def _parse_danwa(text: str) -> dict:
    """Parse a danwa cell text into structured data.

    Input format: "\u25cb\u30b8\u30e5\u30fc\u30f3\u30c9\u30e9\u30b4\u30f3(\u72b6\u614b\u306f\u7dad\u6301)\\n\u3000\u9234\u6728\u5553\u5e2b\u2015\u2015\u30b3\u30e1\u30f3\u30c8\u672c\u6587"
    """
    mark = ""
    status = ""
    trainer = ""
    comment = ""

    # Extract mark (first char if it's a special symbol)
    if text and text[0] in "\u25ce\u25cb\u25b2\u25b3\u00d7\u2606":
        mark = text[0]
        text = text[1:]

    # Extract status from parentheses
    m_status = re.search(r"[\\(\uff08](.+?)[\\)\uff09]", text)
    if m_status:
        status = m_status.group(1)

    # Extract trainer and comment after \u2015\u2015
    m_comment = re.search(r"[\\s\u3000]+(.+?)(?:\u2015\u2015|\u30fc{2}|\u2500\u2500)(.+)", text, re.DOTALL)
    if m_comment:
        trainer = m_comment.group(1).strip()
        comment = m_comment.group(2).strip().replace("\\n", " ").replace("\u3000", " ")

    return {"mark": mark, "status": status, "trainer": trainer, "comment": comment}'''

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

    return {"mark": mark, "status": status, "trainer": trainer, "comment": comment}'''

if old_func in content:
    content = content.replace(old_func, new_func)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: File updated')
else:
    print('ERROR: Could not find old function')
    # Try to find the function
    idx = content.find('def _parse_danwa')
    if idx >= 0:
        print(f'Found at index {idx}')
        print(repr(content[idx:idx+500]))
    else:
        print('Function not found at all!')
