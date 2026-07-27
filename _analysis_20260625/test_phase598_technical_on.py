# -*- coding: utf-8 -*-
"""Closed-set tests for the Phase 598 technical-``on`` Ruby sidecar."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import apply_corpus_word_anno as corpus_settings
import no_worsening_audit as audit
import phase558_ruby_overlay_runtime_gate as phase558_runtime
import phase598_technical_on_activation as activation
import phase598_technical_on_policy as policy
import phase598_technical_on_runtime_gate as runtime_gate


PHASE597_DIR = Path(os.environ.get(
    "ESP_PHASE597_CANDIDATE_DIR",
    r"D:\tmp\esperanto_stage_20260726_phase597_audit",
))


def payload_for_signatures(signatures: dict, *, tuple_rows: bool) -> dict:
    rows = []
    for index, surface in enumerate(sorted(signatures)):
        _reconstruction, spans = signatures[surface]
        rendered = "".join(
            (
                f'<ruby>{text}<rt class="S_S">x</rt></ruby>'
                if is_ruby else text
            )
            for text, is_ruby in spans
        )
        row = [
            f" {surface} ", f" {rendered} ", f" ${8800000 + index}$ ",
        ]
        rows.append(tuple(row) if tuple_rows else row)
    return {
        "localized_string": [],
        "replacements_final_list": rows,
        "replacements_list_for_2char": [],
    }


class Phase598TechnicalOnTests(unittest.TestCase):
    def test_review_is_exact_eight_row_two_track_partition(self):
        review = policy.load_review()
        self.assertEqual(len(review["entries"]), 8)
        self.assertEqual(set(policy.managed_morph_targets()), {
            "fonono", "fotono", "gangliono", "magnetono",
            "mezono", "nukleono", "termoelektrono",
        })
        self.assertEqual(policy.typed_exact_targets(), {
            "gigaelektronvolto": {
                "target": "giga/elektron/volt/o",
                "typed_roles": "RRRL",
                "case_sensitive": True,
                "ruby_only": True,
            },
        })
        self.assertEqual(
            review["sources"]["base_app_parent"],
            {
                "commit": (
                    "4682D32496F166802B4A2CF28626F376E12AAE3E"
                ),
                "tree": "2C494DB69EBAC28EF63A192BEFA017A22710CCD7",
                "required_r71_ancestor": (
                    "2E05403756DB6A4D1081BDD0EF95ADD77C3BFA87"
                ),
            },
        )
        for spec in policy.managed_morph_targets().values():
            self.assertIs(spec["ruby_track_only"], True)
            self.assertTrue(spec["ruby_context_annotation"].startswith(
                "@phase598-ruby:technical-on:"
            ))

    def test_review_and_activation_tamper_fail_closed(self):
        review = copy.deepcopy(policy.load_review())
        review["entries"][0]["selected_ruby_target"] = "fon/on/o"
        review["entries_sha256"] = policy.compact_sha256(review["entries"])
        with self.assertRaisesRegex(ValueError, "identity drift"):
            policy.validate_review_payload(review)

        report = activation.activation_report()
        self.assertTrue(report["phase598_technical_on_active"])
        self.assertTrue(report["parent"]["phase558_ruby_overlay_active"])
        self.assertTrue(report["gate"])
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "activation.json"
            payload = json.loads(
                activation.ACTIVATION_PATH.read_text(encoding="utf-8")
            )
            payload["active"] = False
            path.write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "identity drift"):
                activation.activation_report(activation_path=path)

    def test_positive_and_strengthened_negative_closure(self):
        positive = runtime_gate.positive_surface_list()
        groups = runtime_gate.negative_surface_groups()
        negative = runtime_gate.negative_surface_list()
        self.assertEqual(len(positive), 211)
        self.assertEqual(
            {name: len(rows) for name, rows in groups.items()},
            {
                "genuine_fraction_guards": 120,
                "bare_homograph_guards": 21,
                "adjacent_technical_guards": 14,
                "exact_leakage_guards": 4,
            },
        )
        self.assertEqual(len(negative), 159)
        self.assertEqual(len(runtime_gate.combined_surface_list()), 370)
        self.assertFalse(set(positive) & set(negative))
        for surface in (
            "termoelektron", "Termoelektron", "TERMOELEKTRON",
            "Gigaelektronvolto", "GIGAELEKTRONVOLTO",
            "gigaelektronvolton", "gigaelektronvoltoj",
        ):
            self.assertIn(surface, negative)
        for surface in (
            "fotono", "fotonon", "FOTONO", "nukleono",
            "nukleonon", "gigaelektronvolto",
        ):
            self.assertIn(surface, positive)

    def test_positive_manifests_and_annotations_are_exact(self):
        signatures, signature_sha256 = (
            runtime_gate.positive_expected_signatures()
        )
        annotations, gloss_sha256 = (
            runtime_gate.positive_expected_annotations()
        )
        self.assertEqual(
            signature_sha256,
            runtime_gate.POSITIVE_SIGNATURE_MANIFEST_SHA256,
        )
        self.assertEqual(
            gloss_sha256, runtime_gate.POSITIVE_GLOSS_MANIFEST_SHA256,
        )
        self.assertEqual(
            annotations["JA"]["fotono"],
            [{"rb": "foton", "rt": "光子"}],
        )
        self.assertEqual(
            annotations["ZH"]["gangliono"],
            [{"rb": "ganglion", "rt": "淋巴结"}],
        )
        self.assertEqual(
            annotations["KO"]["gigaelektronvolto"],
            [
                {"rb": "giga", "rt": "기가"},
                {"rb": "elektron", "rt": "전자"},
                {"rb": "volt", "rt": "볼트"},
            ],
        )
        self.assertEqual(
            sum(len(rows) for rows in annotations["JA"].values()), 213,
        )
        self.assertEqual(
            signatures["fotonon"],
            audit.signature_from_typed_parts([
                ("foton", True), ("on", False),
            ]),
        )

    def test_in_memory_tuple_payload_rows_are_first_class_candidates(self):
        signatures, _digest = runtime_gate.positive_expected_signatures()
        tuple_payload = payload_for_signatures(
            signatures, tuple_rows=True,
        )
        payloads = {
            language: copy.deepcopy(tuple_payload)
            for language in runtime_gate.LANGUAGES
        }
        report = runtime_gate.validate_positive_payload_closure(payloads)
        self.assertTrue(report["positive_payload_gate"])
        self.assertEqual(
            set(report["positive_payload_rows_per_language"].values()),
            {211},
        )

        # Phase 558 uses the same in-memory generator representation.  This
        # regression prevents its pre-write gate from treating tuples as zero
        # matching rows while accepting the JSON-round-tripped list form.
        phase558_signatures, _digest = (
            phase558_runtime.payload_variant_signatures()
        )
        phase558_payload = payload_for_signatures(
            phase558_signatures, tuple_rows=True,
        )
        phase558_report = phase558_runtime.validate_payload_variant_closure({
            language: copy.deepcopy(phase558_payload)
            for language in phase558_runtime.LANGUAGES
        })
        self.assertTrue(phase558_report["payload_variant_gate"])
        self.assertEqual(
            phase558_report["expanded_payload_variants"], 63,
        )

    def test_generic_fraction_on_and_reserved_contexts_are_separate(self):
        expected_on = {
            "JA": [["on", "分数"]],
            "ZH": [["on", "分数"]],
            "KO": [["on", "분수"]],
        }
        for language in runtime_gate.LANGUAGES:
            data = json.loads(
                (
                    ROOT / f"Esperanto-Kanji-Ruby-{language}"
                    / "app_data" / "word_anno.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(data["on"], expected_on[language])
            self.assertEqual(
                data["@phase598-ruby:technical-on:foton"][0][0],
                "foton",
            )
            self.assertEqual(
                data["@typed:gigaelektronvolto:1"][0][0],
                "elektron",
            )

    def test_corpus_settings_connect_only_the_reviewed_scope(self):
        self.assertTrue(corpus_settings.PHASE598_FORMAL)
        for surface, spec in policy.managed_morph_targets().items():
            self.assertEqual(
                corpus_settings.MANAGED_MORPH_TARGETS[surface], spec,
            )
        for surface, spec in policy.typed_exact_targets().items():
            self.assertEqual(
                corpus_settings.MANAGED_TYPED_EXACT_TARGETS[surface], spec,
            )
        self.assertFalse(
            set(policy.managed_morph_targets())
            & set(policy.typed_exact_targets())
        )

    def test_expected_width_is_recomputed_below_two_without_breaks(self):
        report = runtime_gate.validate_expected_widths()
        self.assertTrue(report["width_gate"])
        self.assertTrue(report["effective_ruby_width_within_2x"])
        self.assertEqual(report["unknown_width_characters"], 0)
        self.assertEqual(report["automatic_br_count"], 0)
        self.assertLess(
            max(report["max_effective_width_ratio"].values()), 0.9,
        )
        self.assertEqual(
            report["expected_ruby_annotations_rendered"], 639,
        )

    def test_writer_runs_phase598_gate_before_first_payload_write(self):
        source = (HERE / "apply_confirmed_now.py").read_text(
            encoding="utf-8"
        )
        build_position = source.index("_prepared_candidates =")
        gate_position = source.index(
            "_phase598_runtime_report = "
            "validate_phase598_generated_payloads"
        )
        write_position = source.index(
            "write_all_prepared_candidates(_prepared_candidates)"
        )
        self.assertLess(build_position, gate_position)
        self.assertLess(gate_position, write_position)

    @unittest.skipUnless(
        (PHASE597_DIR / "learner.txt").is_file()
        and (PHASE597_DIR / "academic.txt").is_file()
        and (PHASE597_DIR / "pejvo_original.txt").is_file(),
        "frozen Phase 597 authority is unavailable",
    )
    def test_frozen_phase597_rows_and_files_match_the_review(self):
        review = policy.load_review()
        files = {
            "phase597_learner": PHASE597_DIR / "learner.txt",
            "phase597_academic": PHASE597_DIR / "academic.txt",
            "phase597_pejvo_original": PHASE597_DIR / "pejvo_original.txt",
        }
        for key, path in files.items():
            raw = path.read_bytes()
            expected = policy.EXPECTED_SOURCES[key]
            self.assertEqual(len(raw), expected["bytes"])
            self.assertEqual(
                hashlib.sha256(raw).hexdigest().upper(),
                expected["sha256"],
            )
            self.assertEqual(len(raw.decode("utf-8").splitlines()), expected["lines"])
        learner_lines = files["phase597_learner"].read_text(
            encoding="utf-8"
        ).splitlines()
        academic_lines = files["phase597_academic"].read_text(
            encoding="utf-8"
        ).splitlines()
        for entry in review["entries"]:
            index = entry["learner_line"] - 1
            self.assertEqual(learner_lines[index], entry["learner_line_text"])
            self.assertEqual(academic_lines[index], entry["academic_line_text"])


if __name__ == "__main__":
    unittest.main()
