# -*- coding: utf-8 -*-
from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest
from unittest import mock

import build_corpus_reviewed_exact_evidence_transition as transition


class ReviewedExactEvidenceTransitionTests(unittest.TestCase):
    def ledger(self):
        return json.loads(transition.LEDGER_PATH.read_text(encoding="utf-8"))

    def test_ledger_closes_exactly_four_evidence_deltas(self):
        ledger = self.ledger()
        transition.validate_ledger(ledger)
        self.assertEqual(
            {row["surface"] for row in ledger["evidence_deltas"]},
            {"Chiba", "Gugyeol", "Sophia-Universitato", "Tokio"},
        )
        self.assertFalse(ledger["policy"]["runtime_rules_changed"])
        self.assertFalse(ledger["policy"]["old_residual_report_reuse"])

    def test_fifth_evidence_delta_is_rejected(self):
        ledger = self.ledger()
        ledger["evidence_deltas"].append({
            "surface": "Temis", "old_count": 1, "new_count": 2,
            "cause": "unexpected", "path_deltas": {"x.html": 1},
        })
        with self.assertRaisesRegex(ValueError, "delta closure"):
            transition.validate_ledger(ledger)

    def test_parent_hash_is_required_before_json_use(self):
        ledger = self.ledger()
        with mock.patch.object(
            transition, "git_blob", return_value=b'{"schema_version":1}',
        ):
            with self.assertRaisesRegex(ValueError, "manifest hash"):
                transition.load_parent(ledger)

    def test_semantic_projection_excludes_counts_but_not_boundaries(self):
        row = {
            "surface": "Tokio", "target": "Tokio", "typed_roles": "R",
            "signature": {"reconstruction": "Tokio", "spans": [
                {"text": "Tokio", "ruby": True},
            ]},
            "typed": "R:Tokio", "available_expected_options": ["R:Tokio"],
            "annotation_keys": {"0": "@typed:Tokio:0"},
            "count": 1, "paths": [],
        }
        count_changed = copy.deepcopy(row)
        count_changed["count"] = 2
        self.assertEqual(
            transition.row_semantics([row]),
            transition.row_semantics([count_changed]),
        )
        boundary_changed = copy.deepcopy(row)
        boundary_changed["typed_roles"] = "L"
        self.assertNotEqual(
            transition.row_semantics([row]),
            transition.row_semantics([boundary_changed]),
        )

    def test_regeneration_pipeline_retains_history_behind_successor_gate(self):
        source = (Path(__file__).parent / "regenerate_all.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn(
            "build_corpus_reviewed_exact_evidence_transition.py", source,
        )
        self.assertIn("build_corpus_source_transition_dd55318.py", source)
        self.assertIn(
            "test_corpus_reviewed_exact_evidence_transition.py", source,
        )


if __name__ == "__main__":
    unittest.main()
