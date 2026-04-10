#!/usr/bin/env bash
# Stop the data-oncall demo: kill dashboard + disable Tailscale Funnel.
set -euo pipefail

PIDFILE="/tmp/data-oncall-dashboard.pid"
FUNNEL_PORT="${FUNNEL_PORT:-10001}"

echo "Stopping data-oncall demo..."

# 1. Disable Funnel rule for our port
if tailscale funnel status 2>&1 | grep -q ":$FUNNEL_PORT"; then
    echo "→ disabling Funnel on :$FUNNEL_PORT"
    tailscale funnel --https="$FUNNEL_PORT" off 2>&1 | head -3 || true
fi

# 2. Kill dashboard
if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "→ killing dashboard (pid $PID)"
        kill "$PID" || true
        sleep 1
        if kill -0 "$PID" 2>/dev/null; then
            kill -9 "$PID" || true
        fi
    fi
    rm -f "$PIDFILE"
fi

# 3. Cleanup any lingering uvicorn for our port
pkill -f "uvicorn dashboard.server" 2>/dev/null || true

echo "✅ stopped"
