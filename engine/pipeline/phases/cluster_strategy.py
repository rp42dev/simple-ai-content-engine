import os
import json

from crews.content_crew import run_cluster_crew
from tools.state_manager import load_cluster_map, load_state, update_state

from engine.pipeline.helpers import clean_json_output, get_cluster_pillar, get_cluster_spokes, safe_slug
from engine.pipeline.phase_logging import log_phase_skip


def run(queue):
    print("\n--- Phase 1: Cluster Strategy ---")
    for item in queue:
        topic = item["topic"]
        state = load_state(topic)
        topic_slug = safe_slug(topic)
        cluster_file = os.path.join("outputs", f"{topic_slug}_cluster.json")

        if state.get("cluster_generated"):
            log_phase_skip("cluster_strategy", topic, "completed")
            continue

        cluster_map = load_cluster_map(topic)
        cluster_map_context = str(cluster_map) if cluster_map else None

        print(f"Generating cluster map for: {topic}...")
        try:
            result = run_cluster_crew(topic, item=item, cluster_map_context=cluster_map_context)
            payload = json.loads(clean_json_output(str(result)))
            normalized = {
                "pillar_topic": get_cluster_pillar(payload, topic),
                "spoke_topics": get_cluster_spokes(payload),
            }
            with open(cluster_file, "w", encoding="utf-8") as f:
                json.dump(normalized, f, indent=2)
            update_state("cluster_generated", True, topic)
            update_state("cluster_approved", True, topic)  # Auto-approve in batch mode
            print(f"✓ Cluster generated and approved for: {topic}")
        except Exception as exc:
            print(f"Error in Phase 1 for {topic}: {exc}")
