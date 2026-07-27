# -*- coding: utf-8 -*-
"""Safety tests for the 7c04-reference / d1642c2-current successor."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import current_corpus_no_worsening_sidecar_gate as gate
import run_current_corpus_no_worsening as runner


OLD_REPORT = HERE / "out" / "_audit_no_worsening_current_e373.json"
OLD_SCOPE = HERE / "_phase558_current_corpus_scope_manifest.json"


def successor_fixture() -> dict:
    report = json.loads(OLD_REPORT.read_text(encoding="utf-8"))
    scope = gate.load_scope()
    expected = scope["expected"]
    manifest = gate.load_manifest()
    projection = manifest["reference_authority"]["projection"]

    report["reference_projection"] = copy.deepcopy(expected)
    report["scope"]["corpus_repository"] = copy.deepcopy(
        expected["corpus_repository"]
    )
    extended = report["scope"]["corpus"]["extended_reference_manifest"]
    report["scope"]["corpus"] = {
        **copy.deepcopy(expected["corpus"]),
        "extended_reference_manifest": extended,
    }
    report["scope"]["place_manifest"] = copy.deepcopy(
        expected["place_manifest"]
    )
    # Dynamic snapshot fields are retained; the frozen projection fields are
    # replaced exactly with the successor authority.
    old_gold = report["scope"]["gold"]
    report["scope"]["gold"] = {
        **copy.deepcopy(expected["gold"]),
        **{
            key: old_gold[key]
            for key in (
                "path",
                "expected_sha256",
                "mtime_ns",
                "consistent_snapshot",
                "mixed_marker_surface_list",
                "unmarked_conflicts",
            )
        },
    }
    report["raw_case_count"] = projection["raw_cases"]
    report["surface_count"] = projection["surfaces"]
    report["case_count"] = projection["resolved_cases"]
    report["resolved_reference"] = {
        "case_count": projection["resolved_cases"],
        "surface_count": projection["surfaces"],
        "reference_sha256": projection["resolved_reference_sha256"],
    }
    report["reviewed_reference"]["scope_manifest"] = str(gate.SCOPE_PATH)
    report["reviewed_reference"]["scope_manifest_sha256"] = (
        gate.EXPECTED_SCOPE_SHA256
    )
    checkpoint = report["checkpoint_context"]
    checkpoint.update({
        "raw_reference_sha256": projection["raw_reference_sha256"],
        "reference_sha256": projection["resolved_reference_sha256"],
        "surface_sha256": projection["surface_sha256"],
        "corpus_sha256": manifest["reference_authority"]["corpus"][
            "content_sha256"
        ],
        "corpus_head_oid": manifest["reference_authority"]["corpus"][
            "head_oid"
        ],
        "corpus_status_sha256": manifest["reference_authority"]["corpus"][
            "status_sha256"
        ],
        "scope_manifest_sha256": gate.EXPECTED_SCOPE_SHA256,
    })
    report["successor_trilingual_boundaries"] = {
        "schema_version": 1,
        "surface_count": 68429,
        "languages": ["JA", "ZH", "KO"],
        "signature_sha256": {
            "JA": "A" * 64,
            "ZH": "A" * 64,
            "KO": "A" * 64,
        },
        "mismatches": 0,
        "gate": True,
    }
    added_findings = []
    for surface in ("Temis", "iniciatoro"):
        expected_finding = gate.EXPECTED_FINDING_RECORDS[surface]
        added_findings.append({
            "surface": surface,
            **copy.deepcopy(expected_finding),
            "baseline": expected_finding["current"],
            "baseline_typed": expected_finding["current_typed"],
        })
    for language in report["languages"]:
        comparison = language["comparison"]
        findings = comparison["current_unreferenced_wrong_surfaces"]
        findings.extend(copy.deepcopy(added_findings))
        findings.sort(key=lambda row: row["surface"])
    return report


def sealed_test_manifest(report: dict) -> dict:
    """Create test-local pins; these are never tracked as measured evidence."""
    manifest = copy.deepcopy(gate.load_manifest())
    first = report["languages"][0]["comparison"]
    measurement = manifest["current_only_audit_contract"][
        "post_phase600_measurement"
    ]
    measurement.update({
        "status": "sealed_full_raw_audit",
        "trilingual_signature_sha256": "A" * 64,
        "raw_source_statistics_sha256": gate.stable_json_sha256(
            first["sources"]
        ),
        "raw_combined": copy.deepcopy(first["combined"]),
        "raw_html_corpus": copy.deepcopy(first["sources"]["html_corpus"]),
    })
    return manifest


def phase599_fixture() -> dict:
    return {
        "promotion_audit_gate": True,
        "post_promotion_global_rows_per_language": 572506,
        "managed_rows_per_language": {"JA": 5, "ZH": 5, "KO": 5},
        "kanji_nonintervention": True,
        "promoted_corpus_context_runtime": {
            "gate": True,
            "corpus_instances": 6,
            "language_cases_activated": 15,
            "trilingual_boundaries_identical": True,
            "trilingual_rb_sequences_identical": True,
        },
    }


class SuccessorManifestTests(unittest.TestCase):
    def test_scope_and_sidecar_are_sealed(self):
        manifest = gate.load_manifest()
        scope = gate.load_scope()
        self.assertEqual(
            gate.stable_json_sha256(scope["expected"]),
            gate.EXPECTED_SCOPE_PROJECTION_SHA256,
        )
        self.assertEqual(
            scope["expected"]["reference_sha256"],
            "51D51B1F2FCB32B94FB5F904714AB39AB772884410DE35A20B5B7955BEA868BB",
        )
        self.assertEqual(
            hashlib.sha256(gate.MANIFEST_PATH.read_bytes())
            .hexdigest()
            .upper(),
            gate.EXPECTED_MANIFEST_SHA256,
        )
        self.assertEqual(
            manifest["e373_to_7c04_weight_transition"][
                "changed_weight_rows"
            ],
            110,
        )
        self.assertEqual(
            manifest["e373_to_7c04_weight_transition"][
                "aggregate_weight_delta"
            ],
            -302,
        )
        contract = manifest["current_only_audit_contract"]
        self.assertEqual(
            contract["raw_current_wrong_surfaces"],
            ["Izraelio", "Temis", "iniciatoro", "tia-tia"],
        )
        self.assertEqual(
            contract["retained_reviewed_ruby_authorities"],
            ["Izraelio", "tia-tia"],
        )
        self.assertEqual(contract["active_semantic_wrong_surfaces"], [])
        measurement = contract["post_phase600_measurement"]
        self.assertEqual(
            measurement["status"],
            "sealed_full_raw_audit",
        )
        self.assertEqual(
            measurement["trilingual_signature_sha256"],
            "3CA7979E3AE68D39BED1DEC229757B56C8AF51394F73EF9EB70C0F2ED8D673E9",
        )
        self.assertEqual(
            measurement["raw_source_statistics_sha256"],
            "E66300BD03550FDCABADD63F1439BCE9FB5583F9E2C9467A2D1CA4AF27B3FDF3",
        )
        self.assertEqual(measurement["raw_combined"]["total_weight"], 323225)
        self.assertEqual(
            measurement["raw_html_corpus"]["total_weight"], 270763,
        )

    def test_predecessor_authorities_remain_exact(self):
        manifest = gate.load_manifest()
        for identity in manifest["immutable_predecessors"].values():
            path = HERE / identity["path"]
            self.assertEqual(path.stat().st_size, identity["bytes"])
            self.assertEqual(gate.file_sha256(path), identity["sha256"])


class SuccessorReportTests(unittest.TestCase):
    def _validate(self, report, *, manifest=None, phase599=None):
        return gate.validate_audit_report(
            report,
            manifest=manifest or sealed_test_manifest(report),
            phase599_report=phase599 or phase599_fixture(),
        )

    def test_pending_measurements_fail_closed(self):
        report = successor_fixture()
        manifest = copy.deepcopy(gate.load_manifest())
        measurement = manifest["current_only_audit_contract"][
            "post_phase600_measurement"
        ]
        measurement["status"] = "pending_full_raw_audit"
        for name in gate.POST_PHASE600_REQUIRED_PINS:
            measurement[name] = None
        with self.assertRaisesRegex(ValueError, "not measured and sealed"):
            gate.validate_audit_report(
                report,
                manifest=manifest,
                phase599_report=phase599_fixture(),
            )

    def test_synthetic_sealed_fixture_exercises_closed_gate(self):
        report = successor_fixture()
        summary = self._validate(report)
        self.assertTrue(summary["gate"])
        self.assertEqual(summary["trilingual_boundary_mismatches"], 0)
        self.assertEqual(summary["reviewed_active_improvements"], ["iniciatoro"])
        self.assertEqual(summary["contextual_admissions"], ["Temis"])
        self.assertEqual(summary["active_semantic_wrong_surfaces"], [])

    def test_missing_iniciator_fails_closed(self):
        report = successor_fixture()
        for language in report["languages"]:
            language["comparison"][
                "current_unreferenced_wrong_surfaces"
            ] = [
                row
                for row in language["comparison"][
                    "current_unreferenced_wrong_surfaces"
                ]
                if row["surface"] != "iniciatoro"
            ]
        with self.assertRaisesRegex(ValueError, "finding surface"):
            self._validate(report)

    def test_extra_finding_fails_closed(self):
        report = successor_fixture()
        extra = copy.deepcopy(
            report["languages"][0]["comparison"][
                "current_unreferenced_wrong_surfaces"
            ][0]
        )
        extra["surface"] = "unexpected"
        for language in report["languages"]:
            language["comparison"][
                "current_unreferenced_wrong_surfaces"
            ].append(copy.deepcopy(extra))
        with self.assertRaisesRegex(ValueError, "finding surface"):
            self._validate(report)

    def test_statistics_tamper_fails_closed(self):
        report = successor_fixture()
        manifest = sealed_test_manifest(report)
        report["languages"][1]["comparison"]["sources"]["html_corpus"][
            "total_weight"
        ] += 1
        with self.assertRaisesRegex(ValueError, "statistics|absolute"):
            self._validate(report, manifest=manifest)

    def test_trilingual_boundary_tamper_fails_closed(self):
        report = successor_fixture()
        finding = report["languages"][2]["comparison"][
            "current_unreferenced_wrong_surfaces"
        ][1]
        finding["current"] = "iniciat/or/o"
        with self.assertRaisesRegex(ValueError, "finding drift"):
            self._validate(report)

    def test_full_trilingual_fingerprint_mismatch_fails_closed(self):
        report = successor_fixture()
        manifest = sealed_test_manifest(report)
        report["successor_trilingual_boundaries"]["signature_sha256"][
            "KO"
        ] = "B" * 64
        report["successor_trilingual_boundaries"]["mismatches"] = 1
        report["successor_trilingual_boundaries"]["gate"] = False
        with self.assertRaisesRegex(ValueError, "trilingual boundary"):
            self._validate(report, manifest=manifest)

    def test_active_projection_cannot_replace_reference_projection(self):
        report = successor_fixture()
        report["reference_projection"]["case_count"] = 68517
        with self.assertRaisesRegex(ValueError, "projection identity"):
            self._validate(report)

    def test_phase599_context_gate_is_required(self):
        report = successor_fixture()
        phase599 = phase599_fixture()
        phase599["promoted_corpus_context_runtime"]["corpus_instances"] = 5
        with self.assertRaisesRegex(ValueError, "Phase 599"):
            self._validate(report, phase599=phase599)


class TransitionHelperTests(unittest.TestCase):
    def _case(self, expected: str, weight: int):
        signature = gate.audit.expected_signature(expected, frozenset())
        surface = signature[0]
        return (surface, signature), {
            "surface": surface,
            "expected": expected,
            "signature": signature,
            "sources": {"html_corpus": weight},
        }

    def test_weight_rows_are_deterministic_and_weighted(self):
        key, before = self._case("radik/o", 4)
        _key, after = self._case("radik/o", 2)
        rows = gate._weight_rows({key: before}, {key: after})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["delta"], -2)
        self.assertEqual(rows[0]["surface"], "radiko")


class RunnerTests(unittest.TestCase):
    def test_successor_glu_override_is_atomic_and_isolated(self):
        isolated = types.SimpleNamespace(
            OFFICIAL_LONG_ROOT_OVERRIDES={
                "glu-glu-glu": "glu/-/glu/-/glu",
            },
            REVIEWED_GOLD_OVERRIDES={
                "glu-glu-glu": "glu/-/glu/-/glu",
            },
        )
        runner._activate_successor_reference_overrides(isolated)
        self.assertEqual(
            isolated.OFFICIAL_LONG_ROOT_OVERRIDES["glu-glu-glu"],
            "glu-glu-glu",
        )
        self.assertEqual(
            isolated.REVIEWED_GOLD_OVERRIDES["glu-glu-glu"],
            "glu-glu-glu",
        )
        self.assertEqual(
            gate.audit.OFFICIAL_LONG_ROOT_OVERRIDES["glu-glu-glu"],
            "glu/-/glu/-/glu",
        )

    def test_missing_environment_fails_before_mutation(self):
        with self.assertRaisesRegex(RuntimeError, "requires explicit"):
            runner.run_formal_audit(environ={})

    def test_runner_separates_reference_and_active_corpora(self):
        report = successor_fixture()
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            gold = temporary / "gold.txt"
            gold.write_text("frozen", encoding="utf-8")
            e373 = temporary / "e373"
            reference = temporary / "7c04"
            active = temporary / "d164"
            for path in (e373, reference, active):
                path.mkdir()
            output = temporary / "report.json"
            environment = {
                "ESP_GOLD_PATH": str(gold),
                "ESP_CURRENT_CORPUS_E373_PATH": str(e373),
                "ESP_CURRENT_CORPUS_REFERENCE_PATH": str(reference),
                "ESP_CURRENT_CORPUS_ACTIVE_PATH": str(active),
                "ESP_CORPUS_PATH": "moving-active-must-not-be-inherited",
            }
            calls = []

            def fake_run(command, *, cwd, env, check):
                calls.append((list(command), dict(env)))
                if len(calls) == 1:
                    output.write_text(
                        json.dumps(report, ensure_ascii=False),
                        encoding="utf-8",
                    )
                    return types.SimpleNamespace(returncode=1)
                return types.SimpleNamespace(returncode=0)

            with (
                mock.patch.object(runner, "REPORT", output),
                mock.patch.object(
                    runner,
                    "RAW_DEFAULT_REPORT",
                    temporary / "parent-current.json",
                ),
            ):
                summary = runner.run_formal_audit(
                    environ=environment,
                    run_process=fake_run,
                    head_reader=lambda: "a" * 40,
                    state_reader=lambda: {"stable": True},
                )
            self.assertTrue(summary["gate"])
            self.assertEqual(len(calls), 2)
            self.assertEqual(
                calls[0][1]["ESP_CORPUS_PATH"], str(reference)
            )
            self.assertNotEqual(
                calls[0][1]["ESP_CORPUS_PATH"], str(active)
            )
            gate_command = calls[1][0]
            self.assertIn(str(e373), gate_command)
            self.assertIn(str(reference), gate_command)
            self.assertIn(str(active), gate_command)


class OptionalCleanCorpusIntegrationTests(unittest.TestCase):
    def test_clean_corpus_transition_when_explicitly_configured(self):
        names = (
            "ESP_TEST_CURRENT_CORPUS_E373_PATH",
            "ESP_TEST_CURRENT_CORPUS_REFERENCE_PATH",
            "ESP_TEST_CURRENT_CORPUS_ACTIVE_PATH",
        )
        if not all(os.environ.get(name) for name in names):
            self.skipTest("clean successor corpus fixtures are not configured")
        summary = gate.validate_corpus_authorities(
            Path(os.environ[names[0]]),
            Path(os.environ[names[1]]),
            Path(os.environ[names[2]]),
        )
        self.assertTrue(summary["gate"])
        self.assertEqual(summary["e373_to_7c04_weight_rows"], 110)
        self.assertEqual(summary["e373_to_7c04_weight_delta"], -302)


if __name__ == "__main__":
    unittest.main()
