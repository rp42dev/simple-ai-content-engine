import json
import os

from crews.content_crew import run_outline_crew, run_writer_from_outline_crew
from tools.article_post_processor import ensure_article_template
from tools.state_manager import (
    load_article,
    load_outline,
    load_serp_analysis,
    load_state,
    save_article,
    save_outline,
    update_pipeline_status,
    update_state,
)

from engine.pipeline.helpers import clean_json_output, get_cluster_spokes, safe_slug
from engine.pipeline.phase_logging import log_phase_skip


def _spoke_safe(name):
    if not name:
        return ""
    return safe_slug(name)


def _backfill_outline_payload(subtopic, article_content):
    headings = [line.strip() for line in article_content.splitlines() if line.strip().startswith("#")]
    outline_body = "\n".join(headings) if headings else f"# {subtopic}"
    return {
        "subtopic": subtopic,
        "source": "backfilled_from_article",
        "content": outline_body,
    }


def run(queue, limit):
    print("\n--- Phase 3: Spoke Article Generation ---")
    for item in queue:
        topic = item["topic"]
        state = load_state(topic)
        topic_slug = safe_slug(topic)
        cluster_file = os.path.join("outputs", f"{topic_slug}_cluster.json")

        if not os.path.exists(cluster_file):
            log_phase_skip("spoke_generation", topic, "missing_prerequisite", detail="cluster_strategy")
            continue
        if not state.get("cluster_approved", False):
            log_phase_skip("spoke_generation", topic, "cluster_approval_pending")
            continue
        if state.get("spokes_written"):
            try:
                with open(cluster_file, "r", encoding="utf-8") as f:
                    cdata = json.loads(clean_json_output(f.read()))
                for spoke in get_cluster_spokes(cdata):
                    spoke_name = spoke.get("title") or spoke.get("topic") or spoke.get("sub_topic")
                    if not spoke_name:
                        continue
                    article_name = f"spoke_{_spoke_safe(spoke_name)}"
                    spoke_file = os.path.join("outputs", f"{article_name}.md")
                    if not os.path.exists(spoke_file):
                        continue
                    with open(spoke_file, "r", encoding="utf-8", errors="replace") as f:
                        article_content = f.read()
                    if not load_article(topic, article_name=article_name):
                        save_article(topic, article_content, article_name=article_name)
                    if not load_outline(topic, article_name=article_name):
                        save_outline(topic, _backfill_outline_payload(spoke_name, article_content), article_name=article_name)
            except Exception:
                pass
            update_pipeline_status(topic, "outline", "completed")
            update_pipeline_status(topic, "writer", "completed")
            log_phase_skip("spoke_generation", topic, "completed")
            continue

        print(f"Processing Spokes for: {topic}...")
        try:
            with open(cluster_file, "r", encoding="utf-8") as f:
                cdata = json.loads(clean_json_output(f.read()))

            spokes = get_cluster_spokes(cdata)
            serp_payload = load_serp_analysis(topic) or {}
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
                    serp_analysis = (serp_payload.get("spokes") or {}).get(spoke_name)
                    article_name = f"spoke_{_spoke_safe(spoke_name)}"
                    update_pipeline_status(topic, "outline", "running")
                    outline = run_outline_crew(topic, spoke_name, item=item, serp_analysis=serp_analysis)
                    save_outline(topic, {"subtopic": spoke_name, "content": str(outline)}, article_name=article_name)
                    update_pipeline_status(topic, "outline", "completed")

                    update_pipeline_status(topic, "writer", "running")
                    result = run_writer_from_outline_crew(
                        topic,
                        spoke_name,
                        str(outline),
                        item=item,
                        serp_analysis=serp_analysis,
                    )
                    article_content = ensure_article_template(str(result))
                    with open(spoke_file, "w", encoding="utf-8") as f:
                        f.write(article_content)
                    save_article(topic, article_content, article_name=article_name)
                    update_pipeline_status(topic, "writer", "completed")
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
                update_state("article_locked", True, topic)
            else:
                print(f"  Partially finished '{topic}'. {written} new spokes added.")
        except Exception as exc:
            update_pipeline_status(topic, "writer", "failed")
            print(f"Error in Spoke Production for {topic}: {exc}")
