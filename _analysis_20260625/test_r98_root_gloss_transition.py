# -*- coding: utf-8 -*-
"""Fail-closed tests for the exact R95/R96/R98 gloss carry-forward."""
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

import build_r98_root_gloss_transition_ledger as builder


R94_COMMIT = "15e2f7fc19db08e332a797c9703019790ea23c36"
LANGUAGES = builder.LANGUAGES
LISTS = builder.LISTS
PAYLOAD_NAME = builder.PAYLOAD_NAME
KANJI_ARTIFACTS = {
    "JA": ("置換リスト_漢字.json", "置換リスト_漢字_純粋置換.json"),
    "ZH": ("置換リスト_漢字.json",),
    "KO": ("置換リスト_漢字.json",),
}


def git_blob(commit: str, relative_path: str) -> bytes:
    return subprocess.check_output(
        ["git", "show", f"{commit}:{relative_path}"], cwd=ROOT,
    )


def payload_relative_path(language: str) -> str:
    return f"Esperanto-Kanji-Ruby-{language}/app_data/{PAYLOAD_NAME}"


def current_payload(language: str) -> dict:
    path = ROOT / payload_relative_path(language)
    return json.loads(path.read_text(encoding="utf-8"))


def committed_payload(commit: str, language: str) -> dict:
    return json.loads(
        git_blob(commit, payload_relative_path(language)).decode("utf-8")
    )


def selected_source_index(rows: list, wanted: set[str]) -> dict[str, list]:
    result = {}
    for row in rows:
        if not (
            isinstance(row, list)
            and len(row) >= 2
            and isinstance(row[0], str)
        ):
            continue
        if row[0] not in wanted:
            continue
        if row[0] in result:
            raise AssertionError(f"duplicate source key: {row[0]!r}")
        result[row[0]] = row
    return result


def rendered_surface(value: str) -> str:
    result = []
    pos = 0
    for match in builder.RUBY.finditer(value):
        result.append(builder.TAG.sub("", value[pos:match.start()]))
        result.append(builder.clean_base(match.group(1)))
        pos = match.end()
    result.append(builder.TAG.sub("", value[pos:]))
    return "".join(result)


def authorization(ledger: dict, language: str) -> dict:
    result = {}
    for item in ledger["confirmed"]:
        root = item["root"]
        for row in item["transitions"][language]:
            token = (row["list"], row["key"])
            if token in result:
                raise AssertionError(f"duplicate authorized row: {language}/{token!r}")
            result[token] = {
                segment["index"]: (
                    root, segment["before"], segment["after"],
                )
                for segment in row["segments"]
            }
    return result


class R98RootGlossTransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger_raw = builder.LEDGER_PATH.read_bytes()
        cls.ledger = json.loads(cls.ledger_raw.decode("utf-8"))

    def test_ledger_schema_counts_policy_and_seal(self):
        self.assertEqual(self.ledger["schema_version"], 1)
        self.assertEqual(
            self.ledger["ledger_id"],
            "r95-r96-r98-root-gloss-exact-transition-v1",
        )
        self.assertEqual(self.ledger["summary"]["roots"], 37)
        self.assertEqual(
            self.ledger["summary"]["changed_rows"],
            builder.EXPECTED_CHANGED_ROWS,
        )
        self.assertEqual(
            {item["root"] for item in self.ledger["confirmed"]},
            builder.EXPECTED_ROOTS,
        )
        self.assertEqual(
            hashlib.sha256(self.ledger_raw).hexdigest().upper(),
            builder.EXPECTED_LEDGER_SHA256,
        )
        policy = self.ledger["policy"]
        self.assertTrue(policy["ruby_only"])
        self.assertTrue(policy["gloss_and_size_class_only"])
        self.assertTrue(policy["source_key_must_remain_exact"])
        self.assertTrue(policy["list_bucket_must_remain_exact"])
        self.assertTrue(policy["ruby_segment_index_must_remain_exact"])
        self.assertFalse(policy["wildcard_or_substring_authorization"])
        self.assertFalse(policy["boundary_change_authorized"])
        self.assertFalse(policy["kanji_change_authorized"])
        segment_count = 0
        for item in self.ledger["confirmed"]:
            for language in LANGUAGES:
                for row in item["transitions"][language]:
                    for segment in row["segments"]:
                        self.assertEqual(set(segment), {
                            "index", "before", "after",
                            "before_rendered", "after_rendered",
                        })
                        self.assertNotEqual(
                            segment["before_rendered"],
                            segment["after_rendered"],
                        )
                        segment_count += 1
        self.assertEqual(segment_count, sum(
            self.ledger["summary"]["changed_segments"].values()
        ))

    def test_only_authorized_r94_rows_changed_and_match_upstream_target(self):
        for language in LANGUAGES:
            with self.subTest(language=language):
                deployed = current_payload(language)
                r94 = committed_payload(R94_COMMIT, language)
                upstream = committed_payload(builder.TARGET_COMMIT, language)
                allowed = authorization(self.ledger, language)
                actual = set()
                for key in deployed:
                    if key not in LISTS.values():
                        self.assertEqual(deployed[key], r94[key], key)
                for code, list_name in LISTS.items():
                    deployed_rows = deployed[list_name]
                    r94_rows = r94[list_name]
                    self.assertEqual(len(deployed_rows), len(r94_rows))
                    wanted = {
                        source for pair_code, source in allowed
                        if pair_code == code
                    }
                    upstream_by_source = selected_source_index(
                        upstream[list_name], wanted,
                    )
                    self.assertEqual(set(upstream_by_source), wanted)
                    for deployed_row, r94_row in zip(deployed_rows, r94_rows):
                        if deployed_row == r94_row:
                            continue
                        self.assertEqual(deployed_row[0], r94_row[0])
                        self.assertEqual(deployed_row[2:], r94_row[2:])
                        token = (code, deployed_row[0])
                        self.assertIn(token, allowed)
                        self.assertIn(deployed_row[0], upstream_by_source)
                        self.assertEqual(
                            deployed_row[1],
                            upstream_by_source[deployed_row[0]][1],
                        )
                        actual.add(token)
                self.assertEqual(actual, set(allowed))
                self.assertEqual(
                    len(actual),
                    builder.EXPECTED_CHANGED_ROWS[language],
                )

    def test_authorized_after_glosses_and_boundaries_are_exact_in_all_languages(self):
        allowed = {
            language: authorization(self.ledger, language)
            for language in LANGUAGES
        }
        union = set().union(*(set(rows) for rows in allowed.values()))
        boundary = {language: {} for language in LANGUAGES}
        for language in LANGUAGES:
            deployed = current_payload(language)
            for code, list_name in LISTS.items():
                wanted = {key for pair_code, key in union if pair_code == code}
                selected = selected_source_index(deployed[list_name], wanted)
                self.assertEqual(set(selected), wanted)
                for source, row in selected.items():
                    segments = builder.ruby_segments(row[1])
                    boundary[language][(code, source)] = tuple(
                        segment["base"] for segment in segments
                    )
                    self.assertEqual(
                        rendered_surface(row[1]).strip(),
                        source.strip(),
                    )
                    for index, (root, _before, after) in allowed[language].get(
                        (code, source), {}
                    ).items():
                        self.assertLess(index, len(segments))
                        self.assertEqual(segments[index]["base"].lower(), root)
                        self.assertEqual(segments[index]["gloss"], after)
        for token in union:
            with self.subTest(token=token):
                signatures = {
                    boundary[language][token] for language in LANGUAGES
                }
                self.assertEqual(len(signatures), 1)

    def test_kanji_artifacts_remain_byte_identical_to_r94(self):
        for language in LANGUAGES:
            for name in KANJI_ARTIFACTS[language]:
                relative = f"Esperanto-Kanji-Ruby-{language}/app_data/{name}"
                with self.subTest(language=language, name=name):
                    self.assertEqual(
                        (ROOT / relative).read_bytes(),
                        git_blob(R94_COMMIT, relative),
                    )

    def test_formal_pipeline_checks_authority_before_writes_and_applies_last(self):
        source = (HERE / "regenerate_all.py").read_text(encoding="utf-8")
        builder_check = source.index(
            "'build_r98_root_gloss_transition_ledger.py'"
        )
        first_writer = source.index(
            "'capture', '--output', R67_R68_OVERLAY_SNAPSHOT"
        )
        r93 = source.index("'fix_ruby_sense_by_kanji.py'")
        r98 = source.index("'fix_ruby_root_gloss_mixup.py'", r93)
        final_overlay_audit = source.index(
            "'audit', '--expected-global-rows', '573299'", r98
        )
        transaction_test = source.index("'test_r98_payload_transaction.py'", r98)
        unit_test = source.index(
            "'test_r98_root_gloss_transition.py'", transaction_test,
        )
        successor_gate = source.index("'post_r98_no_worsening_gate.py'", unit_test)
        self.assertLess(builder_check, first_writer)
        self.assertLess(r93, r98)
        self.assertLess(r98, final_overlay_audit)
        self.assertLess(final_overlay_audit, transaction_test)
        self.assertLess(transaction_test, unit_test)
        self.assertLess(unit_test, successor_gate)
        self.assertIn("'--targets', R98_ROOT_GLOSS_LEDGER", source)
        self.assertIn("'--apply', '--no-backup'", source[r98:r98 + 400])
        self.assertNotIn(
            "'build_r98_root_gloss_transition_ledger.py'),\n"
            "        '--write'",
            source,
        )

    def test_fixer_uses_sealed_exact_transaction_not_sequential_writes(self):
        source = (HERE / "fix_ruby_root_gloss_mixup.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("EXPECTED_LEDGER_SHA256", source)
        self.assertIn("before_rendered", source)
        self.assertIn("after_rendered", source)
        self.assertIn("apply_payload_transaction(", source)
        self.assertIn("candidate_validator=validate_candidates", source)
        self.assertIn("keep_permanent_backups=not A.no_backup", source)
        self.assertIn("validate_report_path(", source)
        self.assertNotIn("atomic_json_dump", source)
        self.assertNotIn("atomic_file_copy", source)


if __name__ == "__main__":
    unittest.main()
