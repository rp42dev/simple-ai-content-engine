# AI Content Engine Architecture

## Purpose
This document defines the current architecture, target repository layout, and execution/data flow for long-term development.

The current dashboard is a temporary operations surface and does not define the engine architecture.

---

## Current System Snapshot

### Engine Modules
- `main.py` is the current pipeline runner and phase coordinator.
- `crews/content_crew.py` composes CrewAI crews for strategy, writing, SEO, and intelligence.
- `tasks/` contains task templates that encode task contracts (inputs/expected outputs).

### Agents
- `agents/strategist.py`: pillar/spoke cluster strategy.
- `agents/writer.py`: outline + article generation.
- `agents/seo_agents.py`: SEO optimization + internal linking suggestions.
- `agents/intelligence_agents.py`: competitor crawling + content gap detection.

### Tools
- `tools/state_manager.py`: workflow state persistence by topic.
- `tools/link_injector.py`: resolves placeholder links into concrete article filenames.
- `tools/search_tools.py`: crawling/scraping tool access.
- `tools/wordpress_tool.py`: optional publishing integration.

### Pipeline Orchestration
Current execution in `main.py` is phase-based and queue-driven:
1. Cluster Strategy
2. Pillar + Spoke Generation
3. SEO Optimization
4. Final Link Injection

Intelligence and scaling capabilities exist in the codebase (`run_intelligence_crew`, queue/state model) and should be formalized as first-class phases in the target architecture.

### State Handling
- State is JSON-file based under `state/`.
- Per-topic files (`state/workflow_<topic>.json`) hold progress flags and counters.
- Queue source is `topics_queue.json`.

### Outputs
- Cluster blueprints: `outputs/*_cluster.json`
- Draft and transformed content: `outputs/*.md`, `*_seo.md`, `*_final.md`

### Frontend / Dashboard
- `dashboard.py` (Streamlit) is currently a temporary operations console.
- It starts pipeline runs, shows status/progress, manages queue entries, and previews artifacts.
- It should stay thin and call engine interfaces instead of owning business rules.

---

## Canonical Pipeline (Must Preserve)

The conceptual pipeline for long-term architecture is:
1. Cluster Strategy
2. Pillar Article Generation
3. Spoke Article Generation
4. SEO Optimization
5. Intelligence (Content Gap Detection)
6. Cluster Scaling
7. Final Link Injection

Notes:
- Phase 2 and 3 may execute in one production stage internally, but must remain separately tracked.
- Phase 6 uses intelligence outputs to add/refine spokes and schedule incremental production runs.

---

## Target Repository Structure

```text
ai-content-engine/
  engine/
    __init__.py
    pipeline/
      runner.py                # Phase scheduler + execution graph
      phases/
        cluster_strategy.py
        pillar_generation.py
        spoke_generation.py
        seo_optimization.py
        intelligence_gap_detection.py
        cluster_scaling.py
        final_link_injection.py
    models/
      topic.py                 # Topic/work item models
      cluster.py               # Cluster/spoke contracts
      workflow_state.py        # Typed state schema
    services/
      queue_service.py
      state_service.py
      artifact_service.py

  agents/
    strategist.py
    writer.py
    seo_agents.py
    intelligence_agents.py
    registry.py                # Agent factory/registration layer

  tasks/
    strategist_tasks.py
    writer_tasks.py
    seo_tasks.py
    intelligence_tasks.py

  crews/
    content_crew.py            # Transitional adapter; eventually optional

  tools/
    link_injector.py
    search_tools.py
    wordpress_tool.py

  state/
    workflow_state.json
    workflow_<topic>.json

  outputs/
    *.json
    *.md

  frontend/
    streamlit/
      app.py                   # Temporary monitor/control UI

  scripts/
    run_pipeline.py
    migrate_state.py
    backfill_artifacts.py

  docs/
    ARCHITECTURE.md
    ROADMAP.md
    DEV_RULES.md

  CHANGELOG.md
  requirements.txt
  main.py                      # Transitional entrypoint; delegates to engine
```

---

## Responsibility Boundaries

### Engine (`engine/`)
- Owns phase ordering, retry policy, state transitions, validation, and resumability.
- No Streamlit/UI logic.

### Agents + Tasks (`agents/`, `tasks/`)
- Define LLM behavior and expected outputs.
- Must remain stateless and reusable across interfaces (CLI/UI/API).

### Tools (`tools/`)
- Deterministic side-effect modules (scraping, link rewriting, publishing).
- Should expose clear contracts and input validation.

### Frontend (`frontend/`)
- Reads queue/state/outputs via engine services.
- Triggers pipeline actions through stable interfaces; no file-shape assumptions.

---

## Data Flow

1. Queue item loaded (`topic`, optional metadata, priority).
2. Pipeline runner resolves latest state snapshot.
3. Each phase executes if prerequisite flags are satisfied.
4. Artifacts are written to `outputs/`.
5. State transitions are persisted atomically per phase.
6. Intelligence findings create/upsert additional spokes (scaling inputs).
7. Final link injection produces publish-ready `*_final.md` artifacts.

---

## Stability and Scaling Recommendations

1. Introduce a typed state schema and version field (`state_version`) for migration safety.
2. Move phase logic out of `main.py` into `engine/pipeline/phases/*` modules.
3. Add a phase registry (plugin pattern) so new phases can be added without editing runner core.
4. Make each phase idempotent (safe to re-run without data corruption).
5. Separate artifact tiers explicitly: `draft -> seo -> final`.
6. Keep UI as a client of engine APIs/services, not an orchestration owner.
