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

from engine.pipeline.helpers import safe_slug
from engine.pipeline.phase_logging import log_phase_skip


def _backfill_outline_payload(subtopic, article_content):
    headings = [line.strip() for line in article_content.splitlines() if line.strip().startswith("#")]
    outline_body = "\n".join(headings) if headings else f"# {subtopic}"
    return {
        "subtopic": subtopic,
        "source": "backfilled_from_article",
        "content": outline_body,
    }


def run(queue):
    print("\n--- Phase 2: Pillar Article Generation ---")
    for item in queue:
        topic = item["topic"]
        state = load_state(topic)
        topic_slug = safe_slug(topic)
        cluster_file = os.path.join("outputs", f"{topic_slug}_cluster.json")

        if not os.path.exists(cluster_file):
            log_phase_skip("pillar_generation", topic, "missing_prerequisite", detail="cluster_strategy")
            continue
        if not state.get("cluster_approved", False):
            log_phase_skip("pillar_generation", topic, "cluster_approval_pending")
            continue
        if state.get("pillar_written"):
            output_path = os.path.join("outputs", f"{topic_slug}_pillar.md")
            if os.path.exists(output_path):
                with open(output_path, "r", encoding="utf-8", errors="replace") as f:
                    article_content = f.read()
                if not load_article(topic):
                    save_article(topic, article_content)
                if not load_outline(topic):
                    save_outline(topic, _backfill_outline_payload(f"Ultimate Guide to {topic}", article_content))
            update_pipeline_status(topic, "outline", "completed")
            update_pipeline_status(topic, "writer", "completed")
            log_phase_skip("pillar_generation", topic, "completed")
            continue

        print(f"Writing Pillar: {topic}...")
        try:
            serp_analysis = (load_serp_analysis(topic) or {}).get("pillar")
            update_pipeline_status(topic, "outline", "running")
            outline = run_outline_crew(topic, f"Ultimate Guide to {topic}", item=item, serp_analysis=serp_analysis)
            save_outline(topic, {"subtopic": f"Ultimate Guide to {topic}", "content": str(outline)})
            update_pipeline_status(topic, "outline", "completed")

            update_pipeline_status(topic, "writer", "running")
            result = run_writer_from_outline_crew(
                topic,
                f"Ultimate Guide to {topic}",
                str(outline),
                item=item,
                serp_analysis=serp_analysis,
            )
            article_content = ensure_article_template(str(result))
            output_path = os.path.join("outputs", f"{topic_slug}_pillar.md")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(article_content)
            save_article(topic, article_content)
            update_pipeline_status(topic, "writer", "completed")
            update_state("pillar_written", True, topic)
            update_state("article_locked", True, topic)
        except Exception as exc:
            update_pipeline_status(topic, "writer", "failed")
            print(f"Error writing Pillar for {topic}: {exc}")
