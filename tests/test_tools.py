"""Integration tests for the tools layer.

These tests hit real Studio A DataHub. Run with:
    source ~/.config/openclaw/shell-secrets.zsh && pytest tests/test_tools.py -v

Tests that require Nebius credits are gated behind RUN_NEBIUS_TESTS=1.
"""
import os
import pytest

from incident_response.events import (
    Event,
    agent_started,
    thinking,
    nl_query,
    graphql_generated,
    graphql_executed,
    tool_called,
    agent_completed,
    coordinator_synthesizing,
    postmortem_written,
    slack_posted,
    incident_complete,
    error,
)
from incident_response.tools import datahub_graphql, datahub_sdk, slack


# ─── events.py ─────────────────────────────────────────────────────────────

def test_event_constructors_cover_all_types():
    events = [
        agent_started("coordinator"),
        thinking("coordinator", "I'm thinking..."),
        nl_query("detective", "find revenue dashboard"),
        graphql_generated("detective", "{ search(...) }"),
        graphql_executed("detective", "found 1 dataset", rows=1),
        tool_called("fixer", "datahub_sdk", {"action": "update"}),
        agent_completed("detective", "lineage traced"),
        coordinator_synthesizing(),
        postmortem_written("urn:li:dataset:(urn:li:dataPlatform:sqlite,olist_dirty.test,PROD)", "test"),
        slack_posted("#data-incidents", "hello"),
        incident_complete(elapsed_ms=1234, postmortem="ok"),
        error("system", "boom"),
    ]
    for e in events:
        assert isinstance(e, Event)
        assert e.type
        assert e.agent
        d = e.model_dump()
        assert "ts" in d
        assert isinstance(d["data"], dict)


def test_event_serializes_to_json():
    e = thinking("coordinator", "test reasoning")
    j = e.model_dump_json()
    assert "coordinator" in j
    assert "thinking" in j
    assert "test reasoning" in j


# ─── datahub_graphql.py ────────────────────────────────────────────────────

@pytest.mark.skipif(
    not os.environ.get("DATAHUB_GMS_TOKEN"),
    reason="DATAHUB_GMS_TOKEN not set — source ~/.config/openclaw/shell-secrets.zsh",
)
def test_datahub_graphql_search_returns_olist():
    """Live query against Studio A — must return olist_orders datasets."""
    data = datahub_graphql.query(
        '{ search(input: {type: DATASET, query: "olist_orders", start: 0, count: 3}) '
        '{ total searchResults { entity { urn } } } }'
    )
    assert "search" in data
    assert data["search"]["total"] >= 1


@pytest.mark.skipif(
    not os.environ.get("DATAHUB_GMS_TOKEN"),
    reason="DATAHUB_GMS_TOKEN not set",
)
def test_datahub_graphql_raises_on_bad_query():
    with pytest.raises(datahub_graphql.DatahubError):
        datahub_graphql.query("{ this_is_not_a_real_field }")


# ─── datahub_sdk.py ────────────────────────────────────────────────────────

def test_make_dataset_urn_format():
    urn = datahub_sdk.make_dataset_urn("olist_dirty", "olist_order_items")
    assert urn == "urn:li:dataset:(urn:li:dataPlatform:sqlite,olist_dirty.olist_order_items,PROD)"


@pytest.mark.skipif(
    not os.environ.get("DATAHUB_GMS_TOKEN"),
    reason="DATAHUB_GMS_TOKEN not set",
)
def test_datahub_sdk_round_trip():
    """Write a test annotation, verify via GraphQL, clean up."""
    urn = datahub_sdk.make_dataset_urn("olist_dirty", "olist_order_items")
    test_id = "TEST-PYTEST-L2"
    try:
        datahub_sdk.quarantine_dataset(urn, test_id, "L2 round-trip test")
        # Give DataHub a moment to ingest
        import time
        time.sleep(1)
        # Verify via GraphQL
        data = datahub_graphql.query(
            f'{{ dataset(urn: "{urn}") {{ editableProperties {{ description }} }} }}'
        )
        ds = data.get("dataset")
        assert ds is not None
        editable = ds.get("editableProperties") or {}
        desc = editable.get("description") or ""
        assert test_id in desc, f"Expected '{test_id}' in description, got: {desc!r}"
    finally:
        # Always clean up
        datahub_sdk.reset_dataset_descriptions([urn])


# ─── slack.py ──────────────────────────────────────────────────────────────

def test_slack_fallback_to_stderr_when_unset(monkeypatch):
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    result = slack.post("test message")
    assert result["sent"] is False
    assert result["channel"] == "#data-incidents"
    assert result["fallback"] == "stderr"


def test_slack_custom_channel(monkeypatch):
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    result = slack.post("test message", channel="#oncall")
    assert result["channel"] == "#oncall"
