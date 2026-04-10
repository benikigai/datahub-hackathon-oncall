# DataHub × Nebius Hackathon — TECH REFERENCE

Day-of reference card. Open this in a second tab during Phase 1 (10:15) and Phase 2 (1:00).

## What is DataHub? (plain English)

Think of it as **Wikipedia \+ Google Maps for your data**. Every table, dashboard, ML model, and pipeline gets a page describing:

- **Schema** — columns and types  
- **Lineage** — graph of upstream/downstream dependencies  
- **Ownership** — who owns it, who to ping  
- **Glossary terms** — "this is PII", "this is the canonical revenue metric"  
- **Quality signals** — last refresh, row counts, anomaly flags  
- **Usage** — who queries it, how often

It's the "context layer" — the missing brain that lets a data team (or an LLM agent) answer "where does this number come from?" without paging a human. A normal LLM can write SQL, but it has no idea which of your 800 tables is the *right* one. DataHub gives it that index.

**Hackathon framing**: DataHub answers "what *should* be true" (metadata). Nebius reasons over it. The **gap between what DataHub claims and what the actual SQLite database contains** is where L5/L6 magic happens.

## DataHub Core vs DataHub Cloud — settled by the kit

**Use DataHub Core (OSS).** This isn't a real choice — the kit only supports Core:

| Signal | What it says |
| :---- | :---- |
| Setup instructions | `pip install acryl-datahub` \+ `datahub docker quickstart` (Core) |
| FAQ "Do I need cloud setup?" | "**No — everything runs locally**" |
| Verify URL | `http://localhost:9002` (Core, default `datahub`/`datahub` login) |
| Reset command | `datahub docker nuke` (Core) |
| Cloud trial process | Requires sales engagement, not provisioned for participants |

### What Cloud-only features you'd lose (none matter for a 6hr build)

SOC2, SLAs, dedicated support, in-VPC remote execution, computational governance workflows, enterprise SSO, advanced AI automation. **All judging-relevant features (catalog, lineage, GraphQL API, Python SDK, MCP server) are in Core.**

## DataHub strengths (what to lean on)

1. **Metadata-as-context for LLMs** — schemas, lineage graphs, ownership, glossary terms, quality signals, usage patterns. Exactly the "context" half of the hackathon theme.  
2. **GraphQL API \+ Python SDK** — easy to query from a Nebius-powered agent.  
3. **MCP server** — production-ready Model Context Protocol server you can wire to Cursor/Claude/your own agent. Block already runs this in production. **This is your L3-L6 unlock.** Docs: `docs.datahub.com/docs/features/feature-guides/mcp`  
4. **Ingestion recipes** — pre-built for the Olist / NYC Taxi / Healthcare datasets, including lineage scripts and metadata enrichment.  
5. **showcase-ecommerce datapack** — 1,050 entities across Snowflake/Looker/PowerBI/Tableau/dbt/Spark to play with before event day.

## DataHub vs Palantir Ontology (mental model)

**They're solving adjacent problems from opposite ends.**

|  | Palantir Ontology | DataHub |
| :---- | :---- | :---- |
| **What it models** | Your *business* (Customers, Aircraft, Missions) as semantic objects | Your *data stack* (tables, columns, dashboards, dbt jobs) as physical assets |
| **Active or passive?** | **Active** — apps run *through* it. AIP agents call it. It IS production. | **Passive** — describes the stack. Apps reference it for context but don't run *through* it. |
| **Layer** | Semantic / business layer (above SQL) | Metadata layer (alongside the warehouse) |
| **Primary verb** | "Take action on a Customer" | "Find the right table" |
| **What breaks if it goes down** | Production apps and decisions | Discoverability and governance reports |

**Palantir Ontology is what you build *on top of*. DataHub is what you look up to know what to build on top of.**

DataHub is roughly what Palantir's data catalog feature inside Foundry is, extracted as a standalone OSS product. Ontology sits on top of that catalog and adds the semantic \+ action layer DataHub doesn't have.

## Is DataHub focused on data accuracy?

**No — it's focused on trust and discoverability.** DataHub is a *trust signal aggregator*, not an accuracy engine. It surfaces what other tools have said about quality (Great Expectations, dbt tests, Monte Carlo) but doesn't compute or check accuracy itself.

This is exactly why **L5 of the hackathon is interesting**: the kit says "the truth is in the GAP" — DataHub claims X, the actual data is Y, and a Nebius agent finds the discrepancy. That gap exists *because* DataHub doesn't do its own accuracy checking. Your L5/L6 agent becomes the missing accuracy layer that closes the loop.

## DataHub business model — open core

DataHub is open-sourced by **Acryl Data** (recently rebranded to DataHub the company). It's the standard "open core" model:

- **DataHub Core (OSS, Apache 2.0)** — full product, runs anywhere, free forever. Built-in MCP server, GraphQL API, Python SDK, lineage, glossary.  
- **DataHub Cloud (paid SaaS)** — same product \+ enterprise glue: SSO, SOC2, RBAC, in-VPC execution agents, SLA, dedicated support, computational governance.

**Same playbook as**: GitLab, Confluent (Kafka), Elastic, MongoDB, HashiCorp, Grafana Labs, dbt Labs, ClickHouse, Supabase, PostHog. The OSS *is* the marketing. Every dev who runs `datahub docker quickstart` is a future enterprise lead.

**Why this matters for the hackathon**: Acryl is unusually generous on the OSS side — most cool stuff (including the MCP server) is in Core. They want the agent ecosystem to grow on top of OSS DataHub, then upsell enterprise teams. **Every impressive demo on OSS DataHub is a marketing asset for them** — building something they can post on their blog is *aligned with their incentives*, which makes you more likely to win.

## What is Nebius?

**Nebius** is an AI-first cloud platform — fast on-demand NVIDIA GPUs \+ a managed inference layer for open-source and frontier models at scale.

For the hackathon you'll use **Nebius Token Factory** as your model API:

- **OpenAI-compatible** — drop into any OpenAI SDK by swapping `base_url`  
- **Endpoint**: `https://api.studio.nebius.com/v1`  
- **60+ models**: DeepSeek, GPT-OSS, Llama, Qwen, Mistral, Gemma, Nemotron  
- **Vision models**: Qwen2.5-VL-72B (unlocks dashboard screenshots, ER diagrams, lineage graph reasoning)  
- **Tool/function calling** supported — required for L3+ agent levels  
- **Streaming responses** supported

## DeepSeek-R1-0528 — why the kit recommends it

It's not random. Reasons:

| Reason | Why it matters here |
| :---- | :---- |
| **Reasoning model (RLHF \+ chain-of-thought)** | Trained to plan multi-step actions before acting — exactly L3-L6 agent behavior |
| **128K context** | Dump entire DataHub lineage graphs \+ schemas \+ glossary into one prompt without RAG gymnastics |
| **Open-weights, no vendor lock-in** | Nebius hosts it cheap; judges can recreate your demo |
| **Strong on tool/function calling** | Required for "Nebius LLM decides what to do → DataHub / SQL / Slack / Jira" |
| **Cheap** | $0.80/$2.40 per M tokens base, $2/$6 fast tier |
| **Latency tradeoff acceptable** | 25s for 250 tokens is slow for chat but fine for agentic workflows where each step does real work |

R1 emits a `<think>` block before its final answer — that's the reasoning trace, and it's the whole point of the model.

**Take**: R1 is the right default for L5/L6 because thinking models shine when there's a real planning/decision step. For L1-L2 (just summarizing metadata), use a faster model — `meta-llama/Meta-Llama-3.1-70B-Instruct` or `Qwen3-235B-A22B` will be 5-10x faster. **Build with R1, swap in a faster model for hot paths.**

## Verified working call

NEBIUS\_API\_KEY=$(env HOME=\~/.config/op/home op read \\

  "op://Clawdbot/Nebius Token Factory \- Datahub Hackathon/notesPlain")

curl https://api.studio.nebius.com/v1/chat/completions \\

  \-H "Authorization: Bearer $NEBIUS\_API\_KEY" \\

  \-H "Content-Type: application/json" \\

  \-d '{

    "model": "deepseek-ai/DeepSeek-R1-0528",

    "max\_tokens": 80,

    "messages": \[{"role":"user","content":"Reply with: HACKATHON KEY OK"}\]

  }'

\# Tested 2026-04-09: HTTP 200, 2.6s, "DATAHUB HACKATHON KEY OK"

## Python (OpenAI SDK) drop-in

from openai import OpenAI

import os

client \= OpenAI(

    base\_url="https://api.studio.nebius.com/v1",

    api\_key=os.environ\["NEBIUS\_API\_KEY"\],

)

response \= client.chat.completions.create(

    model="deepseek-ai/DeepSeek-R1-0528",

    messages=\[

        {"role": "system", "content": "You are a data lineage detective."},

        {"role": "user", "content": "What does this DataHub URN mean?"}

    \],

)

print(response.choices\[0\].message.content)

## Other useful Nebius models for the hackathon

| Model | Use case | Speed |
| :---- | :---- | :---- |
| `deepseek-ai/DeepSeek-R1-0528` | L5/L6 agent reasoning, root-cause analysis | Slow (thinking) |
| `meta-llama/Meta-Llama-3.1-70B-Instruct` | L1-L3 metadata summarization, RAG | Fast |
| `Qwen/Qwen3-235B-A22B` | High-quality planning, multi-step tool use | Medium |
| `Qwen/Qwen2.5-VL-72B-Instruct` | Vision — dashboard screenshots, ER diagrams | Medium |
| `nvidia/nemotron-3-super-120b-a12b` | (used in Injester) general purpose | Fast |
| `mistralai/Mistral-Nemo-Instruct-2407` | Cheap fallback | Very fast |

## Pricing (rough, base tier per M tokens)

| Model | Input | Output |
| :---- | :---- | :---- |
| DeepSeek-R1-0528 | $0.80 | $2.40 |
| DeepSeek-V3-0324 | $0.50 | $1.50 |
| Llama 3.1 70B | $0.13 | $0.40 |
| Qwen2.5-72B | $0.13 | $0.40 |

**Net**: hackathon usage will cost cents, not dollars. Don't rate-limit yourself.

## **The Core Idea**

DataHub is an open-source metadata platform — born at LinkedIn to handle hyperscale data — that acts as the central nervous system for your data stack. The key distinction: **DataHub doesn't store or process your actual data.** It stores *metadata about* your data — the schema, lineage, ownership, quality signals, usage patterns, governance tags, and business definitions.

The insight driving the hackathon's thesis is that most AI systems don't fail because of models — they fail because they lack context. Without it, agents query deprecated tables, hallucinate metrics, and violate governance policies.

## **What DataHub Does With Data — Layer by Layer**

**1\. Ingestion (pulling metadata in)** DataHub automatically collects metadata from your data sources — it has pre-built templates for platforms like Snowflake, BigQuery, Redshift, Databricks, and many more. It connects to over 100 data sources out of the box, with an event-driven architecture that ensures changes propagate in real time rather than as stale snapshots.

What gets ingested: table schemas, column types, data lineage (where data came from and where it flows), usage statistics, ownership info, quality metrics, and operational metadata.

**2\. The Metadata Graph** DataHub uses a schema-first approach to modeling metadata with the Pegasus schema language, and builds a graph of entities (datasets, dashboards, users, pipelines) connected by relationships (OwnedBy, Contains, DerivedFrom). Everything gets a URN — a unique identifier like `urn:li:dataset:(urn:li:dataPlatform:snowflake,mydb.users,PROD)`.

This graph is the real power. It's not a flat catalog — it's a living, queryable knowledge graph of your entire data ecosystem.

**3\. Curation & Enrichment** DataHub enriches raw metadata with business context through glossary management, domain classification, ownership assignment, documentation authoring, and tag management. AI-powered documentation generation can automatically create contextual descriptions based on schema, lineage, and organizational standards.

**4\. Governance & Access Control** DataHub integrates with enterprise identity providers and enforces role-based access controls at the metadata layer. Every agent query is logged with full telemetry — tool name, actor identity, duration, result size — providing audit trails.

**5\. Quality Signals** DataHub supports dataset certification, freshness SLAs, quality scoring, and deprecation tracking. When an agent surfaces a dataset, quality signals travel with it so it can distinguish a certified production table from an experimental dataset with a freshness violation.

## **The MCP Server — Why It Matters for Your Hackathon**

This is the piece most directly relevant to what you're building today. DataHub implements Anthropic's Model Context Protocol (MCP), giving AI agents standardized, real-time access to rich metadata — its meaning, behavior, and rules.

The MCP server exposes these tools to AI agents:

* **`search`** — find datasets, dashboards, etc. with natural language and boolean logic  
* **`get_lineage`** — trace upstream/downstream dependencies with hop control  
* **`get_queries`** — fetch real SQL queries tied to a dataset to understand actual usage  
* **`get_entity`** — pull full metadata for any asset by URN (batch supported)  
* **`list_schema_fields`** — explore large schemas with filtering  
* **`get_lineage_between`** — get the exact transformation path between two assets

Plus mutation tools (v0.5.0+) for adding/removing tags, glossary terms, ownership, domain membership, and descriptions — so agents can write back to the catalog, not just read.

## **The Practical Framing for Today**

The key distinction the DataHub team emphasizes: MCP is the delivery truck; context management is the factory, warehouse, and QA. A raw database connection gives an agent schema info. DataHub gives it schema *plus* lineage, ownership, quality, usage, and business definitions — through the same protocol.

Block (Square/Cash App) is a reference case — they connected their AI agent Goose to DataHub's MCP server across 50+ data platforms. Engineers who previously spent hours tracing dependencies across tools during incidents can now do it in minutes through natural language.

So the hackathon challenge is essentially: **build an AI agent that doesn't just call an LLM, but calls an LLM *with* DataHub's metadata context** — making it aware of what data exists, who owns it, whether it's trustworthy, and what breaks if you change it.

Want me to dig into the specific MCP server setup, the API patterns, or help you brainstorm a track strategy?

