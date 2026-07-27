#!/usr/bin/env python3
"""Regression tests for the pinned R67/R68 Ruby carry-forward layer."""

from __future__ import annotations

import copy
from pathlib import Path
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import preserve_r67_r68_ruby_overlays as overlay
import phase599_temis_context_promotion as phase599_promotion
import phase600_master_ruby_policy as phase600_policy


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
        deployed_counts = {
            language: len(overlay.global_bucket(payload)[1])
            for language, payload in payloads.items()
        }
        self.assertEqual(
            set(deployed_counts.values()),
            {overlay.EXPECTED_POST_PHASE600_GLOBAL_ROWS},
        )

        without_phase600 = {}
        for language in overlay.LANGUAGES:
            stripped, managed = phase600_policy.strip_optional_layer(
                payloads[language],
                language,
                require_present=True,
            )
            self.assertEqual(len(managed), phase600_policy.MANAGED_ROWS)
            _key, stripped_rows = overlay.global_bucket(stripped)
            self.assertEqual(
                len(stripped_rows),
                overlay.EXPECTED_POST_PHASE599_GLOBAL_ROWS,
            )

            # Phase 600 duplicates the 48 historical R68 compound sources.
            # Removing by source would erase those parent rows too.  The
            # dedicated-placeholder strip must leave the complete R68 set.
            r68_sources = {
                f" {surface} "
                for surface in phase600_policy.compound_surfaces()
            }
            historical_r68 = [
                row
                for row in stripped_rows
                if (
                    isinstance(row, list)
                    and len(row) == 3
                    and row[0] in r68_sources
                    and isinstance(row[2], str)
                    and "$R68W" in row[2]
                )
            ]
            self.assertEqual(len(historical_r68), len(r68_sources))
            without_phase600[language] = stripped

        normalized = {}
        for language in overlay.LANGUAGES:
            rows = phase599_promotion.expected_rows(language)
            normalized[language], candidate, state = (
                phase599_promotion.normalize_and_build_payload(
                    without_phase600[language], language, rows,
                )
            )
            self.assertEqual(state["state"], "promoted_canonical")
            self.assertEqual(
                state["later_phase600_rows_preserved"], 0,
            )
            self.assertEqual(candidate, without_phase600[language])

        report = overlay.audit_payloads(
            normalized,
            overlay.EXPECTED_POST_R73_GLOBAL_ROWS,
        )
        self.assertTrue(report["gate"])
        self.assertEqual(
            set(report["global_rows"].values()),
            {overlay.EXPECTED_POST_R73_GLOBAL_ROWS},
        )


if __name__ == "__main__":
    unittest.main()
