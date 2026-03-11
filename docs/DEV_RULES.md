# Development Rules

This document defines how to build safely in an AI-assisted workflow while protecting pipeline stability.

---

## 1) Git Workflow (Required)

### Branching Model
- `main`: production-stable only.
- `dev`: integration branch for validated features.
- `feature/*`: short-lived branches for isolated work.

Examples:
- `feature/engine-phase-registry`
- `feature/state-schema-v2`
- `feature/dashboard-queue-visuals`

### Merge Policy
- `feature/*` -> `dev` via PR with review.
- `dev` -> `main` only after release readiness checks.
- No direct pushes to `main`.

### Commit Style
Use Conventional-style prefixes:
- `feat:` new capability
- `fix:` bug fix
- `refactor:` internal restructuring without behavior change
- `docs:` documentation only

Examples:
- `feat: extract phase runner into engine module`
- `fix: preserve topic state during partial spoke runs`
- `refactor: move link injection into finalization service`
- `docs: add architecture and roadmap baselines`

---

## 2) Change Safety Rules

1. **One concern per PR**
   - Avoid mixing engine logic refactors with UI changes in one PR.

2. **Protect stable components**
   - Treat phase contracts and state schema as protected interfaces.
   - Any breaking change requires migration notes and test updates.

3. **Idempotent phase behavior**
   - Re-running a phase must not duplicate or corrupt artifacts.

4. **State-first reliability**
   - All phase transitions must persist state only after successful artifact write.
   - Failed phase runs must preserve resumability.

5. **No hidden UI logic**
   - Business rules belong in engine/services, not Streamlit handlers.

---

## 3) AI-Agent Assisted Coding Workflow

### Before Modifying Code
- Identify impacted phase(s) and state keys.
- Confirm whether change is behavior, refactor, or docs only.
- Add or update a brief plan in PR description.

### During Implementation
- Modify the smallest stable surface possible.
- Keep agent/task prompts versioned and diff-reviewable.
- Prefer explicit contracts over implicit file-name heuristics.

### Validation Checklist (Minimum)
- Run targeted flow for affected phase(s).
- Validate state transitions for partial and full runs.
- Verify generated artifact names and tier progression (`.md`, `_seo.md`, `_final.md`).

### Incremental Testing Protocol (Required)
Always test in increments before moving to broader runs:

1. **Step test (smallest scope)**
   - Run one topic and one affected phase path first.
   - Confirm expected state key transitions and artifact creation.

2. **Path test (related phases)**
   - Run contiguous phases touched by the change (for example, strategy -> pillar -> spoke).
   - Confirm resumability from partial completion state.

3. **Batch test (queue behavior)**
   - Run at least 2 topics with different priorities.
   - Confirm queue ordering and per-topic isolation.

4. **Regression check**
   - Re-run previously completed topic and verify idempotent skip behavior.

5. **Document next test step in every PR**
   - Each PR must include: "Tested now" and "Recommended next test".

### PR Checklist
- [ ] Branch name follows `feature/*`.
- [ ] Commit messages use approved prefixes.
- [ ] Pipeline phase impact documented.
- [ ] `docs/ARCHITECTURE.md` updated if structure/flow changed.
- [ ] `CHANGELOG.md` updated under `Unreleased` for user-visible changes.
- [ ] Incremental testing notes included (`Tested now` + `Recommended next test`).

---

## 4) CrewAI Framework Compliance

### AI-Assisted Coding Requirements
All AI-assisted coding (Copilot, agents, etc.) must follow the CrewAI framework strictly:
- Use `Crew`, `Flow`, `Task`, and hierarchical process first.
- Do not create manual loops or custom orchestration.
- Check for required CrewAI imports/modules and add if missing.

### Workflow Enforcement
- Check `docs/ARCHITECTURE.md` before modifying flows or agents.
- Follow `docs/ROADMAP.md` for priorities.
- Update `CHANGELOG.md` and `docs/RELEASE_CHECKLIST.md` as usual.
- No new planning docs — always update existing ones.

---

## 5) Architecture Documentation Update Policy

Update `docs/ARCHITECTURE.md` whenever any of these changes occur:
- New phase added, removed, or reordered.
- Phase prerequisites/state transitions changed.
- New shared module or service boundary introduced.
- Frontend begins owning new operational responsibilities.

Required in same PR:
1. Updated architecture section(s).
2. Updated roadmap impact (if milestone changes).
3. Changelog entry under `Unreleased`.

---

## 6) Dashboard Evolution Guidance

Current dashboard is temporary and operational.

Future dashboard should provide:
- Queue view with priority and status.
- Topic-level phase progression and run history.
- Cluster map/graph visibility (pillar-spoke relationships).
- Intelligence gap backlog and scaling suggestions.
- Artifact lineage (`draft -> seo -> final`) and publish readiness.

Do not couple dashboard components to direct filesystem assumptions long-term; use engine service endpoints/contracts.
