#!/usr/bin/env bash
# L0 smoke test — verify all endpoints reachable before any agent code runs.
# Sources DataHub PAT from ~/.config/openclaw/shell-secrets.zsh
# Sources Nebius API key from 1Password (op CLI)
#
# Exit codes:
#   0 = all 5 checks passed
#   1+ = at least one check failed
set -uo pipefail

PASS=0
FAIL=0

check() {
    local name=$1; shift
    if "$@" >/dev/null 2>&1; then
        echo "✅ $name"
        PASS=$((PASS+1))
    else
        echo "❌ $name"
        FAIL=$((FAIL+1))
    fi
}

# 1. DataHub GMS health
check "DataHub GMS health (100.114.31.63:8080)" \
    curl -sf -m 5 http://100.114.31.63:8080/health

# 2. DataHub PAT works for authenticated GraphQL
if [ -f ~/.config/openclaw/shell-secrets.zsh ]; then
    # shellcheck disable=SC1090
    source ~/.config/openclaw/shell-secrets.zsh
fi
if [ -n "${DATAHUB_GMS_TOKEN:-}" ]; then
    check "DataHub authenticated GraphQL (PAT valid)" \
        bash -c 'curl -sf -m 5 -X POST http://100.114.31.63:8080/api/graphql \
            -H "Authorization: Bearer $DATAHUB_GMS_TOKEN" \
            -H "Content-Type: application/json" \
            -d "{\"query\":\"{ search(input: {type: DATASET, query: \\\"olist\\\", start: 0, count: 1}) { total } }\"}" \
            | grep -q "\"total\""'
else
    echo "❌ DataHub PAT (DATAHUB_GMS_TOKEN unset — generate at http://100.114.31.63:9002/settings/tokens and add to ~/.config/openclaw/shell-secrets.zsh)"
    FAIL=$((FAIL+1))
fi

# 3-5. Nebius models
NEBIUS_API_KEY=$(env HOME=~/.config/op/home op read \
    "op://Clawdbot/Nebius Token Factory - Datahub Hackathon/notesPlain" 2>/dev/null || echo "")

test_nebius_model() {
    local model=$1
    local maxtok=${2:-30}
    curl -sf -m 30 https://api.studio.nebius.com/v1/chat/completions \
        -H "Authorization: Bearer $NEBIUS_API_KEY" \
        -H "Content-Type: application/json" \
        -d "{\"model\":\"$model\",\"max_tokens\":$maxtok,\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}]}" \
        2>/dev/null | grep -q '"choices"'
}

if [ -n "$NEBIUS_API_KEY" ]; then
    check "Nebius / moonshotai/Kimi-K2-Thinking"            test_nebius_model "moonshotai/Kimi-K2-Thinking" 200
    check "Nebius / meta-llama/Meta-Llama-3.1-8B-Instruct"  test_nebius_model "meta-llama/Meta-Llama-3.1-8B-Instruct"
    check "Nebius / MiniMaxAI/MiniMax-M2.5"                 test_nebius_model "MiniMaxAI/MiniMax-M2.5" 100
else
    echo "❌ NEBIUS_API_KEY not loadable from 1Password (op://Clawdbot/Nebius Token Factory - Datahub Hackathon)"
    FAIL=$((FAIL+3))
fi

echo
echo "─────────────────────────────────"
echo "  $PASS passed, $FAIL failed"
echo "─────────────────────────────────"

if [ $FAIL -eq 0 ]; then
    echo "✅ All smoke tests passed — ready to build."
    exit 0
else
    echo "❌ Fix the failing checks before proceeding."
    exit 1
fi
