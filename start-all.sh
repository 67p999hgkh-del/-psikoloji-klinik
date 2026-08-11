#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

SESSION_FLASK="flask-psikoloji-klinik"
SESSION_TUNNEL="cf-tunnel-5000"
URL_FILE="$PWD/.tunnel-url"

# Flask sunucusu
if ! tmux -f /exec-daemon/tmux.portal.conf has-session -t "=$SESSION_FLASK" 2>/dev/null; then
  tmux -f /exec-daemon/tmux.portal.conf new-session -d -s "$SESSION_FLASK" -c "$PWD" -- \
    "/bin/bash" -l -c "source .venv/bin/activate && python app.py"
else
  tmux -f /exec-daemon/tmux.portal.conf send-keys -t "$SESSION_FLASK:0.0" C-c \
    "cd '$PWD' && source .venv/bin/activate && python app.py" C-m
fi

sleep 2

# Cloudflare tunnel — her başlatmada yenile (Error 1033 önlemi)
if [ ! -x /tmp/cloudflared ]; then
  curl -sL -o /tmp/cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
  chmod +x /tmp/cloudflared
fi
pkill -f "/tmp/cloudflared tunnel" 2>/dev/null || true
tmux -f /exec-daemon/tmux.portal.conf kill-session -t "$SESSION_TUNNEL" 2>/dev/null || true
tmux -f /exec-daemon/tmux.portal.conf new-session -d -s "$SESSION_TUNNEL" -- \
  "/tmp/cloudflared tunnel --url http://127.0.0.1:5000"
sleep 12

TUNNEL_URL=$(tmux -f /exec-daemon/tmux.portal.conf capture-pane -t "$SESSION_TUNNEL" -S -300 -p 2>/dev/null \
  | tr -d '\n' | rg -o 'https://[a-z0-9-]+\.trycloudflare\.com' | head -1 || true)
if [ -n "$TUNNEL_URL" ]; then
  echo "$TUNNEL_URL" > "$URL_FILE"
fi

echo "Flask: http://127.0.0.1:5000"
echo "Public: ${TUNNEL_URL:-$(cat "$URL_FILE" 2>/dev/null || echo 'bekleniyor...')}"
