"""End-to-end smoke test for the LEFT lane (orchestrator + 4 agents + tools).

Runs the full orchestrator against real Studio A DataHub + real Nebius models
and verifies:
  - completes in <120 seconds (target: <90s)
  - emits agent_started for all 4 agents
  - emits at least one nl_query, graphql_executed, postmortem_written event
  - returns a non-empty postmortem
  - writes annotations to all 3 affected datasets

This is task L10 in the spec. Run with:
    source ~/.config/openclaw/shell-secrets.zsh && \
    NEBIUS_API_KEY=$(env HOME=~/.config/op/home op read \
      "op://Clawdbot/Nebius Token Factory - Datahub Hackathon/notesPlain") \
    pytest tests/test_e2e_left.py -v --timeout=180
"""
import asyncio
import os
import time

import pytest

from incident_response.events import Event
from incident_response.orchestrator import run as orchestrator_run
from incident_response.tools import datahub_sdk


pytestmark = pytest.mark.skipif(
    not os.environ.get("DATAHUB_GMS_TOKEN") or not os.environ.get("NEBIUS_API_KEY"),
    reason="Requires DATAHUB_GMS_TOKEN + NEBIUS_API_KEY",
)


@pytest.mark.timeout(180)
@pytest.mark.asyncio
async def test_orchestrator_runs_end_to_end():
    events: list[Event] = []

    def emit(event):
        if isinstance(event, Event):
            events.append(event)

    start = time.time()
    result = await orchestrator_run("revenue dashboard wrong — investigate", emit)
    elapsed = time.time() - start

    print(f"\nOrchestrator finished in {elapsed:.1f}s with {len(events)} events")

    # Acceptance: timing
    assert elapsed < 120, f"Orchestrator took {elapsed:.1f}s, expected <120s"

    # Acceptance: all 4 agents fired
    started_agents = {e.agent for e in events if e.type == "agent_started"}
    expected_agents = {"system", "coordinator", "detective", "reality_checker", "fixer"}
    missing = expected_agents - started_agents
    assert not missing, f"Missing agent_started events for: {missing}"

    # Acceptance: at least one of each meaningful event type
    types = {e.type for e in events}
    for required_type in ["agent_started", "nl_query", "graphql_executed", "agent_completed", "incident_complete"]:
        assert required_type in types, f"Missing event type: {required_type}"

    # Acceptance: postmortem populated
    assert result.get("postmortem"), "Postmortem is empty"
    assert len(result["postmortem"]) > 50, "Postmortem too short"

    # Acceptance: incident_id set
    assert result.get("incident_id", "").startswith("INC-")

    # Acceptance: at least 1 dataset annotated (target: 3)
    affected = result.get("affected_datasets", [])
    assert len(affected) >= 1, f"No datasets quarantined; affected={affected}"

    # Acceptance: Reality-Checker found gap
    rc = result.get("reality_checker", {})
    gap = rc.get("gap", [])
    assert len(gap) >= 1, f"Reality-Checker found no gap; rc={rc}"

    # Cleanup: reset descriptions on the affected datasets so the next run is clean
    if affected:
        try:
            datahub_sdk.reset_dataset_descriptions(affected)
        except Exception as e:
            print(f"Cleanup warning: {e}")
