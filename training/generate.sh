#!/usr/bin/env bash
# Generate ~300 NL→GraphQL training pairs via DeepSeek-R1 on Nebius.
# Output: training/raw_pairs.jsonl
#
# Prereqs:
#   - NEBIUS_API_KEY env var set
#   - jq installed (brew install jq)
#
# Usage:
#   cd training/
#   bash generate.sh
set -euo pipefail

cd "$(dirname "$0")"

if [ -z "${NEBIUS_API_KEY:-}" ]; then
    echo "❌ NEBIUS_API_KEY not set" >&2
    exit 1
fi

if ! command -v jq >/dev/null; then
    echo "❌ jq not installed (brew install jq)" >&2
    exit 1
fi

if [ ! -f seeds.jsonl ]; then
    echo "❌ seeds.jsonl not found" >&2
    exit 1
fi

# Build the prompt by interpolating seeds.jsonl into gen_prompt.txt
SEEDS_BLOCK=$(cat seeds.jsonl)
PROMPT_TEMPLATE=$(cat gen_prompt.txt)
PROMPT_BASE="${PROMPT_TEMPLATE/\[PASTE seeds.jsonl HERE\]/$SEEDS_BLOCK}"

> raw_pairs.jsonl

PATTERNS=(
    search_by_name
    search_by_tag
    get_dataset_details
    lineage_upstream
    lineage_downstream
    assertions_with_results
    failing_assertions
    column_metadata
)

for pattern in "${PATTERNS[@]}"; do
    echo "Generating for $pattern..."
    PROMPT_FOR_PATTERN="${PROMPT_BASE/<PATTERN_NAME>/$pattern}"
    PAYLOAD=$(jq -n --arg prompt "$PROMPT_FOR_PATTERN" '{
        model: "deepseek-ai/DeepSeek-R1-0528",
        max_tokens: 8000,
        temperature: 0.7,
        messages: [{role: "user", content: $prompt}]
    }')
    RESPONSE=$(curl -sf -m 120 https://api.studio.nebius.com/v1/chat/completions \
        -H "Authorization: Bearer $NEBIUS_API_KEY" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD")
    if [ -z "$RESPONSE" ]; then
        echo "  ⚠ empty response — skipping"
        continue
    fi
    CONTENT=$(echo "$RESPONSE" | jq -r '.choices[0].message.content // empty')
    if [ -z "$CONTENT" ]; then
        echo "  ⚠ no content — skipping"
        continue
    fi
    # Strip any markdown code fences and append valid JSONL lines
    echo "$CONTENT" | sed -E '/^```/d; /^[[:space:]]*$/d' >> raw_pairs.jsonl
done

LINES=$(wc -l < raw_pairs.jsonl)
echo
echo "Generated $LINES raw lines in raw_pairs.jsonl"
echo "Next: python validate_pairs.py raw_pairs.jsonl validated_pairs.jsonl"
