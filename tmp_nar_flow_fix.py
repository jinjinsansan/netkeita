"""Replacement for _calculate_flow_matching in LocalViewLogicEngineV2.

Produces 40-85 range flow_scores compatible with JRA format, using CORNER
position data instead of 3F times (which are often '000' in NAR records).
"""
# This is just a reference code; the actual patch will be applied to
# /opt/dlogic/backend/services/local_viewlogic_engine_v2.py

def _calculate_flow_matching_nar(self, horses_data, pace_prediction):
    """NAR-specific展開適性マッチング using corner positions."""
    from statistics import mean

    flow_scores = {}
    pace = pace_prediction.get('calculation_pace', pace_prediction.get('pace', 'ミドルペース'))

    def _style_index_from_corners(races):
        """Return style index in -5..+5 range.
        Negative = front-runner (逃げ/先行), positive = closer (差し/追込)
        """
        diffs = []
        for race in races[:5]:
            c1_raw = race.get('CORNER1_JUNI') or race.get('CORNER2_JUNI')
            c4_raw = race.get('CORNER4_JUNI')
            try:
                c1 = int(c1_raw) if c1_raw else None
                c4 = int(c4_raw) if c4_raw else None
            except (ValueError, TypeError):
                continue
            if not c1 or not c4:
                continue
            # Position 1-2 = leader, 3-5 = stalker, 6-10 = mid, 10+ = closer
            # style = average position shift from corner1 to corner4
            # A frontrunner stays low (index < 0), a closer moves up (index > 0)
            if c1 <= 2:
                s = -4
            elif c1 <= 4:
                s = -2
            elif c1 <= 7:
                s = 0
            elif c1 <= 10:
                s = 2
            else:
                s = 4
            # Slight correction from how they moved to corner4
            if c4 < c1 - 2:  # moved up strongly
                s += 1
            elif c4 > c1 + 2:  # dropped back
                s -= 1
            diffs.append(max(-5, min(5, s)))
        return mean(diffs) if diffs else 0

    for horse in horses_data:
        horse_name = horse.get('horse_name', '不明')
        if 'races' not in horse or not horse['races']:
            flow_scores[horse_name] = 50.0
            continue

        style_index = _style_index_from_corners(horse['races'])
        base = 60.0
        if 'ハイペース' in pace:
            if style_index > 0:
                score = base * (1.2 + style_index * 0.04)
            else:
                score = base * (0.85 + style_index * 0.03)
        elif 'スロー' in pace:
            if style_index < 0:
                score = base * (1.15 - style_index * 0.03)
            else:
                score = base * (0.9 - style_index * 0.02)
        else:
            adjustment = (5 - abs(style_index)) * 3 + style_index * 0.5
            score = base + adjustment

        flow_scores[horse_name] = min(85, max(40, score))

    return flow_scores
