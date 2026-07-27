# -*- coding: utf-8 -*-
"""Focused safety tests for the reviewed corpus-exact manifest builder."""
import collections
import json
from pathlib import Path
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_corpus_reviewed_exact_manifest as reviewed  # noqa: E402
import build_corpus_exact_manifest as exact  # noqa: E402
import no_worsening_audit as audit  # noqa: E402


class ReviewedExactManifestTests(unittest.TestCase):
    def test_checkout_branch_is_provenance_not_manifest_identity(self):
        main = {
            "schema_version": 1,
            "source": {
                "head_oid": "SAME",
                "branch": "main",
                "content_sha256": "SAME-CONTENT",
            },
            "counts": {"exact_surfaces": 1},
        }
        audit_branch = {
            **main,
            "source": {
                **main["source"],
                "branch": "agent/audit",
            },
        }
        self.assertEqual(
            exact.semantic_manifest(main),
            exact.semantic_manifest(audit_branch),
        )
        self.assertEqual(
            reviewed.semantic_manifest(main),
            reviewed.semantic_manifest(audit_branch),
        )
        changed_head = {
            **audit_branch,
            "source": {
                **audit_branch["source"],
                "head_oid": "DIFFERENT",
            },
        }
        self.assertNotEqual(
            exact.semantic_manifest(main),
            exact.semantic_manifest(changed_head),
        )

    def test_source_refresh_requires_identical_reviewed_rules(self):
        current = {
            "schema_version": 1,
            "source": {"head_oid": "OLD", "report": {"sha256": "REPORT"}},
            "counts": {"exact_surfaces": 1},
            "exact_surfaces": [{"surface": "radiko"}],
            "annotations": {},
        }
        refreshed = {
            **current,
            "source": {"head_oid": "NEW", "report": {"sha256": "REPORT"}},
        }

        reviewed.require_source_only_refresh(current, refreshed)

        changed = {
            **refreshed,
            "exact_surfaces": [{"surface": "alia"}],
        }
        with self.assertRaisesRegex(ValueError, "new residual report"):
            reviewed.require_source_only_refresh(current, changed)

    def test_source_refresh_rejects_report_authority_change(self):
        current = {
            "schema_version": 1,
            "source": {"report": {"sha256": "ORIGINAL"}},
            "counts": {},
            "exact_surfaces": [],
            "annotations": {},
        }
        refreshed = {
            **current,
            "source": {"report": {"sha256": "OTHER"}},
        }
        with self.assertRaisesRegex(ValueError, "report authority"):
            reviewed.require_source_only_refresh(current, refreshed)

    def test_zero_residual_report_is_a_reproducible_empty_selection(self):
        report = {
            "schema_version": 1,
            "clone_content_sha256": "CORPUS",
            "surface_count": 123,
            "temp_mismatch": 0,
            "residuals": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "residual.json")
            path.write_text(json.dumps(report), encoding="utf-8")
            selected, metadata = reviewed.load_report(path, "CORPUS")

        self.assertEqual(selected, {})
        self.assertEqual(metadata["temp_mismatch"], 0)

    def test_surface_wide_rule_rejects_multiple_compatible_signatures(self):
        split = audit.signature_from_typed_parts([("radik", True), ("o", False)])
        atomic = audit.signature_from_typed_parts([("radiko", True)])
        observed = collections.Counter({split: 3, atomic: 1})
        expected = {
            audit.display_typed_parts(list(split[1])),
            audit.display_typed_parts(list(atomic[1])),
        }

        with self.assertRaisesRegex(ValueError, "surface-wide reviewed exact rule is ambiguous"):
            reviewed.select_compatible_signature("radiko", observed, expected)

    def test_report_can_explicitly_narrow_a_multi_signature_surface(self):
        split = audit.signature_from_typed_parts([("radik", True), ("o", False)])
        atomic = audit.signature_from_typed_parts([("radiko", True)])
        observed = collections.Counter({split: 1, atomic: 99})
        expected = {audit.display_typed_parts(list(split[1]))}

        signature, count, typed = reviewed.select_compatible_signature(
            "radiko", observed, expected
        )

        self.assertEqual(signature, split)
        self.assertEqual(count, 1)
        self.assertEqual(typed, next(iter(expected)))


if __name__ == "__main__":
    unittest.main()
