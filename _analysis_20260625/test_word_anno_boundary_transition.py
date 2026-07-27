# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import unittest

import build_word_anno_boundary_manifest as boundary


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

    def test_active_manifest_is_the_candidate_projection(self):
        active = json.loads(
            boundary.DEFAULT_MANIFEST.read_text(encoding="utf-8")
        )
        candidate = self.ledger["candidate"]
        for key in (
            "authority_keys", "authority_sha256", "expected_key_counts",
        ):
            self.assertEqual(active[key], candidate[key])

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
