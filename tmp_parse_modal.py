from bs4 import BeautifulSoup

with open("/tmp/horse_modal_pw.html") as f:
    soup = BeautifulSoup(f.read(), "lxml")

# Find horse-specific data sections
for section in soup.select("[class*='Data'], [class*='data'], [class*='Analysis'], [class*='Result']"):
    cls = section.get("class", [])
    text = section.get_text(strip=True)[:300]
    if any(k in text for k in ["勝率", "複勝率", "着順", "1-", "2-", "3-", "未経験"]):
        print(f"CLASS: {cls}")
        print(f"TEXT: {text}")
        print("---")

print("\n=== Looking for table structure ===")
for table in soup.select("table"):
    text = table.get_text(strip=True)[:200]
    if "勝率" in text or "複勝" in text:
        print(f"TABLE class={table.get('class')}")
        for tr in table.select("tr"):
            cells = [td.get_text(strip=True) for td in tr.select("td,th")]
            if cells:
                print(f"  ROW: {cells}")
        print("---")
