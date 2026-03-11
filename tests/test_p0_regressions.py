import json
import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from crews import content_crew
from engine.pipeline import helpers
from engine.pipeline import runner
from engine.pipeline import phase_registry
from engine.pipeline.phases import article_quality_assurance as qa_phase
from engine.pipeline.phases import cluster_scaling as cs_phase
from tools import article_post_processor
from tools import state_manager

# Ordered phase module paths matching canonical pipeline order
_PHASE_MODULE_PATHS = [
    "engine.pipeline.phases.cluster_map_generation.run",
    "engine.pipeline.phases.cluster_strategy.run",
    "engine.pipeline.phases.serp_analysis.run",
    "engine.pipeline.phases.pillar_generation.run",
    "engine.pipeline.phases.spoke_generation.run",
    "engine.pipeline.phases.seo_optimization.run",
    "engine.pipeline.phases.intelligence_gap_detection.run",
    "engine.pipeline.phases.cluster_scaling.run",
    "engine.pipeline.phases.final_link_injection.run",
    "engine.pipeline.phases.humanization_readability.run",
    "engine.pipeline.phases.article_quality_assurance.run",
]


class RunnerExecutionControlTests(unittest.TestCase):
    def _patch_phases(self):
        return [mock.patch(path) for path in _PHASE_MODULE_PATHS]

    def test_topic_limit_caps_prioritized_queue(self):
        queue = [
            {"topic": "Low Topic", "priority": "low"},
            {"topic": "High Topic", "priority": "high"},
            {"topic": "Medium Topic", "priority": "medium"},
            {"topic": "High Topic 2", "priority": "high"},
        ]

        patches = self._patch_phases()
        with mock.patch("engine.pipeline.runner.load_queue", return_value=queue):
            with patches[0] as cluster_map_run, patches[1] as cluster_run, patches[2], patches[3], patches[4] as spoke_run, patches[5], patches[6], patches[7], patches[8], patches[9]:
                runner.run_pipeline(spoke_limit=1, topic_limit=2, cluster_size=6)

        self.assertEqual(6, cluster_map_run.call_args[0][1])
        processed_queue = cluster_run.call_args[0][0]
        self.assertEqual(2, len(processed_queue))
        self.assertEqual(["High Topic", "High Topic 2"], [item["topic"] for item in processed_queue])
        self.assertEqual(1, spoke_run.call_args[0][1])

    def test_topic_filter_takes_precedence_over_topic_limit(self):
        queue = [
            {"topic": "Invisalign", "priority": "high"},
            {"topic": "Dental Implants", "priority": "medium"},
            {"topic": "Whitening", "priority": "low"},
        ]

        patches = self._patch_phases()
        with mock.patch("engine.pipeline.runner.load_queue", return_value=queue):
            with patches[0], patches[1] as cluster_run, patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8], patches[9]:
                runner.run_pipeline(topic="Dental Implants", spoke_limit=3, topic_limit=1, cluster_size=7)

        processed_queue = cluster_run.call_args[0][0]
        self.assertEqual(1, len(processed_queue))
        self.assertEqual("Dental Implants", processed_queue[0]["topic"])

    def test_run_summary_written_on_success(self):
        queue = [
            {"topic": "Invisalign", "priority": "high"},
        ]

        patches = self._patch_phases()
        with tempfile.TemporaryDirectory() as temp_dir:
            summary_dir = Path(temp_dir)
            with mock.patch("engine.pipeline.runner.load_queue", return_value=queue):
                with mock.patch.object(runner, "RUN_SUMMARY_DIR", summary_dir):
                    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8], patches[9], patches[10]:
                        runner.run_pipeline(spoke_limit=1, topic_limit=1)

            summary_files = list(summary_dir.glob("*.json"))
            self.assertEqual(1, len(summary_files))
            payload = json.loads(summary_files[0].read_text(encoding="utf-8"))

        self.assertEqual("completed", payload["status"])
        self.assertEqual(11, len(payload["phases"]))
        self.assertTrue(all(p["status"] == "completed" for p in payload["phases"]))

    def test_run_summary_written_on_failure(self):
        queue = [
            {"topic": "Invisalign", "priority": "high"},
        ]

        patches = self._patch_phases()
        with tempfile.TemporaryDirectory() as temp_dir:
            summary_dir = Path(temp_dir)
            with mock.patch("engine.pipeline.runner.load_queue", return_value=queue):
                with mock.patch.object(runner, "RUN_SUMMARY_DIR", summary_dir):
                    with patches[0], patches[1], patches[2], patches[3], patches[4] as spoke_run, patches[5], patches[6], patches[7], patches[8], patches[9], patches[10]:
                        spoke_run.side_effect = RuntimeError("spoke boom")
                        with self.assertRaises(RuntimeError):
                            runner.run_pipeline(spoke_limit=1, topic_limit=1)

            summary_files = list(summary_dir.glob("*.json"))
            self.assertEqual(1, len(summary_files))
            payload = json.loads(summary_files[0].read_text(encoding="utf-8"))

        self.assertEqual("failed", payload["status"])
        failed_phases = [p for p in payload["phases"] if p["status"] == "failed"]
        self.assertEqual(1, len(failed_phases))
        self.assertEqual("spoke_generation", failed_phases[0]["name"])
        self.assertIn("spoke boom", failed_phases[0]["error"])

    def test_standardized_skip_events_are_captured(self):
        queue = [
            {"topic": "Invisalign", "priority": "high"},
        ]

        patches = self._patch_phases()
        with tempfile.TemporaryDirectory() as temp_dir:
            summary_dir = Path(temp_dir)
            with mock.patch("engine.pipeline.runner.load_queue", return_value=queue):
                with mock.patch.object(runner, "RUN_SUMMARY_DIR", summary_dir):
                    with patches[0], patches[1] as cluster_run, patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8], patches[9], patches[10]:
                        cluster_run.side_effect = lambda *_args, **_kwargs: print(
                            'Skipping: phase=cluster_strategy topic="Invisalign" reason=completed'
                        )
                        runner.run_pipeline(spoke_limit=1, topic_limit=1)

            summary_files = list(summary_dir.glob("*.json"))
            self.assertEqual(1, len(summary_files))
            payload = json.loads(summary_files[0].read_text(encoding="utf-8"))

        cluster_phase = [p for p in payload["phases"] if p["name"] == "cluster_strategy"][0]
        self.assertEqual(1, len(cluster_phase["skips"]))
        self.assertEqual("completed", cluster_phase["skips"][0]["reason"])
        self.assertEqual("Invisalign", cluster_phase["skips"][0]["topic"])


class StateManagerSchemaTests(unittest.TestCase):
    def test_load_state_returns_versioned_defaults(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)

            def fake_state_file(topic=None):
                name = f"workflow_{state_manager._safe_topic(topic)}.json" if topic else "workflow_state.json"
                return temp_root / name

            with mock.patch("tools.state_manager._state_file_for_topic", side_effect=fake_state_file):
                state = state_manager.load_state("Schema Topic")

        self.assertEqual(state_manager.STATE_VERSION, state["state_version"])
        self.assertEqual("Schema Topic", state["topic"])
        self.assertFalse(state["cluster_generated"])
        self.assertFalse(state["cluster_map_generated"])
        self.assertFalse(state["serp_analysis_generated"])
        self.assertFalse(state["article_locked"])
        self.assertFalse(state["humanized"])
        self.assertEqual(0, state["spokes_total"])

    def test_save_and_load_normalize_legacy_and_numeric_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)

            def fake_state_file(topic=None):
                name = f"workflow_{state_manager._safe_topic(topic)}.json" if topic else "workflow_state.json"
                return temp_root / name

            legacy_payload = {
                "topic": "State Topic",
                "cluster_generated": "yes",
                "spokes_total": "3",
                "spokes_completed": "99",
                "intelligence_run": "true",
            }

            with mock.patch("tools.state_manager._state_file_for_topic", side_effect=fake_state_file):
                state_manager.save_state(legacy_payload, topic="State Topic")
                normalized = state_manager.load_state("State Topic")

        self.assertEqual(state_manager.STATE_VERSION, normalized["state_version"])
        self.assertTrue(normalized["cluster_generated"])
        self.assertEqual(3, normalized["spokes_total"])
        self.assertEqual(3, normalized["spokes_completed"])
        self.assertTrue(normalized["intelligence_completed"])

    def test_save_and_load_cluster_map_topic_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            payload = {
                "topic": "Dental Implants",
                "pillar": "Ultimate Guide to Dental Implants",
                "spokes": [{"title": "Dental Implant Costs in Ireland", "intent": "commercial"}],
            }

            with mock.patch("tools.state_manager.topic_state_dir", side_effect=lambda topic: temp_root / state_manager._safe_topic(topic)):
                state_manager.save_cluster_map("Dental Implants", payload)
                loaded = state_manager.load_cluster_map("Dental Implants")

            self.assertEqual(payload, loaded)
            self.assertTrue((temp_root / "dental_implants" / "cluster_map.json").exists())

    def test_save_and_load_serp_analysis_topic_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            payload = {
                "topic": "Dental Implants",
                "pillar": {"query": "Dental Implants", "top_headings": ["What are dental implants?"], "questions": [], "recommended_word_range": "1500-1800"},
                "spokes": {},
            }

            with mock.patch("tools.state_manager.topic_state_dir", side_effect=lambda topic: temp_root / state_manager._safe_topic(topic)):
                state_manager.save_serp_analysis("Dental Implants", payload)
                loaded = state_manager.load_serp_analysis("Dental Implants")

            self.assertEqual(payload, loaded)
            self.assertTrue((temp_root / "dental_implants" / "serp_analysis.json").exists())

    def test_save_and_load_outline_article_and_pipeline_status(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            outline_payload = {"subtopic": "Ultimate Guide to Dental Implants", "content": "# Outline"}
            article_content = "# Dental Implants\n\nBody"

            with mock.patch("tools.state_manager.topic_state_dir", side_effect=lambda topic: temp_root / state_manager._safe_topic(topic)):
                state_manager.save_outline("Dental Implants", outline_payload)
                state_manager.save_article("Dental Implants", article_content)
                state_manager.update_pipeline_status("Dental Implants", "writer", "completed")
                state_manager.update_pipeline_status("Dental Implants", "qa", "completed")

                loaded_outline = state_manager.load_outline("Dental Implants")
                loaded_article = state_manager.load_article("Dental Implants")
                loaded_status = state_manager.load_pipeline_status("Dental Implants")

            self.assertEqual(outline_payload, loaded_outline)
            self.assertEqual(article_content, loaded_article)
            self.assertEqual("completed", loaded_status["writer"])
            self.assertEqual("completed", loaded_status["qa"])
            self.assertEqual("pending", loaded_status["seo"])
            self.assertTrue((temp_root / "dental_implants" / "outline.json").exists())
            self.assertTrue((temp_root / "dental_implants" / "article.md").exists())
            self.assertTrue((temp_root / "dental_implants" / "pipeline_status.json").exists())

    def test_save_and_load_qa_report_topic_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            payload = {"publish_ready": False, "score": 68, "blockers": [{"issue": "Placeholder text"}]}
            summary = {"topic": "Dental Implants", "publish_ready": False, "articles": []}

            with mock.patch("tools.state_manager.topic_state_dir", side_effect=lambda topic: temp_root / state_manager._safe_topic(topic)):
                state_manager.save_qa_report("Dental Implants", payload)
                loaded = state_manager.load_qa_report("Dental Implants")
                state_manager.save_qa_summary("Dental Implants", summary)
                loaded_summary = state_manager.load_qa_summary("Dental Implants")

            self.assertEqual(payload, loaded)
            self.assertEqual(summary, loaded_summary)
            self.assertTrue((temp_root / "dental_implants" / "article_qa_report.json").exists())
            self.assertTrue((temp_root / "dental_implants" / "qa_report.json").exists())


class ArticlePostProcessorTests(unittest.TestCase):
    def test_ensure_article_template_adds_lock_and_markers(self):
        article = "# Title\n\nIntro paragraph.\n\n## Conclusion\n\nDone."
        rendered = article_post_processor.ensure_article_template(article)

        self.assertIn("<!-- ARTICLE_LOCKED -->", rendered)
        self.assertIn("<!-- SLOT:INTRO -->", rendered)
        self.assertIn("<!-- SLOT:CONCLUSION -->", rendered)

    def test_apply_seo_suggestions_updates_metadata_only(self):
        article = "# Title\n\nBody"
        rendered = article_post_processor.apply_seo_suggestions(
            article,
            {"meta_title": "Meta Title", "meta_description": "Meta Description"},
        )

        self.assertIn("Meta Title: Meta Title", rendered)
        self.assertIn("Meta Description: Meta Description", rendered)
        self.assertIn("# Title", rendered)

    def test_apply_link_and_humanization_suggestions(self):
        article = "This explains dental implant procedure and recovery in simple terms."
        with_links = article_post_processor.apply_link_suggestions(
            article,
            {"internal_links": [{"anchor": "dental implant procedure", "url": "/dental-implant-procedure"}]},
            {},
        )
        final = article_post_processor.apply_humanization_suggestions(
            with_links,
            {"phrase_rewrites": [{"source": "simple terms", "replacement": "plain language"}]},
        )

        self.assertIn("[dental implant procedure](/dental-implant-procedure)", final)
        self.assertIn("plain language", final)

    def test_apply_link_suggestions_skips_headings(self):
        article = "## dental implant procedure\n\nThis dental implant procedure is explained here."
        rendered = article_post_processor.apply_link_suggestions(
            article,
            {"internal_links": [{"anchor": "dental implant procedure", "url": "/dental-implant-procedure"}]},
            {},
        )

        self.assertIn("## dental implant procedure", rendered)
        self.assertIn("[dental implant procedure](/dental-implant-procedure) is explained here", rendered)

    def test_apply_link_suggestions_fallbacks_when_anchor_missing(self):
        article = "This section compares dental implants and dentures to help you choose the best treatment."
        rendered = article_post_processor.apply_link_suggestions(
            article,
            {
                "internal_links": [
                    {
                        "anchor": "the differences between dental implants and dentures to help decide which tooth replacement is best for you",
                        "target_topic": "dental implants vs dentures which tooth replacement option is right for you",
                        "url": "/dental-implants-vs-dentures-which-tooth-replacement-option-is-right-for-you",
                    }
                ]
            },
            {},
        )

        self.assertIn("/dental-implants-vs-dentures-which-tooth-replacement-option-is-right-for-you", rendered)

    def test_ensure_metadata_guardrails_restores_meta_lines(self):
        rendered = article_post_processor.ensure_metadata_guardrails(
            "# Title\n\nBody",
            seo_suggestions={
                "meta_title": "Meta T",
                "meta_description": "Meta D",
            },
            reference_content="Meta Title: Ref Title\nMeta Description: Ref Desc\n\n# Ref",
        )

        self.assertIn("Meta Title:", rendered)
        self.assertIn("Meta Description:", rendered)

    def test_ensure_internal_link_coverage_appends_when_missing(self):
        article = "Meta Title: T\nMeta Description: D\n\n# Title\n\nBody paragraph.\n\n## Local Consultation Call to Action\nCTA"
        rendered = article_post_processor.ensure_internal_link_coverage(
            article,
            {
                "internal_links": [
                    {
                        "anchor": "step by step dental implant procedure what to expect",
                        "url": "/step-by-step-dental-implant-procedure-what-to-expect-before-during-and-after-surgery",
                    }
                ]
            },
            min_links=1,
        )

        self.assertIn("/step-by-step-dental-implant-procedure-what-to-expect-before-during-and-after-surgery", rendered)
        self.assertIn("For related reading, see", rendered)

    def test_apply_link_suggestions_avoids_single_word_fallback_anchor(self):
        article = "The dental implant process typically involves several key steps for safe recovery."
        rendered = article_post_processor.apply_link_suggestions(
            article,
            {
                "internal_links": [
                    {
                        "anchor": "a detailed walkthrough of the dental implant procedure including what to expect",
                        "target_topic": "step by step dental implant procedure what to expect before during and after surgery",
                        "url": "/step-by-step-dental-implant-procedure-what-to-expect-before-during-and-after-surgery",
                    }
                ]
            },
            {},
        )

        self.assertIn("/step-by-step-dental-implant-procedure-what-to-expect-before-during-and-after-surgery", rendered)
        self.assertNotIn("[implant](/step-by-step-dental-implant-procedure-what-to-expect-before-during-and-after-surgery)", rendered)

    def test_sanitize_placeholder_text_removes_dummy_local_cta(self):
        article = (
            "Thinking about treatment? Our team at our clinic provides consultations for patients in your local area and surrounding areas. "
            "📍 Your local area 📞 Contact us for availability.\n\n"
            "Call us at [Local Clinic Phone Number] to get started."
        )

        rendered = article_post_processor.sanitize_placeholder_text(article, location={}, business={})

        self.assertNotIn("our clinic", rendered.lower())
        self.assertNotIn("your local area", rendered.lower())
        self.assertNotIn("contact us for availability", rendered.lower())
        self.assertNotIn("[Local Clinic Phone Number]", rendered)
        self.assertIn("qualified dental professional", rendered)

    def test_sanitize_placeholder_text_cleans_markdown_cta_and_duplicates(self):
        article = (
            "**Thinking about dental implants?** Our team at our clinic provides consultations for patients in your local area and surrounding communities.\n\n"
            "Patients in many local communities choose implants to regain confidence.\n\n"
            "Thinking about treatment? Book a consultation with a qualified dental professional to discuss your options and next steps.\n\n"
            "**If you are considering treatment, book a consultation with a qualified dental professional to discuss suitability, costs, and next steps.**"
        )

        rendered = article_post_processor.sanitize_placeholder_text(article, location={}, business={})

        self.assertNotIn("our clinic", rendered.lower())
        self.assertNotIn("your local area", rendered.lower())
        self.assertEqual(1, rendered.count("Thinking about treatment?"))
        self.assertNotIn("**Thinking about dental implants?**", rendered)
        self.assertIn("Many patients choose implants", rendered)


class QueueAndPromptContextTests(unittest.TestCase):
    def test_load_queue_normalizes_location_and_business(self):
        payload = json.dumps(
            [
                {
                    "topic": "Dental Implants",
                    "priority": "high",
                    "location": {"city": "Dublin", "area": "Dublin 8", "country": "Ireland"},
                    "business": {"name": "Dental Care Dublin 8", "phone": "01 4549688"},
                },
                {"topic": "Whitening", "priority": "low"},
            ]
        )

        with mock.patch("engine.pipeline.helpers.os.path.exists", return_value=True):
            with mock.patch("builtins.open", mock.mock_open(read_data=payload)):
                queue = helpers.load_queue()

        self.assertEqual("Dublin", queue[0]["location"]["city"])
        self.assertEqual("Dental Care Dublin 8", queue[0]["business"]["name"])
        self.assertEqual("healthcare", queue[0]["profile"]["industry"])
        self.assertEqual({}, queue[1]["location"])
        self.assertEqual({}, queue[1]["business"])
        self.assertEqual("healthcare", queue[1]["profile"]["industry"])

    def test_load_queue_profile_overrides_are_applied(self):
        payload = json.dumps(
            [
                {
                    "topic": "Cloud Cost Optimization",
                    "priority": "high",
                    "location": {"country": "United States"},
                    "profile": {
                        "industry": "generic_business",
                        "language": "en",
                        "tone": "confident",
                        "cta_style": "direct"
                    }
                }
            ]
        )

        with mock.patch("engine.pipeline.helpers.os.path.exists", return_value=True):
            with mock.patch("builtins.open", mock.mock_open(read_data=payload)):
                queue = helpers.load_queue()

        self.assertEqual("generic_business", queue[0]["profile"]["industry"])
        self.assertEqual("confident", queue[0]["profile"]["tone"])
        self.assertEqual("direct", queue[0]["profile"]["cta_style"])
        self.assertEqual("$", queue[0]["profile"]["currency"])

    def test_load_queue_infers_finance_and_legal_industries(self):
        payload = json.dumps(
            [
                {
                    "topic": "Retirement Investment Planning Basics",
                    "priority": "high",
                    "location": {"country": "United States"}
                },
                {
                    "topic": "Employment Contract Review Checklist",
                    "priority": "high",
                    "location": {"country": "United Kingdom"}
                },
            ]
        )

        with mock.patch("engine.pipeline.helpers.os.path.exists", return_value=True):
            with mock.patch("builtins.open", mock.mock_open(read_data=payload)):
                queue = helpers.load_queue()

        self.assertEqual("finance", queue[0]["profile"]["industry"])
        self.assertEqual("legal", queue[1]["profile"]["industry"])

    def test_run_writing_crew_passes_location_inputs(self):
        fake_crew = mock.Mock()
        fake_crew.kickoff.return_value = "ok"
        item = {
            "location": {"city": "Dublin", "area": "Dublin 8", "country": "Ireland"},
            "business": {"name": "Dental Care Dublin 8", "phone": "01 4549688"},
        }
        serp_analysis = {
            "top_headings": ["What is the dental implant procedure?"],
            "questions": ["How long does implant recovery take?"],
            "recommended_word_range": "900-1200",
        }

        with mock.patch("crews.content_crew.Crew", return_value=fake_crew):
            with mock.patch("crews.content_crew.get_outline_agent"):
                with mock.patch("crews.content_crew.get_writer_agent"):
                    with mock.patch("crews.content_crew.get_outline_task"):
                        with mock.patch("crews.content_crew.get_writer_task"):
                            content_crew.run_writing_crew("Dental Implants", "Dental Implant Costs", item=item, serp_analysis=serp_analysis)

        kickoff_inputs = fake_crew.kickoff.call_args.kwargs["inputs"]
        self.assertEqual("Dental Implants", kickoff_inputs["topic"])
        self.assertEqual("Dental Implant Costs", kickoff_inputs["subtopic"])
        self.assertIn("city=Dublin", kickoff_inputs["location_context"])
        self.assertIn("name=Dental Care Dublin 8", kickoff_inputs["business_context"])
        self.assertEqual(["What is the dental implant procedure?"], kickoff_inputs["serp_headings"])
        self.assertEqual(["How long does implant recovery take?"], kickoff_inputs["common_questions"])

    def test_build_cta_context_uses_neutral_fallback_when_business_missing(self):
        rendered = helpers.build_cta_context({}, {})

        self.assertNotIn("our clinic", rendered.lower())
        self.assertNotIn("your local area", rendered.lower())
        self.assertNotIn("contact us for availability", rendered.lower())
        self.assertIn("qualified dental professional", rendered)

    def test_format_profile_context_includes_key_dimensions(self):
        rendered = helpers.format_profile_context(
            {
                "industry": "healthcare",
                "language": "en",
                "tone": "professional",
                "audience": "patients",
                "intent": "informational",
                "compliance_level": "strict",
                "cta_style": "consultative",
                "region": "Ireland",
            }
        )

        self.assertIn("industry=healthcare", rendered)
        self.assertIn("compliance_level=strict", rendered)


class RunSummaryInspectorTests(unittest.TestCase):
    def test_print_last_run_summary(self):
        summary_payload = {
            "run_id": "run_20260309T000000Z_abcd1234",
            "status": "completed",
            "started_at": "2026-03-09T00:00:00Z",
            "ended_at": "2026-03-09T00:00:10Z",
            "duration_seconds": 10.0,
            "config": {"topic": None, "topic_limit": 1, "spoke_limit": 1},
            "queue_size": 1,
            "topics": ["Invisalign"],
            "phases": [
                {
                    "name": "cluster_strategy",
                    "status": "completed",
                    "duration_seconds": 0.2,
                    "error": None,
                    "skips": [{"phase": "cluster_strategy", "topic": "Invisalign", "reason": "completed", "detail": None}],
                }
            ],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            summary_dir = Path(temp_dir)
            (summary_dir / "run_20260309T000000Z_abcd1234.json").write_text(
                json.dumps(summary_payload), encoding="utf-8"
            )

            with mock.patch.object(runner, "RUN_SUMMARY_DIR", summary_dir):
                output = io.StringIO()
                with redirect_stdout(output):
                    code = runner.print_run_summary(latest=True)

        self.assertEqual(0, code)
        rendered = output.getvalue()
        self.assertIn("Run Summary: run_20260309T000000Z_abcd1234", rendered)
        self.assertIn("skip topic=Invisalign reason=completed", rendered)

    def test_print_last_run_summary_json(self):
        summary_payload = {
            "run_id": "run_20260309T000000Z_abcd1234",
            "status": "completed",
            "started_at": "2026-03-09T00:00:00Z",
            "ended_at": "2026-03-09T00:00:10Z",
            "duration_seconds": 10.0,
            "config": {"topic": None, "topic_limit": 1, "spoke_limit": 1},
            "queue_size": 1,
            "topics": ["Invisalign"],
            "phases": [],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            summary_dir = Path(temp_dir)
            (summary_dir / "run_20260309T000000Z_abcd1234.json").write_text(
                json.dumps(summary_payload), encoding="utf-8"
            )

            with mock.patch.object(runner, "RUN_SUMMARY_DIR", summary_dir):
                output = io.StringIO()
                with redirect_stdout(output):
                    code = runner.print_run_summary(latest=True, as_json=True)

        self.assertEqual(0, code)
        rendered = json.loads(output.getvalue())
        self.assertEqual("run_20260309T000000Z_abcd1234", rendered["run_id"])

    def test_print_run_summary_missing_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            summary_dir = Path(temp_dir)
            with mock.patch.object(runner, "RUN_SUMMARY_DIR", summary_dir):
                output = io.StringIO()
                with redirect_stdout(output):
                    code = runner.print_run_summary(run_id="run_missing")

        self.assertEqual(1, code)
        self.assertIn("Run summary not found", output.getvalue())

    def test_print_run_summary_list(self):
        payload_a = {
            "run_id": "run_20260309T000001Z_aaaa1111",
            "status": "completed",
            "started_at": "2026-03-09T00:00:01Z",
            "duration_seconds": 1.2,
            "queue_size": 1,
            "config": {"topic": "Invisalign", "topic_limit": 1, "spoke_limit": 1},
        }
        payload_b = {
            "run_id": "run_20260309T000002Z_bbbb2222",
            "status": "failed",
            "started_at": "2026-03-09T00:00:02Z",
            "duration_seconds": 2.3,
            "queue_size": 2,
            "config": {"topic": None, "topic_limit": 2, "spoke_limit": 1},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            summary_dir = Path(temp_dir)
            (summary_dir / "run_20260309T000001Z_aaaa1111.json").write_text(json.dumps(payload_a), encoding="utf-8")
            (summary_dir / "run_20260309T000002Z_bbbb2222.json").write_text(json.dumps(payload_b), encoding="utf-8")

            with mock.patch.object(runner, "RUN_SUMMARY_DIR", summary_dir):
                output = io.StringIO()
                with redirect_stdout(output):
                    code = runner.print_run_summary_list(limit=2)

        self.assertEqual(0, code)
        rendered = output.getvalue()
        self.assertIn("Recent Runs:", rendered)
        self.assertIn("run_20260309T000001Z_aaaa1111", rendered)
        self.assertIn("run_20260309T000002Z_bbbb2222", rendered)

    def test_print_run_summary_list_json(self):
        payload_a = {
            "run_id": "run_20260309T000001Z_aaaa1111",
            "status": "completed",
            "started_at": "2026-03-09T00:00:01Z",
            "duration_seconds": 1.2,
            "queue_size": 1,
            "config": {"topic": "Invisalign", "topic_limit": 1, "spoke_limit": 1},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            summary_dir = Path(temp_dir)
            (summary_dir / "run_20260309T000001Z_aaaa1111.json").write_text(json.dumps(payload_a), encoding="utf-8")

            with mock.patch.object(runner, "RUN_SUMMARY_DIR", summary_dir):
                output = io.StringIO()
                with redirect_stdout(output):
                    code = runner.print_run_summary_list(limit=2, as_json=True)

        self.assertEqual(0, code)
        rendered = json.loads(output.getvalue())
        self.assertEqual(1, len(rendered))
        self.assertEqual("run_20260309T000001Z_aaaa1111", rendered[0]["run_id"])

    def test_print_run_summary_list_empty(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            summary_dir = Path(temp_dir)
            with mock.patch.object(runner, "RUN_SUMMARY_DIR", summary_dir):
                output = io.StringIO()
                with redirect_stdout(output):
                    code = runner.print_run_summary_list(limit=5)

        self.assertEqual(1, code)
        self.assertIn("No run summaries found.", output.getvalue())

    def test_print_run_summary_list_failed_only(self):
        payload_ok = {
            "run_id": "run_20260309T000001Z_aaaa1111",
            "status": "completed",
            "started_at": "2026-03-09T00:00:01Z",
            "duration_seconds": 1.2,
            "queue_size": 1,
            "config": {"topic": "Invisalign", "topic_limit": 1, "spoke_limit": 1},
        }
        payload_fail = {
            "run_id": "run_20260309T000002Z_bbbb2222",
            "status": "failed",
            "started_at": "2026-03-09T00:00:02Z",
            "duration_seconds": 2.3,
            "queue_size": 2,
            "config": {"topic": None, "topic_limit": 2, "spoke_limit": 1},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            summary_dir = Path(temp_dir)
            (summary_dir / "run_20260309T000001Z_aaaa1111.json").write_text(json.dumps(payload_ok), encoding="utf-8")
            (summary_dir / "run_20260309T000002Z_bbbb2222.json").write_text(json.dumps(payload_fail), encoding="utf-8")

            with mock.patch.object(runner, "RUN_SUMMARY_DIR", summary_dir):
                output = io.StringIO()
                with redirect_stdout(output):
                    code = runner.print_run_summary_list(limit=5, failed_only=True)

        self.assertEqual(0, code)
        rendered = output.getvalue()
        self.assertIn("Recent Failed Runs:", rendered)
        self.assertIn("run_20260309T000002Z_bbbb2222", rendered)
        self.assertNotIn("run_20260309T000001Z_aaaa1111", rendered)

    def test_print_run_summary_list_failed_only_empty(self):
        payload_ok = {
            "run_id": "run_20260309T000001Z_aaaa1111",
            "status": "completed",
            "started_at": "2026-03-09T00:00:01Z",
            "duration_seconds": 1.2,
            "queue_size": 1,
            "config": {"topic": "Invisalign", "topic_limit": 1, "spoke_limit": 1},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            summary_dir = Path(temp_dir)
            (summary_dir / "run_20260309T000001Z_aaaa1111.json").write_text(json.dumps(payload_ok), encoding="utf-8")

            with mock.patch.object(runner, "RUN_SUMMARY_DIR", summary_dir):
                output = io.StringIO()
                with redirect_stdout(output):
                    code = runner.print_run_summary_list(limit=5, failed_only=True)

        self.assertEqual(1, code)
        self.assertIn("No failed run summaries found.", output.getvalue())


class QAProfileThresholdTests(unittest.TestCase):
    # ---- _get_publish_threshold ----------------------------------------
    def test_get_publish_threshold_strict_returns_85(self):
        self.assertEqual(85, qa_phase._get_publish_threshold("strict"))

    def test_get_publish_threshold_standard_returns_75(self):
        self.assertEqual(75, qa_phase._get_publish_threshold("standard"))

    # ---- _merge_report compliance gate ---------------------------------
    def test_merge_report_strict_rejects_score_below_85(self):
        model_report = {"publish_ready": True, "score": 80, "blockers": [], "warnings": [], "strengths": [], "suggested_edits": []}
        result = qa_phase._merge_report([], [], [], model_report, compliance_level="strict")
        self.assertFalse(result["publish_ready"])
        self.assertLess(result["score"], 85)

    def test_merge_report_strict_allows_score_85_and_above(self):
        model_report = {"publish_ready": True, "score": 90, "blockers": [], "warnings": [], "strengths": [], "suggested_edits": []}
        result = qa_phase._merge_report([], [], [], model_report, compliance_level="strict")
        self.assertTrue(result["publish_ready"])
        self.assertGreaterEqual(result["score"], 85)

    def test_merge_report_standard_allows_score_75_to_84(self):
        model_report = {"publish_ready": True, "score": 78, "blockers": [], "warnings": [], "strengths": [], "suggested_edits": []}
        result = qa_phase._merge_report([], [], [], model_report, compliance_level="standard")
        self.assertTrue(result["publish_ready"])
        self.assertGreaterEqual(result["score"], 75)

    def test_merge_report_standard_rejects_score_below_75(self):
        model_report = {"publish_ready": True, "score": 70, "blockers": [], "warnings": [], "strengths": [], "suggested_edits": []}
        result = qa_phase._merge_report([], [], [], model_report, compliance_level="standard")
        self.assertFalse(result["publish_ready"])
        self.assertLess(result["score"], 75)

    def test_merge_report_exposes_compliance_level_in_result(self):
        model_report = {"publish_ready": True, "score": 88, "blockers": [], "warnings": [], "strengths": [], "suggested_edits": []}
        result = qa_phase._merge_report([], [], [], model_report, compliance_level="strict")
        self.assertEqual("strict", result["compliance_level"])
        self.assertEqual(85, result["publish_threshold"])

    # ---- _deterministic_findings forbidden phrases ----------------------
    def test_deterministic_findings_flags_forbidden_phrase_as_blocker(self):
        article = "Meta Title: Test\nMeta Description: Test\n\nThis investment is a guaranteed return for all clients."
        profile = {"industry": "finance", "forbidden_phrases": ["guaranteed return", "risk-free investment"]}
        blockers, warnings, _ = qa_phase._deterministic_findings(article, profile=profile)
        issues = [b["issue"] for b in blockers]
        evidences = [b["evidence"] for b in blockers]
        self.assertIn("Forbidden phrase detected", issues)
        self.assertIn("guaranteed return", evidences)

    def test_deterministic_findings_no_blockers_when_phrase_absent(self):
        article = "Meta Title: Test\nMeta Description: Test\n\nThis is a standard investment commentary."
        profile = {"industry": "finance", "forbidden_phrases": ["guaranteed return"]}
        blockers, _, _ = qa_phase._deterministic_findings(article, profile=profile)
        forbidden_blockers = [b for b in blockers if b["issue"] == "Forbidden phrase detected"]
        self.assertEqual(0, len(forbidden_blockers))

    def test_deterministic_findings_no_profile_still_works(self):
        article = "Meta Title: Title\nMeta Description: Desc\n\nSome content."
        blockers, warnings, strengths = qa_phase._deterministic_findings(article, profile=None)
        self.assertIsInstance(blockers, list)
        self.assertIsInstance(warnings, list)


class PhaseRegistryTests(unittest.TestCase):
    def test_get_phase_ids_returns_canonical_order(self):
        ids = phase_registry.get_phase_ids()
        self.assertEqual(11, len(ids))
        self.assertEqual("cluster_map_generation", ids[0])
        self.assertEqual("article_quality_assurance", ids[-1])
        # Verify key ordering invariants
        self.assertLess(ids.index("cluster_strategy"), ids.index("serp_analysis"))
        self.assertLess(ids.index("serp_analysis"), ids.index("pillar_generation"))
        self.assertLess(ids.index("pillar_generation"), ids.index("spoke_generation"))
        self.assertLess(ids.index("seo_optimization"), ids.index("final_link_injection"))
        self.assertLess(ids.index("final_link_injection"), ids.index("humanization_readability"))
        self.assertLess(ids.index("humanization_readability"), ids.index("article_quality_assurance"))

    def test_get_phase_returns_definition(self):
        defn = phase_registry.get_phase("seo_optimization")
        self.assertIsNotNone(defn)
        self.assertEqual("seo_optimization", defn.phase_id)
        self.assertEqual("engine.pipeline.phases.seo_optimization", defn.module_path)
        self.assertEqual("run", defn.runner_fn)
        self.assertEqual([], defn.extra_args)

    def test_get_phase_returns_none_for_unknown(self):
        self.assertIsNone(phase_registry.get_phase("nonexistent_phase"))

    def test_phases_with_extra_args_are_declared(self):
        cluster_map = phase_registry.get_phase("cluster_map_generation")
        self.assertIn("cluster_size", cluster_map.extra_args)
        spoke = phase_registry.get_phase("spoke_generation")
        self.assertIn("spoke_limit", spoke.extra_args)

    def test_build_phases_returns_all_11_by_default(self):
        queue = [{"topic": "Test Topic", "priority": "high"}]
        config = {"spoke_limit": 2, "cluster_size": 6}
        with mock.patch.dict("os.environ", {}, clear=False):
            os.environ.pop("PIPELINE_SKIP_PHASES", None)
            phases = phase_registry.build_phases(queue, config)
        self.assertEqual(11, len(phases))
        ids = [p[0] for p in phases]
        self.assertEqual(phase_registry.get_phase_ids(), ids)

    def test_build_phases_skips_disabled_phases(self):
        import os
        queue = [{"topic": "Test Topic", "priority": "high"}]
        config = {"spoke_limit": 2, "cluster_size": 6}
        with mock.patch.dict("os.environ", {"PIPELINE_SKIP_PHASES": "intelligence_gap_detection,cluster_scaling"}):
            phases = phase_registry.build_phases(queue, config)
        ids = [p[0] for p in phases]
        self.assertEqual(9, len(ids))
        self.assertNotIn("intelligence_gap_detection", ids)
        self.assertNotIn("cluster_scaling", ids)
        # Remaining phases preserve canonical order
        self.assertLess(ids.index("seo_optimization"), ids.index("final_link_injection"))

    def test_build_phases_runners_are_callable(self):
        queue = [{"topic": "Test Topic", "priority": "high"}]
        config = {"spoke_limit": 2, "cluster_size": 6}
        with mock.patch.dict("os.environ", {}, clear=False):
            os.environ.pop("PIPELINE_SKIP_PHASES", None)
            phases = phase_registry.build_phases(queue, config)
        for phase_id, runner_fn in phases:
            self.assertTrue(callable(runner_fn), f"Runner for {phase_id} is not callable")

    def test_build_phases_passes_extra_args_to_runner(self):
        """Verify build_phases wires extra_args from config into each phase runner."""
        queue = [{"topic": "Test", "priority": "high"}]
        config = {"spoke_limit": 5, "cluster_size": 8}

        call_log = {}

        def make_fake_run(phase_id):
            def fake_run(*args):
                call_log[phase_id] = args
            return fake_run

        import importlib
        import engine.pipeline.phases.cluster_map_generation as _cmg
        import engine.pipeline.phases.spoke_generation as _sg

        with mock.patch.object(_cmg, "run", side_effect=make_fake_run("cluster_map_generation")), \
             mock.patch.object(_sg, "run", side_effect=make_fake_run("spoke_generation")):
            with mock.patch.dict("os.environ", {}, clear=False):
                os.environ.pop("PIPELINE_SKIP_PHASES", None)
                phases = phase_registry.build_phases(queue, config)

            phase_map = {pid: fn for pid, fn in phases}
            phase_map["cluster_map_generation"]()
            phase_map["spoke_generation"]()

        self.assertEqual((queue, 8), call_log["cluster_map_generation"])
        self.assertEqual((queue, 5), call_log["spoke_generation"])


class ClusterScalingTests(unittest.TestCase):
    def _base_state(self, **overrides):
        state = {
            "cluster_scaled": False,
            "intelligence_completed": True,
            "cluster_generated": True,
            "spoke_backlog_saved": False,
        }
        state.update(overrides)
        return state

    def _sample_gap_items(self):
        return [
            {
                "gap_topic": "Big SEO Gap",
                "justification": "There is a significant gap in competitor coverage.",
                "suggested_new_sub_topic": "Filling the SEO Gap",
            },
            {
                "gap_topic": "Minor Topic",
                "justification": "You could consider adding this topic.",
                "suggested_new_sub_topic": "Minor Topic Article",
            },
        ]

    # ---- helper unit tests -----------------------------------------------

    def test_score_confidence_high_signal(self):
        self.assertEqual(0.9, cs_phase._score_confidence("There is a significant gap here"))

    def test_score_confidence_medium_high_signal(self):
        self.assertEqual(0.8, cs_phase._score_confidence("This is an important topic to cover"))

    def test_score_confidence_medium_signal(self):
        self.assertEqual(0.7, cs_phase._score_confidence("Our content lacks this topic currently"))

    def test_score_confidence_lower_medium_signal(self):
        self.assertEqual(0.6, cs_phase._score_confidence("You could consider adding this"))

    def test_score_confidence_default(self):
        self.assertEqual(0.5, cs_phase._score_confidence("A nice topic for the future"))

    def test_existing_spoke_titles_returns_lowercase_set(self):
        cluster_map = {
            "pillar_topic": "Test",
            "spoke_topics": [
                {"sub_topic": "Invisalign Treatment Process"},
                {"sub_topic": "Braces vs Aligners"},
            ],
        }
        result = cs_phase._existing_spoke_titles(cluster_map)
        self.assertIn("invisalign treatment process", result)
        self.assertIn("braces vs aligners", result)

    def test_existing_spoke_titles_empty_for_none_and_empty_map(self):
        self.assertEqual(set(), cs_phase._existing_spoke_titles(None))
        self.assertEqual(set(), cs_phase._existing_spoke_titles({}))

    def test_build_backlog_excludes_existing_spokes(self):
        gap_items = [
            {"gap_topic": "Gap", "justification": "significant gap", "suggested_new_sub_topic": "New Topic"},
            {"gap_topic": "Dup", "justification": "important", "suggested_new_sub_topic": "Existing Topic"},
        ]
        result = cs_phase._build_backlog(gap_items, {"existing topic"})
        self.assertEqual(1, len(result))
        self.assertEqual("New Topic", result[0]["title"])

    def test_build_backlog_entry_structure(self):
        gap_items = [
            {
                "gap_topic": "SEO Gap",
                "justification": "there is a significant gap in competitor content",
                "suggested_new_sub_topic": "New Spoke Title",
            },
        ]
        result = cs_phase._build_backlog(gap_items, set())
        self.assertEqual(1, len(result))
        entry = result[0]
        self.assertEqual("New Spoke Title", entry["title"])
        self.assertEqual("SEO Gap", entry["intent"])
        self.assertEqual(0.9, entry["confidence"])
        self.assertEqual("intelligence", entry["source"])
        self.assertFalse(entry["approved"])

    def test_build_backlog_skips_items_missing_title(self):
        gap_items = [
            {"gap_topic": "No Title", "justification": "important", "suggested_new_sub_topic": ""},
            {"gap_topic": "Has Title", "justification": "gaps", "suggested_new_sub_topic": "Valid Title"},
        ]
        result = cs_phase._build_backlog(gap_items, set())
        self.assertEqual(1, len(result))
        self.assertEqual("Valid Title", result[0]["title"])

    # ---- run() integration tests -----------------------------------------

    def test_run_skips_when_already_scaled(self):
        queue = [{"topic": "Dental Implants"}]
        state = self._base_state(cluster_scaled=True)
        with mock.patch("engine.pipeline.phases.cluster_scaling.load_state", return_value=state):
            with mock.patch("engine.pipeline.phases.cluster_scaling.save_spoke_backlog") as mock_save:
                cs_phase.run(queue)
        mock_save.assert_not_called()

    def test_run_skips_when_intelligence_pending(self):
        queue = [{"topic": "Dental Implants"}]
        state = self._base_state(intelligence_completed=False)
        with mock.patch("engine.pipeline.phases.cluster_scaling.load_state", return_value=state):
            with mock.patch("engine.pipeline.phases.cluster_scaling.save_spoke_backlog") as mock_save:
                cs_phase.run(queue)
        mock_save.assert_not_called()

    def test_run_sets_state_flags(self):
        queue = [{"topic": "Invisalign"}]
        state = self._base_state()
        gap_items = self._sample_gap_items()
        cluster_map = {"pillar_topic": "Invisalign", "spoke_topics": []}
        with mock.patch("engine.pipeline.phases.cluster_scaling.load_state", return_value=state):
            with mock.patch("engine.pipeline.phases.cluster_scaling._parse_intelligence", return_value=gap_items):
                with mock.patch("engine.pipeline.phases.cluster_scaling.load_cluster_map", return_value=cluster_map):
                    with mock.patch("engine.pipeline.phases.cluster_scaling.save_spoke_backlog"):
                        with mock.patch("engine.pipeline.phases.cluster_scaling.update_state") as mock_update:
                            cs_phase.run(queue)
        updated = {call.args[0]: call.args[1] for call in mock_update.call_args_list}
        self.assertTrue(updated.get("spoke_backlog_saved"))
        self.assertTrue(updated.get("cluster_scaled"))

    def test_run_deduplicates_against_cluster_map(self):
        queue = [{"topic": "Invisalign"}]
        state = self._base_state()
        gap_items = [
            {
                "gap_topic": "Dup",
                "justification": "gaps",
                "suggested_new_sub_topic": "Invisalign vs Traditional Braces: Pros and Cons",
            },
            {
                "gap_topic": "New",
                "justification": "gaps",
                "suggested_new_sub_topic": "Brand New Article",
            },
        ]
        cluster_map = {
            "pillar_topic": "Invisalign",
            "spoke_topics": [{"sub_topic": "Invisalign vs Traditional Braces: Pros and Cons"}],
        }
        captured = []
        with mock.patch("engine.pipeline.phases.cluster_scaling.load_state", return_value=state):
            with mock.patch("engine.pipeline.phases.cluster_scaling._parse_intelligence", return_value=gap_items):
                with mock.patch("engine.pipeline.phases.cluster_scaling.load_cluster_map", return_value=cluster_map):
                    with mock.patch("engine.pipeline.phases.cluster_scaling.save_spoke_backlog", side_effect=lambda t, b: captured.extend(b)):
                        with mock.patch("engine.pipeline.phases.cluster_scaling.update_state"):
                            cs_phase.run(queue)
        self.assertEqual(1, len(captured))
        self.assertEqual("Brand New Article", captured[0]["title"])

    def test_run_handles_empty_intelligence_result(self):
        queue = [{"topic": "Dental Implants"}]
        state = self._base_state()
        with mock.patch("engine.pipeline.phases.cluster_scaling.load_state", return_value=state):
            with mock.patch("engine.pipeline.phases.cluster_scaling._parse_intelligence", return_value=[]):
                with mock.patch("engine.pipeline.phases.cluster_scaling.load_cluster_map", return_value=None):
                    with mock.patch("engine.pipeline.phases.cluster_scaling.save_spoke_backlog") as mock_save:
                        with mock.patch("engine.pipeline.phases.cluster_scaling.update_state"):
                            cs_phase.run(queue)
        mock_save.assert_called_once_with("Dental Implants", [])

    def test_parse_intelligence_handles_missing_file(self):
        result = cs_phase._parse_intelligence("/nonexistent/path/intel.md")
        self.assertEqual([], result)

    def test_parse_intelligence_handles_invalid_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write("this is not valid json {{{{")
            tmp_path = f.name
        try:
            result = cs_phase._parse_intelligence(tmp_path)
            self.assertEqual([], result)
        finally:
            os.unlink(tmp_path)

    def test_parse_intelligence_parses_valid_json_array(self):
        payload = json.dumps([
            {"gap_topic": "Test Gap", "justification": "missing content", "suggested_new_sub_topic": "Test Article"},
        ])
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(payload)
            tmp_path = f.name
        try:
            result = cs_phase._parse_intelligence(tmp_path)
            self.assertEqual(1, len(result))
            self.assertEqual("Test Gap", result[0]["gap_topic"])
        finally:
            os.unlink(tmp_path)

    def test_parse_intelligence_strips_markdown_fence(self):
        payload = json.dumps([{"gap_topic": "G", "justification": "j", "suggested_new_sub_topic": "S"}])
        content = f"```json\n{payload}\n```"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(content)
            tmp_path = f.name
        try:
            result = cs_phase._parse_intelligence(tmp_path)
            self.assertEqual(1, len(result))
        finally:
            os.unlink(tmp_path)


if __name__ == "__main__":
    unittest.main()