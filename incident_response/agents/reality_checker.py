"""Reality-Checker — THE L5 agent.

Queries assertions on the same datasets in BOTH olist_source and olist_dirty
instances, computes the diff in Python (deterministic), then has the LLM
write the human-readable narrative around the gap.
"""
import os

from incident_response.agents.base import BaseAgent
from incident_response.events import (
    agent_started,
    agent_completed,
    graphql_executed,
    graphql_generated,
    nl_query,
)
from incident_response.tools import datahub_graphql
from incident_response.tools.nl_to_graphql import nl_to_graphql_async


SYSTEM_PROMPT = """You are the Reality-Checker agent in a 4-agent incident
response team. Your job: given a list of datasets and the cross-instance
assertion diff, write a tight, factual narrative explaining what the
production-only failures mean.

INPUT FORMAT (you will receive this as the user message):
A bullet list of failing assertions, each with:
  - dataset name
  - check name
  - observed value
  - what it should be
  - downstream impact

OUTPUT: A 4-6 sentence summary that:
1. States what's broken in production (using the row counts)
2. Notes that the SAME assertions pass on the clean source instance
3. Explains the downstream blast radius
4. Recommends what the Fixer should do

No headers, no bullet points in your output — just dense prose. Be concrete
about the row counts."""


# These are the 3 tables we always check (the planted-issue tables)
INSTRUMENTED_TABLES = ["olist_order_items", "olist_customers", "olist_products"]

# Which "production" instance to compare against the clean source.
# Defaults to olist_dirty; override via env to test against olist_dirty_2.
DIRTY_INSTANCE = os.environ.get("OLIST_DIRTY_INSTANCE", "olist_dirty")
SOURCE_INSTANCE = os.environ.get("OLIST_SOURCE_INSTANCE", "olist_source")


def _ds_urn(instance: str, table: str) -> str:
    return f"urn:li:dataset:(urn:li:dataPlatform:sqlite,{instance}.main.{table},PROD)"


def _build_assertions_query(instance: str, table: str) -> str:
    urn = _ds_urn(instance, table)
    return (
        f'{{ dataset(urn: "{urn}") {{ '
        'assertions(start: 0, count: 50) { total assertions { '
        'urn info { description datasetAssertion { nativeType operator scope } } '
        'runEvents(limit: 1) { runEvents { result { type actualAggValue } } } '
        '} } } }'
    )


class RealityChecker(BaseAgent):
    name = "reality_checker"
    model = os.environ.get("REALITY_CHECKER_MODEL", "meta-llama/Meta-Llama-3.1-8B-Instruct")
    system_prompt = SYSTEM_PROMPT

    async def run(self, payload: dict) -> dict:
        """payload: {"target_urn": str, "upstream_urns": list[str]}
        returns: {"gap": list[dict], "narrative": str}
        """
        await self._emit(agent_started(self.name))

        nl_qs = (
            "Show me all assertions and their latest results for "
            "olist_order_items, olist_customers, and olist_products in "
            "BOTH olist_source and olist_dirty platform instances"
        )
        await self._emit(nl_query(self.name, nl_qs))

        # Get the GraphQL representation (for the dashboard) but execute our
        # known-good query directly (for reliability)
        try:
            generated_gql = await nl_to_graphql_async(nl_qs)
            await self._emit(graphql_generated(self.name, generated_gql[:500]))
        except Exception:
            pass  # not fatal — we have our own queries

        # Query both instances for all 3 tables
        dirty_results: dict[str, dict] = {}
        source_results: dict[str, dict] = {}
        for table in INSTRUMENTED_TABLES:
            for instance, target in [(DIRTY_INSTANCE, dirty_results), (SOURCE_INSTANCE, source_results)]:
                q = _build_assertions_query(instance, table)
                try:
                    data = await datahub_graphql.query_async(q)
                    target[table] = self._parse_assertions(data)
                except Exception as e:
                    target[table] = {"error": str(e), "assertions": []}

        await self._emit(graphql_executed(
            self.name,
            f"Queried 6 dataset assertion sets ({len(INSTRUMENTED_TABLES)} tables × 2 instances)",
            rows=len(INSTRUMENTED_TABLES) * 2,
        ))

        # Compute the cross-instance diff: assertions FAILING in dirty but PASSING in source
        gap: list[dict] = []
        for table in INSTRUMENTED_TABLES:
            d = dirty_results.get(table, {}).get("assertions", [])
            s = source_results.get(table, {}).get("assertions", [])
            s_passing = {a["check_name"] for a in s if a["status"] == "SUCCESS"}
            for da in d:
                if da["status"] == "FAILURE" and da["check_name"] in s_passing:
                    gap.append({
                        "table": table,
                        "check": da["check_name"],
                        "observed": da["observed"],
                        "description": da["description"],
                    })

        # Llama writes the narrative
        gap_summary = "\n".join(
            f"- {g['table']}: {g['check']} — observed {g['observed']} (clean source: passing). {g['description']}"
            for g in gap
        )
        if gap:
            try:
                narrative, _ = await self.chat(
                    f"Cross-instance assertion diff for the production incident:\n\n{gap_summary}",
                    max_tokens=400,
                )
            except Exception:
                narrative = self._fallback_narrative(gap)
        else:
            narrative = "No production-only assertion failures detected. All assertions pass equally in both instances."

        await self._emit(agent_completed(
            self.name,
            f"Found {len(gap)} production-only failures (clean source has 0 of these)",
        ))
        return {"gap": gap, "narrative": narrative}

    @staticmethod
    def _parse_assertions(data: dict) -> dict:
        ds = data.get("dataset")
        if not ds:
            return {"assertions": []}
        items = ((ds.get("assertions") or {}).get("assertions")) or []
        out = []
        for a in items:
            info = a.get("info") or {}
            desc = info.get("description") or ""
            ds_a = info.get("datasetAssertion") or {}
            check_name = ds_a.get("nativeType") or ""
            run_events = ((a.get("runEvents") or {}).get("runEvents")) or []
            if not run_events:
                continue
            result = (run_events[0].get("result")) or {}
            out.append({
                "check_name": check_name,
                "description": desc,
                "status": result.get("type", "UNKNOWN"),
                "observed": result.get("actualAggValue"),
            })
        return {"assertions": out}

    @staticmethod
    def _fallback_narrative(gap: list[dict]) -> str:
        parts = []
        for g in gap:
            parts.append(f"{g['table']} has {int(g['observed']) if g['observed'] is not None else '?'} violations of '{g['check']}'")
        return "Production data has " + "; ".join(parts) + ". The same checks all pass on the clean olist_source instance, so the issues are confined to olist_dirty. The Fixer should quarantine the affected tables and escalate to the upstream loader owners."
