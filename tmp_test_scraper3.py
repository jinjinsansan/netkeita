"""Test: Navigate carousel from first horse using JS click on horse numbers."""
import sys
sys.path.insert(0, "/opt/dlogic/linebot")
from playwright.sync_api import sync_playwright
import json

race_id = "202606030311"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # First get horse_ids from shutuba page
    shutuba_url = f"https://race.sp.netkeiba.com/race/shutuba.html?race_id={race_id}"
    page.goto(shutuba_url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(2000)

    # Extract horse_ids from links
    horse_ids = []
    links = page.query_selector_all("a[href*='horse_id=']")
    for link in links:
        href = link.get_attribute("href") or ""
        if "horse_id=" in href:
            hid = href.split("horse_id=")[1].split("&")[0]
            if hid and hid not in [h[1] for h in horse_ids]:
                # Get horse number from parent row
                parent_tr = link.evaluate("el => el.closest('tr')")
                horse_ids.append(hid)

    print(f"Found {len(horse_ids)} horse_ids")
    for hid in horse_ids[:5]:
        print(f"  {hid}")

    # Now open modal for first horse and navigate
    first_hid = horse_ids[0] if horse_ids else "2018101343"
    modal_url = f"https://race.sp.netkeiba.com/modal/horse.html?race_id={race_id}&horse_id={first_hid}&i=0&rf=shutuba_modal&tab=2"
    page.goto(modal_url, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(5000)

    # Check which slide is active now
    active = page.query_selector("div.slick-slide.slick-active:not(.slick-cloned)")
    if active:
        idx = active.get_attribute("data-slick-index")
        num_el = active.query_selector("[class*='Num']")
        num = num_el.inner_text().strip() if num_el else "?"
        print(f"\nFirst active: index={idx} num={num}")

        # Check for table data
        tables = active.query_selector_all("table.Racing_Common_Table")
        print(f"Tables: {len(tables)}")
        if tables:
            rows = tables[0].query_selector_all("tr")
            for row in rows:
                cells = row.query_selector_all("td, th")
                texts = [c.inner_text().strip() for c in cells]
                print(f"  Row: {texts}")

    browser.close()
