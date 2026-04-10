"""CLI trigger — POSTs an incident to the dashboard's /trigger endpoint.

Usage:
    python -m incident_response.triggers.page_team "revenue dashboard wrong"
    python -m incident_response.triggers.page_team --dry-run "test"
    python -m incident_response.triggers.page_team --local "test"   # bypass dashboard, run locally

If --local is set, runs the orchestrator directly in this process and prints
events as they arrive (useful for testing without the dashboard server).
"""
import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone

import httpx

DASHBOARD_URL = os.environ.get("DASHBOARD_URL", "http://localhost:8001")


def _print_event(event_dict):
    """Pretty-print one SSE event to stdout."""
    ts = event_dict.get("ts", "")
    agent = event_dict.get("agent", "")
    etype = event_dict.get("type", "")
    data = event_dict.get("data", {})
    short_ts = ts.split("T")[-1].split("+")[0][:12] if "T" in ts else ""
    summary = ""
    if etype == "thinking":
        summary = f": {(data.get('text','')[:80]).strip()}"
    elif etype == "nl_query":
        summary = f": {data.get('question','')[:80]}"
    elif etype == "graphql_executed":
        summary = f": {data.get('summary','')}"
    elif etype == "agent_completed":
        summary = f": {data.get('summary','')}"
    elif etype == "incident_complete":
        summary = f" — {data.get('elapsed_ms', 0)} ms"
    elif etype == "postmortem_written":
        summary = f": {data.get('annotation', '')[:80]}"
    print(f"[{short_ts}] {agent:<18} {etype}{summary}")


async def _run_local(incident: str, dry_run: bool):
    """Run the orchestrator in-process, printing events to stdout."""
    if dry_run:
        print(f"[DRY-RUN] would page team with: {incident!r}")
        return 0

    from incident_response.orchestrator import run
    from incident_response.events import Event

    def emit(event: Event):
        # Convert Pydantic Event → dict for printing
        if isinstance(event, Event):
            _print_event(event.model_dump())
        else:
            _print_event(event)

    try:
        result = await run(incident, emit)
    except Exception as e:
        print(f"\n❌ Orchestrator failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

    print()
    print("─" * 60)
    print(f"INCIDENT {result.get('incident_id')}")
    print(f"Elapsed: {result.get('elapsed_ms', 0)} ms")
    print(f"Affected datasets: {len(result.get('affected_datasets', []))}")
    print()
    print("POSTMORTEM:")
    print(result.get("postmortem", "(empty)"))
    return 0


def _post_to_dashboard(incident: str, dry_run: bool) -> int:
    if dry_run:
        print(f"[DRY-RUN] would POST to {DASHBOARD_URL}/trigger: {{\"incident\": {incident!r}}}")
        return 0
    try:
        r = httpx.post(
            f"{DASHBOARD_URL}/trigger",
            json={"incident": incident},
            timeout=10,
        )
    except Exception as e:
        print(f"❌ Could not reach dashboard at {DASHBOARD_URL}: {e}", file=sys.stderr)
        print("   Tip: start the dashboard with `uvicorn dashboard.server:app --port 8001`", file=sys.stderr)
        return 1
    if r.status_code == 409:
        print("⚠ Another incident is already running. Use the dashboard's RESET button first.", file=sys.stderr)
        return 1
    if r.status_code != 200:
        print(f"❌ Dashboard returned HTTP {r.status_code}: {r.text}", file=sys.stderr)
        return 1
    body = r.json()
    print(f"✅ Triggered run {body.get('run_id', '?')} — watch progress at {DASHBOARD_URL}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Page the data-oncall team for an incident")
    parser.add_argument("incident", nargs="?", default="revenue dashboard showing wrong numbers — investigate")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually trigger; just print what would happen")
    parser.add_argument("--local", action="store_true", help="Run orchestrator in-process instead of POSTing to dashboard")
    args = parser.parse_args()

    if args.local or args.dry_run:
        return asyncio.run(_run_local(args.incident, args.dry_run))
    return _post_to_dashboard(args.incident, args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
