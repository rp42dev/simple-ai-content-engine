import json
import os

from crews.content_crew import run_writing_crew
from tools.state_manager import load_state, update_state

from engine.pipeline.helpers import clean_json_output, safe_slug


def _spoke_safe(name):
    if not name:
        return ""
    return safe_slug(name)


def run(queue, limit):
    print("\n--- Phase 3: Spoke Article Generation ---")
    for item in queue:
        topic = item["topic"]
        state = load_state(topic)
        topic_slug = safe_slug(topic)
        cluster_file = os.path.join("outputs", f"{topic_slug}_cluster.json")

        if not os.path.exists(cluster_file):
            continue
        if not state.get("cluster_approved", False):
            print(f"Skipping Phase 3 for {topic} (Awaiting Cluster Approval in Dashboard)")
            continue
        if state.get("spokes_written"):
            print(f"Skipping Spokes for {topic} (Completed)")
            continue

        print(f"Processing Spokes for: {topic}...")
        try:
            with open(cluster_file, "r", encoding="utf-8") as f:
                cdata = json.loads(clean_json_output(f.read()))

            spokes = cdata.get("spoke_topics", [])
            update_state("spokes_total", len(spokes), topic)
            written = 0
            print(f"  Spoke Production: Limit set to {limit} new articles.")

            for spoke in spokes:
                spoke_name = spoke.get("title") or spoke.get("topic") or spoke.get("sub_topic")
                if not spoke_name:
                    print(f"    [Warning] Skipping malformed spoke entry: {spoke}")
                    continue

                spoke_file = os.path.join("outputs", f"spoke_{_spoke_safe(spoke_name)}.md")
                if not os.path.exists(spoke_file):
                    if written >= limit:
                        print(f"  Batch limit ({limit}) reached. Stopping spoke production for this run.")
                        break
                    print(f"  Writing Spoke ({written+1}/{limit}): {spoke_name}...")
                    result = run_writing_crew(topic, spoke_name)
                    with open(spoke_file, "w", encoding="utf-8") as f:
                        f.write(str(result))
                    written += 1

                completed = len(
                    [
                        s
                        for s in spokes
                        if os.path.exists(
                            os.path.join(
                                "outputs",
                                f"spoke_{_spoke_safe(s.get('title') or s.get('topic') or s.get('sub_topic', ''))}.md",
                            )
                        )
                    ]
                )
                update_state("spokes_completed", completed, topic)
                update_state("spokes_total", len(spokes), topic)

            all_done = True
            for spoke in spokes:
                spoke_name = _spoke_safe(spoke.get("title") or spoke.get("topic") or spoke.get("sub_topic", ""))
                if not spoke_name or not os.path.exists(os.path.join("outputs", f"spoke_{spoke_name}.md")):
                    all_done = False
                    break

            if all_done:
                print(f"  All spokes for '{topic}' are now complete.")
                update_state("spokes_written", True, topic)
            else:
                print(f"  Partially finished '{topic}'. {written} new spokes added.")
        except Exception as exc:
            print(f"Error in Spoke Production for {topic}: {exc}")
