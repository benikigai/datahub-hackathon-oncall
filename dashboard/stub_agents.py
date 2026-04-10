"""Hardcoded stub event sequence for dashboard development.

Lets the middle terminal iterate on the UI without waiting for real LLMs.
Fires 25 events on a 200ms cadence simulating a full incident response run.
"""
import asyncio
import time
from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc).isoformat()


STUB_SEQUENCE = [
    {"agent": "system", "type": "agent_started", "data": {"incident": "revenue dashboard wrong"}},
    {"agent": "coordinator", "type": "agent_started", "data": {}},
    {"agent": "coordinator", "type": "thinking", "data": {"text": "User reports revenue dashboard wrong. Need to identify backing dataset, trace lineage, validate against reality, propose fix."}},
    {"agent": "detective", "type": "agent_started", "data": {}},
    {"agent": "reality_checker", "type": "agent_started", "data": {}},
    {"agent": "detective", "type": "nl_query", "data": {"question": "Find the dataset for v_seller_performance in olist_dirty"}},
    {"agent": "detective", "type": "graphql_generated", "data": {"graphql": "{ search(input: {type: DATASET, query: \"v_seller_performance\", start: 0, count: 5}) { searchResults { entity { urn } } } }"}},
    {"agent": "detective", "type": "graphql_executed", "data": {"summary": "Identified affected dataset: v_seller_performance", "rows": 1}},
    {"agent": "reality_checker", "type": "nl_query", "data": {"question": "Show me all assertions and their latest results for olist_order_items, olist_customers, olist_products in BOTH instances"}},
    {"agent": "detective", "type": "nl_query", "data": {"question": "Get all upstream lineage from olist_dirty.v_seller_performance, 2 hops"}},
    {"agent": "detective", "type": "graphql_generated", "data": {"graphql": "{ lineage(input: {urn: \"urn:li:dataset:(urn:li:dataPlatform:sqlite,olist_dirty.main.v_seller_performance,PROD)\", direction: UPSTREAM, count: 100, hops: 2}) { count entities { entity { urn } degree } } }"}},
    {"agent": "reality_checker", "type": "graphql_executed", "data": {"summary": "Queried 6 dataset assertion sets (3 tables × 2 instances)", "rows": 6}},
    {"agent": "detective", "type": "graphql_executed", "data": {"summary": "Found 5 upstream datasets", "rows": 5}},
    {"agent": "detective", "type": "agent_completed", "data": {"summary": "Lineage traced: v_seller_performance ← olist_order_items ← olist_sellers"}},
    {"agent": "reality_checker", "type": "agent_completed", "data": {"summary": "Found 3 production-only failures: 5,632 truncated seller_ids, 7,955 deleted customers, 988 NULL categories"}},
    {"agent": "coordinator", "type": "coordinator_synthesizing", "data": {}},
    {"agent": "fixer", "type": "agent_started", "data": {}},
    {"agent": "fixer", "type": "tool_called", "data": {"tool": "datahub_sdk.quarantine_dataset", "args": {"urn": "olist_dirty.main.olist_order_items", "incident_id": "INC-STUB"}}},
    {"agent": "fixer", "type": "postmortem_written", "data": {"urn": "urn:li:dataset:(urn:li:dataPlatform:sqlite,olist_dirty.main.olist_order_items,PROD)", "annotation": "⚠️ INC-STUB: 5632 seller_id_length_eq_32 violations"}},
    {"agent": "fixer", "type": "tool_called", "data": {"tool": "datahub_sdk.quarantine_dataset", "args": {"urn": "olist_dirty.main.olist_customers", "incident_id": "INC-STUB"}}},
    {"agent": "fixer", "type": "postmortem_written", "data": {"urn": "urn:li:dataset:(urn:li:dataPlatform:sqlite,olist_dirty.main.olist_customers,PROD)", "annotation": "⚠️ INC-STUB: 7955 row_count violations"}},
    {"agent": "fixer", "type": "tool_called", "data": {"tool": "datahub_sdk.quarantine_dataset", "args": {"urn": "olist_dirty.main.olist_products", "incident_id": "INC-STUB"}}},
    {"agent": "fixer", "type": "postmortem_written", "data": {"urn": "urn:li:dataset:(urn:li:dataPlatform:sqlite,olist_dirty.main.olist_products,PROD)", "annotation": "⚠️ INC-STUB: 988 product_category_name violations"}},
    {"agent": "fixer", "type": "slack_posted", "data": {"channel": "#data-incidents", "text": "🚨 INCIDENT: 3 referential integrity bugs in olist_dirty"}},
    {"agent": "fixer", "type": "agent_completed", "data": {"summary": "Quarantined 3 datasets, Slack post sent"}},
    {"agent": "coordinator", "type": "agent_completed", "data": {"summary": "Postmortem complete for INC-STUB"}},
    {"agent": "system", "type": "incident_complete", "data": {"elapsed_ms": 5000, "postmortem": "INCIDENT INC-STUB: Production data quality failure detected in olist_dirty.\n  • olist_order_items: 5,632 seller_id_length_eq_32 violations\n  • olist_customers: 7,955 row_count violations\n  • olist_products: 988 product_category_name violations\nAll 11 assertions pass on the clean olist_source instance. 3 datasets quarantined via DataHub Python SDK."}},
]


async def stub_run(emit):
    """Fire the stub sequence on a 200ms cadence."""
    for event in STUB_SEQUENCE:
        e = {**event, "ts": _now()}
        result = emit(e)
        if hasattr(result, "__await__"):
            await result
        await asyncio.sleep(0.2)
