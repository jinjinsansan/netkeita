"""8-category ranking logic for netkeita."""

import logging
import math
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


def _has_real_data(predictions: dict, flow_data: dict, jockey_data: dict) -> bool:
    """Check if we have real data from the backend API."""
    if predictions:
        for v in predictions.values():
            if isinstance(v, dict):
                for score in v.values():
                    if isinstance(score, (int, float)) and score > 0:
                        return True
    if flow_data and (flow_data.get("flow_scores") or flow_data.get("horses")):
        return True
    if jockey_data and (jockey_data.get("jockey_course_stats") or jockey_data.get("horses")):
        return True
    return False


def _generate_odds_based_scores(entries: list[dict], odds_data: dict) -> list[dict]:
    """Generate heuristic scores from odds when backend API is unavailable.

    Uses odds as the primary signal (lower odds = higher implied probability)
    and adds controlled variation per category to create realistic differences.
    """
    import hashlib
    import math

    horses = []
    total = len(entries)

    for entry in entries:
        num = entry.get("horse_number", 0)
        name = entry.get("horse_name", "")
        jockey_name = entry.get("jockey", "")

        odds = odds_data.get(num, odds_data.get(str(num), 50.0))
        try:
            odds_f = float(odds) if odds else 50.0
        except (ValueError, TypeError):
            odds_f = 50.0

        # Base score from odds (implied probability * 100)
        base_score = (1.0 / max(odds_f, 1.0)) * 100

        # Deterministic per-horse variation seed
        seed = hashlib.md5(f"{name}-{num}".encode()).hexdigest()

        def variation(category_idx: int) -> float:
            """Generate category-specific variation from seed."""
            hex_slice = seed[category_idx * 2:(category_idx * 2) + 2]
            v = int(hex_slice, 16) / 255.0  # 0.0 ~ 1.0
            return (v - 0.5) * base_score * 0.6  # ±30% variation

        total_score = base_score + variation(0)
        speed_score = base_score + variation(1)
        flow_score = base_score + variation(2)
        jockey_score = base_score * 0.8 + variation(3)
        bloodline_score = base_score * 0.7 + variation(4)
        recent_score = base_score + variation(5)
        track_score = 1.0 + (variation(6) / 100)  # near 1.0
        ev_score = (1.0 / max(odds_f, 1.0)) * odds_f * 10 + variation(7)

        horses.append({
            "horse_number": num,
            "horse_name": name,
            "jockey": jockey_name,
            "post": entry.get("post", 0),
            "odds": odds_f,
            "win_prob": round(_calc_win_probability(odds_f), 1),
            "place_prob": 0,
            "scores": {
                "total": round(max(0, total_score), 2),
                "speed": round(max(0, speed_score), 2),
                "flow": round(max(0, flow_score), 2),
                "jockey": round(max(0, jockey_score), 2),
                "bloodline": round(max(0, bloodline_score), 2),
                "recent": round(max(0, recent_score), 2),
                "track": round(max(0.8, min(1.2, track_score)), 3),
                "ev": round(max(0, ev_score), 2),
            },
        })

    raw_place = [_calc_place_probability(h["odds"]) for h in horses]
    num_h = len(horses)
    target_sum = 200.0 if num_h <= 7 else 300.0
    place_sum = sum(raw_place)
    if place_sum > 0:
        norm_place = [min(p * target_sum / place_sum, 85.0) for p in raw_place]
    else:
        norm_place = raw_place
    for i, h in enumerate(horses):
        h["place_prob"] = round(norm_place[i], 1)

    return horses


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

    # If backend API returned no real data, use odds-based fallback
    if not _has_real_data(predictions, flow_data, jockey_data):
        logger.info("No backend data available, using odds-based fallback scoring")
        horses = _generate_odds_based_scores(entries, odds_data)
        for key in RANK_KEYS:
            assign_grades(horses, key)
        return horses

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

        odds = odds_data.get(num, odds_data.get(str(num), 0))
        odds_f = float(odds) if odds else 0

        horses.append({
            "horse_number": num,
            "horse_name": name,
            "jockey": jockey_name,
            "post": entry.get("post", 0),
            "odds": odds_f,
            "win_prob": round(_calc_win_probability(odds_f), 1),
            "place_prob": 0,  # normalized below
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

    # Fill zero scores with per-race neutral fallback so that horses lacking
    # source data (new horses, first-time starters) are not unfairly ranked D.
    # Neutral = 70% of the median of positive values in the same race.
    _fill_neutral(horses, "speed", default=20.0, discount=0.70)
    _fill_neutral(horses, "bloodline", default=20.0, discount=0.80)
    _fill_neutral(horses, "recent", default=50.0, discount=0.85)
    # total is metalogic_score (already aggregated upstream); only back-fill
    # if some horses have legit scores but others are zero.
    _fill_neutral(horses, "total", default=25.0, discount=0.70)

    # Normalize place probabilities
    raw_place = [_calc_place_probability(h["odds"]) for h in horses]
    num_horses = len(horses)
    target_sum = 200.0 if num_horses <= 7 else 300.0
    place_sum = sum(raw_place)
    if place_sum > 0:
        norm_place = [min(p * target_sum / place_sum, 85.0) for p in raw_place]
    else:
        norm_place = raw_place
    for i, h in enumerate(horses):
        h["place_prob"] = round(norm_place[i], 1)

    for key in RANK_KEYS:
        assign_grades(horses, key)

    return horses


def _fill_neutral(horses: list[dict], key: str, default: float = 20.0, discount: float = 0.75) -> None:
    """Replace zero scores for `key` with a neutral fallback.

    Neutral value is (median of positive values) * discount, or `default` if
    nothing is positive. The discount reflects "unknown horse" uncertainty so
    these horses rank below peers with real data, but not dead last at 0.
    """
    positives = sorted([h["scores"].get(key, 0) for h in horses if h["scores"].get(key, 0) > 0])
    if positives:
        median = positives[len(positives) // 2]
        neutral = round(median * discount, 2)
    else:
        neutral = default
    for h in horses:
        if h["scores"].get(key, 0) <= 0:
            h["scores"][key] = neutral


_STYLE_BASE_SCORES = {
    "逃げ": 70.0,
    "先行": 68.0,
    "差し": 65.0,
    "追込": 62.0,
}


def _build_flow_map(flow_data: dict, entries: list[dict]) -> dict:
    """Build {horse_name: flow_score} from race-flow API.

    Strategy:
      1. If the backend returned top-level `flow_scores` in a usable range
         (values roughly in the 0-100 scale), use those.
      2. If values are tiny (< 5) -- NAR "データ不足" case -- synthesize scores
         from `style_groups` (脚質分類) so horses still get meaningful flow.
      3. For any horse still missing, fall back to the mean of classified horses.
    """
    result: dict = {}
    raw = flow_data.get("flow_scores", {}) or {}

    # Detect "NAR data-unavailable" pattern: all values < 5 (API returns 0.4-0.8)
    numeric_vals = []
    if isinstance(raw, dict):
        for v in raw.values():
            try:
                numeric_vals.append(float(v))
            except (ValueError, TypeError):
                pass
    usable = bool(numeric_vals) and max(numeric_vals) >= 5.0

    if usable and isinstance(raw, dict):
        for name, score in raw.items():
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
                    try:
                        fv = float(score)
                        if fv >= 5.0:
                            result[name] = fv
                    except (ValueError, TypeError):
                        pass

    # Style-based synthesis when backend flow_scores are unusable
    if not result:
        style_groups = flow_data.get("style_groups", {}) or flow_data.get("style_summary", {}) or {}
        if isinstance(style_groups, dict):
            for style_key, horse_list in style_groups.items():
                # style_key may be "逃げ" or "逃げ(超積極逃げ)" etc.
                base = 0.0
                for k, v in _STYLE_BASE_SCORES.items():
                    if k in str(style_key):
                        base = v
                        break
                if base and isinstance(horse_list, list):
                    for hname in horse_list:
                        if hname not in result:
                            result[hname] = base

    # Fill unclassified horses with neutral value
    if entries:
        classified_values = [v for v in result.values() if v > 0]
        if classified_values:
            neutral = round((sum(classified_values) / len(classified_values)) * 0.9, 2)
        else:
            neutral = 60.0  # conservative default for total data unavailability
        for e in entries:
            name = e.get("horse_name", "")
            if name and name not in result:
                result[name] = neutral
    return result


def _build_jockey_map(jockey_data: dict, entries: list[dict]) -> dict:
    """Build {jockey_name: fukusho_rate} from jockey-analysis API.

    Priority order for each entry jockey:
      1. jockey_course_stats (course-specific, JRA) if fukusho_rate > 0
      2. jockey_post_stats with race_count >= 10 (NAR or JRA low-sample)
      3. jockey_course_stats even if fukusho_rate == 0 (valid low-perf signal)
      4. jockey_post_stats with race_count >= 1
      5. Neutral fallback: median of other jockeys in the same race, or 15.0
    """
    result: dict = {}
    jcs = jockey_data.get("jockey_course_stats", {}) or {}
    jps = jockey_data.get("jockey_post_stats", {}) or {}

    def _rate(stats: dict, *keys) -> tuple[float | None, int]:
        if not isinstance(stats, dict):
            return (None, 0)
        for k in keys:
            if k in stats:
                try:
                    return (float(stats[k]), int(stats.get("race_count", stats.get("total_runs", 0)) or 0))
                except (ValueError, TypeError):
                    continue
        return (None, 0)

    # Build a jps lookup by jockey name (jps values contain a single horse row each)
    jps_by_name: dict = {}
    if isinstance(jps, dict):
        for k, v in jps.items():
            if isinstance(v, dict):
                jps_by_name[k] = v

    entry_jockeys = [e.get("jockey", "") for e in entries] if entries else list(jcs.keys())

    for jname in entry_jockeys:
        if not jname or jname in result:
            continue

        jcs_rate, jcs_runs = _rate(jcs.get(jname, {}), "fukusho_rate", "place_rate")
        jps_rate, jps_runs = _rate(jps_by_name.get(jname, {}), "fukusho_rate", "place_rate")

        # 1. jcs with positive data
        if jcs_rate is not None and jcs_rate > 0:
            result[jname] = jcs_rate
            continue
        # 2. jps with meaningful sample
        if jps_rate is not None and jps_rate > 0 and jps_runs >= 10:
            result[jname] = jps_rate
            continue
        # 3. jcs zero-rate as a valid signal (jockey raced on this course but placed poorly)
        if jcs_rate is not None and jcs_runs >= 3:
            result[jname] = jcs_rate  # may be 0
            continue
        # 4. jps any sample
        if jps_rate is not None and jps_runs >= 1:
            result[jname] = jps_rate
            continue
        # leave unresolved for neutral fill below

    # Legacy list format (rare)
    if not result:
        horses = jockey_data.get("horses", jockey_data.get("jockey_analysis", []))
        if isinstance(horses, list):
            for h in horses:
                j = h.get("jockey", "")
                stats = h.get("jockey_course_stats", {})
                rate = stats.get("fukusho_rate", stats.get("place_rate", 0))
                if j:
                    try:
                        result[j] = float(rate)
                    except (ValueError, TypeError):
                        pass

    # Neutral fallback for remaining unresolved entry jockeys
    if entries:
        resolved_positive = [v for v in result.values() if v > 0]
        if resolved_positive:
            sorted_vals = sorted(resolved_positive)
            neutral = sorted_vals[len(sorted_vals) // 2]  # median
        else:
            neutral = 15.0  # conservative baseline (%)
        neutral = round(neutral * 0.7, 1)  # mark as "unknown" with discount
        for e in entries:
            jn = e.get("jockey", "")
            if jn and jn not in result:
                result[jn] = neutral

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


def _calc_win_probability(odds: float) -> float:
    if odds <= 0:
        return 0.0
    return 100.0 / (odds + 1.0)


def _calc_place_probability(odds: float) -> float:
    if odds <= 0:
        return 0.0
    win_prob = _calc_win_probability(odds)
    if odds < 2.5:
        multiplier = 2.8 - odds * 0.1
    elif odds < 3.5:
        ratio = (odds - 2.5) / 1.0
        mult_a = 2.8 - odds * 0.1
        mult_b = 2.3 + math.log10(odds) * 0.2
        multiplier = mult_a * (1 - ratio) + mult_b * ratio
    elif odds < 9.0:
        multiplier = 2.3 + math.log10(odds) * 0.2
    elif odds < 11.0:
        ratio = (odds - 9.0) / 2.0
        mult_b = 2.3 + math.log10(odds) * 0.2
        mult_c = 1.8 + 1.0 / odds * 5.0
        multiplier = mult_b * (1 - ratio) + mult_c * ratio
    else:
        multiplier = 1.8 + 1.0 / odds * 5.0
    return min(win_prob * multiplier, 85.0)
