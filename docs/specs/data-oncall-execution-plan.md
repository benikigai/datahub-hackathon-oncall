# Spec: data-oncall-execution-plan
**Date:** 2026-04-10
**Status:** Approved
**Approved option:** Option C — Parallel with stubs + 30-minute integration checkpoints
**Complexity:** Moderate (29 tasks: 18 SIMPLE + 11 MODERATE + 0 COMPLEX)
**Repo:** `/Users/elias/code/datahub-nebius-hackathon/`
**Public GitHub:** `github.com/<user>/datahub-hackathon-oncall`

---

## Context

Build the **data-oncall** project: a 4-agent incident response team that uses DataHub as shared metadata memory, finds production data quality bugs by comparing assertion results across two parallel platform instances (`olist_source` clean vs `olist_dirty` planted), and writes postmortems back to DataHub via Python SDK.

**Demo target:** live 5-minute showcase at 5pm today (2026-04-10) at the DataHub × Nebius hackathon at EF SF. Need a working end-to-end run in ~90 seconds.

**Three terminals work in parallel:**
- **LEFT** (this terminal): incident_response harness + GE setup + integration glue
- **MIDDLE**: FastAPI + SSE 4-pane dashboard
- **RIGHT**: LoRA fine-tune for NL→GraphQL (Llama 3.1 8B)

Architecture is **locked** in `docs/specs/research/DataHub-Nebius - PROJECT-SPEC.md`. This spec decomposes the locked architecture into executable tasks with dependencies, acceptance criteria, and rollback plans.

---

## Decisions

1. **Execution strategy: Option C** (parallel with stubs + 30-min integration checkpoints) over Option A (linear, late integration risk) and Option B (vertical slice, wastes parallelism). Three Es total: 27 vs A=17 vs B=24.

2. **Demo trigger UX: Both CLI and dashboard button** (user choice C in Phase 1). CLI at `triggers/page_team.py` POSTs to dashboard's `/trigger` endpoint; dashboard also exposes a "Trigger Incident" button.

3. **Reality-Checker diff: Hybrid Python + LLM** (user choice C). Python set difference computes the deterministic diff between `olist_source` and `olist_dirty` assertion results. Llama LoRA writes the human-readable narrative around it. Best of both worlds — deterministic computation, narrative output.

4. **DataHub annotation type: `editableSchemaMetadata` description update** (user choice C) **plus belt-and-suspenders `customProperties`**. Most visible — judges Cmd+Tab to DataHub and immediately see the warning banner at the top of the affected dataset page.

5. **Plan B fallback for fine-tune** baked into Task L4 via env-var swap. If LoRA training fails or times out, swap `NL_TO_GRAPHQL_MODEL` to base Llama 3.1 8B. Detective + Reality-Checker still work at ~70-80% accuracy with the in-context seeds prompt loaded as the system prompt.

6. **GE pinned to `<1.0.0`** because the DataHub plugin doesn't support GX 1.x. Failure mode is silent — assertions just never appear in DataHub. Pin enforced in `pyproject.toml`.

7. **Reads via GraphQL, writes via Python SDK** per DataHub docs explicit recommendation: *"GraphQL mutations are primarily designed to support UI interactions and should generally be avoided in programmatic use cases."*

8. **Repo location: `/Users/elias/code/datahub-nebius-hackathon/`** (Mac Mini, this terminal). Public GitHub at `github.com/<user>/datahub-hackathon-oncall` after smoke tests pass.

9. **Critic verdict: CONCERNS** (not REJECT). All concerns addressed in task ordering:
   - PAT generation moved to L0 (before any code)
   - GE setup (L3) sequenced before Reality-Checker (L7)
   - Smoke tests for all 3 model endpoints in L0
   - Plan B fallback baked into L4
   - Dashboard reset endpoint in M5
   - Backup video as Task I4

---

## Tasks

Task IDs use prefixes: **L** = LEFT terminal, **M** = MIDDLE, **R** = RIGHT, **I** = Integration.

### LEFT terminal — incident_response harness + GE setup

#### Task L0: Smoke tests — all endpoints reachable
**Objective:** Verify the build environment can talk to DataHub, Nebius (Kimi + Llama base + MiniMax M2.5), and that the DataHub PAT can be generated and stored. Anything that fails here is a hard blocker before any code is written.
**Complexity:** SIMPLE
**Dependencies:** None
**Files to change:** `scripts/smoke_test.sh`
**Acceptance criteria:**
  - `curl http://100.114.31.63:8080/health` returns 200 (or DataHub equivalent)
  - DataHub PAT generated at `http://100.114.31.63:9002/settings/tokens` and stored at `~/.config/openclaw/datahub_pat` (chmod 600)
  - Test call to `moonshotai/Kimi-K2-Thinking` returns a valid response
  - Test call to `meta-llama/Meta-Llama-3.1-8B-Instruct` returns a valid response
  - Test call to `MiniMaxAI/MiniMax-M2.5` returns a valid response
**Test plan:**
  - Smoke: `bash scripts/smoke_test.sh` exits 0 with 5 ✅ lines
**Rollback:** N/A (read-only smoke tests).
**Blast radius:** None.
**Research needed:** No.

#### Task L1: Repo scaffold + git init
**Objective:** Create the directory structure, `pyproject.toml` (with GE pinned `<1.0`), `.env.example`, `.gitignore`, `README.md` skeleton, and `git init`. Establishes the foundation all other LEFT/MIDDLE tasks build on.
**Complexity:** SIMPLE
**Dependencies:** L0
**Files to change:** `pyproject.toml`, `.env.example`, `.gitignore`, `README.md`, `incident_response/__init__.py`, `incident_response/agents/__init__.py`, `incident_response/tools/__init__.py`, `incident_response/triggers/__init__.py`, `gx/`, `dashboard/`, `training/`
**Acceptance criteria:**
  - `pip install -e .` succeeds in a clean venv
  - `python -c "import incident_response"` works
  - `git status` shows clean tree after initial commit
  - `.env.example` has all 7 required env vars
**Test plan:**
  - Smoke: clean venv install
**Rollback:** `rm -rf /Users/elias/code/datahub-nebius-hackathon/`
**Blast radius:** None (new directory).
**Research needed:** No.

#### Task L2: Event models + tools layer
**Objective:** Implement the SSE event Pydantic models and 4 tool helpers (`datahub_graphql`, `nl_to_graphql`, `datahub_sdk`, `slack`). This is the foundation that agents call into.
**Complexity:** MODERATE
**Dependencies:** L1
**Files to change:** `incident_response/events.py`, `incident_response/tools/datahub_graphql.py`, `incident_response/tools/nl_to_graphql.py`, `incident_response/tools/datahub_sdk.py`, `incident_response/tools/slack.py`
**Acceptance criteria:**
  - `from incident_response.events import Event` works
  - `datahub_graphql.query("{ search(...) }")` returns parsed JSON from real DataHub
  - `nl_to_graphql("find revenue dashboard")` returns a GraphQL string from base Llama 8B
  - `datahub_sdk.update_description(urn, "test")` round-trips through DataHub UI
  - `slack.post("test")` returns 200 if `SLACK_WEBHOOK_URL` set, else returns a warning
**Test plan:**
  - Unit: `tests/test_tools.py` exercises each helper with a real call to Studio A
  - Smoke: each tool has a `if __name__ == "__main__"` block
**Rollback:** Remove `tools/` dir.
**Blast radius:** None (new code).
**Research needed:** No.

#### Task L3: GE setup + run against both instances
**Objective:** Drop in `setup_gx.py` and `setup_gx_source.py` from `GX-DEEP-DIVE.md`. Run both. Verify all 9 assertions land in DataHub UI under both `olist_source.*` and `olist_dirty.*` Quality tabs. **This must complete before L7 (Reality-Checker) can be tested.**
**Complexity:** MODERATE
**Dependencies:** L1, L0
**Files to change:** `gx/setup_gx.py`, `gx/setup_gx_source.py`, `gx/data/olist.db` (symlink), `gx/data/olist_dirty.db` (symlink)
**Acceptance criteria:**
  - `pip install 'great_expectations<1.0.0' acryl-datahub-gx-plugin` succeeds
  - `python gx/setup_gx.py` prints `Success: False` (3 expected failures)
  - `python gx/setup_gx_source.py` prints `Success: True` (clean baseline)
  - DataHub UI shows 9 assertions on `olist_dirty.olist_order_items`, `olist_dirty.olist_customers`, `olist_dirty.olist_products`
  - DataHub UI shows the same 9 assertions on `olist_source.*` (all passing)
**Test plan:**
  - Smoke: GraphQL query for assertions on `olist_dirty.olist_order_items` returns ≥1 result with `result.type=FAILURE`
**Rollback:** `rm -rf gx/great_expectations/` (re-creatable from script)
**Blast radius:** Adds rows to DataHub MySQL/Kafka/ES; reversible via cleanup script.
**Research needed:** No.

#### Task L4: BaseAgent class + LoRA-or-base swap
**Objective:** Implement `agents/base.py` with the abstract class. Configure `nl_to_graphql.py` to swap between base Llama (default) and fine-tuned LoRA endpoint via `NL_TO_GRAPHQL_MODEL` env var. Build the Plan B fallback (in-context seeds prompt) that base Llama uses when no LoRA is set.
**Complexity:** SIMPLE
**Dependencies:** L2
**Files to change:** `incident_response/agents/base.py`, `incident_response/tools/nl_to_graphql.py` (refactor for env-var model selection + Plan B prompt loading)
**Acceptance criteria:**
  - `BaseAgent` is importable, has abstract `run()` method
  - `nl_to_graphql("find dataset X")` works with default model (base Llama + seeds)
  - Setting `NL_TO_GRAPHQL_MODEL=<lora-name>` swaps the model on next call
  - With base model + seeds, ≥6/8 seed test queries return valid GraphQL
**Test plan:**
  - Unit: `tests/test_base_agent.py` creates a stub subclass and verifies `run()` raises NotImplementedError
  - Integration: 8 seed query test
**Rollback:** Revert files.
**Blast radius:** None.
**Research needed:** No.

#### Task L5: Coordinator agent (Kimi-K2-Thinking)
**Objective:** Implement Coordinator that receives the incident text, dispatches Detective + Reality-Checker in parallel via `asyncio.gather`, then dispatches Fixer with their outputs, then synthesizes the final postmortem. Emits `thinking` events from Kimi's `<think>` blocks.
**Complexity:** MODERATE
**Dependencies:** L4 (can be implemented with stubs first; depends logically on L6/L7/L8 for end-to-end)
**Files to change:** `incident_response/agents/coordinator.py`, `incident_response/prompts/coordinator.txt`
**Acceptance criteria:**
  - `await coordinator.run({"incident": "..."})` returns `{"postmortem": str, "incident_id": str, "affected_datasets": list}`
  - Emits `agent_started`, `thinking` (≥1), `coordinator_synthesizing`, `agent_completed` events
  - Calls Detective and Reality-Checker concurrently (verified via timing — both complete in <max(detective_time, rc_time) + 1s overhead)
**Test plan:**
  - Unit: `tests/test_coordinator.py` with stubbed sub-agents
  - Integration: full run with real Kimi-K2-Thinking + stubbed Detective/Reality-Checker
**Rollback:** Revert file.
**Blast radius:** None.
**Research needed:** No.

#### Task L6: Detective agent (Llama LoRA / base, lineage focus)
**Objective:** Implement Detective that takes the incident, identifies the affected dataset via search, traces upstream lineage, returns a list of upstream datasets + the lineage path.
**Complexity:** MODERATE
**Dependencies:** L4
**Files to change:** `incident_response/agents/detective.py`, `incident_response/prompts/detective.txt`
**Acceptance criteria:**
  - `await detective.run({"incident": "revenue dashboard wrong"})` returns `{"target_urn": str, "upstream": list, "lineage_path": list}`
  - Emits `nl_query`, `graphql_generated`, `graphql_executed` events for each call
  - Handles "no dataset found" gracefully (emits `error` event, returns empty)
**Test plan:**
  - Unit: mocked GraphQL responses, assert agent picks the right URN
  - Integration: real DataHub query, returns ≥1 upstream dataset
**Rollback:** Revert file.
**Blast radius:** Read-only.
**Research needed:** No.

#### Task L7: Reality-Checker agent (Llama + Python diff)
**Objective:** Implement Reality-Checker that queries assertions on the same datasets in BOTH `olist_source` and `olist_dirty` instances, computes the diff in Python (set difference), then has the LLM write the human-readable narrative around the diff.
**Complexity:** MODERATE
**Dependencies:** L4, L3 (GE assertions must exist in DataHub)
**Files to change:** `incident_response/agents/reality_checker.py`, `incident_response/prompts/reality_checker.txt`
**Acceptance criteria:**
  - `await reality_checker.run({"target_urn": "olist_dirty.olist_order_items", "upstream_urns": [...]})` returns `{"gap": list, "narrative": str}`
  - Python diff correctly identifies the 3 planted issues (5,632 truncated seller_ids, 7,955 deleted customers, 988 NULL categories)
  - LLM narrative includes the row counts
  - Emits 4-6 `nl_query`/`graphql_executed` event pairs (one per instance per table)
**Test plan:**
  - Unit: stubbed GraphQL with known clean+dirty assertion sets, assert diff = 3 expected items
  - Integration: real DataHub query, all 3 planted issues found
**Rollback:** Revert file.
**Blast radius:** Read-only.
**Research needed:** No.

#### Task L8: Fixer agent (MiniMax-M2.5)
**Objective:** Implement Fixer that takes the gap report and generates Python SDK code to update `editableSchemaMetadata.description` (most visible) AND `customProperties` (belt-and-suspenders) on the 3 affected datasets with the incident annotation. Executes the code. Optionally posts to Slack.
**Complexity:** MODERATE
**Dependencies:** L4, L2 (datahub_sdk tool)
**Files to change:** `incident_response/agents/fixer.py`, `incident_response/prompts/fixer.txt`
**Acceptance criteria:**
  - `await fixer.run({"gap": [...]})` returns `{"annotations_written": [3 urns], "slack_posted": bool}`
  - DataHub UI shows the warning text at the top of each affected dataset page within 5 seconds of completion
  - Emits `tool_called`, `postmortem_written`, `slack_posted` (if applicable) events
**Test plan:**
  - Unit: stubbed SDK, assert 3 write calls
  - Integration: real DataHub write, GraphQL re-query confirms description updated
  - Smoke: refresh DataHub UI manually, see warning banner
**Rollback:** Cleanup script that resets the descriptions on the 3 datasets to empty.
**Blast radius:** Modifies DataHub state on 3 datasets — easy to revert.
**Research needed:** No.

#### Task L9: Orchestrator + trigger CLI
**Objective:** Implement `orchestrator.run(incident, emit)` that wires Coordinator → Detective+Reality-Checker (parallel) → Fixer. Implement `triggers/page_team.py` CLI that POSTs to dashboard's `/trigger` endpoint.
**Complexity:** MODERATE
**Dependencies:** L5, L6, L7, L8
**Files to change:** `incident_response/orchestrator.py`, `incident_response/triggers/page_team.py`
**Acceptance criteria:**
  - `await orchestrator.run("revenue dashboard wrong", emit_callback)` runs the full 4-agent flow
  - Total wall time <90 seconds against real Studio A DataHub
  - Final event is `incident_complete` with `elapsed_ms` populated
  - `python -m incident_response.triggers.page_team "..."` POSTs to `http://localhost:8001/trigger` and returns
**Test plan:**
  - Unit: stubbed agents, assert correct dispatch order
  - Integration: full run against real models + DataHub
  - Smoke: CLI returns 0
**Rollback:** Revert files.
**Blast radius:** Same as Fixer (writes to 3 datasets).
**Research needed:** No.

#### Task L10: End-to-end smoke test (LEFT-only, no dashboard)
**Objective:** Run the full orchestrator standalone (without dashboard) against real Studio A. Verify all 4 agents fire, GE diff finds 3 planted issues, Fixer writes annotations, total wall time <90s.
**Complexity:** SIMPLE
**Dependencies:** L9
**Files to change:** `tests/test_e2e_left.py`
**Acceptance criteria:**
  - Test passes in <90 seconds
  - DataHub UI shows fresh annotations on all 3 affected datasets
  - Final event sequence matches `PROJECT-SPEC.md` section 6 example (≥20 events emitted)
**Test plan:**
  - Smoke: `pytest tests/test_e2e_left.py -v`
**Rollback:** Run cleanup script to revert dataset descriptions.
**Blast radius:** Same as L9.
**Research needed:** No.

### MIDDLE terminal — dashboard

#### Task M1: Dashboard skeleton + stub events
**Objective:** Create `dashboard/` directory, FastAPI server stub, static HTML file, and `stub_agents.py` with hardcoded 25-event sequence on 200ms cadence.
**Complexity:** SIMPLE
**Dependencies:** L1
**Files to change:** `dashboard/server.py`, `dashboard/stub_agents.py`, `dashboard/static/index.html`, `dashboard/static/style.css`, `dashboard/static/app.js`
**Acceptance criteria:**
  - `uvicorn dashboard.server:app --port 8001` starts
  - `curl http://localhost:8001/` returns the HTML page
  - Stub trigger fires 25 SSE events
**Test plan:**
  - Smoke: open in browser, click trigger, see events scroll
**Rollback:** `rm -rf dashboard/`
**Blast radius:** None.
**Research needed:** No.

#### Task M2: FastAPI server + SSE endpoint + trigger mutex
**Objective:** Implement `/trigger` (POST) and `/stream` (SSE GET) endpoints. Add server-side mutex so concurrent triggers return 409. Add `/reset` endpoint to clear state between runs.
**Complexity:** MODERATE
**Dependencies:** M1
**Files to change:** `dashboard/server.py`
**Acceptance criteria:**
  - `POST /trigger` with `{"incident": "..."}` returns `{"run_id": "..."}` and starts a background task
  - Concurrent POST returns 409
  - `GET /stream?run_id=...` streams SSE events for that run
  - `POST /reset` clears state and returns 200
**Test plan:**
  - Unit: mocked orchestrator
  - Smoke: curl-based smoke test of all 3 endpoints
**Rollback:** Revert file.
**Blast radius:** None.
**Research needed:** No.

#### Task M3: HTML layout + dark theme + fine-tune story panel
**Objective:** Single static HTML file implementing the full layout in `docs/specs/dashboard-design.md`. The dashboard tells two stories on one page: the fine-tune story (top static panel reading from `finetune_metrics.json`) and the live agent story (4-pane console). Includes top stats bar with 4 model badges, fine-tune story panel, incident trigger input + button + reset, 4-pane live agent console, postmortem footer with DataHub deep-links.
**Complexity:** SIMPLE
**Dependencies:** M1
**Files to change:** `dashboard/static/index.html`, `dashboard/static/style.css`, `dashboard/static/finetune_metrics.json`
**Acceptance criteria:**
  - Top stats bar (sticky) shows 4 model badges with cost in/out per 1M and region per dashboard-design.md
  - Fine-tune story panel renders accuracy bars, training/val counts, LoRA config, and sample seed pair from `finetune_metrics.json` (placeholder values OK at build time, real numbers dropped in later)
  - Incident trigger has text input pre-filled, TRIGGER button, RESET button
  - 4 panes labeled COORDINATOR / DETECTIVE / REALITY-CHECKER / FIXER with status LED + scrolling event log areas
  - Postmortem footer reserved with DataHub deep-link buttons
  - Dark theme palette per `dashboard-design.md` CSS variables (--bg-base, --cyan-nl, etc.)
  - Monospace, no JS frameworks (vanilla only; Prism.js via CDN allowed for syntax highlighting)
**Test plan:**
  - Visual: open in Chrome, take screenshot, compare to `docs/specs/dashboard-design.md` ASCII layout
  - Smoke: page loads with 0 console errors, all 4 sections render even before any events stream
**Rollback:** Revert files.
**Blast radius:** None.
**Research needed:** No.
**Reference:** `docs/specs/dashboard-design.md` for full layout, color palette, and finetune_metrics.json schema.

#### Task M4: SSE client + DOM updates
**Objective:** Vanilla JS SSE client that subscribes to `/stream`, parses incoming events, and updates the appropriate pane. Each pane has its own scrolling event log.
**Complexity:** MODERATE
**Dependencies:** M2, M3
**Files to change:** `dashboard/static/app.js`
**Acceptance criteria:**
  - `EventSource` connects to `/stream`
  - All 12 event types render in the right pane
  - Coordinator's `thinking` events scroll inside its pane
  - `incident_complete` updates the footer with the postmortem
**Test plan:**
  - Smoke: stub_agents.py fires all 12 event types, verify each renders
**Rollback:** Revert file.
**Blast radius:** None.
**Research needed:** No.

#### Task M5: Trigger button + reset mechanism
**Objective:** Add "Trigger Incident" button to the page (next to incident text input). Add "Reset" button that POSTs to `/reset`.
**Complexity:** SIMPLE
**Dependencies:** M4
**Files to change:** `dashboard/static/index.html`, `dashboard/static/app.js`, `dashboard/static/style.css`
**Acceptance criteria:**
  - Button click triggers a run end-to-end
  - Reset clears all panes and footer
  - Button is disabled while a run is in progress
**Test plan:**
  - Smoke: click trigger, watch events; click reset, verify clean state; click trigger again, verify second run works
**Rollback:** Revert files.
**Blast radius:** None.
**Research needed:** No.

#### Task M6: End-to-end test with stubs
**Objective:** Verify the dashboard renders all stub events correctly. Gate before swapping to real orchestrator.
**Complexity:** SIMPLE
**Dependencies:** M5
**Files to change:** None (test only)
**Acceptance criteria:**
  - Open browser, click trigger, see 25 stub events render across 4 panes in <10 seconds, footer populates
**Test plan:**
  - Visual smoke test
**Rollback:** N/A.
**Blast radius:** None.
**Research needed:** No.

#### Task M7: Wire to real orchestrator
**Objective:** Replace `stub_agents.py` import with `incident_response.orchestrator.run`. Verify dashboard renders real events from real agents.
**Complexity:** MODERATE
**Dependencies:** M6, L9
**Files to change:** `dashboard/server.py`
**Acceptance criteria:**
  - Click "Trigger Incident" → real orchestrator runs → dashboard shows real events
  - Total wall time <90 seconds
  - All 4 panes populate
  - Footer shows real postmortem
**Test plan:**
  - Smoke: full live run
**Rollback:** Revert to stub import.
**Blast radius:** Real DataHub writes (handled by L8 cleanup).
**Research needed:** No.

### RIGHT terminal — fine-tune

#### Task R1: Seeds + R1 batch generation
**Objective:** Save 8 seed pairs from FINETUNE-SEEDS.md as `training/seeds.jsonl`. Run R1 batch generation script to produce ~300 raw NL→GraphQL pairs.
**Complexity:** SIMPLE
**Dependencies:** L0 (Nebius API works)
**Files to change:** `training/seeds.jsonl`, `training/gen_prompt.txt`, `training/generate.sh`, `training/raw_pairs.jsonl` (output)
**Acceptance criteria:**
  - `seeds.jsonl` has 8 lines, all parse as JSON
  - `bash training/generate.sh` produces `raw_pairs.jsonl` with 200-300 lines
**Test plan:**
  - Smoke: `wc -l training/raw_pairs.jsonl` ≥ 200
**Rollback:** Delete files.
**Blast radius:** Spends Nebius credits (~$0.10).
**Research needed:** No.

#### Task R2: Validate pairs against live DataHub
**Objective:** Run `validate_pairs.py` to filter out broken queries. Target ≥200 validated pairs.
**Complexity:** MODERATE
**Dependencies:** R1, L0 (DataHub PAT)
**Files to change:** `training/validate_pairs.py`, `training/validated_pairs.jsonl`
**Acceptance criteria:**
  - Output has ≥200 pairs
  - Each pair's GraphQL parses AND returns non-error response from real DataHub
**Test plan:**
  - Smoke: spot-check 5 random pairs
**Rollback:** Re-run R1 to top up.
**Blast radius:** Read-only.
**Research needed:** No.

#### Task R3: Format + split + upload to Nebius
**Objective:** Convert validated pairs to OpenAI chat format JSONL, 80/20 split. Upload to Nebius Data Lab.
**Complexity:** SIMPLE
**Dependencies:** R2
**Files to change:** `training/format_for_nebius.py`, `training/train.jsonl`, `training/val.jsonl`
**Acceptance criteria:**
  - Files visible in Nebius Studio → Data Lab → Datasets with valid `dataset_id`
**Test plan:**
  - Smoke: manual verification in Nebius UI
**Rollback:** Delete from Nebius UI.
**Blast radius:** None.
**Research needed:** No.

#### Task R4: Launch LoRA training
**Objective:** Configure and launch the Nebius post-training job: `meta-llama/Meta-Llama-3.1-8B-Instruct` + LoRA (rank 16, alpha 32, LR 2e-4, 3 epochs, batch 4). Job runs ~20-30 min unattended.
**Complexity:** SIMPLE
**Dependencies:** R3
**Files to change:** `training/job_id.txt`
**Acceptance criteria:**
  - Job ID returned and saved
  - Training loss visible in Nebius UI, dropping
**Test plan:**
  - Monitor Nebius UI
**Rollback:** Cancel job in Nebius UI.
**Blast radius:** Spends Nebius credits (~$0.50-2).
**Research needed:** No.

#### Task R5: Deploy LoRA endpoint + smoke test
**Objective:** Deploy the LoRA endpoint via Nebius UI. Test with all 8 seed NL queries.
**Complexity:** SIMPLE
**Dependencies:** R4
**Files to change:** `training/test_endpoint.py`, `training/endpoint_name.txt`
**Acceptance criteria:**
  - Endpoint deploys
  - All 8 seed queries return valid GraphQL
  - ≥6/8 return non-empty results when executed against DataHub
**Test plan:**
  - Smoke: `python training/test_endpoint.py`
**Rollback:** Use base Llama 8B + seeds (Plan B).
**Blast radius:** None.
**Research needed:** No.

#### Task R6: Plan B fallback ready
**Objective:** Independent of training success — write the in-context system prompt for base Llama 8B that includes all 8 seed examples.
**Complexity:** SIMPLE
**Dependencies:** R1
**Files to change:** `training/plan_b_system_prompt.txt`
**Acceptance criteria:**
  - System prompt loaded into `nl_to_graphql.py` works for ≥6/8 seed queries
**Test plan:**
  - Smoke: 8 seed query test with `NL_TO_GRAPHQL_MODE=plan_b`
**Rollback:** N/A.
**Blast radius:** None.
**Research needed:** No.

### Integration

#### Task I1: LEFT plugs in LoRA endpoint
**Objective:** When R5 hands LEFT the deployed endpoint name, update `.env` and re-run L10.
**Complexity:** SIMPLE
**Dependencies:** R5, L10
**Files to change:** `.env`
**Acceptance criteria:**
  - `NL_TO_GRAPHQL_MODEL=<lora-name>` set
  - L10 still passes
**Test plan:**
  - Re-run `pytest tests/test_e2e_left.py`
**Rollback:** Unset env var.
**Blast radius:** None.
**Research needed:** No.

#### Task I2: LEFT × MIDDLE integration test
**Objective:** Run the dashboard with the real orchestrator. Verify SSE events render correctly against real LLM timing.
**Complexity:** MODERATE
**Dependencies:** L10, M7
**Files to change:** None
**Acceptance criteria:**
  - Trigger from CLI → events render in dashboard
  - Trigger from dashboard button → same flow
  - Both complete in <90s
**Test plan:**
  - Manual smoke test, both trigger paths
**Rollback:** N/A.
**Blast radius:** Same as L9.
**Research needed:** No.

#### Task I3: Full end-to-end demo rehearsal
**Objective:** Open DataHub UI in tab 2, dashboard in tab 1. Run a full demo. Verify the annotation appears in DataHub UI when we Cmd+Tab.
**Complexity:** MODERATE
**Dependencies:** I2
**Files to change:** None
**Acceptance criteria:**
  - Demo runs end-to-end in <90s
  - DataHub UI annotation visible after Cmd+Tab + refresh
  - All 4 panes populate visibly
  - Postmortem readable
  - No errors in browser console
**Test plan:**
  - Manual rehearsal × 2
**Rollback:** Cleanup script.
**Blast radius:** Annotations on 3 datasets (revertible).
**Research needed:** No.

#### Task I4: Backup video recording
**Objective:** Record a screen capture of a successful demo run. Plan C if anything fails on stage.
**Complexity:** SIMPLE
**Dependencies:** I3
**Files to change:** `docs/backup_demo.mov`
**Acceptance criteria:**
  - Video shows trigger → 4 agents → postmortem → DataHub annotation
  - Saved to `docs/` and uploaded to gdrive
**Test plan:**
  - Play back
**Rollback:** N/A.
**Blast radius:** None.
**Research needed:** No.

#### Task I5: GitHub repo public + final push
**Objective:** Create `github.com/<user>/datahub-hackathon-oncall` as a public repo. Push the final state.
**Complexity:** SIMPLE
**Dependencies:** I3
**Files to change:** None locally
**Acceptance criteria:**
  - Public URL accessible in incognito
  - README renders correctly
**Test plan:**
  - Open in incognito browser
**Rollback:** `gh repo delete` (within 1hr grace).
**Blast radius:** Public visibility — verify no secrets first.
**Research needed:** No.

---

## Dependency Graph

```
LEFT critical path (~3h):
L0 → L1 → L2 → L3 (GE) ─┐
              └→ L4 → L6, L8 ─┐
                    L5 ──────┤
                    L7 (needs L3) ─┤
                                   └→ L9 → L10

MIDDLE critical path (~2h, parallel):
M1 → M2, M3 → M4 → M5 → M6 → (wait L9) → M7

RIGHT critical path (~2.5h, mostly unattended):
R1 → R2 → R3 → R4 (~25 min unattended) → R5 → I1
R6 (Plan B) runs in parallel, ready in <10 min

Integration:
(L10 + M7) → I2 → I3 → I4 → I5
```

**Critical path total: ~3 hours** (LEFT-paced; RIGHT runs unattended for chunks).

---

## Risks

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| LoRA training fails or times out | Medium | Medium | R6 (Plan B) ready in parallel; env-var swap in I1; validation tests still pass at lower accuracy |
| DataHub PAT generation fails | Low | High | Task L0 verifies before any code is written |
| MiniMax M2.5 slug typo | Low | High | Task L0 smoke tests all 3 model endpoints |
| GE 1.x accidentally installed | Low | Critical | `pyproject.toml` pins `great_expectations<1.0.0` |
| Dashboard reset between runs leaks state | Low | Medium | Task M5 includes `/reset` endpoint |
| Network drop at venue | Medium | High | Backup video recorded in I4 as Plan C |
| Demo timer overruns 90s | Medium | Medium | Per-agent 30s timeout in L9, Coordinator 90s cutoff |
| Studio A goes down during demo | Low | Critical | Backup video; can fall back to running DataHub locally on MBP |
| Stubs lie (real LLM behavior surprises us) | Medium | Medium | First integration checkpoint at T+30 uses real DataHub queries even with stubbed agents |

---

## Research Notes

Research artifacts in `docs/specs/research/` (synced from `/tmp/hackathon-prep/`):

| File | Purpose |
|---|---|
| `DataHub-Nebius - PROJECT-SPEC.md` | Locked architecture, model lineup, file structure, SSE protocol, integration contracts |
| `DataHub-Nebius - STATE-2026-04-10.md` | Current build state, 47 ingested datasets, planted issues confirmed, full demo narrative |
| `DataHub-Nebius - GX-DEEP-DIVE.md` | Great Expectations integration with corrected planted-issue expectations + drop-in `setup_gx.py` template |
| `DataHub-Nebius - FINETUNE-SEEDS.md` | 8 NL→GraphQL seed pairs + R1 generation script + validation/format scripts |
| `DataHub-Nebius - PREP.md` | Pre-event checklist + Live Build State action list |
| `DataHub-Nebius - INTEL.md` | Event facts + 6-level scoring rubric |
| `DataHub-Nebius - IDEAS.md` | The 3 candidate ideas (Idea #1 selected) |
| `DataHub-Nebius - SELECTED-IDEA.md` | Original L6 pitch (mostly superseded by PROJECT-SPEC.md) |
| `DataHub-Nebius - TECH-REFERENCE.md` | DataHub + Nebius tech overview, model recommendations |
