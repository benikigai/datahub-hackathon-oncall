# DataHub × Nebius Hackathon — Live State Snapshot (2026-04-10)

> Snapshot of current build state, captured 2026-04-10 morning. **This doc is the live source of truth during the build.** The 5 standard PARA docs in this folder (INTEL, TECH-REFERENCE, IDEAS, PREP, SELECTED-IDEA) remain frozen as the pre-event prep snapshot; this doc supersedes them where they overlap.
>
> Origin: Captured from a claude.ai conversation that had read-only Drive access. Synced to Drive via Claude Code (rclone) so it's reachable from any terminal/machine in the fleet.

---

# HACKATHON CONTEXT HANDOFF — DataHub x Nebius
**Date:** Apr 10, 2026 · **Event:** DataHub x Nebius AI Hackathon @ EF SF
**Project:** Healthcare + Multi-Dataset Incident Response (L5+L6 fused)

---

## CURRENT STATE (what's done)

### DataHub Core — RUNNING on Studio A
- **GMS endpoint:** `http://100.114.31.63:8080` (from MBP/Mac Mini via Tailscale)
- **Web UI:** `http://100.114.31.63:9002`
- **From studio-a shell:** `http://localhost:8080` works
- **47 datasets ingested** across 4 platform instances:
  - `healthcare` (sqlite) — 7 datasets, original sample
  - `olist_source` (sqlite) — 14 datasets, 9 tables + 5 views, full lineage, tags (pii/identifier/financial), glossary (Customer Identity, Order Status), 5 team owners
  - `olist_dirty` (sqlite) — 14 datasets, same schema w/ planted quality issues (orphan FKs, truncated seller IDs, NULL categories)
  - `nyc_taxi` (sqlite) — 5 datasets, 3-stage pipeline (raw→staging→mart), 4 lineage relationships, freshness tags
- **Known recipe fix applied:** `include_view_lineage: false` + `include_view_column_lineage: false` in olist recipes (SQLite URN-mismatch bug, add_lineage.py handles lineage separately)
- **Version note:** CLI 1.5.0.6 ahead of GMS 1.4.0.3, non-blocking

### Ingestion commands used (for reference)
```bash
# On studio-a, in ~/code/datahub-static-assets/datasets/olist-ecommerce/
source ~/.venvs/datahub/bin/activate
datahub ingest -c ingest_source.yaml   # then add_lineage.py, add_metadata.py
datahub ingest -c ingest_dirty.yaml
# And in ../nyc-taxi/: datahub ingest -c ingest.yaml
```

---

## LOCKED ARCHITECTURE — L5 + L6 FUSED

### The core insight
- **L5:** Truth lives in the GAP between DataHub's "should be" and reality's "actually is"
- **L6:** Multi-agent team collaborates through DataHub as shared memory
- **Fusion:** Reality-Checker agent specializes in the gap; all other agents delegate verification to it

### Agent team (4 agents)
| Agent | Model | Role |
|---|---|---|
| Coordinator | DeepSeek-R1-0528 (Fast) | Receives incident, delegates, synthesizes |
| Detective | DeepSeek-R1-0528 (Fast) | Lineage traversal, impact analysis |
| Reality-Checker | DeepSeek-R1-0528 (Fast) | THE L5 agent — reads DataHub vs GE, returns gap |
| Fixer | Llama-3.1-8B (base) | Proposes + applies remediation via Python SDK |

### Data flow
```
Raw data (Postgres/SQLite)
    ↓
Great Expectations validates → DataHubValidationAction pushes assertions
    ↓
DataHub holds: schema + lineage + ownership + GE assertions
    ↓
Human triggers: "handle incident on <dataset>"
    ↓
Coordinator delegates to 4 agents in parallel
    ↓
Each agent asks NL questions → fine-tuned Llama → GraphQL → DataHub
    ↓
Reality-Checker computes GAP
    ↓
Fixer writes remediation via Python SDK (not GraphQL mutations)
    ↓
Coordinator synthesizes final report
```

---

## FINE-TUNE PLAN — LOCKED

### Target: Meta-Llama-3.1-8B-Instruct (Nebius Token Factory)
- **Why not Qwen3.5-397B:** Too big, LoRA questionable, wastes capacity on pattern task
- **Why not DeepSeek-R1:** Fine-tuning destroys reasoning capability
- **Why Llama 8B:** Cheapest ($0.02/$0.06 per 1M), fastest (155 tok/s), best LoRA docs, sufficient capacity for narrow NL→GraphQL task

### Task scope — READ QUERIES ONLY
Confirmed from DataHub docs: *"GraphQL mutations are primarily designed to support UI interactions and should generally be avoided in programmatic use cases. For programmatic metadata management, use the Python SDK instead."*

**Therefore:**
- Fine-tune covers: search, dataset lookup, lineage, ownership, assertions, schema fields
- **Writes go through Python SDK:** `DatahubRestEmitter` + `MetadataChangeProposalWrapper`

### Training data
- **Size:** 300 examples, 80/20 split (240 train / 60 val)
- **Format:** JSONL, OpenAI chat format
- **Generation:** DeepSeek-R1 via Nebius Playground, 10 runs of 30 examples each
- **System prompt:** "You translate natural language questions about data assets into DataHub GraphQL read queries. Return only valid GraphQL, no explanation."

### LoRA config
- Rank: 16, alpha: 32
- Learning rate: 2e-4
- Epochs: 3
- Batch size: 4
- Validation metric: % of generated queries that parse AND return non-empty results against live DataHub

### ⚠️ Nebius deprecation warning
Dashboard banner: *"LoRA serverless deployments will be deprecated on Apr 13, 2026"* — 3 days out. Must verify new LoRA deployments still accepted today before investing training time. Fallback = base Llama 8B with in-context examples, or zero-shot Qwen3-Coder-30B.

---

## MCP SERVER — SELF-HOSTED FOR DATAHUB CORE

### Install command
```bash
# Requires uvx (installed via curl -LsSf https://astral.sh/uv/install.sh | sh)
DATAHUB_GMS_URL=http://100.114.31.63:8080 \
DATAHUB_GMS_TOKEN=<PAT> \
uvx mcp-server-datahub@latest
```

### Get Personal Access Token
`http://100.114.31.63:9002/settings/tokens` → Generate new → copy once (only shown once)

### Confirmed MCP tools (read-side)
- `search` — keyword + boolean (`tag:PII`, `(sales OR revenue) AND quarterly`, wildcards `revenue_*`)
- `get_entities` — batch URN fetch
- `get_lineage` — upstream/downstream with hop control
- `get_lineage_paths_between` — exact path + intermediate SQL
- `get_dataset_queries` — real SQL referencing dataset
- `list_schema_fields` — column-level exploration

### Mutation tools (enable with `TOOLS_IS_MUTATION_ENABLED=true`)
`add_tags`, `remove_tags`, `add_terms`, `remove_terms`, `add_owners`, `remove_owners`, `set_domains`, `update_description`, `add_structured_properties`
**But:** docs recommend Python SDK for bulk/programmatic writes.

### Claude Code config pattern
```json
{
  "mcpServers": {
    "datahub": {
      "command": "uvx",
      "args": ["mcp-server-datahub@latest"],
      "env": {
        "DATAHUB_GMS_URL": "http://100.114.31.63:8080",
        "DATAHUB_GMS_TOKEN": "<token>"
      }
    }
  }
}
```

---

## PYTHON SDK PATTERN (for Fixer agent writes)

```python
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.metadata.schema_classes import DatasetPropertiesClass
import datahub.emitter.mce_builder as builder

emitter = DatahubRestEmitter(gms_server="http://100.114.31.63:8080",
                             token="<PAT>")
emitter.test_connection()

mcp = MetadataChangeProposalWrapper(
    entityUrn=builder.make_dataset_urn("sqlite",
        "olist_source.olist_customers", "PROD"),
    aspect=DatasetPropertiesClass(
        description="⚠️ Incident-marked by Fixer agent",
        customProperties={"incident_id": "INC-2026-0410", "status": "quarantined"}
    ),
)
emitter.emit(mcp)
```

**Use MCP (MetadataChangeProposalWrapper), not legacy MCE.** Modern wire format.

---

## GREAT EXPECTATIONS INTEGRATION

```bash
pip install great-expectations 'acryl-datahub[great-expectations]'
great_expectations init
```

Then in GE checkpoint config:
```yaml
action_list:
  - name: datahub_action
    action:
      module_name: datahub.integrations.great_expectations.action
      class_name: DataHubValidationAction
      server_url: http://localhost:8080
```

Write 8–12 expectations targeting planted issues in `olist_dirty` and `healthcare`:
- Orphan FKs → `expect_column_values_to_be_in_set`
- Truncated IDs → `expect_column_value_lengths_to_be_between`
- NULL categories → `expect_column_values_to_not_be_null`
- Freshness → `expect_column_max_to_be_between`

Pre-run GE before demo. Agents read assertions from DataHub via MCP.

> **See also**: `DataHub-Nebius - GX-DEEP-DIVE.md` (sibling doc) for the full GE deep-dive — what GX is, how the action plugin works, what lands in DataHub, the version landmine (must pin GE `<1.0.0`), and a drop-in `setup_gx.py` template tailored to `olist_orders_dataset`.

---

## CRITICAL GOTCHAS

### localhost confusion
Three different "localhosts" in play:
| Where | Resolves to | Works? |
|---|---|---|
| MBP browser → `localhost:8080` | MBP itself | ❌ |
| studio-a shell → `curl localhost:8080` | studio-a loopback → Docker GMS | ✅ |
| DataHub UI ingestion recipe → `localhost:8080` | actions container (NOT studio-a) | ❌ |

**Fix for UI ingestion:** use `http://datahub-gms:8080` (Docker service name).
**Current state:** CLI-based ingestion from studio-a shell works; UI ingestion sources page is cosmetic only for now.

### GraphQL mutations ≠ programmatic writes
Docs explicitly warn against this. Use Python SDK for anything bulk/programmatic.

### Search index lag
DataHub's OpenSearch needs a few seconds to index after ingestion. `add_lineage.py` can miss views on first run — re-run after a pause if it returns 0 lineage relationships.

---

## NEXT ACTIONS (priority order)

1. **Get PAT from DataHub UI** → `http://100.114.31.63:9002/settings/tokens` → name `claude-mcp-elias`
2. **Store PAT** in `~/.config/openclaw/shell-secrets.zsh` (chmod 600)
3. **Install DataHub MCP server** on Mac Mini + MBP (Option C — both machines)
4. **Verify MCP** with test query: "search DataHub for datasets tagged pii" → should return olist customers/reviews/geolocation
5. **Check Nebius LoRA deprecation status** — determines Plan A (fine-tune) vs Plan B (zero-shot)
6. **Generate 300 NL→GraphQL training pairs** via Nebius Playground + DeepSeek-R1
7. **Upload to Nebius Data Lab → Datasets** (train + val JSONL)
8. **Launch Post-training job** → Llama 3.1 8B + LoRA
9. **Write GE expectations** for planted issues in olist_dirty + healthcare
10. **Wire Fixer agent** with Python SDK helper
11. **Rehearse demo** — record backup video

---

## DEMO NARRATIVE

> "Most AI systems fail not because the model is weak, but because they lack context. We built a multi-agent incident response team that solves this at two levels.
>
> **First — the gap.** DataHub tells us what the data should be. Great Expectations tells us what it actually is. Our Reality-Checker agent finds the truth in between.
>
> **Second — the team.** Four specialized agents — Coordinator, Detective, Reality-Checker, Fixer — collaborate through DataHub as shared memory.
>
> **The glue:** a fine-tuned Llama 3.1 on Nebius that translates every agent's natural language into precise DataHub GraphQL on the fly. Base model hit ~50%. Fine-tuned hits 90%+.
>
> DataHub is the context layer. Nebius is the reasoning engine. Together — every level."

---

## KEY FILES ON STUDIO-A

```
~/code/datahub-static-assets/
├── datasets/
│   ├── olist-ecommerce/
│   │   ├── olist.db                    # SQLite source
│   │   ├── ingest_source.yaml          # EDITED (view_lineage: false)
│   │   ├── ingest_dirty.yaml           # EDITED (view_lineage: false)
│   │   ├── add_lineage.py              # Runs after ingest
│   │   ├── add_metadata.py             # Tags, glossary, owners
│   │   └── README.md
│   ├── nyc-taxi/
│   │   ├── ingest.yaml
│   │   └── add_lineage.py
│   └── healthcare/                     # Already ingested from sample-data
└── (git diff: 2 modified files, 2 .bak files — keep the fix)
```

---

## OPEN QUESTIONS

- [ ] Nebius LoRA serverless deployments still accepting new jobs? (deprecation Apr 13)
- [ ] PAT generated and stored?
- [ ] MCP server installed + verified on Mac Mini and MBP?
- [ ] GE expectation suite written for planted issues?
- [ ] Training data generated (300 pairs) and uploaded?
- [ ] Fine-tune job launched?

---

## OLIST PLANTED ISSUES — CONFIRMED FROM KIT README (2026-04-10)

Verified by fetching `datasets/olist-ecommerce/README.md` from `datahub-project/static-assets`. **Earlier speculation about freshness lag, negative prices, future dates, and `'lost'` order_status was wrong — none of those are in the kit.** The actual planted issues are all referential-integrity bugs:

| # | Table | Column | What was done | Scope | Downstream blast radius |
|---|---|---|---|---|---|
| 1 | `olist_customers` | (entire rows) | ~8% of customer rows physically deleted | **7,955 rows** removed (99,441 → 91,486) | `v_order_details` either drops orders (INNER JOIN) or shows NULL customer fields. Orphan FKs from `olist_orders.customer_id`. |
| 2 | `olist_order_items` | `seller_id` | ~5% of values truncated by 1 character (32 → 31 chars) | **5,632 rows** modified | Truncated IDs no longer match `olist_sellers`. `v_seller_performance` undercounts every affected seller's revenue. |
| 3 | `olist_products` | `product_category_name` | ~3% of category values set to NULL | **988 rows** modified | `v_product_sales` joins to `product_category_name_translation`; NULLs silently drop affected products from category aggregations. |

All three use `random.seed(42)` — deterministic, reproducible, identical rows affected on every regeneration. Both `olist.db` (clean) and `olist_dirty.db` ship in the kit at `~/code/datahub-static-assets/datasets/olist-ecommerce/`.

---

## DEMO NARRATIVE — 4 Agents on `olist_dirty` (corrected with real planted issues)

### The setup (45 sec)

Screen layout: top-left "Acme Marketplace" dashboard widget showing seller revenue + category revenue (both wrong because of the planted issues). Top-right empty Slack channel `#data-incidents`. Bottom: trigger CLI.

We open with: *"This dashboard is wrong. We don't know why yet. Watch what happens when we page our incident team."*

```bash
$ python triggers/page_team.py "revenue dashboard showing wrong numbers — investigate"
```

### The 4-pane workflow (~90 sec)

**Pane 1 — Coordinator (R1)**
- Receives the trigger
- `<think>` block scrolls visibly: "Need to identify which dataset backs the dashboard, find what's upstream, validate against reality, propose a fix."
- Dispatches Detective + Reality-Checker in parallel

**Pane 2 — Detective (R1)**
- NL query 1: *"Find the dataset for Acme's seller performance view in olist_dirty"*
  - `nl_to_graphql()` → search for `v_seller_performance` → returns URN
- NL query 2: *"Get all upstream lineage from olist_dirty.v_seller_performance, 2 hops"*
  - `nl_to_graphql()` → lineage query → returns: `olist_order_items` (1 hop), then `olist_orders` + `olist_products` + `olist_sellers` (2 hops)
- NL query 3: *"Find the dataset for product sales view in olist_dirty"* → returns `v_product_sales`
- NL query 4: lineage upstream → returns `olist_order_items`, `olist_products`, `product_category_name_translation`
- **Returns to Coordinator**: *"Both broken views depend on `olist_order_items` and `olist_products`. Reality-Checker should focus there + on `olist_customers` since it's also upstream of orders."*

**Pane 3 — Reality-Checker (R1) — the L5 agent**
- NL query 1: *"Show me all assertions and their latest results for olist_order_items, olist_customers, and olist_products in olist_dirty"*
  - `nl_to_graphql()` → 3 parallel `dataset(urn:...) { assertions { ... } }` queries
- NL query 2: *"Show me the same assertions and results for the same 3 tables but in olist_source instead"*
  - Same queries, different platform instance — this is the L5 multi-instance trick
- **Computes the diff**:
  > "Three assertions pass on `olist_source` but fail on `olist_dirty`. This is the production-only failure set:
  >   1. `olist_order_items.seller_id` length=32: clean has 0 violations, dirty has **5,632** rows truncated to 31 chars. These line items have unmatched FKs to `olist_sellers`. Every aggregate in `v_seller_performance` undercounts by exactly that many line items.
  >   2. `olist_customers` row count=99,441: clean has 99,441 rows, dirty has **91,486**. Missing 7,955 customers. Every order with a customer_id pointing at a deleted row is now an orphan FK; `v_order_details` either drops them or shows NULL customer fields.
  >   3. `olist_products.product_category_name` not null: clean has 0 NULLs, dirty has **988** NULL categories. These products are silently dropped from the category aggregation in `v_product_sales`.
  >
  > **The dashboard is wrong because the upstream `olist_dirty` instance has 3 distinct referential-integrity bugs that all silently undercount the views on top of it.**"
- Returns gap report to Coordinator

**Pane 4 — Fixer (Llama 8B base)**
- Receives gap report + lineage report
- Generates Python SDK calls (not GraphQL — DataHub docs explicitly recommend SDK for writes):

```python
# Quarantine the 3 affected tables in olist_dirty with incident annotation
for urn in [
    builder.make_dataset_urn("sqlite", "olist_dirty.olist_order_items", "PROD"),
    builder.make_dataset_urn("sqlite", "olist_dirty.olist_customers", "PROD"),
    builder.make_dataset_urn("sqlite", "olist_dirty.olist_products", "PROD"),
]:
    emitter.emit(MetadataChangeProposalWrapper(
        entityUrn=urn,
        aspect=DatasetPropertiesClass(
            description="⚠️ INC-2026-0410: quarantined by Fixer agent",
            customProperties={
                "incident_id": "INC-2026-0410",
                "status": "quarantined",
                "root_cause": "upstream loader corruption",
            },
        ),
    ))
```

- Posts to Slack:
  ```
  🚨 INC-2026-0410: revenue + seller dashboards impaired
  Root cause: 3 upstream tables corrupted in olist_dirty
    • olist_order_items: 5,632 truncated seller_ids → v_seller_performance broken
    • olist_customers:   7,955 deleted rows → v_order_details orphaned
    • olist_products:    988 NULL categories → v_product_sales drops them
  Action: 3 tables quarantined in DataHub. @data-platform paged.
  Compare olist_source (clean baseline) to confirm — all 9 assertions pass there.
  ```

### The reveal (60 sec)

- Coordinator synthesizes everything into a postmortem
- Writes it back to DataHub via SDK as a new annotation on `olist_order_items`
- Refresh DataHub UI tab — the dataset page now shows **"⚠️ INC-2026-0410: quarantined by Fixer agent"** as a fresh annotation
- Slack channel has the post
- 4-pane console shows the full timeline

**Closing line**: *"Compute is easy. Context is hard. We just paged a team of agents that read 14 datasets across two parallel platform instances, traced 6 upstream relationships, validated 9 assertions in both instances, found 3 distinct quality bugs, proposed a fix, and wrote the postmortem back to the same metadata graph they read from. In 90 seconds. DataHub is the context layer. Nebius is the reasoning engine. Together — every level."*

### Why this beats my earlier (wrong) demo narrative

| Old narrative (speculation) | New narrative (real planted issues) |
|---|---|
| Negative prices, future dates, `'lost'` status, freshness lag | Truncated FKs, deleted rows, NULL category joins |
| Single table focus (`olist_orders`) | 3 affected tables, traced via lineage to 2 broken views |
| GX validates real data and finds problems | GX validates the SAME schema in TWO platform instances; the diff is the incident |
| Reality-Checker is just "GX results in DataHub" | Reality-Checker computes the **cross-instance diff** — clean baseline vs dirty production |
| Fix story is hand-wavy | Fix story is concrete: quarantine the 3 tables, page the 5 owners, escalate the upstream loader |
| L5 framing: "metadata vs reality" | L5 framing: "the diff between two parallel data realities, both indexed by the same metadata graph" |

**The new framing is also closer to a real-world enterprise pattern**: every data team has staging vs production, and the question "what's different about prod that broke the view?" is exactly what DataHub Cloud sells against. Judges from DataHub will recognize the framing instantly.
