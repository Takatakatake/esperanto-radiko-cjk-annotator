# -*- coding: utf-8 -*-
from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

import build_no_worsening_scope_transition_dd55318 as transition


HERE = Path(__file__).resolve().parent


class NoWorseningScopeTransitionDD55318Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scope, cls.conflict = transition.build()
        cls.by_surface = {
            row["surface"]: row for row in cls.conflict["entries"]
        }

    def test_successor_outputs_are_sealed_and_current(self):
        transition.verify_output(
            transition.OUTPUT_SCOPE_PATH,
            self.scope,
            transition.EXPECTED_SCOPE_FILE_SHA256,
        )
        transition.verify_output(
            transition.OUTPUT_CONFLICT_PATH,
            self.conflict,
            transition.EXPECTED_CONFLICT_FILE_SHA256,
        )
        self.assertEqual(self.scope["expected"]["case_count"], 68650)
        self.assertEqual(self.scope["expected"]["surface_count"], 68559)
        self.assertEqual(len(self.conflict["entries"]), 91)

    def test_three_new_conflicts_select_only_coarse_kyoto_ruby(self):
        for surface, expected in transition.COARSE_EXPECTED.items():
            with self.subTest(surface=surface):
                row = self.by_surface[surface]
                self.assertEqual(
                    row["category"],
                    "ruby_track_coarse_two_track_partition",
                )
                self.assertEqual(len(row["allowed_signatures"]), 1)
                allowed = json.dumps(
                    row["allowed_signatures"][0],
                    ensure_ascii=True,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                matching = [
                    option for option in row["options"]
                    if json.dumps(
                        option["signature"], ensure_ascii=True,
                        sort_keys=True, separators=(",", ":"),
                    ) == allowed
                ]
                self.assertEqual([option["expected"] for option in matching], [expected])

    def test_historical_iniciatoro_conflict_is_retired_not_rewritten(self):
        parent = transition.read_sealed(
            transition.PARENT_CONFLICT_PATH,
            transition.PARENT_CONFLICT_FILE_SHA256,
        )
        self.assertIn("iniciatoro", {row["surface"] for row in parent["entries"]})
        self.assertNotIn("iniciatoro", self.by_surface)

    def test_fourth_new_conflict_is_rejected(self):
        parent = transition.read_sealed(
            transition.PARENT_CONFLICT_PATH,
            transition.PARENT_CONFLICT_FILE_SHA256,
        )
        candidate = transition.read_sealed(
            transition.CANDIDATE_PATH,
            transition.CANDIDATE_FILE_SHA256,
        )
        conflicts = copy.deepcopy(candidate["conflicts"])
        conflicts.append({"surface": "surplus", "options": []})
        with self.assertRaisesRegex(ValueError, "new conflict set"):
            transition.build_conflict_manifest(parent, conflicts)

    def test_no_worsening_cli_accepts_paired_successor_manifests(self):
        source = (HERE / "no_worsening_audit.py").read_text(encoding="utf-8")
        self.assertIn('"--scope-manifest"', source)
        self.assertIn('"--conflict-manifest"', source)
        pipeline = (HERE / "regenerate_all.py").read_text(encoding="utf-8")
        self.assertIn("build_no_worsening_scope_transition_dd55318.py", pipeline)
        self.assertIn("test_no_worsening_scope_transition_dd55318.py", pipeline)

    def test_real_validator_accepts_only_the_paired_successor_review(self):
        candidate = transition.read_sealed(
            transition.CANDIDATE_PATH,
            transition.CANDIDATE_FILE_SHA256,
        )
        metadata, allowed = transition.audit.validate_reviewed_reference_scope(
            candidate["projection"],
            candidate["conflicts"],
            scope_path=transition.OUTPUT_SCOPE_PATH,
            conflict_path=transition.OUTPUT_CONFLICT_PATH,
        )
        self.assertEqual(metadata["reviewed_conflicts"], 91)
        self.assertEqual(metadata["contextual_multi_signature_conflicts"], 50)
        for surface in transition.ADDED_CONFLICTS:
            self.assertEqual(len(allowed[surface]), 1)

    def test_source_transition_and_successor_outputs_are_byte_sealed(self):
        self.assertEqual(
            transition.raw_sha256(transition.SOURCE_TRANSITION_PATH.read_bytes()),
            transition.SOURCE_TRANSITION_FILE_SHA256,
        )
        self.assertEqual(
            transition.raw_sha256(transition.serialized_payload(self.scope)),
            transition.EXPECTED_SCOPE_FILE_SHA256,
        )
        self.assertEqual(
            transition.raw_sha256(transition.serialized_payload(self.conflict)),
            transition.EXPECTED_CONFLICT_FILE_SHA256,
        )


if __name__ == "__main__":
    unittest.main()
