#!/bin/bash
# Deploy netkeita API to VPS
# Run from local machine: bash scripts/deploy_api.sh

set -e

VPS_HOST="root@220.158.24.157"
VPS_KEY="$HOME/.ssh/id_ed25519_vps"
REMOTE_DIR="/opt/dlogic/netkeita-api"

echo "=== Deploying netkeita API to VPS ==="

# 1. Create remote directory
ssh -i "$VPS_KEY" "$VPS_HOST" "mkdir -p $REMOTE_DIR"

# 2. Sync API files
echo "Syncing files..."
rsync -avz --exclude='venv/' --exclude='__pycache__/' --exclude='data/' --exclude='.env.local' \
  -e "ssh -i $VPS_KEY" \
  api/ "$VPS_HOST:$REMOTE_DIR/"

# 3. Setup venv and install deps on VPS
echo "Installing dependencies..."
ssh -i "$VPS_KEY" "$VPS_HOST" "
  cd $REMOTE_DIR
  python3 -m venv venv 2>/dev/null || true
  ./venv/bin/pip install -r requirements.txt -q
"

# 4. Create .env.local if not exists
ssh -i "$VPS_KEY" "$VPS_HOST" "
  if [ ! -f $REMOTE_DIR/.env.local ]; then
    cat > $REMOTE_DIR/.env.local << 'EOF'
DLOGIC_API_URL=http://localhost:8000
PREFETCH_DIR=/opt/dlogic/linebot/data/prefetch
PORT=5002
EOF
    echo 'Created .env.local'
  else
    echo '.env.local already exists, skipping'
  fi
"

# 5. Install and start systemd service
echo "Setting up systemd service..."
ssh -i "$VPS_KEY" "$VPS_HOST" "
  cp $REMOTE_DIR/netkeita-api.service /etc/systemd/system/
  systemctl daemon-reload
  systemctl enable netkeita-api
  systemctl restart netkeita-api
  sleep 2
  systemctl status netkeita-api --no-pager
"

echo ""
echo "=== Deploy complete ==="
echo "API running at http://220.158.24.157:5002"
echo "Don't forget to add Nginx proxy config for /netkeita-api/"
