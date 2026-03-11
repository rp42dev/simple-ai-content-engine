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
  - `python main.py --topic "Invisalign" --spoke-limit 2`
- Prioritized queue slice (batch cap):
  - `python main.py --topic-limit 2 --spoke-limit 2`
- Backward compatibility:
  - `--limit` still works as alias for `--spoke-limit`
- Inspect latest run summary:
  - `python main.py --last-run`
  - JSON: `python main.py --last-run --json`
- Inspect specific run summary:
  - `python main.py --run-id run_YYYYMMDDTHHMMSSZ_xxxxxxxx`
  - JSON: `python main.py --run-id run_YYYYMMDDTHHMMSSZ_xxxxxxxx --json`
- List recent run summaries:
  - `python main.py --run-list`
  - `python main.py --run-list 20`
  - Failed runs only: `python main.py --run-list 20 --failed-only`
  - JSON list: `python main.py --run-list 20 --json`

Run traceability:
- Each run gets a generated `run_id` printed in console.
- A run summary JSON is written to `outputs/run_summaries/` with:
  - run config (`topic`, `topic_limit`, `spoke_limit`),
  - selected topics,
  - per-phase status/timing,
  - standardized skip events (`phase`, `topic`, `reason`, `detail`),
  - final run status and duration.

## Flow Spike (Feature Flag)
This repo includes a safe CrewAI Flow integration spike behind env flags.

- Enable flow spike path:
  - PowerShell: `$env:CREWAI_FLOW_SPIKE_ENABLED="1"`
- Optional memory flag for spike validation path:
  - PowerShell: `$env:CREWAI_FLOW_MEMORY_ENABLED="1"`

Current behavior is intentionally non-breaking: spike mode logs flow/memory path activation and runs the same stable phase runner underneath.

### Optional Intelligence Memory (Phase 5)
- Enable intelligence-only memory:
  - PowerShell: `$env:CREWAI_INTELLIGENCE_MEMORY_ENABLED="1"`

Behavior:
- Applies only to Phase 5 (Content Gap Detection).
- Recalls prior intelligence context from scoped memory path: `/topic/<topic_slug>/intelligence`.
- Stores newly extracted intelligence facts back into that same scope.
- If memory dependencies/keys are unavailable, pipeline continues safely without memory.

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
1. Step test: one topic (`--topic`) and low spoke limit (`--spoke-limit 1`)
2. Path test: rerun affected contiguous phases and confirm resumability
3. Batch test: two or more topics with priorities (`--topic-limit 2`)
4. Regression test: rerun completed topic and confirm skip/idempotent behavior

Minimal local regression tests:
- `D:/ai-content-engine/.venv/Scripts/python.exe -m unittest tests/test_p0_regressions.py -v`

Recommended spike smoke commands:
- Baseline: `python main.py --topic "__smoke_nonexistent_topic__" --spoke-limit 1`
- Flow flag path: set `CREWAI_FLOW_SPIKE_ENABLED=1` then rerun baseline command

## Docs
- `docs/ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `docs/DEV_RULES.md`
- `docs/RELEASE_CHECKLIST.md`
- `CHANGELOG.md`

## Team Workflow Files
- PR template: `.github/pull_request_template.md`
