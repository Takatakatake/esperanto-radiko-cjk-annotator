# -*- coding: utf-8 -*-
"""Closed-set tests for the five-surface Phase 558 Ruby sidecar."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import apply_corpus_word_anno as corpus_settings
import audit_master_3lang_full_snapshot as full_master_audit
import build_phase558_ruby_overlay_review as builder
import no_worsening_audit as audit
import phase558_ruby_overlay as policy
import phase558_ruby_overlay_activation as activation
import phase558_ruby_overlay_runtime_gate as runtime_gate


PHASE532_DIR = Path(os.environ.get(
    "ESP_PHASE532_CANDIDATE_DIR",
    r"D:\tmp\esperanto_stage_20260718_phase532_candidate",
))
PHASE558_DIR = Path(os.environ.get(
    "ESP_PHASE558_CANDIDATE_DIR",
    r"D:\tmp\esperanto_stage_20260721_phase558_audit",
))
DISPOSITION_LEDGER = Path(os.environ.get(
    "ESP_PHASE558_RUBY_DISPOSITION_LEDGER",
    r"D:\tmp\phase558_ruby_track_dispositions_candidate.json",
))
GUIDE_ROOT = Path(
    r"D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学"
    r"\エスペラントの漢字化プロジェクト総結集20260630"
    r"\語根分解、注釈ルビ振り、漢字化アプリ徹底ブラッシュアップ20260630"
    r"\_project_root_misc\京大エス研html文書＿Github"
    r"\esperanto_html_redaktado"
)
JAPANESE_GUIDE = Path(os.environ.get(
    "ESP_RUBY_HTML_GUIDE_JA",
    str(GUIDE_ROOT / "エスペラントルビHTML修正ガイド260328.txt"),
))
CHINESE_GUIDE = Path(os.environ.get(
    "ESP_RUBY_HTML_GUIDE_ZH",
    str(GUIDE_ROOT / "世界语HTML修正指南_中文注释版.txt"),
))


class Phase558RubyOverlayTests(unittest.TestCase):
    @staticmethod
    def _payload_for_variant_signatures(signatures):
        rows = []
        for index, surface in enumerate(sorted(signatures)):
            _reconstruction, spans = signatures[surface]
            rendered = "".join(
                (
                    f'<ruby>{text}<rt class="S">x</rt></ruby>'
                    if is_ruby else text
                )
                for text, is_ruby in spans
            )
            rows.append([
                f" {surface} ", f" {rendered} ", f" ${8000000 + index}$ ",
            ])
        return {
            "localized_string": [],
            "replacements_final_list": rows,
            "replacements_list_for_2char": [],
        }

    def test_width_css_scale_is_pinned_and_unknown_classes_fail_closed(self):
        root = HERE.parent
        for language in ("JA", "ZH", "KO"):
            observed = full_master_audit.deployed_css_class_scale(
                root / f"Esperanto-Kanji-Ruby-{language}"
            )
            self.assertEqual(observed, full_master_audit.CLASS_SCALE)
        with tempfile.TemporaryDirectory() as temporary_directory:
            app_dir = Path(temporary_directory)
            (app_dir / "esp_text_replacement_module.py").write_text(
                "rt.UNKNOWN { --ruby-font-size: 0.1em; }\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "CSS scale mapping drift"):
                full_master_audit.deployed_css_class_scale(app_dir)

    def test_closed_set_and_two_track_partition(self):
        review = policy.load_review()
        self.assertEqual(len(review["entries"]), 5)
        self.assertEqual(
            policy.selected_ruby_targets(),
            {
                "kateĥismo": "kateĥism/o",
                "kateĥisto": "kateĥist/o",
                "magnetito": "magnetit/o",
                "Izraelio": "Izrael/io",
                "tia-tia": "tia/-/tia",
            },
        )
        self.assertEqual(set(policy.managed_morph_targets()), {
            "kateĥismo", "kateĥisto",
        })
        self.assertEqual(set(policy.typed_exact_targets()), {
            "magnetito", "Izraelio", "tia-tia",
        })
        for spec in policy.managed_morph_targets().values():
            self.assertIs(spec["ruby_track_only"], True)
            self.assertTrue(spec["ruby_context_annotation"].startswith(
                "@phase558-ruby:"
            ))
        for spec in policy.typed_exact_targets().values():
            self.assertEqual(
                {key for key, value in spec.items() if value is True},
                {"case_sensitive", "ruby_only"},
            )
            self.assertIn(spec["typed_roles"], {"RL", "RLR"})

    def test_activation_requires_exact_parent_and_sidecar_identities(self):
        report = activation.activation_report()
        self.assertTrue(report["phase532_active"])
        self.assertTrue(report["phase558_ruby_overlay_active"])
        self.assertTrue(report["gate"])
        self.assertEqual(report["overlay_review"], policy.review_identity())
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

    def test_recomputed_review_tamper_fails_closed(self):
        review = copy.deepcopy(policy.load_review())
        target = next(
            entry for entry in review["entries"]
            if entry["surface"] == "magnetito"
        )
        target["selected_ruby_target"] = "magnet/it/o"
        review["entries_sha256"] = policy.compact_sha256(review["entries"])
        with self.assertRaisesRegex(ValueError, "identity drift"):
            policy.validate_review_payload(review)

    def test_source_and_policy_schema_are_pinned(self):
        review = copy.deepcopy(policy.load_review())
        review["sources"]["phase558_learner"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "identity drift"):
            policy.validate_review_payload(review)
        review = copy.deepcopy(policy.load_review())
        review["policy"] += " "
        with self.assertRaisesRegex(ValueError, "identity drift"):
            policy.validate_review_payload(review)
        review = copy.deepcopy(policy.load_review())
        review["unreviewed_scope"] = []
        with self.assertRaisesRegex(ValueError, "identity drift"):
            policy.validate_review_payload(review)

    def test_context_annotations_are_exact_and_trilingual(self):
        morph = policy.morph_context_annotations()
        self.assertEqual(set(morph), {
            "@phase558-ruby:kateĥism", "@phase558-ruby:kateĥist",
        })
        typed = policy.typed_context_glosses()
        self.assertEqual(set(typed), {
            ("magnetito", 0, "magnetit"),
            ("Izraelio", 0, "Izrael"),
            ("tia-tia", 0, "tia"),
            ("tia-tia", 2, "tia"),
        })
        for annotation in list(morph.values()) + [
            {"glosses": glosses} for glosses in typed.values()
        ]:
            self.assertEqual(set(annotation["glosses"]), {"ja", "zh", "ko"})

    def test_strict_supersession_is_one_exact_lowercase_row(self):
        self.assertEqual(policy.strict_supersessions(), {
            "tia-tia": {
                "w": "tia-tia", "target": "ti/a-/ti/a",
                "typed_roles": "RLRL", "exact_only": True,
                "boundary_only": True, "case_sensitive": True,
            },
        })

    def test_overlay_is_connected_without_changing_phase532_partition(self):
        self.assertTrue(corpus_settings.PHASE532_FORMAL)
        self.assertTrue(corpus_settings.PHASE558_FORMAL)
        for surface, spec in policy.managed_morph_targets().items():
            self.assertEqual(corpus_settings.MANAGED_MORPH_TARGETS[surface], spec)
        for surface, spec in policy.typed_exact_targets().items():
            self.assertEqual(
                corpus_settings.MANAGED_TYPED_EXACT_TARGETS[surface], spec
            )

    def test_runtime_pre_and_post_signatures_are_exact_and_trilingual(self):
        for mode in runtime_gate.MODES:
            expected, expected_sha256 = runtime_gate.expected_signatures(mode)
            rendered = {
                language: {
                    surface: {"signature": signature}
                    for surface, signature in expected.items()
                }
                for language in runtime_gate.LANGUAGES
            }
            report = runtime_gate.validate_rendered_results(rendered, mode)
            self.assertTrue(report["gate"])
            self.assertEqual(report["surfaces"], 5)
            self.assertEqual(report["trilingual_mismatches"], 0)
            self.assertEqual(
                report["signature_manifest_sha256"], expected_sha256
            )

    def test_runtime_gate_rejects_one_language_drift(self):
        expected, _digest = runtime_gate.expected_signatures("post-regen")
        rendered = {
            language: {
                surface: {"signature": signature}
                for surface, signature in expected.items()
            }
            for language in runtime_gate.LANGUAGES
        }
        rendered["KO"]["magnetito"] = {
            "signature": audit.expected_signature("magnet/it/o")
        }
        with self.assertRaisesRegex(ValueError, "runtime signature gate failed"):
            runtime_gate.validate_rendered_results(rendered, "post-regen")

    def test_productive_and_negative_scope_guard_is_closed_and_trilingual(self):
        expected, expected_sha256 = runtime_gate.scope_guard_signatures()
        self.assertEqual(len(expected), 28)
        self.assertEqual(
            set(expected) & set(policy.selected_ruby_targets()), set()
        )
        for required in (
            "kateĥismoj", "kateĥistino", "magnetita", "magnetitoj",
            "Tia-tia", "TIA-TIA", "izraelio", "IZRAELIO",
            "Izraelion", "Japanio", "monarĥio", "oligarĥio",
        ):
            self.assertIn(required, expected)
        rendered = {
            language: {
                surface: {"signature": signature}
                for surface, signature in expected.items()
            }
            for language in runtime_gate.LANGUAGES
        }
        report = runtime_gate.validate_scope_guard_results(rendered)
        self.assertTrue(report["scope_guard_gate"])
        self.assertEqual(report["scope_guard_trilingual_mismatches"], 0)
        self.assertEqual(
            report["scope_guard_signature_manifest_sha256"],
            expected_sha256,
        )
        rendered["ZH"]["magnetitoj"] = {
            "signature": audit.expected_signature("magnetit/oj")
        }
        with self.assertRaisesRegex(ValueError, "scope guard failed"):
            runtime_gate.validate_scope_guard_results(rendered)

    def test_payload_variant_closure_distinguishes_five_from_sixty_three(self):
        signatures, manifest_sha256 = runtime_gate.payload_variant_signatures()
        self.assertEqual(len(policy.selected_ruby_targets()), 5)
        self.assertEqual(len(signatures), 63)
        self.assertEqual(
            manifest_sha256, runtime_gate.PAYLOAD_VARIANT_MANIFEST_SHA256,
        )
        payload = self._payload_for_variant_signatures(signatures)
        payloads = {
            language: copy.deepcopy(payload)
            for language in runtime_gate.LANGUAGES
        }
        report = runtime_gate.validate_payload_variant_closure(payloads)
        self.assertTrue(report["payload_variant_gate"])
        self.assertEqual(report["adjudicated_source_rows"], 5)
        self.assertEqual(report["productive_payload_variants"], 60)
        self.assertEqual(report["exact_payload_variants"], 3)
        self.assertEqual(report["expanded_payload_variants"], 63)
        self.assertEqual(report["payload_variant_trilingual_mismatches"], 0)

        tampered = copy.deepcopy(payloads)
        row = next(
            row for row in tampered["KO"]["replacements_final_list"]
            if row[0].strip() == "kateĥismajn"
        )
        row[1] = ' <ruby>kateĥ<rt class="S">x</rt></ruby>ismajn '
        with self.assertRaisesRegex(ValueError, "payload variant closure failed"):
            runtime_gate.validate_payload_variant_closure(tampered)

    def test_payload_gloss_gate_rejects_same_boundary_wrong_rt(self):
        signatures, _signature_digest = runtime_gate.payload_variant_signatures()
        glosses, gloss_digest = runtime_gate.payload_variant_glosses()
        self.assertEqual(
            gloss_digest, runtime_gate.PAYLOAD_GLOSS_MANIFEST_SHA256,
        )
        rendered = {
            language: {
                surface: {
                    "signature": signatures[surface],
                    "annotations": copy.deepcopy(
                        glosses[language][surface]
                    ),
                }
                for surface in signatures
            }
            for language in runtime_gate.LANGUAGES
        }
        report = runtime_gate.validate_payload_gloss_results(rendered)
        self.assertTrue(report["payload_gloss_gate"])
        self.assertEqual(report["payload_gloss_surfaces"], 63)
        self.assertEqual(
            set(report["payload_gloss_annotations_per_language"].values()),
            {64},
        )

        # Keep the complete R/L signature and rb text unchanged; only the
        # deployed Chinese annotation is wrong.  A boundary-only gate would
        # miss this mutation, while the Phase 558 gloss gate must reject it.
        rendered["ZH"]["magnetito"]["annotations"][0]["rt"] = "错误注释"
        with self.assertRaisesRegex(ValueError, "payload gloss gate failed"):
            runtime_gate.validate_payload_gloss_results(rendered)

    def test_rendered_annotation_helper_preserves_visible_rb_and_rt(self):
        rendered = (
            ' <ruby>magnetit<rt class="XXL_L">磁鉄鉱</rt></ruby>o '
        )
        self.assertEqual(audit.rendered_ruby_annotations(rendered), [{
            "rb": "magnetit", "rt": "磁鉄鉱",
        }])

    def test_deployed_wrapper_rejects_payload_and_fingerprint_toctou(self):
        old_payloads = {
            language: {"snapshot": "old", "language": language}
            for language in runtime_gate.LANGUAGES
        }
        app_fingerprints = {
            language: {"input": language}
            for language in runtime_gate.LANGUAGES
        }
        generated_report = {
            "candidate_payload_sha256": {
                language: runtime_gate.compact_sha256(old_payloads[language])
                for language in runtime_gate.LANGUAGES
            },
            "app_input_fingerprints": copy.deepcopy(app_fingerprints),
        }

        with mock.patch.object(
            runtime_gate, "validate_generated_payloads",
            return_value=copy.deepcopy(generated_report),
        ):
            report = runtime_gate.validate_deployed_payloads(
                "post-regen", payload_loader=lambda: old_payloads,
                payload_hash_reader=lambda: {
                    language: runtime_gate.compact_sha256(
                        old_payloads[language]
                    ) for language in runtime_gate.LANGUAGES
                },
                fingerprint_reader=lambda: copy.deepcopy(app_fingerprints),
            )
        self.assertTrue(report["deployed_snapshot_revalidated"])

        changed_payloads = copy.deepcopy(old_payloads)
        changed_payloads["KO"]["snapshot"] = "changed-after-load"
        with mock.patch.object(
            runtime_gate, "validate_generated_payloads",
            return_value=copy.deepcopy(generated_report),
        ):
            with self.assertRaisesRegex(ValueError, "load/render/reload"):
                runtime_gate.validate_deployed_payloads(
                    "post-regen", payload_loader=lambda: old_payloads,
                    payload_hash_reader=lambda: {
                        language: runtime_gate.compact_sha256(
                            changed_payloads[language]
                        ) for language in runtime_gate.LANGUAGES
                    },
                    fingerprint_reader=lambda: copy.deepcopy(app_fingerprints),
                )

        changed_fingerprints = copy.deepcopy(app_fingerprints)
        changed_fingerprints["JA"]["input"] = "changed-after-render"
        with mock.patch.object(
            runtime_gate, "validate_generated_payloads",
            return_value=copy.deepcopy(generated_report),
        ):
            with self.assertRaisesRegex(ValueError, "load/render/reload"):
                runtime_gate.validate_deployed_payloads(
                    "post-regen", payload_loader=lambda: old_payloads,
                    payload_hash_reader=lambda: {
                        language: runtime_gate.compact_sha256(
                            old_payloads[language]
                        ) for language in runtime_gate.LANGUAGES
                    },
                    fingerprint_reader=lambda: changed_fingerprints,
                )

    def test_runtime_signature_type_is_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "runtime span"):
            runtime_gate._normalize_signature((
                "magnetito", (("magnetit", "false"), ("o", False)),
            ))

    def test_writer_gates_overlay_candidate_before_first_write(self):
        source = (HERE / "apply_confirmed_now.py").read_text(encoding="utf-8")
        corpus_source = (HERE / "apply_corpus_word_anno.py").read_text(
            encoding="utf-8"
        )
        build_position = source.index("_prepared_candidates =")
        gate_position = source.index(
            "_phase558_runtime_report = validate_phase558_generated_payloads"
        )
        write_position = source.index(
            "write_all_prepared_candidates(_prepared_candidates)"
        )
        self.assertLess(build_position, gate_position)
        self.assertLess(gate_position, write_position)
        self.assertIn(".phase558_staged", source)
        self.assertIn(".phase558_rollback", source)
        self.assertNotIn(
            "write_prepared_candidate(_prepared_candidates[_key])", source
        )
        self.assertIn("transactional_json_writes(pending_writes)", corpus_source)
        self.assertIn(".phase558_staged", corpus_source)
        self.assertIn(".phase558_rollback", corpus_source)

    def test_repeat_pipeline_closes_sources_prewrite_postfix_and_full_audit(self):
        pipeline = (HERE / "regenerate_all.py").read_text(encoding="utf-8")
        full_audit = (HERE / "audit_master_3lang_full_snapshot.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("ESP_PHASE558_CANDIDATE_DIR", pipeline)
        self.assertIn("ESP_PHASE558_RUBY_DISPOSITION_LEDGER", pipeline)
        self.assertIn("ESP_RUBY_HTML_GUIDE_JA", pipeline)
        self.assertIn("ESP_RUBY_HTML_GUIDE_ZH", pipeline)
        self.assertGreaterEqual(
            pipeline.count("phase558_ruby_overlay_runtime_gate.py"), 2
        )
        first_gate = pipeline.index("phase558_ruby_overlay_runtime_gate.py")
        first_writer = pipeline.index("apply_corpus_word_anno.py")
        fixer = pipeline.index("fix_ruby_postregen.py")
        second_gate = pipeline.index(
            "phase558_ruby_overlay_runtime_gate.py", first_gate + 1
        )
        self.assertLess(first_gate, first_writer)
        self.assertLess(fixer, second_gate)
        for flag in (
            "--phase558-candidate-dir",
            "--phase558-ruby-disposition-ledger",
            "--phase558-japanese-guide",
            "--phase558-chinese-guide",
            "--phase558-runtime-mode",
        ):
            self.assertIn(flag, pipeline)
            self.assertIn(flag, full_audit)
        self.assertIn("ruby_overlay_adoption_authorized", full_audit)
        self.assertIn("master_candidate_promotion_authorized", full_audit)
        self.assertIn("master_candidate_promotion_blockers", full_audit)
        self.assertIn("effective_ruby_width_within_2x", full_audit)
        self.assertIn('phase558_signature_report["payload_gloss_gate"]', full_audit)

    @unittest.skipUnless(
        PHASE532_DIR.is_dir() and PHASE558_DIR.is_dir()
        and DISPOSITION_LEDGER.is_file()
        and JAPANESE_GUIDE.is_file() and CHINESE_GUIDE.is_file(),
        "frozen Phase 532/558 sources and guide authorities are unavailable",
    )
    def test_frozen_source_closure_selects_only_five_of_eighty_five(self):
        report = builder.validate_frozen_closure(
            PHASE532_DIR, PHASE558_DIR, DISPOSITION_LEDGER,
            JAPANESE_GUIDE, CHINESE_GUIDE,
        )
        self.assertTrue(report["gate"])
        self.assertTrue(report["inputs_stable"])
        self.assertEqual(report["learner_changed_rows"], 87)
        self.assertEqual(report["academic_changed_rows"], 4)
        self.assertEqual(report["changed_surfaces"], 85)
        self.assertEqual(len(report["selected_entries"]), 5)
        self.assertFalse(report["master_candidate_promotion_gate"])
        self.assertTrue(report["master_candidate_promotion_blockers"])
        self.assertEqual(report["disposition_surfaces"], 143)
        self.assertEqual(report["phase558_delta_authority_surfaces"], 85)
        self.assertEqual(report["selected_authority_surfaces"], 5)
        self.assertEqual(report["keep_coarse_authority_surfaces"], 2)

    @unittest.skipUnless(
        PHASE532_DIR.is_dir() and PHASE558_DIR.is_dir()
        and DISPOSITION_LEDGER.is_file()
        and JAPANESE_GUIDE.is_file() and CHINESE_GUIDE.is_file(),
        "frozen Phase 532/558 sources and guide authorities are unavailable",
    )
    def test_frozen_source_mutation_after_read_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary = Path(temporary_directory)
            copied_dirs = {
                "phase532": temporary / "phase532",
                "phase558": temporary / "phase558",
            }
            for directory in copied_dirs.values():
                directory.mkdir()
            for phase, source_dir in (
                ("phase532", PHASE532_DIR), ("phase558", PHASE558_DIR),
            ):
                for track in ("learner", "academic"):
                    expected = policy.EXPECTED_SOURCES[f"{phase}_{track}"]
                    source = builder.find_bound_file(source_dir, expected)
                    shutil.copy2(source, copied_dirs[phase] / source.name)
            ledger = temporary / DISPOSITION_LEDGER.name
            japanese = temporary / JAPANESE_GUIDE.name
            chinese = temporary / CHINESE_GUIDE.name
            shutil.copy2(DISPOSITION_LEDGER, ledger)
            shutil.copy2(JAPANESE_GUIDE, japanese)
            shutil.copy2(CHINESE_GUIDE, chinese)
            mutable = builder.find_bound_file(
                copied_dirs["phase558"],
                policy.EXPECTED_SOURCES["phase558_learner"],
            )
            original_changed_rows = builder.changed_rows
            calls = 0

            def mutate_after_first_parse(old, new):
                nonlocal calls
                rows = original_changed_rows(old, new)
                calls += 1
                if calls == 1:
                    mutable.write_bytes(mutable.read_bytes() + b"\n")
                return rows

            with mock.patch.object(
                builder, "changed_rows", side_effect=mutate_after_first_parse,
            ):
                with self.assertRaisesRegex(ValueError, "source changed"):
                    builder.validate_frozen_closure(
                        copied_dirs["phase532"], copied_dirs["phase558"],
                        ledger, japanese, chinese,
                    )


if __name__ == "__main__":
    unittest.main()
