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
