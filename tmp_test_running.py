"""Test fetching running analysis tab from netkeiba horse modal."""
import sys
sys.path.insert(0, "/opt/dlogic/linebot")
from playwright.sync_api import sync_playwright

# tab=7 is 走行解析 (8th tab, 0-indexed)
race_id = "202606030311"
horse_id = "2022105230"  # 2nd horse (ミニトランザット)
url = f"https://race.sp.netkeiba.com/modal/horse.html?race_id={race_id}&horse_id={horse_id}&i=1&rf=shutuba_modal&tab=7"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(5000)

    # Save HTML
    html = page.content()
    with open("/tmp/horse_running.html", "w") as f:
        f.write(html)
    print(f"Saved {len(html)} bytes")

    # Look for running analysis content
    # Check visible text
    active = page.query_selector("div.slick-slide.slick-active:not(.slick-cloned)")
    if active:
        text = active.inner_text()
        # Filter out noise
        lines = [l.strip() for l in text.split("\n") if l.strip() and len(l.strip()) > 1]
        for line in lines[:40]:
            print(f"  {line}")
    else:
        print("NO ACTIVE SLIDE")

    browser.close()
