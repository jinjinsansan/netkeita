#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
レースレベルデータ取得スクリプト (netkeiba マスターコース)

ネット競馬のマスターコース (有料) にログインし、
各馬の過去走から「勝ち上がり頭数 / 複勝頭数」を取得して
レースレベル (S/A/B/C/D) を算出・保存する。

Usage:
    python scripts/scrape_race_level.py

環境変数 (.env.local):
    NETKEIBA_EMAIL    — ネット競馬ログインメールアドレス
    NETKEIBA_PASSWORD — ネット競馬ログインパスワード
"""

import os
import sys
import json
import time
import re
import io
import logging
import hashlib
from pathlib import Path
from datetime import datetime

# Windows 文字化け対策
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── 設定 ──
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

# .env.local の読み込み
def _load_env():
    """Load .env.local from project root or VPS paths."""
    for p in [
        PROJECT_ROOT / ".env.local",
        Path("/opt/dlogic/netkeita-api/.env.local"),
        Path("/opt/dlogic/netkeita/.env.local"),
    ]:
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
            logger.info(f"Loaded env from {p}")
            return
    logger.warning("No .env.local found")

_load_env()

NETKEIBA_EMAIL = os.environ.get("NETKEIBA_EMAIL", "")
NETKEIBA_PASSWORD = os.environ.get("NETKEIBA_PASSWORD", "")

# Redis 接続 (VPS 上で動く前提)
REDIS_HOST = os.environ.get("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_DB = 3
RACE_LEVEL_PREFIX = "nk:racelevel"
RACE_LEVEL_TTL = 86400 * 180  # 180日

# 出力ファイル (R2 アップロード用)
OUTPUT_FILE = SCRIPT_DIR / f"race_level_{datetime.now().strftime('%Y%m%d')}.json"

# ── レースレベル算出 ──

def calculate_race_level(win_count: int, win_total: int,
                         place_count: int, place_total: int) -> str:
    """勝ち上がり率と複勝率からレースレベルを算出する。

    Composite Score = win_rate * 0.4 + place_rate * 0.6

    |  Level  |  Score  |  イメージ                       |
    |---------|---------|--------------------------------|
    |    S    |  35+    |  G1〜重賞クラスハイレベル         |
    |    A    |  22+    |  重賞〜OP クラス                 |
    |    B    |  12+    |  条件戦で平均的                  |
    |    C    |   5+    |  やや低い                        |
    |    D    |   <5    |  低レベル戦 or データ不足          |
    """
    if win_total == 0 and place_total == 0:
        return "?"  # データなし

    total = max(win_total, place_total, 1)
    win_rate = (win_count / total) * 100
    place_rate = (place_count / total) * 100
    composite = win_rate * 0.4 + place_rate * 0.6

    if composite >= 35:
        return "S"
    elif composite >= 22:
        return "A"
    elif composite >= 10:
        return "B"
    elif composite >= 4:
        return "C"
    else:
        return "D"


def race_level_key(date_str: str, venue: str, race_name: str) -> str:
    """Redis キーに使うレース識別子を生成。

    date_str: "2026/03/05" or "20260305" 形式
    venue: "中山"
    race_name: "中山記念"
    """
    d = date_str.replace("/", "")[:8]
    return f"{d}_{venue}_{race_name}"


# ── ネット競馬スクレイピング ──

def login_netkeiba(session):
    """ネット競馬にログインする (requests.Session)。

    Returns True on success, False on failure.
    """
    if not NETKEIBA_EMAIL or not NETKEIBA_PASSWORD:
        logger.error("NETKEIBA_EMAIL / NETKEIBA_PASSWORD が設定されていません")
        return False

    login_url = "https://regist.netkeiba.com/account/login"
    login_data = {
        "pid": "login",
        "action": "auth",
        "login_id": NETKEIBA_EMAIL,
        "pswd": NETKEIBA_PASSWORD,
    }

    try:
        resp = session.post(login_url, data=login_data, timeout=30)
        if resp.status_code == 200 and "logout" in resp.text.lower():
            logger.info("netkeiba ログイン成功")
            return True
        # Cookie ベースのリダイレクト認証も試す
        if resp.status_code in (200, 302):
            # ログイン後のページにアクセスしてみる
            check = session.get("https://race.sp.netkeiba.com/", timeout=15)
            if "マスターコース" in check.text or "ログアウト" in check.text:
                logger.info("netkeiba ログイン成功 (リダイレクト認証)")
                return True
        logger.error(f"netkeiba ログイン失敗: status={resp.status_code}")
        return False
    except Exception as e:
        logger.error(f"netkeiba ログインエラー: {e}")
        return False


def fetch_horse_race_levels(session, horse_id: str) -> list[dict]:
    """馬の過去走ページから勝ち上がりデータを取得する。

    Args:
        session: ログイン済みの requests.Session
        horse_id: ネット競馬の horse_id (例: "2019104308")

    Returns:
        [{
            "date": "2026/03/01",
            "venue": "中山",
            "race_name": "中山記念",
            "win_count": 0, "win_total": 14,
            "place_count": 0, "place_total": 14,
            "level": "D"
        }, ...]
    """
    # TODO: 実際のネット競馬マスターコースページの HTML 構造に合わせて実装
    # 走行タイプ解析ページ (マスターコース限定):
    # https://race.sp.netkeiba.com/modal/horse.html?horse_id={horse_id}&tab=3
    #
    # HTML の構造 (推定):
    # - 各レースエントリに「勝ち X/Y頭 複勝 X/Y頭」テキストが含まれる
    # - BeautifulSoup でパースして抽出

    url = f"https://race.sp.netkeiba.com/modal/horse.html?horse_id={horse_id}&tab=3"
    try:
        resp = session.get(url, timeout=20)
        resp.encoding = "utf-8"
        if resp.status_code != 200:
            logger.warning(f"Horse page failed: {horse_id} status={resp.status_code}")
            return []

        return _parse_race_level_html(resp.text)
    except Exception as e:
        logger.error(f"Failed to fetch horse {horse_id}: {e}")
        return []


def _parse_race_level_html(html: str) -> list[dict]:
    """HTML から勝ち上がり/複勝データをパースする。

    ※ 実際の HTML 構造に合わせて調整が必要。
    スクリーンショットから推定した構造で実装。
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    results = []

    # 推定: 各レース行は特定の CSS クラスまたは構造を持つ
    # パターン: 「勝ち X/Y頭 複勝 X/Y頭」
    win_pattern = re.compile(r"勝ち\s*(\d+)\s*/\s*(\d+)\s*頭")
    place_pattern = re.compile(r"複勝\s*(\d+)\s*/\s*(\d+)\s*頭")

    # 走行解析ページの各レースエントリを探す
    # ※ 実際の CSS セレクタは netkeiba のページ構造に依存
    race_entries = soup.select(".RaceList_Data, .Race_Data, .HorseRace, tr, .result_table tr")

    for entry in race_entries:
        text = entry.get_text()
        win_match = win_pattern.search(text)
        place_match = place_pattern.search(text)

        if win_match and place_match:
            win_count = int(win_match.group(1))
            win_total = int(win_match.group(2))
            place_count = int(place_match.group(1))
            place_total = int(place_match.group(2))

            # レース情報 (日付、会場、レース名) の抽出
            # ※ HTML 構造に合わせて調整が必要
            date_str = ""
            venue = ""
            race_name = ""

            # 日付パターン: YYYY/MM/DD
            date_match = re.search(r"(\d{4}/\d{2}/\d{2})", text)
            if date_match:
                date_str = date_match.group(1)

            # TODO: venue と race_name の抽出ロジックを HTML 構造に合わせて実装

            level = calculate_race_level(win_count, win_total, place_count, place_total)

            results.append({
                "date": date_str,
                "venue": venue,
                "race_name": race_name,
                "win_count": win_count,
                "win_total": win_total,
                "place_count": place_count,
                "place_total": place_total,
                "level": level,
            })

    return results


def get_horse_ids_for_today(session) -> list[dict]:
    """本日の JRA レースの出走馬の netkeiba horse_id を取得する。

    Returns:
        [{"horse_name": "...", "horse_id": "...", "race_id_nk": "..."}, ...]
    """
    # TODO: 本日のJRAレースから horse_id を取得する
    # 方法1: netkeiba の出馬表ページをスクレイプ
    # 方法2: PC-KEIBA DB の ketto_toroku_bango から netkeiba horse_id にマッピング
    # 方法3: 既存の course_stats_scraper.py の _get_horse_ids() を流用
    logger.warning("get_horse_ids_for_today: TODO - 実装が必要です")
    return []


# ── Redis 保存 ──

def save_to_redis(race_levels: dict[str, dict]):
    """レースレベルデータを Redis に保存する。"""
    import redis
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)

    pipe = r.pipeline(transaction=False)
    count = 0
    for key, data in race_levels.items():
        redis_key = f"{RACE_LEVEL_PREFIX}:{key}"
        pipe.set(redis_key, json.dumps(data, ensure_ascii=False), ex=RACE_LEVEL_TTL)
        count += 1

    pipe.execute()
    logger.info(f"Redis に {count} 件のレースレベルを保存")


def save_to_json(race_levels: dict[str, dict]):
    """レースレベルデータを JSON ファイルに保存する。"""
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(race_levels, f, ensure_ascii=False, indent=2)
    size_mb = OUTPUT_FILE.stat().st_size / 1024 / 1024
    logger.info(f"JSON 出力: {OUTPUT_FILE} ({size_mb:.1f}MB)")


# ── メイン処理 ──

def main():
    logger.info("=" * 60)
    logger.info("レースレベルデータ取得開始")
    logger.info("=" * 60)

    if not NETKEIBA_EMAIL or not NETKEIBA_PASSWORD:
        logger.error("環境変数 NETKEIBA_EMAIL / NETKEIBA_PASSWORD を設定してください")
        logger.info("例: .env.local に以下を追加:")
        logger.info("  NETKEIBA_EMAIL=your@email.com")
        logger.info("  NETKEIBA_PASSWORD=yourpassword")
        sys.exit(1)

    import requests
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; Pixel 3) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36"
    })

    # 1. ログイン
    if not login_netkeiba(session):
        logger.error("ネット競馬へのログインに失敗しました")
        sys.exit(1)

    # 2. 本日のレースの出走馬 horse_id を取得
    horses = get_horse_ids_for_today(session)
    if not horses:
        logger.warning("出走馬データが取得できません。スクリプトの実装を確認してください。")
        sys.exit(1)

    # 3. 各馬の過去走データを取得
    all_race_levels: dict[str, dict] = {}
    processed = 0

    for horse in horses:
        hid = horse.get("horse_id", "")
        if not hid:
            continue

        levels = fetch_horse_race_levels(session, hid)
        for lv in levels:
            key = race_level_key(lv["date"], lv["venue"], lv["race_name"])
            if key and key not in all_race_levels:
                all_race_levels[key] = lv

        processed += 1
        if processed % 10 == 0:
            logger.info(f"  {processed}/{len(horses)} 頭処理...")
            time.sleep(1)  # Rate limiting

        time.sleep(0.5)  # Polite scraping

    logger.info(f"\n取得完了: {len(all_race_levels)} レースのレベルデータ")

    # 4. 保存
    if all_race_levels:
        save_to_json(all_race_levels)
        save_to_redis(all_race_levels)

    logger.info("=" * 60)
    logger.info("完了")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
