# -*- coding: utf-8 -*-
"""Closed-set and activation-aware tests for the frozen Phase 532 Ruby policy."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import adopt_phase532_no_worsening_candidate as adopter
import apply_corpus_word_anno as corpus_settings
import build_phase532_ruby_policy_review as builder
import no_worsening_audit as audit
import phase532_activation as activation
import phase532_ruby_policy as policy
import phase532_runtime_signature_gate as runtime_gate


BASELINE_DIR = Path(r"D:\tmp\esperanto_stage_20260715_phase513")
CANDIDATE_DIR = Path(r"D:\tmp\esperanto_stage_20260718_phase532_candidate")
CANDIDATE_MANIFEST = Path(r"D:\tmp\phase532_fake_coarse_reference_candidate.json")
REFERENCE_CANDIDATE = Path(
    r"D:\tmp\phase532_no_worsening_reference_candidate.json"
)


class Phase532RubyPolicyTests(unittest.TestCase):
    def test_closed_set_and_safe_track_partition(self):
        loaded = policy.load_phase532_policy()
        self.assertEqual(len(loaded["unmarked"]["entries"]), 23)
        self.assertEqual(len(loaded["fake"]["entries"]), 35)
        self.assertEqual(
            len({
                entry["learner_line"]
                for ledger in (loaded["unmarked"], loaded["fake"])
                for entry in ledger["entries"]
            }),
            58,
        )
        self.assertEqual(loaded["safe_targets"], policy.EXPECTED_SAFE_TARGETS)
        managed = policy.managed_morph_targets()
        self.assertEqual(set(managed), set(policy.EXPECTED_SAFE_TARGETS))
        self.assertEqual(
            {surface for surface, spec in managed.items()
             if "ruby_track_only" not in spec},
            {"lulu", "suprenglisi", "pasivaĵo", "pasivigi"},
        )
        self.assertEqual(
            {surface for surface, spec in managed.items()
             if spec.get("ruby_track_only") is True},
            {"neologismemo", "neologismemulo", "stenografistino"},
        )

    def test_safe7_is_connected_to_managed_settings_without_reinterpretation(self):
        expected = policy.managed_morph_targets()
        present = {
            surface: corpus_settings.MANAGED_MORPH_TARGETS[surface]
            for surface in expected
            if surface in corpus_settings.MANAGED_MORPH_TARGETS
        }
        if corpus_settings.PHASE532_FORMAL:
            self.assertEqual(present, expected)
        else:
            self.assertEqual(present, {})

    def test_safe7_typed_boundaries_are_exact(self):
        expected_spans = {
            "lulu": (("lul", True), ("u", False)),
            "suprenglisi": (
                ("supr", True), ("en", False), ("glis", True),
                ("i", False),
            ),
            "pasivaĵo": (("pasiv", True), ("aĵ", True), ("o", False)),
            "pasivigi": (("pasiv", True), ("ig", True), ("i", False)),
            "neologismemo": (
                ("neologism", True), ("em", True), ("o", False),
            ),
            "neologismemulo": (
                ("neologism", True), ("em", True), ("ul", True),
                ("o", False),
            ),
            "stenografistino": (
                ("stenograf", True), ("ist", True), ("in", True),
                ("o", False),
            ),
        }
        self.assertEqual(
            {
                surface: audit.expected_signature(reviewed["target"])[1]
                for surface, reviewed in policy.EXPECTED_SAFE_TARGETS.items()
            },
            expected_spans,
        )

    def test_selected_expression_partition_keeps_multiword_tokens(self):
        expressions = policy.selected_ruby_expressions()
        self.assertEqual(len(expressions), 58)
        self.assertEqual(len(policy.ordinary_reference_targets()), 57)
        self.assertEqual(
            expressions["ritma gimnastiko"], policy.MULTIWORD_EXPRESSION,
        )
        self.assertEqual(
            runtime_gate._expression_signature(
                expressions["ritma gimnastiko"]
            ),
            (
                "ritma gimnastiko",
                (
                    ("ritm", True), ("a ", False),
                    ("gimnastik", True), ("o", False),
                ),
            ),
        )
        self.assertNotEqual(
            audit.expected_signature("ritm/a gimnastik/o"),
            runtime_gate._expression_signature(
                expressions["ritma gimnastiko"]
            ),
        )

    def test_review_fingerprints_and_historical_bytes_are_pinned(self):
        identity = policy.review_identity()
        self.assertEqual(identity["unmarked_entries"], 23)
        self.assertEqual(identity["fake_transition_entries"], 35)
        self.assertEqual(identity["retired_historical_entries"], 1)
        historical = HERE / "_fake_coarse_transition_review.json"
        self.assertEqual(
            hashlib.sha256(historical.read_bytes()).hexdigest().upper(),
            builder.HISTORICAL_TRANSITION_SHA256,
        )

    def test_recomputed_tamper_cannot_widen_safe7(self):
        loaded = policy.load_phase532_policy()
        unmarked = copy.deepcopy(loaded["unmarked"])
        fake = copy.deepcopy(loaded["fake"])
        lulu = next(
            entry for entry in unmarked["entries"]
            if entry["surface"] == "lulu"
        )
        lulu["selected_ruby_decomposition"] = "lu/lu"
        lulu["setting"]["target"] = "lu/lu"
        unmarked["entries_sha256"] = policy.compact_sha256(
            unmarked["entries"]
        )
        with self.assertRaisesRegex(ValueError, "fingerprint drift"):
            policy.validate_policy_payloads(unmarked, fake)

    def test_source_identity_tamper_fails_closed(self):
        loaded = policy.load_phase532_policy()
        unmarked = copy.deepcopy(loaded["unmarked"])
        unmarked["sources"]["candidate_learner_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "source identity drift"):
            policy.validate_policy_payloads(unmarked, loaded["fake"])

    def test_policy_text_and_source_schema_fail_closed(self):
        loaded = policy.load_phase532_policy()
        unmarked = copy.deepcopy(loaded["unmarked"])
        unmarked["policy"] += " "
        with self.assertRaisesRegex(ValueError, "header drift"):
            policy.validate_policy_payloads(unmarked, loaded["fake"])
        unmarked = copy.deepcopy(loaded["unmarked"])
        unmarked["sources"]["unreviewed_source"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "source identity drift"):
            policy.validate_policy_payloads(unmarked, loaded["fake"])

    def test_unmarked_cannot_smuggle_fake_ledger_keys(self):
        loaded = policy.load_phase532_policy()
        unmarked = copy.deepcopy(loaded["unmarked"])
        unmarked["retired_historical_entries"] = []
        with self.assertRaisesRegex(ValueError, "unsupported.*review keys"):
            policy.validate_policy_payloads(unmarked, loaded["fake"])

    def test_strict_supersession_is_one_exact_legacy_row(self):
        self.assertEqual(policy.strict_supersessions(), {
            "lulu": {
                "w": "lulu", "target": "lulu", "typed_roles": "R",
                "exact_only": True, "boundary_only": True,
                "case_sensitive": True,
            },
        })

    def test_adopter_removes_only_lulu_and_is_idempotent(self):
        strict = json.loads(
            (HERE / "_strict_gold_reference_fixes.json").read_text(
                encoding="utf-8"
            )
        )
        available = {
            (entry["w"], adopter.typed_signature(entry))
            for entry in strict["entries"] if entry["w"] != "lulu"
        }
        projection = {
            "gold": {"sha256": policy.CANDIDATE_LEARNER_SHA256},
            "reference_sha256": adopter.PHASE532_REFERENCE_SHA256,
        }
        adopted = adopter.rebind_strict_ledger(
            copy.deepcopy(strict), projection, available,
        )
        self.assertEqual(adopted["expected_entries"], 932)
        self.assertNotIn("lulu", {entry["w"] for entry in adopted["entries"]})
        readopted = adopter.rebind_strict_ledger(
            copy.deepcopy(adopted), projection, available,
        )
        self.assertEqual(readopted, adopted)

    @unittest.skipUnless(
        REFERENCE_CANDIDATE.is_file(),
        "frozen Phase 532 references-only candidate is unavailable",
    )
    def test_adopter_candidate_requires_exact_policy_identity(self):
        candidate = json.loads(
            REFERENCE_CANDIDATE.read_text(encoding="utf-8")
        )
        adopter.validate_candidate(candidate, policy.CANDIDATE_LEARNER_SHA256)
        tampered = copy.deepcopy(candidate)
        tampered["projection"]["phase532_ruby_policy"][
            "fake_transition_entries"
        ] = 36
        tampered["scope_manifest_candidate"]["expected"] = tampered[
            "projection"
        ]
        tampered["scope_manifest_candidate"]["projection_sha256"] = (
            audit.stable_json_sha256(tampered["projection"])
        )
        with self.assertRaisesRegex(ValueError, "candidate identity changed"):
            adopter.validate_candidate(
                tampered, policy.CANDIDATE_LEARNER_SHA256,
            )

    def test_adopter_requires_57_words_and_defers_bounded_multiword(self):
        atomic_hyphens, _identity = audit.load_atomic_hyphen_review()
        cases = {}
        for index, (surface, target) in enumerate(
            adopter.ordinary_selected_policy_targets().items()
        ):
            normalized = audit.canonical(surface)
            pieces = audit.reviewed_atomic_hyphen_pieces(
                normalized, target, atomic_hyphens,
            )
            cases[index] = {
                "surface": normalized,
                "expected": target,
                "signature": audit.expected_signature(target, pieces),
                "sources": {adopter.PHASE532_REFERENCE_SOURCE: 1},
            }
        adopter.validate_phase532_reference_cases(cases)
        deduped_key = next(iter(cases))
        original_expected = cases[deduped_key]["expected"]
        cases[deduped_key]["expected"] = "earlier-html-spelling"
        adopter.validate_phase532_reference_cases(cases)
        cases[deduped_key]["expected"] = original_expected
        removed_key = next(iter(cases))
        removed_case = cases.pop(removed_key)
        with self.assertRaisesRegex(ValueError, "absent/ambiguous"):
            adopter.validate_phase532_reference_cases(cases)
        cases[removed_key] = removed_case

        # A single-word slash parser cannot represent this phrase correctly;
        # the dedicated full-runtime gate owns it and the adopter must not
        # manufacture a 58th ordinary requirement.
        cases[999] = {
            "surface": "ritma gimnastiko",
            "expected": "ritm/a gimnastik/o",
            "signature": audit.expected_signature("ritm/a gimnastik/o"),
            "sources": {adopter.PHASE532_REFERENCE_SOURCE: 1},
        }
        adopter.validate_phase532_reference_cases(cases)

    def test_runtime_signature_pre_and_post_modes_are_exact(self):
        for mode, mismatch_count in (("pre-regen", 7), ("post-regen", 0)):
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
            self.assertEqual(
                report["selected_target_mismatches"], mismatch_count,
            )
            self.assertEqual(
                report["signature_manifest_sha256"], expected_sha256,
            )

    def test_runtime_signature_gate_rejects_one_language_multiword_drift(self):
        expected, _sha256 = runtime_gate.expected_signatures("pre-regen")
        rendered = {
            language: {
                surface: {"signature": signature}
                for surface, signature in expected.items()
            }
            for language in runtime_gate.LANGUAGES
        }
        rendered["KO"]["ritma gimnastiko"] = {
            "signature": audit.expected_signature("ritm/a gimnastik/o"),
        }
        with self.assertRaisesRegex(ValueError, "runtime signature gate failed"):
            runtime_gate.validate_rendered_results(rendered, "pre-regen")

    def test_formal_pipeline_gates_before_and_after_in_memory_generation(self):
        pipeline = (HERE / "regenerate_all.py").read_text(encoding="utf-8")
        apply_source = (HERE / "apply_confirmed_now.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("phase532_runtime_signature_gate.py", pipeline)
        self.assertIn('phase532_deployed_mode = "post-regen"', pipeline)
        self.assertIn("'--mode', phase532_deployed_mode, '--deployed'", pipeline)
        self.assertIn("'--mode', 'post-regen', '--deployed'", pipeline)
        self.assertIn("build_phase532_authority_carry_forward.py", pipeline)
        self.assertIn("'--phase532-runtime-mode', 'post-regen'", pipeline)
        self.assertIn("'ESP_PHASE532_BASELINE_DIR'", pipeline)
        self.assertIn("'ESP_PHASE532_CANDIDATE_DIR'", pipeline)
        build_position = apply_source.index("_prepared_candidates =")
        gate_position = apply_source.index(
            "_phase532_runtime_report = validate_generated_payloads"
        )
        write_position = apply_source.index(
            "write_all_prepared_candidates(_prepared_candidates)"
        )
        self.assertLess(build_position, gate_position)
        self.assertLess(gate_position, write_position)
        self.assertNotIn("process('ZH', True)", apply_source)

    @unittest.skipUnless(
        all(
            (
                HERE.parent / f"Esperanto-Kanji-Ruby-{language}"
                / "app_data" / "置換リスト_ルビ.json"
            ).is_file()
            for language in runtime_gate.LANGUAGES
        ),
        "deployed JA/ZH/KO Ruby payloads are unavailable",
    )
    def test_deployed_runtime_matches_the_tracked_activation_state(self):
        active = activation.phase532_active()
        mode = "post-regen" if active else "pre-regen"
        report = runtime_gate.validate_generated_payloads(
            runtime_gate.load_deployed_payloads(), mode,
        )
        self.assertTrue(report["gate"])
        self.assertTrue(report["all_inputs_stable"])
        self.assertEqual(report["surfaces"], 58)
        self.assertEqual(
            report["selected_target_mismatches"], 0 if active else 7,
        )
        self.assertEqual(report["trilingual_mismatches"], 0)

    @unittest.skipUnless(
        BASELINE_DIR.is_dir()
        and CANDIDATE_DIR.is_dir()
        and CANDIDATE_MANIFEST.is_file(),
        "local frozen Phase 513/532 snapshots are unavailable",
    )
    def test_frozen_source_builder_integration(self):
        report = builder.validate_frozen_closure(
            BASELINE_DIR, CANDIDATE_DIR, CANDIDATE_MANIFEST,
        )
        self.assertTrue(report["gate"])
        self.assertTrue(report["all_inputs_stable"])
        self.assertEqual(report["changed_surface_union"], 58)
        self.assertEqual(report["unmarked_dispositions"], 23)
        self.assertEqual(report["fake_transitions"], 35)
        self.assertEqual(report["safe_managed_targets"], 7)
        self.assertEqual(report["retained_phase513_ruby_targets"], 51)
        self.assertEqual(report["adopted_shared_repairs"], 4)
        self.assertEqual(report["adopted_ruby_track_only_repairs"], 3)


if __name__ == "__main__":
    unittest.main()
