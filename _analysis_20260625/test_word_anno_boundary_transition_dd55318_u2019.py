# -*- coding: utf-8 -*-
"""Fail-closed proof for the dd55318 U+2019 typed-exact successor.

The historical ccb9398 transition and R94 residual ledger use the canonical
ASCII-apostrophe spelling.  This successor must add exactly one browser-visible
U+2019 context key and one bounded Ruby-only rule without rewriting either
historical authority.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import build_word_anno_boundary_manifest as boundary
import check_raw_apostrophe_structure as raw_apostrophe


LEDGER_PATH = HERE / "_word_anno_boundary_transition_dd55318_u2019.json"
LANGUAGES = ("ja", "zh", "ko")


def canonical_sha256(payload) -> str:
    raw = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def read_authority(spec: dict) -> dict:
    path = ROOT / spec["path"]
    if file_sha256(path) != spec["file_sha256"]:
        raise AssertionError(f"historical authority changed: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def out_word_anno_path(language: str) -> Path:
    return HERE / "out" / f"word_anno_{language}.json"


def app_word_anno_path(language: str) -> Path:
    return (
        ROOT / f"Esperanto-Kanji-Ruby-{language.upper()}"
        / "app_data" / "word_anno.json"
    )


def settings_path(language: str) -> Path:
    return (
        ROOT / f"Esperanto-Kanji-Ruby-{language.upper()}"
        / "app_data" / "分解設定.json"
    )


def map_delta(old: dict, new: dict) -> dict:
    added_keys = sorted(set(new) - set(old))
    removed_keys = sorted(set(old) - set(new))
    changed_keys = sorted(
        key for key in set(old) & set(new) if old[key] != new[key]
    )
    return {
        "added": {key: new[key] for key in added_keys},
        "removed": {key: old[key] for key in removed_keys},
        "changed": {
            key: {"old": old[key], "new": new[key]}
            for key in changed_keys
        },
    }


class Dd55318U2019WordAnnoBoundaryTransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        cls.current_maps = {
            language: json.loads(
                out_word_anno_path(language).read_text(encoding="utf-8")
            )
            for language in LANGUAGES
        }

    def test_schema_and_policy_are_closed(self):
        self.assertEqual(
            set(self.ledger),
            {
                "schema_version", "ledger_id", "description", "authority",
                "parent", "candidate", "delta", "languages", "policy",
            },
        )
        self.assertEqual(self.ledger["schema_version"], 1)
        self.assertEqual(
            self.ledger["ledger_id"],
            "word-anno-boundary-dd55318-u2019-successor-v1",
        )
        self.assertEqual(set(self.ledger["languages"]), set(LANGUAGES))

        delta = self.ledger["delta"]
        self.assertEqual(delta["transform"], "U+0027_TO_U+2019")
        self.assertEqual(delta["source_surface"], "Fukuwarai'")
        self.assertEqual(delta["candidate_surface"], "Fukuwarai\u2019")
        self.assertEqual([ord(char) for char in delta["candidate_surface"][-1]], [0x2019])
        self.assertEqual(delta["source_target"], "Fukuwarai/'")
        self.assertEqual(delta["candidate_target"], "Fukuwarai/\u2019")
        self.assertEqual(delta["typed_roles"], "RL")
        self.assertEqual(delta["added_keys"], [delta["candidate_context_key"]])

        policy = self.ledger["policy"]
        self.assertEqual(
            policy,
            {
                "derived_from_sealed_ascii_rule": True,
                "only_unicode_substitution": "U+0027_TO_U+2019",
                "observed_raw_surface_required": True,
                "exact_only": True,
                "word_boundary_required": True,
                "case_sensitive": True,
                "typed_roles_required": True,
                "ruby_only": True,
                "wildcard_or_substring_authorization": False,
                "kanji_track_changed": False,
                "learner_master_changed": False,
                "corpus_changed": False,
                "three_language_boundary_identity_required": True,
                "glosses_remain_language_local": True,
                "historical_ledgers_rewritten": False,
            },
        )

    def test_historical_authorities_form_an_immutable_successor_chain(self):
        authority = self.ledger["authority"]
        ccb = read_authority(authority["historical_ccb9398_transition"])
        source = read_authority(authority["corpus_source_transition"])
        r94 = read_authority(authority["r94_residual_ledger"])

        parent = self.ledger["parent"]
        self.assertEqual(
            ccb["candidate"],
            {
                key: parent[key]
                for key in (
                    "canonical_payload_sha256", "authority_keys",
                    "authority_sha256", "expected_key_counts",
                )
            },
        )
        self.assertEqual(
            source["active_manifests"]["word_anno_boundary"],
            {
                "path": parent["manifest_path"],
                "file_sha256": parent["file_sha256"],
                "canonical_payload_sha256": parent[
                    "canonical_payload_sha256"
                ],
                "authority_keys": parent["authority_keys"],
                "authority_sha256": parent["authority_sha256"],
                "expected_key_counts": parent["expected_key_counts"],
            },
        )
        self.assertEqual(
            source["corpus"]["candidate"],
            {
                key: authority["corpus"][key]
                for key in ("head_oid", "tree_oid", "content_sha256")
            },
        )
        self.assertEqual(
            source["corpus"]["branch"], authority["corpus"]["branch"],
        )

        ascii_policy = r94["policy"]["managed_typed_exact_targets"]
        self.assertEqual(
            ascii_policy,
            {
                self.ledger["delta"]["source_surface"]: {
                    "target": self.ledger["delta"]["source_target"],
                    "typed_roles": "RL",
                    "case_sensitive": True,
                    "ruby_only": True,
                }
            },
        )
        self.assertNotIn(
            self.ledger["delta"]["candidate_surface"], ascii_policy,
            "the U+2019 successor must not rewrite the sealed R94 policy",
        )

    def test_active_manifest_and_both_word_anno_copies_are_the_candidate(self):
        candidate = self.ledger["candidate"]
        active_path = ROOT / candidate["manifest_path"]
        active = json.loads(active_path.read_text(encoding="utf-8"))
        self.assertEqual(file_sha256(active_path), candidate["file_sha256"])
        self.assertEqual(
            canonical_sha256(active), candidate["canonical_payload_sha256"],
        )
        for key in (
            "authority_keys", "authority_sha256", "expected_key_counts",
        ):
            self.assertEqual(active[key], candidate[key], key)

        for language in LANGUAGES:
            deployed = json.loads(
                app_word_anno_path(language).read_text(encoding="utf-8")
            )
            self.assertEqual(deployed, self.current_maps[language], language)
        self.assertEqual(boundary.build(self.current_maps), active)

    def test_candidate_is_exactly_one_context_key_beyond_parent(self):
        delta = self.ledger["delta"]
        source_key = delta["source_context_key"]
        candidate_key = delta["candidate_context_key"]
        parent_maps = copy.deepcopy(self.current_maps)

        for language in LANGUAGES:
            current = self.current_maps[language]
            expected_language = self.ledger["languages"][language]
            self.assertTrue(
                source_key in current,
                f"{language}: missing sealed ASCII source key {source_key!r}",
            )
            self.assertTrue(
                candidate_key in current,
                f"{language}: missing U+2019 candidate key {candidate_key!r}",
            )
            self.assertEqual(current[source_key], expected_language["source_value"])
            self.assertEqual(
                current[candidate_key], expected_language["candidate_value"],
            )
            self.assertEqual(current[candidate_key], current[source_key])
            removed = parent_maps[language].pop(candidate_key)
            self.assertEqual(removed, current[source_key])

        rebuilt_parent = boundary.build(parent_maps)
        parent = self.ledger["parent"]
        self.assertEqual(
            canonical_sha256(rebuilt_parent), parent["canonical_payload_sha256"],
        )
        for key in (
            "authority_keys", "authority_sha256", "expected_key_counts",
        ):
            self.assertEqual(rebuilt_parent[key], parent[key], key)

        rebuilt_candidate_maps = copy.deepcopy(parent_maps)
        for language in LANGUAGES:
            rebuilt_candidate_maps[language][candidate_key] = copy.deepcopy(
                rebuilt_candidate_maps[language][source_key]
            )
        self.assertEqual(rebuilt_candidate_maps, self.current_maps)

        rebuilt_candidate = boundary.build(rebuilt_candidate_maps)
        candidate = self.ledger["candidate"]
        self.assertEqual(
            canonical_sha256(rebuilt_candidate),
            candidate["canonical_payload_sha256"],
        )
        for key in (
            "authority_keys", "authority_sha256", "expected_key_counts",
        ):
            self.assertEqual(rebuilt_candidate[key], candidate[key], key)

        for language in LANGUAGES:
            observed = map_delta(parent_maps[language], self.current_maps[language])
            expected = self.ledger["languages"][language]
            self.assertEqual(set(observed["added"]), {candidate_key})
            self.assertEqual(len(observed["added"]), expected["added"])
            self.assertEqual(len(observed["removed"]), expected["removed"])
            self.assertEqual(sorted(observed["changed"]), expected["changed_keys"])
            self.assertEqual(
                canonical_sha256(observed), expected["canonical_diff_sha256"],
            )

    def test_reconstructed_parent_still_matches_the_full_ccb9398_delta(self):
        ccb = read_authority(
            self.ledger["authority"]["historical_ccb9398_transition"]
        )
        candidate_key = self.ledger["delta"]["candidate_context_key"]
        parent_maps = copy.deepcopy(self.current_maps)
        for language in LANGUAGES:
            self.assertTrue(
                candidate_key in parent_maps[language],
                f"{language}: missing U+2019 candidate key {candidate_key!r}",
            )
            parent_maps[language].pop(candidate_key)

        baseline_commit = ccb["parent"]["app_commit"]
        expected_added = set(ccb["added_keys"])
        for language in LANGUAGES:
            relative = app_word_anno_path(language).relative_to(ROOT).as_posix()
            old_raw = subprocess.check_output(
                ["git", "show", f"{baseline_commit}:{relative}"], cwd=ROOT,
            )
            baseline = json.loads(old_raw)
            observed = map_delta(baseline, parent_maps[language])
            expected = ccb["languages"][language]
            with self.subTest(language=language):
                self.assertEqual(set(observed["added"]), expected_added)
                self.assertEqual(len(observed["added"]), expected["added"])
                self.assertEqual(len(observed["removed"]), expected["removed"])
                self.assertEqual(
                    sorted(observed["changed"]), expected["changed_keys"],
                )
                self.assertEqual(
                    canonical_sha256(observed),
                    expected["canonical_diff_sha256"],
                )

    def test_runtime_rule_is_exact_case_sensitive_bounded_and_ruby_only(self):
        delta = self.ledger["delta"]
        expected_entry = delta["confirmed_entry"]
        confirmed = json.loads(
            (HERE / "out" / "confirmed_tier30.json").read_text(
                encoding="utf-8"
            )
        )
        matches = [row for row in confirmed if row.get("w") == expected_entry["w"]]
        self.assertEqual(matches, [expected_entry])
        self.assertNotIn("allow_substring", matches[0])
        self.assertNotIn("kanji_track_only", matches[0])
        self.assertNotIn("ruby_track_only", matches[0])

        expected_setting = delta["settings_row"]
        for language in LANGUAGES:
            settings = json.loads(
                settings_path(language).read_text(encoding="utf-8")
            )
            matches = [
                row for row in settings
                if isinstance(row, list) and len(row) == 3
                and row[0] == expected_setting[0]
            ]
            with self.subTest(language=language):
                self.assertEqual(matches, [expected_setting])
                self.assertEqual(
                    set(matches[0][2]),
                    {
                        "ne", "word_boundary", "case_sensitive",
                        "typed_roles:RL", "ruby_only",
                    },
                )

    def test_dd55318_corpus_contains_the_one_authorized_raw_surface(self):
        raw_path = os.environ.get("ESP_CORPUS_PATH", "").strip()
        self.assertTrue(raw_path, "ESP_CORPUS_PATH is required")
        corpus_root = Path(raw_path).resolve()
        state, fingerprint = raw_apostrophe.verify_pinned_corpus(corpus_root)
        authority = self.ledger["authority"]["corpus"]
        self.assertEqual(state["head_oid"], authority["head_oid"])
        self.assertEqual(fingerprint["sha256"], authority["content_sha256"])

        cases, _counts = raw_apostrophe.collect_cases(corpus_root)
        surface = self.ledger["delta"]["candidate_surface"]
        observed = self.ledger["delta"]["observed_corpus"]
        self.assertIn(surface, cases)
        self.assertEqual(cases[surface]["count"], observed["instances"])
        self.assertEqual(
            [raw_apostrophe.display_signature(signature)
             for signature in cases[surface]["signatures"]],
            [observed["expected_typed"]],
        )
        self.assertEqual(
            dict(cases[surface]["paths"]),
            {
                context["path"]: context["count"]
                for context in observed["contexts"]
            },
        )


if __name__ == "__main__":
    unittest.main()
