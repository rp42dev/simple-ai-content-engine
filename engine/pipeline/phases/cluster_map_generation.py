import json

from crews.content_crew import run_cluster_map_crew
from tools.state_manager import (
    load_cluster_map,
    load_state,
    save_cluster_map,
    update_pipeline_status,
    update_state,
)

from engine.pipeline.helpers import clean_json_output
from engine.pipeline.phase_logging import log_phase_skip


def _normalize_cluster_map(payload, topic):
    if not isinstance(payload, dict):
        return None

    pillar = payload.get("pillar") or payload.get("pillar_topic") or f"Ultimate Guide to {topic}"
    raw_spokes = payload.get("spokes") if isinstance(payload.get("spokes"), list) else []

    spokes = []
    for item in raw_spokes:
        if isinstance(item, str):
            title = item.strip()
            intent = "informational"
        elif isinstance(item, dict):
            title = (item.get("title") or item.get("topic") or item.get("sub_topic") or "").strip()
            intent = (item.get("intent") or "informational").strip().lower()
        else:
            continue

        if not title:
            continue
        if intent not in {"informational", "commercial", "comparison", "supporting"}:
            intent = "informational"

        spokes.append({"title": title, "intent": intent})

    if not spokes:
        return None

    return {
        "topic": topic,
        "pillar": pillar,
        "spokes": spokes,
    }


def run(queue, cluster_size):
    print("\n--- Phase 0: Cluster Map Generation ---")
    for item in queue:
        topic = item["topic"]
        state = load_state(topic)

        if state.get("cluster_map_generated") and load_cluster_map(topic):
            update_pipeline_status(topic, "cluster_map", "completed")
            log_phase_skip("cluster_map_generation", topic, "completed")
            continue

        print(f"Planning cluster map for: {topic}...")
        try:
            update_pipeline_status(topic, "cluster_map", "running")
            result = run_cluster_map_crew(topic, item=item, cluster_size=cluster_size)
            payload = json.loads(clean_json_output(str(result)))
            normalized = _normalize_cluster_map(payload, topic)
            if not normalized:
                raise ValueError("Cluster map output was empty or invalid")

            save_cluster_map(topic, normalized)
            update_pipeline_status(topic, "cluster_map", "completed")
            update_state("cluster_map_generated", True, topic)
            print(f"✓ Cluster map saved for: {topic}")
        except Exception as exc:
            update_pipeline_status(topic, "cluster_map", "failed")
            print(f"Error in Phase 0 for {topic}: {exc}")
