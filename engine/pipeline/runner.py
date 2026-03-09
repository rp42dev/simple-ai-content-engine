from engine.pipeline.helpers import load_queue
from engine.pipeline.phases import (
    cluster_strategy,
    pillar_generation,
    spoke_generation,
    seo_optimization,
    intelligence_gap_detection,
    cluster_scaling,
    final_link_injection,
)


def run_pipeline(topic=None, limit=2):
    queue = load_queue()
    if not queue:
        print("No topics found in queue. Add topics via dashboard or topics_queue.json")
        return

    if topic:
        queue = [item for item in queue if item["topic"].lower() == topic.lower()]
        if not queue:
            print(f"Topic '{topic}' not found in queue.")
            return
        print(f"Targeted Run: Processing only '{topic}'")

    priority_map = {"high": 1, "medium": 2, "low": 3}
    queue.sort(key=lambda item: priority_map.get(item.get("priority", "medium"), 2))

    print(f"--- Starting Industrial Pipelined Content Engine ({len(queue)} topics) ---")

    cluster_strategy.run(queue)
    pillar_generation.run(queue)
    spoke_generation.run(queue, limit)
    seo_optimization.run(queue)
    intelligence_gap_detection.run(queue)
    cluster_scaling.run(queue)
    final_link_injection.run(queue)

    print("\n--- Industrial Batch Run Complete ---")
