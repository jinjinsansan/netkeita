import sys, json, logging
sys.path.insert(0, "/opt/dlogic/linebot")
logging.basicConfig(level=logging.INFO)

# Inline the scraper logic for testing
from playwright.sync_api import sync_playwright

race_id = "202606030311"
url = f"https://race.sp.netkeiba.com/modal/horse.html?race_id={race_id}&horse_id=0&i=0&rf=shutuba_modal&tab=2"

results = {}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(3000)

    slides = page.query_selector_all("div.slick-slide:not(.slick-cloned)")
    total = len(slides)
    print(f"Total slides: {total}")

    for i in range(total):
        page.wait_for_timeout(500)

        active = page.query_selector("div.slick-slide.slick-active:not(.slick-cloned)")
        if active:
            num_el = active.query_selector("[class*='Num']")
            num_text = num_el.inner_text().strip() if num_el else ""
            horse_num = int(num_text) if num_text.isdigit() else 0

            # Extract stats from first table
            stats = {}
            tables = active.query_selector_all("table.Racing_Common_Table")
            if tables:
                rows = tables[0].query_selector_all("tr")
                for row in rows:
                    cells = row.query_selector_all("td, th")
                    texts = [c.inner_text().strip() for c in cells]
                    if len(texts) >= 4 and texts[1] != "着順" and "***" not in texts[1]:
                        stats[texts[0]] = {"record": texts[1], "win_rate": texts[2], "place_rate": texts[3]}

            if horse_num > 0:
                results[horse_num] = stats
                status = "OK" if stats else "NO DATA"
                print(f"  馬番{horse_num}: {status} {list(stats.keys()) if stats else ''}")

        if i < total - 1:
            next_btn = page.query_selector("button.slick-next, .slick-next")
            if next_btn:
                next_btn.click()

    browser.close()

print(f"\nTotal: {len(results)} horses with data: {sum(1 for v in results.values() if v)}")
print(json.dumps(results, ensure_ascii=False, indent=2))
