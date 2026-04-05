"""Fetch race results (winners + win payouts) from netkeiba.

Used by the mypage vote-history endpoint to compute hit-rate and ROI.

Storage: Redis db=4 (shared with course_stats_scraper, rewriter).
Key:     nk:race_result:{race_id}
Value (finalised): {
    "winner_horse_numbers": [int, ...],   # list — multiple on dead heat
    "win_payouts":          {str: int},   # {"3": 430} — yen per 100 yen bet
    "finalized":            True,
    "cancelled":            False,
    "fetched_at":           "2026-04-05T17:30:00+09:00",
}
Value (cancelled): finalized=False, cancelled=True, refund 100 on ROI calc.

Negative cache (short TTL) is used for pages we fetched successfully but
that aren't yet finalised — prevents hammering netkeiba every minute.

Scraping strategy:
  1. Two to three HTTP attempts with exponential backoff (403/5xx tolerant)
  2. Let requests auto-detect encoding (UTF-8 for current pages, fallback
     to EUC-JP for archival pages)
  3. Try multiple CSS selector paths because netkeiba alters markup
  4. Detect cancellation strings ("中止", "取止", "発走取止")
  5. Cap the payout at a sane upper bound to avoid parser madness
  6. Gracefully return None on unknown states so callers can keep "pending"
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timedelta, timezone

import redis
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ── Redis ────────────────────────────────────────────────────────────────────
_redis = redis.Redis(host="127.0.0.1", port=6379, db=4, decode_responses=True)

_CACHE_KEY_PREFIX = "nk:race_result"
_NEG_CACHE_KEY_PREFIX = "nk:race_result:neg"
_CACHE_TTL_FINAL = 86400 * 30        # finalised results retained 30 days
_CACHE_TTL_CANCELLED = 86400 * 30    # cancelled races same
_CACHE_TTL_NEGATIVE = 900            # not-yet-finalised: retry in 15 min

# ── HTTP ─────────────────────────────────────────────────────────────────────
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)
_REQUEST_TIMEOUT = 15
_MAX_RETRIES = 3
_RETRY_BACKOFF_BASE = 1.5  # seconds; actual = base * 2**attempt

# ── Payout sanity cap ────────────────────────────────────────────────────────
# The single largest 単勝 payout in Japanese racing history is ~83,000 yen
# (Kokonoe Park 2017). Anything above 1,000,000 is almost certainly a
# parsing error and should be discarded.
_PAYOUT_SANITY_CAP = 1_000_000

_JST = timezone(timedelta(hours=9))
_CANCEL_PATTERNS = ("中止", "取止", "発走取止", "開催中止", "取りやめ")


# ─────────────────────────────────────────────────────────────────────────────
# Public cache API
# ─────────────────────────────────────────────────────────────────────────────


def _cache_key(race_id: str) -> str:
    return f"{_CACHE_KEY_PREFIX}:{race_id}"


def _neg_cache_key(race_id: str) -> str:
    return f"{_NEG_CACHE_KEY_PREFIX}:{race_id}"


def get_cached_result(race_id: str) -> dict | None:
    """Return the cached finalised (or cancelled) race result.

    Never performs network I/O — safe to call from latency-sensitive handlers.
    Returns None when the race has no positive cache entry yet.
    """
    if not race_id:
        return None
    try:
        raw = _redis.get(_cache_key(race_id))
        if raw:
            return json.loads(raw)
    except Exception:
        logger.exception(f"race_result cache load failed: {race_id}")
    return None


def save_result(race_id: str, result: dict) -> None:
    """Persist a finalised or cancelled race result in Redis."""
    if not race_id or not result:
        return
    try:
        ttl = _CACHE_TTL_CANCELLED if result.get("cancelled") else _CACHE_TTL_FINAL
        payload = json.dumps(result, ensure_ascii=False)
        _redis.setex(_cache_key(race_id), ttl, payload)
        # Clear any negative cache — the race is now resolved
        _redis.delete(_neg_cache_key(race_id))
    except Exception:
        logger.exception(f"race_result cache save failed: {race_id}")


def _is_neg_cached(race_id: str) -> bool:
    try:
        return bool(_redis.exists(_neg_cache_key(race_id)))
    except Exception:
        return False


def _set_neg_cache(race_id: str) -> None:
    try:
        _redis.setex(_neg_cache_key(race_id), _CACHE_TTL_NEGATIVE, "1")
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Scraping
# ─────────────────────────────────────────────────────────────────────────────


def fetch_result_from_netkeiba(
    race_id_netkeiba: str,
    is_local: bool = False,
    skip_negative_cache: bool = False,
) -> dict | None:
    """Scrape the netkeiba race result page.

    Args:
        race_id_netkeiba: netkeiba 12-digit race id (e.g. "202506040711")
        is_local:        True for NAR (uses nar.netkeiba.com)
        skip_negative_cache: when True, ignore the "retry later" marker

    Returns:
        A finalised/cancelled result dict ready for `save_result`, or None
        if the race isn't finalised yet / the scrape failed after retries.
        Side effect: writes a short-TTL negative cache entry on None returns
        so mypage doesn't retry every view.
    """
    if not race_id_netkeiba or not _valid_nk_race_id(race_id_netkeiba):
        return None

    # Short-circuit: if we recently failed to fetch a finalised state, wait.
    if not skip_negative_cache and _is_neg_cached(race_id_netkeiba):
        logger.debug(f"negative cache hit: {race_id_netkeiba}")
        return None

    base = "https://nar.netkeiba.com" if is_local else "https://race.netkeiba.com"
    url = f"{base}/race/result.html?race_id={race_id_netkeiba}"

    html = _http_get_with_retry(url)
    if html is None:
        _set_neg_cache(race_id_netkeiba)
        return None

    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        logger.exception("BeautifulSoup parse failed")
        _set_neg_cache(race_id_netkeiba)
        return None

    # Cancellation detection comes first — cancelled pages may still show
    # entries but without a winner.
    if _detect_cancellation(soup):
        logger.info(f"race cancelled: {race_id_netkeiba}")
        return {
            "winner_horse_numbers": [],
            "win_payouts": {},
            "finalized": False,
            "cancelled": True,
            "fetched_at": datetime.now(_JST).isoformat(),
        }

    winners = _parse_winners(soup)
    if not winners:
        _set_neg_cache(race_id_netkeiba)
        return None

    payouts = _parse_win_payouts(soup, winners)

    return {
        "winner_horse_numbers": winners,
        "win_payouts": {str(n): p for n, p in payouts.items()},
        "finalized": True,
        "cancelled": False,
        "fetched_at": datetime.now(_JST).isoformat(),
    }


def fetch_and_cache(
    race_id: str, race_id_netkeiba: str, is_local: bool = False
) -> dict | None:
    """Convenience: check cache first, scrape on miss, persist on success."""
    cached = get_cached_result(race_id)
    if cached:
        return cached

    result = fetch_result_from_netkeiba(race_id_netkeiba, is_local=is_local)
    if result:
        save_result(race_id, result)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# HTTP with retry
# ─────────────────────────────────────────────────────────────────────────────


def _http_get_with_retry(url: str) -> str | None:
    """GET with exponential-backoff retry. Returns decoded HTML or None."""
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            resp = requests.get(
                url,
                headers={"User-Agent": _UA, "Accept-Language": "ja,en;q=0.8"},
                timeout=_REQUEST_TIMEOUT,
            )
            if resp.status_code == 200:
                # Let requests auto-detect encoding via apparent_encoding
                # (works for both UTF-8 new pages and EUC-JP archive pages).
                if not resp.encoding or resp.encoding.lower() in ("iso-8859-1", "ascii"):
                    resp.encoding = resp.apparent_encoding or "utf-8"
                return resp.text
            if resp.status_code in (404, 410):
                # Race page doesn't exist — don't retry
                return None
            logger.warning(
                f"scrape got HTTP {resp.status_code} for {url} (attempt {attempt + 1})"
            )
        except Exception as e:
            last_exc = e
            logger.warning(
                f"scrape error for {url} (attempt {attempt + 1}): {e.__class__.__name__}: {e}"
            )

        if attempt < _MAX_RETRIES - 1:
            time.sleep(_RETRY_BACKOFF_BASE * (2**attempt))

    if last_exc:
        logger.error(f"scrape failed after retries: {url} ({last_exc})")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# HTML parsing
# ─────────────────────────────────────────────────────────────────────────────


def _detect_cancellation(soup: BeautifulSoup) -> bool:
    """Return True if the page shows that the race was cancelled / abandoned."""
    # Common containers where netkeiba displays cancellation notices
    for sel in (
        ".Result_Cancel",
        ".RaceData02_Cancel",
        "div.Cancel",
        ".ChushiTextWarp",
        ".RaceList_Notice",
    ):
        el = soup.select_one(sel)
        if el and any(p in el.get_text() for p in _CANCEL_PATTERNS):
            return True

    # Header area fallback — look near the race title
    for sel in ("div.RaceList_Item02", ".RaceList_NameBox", "h1.RaceName"):
        el = soup.select_one(sel)
        if el and any(p in el.get_text() for p in _CANCEL_PATTERNS):
            return True

    return False


def _parse_winners(soup: BeautifulSoup) -> list[int]:
    """Return the sorted list of 1st-place horse numbers (supports dead heat)."""
    winners: list[int] = []

    # Strategy 1: tr.HorseList rows — standard result table
    for tr in soup.select("tr.HorseList"):
        rank_text = _find_text(
            tr,
            [
                "td.Result_Num div.Rank",
                "td.Result_Num span",
                "div.Rank",
                "td.Rank",
                ".Rank_Num",
            ],
        )
        if rank_text != "1":
            continue
        num_text = _find_text(
            tr,
            [
                "td.Num.Txt_C span",
                "td.Num span",
                "td.Umaban",
                "span.Umaban",
                ".Umaban",
            ],
        )
        if num_text and num_text.isdigit():
            n = int(num_text)
            if 1 <= n <= 28 and n not in winners:
                winners.append(n)

    # Strategy 2: dedicated "winning horse" block
    if not winners:
        for sel in (
            "div.Result_Win td.Umaban",
            "div.FirstHorse .Umaban",
            ".Ninki_1 .Umaban",
        ):
            el = soup.select_one(sel)
            if el:
                txt = el.get_text(strip=True)
                if txt.isdigit():
                    n = int(txt)
                    if 1 <= n <= 28:
                        winners.append(n)
                        break

    return sorted(set(winners))


def _parse_win_payouts(soup: BeautifulSoup, winners: list[int]) -> dict[int, int]:
    """Return {horse_number: payout_yen} for each 1st-place finisher.

    On dead heat, netkeiba lists the single payout value which applies to
    every winning ticket, so we assign the same value to all winners.
    """
    if not winners:
        return {}

    single_payout = _extract_tansho_payout(soup)

    # Dead heat: the same payout applies to all winning horses
    return {num: single_payout for num in winners}


def _extract_tansho_payout(soup: BeautifulSoup) -> int:
    """Find the 単勝 (win) payout amount on the result page."""
    # Strategy 1: Payout_Detail_Table / Result_Pay_Back tables
    tables = soup.select(
        "table.Payout_Detail_Table, "
        "div.Result_Pay_Back table, "
        "div.Payout_Detail_Table table, "
        "table.Payout"
    )
    for table in tables:
        for tr in table.select("tr"):
            th = tr.select_one("th")
            if not th or "単勝" not in th.get_text():
                continue
            for td in tr.select("td"):
                amount = _extract_yen(td.get_text())
                if 0 < amount <= _PAYOUT_SANITY_CAP:
                    return amount

    # Strategy 2: walk any element with "単勝" text and look at next sibling
    for node in soup.find_all(string=re.compile(r"単勝")):
        parent = getattr(node, "parent", None)
        if not parent:
            continue
        sibling = parent.find_next(["td", "dd", "span"])
        if sibling:
            amount = _extract_yen(sibling.get_text())
            if 0 < amount <= _PAYOUT_SANITY_CAP:
                return amount

    return 0


def _find_text(element, selectors: list[str]) -> str:
    """Return the stripped text of the first matching selector."""
    for sel in selectors:
        el = element.select_one(sel)
        if el:
            txt = el.get_text(strip=True)
            if txt:
                return txt
    return ""


_YEN_PATTERN = re.compile(r"(\d[\d,]*)")


def _extract_yen(text: str) -> int:
    """Extract the FIRST contiguous digit run from a short text chunk.

    Critically, this must NOT concatenate digits from "430円 2人気" into 4302.
    """
    if not text:
        return 0
    # Split on common separators that could glue numbers together
    first_line = text.splitlines()[0] if "\n" in text else text
    m = _YEN_PATTERN.search(first_line)
    if not m:
        return 0
    raw = m.group(1).replace(",", "")
    try:
        return int(raw)
    except ValueError:
        return 0


# ─────────────────────────────────────────────────────────────────────────────
# Misc helpers
# ─────────────────────────────────────────────────────────────────────────────


_NK_RACE_ID_RE = re.compile(r"^\d{10,12}$")


def _valid_nk_race_id(s: str) -> bool:
    """netkeiba race_ids are 10-12 digit numeric strings."""
    return bool(s) and bool(_NK_RACE_ID_RE.match(s))


__all__ = [
    "get_cached_result",
    "save_result",
    "fetch_result_from_netkeiba",
    "fetch_and_cache",
]
