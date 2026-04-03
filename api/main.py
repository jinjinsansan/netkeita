"""netkeita API server — FastAPI backend for JRA race ranking data."""

import asyncio
import logging
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

# In-memory session store (token -> user_info)
_sessions: dict[str, dict] = {}


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
        _sessions[session_token] = {
            "line_user_id": line_user_id,
            "display_name": display_name,
            "picture_url": picture_url,
        }

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
    if not token or token not in _sessions:
        return {"authenticated": False}
    user = _sessions[token]
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


@app.get("/api/horse-detail/{race_id}/{horse_number}")
def api_horse_detail(race_id: str, horse_number: int, date: str = ""):
    """Get detailed info for a single horse: stable comments, recent runs, bloodline."""
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

    # Rewrite comment to avoid copyright issues
    if horse_stable and horse_stable.get("comment"):
        horse_stable = rewrite_comment(horse_number, horse_stable)

    recent_runs = get_horse_recent_runs(race_data, horse_number)
    bloodline = get_horse_bloodline(race_data, horse_number)

    return {
        "horse_number": horse_number,
        "horse_name": entry["horse_name"],
        "stable_comment": horse_stable,
        "recent_runs": recent_runs,
        "bloodline": bloodline,
    }


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


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
