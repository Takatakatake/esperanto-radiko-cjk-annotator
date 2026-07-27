# -*- coding: utf-8 -*-
"""Safety tests for the fail-closed b769 -> 7c04 corpus transition review."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_corpus_7c04_transition_review as review  # noqa: E402


class Corpus7c04TransitionReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.committed = json.loads(
            review.DEFAULT_REVIEW.read_text(encoding="utf-8")
        )

    def test_committed_ledger_has_fixed_authority_and_pass_gate(self):
        review.validate_authority(self.committed)
        self.assertIs(self.committed["gate"]["pass"], True)
        self.assertEqual(
            self.committed["file_set"],
            {"added": [], "removed": [], "renamed": []},
        )
        old = self.committed["source"]["old"]
        new = self.committed["source"]["new"]
        self.assertEqual((old["all_html_files"], old["files"]), (172, 169))
        self.assertEqual((new["all_html_files"], new["files"]), (172, 169))
        self.assertEqual((old["raw_ruby"], new["raw_ruby"]), (348971, 348581))
        self.assertEqual((old["parsed_units"], new["parsed_units"]), (271065, 270763))

    def test_authority_rejects_pin_or_count_tampering(self):
        for path, bad_value in (
            (("source", "new", "head_oid"), "0" * 40),
            (("source", "new", "raw_ruby"), 348580),
            (("ruby_transition", "duplicate_removal", "removed_ruby_total"), 389),
            (("ruby_transition", "spelling_corrections", "instances"), 16),
            (("ruby_transition", "annotation_corrections", "instances"), 3),
            (("ruby_transition", "unexplained_added_records"), 1),
        ):
            tampered = copy.deepcopy(self.committed)
            target = tampered
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = bad_value
            with self.subTest(path=path):
                with self.assertRaises(review.TransitionReviewError):
                    review.validate_authority(tampered)

    def test_exact_ledger_comparison_rejects_detail_tampering(self):
        tampered = copy.deepcopy(self.committed)
        tampered["ruby_transition"]["spelling_corrections"]["rows"][0][
            "new"
        ]["rb"] = "ŝancX"
        # Summary-only authority remains fixed; the independent recomputation
        # must still reject the changed reviewed row.
        review.validate_authority(tampered)
        with self.assertRaisesRegex(
            review.TransitionReviewError, "differs from committed ledger"
        ):
            review.require_review_match(tampered, self.committed)

    def test_duplicate_proof_requires_one_adjacent_two_to_one_block(self):
        prefix = [review.record("p", "P", "S_S")]
        block = [
            review.record("a", "A", "S_S"),
            review.record("b", "B", "M_M"),
        ]
        suffix = [review.record("s", "S", "L_L")]
        old = prefix + block + block + suffix
        new = prefix + block + suffix
        found, old_hits, new_hits = review.prove_duplicate_transition(
            old, new, block_size=2
        )
        self.assertEqual(found, block)
        self.assertEqual(old_hits, [1, 3])
        self.assertEqual(new_hits, [1])

        with self.assertRaises(review.TransitionReviewError):
            review.prove_duplicate_transition(
                old,
                prefix + [review.record("x", "X", "S_S")] + suffix,
                block_size=2,
            )

    def test_ruby_parser_rejects_unparsed_or_rb_markup(self):
        valid = '<ruby>radik<rt class="S_S">根</rt></ruby>'
        records, raw = review.extract_ruby_records(valid, "valid.html")
        self.assertEqual(len(records), 1)
        self.assertEqual(raw["ruby_open"], 1)

        malformed = '<ruby>radik<rt class="S_S">根</ruby>'
        with self.assertRaises(review.TransitionReviewError):
            review.extract_ruby_records(malformed, "malformed.html")

        explicit_rb = (
            '<ruby><rb>radik</rb><rt class="S_S">根</rt></ruby>'
        )
        with self.assertRaises(review.TransitionReviewError):
            review.extract_ruby_records(explicit_rb, "rb.html")

    def test_git_state_rejects_dirty_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(
                ["git", "-C", str(root), "config", "user.email", "test@example.com"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(root), "config", "user.name", "Transition Test"],
                check=True,
            )
            tracked = root / "tracked.txt"
            tracked.write_text("fixed\n", encoding="utf-8")
            subprocess.run(
                ["git", "-C", str(root), "add", "tracked.txt"], check=True
            )
            subprocess.run(
                ["git", "-C", str(root), "commit", "-q", "-m", "fixture"],
                check=True,
            )
            state = review.git_repo_state(root)
            self.assertEqual(state["status_entries"], 0)

            (root / "untracked.txt").write_text("dirty\n", encoding="utf-8")
            with self.assertRaisesRegex(
                review.TransitionReviewError, "must be clean"
            ):
                review.git_repo_state(root)

    def test_full_recomputation_matches_ledger_when_checkouts_are_supplied(self):
        old_raw = os.environ.get("ESP_CORPUS_OLD_PATH")
        new_raw = os.environ.get("ESP_CORPUS_NEW_PATH")
        if not old_raw or not new_raw:
            self.skipTest(
                "set ESP_CORPUS_OLD_PATH and ESP_CORPUS_NEW_PATH "
                "for the full 172-file integration check"
            )
        actual = review.finalized_review(
            review.build_transition_review(Path(old_raw), Path(new_raw))
        )
        review.require_review_match(self.committed, actual)


if __name__ == "__main__":
    unittest.main()
