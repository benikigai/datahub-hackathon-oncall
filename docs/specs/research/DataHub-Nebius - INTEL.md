# DataHub × Nebius Hackathon — INTEL

🚨 **TODAY IS EVENT DAY** — Friday, April 10, 2026\. Doors open at 9:00 AM at EF SF.

## Core facts

| Field | Value |
| :---- | :---- |
| **Date** | Friday, April 10, 2026 |
| **Time** | 9:00 AM – 5:30 PM Pacific |
| **Venue** | Entrepreneurs First (EF), San Francisco |
| **Format** | In-person, free, max team size 3 (solo OK) |
| **Hosts** | DataHub, Nebius, Entrepreneurs First |
| **Organizers** | Lakshay Nasa, Sophy Li, Orie Bolitho, Alyssa Lee, Alice Lin |
| **Slack** | [https://datahubspace.slack.com/archives/C0AQJQ79SJX](https://datahubspace.slack.com/archives/C0AQJQ79SJX) |
| **Luma** | [https://luma.com/49k20jo8](https://luma.com/49k20jo8) |

## The theme

**"Compute is easy. Context is hard. Build the bridge."**

Build a production-style AI agent where:

- **DataHub** \= context layer (metadata, lineage, governance, glossary, ownership, quality signals)  
- **Nebius** \= reasoning engine (LLM inference via Token Factory, OpenAI-compatible API)

## Schedule

| Time | Activity |
| :---- | :---- |
| 9:00 | Doors open \+ breakfast \+ team formation |
| 9:30 | Welcome \+ briefing |
| 9:45 | Technical keynote |
| 10:15 | **Phase 1 (setup) \+ Problem Statement Revealed** |
| 12:30 | Lunch |
| 1:00 | **Phase 2 (build)** |
| 4:00 | Submissions |
| 5:00 | Demos \+ judging \+ awards \+ happy hour |

## The 6-Level system (the hidden scoring rubric)

The kit explicitly grades ambition by these levels. Winners hit L5/L6.

| Level | Pattern | Trigger | Analogy |
| :---- | :---- | :---- | :---- |
| **L1** | RAG over metadata → static doc | Human asks | Google search → read results |
| **L2** | Feedback loop, Nebius writes back to DataHub | Human triggers pass 1 | Spell-checker re-reads itself |
| **L3** | Agent (human-triggered) | "Fix the dashboard" | Calling a plumber |
| **L4** | Agentic always-on | Event: schema changed | Smoke detector \+ extinguisher |
| **L5** | Metadata vs **real data** gap detector | "Is this data correct?" | Building inspector vs blueprints |
| **L6** | Multi-agent team using DataHub as **shared memory** | "Handle this incident" | Surgical team |

*"DataHub \= context layer | Nebius \= reasoning engine | Together \= every level. Levels 3-4 are same code, different trigger. Level 5 adds real data. Level 6 adds coordination."*

## What you build

A functional enterprise-grade AI agent powered by Nebius inference, grounded in DataHub's real-time metadata. Hands-on with context-aware systems, multi-agent flows, schema introspection, and lineage traversal.

## Datasets — cloned and ready

**Source repo**: [https://github.com/datahub-project/static-assets](https://github.com/datahub-project/static-assets) **Local path on Studio A**: `~/code/datahub-static-assets/datasets/`

### Primary (3 datasets, each engineered for a specific L5/L6 pattern)

| Dataset | Folder size | .db files | Engineered for | L-level fit |
| :---- | :---- | :---- | :---- | :---- |
| **healthcare** | \~30 MB | `healthcare.db` | Quality monitoring, **selective pipeline halting** | **L4/L6** ⭐ |
| **nyc-taxi** | \~173 MB | `nyc_taxi.db` \+ `nyc_taxi_pipeline.db` | Freshness monitoring, staleness detection | **L5** |
| **olist-ecommerce** | \~195 MB | `olist.db` (clean) \+ `olist_dirty.db` (planted issues) | Join validation, schema matching, reconciliation | **L5** |

**Critical insight**: Each dataset has *deliberately planted* quality issues, schema mismatches, or freshness gaps. The hackathon authors built L5 "metadata vs reality" trick cases directly into the data. Read each dataset's README — it tells you exactly what the planted issues are and what they're meant to test.

### Healthcare \= best fit for L6 multi-agent incident response

The healthcare dataset's **forking pipeline** (raw → staging → billing-mart \+ demographics-mart) with **differential downstream impact** is a literal match for the L6 SELECTED-IDEA. Bad billing data should halt `mart_billing` but NOT `mart_demographics`. A smart multi-agent system makes this nuanced call. A naive system halts everything.

### Each dataset folder includes

- `<name>.db` — pre-built SQLite, ready to ingest  
- `ingest.yaml` (or `ingest_*.yaml` variants) — DataHub ingestion recipe  
- `add_lineage.py` — adds view→table lineage to DataHub  
- `add_metadata.py` — adds tags, glossary terms, ownership  
- `create_db.py` — regenerates the .db from source CSV (if needed)  
- `README.md` — full pipeline description, quality issues, table schemas

### Stretch (raw CSVs, no pre-built .db)

| \# | Dataset | Source | Size |
| :---- | :---- | :---- | :---- |
| 1 | Online Retail (UCI) | [https://kaggle.com/datasets/vijayuv/onlineretail](https://kaggle.com/datasets/vijayuv/onlineretail) | \~25 MB |
| 2 | dbt jaffle\_shop | [https://github.com/dbt-labs/jaffle-shop](https://github.com/dbt-labs/jaffle-shop) | tiny |
| 3 | dbt MRR playbook | [https://github.com/dbt-labs/mrr-playbook](https://github.com/dbt-labs/mrr-playbook) | tiny |
| 4 | Chinook | [https://kaggle.com/datasets/ranasabrii/chinook](https://kaggle.com/datasets/ranasabrii/chinook) | \~1 MB |

## Audience profile

- Software & data engineers  
- AI/ML engineers  
- Startup founders & technical practitioners  
- Limited seats, application-reviewed

## Prizes

- Top teams present \+ win prizes  
- Event swag for participants  
- "Additional rewards as teams progress" — kit hints at level-tier rewards

## Key links

- **Onboarding kit PDF**: [https://drive.google.com/file/d/1K2EjCXtmfUohgTJXC5mIIA4myC4d-Nkh/view](https://drive.google.com/file/d/1K2EjCXtmfUohgTJXC5mIIA4myC4d-Nkh/view)  
- **DataHub docs**: [https://docs.datahub.com](https://docs.datahub.com)  
- **DataHub MCP server**: [https://docs.datahub.com/docs/features/feature-guides/mcp](https://docs.datahub.com/docs/features/feature-guides/mcp)  
- **Nebius Token Factory**: [https://tokenfactory.nebius.com](https://tokenfactory.nebius.com)  
- **Token Factory cookbook**: [https://github.com/nebius/token-factory-cookbook](https://github.com/nebius/token-factory-cookbook)  
- **Nebius docs**: [https://docs.nebius.com](https://docs.nebius.com)

Great — you're at the DataHub x Nebius hackathon *today*. Here's the deep dive on what DataHub actually does with data, especially relevant to what you'll be building.

