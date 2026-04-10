# Dashboard Design — data-oncall

> Visual reference for the middle terminal building `dashboard/`. Read alongside Task M3 in `data-oncall-execution-plan.md`.
> The agent dashboard is one of two visible artifacts during the demo (the other is the DataHub UI in a second browser tab).

## TL;DR

Single-page vertical-scroll dashboard. Tells **two stories**:

1. **The fine-tune story** (top static panel) — *"we picked the right models, fine-tuned Llama, here's the proof"*
2. **The agent story** (live console) — *"watch 4 agents collaborate via DataHub in 90 seconds"*

Plus DataHub UI in a separate browser tab as the *"proof landed in the metadata graph"* reveal.

---

## Layout (one page, top to bottom)

```
┌──────────────────────────────────────────────────────────────────────────┐
│ DATA-ONCALL                          ⏱ 00:00 IDLE          💰 $0.0000    │
│                                                                          │
│ ┌──────────┬──────────┬──────────┬──────────┐  ← top stats bar (sticky) │
│ │ COORD    │ DETECTIVE│ REAL-CHK │  FIXER   │     4 model badges        │
│ │ Kimi-K2  │ Llama+LoRA│ (same)  │ MiniMax  │     cost/speed each       │
│ │$0.6/$2.5 │ $0.03/.09 │         │ $0.3/$1.2│                          │
│ └──────────┴──────────┴──────────┴──────────┘                          │
└──────────────────────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────────────────────┐
│  FINE-TUNE STORY                                                         │
│                                                                          │
│  Base Llama 3.1 8B → Llama 3.1 8B + LoRA (300 pairs)                    │
│                                                                          │
│   Base accuracy:        ████████░░░░░░░░░░░░  50%                       │
│   Fine-tuned accuracy:  ██████████████████░░  90%                       │
│   Improvement:          +40 points                                       │
│                                                                          │
│   Training set: 240 pairs · Validation set: 60 pairs · 8 query patterns │
│   LoRA: rank 16 · alpha 32 · LR 2e-4 · 3 epochs · ~25 min training      │
│                                                                          │
│   [Sample seed pair, syntax-highlighted GraphQL via Prism.js]           │
└──────────────────────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────────────────────┐
│  INCIDENT TRIGGER                                                        │
│  ┌────────────────────────────────────────────────────────┐  [TRIGGER]  │
│  │ revenue dashboard showing wrong numbers — investigate   │  [RESET]    │
│  └────────────────────────────────────────────────────────┘             │
└──────────────────────────────────────────────────────────────────────────┘
┌──────────────┬──────────────┬──────────────┬──────────────────────────┐
│ COORDINATOR  │  DETECTIVE   │REALITY-CHECK │      FIXER               │
│ ● thinking   │ ● querying   │ ● diffing    │ ○ waiting                │
│              │              │              │                          │
│ <think>      │ NL: "find    │ ┌─source─┐   │                          │
│ scrolling    │  v_seller_   │ │ ✅ x9  │   │                          │
│ reasoning    │  perf in     │ │ ✅ x3  │   │                          │
│ trace        │  olist_dirty"│ │ ✅ x3  │   │                          │
│              │              │ └────────┘   │                          │
│              │ GraphQL:     │ ┌─dirty──┐   │                          │
│              │ { search(... │ │ ❌ ×1  │   │                          │
│              │              │ │ ❌ ×1  │   │                          │
│              │ ✅ Found URN │ │ ❌ ×1  │   │                          │
│              │              │ └────────┘   │                          │
│ Tokens: 412  │ Tokens: 89   │ ▶ 3 in dirty│ Tokens: 0                │
│ $0.0021      │ $0.0001      │   none in   │ $0.0000                  │
│              │              │   source    │                          │
└──────────────┴──────────────┴──────────────┴──────────────────────────┘
┌──────────────────────────────────────────────────────────────────────────┐
│ POSTMORTEM (populated after Coordinator synthesizes)                     │
│ ⚠️ INC-2026-0410: 3 referential integrity bugs in olist_dirty           │
│   • 5,632 truncated seller_ids → v_seller_performance broken             │
│   • 7,955 deleted customers → v_order_details orphaned                   │
│   •   988 NULL categories → v_product_sales drops them                   │
│                                                                          │
│ Affected datasets:                                                       │
│   → olist_dirty.olist_order_items   [open in DataHub →]                  │
│   → olist_dirty.olist_customers     [open in DataHub →]                  │
│   → olist_dirty.olist_products      [open in DataHub →]                  │
│                                                                          │
│ Total elapsed: 87s · Total cost: $0.0247                                 │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Sections in detail

### 1. Top stats bar (sticky)
- 4 model badges, one per agent
- Each badge shows: agent name, model slug (short form), cost in/out per 1M tokens, region
- Right side: live elapsed timer + live total-cost counter that ticks up during runs

### 2. Fine-tune story panel
- Reads from `dashboard/static/finetune_metrics.json` on page load (no page reload needed when you update the JSON)
- Renders:
  - Base vs fine-tuned accuracy as horizontal progress bars
  - Training set / validation set / pattern count
  - LoRA hyperparameters
  - One sample seed NL→GraphQL pair, syntax-highlighted
- All values are placeholders at build time; you drop real numbers in later

### 3. Incident trigger
- Text input pre-filled with: `revenue dashboard showing wrong numbers — investigate`
- **TRIGGER** button (POSTs to `/trigger`, disables itself while running)
- **RESET** button (POSTs to `/reset`, clears all panes + footer)

### 4. 4-pane live agent console
Each pane:
- Header: agent name + short model badge + status LED (●thinking / ●querying / ●done / ○waiting)
- Body: scrolling event log specific to that agent (NL queries, generated GraphQL, GraphQL results, thinking traces)
- Footer: per-agent token counter + per-agent cost counter

### 5. Postmortem footer
- Hidden until `incident_complete` event fires
- Shows: incident ID, root cause bullet list, affected datasets (with `[open in DataHub →]` deep-links to `http://100.114.31.63:9002/dataset/<urn>`), elapsed time, total cost

---

## Must-have / Should-have / Nice-to-have

### MUST HAVE (Task M3 baseline)
1. Top stats bar with 4 model badges
2. Fine-tune story panel (reads from `finetune_metrics.json`, placeholder values at first)
3. Trigger input + TRIGGER button + RESET button
4. 4-pane live console with agent headers + scrolling event logs
5. Postmortem footer with DataHub deep-links

### SHOULD HAVE (Task M4 — when wiring SSE)
6. Live total-cost counter (ticks up on each `graphql_executed` event)
7. Per-agent token + cost counters
8. Status LEDs with pulse animation
9. Color-coded event types (cyan / magenta / green / red — see palette below)
10. Syntax-highlighted GraphQL via Prism.js (single CDN tag, no build step)

### NICE TO HAVE (new Task M8 stretch — only if M7 finishes by T+1:30)
11. Side-by-side assertion diff in Reality-Checker pane (the L5 visual moment)
12. Pre-demo splash overlay (architecture diagram + "Press TRIGGER to begin")
13. Animated dispatch arrows (Coordinator → Detective + Reality-Checker)
14. Sparkline of past runs (if you trigger more than once)
15. Completion confetti (subtle, brief)

---

## `finetune_metrics.json` schema

Drop this file at `dashboard/static/finetune_metrics.json`. The dashboard reads it on every page load. Update the values whenever the right terminal hands you new numbers — no code changes needed.

```json
{
  "base_model": "meta-llama/Meta-Llama-3.1-8B-Instruct",
  "fine_tuned_model": "meta-llama/Meta-Llama-3.1-8B-Instruct + LoRA",
  "lora_config": {
    "rank": 16,
    "alpha": 32,
    "lr": "2e-4",
    "epochs": 3,
    "batch_size": 4,
    "training_time_min": 25
  },
  "training": {
    "pairs_total": 300,
    "train_pairs": 240,
    "val_pairs": 60,
    "patterns_covered": 8,
    "drop_rate_pct": 20,
    "validated_against": "DataHub Core @ Studio A (real GraphQL execution)"
  },
  "accuracy": {
    "base_pct": 50,
    "fine_tuned_pct": 90,
    "improvement_pct": 40,
    "metric_definition": "% of generated GraphQL that parses AND returns non-empty results"
  },
  "sample_pair": {
    "nl": "Find the dataset for the seller performance view in olist_dirty",
    "graphql": "{ search(input: {type: DATASET, query: \"v_seller_performance\", start: 0, count: 5}) { searchResults { entity { urn ... on Dataset { name platform { name } } } } } }"
  },
  "cost_per_1m": {
    "input_usd": 0.03,
    "output_usd": 0.09
  },
  "labs_represented": ["Moonshot (Beijing)", "Meta (USA)", "MiniMax (Shanghai)"]
}
```

---

## Color palette (CSS variables)

```css
:root {
  --bg-base: #0a0a0f;
  --bg-pane: #13131a;
  --border: #2a2a35;
  --text-primary: #e0e0e6;
  --text-muted: #8a8a95;

  --cyan-nl: #00d4ff;        /* NL queries */
  --magenta-graphql: #ff00aa; /* generated GraphQL */
  --green-success: #00ff88;   /* successful execution */
  --red-error: #ff3355;       /* errors */
  --yellow-warn: #ffcc00;     /* warnings */

  --led-active: #00ff88;
  --led-idle: #444;
}
```

---

## Tech stack

- **Backend**: FastAPI + Server-Sent Events (`sse-starlette` package). No WebSocket needed.
- **Frontend**: Single static HTML page, vanilla JS, no frameworks
- **Syntax highlighting**: Prism.js via CDN
  ```html
  <link href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css" rel="stylesheet">
  <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-graphql.min.js"></script>
  ```
- **No build step.** Just open `dashboard/static/index.html` directly to test.

Total LOC budget: ~600 JS + ~300 CSS + ~150 HTML = ~1,050 lines.

---

## Demo flow (how the dashboard supports the 5-minute demo)

| Time | Audience sees | Presenter says |
|---|---|---|
| 0:00–0:30 | Page loads. Top stats bar + fine-tune story visible. | *"Here's our setup. Four models. Three labs — Moonshot, Meta, MiniMax. Llama 3.1 8B fine-tuned on 300 NL→GraphQL pairs. Base model hit 50%. Ours hits 90%. Now watch what they do."* |
| 0:30–0:45 | Presenter types incident in trigger box, hits TRIGGER. | *"This dashboard is wrong. We don't know why yet. Page the team."* |
| 0:45–1:30 | 4 panes light up. Coordinator's `<think>` block scrolls. Detective fires queries. Reality-Checker shows the side-by-side diff. Cost counter ticks up. | *(let it speak — narrate sparingly: "watch them work in parallel")* |
| 1:30–1:45 | Postmortem appears in footer with deep-links. | *"And there's the synthesis. Three planted bugs found, root cause identified, three datasets quarantined."* |
| 1:45–2:15 | Cmd+Tab to DataHub UI tab, refresh. Annotation banner visible. | *"And here's the same finding written back to the actual metadata catalog. Refresh — there it is. Quarantined by the Fixer agent."* |
| 2:15–2:30 | Cmd+Tab back to dashboard. Final stats visible. | *"Total elapsed: 87 seconds. Total cost: 2 cents. Compute is easy. Context is hard. DataHub is the context layer, Nebius is the reasoning engine — together, every level. Thank you."* |
