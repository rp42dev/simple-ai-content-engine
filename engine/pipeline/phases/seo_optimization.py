import json
import os
import re

from crews.content_crew import run_seo_crew
from tools.state_manager import load_state, update_state

from engine.pipeline.helpers import clean_json_output, safe_slug


def run(queue):
    print("\n--- Phase 4: SEO Optimization ---")
    for item in queue:
        topic = item["topic"]
        state = load_state(topic)
        if state.get("seo_optimized"):
            print(f"Skipping SEO for {topic} (Completed)")
            continue

        topic_slug = safe_slug(topic)
        cluster_file = os.path.join("outputs", f"{topic_slug}_cluster.json")
        if not os.path.exists(cluster_file):
            continue

        print(f"Optimizing: {topic}...")
        try:
            with open(cluster_file, "r", encoding="utf-8") as f:
                cluster_info = f.read()

            all_md = [
                f
                for f in os.listdir("outputs")
                if f.endswith(".md") and not f.endswith("_seo.md") and not f.endswith("_final.md")
            ]
            files_to_seo = [f for f in all_md if topic_slug in f]

            try:
                cdata = json.loads(clean_json_output(cluster_info))
                for spoke in cdata.get("spoke_topics", []):
                    spoke_name = spoke.get("title") or spoke.get("topic") or spoke.get("sub_topic", "")
                    if not spoke_name:
                        continue
                    spoke_safe = safe_slug(spoke_name)
                    for filename in all_md:
                        if filename.startswith("spoke_") and spoke_safe in filename and filename not in files_to_seo:
                            files_to_seo.append(filename)
            except Exception as exc:
                print(f"  Warning: Could not parse cluster for spoke SEO list: {exc}")

            for filename in files_to_seo:
                seo_file = os.path.join("outputs", f"{filename.replace('.md', '')}_seo.md")
                if os.path.exists(seo_file):
                    continue
                print(f"  SEO Analysis: {filename}...")
                with open(os.path.join("outputs", filename), "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                result = run_seo_crew(content, cluster_info)
                clean_result = str(result).strip()
                clean_result = re.sub(r"^```[a-z]*\n?", "", clean_result).rstrip("`").strip()
                with open(seo_file, "w", encoding="utf-8") as f:
                    f.write(clean_result)

            if state.get("pillar_written") and state.get("spokes_written"):
                update_state("seo_optimized", True, topic)
                print(f"SEO Phase marked complete for {topic}.")
            else:
                print(f"SEO Phase partially complete or pending for {topic}.")
        except Exception as exc:
            print(f"Error in Phase 4 for {topic}: {exc}")
