# data-oncall

> *Page a team of agents instead of waking up your on-call engineer.*

A 4-agent incident response team for data quality bugs. Built for the **DataHub × Nebius hackathon**, April 10, 2026 at EF SF.

## What it does

When paged with a natural-language production data incident, four specialized agents — **Coordinator**, **Detective**, **Reality-Checker**, **Fixer** — collaborate via DataHub as shared metadata memory to:

1. Identify the affected dataset
2. Trace upstream/downstream lineage
3. Compare assertion results across two parallel DataHub instances (clean vs production) to find the gap
4. Propose a fix and write the postmortem back to DataHub via Python SDK
5. Post to Slack
6. Surface the entire workflow live in a 4-pane web console

End-to-end in ~90 seconds.

## The four agents

| # | Agent | Lab | Model | Why this model |
|---|---|---|---|---|
| 1 | **Coordinator** | Moonshot | `Kimi-K2-Thinking` | Long-horizon agentic reasoning with visible `<think>` traces |
| 2 | **Detective** | Meta | `Llama 3.1 8B + LoRA` | Fast, cheap, fine-tuned for NL→GraphQL on 300 pairs |
| 3 | **Reality-Checker** | Meta | (same LoRA endpoint) | Same model, different system prompt |
| 4 | **Fixer** | MiniMax | `MiniMax-M2.5` | Marketed for agentic coding with precision refactoring |

**Three labs, four roles, one fine-tune.** All four hosted on Nebius, all four OpenAI-compatible.

## Quick start

```bash
pip install -e .
cp .env.example .env
# Fill in NEBIUS_API_KEY and DATAHUB_GMS_TOKEN

# Run the GE setup against both olist instances
python gx/setup_gx.py
python gx/setup_gx_source.py

# Start the dashboard
uvicorn dashboard.server:app --port 8001 &

# Trigger an incident
python -m incident_response.triggers.page_team "revenue dashboard showing wrong numbers"
# Or click TRIGGER in the dashboard at http://localhost:8001
```

## Architecture

See `docs/specs/research/DataHub-Nebius - PROJECT-SPEC.md` for the locked architecture.

See `docs/specs/data-oncall-execution-plan.md` for the build plan.

See `docs/specs/dashboard-design.md` for the dashboard layout.

## Demo narrative

See `docs/specs/research/DataHub-Nebius - STATE-2026-04-10.md` § "Demo Narrative" for the full 4-pane walkthrough with real planted-issue counts (5,632 truncated seller_ids, 7,955 deleted customers, 988 NULL categories).
