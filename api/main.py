"""netkeita API server — FastAPI backend for JRA race ranking data."""

import asyncio
import logging
import random
import secrets
import sys
import time
import urllib.parse

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from config import PORT, LINE_CHANNEL_ID, LINE_CHANNEL_SECRET, FRONTEND_URL
from services.data_fetcher import (
    get_races, get_race_entries, get_today_str, get_full_scores, get_analysis,
    get_odds_from_prefetch, get_available_dates, get_internet_predictions,
    get_horse_recent_runs, get_horse_bloodline, get_stable_comments,
    async_get_full_scores, async_get_analysis,
)
from services.ranking import calculate_matrix
from services.rewriter import rewrite_comment
from services.course_stats_scraper import get_course_stats_for_horse

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


@app.get("/api/auth/me")
def get_me(authorization: str = Header(default="")):
    """Get current user info from session token."""
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else ""
    if not token:
        return {"authenticated": False}
    user = _load_session(token)
    if not user:
        return {"authenticated": False}
    return {
        "authenticated": True,
        "user": {
            "display_name": user["display_name"],
            "picture_url": user.get("picture_url", ""),
        },
    }


@app.get("/api/races")
def api_races(date: str = ""):
    """Get JRA race list for a given date."""
    date_str = date or get_today_str()
    races = get_races(date_str)
    return {"date": date_str, "races": races, "count": len(races)}


@app.get("/api/race/{race_id}/entries")
def api_entries(race_id: str, date: str = ""):
    """Get race entries (出馬表)."""
    date_str = date or (race_id.split("-")[0] if "-" in race_id else get_today_str())
    entries = get_race_entries(date_str, race_id)
    if not entries:
        raise HTTPException(status_code=404, detail="Race not found")
    return entries


@app.get("/api/race/{race_id}/matrix")
async def api_matrix(race_id: str, date: str = ""):
    """Get 8-category rank matrix for all horses in a race."""
    # Check cache first
    cached = _matrix_cache.get(race_id)
    if cached and (time.time() - cached[0]) < MATRIX_CACHE_TTL:
        logger.info(f"Cache hit for {race_id}")
        return cached[1]

    date_str = date or (race_id.split("-")[0] if "-" in race_id else get_today_str())
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
    )

    logger.info(f"Matrix built: {len(horses)} horses, sample scores: {horses[0]['scores'] if horses else 'none'}")

    result = {
        "race_id": race_id,
        "race_name": race_data.get("race_name", ""),
        "venue": race_data.get("venue", ""),
        "distance": race_data.get("distance", ""),
        "race_number": race_data.get("race_number", 0),
        "track_condition": race_data.get("track_condition", ""),
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
    cache_key = f"{race_id}:{horse_number}"
    cached = _horse_detail_cache.get(cache_key)
    if cached and (time.time() - cached[0]) < HORSE_DETAIL_CACHE_TTL:
        return cached[1]

    date_str = date or (race_id.split("-")[0] if "-" in race_id else get_today_str())
    race_data = get_race_entries(date_str, race_id)
    if not race_data:
        raise HTTPException(status_code=404, detail="Race not found")

    entry = next((e for e in race_data.get("entries", []) if e["horse_number"] == horse_number), None)
    if not entry:
        raise HTTPException(status_code=404, detail="Horse not found")

    venue = race_data.get("venue", "")
    race_number_int = race_data.get("race_number", 0)

    stable = get_stable_comments(date_str, venue, race_number_int)
    horse_stable = stable.get(horse_number, stable.get(str(horse_number), {}))

    # Rewrite comment in background (non-blocking)
    if horse_stable and horse_stable.get("comment"):
        horse_stable = rewrite_comment(horse_number, horse_stable)

    recent_runs = get_horse_recent_runs(race_data, horse_number)
    bloodline = get_horse_bloodline(race_data, horse_number)

    # Course stats from netkeiba (Redis cache only - populated by prefetch)
    course_stats = {}
    race_id_nk = race_data.get("race_id_netkeiba", "")
    if race_id_nk:
        try:
            course_stats = get_course_stats_for_horse(race_id_nk, horse_number)
        except Exception:
            pass

    result = {
        "horse_number": horse_number,
        "horse_name": entry["horse_name"],
        "stable_comment": horse_stable,
        "recent_runs": recent_runs,
        "bloodline": bloodline,
        "course_stats": course_stats,
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
_DUMMY_TTL = 86400 * 3  # dummy flag expires in 3 days


def _get_user_from_token(authorization: str) -> dict | None:
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else ""
    if not token:
        return None
    return _load_session(token)


def _ensure_dummy_votes(race_id: str):
    """Generate dummy votes for a race if not already done."""
    flag_key = f"{_VOTE_KEY_PREFIX}:dummy:{race_id}"
    if _redis_votes.exists(flag_key):
        return

    # Try in-memory cache first, then fetch race entries directly
    horses = []
    cached = _matrix_cache.get(race_id)
    if cached:
        horses = cached[1].get("horses", [])

    if not horses:
        # Fallback: get entries from race data and assign uniform weights
        date_str = race_id.split("-")[0] if "-" in race_id else get_today_str()
        race_data = get_race_entries(date_str, race_id)
        if race_data and race_data.get("entries"):
            horses = [{"horse_number": e["horse_number"], "scores": {"total": 0}} for e in race_data["entries"]]

    if not horses:
        return

    # Build weight distribution based on total score (or uniform if no scores)
    has_scores = any(h["scores"]["total"] > 0 for h in horses)
    if has_scores:
        scored = sorted(horses, key=lambda h: h["scores"]["total"], reverse=True)
    else:
        scored = horses
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

    total_w = sum(w for _, w in weights)
    probs = [(num, w / total_w) for num, w in weights]

    total_votes = random.randint(30, 80)
    count_key = f"{_VOTE_KEY_PREFIX}:count:{race_id}"

    for _ in range(total_votes):
        r = random.random()
        cumulative = 0.0
        chosen = probs[0][0]
        for num, p in probs:
            cumulative += p
            if r <= cumulative:
                chosen = num
                break
        _redis_votes.hincrby(count_key, str(chosen), 1)

    _redis_votes.setex(flag_key, _DUMMY_TTL, "1")
    _redis_votes.expire(count_key, _DUMMY_TTL)
    logger.info(f"Generated {total_votes} dummy votes for {race_id}")


class VoteRequest(BaseModel):
    horse_number: int


@app.post("/api/votes/{race_id}")
def api_vote(race_id: str, req: VoteRequest, authorization: str = Header(default="")):
    """Submit or change a vote for a race. Requires authentication."""
    user = _get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="ログインが必要です")

    user_id = user.get("line_user_id", "")
    if not user_id:
        raise HTTPException(status_code=401, detail="ユーザー情報が不正です")

    # Check horse_number validity from matrix cache
    cached = _matrix_cache.get(race_id)
    if cached:
        valid_numbers = {h["horse_number"] for h in cached[1].get("horses", [])}
        if req.horse_number not in valid_numbers:
            raise HTTPException(status_code=400, detail="不正な馬番です")

    vote_key = f"{_VOTE_KEY_PREFIX}:{race_id}"
    count_key = f"{_VOTE_KEY_PREFIX}:count:{race_id}"

    # Check if user already voted (for count adjustment)
    prev = _redis_votes.hget(vote_key, user_id)
    if prev:
        _redis_votes.hincrby(count_key, prev, -1)

    # Save vote and update count
    _redis_votes.hset(vote_key, user_id, str(req.horse_number))
    _redis_votes.hincrby(count_key, str(req.horse_number), 1)
    _redis_votes.expire(vote_key, _DUMMY_TTL)
    _redis_votes.expire(count_key, _DUMMY_TTL)

    # Track user's vote history (sorted set: race_id -> horse_number)
    history_key = f"{_VOTE_KEY_PREFIX}:history:{user_id}"
    _redis_votes.hset(history_key, race_id, str(req.horse_number))
    _redis_votes.expire(history_key, _DUMMY_TTL)

    return {"success": True, "horse_number": req.horse_number}


@app.get("/api/votes/{race_id}/results")
def api_vote_results(race_id: str, authorization: str = Header(default="")):
    """Get vote results for a race."""
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


@app.get("/api/votes/my-history")
def api_my_vote_history(authorization: str = Header(default="")):
    """Get current user's vote history with ROI calculation."""
    user = _get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="ログインが必要です")

    user_id = user.get("line_user_id", "")
    history_key = f"{_VOTE_KEY_PREFIX}:history:{user_id}"
    raw = _redis_votes.hgetall(history_key)
    if not raw:
        return {"history": [], "total_races": 0, "hits": 0, "hit_rate": 0, "roi": 0}

    history = []
    total_bet = 0
    total_return = 0
    hits = 0

    for race_id, horse_number_str in raw.items():
        horse_number = int(horse_number_str)
        date_str = race_id.split("-")[0] if "-" in race_id else ""
        venue = race_id.split("-")[1] if "-" in race_id else ""
        race_num_str = race_id.split("-")[2] if race_id.count("-") >= 2 else ""

        # Get race info
        race_data = get_race_entries(date_str, race_id) if date_str else None
        race_name = race_data.get("race_name", "") if race_data else ""
        entry = None
        if race_data:
            entry = next((e for e in race_data.get("entries", []) if e["horse_number"] == horse_number), None)

        horse_name = entry["horse_name"] if entry else f"馬番{horse_number}"

        # Get odds for the horse
        odds = 0.0
        if entry:
            odds = entry.get("odds", 0.0) or 0.0

        # Check race result (1st place finish)
        # Result is not yet available for future races
        result_status = "pending"  # pending, hit, miss
        payout = 0

        # For now, all current races are "pending" (results not yet available)
        # In the future, integrate race results API
        total_bet += 100

        history.append({
            "race_id": race_id,
            "date": f"{date_str[:4]}/{date_str[4:6]}/{date_str[6:8]}" if len(date_str) == 8 else date_str,
            "venue": venue,
            "race_number": race_num_str,
            "race_name": race_name,
            "horse_number": horse_number,
            "horse_name": horse_name,
            "odds": odds,
            "result": result_status,
            "payout": payout,
        })

    # Sort by date descending
    history.sort(key=lambda x: x["date"], reverse=True)

    hit_rate = round(hits / len(history) * 100, 1) if history else 0
    roi = round(total_return / total_bet * 100, 1) if total_bet > 0 else 0

    return {
        "history": history,
        "total_races": len(history),
        "hits": hits,
        "hit_rate": hit_rate,
        "roi": roi,
        "total_bet": total_bet,
        "total_return": total_return,
    }


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
