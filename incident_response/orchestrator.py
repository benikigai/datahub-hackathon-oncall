"""Orchestrator — thin wrapper around Coordinator.

The dashboard server calls `await orchestrator.run(incident, emit)` to
kick off the full 4-agent flow. The Coordinator handles all the actual
dispatching internally.
"""
import time
from typing import Any, Awaitable, Callable

from incident_response.agents.coordinator import Coordinator
from incident_response.events import (
    Event,
    incident_complete,
    agent_started,
)


EmitFn = Callable[[Event], Awaitable[None] | None]


async def run(incident: str, emit: EmitFn) -> dict[str, Any]:
    """Run the full 4-agent incident response flow.

    Args:
        incident: natural-language incident description
        emit: callback that receives Event objects (sync or async)

    Returns:
        {
            "incident_id": str,
            "postmortem": str,
            "affected_datasets": list[str],
            "elapsed_ms": int,
            "detective": dict,
            "reality_checker": dict,
            "fixer": dict,
        }
    """
    start = time.time()
    # System start event
    await _maybe_await(emit(Event(agent="system", type="agent_started", data={"incident": incident})))

    coordinator = Coordinator(emit=emit)
    result = await coordinator.run({"incident": incident})

    elapsed_ms = int((time.time() - start) * 1000)
    result["elapsed_ms"] = elapsed_ms

    # Final completion event
    await _maybe_await(emit(incident_complete(elapsed_ms=elapsed_ms, postmortem=result.get("postmortem", ""))))

    return result


async def _maybe_await(value):
    if hasattr(value, "__await__"):
        await value
