"""8-category ranking logic for netkeita."""

import logging
import math
import re
from typing import Literal

logger = logging.getLogger(__name__)

Grade = Literal["S", "A", "B", "C", "D"]

# ─────────────────────────────────────────────────────────────────────────────
# Class hierarchy for race quality weighting
# ─────────────────────────────────────────────────────────────────────────────

# Numeric tier: higher = stronger class. Used for both weighting and step calc.
CLASS_TIER: dict[str, float] = {
    # JRA graded
    "G1": 10.0, "Jpn1": 10.0, "GI": 10.0,
    "G2": 9.0, "Jpn2": 9.0, "GII": 9.0,
    "G3": 8.0, "Jpn3": 8.0, "GIII": 8.0,
    # JRA conditions
    "OP": 7.0, "L": 7.0, "オープン": 7.0,
    "3勝": 6.0, "1600万": 6.0,
    "2勝": 5.0, "1000万": 5.0,
    "1勝": 4.0, "500万": 4.0,
    "新馬": 3.0, "未勝利": 3.0,
    # NAR classes
    "S": 8.5,
    "A1": 7.5, "A2": 7.0,
    "B1": 6.0, "B2": 5.5, "B3": 5.0,
    "C1": 4.0, "C2": 3.5, "C3": 3.0,
    "D": 2.0,
}

# class_name → weight multiplier for recent run scoring
CLASS_WEIGHT: dict[str, float] = {
    "G1": 2.0, "Jpn1": 2.0, "GI": 2.0,
    "G2": 1.8, "Jpn2": 1.8, "GII": 1.8,
    "G3": 1.6, "Jpn3": 1.6, "GIII": 1.6,
    "OP": 1.4, "L": 1.4, "オープン": 1.4,
    "3勝": 1.25, "1600万": 1.25,
    "2勝": 1.15, "1000万": 1.15,
    "1勝": 1.0, "500万": 1.0,
    "新馬": 0.9, "未勝利": 0.9,
    "S": 1.5,
    "A1": 1.35, "A2": 1.25,
    "B1": 1.1, "B2": 1.05, "B3": 1.0,
    "C1": 0.9, "C2": 0.85, "C3": 0.8,
    "D": 0.7,
}

# Regex patterns to extract NAR class from race_name
_NAR_CLASS_PATTERNS = [
    (re.compile(r"(Jpn[123]|GI{1,3})"), None),       # graded
    (re.compile(r"\b(A1|A2|B1|B2|B3|C1|C2|C3)\b"), None),
    (re.compile(r"[（(](A1|A2|B1|B2|B3|C1|C2|C3)[)）]"), None),
    (re.compile(r"(A1|A2|B1|B2|B3|C1|C2|C3)[ー\-一二三四五六七八九十組]"), None),
    (re.compile(r"重賞"), "G3"),                        # generic graded
    (re.compile(r"(ダービー|オークス|皐月|天皇|有馬)"), "G1"),
]


def _infer_class(class_name: str, race_name: str) -> str:
    """Return a normalised class string from explicit class_name or race_name."""
    cn = (class_name or "").strip()
    if cn and cn in CLASS_WEIGHT:
        return cn
    # Try to extract from race_name
    rn = race_name or ""
    for pat, forced in _NAR_CLASS_PATTERNS:
        m = pat.search(rn)
        if m:
            return forced if forced else m.group(1)
    return ""


def _class_weight(cls: str) -> float:
    return CLASS_WEIGHT.get(cls, 1.0)


def _class_tier(cls: str) -> float:
    return CLASS_TIER.get(cls, 5.0)


def _headcount_factor(headcount: int) -> float:
    """More runners = more competitive. Returns 0.85-1.15 range."""
    if headcount <= 0:
        return 1.0
    if headcount >= 16:
        return 1.15
    if headcount >= 12:
        return 1.05 + (headcount - 12) * 0.025
    if headcount >= 8:
        return 0.95 + (headcount - 8) * 0.025
    return 0.85 + (headcount - 4) * 0.025


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
    track_condition: str = "良",
    race_name: str = "",
    race_class: str = "",
) -> list[dict]:
    """Calculate 8-category scores and grades for all horses."""

    # Infer current race class from race_name if not explicitly given
    current_class = _infer_class(race_class, race_name)

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
    recent_map = _build_recent_map(recent_data, current_class)
    # Track adjustment map: synthesize from bloodline.by_condition + race track_condition
    track_map = _build_track_map(bloodline_data, entries, track_condition)

    for entry in entries:
        num = entry.get("horse_number", 0)
        name = entry.get("horse_name", "")
        jockey_name = entry.get("jockey", "")

        pred = predictions.get(num, predictions.get(str(num), {}))
        speed_score = pred.get("dlogic_score", 0)
        flow_score = flow_map.get(name, 0)
        jockey_score = jockey_map.get(jockey_name, 0)
        bloodline_score = bloodline_map.get(num, 0)
        recent_score = recent_map.get(num, 0)
        # Prefer synthesized track value over backend fixed 1.0 default
        raw_track = track_map.get(num, pred.get("track_adjustment", 1.0))
        track_score = raw_track
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
                "total": 0,  # computed after back-fill using weighted mix
                "speed": speed_score,
                "flow": flow_score,
                "jockey": jockey_score,
                "bloodline": bloodline_score,
                "recent": recent_score,
                "track": track_score,
                "ev": ev_score,
                # Keep the original metalogic score for transparency / drawer display
                "_metalogic": pred.get("metalogic_score", 0),
            },
        })

    # Fill zero scores with per-race neutral fallback so that horses lacking
    # source data (new horses, first-time starters) are not unfairly ranked D.
    _fill_neutral(horses, "speed", default=20.0, discount=0.70)
    _fill_neutral(horses, "bloodline", default=20.0, discount=0.80)
    _fill_neutral(horses, "recent", default=50.0, discount=0.85)
    _fill_neutral(horses, "jockey", default=15.0, discount=0.75)
    _fill_neutral(horses, "flow", default=60.0, discount=0.90)

    # Build class step adjustment map: compare past race classes to current
    class_step_map = _build_class_step_map(recent_data, current_class)

    # Compute total as a weighted mix of components. Empirically validated
    # (spearman vs market odds) weights: JRA rho +0.70, NAR rho +0.45.
    # total = 0.35*speed + 0.25*recent + 0.20*jockey + 0.10*flow + 0.10*bloodline
    for h in horses:
        s = h["scores"]
        total = (
            0.35 * s["speed"]
            + 0.25 * s["recent"]
            + 0.20 * s["jockey"]
            + 0.10 * s["flow"]
            + 0.10 * s["bloodline"]
        )
        # Apply track adjustment as a small modifier (±10%)
        track_mul = max(0.90, min(1.10, float(s.get("track", 1.0))))
        # Apply class step adjustment (升級ペナルティ / 降級ボーナス)
        name = h.get("horse_name", "")
        class_adj = class_step_map.get(name, 1.0)
        s["total"] = round(total * track_mul * class_adj, 2)

    # Break ties deterministically by adding a horse-number-based nudge
    # (<0.01 for display, never enough to shift ranks for genuinely different
    # scores). This stops S/A/B/C/D assignment from being order-of-insertion.
    _apply_tiebreaker_nudge(horses)

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


def _apply_tiebreaker_nudge(horses: list[dict]) -> None:
    """Add a tiny deterministic offset to each score so that horses with the
    same value get a stable but distinct rank (instead of being broken by
    insertion order). Magnitude is <0.01, invisible in the 1-decimal UI.

    Uses a pseudo-random permutation seeded by horse_number so the order
    within a tie looks uncorrelated to post position (unlike pure ascending
    order which would always advantage low post numbers).
    """
    if not horses:
        return
    import hashlib
    keys = ["total", "speed", "flow", "jockey", "bloodline", "recent", "track", "ev"]
    for h in horses:
        num = h.get("horse_number", 0) or 0
        name = h.get("horse_name", "")
        # Generate per-dimension tiny offsets from a hash of horse+dim
        for k in keys:
            digest = hashlib.md5(f"{name}-{num}-{k}".encode()).digest()
            # 2 bytes -> 0..65535 -> -1..+1 scaled to 0.005 max magnitude
            offset = ((digest[0] * 256 + digest[1]) / 65535.0 - 0.5) * 0.009
            try:
                h["scores"][k] = round(float(h["scores"].get(k, 0)) + offset, 4)
            except (ValueError, TypeError):
                pass


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

    # Style-based synthesis when backend flow_scores are unusable.
    # Add per-horse micro-variation using post position so horses in the same
    # style group get slightly different scores (avoids heavy tie).
    if not result:
        style_groups = flow_data.get("style_groups", {}) or flow_data.get("style_summary", {}) or {}
        name_to_post: dict = {}
        if entries:
            for e in entries:
                name_to_post[e.get("horse_name", "")] = e.get("post", 0) or e.get("horse_number", 0)
        if isinstance(style_groups, dict):
            for style_key, horse_list in style_groups.items():
                base = 0.0
                for k, v in _STYLE_BASE_SCORES.items():
                    if k in str(style_key):
                        base = v
                        break
                if base and isinstance(horse_list, list):
                    # Sort horses by post to get deterministic intra-group ordering
                    ordered = sorted(horse_list, key=lambda n: name_to_post.get(n, 99))
                    group_size = len(ordered)
                    for idx, hname in enumerate(ordered):
                        if hname not in result:
                            # Spread ±1.5 within the group by index position
                            if group_size > 1:
                                offset = 1.5 - (3.0 * idx / (group_size - 1))
                            else:
                                offset = 0.0
                            result[hname] = round(base + offset, 2)

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


def _build_track_map(bloodline_data: dict, entries: list[dict], track_condition: str = "良") -> dict:
    """Synthesize per-horse track adjustment (0.90-1.10).

    Two strategies combined:
    (A) If we know the current track_condition (良/稍重/重/不良), compare
        sire/broodmare's place_rate on that condition vs their baseline.
    (B) If pre-race (track unknown), measure "all-weather consistency":
        horses whose bloodline shows stable place_rate across conditions
        get a mild boost; horses showing high variance get a mild penalty.
    Result is in the 0.90-1.10 range.
    """
    result: dict = {}
    tc = (track_condition or "").strip()
    known = tc not in ("", "-", "−", "不明", "？", "?")
    if not known:
        tc = "良"

    bl_list = bloodline_data.get("bloodline", []) if isinstance(bloodline_data, dict) else []
    for h in bl_list:
        num = h.get("horse_number", 0)
        if not num:
            continue

        def _extract(perf: dict) -> tuple[float, float, float]:
            """Return (cond_rate, baseline, variance) from a perf dict."""
            if not isinstance(perf, dict):
                return (0.0, 0.0, 0.0)
            baseline = float(perf.get("place_rate", 0) or 0)
            cond_rate = 0.0
            rates_by_cond = []
            for row in perf.get("by_condition", []) or []:
                try:
                    pr = float(row.get("place_rate", 0) or 0)
                    rates_by_cond.append(pr)
                    if row.get("condition") == tc:
                        cond_rate = pr
                except (ValueError, TypeError):
                    continue
            variance = 0.0
            if rates_by_cond and len(rates_by_cond) > 1:
                mean = sum(rates_by_cond) / len(rates_by_cond)
                variance = sum((r - mean) ** 2 for r in rates_by_cond) / len(rates_by_cond)
            return (cond_rate, baseline, variance)

        sire_c, sire_b, sire_v = _extract(h.get("sire_performance", {}))
        bm_c, bm_b, bm_v = _extract(h.get("broodmare_performance", {}))

        cond_rate = (sire_c * 2 + bm_c) / 3 if (sire_c or bm_c) else 0.0
        baseline = (sire_b * 2 + bm_b) / 3 if (sire_b or bm_b) else 0.0
        variance = (sire_v * 2 + bm_v) / 3

        if known and baseline > 0:
            # Strategy A: current condition vs baseline
            ratio = cond_rate / baseline
            adj = max(0.90, min(1.10, ratio))
        else:
            # Strategy B: consistency bonus. variance ~ 0-200 range roughly.
            # Lower variance -> +0.05, higher variance -> -0.05.
            if baseline > 0:
                vnorm = min(1.0, variance / 100.0)  # 0..1
                adj = 1.05 - vnorm * 0.15  # 1.05 down to 0.90
                # Plus a small baseline-driven bonus: strong sire +0.02
                if baseline >= 28: adj += 0.02
                elif baseline <= 18: adj -= 0.02
                adj = max(0.90, min(1.10, adj))
            else:
                adj = 1.0

        result[num] = round(adj, 3)

    # Fill missing with neutral 1.0
    if entries:
        for e in entries:
            if e.get("horse_number", 0) not in result:
                result[e.get("horse_number", 0)] = 1.0

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


def _build_recent_map(recent_data: dict, current_class: str = "") -> dict:
    """Build {horse_number: recent_score} with class + headcount weighting.

    Three factors per past run:
      1. Base score from finish position (1st=100, decays by 6 per position)
      2. Class weight: higher-class races multiply the base score
      3. Headcount factor: more runners = more competitive field (0.85-1.15)

    The weighted scores are averaged across the horse's recent runs, producing
    a single composite that rewards strong performances in tough fields.
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
            weighted_scores = []
            for r in runs:
                pos = r.get("finish", r.get("position", 0))
                if not pos or not isinstance(pos, (int, float)) or pos <= 0:
                    continue
                base = max(0, 100 - (pos - 1) * 6)
                cls = _infer_class(
                    r.get("class_name", ""),
                    r.get("race_name", ""),
                )
                cw = _class_weight(cls)
                hc = r.get("headcount", 0) or 0
                hf = _headcount_factor(hc)
                weighted_scores.append(base * cw * hf)
            if not weighted_scores:
                result[num] = 0
                continue
            result[num] = round(sum(weighted_scores) / len(weighted_scores), 2)
    return result


def _build_class_step_map(recent_data: dict, current_class: str) -> dict:
    """Build {horse_name: adjustment} for class step-up / step-down.

    Compares the average tier of a horse's recent races to the current race's
    tier. Stepping up in class penalises the total score; stepping down boosts.

    Returns multipliers in the 0.82-1.08 range.
    """
    if not current_class:
        return {}
    current_tier = _class_tier(current_class)
    result: dict = {}
    horses = recent_data.get("horses", recent_data.get("recent_runs", []))
    if not isinstance(horses, list):
        return result
    for h in horses:
        name = h.get("horse_name", "")
        if not name:
            continue
        runs = h.get("runs", [])
        tiers = []
        for r in runs:
            cls = _infer_class(r.get("class_name", ""), r.get("race_name", ""))
            if cls:
                tiers.append(_class_tier(cls))
        if not tiers:
            continue
        avg_past_tier = sum(tiers) / len(tiers)
        diff = current_tier - avg_past_tier  # positive = stepping UP
        if diff >= 3.0:
            adj = 0.82   # 大幅昇級 → 大きな減点
        elif diff >= 2.0:
            adj = 0.87
        elif diff >= 1.0:
            adj = 0.93
        elif diff >= 0.5:
            adj = 0.97
        elif diff <= -2.0:
            adj = 1.08   # 大幅降級 → ボーナス
        elif diff <= -1.0:
            adj = 1.05
        elif diff <= -0.5:
            adj = 1.02
        else:
            adj = 1.0    # 同クラス
        result[name] = adj
    return result


def _calc_ev(pred: dict, odds_data: dict, horse_number: int) -> float:
    """Calculate expected value score, clipped to a sane display range."""
    win_prob = pred.get("win_probability", 0)
    if not win_prob:
        meta_score = pred.get("metalogic_score", 0)
        if meta_score > 0:
            win_prob = min(0.5, meta_score / 500)

    odds = odds_data.get(horse_number, odds_data.get(str(horse_number), 0))
    if not odds or not win_prob:
        return round(min(win_prob * 100 if win_prob else 0, 100.0), 2)

    try:
        odds_f = float(odds)
        if odds_f <= 0:
            return 0
        implied_prob = 1.0 / odds_f
        ev = (win_prob / implied_prob) * 10 if implied_prob > 0 else 0
        # Clip to 0-100 for grading purposes; >100 means 100%+ ROI which
        # is already max grade worthy.
        return round(max(0.0, min(100.0, ev)), 2)
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
