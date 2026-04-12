"""Click on 走行解析 tab and extract content."""
import sys
sys.path.insert(0, "/opt/dlogic/linebot")
from playwright.sync_api import sync_playwright

race_id = "202606030311"
horse_id = "2022105230"
url = f"https://race.sp.netkeiba.com/modal/horse.html?race_id={race_id}&horse_id={horse_id}&i=1&rf=shutuba_modal&tab=0"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(3000)

    # Find the 走行解析 tab link and click it
    active_slide = page.query_selector("div.slick-slide.slick-active:not(.slick-cloned)")
    if active_slide:
        # Find all tab links within this slide
        tabs = active_slide.query_selector_all("li")
        for t in tabs:
            text = t.inner_text().strip()
            if "走行解析" in text:
                print(f"Found tab: {text}")
                t.click()
                page.wait_for_timeout(3000)
                break

        # Now extract content from active slide
        text = active_slide.inner_text()
        lines = [l.strip() for l in text.split("\n") if l.strip() and len(l.strip()) > 1]
        print(f"\n=== Content after clicking 走行解析 ({len(lines)} lines) ===")
        for line in lines[:60]:
            print(f"  {line}")

        # Also check for any data-related elements
        race_level = active_slide.query_selector_all("[class*='Level'], [class*='level'], [class*='Race']")
        for el in race_level:
            cls = el.get_attribute("class") or ""
            txt = el.inner_text().strip()
            if txt:
                print(f"\n  ELEMENT class={cls}: {txt}")
    else:
        print("NO ACTIVE SLIDE")

    browser.close()
