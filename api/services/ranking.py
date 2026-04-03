"""8-category ranking logic for netkeita."""

import logging
from typing import Literal

logger = logging.getLogger(__name__)

Grade = Literal["S", "A", "B", "C", "D"]


def score_to_grade(rank: int, total: int) -> Grade:
    if rank == 1:
        return "S"
    pct = rank / total
    if pct <= 0.25:
        return "A"
    if pct <= 0.50:
        return "B"
    if pct <= 0.75:
        return "C"
    return "D"


def assign_grades(horses: list[dict], key: str) -> None:
    """Sort horses by scores[key] descending and assign ranks[key] grade."""
    sorted_horses = sorted(
        range(len(horses)),
        key=lambda i: horses[i]["scores"].get(key, 0),
        reverse=True,
    )
    total = len(horses)
    for rank_idx, horse_idx in enumerate(sorted_horses, 1):
        horses[horse_idx].setdefault("ranks", {})[key] = score_to_grade(rank_idx, total)
        horses[horse_idx].setdefault("raw_ranks", {})[key] = rank_idx


RANK_KEYS = ["total", "speed", "flow", "jockey", "bloodline", "recent", "track", "ev"]


def calculate_matrix(
    entries: list[dict],
    predictions: dict,
    flow_data: dict,
    jockey_data: dict,
    bloodline_data: dict,
    recent_data: dict,
    odds_data: dict,
) -> list[dict]:
    """Calculate 8-category scores and grades for all horses."""
    horses = []

    # Pre-build lookup maps from API responses
    flow_map = _build_flow_map(flow_data, entries)
    jockey_map = _build_jockey_map(jockey_data, entries)
    bloodline_map = _build_bloodline_map(bloodline_data)
    recent_map = _build_recent_map(recent_data)

    for entry in entries:
        num = entry.get("horse_number", 0)
        name = entry.get("horse_name", "")
        jockey_name = entry.get("jockey", "")

        pred = predictions.get(num, predictions.get(str(num), {}))
        total_score = pred.get("metalogic_score", 0)
        speed_score = pred.get("dlogic_score", 0)
        flow_score = flow_map.get(name, 0)
        jockey_score = jockey_map.get(jockey_name, 0)
        bloodline_score = bloodline_map.get(num, 0)
        recent_score = recent_map.get(num, 0)
        track_score = pred.get("track_adjustment", 1.0)
        ev_score = _calc_ev(pred, odds_data, num)

        horses.append({
            "horse_number": num,
            "horse_name": name,
            "jockey": jockey_name,
            "post": entry.get("post", 0),
            "scores": {
                "total": total_score,
                "speed": speed_score,
                "flow": flow_score,
                "jockey": jockey_score,
                "bloodline": bloodline_score,
                "recent": recent_score,
                "track": track_score,
                "ev": ev_score,
            },
        })

    for key in RANK_KEYS:
        assign_grades(horses, key)

    return horses


def _build_flow_map(flow_data: dict, entries: list[dict]) -> dict:
    """Build {horse_name: flow_score} from race-flow API.
    API returns: {flow_scores: {horse_name: score, ...}}
    """
    result = {}
    flow_scores = flow_data.get("flow_scores", {})
    if isinstance(flow_scores, dict):
        for name, score in flow_scores.items():
            try:
                result[name] = float(score)
            except (ValueError, TypeError):
                pass
    if not result:
        horses = flow_data.get("horses", flow_data.get("horse_analysis", []))
        if isinstance(horses, list):
            for h in horses:
                name = h.get("horse_name", "")
                score = h.get("flow_score", h.get("position_score", 0))
                if name:
                    result[name] = float(score)
    return result


def _build_jockey_map(jockey_data: dict, entries: list[dict]) -> dict:
    """Build {jockey_name: fukusho_rate} from jockey-analysis API.
    API returns: {jockey_course_stats: {jockey_name: {fukusho_rate: N}}}
    """
    result = {}
    jcs = jockey_data.get("jockey_course_stats", {})
    if isinstance(jcs, dict):
        for jockey_name, stats in jcs.items():
            if isinstance(stats, dict):
                rate = stats.get("fukusho_rate", stats.get("place_rate", 0))
                try:
                    result[jockey_name] = float(rate)
                except (ValueError, TypeError):
                    pass
    if not result:
        horses = jockey_data.get("horses", jockey_data.get("jockey_analysis", []))
        if isinstance(horses, list):
            for h in horses:
                jname = h.get("jockey", "")
                stats = h.get("jockey_course_stats", {})
                rate = stats.get("fukusho_rate", stats.get("place_rate", 0))
                if jname:
                    result[jname] = float(rate)
    return result


def _build_bloodline_map(bloodline_data: dict) -> dict:
    """Build {horse_number: avg_place_rate} from bloodline-analysis API.
    API returns: {bloodline: [{horse_number, sire_performance: {place_rate}, broodmare_performance: {place_rate}}]}
    """
    result = {}
    bloodline_list = bloodline_data.get("bloodline", [])
    if isinstance(bloodline_list, list):
        for h in bloodline_list:
            num = h.get("horse_number", 0)
            sire_perf = h.get("sire_performance", {})
            bm_perf = h.get("broodmare_performance", {})
            sr = float(sire_perf.get("place_rate", 0)) if isinstance(sire_perf, dict) else 0
            br = float(bm_perf.get("place_rate", 0)) if isinstance(bm_perf, dict) else 0
            if sr and br:
                result[num] = (sr + br) / 2
            else:
                result[num] = sr or br
    if not result:
        horses = bloodline_data.get("horses", bloodline_data.get("bloodline_analysis", []))
        if isinstance(horses, list):
            for h in horses:
                num = h.get("horse_number", 0)
                sire = h.get("sire_course_stats", h.get("sire_performance", {}))
                bm = h.get("broodmare_course_stats", h.get("broodmare_performance", {}))
                sr = float(sire.get("place_rate", 0)) if isinstance(sire, dict) else 0
                br = float(bm.get("place_rate", 0)) if isinstance(bm, dict) else 0
                if sr and br:
                    result[num] = (sr + br) / 2
                else:
                    result[num] = sr or br
    return result


def _build_recent_map(recent_data: dict) -> dict:
    """Build {horse_number: recent_score} from recent-runs API.
    API returns: {horses: [{horse_number, runs: [{finish: N}]}]}
    """
    result = {}
    horses = recent_data.get("horses", recent_data.get("recent_runs", []))
    if isinstance(horses, list):
        for h in horses:
            num = h.get("horse_number", 0)
            runs = h.get("runs", [])
            if not runs:
                result[num] = 0
                continue
            positions = []
            for r in runs:
                pos = r.get("finish", r.get("position", 0))
                if pos and isinstance(pos, (int, float)) and pos > 0:
                    positions.append(pos)
            if not positions:
                result[num] = 0
                continue
            avg = sum(positions) / len(positions)
            result[num] = max(0, 100 - (avg - 1) * 6)
    return result


def _calc_ev(pred: dict, odds_data: dict, horse_number: int) -> float:
    """Calculate expected value score."""
    win_prob = pred.get("win_probability", 0)
    if not win_prob:
        meta_score = pred.get("metalogic_score", 0)
        if meta_score > 0:
            win_prob = min(0.5, meta_score / 500)

    odds = odds_data.get(horse_number, odds_data.get(str(horse_number), 0))
    if not odds or not win_prob:
        return win_prob * 100 if win_prob else 0

    try:
        odds_f = float(odds)
        if odds_f <= 0:
            return 0
        implied_prob = 1.0 / odds_f
        return (win_prob / implied_prob) * 10 if implied_prob > 0 else 0
    except (ValueError, TypeError, ZeroDivisionError):
        return 0
