import json
import os

from tools.link_injector import inject_links
from tools.state_manager import load_state, update_state

from engine.pipeline.helpers import clean_json_output, get_global_anchor_map, safe_slug


def run(queue):
    print("\n--- Phase 7: Final Link Injection ---")
    global_map = get_global_anchor_map(queue)

    for item in queue:
        topic = item["topic"]
        state = load_state(topic)
        if state.get("links_injected"):
            continue

        print(f"Finalizing Links for {topic} cluster...")
        topic_slug = safe_slug(topic)

        all_seo_files = [f for f in os.listdir("outputs") if f.endswith("_seo.md")]
        seo_files = [f for f in all_seo_files if topic_slug in f.lower()]

        cluster_file = os.path.join("outputs", f"{topic_slug}_cluster.json")
        if os.path.exists(cluster_file):
            try:
                with open(cluster_file, "r", encoding="utf-8") as f:
                    cdata = json.loads(clean_json_output(f.read()))
                for spoke in cdata.get("spoke_topics", []):
                    spoke_name = spoke.get("title") or spoke.get("topic") or spoke.get("sub_topic", "")
                    if not spoke_name:
                        continue
                    spoke_safe = safe_slug(spoke_name)
                    seo_files.extend(
                        [
                            f
                            for f in all_seo_files
                            if f.startswith("spoke_") and spoke_safe in f and f not in seo_files
                        ]
                    )
            except Exception as exc:
                print(f"  Warning: Could not parse cluster to match spokes: {exc}")

        if not seo_files:
            print(f"No SEO files found for {topic}. Link injection pending.")
            continue

        for seo_file in seo_files:
            try:
                final_content = inject_links(
                    os.path.join("outputs", seo_file),
                    {"spoke_topics": [{"topic": k} for k in global_map.keys()]},
                    "outputs",
                )
                final_name = seo_file.replace("_seo.md", "_final.md")
                with open(os.path.join("outputs", final_name), "w", encoding="utf-8") as f:
                    f.write(final_content)
                print(f"  Success: {final_name}")
            except Exception as exc:
                print(f"  Failed: {seo_file} | {exc}")

        if state.get("seo_optimized"):
            update_state("links_injected", True, topic)
