"""BaseAgent — abstract class all 4 agents inherit from.

Each agent owns its model slug, system prompt, and a `run()` coroutine.
Agents emit Events via the `emit` callback to surface their work to the
dashboard SSE stream.
"""
import os
from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable

from openai import AsyncOpenAI

from incident_response.events import Event

NEBIUS_BASE_URL = "https://api.studio.nebius.com/v1"

EmitFn = Callable[[Event], Awaitable[None] | None]


class BaseAgent(ABC):
    name: str = "base"
    model: str = "meta-llama/Meta-Llama-3.1-8B-Instruct"
    system_prompt: str = "You are a helpful assistant."
    default_max_tokens: int = 600

    def __init__(self, *, emit: EmitFn, tools: dict[str, Any] | None = None):
        api_key = os.environ.get("NEBIUS_API_KEY", "")
        if not api_key:
            raise RuntimeError("NEBIUS_API_KEY not set")
        self.client = AsyncOpenAI(base_url=NEBIUS_BASE_URL, api_key=api_key)
        self.emit = emit
        self.tools = tools or {}

    async def _emit(self, event: Event) -> None:
        """Emit an event, handling both sync and async emit callbacks."""
        result = self.emit(event)
        if hasattr(result, "__await__"):
            await result

    async def chat(
        self,
        user_content: str,
        *,
        system_override: str | None = None,
        max_tokens: int | None = None,
        temperature: float = 0.2,
    ) -> tuple[str, str]:
        """Call the agent's model. Returns (content, reasoning) tuple.
        Reasoning is non-empty for Kimi-K2-Thinking, empty for others.
        """
        response = await self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens or self.default_max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_override or self.system_prompt},
                {"role": "user", "content": user_content},
            ],
        )
        msg = response.choices[0].message
        content = (msg.content or "").strip()
        # Kimi-K2-Thinking puts the <think> trace in message.reasoning
        reasoning = (getattr(msg, "reasoning", None) or "").strip()
        return content, reasoning

    @abstractmethod
    async def run(self, payload: dict) -> dict:
        """Each agent implements its own run loop. Returns its output payload."""
        ...
