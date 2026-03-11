# AI Content Engine Roadmap

## Senior Dev Execution Mode (Ship First)

### Principles
- Keep momentum: deliver runnable, testable increments every session.
- Prioritize reliability over sophistication until stable daily runs are routine.
- Defer polish features unless they remove a real blocker.

### Priority Labels
- **P0 (Critical Now)**: Required to reliably run the full pipeline.
- **P1 (Important Next)**: Improves safety and scale after stable runs.
- **P2 (Tiny / Non-Critical)**: Nice-to-have improvements that can wait.

### Definition of "Running"
- End-to-end 7-phase run completes on at least 2 topics without manual fixes.
- Resume/retry behavior works from state for interrupted runs.
- `--topic`, `--topic-limit`, and `--spoke-limit` execution controls behave correctly.
- Core outputs are generated with predictable naming and traceable state updates.

## Planning Horizon
- Short term: 0-6 weeks
- Medium term: 1-3 months
- Long term: 3-12 months

---

## Short Term Goals (0-6 Weeks)

1. **[DONE] P0: Close execution blockers**
   - `--topic-limit` queue slicing stable and honored in batch mode.
   - `--topic` precedence over queue slicing enforced.
   - Phase skip with explicit reason supported via standardized `Skipping:` log format.

2. **[DONE] P0: Lock state reliability**
   - `state_version` schema stamping on load/save implemented.
   - Atomic state writes and compatibility normalization in place.
   - All state mutations routed through `tools/state_manager.py`.

3. **[DONE] P0: Run verification baseline**
   - `tests/test_p0_regressions.py` covers queue filtering, `--topic` precedence, and state normalization.
   - Standard smoke matrix documented in DEV_RULES.md.

4. **[DONE] P1: Formalize phase contracts**
   - Canonical 11-phase pipeline running in `runner.py`.
   - Standardized skip reason codes defined in `phase_logging.py`.
   - Prerequisite checks added to all 11 phases; all skips emit structured `Skipping:` log lines.
   - CrewAI Flow adapter behind `CREWAI_FLOW_SPIKE_ENABLED` feature flag.

5. **[DONE] P1: Operational traceability**
   - `run_id` generated per run and emitted to console.
   - Run summaries written to `outputs/run_summaries/*.json`.
   - CLI commands: `--last-run`, `--run-id`, `--run-list`, `--failed-only`, `--json`.

6. **P2: Tiny/non-critical polish (defer until stable)**
   - Cleaner console output formatting and emoji-safe Windows logging.
   - Extra dashboard UX refinements.
   - Small docs polish and naming consistency passes.

---

## Medium Term Goals (1-3 Months)

1. **P1: Modular pipeline execution hardening**
   - Introduce phase registry/plugin loader.
   - Preserve execution scopes: single topic, queue slice, full batch.
   - Keep flow-based orchestration as opt-in until parity is proven.

2. **P1: Memory-aware agents (bounded use)**
   - Continue scoped memory for intelligence where measurable value exists.
   - Keep writer/SEO deterministic with artifact-driven contracts.
   - Add simple memory metrics (recall count, reuse quality notes).

3. **P1: Cluster scaling loop**
   - Convert intelligence results into actionable spoke backlog.
   - Add confidence score + manual approval gate for new scale candidates.

4. **P2: Dashboard evolution (temporary UI)**
   - Move Streamlit app to `frontend/streamlit/app.py`.
   - Consume engine service interfaces (not direct file coupling).

5. **P2: Publishing hardening**
   - Add publish lifecycle (`draft`, `approved`, `published`).
   - Improve retry/failure recovery semantics.

---

## Long Term Vision (3-12 Months)

1. **Engine/API separation**
   - Expose the engine through API/worker architecture.
   - Enable multiple frontends (Streamlit, web app, or CLI) on the same backend.

2. **Scalable orchestration**
   - Queue-backed execution workers and durable job history.
   - Parallelizable processing for independent topics/phases.

3. **Knowledge graph + cluster intelligence**
   - Build a cluster map/graph model to optimize internal linking and coverage.
   - Introduce authority scoring and cluster health diagnostics.

4. **Enterprise readiness**
   - Multi-user auth, role-based approvals, audit logs.
   - Secret management, observability dashboards, and SLA-aware retries.

---

## Future Features Backlog

- Site crawling beyond single URL snapshots.
- Automated publishing workflows with approval gates.
- Cluster graph linking optimization and visualization.
- Content refresh/re-optimization scheduler.
- SERP monitoring feedback loop.
- Topic opportunity discovery using competitor + trend intelligence.
- Human-in-the-loop editorial checkpoints.

---

## Current Recommended Sequence (What We Do Next)

1. **P0** Fix `--limit` behavior and add tests for queue slicing.
2. **P0** Add state schema/version checks and atomic phase-state updates.
3. **P0** Run smoke matrix on 2 fresh topics and log baseline outcomes.
4. **P1** Add run IDs + execution summaries for traceability.
5. **P2** Defer cosmetic/logging/dashboard polish until all P0 checks pass consistently.
