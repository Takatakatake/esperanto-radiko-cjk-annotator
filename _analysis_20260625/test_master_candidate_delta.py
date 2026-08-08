# -*- coding: utf-8 -*-
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from _analysis_20260625 import audit_master_candidate_delta as delta


class CandidateDeltaPureTests(unittest.TestCase):
    def test_raw_change_preserves_surface_and_gloss_before_metadata(self):
        old = "foo/bar/o:same gloss\natlet/ik/o:same definition ##old"
        new = "foob/ar/o:same gloss\natlet/ik/o:same definition ##new"
        rows = delta.changed_raw_rows(old, new)
        self.assertEqual([row["surface"] for row in rows], ["foobar/o".replace("/", ""), "atletiko"])
        self.assertTrue(all(row["surface_unchanged"] for row in rows))
        self.assertTrue(all(row["gloss_unchanged_before_metadata"] for row in rows))

    def test_raw_change_rejects_semantic_drift_signal(self):
        rows = delta.changed_raw_rows("radik/o:old", "ra/dik/o:new")
        self.assertTrue(rows[0]["surface_unchanged"])
        self.assertFalse(rows[0]["gloss_unchanged_before_metadata"])

    def test_generic_disposition_groups_are_exact_and_disjoint(self):
        sources = {"baseline": "A", "candidate": "B"}
        value = {
            "schema_version": 1,
            "candidate_only": True,
            "source_phase": 529,
            "policy": {"ruby": "coarse"},
            "sources": sources,
            "groups": {"keep": ["alpha"], "repair": ["beta"]},
            "expected_counts": {"keep": 1, "repair": 1, "union": 2},
            "promotion_gate": False,
            "promotion_blockers": ["review"],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            loaded = delta.validate_ledger(
                path, {"alpha", "beta"}, sources,
            )
        self.assertEqual(loaded["source_phase"], 529)
        self.assertEqual(loaded["counts"]["union"], 2)

    def test_disposition_overlap_fails_closed(self):
        sources = {"baseline": "A", "candidate": "B"}
        value = {
            "schema_version": 1,
            "candidate_only": True,
            "source_phase": 529,
            "policy": {},
            "sources": sources,
            "groups": {"one": ["same"], "two": ["same"]},
            "expected_counts": {"one": 1, "two": 1, "union": 1},
            "promotion_gate": False,
            "promotion_blockers": ["review"],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "overlap"):
                delta.validate_ledger(path, {"same"}, sources)

    def test_render_harness_fingerprint_ignores_only_orchestration(self):
        first = b"X = 1\ndef render():\n    return X\ndef run():\n    return 1\n"
        orchestration_change = (
            b"X = 1\ndef render():\n    return X\ndef run():\n    return 2\n"
        )
        render_change = (
            b"X = 2\ndef render():\n    return X\ndef run():\n    return 1\n"
        )
        self.assertEqual(
            delta.render_harness_ast_sha256(first),
            delta.render_harness_ast_sha256(orchestration_change),
        )
        self.assertNotEqual(
            delta.render_harness_ast_sha256(first),
            delta.render_harness_ast_sha256(render_change),
        )

    def test_candidate_control_identity_binds_phase_and_all_sources(self):
        learner = "L" * 64
        academic = "A" * 64
        pejvo = "P" * 64
        manifest = {"sources": {
            "learner": {"sha256": learner},
            "academic": {"sha256": academic},
            "pejvo_original": {"sha256": pejvo},
        }}
        transition = {"source_phase": 530}
        ledger = {
            "source_phase": 530,
            "sources": {
                "candidate_learner_sha256": learner,
                "candidate_academic_sha256": academic,
            },
        }
        sources, phase = delta.validate_candidate_control_identity(
            manifest, transition, ledger,
        )
        self.assertEqual(phase, 530)
        self.assertEqual(sources["candidate_learner_sha256"], learner)
        transition["source_phase"] = 529
        with self.assertRaisesRegex(ValueError, "source phases"):
            delta.validate_candidate_control_identity(
                manifest, transition, ledger,
            )

    def test_transition_gate_rejects_scope_redistribution(self):
        expected = {"old": 2, "new": 1}
        row = {
            "counts": {
                "transition_rows": 3,
                "transition_matched": 3,
                "transition_mismatched": 0,
            },
            "transition_scopes": {
                "old": {"matched": 2}, "new": {"matched": 1},
            },
        }
        self.assertTrue(delta.transition_scope_gate([row], expected))
        row["transition_scopes"] = {"old": {"matched": 3}}
        self.assertFalse(delta.transition_scope_gate([row], expected))

    def test_report_path_cannot_overwrite_inputs_or_protected_trees(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            bound = root / "bound.json"
            protected = root / "app"
            delta.validate_report_path(
                root / "safe-report.json", [bound], (protected,),
            )
            with self.assertRaisesRegex(ValueError, "overlaps"):
                delta.validate_report_path(bound, [bound], (protected,))
            with self.assertRaisesRegex(ValueError, "overlaps"):
                delta.validate_report_path(
                    protected / "main.py", [bound], (protected,),
                )

    def test_bound_snapshot_rejects_path_escape_before_parsing(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            raw = b"radik/o: gloss\n"
            learner = Path(second) / "learner.txt"
            academic = Path(second) / "academic.txt"
            learner.write_bytes(raw)
            academic.write_bytes(raw)
            digest = delta.sha256_bytes(raw)
            with self.assertRaisesRegex(ValueError, "escaped"):
                delta.parse_snapshot(
                    Path(first), digest, digest,
                    learner_path=learner, academic_path=academic,
                )

    @mock.patch.object(delta, "git", return_value="")
    @mock.patch.object(delta.subprocess, "run")
    def test_runtime_dependency_state_includes_staged_and_unstaged(
        self, run_mock, _git_mock,
    ):
        run_mock.side_effect = [
            mock.Mock(returncode=0), mock.Mock(returncode=1),
        ]
        state = delta.working_runtime_dependency_state()
        self.assertTrue(state["unstaged_clean"])
        self.assertFalse(state["staged_clean"])
        self.assertFalse(state["clean"])

    def test_phase513_authority_fingerprint_is_explicitly_pinned(self):
        self.assertEqual(
            delta.PHASE513_DEFAULT_AUTHORITY_SHA256,
            "5D8A5671E810FB191924CEE696E65E69A0BBE4CAF37160CEC5973876C20DAEA3",
        )

    def test_analysis_dependency_fingerprint_normalizes_only_line_endings(self):
        self.assertEqual(
            delta.semantic_text_sha256(b"one\r\ntwo\r"),
            delta.semantic_text_sha256(b"one\ntwo\n"),
        )
        self.assertNotEqual(
            delta.semantic_text_sha256(b"one\ntwo\n"),
            delta.semantic_text_sha256(b"one\nthree\n"),
        )


if __name__ == "__main__":
    unittest.main()
