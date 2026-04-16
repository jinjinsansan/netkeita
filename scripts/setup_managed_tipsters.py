#!/usr/bin/env python3
"""AI予想家3キャラの managed tipster を本番 Redis (db=6) に登録する。

Usage:
    python scripts/setup_managed_tipsters.py           # 登録 (冪等)
    python scripts/setup_managed_tipsters.py --list    # 登録済みのみ確認

固定 ID (managed_ai_honshi / managed_ai_data / managed_ai_anaba) で登録する
ので、再実行しても重複せず、display_name やキャッチフレーズの更新にも使える。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

# Repo layout differs between local and VPS:
#   local: repo/api/services/*.py, repo/scripts/*.py
#   VPS:   /opt/dlogic/netkeita-api/services/*.py, /opt/dlogic/netkeita-api/scripts/*.py
# Pick whichever has a services/ directory.
if (REPO_ROOT / "api" / "services").is_dir():
    API_DIR = REPO_ROOT / "api"
elif (REPO_ROOT / "services").is_dir():
    API_DIR = REPO_ROOT
else:
    raise SystemExit(f"services/ directory not found under {REPO_ROOT}")

sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(API_DIR))

from services import tipsters as tipsters_service  # noqa: E402
from tipster_personas import ALL_PERSONAS  # noqa: E402


# persona.id (honshi/data/anaba) → 固定 managed custom_id
# "managed_ai_honshi" のような ID になる。ai_ プレフィックスで「AI予想家」と判別しやすく。
CUSTOM_ID_PREFIX = "ai_"


def _custom_id_for(persona_id: str) -> str:
    return f"{CUSTOM_ID_PREFIX}{persona_id}"


def _managed_id_for(persona_id: str) -> str:
    return f"managed_{_custom_id_for(persona_id)}"


def upsert_all() -> list[dict]:
    results: list[dict] = []
    for persona in ALL_PERSONAS:
        mid = _managed_id_for(persona.id)
        existing = tipsters_service.get_tipster(mid)
        profile = tipsters_service.create_managed_tipster(
            display_name=persona.display_name,
            catchphrase=persona.tagline,
            description=persona.personality.replace("\n", " "),
            picture_url="",
            custom_id=_custom_id_for(persona.id),
        )
        action = "updated" if existing else "created"
        print(f"  [{action}] {profile['display_name']:<12} id={profile['line_user_id']}")
        results.append(profile)
    return results


def list_current() -> None:
    for persona in ALL_PERSONAS:
        mid = _managed_id_for(persona.id)
        existing = tipsters_service.get_tipster(mid)
        if existing:
            print(f"  ✓ {persona.id:<8} {existing['display_name']:<12} "
                  f"id={existing['line_user_id']}  status={existing['status']}")
        else:
            print(f"  ✗ {persona.id:<8} 未登録  (期待 ID: {mid})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list", action="store_true", help="登録状況のみ表示")
    args = parser.parse_args()

    if args.list:
        print("[info] 現在の登録状況:")
        list_current()
        return 0

    print("[info] 3キャラを upsert します:")
    upsert_all()
    print("\n[info] 登録後の状況:")
    list_current()
    return 0


if __name__ == "__main__":
    sys.exit(main())
