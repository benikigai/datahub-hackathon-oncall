"""Fixer — quarantines affected datasets via Python SDK + posts Slack message.

Uses MiniMax-M2.5 to draft the human-readable Slack post; the actual SDK
write is deterministic Python (so the demo doesn't depend on the LLM
generating valid Python).
"""
import os
from datetime import datetime, timezone

# Which "production" instance to write quarantine annotations to.
# Defaults to olist_dirty; override via env to target olist_dirty_2.
DIRTY_INSTANCE = os.environ.get("OLIST_DIRTY_INSTANCE", "olist_dirty")

from incident_response.agents.base import BaseAgent
from incident_response.events import (
    agent_started,
    agent_completed,
    postmortem_written,
    slack_posted,
    tool_called,
)
from incident_response.tools import datahub_sdk, slack


SYSTEM_PROMPT = """You are the Fixer agent in a 4-agent incident response
team. Your job: given a gap report from the Reality-Checker, draft a
concise Slack message for the data-platform team.

The message should:
- Start with 🚨 INCIDENT: + the incident ID
- Bullet the affected tables with row counts
- State what action was taken
- End with a one-line ask for the on-call engineer

5-8 lines max. No headers, no markdown other than bullets and emoji."""


class Fixer(BaseAgent):
    name = "fixer"
    model = os.environ.get("FIXER_MODEL", "MiniMaxAI/MiniMax-M2.5")
    system_prompt = SYSTEM_PROMPT
    default_max_tokens = 500

    async def run(self, payload: dict) -> dict:
        """payload: {"incident_id": str, "gap": list[dict], "narrative": str}
        returns: {"annotations_written": list[str], "slack_posted": bool}
        """
        await self._emit(agent_started(self.name))

        incident_id = payload.get("incident_id", f"INC-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}")
        gap = payload.get("gap", [])
        narrative = payload.get("narrative", "")

        # ─── Write quarantine annotations to DataHub via SDK ─────────────
        urns_written: list[str] = []
        for g in gap:
            table = g["table"]
            urn = datahub_sdk.make_dataset_urn(f"{DIRTY_INSTANCE}.main", table)
            root_cause = f"{int(g['observed']) if g['observed'] is not None else '?'} {g['check']} violations"

            await self._emit(tool_called(
                self.name,
                "datahub_sdk.quarantine_dataset",
                {"urn": urn, "incident_id": incident_id},
            ))
            try:
                datahub_sdk.quarantine_dataset(urn, incident_id, root_cause)
                urns_written.append(urn)
                annotation = f"⚠️ {incident_id}: quarantined ({root_cause})"
                await self._emit(postmortem_written(urn, annotation))
            except Exception as e:
                await self._emit(tool_called(self.name, "error", {"error": str(e)}))

        # ─── Llama drafts the Slack message ───────────────────────────────
        gap_lines = "\n".join(
            f"- {g['table']}: {int(g['observed']) if g['observed'] is not None else '?'} {g['check']} violations"
            for g in gap
        )
        prompt = (
            f"Incident: {incident_id}\n\n"
            f"Gap report:\n{gap_lines}\n\n"
            f"Reality-Checker narrative:\n{narrative}\n\n"
            f"Quarantined {len(urns_written)} datasets via DataHub Python SDK."
        )
        try:
            slack_text, _ = await self.chat(prompt, max_tokens=400)
        except Exception:
            slack_text = self._fallback_slack(incident_id, gap, len(urns_written))

        # Ensure we have something to post
        if not slack_text or len(slack_text) < 20:
            slack_text = self._fallback_slack(incident_id, gap, len(urns_written))

        await self._emit(tool_called(self.name, "slack.post", {"channel": "#data-incidents"}))
        result = slack.post(slack_text, channel="#data-incidents")
        await self._emit(slack_posted("#data-incidents", slack_text[:120]))

        await self._emit(agent_completed(
            self.name,
            f"Quarantined {len(urns_written)} datasets, Slack post {'sent' if result.get('sent') else 'fallback'}",
        ))
        return {
            "annotations_written": urns_written,
            "slack_posted": bool(result.get("sent")),
            "slack_text": slack_text,
            "incident_id": incident_id,
        }

    @staticmethod
    def _fallback_slack(incident_id: str, gap: list[dict], n_quarantined: int) -> str:
        lines = [f"🚨 INCIDENT: {incident_id}"]
        for g in gap:
            obs = int(g["observed"]) if g["observed"] is not None else "?"
            lines.append(f"  • {g['table']}: {obs} {g['check']} violations")
        lines.append(f"Action: {n_quarantined} datasets quarantined in DataHub via SDK.")
        lines.append("@data-platform — please investigate the upstream loader.")
        return "\n".join(lines)
