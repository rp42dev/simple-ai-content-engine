import os

from crews.content_crew import run_intelligence_crew
from tools.state_manager import load_state, update_state

from engine.pipeline.helpers import safe_slug


def run(queue):
    print("\n--- Phase 5: Intelligence (Content Gap Detection) ---")
    for item in queue:
        topic = item["topic"]
        state = load_state(topic)
        if state.get("intelligence_completed"):
            print(f"Skipping Intelligence for {topic} (Completed)")
            continue

        competitor_url = item.get("competitor_url")
        if not competitor_url:
            print(f"Skipping Intelligence for {topic} (No competitor URL provided)")
            continue

        topic_slug = safe_slug(topic)
        cluster_file = os.path.join("outputs", f"{topic_slug}_cluster.json")
        if not os.path.exists(cluster_file):
            print(f"Skipping Intelligence for {topic} (Cluster data missing)")
            continue

        print(f"Running intelligence for {topic} against: {competitor_url}")
        try:
            with open(cluster_file, "r", encoding="utf-8") as f:
                cluster_info = f.read()

            result = run_intelligence_crew(competitor_url, cluster_info)
            intel_file = os.path.join("outputs", f"{topic_slug}_intelligence.md")
            with open(intel_file, "w", encoding="utf-8") as f:
                f.write(str(result))
            update_state("intelligence_completed", True, topic)
        except Exception as exc:
            print(f"Error in Phase 5 for {topic}: {exc}")
