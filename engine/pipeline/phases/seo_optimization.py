import json
import os

from crews.content_crew import run_seo_suggestions_crew
from tools.article_post_processor import parse_json_payload
from tools.state_manager import load_seo_suggestions, load_state, save_seo_suggestions, update_pipeline_status, update_state

from engine.pipeline.helpers import clean_json_output, get_cluster_spokes, safe_slug
from engine.pipeline.phase_logging import log_phase_skip


def _artifact_name(filename, topic_slug):
    if filename == f"{topic_slug}_pillar.md":
        return "article"
    return filename.replace(".md", "")


def _load_legacy_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _migrate_legacy_seo_payloads(topic, topic_slug):
    topic_state_dir = os.path.join("state", topic_slug)
    legacy_candidates = {"article": os.path.join(topic_state_dir, f"{topic_slug}_pillar_seo.json")}

    for filename in os.listdir("outputs"):
        if filename.startswith("spoke_") and filename.endswith(".md") and not filename.endswith("_seo.md") and not filename.endswith("_final.md"):
            article_name = filename.replace(".md", "")
            legacy_candidates[article_name] = os.path.join(topic_state_dir, f"{article_name}_seo.json")

    for article_name, legacy_path in legacy_candidates.items():
        if load_seo_suggestions(topic, article_name):
            continue
        legacy_payload = _load_legacy_json(legacy_path)
        if legacy_payload:
            save_seo_suggestions(topic, article_name, legacy_payload)


def run(queue):
    print("\n--- Phase 4: SEO Optimization ---")
    for item in queue:
        topic = item["topic"]
        state = load_state(topic)
        topic_slug = safe_slug(topic)
        if state.get("seo_optimized"):
            _migrate_legacy_seo_payloads(topic, topic_slug)
            update_pipeline_status(topic, "seo", "completed")
            log_phase_skip("seo_optimization", topic, "completed")
            continue

        cluster_file = os.path.join("outputs", f"{topic_slug}_cluster.json")
        if not os.path.exists(cluster_file):
            continue

        print(f"Optimizing: {topic}...")
        try:
            update_pipeline_status(topic, "seo", "running")
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
                for spoke in get_cluster_spokes(cdata):
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
                article_name = _artifact_name(filename, topic_slug)
                seo_file = os.path.join("state", safe_slug(topic), "seo_data.json" if article_name == "article" else f"{article_name}_seo_data.json")
                if os.path.exists(seo_file):
                    continue
                print(f"  SEO Analysis: {filename}...")
                with open(os.path.join("outputs", filename), "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                result = run_seo_suggestions_crew(content, topic=topic, item=item)
                save_seo_suggestions(topic, article_name, parse_json_payload(str(result)))

            if state.get("pillar_written") and state.get("spokes_written"):
                update_pipeline_status(topic, "seo", "completed")
                update_state("seo_optimized", True, topic)
                print(f"SEO Phase marked complete for {topic}.")
            else:
                print(f"SEO Phase partially complete or pending for {topic}.")
        except Exception as exc:
            update_pipeline_status(topic, "seo", "failed")
            print(f"Error in Phase 4 for {topic}: {exc}")
