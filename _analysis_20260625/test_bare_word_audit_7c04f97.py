# -*- coding: utf-8 -*-
import collections
import importlib.util
import json
import os
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("bare_word_audit_7c04f97.py")
SPEC = importlib.util.spec_from_file_location(
    "bare_word_audit_7c04f97_under_test",
    MODULE_PATH,
)
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def anchored_record(
    path="sample.html",
    line=10,
    token="alpha",
    kind="esperanto_word",
    line_class="annotated_body",
    context="[R] alpha [R]",
    count=1,
):
    record = {
        "line": line,
        "line_class": line_class,
        "context": context,
        "token_counts": {token: count},
    }
    anchor = AUDIT.anchor_from_record(record, token, kind, count)
    return (path, token), record, anchor


def one_entry_fixture():
    key, record, anchor = anchored_record()
    entry = {
        "path": key[0],
        "token": key[1],
        "lines": [anchor["line"]],
        "expected_count": 1,
        "category": "test",
        "reason": "test fixture",
        "anchors": [anchor],
    }
    candidate = {
        "path": key[0],
        "line": anchor["line"],
        "token": key[1],
        "kind": anchor["kind"],
        "line_class": anchor["line_class"],
        "context": "legacy-truncated-context-is-not-authoritative",
    }
    ledger = {
        "counts": {
            "candidate_occurrences": 1,
            "reviewed_occurrences": 1,
        },
        "entries": [entry],
        "scope_transitions": [],
    }
    records = {(key[0], anchor["line"]): record}
    return ledger, [candidate], records


class BareWordSchema3StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = AUDIT.load_json(AUDIT.LEDGER_PATH)
        cls.parent = AUDIT.load_json(AUDIT.PARENT_LEDGER_PATH)

    def test_parent_ledger_is_hash_pinned(self):
        self.assertEqual(
            AUDIT.file_sha256(AUDIT.PARENT_LEDGER_PATH),
            AUDIT.PARENT_LEDGER_SHA256,
        )

    def test_schema3_authority_hash_remains_sealed(self):
        self.assertEqual(
            AUDIT.file_sha256(AUDIT.LEDGER_PATH),
            AUDIT.LEDGER_SHA256,
        )

    def test_complete_transition_partition_is_valid(self):
        AUDIT.validate_ledger_structure(self.ledger, self.parent)
        self.assertEqual(self.ledger["counts"], AUDIT.EXPECTED_COUNTS)
        self.assertEqual(len(self.ledger["entries"]), 204)
        self.assertEqual(len(self.ledger["scope_transitions"]), 5)

    def test_ten_shortened_contexts_are_explicit(self):
        actual = {
            (row["path"], row["token"])
            for row in self.ledger["entries"]
            if row["transition"]["disposition"]
            == "reanchor_split_context_reviewed"
        }
        self.assertEqual(actual, AUDIT.EXPECTED_SPLIT_CONTEXT_KEYS)
        self.assertEqual(len(actual), 10)
        for row in self.ledger["entries"]:
            if (row["path"], row["token"]) not in actual:
                continue
            old_anchor = row["transition"]["parent_anchors"][0]
            new_anchor = row["anchors"][0]
            self.assertLess(
                new_anchor["context_length"],
                old_anchor["context_length"],
            )
            self.assertNotEqual(
                new_anchor["context_sha256"],
                old_anchor["context_sha256"],
            )

    def test_five_class_transitions_are_explicit_and_still_required(self):
        actual = {
            (row["path"], row["token"]): row
            for row in self.ledger["scope_transitions"]
        }
        self.assertEqual(set(actual), set(AUDIT.EXPECTED_SCOPE_TRANSITIONS))
        for key, row in actual.items():
            self.assertTrue(row["required_raw_presence"])
            self.assertEqual(
                row["disposition"],
                "still_present_reviewed_source_term",
            )
            self.assertEqual(
                {anchor["line_class"] for anchor in row["parent_anchors"]},
                {"annotated_body"},
            )
            self.assertEqual(
                {anchor["line_class"] for anchor in row["current_anchors"]},
                {"translation_or_note"},
            )
            self.assertEqual(
                row["current_lines"],
                AUDIT.EXPECTED_SCOPE_TRANSITIONS[key]["current_lines"],
            )

    def test_context_hash_policy_forbids_truncation(self):
        policy = self.ledger["context_hash"]
        self.assertIs(policy["truncated"], False)
        self.assertIn("Full normalized visible line", policy["context_projection"])
        self.assertEqual(
            policy["fields"],
            ["context", "kind", "line_class"],
        )
        anchored_lengths = [
            anchor["context_length"]
            for row in self.ledger["entries"]
            for anchor in (
                row["anchors"] + row["transition"]["parent_anchors"]
            )
        ] + [
            anchor["context_length"]
            for row in self.ledger["scope_transitions"]
            for anchor in row["current_anchors"]
        ]
        self.assertGreater(max(anchored_lengths), 500)


class BareWordSchema3FailClosedTests(unittest.TestCase):
    def test_exact_fixture_passes(self):
        ledger, candidates, records = one_entry_fixture()
        report = AUDIT.evaluate_coverage(
            ledger,
            candidates,
            records,
            collections.Counter(),
        )
        self.assertTrue(report["coverage_gate"])

    def test_new_candidate_fails_closed(self):
        ledger, candidates, records = one_entry_fixture()
        candidates.append({
            "path": "sample.html",
            "line": 11,
            "token": "novel",
            "kind": "esperanto_word",
            "line_class": "annotated_body",
            "context": "novel",
        })
        report = AUDIT.evaluate_coverage(
            ledger,
            candidates,
            records,
            collections.Counter(),
        )
        self.assertFalse(report["coverage_gate"])
        self.assertEqual(len(report["new_candidates"]), 1)

    def test_unused_entry_fails_closed(self):
        ledger, _candidates, records = one_entry_fixture()
        report = AUDIT.evaluate_coverage(
            ledger,
            [],
            records,
            collections.Counter(),
        )
        self.assertFalse(report["coverage_gate"])
        self.assertEqual(
            report["unused_entries"],
            [{"path": "sample.html", "token": "alpha"}],
        )

    def test_mutated_full_context_anchor_fails_closed(self):
        ledger, candidates, records = one_entry_fixture()
        records[("sample.html", 10)] = {
            **records[("sample.html", 10)],
            "context": "[R] alpha [R] silently changed after character 500",
        }
        report = AUDIT.evaluate_coverage(
            ledger,
            candidates,
            records,
            collections.Counter(),
        )
        self.assertFalse(report["coverage_gate"])
        self.assertEqual(len(report["mutated_anchors"]), 1)

    def test_scope_transition_token_disappearance_fails_closed(self):
        key, record, anchor = anchored_record(
            path="scope.html",
            line=20,
            token="dol",
            kind="esperanto_word",
            line_class="translation_or_note",
            context="[R] dol [R]",
        )
        ledger = {
            "counts": {
                "candidate_occurrences": 0,
                "reviewed_occurrences": 0,
            },
            "entries": [],
            "scope_transitions": [{
                "path": key[0],
                "token": key[1],
                "current_anchors": [anchor],
                "file_visible_count": 1,
            }],
        }
        records = {
            (key[0], 20): {
                **record,
                "context": "[R] [R]",
                "token_counts": {},
            }
        }
        report = AUDIT.evaluate_coverage(
            ledger,
            [],
            records,
            collections.Counter(),
        )
        self.assertFalse(report["coverage_gate"])
        self.assertTrue(report["scope_transition_mismatches"])

    def test_head_and_content_pin_mismatches_are_reported(self):
        observed = dict(AUDIT.SOURCE_PIN)
        observed["head_oid"] = "0" * 40
        observed["content_sha256"] = "F" * 64
        errors = AUDIT.source_pin_errors(AUDIT.SOURCE_PIN, observed)
        self.assertEqual(
            {row["field"] for row in errors},
            {"head_oid", "content_sha256"},
        )


class BareWordSchema3RealCorpusTests(unittest.TestCase):
    def test_real_latest_scope_when_explicitly_available(self):
        raw = (
            os.environ.get("ESP_BARE_WORD_7C04F97_TEST_CORPUS")
            or os.environ.get("ESP_CORPUS_PATH")
        )
        if not raw:
            self.skipTest("no explicit latest corpus checkout")
        corpus = Path(raw).resolve()
        try:
            state = AUDIT.git_repo_state(corpus)
        except AUDIT.AuditError as exc:
            self.skipTest(f"not a usable Git corpus checkout: {exc}")
        if state["head_oid"] != AUDIT.SOURCE_PIN["head_oid"]:
            self.skipTest("ESP_CORPUS_PATH is not the pinned 7c04f97 checkout")
        report = AUDIT.audit_corpus(corpus)
        self.assertTrue(report["gate"], json.dumps(report, ensure_ascii=False))
        self.assertEqual(report["active_entries"], 204)
        self.assertEqual(report["candidate_occurrences"], 236)
        self.assertEqual(report["reviewed_occurrences"], 236)
        self.assertEqual(report["scope_transitions"], 5)
        self.assertTrue(report["bare_projection_sealed"])
        self.assertEqual(
            report["bare_projection_sha256"],
            AUDIT.BARE_PROJECTION_SHA256,
        )

    def test_d164_annotated_change_preserves_bare_projection(self):
        parent_raw = (
            os.environ.get("ESP_BARE_WORD_7C04F97_TEST_CORPUS")
            or os.environ.get("ESP_CORPUS_PATH")
        )
        successor_raw = (
            os.environ.get("ESP_BARE_WORD_D164_TEST_CORPUS")
            or os.environ.get("ESP_BARE_WORD_D164_CORPUS_PATH")
        )
        if not parent_raw or not successor_raw:
            self.skipTest("explicit 7c04 and d164 corpus checkouts are required")
        report = AUDIT.audit_successor_bare_projection(
            Path(parent_raw).resolve(),
            Path(successor_raw).resolve(),
        )
        self.assertTrue(report["gate"], json.dumps(report, ensure_ascii=False))
        self.assertTrue(report["projection_identical"])
        self.assertTrue(report["sealed_projection"])
        self.assertEqual(
            report["parent_bare_projection"]["sha256"],
            AUDIT.BARE_PROJECTION_SHA256,
        )
        self.assertEqual(
            report["successor_bare_projection"]["sha256"],
            AUDIT.BARE_PROJECTION_SHA256,
        )
        transition = report["annotation_transition"]
        self.assertTrue(transition["gate"])
        self.assertEqual(
            transition["changed_content_files"],
            [AUDIT.INICIATORO_CHANGE_PATH],
        )
        self.assertEqual(transition["annotated_surface_occurrences"], 1)
        self.assertEqual(transition["parent_roots"], ["iniciat", "or"])
        self.assertEqual(transition["successor_roots"], ["iniciator"])
        self.assertEqual(transition["ruby_element_delta"], -1)
        self.assertTrue(transition["visible_base_text_identical"])


if __name__ == "__main__":
    unittest.main()
