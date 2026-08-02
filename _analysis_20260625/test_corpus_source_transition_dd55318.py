# -*- coding: utf-8 -*-
from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

import build_corpus_source_transition_dd55318 as transition


HERE = Path(__file__).resolve().parent


class CorpusSourceTransitionDD55318Tests(unittest.TestCase):
    def ledger(self):
        return json.loads(transition.LEDGER_PATH.read_text(encoding="utf-8"))

    def test_ledger_closes_one_source_only_radioelsendo_change(self):
        ledger = self.ledger()
        transition.validate_ledger(ledger)
        delta = ledger["canonical_transition"]
        self.assertEqual(delta["removed"], transition.EXPECTED_DELTA["removed"])
        self.assertEqual(delta["added"], transition.EXPECTED_DELTA["added"])
        self.assertTrue(ledger["policy"]["source_only_transition"])
        self.assertFalse(
            ledger["policy"]["app_runtime_rules_changed_by_transition"]
        )
        self.assertFalse(ledger["policy"]["kanji_track_changed_by_transition"])
        self.assertTrue(ledger["policy"]["ja_zh_ko_boundary_gate_required"])

    def test_second_canonical_delta_is_rejected(self):
        ledger = self.ledger()
        ledger["canonical_transition"]["added"].append({
            "surface": "radioelsendoj",
            "typed": "R:radio|R:el|R:send|L:oj",
            "count": 1,
        })
        with self.assertRaisesRegex(ValueError, "delta changed"):
            transition.validate_ledger(ledger)

    def test_width_split_or_kanji_change_cannot_be_authorized(self):
        for field in (
            "split_for_width_allowed",
            "kanji_track_changed_by_transition",
            "learner_fake_decomposition_changed_by_transition",
        ):
            with self.subTest(field=field):
                ledger = self.ledger()
                ledger["policy"][field] = True
                with self.assertRaisesRegex(ValueError, "policy changed"):
                    transition.validate_ledger(ledger)

    def test_rich_evidence_reconstructs_the_same_surface(self):
        ledger = self.ledger()
        evidence = ledger["canonical_transition"]
        for side in ("parent_rich", "candidate_rich"):
            self.assertEqual(
                "".join(row["piece"] for row in evidence[side]),
                "radioelsendo",
            )
        self.assertEqual(
            [row["rt"] for row in evidence["candidate_rich"] if row["ruby"]],
            ["ラジオ", "中か<br>ら", "(を)送る"],
        )

    def test_manifest_hash_projection_excludes_only_source_and_prose(self):
        payload = {
            "schema_version": 1,
            "description": "prose",
            "source": {"head_oid": "a"},
            "counts": {},
            "exact_surfaces": [],
            "annotations": {},
        }
        baseline = transition.manifest_hashes(payload, "exact_surfaces")
        provenance_changed = copy.deepcopy(payload)
        provenance_changed["description"] = "new prose"
        provenance_changed["source"]["head_oid"] = "b"
        self.assertEqual(
            baseline,
            transition.manifest_hashes(provenance_changed, "exact_surfaces"),
        )
        runtime_changed = copy.deepcopy(payload)
        runtime_changed["exact_surfaces"].append({"surface": "x"})
        self.assertNotEqual(
            baseline,
            transition.manifest_hashes(runtime_changed, "exact_surfaces"),
        )

    def test_boundary_successor_exactly_links_historical_parent(self):
        ledger = self.ledger()
        successor = transition.read_boundary_successor()
        transition.validate_boundary_successor_link(ledger, successor)
        self.assertEqual(
            successor["parent"], transition.source_boundary_parent(ledger),
        )
        self.assertEqual(
            successor["candidate"],
            transition.EXPECTED_BOUNDARY_SUCCESSOR_CANDIDATE,
        )

    def test_boundary_successor_rejects_historical_parent_drift(self):
        ledger = self.ledger()
        successor = transition.read_boundary_successor()
        successor["parent"]["authority_keys"] += 1
        with self.assertRaisesRegex(ValueError, "historical parent"):
            transition.validate_boundary_successor_link(ledger, successor)

    def test_boundary_successor_rejects_candidate_authority_drift(self):
        ledger = self.ledger()
        successor = transition.read_boundary_successor()
        successor["candidate"]["expected_key_counts"]["ja"] += 1
        with self.assertRaisesRegex(ValueError, "candidate identity"):
            transition.validate_boundary_successor_link(ledger, successor)

    def test_live_boundary_is_byte_and_authority_sealed_successor(self):
        ledger = self.ledger()
        transition.verify_active_boundary_successor(
            ledger, transition.read_boundary_successor(),
        )

    def test_regeneration_pipeline_uses_successor_and_runtime_gate(self):
        source = (HERE / "regenerate_all.py").read_text(encoding="utf-8")
        self.assertIn("build_corpus_source_transition_dd55318.py", source)
        self.assertIn("test_corpus_source_transition_dd55318.py", source)
        self.assertIn(
            "test_word_anno_boundary_transition_dd55318_u2019.py", source,
        )
        self.assertIn("test_r94_ccb9398_runtime_semantics.py", source)


if __name__ == "__main__":
    unittest.main()
