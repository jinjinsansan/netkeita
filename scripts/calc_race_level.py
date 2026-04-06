#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JRA + NAR レースレベル自前計算スクリプト

PC-KEIBA PostgreSQL から全レースの「勝ち上がり頭数/複勝頭数」を計算し、
S/A/B/C/D ランクを付与して Redis + JSON に保存する。

勝ち上がり: 当該レース以降の全レースで1着を取った馬の数
複勝:       当該レース以降の次走で3着以内に入った馬の数

※ NAR (地方競馬) は PC-KEIBA の venue code がでたらめなため、
   スケジュールマスター + 重賞辞書 + テキストパターンで会場補正する。

Usage:
    python scripts/calc_race_level.py
"""

import sys
import io
import json
import time
import logging
import os
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent

import psycopg2

DB_PARAMS = {
    "host": os.environ.get("PCKEIBA_HOST", "127.0.0.1"),
    "port": os.environ.get("PCKEIBA_PORT", "5432"),
    "database": os.environ.get("PCKEIBA_DB", "pckeiba"),
    "user": os.environ.get("PCKEIBA_USER", "postgres"),
    "password": os.environ.get("PCKEIBA_PASSWORD", "postgres"),
}

# ── JRA 会場コード ──
JRA_CODES = {'01', '02', '03', '04', '05', '06', '07', '08', '09', '10'}
JRA_MAP = {
    '01': '札幌', '02': '函館', '03': '福島', '04': '新潟',
    '05': '東京', '06': '中山', '07': '中京', '08': '京都',
    '09': '阪神', '10': '小倉',
}

# ── NAR 会場コード ──
NAR_CODES = {
    '83': '帯広', '30': '門別', '35': '盛岡', '36': '水沢',
    '45': '浦和', '43': '船橋', '42': '大井', '44': '川崎',
    '46': '金沢', '47': '笠松', '48': '名古屋',
    '50': '園田', '51': '姫路', '54': '高知', '55': '佐賀',
}
NANKAN_CODES = {'42', '43', '44', '45'}

# 全会場 (JRA + NAR)
ALL_VENUE_MAP = {**JRA_MAP, **NAR_CODES}

# NAR 公式重賞レース辞書
FIXED_GRADED_RACES = {
    '東京大賞典': '42', '帝王賞': '42', '大井記念': '42',
    'ジャパンダートダービー': '42', '羽田盃': '42',
    'アフター５スター賞': '42', '東京スプリント': '42',
    'レディスプレリュード': '42', 'ゴールドジュニア': '42',
    '京浜盃': '42', '東京2歳優駿牝馬': '42', 'ハイセイコー記念': '42',
    '川崎記念': '44', 'スパーキングレディーカップ': '44',
    'エンプレス杯': '44', 'ローレル賞': '44', '戸塚記念': '44',
    '関東オークス': '44', '全日本2歳優駿': '44',
    'かしわ記念': '43', '日本テレビ盃': '43', 'クイーン賞': '43',
    'マリーンカップ': '43', '京成盃グランドマイラーズ': '43',
    'ダイオライト記念': '43',
    '浦和記念': '45', 'さきたま杯': '45', 'しらさぎ賞': '45',
    'テレ玉杯オーバルスプリント': '45',
    'マイルチャンピオンシップ南部杯': '35', 'クラスターカップ': '35',
    '白山大賞典': '46',
    '全日本サラブレッドカップ': '47',
    '名古屋大賞典': '48', '名古屋グランプリ': '48', 'かきつばた記念': '48',
    '園田金盃': '50', '兵庫ゴールドトロフィー': '50',
    '黒船賞': '54',
    '佐賀記念': '55',
}

VENUE_TEXT_PATTERNS = {
    '東京': '42', '大井': '42', 'TCK': '42',
    '川崎': '44', 'スパーキング': '44',
    '船橋': '43', 'マリーン': '43',
    '浦和': '45', 'さきたま': '45',
    '盛岡': '35', '南部杯': '35',
    '水沢': '36',
    '金沢': '46',
    '笠松': '47',
    '名古屋': '48',
    '園田': '50',
    '姫路': '51',
    '高知': '54', '黒船': '54',
    '佐賀': '55',
    '帯広': '83', 'ばんえい': '83',
    '門別': '30',
}

# スケジュールマスターファイル候補
SCHEDULE_MASTER_PATHS = [
    SCRIPT_DIR / '..' / '..' / 'chatbot' / 'uma' / 'data' / 'nar_schedule_master_2020_2026.json',
    Path(r'E:\dev\Cusor\chatbot\uma\data\nar_schedule_master_2020_2026.json'),
    Path('/opt/dlogic/data/nar_schedule_master_2020_2026.json'),
]

YEARS_BACK = 3

OUTPUT_DIR = SCRIPT_DIR
REDIS_HOST = os.environ.get("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_DB = 3
REDIS_PREFIX = "nk:racelevel"
REDIS_TTL = 86400 * 365


def calculate_level(win_rate: float, place_rate: float) -> str:
    composite = win_rate * 0.4 + place_rate * 0.6
    if composite >= 35:
        return "S"
    elif composite >= 22:
        return "A"
    elif composite >= 12:
        return "B"
    elif composite >= 5:
        return "C"
    else:
        return "D"


def load_schedule_master() -> dict | None:
    for p in SCHEDULE_MASTER_PATHS:
        try:
            resolved = p.resolve()
            if resolved.exists():
                with open(resolved, "r", encoding="utf-8") as f:
                    data = json.load(f)
                logger.info(f"  スケジュールマスター読み込み: {resolved.name}")
                return data
        except Exception:
            continue
    logger.warning("  スケジュールマスターが見つかりません")
    return None


REGION_GROUPS = [
    {'35', '36'},
    {'46', '47', '48'},
    {'50', '51'},
    {'54', '55'},
    {'30', '83'},
]


def correct_nar_venue(nen: str, tsukihi: str, original_code: str,
                      race_name: str, schedule_master: dict | None) -> tuple[str, str]:
    """NAR 会場補正。返り値: (補正後コード, 会場名)"""
    race_date = f"{nen}{tsukihi}"

    # 1. 公式重賞レース辞書
    if race_name:
        for graded_name, venue_code in FIXED_GRADED_RACES.items():
            if graded_name in race_name:
                return venue_code, NAR_CODES.get(venue_code, '?')

    # 2. スケジュールマスター
    if schedule_master and 'schedule_data' in schedule_master:
        day_venues = schedule_master['schedule_data'].get(race_date, [])
        if day_venues:
            if len(day_venues) == 1:
                code = day_venues[0]
                return code, NAR_CODES.get(code, '?')

            if original_code in day_venues:
                return original_code, NAR_CODES.get(original_code, '?')

            if original_code in NANKAN_CODES:
                nankan_on_day = [c for c in day_venues if c in NANKAN_CODES]
                if len(nankan_on_day) == 1:
                    code = nankan_on_day[0]
                    return code, NAR_CODES.get(code, '?')

            for group in REGION_GROUPS:
                if original_code in group:
                    candidates = [c for c in day_venues if c in group]
                    if len(candidates) == 1:
                        return candidates[0], NAR_CODES.get(candidates[0], '?')
                    break

            if race_name:
                for pattern, code in VENUE_TEXT_PATTERNS.items():
                    if pattern in race_name and code in day_venues:
                        return code, NAR_CODES.get(code, '?')

    # 3. テキストパターン
    if race_name:
        for pattern, code in VENUE_TEXT_PATTERNS.items():
            if pattern in race_name:
                return code, NAR_CODES.get(code, '?')

    # 4. 元コード
    return original_code, NAR_CODES.get(original_code, f'不明({original_code})')


def calc_race_levels(cur, venue_codes: set, venue_map: dict,
                     start_year: str, end_year: str,
                     label: str, schedule_master: dict | None = None) -> dict:
    """指定した会場コード群のレースレベルを計算して返す。"""

    codes_tuple = tuple(sorted(venue_codes))

    # Step 1: レース一覧
    logger.info(f"\n  [{label}] レース一覧を取得...")
    cur.execute("""
        SELECT ra.kaisai_nen, ra.kaisai_tsukihi, ra.keibajo_code,
               ra.race_bango, TRIM(ra.kyosomei_hondai) as race_name
        FROM jvd_ra ra
        WHERE ra.keibajo_code IN %s
          AND ra.kaisai_nen BETWEEN %s AND %s
        ORDER BY ra.kaisai_nen DESC, ra.kaisai_tsukihi DESC, ra.keibajo_code, ra.race_bango
    """, (codes_tuple, start_year, end_year))
    races = cur.fetchall()
    logger.info(f"  {len(races):,} レース")

    # Step 2: 出走馬データ
    logger.info(f"  [{label}] 出走馬データを取得...")
    cur.execute("""
        SELECT se.kaisai_nen, se.kaisai_tsukihi, se.keibajo_code,
               se.race_bango, se.ketto_toroku_bango, se.kakutei_chakujun
        FROM jvd_se se
        WHERE se.keibajo_code IN %s
          AND se.kaisai_nen BETWEEN %s AND %s
          AND se.ketto_toroku_bango != '0000000000'
          AND se.bamei IS NOT NULL AND se.bamei != ''
          AND se.kakutei_chakujun IS NOT NULL AND se.kakutei_chakujun != ''
        ORDER BY se.kaisai_nen, se.kaisai_tsukihi
    """, (codes_tuple, start_year, end_year))
    all_entries = cur.fetchall()
    logger.info(f"  {len(all_entries):,} 出走レコード")

    # Step 3: メモリマップ構築
    horse_results: dict[str, list[tuple[str, str, int]]] = defaultdict(list)
    race_horses: dict[str, list[str]] = defaultdict(list)

    for row in all_entries:
        nen, tsukihi, keibajo, race_ban, ketto_id, chakujun_str = row
        try:
            chakujun = int(chakujun_str)
            if chakujun <= 0:
                continue
        except (ValueError, TypeError):
            continue
        horse_results[ketto_id].append((nen, tsukihi, chakujun))
        race_key = f"{nen}{tsukihi}_{keibajo}_{race_ban}"
        race_horses[race_key].append(ketto_id)

    for ketto_id in horse_results:
        horse_results[ketto_id].sort()

    logger.info(f"  {len(horse_results):,} 頭, {len(race_horses):,} レース")

    # Step 4: 計算
    logger.info(f"  [{label}] レースレベル計算中...")
    race_levels = {}
    is_nar = schedule_master is not None
    t0 = time.time()

    for i, (nen, tsukihi, keibajo, race_ban, race_name) in enumerate(races):
        race_key = f"{nen}{tsukihi}_{keibajo}_{race_ban}"
        horses_in_race = race_horses.get(race_key, [])
        total = len(horses_in_race)
        if total == 0:
            continue

        win_count = 0
        place_count = 0

        for ketto_id in horses_in_race:
            runs = horse_results.get(ketto_id, [])
            found_idx = -1
            for idx, (r_nen, r_tsukihi, r_chaku) in enumerate(runs):
                if r_nen == nen and r_tsukihi == tsukihi:
                    found_idx = idx
                    break
            if found_idx < 0:
                continue

            has_won = False
            for subsequent in runs[found_idx + 1:]:
                if subsequent[2] == 1:
                    has_won = True
                    break

            has_placed_next = False
            if found_idx + 1 < len(runs):
                if runs[found_idx + 1][2] <= 3:
                    has_placed_next = True

            if has_won:
                win_count += 1
            if has_placed_next:
                place_count += 1

        win_rate = round(win_count / total * 100, 1) if total > 0 else 0
        place_rate = round(place_count / total * 100, 1) if total > 0 else 0
        level = calculate_level(win_rate, place_rate)

        # 会場名解決
        if is_nar:
            race_name_stripped = race_name.strip() if race_name else ""
            _, venue_name = correct_nar_venue(nen, tsukihi, keibajo, race_name_stripped, schedule_master)
        else:
            venue_name = venue_map.get(keibajo, keibajo)

        race_name_trimmed = race_name.strip() if race_name else ""

        redis_key = f"{nen}{tsukihi}_{venue_name}_{race_ban}"
        name_key = f"{nen}{tsukihi}_{venue_name}_{race_name_trimmed}" if race_name_trimmed else ""

        entry = {
            "date": f"{nen}/{tsukihi[:2]}/{tsukihi[2:]}",
            "venue": venue_name,
            "race_name": race_name_trimmed,
            "race_number": race_ban,
            "win_count": win_count,
            "win_total": total,
            "place_count": place_count,
            "place_total": total,
            "win_rate": win_rate,
            "place_rate": place_rate,
            "level": level,
        }

        race_levels[redis_key] = entry
        if name_key and name_key != redis_key:
            race_levels[name_key] = entry

        if (i + 1) % 5000 == 0:
            elapsed = time.time() - t0
            logger.info(f"    {i + 1:,}/{len(races):,} ({elapsed:.1f}s)")

    elapsed = time.time() - t0
    logger.info(f"  完了: {len(race_levels):,} エントリ ({elapsed:.1f}s)")

    # レベル分布
    level_dist: dict[str, int] = defaultdict(int)
    seen: set[str] = set()
    for key, entry in race_levels.items():
        uid = f"{entry['date']}_{entry['venue']}_{entry['race_number']}"
        if uid not in seen:
            seen.add(uid)
            level_dist[entry["level"]] += 1
    logger.info(f"  [{label}] レベル分布:")
    for lv in ["S", "A", "B", "C", "D"]:
        cnt = level_dist.get(lv, 0)
        pct = cnt / len(seen) * 100 if seen else 0
        logger.info(f"    {lv}: {cnt:,} ({pct:.1f}%)")

    return race_levels


def main():
    logger.info("=" * 60)
    logger.info("JRA + NAR レースレベル自前計算")
    logger.info("=" * 60)

    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    logger.info("PostgreSQL 接続成功")

    today = datetime.now()
    start_year = str(today.year - YEARS_BACK)
    end_year = str(today.year)
    logger.info(f"対象年: {start_year}〜{end_year}")

    # NAR スケジュールマスター読み込み
    schedule_master = load_schedule_master()

    # ── JRA ──
    jra_levels = calc_race_levels(cur, JRA_CODES, JRA_MAP, start_year, end_year, "JRA")

    # ── NAR ──
    nar_venue_codes = set(NAR_CODES.keys())
    nar_levels = calc_race_levels(cur, nar_venue_codes, NAR_CODES, start_year, end_year, "NAR", schedule_master)

    # ── 統合 ──
    all_levels = {**jra_levels, **nar_levels}
    logger.info(f"\n統合: {len(all_levels):,} エントリ (JRA {len(jra_levels):,} + NAR {len(nar_levels):,})")

    # ── JSON 保存 ──
    date_str = today.strftime("%Y%m%d")
    output_file = OUTPUT_DIR / f"race_level_{date_str}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_levels, f, ensure_ascii=False)
    size_mb = output_file.stat().st_size / 1024 / 1024
    logger.info(f"\nJSON 出力: {output_file.name} ({size_mb:.1f}MB)")

    # ── Redis 保存 ──
    try:
        import redis
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
        pipe = r.pipeline(transaction=False)
        for key, data in all_levels.items():
            pipe.set(f"{REDIS_PREFIX}:{key}", json.dumps(data, ensure_ascii=False), ex=REDIS_TTL)
        pipe.execute()
        logger.info(f"Redis 保存: {len(all_levels):,} エントリ")
    except ImportError:
        logger.warning("redis パッケージ未インストール")
    except Exception as e:
        logger.error(f"Redis 保存失敗: {e}")

    cur.close()
    conn.close()
    logger.info("\n完了")


if __name__ == "__main__":
    main()
