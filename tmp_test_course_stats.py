"""Test course stats parsing from the already-saved Playwright HTML."""
import json
import sys
sys.path.insert(0, "/opt/dlogic/linebot")
from bs4 import BeautifulSoup

with open("/tmp/horse_modal_pw.html") as f:
    soup = BeautifulSoup(f.read(), "lxml")

# Find all horse slides in carousel
slides = soup.select("div.slick-slide")
print(f"Total slides: {len(slides)}")

for slide in slides:
    # Horse number
    umaban = slide.select_one("span.Umaban, td.Umaban, div.Umaban")
    num_text = ""
    if umaban:
        num_text = umaban.get_text(strip=True)

    # Horse name
    name_el = slide.select_one("span.Horse_Name, div.Horse_Name, a.Horse_Name")
    name = name_el.get_text(strip=True) if name_el else "?"

    # Course analysis area
    analysis = slide.select_one("div.RacingAnalysisArea")
    if not analysis:
        continue

    tables = analysis.select("table.Racing_Common_Table")
    if not tables:
        continue

    # First table = course stats (free)
    first_table = tables[0]
    rows = first_table.select("tr")
    stats = []
    for row in rows:
        cells = [td.get_text(strip=True) for td in row.select("td, th")]
        if len(cells) >= 4 and cells[1] != "着順":
            if "***" not in cells[1]:
                stats.append(cells)

    if stats:
        print(f"\n馬番{num_text} {name}:")
        for cells in stats:
            print(f"  {cells[0]}: {cells[1]} 勝率{cells[2]} 複勝{cells[3]}")
