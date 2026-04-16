#!/usr/bin/env python3
"""PoC: AI予想家キャラクター自動投稿機能 v2 — ドロワー印ベース。

設計方針 (2026-04-16 決定):
  - 印 (◎○▲△✖) は既存ドロワー `/api/votes/{race_id}/predictions` が真実のソース
  - Claude は印を受け取り、その根拠を各キャラの声で解説するだけ
  - Claude は picks を変更できない。バリデーションで完全一致を強制

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...

    python scripts/poc_auto_tipster.py                          # 今日最初のレース × honshi
    python scripts/poc_auto_tipster.py --persona data
    python scripts/poc_auto_tipster.py --race-id 20260418-tokyo-11 --persona anaba
    python scripts/poc_auto_tipster.py --list                   # 利用可能レース一覧
    python scripts/poc_auto_tipster.py --dry-run                # Claude 呼ばない
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from tipster_personas import (  # noqa: E402
    PERSONAS_BY_ID,
    TipsterPersona,
    get_persona,
)

API_BASE = os.environ.get("NETKEITA_API_BASE", "https://bot.dlogicai.in/nk")
OUTPUT_DIR = REPO_ROOT / "output"
JST = timezone(timedelta(hours=9))

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4000
BODY_MIN_LEN = 700
BODY_MAX_LEN = 1400  # 印ブロック(~120字) + 本文1300字を許容

# 印 → picks キー対応
MARK_TO_KEY = {
    "◎": "honmei",
    "○": "taikou",
    "▲": "tanana",
    "△": "renka",
    "✖": "keshi",
}
PICKS_KEYS = ["honmei", "taikou", "tanana", "renka", "keshi"]


# ─────────────────────────────────────────────────────────────────────────────
# API アクセス
# ─────────────────────────────────────────────────────────────────────────────


def _get(path: str, timeout: float = 30.0) -> dict:
    resp = httpx.get(f"{API_BASE}{path}", timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def fetch_available_dates() -> list[str]:
    return _get("/api/dates").get("dates", [])


def fetch_races(date_str: str) -> list[dict]:
    return _get(f"/api/races?date={date_str}").get("races", [])


def fetch_matrix(race_id: str) -> dict:
    return _get(f"/api/race/{race_id}/matrix")


def fetch_drawer_predictions(race_id: str) -> list[dict]:
    """`/api/votes/{race_id}/predictions` を叩いて3キャラの印を取得。"""
    return _get(f"/api/votes/{race_id}/predictions").get("predictions", [])


# ─────────────────────────────────────────────────────────────────────────────
# 印 → picks 変換
# ─────────────────────────────────────────────────────────────────────────────


def marks_to_picks(marks: dict) -> dict:
    """ドロワーの marks={"2": "◎", "6": "○", ...} を picks={honmei:2, taikou:6, ...} に変換。

    含まれない印は None にする。本命が無ければ ValueError。
    """
    picks = {k: None for k in PICKS_KEYS}
    for uma_str, mark in marks.items():
        try:
            num = int(uma_str)
        except (ValueError, TypeError):
            continue
        key = MARK_TO_KEY.get(mark)
        if key:
            picks[key] = num
    if picks["honmei"] is None:
        raise ValueError(f"ドロワー印に本命 (◎) がありません: {marks}")
    return picks


# ─────────────────────────────────────────────────────────────────────────────
# レースコンテキスト
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class RaceContext:
    race_id: str
    race_name: str
    venue: str
    distance: str
    track_condition: str
    headcount: int
    is_local: bool
    horses: list[dict]
    fixed_picks: dict           # ドロワーから確定済みの picks
    picks_with_names: dict      # 人間可読用: {honmei: {num, name}, ...}

    def to_prompt_json(self) -> str:
        # fixed_picks_with_names は渡さない。Claude が dict 形式を picks 値として
        # 誤採用するため。馬名は別途 picks_summary (テキスト) で伝える。
        payload = {
            "race": {
                "race_id": self.race_id,
                "race_name": self.race_name,
                "venue": self.venue,
                "distance": self.distance,
                "track_condition": self.track_condition,
                "headcount": self.headcount,
                "is_local": self.is_local,
            },
            "horses": self.horses,
            "fixed_picks": self.fixed_picks,
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)


def build_race_context(matrix: dict, picks: dict) -> RaceContext:
    horses_raw = matrix.get("horses", [])
    by_odds = sorted(
        [(h.get("horse_number", 0), h.get("odds", 0) or 999) for h in horses_raw],
        key=lambda x: x[1],
    )
    popularity = {num: rank for rank, (num, _) in enumerate(by_odds, 1)}

    horses: list[dict] = []
    name_by_num: dict[int, str] = {}
    for h in horses_raw:
        num = h.get("horse_number", 0)
        name = h.get("horse_name", "")
        name_by_num[num] = name
        horses.append({
            "number": num,
            "name": name,
            "jockey": h.get("jockey", ""),
            "post": h.get("post", 0),
            "odds": h.get("odds", 0),
            "popularity": popularity.get(num, 0),
            "ranks": h.get("ranks", {}),
        })

    picks_with_names: dict = {}
    for key, val in picks.items():
        if isinstance(val, int):
            picks_with_names[key] = {
                "number": val,
                "name": name_by_num.get(val, ""),
                "popularity": popularity.get(val, 0),
            }
        else:
            picks_with_names[key] = None

    return RaceContext(
        race_id=matrix.get("race_id", ""),
        race_name=matrix.get("race_name", ""),
        venue=matrix.get("venue", ""),
        distance=matrix.get("distance", ""),
        track_condition=matrix.get("track_condition", ""),
        headcount=len(horses),
        is_local=bool(matrix.get("is_local", False)),
        horses=horses,
        fixed_picks=picks,
        picks_with_names=picks_with_names,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Claude API 呼び出し
# ─────────────────────────────────────────────────────────────────────────────


def call_claude(persona: TipsterPersona, ctx: RaceContext, api_key: str) -> dict:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    system_prompt = persona.system_prompt()

    # 人間可読の picks 説明をプロンプトに含めて精度UP
    picks_lines = []
    marks_block_sample = []
    for key in PICKS_KEYS:
        info = ctx.picks_with_names.get(key)
        if info:
            mark = next(m for m, k in MARK_TO_KEY.items() if k == key)
            pop = info.get("popularity", 0)
            pop_str = f" ({pop}人気)" if pop else ""
            picks_lines.append(
                f"  {mark} {key}: 馬番{info['number']} {info['name']}{pop_str}"
            )
            if pop:
                marks_block_sample.append(f"{mark} {info['number']}.{info['name']} ({pop}人気)")
            else:
                marks_block_sample.append(f"{mark} {info['number']}.{info['name']}")
    picks_summary = "\n".join(picks_lines) if picks_lines else "(印なし)"
    marks_block = "\n".join(marks_block_sample) if marks_block_sample else ""

    user_prompt = (
        "以下のレースデータと、既に決定された印で記事を書いてください。\n"
        "**印は固定です。変更や追加はしないでください。**\n"
        "出力は JSON のみ。前後に余計な文章や ```json フェンスを付けないこと。\n\n"
        f"【固定の印】\n{picks_summary}\n\n"
        f"【body 先頭に必ずこの5行をそのまま配置すること (予想印カードになる)】\n"
        f"```\n{marks_block}\n```\n\n"
        "【レースデータ】\n"
        "```json\n"
        f"{ctx.to_prompt_json()}\n"
        "```"
    )

    resp = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = resp.content[0].text.strip()

    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    if "{" not in text or "}" not in text:
        raise ValueError(f"Claude response has no JSON object:\n{text[:300]}")
    start = text.index("{")
    end = text.rindex("}") + 1
    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError as e:
        raise ValueError(f"Claude response JSON parse failed: {e}\nRaw:\n{text[:500]}") from e


# ─────────────────────────────────────────────────────────────────────────────
# 後処理 (予想印ブロック保険注入 + 段落改行正規化)
# ─────────────────────────────────────────────────────────────────────────────


# PredictionDetailView.parseMarks が認識できる行パターン
# ^([◎○▲△☆✖])\s*(\d+)[.\s　]+(.+?)(?:\s*[\(（](\d+)人気[\)）])?$
_MARK_LINE_RE = re.compile(r"^[◎○▲△☆✖]\s*\d+[.\s　]+")


def _generate_marks_block(ctx: "RaceContext") -> str:
    """ctx.picks_with_names から parseMarks 互換の5行を生成する。"""
    lines: list[str] = []
    for key in PICKS_KEYS:
        info = ctx.picks_with_names.get(key)
        if not info:
            continue
        mark = next(m for m, k in MARK_TO_KEY.items() if k == key)
        pop = info.get("popularity", 0)
        pop_str = f" ({pop}人気)" if pop else ""
        lines.append(f"{mark} {info['number']}.{info['name']}{pop_str}")
    return "\n".join(lines)


def postprocess_article(article: dict, ctx: "RaceContext") -> dict:
    """Claude 出力に最低限の整形をかける。

    1. body 冒頭に予想印ブロック(5行)が無ければ、picks から生成して差し込む
    2. CRLF/LF の正規化と末尾空白除去
    3. 3連以上の連続空行を2つに畳む
    """
    body = article.get("body", "") or ""
    # 改行正規化
    body = body.replace("\r\n", "\n").replace("\r", "\n")
    # 末尾空白除去
    body = "\n".join(line.rstrip() for line in body.split("\n")).strip()
    # 連続空行を最大2つに
    body = re.sub(r"\n{3,}", "\n\n", body)

    # 冒頭に印ブロックが存在するか判定 (最初の5行以内に印行が1つでもあればOK)
    head_lines = body.split("\n", 10)[:10]
    has_mark_line = any(_MARK_LINE_RE.match(line.strip()) for line in head_lines)

    if not has_mark_line:
        marks_block = _generate_marks_block(ctx)
        if marks_block:
            body = marks_block + "\n\n" + body

    article["body"] = body
    return article


# ─────────────────────────────────────────────────────────────────────────────
# バリデーション
# ─────────────────────────────────────────────────────────────────────────────


def validate_article(article: dict, ctx: RaceContext) -> list[str]:
    """生成記事を検証。エラーメッセージの list を返す (空=合格)。"""
    errors: list[str] = []
    valid_numbers = {h["number"] for h in ctx.horses}

    # 必須キー
    for k in ("title", "preview_body", "body", "picks", "bet_method", "ticket_count"):
        if k not in article:
            errors.append(f"必須キー欠落: {k}")
    if errors:
        return errors

    # picks: ドロワー印と完全一致すること
    picks = article.get("picks", {})
    if not isinstance(picks, dict):
        errors.append(f"picks が dict でない: {type(picks).__name__}")
    else:
        for key in PICKS_KEYS:
            want = ctx.fixed_picks.get(key)
            got = picks.get(key)
            if want != got:
                errors.append(f"picks.{key} が改変された: 固定={want} / 出力={got}")

        # 馬番存在チェック (念のため)
        for key, val in picks.items():
            if isinstance(val, int) and val not in valid_numbers:
                errors.append(f"picks.{key}={val} は出走表にない馬番")

    # 本文長
    body = article.get("body", "")
    body_len = len(body)
    if body_len < BODY_MIN_LEN:
        errors.append(f"本文が短すぎる: {body_len}字 (最低{BODY_MIN_LEN}字)")
    if body_len > BODY_MAX_LEN:
        errors.append(f"本文が長すぎる: {body_len}字 (最大{BODY_MAX_LEN}字)")

    # タイトルに本命馬名が含まれるか
    honmei_num = picks.get("honmei") if isinstance(picks, dict) else None
    if isinstance(honmei_num, int):
        honmei_horse = next((h for h in ctx.horses if h["number"] == honmei_num), None)
        if honmei_horse and honmei_horse["name"] not in article.get("title", ""):
            errors.append(f"タイトルに本命馬名 ({honmei_horse['name']}) が含まれていない")

    # ticket_count
    tc = article.get("ticket_count")
    if not isinstance(tc, int) or tc <= 0:
        errors.append(f"ticket_count が正の整数でない: {tc!r}")

    # 禁止ワード
    for word in ("必ず勝", "絶対勝", "確実に的中", "保証"):
        if word in body or word in article.get("preview_body", ""):
            errors.append(f"禁止ワード含有: {word}")

    return errors


# ─────────────────────────────────────────────────────────────────────────────
# 出力
# ─────────────────────────────────────────────────────────────────────────────


def save_article(article: dict, persona: TipsterPersona, ctx: RaceContext, errors: list[str]) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    safe_race_id = ctx.race_id.replace("/", "_")
    path = OUTPUT_DIR / f"poc_{safe_race_id}_{persona.id}.md"

    # picks を可読表示に
    picks_display_lines = []
    for key in PICKS_KEYS:
        info = ctx.picks_with_names.get(key)
        if info:
            mark = next(m for m, k in MARK_TO_KEY.items() if k == key)
            picks_display_lines.append(f"  {mark} {key}: 馬番{info['number']} {info['name']}")
    picks_display = "\n".join(picks_display_lines) if picks_display_lines else "(印なし)"

    lines = [
        f"# [PoC v2] {article.get('title', '')}",
        "",
        f"- race_id: `{ctx.race_id}`",
        f"- venue: {ctx.venue} / distance: {ctx.distance} / 頭数: {ctx.headcount}",
        f"- persona: {persona.display_name} ({persona.id})",
        f"- generated_at (JST): {datetime.now(JST).isoformat()}",
        f"- bet_method: {article.get('bet_method', '')}",
        f"- ticket_count: {article.get('ticket_count', '')}",
        "",
        "## 固定の印 (ドロワー由来)",
        "",
        "```",
        picks_display,
        "```",
        "",
    ]
    if errors:
        lines.append("## バリデーションエラー")
        lines.append("")
        lines.extend(f"- {e}" for e in errors)
        lines.append("")
    else:
        lines.append("## バリデーション: OK")
        lines.append("")

    lines.extend([
        "## preview_body",
        "",
        article.get("preview_body", ""),
        "",
        "## body",
        "",
        article.get("body", ""),
        "",
        "## raw JSON",
        "",
        "```json",
        json.dumps(article, ensure_ascii=False, indent=2),
        "```",
    ])

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────
# 記事投稿 (POST /api/articles)
# ─────────────────────────────────────────────────────────────────────────────


# persona.id → managed tipster の固定カスタムID (setup_managed_tipsters.py と同期)
PERSONA_TO_MANAGED_ID = {
    "honshi": "managed_ai_honshi",
    "data": "managed_ai_data",
    "anaba": "managed_ai_anaba",
}


def post_article(
    article: dict,
    persona: "TipsterPersona",
    ctx: "RaceContext",
    *,
    status: str,
    internal_key: str,
) -> dict:
    """POST /api/articles に draft/published 投稿する。内部APIキーで認証。"""
    tipster_id = PERSONA_TO_MANAGED_ID.get(persona.id, "")
    payload = {
        "title": article.get("title", ""),
        "description": article.get("preview_body", "")[:200],
        "body": article.get("body", ""),
        "thumbnail_url": "",
        "status": status,  # "draft" | "published"
        "race_id": ctx.race_id,
        "content_type": "prediction",
        "tipster_id": tipster_id,
        "bet_method": article.get("bet_method", ""),
        "ticket_count": int(article.get("ticket_count", 0) or 0),
        "preview_body": article.get("preview_body", ""),
        "is_premium": False,
        "ai_generated": True,
        "ai_model": MODEL,
        "picks": article.get("picks", {}),
    }
    resp = httpx.post(
        f"{API_BASE}/api/articles",
        json=payload,
        headers={"X-Internal-Key": internal_key},
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()


def resolve_race_id(explicit: str | None) -> str:
    if explicit:
        return explicit
    dates = fetch_available_dates()
    if not dates:
        raise SystemExit("利用可能なレース日がありません")
    date_str = dates[0]
    races = fetch_races(date_str)
    if not races:
        raise SystemExit(f"{date_str} にレースがありません")
    jra = [r for r in races if not r.get("is_local")]
    chosen = (jra or races)[0]
    print(f"[info] 自動選択: {date_str} {chosen.get('venue')}{chosen.get('race_number')}R "
          f"{chosen.get('race_name')} (race_id={chosen.get('race_id')})")
    return chosen.get("race_id", "")


def list_races() -> int:
    dates = fetch_available_dates()
    if not dates:
        print("(利用可能な日付なし)")
        return 0
    for d in dates[:2]:
        print(f"\n=== {d} ===")
        for r in fetch_races(d):
            flag = "[NAR]" if r.get("is_local") else "[JRA]"
            print(f"  {flag} {r.get('venue'):<4} {r.get('race_number'):>2}R "
                  f"{r.get('race_name', ''):<20} {r.get('distance', ''):<10} "
                  f"headcount={r.get('headcount')} id={r.get('race_id')}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--race-id", help="対象レースID")
    parser.add_argument("--persona", default="honshi",
                        choices=list(PERSONAS_BY_ID.keys()),
                        help="ペルソナID (honshi / data / anaba)")
    parser.add_argument("--api-key", help="ANTHROPIC_API_KEY")
    parser.add_argument("--dry-run", action="store_true", help="Claude 呼ばない")
    parser.add_argument("--list", action="store_true", help="利用可能レース一覧")
    parser.add_argument("--post", action="store_true",
                        help="生成後 POST /api/articles に投稿する")
    parser.add_argument("--status", default="draft", choices=["draft", "published"],
                        help="投稿ステータス (--post 時に使用、既定: draft)")
    args = parser.parse_args()

    if args.list:
        return list_races()

    persona = get_persona(args.persona)
    print(f"[info] persona: {persona.display_name} ({persona.id})")

    race_id = resolve_race_id(args.race_id)
    if not race_id:
        return 1

    # ドロワー印取得
    print(f"[info] fetching drawer predictions for {race_id} ...")
    try:
        drawer_list = fetch_drawer_predictions(race_id)
    except httpx.HTTPStatusError as e:
        print(f"[error] drawer predictions fetch failed: {e.response.status_code}", file=sys.stderr)
        return 2

    drawer_char = next((d for d in drawer_list if d.get("id") == persona.id), None)
    if not drawer_char or not drawer_char.get("marks"):
        print(f"[error] ドロワーに persona={persona.id} の印がありません", file=sys.stderr)
        return 3

    try:
        picks = marks_to_picks(drawer_char["marks"])
    except ValueError as e:
        print(f"[error] {e}", file=sys.stderr)
        return 4

    print(f"[info] drawer picks for {persona.id}: {picks}")

    # matrix 取得
    print(f"[info] fetching matrix for {race_id} ...")
    try:
        matrix = fetch_matrix(race_id)
    except httpx.HTTPStatusError as e:
        print(f"[error] matrix fetch failed: {e.response.status_code}", file=sys.stderr)
        return 5
    ctx = build_race_context(matrix, picks)
    print(f"[info] {ctx.venue} {ctx.race_name} ({ctx.distance}, {ctx.headcount}頭)")

    if args.dry_run:
        print("\n========== SYSTEM PROMPT ==========")
        print(persona.system_prompt())
        print("\n========== FIXED PICKS ==========")
        for key in PICKS_KEYS:
            info = ctx.picks_with_names.get(key)
            if info:
                mark = next(m for m, k in MARK_TO_KEY.items() if k == key)
                print(f"  {mark} {key}: 馬番{info['number']} {info['name']}")
        print("\n[info] --dry-run: Claude 呼び出しスキップ")
        return 0

    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("[error] ANTHROPIC_API_KEY 未設定", file=sys.stderr)
        return 6

    print(f"[info] calling Claude ({MODEL}) ...")
    try:
        article = call_claude(persona, ctx, api_key)
    except ValueError as e:
        print(f"[error] Claude parse error: {e}", file=sys.stderr)
        return 7
    except Exception as e:
        print(f"[error] Claude call failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 8

    # 整形 (予想印ブロック保険注入・改行正規化)
    article = postprocess_article(article, ctx)

    errors = validate_article(article, ctx)
    if errors:
        print(f"[warn] バリデーションエラー {len(errors)}件:")
        for e in errors:
            print(f"  - {e}")
    else:
        print("[ok] バリデーション通過")

    out_path = save_article(article, persona, ctx, errors)
    print(f"[info] 出力: {out_path}")
    print(f"[info] body length: {len(article.get('body', ''))}字")

    # 投稿 (--post 指定時のみ、バリデーション通過した場合に限る)
    if args.post:
        if errors:
            print("[warn] バリデーションエラーのため投稿スキップ")
            return 9
        internal_key = os.environ.get("INTERNAL_API_KEY", "")
        if not internal_key:
            print("[error] INTERNAL_API_KEY 未設定 (--post には必須)", file=sys.stderr)
            return 10
        try:
            posted = post_article(article, persona, ctx, status=args.status, internal_key=internal_key)
        except httpx.HTTPStatusError as e:
            print(f"[error] 投稿失敗: HTTP {e.response.status_code} {e.response.text[:200]}",
                  file=sys.stderr)
            return 11
        except Exception as e:
            print(f"[error] 投稿失敗: {type(e).__name__}: {e}", file=sys.stderr)
            return 12
        slug = posted.get("slug", "?")
        print(f"[ok] 投稿完了 status={args.status} slug={slug}")
        print(f"[info] URL: https://www.netkeita.com/articles/{slug}")

    return 0 if not errors else 9


if __name__ == "__main__":
    sys.exit(main())
