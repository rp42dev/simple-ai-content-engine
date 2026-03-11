import json
import re
from pathlib import Path

STATE_FILE = Path("state/workflow_state.json")
STATE_VERSION = 1


def _safe_topic(topic):
    if topic is None:
        return None
    return re.sub(r"[^a-zA-Z0-9]", "_", str(topic).lower())


def _state_file_for_topic(topic=None):
    if topic:
        return Path(f"state/workflow_{_safe_topic(topic)}.json")
    return STATE_FILE


def topic_state_dir(topic):
    return Path("state") / _safe_topic(topic)


def cluster_map_path(topic):
    return topic_state_dir(topic) / "cluster_map.json"


def serp_analysis_path(topic):
    return topic_state_dir(topic) / "serp_analysis.json"


def outline_path(topic, article_name="article"):
    if article_name == "article":
        return topic_state_dir(topic) / "outline.json"
    return topic_state_dir(topic) / f"{article_name}_outline.json"


def article_path(topic, article_name="article"):
    if article_name == "article":
        return topic_state_dir(topic) / "article.md"
    return topic_state_dir(topic) / f"{article_name}.md"


def pipeline_status_path(topic):
    return topic_state_dir(topic) / "pipeline_status.json"


def seo_suggestions_path(topic, article_name):
    if article_name == "article":
        return topic_state_dir(topic) / "seo_data.json"
    return topic_state_dir(topic) / f"{article_name}_seo_data.json"


def link_suggestions_path(topic, article_name):
    if article_name == "article":
        return topic_state_dir(topic) / "link_data.json"
    return topic_state_dir(topic) / f"{article_name}_link_data.json"


def humanization_suggestions_path(topic, article_name):
    if article_name == "article":
        return topic_state_dir(topic) / "humanize_data.json"
    return topic_state_dir(topic) / f"{article_name}_humanize_data.json"


def qa_report_path(topic, article_name="article"):
    if article_name == "article":
        return topic_state_dir(topic) / "article_qa_report.json"
    return topic_state_dir(topic) / f"{article_name}_qa_report.json"


def qa_summary_path(topic):
    return topic_state_dir(topic) / "qa_report.json"


def spoke_backlog_path(topic):
    return topic_state_dir(topic) / "spoke_backlog.json"


def _default_state(topic=None):
    return {
        "state_version": STATE_VERSION,
        "topic": topic,
        "cluster_generated": False,
        "cluster_map_generated": False,
        "serp_analysis_generated": False,
        "cluster_approved": False,
        "article_locked": False,
        "pillar_written": False,
        "spokes_total": 0,
        "spokes_completed": 0,
        "spokes_written": False,
        "seo_optimized": False,
        "intelligence_completed": False,
        "cluster_scaled": False,
        "spoke_backlog_saved": False,
        "links_injected": False,
        "humanized": False,
        "qa_reviewed": False,
        "publish_ready": False,
    }


def _as_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    if isinstance(value, (int, float)):
        return value != 0
    return False


def _as_non_negative_int(value, fallback=0):
    try:
        parsed = int(value)
    except Exception:
        return fallback
    return parsed if parsed >= 0 else fallback


def _normalize_state(data, topic=None):
    base = _default_state(topic)
    source = data if isinstance(data, dict) else {}

    normalized = dict(base)
    normalized.update(source)

    if topic:
        normalized["topic"] = topic
    else:
        normalized["topic"] = normalized.get("topic")

    if source.get("intelligence_completed") is None and "intelligence_run" in source:
        normalized["intelligence_completed"] = _as_bool(source.get("intelligence_run"))

    bool_keys = [
        "cluster_generated",
        "cluster_map_generated",
        "serp_analysis_generated",
        "cluster_approved",
        "article_locked",
        "pillar_written",
        "spokes_written",
        "seo_optimized",
        "intelligence_completed",
        "cluster_scaled",
        "spoke_backlog_saved",
        "links_injected",
        "humanized",
        "qa_reviewed",
        "publish_ready",
    ]
    for key in bool_keys:
        normalized[key] = _as_bool(normalized.get(key))

    normalized["article_locked"] = (
        normalized["article_locked"]
        or normalized["pillar_written"]
        or normalized["spokes_written"]
    )

    normalized["spokes_total"] = _as_non_negative_int(normalized.get("spokes_total"), 0)
    normalized["spokes_completed"] = _as_non_negative_int(normalized.get("spokes_completed"), 0)
    if normalized["spokes_completed"] > normalized["spokes_total"]:
        normalized["spokes_completed"] = normalized["spokes_total"]

    normalized["state_version"] = STATE_VERSION
    return normalized

def load_state(topic=None):
    """Load workflow state. If topic is provided, use topic-specific state file."""
    state_file = _state_file_for_topic(topic)

    if not state_file.exists():
        return _default_state(topic)

    try:
        with open(state_file, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return _default_state(topic)

    return _normalize_state(raw, topic)


def save_state(state, topic=None):
    """Save workflow state"""
    current_topic = topic or (state.get("topic") if isinstance(state, dict) else None)
    state_file = _state_file_for_topic(current_topic)
    state_file.parent.mkdir(parents=True, exist_ok=True)

    normalized = _normalize_state(state, current_topic)
    temp_file = state_file.with_suffix(state_file.suffix + ".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(normalized, f, indent=2)
    temp_file.replace(state_file)


def save_cluster_map(topic, payload):
    target = cluster_map_path(topic)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_file = target.with_suffix(target.suffix + ".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    temp_file.replace(target)


def load_cluster_map(topic):
    target = cluster_map_path(topic)
    if not target.exists():
        return None
    try:
        with open(target, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_serp_analysis(topic, payload):
    target = serp_analysis_path(topic)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_file = target.with_suffix(target.suffix + ".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    temp_file.replace(target)


def load_serp_analysis(topic):
    target = serp_analysis_path(topic)
    if not target.exists():
        return None
    try:
        with open(target, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_outline(topic, payload, article_name="article"):
    _save_topic_payload(outline_path(topic, article_name), payload)


def load_outline(topic, article_name="article"):
    return _load_topic_payload(outline_path(topic, article_name))


def save_article(topic, content, article_name="article"):
    target = article_path(topic, article_name)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_file = target.with_suffix(target.suffix + ".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write(content)
    temp_file.replace(target)


def load_article(topic, article_name="article"):
    target = article_path(topic, article_name)
    if not target.exists():
        return None
    try:
        with open(target, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None


def _default_pipeline_status():
    return {
        "cluster_map": "pending",
        "serp_analysis": "pending",
        "outline": "pending",
        "writer": "pending",
        "seo": "pending",
        "linking": "pending",
        "qa": "pending",
    }


def load_pipeline_status(topic):
    payload = _load_topic_payload(pipeline_status_path(topic))
    status = _default_pipeline_status()
    if isinstance(payload, dict):
        status.update(payload)
    return status


def save_pipeline_status(topic, payload):
    status = _default_pipeline_status()
    if isinstance(payload, dict):
        status.update(payload)
    _save_topic_payload(pipeline_status_path(topic), status)


def update_pipeline_status(topic, phase_name, status):
    payload = load_pipeline_status(topic)
    payload[phase_name] = status
    save_pipeline_status(topic, payload)


def _save_topic_payload(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_file = path.with_suffix(path.suffix + ".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    temp_file.replace(path)


def _load_topic_payload(path):
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_seo_suggestions(topic, article_name, payload):
    _save_topic_payload(seo_suggestions_path(topic, article_name), payload)


def load_seo_suggestions(topic, article_name):
    return _load_topic_payload(seo_suggestions_path(topic, article_name))


def save_link_suggestions(topic, article_name, payload):
    _save_topic_payload(link_suggestions_path(topic, article_name), payload)


def load_link_suggestions(topic, article_name):
    return _load_topic_payload(link_suggestions_path(topic, article_name))


def save_humanization_suggestions(topic, article_name, payload):
    _save_topic_payload(humanization_suggestions_path(topic, article_name), payload)


def load_humanization_suggestions(topic, article_name):
    return _load_topic_payload(humanization_suggestions_path(topic, article_name))


def save_qa_report(topic, payload, article_name="article"):
    _save_topic_payload(qa_report_path(topic, article_name), payload)


def load_qa_report(topic, article_name="article"):
    return _load_topic_payload(qa_report_path(topic, article_name))


def save_qa_summary(topic, payload):
    _save_topic_payload(qa_summary_path(topic), payload)


def load_qa_summary(topic):
    return _load_topic_payload(qa_summary_path(topic))


def save_spoke_backlog(topic, backlog):
    _save_topic_payload(spoke_backlog_path(topic), backlog)


def load_spoke_backlog(topic):
    return _load_topic_payload(spoke_backlog_path(topic))


def update_state(key, value, topic=None):
    """Update a single value in the state"""
    state = load_state(topic)
    state[key] = value
    save_state(state, topic)

def get_state_value(key, topic=None):
    """Retrieve specific value"""
    state = load_state(topic)
    return state.get(key)
