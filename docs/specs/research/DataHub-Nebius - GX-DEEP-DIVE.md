# DataHub × Nebius Hackathon — Great Expectations Deep Dive

> Day-of reference for the L5 "metadata vs reality gap" half of the build.
> Open this in a tab next to TECH-REFERENCE during Hour 0:30–1:00.

## TL;DR (the one-sentence model)

**Great Expectations is a Python library that runs SQL queries against your tables to check rules you wrote ("this column should never be null"), and DataHub ships a plugin that catches those pass/fail results and stores them as queryable assertion entities on your dataset URN.**

Once it's wired up, every agent can read both "what should be true" (existing DataHub metadata) and "what actually is true" (GX results) through the same GraphQL endpoint. **The L5 gap becomes a one-query difference inside the metadata graph itself.**

---

## 🚨 Version landmine — read this first

The DataHub plugin only supports **Great Expectations `>=0.18.0, <1.0.0`**. It does **NOT** work with GX 1.x (the new "GX Core" rewrite shipped in 2024). DataHub hasn't migrated the plugin yet.

```bash
pip install 'great_expectations>=0.18.0,<1.0.0' \
            'acryl-datahub-gx-plugin' \
            psycopg2-binary
```

Verify after install:
```bash
python -c "import great_expectations; print(great_expectations.__version__)"
# Must print 0.18.x — anything else and the plugin won't load
```

If you get GX 1.x by accident, the failure mode is silent: the action will simply never run, and assertions will never appear in DataHub. Pin the version.

---

## Part 1 — What GX actually does (no DataHub yet)

GX is **pytest for data**. You write assertions about what your data *should* look like, run them against real data, and get pass/fail results.

### The 4 things GX puts on disk

When you run `gx.get_context()` for the first time, GX creates `./great_expectations/`:

```
great_expectations/
├── great_expectations.yml          # Master config — points at datasources
├── expectations/                    # ← YOUR RULES live here as JSON files
│   └── olist_order_items_suite.json
├── checkpoints/                     # ← RUNNABLE BUNDLES live here as YAML
│   └── olist_order_items_checkpoint.yml
└── uncommitted/
    ├── validations/                 # ← RESULTS pile up here as JSON, by run timestamp
    └── data_docs/                   # ← Auto-generated HTML reports
```

### The 4 moving parts mapped onto those folders

| GX object | What it is, concretely | Where it lives |
|---|---|---|
| **Datasource** | A connection string + engine type. "Talk to SQLite (or Postgres) at this URL." | `great_expectations.yml` |
| **Expectation Suite** | A list of rules in JSON. "Column X must not be null. Column Y must be in {A, B, C}." | `expectations/*.json` |
| **Checkpoint** | A bound triple: `(which table, which suite, what to do with results)`. The thing you run. | `checkpoints/*.yml` |
| **Validation Result** | The output of one checkpoint run. Per-expectation pass/fail + observed value + the SQL it ran. | `uncommitted/validations/*.json` |

### What happens mechanically when you call `checkpoint.run()`

This is the part most explanations skip. The magic is that **every expectation compiles to SQL**.

```
You write:
    expect_column_value_lengths_to_equal(column="seller_id", value=32)

GX compiles it to:
    SELECT COUNT(*) FROM olist_order_items WHERE LENGTH(seller_id) != 32;

GX runs it against SQLite via SQLAlchemy.

GX builds a result object:
    {
      "expectation_type": "expect_column_value_lengths_to_equal",
      "kwargs": {"column": "seller_id", "value": 32},
      "success": false,
      "result": {
        "element_count": 112650,
        "unexpected_count": 5632,
        "unexpected_percent": 5.0,
        "partial_unexpected_list": [
          "3504c0cb71d7fa48d967e0e4c94d59d",   # truncated by 1 char (planted)
          "955fee9216a65b617aa5c0531780ce6",
          "1f50f920176fa81dab994f9023523100"   # missing trailing char
        ]
      }
    }
```

This expectation catches one of the 3 planted issues in `olist_dirty`: ~5% of `seller_id` values had their last character truncated, breaking the FK join to `olist_sellers`. The planted-issue counts match the kit README exactly (5,632 affected rows out of 112,650 line items).

Multiply that by ~12 expectations and you get one ValidationResult JSON file containing 12 of those blocks plus a top-level `success: false` if any failed.

**That's literally the entire engine.** GX is a SQL templating layer + a result aggregator. The "Expectation" classes are ~60 prebuilt SQL templates. The "Suite" is a list of which templates to fire. The "Checkpoint" is the trigger that runs them all and collects results.

Standalone, the demo loop is just:
```bash
python setup_gx.py        # writes the suite + checkpoint
python run_checkpoint.py  # runs the SQL, dumps a JSON result, opens HTML docs
```

---

## Part 2 — The "Action" plugin point (the bridge)

GX's Checkpoint has a configurable list called `action_list`. After validation finishes (the SQL has run, the result object exists), GX walks the action_list and calls each action with the result.

A GX "Action" is just a class with this contract:

```python
class MyAction(ValidationAction):
    def _run(self, validation_result_suite, ...):
        # do whatever you want with the results
        # e.g. post to Slack, write to S3, send to DataHub
```

GX ships three default actions:
1. `StoreValidationResultAction` — writes the JSON to `uncommitted/validations/`
2. `UpdateDataDocsAction` — regenerates the HTML report
3. `SlackNotificationAction` — fires a webhook on failure

**`DataHubValidationAction` is just a fourth action in this list, written by DataHub's team and shipped as a separate pip package.** That's the entire integration architecture. Nothing magical — GX has a plugin slot, DataHub shipped a plugin that fits the slot.

Wired up:

```yaml
action_list:
  - name: store_validation_result
    action: { class_name: StoreValidationResultAction }
  - name: datahub_action
    action:
      module_name: datahub_gx_plugin.action
      class_name: DataHubValidationAction
      server_url: http://localhost:8080
```

You're telling GX: "After running validation, also call this DataHub class with the results."

### Who owns what

- **GX** owns the SQL compilation, the suite/checkpoint/result data model, and the action plugin contract.
- **DataHub** owns the `acryl-datahub-gx-plugin` pip package, the URN translation logic, and the GMS REST endpoint that ingests assertions.
- **Joint marketing** exists (GE published a "Better Together" blog post, DataHub has a dedicated integration page) — but the code lives on the DataHub side. GE didn't build a DataHub adapter; DataHub built a Checkpoint Action that hooks into GE's plugin point.

---

## Part 3 — What `DataHubValidationAction` does, line by line

When GX hands the validation result to the DataHub action:

```
1. Read the result object
   ↓
2. For each expectation, build a DataHub Assertion entity:
   - Generate a stable URN like:
     urn:li:assertion:<hash of expectation_type + kwargs>
   - Build an `assertionInfo` aspect describing the rule
     (type=DATASET_COLUMN, scope=COLUMN_VALUES, operator=NOT_NULL,
      parameters={column: "order_id"})
   - Attach it to the dataset URN:
     urn:li:dataset:(urn:li:dataPlatform:sqlite,olist_dirty.olist_order_items,PROD)
   ↓
3. For each expectation result, build an AssertionRunEvent aspect:
   - timestampMillis
   - runId
   - status: COMPLETE
   - result: { type: SUCCESS | FAILURE, actualAggValue: 47, ... }
   ↓
4. POST all of these to DataHub's GMS REST endpoint:
   POST http://localhost:8080/aspects?action=ingestProposal
   ↓
5. DataHub's GMS writes them to:
   - Kafka (MetadataChangeProposal_v1 topic)
   - MySQL (the entity store)
   - Elasticsearch (for search)
   ↓
6. The DataHub UI immediately sees the new aspects and surfaces them
   under the dataset's "Quality" tab.
```

**Critical insight**: DataHub treats assertions as **first-class graph entities**, just like datasets, dashboards, and users. They live in the same graph, addressable by URN, queryable by GraphQL. They're not log entries — they're nodes.

This is the part that makes the L5/L6 demo work.

### Action config — full parameter list

| Param | Required? | What it does |
|---|---|---|
| `server_url` | ✅ | DataHub GMS endpoint, e.g. `http://localhost:8080` |
| `env` | optional | Environment for URN construction. Defaults to `"PROD"`. |
| `platform_alias` | optional | Override the platform name in the URN. Use `"sqlite"` for SQLAlchemy sqlite (matches the kit's DataHub ingestion). |
| `platform_instance_map` | optional | Map GX datasource names → DataHub platform instances |
| `exclude_dbname` | optional | Omit catalog from URNs (Trino/Presto) |
| `convert_urns_to_lowercase` | optional | Normalize URN casing — **set to `True`** to match DataHub ingestion |
| `parse_table_names_from_sql` | optional | Enable SQL parsing for query-based assets. Defaults `false`. |
| `graceful_exceptions` | optional | Suppress runtime errors. Defaults `true`. **Set to `False` during dev** so URN mismatches fail loud. Flip to `True` only for the live demo. |
| `token` | optional | Bearer token for DataHub auth |
| `timeout_sec`, `retry_*` | optional | HTTP retry tuning |
| `extra_headers` | optional | Custom request headers |

### Limitations

- **No GX 1.x support** (see version landmine above)
- **No v2 datasources** (the old `SqlAlchemyDataset` API)
- **No Pandas execution engine** — must be SQLAlchemy or Spark
- **No cross-dataset expectations** — assertions can only reference one table
- Spark engine has only been tested with GE 0.18.0–0.99.x

---

## Part 4 — What you and your agents see in DataHub afterward

### Visually, in the UI

`localhost:9002` → datasets → `olist_dirty.olist_order_items` → **Quality** tab:

```
Assertions on olist_order_items (sqlite, olist_dirty, PROD)

✅ order_id not null                                       passed   2026-04-10 11:12
✅ product_id not null                                     passed   2026-04-10 11:12
❌ seller_id length should equal 32                        FAILED   2026-04-10 11:12
   └── 5,632 rows have length=31 (truncated by 1 char)
✅ price ≥ 0                                               passed
✅ freight_value ≥ 0                                       passed
✅ row count = 112650                                      passed

Assertions on olist_customers (sqlite, olist_dirty, PROD)

❌ row count should equal 99441                            FAILED   2026-04-10 11:12
   └── 91,486 rows present (7,955 deleted — orphan FK risk)
✅ customer_unique_id not null                             passed
✅ customer_zip_code_prefix not null                       passed

Assertions on olist_products (sqlite, olist_dirty, PROD)

❌ product_category_name not null                          FAILED   2026-04-10 11:12
   └── 988 rows have NULL category (silent drop from joins)
✅ product_id unique                                       passed
✅ product_weight_g > 0                                    passed
```

**The same 11 assertions all pass on `olist_source`** — that's the L5 gap. DataHub holds two parallel views of the same schema; only the data inside differs.

Plus a sparkline of historical pass/fail per assertion (if you've run the checkpoint multiple times).

### Programmatically, via GraphQL — this is what your agents call

```graphql
{
  dataset(urn: "urn:li:dataset:(urn:li:dataPlatform:sqlite,olist_dirty.olist_order_items,PROD)") {
    assertions(start: 0, count: 100) {
      assertions {
        urn
        info {
          type
          datasetAssertion {
            scope          # COLUMN_VALUES | DATASET_ROWS | etc.
            operator       # NOT_NULL | UNIQUE | IN | BETWEEN | EQUAL_TO
            fields { path }     # which column
            parameters { value { stringValue } }
          }
          description
        }
        runEvents(limit: 1) {
          runEvents {
            timestampMillis
            status
            result {
              type             # SUCCESS | FAILURE
              actualAggValue   # the observed number
              nativeResults    # full GE result blob as key-value
            }
          }
        }
      }
    }
  }
}
```

The response is a clean JSON document of every assertion + its latest run. **This is the L5 ground truth.**

---

## Part 5 — Why this is exactly what the L5 + L6 demo needs

The North Star is: *"find the gap between what DataHub says should be true and what's actually true."*

After GX + the action have run, here's what's now in DataHub for `olist_order_items` (in the `olist_dirty` instance):

**The "should be" half** — already there from kit ingestion:
- Schema (7 columns: `order_id`, `order_item_id`, `product_id`, `seller_id`, `shipping_limit_date`, `price`, `freight_value`)
- Lineage:
  - Upstream: `olist_orders`, `olist_products`, `olist_sellers` (FK joins)
  - Downstream views: `v_order_details`, `v_seller_performance`, `v_product_sales`
- Ownership: 5 team owners (per kit's `add_metadata.py`)
- Glossary terms: `Order Status`, `Customer Identity`
- Tags: `financial`
- Description: "Order line items — joins orders to products and sellers, drives revenue calculations"

**The "actually is" half** — added by GX via the action:
- 6 assertions on `olist_order_items`, 1 failing → **5,632 rows have truncated `seller_id` (length 31 instead of 32)**
- 3 assertions on `olist_customers`, 1 failing → **7,955 rows missing** (deleted from the table)
- 3 assertions on `olist_products`, 1 failing → **988 rows have NULL `product_category_name`**
- last validation run: 2026-04-10 11:12

**Critical observation**: All the same assertions pass cleanly on the `olist_source` instance. The only difference between the two instances is the data inside. DataHub holds two parallel snapshots of the same schema, and the assertion-result diff between them *is* the production incident.

### The Reality-Checker agent job is now trivially defined

> "Query DataHub for `olist_order_items`, `olist_customers`, and `olist_products` in BOTH the `olist_source` and `olist_dirty` instances. For each assertion, compare the result type across the two instances. Return only the assertions that pass on `olist_source` but FAIL on `olist_dirty` — those are the production-only failures, the actual incident. For each, write one sentence: 'DataHub source says X. Dirty production says Y. Gap: Z rows.'"

That's a pure GraphQL query + a Llama prompt. **No SQL execution at runtime. No data movement.** The agent surfaces a discrepancy that already lives in the metadata graph — which is way more impressive to judges because it proves DataHub *as a context layer* is doing the work.

### And for L6 — the multi-agent payoff

Because assertions are first-class graph entities, **all four agents read them via the same GraphQL interface**. No shared file. No message bus. No state hand-off. They all ask DataHub.

- **Detective** queries downstream lineage from `olist_order_items` → finds `v_seller_performance` and `v_product_sales` views consume it
- **Detective** also traces upstream from `v_seller_performance` → confirms the join path is `v_seller_performance ← olist_order_items ← olist_sellers`
- **Reality-Checker** queries assertions on `olist_order_items` in both instances → finds the seller_id length check passes on `olist_source` but FAILS on `olist_dirty` with 5,632 rows truncated. Computes the blast radius: "5,632 line items have unmatched FKs to `olist_sellers`. Every aggregate in `v_seller_performance` undercounts by exactly that many line items"
- **Reality-Checker** also surfaces the parallel issues on `olist_customers` (7,955 deleted → orphan FK from `olist_orders`) and `olist_products` (988 NULL categories → missing from `v_product_sales`)
- **Fixer** queries ownership → drafts a Slack message to the 5 owners on `olist_order_items` proposing the upstream loader be re-run with the fixed seller_id encoding
- **Coordinator** writes the postmortem **back into DataHub** as a new annotation on `olist_order_items` via Python SDK (not GraphQL — DataHub docs explicitly recommend SDK for programmatic writes)

**DataHub is the blackboard.** Not metaphorically — literally. The agents communicate by reading and writing assertion + annotation + ownership aspects on the same graph nodes.

---

## Part 6 — How GX slots into the build order

### Hour 0:30–1:00 task — precisely scoped

```
Hour 0:30 — pip install (PIN GE TO <1.0!)
   pip install 'great_expectations>=0.18.0,<1.0.0' 'acryl-datahub-gx-plugin'
   # SQLite is built into Python — no driver install needed

Hour 0:35 — bootstrap GX context
   python -c "import great_expectations as gx; gx.get_context()"
   # Creates ./great_expectations/ scaffold

Hour 0:40 — write setup_gx.py
   - Add sqlite datasource pointing at olist_dirty.db
   - Add 3 table assets: olist_order_items, olist_customers, olist_products
   - Build 3 expectation suites with the killer planted-issue check in each
   - Build one checkpoint that runs all 3 suites with DataHubValidationAction

Hour 0:50 — run it twice (once per instance)
   python setup_gx.py             # against olist_dirty.db → 3 failures expected
   python setup_gx_source.py      # against olist.db → 0 failures expected
   # The second run is what gives the Reality-Checker its baseline to diff against

Hour 0:55 — verify in DataHub UI
   open http://100.114.31.63:9002
   - olist_dirty.olist_order_items → Quality tab → seller_id length check FAILED
   - olist_dirty.olist_customers   → Quality tab → row count check FAILED
   - olist_dirty.olist_products    → Quality tab → category null check FAILED
   - olist_source.* (same tables)  → Quality tabs all green
   - If empty: URN mismatch — fix platform_instance_map / convert_urns_to_lowercase
```

### Drop-in `setup_gx.py` template

```python
"""
Validates the 3 tables in olist_dirty that contain the kit's planted issues:
  1. olist_order_items   — 5,632 rows have truncated seller_id (length 31, should be 32)
  2. olist_customers     — 7,955 rows physically deleted (creates orphan FKs in olist_orders)
  3. olist_products      —   988 rows have NULL product_category_name (silent drop from joins)

Run the same script against olist.db (clean source) to confirm 0 failures — that's the
L5 baseline for the Reality-Checker agent to compare against.
"""

import great_expectations as gx

context = gx.get_context()  # creates ./great_expectations/ if missing

# 1. Datasource — point at the dirty SQLite (production simulation)
datasource = context.sources.add_sqlite(
    name="olist_dirty_db",
    connection_string="sqlite:///./data/olist_dirty.db",
)

# Helper to keep the suite construction tight
DATAHUB_ACTION = {
    "name": "datahub_action",
    "action": {
        "module_name": "datahub_gx_plugin.action",
        "class_name": "DataHubValidationAction",
        "server_url": "http://100.114.31.63:8080",  # Studio A GMS via Tailscale
        "platform_alias": "sqlite",
        "platform_instance_map": {"olist_dirty_db": "olist_dirty"},  # match kit ingestion
        "convert_urns_to_lowercase": True,
        "graceful_exceptions": False,  # FAIL LOUD during dev
    },
}
DEFAULT_ACTIONS = [
    DATAHUB_ACTION,
    {"name": "store_validation_result",
     "action": {"class_name": "StoreValidationResultAction"}},
    {"name": "update_data_docs",
     "action": {"class_name": "UpdateDataDocsAction"}},
]

# ─── Table 1: olist_order_items (planted: 5,632 truncated seller_ids) ───────
items_asset = datasource.add_table_asset(
    name="olist_order_items", table_name="olist_order_items"
)
items_suite = context.add_or_update_expectation_suite("olist_order_items_suite")
items_v = context.get_validator(
    batch_request=items_asset.build_batch_request(),
    expectation_suite_name="olist_order_items_suite",
)
items_v.expect_column_values_to_not_be_null("order_id")
items_v.expect_column_values_to_not_be_null("product_id")
items_v.expect_column_values_to_not_be_null("seller_id")
# THE KILLER: seller_ids are 32-char hashes; planted issue truncates ~5% to 31 chars
items_v.expect_column_value_lengths_to_equal("seller_id", value=32)
items_v.expect_column_values_to_be_between("price", min_value=0, max_value=15_000)
items_v.expect_column_values_to_be_between("freight_value", min_value=0, max_value=500)
items_v.save_expectation_suite(discard_failed_expectations=False)

# ─── Table 2: olist_customers (planted: 7,955 rows deleted) ─────────────────
cust_asset = datasource.add_table_asset(
    name="olist_customers", table_name="olist_customers"
)
cust_suite = context.add_or_update_expectation_suite("olist_customers_suite")
cust_v = context.get_validator(
    batch_request=cust_asset.build_batch_request(),
    expectation_suite_name="olist_customers_suite",
)
cust_v.expect_column_values_to_not_be_null("customer_id")
cust_v.expect_column_values_to_not_be_null("customer_unique_id")
cust_v.expect_column_values_to_be_unique("customer_id")
# THE KILLER: clean olist has exactly 99,441 customers; dirty has 91,486
cust_v.expect_table_row_count_to_equal(value=99_441)
cust_v.save_expectation_suite(discard_failed_expectations=False)

# ─── Table 3: olist_products (planted: 988 NULL categories) ─────────────────
prod_asset = datasource.add_table_asset(
    name="olist_products", table_name="olist_products"
)
prod_suite = context.add_or_update_expectation_suite("olist_products_suite")
prod_v = context.get_validator(
    batch_request=prod_asset.build_batch_request(),
    expectation_suite_name="olist_products_suite",
)
prod_v.expect_column_values_to_not_be_null("product_id")
prod_v.expect_column_values_to_be_unique("product_id")
# THE KILLER: ~3% of products have NULL category, breaking the translation join
prod_v.expect_column_values_to_not_be_null("product_category_name")
prod_v.expect_column_values_to_be_between("product_weight_g", min_value=1, max_value=50_000)
prod_v.save_expectation_suite(discard_failed_expectations=False)

# ─── One checkpoint that runs all 3 suites in one shot ─────────────────────
checkpoint = context.add_or_update_checkpoint(
    name="olist_dirty_checkpoint",
    validations=[
        {"batch_request": items_asset.build_batch_request(),
         "expectation_suite_name": "olist_order_items_suite"},
        {"batch_request": cust_asset.build_batch_request(),
         "expectation_suite_name": "olist_customers_suite"},
        {"batch_request": prod_asset.build_batch_request(),
         "expectation_suite_name": "olist_products_suite"},
    ],
    action_list=DEFAULT_ACTIONS,
)

result = checkpoint.run()
print("Success:", result.success)  # expect False — 3 planted issues
print("Validations:", len(result.run_results))  # expect 3
```

**To produce the L5 baseline**: copy this script, rename to `setup_gx_source.py`, swap the connection string to `sqlite:///./data/olist.db`, and change `platform_instance_map` to `{"olist_source_db": "olist_source"}`. Run both. The Reality-Checker agent then has two parallel assertion sets in DataHub to diff.

### The 3 planted issues at a glance

The script above already covers all 3 planted issues. Here's the cheat-sheet mapping each one to the agent that surfaces it during the demo:

| Planted issue | Killer expectation | Affected downstream | Surfaced by |
|---|---|---|---|
| **5,632 truncated `seller_id`s in `olist_order_items`** | `expect_column_value_lengths_to_equal("seller_id", value=32)` | `v_seller_performance` undercounts every affected seller's revenue | Detective traces `v_seller_performance ← olist_order_items`, Reality-Checker reports the gap |
| **7,955 deleted rows in `olist_customers`** | `expect_table_row_count_to_equal(value=99441)` | `v_order_details` either drops orders (INNER JOIN) or shows NULL customer fields (LEFT JOIN) — orphan FKs from `olist_orders` | Detective traces `v_order_details ← olist_customers`, Reality-Checker reports the gap |
| **988 NULL `product_category_name`s in `olist_products`** | `expect_column_values_to_not_be_null("product_category_name")` | `v_product_sales` silently drops uncategorized products from category aggregations | Detective traces `v_product_sales ← olist_products`, Reality-Checker reports the gap |

**The L5 multi-instance trick**: run this script twice — once against `olist.db` (clean source, ingested as `olist_source` instance) and once against `olist_dirty.db` (ingested as `olist_dirty` instance). All 9 assertions PASS on `olist_source`. 3 of them FAIL on `olist_dirty`. The diff between the two assertion sets in DataHub is the literal "should be vs actually is" gap that the Reality-Checker agent surfaces.

### The 12-line expectation cheatsheet (reference card)

```python
# Null / uniqueness / domain
v.expect_column_values_to_not_be_null("col")
v.expect_column_values_to_be_unique("col")
v.expect_column_values_to_be_in_set("col", value_set=[...])
v.expect_column_values_to_match_regex("col", regex=r"...")

# Numeric ranges
v.expect_column_values_to_be_between("col", min_value=0, max_value=120)
v.expect_column_mean_to_be_between("col", min_value=1, max_value=14)
v.expect_column_max_to_be_between("col", min_value="...", max_value="...")  # freshness
v.expect_column_value_lengths_to_be_between("col", min_value=3, max_value=10)

# Cross-column logic
v.expect_column_pair_values_a_to_be_greater_than_b("col_A", "col_B")

# Type / table-level
v.expect_column_values_to_be_of_type("col", "TIMESTAMP")
v.expect_table_row_count_to_be_between(min_value=1000, max_value=10_000_000)
v.expect_table_columns_to_match_ordered_list(column_list=[...])

# Distribution
v.expect_column_proportion_of_unique_values_to_be_between("col", 0.95, 1.0)
v.expect_column_values_to_be_dateutil_parseable("col")
```

GX has ~60 built-ins total — these 14 cover ~90% of demo needs.

---

## Part 7 — Failure modes + fixes

| Symptom | Cause | Fix |
|---|---|---|
| `ImportError: cannot import name 'DataHubValidationAction'` | GE 1.x installed | `pip install 'great_expectations<1.0'` and reinstall |
| Action runs, but no assertions appear in DataHub UI | URN mismatch between GX datasource name and DataHub ingestion | Set `platform_alias="sqlite"`, `convert_urns_to_lowercase=True`, and `platform_instance_map={"olist_dirty_db": "olist_dirty"}` (the GX datasource name on the left, the DataHub platform instance on the right). If still broken, query DataHub for the actual dataset URN and reverse-engineer the mapping. |
| `graceful_exceptions` swallowing errors silently | Default is `true` | Set `graceful_exceptions=False` in dev. Only flip back to `True` for the live demo. |
| Connection refused on `localhost:8080` | DataHub GMS not up yet | `datahub docker quickstart` and wait 60s for Kafka + ES to boot |
| `success: True` but planted issues exist | Expectation thresholds too loose | Tighten ranges or add more specific checks (regex, set membership) |
| All expectations failing identically | Wrong table or empty result set | Check `validator.head()` to confirm rows are loading |

---

## Part 8 — Mental model in one diagram

```
┌────────────────────────────────────────────────────────────────┐
│  GX is a SQL-runner that produces structured pass/fail        │
│  results, with a plugin slot for actions.                     │
│                                                                │
│  DataHub's plugin catches those results and converts them     │
│  into queryable assertion entities on the dataset URN.        │
│                                                                │
│  Agents read those entities via GraphQL alongside             │
│  schema/lineage/ownership — same query path, same auth,       │
│  same graph. The "should be / actually is" gap is now a       │
│  one-query difference in the metadata layer itself.           │
└────────────────────────────────────────────────────────────────┘
```

That's the entire integration. Once GX is running and the action is wired, the rest of the stack (DataHub, the four agents, the GraphQL fine-tune) doesn't have to know GX exists — it just sees richer metadata on the dataset.

---

## Sources

- **DataHub × GE integration docs**: https://docs.datahub.com/docs/metadata-ingestion/integration_docs/great-expectations
- **DataHubValidationAction source on GitHub**: https://github.com/datahub-project/datahub/blob/master/metadata-ingestion/integration_docs/great-expectations.md
- **"Better Together" GE blog post**: https://greatexpectations.io/blog/better-together-datahub-and-great-expectations/
- **Working demo repo (postgres + DataHub)**: https://github.com/sarubhai/great_expectations_demo
- **GX Core 1.x intro (for reference, NOT what you'll use)**: https://docs.greatexpectations.io/docs/core/introduction/gx_overview
- **GX 0.18 expectation gallery**: https://greatexpectations.io/expectations
