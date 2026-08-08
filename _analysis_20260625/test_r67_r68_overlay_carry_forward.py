#!/usr/bin/env python3
"""Regression tests for the pinned R67/R68 Ruby carry-forward layer."""

from __future__ import annotations

import copy
import tempfile
from pathlib import Path
import unittest

import preserve_r67_r68_ruby_overlays as overlay


class HistoricalRubyOverlayCarryForwardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(
            prefix="esperanto_r67_r68_test_",
        )
        cls.snapshot_path = (
            Path(cls.temporary.name) / "snapshot.json"
        )
        cls.snapshot = overlay.capture_snapshot(
            cls.snapshot_path,
            overlay.PINNED_PARENT_COMMIT,
        )

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_pinned_parent_identity_and_counts(self):
        self.assertEqual(
            self.snapshot["source_identity"],
            {
                "commit": overlay.PINNED_PARENT_COMMIT,
                "tree": overlay.PINNED_PARENT_TREE,
            },
        )
        self.assertEqual(
            self.snapshot["global_rows_at_capture"],
            {
                language: overlay.PINNED_PARENT_GLOBAL_ROWS
                for language in overlay.LANGUAGES
            },
        )
        overlay.validate_overlay_matrix(
            self.snapshot["overlays"],
            "historical-r72-r73",
        )

    def test_parent_rows_round_trip_exactly(self):
        for language in overlay.LANGUAGES:
            with self.subTest(language=language):
                payload = overlay.load_payload(
                    language,
                    overlay.PINNED_PARENT_COMMIT,
                )
                _key, parent_rows = overlay.global_bucket(payload)
                base_rows = [
                    list(row)
                    for row in parent_rows
                    if not (
                        len(row) >= 3
                        and isinstance(row[2], str)
                        and any(
                            f"${prefix}" in row[2]
                            for prefix in overlay.OVERLAY_PREFIXES
                        )
                    )
                ]
                for row in base_rows:
                    if row[0] == overlay.EXACT_OVERRIDE_SOURCE:
                        row[1] = " corrupt "
                        break
                restored = overlay.restore_bucket(
                    language,
                    base_rows,
                    self.snapshot,
                )
                self.assertEqual(restored, parent_rows)

    def test_snapshot_tamper_is_rejected(self):
        tampered = copy.deepcopy(self.snapshot["overlays"])
        tampered["JA"]["R67H"][0][1] += "x"
        with self.assertRaises(ValueError):
            overlay.validate_overlay_matrix(tampered)

    def test_deployed_overlay_closure(self):
        payloads = {
            language: overlay.load_payload(language)
            for language in overlay.LANGUAGES
        }
        report = overlay.audit_payloads(
            payloads,
            overlay.CURRENT_DEPLOYED_GLOBAL_ROWS,
            "current-post-temis",
        )
        self.assertTrue(report["gate"])
        self.assertEqual(
            set(report["global_rows"].values()),
            {overlay.CURRENT_DEPLOYED_GLOBAL_ROWS},
        )


if __name__ == "__main__":
    unittest.main()
