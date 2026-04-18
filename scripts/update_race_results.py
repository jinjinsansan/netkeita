#!/usr/bin/env python3
"""Fetch race results from netkeiba and cache them in Redis.

Runs as a cron after JRA/NAR race cards finish (e.g. 17:00, 20:00, 23:30 JST).
Reads each day's prefetch file, then scrapes the netkeiba result page for
every race that isn't yet cached. Populates the cache consumed by
`/api/votes/my-history` so ROI / hit-rate become live.

Features:
    * Dead-heat aware (multiple winners per race)
    * Cancelled race detection (marks but does not retry)
    * Per-run flock to prevent concurrent cron overlap
    * Negative-cache aware (honours the scraper's retry-later marker)

Usage:
    python scripts/update_race_results.py              # today (JST)
    python scripts/update_race_results.py 20260405     # a specific date
    python scripts/update_race_results.py --days 3     # last 3 days (for catch-up)
    python scripts/update_race_results.py --days 7 --force   # re-scrape even cached
"""

import json
import logging
import os
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone

_API_ROOT = "/opt/dlogic/netkeita-api"
if os.path.isdir(_API_ROOT) and _API_ROOT not in sys.path:
    sys.path.insert(0, _API_ROOT)
else:
    # Local dev fallback: services live one level up
    _LOCAL_API = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "api"))
    if _LOCAL_API not in sys.path:
        sys.path.insert(0, _LOCAL_API)

from services.race_results import (  # noqa: E402
    fetch_result_from_netkeiba,
    get_cached_result,
    save_result,
)
import redis as _redis_mod
import json as _json_mod

JST = timezone(timedelta(hours=9))

# Kリワード付与
_r_votes = _redis_mod.Redis(host="127.0.0.1", port=6379, db=3, decode_responses=True)
_VOTE_KEY_PREFIX = "nk:votes"
_KREWARD_KEY = "nk:kreward:{uid}"
_KREWARD_LOG_KEY = "nk:kreward:log:{uid}"
_KREWARD_LOG_MAX = 200


def _calc_kreward_points(win_payout_yen: int) -> int:
    """払戻金額（100円馬券）からKリワードポイントを計算。"""
    if win_payout_yen <= 0:
        return 0
    odds = win_payout_yen / 100.0
    if odds <= 10.0:
        return 10
    elif odds <= 30.0:
        return 30
    else:
        return 100


def _grant_kreward(user_id: str, points: int, race_id: str, reason: str) -> None:
    key = _KREWARD_KEY.format(uid=user_id)
    log_key = _KREWARD_LOG_KEY.format(uid=user_id)
    _r_votes.incrby(key, points)
    entry = _json_mod.dumps({
        "points": points,
        "reason": reason,
        "race_id": race_id,
        "at": datetime.now(JST).isoformat(),
    }, ensure_ascii=False)
    pipe = _r_votes.pipeline(transaction=False)
    pipe.lpush(log_key, entry)
    pipe.ltrim(log_key, 0, _KREWARD_LOG_MAX - 1)
    pipe.execute()


def process_krewards(race_id: str, result: dict) -> None:
    """レース結果を元に投票者にKリワードを付与する。"""
    if result.get("cancelled"):
        return

    winners = result.get("winner_horse_numbers") or []
    if not winners and result.get("winner_horse_number"):
        winners = [result["winner_horse_number"]]
    if not winners:
        return

    payouts = result.get("win_payouts") or {}
    # 代表払戻額を取得（複数同着の場合は最初の馬）
    payout_yen = 0
    for w in winners:
        p = payouts.get(str(w)) or result.get("win_payout") or 0
        try:
            payout_yen = int(p)
            if payout_yen > 0:
                break
        except (ValueError, TypeError):
            pass

    points = _calc_kreward_points(payout_yen)
    if points <= 0:
        return

    # このレースに投票した全ユーザーを取得
    vote_key = f"{_VOTE_KEY_PREFIX}:{race_id}"
    all_votes = _r_votes.hgetall(vote_key)
    if not all_votes:
        return

    winner_set = {int(w) for w in winners}
    rewarded = 0
    for user_id, horse_str in all_votes.items():
        if user_id.startswith("__dummy"):
            continue
        try:
            horse_number = int(horse_str)
        except ValueError:
            continue
        if horse_number in winner_set:
            odds_approx = round(payout_yen / 100.0, 1) if payout_yen > 0 else 0
            reason = f"{race_id} 的中 (オッズ約{odds_approx}倍) +{points}pt"
            _grant_kreward(user_id, points, race_id, reason)
            rewarded += 1

    if rewarded > 0:
        logger.info(f"  Kリワード付与: {race_id} → {rewarded}名 各{points}pt (払戻{payout_yen}円)")
PREFETCH_DIR = os.environ.get(
    "PREFETCH_DIR", "/opt/dlogic/linebot/data/prefetch"
)
_LOCK_PATH = os.environ.get(
    "UPDATE_RACE_RESULTS_LOCK",
    os.path.join(tempfile.gettempdir(), "netkeita_update_race_results.lock"),
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("update_race_results")


def _today_jst() -> str:
    return datetime.now(JST).strftime("%Y%m%d")


def _format_winners(result: dict) -> str:
    """Render a human-readable winners/payouts description for logs."""
    if result.get("cancelled"):
        return "CANCELLED"
    winners = result.get("winner_horse_numbers") or []
    if not winners and "winner_horse_number" in result:
        winners = [result["winner_horse_number"]]
    payouts = result.get("win_payouts") or {}
    parts = []
    for n in winners:
        p = payouts.get(str(n), result.get("win_payout", 0))
        parts.append(f"#{n}={p}円")
    return ", ".join(parts) or "UNKNOWN"


# ── Official bot chat notification ──────────────────────────────────────────
# 結果確定時に /api/chat に「運営bot」として結果速報を投稿する。
# 1番人気が 1 着に来なかった場合は「波乱!」サフィックスを追加。
# 投稿は重複防止のため「初回確定時のみ」実行 (cron 再実行で複数回投げない)。


def _top_popularity_horse(race: dict) -> tuple[int, str] | None:
    """prefetch の race dict から 1番人気 (最低オッズ) の馬番と名前を返す。"""
    horses = race.get("horses") or []
    ranked = sorted(
        ((h.get("horse_number"), h.get("horse_name", ""), h.get("odds") or 999.0)
         for h in horses),
        key=lambda t: t[2],
    )
    if not ranked:
        return None
    num, name, _ = ranked[0]
    if num is None:
        return None
    return num, (name or "")


def _notify_chat_bot_result(race: dict, result: dict) -> None:
    """結果速報を netkeita 公式 bot としてチャットに投稿する (fire-and-forget)。"""
    try:
        from services import chat as chat_service
    except Exception:
        logger.exception("chat_service import failed")
        return
    if result.get("cancelled"):
        return
    winners = result.get("winner_horse_numbers") or []
    if not winners and result.get("winner_horse_number"):
        winners = [result["winner_horse_number"]]
    if not winners:
        return

    # 単勝配当 (代表 1 頭分)
    payouts = result.get("win_payouts") or {}
    first = winners[0]
    payout = 0
    try:
        payout = int(payouts.get(str(first)) or result.get("win_payout") or 0)
    except Exception:
        payout = 0

    # 馬名 (prefetch から引ければ添える)
    horses = race.get("horses") or []
    name_by_num = {h.get("horse_number"): (h.get("horse_name") or "") for h in horses}
    first_name = name_by_num.get(first, "")

    # 人気順位を算出 (オッズ昇順)
    popularity_map: dict[int, int] = {}
    ranked = sorted(
        ((h.get("horse_number"), h.get("odds") or 999.0) for h in horses),
        key=lambda t: t[1],
    )
    for i, (num, _) in enumerate(ranked, 1):
        if num is not None:
            popularity_map[num] = i
    first_pop = popularity_map.get(first, 0)

    # レース表示名 (venue と R番号を短く)
    venue = race.get("venue", "")
    rno = race.get("race_number", "?")

    # 波乱判定: 1番人気が winners (= 1着) に入っていない
    is_upset = bool(popularity_map) and popularity_map.get(first) != 1
    upset_tag = " 波乱!" if is_upset else ""

    # 馬名は 8 文字で切って全体を 50 字以内に収める
    name_short = (first_name[:8]) if first_name else f"#{first}"
    pop_part = f"{first_pop}人気/" if first_pop else ""
    payout_part = f"{payout}円" if payout else ""
    body = (
        f"🏆 {venue}{rno}R 1着 #{first} {name_short}"
        f" ({pop_part}{payout_part}){upset_tag}"
    ).rstrip()

    channel = "nar" if race.get("is_local") else "jra"
    try:
        chat_service.post_bot_message(channel, body)
    except Exception:
        logger.exception(f"chat bot post failed for {race.get('race_id', '?')}")


def process_date(date_str: str, force: bool = False) -> None:
    """Scrape results for every race on `date_str` and cache them."""
    path = os.path.join(PREFETCH_DIR, f"races_{date_str}.json")
    if not os.path.exists(path):
        logger.warning(f"prefetch not found: {path}")
        return

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    races = data.get("races", []) if isinstance(data, dict) else []
    if not races:
        logger.info(f"date={date_str} no races in prefetch")
        return

    fetched = 0
    cancelled = 0
    skipped = 0
    not_ready = 0
    total = 0

    for r in races:
        race_id = r.get("race_id", "")
        race_id_nk = r.get("race_id_netkeiba", "")
        is_local = bool(r.get("is_local"))
        venue = r.get("venue", "")
        rno = r.get("race_number", "?")

        if not race_id or not race_id_nk:
            continue
        total += 1

        if not force:
            cached = get_cached_result(race_id)
            if cached and (cached.get("finalized") or cached.get("cancelled")):
                skipped += 1
                continue

        try:
            # --force bypasses the short-TTL negative cache so operators can
            # drive manual retries after fixing upstream issues.
            result = fetch_result_from_netkeiba(
                race_id_nk,
                is_local=is_local,
                skip_negative_cache=force,
            )
        except Exception:
            logger.exception(f"  {venue} {rno}R: scrape error")
            not_ready += 1
            time.sleep(0.6)
            continue

        if result:
            already_cached = get_cached_result(race_id)
            # 初回確定フラグ (Kリワード付与 + bot 速報の判定に使う)
            is_first_time = not already_cached or not already_cached.get("finalized")
            save_result(race_id, result)
            if result.get("cancelled"):
                cancelled += 1
                logger.info(f"  {venue} {rno}R: CANCELLED")
            else:
                fetched += 1
                logger.info(f"  {venue} {rno}R: {_format_winners(result)}")
                if is_first_time:
                    # Kリワード付与 (まだ付与していない結果のみ)
                    process_krewards(race_id, result)
                    # 運営 bot による結果速報をチャットに投稿 (fire-and-forget)
                    try:
                        _notify_chat_bot_result(r, result)
                    except Exception:
                        logger.exception(f"  {venue} {rno}R: bot notify failed")
        else:
            not_ready += 1
            logger.info(f"  {venue} {rno}R: not finalised yet")

        time.sleep(0.6)  # polite throttle

    logger.info(
        f"date={date_str} total={total} fetched={fetched} cancelled={cancelled} "
        f"cached_already={skipped} not_finalised={not_ready}"
    )


def _parse_args(argv: list[str]) -> tuple[list[str], bool]:
    """Return (dates, force_flag)."""
    force = False
    days_n: int | None = None
    explicit_date: str | None = None

    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--days":
            if i + 1 < len(argv):
                try:
                    days_n = int(argv[i + 1])
                except ValueError:
                    days_n = 3
                i += 2
                continue
        elif a == "--force":
            force = True
            i += 1
            continue
        elif a.isdigit() and len(a) == 8:
            explicit_date = a
            i += 1
            continue
        i += 1

    if explicit_date:
        return [explicit_date], force
    if days_n and days_n > 0:
        today = datetime.now(JST).date()
        return [(today - timedelta(days=k)).strftime("%Y%m%d") for k in range(days_n)], force
    return [_today_jst()], force


def _acquire_lock():
    """Create an exclusive advisory lock so cron can't stampede itself.

    Uses fcntl on POSIX; falls back to a no-op on platforms without it
    (e.g. Windows dev boxes) with a best-effort stale-PID file check.
    Returns the opened file handle (must be kept alive for the run) or
    None if another instance holds the lock.
    """
    lock_file = open(_LOCK_PATH, "a+")
    try:
        import fcntl  # type: ignore
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lock_file.close()
            return None
    except ImportError:
        # Windows: degrade to PID file
        try:
            lock_file.seek(0)
            existing = lock_file.read().strip()
            if existing and existing.isdigit():
                logger.warning(
                    f"lock file present (pid={existing}); "
                    "concurrent run not fully prevented on this platform"
                )
            lock_file.seek(0)
            lock_file.truncate()
            lock_file.write(str(os.getpid()))
            lock_file.flush()
        except Exception:
            pass
    return lock_file


def main() -> None:
    lock = _acquire_lock()
    if lock is None:
        logger.warning("another update_race_results instance is running; exiting")
        sys.exit(0)

    try:
        dates, force = _parse_args(sys.argv[1:])
        logger.info(
            f"=== update_race_results start dates={dates} force={force} "
            f"prefetch_dir={PREFETCH_DIR} ==="
        )
        for d in dates:
            process_date(d, force=force)
        logger.info("=== done ===")
    finally:
        try:
            lock.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
