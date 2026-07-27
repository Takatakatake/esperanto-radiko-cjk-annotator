# -*- coding: utf-8 -*-
"""Fail-closed ordering tests for the latest-Kyoto R74 pipeline."""
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent


class R74LatestKyotoPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (HERE / "regenerate_all.py").read_text(encoding="utf-8")

    def test_three_corpus_roles_are_explicit(self):
        for name in (
            "ESP_PHASE558_PARENT_CORPUS_PATH",
            "ESP_LATEST_KYOTO_MAIN_PATH",
            "ESP_CORPUS_PATH",
            "ESP_PHASE558_CURRENT_CORPUS_PATH",
        ):
            self.assertIn(f'"{name}"', self.source)
        self.assertIn(
            '"ESP_CURRENT_CORPUS_REFERENCE_PATH":\n'
            '        os.environ["ESP_LATEST_KYOTO_MAIN_PATH"]',
            self.source,
        )
        self.assertIn(
            '"ESP_CURRENT_CORPUS_ACTIVE_PATH": os.environ["ESP_CORPUS_PATH"]',
            self.source,
        )

    def test_read_only_transition_gates_precede_first_writer(self):
        first_writer = self.source.index(
            "'apply_corpus_word_anno.py'), '--write'"
        )
        required_prewrite = (
            "build_corpus_7c04_transition_review.py",
            "check_latest_kyoto_guide_transition.py",
            "build_corpus_reviewed_exact_transition.py",
            "build_bare_word_review_7c04f97.py",
            "bare_word_audit_7c04f97.py",
        )
        for script in required_prewrite:
            self.assertLess(self.source.index(script), first_writer, script)
        self.assertNotIn(
            "os.path.join(HERE, 'bare_word_audit.py'), '--require-zero'",
            self.source,
        )

    def test_boundary_and_post_generation_gates_are_ordered(self):
        boundary_manifest = self.source.index(
            "build_word_anno_boundary_manifest.py"
        )
        boundary_transition = self.source.index(
            "test_word_anno_boundary_transition.py"
        )
        phase599_apply = self.source.index(
            "'phase599_temis_context_promotion.py'),\n"
            "        'apply', '--promote'"
        )
        phase599_first_audit = self.source.index(
            "'phase599_temis_context_promotion.py'),\n"
            "        'audit', '--deployed'",
            phase599_apply,
        )
        phase600_apply = self.source.index(
            "'phase600_master_ruby_repair.py'),\n"
            "        'apply', '--batch-size'",
        )
        phase600_audit = self.source.index(
            "'phase600_master_ruby_repair.py'),\n"
            "        'audit', '--batch-size'",
        )
        phase599_reaudit = self.source.index(
            "'phase599_temis_context_promotion.py'),\n"
            "        'audit', '--deployed'",
            phase599_first_audit + 1,
        )
        first_guide = self.source.index(
            "check_latest_kyoto_guide_transition.py"
        )
        second_guide = self.source.index(
            "check_latest_kyoto_guide_transition.py", first_guide + 1
        )
        canonical = self.source.index(
            "'check_canonical_corpus_surfaces.py'"
        )
        self.assertLess(boundary_manifest, boundary_transition)
        self.assertLess(boundary_transition, phase599_apply)
        self.assertLess(phase599_apply, phase599_first_audit)
        self.assertLess(phase599_first_audit, phase600_apply)
        self.assertLess(phase600_apply, phase600_audit)
        self.assertLess(phase600_audit, phase599_reaudit)
        self.assertLess(phase599_reaudit, second_guide)
        self.assertLess(second_guide, canonical)

    def test_phase600_regression_precedes_corpus_wide_audits(self):
        phase600_test = self.source.index(
            "'test_phase600_master_ruby_repair.py'"
        )
        successor = self.source.index(
            "'run_current_corpus_no_worsening.py'"
        )
        full_master = self.source.index(
            "'run_phase597_full_master_successor.py'"
        )
        self.assertLess(phase600_test, successor)
        self.assertLess(successor, full_master)

    def test_phase597_successor_replaces_old_phase558_full_command(self):
        successor_test = self.source.index(
            "'test_phase597_full_master_successor_gate.py'"
        )
        successor = self.source.index(
            "'run_phase597_full_master_successor.py'"
        )
        self.assertLess(successor_test, successor)
        self.assertIn(
            "'--phase597-dir', phase597_candidate_dir",
            self.source,
        )
        self.assertNotIn(
            "os.path.join(HERE, 'audit_master_3lang_full_snapshot.py')",
            self.source,
        )

    def test_historical_and_successor_no_worsening_are_separate(self):
        historical = self.source.index("'run_phase558_no_worsening.py'")
        successor = self.source.index(
            "'run_current_corpus_no_worsening.py'"
        )
        self.assertLess(historical, successor)


if __name__ == "__main__":
    unittest.main()
