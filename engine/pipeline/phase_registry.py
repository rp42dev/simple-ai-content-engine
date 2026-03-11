"""
Phase registry for the AI Content Engine pipeline.

Defines the canonical ordered list of pipeline phases and provides
build_phases() to construct the executable phase list for runner.py.

Phases can be selectively disabled at runtime via the environment variable:
    PIPELINE_SKIP_PHASES=<comma-separated phase IDs>
    e.g. PIPELINE_SKIP_PHASES=intelligence_gap_detection,cluster_scaling

This does NOT replace the prerequisite checks inside each phase — skipping
a phase via the registry is an operator-level override for testing/debugging.
"""

import os
from dataclasses import dataclass, field
from typing import Callable, List, Optional


@dataclass
class PhaseDefinition:
    """Declares a single pipeline phase."""
    phase_id: str                          # Stable ID used in state keys and run summaries
    module_path: str                       # Dotted import path relative to engine.pipeline.phases
    runner_fn: str                         # Name of the callable inside the module (usually "run")
    extra_args: List[str] = field(default_factory=list)  # Config keys passed as positional args


# ---------------------------------------------------------------------------
# Canonical 11-phase pipeline — order is execution order
# extra_args refer to keys in the RunConfig dict passed to build_phases()
# ---------------------------------------------------------------------------
PHASE_DEFINITIONS: List[PhaseDefinition] = [
    PhaseDefinition(
        phase_id="cluster_map_generation",
        module_path="engine.pipeline.phases.cluster_map_generation",
        runner_fn="run",
        extra_args=["cluster_size"],
    ),
    PhaseDefinition(
        phase_id="cluster_strategy",
        module_path="engine.pipeline.phases.cluster_strategy",
        runner_fn="run",
    ),
    PhaseDefinition(
        phase_id="serp_analysis",
        module_path="engine.pipeline.phases.serp_analysis",
        runner_fn="run",
    ),
    PhaseDefinition(
        phase_id="pillar_generation",
        module_path="engine.pipeline.phases.pillar_generation",
        runner_fn="run",
    ),
    PhaseDefinition(
        phase_id="spoke_generation",
        module_path="engine.pipeline.phases.spoke_generation",
        runner_fn="run",
        extra_args=["spoke_limit"],
    ),
    PhaseDefinition(
        phase_id="seo_optimization",
        module_path="engine.pipeline.phases.seo_optimization",
        runner_fn="run",
    ),
    PhaseDefinition(
        phase_id="intelligence_gap_detection",
        module_path="engine.pipeline.phases.intelligence_gap_detection",
        runner_fn="run",
    ),
    PhaseDefinition(
        phase_id="cluster_scaling",
        module_path="engine.pipeline.phases.cluster_scaling",
        runner_fn="run",
    ),
    PhaseDefinition(
        phase_id="final_link_injection",
        module_path="engine.pipeline.phases.final_link_injection",
        runner_fn="run",
    ),
    PhaseDefinition(
        phase_id="humanization_readability",
        module_path="engine.pipeline.phases.humanization_readability",
        runner_fn="run",
    ),
    PhaseDefinition(
        phase_id="article_quality_assurance",
        module_path="engine.pipeline.phases.article_quality_assurance",
        runner_fn="run",
    ),
]

# Stable index for fast lookup by phase_id
_PHASE_INDEX: dict = {p.phase_id: p for p in PHASE_DEFINITIONS}


def get_phase_ids() -> List[str]:
    """Return the ordered list of all canonical phase IDs."""
    return [p.phase_id for p in PHASE_DEFINITIONS]


def get_phase(phase_id: str) -> Optional[PhaseDefinition]:
    """Return the PhaseDefinition for a given phase_id, or None."""
    return _PHASE_INDEX.get(phase_id)


def _disabled_phase_ids() -> List[str]:
    """Read PIPELINE_SKIP_PHASES env var and return list of phase IDs to skip."""
    raw = os.getenv("PIPELINE_SKIP_PHASES", "").strip()
    if not raw:
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]


def build_phases(queue: list, config: dict) -> List[tuple]:
    """
    Build the executable phase list for runner.py.

    Returns a list of (phase_id, callable) tuples in canonical order,
    with any phases named in PIPELINE_SKIP_PHASES removed.

    Args:
        queue:  The resolved topic queue list.
        config: Dict with run-level config values (spoke_limit, cluster_size, etc.)

    Returns:
        List of (phase_id: str, runner: Callable[[], None]) tuples.
    """
    import importlib

    disabled = set(_disabled_phase_ids())
    phases = []

    for defn in PHASE_DEFINITIONS:
        if defn.phase_id in disabled:
            print(f"[Registry] Phase '{defn.phase_id}' disabled via PIPELINE_SKIP_PHASES — skipping.")
            continue

        module = importlib.import_module(defn.module_path)
        fn = getattr(module, defn.runner_fn)

        extra_values = [config[key] for key in defn.extra_args]

        # Build a zero-argument lambda capturing the current fn and args
        runner: Callable[[], None] = _make_runner(fn, queue, extra_values)
        phases.append((defn.phase_id, runner))

    return phases


def _make_runner(fn: Callable, queue: list, extra_values: list) -> Callable[[], None]:
    """Return a zero-arg callable that invokes fn(queue, *extra_values)."""
    def _run():
        fn(queue, *extra_values)
    return _run
