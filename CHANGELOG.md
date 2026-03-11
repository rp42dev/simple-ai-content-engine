# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses a release-style version history starting from the current MVP baseline.

## [Unreleased]

## [0.5.0-beta.1] - 2026-03-11

### Added
- `engine/pipeline/phase_registry.py`: canonical phase registry with:
  - `PhaseDefinition` dataclass declaring each phase's ID, module path, runner function, and extra config args.
  - `PHASE_DEFINITIONS`: ordered list of all 11 canonical phases.
  - `get_phase_ids()`: returns stable ordered phase ID list.
  - `get_phase(phase_id)`: fast O(1) lookup by ID.
  - `build_phases(queue, config)`: builds the executable `(phase_id, callable)` list for `runner.py`, resolving extra args from run config.
  - `PIPELINE_SKIP_PHASES` env var support: comma-separated phase IDs to disable at runtime for debugging/testing without touching code.
- 8 new `PhaseRegistryTests` covering canonical order, phase lookup, extra-arg wiring, `PIPELINE_SKIP_PHASES` disabling, and callable validation.

### Changed
- `engine/pipeline/runner.py`: replaced hardcoded phase import list and inline phase tuples with `build_phases()` from the registry. Runner is now decoupled from phase module imports.
- `tests/test_p0_regressions.py`: updated `_patch_phases()` to patch via module string paths (registry-compatible); added `import os`.

## [0.4.1-beta.1] - 2026-03-11

### Added
- Standardized skip reason code constants in `engine/pipeline/phase_logging.py`:
  `completed`, `missing_prerequisite`, `cluster_approval_pending`, `writing_pending`,
  `seo_pending`, `intelligence_pending`, `link_injection_pending`, `humanization_pending`,
  `competitor_url_missing`, `cluster_data_missing`, `final_files_missing`, `article_files_missing`.

### Changed
- Formalized prerequisite checks for all 11 pipeline phases:
  - `cluster_strategy`: skips with `missing_prerequisite` if `cluster_map_generated` state key not set.
  - `serp_analysis`: skips with `missing_prerequisite` if `cluster_generated` state key not set.
  - `pillar_generation`: replaced silent `continue` on missing cluster file with logged `missing_prerequisite` skip.
  - `spoke_generation`: replaced silent `continue` on missing cluster file with logged `missing_prerequisite` skip.
  - `seo_optimization`: skips with `writing_pending` if `pillar_written` not set; replaced silent `continue` on missing cluster file with logged `missing_prerequisite` skip.
  - `intelligence_gap_detection`: skips with `missing_prerequisite` if `cluster_generated` state key not set.
  - `final_link_injection`: skips with `seo_pending` if `seo_optimized` not set.
  - Phases already covered: `cluster_scaling` (`intelligence_pending`), `humanization_readability` (`link_injection_pending`), `article_quality_assurance` (`humanization_pending`).
- All phase skips now emit a structured `Skipping:` log line captured by run summaries.

## [0.4.0-beta.1] - 2026-03-11

### Added
- Expanded pipeline to **11 phases** (from 7): added Cluster Map Generation (phase 1), SERP Analysis (phase 3), Humanization & Readability (phase 10), and Article Quality Assurance (phase 11).
- `engine/pipeline/phase_logging.py`: standardized phase skip log format (`Skipping: phase=... topic="..." reason=...`).
- Minimal P0 regression suite in `tests/test_p0_regressions.py` covering:
  - `--topic-limit` queue slicing and priority order behavior.
  - `--topic` precedence over queue slicing.
  - `state_version` defaults and schema normalization for legacy/typed values.
- Run traceability in pipeline execution:
  - Generated `run_id` emitted per run.
  - Per-run summary artifacts written to `outputs/run_summaries/*.json` with config, selected topics, phase statuses/timings, and final status.
  - Standardized phase skip logs captured into summary `skips` per phase.
  - Regression coverage for success and failure summary writing paths.
  - CLI run-summary inspector commands: `--last-run` and `--run-id`.
  - `--run-list [N]` to list recent run summaries.
  - `--failed-only` filter for `--run-list`.
  - `--json` output mode for `--last-run`, `--run-id`, and `--run-list`.
- Config profile system: `config/profile_defaults.json`, `config/profile_resolver.py`, `config/policies/`.
- `tools/article_post_processor.py`: post-processing transformations for generated articles.
- CrewAI framework compliance section in `docs/DEV_RULES.md`:
  - Requires use of `Crew`, `Flow`, `Task`, and hierarchical process for all AI-assisted coding.
  - Prohibits manual loops or custom orchestration.
  - Enforces ARCHITECTURE.md/ROADMAP.md checks before modifying flows or agents.
  - No new planning docs policy — always update existing ones.

### Changed
- CLI execution controls now distinguish between topic batching and spoke depth:
  - Added `--topic-limit` to cap number of topics processed from prioritized queue.
  - Added `--spoke-limit` as explicit spoke generation cap per topic.
  - Kept `--limit` as a backward-compatible alias for `--spoke-limit`.
- State management is now versioned and normalized:
  - Added `state_version` schema stamping on load/save.
  - Added compatibility normalization for legacy keys and value types.
  - Added atomic state writes to reduce partial-write risk.
- Dashboard topic state load/save now routes through `tools/state_manager.py` for consistent validation behavior.
- `docs/ARCHITECTURE.md` updated to reflect 11-phase pipeline, all actual tools, and current repo structure.
- `docs/ROADMAP.md` Short Term Goals updated to mark completed P0/P1 items.

## [0.3.0-beta.1] - 2026-03-09

### Added
- **Flow/Memory spike** with feature-flagged adoption:
  - `engine/pipeline/flow_spike.py`: Safe Flow orchestration adapter with graceful fallback to stable runner (`CREWAI_FLOW_SPIKE_ENABLED`).
  - Scoped memory integration for Phase 5 (Intelligence) with topic-specific recall/save under `/topic/{slug}/intelligence` scope (`CREWAI_INTELLIGENCE_MEMORY_ENABLED`).
  - Optional log line showing recalled prior insights count per Phase 5 execution for faster parity checks.
- Release governance documentation:
  - `.github/pull_request_template.md`: PR checklist enforcing phase testing and docs updates.
  - `docs/RELEASE_CHECKLIST.md`: Step-by-step release validation workflow.
- Git workflow initialized with branching model (`main`, `dev`, `feature/*`) and incremental version tags.

### Validated
- Memory accumulation: 13 discrete intelligence facts persisted and recalled across two Phase 5 runs on real topic (Invisalign).
- Baseline pipeline parity: No regressions with Flow/Memory flags disabled; identical outputs confirmed.
- Graceful degradation: Memory recall/save operations fail safely with no pipeline disruption.

## [0.2.0] (previously Unreleased)

### Added
- Baseline `.gitignore` for Python envs, caches, generated artifacts, and runtime state files.
- Basic project `README.md` with run instructions and incremental testing workflow.
- New modular engine pipeline package under `engine/`:
  - `engine/pipeline/runner.py`
  - `engine/pipeline/phases/*` (7 conceptual phases)
  - `engine/pipeline/helpers.py`
- Incremental testing protocol in `docs/DEV_RULES.md` with required PR fields:
  - `Tested now`
  - `Recommended next test`

### Changed
- `main.py` is now a thin CLI entrypoint delegating orchestration to `engine.pipeline.runner`.
- `dashboard.py` status parsing now supports 7-phase pipeline log labels.
- Removed duplicate `render_status` implementation in `dashboard.py`.

### Documentation
- Repository governance docs:
  - `docs/ARCHITECTURE.md`
  - `docs/ROADMAP.md`
  - `docs/DEV_RULES.md`
- Documented canonical 7-phase pipeline for long-term architecture:
  1. Cluster Strategy
  2. Pillar Article Generation
  3. Spoke Article Generation
  4. SEO Optimization
  5. Intelligence (Content Gap Detection)
  6. Cluster Scaling
  7. Final Link Injection
- Defined branching model (`main`, `dev`, `feature/*`) and commit style (`feat:`, `fix:`, `refactor:`, `docs:`).

## [0.1.0] - 2026-03-09

### Added
- MVP AI content pipeline with CrewAI-based multi-agent generation.
- Queue-based topic processing using `topics_queue.json`.
- Strategy phase producing topic cluster blueprints.
- Pillar and spoke article generation flow.
- SEO optimization and internal linking content transformation.
- Final link injection stage for publish-ready markdown.
- JSON file-based workflow state tracking by topic in `state/`.
- Streamlit dashboard for queue management, run controls, approvals, and artifact preview.
- Initial WordPress publishing integration utility.

### Notes
- Current UI is treated as operational/temporary and not the canonical architecture boundary.
- Next development phase focuses on modular engine extraction, stronger state contracts, and scalability.
