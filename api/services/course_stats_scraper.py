"""Scrape course performance stats from netkeiba (free data).

Fetches per-race (all horses at once) via Playwright carousel.
Cached in Redis db=4 for 24 hours.
"""

import json
import logging
import re
import redis
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_redis = redis.Redis(host="127.0.0.1", port=6379, db=4, decode_responses=True)
_CACHE_TTL = 86400  # 24h
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def _cache_key(race_id_netkeiba: str) -> str:
    return f"nk:course_stats:{race_id_netkeiba}"


def _get_horse_ids(race_id_netkeiba: str) -> list[dict]:
    """Get ordered [{num, hid}] from PC shutuba page (no JS)."""
    url = f"https://race.netkeiba.com/race/shutuba.html?race_id={race_id_netkeiba}"
    resp = requests.get(url, headers={"User-Agent": _UA}, timeout=15)
    resp.encoding = "euc-jp"
    soup = BeautifulSoup(resp.text, "lxml")

    result = []
    for tr in soup.select("tr.HorseList"):
        tds = tr.select("td")
        if len(tds) < 4:
            continue
        num_text = tds[1].get_text(strip=True)
        if not num_text.isdigit():
            continue
        link = tds[3].select_one("a[href*='/horse/']")
        if link:
            m = re.search(r"/horse/(\d+)", link.get("href", ""))
            if m:
                result.append({"num": int(num_text), "hid": m.group(1)})
    return result


def _fetch_all_stats(race_id_netkeiba: str, horse_list: list[dict]) -> dict:
    """Navigate SP modal carousel to collect course stats for all horses."""
    from playwright.sync_api import sync_playwright

    first_hid = horse_list[0]["hid"]
    url = (
        f"https://race.sp.netkeiba.com/modal/horse.html"
        f"?race_id={race_id_netkeiba}&horse_id={first_hid}"
        f"&i=0&rf=shutuba_modal&tab=2"
    )

    results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(4000)

        total = len(horse_list)
        for i in range(total):
            page.wait_for_timeout(800)

            active = page.query_selector(
                "div.slick-slide.slick-active:not(.slick-cloned)"
            )
            if not active:
                if i < total - 1:
                    btn = page.query_selector("button.slick-next, .slick-next")
                    if btn:
                        btn.click()
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

            if i < total - 1:
                btn = page.query_selector("button.slick-next, .slick-next")
                if btn:
                    btn.click()

        browser.close()
    return results


def fetch_course_stats_for_race(race_id_netkeiba: str) -> dict:
    """Fetch and cache course stats for all horses in a race.

    Returns: {horse_number(int): {label: {record, win_rate, place_rate}}}
    """
    key = _cache_key(race_id_netkeiba)
    try:
        cached = _redis.get(key)
        if cached:
            return {int(k): v for k, v in json.loads(cached).items()}
    except Exception:
        pass

    try:
        horse_list = _get_horse_ids(race_id_netkeiba)
        if not horse_list:
            logger.warning(f"No horse_ids for {race_id_netkeiba}")
            return {}

        results = _fetch_all_stats(race_id_netkeiba, horse_list)

        if results:
            cache_data = {str(k): v for k, v in results.items()}
            try:
                _redis.setex(key, _CACHE_TTL, json.dumps(cache_data, ensure_ascii=False))
            except Exception:
                pass

        logger.info(f"Course stats: {len(results)} horses for {race_id_netkeiba}")
        return results
    except Exception:
        logger.exception(f"Course stats failed for {race_id_netkeiba}")
        return {}


def get_course_stats_for_horse(race_id_netkeiba: str, horse_number: int) -> dict:
    """Get course stats for a single horse from Redis cache only."""
    key = _cache_key(race_id_netkeiba)
    try:
        cached = _redis.get(key)
        if cached:
            all_stats = {int(k): v for k, v in json.loads(cached).items()}
            return all_stats.get(horse_number, {})
    except Exception:
        pass
    return {}
