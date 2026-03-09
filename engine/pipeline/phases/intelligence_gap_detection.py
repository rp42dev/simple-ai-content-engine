import os

from crews.content_crew import run_intelligence_crew
from tools.state_manager import load_state, update_state

from engine.pipeline.helpers import safe_slug

INTELLIGENCE_MEMORY_ENV = "CREWAI_INTELLIGENCE_MEMORY_ENABLED"
INTELLIGENCE_MEMORY_SCOPE_PREFIX = "/topic"

try:
    from crewai import Memory
except Exception:
    Memory = None


def _intelligence_memory_enabled():
    return os.getenv(INTELLIGENCE_MEMORY_ENV, "0") == "1"


def _memory_scope(topic_slug):
    return f"{INTELLIGENCE_MEMORY_SCOPE_PREFIX}/{topic_slug}/intelligence"


def _build_cluster_context_with_memory(topic_slug, cluster_info):
    if not _intelligence_memory_enabled() or Memory is None:
        return cluster_info

    try:
        memory = Memory()
        recalled = memory.recall(
            "previous intelligence findings and content gaps",
            scope=_memory_scope(topic_slug),
            depth="shallow",
            limit=5,
        )
        if not recalled:
            return cluster_info

        lines = [match.record.content for match in recalled if getattr(match, "record", None)]
        if not lines:
            return cluster_info

        print(f"[Intelligence Memory] Recalled {len(lines)} prior insights from memory")
        prior_context = "\n".join([f"- {line}" for line in lines])
        return (
            f"{cluster_info}\n\n"
            "# Prior Intelligence Context\n"
            "Use as historical context; do not duplicate exact recommendations unless still relevant.\n"
            f"{prior_context}\n"
        )
    except Exception as exc:
        print(f"[Intelligence Memory] Recall unavailable, continuing without memory: {exc}")
        return cluster_info


def _remember_intelligence_result(topic_slug, result_text):
    if not _intelligence_memory_enabled() or Memory is None:
        return

    try:
        memory = Memory()
        extracted = memory.extract_memories(result_text)
        if extracted:
            for item in extracted:
                memory.remember(item, scope=_memory_scope(topic_slug), source="phase5:intelligence")
        else:
            memory.remember(result_text, scope=_memory_scope(topic_slug), source="phase5:intelligence")
    except Exception as exc:
        print(f"[Intelligence Memory] Save unavailable, continuing without memory: {exc}")


def run(queue):
    print("\n--- Phase 5: Intelligence (Content Gap Detection) ---")
    for item in queue:
        topic = item["topic"]
        state = load_state(topic)
        if state.get("intelligence_completed"):
            print(f"Skipping Intelligence for {topic} (Completed)")
            continue

        competitor_url = item.get("competitor_url")
        if not competitor_url:
            print(f"Skipping Intelligence for {topic} (No competitor URL provided)")
            continue

        topic_slug = safe_slug(topic)
        cluster_file = os.path.join("outputs", f"{topic_slug}_cluster.json")
        if not os.path.exists(cluster_file):
            print(f"Skipping Intelligence for {topic} (Cluster data missing)")
            continue

        print(f"Running intelligence for {topic} against: {competitor_url}")
        try:
            with open(cluster_file, "r", encoding="utf-8") as f:
                cluster_info = f.read()

            cluster_info_with_memory = _build_cluster_context_with_memory(topic_slug, cluster_info)

            result = run_intelligence_crew(competitor_url, cluster_info_with_memory)
            intel_file = os.path.join("outputs", f"{topic_slug}_intelligence.md")
            with open(intel_file, "w", encoding="utf-8") as f:
                result_text = str(result)
                f.write(result_text)

            _remember_intelligence_result(topic_slug, result_text)
            update_state("intelligence_completed", True, topic)
        except Exception as exc:
            print(f"Error in Phase 5 for {topic}: {exc}")
