# -*- coding: utf-8 -*-
"""Focused fail-closed tests for the latest Kyoto guide transition audit."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import check_latest_kyoto_guide_transition as audit


LEDGER_PATH = HERE / "_latest_kyoto_guide_transition_7c04f97.json"


class LatestKyotoGuideTransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))

    def fresh_ledger(self) -> dict:
        return copy.deepcopy(self.ledger)

    def test_committed_ledger_has_fixed_authority(self) -> None:
        audit.validate_authority(self.fresh_ledger())

    def test_app_lineage_is_stable_across_descendant_commits(self) -> None:
        observed = []

        def is_ancestor(_root, ancestor, descendant):
            observed.append((ancestor, descendant))
            return True

        with mock.patch.object(
            audit, "_git", return_value=audit.APP_BASELINE_HEAD,
        ), mock.patch.object(
            audit, "_git_is_ancestor", side_effect=is_ancestor,
        ):
            baseline = audit.app_lineage_gate(HERE)
        with mock.patch.object(
            audit, "_git", return_value="f" * 40,
        ), mock.patch.object(
            audit, "_git_is_ancestor", side_effect=is_ancestor,
        ):
            descendant = audit.app_lineage_gate(HERE)

        self.assertEqual(baseline, descendant)
        self.assertEqual(
            baseline,
            {
                "app_baseline_head_oid": audit.APP_BASELINE_HEAD,
                "baseline_is_ancestor": True,
            },
        )
        self.assertEqual(
            observed,
            [
                (audit.APP_BASELINE_HEAD, audit.APP_BASELINE_HEAD),
                (audit.APP_BASELINE_HEAD, "f" * 40),
            ],
        )

    def test_unrelated_app_history_fails_closed(self) -> None:
        with mock.patch.object(
            audit, "_git", return_value="e" * 40,
        ), mock.patch.object(
            audit, "_git_is_ancestor", return_value=False,
        ):
            with self.assertRaisesRegex(
                audit.GuideTransitionError,
                "not a descendant of the sealed R73 baseline",
            ):
                audit.app_lineage_gate(HERE)

    def test_diff_classification_is_closed(self) -> None:
        diff = self.ledger["diff"]
        self.assertEqual(
            diff["totals"], {"insertions": 452, "deletions": 101, "hunks": 14}
        )
        self.assertEqual(
            diff["by_category"]["ruby_semantic"],
            {"insertions": 5, "deletions": 1, "hunks": 2},
        )
        self.assertEqual(
            diff["by_category"]["g8_layout"],
            {"insertions": 436, "deletions": 13, "hunks": 5},
        )
        self.assertEqual(
            {
                relative: tuple(row["category"] for row in rows)
                for relative, rows in diff["hunks"].items()
            },
            audit.HUNK_CATEGORIES,
        )

    def test_individual_guide_byte_pin_tamper_fails(self) -> None:
        ledger = self.fresh_ledger()
        ledger["guides"]["active"]["files"][audit.JA_GUIDE]["bytes"] += 1
        with self.assertRaisesRegex(
            audit.GuideTransitionError, "active/ja guide file pin drift"
        ):
            audit.validate_authority(ledger)

    def test_css_fixable_or_selected_rows_tamper_fails(self) -> None:
        ledger = self.fresh_ledger()
        ledger["ruby_css_margin"]["summary"]["fixable"] = 1
        with self.assertRaisesRegex(
            audit.GuideTransitionError, "CSS summary drift"
        ):
            audit.validate_authority(ledger)

        ledger = self.fresh_ledger()
        ledger["ruby_css_margin"]["per_file_rows_sha256"] = "0" * 64
        with self.assertRaisesRegex(
            audit.GuideTransitionError, "CSS selected-row pins drift"
        ):
            audit.validate_authority(ledger)

    def test_payload_runtime_or_width_policy_tamper_fails(self) -> None:
        ledger = self.fresh_ledger()
        ledger["app_runtime"]["languages"]["JA"]["payload"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(
            audit.GuideTransitionError,
            "deployed payload/runtime/probe pins drift",
        ):
            audit.validate_authority(ledger)

        ledger = self.fresh_ledger()
        ledger["app_runtime"]["policy"]["width_changes_root_boundaries"] = True
        with self.assertRaisesRegex(
            audit.GuideTransitionError, "guide/runtime policy drift"
        ):
            audit.validate_authority(ledger)

    def test_runtime_boundary_or_rendered_jus_tamper_fails(self) -> None:
        ledger = self.fresh_ledger()
        ledger["app_runtime"]["languages"]["ZH"]["probe"][
            "boundary_signature"
        ] = [["ĵ", "R"], ["us", "L"]]
        with self.assertRaisesRegex(
            audit.GuideTransitionError,
            "deployed payload/runtime/probe pins drift",
        ):
            audit.validate_authority(ledger)

        ledger = self.fresh_ledger()
        ledger["app_runtime"]["languages"]["JA"]["rendered"] = (
            ' <ruby>ĵus<rt class="XXS_S">たった<br>今</rt></ruby> '
        )
        with self.assertRaisesRegex(
            audit.GuideTransitionError,
            "deployed payload/runtime/probe pins drift",
        ):
            audit.validate_authority(ledger)

    def test_translation_report_parser_is_fail_closed(self) -> None:
        output = """\
検査対象: 本文HTML 152 件
  ルビ+和訳 119 / ルビのみ 3 / 韓国語版 1 / ルビ無し+和訳 29

A. title の表記ずれ : 0 件
B. 一覧バッジのずれ : 0 件
C. 3文以上の塊     : 0 件
D. バッジCSSの欠落 : 0 件

違反合計: 0 件
"""
        self.assertEqual(
            audit.parse_translation_report(output),
            self.ledger["translation_marking"]["report"],
        )
        with self.assertRaisesRegex(
            audit.GuideTransitionError,
            "translation checker output lacks violations",
        ):
            audit.parse_translation_report(output.replace("違反合計", "合計"))

    def test_recomputed_ledger_drift_fails(self) -> None:
        actual = self.fresh_ledger()
        actual["gate"]["jus_exact_runtime"] = False
        with self.assertRaisesRegex(
            audit.GuideTransitionError,
            "recomputed review differs",
        ):
            audit.require_review_match(self.ledger, actual)


if __name__ == "__main__":
    unittest.main()
