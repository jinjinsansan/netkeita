"""List every LINE user who has logged in recently.

This script dumps the Redis session store (db=2, used by api/main.py) and
prints every distinct `line_user_id` along with its display name. Use the
output to populate `ADMIN_LINE_USER_IDS` in `api/.env.local`.

Usage (on the server where Redis is running):
    python scripts/list_line_users.py

Because sessions carry a 24 h TTL, only users who have logged in within
the last day will appear. If the user you want is missing, ask them to
log in once at https://www.netkeita.com and then re-run this script.

Safety: this script is READ-ONLY. It does not modify Redis or session data.
"""

from __future__ import annotations

import json
import sys

import redis


def main() -> int:
    try:
        client = redis.Redis(host="127.0.0.1", port=6379, db=2, decode_responses=True)
        client.ping()
    except Exception as exc:
        print(f"[ERROR] Redis に接続できません: {exc}", file=sys.stderr)
        print("        このスクリプトは Redis が動いているサーバー上で実行してください。", file=sys.stderr)
        return 1

    keys = list(client.scan_iter("nk:session:*"))
    if not keys:
        print("セッションが見つかりません (24時間以内に誰もログインしていないようです)。")
        return 0

    # Dedupe by line_user_id — a single user can have multiple active sessions.
    seen: dict[str, dict] = {}
    for key in keys:
        try:
            raw = client.get(key)
            if not raw:
                continue
            data = json.loads(raw)
            uid = data.get("line_user_id")
            if not uid:
                continue
            # Keep the most recent (last write wins — good enough for display)
            seen[uid] = {
                "display_name": data.get("display_name", "(no name)"),
                "picture_url": data.get("picture_url", ""),
            }
        except Exception as exc:
            print(f"[WARN] {key} の解析に失敗: {exc}", file=sys.stderr)

    if not seen:
        print("有効なセッションにひとりも line_user_id が含まれていません。")
        return 0

    print(f"検出したユーザー: {len(seen)} 名\n")
    print(f"{'DISPLAY NAME':<30}  LINE USER ID")
    print("-" * 70)
    for uid, info in sorted(seen.items(), key=lambda kv: kv[1]["display_name"]):
        print(f"{info['display_name']:<30}  {uid}")

    print()
    print("以下を api/.env.local に追記してください (カンマ区切りで任意の人数まで):")
    print()
    ids = ",".join(seen.keys())
    print(f"    ADMIN_LINE_USER_IDS={ids}")
    print()
    print("(上記は検出した全員のIDです。管理者にしたい人だけを残して不要なものは削除してください)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
