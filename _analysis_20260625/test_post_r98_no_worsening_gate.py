# -*- coding: utf-8 -*-
"""Tests for versioned post-R93 historical and post-R98 deployed evidence."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

import post_r93_no_worsening_gate as old_gate
import post_r98_no_worsening_gate as new_gate
import verify_post_r93_historical_evidence as historical


HERE = Path(__file__).resolve().parent


class PostR98NoWorseningGateTests(unittest.TestCase):
    def test_post_r93_evidence_remains_historical_and_byte_pinned(self):
        result = historical.validate()
        self.assertTrue(result["gate"])
        self.assertTrue(result["historical_only"])
        self.assertTrue(result["deployed_post_r98_fingerprints_not_compared"])
        self.assertEqual(result["regression_cases"], 0)
        self.assertEqual(result["changed_wrong_surfaces"], 0)

    def test_post_r98_deployed_gate_is_green(self):
        result = new_gate.validate_deployed()
        self.assertTrue(result["gate"])
        self.assertTrue(result["deployed_inputs_revalidated"])
        self.assertEqual(result["raw_cases"], 68650)
        self.assertEqual(result["resolved_cases"], 68609)
        self.assertEqual(result["surfaces"], 68559)
        self.assertEqual(result["residual_surfaces_per_language"], 10)
        self.assertEqual(result["regression_cases"], 0)
        self.assertEqual(result["changed_wrong_surfaces"], 0)
        self.assertEqual(result["trilingual_residual_mismatches"], 0)

    def test_successor_manifest_changes_only_gate_report_and_app_fingerprints(self):
        old = json.loads(old_gate.MANIFEST_PATH.read_text(encoding="utf-8"))
        new = json.loads(new_gate.MANIFEST_PATH.read_text(encoding="utf-8"))
        self.assertNotEqual(old["gate_id"], new["gate_id"])
        self.assertNotEqual(old["report"], new["report"])
        for key in (
            "schema_version", "reference_projection", "languages",
            "expected_counts", "residual_contract", "provenance_counts",
        ):
            self.assertEqual(old[key], new[key], key)
        sealed_differences = {
            key for key in old["sealed"]
            if old["sealed"][key] != new["sealed"][key]
        }
        self.assertEqual(sealed_differences, {
            "app_input_fingerprints",
            "app_input_fingerprints_sha256",
        })
        changed_inputs = set()
        for language in ("JA", "ZH", "KO"):
            old_rows = old["sealed"]["app_input_fingerprints"][language]
            new_rows = new["sealed"]["app_input_fingerprints"][language]
            self.assertEqual(set(old_rows), set(new_rows))
            for path in old_rows:
                if old_rows[path] != new_rows[path]:
                    changed_inputs.add((language, path))
        self.assertEqual(changed_inputs, {
            (
                language,
                f"Esperanto-Kanji-Ruby-{language}/app_data/置換リスト_ルビ.json",
            )
            for language in ("JA", "ZH", "KO")
        })

    def test_formal_pipeline_keeps_old_history_then_gates_post_r98(self):
        source = (HERE / "regenerate_all.py").read_text(encoding="utf-8")
        phase558 = source.index("'verify_phase558_historical_evidence.py'")
        old_test = source.index("'test_post_r93_no_worsening_gate.py'", phase558)
        old_history = source.index("'verify_post_r93_historical_evidence.py'", old_test)
        new_test = source.index("'test_post_r98_no_worsening_gate.py'", old_history)
        new_gate_position = source.index("'post_r98_no_worsening_gate.py'", new_test)
        positions = [phase558, old_test, old_history, new_test, new_gate_position]
        self.assertEqual(positions, sorted(positions))
        tail = source[old_history:]
        self.assertNotIn(
            "os.path.join(HERE, 'post_r93_no_worsening_gate.py')", tail,
        )


if __name__ == "__main__":
    unittest.main()
