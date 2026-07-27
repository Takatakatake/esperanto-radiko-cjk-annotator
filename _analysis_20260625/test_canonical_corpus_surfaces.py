# -*- coding: utf-8 -*-
"""Lightweight pure-function tests for the canonical corpus runtime gate."""
import collections
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import check_canonical_corpus_surfaces as gate
import no_worsening_audit as audit


class CanonicalCorpusSurfaceGateTests(unittest.TestCase):
    def test_ruby_scope_matches_pinned_corpus_manifest(self):
        manifest = json.loads(
            (HERE / "_corpus_exact_app_manifest.json").read_text(encoding="utf-8")
        )
        source = manifest["source"]
        self.assertEqual(gate.EXPECTED_SCOPE["content_files"], source["content_files"])
        self.assertEqual(gate.EXPECTED_SCOPE["raw_ruby"], source["raw_ruby"])
        self.assertEqual(gate.EXPECTED_SCOPE["parsed_ruby"], source["parsed_ruby"])
        self.assertEqual(gate.EXPECTED_SCOPE["parsed_units"], source["parsed_units"])
        reviewed = json.loads(
            (HERE / "_corpus_reviewed_exact_app_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            gate.EXPECTED_SCOPE["reviewed_overrides"],
            reviewed["counts"]["exact_surfaces"],
        )

    def test_reviewed_override_narrows_observed_options(self):
        split = audit.signature_from_typed_parts([
            ("radik", True), ("o", False),
        ])
        atomic = audit.signature_from_typed_parts([("radiko", True)])
        cases = {
            "radiko": {
                "options": collections.Counter({split: 2, atomic: 1}),
                "instances": 3,
            },
        }
        gate.apply_reviewed_overrides(cases, [{
            "surface": "radiko",
            "signature": audit.signature_payload(split),
        }])
        self.assertEqual(set(cases["radiko"]["options"]), {split})

    def test_reviewed_override_outside_scope_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "outside canonical corpus scope"):
            gate.apply_reviewed_overrides({}, [{
                "surface": "mankanta",
                "signature": audit.signature_payload(
                    audit.signature_from_typed_parts([("mankanta", True)])
                ),
            }])

    def test_rendered_surface_checks_structure_visible_and_placeholder(self):
        expected = audit.signature_from_typed_parts([
            ("radik", True), ("o", False),
        ])
        good = "<ruby>radik<rt>root</rt></ruby>o"
        result = gate.inspect_rendered_surface("radiko", good, {expected})
        self.assertTrue(result["pass"])

        wrong_structure = "<ruby>radiko<rt>root</rt></ruby>"
        result = gate.inspect_rendered_surface(
            "radiko", wrong_structure, {expected},
        )
        self.assertFalse(result["structure_ok"])
        self.assertFalse(result["pass"])

        result = gate.inspect_rendered_surface(
            "radiko", good + "$123$", {expected},
        )
        self.assertTrue(result["placeholder"])
        self.assertFalse(result["pass"])

    def test_scope_change_fails_closed(self):
        scope = dict(gate.EXPECTED_SCOPE)
        gate.validate_scope(scope)
        scope["canonical_surfaces"] -= 1
        with self.assertRaisesRegex(ValueError, "scope changed"):
            gate.validate_scope(scope)

    def test_contextual_exception_authority_is_closed(self):
        authority = gate.load_contextual_exceptions()
        self.assertEqual(authority["languages"], ["JA", "ZH", "KO"])
        self.assertEqual(len(authority["exceptions"]), 1)
        exception = authority["exceptions"][0]
        self.assertEqual(exception["surface"], "Temis")
        self.assertEqual(exception["corpus_expected_typed"], "R:Tem|R:is")
        self.assertEqual(exception["isolated_runtime_typed"], "L:Temis")
        self.assertFalse(
            exception["resolution"]["global_surface_rule_added"]
        )

    def test_only_exact_temis_residual_is_contextually_admitted(self):
        expected = audit.signature_from_typed_parts([
            ("Tem", True), ("is", True),
        ])
        cases = {
            "Temis": {
                "options": collections.Counter({expected: 6}),
                "instances": 6,
            },
        }
        residual = {
            "surface": "Temis",
            "instances": 6,
            "actual": "L:Temis",
            "expected": ["R:Tem|R:is"],
        }
        results = [
            {
                "language": language,
                "residual_surfaces": 1,
                "residual_instances": 6,
                "visible_failures": 0,
                "placeholder_residual_surfaces": 0,
                "residuals": [dict(residual)],
                "pass": False,
            }
            for language in ("JA", "ZH", "KO")
        ]
        promotion = {
            "promotion_audit_gate": True,
            "post_promotion_global_rows_per_language": 572506,
            "managed_rows_per_language": {"JA": 5, "ZH": 5, "KO": 5},
            "kanji_nonintervention": True,
        }
        report = gate.admit_contextual_residuals(
            results,
            cases,
            gate.load_contextual_exceptions(),
            promotion,
        )
        self.assertTrue(report["gate"])
        self.assertEqual(report["admitted_language_surfaces"], 3)
        self.assertEqual(report["unadmitted_language_surfaces"], 0)
        self.assertTrue(all(result["pass"] for result in results))
        self.assertTrue(all(not result["residuals"] for result in results))

        drifted = json.loads(json.dumps(results))
        drifted[0]["raw_residuals"][0]["surface"] = "Temiso"
        with self.assertRaisesRegex(ValueError, "residual drift"):
            gate.admit_contextual_residuals(
                drifted,
                cases,
                gate.load_contextual_exceptions(),
                promotion,
            )

        promotion["promotion_audit_gate"] = False
        with self.assertRaisesRegex(ValueError, "lacks deployed"):
            gate.admit_contextual_residuals(
                results,
                cases,
                gate.load_contextual_exceptions(),
                promotion,
            )


if __name__ == "__main__":
    unittest.main()
