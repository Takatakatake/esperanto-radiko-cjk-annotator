# -*- coding: utf-8 -*-
"""Pure policy tests plus the read-only Phase 599 deployed-runtime gate."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gen_replacement import load_app_replacement_helper
import no_worsening_audit as audit
import phase599_temis_context_policy as policy
import phase599_temis_context_runtime_gate as gate


ROOT = HERE.parent


def _results(signatures: dict, annotations: dict) -> dict:
    return {
        language: {
            surface: {
                "signature": signatures[surface],
                "annotations": copy.deepcopy(
                    annotations[language][surface]
                ),
            }
            for surface in policy.combined_surfaces()
        }
        for language in policy.LANGUAGES
    }


def _precondition_results() -> dict:
    return _results(
        policy.expected_precondition_signatures(),
        policy.expected_precondition_annotations(),
    )


def _candidate_results() -> dict:
    signatures = policy.expected_precondition_signatures()
    signatures.update(policy.expected_candidate_signatures())
    return _results(signatures, policy.expected_candidate_annotations())


def _fake_output_format(rb, rt, format_type, _widths):
    if format_type != audit.FORMAT:
        raise AssertionError(format_type)
    return f'<ruby>{rb}<rt class="XXL_L">{rt}</rt></ruby>'


class Phase599TemisContextPolicyTests(unittest.TestCase):
    def test_review_is_exact_candidate_only_closed_set(self):
        review = policy.load_review()
        identity = policy.review_identity()
        self.assertEqual(policy.PHASE, 599)
        self.assertEqual(
            policy.REVIEW_PATH.name, "_phase599_temis_context_review.json"
        )
        self.assertEqual(
            tuple(entry["phrase"] for entry in review["entries"]),
            (
                "Temis tamen pri aparatoj",
                "Temis pri tre noveca",
                "Temis pri la volo",
                "Temis pri la distrikto",
                "Temis pri malnovaj",
            ),
        )
        self.assertEqual(
            tuple(entry["surface"] for entry in review["negative_cases"]),
            (
                "Temis",
                "Temiso",
                "TEMIS",
                "La diino Temis pri justeco",
                "Temis tamen bela",
                "Temis, pri justeco",
            ),
        )
        self.assertEqual(
            {
                entry["phrase"]: entry["corpus_instances"]
                for entry in review["entries"]
            },
            {
                "Temis tamen pri aparatoj": 1,
                "Temis pri tre noveca": 1,
                "Temis pri la volo": 1,
                "Temis pri la distrikto": 1,
                "Temis pri malnovaj": 2,
            },
        )
        self.assertEqual(
            sum(entry["corpus_instances"] for entry in review["entries"]), 6
        )
        self.assertEqual(review["sources"]["kyoto_corpus"]["temis_instances"], 6)
        self.assertEqual(review["scope"]["allowed_languages"], ["JA", "ZH", "KO"])
        self.assertEqual(review["scope"]["match_mode"],
                         "exact_case_sensitive_long_phrase")
        self.assertFalse(review["scope"]["generator_integration"])
        self.assertFalse(review["scope"]["filesystem_writes"])
        self.assertEqual(review["scope"]["kanji_paths"], [])
        self.assertEqual(review["expected_counts"]["kanji_files_changed"], 0)
        self.assertEqual(review["expected_counts"]["generator_files_changed"], 0)
        self.assertEqual(identity["status"], "candidate_only")
        self.assertFalse(identity["generator_integration"])

    def test_only_initial_tem_is_changes_and_tails_are_preserved(self):
        precondition = policy.expected_precondition_signatures()
        candidate = policy.expected_candidate_signatures()
        before_annotations = policy.expected_precondition_annotations()
        after_annotations = policy.expected_candidate_annotations()
        for phrase in policy.positive_phrases():
            self.assertEqual(candidate[phrase][1][:2],
                             (("Tem", True), ("is", True)))
            collapsed = audit.signature_from_typed_parts([
                ("Temis", False), *list(candidate[phrase][1][2:]),
            ])
            self.assertEqual(collapsed, precondition[phrase])
            self.assertEqual(precondition[phrase][1][0], ("Temis ", False))
            boundary_sequences = []
            rb_sequences = []
            for language in policy.LANGUAGES:
                self.assertEqual(
                    after_annotations[language][phrase][:2],
                    policy.load_review()["added_annotations"][language],
                )
                self.assertEqual(
                    after_annotations[language][phrase][2:],
                    before_annotations[language][phrase],
                )
                boundary_sequences.append(candidate[phrase])
                rb_sequences.append([
                    row["rb"]
                    for row in after_annotations[language][phrase]
                ])
            self.assertTrue(all(
                value == boundary_sequences[0]
                for value in boundary_sequences[1:]
            ))
            self.assertTrue(all(
                value == rb_sequences[0] for value in rb_sequences[1:]
            ))

    def test_negative_expectations_preserve_deployed_behavior(self):
        signatures = policy.expected_precondition_signatures()
        annotations = policy.expected_precondition_annotations()
        self.assertEqual(signatures["Temis"], ("Temis", (("Temis", False),)))
        self.assertEqual(signatures["Temiso"],
                         ("Temiso", (("Temiso", False),)))
        # Uppercase is deliberately a nonintervention guard, not an atomicity
        # assertion: the deployed runtime already renders TEM/IS.
        self.assertEqual(
            signatures["TEMIS"],
            ("TEMIS", (("TEM", True), ("IS", True))),
        )
        for language in policy.LANGUAGES:
            self.assertEqual(
                [row["rb"] for row in annotations[language]["TEMIS"]],
                ["TEM", "IS"],
            )
            self.assertEqual(annotations[language]["Temis"], [])
            self.assertEqual(annotations[language]["Temiso"], [])

    def test_review_tampering_fails_closed(self):
        mutations = []

        changed = copy.deepcopy(policy.load_review())
        changed["scope"]["generator_integration"] = True
        mutations.append(changed)

        changed = copy.deepcopy(policy.load_review())
        changed["entries"][0]["phrase"] = "Temis tamen pri"
        mutations.append(changed)

        changed = copy.deepcopy(policy.load_review())
        changed["entries"][4]["corpus_instances"] = 1
        mutations.append(changed)

        changed = copy.deepcopy(policy.load_review())
        changed["added_annotations"]["JA"][0]["rt"] = "話題"
        mutations.append(changed)

        changed = copy.deepcopy(policy.load_review())
        changed["negative_cases"].pop()
        mutations.append(changed)

        changed = copy.deepcopy(policy.load_review())
        changed["sources"]["kyoto_corpus"]["commit"] = "0" * 40
        mutations.append(changed)

        for payload in mutations:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    policy.validate_review_payload(payload)

    def test_pure_precondition_validator_accepts_and_rejects_drift(self):
        valid = _precondition_results()
        report = gate.validate_precondition_rendered_results(valid)
        self.assertTrue(report["precondition_gate"])
        self.assertEqual(report["unresolved_positive_language_cases"], 15)
        self.assertEqual(report["negative_cases"], 6)

        drifted = copy.deepcopy(valid)
        phrase = policy.positive_phrases()[0]
        drifted["JA"][phrase]["signature"] = (
            phrase, (("Tem", True), ("is", True)),
        )
        with self.assertRaises(ValueError):
            gate.validate_precondition_rendered_results(drifted)

        drifted = copy.deepcopy(valid)
        drifted["KO"]["Temis tamen bela"]["annotations"][0]["rt"] = "변경"
        with self.assertRaises(ValueError):
            gate.validate_precondition_rendered_results(drifted)

    def test_pure_candidate_validator_proves_nonintervention(self):
        before = _precondition_results()
        after = _candidate_results()
        report = gate.validate_candidate_rendered_results(after, before)
        self.assertTrue(report["candidate_runtime_gate"])
        self.assertTrue(report["negative_nonintervention"])
        self.assertEqual(report["positive_language_cases_repaired"], 15)
        self.assertEqual(report["negative_language_cases_unchanged"], 18)

        leaked = copy.deepcopy(after)
        leaked["ZH"]["Temis"]["signature"] = (
            "Temis", (("Tem", True), ("is", True)),
        )
        leaked["ZH"]["Temis"]["annotations"] = [
            {"rb": "Tem", "rt": "主题"},
            {"rb": "is", "rt": "过去"},
        ]
        with self.assertRaises(ValueError):
            gate.validate_candidate_rendered_results(leaked, before)

        tail_drift = copy.deepcopy(after)
        phrase = "Temis pri la volo"
        tail_drift["JA"][phrase]["annotations"][-1]["rt"] = "願望"
        with self.assertRaises(ValueError):
            gate.validate_candidate_rendered_results(tail_drift, before)

    def test_in_memory_payload_delta_is_exact_and_nonmutating(self):
        payload = {
            "localized_string": [[" @x@ ", " X ", " $100$ "]],
            "replacements_final_list": [[" old ", " new ", " $101$ "]],
            "replacements_list_for_2char": [["ab", "AB", "$102$"]],
        }
        original = copy.deepcopy(payload)
        candidate, rows = gate.build_candidate_payload(
            payload, "JA", _fake_output_format, {},
        )
        report = gate.validate_candidate_payload_delta(
            payload, candidate, rows, "JA",
        )
        self.assertEqual(payload, original)
        self.assertIsNot(candidate, payload)
        self.assertIs(
            candidate["localized_string"], payload["localized_string"]
        )
        self.assertIs(
            candidate["replacements_list_for_2char"],
            payload["replacements_list_for_2char"],
        )
        self.assertEqual(
            [row[0] for row in rows],
            [f" {phrase} " for phrase in policy.positive_phrases()],
        )
        self.assertNotIn(" Temis ", [row[0] for row in rows])
        self.assertNotIn(" Temis pri ", [row[0] for row in rows])
        self.assertEqual(report["candidate_rows"], 5)
        self.assertEqual(report["local_rows_changed"], 0)
        self.assertEqual(report["two_char_rows_changed"], 0)
        self.assertTrue(report["in_memory_only"])

        already_present = copy.deepcopy(payload)
        already_present["replacements_final_list"].insert(
            0, copy.deepcopy(rows[0])
        )
        with self.assertRaises(ValueError):
            gate.validate_deployed_candidate_absent(already_present)

    def test_candidate_has_no_write_or_generator_integration_hook(self):
        runtime_source = Path(gate.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "write_text(",
            "write_bytes(",
            "json.dump(",
            "atomic_json_dump",
            'open("w',
            "open('w",
        ):
            self.assertNotIn(forbidden, runtime_source)
        for relative in (
            "_analysis_20260625/gen_replacement.py",
            "_analysis_20260625/apply_confirmed_now.py",
        ):
            source = (ROOT / relative).read_text(encoding="utf-8")
            self.assertNotIn("phase599_temis_context", source)
        regeneration = (
            ROOT / "_analysis_20260625" / "regenerate_all.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn(
            "phase599_temis_context_runtime_gate.py", regeneration,
        )
        self.assertNotIn("--deployed-precondition", regeneration)

    def test_added_ruby_width_is_strictly_below_two(self):
        for language in policy.LANGUAGES:
            app = ROOT / f"Esperanto-Kanji-Ruby-{language}"
            helper = load_app_replacement_helper(app)
            widths = json.loads(
                (app / "app_data" / "char_widths.json").read_text(
                    encoding="utf-8"
                )
            )
            report = gate.validate_added_annotation_widths(
                language, helper.output_format, widths,
            )
            self.assertEqual(report["added_annotations_rendered"], 10)
            self.assertEqual(report["automatic_br_count"], 0)
            self.assertLess(report["max_effective_width_ratio"], 2.0)
            self.assertTrue(report["width_gate"])

    def test_deployed_precondition_and_in_memory_candidate_gate(self):
        current = {
            language: gate.file_sha256(gate.deployed_payload_path(language))
            for language in policy.LANGUAGES
        }
        if current != policy.EXPECTED_PAYLOAD_SHA256:
            self.skipTest(
                "candidate-only deployed gate is intentionally pre-promotion; "
                "run test_phase599_temis_context_promotion for deployed state"
            )
        report = gate.validate_deployed_in_memory_candidate(batch_size=20)
        self.assertEqual(
            report["mode"],
            "deployed_precondition_and_in_memory_candidate",
        )
        self.assertTrue(report["precondition"]["precondition_gate"])
        self.assertTrue(
            report["candidate_runtime"]["candidate_runtime_gate"]
        )
        self.assertEqual(
            report["candidate_runtime"]["positive_language_cases_repaired"],
            15,
        )
        self.assertEqual(
            report["candidate_runtime"]["negative_language_cases_unchanged"],
            18,
        )
        self.assertTrue(report["width"]["width_gate"])
        self.assertTrue(report["kanji_nonintervention_gate"])
        self.assertEqual(report["kanji_track_files_changed"], 0)
        self.assertEqual(report["filesystem_payload_writes"], 0)
        self.assertEqual(report["candidate_payloads_materialized_on_disk"], 0)
        self.assertFalse(report["generator_integration"])


if __name__ == "__main__":
    unittest.main()
