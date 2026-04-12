import sys
sys.path.insert(0, "/opt/dlogic/linebot")
from bs4 import BeautifulSoup

with open("/tmp/horse_modal_pw.html") as f:
    soup = BeautifulSoup(f.read(), "lxml")

slides = soup.select("div.slick-slide:not(.slick-cloned)")
print(f"Non-cloned slides: {len(slides)}")

for i, slide in enumerate(slides):
    # Try all possible number/name selectors
    # Look for horse number in various elements
    all_text = slide.get_text()

    # Find horse name
    name_el = slide.select_one("[class*='Horse_Name'], [class*='horse_name'], .HorseName")
    name = name_el.get_text(strip=True) if name_el else ""

    # Find data-index or ordering attribute
    data_idx = slide.get("data-slick-index", "")

    # Check for number elements
    num_el = slide.select_one("[class*='Num'], [class*='Waku'], [class*='waku']")
    num_txt = num_el.get_text(strip=True) if num_el else ""

    # Check data-analysis existence
    analysis = slide.select_one("div.RacingAnalysisArea")
    has_stats = bool(analysis and analysis.select("table.Racing_Common_Table"))

    # Find the horse header area
    header = slide.select_one("[class*='Header'], [class*='header']")
    header_html = str(header)[:300] if header else "NO HEADER"

    if has_stats and i < 5:
        print(f"\n--- Slide {i} (data-index={data_idx}) ---")
        print(f"Name: {name}")
        print(f"Num element: {num_txt}")
        print(f"Header HTML: {header_html}")

        # Get first 500 chars of slide HTML to find horse number
        slide_html = str(slide)[:800]
        # Look for horse number pattern
        import re
        nums_in_html = re.findall(r'Num[^"]*"[^>]*>(\d+)<', slide_html)
        print(f"Nums found in HTML: {nums_in_html}")

        # Look for any single digit near horse info
        info_el = slide.select_one("[class*='Info']")
        if info_el:
            print(f"Info text: {info_el.get_text(strip=True)[:100]}")
