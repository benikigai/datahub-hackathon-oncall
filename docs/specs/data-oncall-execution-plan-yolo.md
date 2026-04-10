# Yolo: data-oncall-execution-plan
**Spec:** docs/specs/data-oncall-execution-plan.md

## LEFT terminal — incident_response harness + GE setup
- [x] Task L0: Smoke tests — all endpoints reachable — SIMPLE
- [x] Task L1: Repo scaffold + git init — SIMPLE
- [x] Task L2: Event models + tools layer — MODERATE
- [x] Task L3: GE setup + run against both instances — MODERATE
- [x] Task L4: BaseAgent + LoRA-or-base swap — SIMPLE
- [x] Task L5: Coordinator agent (Kimi-K2-Thinking) — MODERATE
- [x] Task L6: Detective agent (Llama, lineage focus) — MODERATE
- [x] Task L7: Reality-Checker agent (Llama + Python diff) — MODERATE
- [x] Task L8: Fixer agent (MiniMax-M2.5) — MODERATE
- [x] Task L9: Orchestrator + trigger CLI — MODERATE
- [x] Task L10: End-to-end smoke test (LEFT only) — SIMPLE

## MIDDLE terminal — dashboard
- [x] Task M1: Dashboard skeleton + stub events — SIMPLE
- [x] Task M2: FastAPI + SSE + trigger mutex — MODERATE
- [x] Task M3: HTML 4-pane layout + dark theme + fine-tune story panel — SIMPLE
- [x] Task M4: SSE client + DOM updates + cost counter + LEDs — MODERATE
- [x] Task M5: Trigger button + reset mechanism — SIMPLE
- [x] Task M6: End-to-end test with stubs — SIMPLE
- [x] Task M7: Wire to real orchestrator — MODERATE

## RIGHT terminal — fine-tune
- [x] Task R1: Seeds + R1 batch generation — SIMPLE  *(scripts ready, not yet run)*
- [ ] Task R2: Validate pairs against live DataHub — MODERATE  *(needs R1 to run first)*
- [ ] Task R3: Format + split + upload to Nebius — SIMPLE  *(needs Nebius UI upload)*
- [ ] Task R4: Launch LoRA training — SIMPLE  *(needs Nebius UI + ~25min training)*
- [ ] Task R5: Deploy LoRA endpoint + smoke test — SIMPLE  *(needs R4 done)*
- [x] Task R6: Plan B fallback ready — SIMPLE  *(in-context seeds prompt at training/plan_b_system_prompt.txt; nl_to_graphql.py auto-loads it)*

## Integration
- [ ] Task I1: LEFT plugs in LoRA endpoint — SIMPLE
- [x] Task I2: LEFT × MIDDLE integration test — MODERATE  *(real orchestrator via dashboard SSE → 69s, 50 events, 3 quarantines)*
- [ ] Task I3: Full end-to-end demo rehearsal — MODERATE
- [ ] Task I4: Backup video recording — SIMPLE
- [ ] Task I5: GitHub repo public + final push — SIMPLE
