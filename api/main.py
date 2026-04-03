"""netkeita API server — FastAPI backend for JRA race ranking data."""

import logging
import sys

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import PORT
from services.data_fetcher import get_races, get_race_entries, get_today_str, get_predictions, get_analysis, get_odds_from_prefetch, get_available_dates
from services.ranking import calculate_matrix

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

app = FastAPI(title="netkeita API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict to Vercel domain
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


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
def api_matrix(race_id: str, date: str = ""):
    """Get 8-category rank matrix for all horses in a race."""
    date_str = date or (race_id.split("-")[0] if "-" in race_id else get_today_str())
    race_data = get_race_entries(date_str, race_id)
    if not race_data or not race_data.get("entries"):
        raise HTTPException(status_code=404, detail="Race not found")

    logger.info(f"Building matrix for {race_id} ({len(race_data['entries'])} horses)")

    # Fetch all data from backend
    pred_raw = get_predictions(race_data)
    flow_data = get_analysis("/api/v2/analysis/race-flow", race_data)
    jockey_data = get_analysis("/api/v2/analysis/jockey-analysis", race_data)
    bloodline_data = get_analysis("/api/v2/analysis/bloodline-analysis", race_data)
    recent_data = get_analysis("/api/v2/analysis/recent-runs", race_data)

    # Build per-horse prediction scores from the raw newspaper response
    predictions = _build_prediction_scores(pred_raw, race_data)

    # Odds from prefetch data
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

    return {
        "race_id": race_id,
        "race_name": race_data.get("race_name", ""),
        "venue": race_data.get("venue", ""),
        "distance": race_data.get("distance", ""),
        "race_number": race_data.get("race_number", 0),
        "track_condition": race_data.get("track_condition", ""),
        "horses": horses,
    }


def _build_prediction_scores(pred_raw: dict, race_data: dict) -> dict:
    """Convert newspaper API response to per-horse score dict.

    The newspaper API returns top-N horse numbers per engine.
    We convert rank position to a score (higher = better).
    """
    entries = race_data.get("entries", [])
    total = len(entries)
    scores: dict[int, dict] = {}

    for entry in entries:
        num = entry["horse_number"]
        scores[num] = {
            "dlogic_score": 0,
            "ilogic_score": 0,
            "viewlogic_score": 0,
            "metalogic_score": 0,
        }

    engine_map = {
        "dlogic": "dlogic_score",
        "ilogic": "ilogic_score",
        "viewlogic": "viewlogic_score",
        "metalogic": "metalogic_score",
    }

    for engine_key, score_key in engine_map.items():
        ranked_nums = pred_raw.get(engine_key, [])
        for rank_idx, horse_num in enumerate(ranked_nums):
            if horse_num in scores:
                scores[horse_num][score_key] = max(0, (total - rank_idx) * 10)

    return scores


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
