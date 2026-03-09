# AI Content Engine

AI Content Engine is a CrewAI-based pipeline for generating SEO content clusters using multiple agents and phased execution.

## Current Pipeline Phases
1. Cluster Strategy
2. Pillar Article Generation
3. Spoke Article Generation
4. SEO Optimization
5. Intelligence (Content Gap Detection)
6. Cluster Scaling
7. Final Link Injection

## Quick Start
1. Create and activate your Python environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Add environment variables in `.env` (for model/provider keys).
4. Add topics in `topics_queue.json`.

## Run
- Full queue:
  - `python main.py`
- Single topic:
  - `python main.py --topic "Invisalign" --limit 2`

## Dashboard (Temporary Ops UI)
- Run Streamlit monitor/control UI:
  - `streamlit run dashboard.py`

## Project Structure (Current)
- `engine/` modular pipeline runner + phase modules
- `agents/` CrewAI agents
- `tasks/` task contracts/prompts
- `crews/` crew orchestration adapters
- `tools/` state, linking, crawl, publish helpers
- `state/` workflow JSON state
- `outputs/` generated artifacts
- `docs/` architecture, roadmap, development rules

## Incremental Testing Workflow
Always test in this order:
1. Step test: one topic (`--topic`) and low spoke limit (`--limit 1`)
2. Path test: rerun affected contiguous phases and confirm resumability
3. Batch test: two or more topics with priorities
4. Regression test: rerun completed topic and confirm skip/idempotent behavior

## Docs
- `docs/ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `docs/DEV_RULES.md`
- `docs/RELEASE_CHECKLIST.md`
- `CHANGELOG.md`

## Team Workflow Files
- PR template: `.github/pull_request_template.md`
