"""Get horse_ids from PC shutuba page, then navigate SP modal carousel."""
import sys, json
sys.path.insert(0, "/opt/dlogic/linebot")
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import requests, re

race_id = "202606030311"

# Step 1: Get horse_id list from PC shutuba page (no JS needed)
url = f"https://race.netkeiba.com/race/shutuba.html?race_id={race_id}"
resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
resp.encoding = "euc-jp"
soup = BeautifulSoup(resp.text, "lxml")

horse_list = []
for tr in soup.select("tr.HorseList"):
    tds = tr.select("td")
    if len(tds) < 4:
        continue
    num_text = tds[1].get_text(strip=True)
    if not num_text.isdigit():
        continue
    horse_num = int(num_text)

    # Find horse_id from link
    link = tds[3].select_one("a[href*='/horse/']")
    if link:
        href = link.get("href", "")
        m = re.search(r'/horse/(\d+)', href)
        if m:
            horse_list.append({"num": horse_num, "hid": m.group(1)})

print(f"Horses: {len(horse_list)}")
for h in horse_list:
    print(f"  馬番{h['num']}: {h['hid']}")

# Step 2: Navigate SP modal with carousel
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    first_hid = horse_list[0]["hid"]
    modal_url = f"https://race.sp.netkeiba.com/modal/horse.html?race_id={race_id}&horse_id={first_hid}&i=0&rf=shutuba_modal&tab=2"
    page.goto(modal_url, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(4000)

    results = {}
    total = len(horse_list)

    for i in range(total):
        page.wait_for_timeout(800)

        active = page.query_selector("div.slick-slide.slick-active:not(.slick-cloned)")
        if not active:
            if i < total - 1:
                next_btn = page.query_selector("button.slick-next, .slick-next")
                if next_btn:
                    next_btn.click()
            continue

        horse_num = horse_list[i]["num"]

        tables = active.query_selector_all("table.Racing_Common_Table")
        stats = {}
        if tables:
            rows = tables[0].query_selector_all("tr")
            for row in rows:
                cells = row.query_selector_all("td, th")
                texts = [c.inner_text().strip() for c in cells]
                if len(texts) >= 4 and texts[1] != "着順" and "***" not in texts[1]:
                    stats[texts[0]] = {
                        "record": texts[1],
                        "win_rate": texts[2],
                        "place_rate": texts[3],
                    }

        results[horse_num] = stats
        status = f"{list(stats.keys())}" if stats else "EMPTY"
        print(f"  馬番{horse_num}: {status}")

        if i < total - 1:
            next_btn = page.query_selector("button.slick-next, .slick-next")
            if next_btn:
                next_btn.click()

    browser.close()

print(f"\nResult: {sum(1 for v in results.values() if v)}/{total} horses with stats")
