from playwright.sync_api import sync_playwright

url = "https://race.sp.netkeiba.com/modal/horse.html?race_id=202606030311&horse_id=2018101343&i=0&rf=shutuba_modal&tab=2"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(5000)
    html = page.content()
    with open("/tmp/horse_modal_pw.html", "w") as f:
        f.write(html)
    print(f"Saved {len(html)} bytes")
    browser.close()
