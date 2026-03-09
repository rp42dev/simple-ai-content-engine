# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses a release-style version history starting from the current MVP baseline.

## [Unreleased]

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
- Optional Phase 5 intelligence memory integration (feature flag: `CREWAI_INTELLIGENCE_MEMORY_ENABLED`) with topic-scoped recall/save behavior.

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
