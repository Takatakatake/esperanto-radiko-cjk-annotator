# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import build_word_anno_boundary_manifest as boundary
import build_fake_coarse_transition_app_review as historical_transition


LEDGER = HERE / "_word_anno_boundary_transition_ccb9398.json"
SUCCESSOR_LEDGER = (
    HERE / "_word_anno_boundary_transition_dd55318_u2019.json"
)
LANGUAGES = ("ja", "zh", "ko")


def canonical_sha256(payload):
    raw = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


def app_path(language):
    return (
        ROOT / f"Esperanto-Kanji-Ruby-{language.upper()}"
        / "app_data" / "word_anno.json"
    )


class Ccb9398WordAnnoBoundaryTransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
        cls.successor = json.loads(
            SUCCESSOR_LEDGER.read_text(encoding="utf-8")
        )
        cls.successor_added = set(cls.successor["delta"]["added_keys"])

    def test_policy_is_closed_and_keeps_kanji_authority(self):
        policy = self.ledger["policy"]
        self.assertTrue(policy["three_language_boundary_identity_required"])
        self.assertTrue(policy["glosses_remain_language_local"])
        self.assertTrue(policy["removed_keys_allowed"] is False)
        self.assertTrue(policy["wildcard_or_unbounded_authorization"] is False)
        self.assertTrue(policy["radio_media_gloss_is_compound_context_only"])
        self.assertTrue(policy["kanji_master_decomposition_is_not_changed"])
        self.assertEqual(len(self.ledger["added_keys"]), 31)
        self.assertEqual(len(set(self.ledger["added_keys"])), 31)

    def test_parent_manifest_is_exact_pinned_git_evidence(self):
        parent = self.ledger["parent"]
        raw = subprocess.check_output(
            [
                "git", "show",
                f"{parent['app_commit']}:{parent['manifest_path']}",
            ],
            cwd=ROOT,
        )
        self.assertEqual(
            hashlib.sha256(raw).hexdigest().upper(),
            parent["manifest_file_sha256"],
        )
        payload = json.loads(raw)
        self.assertEqual(payload["authority_keys"], parent["authority_keys"])
        self.assertEqual(
            payload["authority_sha256"], parent["authority_sha256"],
        )
        self.assertEqual(
            payload["expected_key_counts"], parent["expected_key_counts"],
        )

    def test_successor_parent_is_exact_sealed_candidate(self):
        candidate = self.ledger["candidate"]
        parent = self.successor["parent"]
        self.assertEqual(
            parent["canonical_payload_sha256"],
            candidate["canonical_payload_sha256"],
        )
        self.assertEqual(parent["authority_keys"], candidate["authority_keys"])
        self.assertEqual(
            parent["authority_sha256"], candidate["authority_sha256"],
        )
        self.assertEqual(
            parent["expected_key_counts"],
            candidate["expected_key_counts"],
        )
        authority = self.successor["authority"][
            "historical_ccb9398_transition"
        ]
        self.assertEqual(
            authority["path"], LEDGER.relative_to(ROOT).as_posix(),
        )
        self.assertEqual(
            authority["file_sha256"],
            hashlib.sha256(LEDGER.read_bytes()).hexdigest().upper(),
        )

    def test_live_maps_minus_successor_rebuild_historical_candidate(self):
        maps = {
            language: json.loads(app_path(language).read_text(encoding="utf-8"))
            for language in LANGUAGES
        }
        for mapping in maps.values():
            for key in self.successor_added:
                mapping.pop(key)
        rebuilt = boundary.build(maps)
        candidate = self.ledger["candidate"]
        self.assertEqual(
            canonical_sha256(rebuilt),
            candidate["canonical_payload_sha256"],
        )
        self.assertEqual(
            rebuilt["authority_keys"], candidate["authority_keys"],
        )
        self.assertEqual(
            rebuilt["authority_sha256"], candidate["authority_sha256"],
        )
        self.assertEqual(
            rebuilt["expected_key_counts"],
            candidate["expected_key_counts"],
        )

    def test_each_language_delta_matches_the_sealed_payload(self):
        parent_commit = self.ledger["parent"]["app_commit"]
        expected_added = set(self.ledger["added_keys"])
        for language in LANGUAGES:
            relative = app_path(language).relative_to(ROOT).as_posix()
            old_raw = subprocess.check_output(
                ["git", "show", f"{parent_commit}:{relative}"], cwd=ROOT,
            )
            old = json.loads(old_raw)
            new = json.loads(app_path(language).read_text(encoding="utf-8"))
            for key in self.successor_added:
                new.pop(key)
            added_keys = sorted(set(new) - set(old))
            removed_keys = sorted(set(old) - set(new))
            changed_keys = sorted(
                key for key in set(old) & set(new) if old[key] != new[key]
            )
            diff = {
                "added": {key: new[key] for key in added_keys},
                "removed": {key: old[key] for key in removed_keys},
                "changed": {
                    key: {"old": old[key], "new": new[key]}
                    for key in changed_keys
                },
            }
            expected = self.ledger["languages"][language]
            with self.subTest(language=language):
                self.assertEqual(set(added_keys), expected_added)
                self.assertEqual(len(added_keys), expected["added"])
                self.assertEqual(len(removed_keys), expected["removed"])
                self.assertEqual(changed_keys, expected["changed_keys"])
                self.assertEqual(
                    canonical_sha256(diff),
                    expected["canonical_diff_sha256"],
                )

    def test_successor_keys_do_not_rewrite_phase511_historical_evidence(self):
        historical = json.loads(
            historical_transition.DEFAULT_MANIFEST.read_text(encoding="utf-8")
        )
        _roots, identities = historical_transition.localized_root_sets()
        self.assertEqual(identities, historical["localized_sources"])
        self.assertEqual(
            historical_transition.validate(historical), historical["counts"]
        )


if __name__ == "__main__":
    unittest.main()
