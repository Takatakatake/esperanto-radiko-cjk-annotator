# -*- coding: utf-8 -*-
"""Closed-set tests for the seven Phase 619 ordinary-word Ruby repairs."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import apply_corpus_word_anno as corpus_settings
import build_phase619_ordinary_ruby_review as review_builder
import no_worsening_audit as audit
import phase619_ordinary_ruby_activation as activation
import phase619_ordinary_ruby_policy as policy
import phase619_ordinary_ruby_runtime_gate as runtime_gate


PHASE597_DIR = Path(os.environ.get(
    "ESP_PHASE597_CANDIDATE_DIR",
    r"D:\fuyou\20260728_tmp\esperanto_stage_20260726_phase597_audit",
))
PHASE619_DIR = Path(os.environ.get(
    "ESP_PHASE619_CANDIDATE_DIR",
    r"D:\tmp\r78_phase619_snapshot_20260729",
))
GUIDE_DIR = Path(os.environ.get(
    "ESP_KYOTO_GUIDE_DIR",
    (
        r"D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学"
        r"\Esperanto_HTML文書\京大エス研html文書＿Github"
        r"\esperanto_html_redaktado"
    ),
))
JAPANESE_GUIDE = Path(os.environ.get(
    "ESP_RUBY_HTML_GUIDE_JA",
    str(GUIDE_DIR / "エスペラントルビHTML修正ガイド260328.txt"),
))
CHINESE_GUIDE = Path(os.environ.get(
    "ESP_RUBY_HTML_GUIDE_ZH",
    str(GUIDE_DIR / "世界语HTML修正指南_中文注释版.txt"),
))


def payload_for_signatures(signatures: dict) -> dict:
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
        rows.append((
            f" {surface} ", f" {rendered} ", f" ${8900000 + index}$ ",
        ))
    return {
        "localized_string": [],
        "replacements_final_list": rows,
        "replacements_list_for_2char": [],
    }


def synthetic_rendered_results() -> dict:
    signatures, _digest = runtime_gate.positive_expected_signatures()
    annotations, _digest = runtime_gate.positive_expected_annotations()
    results = {language: {} for language in runtime_gate.LANGUAGES}
    for language in runtime_gate.LANGUAGES:
        for surface, signature in signatures.items():
            results[language][surface] = {
                "signature": signature,
                "annotations": copy.deepcopy(
                    annotations[language][surface]
                ),
            }
        for surface in runtime_gate.negative_surface_list():
            results[language][surface] = {
                "signature": audit.signature_from_typed_parts([
                    (surface, False),
                ]),
                "annotations": [],
            }
    return results


class Phase619OrdinaryRubyTests(unittest.TestCase):
    def test_review_is_exact_seven_row_two_track_partition(self):
        review = policy.load_review()
        self.assertEqual(len(review["entries"]), 7)
        self.assertEqual(policy.selected_ruby_targets(), {
            "imperialisto": "imperialist/o",
            "provincialismo": "provincialism/o",
            "endoskopio": "endoskopi/o",
            "mikroskopio": "mikroskopi/o",
            "mukozaĵo": "mukoz/aĵ/o",
            "ditionato": "ditionat/o",
            "tetrationato": "tetrationat/o",
        })
        self.assertEqual(
            sum(
                row["setting"]["kind"]
                == "productive_atomic_ruby_morph"
                for row in review["entries"]
            ),
            6,
        )
        self.assertEqual(
            sum(
                row["setting"]["kind"]
                == "productive_split_ruby_morph"
                for row in review["entries"]
            ),
            1,
        )
        self.assertTrue(all(
            row["setting"]["ruby_track_only"] is True
            for row in review["entries"]
        ))
        self.assertEqual(review["expected_counts"]["proper_name_changes"], 0)

    def test_review_and_activation_tamper_fail_closed(self):
        review = copy.deepcopy(policy.load_review())
        review["entries"][0]["selected_ruby_target"] = "imperial/ist/o"
        review["entries_sha256"] = policy.compact_sha256(review["entries"])
        with self.assertRaisesRegex(ValueError, "identity drift"):
            policy.validate_review_payload(review)

        report = activation.activation_report()
        self.assertTrue(report["phase619_ordinary_ruby_active"])
        self.assertTrue(report["parent"]["phase598_technical_on_active"])
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

    def test_positive_and_nonfreezing_negative_closure(self):
        positive = runtime_gate.positive_surface_list()
        groups = runtime_gate.negative_surface_groups()
        negative = runtime_gate.negative_surface_list()
        self.assertEqual(len(positive), 210)
        self.assertEqual(
            {name: len(rows) for name, rows in groups.items()},
            {
                "bare_stem_guards": 21,
                "left_boundary_guards": 7,
                "right_boundary_guards": 7,
                "derivational_leakage_guards": 7,
                "adjacent_ordinary_guards": 22,
            },
        )
        self.assertEqual(len(negative), 64)
        self.assertEqual(len(runtime_gate.combined_surface_list()), 274)
        self.assertFalse(set(positive) & set(negative))
        for surface in (
            "imperialisto", "Imperialiston", "IMPERIALISTOJN",
            "mukozaĵo", "MUKOZAĴAJN", "tetrationata",
        ):
            self.assertIn(surface, positive)
        for surface in (
            "imperialist", "ximperialisto", "imperialistox",
            "mukozaĵeto", "ditionito", "tetrafluorido",
        ):
            self.assertIn(surface, negative)

    def test_positive_signatures_glosses_and_split_are_exact(self):
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
            gloss_sha256,
            runtime_gate.POSITIVE_GLOSS_MANIFEST_SHA256,
        )
        self.assertEqual(
            signatures["mukozaĵo"],
            audit.signature_from_typed_parts([
                ("mukoz", True), ("aĵ", True), ("o", False),
            ]),
        )
        self.assertEqual(
            annotations["JA"]["mukozaĵo"],
            [
                {"rb": "mukoz", "rt": "粘膜"},
                {"rb": "aĵ", "rt": "事物"},
            ],
        )
        self.assertEqual(
            annotations["ZH"]["ditionato"],
            [{"rb": "ditionat", "rt": "连二硫酸盐"}],
        )
        self.assertEqual(
            annotations["KO"]["IMPERIALISTO"],
            [{"rb": "IMPERIALIST", "rt": "제국주의자"}],
        )
        self.assertEqual(
            {
                language: sum(
                    len(rows) for rows in annotations[language].values()
                )
                for language in runtime_gate.LANGUAGES
            },
            {"JA": 240, "ZH": 240, "KO": 240},
        )

    def test_negative_gate_blocks_only_sidecar_leakage(self):
        results = synthetic_rendered_results()
        report = runtime_gate.validate_rendered_results(results)
        self.assertTrue(report["gate"])
        self.assertFalse(report["negative_parse_or_gloss_frozen"])

        # An unrelated technical parse may improve later without repinning
        # this Phase 619 gate, provided all three languages retain one
        # structural boundary.
        for language in runtime_gate.LANGUAGES:
            results[language]["ditionito"] = {
                "signature": audit.signature_from_typed_parts([
                    ("ditionit", True), ("o", False),
                ]),
                "annotations": [
                    {"rb": "ditionit", "rt": f"{language}-future"},
                ],
            }
        report = runtime_gate.validate_rendered_results(results)
        self.assertTrue(report["gate"])

        leaked = runtime_gate.forbidden_negative_annotation_sequences("JA")[0]
        results["JA"]["ximperialisto"]["annotations"] = [
            {"rb": rb, "rt": rt} for rb, rt in leaked
        ]
        with self.assertRaisesRegex(ValueError, "negative/non-leakage"):
            runtime_gate.validate_rendered_results(results)

        # Exercise leakage detection itself, not merely the independent
        # trilingual-rb guard: inject each language's localized form while
        # retaining the same rb sequence and signature in all three.
        results = synthetic_rendered_results()
        for language in runtime_gate.LANGUAGES:
            leaked = (
                runtime_gate.forbidden_negative_annotation_sequences(
                    language
                )[0]
            )
            results[language]["ximperialisto"]["annotations"] = [
                {"rb": rb, "rt": rt} for rb, rt in leaked
            ]
        with self.assertRaisesRegex(
            ValueError,
            r"negative/non-leakage.*ximperialisto",
        ):
            runtime_gate.validate_rendered_results(results)

    def test_deployed_wrapper_rejects_post_render_input_drift(self):
        payload_hashes = {
            language: f"{language}-payload"
            for language in runtime_gate.LANGUAGES
        }
        fingerprints = {
            language: {f"{language}-input": f"{language}-sha"}
            for language in runtime_gate.LANGUAGES
        }
        generated_report = {
            "candidate_payload_sha256": payload_hashes,
            "app_input_fingerprints": fingerprints,
        }
        with mock.patch.object(
            runtime_gate,
            "validate_generated_payloads",
            return_value=copy.deepcopy(generated_report),
        ):
            report = runtime_gate.validate_deployed_payloads(
                payload_loader=lambda: {"synthetic": True},
                payload_hash_reader=lambda: copy.deepcopy(payload_hashes),
                fingerprint_reader=lambda: copy.deepcopy(fingerprints),
            )
            self.assertTrue(report["deployed_snapshot_revalidated"])

            changed_payloads = copy.deepcopy(payload_hashes)
            changed_payloads["JA"] = "changed"
            with self.assertRaisesRegex(
                ValueError, "changed across load/render/reload",
            ):
                runtime_gate.validate_deployed_payloads(
                    payload_loader=lambda: {"synthetic": True},
                    payload_hash_reader=lambda: changed_payloads,
                    fingerprint_reader=lambda: copy.deepcopy(fingerprints),
                )

            changed_fingerprints = copy.deepcopy(fingerprints)
            changed_fingerprints["KO"]["KO-input"] = "changed"
            with self.assertRaisesRegex(
                ValueError, "changed across load/render/reload",
            ):
                runtime_gate.validate_deployed_payloads(
                    payload_loader=lambda: {"synthetic": True},
                    payload_hash_reader=lambda: copy.deepcopy(payload_hashes),
                    fingerprint_reader=lambda: changed_fingerprints,
                )

    def test_in_memory_tuple_payload_rows_are_first_class_candidates(self):
        signatures, _digest = runtime_gate.positive_expected_signatures()
        tuple_payload = payload_for_signatures(signatures)
        report = runtime_gate.validate_positive_payload_closure({
            language: copy.deepcopy(tuple_payload)
            for language in runtime_gate.LANGUAGES
        })
        self.assertTrue(report["positive_payload_gate"])
        self.assertEqual(
            set(report["positive_payload_rows_per_language"].values()),
            {210},
        )

    def test_expected_width_is_recomputed_below_two_without_breaks(self):
        report = runtime_gate.validate_expected_widths()
        self.assertTrue(report["width_gate"])
        self.assertTrue(report["effective_ruby_width_within_2x"])
        self.assertEqual(report["unknown_width_characters"], 0)
        self.assertEqual(report["automatic_br_count"], 0)
        self.assertLess(
            max(report["max_effective_width_ratio"].values()), 1.0,
        )
        self.assertEqual(
            report["expected_ruby_annotations_rendered"], 720,
        )

    def test_corpus_settings_connect_only_the_reviewed_ruby_scope(self):
        self.assertTrue(corpus_settings.PHASE619_FORMAL)
        for surface, spec in policy.managed_morph_targets().items():
            self.assertEqual(
                corpus_settings.MANAGED_MORPH_TARGETS[surface], spec,
            )
        for language in ("JA", "ZH", "KO"):
            data = json.loads(
                (
                    ROOT / f"Esperanto-Kanji-Ruby-{language}"
                    / "app_data" / "word_anno.json"
                ).read_text(encoding="utf-8")
            )
            for key in policy.morph_context_annotations():
                self.assertIn(key, data)
            self.assertIn("mukoz/aĵ", data)

    def test_writer_runs_phase619_gate_before_first_payload_write(self):
        source = (HERE / "apply_confirmed_now.py").read_text(
            encoding="utf-8"
        )
        build_position = source.index("_prepared_candidates =")
        gate_position = source.index(
            "_phase619_runtime_report = "
            "validate_phase619_generated_payloads"
        )
        write_position = source.index(
            "write_all_prepared_candidates(_prepared_candidates)"
        )
        self.assertLess(build_position, gate_position)
        self.assertLess(gate_position, write_position)

    def test_formal_regeneration_replays_and_rechecks_phase619(self):
        source = (HERE / "regenerate_all.py").read_text(encoding="utf-8")
        self.assertNotIn("phase598_parent_payload_delta_gate.py", source)
        self.assertNotIn("port_phase600_glosses.py", source)
        builder = source.index("build_phase619_ordinary_ruby_review.py")
        pre_gate = source.index(
            "phase619_ordinary_ruby_runtime_gate.py",
            builder,
        )
        capture = source.index(
            "preserve_r67_r68_ruby_overlays.py",
            pre_gate,
        )
        generator = source.index("apply_confirmed_now.py", capture)
        restore = source.index(
            "'apply', '--input', R67_R68_OVERLAY_SNAPSHOT",
            generator,
        )
        r81 = source.index("fix_ruby_kyodai_meaning_break.py", restore)
        r85 = source.index("fix_ruby_hyphen_joiner.py", r81)
        r86 = source.index("fix_ruby_zhko_diminutive_gloss.py", r85)
        final_audit = source.index(
            "'audit', '--expected-global-rows', '572729'",
            r86,
        )
        post_gate = source.index(
            "phase619_ordinary_ruby_runtime_gate.py",
            pre_gate + 1,
        )
        full_audit = source.index(
            "'phase619_learner'",
            post_gate,
        )
        positions = [
            builder, pre_gate, capture, generator, restore,
            r81, r85, r86, final_audit, post_gate, full_audit,
        ]
        self.assertEqual(
            positions,
            sorted(positions),
        )
        self.assertIn(
            "'apply', '--input', R67_R68_OVERLAY_SNAPSHOT,\n"
            "        '--expected-global-rows', '572713'",
            source,
        )

    @unittest.skipUnless(
        PHASE597_DIR.is_dir()
        and PHASE619_DIR.is_dir()
        and JAPANESE_GUIDE.is_file()
        and CHINESE_GUIDE.is_file(),
        "frozen Phase 597/619 authorities or current guides unavailable",
    )
    def test_frozen_phase597_to_619_rows_and_guides_match(self):
        report = review_builder.validate_frozen_closure(
            PHASE597_DIR,
            PHASE619_DIR,
            JAPANESE_GUIDE,
            CHINESE_GUIDE,
        )
        self.assertTrue(report["gate"])
        self.assertTrue(report["inputs_stable"])
        self.assertEqual(report["ordinary_entries"], 7)
        self.assertEqual(report["proper_name_changes"], 0)
        self.assertEqual(
            report["review_identity"], policy.review_identity(),
        )


if __name__ == "__main__":
    unittest.main()
