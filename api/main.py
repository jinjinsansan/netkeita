"""netkeita API server — FastAPI backend for JRA race ranking data."""

import asyncio
import logging
import os
import random
import re
import secrets
import sys
import time
import urllib.parse
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from pydantic import BaseModel

from config import (
    PORT, LINE_CHANNEL_ID, LINE_CHANNEL_SECRET, FRONTEND_URL,
    ADMIN_LINE_USER_IDS, INTERNAL_API_KEY,
)
from services.data_fetcher import (
    get_races, get_race_entries, get_today_str, get_full_scores, get_analysis,
    get_odds_from_prefetch, get_available_dates, get_display_dates,
    get_internet_predictions,
    get_horse_recent_runs, get_horse_bloodline, get_stable_comments,
    async_get_full_scores, async_get_analysis,
)
from services.ranking import calculate_matrix
from services.rewriter import rewrite_comment
from services.course_stats_scraper import get_course_stats_for_horse
from services.race_results import get_cached_result as get_cached_race_result
from services import articles as articles_service
from services.race_level import enrich_recent_runs
from services import tipsters as tipsters_service

JST = timezone(timedelta(hours=9))

# race_id format: YYYYMMDD-<venue>-<number>.  Venue may contain Japanese
# characters. This regex is deliberately lenient but rejects obviously
# malformed input that could be used for Redis key injection.
_RACE_ID_RE = re.compile(r"^\d{8}-[^:\s/\\]{1,20}-\d{1,2}$")


def _assert_valid_race_id(race_id: str) -> None:
    if not race_id or not _RACE_ID_RE.match(race_id):
        raise HTTPException(status_code=400, detail="不正なレースIDです")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

app = FastAPI(title="netkeita API", version="0.3.0")

# CORS is handled by Nginx reverse proxy — do NOT add CORSMiddleware here
# to avoid duplicate Access-Control-Allow-Origin headers.

# In-memory cache for matrix responses (race_id -> (timestamp, response))
_matrix_cache: dict[str, tuple[float, dict]] = {}
MATRIX_CACHE_TTL = 60  # seconds

# Redis session store (shared across workers, auto-expiry)
import json as _json
import redis as _redis

_redis_client = _redis.Redis(host="127.0.0.1", port=6379, db=2, decode_responses=True)
_SESSION_TTL = 86400  # 24 hours


def _save_session(token: str, data: dict):
    try:
        _redis_client.setex(f"nk:session:{token}", _SESSION_TTL, _json.dumps(data))
    except Exception:
        logger.exception("Failed to save session to Redis")


def _load_session(token: str) -> dict | None:
    try:
        raw = _redis_client.get(f"nk:session:{token}")
        return _json.loads(raw) if raw else None
    except Exception:
        logger.exception("Failed to load session from Redis")
        return None


class LineCallbackRequest(BaseModel):
    code: str
    state: str


@app.get("/api/auth/line-url")
def get_line_login_url():
    """Generate LINE Login URL with bot_prompt for friend-adding."""
    state = secrets.token_urlsafe(16)
    params = {
        "response_type": "code",
        "client_id": LINE_CHANNEL_ID,
        "redirect_uri": f"{FRONTEND_URL}/api/auth/callback",
        "state": state,
        "scope": "profile openid",
        "bot_prompt": "aggressive",
    }
    url = f"https://access.line.me/oauth2/v2.1/authorize?{urllib.parse.urlencode(params)}"
    return {"url": url, "state": state}


@app.post("/api/auth/callback")
async def line_callback(req: LineCallbackRequest):
    """LINE callback: code -> access_token -> profile -> session token."""
    try:
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                "https://api.line.me/oauth2/v2.1/token",
                data={
                    "grant_type": "authorization_code",
                    "code": req.code,
                    "redirect_uri": f"{FRONTEND_URL}/api/auth/callback",
                    "client_id": LINE_CHANNEL_ID,
                    "client_secret": LINE_CHANNEL_SECRET,
                },
            )
            if token_resp.status_code != 200:
                logger.error(f"LINE token error: {token_resp.text}")
                return {"success": False, "error": "LINE認証に失敗しました"}

            token_data = token_resp.json()
            access_token = token_data.get("access_token")

            profile_resp = await client.get(
                "https://api.line.me/v2/profile",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if profile_resp.status_code != 200:
                return {"success": False, "error": "プロフィール取得に失敗しました"}

            profile = profile_resp.json()

        line_user_id = profile.get("userId")
        display_name = profile.get("displayName", "")
        picture_url = profile.get("pictureUrl", "")

        session_token = secrets.token_urlsafe(32)
        _save_session(session_token, {
            "line_user_id": line_user_id,
            "display_name": display_name,
            "picture_url": picture_url,
        })

        logger.info(f"LINE login: {display_name} ({line_user_id})")

        return {
            "success": True,
            "token": session_token,
            "user": {"display_name": display_name, "picture_url": picture_url},
        }
    except Exception as e:
        logger.exception(f"LINE callback error: {e}")
        return {"success": False, "error": "認証処理中にエラーが発生しました"}


def _is_admin_user(user: dict | None) -> bool:
    """Return True when the given user dict belongs to an admin LINE account."""
    if not user:
        return False
    uid = user.get("line_user_id") or ""
    return bool(uid) and uid in ADMIN_LINE_USER_IDS


@app.get("/api/auth/me")
def get_me(authorization: str = Header(default="")):
    """Get current user info from session token."""
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else ""
    if not token:
        return {"authenticated": False}
    user = _load_session(token)
    if not user:
        return {"authenticated": False}
    uid = user.get("line_user_id", "")
    return {
        "authenticated": True,
        "user": {
            "display_name": user["display_name"],
            "picture_url": user.get("picture_url", ""),
            "is_admin": _is_admin_user(user),
            "is_tipster": tipsters_service.is_approved_tipster(uid),
            "line_user_id": uid,
        },
    }


def _enforce_display_date(date_str: str) -> str:
    """Ensure the requested date is in the currently-allowed display list.

    Returns the (possibly corrected) date_str if allowed, otherwise raises
    HTTPException(403). Empty date is resolved to the primary display date.
    """
    allowed = get_display_dates()
    if not allowed:
        raise HTTPException(status_code=404, detail="No races available")
    if not date_str:
        return allowed[0]
    if date_str not in allowed:
        raise HTTPException(status_code=403, detail="Date not currently displayed")
    return date_str


@app.get("/api/races")
def api_races(date: str = ""):
    """Get race list for a given date. Only dates in get_display_dates()
    are accessible; older dates return 403."""
    date_str = _enforce_display_date(date)
    races = get_races(date_str)
    return {"date": date_str, "races": races, "count": len(races)}


@app.get("/api/race/{race_id}/entries")
def api_entries(race_id: str, date: str = ""):
    """Get race entries (出馬表)."""
    date_str = date or (race_id.split("-")[0] if "-" in race_id else get_today_str())
    date_str = _enforce_display_date(date_str)
    entries = get_race_entries(date_str, race_id)
    if not entries:
        raise HTTPException(status_code=404, detail="Race not found")
    return entries


@app.get("/api/race/{race_id}/matrix")
async def api_matrix(race_id: str, date: str = ""):
    """Get 8-category rank matrix for all horses in a race."""
    date_str = date or (race_id.split("-")[0] if "-" in race_id else get_today_str())
    date_str = _enforce_display_date(date_str)

    # Check cache first
    cached = _matrix_cache.get(race_id)
    if cached and (time.time() - cached[0]) < MATRIX_CACHE_TTL:
        logger.info(f"Cache hit for {race_id}")
        return cached[1]

    race_data = get_race_entries(date_str, race_id)
    if not race_data or not race_data.get("entries"):
        raise HTTPException(status_code=404, detail="Race not found")

    logger.info(f"Building matrix for {race_id} ({len(race_data['entries'])} horses)")

    # Fetch all backend APIs in parallel
    full_scores_raw, flow_data, jockey_data, bloodline_data, recent_data = await asyncio.gather(
        async_get_full_scores(race_data),
        async_get_analysis("/api/v2/analysis/race-flow", race_data),
        async_get_analysis("/api/v2/analysis/jockey-analysis", race_data),
        async_get_analysis("/api/v2/analysis/bloodline-analysis", race_data),
        async_get_analysis("/api/v2/analysis/recent-runs", race_data),
    )

    predictions = _build_full_predictions(full_scores_raw, race_data)
    odds_data = get_odds_from_prefetch(date_str, race_id)

    horses = calculate_matrix(
        entries=race_data["entries"],
        predictions=predictions,
        flow_data=flow_data,
        jockey_data=jockey_data,
        bloodline_data=bloodline_data,
        recent_data=recent_data,
        odds_data=odds_data,
        track_condition=race_data.get("track_condition", "良"),
        race_name=race_data.get("race_name", ""),
    )

    logger.info(f"Matrix built: {len(horses)} horses, sample scores: {horses[0]['scores'] if horses else 'none'}")

    result = {
        "race_id": race_id,
        "race_name": race_data.get("race_name", ""),
        "venue": race_data.get("venue", ""),
        "distance": race_data.get("distance", ""),
        "race_number": race_data.get("race_number", 0),
        "track_condition": race_data.get("track_condition", ""),
        "is_local": race_data.get("is_local", False),
        "horses": horses,
        "jockey_data": {
            "jockey_post_stats": jockey_data.get("jockey_post_stats", {}),
            "jockey_course_stats": jockey_data.get("jockey_course_stats", {}),
        },
    }

    # Store in cache
    _matrix_cache[race_id] = (time.time(), result)
    return result


def _build_full_predictions(full_scores_raw: dict, race_data: dict) -> dict:
    """Convert full-scores API response to per-horse score dict.

    Returns {horse_number: {dlogic_score, ilogic_score, viewlogic_score,
                            metalogic_score, track_adjustment}}.
    """
    entries = race_data.get("entries", [])
    scores: dict[int, dict] = {}

    for entry in entries:
        num = entry["horse_number"]
        scores[num] = {
            "dlogic_score": 0,
            "ilogic_score": 0,
            "viewlogic_score": 0,
            "metalogic_score": 0,
            "track_adjustment": 1.0,
        }

    for h in full_scores_raw.get("horses", []):
        num = h.get("horse_number", 0)
        if num in scores:
            scores[num] = {
                "dlogic_score": h.get("dlogic_score", 0),
                "ilogic_score": h.get("ilogic_score", 0),
                "viewlogic_score": h.get("viewlogic_score", 0),
                "metalogic_score": h.get("metalogic_score", 0),
                "track_adjustment": h.get("track_adjustment", 1.0),
            }

    return scores


# Cache for horse-detail (key: "race_id:horse_number" -> (timestamp, response))
_horse_detail_cache: dict[str, tuple[float, dict]] = {}
HORSE_DETAIL_CACHE_TTL = 60  # 1 minute (short to pick up rewrite results quickly)


@app.get("/api/horse-detail/{race_id}/{horse_number}")
def api_horse_detail(race_id: str, horse_number: int, date: str = ""):
    """Get detailed info for a single horse: stable comments, recent runs, bloodline."""
    date_str = date or (race_id.split("-")[0] if "-" in race_id else get_today_str())
    date_str = _enforce_display_date(date_str)

    cache_key = f"{race_id}:{horse_number}"
    cached = _horse_detail_cache.get(cache_key)
    if cached and (time.time() - cached[0]) < HORSE_DETAIL_CACHE_TTL:
        return cached[1]

    race_data = get_race_entries(date_str, race_id)
    if not race_data:
        raise HTTPException(status_code=404, detail="Race not found")

    entry = next((e for e in race_data.get("entries", []) if e["horse_number"] == horse_number), None)
    if not entry:
        raise HTTPException(status_code=404, detail="Horse not found")

    venue = race_data.get("venue", "")
    race_number_int = race_data.get("race_number", 0)
    is_local = race_data.get("is_local", False)

    # Stable comments and course_stats are JRA-only (scraped from JRA-specific sources)
    horse_stable: dict = {}
    course_stats: dict = {}

    if not is_local:
        stable = get_stable_comments(date_str, venue, race_number_int)
        horse_stable = stable.get(horse_number, stable.get(str(horse_number), {}))

        # Rewrite comment in background (non-blocking)
        if horse_stable and horse_stable.get("comment"):
            horse_stable = rewrite_comment(horse_number, horse_stable)

        # Course stats from netkeiba (Redis cache only - populated by prefetch)
        race_id_nk = race_data.get("race_id_netkeiba", "")
        if race_id_nk:
            try:
                course_stats = get_course_stats_for_horse(race_id_nk, horse_number)
            except Exception:
                pass

    recent_runs = get_horse_recent_runs(race_data, horse_number)
    enrich_recent_runs(recent_runs)
    bloodline = get_horse_bloodline(race_data, horse_number)

    result = {
        "horse_number": horse_number,
        "horse_name": entry["horse_name"],
        "stable_comment": horse_stable,
        "recent_runs": recent_runs,
        "bloodline": bloodline,
        "course_stats": course_stats,
        "is_local": is_local,
    }

    _horse_detail_cache[cache_key] = (time.time(), result)
    return result


@app.get("/api/internet-predictions/{race_name}")
def api_internet_predictions(race_name: str):
    """Get internet predictions (YouTube + keiba site) for a graded race."""
    data = get_internet_predictions(race_name)
    if not data:
        raise HTTPException(status_code=404, detail="Internet predictions not found")
    return data


@app.get("/api/dates")
def api_dates():
    """Get list of available race dates (newest first)."""
    dates = get_available_dates()
    return {"dates": dates}


# ── Minna-no-Yosou (みんなの予想) voting system ──────────────────────
# Uses Redis db=3 for vote storage, separate from sessions (db=2).

_redis_votes = _redis.Redis(host="127.0.0.1", port=6379, db=3, decode_responses=True)
_VOTE_KEY_PREFIX = "nk:votes"
_VOTE_COUNT_TTL = 86400 * 90      # count + per-race vote hash retained 90 days
_VOTE_HISTORY_TTL = 86400 * 90    # user vote history retained for 90 days
_DUMMY_FLAG_TTL = 86400 * 90      # dummy flag: once generated, never regen

# Kリワードポイント (Redis db=3 に同居)
_KREWARD_KEY = "nk:kreward:{uid}"        # total balance (int as string)
_KREWARD_LOG_KEY = "nk:kreward:log:{uid}"  # list of JSON log entries (newest first)
_KREWARD_LOG_MAX = 200
_KREWARD_COIN_RATE = 1  # 1 Kリワード = 1 bakugatcha coin
# bakugatcha endpoint for coin transfer
_BAKU_KREWARD_URL = os.getenv("BAKU_KREWARD_URL", "https://www.bakugacha.com/api/kreward")
_BAKU_KREWARD_SECRET = os.getenv("BAKU_KREWARD_SECRET", "")


def _get_user_from_token(authorization: str) -> dict | None:
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else ""
    if not token:
        return None
    return _load_session(token)


def _get_user_from_internal_key(x_internal_key: str) -> dict | None:
    """Return a synthetic admin user dict when the internal API key matches."""
    if not INTERNAL_API_KEY or not x_internal_key:
        return None
    if not secrets.compare_digest(x_internal_key, INTERNAL_API_KEY):
        return None
    return {
        "line_user_id": ADMIN_LINE_USER_IDS[0] if ADMIN_LINE_USER_IDS else "_internal",
        "display_name": "Internal System",
        "is_admin": True,
    }


def _get_valid_horse_numbers(race_id: str) -> tuple[set[int], dict | None]:
    """Resolve the set of valid horse numbers for a race.

    Looks at the matrix cache first, falls back to prefetch on cache miss so
    vote validation is never skipped (closes the TOCTOU hole where a cold
    cache allowed arbitrary horse numbers to be stored in Redis).
    """
    cached = _matrix_cache.get(race_id)
    if cached:
        nums = {h["horse_number"] for h in cached[1].get("horses", [])}
        if nums:
            return nums, None

    date_str = race_id.split("-")[0] if "-" in race_id else get_today_str()
    race_data = get_race_entries(date_str, race_id)
    if race_data and race_data.get("entries"):
        return ({e["horse_number"] for e in race_data["entries"]}, race_data)

    return set(), None


def _parse_start_datetime(date_str: str, start_time: str) -> datetime | None:
    """Combine YYYYMMDD + 'HH:MM' into a JST datetime."""
    if not date_str or not start_time or len(date_str) != 8:
        return None
    m = re.match(r"^(\d{1,2}):(\d{2})", start_time)
    if not m:
        return None
    try:
        hh, mm = int(m.group(1)), int(m.group(2))
        return datetime(
            int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]),
            hh, mm, tzinfo=JST,
        )
    except (ValueError, TypeError):
        return None


def _ensure_dummy_votes(race_id: str):
    """Generate dummy votes for a race exactly once, atomically."""
    flag_key = f"{_VOTE_KEY_PREFIX}:dummy:{race_id}"
    # Atomic "set if not exists" prevents multi-worker double generation.
    acquired = _redis_votes.set(flag_key, "1", nx=True, ex=_DUMMY_FLAG_TTL)
    if not acquired:
        return

    try:
        # Resolve horses from cache → prefetch
        horses = []
        cached = _matrix_cache.get(race_id)
        if cached:
            horses = cached[1].get("horses", [])
        if not horses:
            date_str = race_id.split("-")[0] if "-" in race_id else get_today_str()
            race_data = get_race_entries(date_str, race_id)
            if race_data and race_data.get("entries"):
                horses = [
                    {"horse_number": e["horse_number"], "scores": {"total": 0}}
                    for e in race_data["entries"]
                ]
        if not horses:
            # Couldn't find the race — release the flag so a later request retries.
            _redis_votes.delete(flag_key)
            return

        has_scores = any(h["scores"]["total"] > 0 for h in horses)
        if has_scores:
            scored = sorted(horses, key=lambda h: h["scores"]["total"], reverse=True)
        else:
            scored = list(horses)
            random.shuffle(scored)

        n = len(scored)
        weights = []
        for i, h in enumerate(scored):
            if i < n * 0.25:
                w = random.uniform(3.0, 5.0)
            elif i < n * 0.60:
                w = random.uniform(1.5, 3.0)
            else:
                w = random.uniform(0.3, 1.5)
            weights.append((h["horse_number"], w))

        total_w = sum(w for _, w in weights) or 1.0
        probs = [(num, w / total_w) for num, w in weights]

        total_votes = random.randint(30, 80)
        count_key = f"{_VOTE_KEY_PREFIX}:count:{race_id}"

        # Batch writes into a single pipeline — ~1 network roundtrip instead
        # of 30-80 individual hincrby calls.
        pipe = _redis_votes.pipeline(transaction=False)
        for _ in range(total_votes):
            r = random.random()
            cumulative = 0.0
            chosen = probs[0][0]
            for num, p in probs:
                cumulative += p
                if r <= cumulative:
                    chosen = num
                    break
            pipe.hincrby(count_key, str(chosen), 1)
        pipe.expire(count_key, _VOTE_COUNT_TTL)
        pipe.execute()

        logger.info(f"Generated {total_votes} dummy votes for {race_id}")
    except Exception:
        logger.exception(f"_ensure_dummy_votes failed: {race_id}")
        # Release the flag so a subsequent call can retry
        try:
            _redis_votes.delete(flag_key)
        except Exception:
            pass


# ── Character Predictions (3キャラ予想印) ──────────────────────────────
_PRED_KEY_PREFIX = "nk:charpred:v2"
_PRED_TTL = 86400 * 90

MARK_HONMEI = "◎"
MARK_TAIKOU = "○"
MARK_TANANA = "▲"
MARK_RENKA  = "△"
MARK_HOSHI  = "✖"

CHARACTER_PROFILES = [
    {
        "id": "honshi",
        "name": "netkeita本紙",
        "description": "本命重視の正統派",
        "emoji": "📰",
    },
    {
        "id": "data",
        "name": "データ分析",
        "description": "数値とスピード重視",
        "emoji": "📊",
    },
    {
        "id": "anaba",
        "name": "穴党記者",
        "description": "人気薄の激走を狙う",
        "emoji": "🔥",
    },
]


_DLOGIC_API_URL = "http://localhost:8000"


def _marks_from_top5(top5_numbers: list[int], horse_map: dict[int, str]) -> dict[str, str]:
    """上位5頭の馬番リストから印辞書を生成する。"""
    mark_order = [MARK_HONMEI, MARK_TAIKOU, MARK_TANANA, MARK_RENKA, MARK_HOSHI]
    marks: dict[str, str] = {}
    for i, num in enumerate(top5_numbers[:5]):
        if num in horse_map:
            marks[str(num)] = mark_order[i]
    return marks


def _generate_character_predictions(race_id: str) -> list[dict] | None:
    """Dlogic APIを使って3キャラクターの予想印を生成する（Redisキャッシュあり）。"""
    cache_key = f"{_PRED_KEY_PREFIX}:{race_id}"
    cached = _redis_votes.get(cache_key)
    if cached:
        try:
            return _json.loads(cached)
        except Exception:
            pass

    # レースエントリーを取得
    date_str = race_id.split("-")[0] if "-" in race_id else get_today_str()
    race_data = get_race_entries(date_str, race_id)
    if not race_data or not race_data.get("entries"):
        return None

    entries = race_data["entries"]
    if len(entries) < 4:
        return None

    horse_numbers = [e["horse_number"] for e in entries]
    horse_names   = [e.get("horse_name", "") for e in entries]
    jockeys       = [e.get("jockey", "") for e in entries]
    posts         = [e.get("post", 0) for e in entries]
    odds_list     = [float(e.get("odds", 10.0)) for e in entries]
    horse_map     = {e["horse_number"]: e.get("horse_name", "") for e in entries}

    # Dlogic API へリクエスト
    payload = {
        "race_id": race_id,
        "horses": horse_names,
        "horse_numbers": horse_numbers,
        "venue": race_data.get("venue", ""),
        "race_number": race_data.get("race_number", 0),
        "jockeys": jockeys,
        "posts": posts,
        "distance": race_data.get("distance", ""),
        "track_condition": race_data.get("track_condition", "良"),
        "odds": odds_list,
    }

    try:
        resp = httpx.post(
            f"{_DLOGIC_API_URL}/api/v2/predictions/newspaper",
            json=payload,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        honshi_marks = _marks_from_top5(data.get("dlogic", []),    horse_map)
        data_marks   = _marks_from_top5(data.get("metalogic", []), horse_map)
        anaba_marks  = _marks_from_top5(data.get("viewlogic", []), horse_map)

    except Exception:
        logger.exception(f"Dlogic API call failed for {race_id}, falling back to score-based")
        # フォールバック: スコアベースのロジック
        cached_matrix = _matrix_cache.get(race_id)
        horses = cached_matrix[1].get("horses", []) if cached_matrix else []
        if not horses:
            horses = [
                {"horse_number": e["horse_number"], "horse_name": e.get("horse_name", ""),
                 "odds": float(e.get("odds", 10.0)),
                 "scores": {"total": 0, "speed": 0, "recent": 0, "jockey": 0,
                            "flow": 0, "bloodline": 0}}
                for e in entries
            ]
        has_scores = any(h.get("scores", {}).get("total", 0) > 0 for h in horses)
        if has_scores:
            by_total = sorted(horses, key=lambda h: h["scores"]["total"], reverse=True)
        else:
            by_total = sorted(horses, key=lambda h: h["horse_number"])
        honshi_marks = _assign_marks_standard(by_total)
        data_marks   = honshi_marks
        by_ev = sorted(horses, key=lambda h: h.get("odds", 10.0), reverse=True)
        anaba_marks  = _assign_marks_anaba(by_ev, by_total)

    predictions = []
    for profile, marks in zip(CHARACTER_PROFILES, [honshi_marks, data_marks, anaba_marks]):
        predictions.append({**profile, "marks": marks})

    try:
        _redis_votes.set(cache_key, _json.dumps(predictions, ensure_ascii=False), ex=_PRED_TTL)
    except Exception:
        pass

    return predictions


def _assign_marks_standard(sorted_horses: list[dict]) -> dict[str, str]:
    """Assign marks based on a sorted horse list (top = best)."""
    marks: dict[str, str] = {}
    n = len(sorted_horses)
    if n >= 1:
        marks[str(sorted_horses[0]["horse_number"])] = MARK_HONMEI
    if n >= 2:
        marks[str(sorted_horses[1]["horse_number"])] = MARK_TAIKOU
    if n >= 3:
        marks[str(sorted_horses[2]["horse_number"])] = MARK_TANANA
    if n >= 4:
        marks[str(sorted_horses[3]["horse_number"])] = MARK_RENKA
    if n >= 5:
        marks[str(sorted_horses[-1]["horse_number"])] = MARK_HOSHI
    return marks


def _assign_marks_anaba(ev_sorted: list[dict], total_sorted: list[dict]) -> dict[str, str]:
    """Assign marks for the contrarian character.

    ◎ is NOT the #1 by total — picks from ev_sorted top that isn't
    the overall favourite, creating interesting divergence.
    """
    marks: dict[str, str] = {}
    top_fav_num = total_sorted[0]["horse_number"] if total_sorted else -1
    used: set[int] = set()

    # ◎: First in ev_sorted that is NOT the overall favourite
    for h in ev_sorted:
        if h["horse_number"] != top_fav_num:
            marks[str(h["horse_number"])] = MARK_HONMEI
            used.add(h["horse_number"])
            break
    # ○: Next best in ev_sorted
    for h in ev_sorted:
        if h["horse_number"] not in used:
            marks[str(h["horse_number"])] = MARK_TAIKOU
            used.add(h["horse_number"])
            break
    # ▲: Next
    for h in ev_sorted:
        if h["horse_number"] not in used:
            marks[str(h["horse_number"])] = MARK_TANANA
            used.add(h["horse_number"])
            break
    # △: Next
    for h in ev_sorted:
        if h["horse_number"] not in used:
            marks[str(h["horse_number"])] = MARK_RENKA
            used.add(h["horse_number"])
            break
    # ✖: The overall favourite (contrarian pick)
    if top_fav_num not in used and len(ev_sorted) >= 5:
        marks[str(top_fav_num)] = MARK_HOSHI

    return marks


@app.get("/api/votes/{race_id}/predictions")
def api_character_predictions(race_id: str):
    """Return 3-character mark predictions (◎○▲△✖) for a race."""
    _assert_valid_race_id(race_id)
    predictions = _generate_character_predictions(race_id)
    if predictions is None:
        return {"race_id": race_id, "predictions": []}
    return {"race_id": race_id, "predictions": predictions}


class VoteRequest(BaseModel):
    horse_number: int


@app.post("/api/votes/{race_id}")
def api_vote(race_id: str, req: VoteRequest, authorization: str = Header(default="")):
    """Submit or change a vote for a race. Requires authentication.

    Guarantees:
      * race_id format is validated (rejects Redis key injection)
      * horse_number is validated against the real entries list (even when
        the in-memory matrix cache is cold)
      * votes are refused after the race has started (JST)
      * the odds at the moment of voting are snapshotted so the mypage ROI
        display reflects the price the user actually bet at
    """
    _assert_valid_race_id(race_id)

    user = _get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="ログインが必要です")

    user_id = user.get("line_user_id", "")
    if not user_id:
        raise HTTPException(status_code=401, detail="ユーザー情報が不正です")

    # Validate horse number against the actual race (cache or disk).
    valid_numbers, race_data = _get_valid_horse_numbers(race_id)
    if not valid_numbers:
        raise HTTPException(status_code=404, detail="レースが見つかりません")
    if req.horse_number not in valid_numbers:
        raise HTTPException(status_code=400, detail="不正な馬番です")

    # Enforce voting cut-off at race start time.
    date_str = race_id.split("-")[0] if "-" in race_id else ""
    if race_data is None:
        race_data = get_race_entries(date_str, race_id) if date_str else None
    start_dt = _parse_start_datetime(date_str, (race_data or {}).get("start_time", ""))
    if start_dt and datetime.now(JST) >= start_dt - timedelta(minutes=1):
        raise HTTPException(status_code=403, detail="締め切り（発走1分前）を過ぎたため投票できません")

    # Capture odds snapshot for this user+race (used by ROI history).
    odds_snapshot = 0.0
    if race_data:
        for e in race_data.get("entries", []):
            if e.get("horse_number") == req.horse_number:
                try:
                    odds_snapshot = float(e.get("odds", 0.0) or 0.0)
                except (ValueError, TypeError):
                    odds_snapshot = 0.0
                break

    vote_key = f"{_VOTE_KEY_PREFIX}:{race_id}"
    count_key = f"{_VOTE_KEY_PREFIX}:count:{race_id}"

    # Adjust aggregate count atomically using a pipeline
    prev = _redis_votes.hget(vote_key, user_id)
    pipe = _redis_votes.pipeline(transaction=True)
    if prev:
        pipe.hincrby(count_key, prev, -1)
    pipe.hset(vote_key, user_id, str(req.horse_number))
    pipe.hincrby(count_key, str(req.horse_number), 1)
    pipe.expire(vote_key, _VOTE_COUNT_TTL)
    pipe.expire(count_key, _VOTE_COUNT_TTL)

    # User history (race_id → horse_number) with odds snapshot.
    history_key = f"{_VOTE_KEY_PREFIX}:history:{user_id}"
    odds_snap_key = f"{_VOTE_KEY_PREFIX}:odds:{user_id}"
    pipe.hset(history_key, race_id, str(req.horse_number))
    pipe.expire(history_key, _VOTE_HISTORY_TTL)
    pipe.hset(odds_snap_key, race_id, f"{odds_snapshot:.1f}")
    pipe.expire(odds_snap_key, _VOTE_HISTORY_TTL)
    pipe.execute()

    return {
        "success": True,
        "horse_number": req.horse_number,
        "odds_at_vote": round(odds_snapshot, 1),
    }


@app.get("/api/votes/{race_id}/results")
def api_vote_results(race_id: str, authorization: str = Header(default="")):
    """Get vote results for a race."""
    _assert_valid_race_id(race_id)
    _ensure_dummy_votes(race_id)

    count_key = f"{_VOTE_KEY_PREFIX}:count:{race_id}"
    raw_counts = _redis_votes.hgetall(count_key)

    counts: dict[int, int] = {}
    for k, v in raw_counts.items():
        cnt = int(v)
        if cnt > 0:
            counts[int(k)] = cnt

    total = sum(counts.values())

    # Build results with horse info from matrix cache or race entries
    cached = _matrix_cache.get(race_id)
    horses_info = {}
    if cached:
        for h in cached[1].get("horses", []):
            horses_info[h["horse_number"]] = {
                "horse_name": h["horse_name"],
                "post": h.get("post", 0),
                "jockey": h.get("jockey", ""),
            }
    if not horses_info:
        date_str = race_id.split("-")[0] if "-" in race_id else get_today_str()
        race_data = get_race_entries(date_str, race_id)
        if race_data:
            for e in race_data.get("entries", []):
                horses_info[e["horse_number"]] = {
                    "horse_name": e["horse_name"],
                    "post": e.get("post", 0),
                    "jockey": e.get("jockey", ""),
                }

    results = []
    for num, cnt in sorted(counts.items(), key=lambda x: x[1], reverse=True):
        info = horses_info.get(num, {})
        results.append({
            "horse_number": num,
            "horse_name": info.get("horse_name", f"馬番{num}"),
            "post": info.get("post", 0),
            "jockey": info.get("jockey", ""),
            "votes": cnt,
            "rate": round(cnt / total * 100, 1) if total > 0 else 0,
        })

    # Check if current user has voted
    my_vote = None
    user = _get_user_from_token(authorization)
    if user:
        vote_key = f"{_VOTE_KEY_PREFIX}:{race_id}"
        v = _redis_votes.hget(vote_key, user.get("line_user_id", ""))
        if v:
            my_vote = int(v)

    return {
        "race_id": race_id,
        "total_votes": total,
        "results": results,
        "my_vote": my_vote,
    }


def _parse_race_id(race_id: str) -> tuple[str, str, str]:
    """Split a race_id into (date, venue, race_number) strings.

    Returns empty strings for components that cannot be parsed. This is
    robust against legacy ids with unusual venue characters.
    """
    if not race_id or "-" not in race_id:
        return "", "", ""
    parts = race_id.split("-")
    date_str = parts[0] if parts and len(parts[0]) == 8 and parts[0].isdigit() else ""
    venue = parts[1] if len(parts) > 1 else ""
    race_num = parts[2] if len(parts) > 2 else ""
    return date_str, venue, race_num


@app.get("/api/votes/my-history")
def api_my_vote_history(authorization: str = Header(default="")):
    """Return the current user's vote history with automatic ROI tracking.

    Per-vote lookup flow:
      1. Load the odds snapshot captured when the user voted (falls back to
         current prefetch odds if the snapshot is missing)
      2. Look up the cached race result (populated by
         `scripts/update_race_results.py` cron — this endpoint never scrapes)
      3. Assign status: hit / miss / cancelled / hit_no_payout / pending
      4. Accumulate hits, total_return, finalized and cancelled counters

    Hit rate and ROI are computed against *finalised* races only (pending and
    cancelled are excluded) so unresolved bets don't drag the metrics down.
    Cancelled races refund the stake so they neither credit nor debit ROI.
    """
    user = _get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="ログインが必要です")

    user_id = user.get("line_user_id", "")
    history_key = f"{_VOTE_KEY_PREFIX}:history:{user_id}"
    odds_snap_key = f"{_VOTE_KEY_PREFIX}:odds:{user_id}"
    raw = _redis_votes.hgetall(history_key)

    if not raw:
        return {
            "history": [],
            "total_races": 0,
            "hits": 0,
            "hit_rate": 0,
            "roi": 0,
            "total_bet": 0,
            "total_return": 0,
            "finalized_count": 0,
            "pending_count": 0,
            "cancelled_count": 0,
        }

    # Fetch all odds snapshots in one roundtrip
    try:
        odds_snapshots = _redis_votes.hgetall(odds_snap_key) or {}
    except Exception:
        odds_snapshots = {}

    # Group race_ids by date so each prefetch file is read only once
    by_date: dict[str, list[tuple[str, int]]] = {}
    for race_id, horse_number_str in raw.items():
        try:
            hn = int(horse_number_str)
        except ValueError:
            continue
        date_str, _, _ = _parse_race_id(race_id)
        by_date.setdefault(date_str, []).append((race_id, hn))

    history: list[dict] = []
    total_return = 0
    hits = 0
    finalized_count = 0
    pending_count = 0
    cancelled_count = 0

    for date_str, rows in by_date.items():
        # Cache odds per race in this date using a single prefetch read
        odds_by_race: dict[str, dict[int, float]] = {}

        for race_id, horse_number in rows:
            _, venue, race_num_str = _parse_race_id(race_id)
            race_data = get_race_entries(date_str, race_id) if date_str else None
            race_name = race_data.get("race_name", "") if race_data else ""

            entry = None
            if race_data:
                entry = next(
                    (e for e in race_data.get("entries", []) if e["horse_number"] == horse_number),
                    None,
                )
            horse_name = entry["horse_name"] if entry else f"馬番{horse_number}"

            # Prefer the snapshot taken at vote time
            odds_val = 0.0
            snap = odds_snapshots.get(race_id)
            if snap:
                try:
                    odds_val = float(snap)
                except ValueError:
                    odds_val = 0.0
            if odds_val <= 0 and entry:
                try:
                    odds_val = float(entry.get("odds", 0.0) or 0.0)
                except (ValueError, TypeError):
                    odds_val = 0.0
            if odds_val <= 0 and race_id not in odds_by_race:
                # Last-resort fallback: prefetch odds map (covers races where
                # the entries list was sparse at vote time)
                try:
                    odds_by_race[race_id] = get_odds_from_prefetch(date_str, race_id)
                except Exception:
                    odds_by_race[race_id] = {}
            if odds_val <= 0:
                try:
                    odds_val = float(odds_by_race.get(race_id, {}).get(horse_number, 0.0))
                except (ValueError, TypeError):
                    odds_val = 0.0

            # Result lookup (Redis only — no network I/O)
            race_result = get_cached_race_result(race_id)
            result_status = "pending"
            payout = 0

            if race_result:
                if race_result.get("cancelled"):
                    result_status = "cancelled"
                    cancelled_count += 1
                elif race_result.get("finalized"):
                    finalized_count += 1
                    winners = race_result.get("winner_horse_numbers")
                    if winners is None and "winner_horse_number" in race_result:
                        # Backward-compat with the earlier single-winner schema
                        winners = [race_result["winner_horse_number"]]
                    winners = set(winners or [])

                    if horse_number in winners:
                        payouts = race_result.get("win_payouts") or {}
                        try:
                            payout = int(payouts.get(str(horse_number), 0) or 0)
                        except (ValueError, TypeError):
                            payout = 0
                        # Backward compat with old "win_payout" scalar
                        if payout <= 0 and "win_payout" in race_result:
                            try:
                                payout = int(race_result.get("win_payout", 0) or 0)
                            except (ValueError, TypeError):
                                payout = 0
                        if payout > 0:
                            result_status = "hit"
                            total_return += payout
                            hits += 1
                        else:
                            # Parsed a hit but couldn't extract payout — still
                            # count it as a hit for stats purposes; profit
                            # display is suppressed on the frontend.
                            result_status = "hit_no_payout"
                            hits += 1
                    else:
                        result_status = "miss"
                else:
                    pending_count += 1
            else:
                pending_count += 1

            history.append({
                "race_id": race_id,
                "date": (
                    f"{date_str[:4]}/{date_str[4:6]}/{date_str[6:8]}"
                    if len(date_str) == 8 else date_str
                ),
                "venue": venue,
                "race_number": race_num_str,
                "race_name": race_name,
                "horse_number": horse_number,
                "horse_name": horse_name,
                "odds": round(odds_val, 1),
                "result": result_status,
                "payout": payout,
            })

    # Sort by date desc, then race number desc (stable ordering)
    def _sort_key(h: dict) -> tuple[str, int]:
        try:
            rn = int(h.get("race_number") or 0)
        except (ValueError, TypeError):
            rn = 0
        return (h.get("date", ""), rn)

    history.sort(key=_sort_key, reverse=True)

    total_bet_finalized = finalized_count * 100
    hit_rate = round(hits / finalized_count * 100, 1) if finalized_count > 0 else 0
    roi = round(total_return / total_bet_finalized * 100, 1) if total_bet_finalized > 0 else 0

    return {
        "history": history,
        "total_races": len(history),
        "hits": hits,
        "hit_rate": hit_rate,
        "roi": roi,
        "total_bet": total_bet_finalized,
        "total_return": total_return,
        "finalized_count": finalized_count,
        "pending_count": pending_count,
        "cancelled_count": cancelled_count,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Kリワード (K-Reward point system)
# ─────────────────────────────────────────────────────────────────────────────

def _kreward_balance(user_id: str) -> int:
    try:
        v = _redis_votes.get(_KREWARD_KEY.format(uid=user_id))
        return int(v) if v else 0
    except Exception:
        return 0


def _kreward_log(user_id: str) -> list[dict]:
    try:
        raw = _redis_votes.lrange(_KREWARD_LOG_KEY.format(uid=user_id), 0, 49)
        return [_json.loads(r) for r in raw]
    except Exception:
        return []


def grant_kreward(user_id: str, points: int, reason: str, race_id: str = "") -> int:
    """Kリワードを付与し新残高を返す。"""
    key = _KREWARD_KEY.format(uid=user_id)
    log_key = _KREWARD_LOG_KEY.format(uid=user_id)
    new_balance = _redis_votes.incrby(key, points)
    entry = _json.dumps({
        "points": points,
        "reason": reason,
        "race_id": race_id,
        "at": datetime.now(JST).isoformat(),
    }, ensure_ascii=False)
    pipe = _redis_votes.pipeline(transaction=False)
    pipe.lpush(log_key, entry)
    pipe.ltrim(log_key, 0, _KREWARD_LOG_MAX - 1)
    pipe.execute()
    return int(new_balance)


@app.get("/api/kreward")
def api_kreward(authorization: str = Header(default="")):
    """Get current user's K-reward balance and history."""
    user = _get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="ログインが必要です")
    uid = user.get("line_user_id", "")
    return {
        "balance": _kreward_balance(uid),
        "coin_rate": _KREWARD_COIN_RATE,
        "log": _kreward_log(uid),
    }


class KRewardTransferRequest(BaseModel):
    points: int


@app.post("/api/kreward/transfer")
async def api_kreward_transfer(
    req: KRewardTransferRequest,
    authorization: str = Header(default=""),
):
    """Transfer K-rewards to bakugatcha free coins. 1pt = 100 coins."""
    user = _get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="ログインが必要です")
    uid = user.get("line_user_id", "")

    if req.points <= 0:
        raise HTTPException(status_code=400, detail="転送ポイント数が不正です")

    balance = _kreward_balance(uid)
    if balance < req.points:
        raise HTTPException(status_code=400, detail=f"残高不足です（現在: {balance}pt）")

    if not _BAKU_KREWARD_SECRET:
        raise HTTPException(status_code=503, detail="爆ガチャ連携が設定されていません")

    coins_to_grant = req.points * _KREWARD_COIN_RATE

    # Call bakugatcha /api/kreward endpoint
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _BAKU_KREWARD_URL,
                json={
                    "line_user_id": uid,
                    "coins": coins_to_grant,
                    "description": f"netkeita Kリワード転送 ({req.points}pt)",
                },
                headers={"X-Kreward-Secret": _BAKU_KREWARD_SECRET},
                timeout=10,
            )
    except Exception as e:
        logger.error(f"bakugatcha kreward error: {e}")
        raise HTTPException(status_code=503, detail="爆ガチャへの転送に失敗しました")

    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="爆ガチャアカウントが見つかりません。爆ガチャにLINEログインしてください。")
    if resp.status_code not in (200, 201):
        logger.warning(f"bakugatcha kreward {resp.status_code}: {resp.text[:200]}")
        raise HTTPException(status_code=503, detail="爆ガチャへの転送に失敗しました")

    # Deduct K-rewards
    key = _KREWARD_KEY.format(uid=uid)
    new_balance = _redis_votes.decrby(key, req.points)
    log_key = _KREWARD_LOG_KEY.format(uid=uid)
    entry = _json.dumps({
        "points": -req.points,
        "reason": f"爆ガチャ転送 (+{coins_to_grant}コイン)",
        "at": datetime.now(JST).isoformat(),
    }, ensure_ascii=False)
    pipe = _redis_votes.pipeline(transaction=False)
    pipe.lpush(log_key, entry)
    pipe.ltrim(log_key, 0, _KREWARD_LOG_MAX - 1)
    pipe.execute()

    return {
        "success": True,
        "points_transferred": req.points,
        "coins_granted": coins_to_grant,
        "new_balance": int(new_balance),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Article posting (note-style) — public read, admin-only write
# ─────────────────────────────────────────────────────────────────────────────


class ArticleCreateRequest(BaseModel):
    title: str
    description: str = ""
    body: str
    thumbnail_url: str = ""
    status: str = "published"  # "published" or "draft"
    slug: str | None = None    # optional, auto-generated when omitted
    race_id: str = ""          # optional, links article to a specific race
    # prediction-specific fields (ignored when content_type="article")
    content_type: str = "article"   # "article" | "prediction"
    tipster_id: str = ""
    bet_method: str = ""
    ticket_count: int = 0
    preview_body: str = ""
    is_premium: bool = False


class ArticleUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    body: str | None = None
    thumbnail_url: str | None = None
    status: str | None = None
    race_id: str | None = None
    expected_updated_at: str | None = None  # optimistic locking
    bet_method: str | None = None
    ticket_count: int | None = None
    preview_body: str | None = None
    is_premium: bool | None = None


def _require_admin(authorization: str) -> dict:
    """Resolve the caller's session and require admin privileges."""
    user = _get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="ログインが必要です")
    if not _is_admin_user(user):
        raise HTTPException(status_code=403, detail="管理者権限がありません")
    return user


# ── Simple Redis-backed rate limiter ────────────────────────────────────────
# Prevents a compromised admin session (or a buggy client) from flooding the
# write endpoints. Limits are deliberately generous for normal editorial use.
_ADMIN_WRITE_LIMIT = 30      # writes
_ADMIN_WRITE_WINDOW = 60     # per this many seconds


def _rate_limit(bucket: str, user_id: str, limit: int, window: int) -> None:
    """Raise 429 when the caller exceeds `limit` hits in `window` seconds."""
    if not user_id:
        return
    key = f"nk:rate:{bucket}:{user_id}"
    try:
        pipe = _redis_client.pipeline(transaction=False)
        pipe.incr(key)
        pipe.expire(key, window)
        count, _ = pipe.execute()
    except Exception:
        logger.exception("rate limiter error")
        return
    if count and int(count) > limit:
        raise HTTPException(
            status_code=429,
            detail=f"リクエストが多すぎます。{window}秒後に再試行してください",
        )


@app.get("/api/articles")
def api_list_articles(
    include_drafts: bool = False,
    limit: int = 50,
    offset: int = 0,
    authorization: str = Header(default=""),
):
    """List articles. Public by default; admin sessions may include drafts.

    Response shape:
        {
            "articles":    [ArticleSummary, ...],
            "count":       int,      # items returned in this page
            "total_count": int,      # total matching articles
            "has_more":    bool,     # whether more pages exist
            "offset":      int,
            "limit":       int,
        }
    """
    # Only admins may request drafts.
    show_drafts = False
    if include_drafts:
        user = _get_user_from_token(authorization)
        if _is_admin_user(user):
            show_drafts = True

    page = articles_service.list_articles(
        include_drafts=show_drafts, limit=limit, offset=offset
    )
    return {
        "articles": page["items"],
        "count": len(page["items"]),
        "total_count": page["total_count"],
        "has_more": page["has_more"],
        "offset": page["offset"],
        "limit": page["limit"],
    }


@app.get("/api/articles/by-race/{race_id:path}")
def api_get_articles_by_race(race_id: str):
    """Return published articles linked to a specific race."""
    articles = articles_service.get_articles_by_race_id(race_id)
    return {"race_id": race_id, "articles": articles}


@app.get("/api/articles/{slug}")
def api_get_article(slug: str, authorization: str = Header(default="")):
    """Fetch one article.

    Draft articles are only visible to admins. Public responses strip
    author_id (admin's LINE user id) to prevent account enumeration.
    """
    if not articles_service.is_valid_slug(slug):
        raise HTTPException(status_code=400, detail="不正なスラッグです")

    record = articles_service.get_article_raw(slug)
    if not record:
        raise HTTPException(status_code=404, detail="記事が見つかりません")

    user = _get_user_from_token(authorization)
    is_admin = _is_admin_user(user)

    if record.get("status") != "published" and not is_admin:
        raise HTTPException(status_code=404, detail="記事が見つかりません")

    return articles_service.admin_view(record) if is_admin else articles_service.public_view(record)


@app.post("/api/articles")
def api_create_article(
    req: ArticleCreateRequest,
    authorization: str = Header(default=""),
    x_internal_key: str = Header(default=""),
):
    """Create a new article/prediction. Admin always allowed; approved tipsters may post predictions."""
    user = _get_user_from_token(authorization) or _get_user_from_internal_key(x_internal_key)
    if not user:
        raise HTTPException(status_code=401, detail="ログインが必要です")
    uid = user.get("line_user_id", "")
    is_tipster = req.content_type == "prediction" and tipsters_service.is_approved_tipster(uid)
    if not _is_admin_user(user) and not is_tipster:
        raise HTTPException(status_code=403, detail="管理者権限または承認済み予想家のみ投稿できます")
    _rate_limit("article_write", user.get("line_user_id", ""),
                _ADMIN_WRITE_LIMIT, _ADMIN_WRITE_WINDOW)
    try:
        # For predictions posted by tipsters: allow approved tipsters to post,
        # not just admins. The caller's line_user_id is stored as tipster_id.
        uid = user.get("line_user_id", "")
        is_tipster_post = (
            req.content_type == "prediction"
            and tipsters_service.is_approved_tipster(uid)
            and not _is_admin_user(user)
        )
        # Admin can supply any approved tipster_id (including managed ones)
        if _is_admin_user(user) and req.tipster_id:
            effective_tipster_id = req.tipster_id
        elif is_tipster_post:
            effective_tipster_id = uid
        else:
            effective_tipster_id = req.tipster_id or ""
        # Validate that the supplied tipster_id is actually approved
        if effective_tipster_id and not tipsters_service.is_approved_tipster(effective_tipster_id):
            raise HTTPException(status_code=400, detail="指定された予想家IDは承認されていません")
        record = articles_service.create_article(
            title=req.title,
            description=req.description,
            body=req.body,
            thumbnail_url=req.thumbnail_url,
            status=req.status,
            author=user.get("display_name", ""),
            author_id=uid,
            slug=req.slug,
            race_id=req.race_id,
            content_type=req.content_type,
            tipster_id=effective_tipster_id,
            bet_method=req.bet_method,
            ticket_count=req.ticket_count,
            preview_body=req.preview_body,
            is_premium=req.is_premium,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return articles_service.admin_view(record)


@app.put("/api/articles/{slug}")
def api_update_article(
    slug: str,
    req: ArticleUpdateRequest,
    authorization: str = Header(default=""),
):
    """Update an existing article. Admin or the tipster who owns the prediction."""
    user = _get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="ログインが必要です")
    uid = user.get("line_user_id", "")
    if not articles_service.is_valid_slug(slug):
        raise HTTPException(status_code=400, detail="不正なスラッグです")
    existing = articles_service.get_article_raw(slug)
    if not existing:
        raise HTTPException(status_code=404, detail="記事が見つかりません")
    is_owner = existing.get("tipster_id") == uid and tipsters_service.is_approved_tipster(uid)
    if not _is_admin_user(user) and not is_owner:
        raise HTTPException(status_code=403, detail="編集権限がありません")
    _rate_limit("article_write", uid, _ADMIN_WRITE_LIMIT, _ADMIN_WRITE_WINDOW)
    try:
        record = articles_service.update_article(
            slug,
            title=req.title,
            description=req.description,
            body=req.body,
            thumbnail_url=req.thumbnail_url,
            status=req.status,
            race_id=req.race_id,
            expected_updated_at=req.expected_updated_at,
            bet_method=req.bet_method,
            ticket_count=req.ticket_count,
            preview_body=req.preview_body,
            is_premium=req.is_premium,
        )
    except articles_service.ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if record is None:
        raise HTTPException(status_code=404, detail="記事が見つかりません")
    return articles_service.admin_view(record)


@app.delete("/api/articles/{slug}")
def api_delete_article(slug: str, authorization: str = Header(default="")):
    """Delete an article. Admin or the tipster who owns the prediction."""
    user = _get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="ログインが必要です")
    uid = user.get("line_user_id", "")
    if not articles_service.is_valid_slug(slug):
        raise HTTPException(status_code=400, detail="不正なスラッグです")
    record = articles_service.get_article_raw(slug)
    if not record:
        raise HTTPException(status_code=404, detail="記事が見つかりません")
    # Allow: admin OR the tipster who originally posted it
    is_owner = record.get("tipster_id") == uid and tipsters_service.is_approved_tipster(uid)
    if not _is_admin_user(user) and not is_owner:
        raise HTTPException(status_code=403, detail="削除権限がありません")
    _rate_limit("article_write", uid, _ADMIN_WRITE_LIMIT, _ADMIN_WRITE_WINDOW)
    articles_service.delete_article(slug)
    return {"success": True, "slug": slug}


# ─────────────────────────────────────────────────────────────────────
# Image upload (admin only) — stores images in Supabase Storage and
# returns a public URL that the markdown editor can insert immediately.
# ─────────────────────────────────────────────────────────────────────

# Separate, stricter bucket for uploads (10 per minute) — they're much
# heavier than plain article writes.
_IMAGE_UPLOAD_LIMIT = 10
_IMAGE_UPLOAD_WINDOW = 60


@app.post("/api/articles/upload-image")
async def api_upload_article_image(
    file: UploadFile = File(...),
    authorization: str = Header(default=""),
):
    """Upload a single image for article authoring. Admin only."""
    user = _require_admin(authorization)
    _rate_limit(
        "image_upload", user.get("line_user_id", ""),
        _IMAGE_UPLOAD_LIMIT, _IMAGE_UPLOAD_WINDOW,
    )

    # Lazy import so the rest of the API never fails to boot if the
    # supabase package is missing on a dev machine.
    try:
        from services import image_upload  # noqa: WPS433 (local import by design)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("image_upload module import failed")
        raise HTTPException(
            status_code=500,
            detail=f"画像アップロード機能が使えません: {exc}",
        ) from exc

    try:
        data = await file.read()
    finally:
        await file.close()

    try:
        url = image_upload.upload_image(data, file.content_type or "")
    except image_upload.ImageUploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    logger.info(f"image uploaded: {file.filename} -> {url}")
    return {"success": True, "url": url}


@app.get("/health")
def health():
    return {"status": "ok"}


# ─────────────────────────────────────────────────────────────────────────────
# Tipster (予想家) endpoints
# ─────────────────────────────────────────────────────────────────────────────


class TipsterApplyRequest(BaseModel):
    catchphrase: str
    description: str = ""


@app.post("/api/tipsters/apply")
def api_tipster_apply(req: TipsterApplyRequest, authorization: str = Header(default="")):
    """Submit a tipster application. Requires LINE login."""
    user = _get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="ログインが必要です")
    try:
        profile = tipsters_service.apply(
            line_user_id=user["line_user_id"],
            display_name=user.get("display_name", ""),
            picture_url=user.get("picture_url", ""),
            catchphrase=req.catchphrase,
            description=req.description,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"success": True, "profile": profile}


@app.get("/api/tipsters/me")
def api_tipster_me(authorization: str = Header(default="")):
    """Get the current user's tipster profile (if any)."""
    user = _get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="ログインが必要です")
    profile = tipsters_service.get_tipster(user["line_user_id"])
    return {"profile": profile}


@app.get("/api/tipsters")
def api_list_tipsters():
    """List all approved tipsters."""
    tipsters = tipsters_service.list_approved()
    return {"tipsters": tipsters, "count": len(tipsters)}


@app.get("/api/tipsters/{tipster_id}")
def api_get_tipster(tipster_id: str):
    """Get a tipster profile and their published predictions."""
    profile = tipsters_service.get_tipster(tipster_id)
    if not profile or profile.get("status") != "approved":
        raise HTTPException(status_code=404, detail="予想家が見つかりません")
    predictions = articles_service.list_predictions_by_tipster(tipster_id)
    return {"profile": profile, "predictions": predictions}


class TipsterProfileUpdateRequest(BaseModel):
    display_name: str | None = None
    catchphrase: str | None = None
    description: str | None = None
    picture_url: str | None = None
    sns_links: dict | None = None


@app.put("/api/tipsters/me")
def api_tipster_update_profile(
    req: TipsterProfileUpdateRequest,
    authorization: str = Header(default=""),
):
    """Update the current user's tipster profile."""
    user = _get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="ログインが必要です")
    updated = tipsters_service.update_profile(
        user["line_user_id"],
        display_name=req.display_name,
        catchphrase=req.catchphrase,
        description=req.description,
        picture_url=req.picture_url,
        sns_links=req.sns_links,
    )
    if not updated:
        raise HTTPException(status_code=403, detail="承認済みの予想家のみ更新できます")
    return {"success": True, "profile": updated}


# ── Admin: tipster management ─────────────────────────────────────────────────


@app.get("/api/admin/tipsters/pending")
def api_admin_list_pending(authorization: str = Header(default="")):
    """List pending tipster applications (admin only)."""
    _require_admin(authorization)
    pending = tipsters_service.list_pending()
    return {"pending": pending, "count": len(pending)}


class ManagedTipsterCreateRequest(BaseModel):
    display_name: str
    catchphrase: str
    description: str = ""
    picture_url: str = ""


@app.post("/api/admin/tipsters/managed")
def api_admin_create_managed_tipster(
    req: ManagedTipsterCreateRequest,
    authorization: str = Header(default=""),
):
    """Create a managed tipster profile (admin only, no LINE account needed)."""
    _require_admin(authorization)
    try:
        profile = tipsters_service.create_managed_tipster(
            display_name=req.display_name,
            catchphrase=req.catchphrase,
            description=req.description,
            picture_url=req.picture_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"success": True, "profile": profile}


@app.post("/api/admin/tipsters/{tipster_id}/approve")
def api_admin_approve_tipster(tipster_id: str, authorization: str = Header(default="")):
    """Approve a tipster application (admin only)."""
    _require_admin(authorization)
    profile = tipsters_service.approve(tipster_id)
    if not profile:
        raise HTTPException(status_code=404, detail="申請が見つかりません")
    return {"success": True, "profile": profile}


@app.post("/api/admin/tipsters/{tipster_id}/reject")
def api_admin_reject_tipster(tipster_id: str, authorization: str = Header(default="")):
    """Reject a tipster application (admin only)."""
    _require_admin(authorization)
    profile = tipsters_service.reject(tipster_id)
    if not profile:
        raise HTTPException(status_code=404, detail="申請が見つかりません")
    return {"success": True, "profile": profile}


@app.delete("/api/admin/tipsters/{tipster_id}")
def api_admin_delete_tipster(tipster_id: str, authorization: str = Header(default="")):
    """Delete a tipster profile (admin only)."""
    _require_admin(authorization)
    if not tipsters_service.delete_tipster(tipster_id):
        raise HTTPException(status_code=404, detail="予想家が見つかりません")
    return {"success": True, "tipster_id": tipster_id}


# ── Admin: premium access management ─────────────────────────────────────────


@app.post("/api/admin/premium-access/{target_user_id}")
def api_admin_grant_premium(target_user_id: str, authorization: str = Header(default="")):
    """Grant premium access to a user (admin only)."""
    _require_admin(authorization)
    tipsters_service.grant_premium_access(target_user_id)
    return {"success": True, "user_id": target_user_id, "access": "granted"}


@app.delete("/api/admin/premium-access/{target_user_id}")
def api_admin_revoke_premium(target_user_id: str, authorization: str = Header(default="")):
    """Revoke premium access from a user (admin only)."""
    _require_admin(authorization)
    tipsters_service.revoke_premium_access(target_user_id)
    return {"success": True, "user_id": target_user_id, "access": "revoked"}


@app.get("/api/auth/premium-status")
def api_premium_status(authorization: str = Header(default="")):
    """Check if the current user has premium access."""
    user = _get_user_from_token(authorization)
    if not user:
        return {"has_premium": False}
    has_premium = (
        _is_admin_user(user)
        or tipsters_service.is_approved_tipster(user["line_user_id"])
        or tipsters_service.has_premium_access(user["line_user_id"])
    )
    return {"has_premium": has_premium}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
