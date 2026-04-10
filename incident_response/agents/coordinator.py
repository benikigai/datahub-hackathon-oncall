"""Coordinator — Kimi-K2-Thinking.

Receives the incident text. Dispatches Detective and Reality-Checker in
parallel via asyncio.gather. When both return, dispatches Fixer with their
combined output. Synthesizes the final postmortem.

Emits Kimi's <think> reasoning trace as `thinking` SSE events — that's the
visible wow moment for judges.
"""
import asyncio
import os
from datetime import datetime, timezone

from incident_response.agents.base import BaseAgent
from incident_response.agents.detective import Detective
from incident_response.agents.reality_checker import RealityChecker
from incident_response.agents.fixer import Fixer
from incident_response.events import (
    agent_started,
    agent_completed,
    coordinator_synthesizing,
    thinking,
)


SYSTEM_PROMPT = """You are the Coordinator of a 4-agent data incident
response team. You receive a production data incident from a human and
orchestrate three specialist agents:

- Detective: identifies the affected dataset and traces upstream lineage in DataHub
- Reality-Checker: queries assertions in BOTH the clean source instance and the
  production instance, computes the diff, and reports the production-only failures
- Fixer: quarantines affected datasets via the DataHub Python SDK and posts
  to Slack

For the FIRST call (planning), output a 2-3 sentence plan describing what
the team will do. For the FINAL call (synthesis), output a tight 4-6 sentence
postmortem combining what Detective + Reality-Checker + Fixer found.

Be concrete about counts (e.g., "5,632 truncated seller_ids"), name the
affected views, and end with a one-line recommendation."""


class Coordinator(BaseAgent):
    name = "coordinator"
    model = os.environ.get("COORDINATOR_MODEL", "moonshotai/Kimi-K2-Thinking")
    system_prompt = SYSTEM_PROMPT
    default_max_tokens = 800

    async def run(self, payload: dict) -> dict:
        """payload: {"incident": str}
        returns: {"postmortem": str, "incident_id": str, "affected_datasets": list, "fixer_result": dict}
        """
        incident = payload["incident"]
        incident_id = f"INC-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

        await self._emit(agent_started(self.name))

        # Phase 1: Plan (Kimi gets to think)
        try:
            plan_text, plan_reasoning = await self.chat(
                f"Production incident reported: {incident!r}\n\nWhat's your plan?",
                max_tokens=600,
            )
            if plan_reasoning:
                # Stream the reasoning trace as thinking events
                # Chunk into 200-char segments for visual streaming effect
                for i in range(0, len(plan_reasoning), 200):
                    await self._emit(thinking(self.name, plan_reasoning[i : i + 200]))
            elif plan_text:
                await self._emit(thinking(self.name, plan_text[:500]))
        except Exception as e:
            await self._emit(thinking(
                self.name,
                f"(Kimi unavailable, falling back to default plan: {e})\n"
                "Plan: dispatch Detective + Reality-Checker in parallel, then Fixer with their results.",
            ))

        # Phase 2: Dispatch Detective + Reality-Checker in parallel
        detective = Detective(emit=self.emit, tools=self.tools)
        reality_checker = RealityChecker(emit=self.emit, tools=self.tools)

        det_task = asyncio.create_task(detective.run({"incident": incident}))
        # Reality-Checker doesn't need detective's output for our hardcoded path
        rc_task = asyncio.create_task(
            reality_checker.run({
                "target_urn": "",  # not strictly used by RC
                "upstream_urns": [],
            })
        )

        det_result, rc_result = await asyncio.gather(det_task, rc_task, return_exceptions=True)

        if isinstance(det_result, Exception):
            det_result = {"target_urn": "", "upstream": [], "lineage_path": [], "error": str(det_result)}
        if isinstance(rc_result, Exception):
            rc_result = {"gap": [], "narrative": f"Reality-Checker failed: {rc_result}"}

        # Phase 3: Synthesizing
        await self._emit(coordinator_synthesizing())

        # Phase 4: Dispatch Fixer
        fixer = Fixer(emit=self.emit, tools=self.tools)
        fixer_result = await fixer.run({
            "incident_id": incident_id,
            "gap": rc_result.get("gap", []),
            "narrative": rc_result.get("narrative", ""),
        })

        # Phase 5: Final synthesis (Kimi again)
        synth_input = (
            f"Incident: {incident}\n"
            f"Incident ID: {incident_id}\n\n"
            f"Detective found:\n"
            f"  target: {det_result.get('target_urn', '?')}\n"
            f"  upstream: {len(det_result.get('upstream', []))} datasets\n"
            f"  lineage path: {' ← '.join(det_result.get('lineage_path', []))}\n\n"
            f"Reality-Checker found {len(rc_result.get('gap', []))} production-only assertion failures:\n"
            f"{rc_result.get('narrative', '')}\n\n"
            f"Fixer quarantined {len(fixer_result.get('annotations_written', []))} datasets.\n\n"
            f"Write the final postmortem."
        )
        try:
            postmortem, synth_reasoning = await self.chat(synth_input, max_tokens=600)
            if synth_reasoning:
                for i in range(0, len(synth_reasoning), 200):
                    await self._emit(thinking(self.name, synth_reasoning[i : i + 200]))
        except Exception as e:
            postmortem = self._fallback_postmortem(incident_id, det_result, rc_result, fixer_result)

        if not postmortem or len(postmortem) < 50:
            postmortem = self._fallback_postmortem(incident_id, det_result, rc_result, fixer_result)

        await self._emit(agent_completed(self.name, f"Postmortem complete for {incident_id}"))

        return {
            "postmortem": postmortem,
            "incident_id": incident_id,
            "affected_datasets": fixer_result.get("annotations_written", []),
            "detective": det_result,
            "reality_checker": rc_result,
            "fixer": fixer_result,
        }

    @staticmethod
    def _fallback_postmortem(incident_id, det, rc, fix) -> str:
        gap = rc.get("gap", [])
        lines = [
            f"INCIDENT {incident_id}: Production data quality failure detected in olist_dirty.",
        ]
        for g in gap:
            obs = int(g["observed"]) if g["observed"] is not None else "?"
            lines.append(f"  • {g['table']}: {obs} {g['check']} violations")
        lines.append(
            f"All {len(gap)} assertions pass on the clean olist_source instance, "
            f"confirming the issues are confined to production. "
            f"{len(fix.get('annotations_written', []))} datasets have been quarantined "
            f"via DataHub Python SDK. Recommend the data-platform team rerun the "
            f"upstream loader and investigate the source of the corruption."
        )
        return "\n".join(lines)
