# DataHub × Nebius Hackathon — PROJECT SPEC

> **Master architectural reference for the 3-terminal build.**
> Read this before starting any code in any terminal. It defines ownership, interfaces, file structure, and integration contracts.
>
> Live source of truth — supersedes anything in INTEL/IDEAS/SELECTED-IDEA where they conflict.

## 1. Mission

Build a 4-agent incident response team that, when paged with a natural-language production incident, automatically:

1. Identifies the affected dataset
2. Traces upstream/downstream lineage via DataHub
3. Compares assertion results across `olist_source` (clean) and `olist_dirty` (planted issues) to find the production-only failures
4. Proposes a fix and writes the postmortem back into DataHub via Python SDK
5. Posts to Slack
6. Surfaces the entire workflow live in a 4-pane web console for judges

End-to-end demonstrable in ~90 seconds at the 5pm showcase.

---

## 2. Architecture (locked)

```
   [ Trigger CLI ]                    [ Browser tab 1: Agent Console ]
        │                             [ Browser tab 2: DataHub UI    ]
        ▼                                       ▲
[ Coordinator (Kimi-K2-Thinking) ]             │ SSE
        │                                       │
   ┌────┴───────────┬─────────────┐             │
   ▼                ▼             ▼             │
[Detective]   [Reality-Chk]   [Fixer]           │
[Llama LoRA]  [Llama LoRA]    [MiniMax M2.5]    │
   │                │             │             │
   └────────────┬───┴─────────────┘             │
                ▼                                │
         [ DataHub @ Studio A 100.114.31.63 ]   │
         [ Python SDK + GraphQL                ]│
                │                                │
                └────────────────────────────────┘
                       (live event stream)
```

### Three labs, four roles, one fine-tune

| Lab | Role |
|---|---|
| **Moonshot (Beijing)** | Coordinator — long-horizon agentic reasoning |
| **Meta (USA)** | Detective + Reality-Checker — fine-tuned NL→GraphQL |
| **MiniMax (Shanghai)** | Fixer — agentic code generation |

The pitch line: *"We didn't use one model. We picked three, each for what it's best at — and we fine-tuned a fourth. All four hosted on Nebius, all four OpenAI-compatible, one unified demo."*

---

## 3. Model lineup (LOCKED)

| # | Agent | Lab | Nebius slug | Cost in/out per 1M | Speed | Region |
|---|---|---|---|---|---|---|
| 1 | **Coordinator** | Moonshot | `moonshotai/Kimi-K2-Thinking` | $0.60 / $2.50 | 45.7 tok/s | eu-north1 Base |
| 2 | **Detective** | Meta | `meta-llama/Meta-Llama-3.1-8B-Instruct` + LoRA | $0.03 / $0.09 | 155 tok/s | eu-north1 Fast |
| 3 | **Reality-Checker** | Meta | (same LoRA endpoint as #2) | (same) | (same) | (same) |
| 4 | **Fixer** | MiniMax | `MiniMaxAI/MiniMax-M2.5` | $0.30 / $1.20 | 36.8 tok/s | us-central1 Base |

### ⚠️ Verify before launch

| Slug | Status | Risk |
|---|---|---|
| `moonshotai/Kimi-K2-Thinking` | Confirmed available on Nebius (multiple provider listings reference it) | Low |
| `meta-llama/Meta-Llama-3.1-8B-Instruct` | Confirmed available on Nebius (kit-recommended) | None |
| `MiniMaxAI/MiniMax-M2.5` | ✅ **Confirmed available on Nebius Playground** (verified 2026-04-10) — visible at the front of the catalog | None |

### Why these four

- **Coordinator → Kimi-K2-Thinking**: Built for long-horizon agentic reasoning with interleaved tool calls. Has visible `<think>` blocks (the wow moment for judges). 256K context window means we never have to truncate the orchestration history.
- **Detective + Reality-Checker → Llama 3.1 8B + LoRA**: Cheapest, fastest model on Nebius. Fine-tuned on 300 NL→GraphQL pairs for the specific task of generating valid DataHub GraphQL. Same endpoint, two roles via different system prompts.
- **Fixer → MiniMax-M2.5**: Marketed as "agentic coding with precision refactoring" — exactly the Python SDK code generation we need. The marketing copy writes itself.

---

## 4. Repo structure (locked)

```
~/code/datahub-nebius-hackathon/
├── README.md                              # 5-min demo script
├── pyproject.toml
├── .env.example
│
├── incident_response/                     # ⬅ LEFT terminal owns
│   ├── __init__.py
│   ├── orchestrator.py                    # Async runner: dispatch + collect
│   ├── events.py                          # Event Pydantic models
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py                        # BaseAgent + Nebius client
│   │   ├── coordinator.py                 # Kimi-K2-Thinking
│   │   ├── detective.py                   # Llama LoRA, lineage focus
│   │   ├── reality_checker.py             # Llama LoRA, assertions diff
│   │   └── fixer.py                       # MiniMax-M2.5, code gen
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── nl_to_graphql.py               # Calls fine-tuned LoRA endpoint
│   │   ├── datahub_graphql.py             # POST to GMS /api/graphql
│   │   ├── datahub_sdk.py                 # Python SDK writes (Fixer)
│   │   └── slack.py                       # Webhook for postmortem
│   ├── prompts/
│   │   ├── coordinator.txt
│   │   ├── detective.txt
│   │   ├── reality_checker.txt
│   │   └── fixer.txt
│   └── triggers/
│       └── page_team.py                   # CLI entry point
│
├── dashboard/                             # ⬅ MIDDLE terminal owns
│   ├── server.py                          # FastAPI + /stream SSE
│   ├── static/
│   │   ├── index.html                     # 4-pane layout
│   │   ├── style.css                      # Dark theme
│   │   └── app.js                         # SSE client + DOM
│   └── stub_agents.py                     # Fake event stream for UI testing
│
├── gx/                                    # ⬅ LEFT terminal owns
│   ├── setup_gx.py                        # Validates olist_dirty
│   ├── setup_gx_source.py                 # Validates olist (clean baseline)
│   └── data/
│       ├── olist.db                       # symlink → studio-a kit
│       └── olist_dirty.db                 # symlink → studio-a kit
│
└── training/                              # ⬅ RIGHT terminal owns
    ├── seeds.jsonl                        # 8 hand-crafted few-shot examples
    ├── gen_prompt.txt                     # R1 meta-prompt template
    ├── generate.sh                        # 10-batch R1 generation
    ├── validate_pairs.py                  # Parse + execute filter
    ├── format_for_nebius.py               # JSONL chat + 80/20 split
    ├── train.jsonl                        # ⬅ uploaded to Nebius Data Lab
    └── val.jsonl                          # ⬅ uploaded to Nebius Data Lab
```

---

## 5. Agent base class (Python interface)

```python
# incident_response/agents/base.py
from abc import ABC, abstractmethod
from typing import Any, Callable
from openai import AsyncOpenAI
from incident_response.events import Event

class BaseAgent(ABC):
    name: str            # "coordinator" | "detective" | "reality_checker" | "fixer"
    model: str           # Nebius slug
    system_prompt: str   # loaded from prompts/<name>.txt

    def __init__(
        self,
        nebius_api_key: str,
        emit: Callable[[Event], None],   # SSE event emitter
        tools: dict[str, Any],            # nl_to_graphql, datahub_graphql, etc.
    ):
        self.client = AsyncOpenAI(
            base_url="https://api.studio.nebius.com/v1",
            api_key=nebius_api_key,
        )
        self.emit = emit
        self.tools = tools

    @abstractmethod
    async def run(self, payload: dict) -> dict:
        """
        Each agent implements its own run loop.
        Calls self.emit(Event(...)) at meaningful points.
        Returns its output payload to the Coordinator.
        """
        ...
```

Each agent overrides `run()` and emits events as it works. Coordinator calls Detective + Reality-Checker via `asyncio.gather` for parallelism, then awaits both before dispatching Fixer.

---

## 6. SSE event protocol — the contract between LEFT and MIDDLE

The dashboard subscribes to `GET /stream` (Server-Sent Events). Each event is JSON:

```typescript
{
  "ts": "2026-04-10T11:23:45.123Z",       // ISO timestamp
  "agent": "coordinator" | "detective" | "reality_checker" | "fixer" | "system",
  "type": EventType,
  "data": { ... }                          // shape depends on type
}
```

### Event types

| `type` | When fired | `data` shape |
|---|---|---|
| `agent_started` | Agent begins work | `{}` |
| `thinking` | Reasoning trace from Kimi-K2-Thinking `<think>` blocks | `{ "text": "..." }` |
| `nl_query` | Agent poses NL question to `nl_to_graphql` | `{ "question": "..." }` |
| `graphql_generated` | Fine-tuned LoRA returned GraphQL | `{ "graphql": "..." }` |
| `graphql_executed` | DataHub returned a result | `{ "summary": "...", "rows": int }` |
| `tool_called` | Agent invoked a non-LoRA tool (SDK, Slack) | `{ "tool": "...", "args": {...} }` |
| `agent_completed` | Agent returned its output payload | `{ "summary": "..." }` |
| `coordinator_synthesizing` | Coordinator begins final synthesis | `{}` |
| `postmortem_written` | Fixer wrote annotation back to DataHub | `{ "urn": "...", "annotation": "..." }` |
| `slack_posted` | Slack webhook fired | `{ "channel": "...", "text": "..." }` |
| `incident_complete` | Whole flow done | `{ "elapsed_ms": int, "postmortem": "..." }` |
| `error` | Anything went wrong | `{ "agent": "...", "message": "..." }` |

### Example event sequence (the demo flow as JSON)

```json
{"ts":"...","agent":"system","type":"agent_started","data":{}}
{"ts":"...","agent":"coordinator","type":"agent_started","data":{}}
{"ts":"...","agent":"coordinator","type":"thinking","data":{"text":"User reports revenue dashboard is wrong. Need to identify backing dataset, trace lineage, validate against reality, propose fix..."}}
{"ts":"...","agent":"detective","type":"agent_started","data":{}}
{"ts":"...","agent":"reality_checker","type":"agent_started","data":{}}
{"ts":"...","agent":"detective","type":"nl_query","data":{"question":"Find the dataset for v_seller_performance in olist_dirty"}}
{"ts":"...","agent":"detective","type":"graphql_generated","data":{"graphql":"{ search(input: {type: DATASET, query: \"v_seller_performance\", start: 0, count: 5}) { searchResults { entity { urn } } } }"}}
{"ts":"...","agent":"detective","type":"graphql_executed","data":{"summary":"Found 1 dataset","rows":1}}
{"ts":"...","agent":"reality_checker","type":"nl_query","data":{"question":"Show me assertions on olist_order_items in BOTH instances"}}
{"ts":"...","agent":"reality_checker","type":"graphql_executed","data":{"summary":"6 assertions in olist_dirty (1 failing), 6 in olist_source (0 failing)","rows":12}}
{"ts":"...","agent":"detective","type":"agent_completed","data":{"summary":"Lineage: v_seller_performance ← olist_order_items ← olist_sellers (3 hops)"}}
{"ts":"...","agent":"reality_checker","type":"agent_completed","data":{"summary":"3 assertions fail in dirty, pass in source: seller_id length, customer row count, product category null"}}
{"ts":"...","agent":"coordinator","type":"coordinator_synthesizing","data":{}}
{"ts":"...","agent":"fixer","type":"agent_started","data":{}}
{"ts":"...","agent":"fixer","type":"tool_called","data":{"tool":"datahub_sdk","args":{"action":"add_annotation","urn":"urn:li:dataset:(urn:li:dataPlatform:sqlite,olist_dirty.olist_order_items,PROD)"}}}
{"ts":"...","agent":"fixer","type":"postmortem_written","data":{"urn":"urn:li:dataset:(urn:li:dataPlatform:sqlite,olist_dirty.olist_order_items,PROD)","annotation":"⚠️ INC-2026-0410: 5,632 truncated seller_ids quarantined by Fixer agent"}}
{"ts":"...","agent":"fixer","type":"slack_posted","data":{"channel":"#data-incidents","text":"🚨 INC-2026-0410..."}}
{"ts":"...","agent":"system","type":"incident_complete","data":{"elapsed_ms":89123,"postmortem":"..."}}
```

The dashboard renders these into the appropriate pane based on `agent`. Reasoning traces (`thinking`) scroll inside the agent's pane.

---

## 7. Dashboard build brief (for MIDDLE terminal)

### What to build

A FastAPI app at `dashboard/server.py` that:

1. Serves static HTML at `/`
2. `POST /trigger` — accepts `{"incident": "..."}`, kicks off `incident_response.orchestrator.run()` in background
3. `GET /stream` — SSE stream of all events from the current run

### What the HTML looks like

Single-page layout, dark theme, monospace, vanilla JS, NO frameworks:

```
┌────────────────────────────────────────────────────────────────┐
│ ACME INCIDENT RESPONSE — INC-2026-0410        ⏱ 00:23 RUNNING  │
│ "revenue dashboard showing wrong numbers — investigate"        │
└────────────────────────────────────────────────────────────────┘
┌──────────────┬──────────────┬──────────────┬─────────────────┐
│ COORDINATOR  │  DETECTIVE   │REALITY-CHECK │     FIXER       │
│ Kimi-K2      │ Llama+LoRA   │ Llama+LoRA   │  MiniMax M2.5   │
│              │              │              │                 │
│ <thinking>   │ NL: "..."    │ NL: "..."    │ Waiting on      │
│ scrolling    │              │              │ Detective +     │
│ reasoning    │ GraphQL:     │ GraphQL:     │ Reality-Checker │
│ trace here   │ { ... }      │ { ... }      │                 │
│              │              │              │                 │
│              │ ✅ Found URN │ ⏳ Querying  │                 │
│              │              │              │                 │
└──────────────┴──────────────┴──────────────┴─────────────────┘
┌────────────────────────────────────────────────────────────────┐
│ POSTMORTEM (Coordinator final synthesis)                       │
│ ✅ olist_order_items quarantined → see DataHub UI tab          │
└────────────────────────────────────────────────────────────────┘
```

### Stub agents for testing

`dashboard/stub_agents.py` should fire a hardcoded sequence of events on a 200ms cadence so the dashboard can be built without waiting for real agents. Use the example JSON sequence in section 6 as the data.

```python
# dashboard/stub_agents.py
import asyncio, json, time
from incident_response.events import Event

STUB_SEQUENCE = [
    {"agent": "system",       "type": "agent_started",        "data": {}},
    {"agent": "coordinator",  "type": "agent_started",        "data": {}},
    {"agent": "coordinator",  "type": "thinking",             "data": {"text": "User reports revenue dashboard..."}},
    {"agent": "detective",    "type": "agent_started",        "data": {}},
    # ... etc, 20-30 events
    {"agent": "system",       "type": "incident_complete",    "data": {"elapsed_ms": 89123}},
]

async def stub_run(emit):
    for event in STUB_SEQUENCE:
        emit({**event, "ts": time.time()})
        await asyncio.sleep(0.2)
```

### When ready

Hand LEFT a working URL like `http://localhost:8001`. The trigger CLI will POST to `http://localhost:8001/trigger`.

---

## 8. Demo flow (90 seconds)

```
T+0:00  $ python triggers/page_team.py "revenue dashboard wrong — investigate"
        → POST http://localhost:8001/trigger
        → Orchestrator spawns Coordinator
        
T+0:01  Coordinator agent_started, thinking trace begins
        → Pane 1 lights up with scrolling <think> block

T+0:05  Coordinator dispatches Detective + Reality-Checker via asyncio.gather
        → Panes 2 + 3 light up simultaneously

T+0:08–0:35  Parallel work:
   Detective: 2 nl_query → graphql → result
   Reality-Checker: 2 nl_query (both instances) → graphql → cross-instance diff
        
T+0:35  Both agent_completed → Coordinator coordinator_synthesizing
        → Pane 4 (Fixer) lights up

T+0:45–1:10  Fixer:
   - Generates Python SDK code
   - Calls datahub_sdk.emit() to write annotation
   - Calls slack.post() to fire webhook
   → postmortem_written event
   → slack_posted event

T+1:15  Coordinator emits final summary
        → incident_complete fires
        → Bottom bar shows postmortem
        → Demo done

T+1:20  Presenter Cmd+Tabs to DataHub UI tab
        → Refresh olist_dirty.olist_order_items page
        → Annotation "⚠️ INC-2026-0410 quarantined" visible
        → "And here it is in the actual metadata catalog. Thank you."
```

---

## 9. Integration contracts (handoffs)

### RIGHT → LEFT
- Right hands LEFT a Nebius LoRA endpoint name (e.g., `your-org/llama-3.1-8b-datahub-graphql-lora-v1`) once training completes
- LEFT plugs it into `incident_response/tools/nl_to_graphql.py`
- Until then, LEFT uses base `meta-llama/Meta-Llama-3.1-8B-Instruct` with the in-context examples from `seeds.jsonl` as a fallback

### LEFT → MIDDLE
- LEFT hands MIDDLE a working `incident_response/orchestrator.py` exposing:
  ```python
  async def run(incident: str, emit: Callable[[Event], None]) -> dict:
      """Run the full 4-agent flow, emitting events as we go."""
  ```
- MIDDLE calls it from the FastAPI handler and pipes events to the SSE stream
- Until LEFT is ready, MIDDLE uses `dashboard/stub_agents.py` to fake the event stream

### MIDDLE → DEMO
- MIDDLE hands LEFT a working URL like `http://localhost:8001`
- The trigger CLI hits `POST /trigger` to start a run

---

## 10. Environment variables

```bash
# .env.example
NEBIUS_API_KEY="<from op://Clawdbot/Nebius Token Factory - Datahub Hackathon/notesPlain>"
DATAHUB_GMS_URL="http://100.114.31.63:8080"
DATAHUB_GMS_TOKEN="<from op://Clawdbot/DataHub PAT - claude-mcp-elias>"
SLACK_WEBHOOK_URL="<optional, for postmortem post>"

# Model slugs (override here if Nebius slug names need updating)
COORDINATOR_MODEL="moonshotai/Kimi-K2-Thinking"
DETECTIVE_MODEL="meta-llama/Meta-Llama-3.1-8B-Instruct"   # swap to LoRA when right delivers
REALITY_CHECKER_MODEL="meta-llama/Meta-Llama-3.1-8B-Instruct"  # same as Detective
FIXER_MODEL="MiniMaxAI/MiniMax-M2.5"                      # ⚠️ verify availability
```

---

## 11. Risks + mitigations (locked)

| Risk | Mitigation |
|---|---|
| **Nebius LoRA serverless deprecated Apr 13 (3 days out)** | Verify LoRA flow alive TODAY before generating training data. Plan B: zero-shot Llama 8B with in-context examples from `seeds.jsonl` (~70-80% accuracy vs 90% fine-tuned). |
| **MiniMax M2.5 not in Nebius catalog** | ✅ Resolved — M2.5 confirmed visible at front of Nebius Playground catalog 2026-04-10 |
| **Kimi-K2-Thinking slug wrong** | Verify on Playground. Fallback: DeepSeek-R1-0528 (proven). |
| **LoRA endpoint not ready by demo** | Use base Llama 8B with seeds. Validation tests still pass at lower accuracy. |
| **Agents take >2 min total** | Per-agent timeout = 30s. Coordinator has final-say cutoff at 90s. |
| **Dashboard doesn't render events** | Test via `stub_agents.py` first. Don't wire real agents until UI works. |
| **Demo browser blocks SSE** | Test on the actual demo browser early (likely Chrome on MBP). |
| **Annotation doesn't appear in DataHub UI** | Pre-test the SDK write path with a known-good MCP. Refresh tab manually if needed. |
| **Network drop mid-demo** | Record a backup video of a successful run during Phase 2. |

---

## 12. Verification gates (pre-build)

Before any terminal commits time to building, verify these from MBP:

| Gate | What | How |
|---|---|---|
| **Gate 1** | LoRA serverless flow still accepting jobs | Open `https://studio.nebius.com/post-training`, click "Create job", see if model selection accepts `meta-llama/Meta-Llama-3.1-8B-Instruct` and the form lets you proceed past step 1 |
| **Gate 2** | (your message cut off — fill in here once you tell me what Gate 2 is) | TBD |
| **Gate 3** | Kimi-K2-Thinking + MiniMaxAI/MiniMax-M2.5 slugs both work | ✅ MiniMax M2.5 confirmed visible at front of Nebius Playground (2026-04-10). Kimi-K2-Thinking still needs Playground confirmation but availability is well-documented across providers. |

---

## 13. What each terminal does next

### RIGHT (fine-tune)
1. Verify Gate 1 (LoRA flow alive)
2. If yes → continue with `seeds.jsonl` from `FINETUNE-SEEDS.md`, generate 300 pairs, validate, upload, train
3. If no → switch to Plan B (in-context Llama) — same `seeds.jsonl` becomes the prompt library
4. Hand LEFT the deployed model name when ready (or "use base + seeds" if Plan B)

### MIDDLE (dashboard)
1. Read this spec
2. Build `dashboard/` skeleton
3. Implement `stub_agents.py` first
4. Build FastAPI server + 4-pane HTML console
5. Iterate on UI polish using stub events
6. When ready, hand LEFT a working URL

### LEFT (incident response harness — ME)
1. Push this spec to gdrive ✓ (done in this turn)
2. Verify Gate 3 (Kimi + MiniMax slugs) — runs in parallel with the build
3. Set up `incident_response/` repo skeleton (`pyproject.toml`, base modules)
4. Implement `events.py` (Pydantic models)
5. Implement `tools/nl_to_graphql.py`, `tools/datahub_graphql.py`, `tools/datahub_sdk.py`
6. Implement `agents/base.py`
7. Implement Coordinator + Detective + Reality-Checker + Fixer
8. Implement `orchestrator.py`
9. Wire to GE setup from `gx/setup_gx.py` (template in GX-DEEP-DIVE doc)
10. Hand MIDDLE a working `orchestrator.run(incident, emit)` interface

---

## 14. Sibling PARA docs

| Doc | Purpose |
|---|---|
| `STATE-2026-04-10.md` | Live build state — current ingestion, planted issues confirmed, demo narrative |
| `GX-DEEP-DIVE.md` | Great Expectations setup, the `setup_gx.py` template, planted-issue mapping |
| `FINETUNE-SEEDS.md` | The 8 seed pairs + R1 generation prompt + validate/format scripts |
| `PREP.md` | Pre-event checklist + Live Build State action list |
| `INTEL.md` / `IDEAS.md` / `TECH-REFERENCE.md` / `SELECTED-IDEA.md` | Pre-event reference (frozen) |
