# -*- coding: utf-8 -*-
"""Unit tests for the closed Phase 558 no-worsening sidecar."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import phase532_ruby_policy as phase532
import phase558_no_worsening_sidecar_gate as gate
import phase558_ruby_overlay as overlay_policy
import phase558_ruby_overlay_runtime_gate as runtime_gate


def _stat_block(*, total=10, correct=8):
    return {
        "total_weight": total,
        "total_cases": total,
        "baseline_correct_weight": correct,
        "baseline_correct_cases": correct,
        "current_correct_weight": correct,
        "current_correct_cases": correct,
        "regression_weight": 0,
        "regression_cases": 0,
        "improvement_weight": 0,
        "improvement_cases": 0,
    }


def _full_stat_block(*, total, baseline, current, regressions, improvements):
    return {
        "total_weight": total,
        "total_cases": total,
        "baseline_correct_weight": baseline,
        "baseline_correct_cases": baseline,
        "current_correct_weight": current,
        "current_correct_cases": current,
        "regression_weight": regressions,
        "regression_cases": regressions,
        "improvement_weight": improvements,
        "improvement_cases": improvements,
    }


def _sum_stat_blocks(blocks):
    return {
        key: sum(block[key] for block in blocks)
        for key in gate.STAT_KEYS
    }


def _unchanged_stat_block(
    *, total_weight, total_cases, correct_weight=None, correct_cases=None,
):
    if correct_weight is None:
        correct_weight = total_weight
    if correct_cases is None:
        correct_cases = total_cases
    return {
        "total_weight": total_weight,
        "total_cases": total_cases,
        "baseline_correct_weight": correct_weight,
        "baseline_correct_cases": correct_cases,
        "current_correct_weight": correct_weight,
        "current_correct_cases": correct_cases,
        "regression_weight": 0,
        "regression_cases": 0,
        "improvement_weight": 0,
        "improvement_cases": 0,
    }


def _exact_sources(profile):
    sources = {
        "gold_fake_coarse_paired_academic": _unchanged_stat_block(
            total_weight=120, total_cases=120,
        ),
        "gold_fake_coarse_pejvo_original": _unchanged_stat_block(
            total_weight=34, total_cases=33,
        ),
        "gold_fake_coarse_project_reviewed_override": _unchanged_stat_block(
            total_weight=2, total_cases=2,
        ),
        "gold_official_override": _unchanged_stat_block(
            total_weight=11, total_cases=11,
        ),
        "gold_phase532_selected_ruby_policy": _unchanged_stat_block(
            total_weight=57, total_cases=57,
        ),
        "gold_project_ruby_boundary_override": _unchanged_stat_block(
            total_weight=2, total_cases=2,
        ),
        "gold_unmarked": _unchanged_stat_block(
            total_weight=52162, total_cases=52162,
            correct_weight=52160, correct_cases=52160,
        ),
        "html_corpus": _unchanged_stat_block(
            total_weight=271065,
            total_cases=21872 if profile == "current-e373" else 21877,
        ),
        "html_place_manifest": _unchanged_stat_block(
            total_weight=74, total_cases=36,
        ),
    }
    if profile in {"full-data-isolated", "full-comprehensive"}:
        sources["gold_unmarked"] = _full_stat_block(
            total=52162, baseline=52162, current=52160,
            regressions=2, improvements=0,
        )
    return sources


class Phase558NoWorseningSidecarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = gate.load_manifest()
        cls.entries = {
            entry["surface"]: entry for entry in cls.manifest["entries"]
        }
        cls.pre_signatures, _digest = runtime_gate.expected_signatures(
            "pre-regen"
        )
        cls.post_signatures, _digest = runtime_gate.expected_signatures(
            "post-regen"
        )

    def finding(self, surface):
        entry = self.entries[surface]
        pre_signatures, _digest = runtime_gate.expected_signatures("pre-regen")
        return {
            "surface": surface,
            "expected_options": [entry["old_decomposition"]],
            "expected_signatures": [
                gate._signature_payload(pre_signatures[surface])
            ],
            "sources": list(entry["required_reference_sources"]),
            "baseline": entry["new_decomposition"],
            "baseline_typed": entry["new_typed"],
            "current": entry["new_decomposition"],
            "current_typed": entry["new_typed"],
            "current_signature": gate._signature_payload(
                self.post_signatures[surface]
            ),
        }

    def comparison(self, profile="parent-current"):
        sources = _exact_sources(profile)
        return {
            "comparison": "current_only",
            "sources": sources,
            "combined": _sum_stat_blocks(sources.values()),
            "regression_cases": [],
            "changed_to_unreferenced_wrong_surfaces": [],
            "current_unreferenced_wrong_surfaces": [
                self.finding("Izraelio"), self.finding("tia-tia"),
            ],
            "current_place_manifest_wrong_cases": [],
            "current_official_override_wrong_cases": [],
            "current_project_ruby_boundary_override_wrong_cases": [],
            "current_exact_required_wrong_cases": [],
            "weighted_worsening_sources": [],
            "gate": False,
        }

    def audit_report(self):
        parent = self.manifest["parent_authority"]
        return {
            "scope": {
                "gold": {
                    "sha256": phase532.CANDIDATE_LEARNER_SHA256,
                    "fake_coarse_reference": {
                        "sha256": parent["fake_coarse_reference"]["sha256"],
                    },
                },
            },
            "case_count": 10,
            "raw_case_count": 12,
            "surface_count": 8,
            "languages": [
                {
                    "language": language,
                    "comparison": self.comparison(),
                    "input_fingerprint": {"candidate": language},
                    "input_stable": True,
                    "gate": False,
                }
                for language in runtime_gate.LANGUAGES
            ],
            "reference_projection": {"case_count": 12, "surface_count": 8},
            "resolved_reference": {"case_count": 10, "surface_count": 8},
            "reviewed_reference": {
                "scope_manifest_sha256": parent["scope_manifest"]["sha256"],
            },
            "checkpoint_context": {
                "scope_manifest_sha256": parent["scope_manifest"]["sha256"],
                "head_oid": parent["app_head_oid"],
                "gold_sha256": phase532.CANDIDATE_LEARNER_SHA256,
            },
            "inputs_stable": {
                key: True
                for key in self.manifest["audit_contract"][
                    "required_input_stability"
                ]
            },
            "complete": True,
            "gate": False,
        }

    def runtime_report(self):
        review = overlay_policy.review_identity()
        return {
            "phase": 558,
            "mode": "post-regen",
            "languages": list(runtime_gate.LANGUAGES),
            "surfaces": 5,
            "trilingual_mismatches": 0,
            "signature_manifest_sha256": self.manifest["audit_contract"][
                "candidate_signature_manifest_sha256"
            ],
            "scope_guard_surfaces": self.manifest["audit_contract"][
                "candidate_scope_guard_surfaces"
            ],
            "scope_guard_trilingual_mismatches": 0,
            "scope_guard_signature_manifest_sha256": self.manifest[
                "audit_contract"
            ]["candidate_scope_guard_signature_manifest_sha256"],
            "scope_guard_gate": True,
            "gate": True,
            "candidate_payload_sha256": {
                language: f"payload-{language}"
                for language in runtime_gate.LANGUAGES
            },
            "app_input_fingerprints": {
                language: {"candidate": language}
                for language in runtime_gate.LANGUAGES
            },
        "adjudicated_source_rows": 5,
        "productive_rules": 2,
        "productive_endings": 10,
        "productive_cases": 3,
        "productive_payload_variants": 60,
            "exact_payload_variants": 3,
            "expanded_payload_variants": 63,
            "payload_variant_manifest_sha256": (
                runtime_gate.PAYLOAD_VARIANT_MANIFEST_SHA256
            ),
            "payload_variant_trilingual_mismatches": 0,
            "payload_variant_gate": True,
            "deployed_snapshot_revalidated": True,
            "overlay_review": review,
            "all_inputs_stable": True,
        }

    def full_finding(self, surface, bucket):
        entry = self.entries[surface]
        record = {
            "surface": surface,
            "expected_options": [entry["old_decomposition"]],
            "sources": list(entry["required_reference_sources"]),
            "baseline": entry["old_decomposition"],
            "baseline_typed": entry["old_typed"],
            "current": entry["new_decomposition"],
            "current_typed": entry["new_typed"],
        }
        if bucket == "current_unreferenced_wrong_surfaces":
            record.update({
                "expected_signatures": [
                    gate._signature_payload(self.pre_signatures[surface])
                ],
                "current_signature": gate._signature_payload(
                    self.post_signatures[surface]
                ),
            })
        return record

    def signature_change(self, surface):
        entry = self.entries[surface]
        return {
            "surface": surface,
            "baseline": entry["old_decomposition"],
            "baseline_typed": entry["old_typed"],
            "baseline_signature": gate._signature_payload(
                self.pre_signatures[surface]
            ),
            "current": entry["new_decomposition"],
            "current_typed": entry["new_typed"],
            "current_signature": gate._signature_payload(
                self.post_signatures[surface]
            ),
        }

    def full_comparison(self, label):
        sources = _exact_sources(f"full-{label.replace('_', '-')}")
        replacements = ("Izraelio", "tia-tia")
        return {
            "comparison": label,
            "sources": sources,
            "combined": _sum_stat_blocks(sources.values()),
            "regression_cases": [
                self.full_finding(surface, "regression_cases")
                for surface in replacements
            ],
            "changed_to_unreferenced_wrong_surfaces": [
                self.full_finding(
                    surface, "changed_to_unreferenced_wrong_surfaces"
                ) for surface in replacements
            ],
            "current_unreferenced_wrong_surfaces": [
                self.full_finding(
                    surface, "current_unreferenced_wrong_surfaces"
                ) for surface in replacements
            ],
            "current_place_manifest_wrong_cases": [],
            "current_official_override_wrong_cases": [],
            "current_project_ruby_boundary_override_wrong_cases": [],
            "current_exact_required_wrong_cases": [],
            "weighted_worsening_sources": ["gold_unmarked", "combined"],
            "signature_changes": [
                self.signature_change(surface)
                for surface in self.manifest["full_audit_contract"][
                    "required_signature_change_surfaces"
                ]
            ],
            "gate": False,
        }

    def full_report(self):
        contract = self.manifest["full_audit_contract"]
        pin = contract["reference_projection"]
        parent = self.manifest["parent_authority"]
        repository = {
            "head_oid": pin["corpus_head_oid"],
            "branch": "main",
            "status_entries": 0,
            "status_sha256": pin["corpus_status_sha256"],
        }
        projection = {
            "case_count": pin["raw_cases"],
            "surface_count": pin["surfaces"],
            "reference_sha256": pin["raw_reference_sha256"],
            "corpus": {"content_sha256": pin["corpus_content_sha256"]},
            "corpus_repository": repository,
        }
        fingerprints = {
            language: {"candidate": language}
            for language in runtime_gate.LANGUAGES
        }
        rows = []
        for language in runtime_gate.LANGUAGES:
            rows.append({
                "language": language,
                "data_isolated_definition": (
                    "HEAD Ruby JSON + current runtime -> working-tree Ruby JSON "
                    "+ current runtime"
                ),
                "comprehensive_definition": (
                    "HEAD Ruby JSON + HEAD runtime -> working-tree Ruby JSON "
                    "+ current runtime"
                ),
                "data_isolated": self.full_comparison("data_isolated"),
                "comprehensive": self.full_comparison("comprehensive"),
                "current_input_fingerprint": fingerprints[language],
                "head_overlay_dependency_fingerprint": {"head": language},
                "current_input_stable_during_language_audit": True,
                "gate": False,
                "elapsed_seconds": 1.0,
            })
        worktree_head = "f" * 40
        return {
            "scope": {
                "gold": {
                    "sha256": phase532.CANDIDATE_LEARNER_SHA256,
                    "fake_coarse_reference": {
                        "sha256": parent["fake_coarse_reference"]["sha256"],
                    },
                },
            },
            "case_count": pin["resolved_cases"],
            "surface_count": pin["surfaces"],
            "raw_case_count": pin["raw_cases"],
            "languages": rows,
            "requested_languages": list(runtime_gate.LANGUAGES),
            "head_oid": contract["baseline_revision"],
            "worktree_head_oid_at_start": worktree_head,
            "worktree_head_oid_at_end": worktree_head,
            "head_stable_at_end": True,
            "reference_projection": projection,
            "resolved_reference": {
                "case_count": pin["resolved_cases"],
                "surface_count": pin["surfaces"],
                "reference_sha256": pin["resolved_reference_sha256"],
            },
            "reviewed_reference": {
                "scope_manifest_sha256": contract["scope_manifest_sha256"],
                "conflict_manifest_sha256": contract[
                    "conflict_manifest_sha256"
                ],
            },
            "checkpoint_context": {
                "head_oid": contract["baseline_revision"],
                "raw_reference_sha256": pin["raw_reference_sha256"],
                "reference_sha256": pin["resolved_reference_sha256"],
                "surface_sha256": pin["surface_sha256"],
                "corpus_sha256": pin["corpus_content_sha256"],
                "corpus_head_oid": pin["corpus_head_oid"],
                "corpus_status_sha256": pin["corpus_status_sha256"],
                "scope_manifest_sha256": contract["scope_manifest_sha256"],
                "gold_sha256": phase532.CANDIDATE_LEARNER_SHA256,
            },
            "resumed_from_audit_code_sha256": None,
            "corpus_stable_at_end": True,
            "corpus_repository_at_end": repository,
            "place_manifest_stable_at_end": True,
            "audit_code_stable_at_end": True,
            "review_manifests_stable_at_end": True,
            "all_app_inputs_stable_at_end": True,
            "app_fingerprints_at_start": fingerprints,
            "app_fingerprints_at_end": copy.deepcopy(fingerprints),
            "complete": True,
            "final_gold_sha256": phase532.CANDIDATE_LEARNER_SHA256,
            "gold_source_matches_snapshot_at_end": True,
            "gold_snapshot_isolated_from_external_changes": True,
            "gold_snapshot_source_stable_during_audit": True,
            "gate": False,
        }

    def e373_comparison(self):
        return self.comparison("current-e373")

    def e373_report(self):
        contract = self.manifest["current_e373_contract"]
        pin = contract["reference_projection"]
        scope_projection = gate._load_current_e373_scope(self.manifest)
        parent_scope = json.loads(
            (HERE / "out" / "_audit_no_worsening_current_only.json")
            .read_text(encoding="utf-8")
        )["scope"]
        scope = {
            "corpus": {
                **copy.deepcopy(scope_projection["corpus"]),
                "extended_reference_manifest": copy.deepcopy(
                    parent_scope["corpus"]["extended_reference_manifest"]
                ),
            },
            "corpus_repository": copy.deepcopy(
                scope_projection["corpus_repository"]
            ),
            "place_manifest": copy.deepcopy(scope_projection["place_manifest"]),
            "gold": {
                **copy.deepcopy(scope_projection["gold"]),
                **{
                    key: copy.deepcopy(parent_scope["gold"][key])
                    for key in (
                        "path", "expected_sha256", "mtime_ns",
                        "consistent_snapshot", "mixed_marker_surface_list",
                        "unmarked_conflicts",
                    )
                },
            },
        }
        return {
            "scope": scope,
            "case_count": pin["resolved_cases"],
            "raw_case_count": pin["raw_cases"],
            "surface_count": pin["surfaces"],
            "languages": [
                {
                    "language": language,
                    "comparison": self.e373_comparison(),
                    "input_fingerprint": {"candidate": language},
                    "input_stable": True,
                    "gate": False,
                }
                for language in runtime_gate.LANGUAGES
            ],
            "reference_projection": copy.deepcopy(scope_projection),
            "resolved_reference": {
                "case_count": pin["resolved_cases"],
                "surface_count": pin["surfaces"],
                "reference_sha256": pin["resolved_reference_sha256"],
            },
            "reviewed_reference": {
                "scope_manifest_sha256": contract["scope_manifest"]["sha256"],
                "conflict_manifest_sha256": contract[
                    "conflict_manifest_sha256"
                ],
            },
            "checkpoint_context": {
                "head_oid": "f" * 40,
                "scope_manifest_sha256": contract["scope_manifest"]["sha256"],
                "conflict_manifest_sha256": contract[
                    "conflict_manifest_sha256"
                ],
                "raw_reference_sha256": pin["raw_reference_sha256"],
                "reference_sha256": pin["resolved_reference_sha256"],
                "surface_sha256": pin["surface_sha256"],
                "corpus_sha256": contract["corpus"]["content_sha256"],
                "corpus_head_oid": contract["corpus"]["head_oid"],
                "corpus_status_sha256": contract["corpus"]["status_sha256"],
                "gold_sha256": phase532.CANDIDATE_LEARNER_SHA256,
            },
            "inputs_stable": {
                key: True for key in self.manifest["audit_contract"][
                    "required_input_stability"
                ]
            },
            "complete": True,
            "gate": False,
        }

    def test_manifest_is_closed_and_old_is_not_a_current_alternative(self):
        self.assertEqual(
            set(self.entries),
            {"kateĥismo", "kateĥisto", "magnetito", "Izraelio", "tia-tia"},
        )
        for entry in self.entries.values():
            self.assertTrue(entry["new_is_only_current_allowance"])
            self.assertNotEqual(entry["old_typed"], entry["new_typed"])
            self.assertNotIn("allowed_current_signatures", entry)

    def test_valid_closed_exception_passes(self):
        result = gate.validate_audit_report(
            self.audit_report(), self.runtime_report(), manifest=self.manifest,
        )
        self.assertTrue(result["gate"])
        self.assertEqual(result["unadjudicated_findings"], 0)
        self.assertEqual(result["trilingual_mismatches"], 0)
        self.assertTrue(result["new_signature_only"])

    def test_runtime_snapshot_must_match_all_three_raw_audit_kinds(self):
        cases = (
            (gate.validate_audit_report, self.audit_report),
            (gate.validate_full_audit_report, self.full_report),
            (gate.validate_current_e373_report, self.e373_report),
        )
        for validator, report_factory in cases:
            with self.subTest(validator=validator.__name__):
                runtime = self.runtime_report()
                runtime["app_input_fingerprints"]["JA"]["candidate"] = (
                    "tampered-between-raw-and-sidecar"
                )
                with self.assertRaisesRegex(
                    ValueError, "runtime/audit app snapshot drift",
                ):
                    validator(
                        report_factory(), runtime, manifest=self.manifest,
                    )

    def test_incomplete_or_unstable_audit_fails_closed(self):
        for mutator in (
            lambda report: report.__setitem__("complete", False),
            lambda report: report["inputs_stable"].__setitem__("corpus", False),
        ):
            report = self.audit_report()
            mutator(report)
            with self.assertRaises(ValueError):
                gate.validate_audit_report(
                    report, self.runtime_report(), manifest=self.manifest,
                )

    def test_parent_gate_true_or_parent_identity_drift_fails(self):
        report = self.audit_report()
        report["gate"] = True
        with self.assertRaises(ValueError):
            gate.validate_audit_report(
                report, self.runtime_report(), manifest=self.manifest,
            )
        report = self.audit_report()
        report["checkpoint_context"]["head_oid"] = "0" * 40
        with self.assertRaises(ValueError):
            gate.validate_audit_report(
                report, self.runtime_report(), manifest=self.manifest,
            )

    def test_unreviewed_surface_cannot_hide_in_any_finding_bucket(self):
        report = self.audit_report()
        extra = copy.deepcopy(
            report["languages"][0]["comparison"]
            ["current_unreferenced_wrong_surfaces"][0]
        )
        extra["surface"] = "magnetito"
        report["languages"][0]["comparison"][
            "current_unreferenced_wrong_surfaces"
        ].append(extra)
        with self.assertRaises(ValueError):
            gate.validate_audit_report(
                report, self.runtime_report(), manifest=self.manifest,
            )

    def test_old_signature_is_never_accepted_as_current(self):
        report = self.audit_report()
        finding = report["languages"][1]["comparison"][
            "current_unreferenced_wrong_surfaces"
        ][0]
        entry = self.entries[finding["surface"]]
        finding["current"] = entry["old_decomposition"]
        finding["current_typed"] = entry["old_typed"]
        with self.assertRaises(ValueError):
            gate.validate_audit_report(
                report, self.runtime_report(), manifest=self.manifest,
            )
        report = self.audit_report()
        finding = report["languages"][0]["comparison"][
            "current_unreferenced_wrong_surfaces"
        ][0]
        finding["expected_signatures"].append(finding["current_signature"])
        with self.assertRaises(ValueError):
            gate.validate_audit_report(
                report, self.runtime_report(), manifest=self.manifest,
            )

    def test_missing_reviewed_replacement_fails_closed(self):
        report = self.audit_report()
        report["languages"][2]["comparison"][
            "current_unreferenced_wrong_surfaces"
        ].pop()
        with self.assertRaises(ValueError):
            gate.validate_audit_report(
                report, self.runtime_report(), manifest=self.manifest,
            )

    def test_trilingual_runtime_scope_and_boundaries_are_mandatory(self):
        for mutator in (
            lambda report: report.__setitem__("trilingual_mismatches", 1),
            lambda report: report.__setitem__("languages", ["JA", "ZH"]),
            lambda report: report.__setitem__("all_inputs_stable", False),
        ):
            runtime = self.runtime_report()
            mutator(runtime)
            with self.assertRaises(ValueError):
                gate.validate_audit_report(
                    self.audit_report(), runtime, manifest=self.manifest,
                )

    def test_scope_guard_tamper_fails_closed(self):
        for key, value in (
            ("scope_guard_surfaces", 27),
            ("scope_guard_trilingual_mismatches", 1),
            ("scope_guard_signature_manifest_sha256", "0" * 64),
            ("scope_guard_gate", False),
        ):
            runtime = self.runtime_report()
            runtime[key] = value
            with self.assertRaises(ValueError):
                gate.validate_audit_report(
                    self.audit_report(), runtime, manifest=self.manifest,
                )

    def test_full_historical_or_partial_schema_is_not_silently_accepted(self):
        report = self.audit_report()
        report["requested_languages"] = list(runtime_gate.LANGUAGES)
        with self.assertRaises(ValueError):
            gate.validate_audit_report(
                report, self.runtime_report(), manifest=self.manifest,
            )

    def test_full_reference_two_is_separate_from_runtime_five_and_sixty_three(self):
        runtime = self.runtime_report()
        result = gate.validate_full_audit_report(
            self.full_report(), runtime, manifest=self.manifest,
        )
        self.assertTrue(result["gate"])
        self.assertEqual(
            self.manifest["full_audit_contract"][
                "required_signature_change_surfaces"
            ],
            ["Izraelio", "tia-tia"],
        )
        self.assertEqual(result["signature_changes"], 2)
        self.assertEqual(result["reference_alignment_improvements"], 0)
        self.assertEqual(result["reviewed_expectation_replacements"], 2)
        self.assertEqual(runtime["adjudicated_source_rows"], 5)
        self.assertEqual(runtime["expanded_payload_variants"], 63)
        self.assertEqual(result["unadjudicated_signature_changes"], 0)
        self.assertEqual(result["trilingual_signature_delta_mismatches"], 0)

    def test_full_signature_change_scope_and_pre_post_are_exact(self):
        report = self.full_report()
        report["languages"][0]["data_isolated"]["signature_changes"][0][
            "surface"
        ] = "Japanio"
        with self.assertRaises(ValueError):
            gate.validate_full_audit_report(
                report, self.runtime_report(), manifest=self.manifest,
            )
        report = self.full_report()
        change = report["languages"][1]["comprehensive"][
            "signature_changes"
        ][1]
        change["current_typed"] = change["baseline_typed"]
        with self.assertRaises(ValueError):
            gate.validate_full_audit_report(
                report, self.runtime_report(), manifest=self.manifest,
            )
        report = self.full_report()
        change = report["languages"][2]["data_isolated"][
            "signature_changes"
        ][0]
        change["baseline_signature"] = change["current_signature"]
        with self.assertRaises(ValueError):
            gate.validate_full_audit_report(
                report, self.runtime_report(), manifest=self.manifest,
            )

    def test_full_classification_and_trilingual_delta_tamper_fail(self):
        report = self.full_report()
        stats = report["languages"][0]["data_isolated"]["sources"][
            "gold_fake_coarse_pejvo_original"
        ]
        stats["improvement_cases"] = 1
        stats["improvement_weight"] = 1
        with self.assertRaises(ValueError):
            gate.validate_full_audit_report(
                report, self.runtime_report(), manifest=self.manifest,
            )
        report = self.full_report()
        report["languages"][1]["comprehensive"]["signature_changes"].reverse()
        with self.assertRaises(ValueError):
            gate.validate_full_audit_report(
                report, self.runtime_report(), manifest=self.manifest,
            )
        report = self.full_report()
        report["worktree_head_oid_at_end"] = "0" * 40
        with self.assertRaises(ValueError):
            gate.validate_full_audit_report(
                report, self.runtime_report(), manifest=self.manifest,
            )
        report = self.full_report()
        report["worktree_head_oid_at_start"] = "z" * 40
        report["worktree_head_oid_at_end"] = "z" * 40
        with self.assertRaises(ValueError):
            gate.validate_full_audit_report(
                report, self.runtime_report(), manifest=self.manifest,
            )
        report = self.full_report()
        report["reviewed_reference"]["conflict_manifest_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            gate.validate_full_audit_report(
                report, self.runtime_report(), manifest=self.manifest,
            )

    def test_valid_current_e373_scope_passes_without_replacing_parent(self):
        result = gate.validate_current_e373_report(
            self.e373_report(), self.runtime_report(), manifest=self.manifest,
        )
        self.assertTrue(result["gate"])
        self.assertEqual(
            result["corpus_head_oid"],
            "e37337822cf31529ba50b8534227721e4ec39a38",
        )
        self.assertEqual(result["html_mismatches"], 0)
        self.assertEqual(result["unadjudicated_findings"], 0)
        self.assertNotEqual(
            self.manifest["current_e373_contract"]["scope_manifest"]["sha256"],
            self.manifest["parent_authority"]["scope_manifest"]["sha256"],
        )

    def test_current_e373_identity_tamper_fails_closed(self):
        for mutator in (
            lambda report: report["reviewed_reference"].__setitem__(
                "scope_manifest_sha256",
                self.manifest["parent_authority"]["scope_manifest"]["sha256"],
            ),
            lambda report: report["checkpoint_context"].__setitem__(
                "corpus_head_oid", "b769038ef15346a536ce93721d6f0f46849db0ea",
            ),
            lambda report: report["reference_projection"].__setitem__(
                "reference_sha256", "0" * 64,
            ),
            lambda report: report["scope"]["corpus"].__setitem__(
                "content_sha256", "0" * 64,
            ),
            lambda report: report["scope"]["place_manifest"].__setitem__(
                "rows", "TAMPERED",
            ),
            lambda report: report["checkpoint_context"].__setitem__(
                "head_oid", "z" * 40,
            ),
            lambda report: report["scope"]["gold"].__setitem__(
                "mtime_ns", True,
            ),
            lambda report: report["scope"]["gold"].__setitem__(
                "mixed_marker_surface_list",
                list(range(report["scope"]["gold"]["mixed_marker_surfaces"])),
            ),
        ):
            report = self.e373_report()
            mutator(report)
            with self.assertRaises(ValueError):
                gate.validate_current_e373_report(
                    report, self.runtime_report(), manifest=self.manifest,
                )

    def test_current_e373_html_and_exception_closure_tamper_fail(self):
        report = self.e373_report()
        html_stats = report["languages"][0]["comparison"]["sources"][
            "html_corpus"
        ]
        html_stats["current_correct_weight"] -= 1
        html_stats["baseline_correct_weight"] -= 1
        with self.assertRaises(ValueError):
            gate.validate_current_e373_report(
                report, self.runtime_report(), manifest=self.manifest,
            )
        report = self.e373_report()
        gold_stats = report["languages"][0]["comparison"]["sources"][
            "gold_unmarked"
        ]
        gold_stats["baseline_correct_weight"] = gold_stats["total_weight"] + 1
        gold_stats["current_correct_weight"] = gold_stats["total_weight"] + 1
        gold_stats["baseline_correct_cases"] = gold_stats["total_cases"] + 1
        gold_stats["current_correct_cases"] = gold_stats["total_cases"] + 1
        report["languages"][0]["comparison"]["combined"] = _sum_stat_blocks(
            report["languages"][0]["comparison"]["sources"].values()
        )
        with self.assertRaises(ValueError):
            gate.validate_current_e373_report(
                report, self.runtime_report(), manifest=self.manifest,
            )
        report = self.e373_report()
        html_stats = report["languages"][0]["comparison"]["sources"][
            "html_corpus"
        ]
        html_stats["total_cases"] = 0
        html_stats["baseline_correct_cases"] = 0
        html_stats["current_correct_cases"] = 0
        report["languages"][0]["comparison"]["combined"] = _sum_stat_blocks(
            report["languages"][0]["comparison"]["sources"].values()
        )
        with self.assertRaises(ValueError):
            gate.validate_current_e373_report(
                report, self.runtime_report(), manifest=self.manifest,
            )
        report = self.e373_report()
        report["languages"][1]["comparison"]["combined"] = _stat_block(
            total=1, correct=0,
        )
        with self.assertRaises(ValueError):
            gate.validate_current_e373_report(
                report, self.runtime_report(), manifest=self.manifest,
            )
        report = self.e373_report()
        extra = copy.deepcopy(report["languages"][2]["comparison"][
            "current_unreferenced_wrong_surfaces"
        ][0])
        extra["surface"] = "magnetito"
        report["languages"][2]["comparison"][
            "current_unreferenced_wrong_surfaces"
        ].append(extra)
        with self.assertRaises(ValueError):
            gate.validate_current_e373_report(
                report, self.runtime_report(), manifest=self.manifest,
            )

    def test_statistics_contract_seals_all_fresh_report_profiles(self):
        contract = self.manifest["statistics_contract"]
        self.assertEqual(len(contract["required_sources"]), 9)
        self.assertEqual(len(set(contract["required_sources"])), 9)
        self.assertEqual(contract["stat_keys"], sorted(gate.STAT_KEYS))
        report_cases = (
            (
                "_audit_no_worsening_current_only.json",
                "comparison", "parent-current",
            ),
            (
                "_audit_no_worsening.json",
                "data_isolated", "full-data-isolated",
            ),
            (
                "_audit_no_worsening.json",
                "comprehensive", "full-comprehensive",
            ),
            (
                "_audit_no_worsening_current_e373.json",
                "comparison", "current-e373",
            ),
        )
        for filename, comparison_key, profile in report_cases:
            report = json.loads(
                (HERE / "out" / filename).read_text(encoding="utf-8")
            )
            for row in report["languages"]:
                with self.subTest(profile=profile, language=row["language"]):
                    comparison = row[comparison_key]
                    gate._validate_absolute_statistics(
                        comparison, self.manifest, profile,
                        f"test/{row['language']}/{profile}",
                    )

    def test_parent_statistics_reject_missing_extra_zero_and_totals(self):
        def missing_source(comparison):
            comparison["sources"].pop("html_place_manifest")

        def extra_source(comparison):
            comparison["sources"]["unreviewed_source"] = copy.deepcopy(
                comparison["sources"]["html_place_manifest"]
            )

        def zero_source(comparison):
            comparison["sources"]["html_place_manifest"] = {
                key: 0 for key in gate.STAT_KEYS
            }

        def totals_drift(comparison):
            comparison["sources"]["html_place_manifest"]["total_weight"] += 1

        for label, mutator in (
            ("missing", missing_source),
            ("extra", extra_source),
            ("zero", zero_source),
            ("totals", totals_drift),
        ):
            with self.subTest(mutation=label):
                report = self.audit_report()
                comparison = report["languages"][0]["comparison"]
                mutator(comparison)
                comparison["combined"] = _sum_stat_blocks(
                    comparison["sources"].values()
                )
                with self.assertRaises(ValueError):
                    gate.validate_audit_report(
                        report, self.runtime_report(), manifest=self.manifest,
                    )

    def test_both_full_and_e373_absolute_totals_mutations_fail(self):
        full_report = self.full_report()
        for label in ("data_isolated", "comprehensive"):
            with self.subTest(profile=f"full-{label}"):
                report = copy.deepcopy(full_report)
                comparison = report["languages"][0][label]
                source = comparison["sources"]["html_place_manifest"]
                source["total_cases"] += 1
                comparison["combined"] = _sum_stat_blocks(
                    comparison["sources"].values()
                )
                with self.assertRaises(ValueError):
                    gate.validate_full_audit_report(
                        report, self.runtime_report(), manifest=self.manifest,
                    )
        report = self.e373_report()
        comparison = report["languages"][0]["comparison"]
        source = comparison["sources"]["html_corpus"]
        source["total_cases"] += 1
        source["baseline_correct_cases"] += 1
        source["current_correct_cases"] += 1
        comparison["combined"] = _sum_stat_blocks(
            comparison["sources"].values()
        )
        with self.assertRaises(ValueError):
            gate.validate_current_e373_report(
                report, self.runtime_report(), manifest=self.manifest,
            )

    def test_combined_must_equal_source_sum_in_every_audit_mode(self):
        parent = self.audit_report()
        parent["languages"][0]["comparison"]["combined"]["total_weight"] += 1
        with self.assertRaises(ValueError):
            gate.validate_audit_report(
                parent, self.runtime_report(), manifest=self.manifest,
            )

        for label in ("data_isolated", "comprehensive"):
            with self.subTest(profile=f"full-{label}"):
                full = self.full_report()
                full["languages"][0][label]["combined"]["total_weight"] += 1
                with self.assertRaises(ValueError):
                    gate.validate_full_audit_report(
                        full, self.runtime_report(), manifest=self.manifest,
                    )

        current = self.e373_report()
        current["languages"][0]["comparison"]["combined"]["total_weight"] += 1
        with self.assertRaises(ValueError):
            gate.validate_current_e373_report(
                current, self.runtime_report(), manifest=self.manifest,
            )

    def test_audit_kinds_cannot_be_silently_mixed(self):
        with self.assertRaises(ValueError):
            gate.validate_audit_report(
                self.full_report(), self.runtime_report(), manifest=self.manifest,
            )
        with self.assertRaises(ValueError):
            gate.validate_full_audit_report(
                self.e373_report(), self.runtime_report(), manifest=self.manifest,
            )
        with self.assertRaises(ValueError):
            gate.validate_current_e373_report(
                self.audit_report(), self.runtime_report(), manifest=self.manifest,
            )


if __name__ == "__main__":
    unittest.main()
