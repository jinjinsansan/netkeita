#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JRA レースレベル自前計算スクリプト

PC-KEIBA PostgreSQL から全JRAレースの「勝ち上がり頭数/複勝頭数」を計算し、
S/A/B/C/D ランクを付与して Redis + JSON に保存する。

勝ち上がり: 当該レース以降の全レースで1着を取った馬の数
複勝:       当該レース以降の次走で3着以内に入った馬の数

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

# ── DB設定 ──
import psycopg2

DB_PARAMS = {
    "host": os.environ.get("PCKEIBA_HOST", "127.0.0.1"),
    "port": os.environ.get("PCKEIBA_PORT", "5432"),
    "database": os.environ.get("PCKEIBA_DB", "pckeiba"),
    "user": os.environ.get("PCKEIBA_USER", "postgres"),
    "password": os.environ.get("PCKEIBA_PASSWORD", "postgres"),
}

KEIBAJO_MAP = {
    '01': '札幌', '02': '函館', '03': '福島', '04': '新潟',
    '05': '東京', '06': '中山', '07': '中京', '08': '京都',
    '09': '阪神', '10': '小倉',
}

# 計算対象年数
YEARS_BACK = 3

# 出力
OUTPUT_DIR = SCRIPT_DIR
REDIS_HOST = os.environ.get("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_DB = 3
REDIS_PREFIX = "nk:racelevel"
REDIS_TTL = 86400 * 365


def calculate_level(win_rate: float, place_rate: float) -> str:
    """勝ち上がり率と複勝率からレースレベルを算出。
    composite = win_rate * 0.4 + place_rate * 0.6

    | Level | composite | 割合   | イメージ                 |
    |-------|-----------|--------|--------------------------|
    | S     | >= 35     | ~15%   | G1〜重賞クラスハイレベル  |
    | A     | >= 22     | ~30%   | 重賞〜OP クラス           |
    | B     | >= 12     | ~33%   | 条件戦で平均的            |
    | C     | >=  5     | ~14%   | やや低い                  |
    | D     | <   5     | ~ 7%   | 低レベル戦                |
    """
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


def main():
    logger.info("=" * 60)
    logger.info("JRA レースレベル自前計算")
    logger.info("=" * 60)

    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    logger.info("PostgreSQL 接続成功")

    today = datetime.now()
    start_year = str(today.year - YEARS_BACK)
    end_year = str(today.year)
    logger.info(f"対象年: {start_year}〜{end_year}")

    # ── Step 1: 全 JRA レースを取得 ──
    logger.info("\nStep 1: JRA レース一覧を取得...")
    cur.execute("""
        SELECT ra.kaisai_nen, ra.kaisai_tsukihi, ra.keibajo_code,
               ra.race_bango, TRIM(ra.kyosomei_hondai) as race_name
        FROM jvd_ra ra
        WHERE ra.keibajo_code IN ('01','02','03','04','05','06','07','08','09','10')
          AND ra.kaisai_nen BETWEEN %s AND %s
        ORDER BY ra.kaisai_nen DESC, ra.kaisai_tsukihi DESC, ra.keibajo_code, ra.race_bango
    """, (start_year, end_year))
    races = cur.fetchall()
    logger.info(f"  {len(races):,} レース")

    # ── Step 2: 各レースの出走馬の ketto_toroku_bango を取得 ──
    logger.info("\nStep 2: 全出走馬データを取得...")
    cur.execute("""
        SELECT se.kaisai_nen, se.kaisai_tsukihi, se.keibajo_code,
               se.race_bango, se.ketto_toroku_bango, se.kakutei_chakujun
        FROM jvd_se se
        WHERE se.keibajo_code IN ('01','02','03','04','05','06','07','08','09','10')
          AND se.kaisai_nen BETWEEN %s AND %s
          AND se.ketto_toroku_bango != '0000000000'
          AND se.bamei IS NOT NULL AND se.bamei != ''
          AND se.kakutei_chakujun IS NOT NULL AND se.kakutei_chakujun != ''
        ORDER BY se.kaisai_nen, se.kaisai_tsukihi
    """, (start_year, end_year))
    all_entries = cur.fetchall()
    logger.info(f"  {len(all_entries):,} 出走レコード")

    # ── Step 3: 馬ごとの全レース結果をメモリに構築 ──
    logger.info("\nStep 3: 馬ごとの成績マップを構築...")
    # horse_results[ketto_id] = [(kaisai_nen, kaisai_tsukihi, chakujun), ...]
    horse_results: dict[str, list[tuple[str, str, int]]] = defaultdict(list)
    # race_horses[race_key] = [ketto_id, ...]
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

    # Sort each horse's results chronologically
    for ketto_id in horse_results:
        horse_results[ketto_id].sort()

    logger.info(f"  {len(horse_results):,} 頭, {len(race_horses):,} レース")

    # ── Step 4: 各レースの勝ち上がり/複勝を計算 ──
    logger.info("\nStep 4: レースレベル計算中...")
    race_levels = {}
    t0 = time.time()

    for i, (nen, tsukihi, keibajo, race_ban, race_name) in enumerate(races):
        race_key = f"{nen}{tsukihi}_{keibajo}_{race_ban}"
        horses_in_race = race_horses.get(race_key, [])
        total = len(horses_in_race)
        if total == 0:
            continue

        race_date_key = f"{nen}{tsukihi}"
        win_count = 0
        place_count = 0

        for ketto_id in horses_in_race:
            runs = horse_results.get(ketto_id, [])
            # Find this race's index
            has_won = False
            has_placed_next = False

            found_idx = -1
            for idx, (r_nen, r_tsukihi, r_chaku) in enumerate(runs):
                if r_nen == nen and r_tsukihi == tsukihi:
                    found_idx = idx
                    break

            if found_idx < 0:
                continue

            # 勝ち上がり: 以降の全レースで1着
            for subsequent in runs[found_idx + 1:]:
                if subsequent[2] == 1:
                    has_won = True
                    break

            # 複勝: 次走で3着以内
            if found_idx + 1 < len(runs):
                next_run = runs[found_idx + 1]
                if next_run[2] <= 3:
                    has_placed_next = True

            if has_won:
                win_count += 1
            if has_placed_next:
                place_count += 1

        win_rate = round(win_count / total * 100, 1) if total > 0 else 0
        place_rate = round(place_count / total * 100, 1) if total > 0 else 0
        level = calculate_level(win_rate, place_rate)

        venue_name = KEIBAJO_MAP.get(keibajo, keibajo)

        # Redis key: date_venue_racenumber (unique)
        redis_key = f"{nen}{tsukihi}_{venue_name}_{race_ban}"
        # Also store a name-based key for lookup from recent_runs
        race_name_trimmed = race_name.strip()
        name_key = f"{nen}{tsukihi}_{venue_name}_{race_name_trimmed}" if race_name_trimmed else ""

        entry = {
            "date": f"{nen}/{tsukihi[:2]}/{tsukihi[2:]}",
            "venue": venue_name,
            "race_name": race_name,
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

        if (i + 1) % 2000 == 0:
            elapsed = time.time() - t0
            logger.info(f"  {i + 1:,}/{len(races):,} ({elapsed:.1f}s)")

    elapsed = time.time() - t0
    logger.info(f"  完了: {len(race_levels):,} エントリ ({elapsed:.1f}s)")

    # ── レベル分布 ──
    level_dist: dict[str, int] = defaultdict(int)
    seen_races: set[str] = set()
    for key, entry in race_levels.items():
        # Deduplicate (some races have 2 keys)
        race_unique = f"{entry['date']}_{entry['venue']}_{entry['race_number']}"
        if race_unique not in seen_races:
            seen_races.add(race_unique)
            level_dist[entry["level"]] += 1

    logger.info("\nレベル分布:")
    for lv in ["S", "A", "B", "C", "D"]:
        cnt = level_dist.get(lv, 0)
        pct = cnt / len(seen_races) * 100 if seen_races else 0
        logger.info(f"  {lv}: {cnt:,} ({pct:.1f}%)")

    # ── Step 5: JSON 保存 ──
    output_file = OUTPUT_DIR / f"jra_race_level_{datetime.now().strftime('%Y%m%d')}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(race_levels, f, ensure_ascii=False)
    size_mb = output_file.stat().st_size / 1024 / 1024
    logger.info(f"\nJSON 出力: {output_file.name} ({size_mb:.1f}MB)")

    # ── Step 6: Redis 保存 ──
    try:
        import redis
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
        pipe = r.pipeline(transaction=False)
        for key, data in race_levels.items():
            pipe.set(f"{REDIS_PREFIX}:{key}", json.dumps(data, ensure_ascii=False), ex=REDIS_TTL)
        pipe.execute()
        logger.info(f"Redis 保存: {len(race_levels):,} エントリ")
    except ImportError:
        logger.warning("redis パッケージ未インストール (pip install redis)")
    except Exception as e:
        logger.error(f"Redis 保存失敗: {e}")

    cur.close()
    conn.close()
    logger.info("\n完了")


if __name__ == "__main__":
    main()
