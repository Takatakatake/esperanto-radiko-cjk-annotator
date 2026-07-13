# -*- coding: utf-8 -*-
"""Focused safety tests for the reviewed corpus-exact manifest builder."""
import collections
import json
from pathlib import Path
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_corpus_reviewed_exact_manifest as reviewed  # noqa: E402
import no_worsening_audit as audit  # noqa: E402


class ReviewedExactManifestTests(unittest.TestCase):
    def test_zero_residual_report_is_a_reproducible_empty_selection(self):
        report = {
            "schema_version": 1,
            "clone_content_sha256": "CORPUS",
            "surface_count": 123,
            "temp_mismatch": 0,
            "residuals": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "residual.json")
            path.write_text(json.dumps(report), encoding="utf-8")
            selected, metadata = reviewed.load_report(path, "CORPUS")

        self.assertEqual(selected, {})
        self.assertEqual(metadata["temp_mismatch"], 0)

    def test_surface_wide_rule_rejects_multiple_compatible_signatures(self):
        split = audit.signature_from_typed_parts([("radik", True), ("o", False)])
        atomic = audit.signature_from_typed_parts([("radiko", True)])
        observed = collections.Counter({split: 3, atomic: 1})
        expected = {
            audit.display_typed_parts(list(split[1])),
            audit.display_typed_parts(list(atomic[1])),
        }

        with self.assertRaisesRegex(ValueError, "surface-wide reviewed exact rule is ambiguous"):
            reviewed.select_compatible_signature("radiko", observed, expected)

    def test_report_can_explicitly_narrow_a_multi_signature_surface(self):
        split = audit.signature_from_typed_parts([("radik", True), ("o", False)])
        atomic = audit.signature_from_typed_parts([("radiko", True)])
        observed = collections.Counter({split: 1, atomic: 99})
        expected = {audit.display_typed_parts(list(split[1]))}

        signature, count, typed = reviewed.select_compatible_signature(
            "radiko", observed, expected
        )

        self.assertEqual(signature, split)
        self.assertEqual(count, 1)
        self.assertEqual(typed, next(iter(expected)))


if __name__ == "__main__":
    unittest.main()
