#!/usr/bin/env python3
"""Fail-closed tests for the Phase-600 master-only Ruby layer."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import sys
import unittest


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import no_worsening_audit as audit
import phase599_temis_context_promotion as phase599
import phase600_master_ruby_policy as policy
import phase600_master_ruby_repair as repair


def payload(language: str) -> dict:
    return json.loads(
        repair.payload_path(language).read_text(encoding="utf-8")
    )


class Phase600PolicyTests(unittest.TestCase):
    def test_closed_surface_inventory(self):
        self.assertEqual(len(policy.compound_surfaces()), 48)
        self.assertEqual(len(policy.positive_surfaces()), 50)
        self.assertEqual(len(policy.negative_surfaces()), 21)
        self.assertEqual(len(policy.managed_sources()), 52)
        self.assertEqual(len(set(policy.managed_sources())), 52)
        self.assertEqual(policy.NORMALIZED_GLOBAL_ROWS, 572506)
        self.assertEqual(policy.PROMOTED_GLOBAL_ROWS, 572558)

    def test_trilingual_rows_share_sources_but_not_placeholders(self):
        rows = {
            language: policy.build_expected_rows(
                payload(language), language,
            )
            for language in policy.LANGUAGES
        }
        self.assertTrue(all(len(value) == 52 for value in rows.values()))
        sources = {
            tuple(row[0] for row in rows[language])
            for language in policy.LANGUAGES
        }
        self.assertEqual(len(sources), 1)
        placeholders = [
            row[2]
            for language in policy.LANGUAGES
            for row in rows[language]
        ]
        self.assertEqual(len(placeholders), len(set(placeholders)))

    def test_glu_is_atomic_and_semantically_dedicated(self):
        for language in policy.LANGUAGES:
            row = policy.build_expected_rows(
                payload(language), language,
            )[0]
            self.assertEqual(row[0], " glu-glu-glu ")
            self.assertIn(
                f"<ruby>glu-glu-glu<rt", row[1],
            )
            self.assertIn(policy.GLU_GLOSS[language], row[1])
            self.assertNotIn(
                {
                    "JA": "糊",
                    "ZH": "粘",
                    "KO": "붙이다",
                }[language],
                row[1],
            )

    def test_lowercase_nor_guards_precede_generic_nor(self):
        rows = policy.build_expected_rows(payload("JA"), "JA")
        self.assertEqual(
            [row[0] for row in rows[:4]],
            [
                " glu-glu-glu ",
                " kuku-nor ",
                " lob-nor ",
                " nor ",
            ],
        )
        self.assertIn("</ruby>-nor", rows[1][1])
        self.assertIn("</ruby>-nor", rows[2][1])
        self.assertIn("<ruby>nor<rt", rows[3][1])


class Phase600PayloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.phase599_rows = phase599.validate_trilingual_row_manifests()[
            "rows"
        ]

    def test_candidate_delta_is_global_only_and_ordered(self):
        for language in policy.LANGUAGES:
            base = payload(language)
            local_key, global_key, two_char_key = policy.rule_keys(base)
            normalized, candidate, state = repair.normalize_and_build_payload(
                base, language, self.phase599_rows[language],
            )
            self.assertEqual(state["normalized_global_rows"], 572506)
            self.assertEqual(state["promoted_global_rows"], 572558)
            self.assertIs(candidate[local_key], base[local_key])
            self.assertIs(candidate[two_char_key], base[two_char_key])
            self.assertEqual(
                candidate[global_key][:5],
                self.phase599_rows[language],
            )
            managed = policy.validate_optional_layer(
                candidate, language, require_present=True,
            )
            self.assertEqual(
                candidate[global_key][5:57], managed,
            )
            self.assertEqual(
                normalized[global_key],
                [
                    *base[global_key][:5],
                    *base[global_key][57:],
                ],
            )
            self.assertEqual(candidate, base)
            _normalized2, promoted_from_parent, parent_state = (
                repair.normalize_and_build_payload(
                    normalized,
                    language,
                    self.phase599_rows[language],
                )
            )
            self.assertEqual(parent_state["state"], "unpromoted")
            self.assertTrue(parent_state["needs_write"])
            self.assertEqual(promoted_from_parent, candidate)

    def test_in_memory_candidate_is_idempotent(self):
        for language in policy.LANGUAGES:
            base = payload(language)
            _normalized, candidate, _state = (
                repair.normalize_and_build_payload(
                    base, language, self.phase599_rows[language],
                )
            )
            _normalized2, rebuilt, state2 = (
                repair.normalize_and_build_payload(
                    candidate, language, self.phase599_rows[language],
                )
            )
            self.assertEqual(state2["state"], "promoted_canonical")
            self.assertFalse(state2["needs_write"])
            self.assertEqual(rebuilt, candidate)

    def test_phase599_reaudit_preserves_exact_later_layer(self):
        for language in policy.LANGUAGES:
            base = payload(language)
            _normalized, candidate, _state = (
                repair.normalize_and_build_payload(
                    base, language, self.phase599_rows[language],
                )
            )
            phase599_normalized, phase599_rebuilt, state = (
                phase599.normalize_and_build_payload(
                    candidate,
                    language,
                    self.phase599_rows[language],
                )
            )
            _local_key, global_key, _two_char_key = policy.rule_keys(
                phase599_normalized
            )
            self.assertEqual(
                len(phase599_normalized[global_key]), 572501,
            )
            self.assertEqual(
                state["later_phase600_rows_preserved"], 52,
            )
            self.assertEqual(state["phase599_global_rows"], 572506)
            self.assertEqual(state["deployed_global_rows"], 572558)
            self.assertEqual(state["state"], "promoted_canonical")
            self.assertEqual(phase599_rebuilt, candidate)

    def test_partial_or_tampered_layer_fails_closed(self):
        language = "JA"
        base = payload(language)
        _normalized, candidate, _state = repair.normalize_and_build_payload(
            base, language, self.phase599_rows[language],
        )
        _local_key, global_key, _two_char_key = policy.rule_keys(candidate)
        partial = copy.deepcopy(candidate)
        del partial[global_key][8]
        with self.assertRaisesRegex(ValueError, "managed rows|position"):
            policy.validate_optional_layer(
                partial, language, require_present=True,
            )
        tampered = copy.deepcopy(candidate)
        tampered[global_key][5][1] = " glu-glu-glu "
        with self.assertRaisesRegex(ValueError, "managed rows"):
            policy.validate_optional_layer(
                tampered, language, require_present=True,
            )

    def test_expected_boundary_shapes(self):
        self.assertEqual(
            audit.signature_payload(
                repair._expected_signature("glu-glu-glu")
            ),
            {
                "reconstruction": "glu-glu-glu",
                "spans": [{"text": "glu-glu-glu", "ruby": True}],
            },
        )
        self.assertEqual(
            repair._expected_signature("nor-adrenalino")[1],
            (
                ("nor", True),
                ("-", False),
                ("adrenalin", True),
                ("o", False),
            ),
        )


class OptionalRuntimeIntegrationTests(unittest.TestCase):
    def test_full_plan_when_explicitly_enabled(self):
        if os.environ.get("ESP_TEST_PHASE600_RUNTIME") != "1":
            self.skipTest("Phase 600 runtime integration is not enabled")
        report = repair.plan_repair(batch_size=100)
        self.assertTrue(report["gate"])
        self.assertEqual(
            report["trilingual"]["boundary_mismatches"], 0,
        )
        self.assertTrue(report["kanji_nonintervention"])
        self.assertTrue(all(
            ratio < 2.0
            for ratio in report["width"][
                "max_effective_width_ratio"
            ].values()
        ))


if __name__ == "__main__":
    unittest.main()
