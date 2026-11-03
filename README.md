# data-oncall

**Page a team of agents instead of waking up your on-call engineer.**

> **Status:** Hackathon project — DataHub × Nebius AI Hackathon, Entrepreneurs First, San Francisco, 2026-04-10. **1st place.** Reference build. The hosted site is a static replay of a real run.

[Replay demo](https://datahub-hackathon-oncall.vercel.app) · [Fine-tuned model](https://huggingface.co/BenjaminBear/llama-3.1-8b-datahub-graphql-lora-v1) · [Training run (W&B)](https://wandb.ai/benjamin-shyong-ikigai-endeavors-llc/datahub-graphql-lora/runs/qhmoh063)

## What it does

A four-agent incident response team for data quality bugs. Given a natural-language page such as *"revenue dashboard showing wrong numbers"*, the agents use DataHub as shared metadata memory to:

1. Identify the affected dataset.
2. Trace upstream and downstream lineage.
3. Diff assertion results between two DataHub instances (clean source vs planted-dirty production) to find the gap.
4. Propose a fix and write the postmortem back to DataHub through the Python SDK.
5. Post to Slack.
6. Stream the whole workflow into a four-pane web console.

End to end in 54.8 seconds (median). The planted issues in the demo data: 5,632 truncated `seller_id`s, 7,955 deleted customers and 988 NULL categories in the Olist e-commerce dataset.

## How it works

| # | Agent | Model (all on Nebius, OpenAI-compatible) | Job |
|---|---|---|---|
| 1 | **Coordinator** | Moonshot `Kimi-K2-Thinking` | Long-horizon plan, visible reasoning traces |
| 2 | **Detective** | Meta Llama 3.1 8B + LoRA | NL → DataHub GraphQL, fine-tuned on 300 pairs |
| 3 | **Reality-Checker** | same LoRA endpoint | Verifies Detective's findings with a different system prompt |
| 4 | **Fixer** | MiniMax `MiniMax-M2.5` | Fix proposal and postmortem |

Three labs, four roles, one fine-tune.

```
page (CLI or dashboard TRIGGER)
   └─> Coordinator ──> Detective ──> DataHub GraphQL (lineage, assertions)
            │              └─> Reality-Checker (cross-check clean vs dirty)
            └─> Fixer ──> DataHub SDK (postmortem) ──> Slack
   events ──> FastAPI SSE ──> 4-pane dashboard
```

- `incident_response/` — orchestrator, agents, prompts, tools, triggers
- `gx/` — Great Expectations assertions written to both Olist instances (11 each; 3 fail on the dirty copy)
- `training/` — pair generation, validation and formatting for the Nebius fine-tune
- `dashboard/` — FastAPI + SSE server and the static console (replay mode on Vercel)

Architecture and build plan: [`docs/specs/`](docs/specs/).

## Stack

Python · DataHub (GraphQL + Python SDK) · Great Expectations · Nebius AI Studio (Kimi-K2-Thinking, Llama 3.1 8B LoRA, MiniMax-M2.5) · FastAPI + SSE · Slack webhooks · Vercel (static replay) · Weights & Biases.

## Run locally

Requires two DataHub instances loaded with the Olist dataset (clean and dirty) and a Nebius account.

```bash
pip install -e ".[dev]"
cp .env.example .env          # fill NEBIUS_API_KEY, DATAHUB_GMS_TOKEN, etc.

python gx/setup_gx.py         # 11 assertions on olist_dirty (3 fail = planted issues)
python gx/setup_gx_source.py  # same 11 on olist_source (all pass)

bash scripts/start_demo.sh    # dashboard + backend
python -m incident_response.triggers.page_team "revenue dashboard showing wrong numbers"
```

The original event demo exposed the dashboard through a Tailscale Funnel on a home machine; that setup is not maintained. The Vercel site serves a replay of a recorded end-to-end run.

## Credits

Built by [Ben Shyong](https://github.com/benikigai) with his AI agent Elias (commit author) at the DataHub × Nebius AI Hackathon. Sponsors: DataHub, Nebius.
