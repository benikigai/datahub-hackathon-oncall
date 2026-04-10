# DataHub × Nebius Hackathon — SELECTED IDEA

🚀 **GO TIME** — Friday April 10, 2026\. Architecture below is committed; only the prompts swap when the problem statement drops at 10:15.

## Picked: Idea \#1 — Healthcare Incident Response Team (L6)

**Tagline**: *"Page a team of agents instead of waking up an on-call data engineer. They figure out which downstream to halt and which to keep alive."*

## Why this is now the obvious pick

After cloning the official `datahub-project/static-assets` repo, the **healthcare dataset is a literal pre-baked test case for L6 multi-agent coordination**. From its README:

*"A smart quality system should selectively halt based on which mart is impacted — not shut down everything. Negative billing affects `mart_billing` but NOT `mart_demographics`. Invalid ages affect `mart_demographics` but NOT `mart_billing`. A naive circuit breaker halts everything. A smart one halts only the affected downstream."*

This is the L6 incident response pattern verbatim. The dataset isn't generic — it was engineered to test exactly what we're building.

## The pitch in one breath

When a quality alert fires on the healthcare data pipeline, four Nebius-powered agents — Coordinator, Detective, Reality-Checker, Fixer — work in parallel using DataHub as shared blackboard memory. They identify which planted quality issue triggered the alert, query the actual SQLite database to confirm, decide *which downstream marts are affected*, and halt only those. The other downstream stays running. Postmortem written back to DataHub. Live demo, 30 seconds.

## The healthcare pipeline (target architecture)

raw\_patients ──→ staging\_patients ──┬──→ mart\_billing       (financial)

                                    └──→ mart\_demographics  (reporting)

### Planted quality issues (from official README)

| Issue | What's planted | Rows | Affects | Impact |
| :---- | :---- | :---- | :---- | :---- |
| Negative billing | `billing_amount` set negative | \~1,100 (2%) | `mart_billing` only | Wrong revenue totals |
| NULL names | `name` set to NULL | \~555 (1%) | `mart_demographics` only | Incomplete records |
| Invalid ages | Ages \< 0 or \> 120 | \~830 (1.5%) | `mart_demographics` only | Impossible age values |
| Date swaps | Admission/discharge swapped | \~275 (0.5%) | `mart_billing` only | Negative length-of-stay |

**The whole point**: a naive system halts both marts when ANY issue fires. A smart L6 system inspects the actual data, traces lineage, and halts ONLY the affected downstream.

## Architecture

                     ┌──────────────────┐

                     │     TRIGGER       │

                     │ "Quality alert on │

                     │   raw\_patients"   │

                     └────────┬──────────┘

                              │

                              ▼

                  ┌─────────────────────┐

                  │    COORDINATOR      │

                  │   (DeepSeek-R1)     │

                  │  Plans \+ dispatches │

                  └──────┬──────────────┘

                         │

       ┌─────────────────┼─────────────────┐

       │                 │                 │

       ▼                 ▼                 ▼

┌──────────────┐ ┌──────────────┐ ┌──────────────┐

│  DETECTIVE   │ │REALITY-CHECK │ │    FIXER     │

│   (Qwen-72B) │ │  (Llama-70B) │ │ (DeepSeek-R1)│

│              │ │              │ │              │

│ DataHub MCP  │ │ SQLite query │ │ DataHub SDK  │

│ Lineage scan │ │ on .db file  │ │ (write)      │

│ Find affected│ │ Count bad    │ │ Halt mart\_X  │

│ downstream   │ │ rows per     │ │ Annotate \+   │

│ marts        │ │ mart         │ │ postmortem   │

└──────┬───────┘ └──────┬───────┘ └──────┬───────┘

       │                │                │

       └────────────────┼────────────────┘

                        │

                        ▼

              ┌─────────────────────┐

              │  DataHub Blackboard │

              │   (shared memory)   │

              │                     │

              │  Each agent reads \+ │

              │  writes findings    │

              │  via DataHub API    │

              └─────────────────────┘

                        │

                        ▼

              ┌─────────────────────┐

              │   DEMO OUTPUT       │

              │  \- Slack post       │

              │  \- "halt mart\_X"    │

              │  \- Postmortem doc   │

              │  \- DataHub annot.   │

              │  \- Live console     │

              └─────────────────────┘

## Tech stack

| Component | Tool | Local path on Studio A |
| :---- | :---- | :---- |
| Orchestration | OpenClaw multi-agent (lifted from RoboStore) | `~/code/incident_response/` |
| LLMs | DeepSeek-R1-0528 (planning), Llama-3.1-70B (fast reads), Qwen-72B (lineage) | via Nebius |
| Inference | Nebius Token Factory | `https://api.studio.nebius.com/v1` |
| Context layer | DataHub Core (local Docker) | `http://100.114.31.63:9002` |
| Real data | `healthcare.db` | `~/code/datahub-static-assets/datasets/healthcare/healthcare.db` |
| Ingestion recipe | `ingest.yaml` (provided) | `~/code/datahub-static-assets/datasets/healthcare/ingest.yaml` |
| Lineage seeding | `add_lineage.py` (provided) | `~/code/datahub-static-assets/datasets/healthcare/add_lineage.py` |
| Metadata seeding | `add_metadata.py` (provided) | `~/code/datahub-static-assets/datasets/healthcare/add_metadata.py` |
| MCP | DataHub MCP server | local |
| Notifications | Slack webhook (or Discord) | env var |
| UI | FastAPI \+ simple dark HTML demo console (lifted from RoboStore) | `~/code/incident_response/ui/` |

## Pre-build status (April 9 night)

### ✅ Done

- [x] DataHub CLI installed in `~/.venvs/datahub/` on Studio A  
- [x] `~/.local/bin/datahub` symlink so `datahub` works on PATH  
- [x] `datahub-project/static-assets` repo cloned to `~/code/datahub-static-assets/`  
- [x] All 3 datasets present with .db files \+ ingest recipes \+ lineage/metadata scripts  
- [x] Nebius API key verified (DeepSeek-R1 round-trip working)  
- [x] PARA docs filed  
- [ ] DataHub Docker stack started — *running now via background quickstart*  
- [ ] Healthcare dataset ingested into DataHub  
- [ ] 4-agent skeleton scaffolded (waiting on user signal — step 4\)

### Folder structure to scaffold (step 4, on Ben's signal)

\~/code/incident\_response/

├── orchestrator.py          \# Coordinator entry point \+ agent dispatch

├── agents/

│   ├── \_\_init\_\_.py

│   ├── base.py              \# Shared Nebius client \+ DataHub blackboard interface

│   ├── coordinator.py       \# Plans investigation, dispatches in parallel

│   ├── detective.py         \# DataHub MCP \+ lineage traversal (find affected marts)

│   ├── reality\_checker.py   \# SQL on healthcare.db, count bad rows per mart

│   └── fixer.py             \# DataHub SDK writes \+ Slack post \+ postmortem

├── tools/

│   ├── datahub\_mcp.py       \# MCP client wrapper

│   ├── datahub\_sdk.py       \# Read/write helpers via Python SDK

│   ├── sqlite\_oracle.py     \# SQL execution against healthcare.db

│   └── slack\_webhook.py     \# Slack post helper

├── prompts/

│   ├── coordinator.txt

│   ├── detective.txt

│   ├── reality\_checker.txt

│   └── fixer.txt

├── triggers/

│   └── fake\_alert.py        \# CLI to fire "negative billing detected" alert

├── ui/

│   └── console.py           \# FastAPI live console (3-pane: agents | timeline | output)

├── pyproject.toml

├── .env.example

└── README.md

## Demo script (5 minutes at 5pm)

1. **Open** (30s) — *"Compute is easy. Context is hard. Today we paged a team of AI agents instead of an on-call data engineer. They figure out which downstream to halt and which to keep alive — like a smart quality circuit breaker."*  
     
2. **Setup** (60s) — Show DataHub UI with the healthcare pipeline already ingested. Point at the lineage graph: `raw_patients → staging_patients → mart_billing` (red) and `→ mart_demographics` (also a downstream). *"DataHub knows the topology. It does NOT know which downstream is affected when bad data appears."*  
     
3. **Trigger** (15s) — Type `python triggers/fake_alert.py "negative billing detected in raw_patients"` and hit enter.  
     
4. **Watch** (90s) — Live console shows 4 agents working in parallel:  
     
   - **Coordinator** plans the investigation  
   - **Detective** traces lineage via DataHub MCP, identifies billing AND demographics as downstream  
   - **Reality-Checker** runs `SELECT COUNT(*) FROM mart_billing WHERE billing_amount < 0` → returns 1,127 bad rows. Then runs same on demographics → returns 0\.  
   - **Fixer** decides: halt `mart_billing`, leave `mart_demographics` running. Posts to Slack. Writes postmortem. Annotates DataHub with the halt decision.

   

5. **Reveal** (60s) — Final output:  
     
   - Slack post: "Halted mart\_billing due to 1,127 negative billing rows. mart\_demographics unaffected, continuing."  
   - Refresh DataHub UI → new annotation appears on `mart_billing` showing "HALTED by agent" with reason  
   - Postmortem doc written  
   - **Cut to**: same demo with invalid ages — agents make the OPPOSITE call. Halt demographics, keep billing.

   

6. **Close** (15s) — *"DataHub is the context layer. Nebius is the reasoning engine. Together they're a smart on-call team that knows the difference between a billing problem and a demographics problem. Thank you."*

## Why each design choice maps to a judging criterion

| Choice | Maps to |
| :---- | :---- |
| 4 agents in parallel via OpenClaw | "Multi-agent coordination" (L6 explicit) |
| DataHub as shared blackboard | "DataHub as context layer" (theme) |
| SQL on real `healthcare.db` | L5 "metadata \+ real data gap" |
| Annotations written back to DataHub | "Feedback loop" (L2) — bonus level coverage |
| Slack post \+ postmortem | "Production-style patterns" (kit language) |
| MCP server integration | "Tool/function calling" \+ DataHub-specific bonus |
| DeepSeek-R1 \+ Llama \+ Qwen mix | Showcases multiple Nebius models |
| Live FastAPI console | Demo polish \+ visible "wow" moment |
| **Selective halt (NOT halt-everything)** | Demonstrates *nuanced* multi-agent decision — not just "agents do something", but "agents make a hard call humans usually make" |

## Risks \+ mitigations

| Risk | Mitigation |
| :---- | :---- |
| Problem statement is wildly different from "healthcare incident response" | Architecture is dataset-agnostic. If problem points at olist or nyc-taxi, swap the .db file \+ ingest recipe \+ agent prompts. The 4-agent topology stays. |
| Nebius latency makes the demo feel slow | Run agents in true parallel (`asyncio.gather`), not sequential. Use Llama 70B for fast paths, R1 only for the final synthesis. |
| DataHub MCP server hard to wire | Have a fallback path that uses raw GraphQL — don't make MCP a hard dependency, make it a "level up". |
| Multi-agent coordination logic flakes mid-demo | Have a recorded backup video of the demo flow as Plan B. Record it at 3:30. |
| Slack webhook fails on venue WiFi | Discord webhook as backup, or just dump to terminal. |
| One agent takes too long, blocks the others | Per-agent timeout \+ graceful degradation in Coordinator. |
| Healthcare ingest fails event day | Pre-ingest tonight on Studio A as part of dress rehearsal. |

## Backup ideas if healthcare doesn't fit the problem

If the problem statement is incompatible with healthcare's selective-halt scenario, fall back to:

- **olist** \+ Idea \#2 (Reality vs Lineage Auditor) — same 4-agent skeleton, reframed as "find the lies in 1,050 entities"  
- **nyc-taxi** \+ Idea \#2 — reframed as "freshness audit" using the 3-day staging lag  
- All 3 datasets → Idea \#3 (Schema-Change Bouncer) using planted quality issues as the schema-change events

The architecture is the moat. The prompts, dataset, and demo arc are disposable.

## Success criteria

- [ ] Hits L6 (multi-agent coordination via DataHub shared memory)  
- [ ] Also hits L2 \+ L4 \+ L5 (writes back to DataHub, event-triggered, queries real data)  
- [ ] Uses the DataHub MCP server  
- [ ] Uses 2+ different Nebius models  
- [ ] Live demo works without venue WiFi (cellular hotspot)  
- [ ] **Demonstrates the *selective* halt — not just halting, but choosing which downstream to halt** (this is the wow)  
- [ ] Total build effort: 6-8 hours of pre-event prep \+ 3 hours on event day

