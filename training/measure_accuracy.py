"""Measure NL→GraphQL accuracy: base model vs fine-tuned LoRA endpoint.

Runs the 8 seed pairs through BOTH the base Llama 3.1 8B (with the in-context
seeds prompt — Plan B) AND the fine-tuned LoRA endpoint, then validates each
generated GraphQL by:
  1. Parsing it with `gql()`
  2. POSTing it to live DataHub at $DATAHUB_GMS_URL
  3. Checking the response is HTTP 200 with no GraphQL errors
  4. Checking the response has at least one non-empty result

Reports per-model: parse rate, execution rate, non-empty result rate.

Usage:
    source ~/.config/openclaw/shell-secrets.zsh
    export NEBIUS_API_KEY=$(env HOME=~/.config/op/home op read \
      "op://Clawdbot/Nebius Token Factory - Datahub Hackathon/notesPlain")
    # Pass the deployed LoRA endpoint slug:
    python training/measure_accuracy.py meta-llama/Meta-Llama-3.1-8B-Instruct your-org/datahub-graphql-v1
"""
import json
import os
import sys
import time
from pathlib import Path

import requests
from openai import OpenAI

try:
    from gql import gql
except ImportError:
    print("Install gql: pip install gql", file=sys.stderr)
    sys.exit(1)


REPO_ROOT = Path(__file__).parent.parent
SEEDS_PATH = REPO_ROOT / "training" / "seeds.jsonl"
PLAN_B_PROMPT_PATH = REPO_ROOT / "training" / "plan_b_system_prompt.txt"

NEBIUS_BASE = "https://api.studio.nebius.com/v1"
NEBIUS_KEY = os.environ.get("NEBIUS_API_KEY", "")
DATAHUB_URL = os.environ.get("DATAHUB_GMS_URL", "http://100.114.31.63:8080")
DATAHUB_TOKEN = os.environ.get("DATAHUB_GMS_TOKEN", "")

if not NEBIUS_KEY or not DATAHUB_TOKEN:
    print("❌ NEBIUS_API_KEY and DATAHUB_GMS_TOKEN must both be set", file=sys.stderr)
    sys.exit(1)


def load_seeds() -> list[dict]:
    with open(SEEDS_PATH) as f:
        return [json.loads(line) for line in f if line.strip()]


def base_system_prompt() -> str:
    """Plan B in-context prompt — used for the BASE model run."""
    if PLAN_B_PROMPT_PATH.exists():
        return PLAN_B_PROMPT_PATH.read_text()
    return (
        "You translate natural language questions about data assets into "
        "DataHub GraphQL read queries. Return only valid GraphQL, no markdown."
    )


def fine_tuned_system_prompt() -> str:
    """Minimal prompt for the FINE-TUNED model — it should know the format from training."""
    return (
        "You translate natural language questions about data assets into "
        "DataHub GraphQL read queries. Return only valid GraphQL, no markdown."
    )


def call_model(client: OpenAI, model: str, system: str, user: str) -> str:
    response = client.chat.completions.create(
        model=model,
        max_tokens=600,
        temperature=0.0,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    text = (response.choices[0].message.content or "").strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def validate_graphql(graphql: str) -> tuple[bool, bool, bool, str]:
    """Returns (parses, executes, non_empty, error_msg)."""
    if not graphql:
        return False, False, False, "empty"
    try:
        gql(graphql)
    except Exception as e:
        return False, False, False, f"parse: {str(e)[:60]}"
    try:
        r = requests.post(
            f"{DATAHUB_URL}/api/graphql",
            json={"query": graphql},
            headers={
                "Authorization": f"Bearer {DATAHUB_TOKEN}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
    except Exception as e:
        return True, False, False, f"http: {e}"
    if r.status_code != 200:
        return True, False, False, f"http {r.status_code}"
    body = r.json()
    if "errors" in body:
        msg = (body["errors"][0].get("message") or "")[:60]
        return True, False, False, f"gql: {msg}"
    data = body.get("data") or {}
    has_payload = bool(data) and any(v for v in data.values() if v)
    return True, True, has_payload, "ok"


def measure(model: str, system: str, label: str) -> dict:
    print(f"\n=== {label}: {model} ===")
    client = OpenAI(base_url=NEBIUS_BASE, api_key=NEBIUS_KEY)
    seeds = load_seeds()

    parsed = executed = non_empty = 0
    rows = []
    for seed in seeds:
        nl = seed["nl"]
        try:
            graphql = call_model(client, model, system, nl)
        except Exception as e:
            print(f"  ❌ {seed['pattern']:<26} model_error: {str(e)[:60]}")
            rows.append({"pattern": seed["pattern"], "result": "model_error", "msg": str(e)})
            continue

        p, e, ne, msg = validate_graphql(graphql)
        if p: parsed += 1
        if e: executed += 1
        if ne: non_empty += 1
        marker = "✅" if ne else ("⚠️" if e else "❌")
        print(f"  {marker} {seed['pattern']:<26} parse={p} exec={e} non_empty={ne}  {msg}")
        rows.append({
            "pattern": seed["pattern"],
            "parses": p, "executes": e, "non_empty": ne,
            "msg": msg,
            "graphql": graphql[:200],
        })

    n = len(seeds)
    summary = {
        "model": model,
        "label": label,
        "total": n,
        "parsed": parsed,
        "executed": executed,
        "non_empty": non_empty,
        "parse_pct": round(100 * parsed / n, 1) if n else 0,
        "execute_pct": round(100 * executed / n, 1) if n else 0,
        "non_empty_pct": round(100 * non_empty / n, 1) if n else 0,
    }
    print(f"\n  Summary: parse {summary['parse_pct']}% · execute {summary['execute_pct']}% · non-empty {summary['non_empty_pct']}%")
    return summary, rows


def main():
    if len(sys.argv) < 3:
        print("Usage: python measure_accuracy.py <base_model> <finetuned_model>", file=sys.stderr)
        print("Example: python measure_accuracy.py meta-llama/Meta-Llama-3.1-8B-Instruct your-org/datahub-graphql-v1", file=sys.stderr)
        sys.exit(1)

    base_model = sys.argv[1]
    ft_model = sys.argv[2]

    base_summary, base_rows = measure(base_model, base_system_prompt(), "BASE (with in-context seeds)")
    ft_summary, ft_rows = measure(ft_model, fine_tuned_system_prompt(), "FINE-TUNED")

    delta = ft_summary["non_empty_pct"] - base_summary["non_empty_pct"]
    print()
    print("─" * 60)
    print(f"  {'Metric':<26} {'Base':>10} {'Fine-tuned':>14} {'Δ':>10}")
    print(f"  {'Parses':<26} {base_summary['parse_pct']:>9}% {ft_summary['parse_pct']:>13}% {ft_summary['parse_pct']-base_summary['parse_pct']:>+9.1f}")
    print(f"  {'Executes (no errors)':<26} {base_summary['execute_pct']:>9}% {ft_summary['execute_pct']:>13}% {ft_summary['execute_pct']-base_summary['execute_pct']:>+9.1f}")
    print(f"  {'Non-empty result':<26} {base_summary['non_empty_pct']:>9}% {ft_summary['non_empty_pct']:>13}% {delta:>+9.1f}")
    print("─" * 60)

    # Save report so the dashboard can pick up the numbers
    report = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "base": base_summary,
        "fine_tuned": ft_summary,
        "delta_pct": delta,
        "base_rows": base_rows,
        "ft_rows": ft_rows,
    }
    out = REPO_ROOT / "training" / "accuracy_report.json"
    with open(out, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  Report saved: {out}")
    print(f"\n  → Update dashboard/static/finetune_metrics.json:")
    print(f"      accuracy.base_pct = {base_summary['non_empty_pct']}")
    print(f"      accuracy.fine_tuned_pct = {ft_summary['non_empty_pct']}")
    print(f"      accuracy.improvement_pct = {delta}")


if __name__ == "__main__":
    main()
