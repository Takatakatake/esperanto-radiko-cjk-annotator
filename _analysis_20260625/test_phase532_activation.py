# -*- coding: utf-8 -*-
"""Activation and post-adoption simulation for the Phase 532 formal path."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import adopt_phase532_no_worsening_candidate as adopter
import audit_master_3lang_full_snapshot as full_audit
import build_phase532_authority_carry_forward as carry_builder
import build_phase532_ruby_policy_review as policy_builder
import no_worsening_audit as no_worsening
import phase532_activation as activation
import phase532_ruby_policy as policy


BASELINE_DIR = Path(r"D:\tmp\esperanto_stage_20260715_phase513")
CANDIDATE_DIR = Path(r"D:\tmp\esperanto_stage_20260718_phase532_candidate")
CANDIDATE_MANIFEST = Path(
    r"D:\tmp\phase532_fake_coarse_reference_candidate.json"
)
REFERENCE_CANDIDATE = Path(
    r"D:\tmp\phase532_no_worsening_reference_candidate.json"
)


def phase532_strict_payload() -> dict:
    strict = json.loads(activation.STRICT_PATH.read_text(encoding="utf-8"))
    entries = [entry for entry in strict["entries"] if entry["w"] != "lulu"]
    if adopter.compact_sha256(entries) != (
        adopter.PHASE532_STRICT_ENTRIES_SHA256
    ):
        raise AssertionError("test strict Phase 532 derivation drifted")
    strict.update({
        "gold_sha256": policy.CANDIDATE_LEARNER_SHA256,
        "reference_sha256": adopter.PHASE532_REFERENCE_SHA256,
        "expected_entries": 932,
        "entries_sha256": adopter.PHASE532_STRICT_ENTRIES_SHA256,
        "entries": entries,
    })
    return strict


class Phase532ActivationTests(unittest.TestCase):
    def test_current_phase532_state_is_active_and_safe_seven_are_present(self):
        report = activation.activation_report()
        self.assertTrue(report["phase532_active"])
        import apply_corpus_word_anno as corpus

        self.assertTrue(corpus.PHASE532_FORMAL)
        self.assertEqual(
            {
                surface: corpus.MANAGED_MORPH_TARGETS[surface]
                for surface in policy.managed_morph_targets()
            },
            policy.managed_morph_targets(),
        )

    @unittest.skipUnless(
        REFERENCE_CANDIDATE.is_file() and CANDIDATE_MANIFEST.is_file(),
        "frozen Phase 532 adoption files unavailable",
    )
    def test_exact_post_adoption_triplet_activates_and_mixed_state_fails(self):
        candidate = json.loads(
            REFERENCE_CANDIDATE.read_text(encoding="utf-8")
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scope_path = root / "scope.json"
            strict_path = root / "strict.json"
            fake_path = root / "fake.json"
            scope_path.write_text(
                json.dumps(
                    candidate["scope_manifest_candidate"], ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            strict_path.write_text(
                json.dumps(phase532_strict_payload(), ensure_ascii=False),
                encoding="utf-8",
            )
            fake_path.write_bytes(CANDIDATE_MANIFEST.read_bytes())
            report = activation.activation_report(
                scope_path=scope_path, strict_path=strict_path,
                fake_reference_path=fake_path,
            )
            self.assertTrue(report["phase532_active"])
            fake_path.write_bytes(
                carry_builder.PHASE513_MANIFEST_PATH.read_bytes()
            )
            with self.assertRaisesRegex(ValueError, "incoherent Phase 532"):
                activation.activation_report(
                    scope_path=scope_path, strict_path=strict_path,
                    fake_reference_path=fake_path,
                )

    def test_phase513_raw_evidence_is_separate_and_exact(self):
        evidence = carry_builder.PHASE513_MANIFEST_PATH
        self.assertNotEqual(evidence, activation.FAKE_REFERENCE_PATH)
        self.assertEqual(
            carry_builder.sha256_file(evidence),
            no_worsening.PHASE513_FAKE_COARSE_MANIFEST_SHA256,
        )

    @unittest.skipUnless(
        BASELINE_DIR.is_dir() and CANDIDATE_DIR.is_dir()
        and CANDIDATE_MANIFEST.is_file(),
        "frozen Phase 513/532 sources unavailable",
    )
    def test_full_audit_loader_accepts_adopted_tracked_manifest_simulation(self):
        learner = policy_builder.find_by_sha(
            CANDIDATE_DIR, policy.CANDIDATE_LEARNER_SHA256,
        )
        academic = policy_builder.find_by_sha(
            CANDIDATE_DIR, policy.CANDIDATE_ACADEMIC_SHA256,
        )
        raw = learner.read_bytes()
        review = no_worsening.load_phase532_reference_review(
            CANDIDATE_MANIFEST
        )
        with mock.patch.object(
            full_audit, "FAKE_COARSE_MANIFEST", CANDIDATE_MANIFEST,
        ):
            rows, identity = full_audit.load_fake_coarse_authority(
                raw, raw.decode("utf-8"), academic,
                policy.CANDIDATE_ACADEMIC_SHA256,
                phase532_reference_review=review,
            )
        self.assertEqual(len(rows), 3517)
        transition = identity["transition_manifests"]
        self.assertEqual(transition["combined_entries"], 193)
        self.assertEqual(transition["active_entries"], 192)
        self.assertEqual(
            transition["active_scope_rows"]["phase532_selected_ruby"], 35,
        )


if __name__ == "__main__":
    unittest.main()
