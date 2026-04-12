"""Patch: Add /full-scores endpoint to predictions.py on VPS"""
import sys

filepath = "/opt/dlogic/backend/api/v2/predictions.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add FullScoresResponse model after NewspaperPredictionResponse
model_addition = '''

class FullScoresRequest(BaseModel):
    race_id: str
    horses: List[str]
    horse_numbers: List[int]
    venue: Optional[str] = None
    race_number: Optional[int] = None
    jockeys: Optional[List[str]] = None
    posts: Optional[List[int]] = None
    distance: Optional[str] = None
    track_condition: Optional[str] = None
    odds: Optional[List[float]] = None


class HorseFullScore(BaseModel):
    horse_number: int
    horse_name: str
    dlogic_score: float = 0
    ilogic_score: float = 0
    viewlogic_score: float = 0
    metalogic_score: float = 0
    track_adjustment: float = 1.0


class FullScoresResponse(BaseModel):
    race_id: str
    horses: List[HorseFullScore]
    track_adjusted: bool = False
'''

# Insert after the NewspaperPredictionResponse class
marker = "class NewspaperPredictionResponse(BaseModel):\n    race_id: str\n    dlogic: List[int]\n    ilogic: List[int]\n    viewlogic: List[int]\n    metalogic: List[int]\n    track_adjusted: bool = False"
if marker not in content:
    print("ERROR: Could not find NewspaperPredictionResponse marker")
    sys.exit(1)

content = content.replace(marker, marker + model_addition)

# 2. Add /full-scores endpoint at the end of the file
endpoint_code = '''

@router.post("/full-scores", response_model=FullScoresResponse)
async def get_full_scores(request: FullScoresRequest):
    """
    netkeita用: 全馬の全エンジンスコア + 馬場補正係数を一括返却
    """
    horses = request.horses
    horse_numbers = request.horse_numbers
    jockeys = request.jockeys or []
    posts = request.posts or []
    odds = request.odds or [0.0] * len(horses)
    venue = request.venue or ""
    distance = request.distance or ""
    track_condition = request.track_condition or "良"

    context = {
        "venue": venue,
        "distance": distance,
        "track_type": "芝" if "芝" in (distance or "") else "ダート",
        "track_condition": track_condition,
    }

    d_scores: Dict[str, float] = {}
    i_scores: Dict[str, float] = {}
    v_scores: Dict[str, float] = {}
    track_adjusted = False

    try:
        from services.metalogic_engine import MetaLogicEngine
        engine = MetaLogicEngine()

        try:
            d_scores = await engine.calculate_dlogic_scores(horses, context)
        except Exception as e:
            logger.warning(f"D-Logic計算失敗 ({request.race_id}): {e}")

        try:
            i_scores = engine.calculate_ilogic_scores(horses, jockeys, posts, context)
        except Exception as e:
            logger.warning(f"I-Logic計算失敗 ({request.race_id}): {e}")

        try:
            v_scores = engine.calculate_viewlogic_scores(horses, jockeys, posts, context)
        except Exception as e:
            logger.warning(f"ViewLogic計算失敗 ({request.race_id}): {e}")

        # 馬場補正 (良馬場以外)
        if track_condition != "良":
            d_scores = _apply_track_adjustment(d_scores, horses, track_condition, venue)
            i_scores = _apply_track_adjustment(i_scores, horses, track_condition, venue)
            v_scores = _apply_track_adjustment(v_scores, horses, track_condition, venue)
            track_adjusted = True

        # MetaLogic (全馬)
        meta_scores_map: Dict[str, float] = {}
        try:
            meta_results = engine.calculate_meta_scores(
                d_scores, i_scores, v_scores, odds, horses,
            )
            for horse_name, score, _ in meta_results:
                meta_scores_map[horse_name] = score
        except Exception as e:
            logger.warning(f"MetaLogic計算失敗 ({request.race_id}): {e}")

        # 馬場補正係数を個別に算出
        baba = BABA_CODE_MAP_INV.get(track_condition, 1)

    except Exception as e:
        logger.error(f"エンジン初期化失敗 ({request.race_id}): {e}")
        baba = 1

    # 全馬のスコアを構築
    result_horses = []
    for i, (name, num) in enumerate(zip(horses, horse_numbers)):
        factor = 1.0
        if baba > 1:
            try:
                factor = _get_track_adjustment_factor(name, baba, venue)
            except Exception:
                factor = 1.0

        result_horses.append(HorseFullScore(
            horse_number=num,
            horse_name=name,
            dlogic_score=round(d_scores.get(name, 0), 1),
            ilogic_score=round(i_scores.get(name, 0), 1),
            viewlogic_score=round(v_scores.get(name, 0), 1),
            metalogic_score=round(meta_scores_map.get(name, 0), 1),
            track_adjustment=round(factor, 3),
        ))

    return FullScoresResponse(
        race_id=request.race_id,
        horses=result_horses,
        track_adjusted=track_adjusted,
    )
'''

content = content.rstrip() + "\n" + endpoint_code + "\n"

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("OK: /full-scores endpoint added to predictions.py")
