echo "=== Backend directory ==="
ls /opt/dlogic/backend/

echo ""
echo "=== API v2 directory ==="
ls /opt/dlogic/backend/api/v2/

echo ""
echo "=== Main app entry point ==="
head -50 /opt/dlogic/backend/main.py 2>/dev/null || head -50 /opt/dlogic/backend/app.py 2>/dev/null || echo "not found"

echo ""
echo "=== Grep for newspaper endpoint ==="
grep -rn "newspaper" /opt/dlogic/backend/api/v2/ --include="*.py" | head -20

echo ""
echo "=== Grep for full.scores or full_scores ==="
grep -rn "full.score\|full_score" /opt/dlogic/backend/ --include="*.py" | head -10

echo ""
echo "=== Grep for track_adjust ==="
grep -rn "track_adjust\|track_adaptation\|baba\|馬場補正" /opt/dlogic/backend/ --include="*.py" | head -20
