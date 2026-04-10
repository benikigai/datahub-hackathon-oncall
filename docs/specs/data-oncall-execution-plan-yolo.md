# Yolo: data-oncall-execution-plan
**Spec:** docs/specs/data-oncall-execution-plan.md

## LEFT terminal — incident_response harness + GE setup
- [ ] Task L0: Smoke tests — all endpoints reachable — SIMPLE
- [ ] Task L1: Repo scaffold + git init — SIMPLE
- [ ] Task L2: Event models + tools layer — MODERATE
- [ ] Task L3: GE setup + run against both instances — MODERATE
- [ ] Task L4: BaseAgent + LoRA-or-base swap — SIMPLE
- [ ] Task L5: Coordinator agent (Kimi-K2-Thinking) — MODERATE
- [ ] Task L6: Detective agent (Llama, lineage focus) — MODERATE
- [ ] Task L7: Reality-Checker agent (Llama + Python diff) — MODERATE
- [ ] Task L8: Fixer agent (MiniMax-M2.5) — MODERATE
- [ ] Task L9: Orchestrator + trigger CLI — MODERATE
- [ ] Task L10: End-to-end smoke test (LEFT only) — SIMPLE

## MIDDLE terminal — dashboard
- [ ] Task M1: Dashboard skeleton + stub events — SIMPLE
- [ ] Task M2: FastAPI + SSE + trigger mutex — MODERATE
- [ ] Task M3: HTML 4-pane layout + dark theme — SIMPLE
- [ ] Task M4: SSE client + DOM updates — MODERATE
- [ ] Task M5: Trigger button + reset mechanism — SIMPLE
- [ ] Task M6: End-to-end test with stubs — SIMPLE
- [ ] Task M7: Wire to real orchestrator — MODERATE

## RIGHT terminal — fine-tune
- [ ] Task R1: Seeds + R1 batch generation — SIMPLE
- [ ] Task R2: Validate pairs against live DataHub — MODERATE
- [ ] Task R3: Format + split + upload to Nebius — SIMPLE
- [ ] Task R4: Launch LoRA training — SIMPLE
- [ ] Task R5: Deploy LoRA endpoint + smoke test — SIMPLE
- [ ] Task R6: Plan B fallback ready — SIMPLE

## Integration
- [ ] Task I1: LEFT plugs in LoRA endpoint — SIMPLE
- [ ] Task I2: LEFT × MIDDLE integration test — MODERATE
- [ ] Task I3: Full end-to-end demo rehearsal — MODERATE
- [ ] Task I4: Backup video recording — SIMPLE
- [ ] Task I5: GitHub repo public + final push — SIMPLE
