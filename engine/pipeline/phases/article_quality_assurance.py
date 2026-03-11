import json
import os

from crews.content_crew import run_article_qa_crew
from tools.article_post_processor import parse_json_payload
from tools.state_manager import (
    load_pipeline_status,
    load_qa_report,
    load_qa_summary,
    load_state,
    save_qa_report,
    save_qa_summary,
    update_pipeline_status,
    update_state,
)

from engine.pipeline.helpers import clean_json_output, get_cluster_spokes, safe_slug
from engine.pipeline.phase_logging import log_phase_skip


PLACEHOLDER_PATTERNS = [
    "our clinic",
    "your local area",
    "contact us for availability",
    "local clinic phone number",
]


def _artifact_name(filename, topic_slug):
    if filename == f"{topic_slug}_pillar_final.md":
        return "article"
    return filename.replace("_final.md", "")


def _is_canonical_final_file(filename):
    return filename.endswith("_final.md") and not filename.endswith("_seo_final.md")


def _get_publish_threshold(compliance_level: str) -> int:
    """Return the minimum score required for publish_ready=True."""
    return 85 if compliance_level == "strict" else 75


def _deterministic_findings(article_content, profile=None):
    text = article_content or ""
    lowered = text.lower()
    _profile = profile if isinstance(profile, dict) else {}

    blockers = []
    warnings = []
    strengths = []

    if not text.strip():
        blockers.append({
            "issue": "Empty final article",
            "evidence": "No article content found.",
            "suggestion": "Regenerate the final article before review.",
        })
        return blockers, warnings, strengths

    lines = text.splitlines()
    meta_title = next((line for line in lines if line.startswith("Meta Title:")), "")
    meta_description = next((line for line in lines if line.startswith("Meta Description:")), "")

    if not meta_title.strip().replace("Meta Title:", "").strip():
        blockers.append({
            "issue": "Missing meta title",
            "evidence": "Meta Title is blank or missing.",
            "suggestion": "Provide a specific SEO title before publishing.",
        })
    if not meta_description.strip().replace("Meta Description:", "").strip():
        blockers.append({
            "issue": "Missing meta description",
            "evidence": "Meta Description is blank or missing.",
            "suggestion": "Provide a specific meta description before publishing.",
        })

    for pattern in PLACEHOLDER_PATTERNS:
        if pattern in lowered:
            blockers.append({
                "issue": "Placeholder local/business text detected",
                "evidence": pattern,
                "suggestion": "Replace placeholders with real business/location details or neutral non-local wording.",
            })

    if "revolutionized" in lowered:
        warnings.append({
            "issue": "AI-sounding hype phrasing",
            "evidence": "revolutionized",
            "suggestion": "Replace with plain, patient-friendly wording.",
        })

    for phrase in _profile.get("forbidden_phrases") or []:
        if phrase.lower() in lowered:
            blockers.append({
                "issue": "Forbidden phrase detected",
                "evidence": phrase,
                "suggestion": f"Remove or rephrase '{phrase}' — disallowed by the '{_profile.get('industry', 'policy')}' policy pack.",
            })

    if meta_title and meta_description:
        strengths.append("Metadata is present in the final article.")
    if "<!-- article_locked -->" in lowered:
        strengths.append("Article lock marker is present.")

    return blockers, warnings, strengths


def _merge_report(deterministic_blockers, deterministic_warnings, deterministic_strengths, model_report, compliance_level="standard"):
    report = model_report if isinstance(model_report, dict) else {}
    blockers = list(deterministic_blockers) + list(report.get("blockers") or [])
    warnings = list(deterministic_warnings) + list(report.get("warnings") or [])
    strengths = list(deterministic_strengths) + list(report.get("strengths") or [])
    suggested_edits = list(report.get("suggested_edits") or [])

    publish_ready = bool(report.get("publish_ready", True)) and not blockers
    score = report.get("score", 85)
    try:
        score = max(0, min(100, int(score)))
    except Exception:
        score = 85

    if blockers:
        score = min(score, 69)
    elif warnings:
        def _warning_text(warning):
            if not isinstance(warning, dict):
                return ""
            issue = warning.get("issue") or ""
            evidence = warning.get("evidence") or ""
            suggestion = warning.get("suggestion") or ""
            return " ".join([issue, evidence, suggestion]).lower()

        warning_texts = [_warning_text(warning) for warning in warnings]
        minor_markers = [
            "minor",
            "slight",
            "slightly",
            "optional",
            "low",
            "format",
            "repetition",
            "redund",
            "generic phrasing",
            "spam",
            "spam-protected",
            "clickable",
        ]
        only_minor_warnings = bool(warning_texts) and all(
            any(marker in text for marker in minor_markers)
            for text in warning_texts
        )
        severity_values = [
            (edit.get("severity") or "").strip().lower()
            for edit in suggested_edits
            if isinstance(edit, dict)
        ]
        all_low_suggested_edits = bool(severity_values) and all(
            severity in {"low", "minor"}
            for severity in severity_values
        )

        if publish_ready and all_low_suggested_edits and len(warnings) <= 5:
            score = max(score, 92)
            score = min(score, 95)
        elif publish_ready and only_minor_warnings:
            score = max(score, 92)
            score = min(score, 95)
        else:
            score = min(score, 89)

    publish_threshold = _get_publish_threshold(compliance_level)
    if score < publish_threshold and publish_ready:
        publish_ready = False
        score = min(score, publish_threshold - 1)

    return {
        "publish_ready": publish_ready,
        "score": score,
        "compliance_level": compliance_level,
        "publish_threshold": publish_threshold,
        "summary": report.get("summary") or ("Ready to publish." if publish_ready else "Edits are needed before publish."),
        "blockers": blockers,
        "warnings": warnings,
        "strengths": strengths,
        "suggested_edits": suggested_edits,
    }


def _normalize_report_for_context(report, item):
    report = dict(report or {})
    location = item.get("location") if isinstance(item.get("location"), dict) else {}
    business = item.get("business") if isinstance(item.get("business"), dict) else {}
    has_local_context = any(location.values()) or any(business.values())

    if has_local_context:
        return report

    blockers = []
    warnings = list(report.get("warnings") or [])
    moved = False

    for blocker in report.get("blockers") or []:
        issue = (blocker.get("issue") or "").lower()
        suggestion = (blocker.get("suggestion") or "").lower()
        evidence = (blocker.get("evidence") or "").lower()
        combined = " ".join([issue, suggestion, evidence])
        if any(
            phrase in combined
            for phrase in [
                "missing local business",
                "specific business",
                "specific location",
                "location details",
                "local clinic",
                "clinic name",
                "booking link",
            ]
        ):
            warnings.append(blocker)
            moved = True
        else:
            blockers.append(blocker)

    report["blockers"] = blockers
    report["warnings"] = warnings
    if moved and not blockers:
        report["publish_ready"] = True
        try:
            report["score"] = max(int(report.get("score", 85)), 89)
        except Exception:
            report["score"] = 89
    return report


def run(queue):
    print("\n--- Phase 9: Article Quality Assurance ---")
    for item in queue:
        topic = item["topic"]
        state = load_state(topic)
        topic_slug = safe_slug(topic)

        if not state.get("humanized"):
            log_phase_skip("article_quality_assurance", topic, "humanization_pending")
            continue

        pipeline_status = load_pipeline_status(topic)
        if state.get("qa_reviewed") and pipeline_status.get("qa") == "completed" and load_qa_summary(topic):
            log_phase_skip("article_quality_assurance", topic, "completed")
            continue

        all_final_files = [f for f in os.listdir("outputs") if _is_canonical_final_file(f)]
        final_files = [f for f in all_final_files if topic_slug in f.lower()]

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
                    final_files.extend(
                        [
                            f
                            for f in all_final_files
                            if f.startswith("spoke_") and spoke_safe in f and f not in final_files
                        ]
                    )
            except Exception as exc:
                print(f"  Warning: Could not parse cluster for QA file matching: {exc}")

        if not final_files:
            log_phase_skip("article_quality_assurance", topic, "final_files_missing")
            continue

        print(f"Reviewing final articles for: {topic}...")
        update_pipeline_status(topic, "qa", "running")
        reports = []
        publish_ready = True

        try:
            for filename in final_files:
                article_name = _artifact_name(filename, topic_slug)
                file_path = os.path.join("outputs", filename)
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    article_content = f.read()

                existing_report = load_qa_report(topic, article_name)
                if existing_report:
                    report = existing_report
                else:
                    profile = item.get("profile") if isinstance(item.get("profile"), dict) else {}
                    compliance_level = profile.get("compliance_level", "standard")
                    deterministic_blockers, deterministic_warnings, deterministic_strengths = _deterministic_findings(article_content, profile=profile)
                    raw_result = run_article_qa_crew(article_content, topic=topic, item=item)
                    model_report = parse_json_payload(str(raw_result))
                    report = _merge_report(deterministic_blockers, deterministic_warnings, deterministic_strengths, model_report, compliance_level=compliance_level)
                    report = _normalize_report_for_context(report, item)
                    report["article_name"] = article_name
                    report["output_file"] = filename
                    save_qa_report(topic, report, article_name=article_name)

                publish_ready = publish_ready and bool(report.get("publish_ready"))
                reports.append({
                    "article_name": article_name,
                    "output_file": filename,
                    "publish_ready": bool(report.get("publish_ready")),
                    "score": report.get("score"),
                    "blocker_count": len(report.get("blockers") or []),
                    "warning_count": len(report.get("warnings") or []),
                    "summary": report.get("summary", ""),
                })
                status_text = "PASS" if report.get("publish_ready") else "REVIEW"
                print(f"  QA {status_text}: {filename}")

            save_qa_summary(topic, {
                "topic": topic,
                "publish_ready": publish_ready,
                "articles": reports,
            })
            update_state("qa_reviewed", True, topic)
            update_state("publish_ready", publish_ready, topic)
            update_pipeline_status(topic, "qa", "completed")
        except Exception as exc:
            update_pipeline_status(topic, "qa", "failed")
            print(f"Error in Phase 9 for {topic}: {exc}")
