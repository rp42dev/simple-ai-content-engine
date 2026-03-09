import os

from crews.content_crew import run_cluster_crew
from tools.state_manager import load_state, update_state

from engine.pipeline.helpers import safe_slug


def run(queue):
    print("\n--- Phase 1: Cluster Strategy ---")
    for item in queue:
        topic = item["topic"]
        state = load_state(topic)
        topic_slug = safe_slug(topic)
        cluster_file = os.path.join("outputs", f"{topic_slug}_cluster.json")

        if state.get("cluster_generated"):
            print(f"Skipping Cluster Strategy for {topic} (Completed)")
            continue

        print(f"Generating cluster map for: {topic}...")
        try:
            result = run_cluster_crew(topic)
            with open(cluster_file, "w", encoding="utf-8") as f:
                f.write(str(result))
            update_state("cluster_generated", True, topic)
        except Exception as exc:
            print(f"Error in Phase 1 for {topic}: {exc}")
