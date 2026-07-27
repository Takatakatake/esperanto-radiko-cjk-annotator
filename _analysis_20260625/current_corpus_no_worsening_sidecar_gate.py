# -*- coding: utf-8 -*-
"""Fail-closed 7c04-reference / d1642c2-current no-worsening gate.

The raw auditor still evaluates the immutable 7c04 reference projection.  The
active d1642c2 corpus is checked independently and may differ only by the
reviewed ``iniciatoro`` correction.  This keeps the historical Phase 558/e373
evidence byte-immutable while preventing a moving corpus from being silently
substituted for the reference authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import no_worsening_audit as audit
import phase532_ruby_policy as phase532
import phase558_no_worsening_sidecar_gate as phase558_gate
import phase558_ruby_overlay_runtime_gate as phase558_runtime


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MANIFEST_PATH = HERE / "_current_corpus_no_worsening_sidecar_d1642c2.json"
SCOPE_PATH = HERE / "_current_corpus_scope_d1642c2.json"
EXPECTED_MANIFEST_SHA256 = (
    "4D5E8FEA01D0890B014EF9E2A7C1EE281EC4C82DBB6D66752745C3CD819A075E"
)
EXPECTED_SCOPE_SHA256 = (
    "F7257CF4EB3819183912BEAC14F728E05A7213C8258EE745476D0B73A1FE2FBE"
)
EXPECTED_SCOPE_PROJECTION_SHA256 = (
    "2F3ABE5657E0EB54CA45556D0D809EEF43B35CBEB4B1B032B5CEB74D24E415C4"
)
EXPECTED_WEIGHT_ROWS_SHA256 = (
    "BE7963E5B99AA28BC9FCBEFC2EBBF695226E6543D4B56EF25BFAD810E8484E04"
)
EXPECTED_ACTIVE_ROWS_SHA256 = (
    "A15E8735FCEBE2DAA5D5619FFFFEFC8BB9F04FB1D6778865DE737FE8A325016C"
)
EXPECTED_LANGUAGES = ("JA", "ZH", "KO")
EXPECTED_FINDINGS = ("Izraelio", "Temis", "iniciatoro", "tia-tia")
EXPECTED_RETAINED_AUTHORITIES = ("Izraelio", "tia-tia")
EXPECTED_ACTIVE_IMPROVEMENTS = ("iniciatoro",)
EXPECTED_CONTEXTUAL_ADMISSIONS = ("Temis",)
EXPECTED_PHASE600_REPAIRS = (
    "glu-glu-glu",
    "nor",
    "nor-adrenalino",
    "nor-epinefrino",
)
POST_PHASE600_MEASUREMENT_KEYS = {
    "status",
    "required_pins",
    "trilingual_signature_sha256",
    "raw_source_statistics_sha256",
    "raw_combined",
    "raw_html_corpus",
}
POST_PHASE600_REQUIRED_PINS = (
    "trilingual_signature_sha256",
    "raw_source_statistics_sha256",
    "raw_combined",
    "raw_html_corpus",
)
STAT_KEYS = {
    "total_weight",
    "total_cases",
    "baseline_correct_weight",
    "baseline_correct_cases",
    "current_correct_weight",
    "current_correct_cases",
    "regression_weight",
    "regression_cases",
    "improvement_weight",
    "improvement_cases",
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
COMPARISON_KEYS = {
    "comparison",
    "sources",
    "combined",
    *FINDING_KEYS,
    "weighted_worsening_sources",
    "gate",
}
TOP_KEYS = {
    "scope",
    "case_count",
    "raw_case_count",
    "surface_count",
    "languages",
    "reference_projection",
    "resolved_reference",
    "reviewed_reference",
    "checkpoint_context",
    "inputs_stable",
    "successor_trilingual_boundaries",
    "complete",
    "gate",
}
LANGUAGE_KEYS = {
    "language",
    "comparison",
    "input_fingerprint",
    "input_stable",
    "gate",
}
EXPECTED_FINDING_RECORDS = {
    "Izraelio": {
        "expected_options": ["Izraeli/o"],
        "expected_signatures": [{
            "reconstruction": "Izraelio",
            "spans": [
                {"text": "Izraeli", "ruby": True},
                {"text": "o", "ruby": False},
            ],
        }],
        "sources": ["gold_unmarked"],
        "current": "Izrael/io",
        "current_typed": "R:Izrael|L:io",
        "current_signature": {
            "reconstruction": "Izraelio",
            "spans": [
                {"text": "Izrael", "ruby": True},
                {"text": "io", "ruby": False},
            ],
        },
    },
    "Temis": {
        "expected_options": ["Tem/is", "Temis"],
        "expected_signatures": [
            {
                "reconstruction": "Temis",
                "spans": [
                    {"text": "Tem", "ruby": True},
                    {"text": "is", "ruby": True},
                ],
            },
            {
                "reconstruction": "Temis",
                "spans": [
                    {"text": "Temis", "ruby": True},
                ],
            },
        ],
        "sources": ["gold_unmarked", "html_corpus"],
        "current": "Temis",
        "current_typed": "L:Temis",
        "current_signature": {
            "reconstruction": "Temis",
            "spans": [
                {"text": "Temis", "ruby": False},
            ],
        },
    },
    "iniciatoro": {
        "expected_options": ["iniciat/or/o"],
        "expected_signatures": [{
            "reconstruction": "iniciatoro",
            "spans": [
                {"text": "iniciat", "ruby": True},
                {"text": "or", "ruby": True},
                {"text": "o", "ruby": False},
            ],
        }],
        "sources": ["html_corpus"],
        "current": "iniciator/o",
        "current_typed": "R:iniciator|L:o",
        "current_signature": {
            "reconstruction": "iniciatoro",
            "spans": [
                {"text": "iniciator", "ruby": True},
                {"text": "o", "ruby": False},
            ],
        },
    },
    "tia-tia": {
        "expected_options": ["ti/a-ti/a"],
        "expected_signatures": [{
            "reconstruction": "tia-tia",
            "spans": [
                {"text": "ti", "ruby": True},
                {"text": "a-", "ruby": False},
                {"text": "ti", "ruby": True},
                {"text": "a", "ruby": False},
            ],
        }],
        "sources": ["gold_unmarked"],
        "current": "tia/-/tia",
        "current_typed": "R:tia|L:-|R:tia",
        "current_signature": {
            "reconstruction": "tia-tia",
            "spans": [
                {"text": "tia", "ruby": True},
                {"text": "-", "ruby": False},
                {"text": "tia", "ruby": True},
            ],
        },
    },
}


def stable_json_sha256(value) -> str:
    raw = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("ascii")
    return hashlib.sha256(raw).hexdigest().upper()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _is_git_oid(value) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(character in "0123456789abcdef" for character in value)
    )


def _validate_file_identity(identity: dict, label: str) -> Path:
    if set(identity) != {"path", "bytes", "sha256"}:
        raise ValueError(f"{label} file-identity schema drift")
    path = HERE / identity["path"]
    if (
        not path.is_file()
        or path.is_symlink()
        or path.stat().st_size != identity["bytes"]
        or file_sha256(path) != identity["sha256"]
    ):
        raise ValueError(f"{label} immutable file drift")
    return path


def _is_upper_sha256(value) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789ABCDEF" for character in value)
    )


def _validate_measurement_contract(measurement: dict) -> None:
    if (
        not isinstance(measurement, dict)
        or set(measurement) != POST_PHASE600_MEASUREMENT_KEYS
        or measurement.get("required_pins")
        != list(POST_PHASE600_REQUIRED_PINS)
    ):
        raise ValueError("post-Phase600 measurement schema drift")
    status = measurement.get("status")
    values = [
        measurement[name] for name in POST_PHASE600_REQUIRED_PINS
    ]
    if status == "pending_full_raw_audit":
        if any(value is not None for value in values):
            raise ValueError(
                "pending post-Phase600 measurement contains projected pins"
            )
        return
    if status != "sealed_full_raw_audit":
        raise ValueError("post-Phase600 measurement status drift")
    if (
        not _is_upper_sha256(
            measurement["trilingual_signature_sha256"]
        )
        or not _is_upper_sha256(
            measurement["raw_source_statistics_sha256"]
        )
    ):
        raise ValueError("post-Phase600 measurement digest drift")
    _validate_stat_block(
        measurement["raw_combined"], "measured post-Phase600 combined"
    )
    _validate_stat_block(
        measurement["raw_html_corpus"],
        "measured post-Phase600 html_corpus",
    )


def _require_sealed_measurements(contract: dict) -> dict:
    measurement = contract["post_phase600_measurement"]
    _validate_measurement_contract(measurement)
    if measurement["status"] != "sealed_full_raw_audit":
        raise ValueError(
            "post-Phase600 fingerprints/statistics are not measured and sealed"
        )
    return measurement


def load_scope() -> dict:
    if (
        not SCOPE_PATH.is_file()
        or SCOPE_PATH.is_symlink()
        or file_sha256(SCOPE_PATH) != EXPECTED_SCOPE_SHA256
    ):
        raise ValueError("current-corpus scope identity drift")
    payload = json.loads(SCOPE_PATH.read_text(encoding="utf-8"))
    if set(payload) != {
        "manifest_schema_version",
        "authority_role",
        "projection_sha256",
        "expected",
    }:
        raise ValueError("current-corpus scope schema drift")
    expected = payload["expected"]
    if (
        payload["manifest_schema_version"] != 1
        or payload["authority_role"]
        != "immutable_7c04_reference_for_active_d1642c2"
        or payload["projection_sha256"] != EXPECTED_SCOPE_PROJECTION_SHA256
        or stable_json_sha256(expected) != payload["projection_sha256"]
        or expected.get("case_count") != 68518
        or expected.get("surface_count") != 68429
        or expected.get("reference_sha256")
        != "51D51B1F2FCB32B94FB5F904714AB39AB772884410DE35A20B5B7955BEA868BB"
        or expected.get("reference_conflict_count") != 89
        or expected.get("reference_conflicts_sha256")
        != "16FD7BFCF7C1FC1840400FC4D09B83BCA96B987971C12C5BDE1A5D6A5D42404E"
        or expected.get("corpus", {}).get("content_sha256")
        != "4F04FD2F3DBE0FC79909CBBEA61ED2848FC093AE2DFE3F0ADEB79882AEB04F52"
        or expected.get("corpus_repository", {}).get("head_oid")
        != "7c04f97c51a7cecf88918d2abc2e6bf2f34601a6"
        or expected.get("corpus_repository", {}).get("status_entries") != 0
        or expected.get("gold", {}).get("sha256")
        != phase532.CANDIDATE_LEARNER_SHA256
    ):
        raise ValueError("current-corpus scope content drift")
    return payload


def load_manifest() -> dict:
    raw = MANIFEST_PATH.read_bytes()
    digest = hashlib.sha256(raw).hexdigest().upper()
    if EXPECTED_MANIFEST_SHA256 == "TO_BE_SEALED":
        raise ValueError(f"unsealed current-corpus sidecar: {digest}")
    if digest != EXPECTED_MANIFEST_SHA256:
        raise ValueError(
            f"current-corpus sidecar drift: {digest} != "
            f"{EXPECTED_MANIFEST_SHA256}"
        )
    manifest = json.loads(raw.decode("utf-8"))
    expected_top = {
        "schema_version",
        "policy",
        "immutable_predecessors",
        "reference_authority",
        "active_current_authority",
        "e373_to_7c04_weight_transition",
        "reference_to_active_transition",
        "current_only_audit_contract",
        "expected_counts",
    }
    if set(manifest) != expected_top or manifest["schema_version"] != 1:
        raise ValueError("current-corpus sidecar schema drift")
    if manifest["expected_counts"] != {
        "immutable_predecessors": 3,
        "languages": 3,
        "e373_to_7c04_weight_rows": 110,
        "reference_to_active_weight_rows": 2,
        "reviewed_active_improvements": 1,
        "raw_current_wrong_surfaces": 4,
        "retained_reviewed_ruby_authorities": 2,
        "contextual_admissions": 1,
        "expected_phase600_repairs": 4,
        "active_semantic_wrong_surfaces": 0,
    }:
        raise ValueError("current-corpus sidecar count drift")
    predecessors = manifest["immutable_predecessors"]
    if set(predecessors) != {
        "phase558_sidecar",
        "e373_scope",
        "conflict_review",
    }:
        raise ValueError("current-corpus predecessor schema drift")
    for name, identity in predecessors.items():
        _validate_file_identity(identity, name)
    scope_identity = manifest["reference_authority"]["scope"]
    if (
        scope_identity != {
            "path": "_current_corpus_scope_d1642c2.json",
            "bytes": 10421,
            "sha256": EXPECTED_SCOPE_SHA256,
        }
        or _validate_file_identity(scope_identity, "successor scope")
        != SCOPE_PATH
    ):
        raise ValueError("current-corpus successor scope cross-link drift")
    scope = load_scope()
    reference = manifest["reference_authority"]
    active = manifest["active_current_authority"]
    weight = manifest["e373_to_7c04_weight_transition"]
    active_delta = manifest["reference_to_active_transition"]
    contract = manifest["current_only_audit_contract"]
    if (
        reference["role"] != "immutable_7c04_reference"
        or reference["projection"]["projection_sha256"]
        != scope["projection_sha256"]
        or reference["projection"]["raw_cases"] != 68518
        or reference["projection"]["surfaces"] != 68429
        or reference["projection"]["raw_reference_sha256"]
        != "51D51B1F2FCB32B94FB5F904714AB39AB772884410DE35A20B5B7955BEA868BB"
        or reference["projection"]["case_set_sha256"]
        != "D28146FE46119D3C58DEB47A6C9E9971FBB599F62C507839BCD218FE364AFB3E"
        or reference["projection"]["reference_conflicts"] != 89
        or reference["projection"]["resolved_cases"] != 68479
        or reference["projection"]["resolved_reference_sha256"]
        != "AD032F3FF47F327179339828BB2B1E7A945ED6AE72D2D5C0CBC5743EC9728143"
        or active["role"] != "active_d1642c2_corpus"
        or active["corpus"]["head_oid"]
        != "d1642c276857c1fe400a6d597214ff7a923e7bd2"
        or active["corpus"]["content_sha256"]
        != "C8CAA1940F7F4685CE317B4107E9AA36AF28CBC47A06630CD24092D3C045BE1B"
        or active["direct_projection_diagnostic"]["raw_cases"] != 68517
        or active["direct_projection_diagnostic"]["reference_conflicts"] != 88
        or active["direct_projection_diagnostic"]["raw_reference_sha256"]
        != "C7E3FEAAC509C2C0CC3206EE773BE75299C1E98F6C4EA0EE26879C934F6F7727"
        or active["direct_projection_diagnostic"]["case_set_sha256"]
        != "72FC79C41ED60DF979A295E3C3AFEA0A18770B3D591B2406977B936E470C6859"
        or active["direct_projection_diagnostic"][
            "resolved_reference_sha256"
        ] != "17E0AB9CA576BB07C5090448AABE296EC0B5B7D7AE34A9EE20EDE75A8F365D10"
        or weight["changed_weight_rows"] != 110
        or weight["aggregate_weight_delta"] != -302
        or weight["weight_rows_sha256"] != EXPECTED_WEIGHT_ROWS_SHA256
        or any(
            weight[key] is not True
            for key in (
                "case_key_set_unchanged",
                "conflicts_unchanged",
                "surfaces_unchanged",
            )
        )
        or active_delta["changed_weight_rows"] != 2
        or active_delta["aggregate_weight_delta"] != 0
        or active_delta["weight_rows_sha256"] != EXPECTED_ACTIVE_ROWS_SHA256
        or active_delta["surface"] != "iniciatoro"
        or active_delta["reference_decomposition"] != "iniciat/or/o"
        or active_delta["active_decomposition"] != "iniciator/o"
        or active_delta["disposition"]
        != "reviewed_active_corpus_improvement"
        or contract["required_languages"] != list(EXPECTED_LANGUAGES)
        or contract["trilingual_boundary_contract"] != {
            "surface_count": 68429,
            "fingerprint_definition": (
                "stable_json_sha256([[surface,signature_payload],...]) in "
                "the immutable reference surface order"
            ),
            "all_language_fingerprints_must_match": True,
            "mismatches": 0,
        }
        or contract["raw_current_wrong_surfaces"] != list(EXPECTED_FINDINGS)
        or contract["active_semantic_wrong_surfaces"]
        != []
        or contract["retained_reviewed_ruby_authorities"]
        != list(EXPECTED_RETAINED_AUTHORITIES)
        or contract["reviewed_active_improvements"]
        != list(EXPECTED_ACTIVE_IMPROVEMENTS)
        or contract["expected_phase600_repairs"]
        != list(EXPECTED_PHASE600_REPAIRS)
    ):
        raise ValueError("current-corpus sidecar semantic drift")
    contextual = contract.get("contextual_admissions")
    if (
        not isinstance(contextual, list)
        or len(contextual) != 1
        or contextual[0].get("surface") != "Temis"
        or contextual[0].get("kind")
        != "phrase_bounded_phase599_promotion"
        or contextual[0].get("global_surface_rule_added") is not False
        or _validate_file_identity(
            contextual[0].get("authority", {}),
            "Phase 599 contextual promotion",
        ).name != "_phase599_temis_context_promotion.json"
    ):
        raise ValueError("current-corpus contextual admission drift")
    _validate_measurement_contract(contract["post_phase600_measurement"])
    return manifest


def _corpus_case_set_sha256(cases: dict) -> str:
    rows = sorted(
        [
            {
                "surface": case["surface"],
                "signature": audit.signature_payload(case["signature"]),
            }
            for case in cases.values()
        ],
        key=lambda row: json.dumps(
            row, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        ),
    )
    return stable_json_sha256(rows)


def _weight_rows(before: dict, after: dict) -> list[dict]:
    def key_text(key):
        surface, signature = key
        return json.dumps(
            {
                "surface": surface,
                "signature": audit.signature_payload(signature),
            },
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )

    rows = []
    for key in sorted(set(before) | set(after), key=key_text):
        before_case = before.get(key)
        after_case = after.get(key)
        before_weight = (
            before_case["sources"].get("html_corpus", 0)
            if before_case is not None
            else 0
        )
        after_weight = (
            after_case["sources"].get("html_corpus", 0)
            if after_case is not None
            else 0
        )
        if before_weight == after_weight:
            continue
        surface, signature = key
        rows.append({
            "surface": surface,
            "expected_before": (
                before_case.get("expected") if before_case is not None else None
            ),
            "expected_after": (
                after_case.get("expected") if after_case is not None else None
            ),
            "signature": audit.signature_payload(signature),
            "before_weight": before_weight,
            "after_weight": after_weight,
            "delta": after_weight - before_weight,
        })
    return rows


def _load_corpus(root: Path, expected: dict, label: str) -> tuple[dict, dict]:
    root = Path(root).resolve()
    if not root.is_dir() or root.is_symlink():
        raise ValueError(f"{label} corpus is not a regular directory")
    cases: dict = {}
    metadata = audit.corpus_cases(cases, root)
    repository = audit.git_repo_state(root)
    if (
        repository.get("head_oid") != expected["head_oid"]
        or repository.get("status_entries") != 0
        or repository.get("status_sha256") != expected["status_sha256"]
        or metadata.get("content_sha256") != expected["content_sha256"]
        or metadata.get("files") != expected["files"]
        or metadata.get("raw_ruby") != expected["raw_ruby"]
        or metadata.get("parsed_units") != expected["parsed_units"]
        or len(cases) != expected["corpus_cases"]
    ):
        raise ValueError(f"{label} corpus identity drift")
    return cases, {"corpus": metadata, "repository": repository}


def _git_changed_paths(
    repository: Path, before_oid: str, after_oid: str
) -> list[str]:
    completed = subprocess.run(
        ["git", "diff", "--name-only", before_oid, after_oid],
        cwd=repository,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        raise ValueError(
            completed.stderr.decode("utf-8", errors="replace").strip()
        )
    return [
        line for line in completed.stdout.decode("utf-8").splitlines() if line
    ]


def validate_corpus_authorities(
    e373_root: Path,
    reference_root: Path,
    active_root: Path,
    *,
    manifest: dict | None = None,
) -> dict:
    if manifest is None:
        manifest = load_manifest()
    old_scope = json.loads(
        (HERE / "_phase558_current_corpus_scope_manifest.json").read_text(
            encoding="utf-8"
        )
    )["expected"]
    e373_expected = {
        "head_oid": old_scope["corpus_repository"]["head_oid"],
        "status_sha256": old_scope["corpus_repository"]["status_sha256"],
        "content_sha256": old_scope["corpus"]["content_sha256"],
        "files": old_scope["corpus"]["files"],
        "raw_ruby": old_scope["corpus"]["raw_ruby"],
        "parsed_units": old_scope["corpus"]["parsed_units"],
        "corpus_cases": 21872,
    }
    reference_expected = manifest["reference_authority"]["corpus"]
    active_expected = manifest["active_current_authority"]["corpus"]
    e373_cases, _e373_identity = _load_corpus(
        e373_root, e373_expected, "e373"
    )
    reference_cases, _reference_identity = _load_corpus(
        reference_root, reference_expected, "7c04 reference"
    )
    active_cases, _active_identity = _load_corpus(
        active_root, active_expected, "d164 active"
    )

    weight_rows = _weight_rows(e373_cases, reference_cases)
    weight_contract = manifest["e373_to_7c04_weight_transition"]
    if (
        set(e373_cases) != set(reference_cases)
        or len(weight_rows) != weight_contract["changed_weight_rows"]
        or len({row["surface"] for row in weight_rows})
        != weight_contract["changed_surfaces"]
        or sum(row["delta"] for row in weight_rows)
        != weight_contract["aggregate_weight_delta"]
        or stable_json_sha256(weight_rows)
        != weight_contract["weight_rows_sha256"]
    ):
        raise ValueError("e373-to-7c04 weight transition drift")

    active_rows = _weight_rows(reference_cases, active_cases)
    active_contract = manifest["reference_to_active_transition"]
    if (
        len(active_rows) != active_contract["changed_weight_rows"]
        or sum(row["delta"] for row in active_rows)
        != active_contract["aggregate_weight_delta"]
        or stable_json_sha256(active_rows)
        != active_contract["weight_rows_sha256"]
        or {row["surface"] for row in active_rows} != {"iniciatoro"}
        or set(active_cases) - set(reference_cases)
        != {
            (
                audit.canonical("iniciatoro"),
                audit.expected_signature("iniciator/o", frozenset()),
            )
        }
        or set(reference_cases) - set(active_cases)
        != {
            (
                audit.canonical("iniciatoro"),
                audit.expected_signature("iniciat/or/o", frozenset()),
            )
        }
    ):
        raise ValueError("7c04-to-d164 semantic transition drift")
    if {case["surface"] for case in reference_cases.values()} != {
        case["surface"] for case in active_cases.values()
    }:
        raise ValueError("d164 active transition changed surface coverage")

    changed_file = active_contract["changed_file"]
    reference_file = Path(reference_root) / changed_file["path"]
    active_file = Path(active_root) / changed_file["path"]
    for path, prefix in (
        (reference_file, "reference"),
        (active_file, "active"),
    ):
        if (
            not path.is_file()
            or path.is_symlink()
            or path.stat().st_size != changed_file[f"{prefix}_bytes"]
            or file_sha256(path) != changed_file[f"{prefix}_sha256"]
        ):
            raise ValueError(f"d164 changed-file {prefix} identity drift")
    changed_paths = _git_changed_paths(
        Path(active_root),
        manifest["reference_authority"]["corpus"]["head_oid"],
        manifest["active_current_authority"]["corpus"]["head_oid"],
    )
    if changed_paths != [changed_file["path"]]:
        raise ValueError("7c04-to-d164 Git path closure drift")
    return {
        "e373_to_7c04_case_set_unchanged": True,
        "e373_to_7c04_weight_rows": len(weight_rows),
        "e373_to_7c04_weight_delta": sum(
            row["delta"] for row in weight_rows
        ),
        "reference_to_active_weight_rows": len(active_rows),
        "reference_to_active_weight_delta": sum(
            row["delta"] for row in active_rows
        ),
        "reviewed_active_improvements": ["iniciatoro"],
        "gate": True,
    }


def _validate_stat_block(stats: dict, label: str) -> None:
    if set(stats) != STAT_KEYS:
        raise ValueError(f"{label} statistics schema drift")
    if any(
        not isinstance(value, int) or value < 0 for value in stats.values()
    ):
        raise ValueError(f"{label} statistics value drift")
    if (
        stats["baseline_correct_weight"] != stats["current_correct_weight"]
        or stats["baseline_correct_cases"] != stats["current_correct_cases"]
        or stats["regression_weight"] != 0
        or stats["regression_cases"] != 0
        or stats["improvement_weight"] != 0
        or stats["improvement_cases"] != 0
        or stats["current_correct_weight"] > stats["total_weight"]
        or stats["current_correct_cases"] > stats["total_cases"]
    ):
        raise ValueError(f"{label} current-only statistics invariant drift")


def _validate_finding_record(record: dict) -> None:
    surface = record.get("surface")
    expected = EXPECTED_FINDING_RECORDS.get(surface)
    expected_keys = {
        "surface",
        "expected_options",
        "expected_signatures",
        "sources",
        "baseline",
        "baseline_typed",
        "current",
        "current_typed",
        "current_signature",
    }
    if (
        expected is None
        or set(record) != expected_keys
        or record["expected_options"] != expected["expected_options"]
        or record["expected_signatures"] != expected["expected_signatures"]
        or record["sources"] != expected["sources"]
        or record["baseline"] != expected["current"]
        or record["baseline_typed"] != expected["current_typed"]
        or record["current"] != expected["current"]
        or record["current_typed"] != expected["current_typed"]
        or record["current_signature"] != expected["current_signature"]
    ):
        raise ValueError(f"current-corpus finding drift: {surface!r}")


def _validate_phase599_context_report(report: dict) -> None:
    context = (
        report.get("promoted_corpus_context_runtime", {})
        if isinstance(report, dict)
        else {}
    )
    if (
        not isinstance(report, dict)
        or report.get("promotion_audit_gate") is not True
        or report.get("post_promotion_global_rows_per_language") != 572506
        or report.get("managed_rows_per_language")
        != {"JA": 5, "ZH": 5, "KO": 5}
        or report.get("kanji_nonintervention") is not True
        or context.get("gate") is not True
        or context.get("corpus_instances") != 6
        or context.get("language_cases_activated") != 15
        or context.get("trilingual_boundaries_identical") is not True
        or context.get("trilingual_rb_sequences_identical") is not True
    ):
        raise ValueError("Phase 599 contextual admission runtime drift")


def validate_audit_report(
    report: dict,
    *,
    manifest: dict | None = None,
    runtime_report: dict | None = None,
    phase599_report: dict | None = None,
) -> dict:
    if manifest is None:
        manifest = load_manifest()
    scope_payload = load_scope()
    expected_projection = scope_payload["expected"]
    contract = manifest["current_only_audit_contract"]
    measurement = _require_sealed_measurements(contract)
    _validate_phase599_context_report(phase599_report)
    projection_pin = manifest["reference_authority"]["projection"]
    corpus_pin = manifest["reference_authority"]["corpus"]
    if (
        not isinstance(report, dict)
        or set(report) != TOP_KEYS
        or report.get("complete") is not True
        or report.get("gate") is not False
    ):
        raise ValueError("successor requires a complete reviewed gate-false audit")
    stability = report["inputs_stable"]
    if (
        not isinstance(stability, dict)
        or set(stability) != set(contract["required_input_stability"])
        or any(value is not True for value in stability.values())
    ):
        raise ValueError("successor audit inputs were not stable")
    phase558_gate._validate_scope_projection(
        report["scope"], expected_projection, "current d164 successor reference"
    )
    resolved = report["resolved_reference"]
    reviewed = report["reviewed_reference"]
    checkpoint = report["checkpoint_context"]
    if (
        report["reference_projection"] != expected_projection
        or report["raw_case_count"] != projection_pin["raw_cases"]
        or report["surface_count"] != projection_pin["surfaces"]
        or report["case_count"] != projection_pin["resolved_cases"]
        or resolved != {
            "case_count": projection_pin["resolved_cases"],
            "surface_count": projection_pin["surfaces"],
            "reference_sha256": projection_pin[
                "resolved_reference_sha256"
            ],
        }
        or reviewed.get("scope_manifest_sha256") != EXPECTED_SCOPE_SHA256
        or reviewed.get("conflict_manifest_sha256")
        != manifest["immutable_predecessors"]["conflict_review"]["sha256"]
        or checkpoint.get("scope_manifest_sha256") != EXPECTED_SCOPE_SHA256
        or checkpoint.get("conflict_manifest_sha256")
        != manifest["immutable_predecessors"]["conflict_review"]["sha256"]
        or checkpoint.get("raw_reference_sha256")
        != projection_pin["raw_reference_sha256"]
        or checkpoint.get("reference_sha256")
        != projection_pin["resolved_reference_sha256"]
        or checkpoint.get("surface_sha256")
        != projection_pin["surface_sha256"]
        or checkpoint.get("corpus_sha256") != corpus_pin["content_sha256"]
        or checkpoint.get("corpus_head_oid") != corpus_pin["head_oid"]
        or checkpoint.get("corpus_status_sha256")
        != corpus_pin["status_sha256"]
        or checkpoint.get("gold_sha256")
        != phase532.CANDIDATE_LEARNER_SHA256
        or not _is_git_oid(checkpoint.get("head_oid"))
    ):
        raise ValueError("successor audit projection identity drift")

    rows = report["languages"]
    if (
        not isinstance(rows, list)
        or [row.get("language") for row in rows] != list(EXPECTED_LANGUAGES)
    ):
        raise ValueError("successor audit language scope drift")
    trilingual = report["successor_trilingual_boundaries"]
    fingerprints_by_language = (
        trilingual.get("signature_sha256", {})
        if isinstance(trilingual, dict)
        else {}
    )
    if (
        not isinstance(trilingual, dict)
        or set(trilingual) != {
            "schema_version",
            "surface_count",
            "languages",
            "signature_sha256",
            "mismatches",
            "gate",
        }
        or trilingual["schema_version"] != 1
        or trilingual["surface_count"] != 68429
        or trilingual["languages"] != list(EXPECTED_LANGUAGES)
        or not isinstance(fingerprints_by_language, dict)
        or list(fingerprints_by_language) != list(EXPECTED_LANGUAGES)
        or any(
            not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789ABCDEF" for character in digest)
            for digest in fingerprints_by_language.values()
        )
        or len(set(fingerprints_by_language.values())) != 1
        or next(iter(fingerprints_by_language.values()), None)
        != measurement["trilingual_signature_sha256"]
        or trilingual["mismatches"] != 0
        or trilingual["gate"] is not True
    ):
        raise ValueError("successor full trilingual boundary closure drift")
    finding_fixtures = []
    fingerprints = {}
    for row in rows:
        language = row["language"]
        if (
            set(row) != LANGUAGE_KEYS
            or row["input_stable"] is not True
            or row["gate"] is not False
            or not isinstance(row["input_fingerprint"], dict)
            or not row["input_fingerprint"]
        ):
            raise ValueError(f"{language} successor language row drift")
        fingerprints[language] = row["input_fingerprint"]
        comparison = row["comparison"]
        if (
            set(comparison) != COMPARISON_KEYS
            or comparison["comparison"] != "current_only"
            or comparison["gate"] is not False
            or comparison["weighted_worsening_sources"] != []
        ):
            raise ValueError(f"{language} successor comparison drift")
        sources = comparison["sources"]
        if set(sources) != set(contract["required_sources"]):
            raise ValueError(f"{language} successor source scope drift")
        for source, stats in sources.items():
            _validate_stat_block(stats, f"{language}/{source}")
        _validate_stat_block(comparison["combined"], f"{language}/combined")
        if (
            stable_json_sha256(sources)
            != measurement["raw_source_statistics_sha256"]
            or comparison["combined"] != measurement["raw_combined"]
            or sources["html_corpus"]
            != measurement["raw_html_corpus"]
        ):
            raise ValueError(f"{language} successor absolute statistics drift")
        for bucket in FINDING_KEYS - {
            "current_unreferenced_wrong_surfaces"
        }:
            if comparison[bucket] != []:
                raise ValueError(f"{language}/{bucket} escaped reviewed closure")
        findings = comparison["current_unreferenced_wrong_surfaces"]
        surfaces = [
            item.get("surface") for item in findings if isinstance(item, dict)
        ]
        if surfaces != list(EXPECTED_FINDINGS):
            raise ValueError(f"{language} successor finding surface drift")
        for finding in findings:
            _validate_finding_record(finding)
        finding_fixtures.append(findings)
    if any(findings != finding_fixtures[0] for findings in finding_fixtures[1:]):
        raise ValueError("JA/ZH/KO successor finding boundaries differ")

    runtime_summary = None
    if runtime_report is not None:
        parent_manifest = phase558_gate.load_manifest()
        runtime_summary = phase558_gate.validate_runtime_report(
            runtime_report, parent_manifest
        )
        phase558_gate.require_same_runtime_app_snapshot(
            fingerprints, runtime_report, "current-d164-successor"
        )
    return {
        "audit_kind": "current_d1642c2_with_immutable_7c04_reference",
        "reference_head_oid": corpus_pin["head_oid"],
        "active_head_oid": manifest["active_current_authority"]["corpus"][
            "head_oid"
        ],
        "languages": list(EXPECTED_LANGUAGES),
        "raw_current_wrong_surfaces": list(EXPECTED_FINDINGS),
        "retained_reviewed_ruby_authorities": list(
            EXPECTED_RETAINED_AUTHORITIES
        ),
        "reviewed_active_improvements": list(
            EXPECTED_ACTIVE_IMPROVEMENTS
        ),
        "contextual_admissions": list(EXPECTED_CONTEXTUAL_ADMISSIONS),
        "active_semantic_wrong_surfaces": [],
        "trilingual_boundary_mismatches": 0,
        "runtime_revalidated": runtime_summary is not None,
        "gate": True,
    }


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--e373-corpus", type=Path, required=True)
    parser.add_argument("--reference-corpus", type=Path, required=True)
    parser.add_argument("--active-corpus", type=Path, required=True)
    parser.add_argument("--deployed", action="store_true", required=True)
    parser.add_argument("--batch-size", type=int, default=33)
    args = parser.parse_args(argv)
    manifest = load_manifest()
    authority_summary = validate_corpus_authorities(
        args.e373_corpus,
        args.reference_corpus,
        args.active_corpus,
        manifest=manifest,
    )
    report = json.loads(args.audit.read_text(encoding="utf-8"))
    runtime_report = phase558_runtime.validate_deployed_payloads(
        "post-regen", batch_size=args.batch_size
    )
    import phase599_temis_context_promotion as phase599_promotion

    phase599_report = phase599_promotion.audit_deployed_promotion(
        batch_size=min(args.batch_size, 50),
    )
    summary = validate_audit_report(
        report,
        manifest=manifest,
        runtime_report=runtime_report,
        phase599_report=phase599_report,
    )
    summary["authority_validation"] = authority_summary
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
