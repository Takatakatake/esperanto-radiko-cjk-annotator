# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import unittest

import build_word_anno_boundary_manifest as boundary
import phase619_ordinary_ruby_policy as phase619_policy


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
LEDGER = HERE / "_word_anno_boundary_transition_d1642c2.json"


class WordAnnoBoundaryTransitionTests(unittest.TestCase):
    def setUp(self):
        self.ledger = json.loads(LEDGER.read_text(encoding="utf-8"))

    def test_closed_six_key_retirement(self):
        self.assertEqual(
            set(self.ledger["removed_keys"]),
            {
                "@typed:bonŝanĉulo:0",
                "@typed:bonŝanĉulo:1",
                "@typed:bonŝanĉulo:2",
                "@typed:fronantaj:0",
                "@typed:fronantaj:1",
                "@typed:jurnal:0",
            },
        )
        self.assertEqual(len(self.ledger["removed_keys"]), 6)
        self.assertFalse(
            self.ledger["policy"]["wildcard_or_productive_rule_removal"]
        )

    def test_parent_manifest_is_pinned_git_evidence(self):
        parent = self.ledger["parent"]
        raw = subprocess.check_output(
            [
                "git",
                "show",
                f"{parent['app_commit']}:{parent['manifest_path']}",
            ],
            cwd=ROOT,
        )
        self.assertEqual(
            hashlib.sha256(raw).hexdigest().upper(),
            parent["manifest_sha256"],
        )
        payload = json.loads(raw)
        self.assertEqual(payload["authority_keys"], parent["authority_keys"])
        self.assertEqual(
            payload["authority_sha256"], parent["authority_sha256"],
        )

    # 第88R: Phase 619 サイドカーは派生語 mukoz/aĵ だけを採り、同じ gold 扱い
    # (学習者版 muk/oz/o##偽分解 / 学術版 mukoz/o)の**基語 mukoz** を採り残していた。
    # Phase 619 の封印されたポリシーは変えず、同じ注釈名前空間に1件だけ重ねた分を
    # ここで明示的に数える(黙って +1 して通さない)。
    R88_ADDED_KEYS = {"@phase619-ruby:mukoz"}

    def test_active_manifest_is_candidate_plus_phase619_sidecar(self):
        active = json.loads(
            boundary.DEFAULT_MANIFEST.read_text(encoding="utf-8")
        )
        candidate = self.ledger["candidate"]
        added_keys = (
            set(phase619_policy.morph_context_annotations())
            | set(phase619_policy.split_context_annotations())
        )
        self.assertEqual(len(added_keys), 7)
        total_added = added_keys | self.R88_ADDED_KEYS
        self.assertEqual(len(total_added), 8)
        self.assertEqual(
            active["authority_keys"],
            candidate["authority_keys"] + len(total_added),
        )
        self.assertEqual(
            active["expected_key_counts"],
            {
                language: count + len(total_added)
                for language, count
                in candidate["expected_key_counts"].items()
            },
        )
        self.assertEqual(
            active["authority_sha256"],
            "386FD7889E2074271D619D526F510F5FB9712964E51410145F30D7AA5F2B83A3",
        )

    def test_only_six_authority_keys_retire(self):
        parent = self.ledger["parent"]
        candidate = self.ledger["candidate"]
        self.assertEqual(
            parent["authority_keys"] - candidate["authority_keys"], 6,
        )
        for language in ("ja", "zh", "ko"):
            self.assertEqual(
                parent["expected_key_counts"][language]
                - candidate["expected_key_counts"][language],
                6,
            )


if __name__ == "__main__":
    unittest.main()
