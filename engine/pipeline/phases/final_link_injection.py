import json
import os

from crews.content_crew import run_link_suggestions_crew
from tools.article_post_processor import (
    apply_link_suggestions,
    apply_seo_suggestions,
    ensure_internal_link_coverage,
    ensure_metadata_guardrails,
    parse_json_payload,
    sanitize_placeholder_text,
)
from tools.state_manager import (
    load_link_suggestions,
    load_seo_suggestions,
    load_state,
    save_link_suggestions,
    update_pipeline_status,
    update_state,
)

from engine.pipeline.helpers import clean_json_output, get_cluster_spokes, get_global_anchor_map, safe_slug
from engine.pipeline.phase_logging import log_phase_skip


def _artifact_name(article_file, topic_slug):
    if article_file == f"{topic_slug}_pillar.md":
        return "article"
    return article_file.replace(".md", "")


def _is_canonical_article_file(filename):
    return filename.endswith(".md") and not filename.endswith("_seo.md") and not filename.endswith("_final.md")


def _final_output_name(article_name, topic_slug):
    if article_name == "article":
        return f"{topic_slug}_pillar_final.md"
    return f"{article_name}_final.md"


def _load_legacy_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _migrate_legacy_link_payloads(topic, topic_slug):
    topic_state_dir = os.path.join("state", topic_slug)
    legacy_candidates = {"article": os.path.join(topic_state_dir, f"{topic_slug}_pillar_links.json")}

    for filename in os.listdir("outputs"):
        if filename.startswith("spoke_") and filename.endswith(".md") and not filename.endswith("_seo.md") and not filename.endswith("_final.md"):
            article_name = filename.replace(".md", "")
            legacy_candidates[article_name] = os.path.join(topic_state_dir, f"{article_name}_links.json")

    for article_name, legacy_path in legacy_candidates.items():
        if load_link_suggestions(topic, article_name):
            continue
        legacy_payload = _load_legacy_json(legacy_path)
        if legacy_payload:
            save_link_suggestions(topic, article_name, legacy_payload)


def run(queue):
    print("\n--- Phase 7: Final Link Injection ---")
    global_map = get_global_anchor_map(queue)

    for item in queue:
        topic = item["topic"]
        state = load_state(topic)
        topic_slug = safe_slug(topic)
        if state.get("links_injected"):
            _migrate_legacy_link_payloads(topic, topic_slug)
            update_pipeline_status(topic, "linking", "completed")
            log_phase_skip("final_link_injection", topic, "completed")
            continue

        if not state.get("seo_optimized"):
            log_phase_skip("final_link_injection", topic, "seo_pending")
            continue

        print(f"Finalizing Links for {topic} cluster...")

        all_article_files = [f for f in os.listdir("outputs") if _is_canonical_article_file(f)]
        article_files = [f for f in all_article_files if topic_slug in f.lower()]

        cluster_file = os.path.join("outputs", f"{topic_slug}_cluster.json")
        if os.path.exists(cluster_file):
            try:
                with open(cluster_file, "r", encoding="utf-8") as f:
                    cdata = json.loads(clean_json_output(f.read()))
                for spoke in get_cluster_spokes(cdata):
                    spoke_name = spoke.get("title") or spoke.get("topic") or spoke.get("sub_topic", "")
                    if not spoke_name:
                        continue
                    spoke_safe = safe_slug(spoke_name)
                    article_files.extend(
                        [
                            f
                            for f in all_article_files
                            if f.startswith("spoke_") and spoke_safe in f and f not in article_files
                        ]
                    )
            except Exception as exc:
                print(f"  Warning: Could not parse cluster to match spokes: {exc}")

        if not article_files:
            log_phase_skip("final_link_injection", topic, "article_files_missing")
            print(f"No article files found for {topic}. Link injection pending.")
            continue

        for article_file in article_files:
            try:
                update_pipeline_status(topic, "linking", "running")
                article_name = _artifact_name(article_file, topic_slug)
                article_path = os.path.join("outputs", article_file)
                with open(article_path, "r", encoding="utf-8", errors="replace") as f:
                    article_content = f.read()

                seo_suggestions = load_seo_suggestions(topic, article_name) or {}
                link_suggestions = load_link_suggestions(topic, article_name)
                if not link_suggestions:
                    link_result = run_link_suggestions_crew(article_content, json.dumps({"spoke_topics": [{"topic": k} for k in global_map.keys()]}), topic=topic, item=item)
                    link_suggestions = parse_json_payload(str(link_result))
                    save_link_suggestions(topic, article_name, link_suggestions)

                with_seo = apply_seo_suggestions(article_content, seo_suggestions)
                linked_content = apply_link_suggestions(with_seo, link_suggestions, global_map)
                final_content = sanitize_placeholder_text(
                    linked_content,
                    location=item.get("location"),
                    business=item.get("business"),
                )
                final_content = ensure_metadata_guardrails(
                    final_content,
                    seo_suggestions=seo_suggestions,
                    reference_content=with_seo,
                )
                final_content = ensure_internal_link_coverage(
                    final_content,
                    link_suggestions,
                    min_links=1,
                )

                final_name = _final_output_name(article_name, topic_slug)
                with open(os.path.join("outputs", final_name), "w", encoding="utf-8") as f:
                    f.write(final_content)
                print(f"  Success: {final_name}")
            except Exception as exc:
                print(f"  Failed: {article_file} | {exc}")

        if state.get("seo_optimized"):
            update_pipeline_status(topic, "linking", "completed")
            update_state("links_injected", True, topic)
