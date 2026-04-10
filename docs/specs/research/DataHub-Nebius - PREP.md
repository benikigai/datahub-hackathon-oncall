# DataHub × Nebius Hackathon — PREP

🚨 **TODAY IS EVENT DAY** — April 10, 2026\. This doc has pivoted from "before the event" to "morning of." If you're reading this in transit, jump to **Morning-of checklist** below.

---

## Morning-of checklist (April 10, before you leave)

### Last 30 minutes at home

- [ ] MBP fully charged \+ brick in bag  
- [ ] Phone charged (cellular hotspot fallback)  
- [ ] Docker Desktop launched on MBP, daemon green  
- [ ] `datahub docker quickstart` running on MBP (verify `http://localhost:9002` opens)  
- [ ] `acryl-datahub` Python package installed on MBP  
- [ ] `NEBIUS_API_KEY` exported in MBP shell (`echo $NEBIUS_API_KEY` returns the key)  
- [ ] `nebius_test.py` runs and prints DeepSeek-R1 response  
- [ ] Latest agent skeleton repo cloned to MBP and pushed to GitHub for cross-machine recovery  
- [ ] Slack `datahubspace.slack.com` workspace logged in on phone for mentor access  
- [ ] DataHub-Nebius PARA folder open in browser tab for reference  
- [ ] 1Password unlocked on MBP (or `op` CLI working)

### What goes in the bag

- [ ] MacBook Pro  
- [ ] Laptop charger (USB-C 96W+)  
- [ ] iPhone \+ Lightning/USB-C cable  
- [ ] AirPods (for keynote audio if needed)  
- [ ] Notebook \+ pen (for problem-statement notes during reveal)  
- [ ] Hoodie/layer (EF venue temperature is unpredictable)  
- [ ] Snacks (lunch is provided but stash backup energy)

### One smoke test before leaving

\# On MBP, with venue WiFi simulated (turn off WiFi, use phone hotspot):

python3 nebius\_test.py                    \# Nebius API works over cellular

curl http://localhost:9002 | head \-5      \# DataHub responds locally

docker ps | grep datahub                  \# Containers up

If all three pass on cellular alone, you're bulletproof for venue WiFi flakes.

---

## Studio A status (dev gym, runs continuously)

✅ Docker 29.2.1 \+ Docker Compose v5.0.2 — running ✅ Tailscale `100.114.31.63` — reachable from anywhere ✅ M4 Max / 128GB / 4TB — ample headroom ✅ `uv` 0.11.6 installed at `~/.local/bin/uv` ✅ Python 3.12.13 venv at `~/.venvs/datahub/` ✅ `acryl-datahub` 1.5.0.6 installed in venv ✅ `datahub` CLI symlinked to `~/.local/bin/datahub` (on PATH) ✅ `datahub-project/static-assets` cloned to `~/code/datahub-static-assets/` ✅ All 3 datasets present with .db files \+ ingest recipes (398 MB total) 🔄 `datahub docker quickstart` — running in background (\~3-4 GB image pull) ⏳ Healthcare dataset ingestion — pending quickstart completion ⏳ 4-agent skeleton scaffold — waiting on user signal (step 4\)

If MBP melts mid-demo, the recovery move is to switch to Studio A via Tailscale and finish the demo from there.

## Datasets (cloned to Studio A)

**Source**: [https://github.com/datahub-project/static-assets](https://github.com/datahub-project/static-assets) **Local path**: `~/code/datahub-static-assets/datasets/`

| Dataset | Size | .db files | Engineered for | Ingest command |
| :---- | :---- | :---- | :---- | :---- |
| **healthcare** ⭐ | 30 MB | `healthcare.db` | Selective pipeline halting (L4/L6) | `cd ~/code/datahub-static-assets/datasets/healthcare && datahub ingest -c ingest.yaml` |
| **nyc-taxi** | 173 MB | `nyc_taxi.db`, `nyc_taxi_pipeline.db` | Freshness/staleness (L5) | `cd ~/code/datahub-static-assets/datasets/nyc-taxi && datahub ingest -c ingest.yaml` |
| **olist-ecommerce** | 195 MB | `olist.db`, `olist_dirty.db` | Join validation, reconciliation (L5) | `cd ~/code/datahub-static-assets/datasets/olist-ecommerce && datahub ingest -c ingest_source.yaml` |

**Each dataset folder also includes**:

- `add_lineage.py` — adds view→table lineage to DataHub  
- `add_metadata.py` — adds tags, glossary terms, ownership  
- `README.md` — full pipeline description, planted quality issues, table schemas  
- `create_db.py` — regenerates the .db from source CSV (if needed)

**Read the per-dataset READMEs** — they list every planted quality issue and which downstream is affected. This is the cheat code to event day.

---

## Nebius API key — verified working

| Item | Vault | Status |
| :---- | :---- | :---- |
| `Nebius Token Factory - Datahub Hackathon` | Clawdbot | ✅ **USE THIS** — verified 2026-04-09 |
| `Injester.lol Token Factory API` | Clawdbot | ✅ Backup |
| `Nebius Token Factory` (no suffix) | Clawdbot | ❌ Dead — slated for delete |

### Quick load via op CLI

export NEBIUS\_API\_KEY=$(env HOME=\~/.config/op/home op read \\

  "op://Clawdbot/Nebius Token Factory \- Datahub Hackathon/notesPlain")

### Endpoint

- Base URL: `https://api.studio.nebius.com/v1`  
- Default model: `deepseek-ai/DeepSeek-R1-0528`  
- 56 models available, OpenAI-compatible  
- Verified: HTTP 200, 2.6s for 70 tokens

---

## Original pre-event checklist (from official kit)

### Required

- [x] Docker Desktop installed (8GB+ RAM, 12GB+ disk allocated)  
- [x] Docker Compose v2 (included with Docker Desktop)  
- [x] Python 3.10+  
- [x] `pip install acryl-datahub`  
- [x] SQLite (or DB Browser for SQLite on Windows)  
- [x] Code editor (VS Code / Cursor / your preference)  
- [x] Git installed  
- [x] Nebius Token Factory account created and verified  
- [x] At least one API key created and stored safely  
- [x] `NEBIUS_API_KEY` set as an environment variable on dev machine

### Optional (recommended)

- [x] AI coding assistant (Cursor, Copilot, etc.)  
- [x] Slack/Discord/Jira integration tools  
- [x] One test script that calls `deepseek-ai/DeepSeek-R1-0528` and prints a response

---

## Event day timeline (today)

| Time | Activity | What you should be doing |
| :---- | :---- | :---- |
| 9:00 | Doors open \+ breakfast | Eat. Network. Form team if solo. Verify DataHub running on MBP. |
| 9:30 | Welcome \+ briefing | Take notes on judging criteria — they may differ from kit hints. |
| 9:45 | Technical keynote | Listen for sponsor-specific evaluation cues. |
| **10:15** | **Phase 1 \+ Problem reveal** | **Note problem statement verbatim. Cross-reference with Idea \#1 skeleton.** |
| 10:20 | `/spec "<problem statement> using L6 incident response team"` | Generate task breakdown |
| 10:30 | Commit to architecture | Don't second-guess. Architecture is committed. |
| 10:45 | Ingest dataset (Phase 1 setup) | `datahub docker nuke && datahub docker quickstart && <ingest recipe>` |
| 11:00 | Wire agents to actual data | Swap test prompts for problem-specific ones |
| 12:30 | Lunch | Eat. Don't skip. Refill water. |
| **1:00** | **Phase 2 build begins** | Heads-down. Use `/yolo` if confident in spec. |
| 2:30 | Mid-build checkpoint | Working e2e demo path? If not, cut scope. |
| 3:00 | Polish demo flow | Practice the 5-min script. Pre-load backup data. |
| 3:30 | `/deslop` → `/review` | Cleanup pass \+ multi-model code review |
| 3:45 | `/ship` to package | Final commit, push, PR if applicable |
| 4:00 | **Submission deadline** | Submit. Breathe. |
| 5:00 | Demo \+ judging | Open with the L6 framing. Run the live trigger. |

---

## Day-of commands cheat sheet

\# At 10:15, after problem reveal:

/spec "\<paste problem statement\>. Use L6 incident response architecture from gdrive:03\_Resources/Hackathon-Playbooks/DataHub × Nebius SF 2026-04-10/DataHub-Nebius \- SELECTED-IDEA.md"

\# After spec approval (\~10:30):

/yolo  \# autonomous execution

\# Mid-day status:

/triage  \# if /yolo runs into issues

\# Before submission (3:30):

/deslop && /review

\# Final ship (3:45):

/ship

---

## Failure modes \+ recovery

| If this happens | Do this |
| :---- | :---- |
| MBP Docker daemon hangs | Force quit Docker Desktop, relaunch, `datahub docker quickstart` again (\~3 min) |
| DataHub UI shows 502 | Wait 60s for ES \+ Kafka to boot, refresh |
| `datahub docker quickstart` fails on disk space | `docker system prune -af && docker volume prune -f` then retry |
| Nebius 401 | Check `op read` worked, re-export `NEBIUS_API_KEY` |
| Nebius 429 (rate limit) | Switch model to Llama 3.1 70B for cheaper/faster calls |
| Venue WiFi blocks Tailscale | Drop to MBP-only mode; Studio A is unreachable, commit to local |
| Whole MBP dies | `ssh elias && ssh studio-a`, demo from Studio A via Tailscale |
| Demo fails live on stage | Have a recorded demo video as Plan B (record it during Phase 2\) |

---

## What to NOT forget

- Charger  
- Phone for hotspot fallback  
- 1Password unlocked on MBP  
- Slack workspace `datahubspace.slack.com` joined  
- The energy to build something exciting  
- Notebook for problem statement notes at 10:15

---

## Mantras for the day

1. **Architecture is committed.** Only prompts and tools swap when the problem drops.  
2. **Phase 1 is for *thinking*, not debugging installs.** Everything was set up last night.  
3. **L6 demo arc**: trigger → 4 agents argue → fix proposal → annotation written back. 30 seconds total.  
4. **The `<think>` block is the wow moment.** Let DeepSeek-R1's reasoning trace show on screen. Judges love seeing the model think.  
5. **If something goes wrong at 3 PM, cut scope, don't add features.**

---

## Live Build State (2026-04-10 morning) — supersedes pre-event checklist above

> The pre-event checklist above was the "before you leave home" plan. This section reflects **current build state at the venue.** Read this section first during the build. For full architectural context, code patterns, and gotchas, see the sibling doc `DataHub-Nebius - STATE-2026-04-10.md`. For Great Expectations setup and the L5 demo mechanics, see `DataHub-Nebius - GX-DEEP-DIVE.md`.

### Current state snapshot

- **DataHub Core running on Studio A** — GMS `http://100.114.31.63:8080`, UI `http://100.114.31.63:9002`
- **47 datasets ingested** across 4 platform instances:
  - `healthcare` (sqlite) — 7 datasets, original sample
  - `olist_source` (sqlite) — 14 datasets, full lineage + tags + glossary + 5 owners
  - `olist_dirty` (sqlite) — 14 datasets, planted issues (orphan FKs, truncated IDs, NULL categories)
  - `nyc_taxi` (sqlite) — 5 datasets, 3-stage raw→staging→mart pipeline
- **Recipe fix in place**: `include_view_lineage: false` in olist recipes (SQLite URN-mismatch bug — lineage handled separately by `add_lineage.py`)
- **L5+L6 architecture locked**: Reality-Checker is the L5 specialist; Coordinator/Detective/Fixer delegate verification to it
- **Fine-tune target**: Llama 3.1 8B + LoRA, 300 NL→GraphQL pairs, READ queries only (writes go through Python SDK)

### ⚠️ Critical blocker to verify before fine-tuning

**Nebius LoRA serverless deprecation Apr 13** (3 days out). Must verify new LoRA jobs still accepted *today* before investing training time. Fallback = Plan B (base Llama 8B + 10 in-context examples).

### Next Actions (priority order)

1. **Get DataHub PAT** from `http://100.114.31.63:9002/settings/tokens` → name `claude-mcp-elias` (only shown once — copy immediately)
2. **Store PAT** in `~/.config/openclaw/shell-secrets.zsh` (chmod 600)
3. **Install DataHub MCP server** on Mac Mini + MBP:
   ```bash
   DATAHUB_GMS_URL=http://100.114.31.63:8080 \
   DATAHUB_GMS_TOKEN=<PAT> \
   uvx mcp-server-datahub@latest
   ```
4. **Verify MCP** with test query: "search DataHub for datasets tagged pii" → should return olist customers/reviews/geolocation
5. **Check Nebius LoRA deprecation status** — determines Plan A (fine-tune) vs Plan B (zero-shot)
6. **Generate 300 NL→GraphQL training pairs** via Nebius Playground + DeepSeek-R1 (10 runs of 30 each)
7. **Upload to Nebius Data Lab → Datasets** (train + val JSONL, 240/60 split)
8. **Launch post-training job** → Llama 3.1 8B + LoRA (rank 16, alpha 32, LR 2e-4, 3 epochs)
9. **Write GE expectations** for planted issues in `olist_dirty` + `healthcare` (see GX-DEEP-DIVE doc for the drop-in `setup_gx.py`)
10. **Wire Fixer agent** with Python SDK helper (`DatahubRestEmitter` + `MetadataChangeProposalWrapper` — *not* GraphQL mutations)
11. **Rehearse demo**, record backup video

### Open questions to close

- [ ] Nebius LoRA serverless deployments still accepting new jobs? (deprecation Apr 13)
- [ ] PAT generated and stored in shell-secrets.zsh?
- [ ] MCP server installed + verified on Mac Mini and MBP?
- [ ] GE expectation suite written for planted issues?
- [ ] Training data generated (300 pairs) and uploaded?
- [ ] Fine-tune job launched?

### localhost gotcha (don't trip on this mid-build)

Three different "localhosts" in play:

| Where | Resolves to | Works? |
|---|---|---|
| MBP browser → `localhost:8080` | MBP itself | ❌ |
| studio-a shell → `curl localhost:8080` | studio-a loopback → Docker GMS | ✅ |
| DataHub UI ingestion recipe → `localhost:8080` | actions container (NOT studio-a) | ❌ — use `http://datahub-gms:8080` |

CLI ingestion from studio-a shell works. UI ingestion sources page is cosmetic only for now.

### Reads vs writes — the rule

- **Reads** (search, lineage, ownership, assertions, schema) → fine-tuned Llama → GraphQL → DataHub
- **Writes** (annotations, tags, descriptions, incident markers) → Python SDK (`DatahubRestEmitter` + `MetadataChangeProposalWrapper`)
- DataHub docs explicitly warn: *"GraphQL mutations are primarily designed to support UI interactions and should generally be avoided in programmatic use cases."*

