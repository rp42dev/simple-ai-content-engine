import json
import os

from crews.content_crew import run_serp_analysis_crew
from tools.search_tools import collect_serp_research, format_serp_research_for_prompt
from tools.state_manager import (
    load_serp_analysis,
    load_state,
    save_serp_analysis,
    update_pipeline_status,
    update_state,
)

from engine.pipeline.helpers import clean_json_output, get_cluster_pillar, get_cluster_spokes, safe_slug
from engine.pipeline.phase_logging import log_phase_skip


def _normalize_serp_output(payload, query, default_range, is_pillar=False):
    if not isinstance(payload, dict):
        return None

    headings = payload.get("top_headings") if isinstance(payload.get("top_headings"), list) else []
    questions = payload.get("questions") if isinstance(payload.get("questions"), list) else []
    notes = payload.get("notes") if isinstance(payload.get("notes"), list) else []

    recommended_word_range = payload.get("recommended_word_range") or default_range
    if is_pillar:
        recommended_word_range = default_range

    normalized = {
        "query": payload.get("query") or query,
        "top_headings": [str(item).strip() for item in headings if str(item).strip()][:10],
        "questions": [str(item).strip() for item in questions if str(item).strip()][:8],
        "recommended_word_range": recommended_word_range,
        "notes": [str(item).strip() for item in notes if str(item).strip()][:6],
    }
    return normalized


def _default_word_range(query, is_pillar=False):
    if is_pillar:
        return "1500-1800"
    return "900-1200"


def _build_queries(topic, cluster_data):
    queries = [("pillar", get_cluster_pillar(cluster_data, topic))]
    for spoke in get_cluster_spokes(cluster_data):
        spoke_title = spoke.get("title") or spoke.get("topic") or spoke.get("sub_topic")
        if spoke_title:
            queries.append((spoke_title, spoke_title))
    return queries


def _localize_query(query, item):
    location = item.get("location") if isinstance(item.get("location"), dict) else {}
    country = (location.get("country") or "").strip()
    city = (location.get("city") or "").strip()

    if country and country.lower() not in query.lower():
        return f"{query} {country}" if not city else f"{query} {city} {country}"
    if city and city.lower() not in query.lower():
        return f"{query} {city}"
    return query


def run(queue):
    print("\n--- Phase 1.5: SERP Analysis ---")
    for item in queue:
        topic = item["topic"]
        state = load_state(topic)
        topic_slug = safe_slug(topic)
        cluster_file = os.path.join("outputs", f"{topic_slug}_cluster.json")

        if state.get("serp_analysis_generated") and load_serp_analysis(topic):
            update_pipeline_status(topic, "serp_analysis", "completed")
            log_phase_skip("serp_analysis", topic, "completed")
            continue

        if not state.get("cluster_generated"):
            log_phase_skip("serp_analysis", topic, "missing_prerequisite", detail="cluster_strategy")
            continue

        if not os.path.exists(cluster_file):
            log_phase_skip("serp_analysis", topic, "cluster_data_missing")
            continue

        print(f"Analyzing SERP patterns for: {topic}...")
        try:
            update_pipeline_status(topic, "serp_analysis", "running")
            with open(cluster_file, "r", encoding="utf-8") as f:
                cluster_data = json.loads(clean_json_output(f.read()))

            analyses = {"topic": topic, "pillar": None, "spokes": {}}
            for label, query in _build_queries(topic, cluster_data):
                search_query = _localize_query(query, item)
                serp_research = collect_serp_research(search_query, max_results=5)
                result = run_serp_analysis_crew(
                    topic=topic,
                    topic_query=search_query,
                    serp_research=format_serp_research_for_prompt(serp_research),
                    item=item,
                )
                normalized = _normalize_serp_output(
                    json.loads(clean_json_output(str(result))),
                    query=search_query,
                    default_range=_default_word_range(query, is_pillar=(label == "pillar")),
                    is_pillar=(label == "pillar"),
                )
                if label == "pillar":
                    analyses["pillar"] = normalized
                else:
                    analyses["spokes"][label] = normalized

            save_serp_analysis(topic, analyses)
            update_pipeline_status(topic, "serp_analysis", "completed")
            update_state("serp_analysis_generated", True, topic)
            print(f"✓ SERP analysis saved for: {topic}")
        except Exception as exc:
            update_pipeline_status(topic, "serp_analysis", "failed")
            print(f"Error in SERP Analysis for {topic}: {exc}")
