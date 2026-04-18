#!/bin/bash
# AI予想家3キャラ 毎日自動投稿 (JRA + NAR 共通)
#
# cron 登録例 (毎朝 6:00 JST):
#   0 6 * * * flock -n /tmp/ai_tipsters.lock /opt/dlogic/netkeita-api/scripts/batch_ai_tipsters_daily.sh
#
# 既存記事チェック:
#   poc_auto_tipster.py が既定で同 race_id × tipster_id の既存記事をスキップするので、
#   途中失敗した後の再実行や手動補填も安全に動く。
#
# ログ:
#   /opt/dlogic/netkeita-api/logs/cron_ai_tipsters_<date>.log        詳細ログ
#   /opt/dlogic/netkeita-api/logs/cron_ai_tipsters_<date>_summary.log サマリ
set -u

cd /opt/dlogic/netkeita-api
set -a; . ./.env.local; set +a

DATE=$(date +%Y%m%d)
LOG=/opt/dlogic/netkeita-api/logs/cron_ai_tipsters_${DATE}.log
SUMMARY=/opt/dlogic/netkeita-api/logs/cron_ai_tipsters_${DATE}_summary.log
mkdir -p /opt/dlogic/netkeita-api/logs
> "$LOG"; > "$SUMMARY"

echo "[cron-ai-tipsters] start: $(date)" | tee -a "$SUMMARY"

# 今日の全レース (JRA + NAR) を取得
races=$(curl -s "https://bot.dlogicai.in/nk/api/races?date=${DATE}" | python3 -c "
import json, sys
try:
    d = json.loads(sys.stdin.read())
    for r in d.get('races', []):
        print(r['race_id'])
except Exception as e:
    print(f'[error] parse: {e}', file=sys.stderr)
")

race_count=$(echo "$races" | grep -c . || true)
total_planned=$((race_count * 3))
echo "[cron-ai-tipsters] races=${race_count}, 3 personas → ${total_planned} planned" \
  | tee -a "$SUMMARY"

if [ "$race_count" -eq 0 ]; then
    echo "[cron-ai-tipsters] no races today, exit" | tee -a "$SUMMARY"
    exit 0
fi

i=0; ok=0; ng=0; skip=0
for race_id in $races; do
    for persona in honshi data anaba; do
        i=$((i+1))
        echo "--- [$i/${total_planned}] $race_id $persona ---" >> "$LOG"
        out=$(/opt/dlogic/backend/venv/bin/python scripts/poc_auto_tipster.py \
              --race-id "$race_id" --persona "$persona" \
              --post --status published 2>&1)
        echo "$out" >> "$LOG"
        if echo "$out" | grep -q "\[skip\] 既存記事あり"; then
            skip=$((skip+1))
        elif echo "$out" | grep -q "投稿完了"; then
            ok=$((ok+1))
        else
            ng=$((ng+1))
            echo "[FAIL] $race_id $persona" >> "$SUMMARY"
        fi
        sleep 5
    done
done
echo "[cron-ai-tipsters] done: $(date) total=$i ok=$ok skip=$skip ng=$ng" \
  | tee -a "$SUMMARY"
