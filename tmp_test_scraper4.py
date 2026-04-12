"""Full working test: get all horse course stats by navigating carousel."""
import sys, json, time
sys.path.insert(0, "/opt/dlogic/linebot")
from playwright.sync_api import sync_playwright

race_id = "202606030311"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # Step 1: Get horse_id list from shutuba page
    shutuba_url = f"https://race.sp.netkeiba.com/race/shutuba.html?race_id={race_id}"
    page.goto(shutuba_url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(2000)

    # Get ordered horse_ids from the modal links (one per horse)
    horse_id_list = page.evaluate("""() => {
        const rows = document.querySelectorAll('tr.HorseList');
        const result = [];
        rows.forEach(row => {
            const numTd = row.querySelector('td:nth-child(2)');
            const num = numTd ? parseInt(numTd.textContent.trim()) : 0;
            const link = row.querySelector('a[href*="horse.html"]');
            let hid = '';
            if (link) {
                const m = link.href.match(/horse_id=(\d+)/);
                if (m) hid = m[1];
            }
            if (num > 0 && hid) result.push({num, hid});
        });
        return result;
    }""")

    print(f"Horses from shutuba: {len(horse_id_list)}")
    for h in horse_id_list:
        print(f"  馬番{h['num']}: {h['hid']}")

    if not horse_id_list:
        print("No horses found!")
        browser.close()
        sys.exit(1)

    # Step 2: Open modal with first horse
    first_hid = horse_id_list[0]["hid"]
    modal_url = f"https://race.sp.netkeiba.com/modal/horse.html?race_id={race_id}&horse_id={first_hid}&i=0&rf=shutuba_modal&tab=2"
    page.goto(modal_url, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(4000)

    total = len(horse_id_list)
    results = {}

    for i in range(total):
        page.wait_for_timeout(800)

        # Extract from active slide
        active = page.query_selector("div.slick-slide.slick-active:not(.slick-cloned)")
        if not active:
            print(f"  Slide {i}: NO ACTIVE")
            if i < total - 1:
                page.query_selector("button.slick-next, .slick-next").click()
            continue

        # Horse number from our ordered list
        horse_num = horse_id_list[i]["num"]

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
        status = f"{list(stats.keys())}" if stats else "NO DATA"
        print(f"  馬番{horse_num}: {status}")

        # Navigate to next
        if i < total - 1:
            next_btn = page.query_selector("button.slick-next, .slick-next")
            if next_btn:
                next_btn.click()

    browser.close()

print(f"\nTotal: {len(results)} horses, {sum(1 for v in results.values() if v)} with stats")
print(json.dumps(results, ensure_ascii=False, indent=2))
