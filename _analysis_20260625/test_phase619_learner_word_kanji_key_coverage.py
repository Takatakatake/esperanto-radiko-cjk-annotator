# -*- coding: utf-8 -*-
"""Regression tests for the limited Phase 619 Kanji source-coverage audit."""
from __future__ import annotations

import os
from pathlib import Path
import unittest

import audit_phase619_learner_word_kanji_key_coverage as coverage


PHASE619_DIR = Path(os.environ.get(
    "ESP_PHASE619_CANDIDATE_DIR",
    r"D:\tmp\r78_phase619_snapshot_20260729",
))


class Phase619LearnerWordKanjiCoverageTests(unittest.TestCase):
    @unittest.skipUnless(
        PHASE619_DIR.is_dir(),
        "frozen Phase 619 source directory is unavailable",
    )
    def test_frozen_direct_key_coverage(self):
        report = coverage.build_report(
            PHASE619_DIR,
            coverage.WORD_KANJI_PATH,
        )
        self.assertTrue(report["gate"])
        self.assertTrue(report["coverage_only"])
        self.assertTrue(report["direct_word_kanji_source_alignment"])
        self.assertEqual(report["covered_piece_drift"], 0)
        self.assertEqual(report["counts"], coverage.EXPECTED_COUNTS)

    @unittest.skipUnless(
        PHASE619_DIR.is_dir(),
        "frozen Phase 619 source directory is unavailable",
    )
    def test_report_does_not_overclaim_full_render_fidelity(self):
        report = coverage.build_report(
            PHASE619_DIR,
            coverage.WORD_KANJI_PATH,
        )
        self.assertFalse(
            report["full_deployed_render_fidelity_certified"]
        )
        self.assertFalse(report["per_root_rendering_evaluated"])
        self.assertFalse(report["fallback_rendering_evaluated"])
        self.assertFalse(report["literal_rendering_evaluated"])
        self.assertTrue(report["uncovered_is_not_failure"])
        self.assertFalse(report["uncovered_keys_are_defects"])

    def test_projection_matches_kanji_master_grammar_policy(self):
        metano, reason = coverage.project_line(
            "met/an/o:metano", 1,
        )
        self.assertIsNone(reason)
        self.assertEqual(metano["key"], "met/an")
        butanono, reason = coverage.project_line(
            "but/an/on/o:butanono", 2,
        )
        self.assertIsNone(reason)
        self.assertEqual(butanono["key"], "but/an")
        suffix, reason = coverage.project_line("-a:adjective", 3)
        self.assertIsNone(reason)
        self.assertEqual(suffix["key"], "")


if __name__ == "__main__":
    unittest.main()
