"""NL → DataHub GraphQL translator.

Backend: Nebius (OpenAI-compatible).

Two modes via NL_TO_GRAPHQL_MODE env var:
- "plan_b" (default): base Llama 3.1 8B + in-context seed examples in the system prompt
- "lora": fine-tuned LoRA endpoint (set NL_TO_GRAPHQL_MODEL to the deployed model name)

Either way, all tool callers use the same `nl_to_graphql(question)` interface.
"""
import json
import os
from pathlib import Path
from openai import OpenAI, AsyncOpenAI

NEBIUS_BASE_URL = "https://api.studio.nebius.com/v1"

# Resolve paths once
_REPO_ROOT = Path(__file__).parent.parent.parent
_SEEDS_PATH = _REPO_ROOT / "training" / "seeds.jsonl"
_PLAN_B_PROMPT_PATH = _REPO_ROOT / "training" / "plan_b_system_prompt.txt"

_BASE_SYSTEM = (
    "You translate natural language questions about data assets into DataHub "
    "GraphQL read queries. The target is DataHub Core with Olist datasets ingested "
    "under sqlite platform instances olist_source (clean) and olist_dirty (planted "
    "issues). URN format is "
    "urn:li:dataset:(urn:li:dataPlatform:sqlite,<instance>.<table>,PROD). "
    "Return only valid GraphQL, no markdown, no explanation."
)


def _model() -> str:
    return os.environ.get("NL_TO_GRAPHQL_MODEL", "meta-llama/Meta-Llama-3.1-8B-Instruct")


def _mode() -> str:
    return os.environ.get("NL_TO_GRAPHQL_MODE", "plan_b")


def _api_key() -> str:
    key = os.environ.get("NEBIUS_API_KEY", "")
    if not key:
        raise RuntimeError(
            "NEBIUS_API_KEY not set — load via "
            "`op read 'op://Clawdbot/Nebius Token Factory - Datahub Hackathon/notesPlain'`"
        )
    return key


_SYSTEM_PROMPT_CACHE: str | None = None


def _build_plan_b_prompt() -> str:
    """Construct the few-shot system prompt by reading seeds.jsonl."""
    # Prefer pre-built prompt file if present (right terminal may have written one)
    if _PLAN_B_PROMPT_PATH.exists():
        return _PLAN_B_PROMPT_PATH.read_text()

    if not _SEEDS_PATH.exists():
        return _BASE_SYSTEM + "\n\n(No seed examples available yet — generating from base patterns.)"

    examples: list[str] = []
    with open(_SEEDS_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                pair = json.loads(line)
                examples.append(f"USER: {pair['nl']}\nASSISTANT: {pair['graphql']}")
            except (json.JSONDecodeError, KeyError):
                continue

    return _BASE_SYSTEM + "\n\nExamples:\n\n" + "\n\n".join(examples)


def _system_prompt() -> str:
    global _SYSTEM_PROMPT_CACHE
    if _SYSTEM_PROMPT_CACHE is None:
        _SYSTEM_PROMPT_CACHE = _build_plan_b_prompt() if _mode() == "plan_b" else _BASE_SYSTEM
    return _SYSTEM_PROMPT_CACHE


def reload_prompt() -> None:
    """Force re-read of seeds/prompt files (used by tests)."""
    global _SYSTEM_PROMPT_CACHE
    _SYSTEM_PROMPT_CACHE = None


def _strip_fences(text: str) -> str:
    """Remove markdown code fences if the model wrapped the output in them."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Drop opening ```graphql or ``` line
        lines = lines[1:]
        # Drop closing ``` if present
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def nl_to_graphql(question: str, *, max_tokens: int = 600) -> str:
    """Sync NL→GraphQL. Returns the GraphQL string only."""
    client = OpenAI(base_url=NEBIUS_BASE_URL, api_key=_api_key())
    response = client.chat.completions.create(
        model=_model(),
        max_tokens=max_tokens,
        temperature=0.0,
        messages=[
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": question},
        ],
    )
    return _strip_fences(response.choices[0].message.content or "")


async def nl_to_graphql_async(question: str, *, max_tokens: int = 600) -> str:
    """Async variant — used by agents inside the orchestrator."""
    client = AsyncOpenAI(base_url=NEBIUS_BASE_URL, api_key=_api_key())
    response = await client.chat.completions.create(
        model=_model(),
        max_tokens=max_tokens,
        temperature=0.0,
        messages=[
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": question},
        ],
    )
    return _strip_fences(response.choices[0].message.content or "")


if __name__ == "__main__":
    print(f"Model: {_model()}, Mode: {_mode()}")
    out = nl_to_graphql("Find the dataset for the seller performance view in olist_dirty")
    print("---")
    print(out)
