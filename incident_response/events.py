"""Event models for the SSE protocol between orchestrator and dashboard.

Each event is JSON-serializable and emitted by an agent during its run loop.
The dashboard subscribes via /stream and renders into the appropriate pane.

See docs/specs/data-oncall-execution-plan.md § Task L2 and
docs/specs/research/DataHub-Nebius - PROJECT-SPEC.md § 6.
"""
from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field

AgentName = Literal["coordinator", "detective", "reality_checker", "fixer", "system"]

EventType = Literal[
    "agent_started",
    "thinking",
    "nl_query",
    "graphql_generated",
    "graphql_executed",
    "tool_called",
    "agent_completed",
    "coordinator_synthesizing",
    "postmortem_written",
    "slack_posted",
    "incident_complete",
    "error",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Event(BaseModel):
    ts: str = Field(default_factory=_now_iso)
    agent: AgentName
    type: EventType
    data: dict[str, Any] = Field(default_factory=dict)


# ─── Convenience constructors ──────────────────────────────────────────────

def agent_started(agent: AgentName) -> Event:
    return Event(agent=agent, type="agent_started")


def thinking(agent: AgentName, text: str) -> Event:
    return Event(agent=agent, type="thinking", data={"text": text})


def nl_query(agent: AgentName, question: str) -> Event:
    return Event(agent=agent, type="nl_query", data={"question": question})


def graphql_generated(agent: AgentName, graphql: str) -> Event:
    return Event(agent=agent, type="graphql_generated", data={"graphql": graphql})


def graphql_executed(agent: AgentName, summary: str, rows: int = 0) -> Event:
    return Event(agent=agent, type="graphql_executed", data={"summary": summary, "rows": rows})


def tool_called(agent: AgentName, tool: str, args: dict) -> Event:
    return Event(agent=agent, type="tool_called", data={"tool": tool, "args": args})


def agent_completed(agent: AgentName, summary: str) -> Event:
    return Event(agent=agent, type="agent_completed", data={"summary": summary})


def coordinator_synthesizing() -> Event:
    return Event(agent="coordinator", type="coordinator_synthesizing")


def postmortem_written(urn: str, annotation: str) -> Event:
    return Event(
        agent="fixer",
        type="postmortem_written",
        data={"urn": urn, "annotation": annotation},
    )


def slack_posted(channel: str, text: str) -> Event:
    return Event(agent="fixer", type="slack_posted", data={"channel": channel, "text": text})


def incident_complete(elapsed_ms: int, postmortem: str) -> Event:
    return Event(
        agent="system",
        type="incident_complete",
        data={"elapsed_ms": elapsed_ms, "postmortem": postmortem},
    )


def error(agent: AgentName, message: str) -> Event:
    return Event(agent=agent, type="error", data={"message": message})
