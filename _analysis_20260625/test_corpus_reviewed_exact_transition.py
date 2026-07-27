# -*- coding: utf-8 -*-
from __future__ import annotations

import copy
import json
import unittest
from unittest import mock

import build_corpus_reviewed_exact_transition as transition


class ReviewedExactTransitionTests(unittest.TestCase):
    def ledger(self):
        return json.loads(transition.LEDGER_PATH.read_text(encoding="utf-8"))

    def test_ledger_has_only_three_source_typo_retirements(self):
        ledger = self.ledger()
        transition.validate_ledger(ledger)
        self.assertEqual(
            {row["surface"] for row in ledger["retirements"]},
            {"bonŝanĉulo", "fronantaj", "jurnal"},
        )
        self.assertFalse(ledger["policy"]["old_residual_report_reuse"])
        self.assertTrue(
            ledger["policy"]["retain_bounded_jurnalisto_compatibility"]
        )
        self.assertTrue(
            ledger["policy"]["require_standard_ĵurnalisto_runtime"]
        )

    def test_foreign_retirement_is_rejected(self):
        ledger = self.ledger()
        ledger["retirements"].append({
            "surface": "Temis",
            "count": 6,
            "annotation_keys": [],
            "replacement_surface": "Temis",
        })
        with self.assertRaisesRegex(ValueError, "retirement closure"):
            transition.validate_ledger(ledger)

    def test_annotation_retirement_drift_is_rejected(self):
        ledger = self.ledger()
        ledger["retirements"][0]["annotation_keys"].pop()
        with self.assertRaisesRegex(ValueError, "retirement closure"):
            transition.validate_ledger(ledger)

    def test_parent_hash_is_required_before_json_use(self):
        ledger = self.ledger()
        with mock.patch.object(
            transition, "git_blob", return_value=b'{"schema_version":1}',
        ):
            with self.assertRaisesRegex(ValueError, "manifest hash"):
                transition.load_parent(ledger)

    def test_canonical_hash_is_key_order_independent(self):
        first = {"b": [2, 1], "a": {"x": "ĵurnal"}}
        second = {"a": {"x": "ĵurnal"}, "b": [2, 1]}
        self.assertEqual(
            transition.canonical_hash(first),
            transition.canonical_hash(second),
        )


if __name__ == "__main__":
    unittest.main()
