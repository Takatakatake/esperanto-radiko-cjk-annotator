# -*- coding: utf-8 -*-
"""Fail-closed tests for the Phase 532 authority carry-forward closure."""
from __future__ import annotations

import copy
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import build_phase532_authority_carry_forward as builder
import phase532_authority_carry_forward as carry


BASELINE_DIR = Path(r"D:\tmp\esperanto_stage_20260715_phase513")
CANDIDATE_DIR = Path(r"D:\tmp\esperanto_stage_20260718_phase532_candidate")
CANDIDATE_MANIFEST = Path(
    r"D:\tmp\phase532_fake_coarse_reference_candidate.json"
)


class CarryForwardLedgerTests(unittest.TestCase):
    def test_reviewed_ledger_and_api_identity(self):
        payload = carry.load_phase532_authority_carry_forward()
        self.assertEqual(payload["authorities"], carry.EXPECTED_AUTHORITY_GROUPS)
        self.assertEqual(
            carry.authority_lines()["app_review"],
            tuple(carry.EXPECTED_AUTHORITY_GROUPS["app_review"]["learner_lines"]),
        )
        self.assertEqual(
            carry.review_identity(),
            {
                "phase_from": 513,
                "phase_to": 532,
                "ledger_sha256": (
                    "D4D4CD8BFC274A006BDA89C8B5E250B4EE1D4286969552F484237E1FF3B97A90"
                ),
                "phase513_fake_manifest_sha256": (
                    "8C507321A27ACD3FE9F919E82C1C380833D6D51760C122467D49757511004504"
                ),
                "phase513_fake_entries_sha256": (
                    "A542BC4464CDA30FBE39C28F0EFBEE51EECE83EEABBEA5D3A201388DA3AA7DEB"
                ),
                "phase532_fake_manifest_sha256": (
                    "5F743A916742BE022EFDEC30D24B5ACA0EB2A9156A2086FBB01740DDC356A060"
                ),
                "phase532_fake_entries_sha256": (
                    "8F823A44A62AFB38321662FB843F52D9E97FB5953962CD5B75406B2F1EBC4368"
                ),
                "authority_groups": 5,
                "reviewed_learner_lines": 113,
                "reviewed_line_union_sha256": (
                    "29A7E25096900620BF3919F90893BC5C146C303D5A14609622C85DA6007AE365"
                ),
            },
        )

    def test_five_scopes_are_disjoint_and_complete(self):
        groups = carry.authority_lines()
        self.assertEqual(
            {name: len(lines) for name, lines in groups.items()},
            {
                "phase511_transition": 21,
                "ff33_transition": 1,
                "5e_transition": 1,
                "app_review": 86,
                "atomic_families": 4,
            },
        )
        union = set()
        for lines in groups.values():
            self.assertFalse(union & set(lines))
            union.update(lines)
        self.assertEqual(len(union), 113)

    def test_semantic_ledger_mutation_is_rejected(self):
        payload = json.loads(carry.LEDGER_PATH.read_text(encoding="utf-8"))
        payload["authorities"]["phase511_transition"]["learner_lines"][0] += 1
        with self.assertRaisesRegex(ValueError, "reviewed identity drift"):
            carry.validate_ledger_payload(payload)

    def test_decision_source_mutation_is_rejected(self):
        payload = json.loads(carry.LEDGER_PATH.read_text(encoding="utf-8"))
        payload["decision_sources"]["app_review"]["learner_lines"] = 85
        with self.assertRaisesRegex(ValueError, "reviewed identity drift"):
            carry.validate_ledger_payload(payload)

    def test_raw_ledger_mutation_is_rejected_before_semantic_use(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "ledger.json"
            path.write_bytes(carry.LEDGER_PATH.read_bytes() + b" ")
            with mock.patch.object(carry, "LEDGER_PATH", path):
                with self.assertRaisesRegex(ValueError, "raw identity drift"):
                    carry.load_phase532_authority_carry_forward()

    def test_source_ledgers_rederive_exact_reviewed_lines(self):
        self.assertEqual(
            builder.load_decision_line_scopes(),
            {
                name: reviewed["learner_lines"]
                for name, reviewed in carry.EXPECTED_AUTHORITY_GROUPS.items()
            },
        )

    def test_check_flag_is_mandatory(self):
        argv = [
            "--baseline-dir", str(BASELINE_DIR),
            "--candidate-dir", str(CANDIDATE_DIR),
            "--candidate-manifest", str(CANDIDATE_MANIFEST),
        ]
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                builder.parse_args(argv)


class FrozenCarryForwardIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (
            BASELINE_DIR.is_dir()
            and CANDIDATE_DIR.is_dir()
            and CANDIDATE_MANIFEST.is_file()
        ):
            raise unittest.SkipTest("frozen Phase 513/532 inputs unavailable")
        cls.master_paths = {
            "phase513_learner": builder.find_by_sha(
                BASELINE_DIR, carry.PHASE513_LEARNER_SHA256,
            ),
            "phase513_academic": builder.find_by_sha(
                BASELINE_DIR, carry.PHASE513_ACADEMIC_SHA256,
            ),
            "phase532_learner": builder.find_by_sha(
                CANDIDATE_DIR, carry.PHASE532_LEARNER_SHA256,
            ),
            "phase532_academic": builder.find_by_sha(
                CANDIDATE_DIR, carry.PHASE532_ACADEMIC_SHA256,
            ),
        }
        cls.masters = {
            name: builder.read_bound_master(
                path, carry.EXPECTED_SOURCES[name]["sha256"],
            )
            for name, path in cls.master_paths.items()
        }
        _old, cls.old_by_line = builder._load_manifest(
            builder.PHASE513_MANIFEST_PATH,
            expected_raw_sha256=carry.PHASE513_FAKE_MANIFEST_SHA256,
            expected_entries_sha256=carry.PHASE513_FAKE_ENTRIES_SHA256,
            expected_entries=3213,
            learner_sha256=carry.PHASE513_LEARNER_SHA256,
            academic_sha256=carry.PHASE513_ACADEMIC_SHA256,
        )
        _new, cls.new_by_line = builder._load_manifest(
            CANDIDATE_MANIFEST,
            expected_raw_sha256=carry.PHASE532_FAKE_MANIFEST_SHA256,
            expected_entries_sha256=carry.PHASE532_FAKE_ENTRIES_SHA256,
            expected_entries=3238,
            learner_sha256=carry.PHASE532_LEARNER_SHA256,
            academic_sha256=carry.PHASE532_ACADEMIC_SHA256,
        )
        cls.scopes = builder.load_decision_line_scopes()

    def verify(self, *, scopes=None, old=None, new=None, masters=None):
        return builder.verify_carry_forward_groups(
            scopes=scopes if scopes is not None else copy.deepcopy(self.scopes),
            phase513_by_line=(
                old if old is not None else copy.deepcopy(self.old_by_line)
            ),
            phase532_by_line=(
                new if new is not None else copy.deepcopy(self.new_by_line)
            ),
            masters=masters if masters is not None else {
                name: list(lines) for name, lines in self.masters.items()
            },
        )

    def test_real_frozen_closure_is_green(self):
        report = builder.validate_frozen_closure(
            BASELINE_DIR, CANDIDATE_DIR, CANDIDATE_MANIFEST,
        )
        self.assertTrue(report["gate"])
        self.assertTrue(report["all_inputs_stable"])
        self.assertEqual(report["reviewed_learner_lines"], 113)
        self.assertTrue(
            report["phase513_to_phase532_manifest_entries_identical"]
        )
        self.assertTrue(
            report["phase513_to_phase532_learner_rows_identical"]
        )
        self.assertTrue(
            report["phase513_to_phase532_academic_rows_identical"]
        )

    def test_manifest_entry_change_is_rejected(self):
        new = copy.deepcopy(self.new_by_line)
        new[4785]["authority"] = "tampered"
        with self.assertRaisesRegex(ValueError, "fake/coarse authority changed"):
            self.verify(new=new)

    def test_learner_row_change_is_rejected(self):
        masters = {name: list(lines) for name, lines in self.masters.items()}
        masters["phase532_learner"][4785 - 1] += " "
        with self.assertRaisesRegex(ValueError, "learner authority rows changed"):
            self.verify(masters=masters)

    def test_academic_row_change_is_rejected(self):
        masters = {name: list(lines) for name, lines in self.masters.items()}
        masters["phase532_academic"][4785 - 1] += " "
        with self.assertRaisesRegex(ValueError, "academic authority rows changed"):
            self.verify(masters=masters)

    def test_missing_candidate_manifest_row_is_rejected(self):
        new = copy.deepcopy(self.new_by_line)
        new.pop(56273)
        with self.assertRaisesRegex(ValueError, "source row missing"):
            self.verify(new=new)

    def test_overlapping_authority_scopes_are_rejected(self):
        scopes = copy.deepcopy(self.scopes)
        scopes["ff33_transition"].append(
            scopes["phase511_transition"][0]
        )
        scopes["ff33_transition"].sort()
        with self.assertRaisesRegex(ValueError, "scopes overlap"):
            self.verify(scopes=scopes)

    def test_candidate_manifest_raw_change_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "candidate.json"
            path.write_bytes(CANDIDATE_MANIFEST.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "JSON source identity changed"):
                builder._load_manifest(
                    path,
                    expected_raw_sha256=carry.PHASE532_FAKE_MANIFEST_SHA256,
                    expected_entries_sha256=carry.PHASE532_FAKE_ENTRIES_SHA256,
                    expected_entries=3238,
                    learner_sha256=carry.PHASE532_LEARNER_SHA256,
                    academic_sha256=carry.PHASE532_ACADEMIC_SHA256,
                )


if __name__ == "__main__":
    unittest.main()
