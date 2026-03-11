# ---------------------------------------------------------------------------
# Standardized skip reason codes
# Must match regex [a-z0-9_]+ (captured by runner.py PHASE_SKIP_RE)
# ---------------------------------------------------------------------------
REASON_COMPLETED = "completed"
REASON_MISSING_PREREQUISITE = "missing_prerequisite"
REASON_CLUSTER_APPROVAL_PENDING = "cluster_approval_pending"
REASON_WRITING_PENDING = "writing_pending"
REASON_SEO_PENDING = "seo_pending"
REASON_INTELLIGENCE_PENDING = "intelligence_pending"
REASON_LINK_INJECTION_PENDING = "link_injection_pending"
REASON_HUMANIZATION_PENDING = "humanization_pending"
REASON_COMPETITOR_URL_MISSING = "competitor_url_missing"
REASON_CLUSTER_DATA_MISSING = "cluster_data_missing"
REASON_FINAL_FILES_MISSING = "final_files_missing"
REASON_ARTICLE_FILES_MISSING = "article_files_missing"
# ---------------------------------------------------------------------------


def _sanitize_text(value):
    if value is None:
        return ""
    return str(value).replace("\n", " ").replace("\r", " ").replace('"', "'").strip()


def log_phase_skip(phase, topic, reason, detail=None):
    phase_value = _sanitize_text(phase)
    topic_value = _sanitize_text(topic)
    reason_value = _sanitize_text(reason)

    message = f'Skipping: phase={phase_value} topic="{topic_value}" reason={reason_value}'
    if detail:
        message += f' detail="{_sanitize_text(detail)}"'
    print(message)
