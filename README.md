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
pip install -e ".[dev]"
cp .env.example .env
# Fill in NEBIUS_API_KEY and DATAHUB_GMS_TOKEN

# Run the assertion writer against both olist instances
python gx/setup_gx.py        # writes 11 assertions on olist_dirty (3 fail = planted issues)
python gx/setup_gx_source.py # writes the same 11 assertions on olist_source (all pass)

# Start the demo (dashboard + Tailscale Funnel public URL)
bash scripts/start_demo.sh
# → prints a public HTTPS URL anyone can hit

# Trigger an incident from the CLI
python -m incident_response.triggers.page_team "revenue dashboard showing wrong numbers"
# Or click TRIGGER in the dashboard
```

## Hosted instance

The live demo runs on the Mac Mini (`eliass-mac-mini`) and is exposed publicly via Tailscale Funnel at:

**🌐 https://eliass-mac-mini.tail365038.ts.net:10001/**

To start it: `bash scripts/start_demo.sh`
To stop it:  `bash scripts/stop_demo.sh`

The public URL serves the same FastAPI backend that calls real DataHub on Studio A and real Nebius models — no fakes, no static screenshots. Verified working end-to-end through the funnel: 56 events, 54.8s elapsed, 3 datasets quarantined.

## Demo

`bash scripts/start_demo.sh` — boots the dashboard + Tailscale Funnel and prints the public URL. Open it in two browser tabs (one for the dashboard, one for DataHub at `http://100.114.31.63:9002` over Tailscale) and click TRIGGER.

## Architecture

See `docs/specs/research/DataHub-Nebius - PROJECT-SPEC.md` for the locked architecture.

See `docs/specs/data-oncall-execution-plan.md` for the build plan.

See `docs/specs/dashboard-design.md` for the dashboard layout.

## Demo narrative

See `docs/specs/research/DataHub-Nebius - STATE-2026-04-10.md` § "Demo Narrative" for the full 4-pane walkthrough with real planted-issue counts (5,632 truncated seller_ids, 7,955 deleted customers, 988 NULL categories).
