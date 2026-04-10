# Context: data-oncall-execution-plan
**Last updated:** 2026-04-10
**Phase:** Spec approved
**Approved option:** Option C — Parallel with stubs + 30-minute integration checkpoints
**Tasks:** 29 (Simple: 18, Moderate: 11, Complex: 0)
**Critic verdict:** CONCERNS — addressed in task ordering

## Key risks
- LoRA training fails or times out → Plan B (base Llama + in-context seeds) ready via env-var swap (Task R6 + I1)
- MiniMax M2.5 endpoint slug typo → Smoke tested in Task L0 before any agent code
- GE plugin requires `great_expectations<1.0.0` → Pinned in `pyproject.toml` (Task L1)
- DataHub PAT generation requires manual UI action → Blocker in Task L0, asks user to generate

## Approved decisions (from Phase 1 user choices)
1. Demo trigger UX: **Both** CLI and dashboard button (option C)
2. Reality-Checker diff: **Hybrid Python diff + LLM narrative** (option C)
3. DataHub annotation: **editableSchemaMetadata + customProperties** belt-and-suspenders (option C)
4. Time budget confirmed: **3.5–4 hours** focused build, 4PM submission, 5PM demo

## Architecture status
- LOCKED in `docs/specs/research/DataHub-Nebius - PROJECT-SPEC.md`
- 4 agents: Coordinator (Kimi-K2-Thinking) → Detective + Reality-Checker (Llama 3.1 8B + LoRA) → Fixer (MiniMax-M2.5)
- All 4 hosted on Nebius, all 4 OpenAI-compatible
- Uses DataHub at Studio A `100.114.31.63:8080` via Tailscale
- 47 datasets pre-ingested; 3 planted issues in `olist_dirty` confirmed (deleted customers, truncated seller_ids, NULL categories)

## Research
9 PARA docs synced into `docs/specs/research/`:
- PROJECT-SPEC.md, STATE-2026-04-10.md, GX-DEEP-DIVE.md, FINETUNE-SEEDS.md
- PREP.md, INTEL.md, IDEAS.md, SELECTED-IDEA.md, TECH-REFERENCE.md

## Execution mode
User chose **one-shot in this terminal via /yolo**. Other 2 terminals reassigned to other items. This terminal will execute all 29 tasks sequentially. Some tasks require manual user action (PAT generation, Nebius UI actions, demo rehearsal observation, GitHub repo creation auth) — /yolo will pause and ask when blocked.
