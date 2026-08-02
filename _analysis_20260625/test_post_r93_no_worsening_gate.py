# -*- coding: utf-8 -*-
"""Unit tests for the sealed post-R93 successor no-worsening gate."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import post_r93_no_worsening_gate as gate


def signature_from_typed(surface: str, typed: str) -> dict:
    spans = []
    for part in typed.split("|"):
        role, text = part.split(":", 1)
        if role not in {"R", "L"} or not text:
            raise AssertionError(f"invalid test typed signature: {typed!r}")
        spans.append({"text": text, "ruby": role == "R"})
    if "".join(span["text"] for span in spans) != surface:
        raise AssertionError(f"test signature does not reconstruct {surface!r}")
    return {"reconstruction": surface, "spans": spans}


def finding(surface: str, current_typed: str) -> dict:
    expected_typed = (
        f"R:{surface}" if current_typed == f"L:{surface}" else f"L:{surface}"
    )
    current_decomposition = "/".join(
        part.split(":", 1)[1] for part in current_typed.split("|")
    )
    return {
        "surface": surface,
        "expected_options": ["reviewed/reference"],
        "expected_signatures": [
            signature_from_typed(surface, expected_typed)
        ],
        "sources": ["gold_unmarked"],
        "baseline": current_decomposition,
        "baseline_typed": current_typed,
        "current": current_decomposition,
        "current_typed": current_typed,
        "current_signature": signature_from_typed(surface, current_typed),
    }


def zero_stats() -> dict:
    return {key: 0 for key in gate.STAT_KEYS}


def comparison() -> dict:
    sources = {source: zero_stats() for source in gate.EXPECTED_SOURCE_NAMES}
    primary = sources["gold_unmarked"]
    primary.update({
        "total_weight": gate.FIXED_REFERENCE["total_weight"],
        "total_cases": gate.FIXED_REFERENCE["total_cases"],
        "baseline_correct_weight": (
            gate.FIXED_REFERENCE["total_weight"] - len(gate.EXPECTED_RESIDUALS)
        ),
        "baseline_correct_cases": (
            gate.FIXED_REFERENCE["total_cases"] - len(gate.EXPECTED_RESIDUALS)
        ),
        "current_correct_weight": (
            gate.FIXED_REFERENCE["total_weight"] - len(gate.EXPECTED_RESIDUALS)
        ),
        "current_correct_cases": (
            gate.FIXED_REFERENCE["total_cases"] - len(gate.EXPECTED_RESIDUALS)
        ),
    })
    combined = {
        key: sum(row[key] for row in sources.values())
        for key in gate.STAT_KEYS
    }
    residuals = [
        finding(row["surface"], row["current_typed"])
        for row in gate.EXPECTED_RESIDUALS
    ]
    exact_record = {
        "surface": "glu-glu-glu",
        "expected": "glu/glu/glu",
        "sources": {"gold_official_override": 1},
        "baseline": "glu-glu-glu",
        "baseline_typed": "R:glu-glu-glu",
        "current": "glu-glu-glu",
        "current_typed": "R:glu-glu-glu",
        "expected_signature": signature_from_typed(
            "glu-glu-glu", "R:glu|L:-|R:glu|L:-|R:glu",
        ),
    }
    return {
        "comparison": "current_only",
        "sources": sources,
        "combined": combined,
        "regression_cases": [],
        "changed_to_unreferenced_wrong_surfaces": [],
        "current_unreferenced_wrong_surfaces": residuals,
        "current_place_manifest_wrong_cases": [],
        "current_official_override_wrong_cases": [copy.deepcopy(exact_record)],
        "current_project_ruby_boundary_override_wrong_cases": [],
        "current_exact_required_wrong_cases": [{
            **copy.deepcopy(exact_record),
            "exact_required_sources": ["gold_official_override"],
        }],
        "weighted_worsening_sources": [],
        "gate": False,
    }


def fingerprints() -> dict:
    result = {}
    for language in gate.LANGUAGES:
        result[language] = {
            path: hashlib.sha256(path.encode("utf-8")).hexdigest().upper()
            for path in gate.expected_fingerprint_paths(language)
        }
    return result


def audit_report() -> dict:
    fixed = gate.FIXED_REFERENCE
    app_fingerprints = fingerprints()
    return {
        "scope": {
            "corpus": {"content_sha256": fixed["corpus_content_sha256"]},
            "corpus_repository": {
                "head_oid": fixed["corpus_head_oid"],
                "status_sha256": fixed["corpus_status_sha256"],
            },
            "place_manifest": {"rows": 48, "instances": 74},
            "gold": {"sha256": fixed["gold_sha256"]},
        },
        "case_count": fixed["resolved_cases"],
        "raw_case_count": fixed["raw_cases"],
        "surface_count": fixed["surfaces"],
        "languages": [
            {
                "language": language,
                "comparison": comparison(),
                "input_fingerprint": app_fingerprints[language],
                "input_stable": True,
                "gate": False,
            }
            for language in gate.LANGUAGES
        ],
        "reference_projection": {
            "schema_version": 5,
            "case_count": fixed["raw_cases"],
            "surface_count": fixed["surfaces"],
            "reference_sha256": fixed["raw_reference_sha256"],
        },
        "resolved_reference": {
            "case_count": fixed["resolved_cases"],
            "surface_count": fixed["surfaces"],
            "reference_sha256": fixed["resolved_reference_sha256"],
        },
        "reviewed_reference": {
            "scope_manifest_sha256": fixed["scope_manifest_sha256"],
            "conflict_manifest_sha256": fixed["conflict_manifest_sha256"],
        },
        "checkpoint_context": {
            "checkpoint_schema_version": 2,
            "reference_schema_version": 5,
            "raw_reference_sha256": fixed["raw_reference_sha256"],
            "reference_sha256": fixed["resolved_reference_sha256"],
            "surface_sha256": fixed["surface_sha256"],
            "corpus_sha256": fixed["corpus_content_sha256"],
            "corpus_head_oid": fixed["corpus_head_oid"],
            "corpus_status_sha256": fixed["corpus_status_sha256"],
            "gold_sha256": fixed["gold_sha256"],
            "scope_manifest_sha256": fixed["scope_manifest_sha256"],
            "conflict_manifest_sha256": fixed["conflict_manifest_sha256"],
            "audit_code_sha256": "A" * 64,
        },
        "inputs_stable": {
            key: True for key in gate.INPUT_STABILITY_KEYS
        },
        "complete": True,
        "gate": False,
    }


def raw_report(report: dict) -> bytes:
    return json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")


class PostR93NoWorseningGateTests(unittest.TestCase):
    def setUp(self):
        self.report = audit_report()
        self.fingerprints = fingerprints()
        self.raw = raw_report(self.report)
        self.manifest = gate.build_manifest_from_report(
            self.report,
            self.raw,
            current_fingerprints=self.fingerprints,
        )

    def test_valid_report_builds_and_validates_separate_successor_evidence(self):
        result = gate.validate_report_bytes(
            self.raw,
            manifest=self.manifest,
            current_fingerprints=self.fingerprints,
        )
        self.assertTrue(result["gate"])
        self.assertEqual(result["surfaces"], gate.FIXED_REFERENCE["surfaces"])
        self.assertEqual(
            result["residual_surfaces_per_language"],
            len(gate.EXPECTED_RESIDUALS),
        )
        self.assertEqual(result["regression_cases"], 0)
        self.assertNotIn("phase558", self.manifest["gate_id"])

    def test_any_surplus_residual_is_rejected(self):
        report = copy.deepcopy(self.report)
        report["languages"][0]["comparison"][
            "current_unreferenced_wrong_surfaces"
        ].append(finding("surplus", "L:surplus"))
        with self.assertRaisesRegex(ValueError, "reviewed set is exact"):
            gate.validate_report(
                report, current_fingerprints=self.fingerprints,
            )

    def test_trilingual_report_mismatch_is_rejected(self):
        report = copy.deepcopy(self.report)
        report["languages"][1]["comparison"][
            "current_unreferenced_wrong_surfaces"
        ][0]["expected_options"] = ["different-reference"]
        with self.assertRaisesRegex(ValueError, "JA/ZH/KO"):
            gate.validate_report(
                report, current_fingerprints=self.fingerprints,
            )

    def test_regression_and_changed_wrong_buckets_are_closed(self):
        for bucket in (
            "regression_cases", "changed_to_unreferenced_wrong_surfaces",
        ):
            report = copy.deepcopy(self.report)
            report["languages"][0]["comparison"][bucket] = [
                {"surface": "forbidden"}
            ]
            with self.subTest(bucket=bucket):
                with self.assertRaisesRegex(ValueError, "forbidden nonempty"):
                    gate.validate_report(
                        report, current_fingerprints=self.fingerprints,
                    )

    def test_only_glu_glu_glu_may_occupy_official_and_exact_buckets(self):
        for bucket in (
            "current_official_override_wrong_cases",
            "current_exact_required_wrong_cases",
        ):
            report = copy.deepcopy(self.report)
            report["languages"][0]["comparison"][bucket] = []
            with self.subTest(bucket=bucket):
                with self.assertRaisesRegex(ValueError, "residual drift"):
                    gate.validate_report(
                        report, current_fingerprints=self.fingerprints,
                    )

    def test_report_and_live_input_hash_changes_are_rejected(self):
        changed_report = copy.deepcopy(self.report)
        key = next(iter(changed_report["languages"][0]["input_fingerprint"]))
        changed_report["languages"][0]["input_fingerprint"][key] = "B" * 64
        with self.assertRaisesRegex(ValueError, "sealed evidence"):
            gate.validate_report(
                changed_report,
                manifest=self.manifest,
                current_fingerprints={
                    row["language"]: row["input_fingerprint"]
                    for row in changed_report["languages"]
                },
            )

        changed_live = copy.deepcopy(self.fingerprints)
        key = next(iter(changed_live["KO"]))
        changed_live["KO"][key] = "C" * 64
        with self.assertRaisesRegex(ValueError, "deployed app input"):
            gate.validate_report(
                self.report,
                manifest=self.manifest,
                current_fingerprints=changed_live,
            )

    def test_raw_report_and_manifest_bytes_are_both_sealed(self):
        manifest_raw = gate.manifest_bytes(self.manifest)
        manifest_digest = gate.raw_sha256(manifest_raw)
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            manifest_path = directory / "manifest.json"
            manifest_path.write_bytes(manifest_raw)
            loaded, loaded_raw = gate.load_manifest(
                manifest_path, expected_sha256=manifest_digest,
            )
            self.assertEqual(loaded, self.manifest)
            self.assertEqual(loaded_raw, manifest_raw)
            with self.assertRaisesRegex(ValueError, "raw report byte"):
                gate.validate_report_bytes(
                    self.raw + b"\n",
                    manifest=loaded,
                    current_fingerprints=self.fingerprints,
                )
            manifest_path.write_bytes(manifest_raw + b"\n")
            with self.assertRaisesRegex(ValueError, "manifest byte drift"):
                gate.load_manifest(
                    manifest_path, expected_sha256=manifest_digest,
                )

    def test_explicit_unsealed_sentinel_and_contract_tamper_fail_closed(self):
        self.assertTrue(gate.is_sha256(gate.EXPECTED_MANIFEST_SHA256))
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.json"
            path.write_bytes(gate.manifest_bytes(self.manifest))
            with self.assertRaisesRegex(ValueError, "not sealed"):
                gate.load_manifest(
                    path,
                    expected_sha256=(
                        "TO_BE_SEALED_AFTER_FINAL_POST_R93_RAW_AUDIT"
                    ),
                )

        changed = copy.deepcopy(self.manifest)
        changed["residual_contract"] = changed["residual_contract"][:-1]
        with self.assertRaisesRegex(ValueError, "residual contract"):
            gate.validate_manifest(changed)

    def test_formal_pipeline_keeps_historical_then_versioned_successor_order(self):
        source = (HERE / "regenerate_all.py").read_text(encoding="utf-8")
        ordered_tokens = (
            "'verify_phase558_historical_evidence.py'",
            "'test_post_r93_no_worsening_gate.py'",
            "'verify_post_r93_historical_evidence.py'",
            "'test_post_r98_no_worsening_gate.py'",
            "'post_r98_no_worsening_gate.py'",
            "'audit_master_3lang_full_snapshot.py'",
        )
        positions = []
        for token in ordered_tokens:
            self.assertEqual(
                source.count(token), 1,
                f"formal pipeline token must occur exactly once: {token}",
            )
            positions.append(source.index(token))
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("build_post_r93_no_worsening_manifest.py", source)
        self.assertNotIn("build_post_r98_no_worsening_manifest.py", source)
        self.assertNotIn("'no_worsening_audit.py'", source)


if __name__ == "__main__":
    unittest.main()
