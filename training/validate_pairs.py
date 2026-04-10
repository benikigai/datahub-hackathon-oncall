"""Validate NL→GraphQL training pairs against the live DataHub.

Drops pairs that fail to parse OR return GraphQL errors. Reads pairs from
the input file (one JSON per line), writes the surviving ones to the output
file. Prints a per-pattern drop summary at the end.

Usage:
    source ~/.config/openclaw/shell-secrets.zsh
    python validate_pairs.py raw_pairs.jsonl validated_pairs.jsonl
"""
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import requests

try:
    from gql import gql
except ImportError:
    print("Install gql: pip install gql", file=sys.stderr)
    sys.exit(1)


GMS_URL = os.environ.get("DATAHUB_GMS_URL", "http://100.114.31.63:8080")
TOKEN = os.environ.get("DATAHUB_GMS_TOKEN", "")

if not TOKEN:
    print("❌ DATAHUB_GMS_TOKEN not set", file=sys.stderr)
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}


def validate(pair: dict) -> tuple[bool, str]:
    g = pair.get("graphql", "")
    if not g:
        return False, "no graphql"
    try:
        gql(g)
    except Exception as e:
        return False, f"parse: {str(e)[:80]}"
    try:
        r = requests.post(
            f"{GMS_URL}/api/graphql",
            json={"query": g},
            headers=HEADERS,
            timeout=10,
        )
    except Exception as e:
        return False, f"http: {str(e)[:80]}"
    if r.status_code != 200:
        return False, f"http {r.status_code}"
    body = r.json()
    if "errors" in body:
        msg = (body["errors"][0].get("message") or "")[:80]
        return False, f"gql: {msg}"
    return True, "ok"


def main():
    if len(sys.argv) != 3:
        print("Usage: python validate_pairs.py <raw.jsonl> <validated.jsonl>", file=sys.stderr)
        sys.exit(1)

    src, dst = sys.argv[1], sys.argv[2]
    if not Path(src).exists():
        print(f"❌ {src} not found", file=sys.stderr)
        sys.exit(1)

    by_pattern_pass: dict[str, int] = defaultdict(int)
    by_pattern_fail: dict[str, int] = defaultdict(int)
    drop_reasons: dict[str, int] = defaultdict(int)
    valid = invalid = 0

    with open(src) as f, open(dst, "w") as out:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                pair = json.loads(line)
            except json.JSONDecodeError:
                invalid += 1
                drop_reasons["bad_json"] += 1
                continue

            ok, msg = validate(pair)
            pattern = pair.get("pattern", "?")
            if ok:
                out.write(json.dumps(pair) + "\n")
                valid += 1
                by_pattern_pass[pattern] += 1
            else:
                invalid += 1
                by_pattern_fail[pattern] += 1
                drop_reasons[msg.split(":")[0]] += 1
                print(f"DROP [{pattern}]: {msg}")

    total = valid + invalid
    pct = (valid / total * 100) if total else 0
    print()
    print(f"Validated: {valid} / {total} ({pct:.0f}% kept)")
    print()
    print("By pattern:")
    all_patterns = sorted(set(list(by_pattern_pass.keys()) + list(by_pattern_fail.keys())))
    for p in all_patterns:
        print(f"  {p:<26} pass={by_pattern_pass[p]:>3}  fail={by_pattern_fail[p]:>3}")
    print()
    print("Drop reasons:")
    for reason, count in sorted(drop_reasons.items(), key=lambda x: -x[1]):
        print(f"  {reason:<26} {count}")


if __name__ == "__main__":
    main()
