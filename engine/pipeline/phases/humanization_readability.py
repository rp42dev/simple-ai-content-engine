import json
import os

from crews.content_crew import run_human_editor_crew
from tools.article_post_processor import (
    apply_humanization_suggestions,
    ensure_internal_link_coverage,
    ensure_metadata_guardrails,
    parse_json_payload,
    sanitize_placeholder_text,
)
from tools.state_manager import (
    load_humanization_suggestions,
    load_link_suggestions,
    load_seo_suggestions,
    load_state,
    save_humanization_suggestions,
    update_state,
)

from engine.pipeline.helpers import clean_json_output, get_cluster_spokes, safe_slug
from engine.pipeline.phase_logging import log_phase_skip


def _artifact_name(filename, topic_slug):
    if filename == f"{topic_slug}_pillar_final.md":
        return "article"
    return filename.replace("_final.md", "")


def _is_canonical_final_file(filename):
    return filename.endswith("_final.md") and not filename.endswith("_seo_final.md")


def run(queue):
    print("\n--- Phase 8: Humanization & Readability ---")
    for item in queue:
        topic = item["topic"]
        state = load_state(topic)

        if state.get("humanized"):
            log_phase_skip("humanization_readability", topic, "completed")
            continue

        if not state.get("links_injected"):
            log_phase_skip("humanization_readability", topic, "link_injection_pending")
            continue

        topic_slug = safe_slug(topic)
        cluster_file = os.path.join("outputs", f"{topic_slug}_cluster.json")
        final_files = []

        all_final_files = [f for f in os.listdir("outputs") if _is_canonical_final_file(f)]
        final_files.extend([f for f in all_final_files if topic_slug in f.lower()])

        if os.path.exists(cluster_file):
            try:
                with open(cluster_file, "r", encoding="utf-8") as f:
                    cdata = json.loads(clean_json_output(f.read()))
                for spoke in get_cluster_spokes(cdata):
                    spoke_name = spoke.get("title") or spoke.get("topic") or spoke.get("sub_topic", "")
                    if not spoke_name:
                        continue
                    spoke_safe = safe_slug(spoke_name)
                    final_files.extend(
                        [
                            f
                            for f in all_final_files
                            if f.startswith("spoke_") and spoke_safe in f and f not in final_files
                        ]
                    )
            except Exception as exc:
                print(f"  Warning: Could not parse cluster to match final spoke files: {exc}")

        if not final_files:
            log_phase_skip("humanization_readability", topic, "final_files_missing")
            continue

        print(f"Humanizing content for: {topic}...")
        for filename in final_files:
            try:
                file_path = os.path.join("outputs", filename)
                article_name = _artifact_name(filename, topic_slug)
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    article_content = f.read()
                suggestions = load_humanization_suggestions(topic, article_name)
                if not suggestions:
                    result = run_human_editor_crew(article_content, topic=topic, item=item)
                    suggestions = parse_json_payload(str(result))
                    save_humanization_suggestions(topic, article_name, suggestions)
                updated_content = apply_humanization_suggestions(article_content, suggestions)
                updated_content = sanitize_placeholder_text(
                    updated_content,
                    location=item.get("location"),
                    business=item.get("business"),
                )
                updated_content = ensure_metadata_guardrails(
                    updated_content,
                    seo_suggestions=load_seo_suggestions(topic, article_name) or {},
                    reference_content=article_content,
                )
                updated_content = ensure_internal_link_coverage(
                    updated_content,
                    load_link_suggestions(topic, article_name) or {},
                    min_links=1,
                )
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(updated_content)
                print(f"  Humanized: {filename}")
            except Exception as exc:
                print(f"  Failed humanization: {filename} | {exc}")

        update_state("humanized", True, topic)