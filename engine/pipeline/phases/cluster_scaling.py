import json
import os

from engine.pipeline.helpers import safe_slug
from engine.pipeline.phase_logging import log_phase_skip
from tools.state_manager import (
    load_cluster_map,
    load_state,
    save_spoke_backlog,
    update_state,
)

# Confidence score thresholds based on justification language signals
_HIGH_CONFIDENCE_SIGNALS = {
    "significant gap": 0.9,
    "high priority": 0.9,
    "top priority": 0.9,
    "critical": 0.9,
    "extremely": 0.9,
    "strong demand": 0.9,
}

_MEDIUM_HIGH_SIGNALS = {
    "important": 0.8,
    "essential": 0.8,
    "high-traffic": 0.8,
    "key": 0.8,
    "major": 0.8,
}

_MEDIUM_SIGNALS = {
    "improve": 0.7,
    "missing": 0.7,
    "not currently": 0.7,
    "lacks": 0.7,
    "gap": 0.7,
}

_LOWER_MEDIUM_SIGNALS = {
    "consider": 0.6,
    "could": 0.6,
    "would": 0.6,
    "may": 0.6,
    "potentially": 0.6,
    "worth": 0.6,
}

_DEFAULT_CONFIDENCE = 0.5

CONFIDENCE_THRESHOLD = 0.7


def _score_confidence(justification: str) -> float:
    """Return confidence score for a gap item based on justification keywords."""
    text = justification.lower()
    for signal, score in _HIGH_CONFIDENCE_SIGNALS.items():
        if signal in text:
            return score
    for signal, score in _MEDIUM_HIGH_SIGNALS.items():
        if signal in text:
            return score
    for signal, score in _MEDIUM_SIGNALS.items():
        if signal in text:
            return score
    for signal, score in _LOWER_MEDIUM_SIGNALS.items():
        if signal in text:
            return score
    return _DEFAULT_CONFIDENCE


def _existing_spoke_titles(cluster_map) -> set:
    """Return lowercased sub_topic titles already in the cluster map."""
    if not cluster_map or not isinstance(cluster_map, dict):
        return set()
    return {
        spoke.get("sub_topic", "").lower().strip()
        for spoke in cluster_map.get("spoke_topics", [])
        if spoke.get("sub_topic")
    }


def _parse_intelligence(intel_path: str) -> list:
    """
    Parse the intelligence output file. Expects a JSON array written by
    intelligence_gap_detection. Falls back to empty list on any parse error.
    """
    if not os.path.exists(intel_path):
        return []
    try:
        with open(intel_path, "r", encoding="utf-8") as f:
            raw = f.read().strip()
        # Strip optional markdown code-fence wrapper
        if raw.startswith("```"):
            lines = raw.splitlines()
            raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        return json.loads(raw)
    except Exception:
        return []


def _build_backlog(gap_items: list, existing_titles: set) -> list:
    """Convert intelligence gap items into scored spoke backlog entries."""
    backlog = []
    for item in gap_items:
        if not isinstance(item, dict):
            continue
        title = item.get("suggested_new_sub_topic", "").strip()
        if not title:
            continue
        # Deduplicate: skip if a spoke with the same normalised title already exists
        if title.lower() in existing_titles:
            continue
        justification = item.get("justification", "")
        confidence = _score_confidence(justification)
        backlog.append({
            "title": title,
            "intent": item.get("gap_topic", "").strip(),
            "confidence": confidence,
            "source": "intelligence",
            "approved": False,
        })
    return backlog


def run(queue):
    print("\n--- Phase 6: Cluster Scaling ---")
    for item in queue:
        topic = item["topic"]
        state = load_state(topic)

        if state.get("cluster_scaled"):
            log_phase_skip("cluster_scaling", topic, "completed")
            continue

        if not state.get("intelligence_completed"):
            log_phase_skip("cluster_scaling", topic, "intelligence_pending")
            continue

        topic_slug = safe_slug(topic)
        intel_path = os.path.join("outputs", f"{topic_slug}_intelligence.md")

        gap_items = _parse_intelligence(intel_path)
        cluster_map = load_cluster_map(topic)
        existing = _existing_spoke_titles(cluster_map)

        backlog = _build_backlog(gap_items, existing)
        above_threshold = [b for b in backlog if b["confidence"] >= CONFIDENCE_THRESHOLD]

        save_spoke_backlog(topic, backlog)
        update_state("spoke_backlog_saved", True, topic)
        update_state("cluster_scaled", True, topic)

        print(
            f"  [{topic}] Cluster scaling complete: "
            f"{len(backlog)} spoke candidate(s) found "
            f"({len(above_threshold)} at confidence >= {CONFIDENCE_THRESHOLD})."
        )
