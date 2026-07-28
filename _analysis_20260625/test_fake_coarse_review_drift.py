# -*- coding: utf-8 -*-
import json
from pathlib import Path
import tempfile
import unittest

import audit_fake_coarse_review_drift as target


class FakeCoarseReviewDriftTest(unittest.TestCase):
    def write_fixture(self, review_entry):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        learner = root / "learner.txt"
        academic = root / "academic.txt"
        original = root / "original.txt"
        review = root / "review.json"
        learner.write_text(
            "a/bc/o:gloss##偽分解(PIV正式分解)\n",
            encoding="utf-8",
        )
        academic.write_text("abc/o:gloss\n", encoding="utf-8")
        original.write_text("ab/c/o:other gloss\n", encoding="utf-8")
        review.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "expected_entries": 1,
                    "entries": [review_entry],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return temp, learner, academic, original, review

    def base_review(self):
        return {
            "learner_line": 1,
            "surface": "abco",
            "academic_decomposition": "abc/o",
            "pejvo_decompositions": ["ab/c/o"],
            "selected_decomposition": "abc/o",
            "decision": "paired_academic",
            "reason": "test review",
        }

    def test_closed_review_is_accepted(self):
        temp, learner, academic, original, review = self.write_fixture(
            self.base_review()
        )
        self.addCleanup(temp.cleanup)
        report = target.build_report(
            learner, academic, original, review,
        )
        self.assertEqual(report["counts"]["matched_existing_reviews"], 1)
        self.assertEqual(report["counts"]["stale_reviews"], 0)
        self.assertTrue(report["review_ledger_closed"])

    def test_context_drift_is_not_double_counted_as_stale(self):
        entry = self.base_review()
        entry["academic_decomposition"] = "abcd/o"
        temp, learner, academic, original, review = self.write_fixture(entry)
        self.addCleanup(temp.cleanup)
        report = target.build_report(
            learner, academic, original, review,
        )
        self.assertEqual(
            report["counts"]["encountered_existing_reviews"], 1
        )
        self.assertEqual(report["counts"]["missing_or_drifted_reviews"], 1)
        self.assertEqual(report["counts"]["stale_reviews"], 0)
        self.assertEqual(
            report["missing_or_drifted_reviews"][0]["kind"],
            "existing_review_context_drift",
        )
        self.assertFalse(report["review_ledger_closed"])

    def test_paired_academic_must_select_academic_boundary(self):
        entry = self.base_review()
        entry["selected_decomposition"] = "ab/c/o"
        temp, learner, academic, original, review = self.write_fixture(entry)
        self.addCleanup(temp.cleanup)
        report = target.build_report(
            learner, academic, original, review,
        )
        self.assertEqual(report["counts"]["stale_reviews"], 0)
        self.assertEqual(
            report["missing_or_drifted_reviews"][0]["kind"],
            "existing_review_decision_drift",
        )
        self.assertFalse(report["review_ledger_closed"])

    def test_pejvo_choice_must_be_available(self):
        entry = self.base_review()
        entry["decision"] = "pejvo_coarse"
        entry["selected_decomposition"] = "a/b/c/o"
        temp, learner, academic, original, review = self.write_fixture(entry)
        self.addCleanup(temp.cleanup)
        report = target.build_report(
            learner, academic, original, review,
        )
        self.assertEqual(report["counts"]["stale_reviews"], 0)
        self.assertEqual(
            report["missing_or_drifted_reviews"][0]["kind"],
            "existing_review_decision_drift",
        )
        self.assertFalse(report["review_ledger_closed"])


if __name__ == "__main__":
    unittest.main()
