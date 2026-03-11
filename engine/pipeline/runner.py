import json
import re
import sys
import time
import uuid
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

from engine.pipeline.helpers import load_queue
from engine.pipeline.phase_registry import build_phases

RUN_SUMMARY_DIR = Path("outputs/run_summaries")
PHASE_SKIP_RE = re.compile(
    r'^Skipping:\s+phase=(?P<phase>[a-z0-9_]+)\s+topic="(?P<topic>.*?)"\s+reason=(?P<reason>[a-z0-9_]+)(?:\s+detail="(?P<detail>.*?)")?$'
)


class _OutputTee:
    def __init__(self, destination, line_callback):
        self.destination = destination
        self.line_callback = line_callback
        self._buffer = ""

    def write(self, data):
        self.destination.write(data)
        self._buffer += data
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self.line_callback(line.rstrip("\r"))
        return len(data)

    def flush(self):
        if self._buffer:
            self.line_callback(self._buffer.rstrip("\r"))
            self._buffer = ""
        self.destination.flush()


def _parse_phase_skip(line):
    match = PHASE_SKIP_RE.match(line.strip())
    if not match:
        return None
    return {
        "phase": match.group("phase"),
        "topic": match.group("topic"),
        "reason": match.group("reason"),
        "detail": match.group("detail"),
    }


def _utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def _new_run_id():
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"run_{timestamp}_{uuid.uuid4().hex[:8]}"


def _write_run_summary(summary):
    RUN_SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = RUN_SUMMARY_DIR / f"{summary['run_id']}.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    return str(summary_path)


def _list_summary_files():
    if not RUN_SUMMARY_DIR.exists():
        return []
    return sorted(RUN_SUMMARY_DIR.glob("run_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)


def list_run_summaries(limit=10, failed_only=False):
    files = _list_summary_files()
    if limit is not None:
        files = files[: max(0, int(limit))]

    summaries = []
    for path in files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception:
            continue

        config = payload.get("config", {})
        summaries.append(
            {
                "run_id": payload.get("run_id", path.stem),
                "status": payload.get("status", "unknown"),
                "started_at": payload.get("started_at", "unknown"),
                "duration_seconds": payload.get("duration_seconds", "unknown"),
                "queue_size": payload.get("queue_size", 0),
                "topic": config.get("topic"),
                "topic_limit": config.get("topic_limit"),
                "spoke_limit": config.get("spoke_limit"),
                "cluster_size": config.get("cluster_size"),
            }
        )

    if failed_only:
        summaries = [item for item in summaries if item.get("status") == "failed"]

    return summaries


def load_run_summary(run_id=None, latest=False):
    summary_path = None

    if run_id:
        candidate = RUN_SUMMARY_DIR / f"{run_id}.json"
        if candidate.exists():
            summary_path = candidate
    elif latest:
        files = _list_summary_files()
        if files:
            summary_path = files[0]

    if not summary_path:
        return None

    with open(summary_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_run_summary_report(summary):
    if not summary:
        return "No run summary found."

    config = summary.get("config", {})
    lines = [
        f"Run Summary: {summary.get('run_id', 'unknown')}",
        f"Status: {summary.get('status', 'unknown')}",
        f"Started: {summary.get('started_at', 'unknown')}",
        f"Ended: {summary.get('ended_at', 'unknown')}",
        f"Duration (s): {summary.get('duration_seconds', 'unknown')}",
        (
            "Config: "
            f"topic={config.get('topic')} "
            f"topic_limit={config.get('topic_limit')} "
            f"spoke_limit={config.get('spoke_limit')} "
            f"cluster_size={config.get('cluster_size')}"
        ),
        f"Queue Size: {summary.get('queue_size', 0)}",
        "Phases:",
    ]

    for phase in summary.get("phases", []):
        lines.append(
            f"- {phase.get('name')}: status={phase.get('status')} "
            f"duration={phase.get('duration_seconds')}s skips={len(phase.get('skips') or [])}"
        )
        for skip in phase.get("skips") or []:
            detail = f" detail={skip.get('detail')}" if skip.get("detail") else ""
            lines.append(
                f"  - skip topic={skip.get('topic')} reason={skip.get('reason')}{detail}"
            )
        if phase.get("error"):
            lines.append(f"  - error: {phase.get('error')}")

    return "\n".join(lines)


def print_run_summary(run_id=None, latest=False, as_json=False):
    summary = load_run_summary(run_id=run_id, latest=latest)
    if not summary:
        if run_id:
            print(f"Run summary not found for run_id '{run_id}'.")
        else:
            print("No run summaries found.")
        return 1

    if as_json:
        print(json.dumps(summary, indent=2))
    else:
        print(build_run_summary_report(summary))
    return 0


def print_run_summary_list(limit=10, failed_only=False, as_json=False):
    rows = list_run_summaries(limit=limit, failed_only=failed_only)
    if not rows:
        if failed_only:
            print("No failed run summaries found.")
        else:
            print("No run summaries found.")
        return 1

    if as_json:
        print(json.dumps(rows, indent=2))
        return 0

    print("Recent Failed Runs:" if failed_only else "Recent Runs:")
    for row in rows:
        print(
            "- "
            f"{row['run_id']} "
            f"status={row['status']} "
            f"started={row['started_at']} "
            f"duration={row['duration_seconds']}s "
            f"queue={row['queue_size']} "
            f"topic={row['topic']} "
            f"topic_limit={row['topic_limit']} "
            f"spoke_limit={row['spoke_limit']} "
            f"cluster_size={row['cluster_size']}"
        )
    return 0


def run_pipeline(topic=None, spoke_limit=2, topic_limit=None, cluster_size=6):
    run_id = _new_run_id()
    run_start = time.perf_counter()
    run_started_at = _utc_now_iso()

    queue = load_queue()
    if not queue:
        print("No topics found in queue. Add topics via dashboard or topics_queue.json")
        return

    if topic:
        queue = [item for item in queue if item["topic"].lower() == topic.lower()]
        if not queue:
            print(f"Topic '{topic}' not found in queue.")
            return
        print(f"Targeted Run: Processing only '{topic}'")

    priority_map = {"high": 1, "medium": 2, "low": 3}
    queue.sort(key=lambda item: priority_map.get(item.get("priority", "medium"), 2))

    if not topic and topic_limit is not None:
        queue = queue[:topic_limit]

    print(f"[Run] ID: {run_id}")
    print(f"--- Starting Industrial Pipelined Content Engine ({len(queue)} topics) ---")

    summary = {
        "run_id": run_id,
        "started_at": run_started_at,
        "ended_at": None,
        "duration_seconds": None,
        "status": "running",
        "config": {
            "topic": topic,
            "topic_limit": topic_limit,
            "spoke_limit": spoke_limit,
            "cluster_size": cluster_size,
        },
        "queue_size": len(queue),
        "topics": [item.get("topic") for item in queue],
        "phases": [],
    }

    run_config = {
        "spoke_limit": spoke_limit,
        "cluster_size": cluster_size,
    }
    phases = build_phases(queue, run_config)

    try:
        for phase_name, phase_runner in phases:
            phase_start = time.perf_counter()
            phase_started_at = _utc_now_iso()
            phase_status = "completed"
            phase_error = None
            phase_skips = []

            try:
                def _collect_line(line):
                    parsed = _parse_phase_skip(line)
                    if parsed and parsed["phase"] == phase_name:
                        phase_skips.append(parsed)

                tee = _OutputTee(sys.stdout, _collect_line)
                with redirect_stdout(tee):
                    phase_runner()
                tee.flush()
            except Exception as exc:
                phase_status = "failed"
                phase_error = str(exc)
                raise
            finally:
                summary["phases"].append(
                    {
                        "name": phase_name,
                        "started_at": phase_started_at,
                        "ended_at": _utc_now_iso(),
                        "duration_seconds": round(time.perf_counter() - phase_start, 4),
                        "status": phase_status,
                        "error": phase_error,
                        "skips": phase_skips,
                    }
                )

        summary["status"] = "completed"
    except Exception:
        summary["status"] = "failed"
        raise
    finally:
        summary["ended_at"] = _utc_now_iso()
        summary["duration_seconds"] = round(time.perf_counter() - run_start, 4)
        summary_path = _write_run_summary(summary)
        print(f"[Run] Summary written: {summary_path}")

    print("\n--- Industrial Batch Run Complete ---")
