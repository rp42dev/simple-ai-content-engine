import os

from crews.content_crew import run_writing_crew
from tools.state_manager import load_state, update_state

from engine.pipeline.helpers import safe_slug


def run(queue):
    print("\n--- Phase 2: Pillar Article Generation ---")
    for item in queue:
        topic = item["topic"]
        state = load_state(topic)
        topic_slug = safe_slug(topic)
        cluster_file = os.path.join("outputs", f"{topic_slug}_cluster.json")

        if not os.path.exists(cluster_file):
            continue
        if not state.get("cluster_approved", False):
            print(f"Skipping Phase 2 for {topic} (Awaiting Cluster Approval in Dashboard)")
            continue
        if state.get("pillar_written"):
            print(f"Skipping Pillar for {topic} (Completed)")
            continue

        print(f"Writing Pillar: {topic}...")
        try:
            result = run_writing_crew(topic, f"Ultimate Guide to {topic}")
            output_path = os.path.join("outputs", f"{topic_slug}_pillar.md")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(str(result))
            update_state("pillar_written", True, topic)
        except Exception as exc:
            print(f"Error writing Pillar for {topic}: {exc}")
