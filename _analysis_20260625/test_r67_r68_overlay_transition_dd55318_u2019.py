# -*- coding: utf-8 -*-
"""Fail-closed proof for the dd55318 U+2019 R67/R68 successor.

The pre-restore test seals the raw generator output while it is present.  The
historical test separately rebuilds the immutable overlay authority from the
tracked pre-R81 backups, so it remains useful after restore and postfix runs.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import preserve_r67_r68_ruby_overlays as overlay


LEDGER_PATH = HERE / "_r67_r68_overlay_transition_dd55318_u2019.json"
LANGUAGES = ("JA", "ZH", "KO")
RUBY_PAYLOAD_NAME = "置換リスト_ルビ.json"
HISTORICAL_OVERLAY_PAYLOAD_NAME = (
    "置換リスト_ルビ.json.bak_preR81K"
)
PLACEHOLDER_RE = re.compile(r"\$(\d+)([^$]*)\$")


def compact_sha256(value) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def read_authority(spec: dict) -> dict:
    path = ROOT / spec["path"]
    if file_sha256(path) != spec["file_sha256"]:
        raise AssertionError(f"sealed authority changed: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def payload_path(language: str, name: str = RUBY_PAYLOAD_NAME) -> Path:
    return ROOT / f"Esperanto-Kanji-Ruby-{language}" / "app_data" / name


def global_rows(payload: dict) -> list:
    _key, rows = overlay.global_bucket(payload)
    return rows


def overlays_in(rows: list, prefix: str) -> list:
    return overlay.overlay_rows(rows, prefix)


def reconstruct_predecessor_for_language(
    payload: dict, transition: dict, language: str,
) -> dict:
    candidate = copy.deepcopy(payload)
    bucket_key, rows = overlay.global_bucket(candidate)
    delta = transition["raw_generation_delta"]
    insertion_index = delta["insertion_index"]
    expected_row = delta["added_rows"][language]
    if rows[insertion_index] != expected_row:
        raise AssertionError(
            f"{language}: reviewed U+2019 row moved or changed"
        )
    if sum(row == expected_row for row in rows) != 1:
        raise AssertionError(f"{language}: reviewed U+2019 row multiplicity")
    rows.pop(insertion_index)

    shift = delta["following_placeholder_delta"]
    changed_placeholders = 0
    for row in rows[insertion_index:]:
        if not (
            isinstance(row, list)
            and len(row) >= 3
            and isinstance(row[2], str)
        ):
            continue

        def undo(match: re.Match[str]) -> str:
            nonlocal changed_placeholders
            changed_placeholders += 1
            return (
                f"${int(match.group(1)) - shift}{match.group(2)}$"
            )

        row[2] = PLACEHOLDER_RE.sub(undo, row[2])
    if not changed_placeholders:
        raise AssertionError(f"{language}: no following placeholders shifted")
    candidate[bucket_key] = rows
    return candidate


class Dd55318U2019R67R68OverlayTransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))

    def test_schema_authority_chain_and_policy_are_closed(self):
        self.assertEqual(
            set(self.ledger),
            {
                "schema_version", "transition", "description",
                "source_app_commit", "authority", "profiles",
                "global_rows", "predecessor_raw_payload_sha256",
                "candidate_raw_payload_sha256", "raw_generation_delta",
                "overlay_transition", "target_overlay_identity",
                "kanji_artifacts", "policy",
            },
        )
        self.assertEqual(self.ledger["schema_version"], 1)
        self.assertEqual(
            self.ledger["transition"],
            "r67-r68-overlay-dd55318-u2019-successor-v1",
        )
        self.assertEqual(
            self.ledger["profiles"],
            {"source": "current-ccb9398", "target": "current-dd55318-u2019"},
        )

        historical_spec = self.ledger["authority"][
            "historical_overlay_transition"
        ]
        historical = read_authority(historical_spec)
        self.assertEqual(
            historical["transition"], historical_spec["required_transition"],
        )
        self.assertEqual(
            historical["target_overlay_identity"],
            self.ledger["target_overlay_identity"],
        )
        self.assertEqual(
            historical["global_rows"]["target_after_existing_postfix_layers"],
            self.ledger["global_rows"]["source_deployed"],
        )

        word_spec = self.ledger["authority"][
            "word_anno_successor_transition"
        ]
        word_successor = read_authority(word_spec)
        self.assertEqual(
            word_successor["ledger_id"], word_spec["required_ledger_id"],
        )
        self.assertEqual(
            word_successor["delta"]["added_keys"],
            [word_spec["required_added_key"]],
        )
        self.assertEqual(
            word_successor["delta"]["candidate_context_key"],
            word_spec["required_added_key"],
        )
        self.assertTrue(word_successor["policy"]["ruby_only"])
        self.assertFalse(
            word_successor["policy"]["wildcard_or_substring_authorization"]
        )

        self.assertEqual(
            self.ledger["policy"],
            {
                "historical_overlay_ledger_rewritten": False,
                "word_anno_successor_required": True,
                "only_one_reviewed_u2019_exact_rule_is_added": True,
                "case_sensitive": True,
                "ruby_only": True,
                "wildcard_or_substring_authorization": False,
                "overlay_row_content_must_remain_identical": True,
                "overlay_row_order_must_remain_identical": True,
                "overlay_source_set_must_remain_identical": True,
                "three_language_source_order_must_match": True,
                "kanji_artifacts_must_remain_byte_identical": True,
                "learner_master_changed": False,
                "corpus_changed": False,
            },
        )

    def test_row_arithmetic_allows_only_one_raw_rule(self):
        counts = self.ledger["global_rows"]
        self.assertEqual(
            counts["candidate_raw"] - counts["predecessor_raw"],
            counts["candidate_raw_delta"],
        )
        self.assertEqual(counts["candidate_raw_delta"], 1)
        overlay_count = sum(
            self.ledger["target_overlay_identity"]["JA"][prefix]["count"]
            for prefix in ("R67H", "R68W")
        )
        self.assertEqual(overlay_count, counts["overlay_rows_restored"])
        self.assertEqual(
            counts["candidate_raw"] + overlay_count,
            counts["target_after_overlay_restore"],
        )
        self.assertEqual(
            counts["target_after_overlay_restore"]
            + counts["existing_postfix_rows"],
            counts["target_after_existing_postfix_layers"],
        )
        for language in LANGUAGES:
            self.assertEqual(
                sum(
                    self.ledger["target_overlay_identity"][language][prefix][
                        "count"
                    ]
                    for prefix in ("R67H", "R68W")
                ),
                overlay_count,
            )

        delta = self.ledger["raw_generation_delta"]
        self.assertEqual(delta["added_surface"], "Fukuwarai’")
        self.assertEqual(delta["ascii_authority_surface"], "Fukuwarai'")
        self.assertEqual(delta["word_anno_context_key"], "@typed:Fukuwarai’:0")
        self.assertEqual(delta["target"], "Fukuwarai/’")
        self.assertEqual(delta["typed_roles"], "RL")
        self.assertTrue(delta["exact_only"])
        self.assertTrue(delta["case_sensitive"])
        self.assertTrue(delta["ruby_only"])
        self.assertFalse(delta["wildcard_or_substring_authorization"])
        self.assertEqual(
            set(delta["settings_flags"]),
            {
                "ne", "word_boundary", "case_sensitive",
                "typed_roles:RL", "ruby_only",
            },
        )

    def test_pre_restore_raw_payload_and_parent_reconstruction(self):
        payloads = {
            language: json.loads(
                payload_path(language).read_text(encoding="utf-8")
            )
            for language in LANGUAGES
        }
        counts = {
            language: len(global_rows(payload))
            for language, payload in payloads.items()
        }
        has_overlays = any(
            overlays_in(global_rows(payloads[language]), prefix)
            for language in LANGUAGES
            for prefix in ("R67H", "R68W")
        )
        if has_overlays or set(counts.values()) != {
            self.ledger["global_rows"]["candidate_raw"]
        }:
            self.skipTest(
                "pre-restore-only raw proof; deployed overlay state is checked "
                "by the separate historical identity test"
            )

        delta = self.ledger["raw_generation_delta"]
        for language, payload in payloads.items():
            with self.subTest(language=language):
                self.assertEqual(
                    compact_sha256(payload),
                    self.ledger["candidate_raw_payload_sha256"][language],
                )
                rows = global_rows(payload)
                index = delta["insertion_index"]
                self.assertEqual(rows[index], delta["added_rows"][language])
                self.assertEqual(
                    rows[index + 1][0], f" {delta['ascii_authority_surface']} ",
                )
                self.assertEqual(
                    sum(row[0] == delta["added_source"] for row in rows), 1,
                )
                self.assertFalse(
                    any(
                        isinstance(row, list)
                        and row
                        and isinstance(row[0], str)
                        and row[0].strip() == delta["added_surface"].lower()
                        for row in rows
                    ),
                    "case-sensitive U+2019 rule leaked to lowercase",
                )
                predecessor = reconstruct_predecessor_for_language(
                    payload, self.ledger, language,
                )
                self.assertEqual(
                    len(global_rows(predecessor)),
                    self.ledger["global_rows"]["predecessor_raw"],
                )
                self.assertEqual(
                    compact_sha256(predecessor),
                    self.ledger["predecessor_raw_payload_sha256"][language],
                )

    def test_historical_overlay_identity_rebuilds_without_mutating_it(self):
        expected = self.ledger["target_overlay_identity"]
        matrices = {}
        for language in LANGUAGES:
            historical_payload = json.loads(
                payload_path(
                    language, HISTORICAL_OVERLAY_PAYLOAD_NAME,
                ).read_text(encoding="utf-8")
            )
            rows = global_rows(historical_payload)
            # The formal successor pipeline writes this backup immediately
            # after restoring the unchanged overlays and before R81/postfix
            # layers.  Its row count therefore includes the one reviewed
            # U+2019 raw rule while the overlay identity remains unchanged.
            self.assertEqual(
                len(rows),
                self.ledger["global_rows"]["target_after_overlay_restore"],
            )
            matrices[language] = {}
            for prefix in ("R67H", "R68W"):
                selected = overlays_in(rows, prefix)
                matrices[language][prefix] = selected
                with self.subTest(language=language, prefix=prefix):
                    self.assertEqual(len(selected), expected[language][prefix]["count"])
                    self.assertEqual(
                        compact_sha256(selected),
                        expected[language][prefix]["rows_sha256"],
                    )
                    self.assertEqual(
                        compact_sha256([row[0] for row in selected]),
                        expected[language][prefix]["sources_sha256"],
                    )

        overlay.validate_overlay_matrix(matrices, "current-ccb9398")
        for prefix in ("R67H", "R68W"):
            source_orders = {
                tuple(row[0] for row in matrices[language][prefix])
                for language in LANGUAGES
            }
            self.assertEqual(len(source_orders), 1)

        # If restore has already happened, additionally bind the deployed
        # rows to the same immutable identity.  Raw state legitimately has 0.
        for language in LANGUAGES:
            current_payload = json.loads(
                payload_path(language).read_text(encoding="utf-8")
            )
            current_rows = global_rows(current_payload)
            current_overlays = {
                prefix: overlays_in(current_rows, prefix)
                for prefix in ("R67H", "R68W")
            }
            if not any(current_overlays.values()):
                continue
            with self.subTest(language=language, state="post-restore"):
                for prefix in ("R67H", "R68W"):
                    self.assertEqual(
                        current_overlays[prefix], matrices[language][prefix],
                    )

    def test_kanji_payloads_equal_the_pinned_source_commit_byte_for_byte(self):
        source_commit = self.ledger["source_app_commit"]
        for language, artifacts in self.ledger["kanji_artifacts"].items():
            self.assertTrue(artifacts, language)
            for relative, expected_sha in artifacts.items():
                path = ROOT / relative
                with self.subTest(language=language, path=relative):
                    self.assertEqual(file_sha256(path), expected_sha)
                    historical = subprocess.check_output(
                        ["git", "show", f"{source_commit}:{relative}"],
                        cwd=ROOT,
                    )
                    self.assertEqual(
                        hashlib.sha256(historical).hexdigest().upper(),
                        expected_sha,
                    )


if __name__ == "__main__":
    unittest.main()
