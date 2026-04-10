#!/usr/bin/env bash
# Start the data-oncall demo: dashboard server + Tailscale Funnel.
#
# Result: a public HTTPS URL that anyone on the internet can hit to run a
# real incident response. Run this on the Mac Mini (where the venv lives
# and Tailscale is up) before the demo.
#
# To stop: bash scripts/stop_demo.sh
set -euo pipefail

cd "$(dirname "$0")/.."
REPO_ROOT="$(pwd)"

PORT="${DASHBOARD_PORT:-8001}"
FUNNEL_PORT="${FUNNEL_PORT:-10001}"
PIDFILE="/tmp/data-oncall-dashboard.pid"
LOGFILE="/tmp/data-oncall-dashboard.log"

echo "data-oncall demo bootstrapper"
echo "─────────────────────────────"

# 1. Venv
if [ ! -f .venv/bin/activate ]; then
    echo "❌ .venv not found. Run: /opt/homebrew/bin/python3.12 -m venv .venv && source .venv/bin/activate && pip install -e '.[dev]'"
    exit 1
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# 2. Secrets
if [ -f ~/.config/openclaw/shell-secrets.zsh ]; then
    # shellcheck disable=SC1090
    source ~/.config/openclaw/shell-secrets.zsh
fi
if [ -z "${DATAHUB_GMS_TOKEN:-}" ]; then
    echo "❌ DATAHUB_GMS_TOKEN not set"
    exit 1
fi

# 3. Nebius key from 1Password
if [ -z "${NEBIUS_API_KEY:-}" ]; then
    NEBIUS_API_KEY=$(env HOME=~/.config/op/home op read \
        "op://Clawdbot/Nebius Token Factory - Datahub Hackathon/notesPlain" 2>/dev/null || true)
fi
if [ -z "${NEBIUS_API_KEY:-}" ]; then
    echo "❌ NEBIUS_API_KEY not loadable from 1Password"
    exit 1
fi
export NEBIUS_API_KEY DATAHUB_GMS_URL DATAHUB_GMS_TOKEN

# 4. If dashboard already running, kill it
if [ -f "$PIDFILE" ] && kill -0 "$(cat $PIDFILE)" 2>/dev/null; then
    echo "→ stopping existing dashboard (pid $(cat $PIDFILE))"
    kill "$(cat $PIDFILE)"
    sleep 1
fi
rm -f "$PIDFILE"

# 5. Start uvicorn in background
echo "→ starting uvicorn on 127.0.0.1:$PORT"
nohup uvicorn dashboard.server:app --host 127.0.0.1 --port "$PORT" >"$LOGFILE" 2>&1 &
DASH_PID=$!
echo "$DASH_PID" > "$PIDFILE"

# Wait for /healthz to come up
for i in 1 2 3 4 5 6 7 8 9 10; do
    if curl -sf -m 1 "http://127.0.0.1:$PORT/healthz" >/dev/null 2>&1; then
        echo "  ✅ dashboard up (pid $DASH_PID)"
        break
    fi
    sleep 0.5
    if [ $i -eq 10 ]; then
        echo "  ❌ dashboard didn't come up — see $LOGFILE"
        tail -10 "$LOGFILE"
        exit 1
    fi
done

# 6. Enable Tailscale Funnel on FUNNEL_PORT → local PORT
echo "→ enabling Tailscale Funnel on :$FUNNEL_PORT"
tailscale funnel --bg --https="$FUNNEL_PORT" "$PORT" 2>&1 | tail -5

# 7. Get the public hostname
HOSTNAME=$(tailscale status --json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['Self']['DNSName'].rstrip('.'))" 2>/dev/null || echo "")
if [ -z "$HOSTNAME" ]; then
    HOSTNAME="$(hostname).<your-tailnet>.ts.net"
fi
PUBLIC_URL="https://$HOSTNAME:$FUNNEL_PORT"

echo
echo "─────────────────────────────────────────────────────────────"
echo "  🌐  Public URL:    $PUBLIC_URL"
echo "  💻  Local URL:     http://127.0.0.1:$PORT"
echo "  📋  Logs:          $LOGFILE"
echo "  🔻  Stop:          bash scripts/stop_demo.sh"
echo "─────────────────────────────────────────────────────────────"
echo
echo "→ Smoke test:"
curl -s -o /dev/null -w "  Public  /healthz  HTTP %{http_code} (%{time_total}s)\n" "$PUBLIC_URL/healthz"
curl -s -o /dev/null -w "  Public  /         HTTP %{http_code} (%{time_total}s)\n" "$PUBLIC_URL/"
echo
echo "Open in browser: $PUBLIC_URL"
