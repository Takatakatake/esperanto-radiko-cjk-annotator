# -*- coding: utf-8 -*-
"""Fail-closed no-worsening sidecar for the five Phase 558 Ruby repairs.

The Phase 532 scope, strict table, and fake/coarse manifest remain immutable.
The ordinary current-only audit must finish against those exact inputs.  This
sidecar then permits only two explicitly reviewed old-expectation replacements;
the other three repairs are covered by the parent fake/coarse authority in
current-only mode and by the deployed runtime closure, but their surfaces are
absent from the full historical reference projection.

Two additional modes stay deliberately separate: a full historical audit must
publish only the two signature changes whose surfaces actually occur in its
reference projection, while the deployed runtime closure independently proves
all five adjudicated rows and 63 expanded payload forms.  A current e373 audit
must use its own tracked scope copy and fixed corpus/reference identity. Neither
mode changes or silently substitutes the parent activation authority.

Old signatures are checked solely as predecessor evidence.  They are never
accepted as alternatives to the one post-regen signature for a current build.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import phase532_ruby_policy as phase532
import phase558_ruby_overlay as overlay_policy
import phase558_ruby_overlay_runtime_gate as runtime_gate


HERE = Path(__file__).resolve().parent
MANIFEST_PATH = HERE / "_phase558_no_worsening_sidecar.json"
EXPECTED_MANIFEST_SHA256 = (
    "7468D660EC39089E9F931BE9F79BF45D0AD5DFEC38F6281651F489D94FAE7FBA"
)
EXPECTED_POLICY = (
    "Evaluate the immutable Phase 532 no-worsening authority first, then "
    "accept only the closed five-surface Phase 558 Ruby overlay. Three coarse "
    "fusions are closed by the immutable parent fake/coarse authority and the "
    "deployed runtime closure over all five adjudicated rows and 63 expanded "
    "forms; they are not claimed as changes in the full historical reference, "
    "where those three surfaces are absent. Two reviewed replacements supersede "
    "exactly one old current-only expectation each and are the only full-reference "
    "signature changes. An old signature is predecessor evidence, never an "
    "alternative current allowance."
)
EXPECTED_DISPOSITIONS = {
    "reference_alignment_improvement": 3,
    "reviewed_expectation_replacement": 2,
}
EXPECTED_ENTRY_KEYS = {
    "reference_alignment_improvement": {
        "surface", "disposition", "old_decomposition", "old_typed",
        "new_decomposition", "new_typed", "new_is_only_current_allowance",
        "expected_current_wrong_buckets",
    },
    "reviewed_expectation_replacement": {
        "surface", "disposition", "old_decomposition", "old_typed",
        "new_decomposition", "new_typed", "new_is_only_current_allowance",
        "required_reference_sources", "expected_current_wrong_buckets",
    },
}
CURRENT_ONLY_TOP_KEYS = {
    "scope", "case_count", "raw_case_count", "surface_count", "languages",
    "reference_projection", "resolved_reference", "reviewed_reference",
    "checkpoint_context", "inputs_stable", "complete", "gate",
}
CURRENT_ONLY_LANGUAGE_KEYS = {
    "language", "comparison", "input_fingerprint", "input_stable", "gate",
}
FULL_TOP_KEYS = {
    "scope", "case_count", "surface_count", "raw_case_count", "languages",
    "requested_languages", "head_oid", "worktree_head_oid_at_start",
    "worktree_head_oid_at_end", "head_stable_at_end",
    "reference_projection", "resolved_reference", "reviewed_reference",
    "checkpoint_context", "resumed_from_audit_code_sha256",
    "corpus_stable_at_end", "corpus_repository_at_end",
    "place_manifest_stable_at_end", "audit_code_stable_at_end",
    "review_manifests_stable_at_end", "all_app_inputs_stable_at_end",
    "app_fingerprints_at_start", "app_fingerprints_at_end", "complete",
    "final_gold_sha256", "gold_source_matches_snapshot_at_end",
    "gold_snapshot_isolated_from_external_changes",
    "gold_snapshot_source_stable_during_audit", "gate",
}
FULL_LANGUAGE_KEYS = {
    "language", "data_isolated_definition", "comprehensive_definition",
    "data_isolated", "comprehensive", "current_input_fingerprint",
    "head_overlay_dependency_fingerprint",
    "current_input_stable_during_language_audit", "gate", "elapsed_seconds",
}
FINDING_KEYS = {
    "regression_cases",
    "changed_to_unreferenced_wrong_surfaces",
    "current_unreferenced_wrong_surfaces",
    "current_place_manifest_wrong_cases",
    "current_official_override_wrong_cases",
    "current_project_ruby_boundary_override_wrong_cases",
    "current_exact_required_wrong_cases",
}
STAT_KEYS = {
    "total_weight", "total_cases",
    "baseline_correct_weight", "baseline_correct_cases",
    "current_correct_weight", "current_correct_cases",
    "regression_weight", "regression_cases",
    "improvement_weight", "improvement_cases",
}
EXPECTED_STATISTICS_CONTRACT = {
    "required_sources": [
        "gold_fake_coarse_paired_academic",
        "gold_fake_coarse_pejvo_original",
        "gold_fake_coarse_project_reviewed_override",
        "gold_official_override",
        "gold_phase532_selected_ruby_policy",
        "gold_project_ruby_boundary_override",
        "gold_unmarked",
        "html_corpus",
        "html_place_manifest",
    ],
    "stat_keys": sorted(STAT_KEYS),
    "profiles": {
        "parent-current": {
            "comparison": "current_only",
            "source_statistics_sha256": (
                "69CB63BA1C59E90909BB3D84752FC69F9B9B4D7DD45C64D11EF78FBB5FC5FE41"
            ),
            "combined": {
                "total_weight": 323527,
                "total_cases": 74300,
                "baseline_correct_weight": 323525,
                "baseline_correct_cases": 74298,
                "current_correct_weight": 323525,
                "current_correct_cases": 74298,
                "regression_weight": 0,
                "regression_cases": 0,
                "improvement_weight": 0,
                "improvement_cases": 0,
            },
        },
        "full-data-isolated": {
            "comparison": "data_isolated",
            "source_statistics_sha256": (
                "8F6E8ECC69B11CEE45B08B0F00A963282F2004C59863C7F6079FF12D3923F685"
            ),
            "combined": {
                "total_weight": 323527,
                "total_cases": 74300,
                "baseline_correct_weight": 323527,
                "baseline_correct_cases": 74300,
                "current_correct_weight": 323525,
                "current_correct_cases": 74298,
                "regression_weight": 2,
                "regression_cases": 2,
                "improvement_weight": 0,
                "improvement_cases": 0,
            },
        },
        "full-comprehensive": {
            "comparison": "comprehensive",
            "source_statistics_sha256": (
                "8F6E8ECC69B11CEE45B08B0F00A963282F2004C59863C7F6079FF12D3923F685"
            ),
            "combined": {
                "total_weight": 323527,
                "total_cases": 74300,
                "baseline_correct_weight": 323527,
                "baseline_correct_cases": 74300,
                "current_correct_weight": 323525,
                "current_correct_cases": 74298,
                "regression_weight": 2,
                "regression_cases": 2,
                "improvement_weight": 0,
                "improvement_cases": 0,
            },
        },
        "current-e373": {
            "comparison": "current_only",
            "source_statistics_sha256": (
                "8A67A8E38E47B63839BD557AD124BC44796C73E83E11428029B5CC58E16AF0D1"
            ),
            "combined": {
                "total_weight": 323527,
                "total_cases": 74295,
                "baseline_correct_weight": 323525,
                "baseline_correct_cases": 74293,
                "current_correct_weight": 323525,
                "current_correct_cases": 74293,
                "regression_weight": 0,
                "regression_cases": 0,
                "improvement_weight": 0,
                "improvement_cases": 0,
            },
        },
    },
}
FULL_COMPARISON_KEYS = {
    "comparison", "sources", "combined", *FINDING_KEYS,
    "weighted_worsening_sources", "signature_changes", "gate",
}
AUDIT_KINDS = (
    "parent-current",
    "full-old-to-new",
    "current-e373",
)


def compact_sha256(value) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


def stable_json_sha256(value) -> str:
    raw = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
    ).encode("ascii")
    return hashlib.sha256(raw).hexdigest().upper()


def is_git_oid(value) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(character in "0123456789abcdef" for character in value)
    )


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _typed_signature(signature) -> str:
    _reconstruction, spans = signature
    return "|".join(
        f"{'R' if is_ruby else 'L'}:{text}" for text, is_ruby in spans
    )


def _decomposition(signature) -> str:
    _reconstruction, spans = signature
    return "/".join(text for text, _is_ruby in spans)


def _signature_payload(signature) -> dict:
    reconstruction, spans = signature
    return {
        "reconstruction": reconstruction,
        "spans": [
            {"text": text, "ruby": bool(is_ruby)}
            for text, is_ruby in spans
        ],
    }


def _entry_index(manifest: dict) -> dict:
    return {entry["surface"]: entry for entry in manifest["entries"]}


def load_manifest() -> dict:
    raw = MANIFEST_PATH.read_bytes()
    digest = hashlib.sha256(raw).hexdigest().upper()
    if EXPECTED_MANIFEST_SHA256.startswith("TO_BE_SEALED"):
        raise ValueError(f"unsealed Phase 558 no-worsening manifest: {digest}")
    if digest != EXPECTED_MANIFEST_SHA256:
        raise ValueError(
            "Phase 558 no-worsening manifest drift: "
            f"{digest} != {EXPECTED_MANIFEST_SHA256}"
        )
    manifest = json.loads(raw.decode("utf-8"))
    expected_top = {
        "schema_version", "phase_from", "phase_to", "policy",
        "parent_authority", "audit_contract", "full_audit_contract",
        "current_e373_contract", "statistics_contract", "expected_counts",
        "entries_sha256", "entries",
    }
    if set(manifest) != expected_top:
        raise ValueError("Phase 558 no-worsening manifest schema drift")
    if (
        manifest["schema_version"] != 2
        or manifest["phase_from"] != 532
        or manifest["phase_to"] != 558
        or manifest["policy"] != EXPECTED_POLICY
    ):
        raise ValueError("Phase 558 no-worsening manifest identity drift")

    parent = manifest["parent_authority"]
    expected_parent_keys = {
        "app_head_oid", "scope_manifest", "strict_reference",
        "fake_coarse_reference", "phase558_overlay_review",
    }
    if set(parent) != expected_parent_keys:
        raise ValueError("Phase 558 parent-authority schema drift")
    if parent["app_head_oid"] != "dcfca809b711075788ee00b6323cdd2ea31618ff":
        raise ValueError("Phase 558 parent app HEAD drift")
    for name in (
        "scope_manifest", "strict_reference", "fake_coarse_reference",
        "phase558_overlay_review",
    ):
        identity = parent[name]
        expected_identity_keys = {"path", "bytes", "sha256"}
        if name == "phase558_overlay_review":
            expected_identity_keys.add("entries_sha256")
        if set(identity) != expected_identity_keys:
            raise ValueError(f"Phase 558 parent identity schema drift: {name}")
        path = HERE / identity["path"]
        if (
            not path.is_file()
            or path.stat().st_size != identity["bytes"]
            or file_sha256(path) != identity["sha256"]
        ):
            raise ValueError(f"Phase 558 immutable parent drift: {name}")

    contract = manifest["audit_contract"]
    expected_contract_keys = {
        "kind", "required_languages", "required_input_stability",
        "required_comparison_keys", "always_empty_findings",
        "candidate_runtime_mode", "candidate_signature_manifest_sha256",
        "candidate_scope_guard_surfaces",
        "candidate_scope_guard_signature_manifest_sha256",
    }
    if set(contract) != expected_contract_keys:
        raise ValueError("Phase 558 audit contract schema drift")
    if (
        contract["kind"] != "current_only"
        or contract["required_languages"] != list(runtime_gate.LANGUAGES)
        or contract["candidate_runtime_mode"] != "post-regen"
        or contract["candidate_signature_manifest_sha256"]
        != runtime_gate.EXPECTED_SIGNATURE_MANIFEST_SHA256["post-regen"]
        or contract["candidate_scope_guard_surfaces"]
        != len(runtime_gate.SCOPE_GUARD_TARGETS)
        or contract["candidate_scope_guard_signature_manifest_sha256"]
        != runtime_gate.SCOPE_GUARD_SIGNATURE_MANIFEST_SHA256
        or set(contract["required_comparison_keys"])
        != {
            "comparison", "sources", "combined", *FINDING_KEYS,
            "weighted_worsening_sources", "gate",
        }
        or not set(contract["always_empty_findings"]).issubset(
            FINDING_KEYS | {"weighted_worsening_sources"}
        )
    ):
        raise ValueError("Phase 558 audit contract identity drift")

    full_contract = manifest["full_audit_contract"]
    expected_full_contract_keys = {
        "kind", "baseline_revision", "worktree_head_policy",
        "scope_manifest_sha256", "conflict_manifest_sha256",
        "reference_projection", "required_languages", "required_comparisons",
        "required_signature_change_surfaces", "expected_combined_delta",
        "expected_source_deltas", "expected_weighted_worsening_sources",
        "assumptions",
    }
    if (
        not isinstance(full_contract, dict)
        or set(full_contract) != expected_full_contract_keys
        or full_contract["kind"] != "full_old_to_new"
        or full_contract["baseline_revision"] != parent["app_head_oid"]
        or full_contract["worktree_head_policy"]
        != "stable_not_baseline_pinned"
        or full_contract["scope_manifest_sha256"]
        != parent["scope_manifest"]["sha256"]
        or full_contract["conflict_manifest_sha256"]
        != "2EDE9CDCB492D1B99C990818EF2E82809C49BDB9943EAB163E04B93C4FA58D94"
        or full_contract["reference_projection"] != {
            "raw_cases": 68524,
            "surfaces": 68435,
            "raw_reference_sha256": (
                "308121D186957A792073F1620C5A4E5EA80D3B7EAA87DFE39573E05A2FE822A9"
            ),
            "resolved_cases": 68485,
            "resolved_reference_sha256": (
                "C6409A1F5CBF5C4ECB14D16592FA5238A141800A3DC69C3676EAF4016A5092A6"
            ),
            "surface_sha256": (
                "CC3BAFBC6CD1558BF9BD3FCC680245819CA1C1059AE4AEE8BAAA0F64415576FE"
            ),
            "corpus_head_oid": "b769038ef15346a536ce93721d6f0f46849db0ea",
            "corpus_content_sha256": (
                "264E4217BE484ABC2DC5EF7A22D83C56076C255BFB389F8218A0C215DD2420B6"
            ),
            "corpus_status_sha256": (
                "E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855"
            ),
        }
        or full_contract["required_languages"] != list(runtime_gate.LANGUAGES)
        or full_contract["required_comparisons"]
        != ["data_isolated", "comprehensive"]
        or full_contract["required_signature_change_surfaces"]
        != ["Izraelio", "tia-tia"]
        or full_contract["expected_combined_delta"] != {
            "regression_cases": 2,
            "improvement_cases": 0,
            "current_minus_baseline_correct_cases": -2,
        }
        or full_contract["expected_source_deltas"] != {
            "gold_unmarked": {
                "regression_cases": 2,
                "improvement_cases": 0,
                "current_minus_baseline_correct_cases": -2,
            },
        }
        or full_contract["expected_weighted_worsening_sources"]
        != ["gold_unmarked", "combined"]
        or not isinstance(full_contract["assumptions"], list)
        or len(full_contract["assumptions"]) != 4
        or any(not assumption for assumption in full_contract["assumptions"])
    ):
        raise ValueError("Phase 558 full-audit contract identity drift")

    current_contract = manifest["current_e373_contract"]
    expected_current_contract_keys = {
        "kind", "scope_manifest", "worktree_head_policy", "corpus",
        "reference_projection", "conflict_manifest_sha256",
        "required_html_source", "required_current_wrong_surfaces",
    }
    if (
        not isinstance(current_contract, dict)
        or set(current_contract) != expected_current_contract_keys
        or current_contract["kind"] != "current_e373"
        or current_contract["worktree_head_policy"]
        != "stable_not_parent_pinned"
        or current_contract["scope_manifest"] != {
            "path": "_phase558_current_corpus_scope_manifest.json",
            "bytes": 10351,
            "sha256": (
                "AA293B609B91A12E38D77AAD6F3C3E02EF033CE762E9FF91B6A547B4A91AC9E2"
            ),
        }
        or current_contract["corpus"] != {
            "head_oid": "e37337822cf31529ba50b8534227721e4ec39a38",
            "content_sha256": (
                "9AC90579B5A935FCDF432BB0CC37CA6D6A0131A5049CFD4215B69FC7F6C369C6"
            ),
            "status_sha256": (
                "E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855"
            ),
            "files": 169,
            "html_weight": 271065,
        }
        or current_contract["reference_projection"] != {
            "projection_sha256": (
                "C5CAB61A2940E52D1BDDD83692EB989C438435C2F694E6B391083B6DD6C154AE"
            ),
            "raw_cases": 68518,
            "surfaces": 68429,
            "raw_reference_sha256": (
                "2A27673CF092CF25779F7C063A3B45770CB158BF3A0CC5D799C5428780BBE6E3"
            ),
            "reference_conflicts": 89,
            "reference_conflicts_sha256": (
                "16FD7BFCF7C1FC1840400FC4D09B83BCA96B987971C12C5BDE1A5D6A5D42404E"
            ),
            "resolved_cases": 68479,
            "resolved_reference_sha256": (
                "15FBD64AC965844E37F07B41A5885087DECF330860A90A6CE0423B6128A51E28"
            ),
            "surface_sha256": (
                "434159C8552E876142BBBE0369A4F86FCF5E7F020EA77E74F02E65236F24B64A"
            ),
        }
        or current_contract["conflict_manifest_sha256"]
        != "2EDE9CDCB492D1B99C990818EF2E82809C49BDB9943EAB163E04B93C4FA58D94"
        or current_contract["required_html_source"] != "html_corpus"
        or current_contract["required_current_wrong_surfaces"]
        != ["Izraelio", "tia-tia"]
    ):
        raise ValueError("Phase 558 e373 current-audit contract identity drift")

    if manifest["statistics_contract"] != EXPECTED_STATISTICS_CONTRACT:
        raise ValueError("Phase 558 absolute statistics contract identity drift")

    entries = manifest["entries"]
    counts = manifest["expected_counts"]
    if (
        not isinstance(entries, list)
        or compact_sha256(entries) != manifest["entries_sha256"]
        or counts != {
            "entries": 5,
            "reference_alignment_improvement": 3,
            "reviewed_expectation_replacement": 2,
            "allowed_current_wrong_surfaces": 2,
            "languages": 3,
        }
        or len(entries) != counts["entries"]
    ):
        raise ValueError("Phase 558 no-worsening entry identity drift")

    review_identity = overlay_policy.review_identity()
    review_pin = parent["phase558_overlay_review"]
    if (
        review_identity["review_sha256"] != review_pin["sha256"]
        or review_identity["entries_sha256"] != review_pin["entries_sha256"]
    ):
        raise ValueError("Phase 558 overlay review cross-link drift")
    selected_targets = overlay_policy.selected_ruby_targets()
    if full_contract["required_signature_change_surfaces"] != [
        "Izraelio", "tia-tia",
    ]:
        raise ValueError("Phase 558 full signature-change surface scope drift")
    pre_signatures, _pre_digest = runtime_gate.expected_signatures("pre-regen")
    post_signatures, post_digest = runtime_gate.expected_signatures("post-regen")
    if post_digest != contract["candidate_signature_manifest_sha256"]:
        raise ValueError("Phase 558 post-regen signature pin drift")

    dispositions: dict[str, int] = {}
    surfaces = set()
    replacement_count = 0
    for entry in entries:
        disposition = entry.get("disposition")
        if disposition not in EXPECTED_ENTRY_KEYS:
            raise ValueError(f"unknown Phase 558 disposition: {disposition!r}")
        if set(entry) != EXPECTED_ENTRY_KEYS[disposition]:
            raise ValueError(
                f"Phase 558 entry schema drift: {entry.get('surface')!r}"
            )
        surface = entry["surface"]
        if surface in surfaces or surface not in selected_targets:
            raise ValueError(f"Phase 558 surface scope drift: {surface!r}")
        surfaces.add(surface)
        dispositions[disposition] = dispositions.get(disposition, 0) + 1
        if entry["new_is_only_current_allowance"] is not True:
            raise ValueError(f"Phase 558 current allowance is not singular: {surface}")
        old_signature = pre_signatures[surface]
        new_signature = post_signatures[surface]
        if (
            entry["old_decomposition"] != _decomposition(old_signature)
            or entry["old_typed"] != _typed_signature(old_signature)
            or entry["new_decomposition"] != _decomposition(new_signature)
            or entry["new_typed"] != _typed_signature(new_signature)
            or entry["new_decomposition"] != selected_targets[surface]
            or old_signature == new_signature
            or entry["old_typed"] == entry["new_typed"]
        ):
            raise ValueError(f"Phase 558 old/new signature drift: {surface!r}")
        expected_buckets = entry["expected_current_wrong_buckets"]
        if (
            not isinstance(expected_buckets, list)
            or len(expected_buckets) != len(set(expected_buckets))
            or not set(expected_buckets).issubset(FINDING_KEYS)
        ):
            raise ValueError(f"Phase 558 finding-bucket drift: {surface!r}")
        if disposition == "reference_alignment_improvement":
            if expected_buckets:
                raise ValueError(
                    f"reference-aligned repair was made an exception: {surface!r}"
                )
        else:
            replacement_count += 1
            if expected_buckets != ["current_unreferenced_wrong_surfaces"]:
                raise ValueError(
                    f"reviewed replacement bucket drift: {surface!r}"
                )
            sources = entry["required_reference_sources"]
            if not isinstance(sources, list) or not sources or len(sources) != len(set(sources)):
                raise ValueError(f"reviewed replacement source drift: {surface!r}")
    if (
        surfaces != set(selected_targets)
        or dispositions != EXPECTED_DISPOSITIONS
        or replacement_count != counts["allowed_current_wrong_surfaces"]
        or {
            entry["surface"] for entry in entries
            if entry["disposition"] == "reviewed_expectation_replacement"
        } != set(full_contract["required_signature_change_surfaces"])
    ):
        raise ValueError("Phase 558 closed surface/disposition count drift")

    # The three fusions are not exceptions to no-worsening: each is already an
    # independently pinned PEJVO coarse authority in the untouched Phase 532
    # fake/coarse manifest.  Verify actual membership, rather than inferring it
    # merely from the absence of a current-only failure row.
    fake_path = HERE / parent["fake_coarse_reference"]["path"]
    fake_payload = json.loads(fake_path.read_text(encoding="utf-8"))
    fake_entries = fake_payload.get("entries")
    if not isinstance(fake_entries, list):
        raise ValueError("Phase 558 parent fake/coarse entry schema drift")
    for entry in entries:
        if entry["disposition"] != "reference_alignment_improvement":
            continue
        surface = entry["surface"]
        matches = [
            row for row in fake_entries
            if phase532.canonical(row.get("surface", ""))
            == phase532.canonical(surface)
        ]
        if len(matches) != 1:
            raise ValueError(
                f"Phase 558 coarse parent-reference coverage drift: {surface!r}"
            )
        row = matches[0]
        expected_line = overlay_policy.EXPECTED_ROWS[surface]["learner_line"]
        if (
            row.get("authority") != "pejvo_original"
            or row.get("learner_line") != expected_line
            or phase532.canonical(row.get("learner_decomposition", ""))
            != phase532.canonical(entry["old_decomposition"])
            or phase532.canonical(row.get("coarse_decomposition", ""))
            != phase532.canonical(entry["new_decomposition"])
        ):
            raise ValueError(
                f"Phase 558 coarse parent-reference identity drift: {surface!r}"
            )
    return manifest


def _load_current_e373_scope(manifest: dict) -> dict:
    contract = manifest["current_e373_contract"]
    identity = contract["scope_manifest"]
    path = HERE / identity["path"]
    if (
        not path.is_file()
        or path.stat().st_size != identity["bytes"]
        or file_sha256(path) != identity["sha256"]
    ):
        raise ValueError("Phase 558 tracked e373 scope identity drift")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if set(payload) != {"manifest_schema_version", "projection_sha256", "expected"}:
        raise ValueError("Phase 558 tracked e373 scope schema drift")
    expected = payload["expected"]
    projection_pin = contract["reference_projection"]
    corpus_pin = contract["corpus"]
    if (
        payload["manifest_schema_version"] != 1
        or payload["projection_sha256"] != projection_pin["projection_sha256"]
        or stable_json_sha256(expected) != payload["projection_sha256"]
        or expected.get("case_count") != projection_pin["raw_cases"]
        or expected.get("surface_count") != projection_pin["surfaces"]
        or expected.get("reference_sha256")
        != projection_pin["raw_reference_sha256"]
        or expected.get("reference_conflict_count")
        != projection_pin["reference_conflicts"]
        or expected.get("reference_conflicts_sha256")
        != projection_pin["reference_conflicts_sha256"]
        or expected.get("corpus", {}).get("files") != corpus_pin["files"]
        or expected.get("corpus", {}).get("content_sha256")
        != corpus_pin["content_sha256"]
        or expected.get("corpus_repository", {}).get("head_oid")
        != corpus_pin["head_oid"]
        or expected.get("corpus_repository", {}).get("status_entries") != 0
        or expected.get("corpus_repository", {}).get("status_sha256")
        != corpus_pin["status_sha256"]
        or expected.get("gold", {}).get("sha256")
        != phase532.CANDIDATE_LEARNER_SHA256
    ):
        raise ValueError("Phase 558 tracked e373 scope content drift")
    return expected


def _validate_scope_projection(scope: dict, expected: dict, label: str) -> None:
    expected_sections = {
        key: expected[key]
        for key in ("corpus", "corpus_repository", "place_manifest", "gold")
    }
    if not isinstance(scope, dict) or set(scope) != set(expected_sections):
        raise ValueError(f"{label} scope schema drift")
    corpus = scope.get("corpus")
    expected_corpus = expected_sections["corpus"]
    if (
        not isinstance(corpus, dict)
        or set(corpus) != set(expected_corpus) | {"extended_reference_manifest"}
        or {key: corpus[key] for key in expected_corpus} != expected_corpus
        or stable_json_sha256(corpus["extended_reference_manifest"])
        != expected_corpus["extended_reference_sha256"]
    ):
        raise ValueError(f"{label} corpus scope drift")
    if scope["corpus_repository"] != expected_sections["corpus_repository"]:
        raise ValueError(f"{label} corpus-repository scope drift")
    if scope["place_manifest"] != expected_sections["place_manifest"]:
        raise ValueError(f"{label} place-manifest scope drift")

    gold = scope.get("gold")
    expected_gold = expected_sections["gold"]
    gold_extras = {
        "path", "expected_sha256", "mtime_ns", "consistent_snapshot",
        "mixed_marker_surface_list", "unmarked_conflicts",
    }
    if (
        not isinstance(gold, dict)
        or set(gold) != set(expected_gold) | gold_extras
        or {key: gold[key] for key in expected_gold} != expected_gold
        or not isinstance(gold["path"], str)
        or not gold["path"]
        or gold["expected_sha256"] != expected_gold["sha256"]
        or type(gold["mtime_ns"]) is not int
        or gold["mtime_ns"] < 0
        or gold["consistent_snapshot"] is not True
        or not isinstance(gold["mixed_marker_surface_list"], list)
        or len(gold["mixed_marker_surface_list"])
        != expected_gold["mixed_marker_surfaces"]
        or any(
            not isinstance(surface, str) or not surface
            for surface in gold["mixed_marker_surface_list"]
        )
        or len(gold["mixed_marker_surface_list"])
        != len(set(gold["mixed_marker_surface_list"]))
        or gold["mixed_marker_surface_list"]
        != sorted(gold["mixed_marker_surface_list"])
        or gold["unmarked_conflicts"] != []
    ):
        raise ValueError(f"{label} gold scope drift")


def _validate_stat_block(stats: dict, label: str) -> None:
    if not isinstance(stats, dict) or set(stats) != STAT_KEYS:
        raise ValueError(f"current-only statistic schema drift: {label}")
    if any(type(value) is not int or value < 0 for value in stats.values()):
        raise ValueError(f"current-only statistic value drift: {label}")
    if (
        stats["baseline_correct_weight"] > stats["total_weight"]
        or stats["current_correct_weight"] > stats["total_weight"]
        or stats["baseline_correct_cases"] > stats["total_cases"]
        or stats["current_correct_cases"] > stats["total_cases"]
        or stats["baseline_correct_weight"] != stats["current_correct_weight"]
        or stats["baseline_correct_cases"] != stats["current_correct_cases"]
        or stats["regression_weight"] != 0
        or stats["regression_cases"] != 0
        or stats["improvement_weight"] != 0
        or stats["improvement_cases"] != 0
    ):
        raise ValueError(f"current-only comparison is not self-consistent: {label}")


def _validate_full_stat_block(stats: dict, label: str) -> None:
    if not isinstance(stats, dict) or set(stats) != STAT_KEYS:
        raise ValueError(f"full-audit statistic schema drift: {label}")
    if any(type(value) is not int or value < 0 for value in stats.values()):
        raise ValueError(f"full-audit statistic value drift: {label}")
    if (
        stats["total_weight"] <= 0
        or stats["total_cases"] <= 0
        or stats["baseline_correct_weight"] > stats["total_weight"]
        or stats["current_correct_weight"] > stats["total_weight"]
        or stats["baseline_correct_cases"] > stats["total_cases"]
        or stats["current_correct_cases"] > stats["total_cases"]
    ):
        raise ValueError(f"full-audit statistic accounting drift: {label}")


def _validate_absolute_statistics(
    comparison: dict, manifest: dict, profile: str, label: str,
) -> None:
    """Bind every audit mode to the fresh nine-source absolute accounting."""
    contract = manifest["statistics_contract"]
    expected = contract["profiles"].get(profile)
    if expected is None:
        raise ValueError(f"Phase 558 unknown statistics profile: {profile}")
    if comparison.get("comparison") != expected["comparison"]:
        raise ValueError(f"Phase 558 {label} statistics comparison drift")

    sources = comparison.get("sources")
    required_sources = contract["required_sources"]
    if (
        not isinstance(sources, dict)
        or len(sources) != len(required_sources)
        or set(sources) != set(required_sources)
    ):
        raise ValueError(f"Phase 558 {label} nine-source scope drift")
    for source, stats in sources.items():
        if stats["total_weight"] <= 0 or stats["total_cases"] <= 0:
            raise ValueError(f"Phase 558 {label}/{source} zero-source drift")

    combined = comparison.get("combined")
    calculated = {
        key: sum(stats[key] for stats in sources.values())
        for key in STAT_KEYS
    }
    if combined != calculated:
        raise ValueError(f"Phase 558 {label} combined/source sum drift")
    if combined != expected["combined"]:
        raise ValueError(f"Phase 558 {label} absolute combined drift")
    digest = stable_json_sha256(sources)
    if digest != expected["source_statistics_sha256"]:
        raise ValueError(
            f"Phase 558 {label} absolute source statistics drift: "
            f"{digest} != {expected['source_statistics_sha256']}"
        )


def _assert_delta(stats: dict, expected: dict, label: str) -> None:
    if (
        stats["regression_cases"] != expected["regression_cases"]
        or stats["regression_weight"] != expected["regression_cases"]
        or stats["improvement_cases"] != expected["improvement_cases"]
        or stats["improvement_weight"] != expected["improvement_cases"]
        or stats["current_correct_cases"] - stats["baseline_correct_cases"]
        != expected["current_minus_baseline_correct_cases"]
        or stats["current_correct_weight"] - stats["baseline_correct_weight"]
        != expected["current_minus_baseline_correct_cases"]
    ):
        raise ValueError(f"Phase 558 full-audit classified delta drift: {label}")


def _validate_finding_record(
    record: dict, entry: dict, bucket: str,
    expected_old_signature_payload: dict,
    expected_current_signature_payload: dict,
) -> None:
    surface = entry["surface"]
    if record.get("surface") != surface:
        raise ValueError(f"Phase 558 finding surface drift: {bucket}/{surface}")
    if (
        record.get("baseline") != entry["new_decomposition"]
        or record.get("baseline_typed") != entry["new_typed"]
        or record.get("current") != entry["new_decomposition"]
        or record.get("current_typed") != entry["new_typed"]
        or record.get("current_typed") == entry["old_typed"]
    ):
        raise ValueError(f"Phase 558 finding signature drift: {bucket}/{surface}")
    expected_options = record.get("expected_options")
    if (
        not isinstance(expected_options, list)
        or not expected_options
        or entry["new_decomposition"] in expected_options
    ):
        raise ValueError(f"Phase 558 old expectation drift: {bucket}/{surface}")
    sources = record.get("sources")
    if not isinstance(sources, list) or not set(entry["required_reference_sources"]).issubset(sources):
        raise ValueError(f"Phase 558 finding source drift: {bucket}/{surface}")
    if bucket == "current_unreferenced_wrong_surfaces":
        expected_signatures = record.get("expected_signatures")
        if (
            not isinstance(expected_signatures, list)
            or expected_old_signature_payload not in expected_signatures
            or expected_current_signature_payload in expected_signatures
            or record.get("current_signature")
            != expected_current_signature_payload
        ):
            raise ValueError(f"Phase 558 finding payload drift: {bucket}/{surface}")


def _validate_full_finding_record(
    record: dict, entry: dict, bucket: str,
    expected_old_signature_payload: dict,
    expected_current_signature_payload: dict,
) -> None:
    surface = entry["surface"]
    if not isinstance(record, dict) or record.get("surface") != surface:
        raise ValueError(f"Phase 558 full finding surface drift: {bucket}/{surface}")
    if (
        record.get("baseline") != entry["old_decomposition"]
        or record.get("baseline_typed") != entry["old_typed"]
        or record.get("current") != entry["new_decomposition"]
        or record.get("current_typed") != entry["new_typed"]
        or record.get("current_typed") == entry["old_typed"]
    ):
        raise ValueError(f"Phase 558 full finding signature drift: {bucket}/{surface}")
    expected_options = record.get("expected_options")
    if (
        not isinstance(expected_options, list)
        or not expected_options
        or entry["new_decomposition"] in expected_options
    ):
        raise ValueError(f"Phase 558 full old expectation drift: {bucket}/{surface}")
    sources = record.get("sources")
    if (
        not isinstance(sources, list)
        or not set(entry["required_reference_sources"]).issubset(sources)
    ):
        raise ValueError(f"Phase 558 full finding source drift: {bucket}/{surface}")
    if bucket == "current_unreferenced_wrong_surfaces":
        expected_signatures = record.get("expected_signatures")
        if (
            not isinstance(expected_signatures, list)
            or expected_old_signature_payload not in expected_signatures
            or expected_current_signature_payload in expected_signatures
            or record.get("current_signature")
            != expected_current_signature_payload
        ):
            raise ValueError(f"Phase 558 full finding payload drift: {bucket}/{surface}")


def _validate_signature_change(
    record: dict, entry: dict,
    expected_old_signature_payload: dict,
    expected_current_signature_payload: dict,
) -> None:
    expected_keys = {
        "surface", "baseline", "baseline_typed", "baseline_signature",
        "current", "current_typed", "current_signature",
    }
    surface = entry["surface"]
    if (
        not isinstance(record, dict)
        or set(record) != expected_keys
        or record.get("surface") != surface
        or record.get("baseline") != entry["old_decomposition"]
        or record.get("baseline_typed") != entry["old_typed"]
        or record.get("baseline_signature") != expected_old_signature_payload
        or record.get("current") != entry["new_decomposition"]
        or record.get("current_typed") != entry["new_typed"]
        or record.get("current_signature") != expected_current_signature_payload
        or record.get("baseline_signature") == record.get("current_signature")
    ):
        raise ValueError(f"Phase 558 full signature change drift: {surface!r}")


def _expected_bucket_surfaces(manifest: dict) -> dict[str, set[str]]:
    expected = {key: set() for key in FINDING_KEYS}
    for entry in manifest["entries"]:
        for bucket in entry["expected_current_wrong_buckets"]:
            expected[bucket].add(entry["surface"])
    return expected


def _validate_comparison(
    comparison: dict, manifest: dict, language: str, statistics_profile: str,
) -> dict:
    contract = manifest["audit_contract"]
    if (
        not isinstance(comparison, dict)
        or set(comparison) != set(contract["required_comparison_keys"])
        or comparison.get("comparison") != "current_only"
        or comparison.get("gate") is not False
    ):
        raise ValueError(f"Phase 558 {language} current-only comparison drift")
    sources = comparison["sources"]
    if not isinstance(sources, dict) or not sources:
        raise ValueError(f"Phase 558 {language} source statistics missing")
    for source, stats in sources.items():
        _validate_stat_block(stats, f"{language}/{source}")
    _validate_stat_block(comparison["combined"], f"{language}/combined")
    _validate_absolute_statistics(
        comparison, manifest, statistics_profile,
        f"{language}/{statistics_profile}",
    )

    expected_by_bucket = _expected_bucket_surfaces(manifest)
    entries = _entry_index(manifest)
    pre_signatures, _pre_digest = runtime_gate.expected_signatures("pre-regen")
    post_signatures, _post_digest = runtime_gate.expected_signatures("post-regen")
    observed_union: set[str] = set()
    for bucket in FINDING_KEYS:
        records = comparison[bucket]
        if not isinstance(records, list):
            raise ValueError(f"Phase 558 {language}/{bucket} is not a list")
        observed = [record.get("surface") for record in records if isinstance(record, dict)]
        if len(observed) != len(records) or len(observed) != len(set(observed)):
            raise ValueError(f"Phase 558 {language}/{bucket} row identity drift")
        if set(observed) != expected_by_bucket[bucket]:
            raise ValueError(
                f"Phase 558 {language}/{bucket} is outside reviewed closure: "
                f"{sorted(observed)!r} != {sorted(expected_by_bucket[bucket])!r}"
            )
        observed_union.update(observed)
        for record in records:
            entry = entries[record["surface"]]
            _validate_finding_record(
                record, entry, bucket,
                _signature_payload(pre_signatures[entry["surface"]]),
                _signature_payload(post_signatures[entry["surface"]]),
            )
    if comparison["weighted_worsening_sources"] != []:
        raise ValueError(f"Phase 558 {language} has weighted worsening")
    replacements = {
        entry["surface"] for entry in manifest["entries"]
        if entry["disposition"] == "reviewed_expectation_replacement"
    }
    if observed_union != replacements:
        raise ValueError(
            f"Phase 558 {language} unadjudicated/current finding closure drift"
        )
    return {
        "language": language,
        "allowed_reviewed_replacements": len(replacements),
        "unadjudicated_findings": 0,
        "gate": True,
    }


def _validate_full_comparison(
    comparison: dict, manifest: dict, language: str, label: str,
) -> dict:
    contract = manifest["full_audit_contract"]
    if (
        not isinstance(comparison, dict)
        or set(comparison) != FULL_COMPARISON_KEYS
        or comparison.get("comparison") != label
        or comparison.get("gate") is not False
    ):
        raise ValueError(f"Phase 558 {language}/{label} full comparison drift")
    sources = comparison["sources"]
    if not isinstance(sources, dict) or not sources:
        raise ValueError(f"Phase 558 {language}/{label} source statistics missing")
    for source, stats in sources.items():
        _validate_full_stat_block(stats, f"{language}/{label}/{source}")
    combined = comparison["combined"]
    _validate_full_stat_block(combined, f"{language}/{label}/combined")
    _validate_absolute_statistics(
        comparison, manifest, f"full-{label.replace('_', '-')}",
        f"{language}/{label}",
    )
    _assert_delta(
        combined, contract["expected_combined_delta"],
        f"{language}/{label}/combined",
    )
    expected_source_deltas = contract["expected_source_deltas"]
    if not set(expected_source_deltas).issubset(sources):
        raise ValueError(f"Phase 558 {language}/{label} classified source missing")
    for source, stats in sources.items():
        expected = expected_source_deltas.get(source, {
            "regression_cases": 0,
            "improvement_cases": 0,
            "current_minus_baseline_correct_cases": 0,
        })
        _assert_delta(stats, expected, f"{language}/{label}/{source}")
    if comparison["weighted_worsening_sources"] != contract[
        "expected_weighted_worsening_sources"
    ]:
        raise ValueError(f"Phase 558 {language}/{label} worsening-source drift")

    entries = _entry_index(manifest)
    replacements = {
        surface for surface, entry in entries.items()
        if entry["disposition"] == "reviewed_expectation_replacement"
    }
    if replacements != set(contract["required_signature_change_surfaces"]):
        raise ValueError(
            f"Phase 558 {language}/{label} full/runtime role separation drift"
        )
    expected_by_bucket = {key: set() for key in FINDING_KEYS}
    for bucket in (
        "regression_cases",
        "changed_to_unreferenced_wrong_surfaces",
        "current_unreferenced_wrong_surfaces",
    ):
        expected_by_bucket[bucket] = set(replacements)
    pre_signatures, _pre_digest = runtime_gate.expected_signatures("pre-regen")
    post_signatures, _post_digest = runtime_gate.expected_signatures("post-regen")
    observed_findings: set[str] = set()
    for bucket in FINDING_KEYS:
        records = comparison[bucket]
        if not isinstance(records, list):
            raise ValueError(f"Phase 558 {language}/{label}/{bucket} is not a list")
        surfaces = [
            record.get("surface") for record in records
            if isinstance(record, dict)
        ]
        if (
            len(surfaces) != len(records)
            or len(surfaces) != len(set(surfaces))
            or set(surfaces) != expected_by_bucket[bucket]
        ):
            raise ValueError(
                f"Phase 558 {language}/{label}/{bucket} finding closure drift"
            )
        observed_findings.update(surfaces)
        for record in records:
            entry = entries[record["surface"]]
            _validate_full_finding_record(
                record, entry, bucket,
                _signature_payload(pre_signatures[entry["surface"]]),
                _signature_payload(post_signatures[entry["surface"]]),
            )
    if observed_findings != replacements:
        raise ValueError(f"Phase 558 {language}/{label} finding union drift")

    changes = comparison["signature_changes"]
    expected_surfaces = contract["required_signature_change_surfaces"]
    if not isinstance(changes, list):
        raise ValueError(f"Phase 558 {language}/{label} signature changes missing")
    surfaces = [record.get("surface") for record in changes if isinstance(record, dict)]
    if (
        len(surfaces) != len(changes)
        or len(surfaces) != len(set(surfaces))
        or surfaces != expected_surfaces
    ):
        raise ValueError(f"Phase 558 {language}/{label} signature-change closure drift")
    changes_by_surface = {record["surface"]: record for record in changes}
    for surface in expected_surfaces:
        _validate_signature_change(
            changes_by_surface[surface], entries[surface],
            _signature_payload(pre_signatures[surface]),
            _signature_payload(post_signatures[surface]),
        )
    return {
        "comparison": label,
        "signature_changes": [
            changes_by_surface[surface] for surface in expected_surfaces
        ],
        "improvements": 0,
        "reviewed_replacements": 2,
        "unadjudicated_signature_changes": 0,
        "gate": True,
    }


def validate_runtime_report(report: dict, manifest: dict | None = None) -> dict:
    if manifest is None:
        manifest = load_manifest()
    contract = manifest["audit_contract"]
    if not isinstance(report, dict):
        raise ValueError("Phase 558 runtime report is not an object")
    required = {
        "phase", "mode", "languages", "surfaces", "trilingual_mismatches",
        "signature_manifest_sha256", "gate", "candidate_payload_sha256",
        "app_input_fingerprints", "overlay_review", "all_inputs_stable",
        "scope_guard_surfaces", "scope_guard_trilingual_mismatches",
        "scope_guard_signature_manifest_sha256", "scope_guard_gate",
        "adjudicated_source_rows", "productive_rules",
        "productive_endings", "productive_cases",
        "productive_payload_variants",
        "exact_payload_variants", "expanded_payload_variants",
        "payload_variant_manifest_sha256",
        "payload_variant_trilingual_mismatches", "payload_variant_gate",
        "deployed_snapshot_revalidated",
    }
    if not required.issubset(report):
        raise ValueError("Phase 558 runtime report schema drift")
    if (
        report["phase"] != 558
        or report["mode"] != contract["candidate_runtime_mode"]
        or report["languages"] != contract["required_languages"]
        or report["surfaces"] != manifest["expected_counts"]["entries"]
        or report["trilingual_mismatches"] != 0
        or report["signature_manifest_sha256"]
        != contract["candidate_signature_manifest_sha256"]
        or report["scope_guard_surfaces"]
        != contract["candidate_scope_guard_surfaces"]
        or report["scope_guard_trilingual_mismatches"] != 0
        or report["scope_guard_signature_manifest_sha256"]
        != contract["candidate_scope_guard_signature_manifest_sha256"]
        or report["scope_guard_gate"] is not True
        or report["adjudicated_source_rows"]
        != runtime_gate.PAYLOAD_VARIANT_COUNTS["adjudicated_source_rows"]
        or report["productive_rules"]
        != runtime_gate.PAYLOAD_VARIANT_COUNTS["productive_rules"]
        or report["productive_endings"]
        != runtime_gate.PAYLOAD_VARIANT_COUNTS["productive_endings"]
        or report["productive_cases"]
        != runtime_gate.PAYLOAD_VARIANT_COUNTS["productive_cases"]
        or report["productive_payload_variants"]
        != runtime_gate.PAYLOAD_VARIANT_COUNTS["productive_payload_variants"]
        or report["exact_payload_variants"]
        != runtime_gate.PAYLOAD_VARIANT_COUNTS["exact_payload_variants"]
        or report["expanded_payload_variants"]
        != runtime_gate.PAYLOAD_VARIANT_COUNTS["expanded_payload_variants"]
        or report["payload_variant_manifest_sha256"]
        != runtime_gate.PAYLOAD_VARIANT_MANIFEST_SHA256
        or report["payload_variant_trilingual_mismatches"] != 0
        or report["payload_variant_gate"] is not True
        or report["deployed_snapshot_revalidated"] is not True
        or report["gate"] is not True
        or report["all_inputs_stable"] is not True
        or set(report["candidate_payload_sha256"])
        != set(contract["required_languages"])
        or set(report["app_input_fingerprints"])
        != set(contract["required_languages"])
    ):
        raise ValueError("Phase 558 runtime report failed closed")
    review = report["overlay_review"]
    review_pin = manifest["parent_authority"]["phase558_overlay_review"]
    if (
        not isinstance(review, dict)
        or review.get("review_sha256") != review_pin["sha256"]
        or review.get("entries_sha256") != review_pin["entries_sha256"]
    ):
        raise ValueError("Phase 558 runtime overlay-review identity drift")
    return {
        "surfaces": report["surfaces"],
        "trilingual_mismatches": 0,
        "new_signature_only": True,
        "all_inputs_stable": True,
        "gate": True,
    }


def require_same_runtime_app_snapshot(
    audit_fingerprints: dict, runtime_report: dict, label: str,
) -> None:
    """Prevent a raw report and runtime gate from certifying two snapshots."""
    runtime_fingerprints = runtime_report.get("app_input_fingerprints")
    if runtime_fingerprints != audit_fingerprints:
        raise ValueError(
            f"Phase 558 {label} runtime/audit app snapshot drift"
        )


def validate_audit_report(
    audit_report: dict, runtime_report: dict, *, manifest: dict | None = None,
) -> dict:
    if manifest is None:
        manifest = load_manifest()
    if not isinstance(audit_report, dict) or set(audit_report) != CURRENT_ONLY_TOP_KEYS:
        raise ValueError("Phase 558 requires a complete current-only audit report")
    if audit_report.get("complete") is not True:
        raise ValueError("Phase 558 current-only audit is incomplete")
    projection = audit_report.get("reference_projection")
    resolved = audit_report.get("resolved_reference")
    if (
        not isinstance(projection, dict)
        or not isinstance(resolved, dict)
        or not all(
            isinstance(audit_report.get(key), int) and audit_report[key] > 0
            for key in ("case_count", "raw_case_count", "surface_count")
        )
        or projection.get("case_count") != audit_report["raw_case_count"]
        or projection.get("surface_count") != audit_report["surface_count"]
        or resolved.get("case_count") != audit_report["case_count"]
        or resolved.get("surface_count") != audit_report["surface_count"]
    ):
        raise ValueError("Phase 558 current-only reference accounting drift")
    stability = audit_report.get("inputs_stable")
    required_stability = manifest["audit_contract"]["required_input_stability"]
    if (
        not isinstance(stability, dict)
        or set(stability) != set(required_stability)
        or any(stability[key] is not True for key in required_stability)
    ):
        raise ValueError("Phase 558 current-only audit inputs were not stable")
    # The parent gate is expected to be false only because two old expectations
    # remain deliberately immutable in the parent authority.
    if audit_report.get("gate") is not False:
        raise ValueError("Phase 558 parent current-only result was not the reviewed two-row exception")

    parent = manifest["parent_authority"]
    reviewed_reference = audit_report.get("reviewed_reference", {})
    checkpoint = audit_report.get("checkpoint_context", {})
    scope = audit_report.get("scope", {})
    if (
        reviewed_reference.get("scope_manifest_sha256")
        != parent["scope_manifest"]["sha256"]
        or checkpoint.get("scope_manifest_sha256")
        != parent["scope_manifest"]["sha256"]
        or checkpoint.get("head_oid") != parent["app_head_oid"]
        or checkpoint.get("gold_sha256") != phase532.CANDIDATE_LEARNER_SHA256
        or scope.get("gold", {}).get("sha256") != phase532.CANDIDATE_LEARNER_SHA256
        or scope.get("gold", {}).get("fake_coarse_reference", {}).get("sha256")
        != parent["fake_coarse_reference"]["sha256"]
    ):
        raise ValueError("Phase 558 current-only audit parent identity drift")

    expected_languages = manifest["audit_contract"]["required_languages"]
    rows = audit_report.get("languages")
    if not isinstance(rows, list) or [row.get("language") for row in rows] != expected_languages:
        raise ValueError("Phase 558 current-only language scope/order drift")
    language_reports = []
    for row in rows:
        language = row["language"]
        if set(row) != CURRENT_ONLY_LANGUAGE_KEYS:
            raise ValueError(f"Phase 558 {language} current-only row schema drift")
        if (
            not isinstance(row.get("input_fingerprint"), dict)
            or not row["input_fingerprint"]
            or row.get("input_stable") is not True
            or row.get("gate") is not False
        ):
            raise ValueError(f"Phase 558 {language} current-only row failed closed")
        language_reports.append(
            _validate_comparison(
                row["comparison"], manifest, language, "parent-current",
            )
        )
    runtime_summary = validate_runtime_report(runtime_report, manifest)
    require_same_runtime_app_snapshot(
        {row["language"]: row["input_fingerprint"] for row in rows},
        runtime_report, "parent-current",
    )
    return {
        "phase": 558,
        "parent_phase": 532,
        "audit_kind": "current_only_plus_closed_sidecar",
        "languages": expected_languages,
        "reference_alignment_improvements": 3,
        "reviewed_expectation_replacements": 2,
        "allowed_current_wrong_surfaces": ["Izraelio", "tia-tia"],
        "unadjudicated_findings": 0,
        "trilingual_mismatches": runtime_summary["trilingual_mismatches"],
        "new_signature_only": runtime_summary["new_signature_only"],
        "all_inputs_stable": True,
        "language_reports": language_reports,
        "gate": True,
    }


def validate_full_audit_report(
    audit_report: dict, runtime_report: dict, *, manifest: dict | None = None,
) -> dict:
    if manifest is None:
        manifest = load_manifest()
    contract = manifest["full_audit_contract"]
    parent = manifest["parent_authority"]
    if not isinstance(audit_report, dict) or set(audit_report) != FULL_TOP_KEYS:
        raise ValueError("Phase 558 requires a complete full old-to-new audit")
    if audit_report.get("complete") is not True or audit_report.get("gate") is not False:
        raise ValueError("Phase 558 full audit is incomplete or not the reviewed exception")
    expected_languages = contract["required_languages"]
    if audit_report.get("requested_languages") != expected_languages:
        raise ValueError("Phase 558 full requested-language scope drift")
    baseline = contract["baseline_revision"]
    worktree_start = audit_report.get("worktree_head_oid_at_start")
    worktree_end = audit_report.get("worktree_head_oid_at_end")
    if (
        audit_report.get("head_oid") != baseline
        or not is_git_oid(worktree_start)
        or worktree_start != worktree_end
        or audit_report.get("head_stable_at_end") is not True
    ):
        raise ValueError("Phase 558 full baseline/worktree identity drift")
    stability_keys = (
        "corpus_stable_at_end",
        "place_manifest_stable_at_end",
        "audit_code_stable_at_end",
        "review_manifests_stable_at_end",
        "all_app_inputs_stable_at_end",
        "gold_source_matches_snapshot_at_end",
        "gold_snapshot_isolated_from_external_changes",
        "gold_snapshot_source_stable_during_audit",
    )
    if any(audit_report.get(key) is not True for key in stability_keys):
        raise ValueError("Phase 558 full audit inputs were not stable")
    if (
        audit_report.get("final_gold_sha256")
        != phase532.CANDIDATE_LEARNER_SHA256
        or audit_report.get("app_fingerprints_at_start")
        != audit_report.get("app_fingerprints_at_end")
        or set(audit_report.get("app_fingerprints_at_start", {}))
        != set(expected_languages)
    ):
        raise ValueError("Phase 558 full app/gold fingerprint drift")

    pin = contract["reference_projection"]
    projection = audit_report.get("reference_projection", {})
    resolved = audit_report.get("resolved_reference", {})
    checkpoint = audit_report.get("checkpoint_context", {})
    reviewed = audit_report.get("reviewed_reference", {})
    scope = audit_report.get("scope", {})
    if (
        audit_report.get("raw_case_count") != pin["raw_cases"]
        or audit_report.get("surface_count") != pin["surfaces"]
        or audit_report.get("case_count") != pin["resolved_cases"]
        or projection.get("case_count") != pin["raw_cases"]
        or projection.get("surface_count") != pin["surfaces"]
        or projection.get("reference_sha256") != pin["raw_reference_sha256"]
        or projection.get("corpus", {}).get("content_sha256")
        != pin["corpus_content_sha256"]
        or projection.get("corpus_repository", {}).get("head_oid")
        != pin["corpus_head_oid"]
        or projection.get("corpus_repository", {}).get("status_sha256")
        != pin["corpus_status_sha256"]
        or resolved.get("case_count") != pin["resolved_cases"]
        or resolved.get("surface_count") != pin["surfaces"]
        or resolved.get("reference_sha256")
        != pin["resolved_reference_sha256"]
        or reviewed.get("scope_manifest_sha256")
        != contract["scope_manifest_sha256"]
        or reviewed.get("conflict_manifest_sha256")
        != contract["conflict_manifest_sha256"]
        or checkpoint.get("head_oid") != baseline
        or checkpoint.get("raw_reference_sha256")
        != pin["raw_reference_sha256"]
        or checkpoint.get("reference_sha256")
        != pin["resolved_reference_sha256"]
        or checkpoint.get("surface_sha256") != pin["surface_sha256"]
        or checkpoint.get("corpus_sha256") != pin["corpus_content_sha256"]
        or checkpoint.get("corpus_head_oid") != pin["corpus_head_oid"]
        or checkpoint.get("corpus_status_sha256") != pin["corpus_status_sha256"]
        or checkpoint.get("scope_manifest_sha256")
        != contract["scope_manifest_sha256"]
        or checkpoint.get("gold_sha256") != phase532.CANDIDATE_LEARNER_SHA256
        or scope.get("gold", {}).get("sha256")
        != phase532.CANDIDATE_LEARNER_SHA256
        or scope.get("gold", {}).get("fake_coarse_reference", {}).get("sha256")
        != parent["fake_coarse_reference"]["sha256"]
        or audit_report.get("corpus_repository_at_end")
        != projection.get("corpus_repository")
    ):
        raise ValueError("Phase 558 full reference identity drift")

    rows = audit_report.get("languages")
    if not isinstance(rows, list) or [row.get("language") for row in rows] != expected_languages:
        raise ValueError("Phase 558 full language scope/order drift")
    language_reports = []
    canonical_changes = None
    for row in rows:
        language = row["language"]
        if set(row) != FULL_LANGUAGE_KEYS:
            raise ValueError(f"Phase 558 {language} full language schema drift")
        if (
            row.get("current_input_stable_during_language_audit") is not True
            or row.get("gate") is not False
            or row.get("data_isolated_definition")
            != "HEAD Ruby JSON + current runtime -> working-tree Ruby JSON + current runtime"
            or row.get("comprehensive_definition")
            != "HEAD Ruby JSON + HEAD runtime -> working-tree Ruby JSON + current runtime"
            or row.get("current_input_fingerprint")
            != audit_report["app_fingerprints_at_start"][language]
            or not isinstance(row.get("head_overlay_dependency_fingerprint"), dict)
            or not row["head_overlay_dependency_fingerprint"]
            or not isinstance(row.get("elapsed_seconds"), (int, float))
            or row["elapsed_seconds"] < 0
        ):
            raise ValueError(f"Phase 558 {language} full language input drift")
        comparisons = []
        for label in contract["required_comparisons"]:
            comparisons.append(
                _validate_full_comparison(row[label], manifest, language, label)
            )
        if comparisons[0]["signature_changes"] != comparisons[1]["signature_changes"]:
            raise ValueError(f"Phase 558 {language} full comparison delta disagreement")
        changes = comparisons[0]["signature_changes"]
        if canonical_changes is None:
            canonical_changes = changes
        elif changes != canonical_changes:
            raise ValueError("Phase 558 full JA/ZH/KO signature delta mismatch")
        language_reports.append({
            "language": language,
            "signature_changes": len(changes),
            "unadjudicated_signature_changes": 0,
            "gate": True,
        })
    runtime_summary = validate_runtime_report(runtime_report, manifest)
    require_same_runtime_app_snapshot(
        audit_report["app_fingerprints_at_end"], runtime_report,
        "full-old-to-new",
    )
    return {
        "phase": 558,
        "parent_phase": 532,
        "audit_kind": "full_old_to_new_plus_closed_sidecar",
        "baseline_revision": baseline,
        "worktree_head_stable": True,
        "languages": expected_languages,
        "signature_changes": len(
            contract["required_signature_change_surfaces"]
        ),
        "reference_alignment_improvements": 0,
        "reviewed_expectation_replacements": 2,
        "unadjudicated_signature_changes": 0,
        "trilingual_signature_delta_mismatches": 0,
        "trilingual_runtime_mismatches": runtime_summary["trilingual_mismatches"],
        "new_signature_only": runtime_summary["new_signature_only"],
        "all_inputs_stable": True,
        "language_reports": language_reports,
        "gate": True,
    }


def validate_current_e373_report(
    audit_report: dict, runtime_report: dict, *, manifest: dict | None = None,
) -> dict:
    if manifest is None:
        manifest = load_manifest()
    expected_projection = _load_current_e373_scope(manifest)
    contract = manifest["current_e373_contract"]
    if not isinstance(audit_report, dict) or set(audit_report) != CURRENT_ONLY_TOP_KEYS:
        raise ValueError("Phase 558 requires a complete e373 current-only audit")
    if audit_report.get("complete") is not True or audit_report.get("gate") is not False:
        raise ValueError("Phase 558 e373 current-only audit is not the reviewed exception")
    stability = audit_report.get("inputs_stable")
    required_stability = manifest["audit_contract"]["required_input_stability"]
    if (
        not isinstance(stability, dict)
        or set(stability) != set(required_stability)
        or any(stability[key] is not True for key in required_stability)
    ):
        raise ValueError("Phase 558 e373 current-only inputs were not stable")
    pin = contract["reference_projection"]
    corpus_pin = contract["corpus"]
    projection = audit_report.get("reference_projection")
    resolved = audit_report.get("resolved_reference", {})
    reviewed = audit_report.get("reviewed_reference", {})
    checkpoint = audit_report.get("checkpoint_context", {})
    scope = audit_report.get("scope", {})
    _validate_scope_projection(scope, expected_projection, "Phase 558 e373")
    if (
        projection != expected_projection
        or audit_report.get("raw_case_count") != pin["raw_cases"]
        or audit_report.get("surface_count") != pin["surfaces"]
        or audit_report.get("case_count") != pin["resolved_cases"]
        or resolved != {
            "case_count": pin["resolved_cases"],
            "surface_count": pin["surfaces"],
            "reference_sha256": pin["resolved_reference_sha256"],
        }
        or reviewed.get("scope_manifest_sha256")
        != contract["scope_manifest"]["sha256"]
        or reviewed.get("conflict_manifest_sha256")
        != contract["conflict_manifest_sha256"]
        or checkpoint.get("scope_manifest_sha256")
        != contract["scope_manifest"]["sha256"]
        or checkpoint.get("conflict_manifest_sha256")
        != contract["conflict_manifest_sha256"]
        or checkpoint.get("raw_reference_sha256")
        != pin["raw_reference_sha256"]
        or checkpoint.get("reference_sha256")
        != pin["resolved_reference_sha256"]
        or checkpoint.get("surface_sha256") != pin["surface_sha256"]
        or checkpoint.get("corpus_sha256") != corpus_pin["content_sha256"]
        or checkpoint.get("corpus_head_oid") != corpus_pin["head_oid"]
        or checkpoint.get("corpus_status_sha256") != corpus_pin["status_sha256"]
        or not is_git_oid(checkpoint.get("head_oid"))
        or checkpoint.get("gold_sha256") != phase532.CANDIDATE_LEARNER_SHA256
        or scope.get("corpus", {}).get("content_sha256")
        != corpus_pin["content_sha256"]
        or scope.get("corpus_repository", {}).get("head_oid")
        != corpus_pin["head_oid"]
        or scope.get("corpus_repository", {}).get("status_entries") != 0
        or scope.get("corpus_repository", {}).get("status_sha256")
        != corpus_pin["status_sha256"]
        or scope.get("gold", {}).get("sha256")
        != phase532.CANDIDATE_LEARNER_SHA256
        or scope.get("gold", {}).get("fake_coarse_reference", {}).get("sha256")
        != manifest["parent_authority"]["fake_coarse_reference"]["sha256"]
    ):
        raise ValueError("Phase 558 e373 current-only identity drift")

    expected_languages = manifest["audit_contract"]["required_languages"]
    rows = audit_report.get("languages")
    if not isinstance(rows, list) or [row.get("language") for row in rows] != expected_languages:
        raise ValueError("Phase 558 e373 current-only language scope drift")
    language_reports = []
    for row in rows:
        language = row["language"]
        if set(row) != CURRENT_ONLY_LANGUAGE_KEYS:
            raise ValueError(f"Phase 558 {language} e373 row schema drift")
        if (
            not isinstance(row.get("input_fingerprint"), dict)
            or not row["input_fingerprint"]
            or row.get("input_stable") is not True
            or row.get("gate") is not False
        ):
            raise ValueError(f"Phase 558 {language} e373 row input drift")
        comparison = row["comparison"]
        language_reports.append(
            _validate_comparison(
                comparison, manifest, language, "current-e373",
            )
        )
        html_stats = comparison["sources"].get(contract["required_html_source"])
        if (
            not isinstance(html_stats, dict)
            or html_stats.get("total_weight") != corpus_pin["html_weight"]
            or not isinstance(html_stats.get("total_cases"), int)
            or html_stats["total_cases"] <= 0
            or html_stats.get("baseline_correct_weight") != corpus_pin["html_weight"]
            or html_stats.get("current_correct_weight") != corpus_pin["html_weight"]
            or html_stats.get("baseline_correct_cases")
            != html_stats["total_cases"]
            or html_stats.get("current_correct_cases")
            != html_stats["total_cases"]
            or html_stats.get("regression_weight") != 0
            or html_stats.get("improvement_weight") != 0
        ):
            raise ValueError(f"Phase 558 {language} e373 HTML coverage drift")
    runtime_summary = validate_runtime_report(runtime_report, manifest)
    require_same_runtime_app_snapshot(
        {row["language"]: row["input_fingerprint"] for row in rows},
        runtime_report, "current-e373",
    )
    return {
        "phase": 558,
        "audit_kind": "current_e373_plus_closed_sidecar",
        "corpus_head_oid": corpus_pin["head_oid"],
        "corpus_content_sha256": corpus_pin["content_sha256"],
        "languages": expected_languages,
        "html_weight": corpus_pin["html_weight"],
        "html_mismatches": 0,
        "allowed_current_wrong_surfaces": contract[
            "required_current_wrong_surfaces"
        ],
        "unadjudicated_findings": 0,
        "trilingual_mismatches": runtime_summary["trilingual_mismatches"],
        "new_signature_only": runtime_summary["new_signature_only"],
        "all_inputs_stable": True,
        "language_reports": language_reports,
        "gate": True,
    }


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--audit-kind", choices=AUDIT_KINDS, default="parent-current",
        help=(
            "Keep parent current-only, full old-to-new, and e373 current-only "
            "authorities explicitly separate."
        ),
    )
    parser.add_argument(
        "--audit",
        type=Path,
        help="Audit JSON; the default depends on --audit-kind.",
    )
    parser.add_argument("--deployed", action="store_true", required=True)
    parser.add_argument("--batch-size", type=int, default=5)
    args = parser.parse_args(argv)
    manifest = load_manifest()
    default_audits = {
        "parent-current": HERE / "out" / "_audit_no_worsening_current_only.json",
        "full-old-to-new": HERE / "out" / "_audit_no_worsening.json",
        "current-e373": HERE / "out" / "_audit_no_worsening_current_e373.json",
    }
    audit_path = args.audit or default_audits[args.audit_kind]
    audit_report = json.loads(audit_path.read_text(encoding="utf-8"))
    runtime_report = runtime_gate.validate_deployed_payloads(
        "post-regen", batch_size=args.batch_size,
    )
    validators = {
        "parent-current": validate_audit_report,
        "full-old-to-new": validate_full_audit_report,
        "current-e373": validate_current_e373_report,
    }
    report = validators[args.audit_kind](
        audit_report, runtime_report, manifest=manifest,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
