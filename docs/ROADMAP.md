# AI Content Engine Roadmap

## Planning Horizon
- Short term: 0-6 weeks
- Medium term: 1-3 months
- Long term: 3-12 months

---

## Short Term Goals (0-6 Weeks)

1. **Stabilize architecture boundaries**
   - Move pipeline logic from `main.py` into `engine/pipeline` modules.
   - Keep `main.py` as a thin CLI entrypoint.

2. **Formalize phase contracts**
   - Keep the 7 conceptual phases as explicit phase IDs.
   - Define phase input/output contracts and prerequisite checks.
   - Evaluate CrewAI `Flows` to model start/listen/router state transitions explicitly.

3. **Strengthen state management**
   - Add typed state schema and `state_version`.
   - Standardize state updates via a single service.

4. **Baseline quality gates**
   - Add linting/formatting and minimal test coverage for state + pipeline transitions.
   - Add CI checks for docs, tests, and static analysis.

5. **Operational traceability**
   - Add structured run logs per topic/phase.
   - Add clear run IDs and artifact lineage metadata.

---

## Medium Term Goals (1-3 Months)

1. **Modular pipeline execution**
   - Introduce phase registry/plugin loader.
   - Allow execution by scope: single topic, queue slice, or full batch.
   - Pilot CrewAI flow-based orchestration for resumable long-running runs.

2. **Memory-aware agents**
   - Add bounded memory strategy for strategist/intelligence agents where it improves consistency.
   - Keep writer/SEO outputs deterministic with prompt+artifact contracts.

3. **Cluster scaling loop**
   - Promote intelligence output into actionable spoke backlog.
   - Add confidence scoring and approval workflow for scale candidates.

4. **Dashboard evolution (still temporary)**
   - Move Streamlit app to `frontend/streamlit/app.py`.
   - Consume engine service interfaces rather than direct file assumptions.

5. **Publishing hardening**
   - Add publish staging lifecycle (`draft`, `approved`, `published`).
   - Add retry-safe publishing and failure recovery.

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
