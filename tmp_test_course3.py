import sys
sys.path.insert(0, "/opt/dlogic/linebot")
from bs4 import BeautifulSoup

with open("/tmp/horse_modal_pw.html") as f:
    soup = BeautifulSoup(f.read(), "lxml")

slides = soup.select("div.slick-slide:not(.slick-cloned)")
print(f"Total slides: {len(slides)}")

for slide in slides:
    idx = slide.get("data-slick-index", "?")
    num_el = slide.select_one("[class*='Num'], [class*='Waku']")
    num = num_el.get_text(strip=True) if num_el else "?"

    analysis = slide.select_one("div.RacingAnalysisArea")
    tables = analysis.select("table.Racing_Common_Table") if analysis else []

    first_row_data = ""
    if tables:
        rows = tables[0].select("tr")
        for row in rows:
            cells = [td.get_text(strip=True) for td in row.select("td, th")]
            if len(cells) >= 4 and cells[1] != "着順" and "***" not in cells[1]:
                first_row_data = f"{cells[0]}: {cells[1]} {cells[2]} {cells[3]}"
                break

    print(f"Slide {idx}: 馬番{num} tables={len(tables)} data={first_row_data or 'NONE'}")
