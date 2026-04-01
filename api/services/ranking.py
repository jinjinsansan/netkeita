"""8-category ranking logic for netkeita."""

from typing import Literal

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
    """Calculate 8-category scores and grades for all horses.

    Args:
        entries: list of horse dicts with horse_number, horse_name, jockey, post
        predictions: full-scores response {horse_number: {dlogic, ilogic, viewlogic, metalogic}}
        flow_data: race-flow response
        jockey_data: jockey-analysis response
        bloodline_data: bloodline-analysis response
        recent_data: recent-runs response
        odds_data: odds dict {horse_number: odds_value}
    """
    horses = []

    for entry in entries:
        num = entry.get("horse_number", 0)
        num_str = str(num)

        # 1. Total: MetaLogic score
        pred = predictions.get(num, predictions.get(num_str, {}))
        total_score = pred.get("metalogic_score", 0)

        # 2. Speed: D-Logic score
        speed_score = pred.get("dlogic_score", 0)

        # 3. Flow: ViewLogic flow_score
        flow_score = _extract_flow_score(flow_data, num)

        # 4. Jockey: course place rate
        jockey_score = _extract_jockey_score(jockey_data, num)

        # 5. Bloodline: avg of sire + broodmare course place rate
        bloodline_score = _extract_bloodline_score(bloodline_data, num)

        # 6. Recent: inverse of avg finishing position (lower avg = higher score)
        recent_score = _extract_recent_score(recent_data, num)

        # 7. Track: track_adjustment coefficient
        track_score = pred.get("track_adjustment", 1.0)

        # 8. EV: predicted win prob / implied prob from odds
        ev_score = _calc_ev(pred, odds_data, num)

        horses.append({
            "horse_number": num,
            "horse_name": entry.get("horse_name", ""),
            "jockey": entry.get("jockey", ""),
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


def _extract_flow_score(flow_data: dict, horse_number: int) -> float:
    horses = flow_data.get("horses", flow_data.get("horse_analysis", []))
    if isinstance(horses, list):
        for h in horses:
            if h.get("horse_number") == horse_number:
                return h.get("flow_score", h.get("position_score", 0))
    return 0


def _extract_jockey_score(jockey_data: dict, horse_number: int) -> float:
    horses = jockey_data.get("horses", jockey_data.get("jockey_analysis", []))
    if isinstance(horses, list):
        for h in horses:
            if h.get("horse_number") == horse_number:
                stats = h.get("jockey_course_stats", {})
                return stats.get("fukusho_rate", stats.get("place_rate", 0))
    return 0


def _extract_bloodline_score(bloodline_data: dict, horse_number: int) -> float:
    horses = bloodline_data.get("horses", bloodline_data.get("bloodline_analysis", []))
    if isinstance(horses, list):
        for h in horses:
            if h.get("horse_number") == horse_number:
                sire = h.get("sire_course_stats", {})
                broodmare = h.get("broodmare_course_stats", {})
                sire_rate = sire.get("place_rate", 0)
                bm_rate = broodmare.get("place_rate", 0)
                if sire_rate and bm_rate:
                    return (sire_rate + bm_rate) / 2
                return sire_rate or bm_rate
    return 0


def _extract_recent_score(recent_data: dict, horse_number: int) -> float:
    horses = recent_data.get("horses", recent_data.get("recent_runs", []))
    if isinstance(horses, list):
        for h in horses:
            if h.get("horse_number") == horse_number:
                runs = h.get("runs", [])
                if not runs:
                    return 0
                positions = [r.get("position", 99) for r in runs if r.get("position")]
                if not positions:
                    return 0
                avg = sum(positions) / len(positions)
                # Invert: lower avg position = better → higher score
                # Score range: avg=1 → 100, avg=18 → ~5
                return max(0, 100 - (avg - 1) * 6)
    return 0


def _calc_ev(pred: dict, odds_data: dict, horse_number: int) -> float:
    win_prob = pred.get("win_probability", 0)
    odds = odds_data.get(horse_number, odds_data.get(str(horse_number), 0))
    if not odds or not win_prob:
        return 0
    try:
        odds_f = float(odds)
        if odds_f <= 0:
            return 0
        implied_prob = 1.0 / odds_f
        return win_prob / implied_prob if implied_prob > 0 else 0
    except (ValueError, TypeError, ZeroDivisionError):
        return 0
