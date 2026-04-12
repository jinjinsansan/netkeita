import sys
sys.path.insert(0, "/opt/dlogic/linebot")
from playwright.sync_api import sync_playwright

race_id = "202606030311"
url = f"https://race.sp.netkeiba.com/modal/horse.html?race_id={race_id}&horse_id=0&i=0&rf=shutuba_modal&tab=2"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(5000)

    # Debug: check active slide classes
    active_slides = page.query_selector_all("div.slick-slide.slick-active")
    print(f"Active slides: {len(active_slides)}")
    for s in active_slides:
        cls = s.get_attribute("class")
        idx = s.get_attribute("data-slick-index")
        print(f"  class={cls} data-slick-index={idx}")

    # Try getting current slide
    current = page.query_selector("div.slick-slide.slick-current")
    if current:
        cls = current.get_attribute("class")
        idx = current.get_attribute("data-slick-index")
        print(f"\nCurrent slide: class={cls} index={idx}")
        inner = current.inner_html()[:1000]
        print(f"Inner HTML (first 1000):\n{inner}")

    # Check what tab is active
    tabs = page.query_selector_all("[class*='Tab'] li, [class*='tab'] li")
    for t in tabs:
        print(f"Tab: {t.get_attribute('class')} text={t.inner_text().strip()}")

    browser.close()
