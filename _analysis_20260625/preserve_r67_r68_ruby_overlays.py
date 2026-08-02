#!/usr/bin/env python3
"""Carry the reviewed R67/R68 Ruby protection layers across regeneration.

``apply_confirmed_now.py --write`` rebuilds the three large Ruby payloads from
the pinned master inputs.  The R67/R68 protections were historically added as
post-generation sidecars, so a plain rebuild drops them.  Re-running the old
R68 discovery script is not an acceptable recovery mechanism: it scans a
moving absolute master and can widen its scope.

This module instead seals the already-deployed, reviewed rows before a rebuild
and restores exactly that closed set afterwards.  Historical recovery keeps
the original R72/R73 profile immutable, while ordinary current regeneration
uses the separately pinned post-Temis profile.  Any collision or drift fails
before the three deployed payloads are replaced.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from atomic_json import atomic_file_copy, atomic_json_dump


ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ("JA", "ZH", "KO")
RUBY_PAYLOAD_NAME = (
    "\u7f6e\u63db\u30ea\u30b9\u30c8_\u30eb\u30d3.json"
)
GLOBAL_BUCKET_TOKEN = "replacements_final_list"
OVERLAY_PREFIXES = ("R67H", "R68W")
SCHEMA_VERSION = 2

PINNED_PARENT_COMMIT = "4682D32496F166802B4A2CF28626F376E12AAE3E"
PINNED_PARENT_TREE = "2C494DB69EBAC28EF63A192BEFA017A22710CCD7"
PINNED_PARENT_GLOBAL_ROWS = 572_356
EXPECTED_POST_R73_GLOBAL_ROWS = 572_501
PRE_R94_PRE_R81_GLOBAL_ROWS = 572_713
PRE_R94_DEPLOYED_GLOBAL_ROWS = 572_771
CCB9398_PRE_R81_GLOBAL_ROWS = 573_240
CCB9398_DEPLOYED_GLOBAL_ROWS = 573_298
CURRENT_PRE_R81_GLOBAL_ROWS = 573_241
# 世代ごとの全域ルビ行数(履歴)。増分の出所を必ず書き残す。
#   572_729  第87R(Phase 619 サイドカー)まで
#   +18      第88R  Phase 619 の族取り残し mukoz 基語(30語形のうち新規18)
#   +24      第89R  京大コーパス全数照合で残った「接尾辞が裸で落ちる」8語族
#   +527     第94R  ccb9398 residual closure + 202608 exact word_anno scope
#   +1       dd55318 U+2019 exact/case-sensitive/Ruby-only alias
CURRENT_DEPLOYED_GLOBAL_ROWS = 573_299
OVERLAY_TRANSITION_PATH = (
    ROOT / "_analysis_20260625" / "_r67_r68_overlay_transition_ccb9398.json"
)
WORD_ANNO_TRANSITION_PATH = (
    ROOT / "_analysis_20260625" / "_word_anno_boundary_transition_ccb9398.json"
)
SUCCESSOR_OVERLAY_TRANSITION_PATH = (
    ROOT / "_analysis_20260625"
    / "_r67_r68_overlay_transition_dd55318_u2019.json"
)
SUCCESSOR_WORD_ANNO_TRANSITION_PATH = (
    ROOT / "_analysis_20260625"
    / "_word_anno_boundary_transition_dd55318_u2019.json"
)

HISTORICAL_EXPECTED_OVERLAYS = {
    "JA": {
        "R67H": {
            "count": 336,
            "rows_sha256": (
                "EFF64DE3C95FEC66209CA72E1EFE5A8E0EB0C438A89AEA4C200A6C41130F340A"
            ),
            "sources_sha256": (
                "0408F60AA78FB00B2A43FAE3A6FDA93E68C1786C660DA6094A0A6E27FCFB919B"
            ),
        },
        "R68W": {
            "count": 1_013,
            "rows_sha256": (
                "BE04F81592359C8DB5B51D45721440D2025BCC61D5C163821EEECC90A70CFF2D"
            ),
            "sources_sha256": (
                "9DD2837E37A927105E626897ACD99E23A40FE22826015B6A0E05CF6DC2833B3B"
            ),
        },
    },
    "ZH": {
        "R67H": {
            "count": 336,
            "rows_sha256": (
                "2BE0D3D80BFCFF668D771DB4891A9F8A0E52BBBB4C5F10A7B364A3DA6625D609"
            ),
            "sources_sha256": (
                "0408F60AA78FB00B2A43FAE3A6FDA93E68C1786C660DA6094A0A6E27FCFB919B"
            ),
        },
        "R68W": {
            "count": 1_013,
            "rows_sha256": (
                "74A9D3F5A4F6BCC879E57C67044F42A6A09FAAACDFD90580878B7752910649FD"
            ),
            "sources_sha256": (
                "9DD2837E37A927105E626897ACD99E23A40FE22826015B6A0E05CF6DC2833B3B"
            ),
        },
    },
    "KO": {
        "R67H": {
            "count": 336,
            "rows_sha256": (
                "3341E8260981925082A3E4D156B64FA2C21A7B7FB6FED8FB97973B941C73B056"
            ),
            "sources_sha256": (
                "0408F60AA78FB00B2A43FAE3A6FDA93E68C1786C660DA6094A0A6E27FCFB919B"
            ),
        },
        "R68W": {
            "count": 1_013,
            "rows_sha256": (
                "663C2D073A563C5B17527E8FFC13829FBEE0125C211C194BACC9C2136AC817BE"
            ),
            "sources_sha256": (
                "9DD2837E37A927105E626897ACD99E23A40FE22826015B6A0E05CF6DC2833B3B"
            ),
        },
    },
}

CURRENT_EXPECTED_OVERLAYS = {
    "JA": {
        "R67H": HISTORICAL_EXPECTED_OVERLAYS["JA"]["R67H"],
        "R68W": {
            "count": 1_012,
            "rows_sha256": (
                "2A43539F873A792F3F50712B575871318A3A96A1E8EE7A90EDBD55D51F342CC0"
            ),
            "sources_sha256": (
                "E6B91C551DD567EEC6B9BA16262F704140B28CA8BF3ED7048C3E5F9AF2672B79"
            ),
        },
    },
    "ZH": {
        "R67H": HISTORICAL_EXPECTED_OVERLAYS["ZH"]["R67H"],
        "R68W": {
            "count": 1_012,
            "rows_sha256": (
                "88A914F4E8BF443585C9319C19DB88BC64DF6EBDE400ED604C64F70F3758865C"
            ),
            "sources_sha256": (
                "E6B91C551DD567EEC6B9BA16262F704140B28CA8BF3ED7048C3E5F9AF2672B79"
            ),
        },
    },
    "KO": {
        "R67H": HISTORICAL_EXPECTED_OVERLAYS["KO"]["R67H"],
        "R68W": {
            "count": 1_012,
            "rows_sha256": (
                "8A9E699E29B860B609883A2FAB4D6256F3ADB67BEF385A503DFE9B7C6B7207EB"
            ),
            "sources_sha256": (
                "E6B91C551DD567EEC6B9BA16262F704140B28CA8BF3ED7048C3E5F9AF2672B79"
            ),
        },
    },
}
CCB9398_EXPECTED_OVERLAYS = {
    "JA": {
        "R67H": CURRENT_EXPECTED_OVERLAYS["JA"]["R67H"],
        "R68W": {
            "count": 1_012,
            "rows_sha256": (
                "7F1E4662EB048D3AE7F85D7D3EB670A6111FBB5055EE9A9466D91419242C970D"
            ),
            "sources_sha256": (
                "BC7F454537089FE4185FEB121FCC9FD200FFC58F2ADCFC7038ABCEC5488904C6"
            ),
        },
    },
    "ZH": {
        "R67H": CURRENT_EXPECTED_OVERLAYS["ZH"]["R67H"],
        "R68W": {
            "count": 1_012,
            "rows_sha256": (
                "727AFE5890EAD1BD01C797ADB6DA84FC0B0ABE742799D9650CD78EDAEEA3AEB0"
            ),
            "sources_sha256": (
                "BC7F454537089FE4185FEB121FCC9FD200FFC58F2ADCFC7038ABCEC5488904C6"
            ),
        },
    },
    "KO": {
        "R67H": CURRENT_EXPECTED_OVERLAYS["KO"]["R67H"],
        "R68W": {
            "count": 1_012,
            "rows_sha256": (
                "71D9584663CAC086BB1D4AB2329DB9387CBDB9CD211BA52416A84D0C4A8AD95C"
            ),
            "sources_sha256": (
                "BC7F454537089FE4185FEB121FCC9FD200FFC58F2ADCFC7038ABCEC5488904C6"
            ),
        },
    },
}
OVERLAY_PROFILES = {
    "historical-r72-r73": HISTORICAL_EXPECTED_OVERLAYS,
    "current-post-temis": CURRENT_EXPECTED_OVERLAYS,
    "current-ccb9398": CCB9398_EXPECTED_OVERLAYS,
}
CURRENT_PROFILE_GLOBAL_ROWS = {
    "current-post-temis": PRE_R94_DEPLOYED_GLOBAL_ROWS,
    "current-ccb9398": CURRENT_DEPLOYED_GLOBAL_ROWS,
}
# A one-time successor rebuild legitimately restores the exact ccb9398 overlay
# snapshot captured immediately before the U+2019 raw rule was generated.
# Future captures still require CURRENT_PROFILE_GLOBAL_ROWS exactly; only the
# signed snapshot loader accepts this explicitly named historical row count.
ALLOWED_CURRENT_SNAPSHOT_ROWS = {
    "current-post-temis": {PRE_R94_DEPLOYED_GLOBAL_ROWS},
    "current-ccb9398": {
        CCB9398_DEPLOYED_GLOBAL_ROWS,
        CURRENT_DEPLOYED_GLOBAL_ROWS,
    },
}

EXACT_OVERRIDE_SOURCE = " Auster "
EXACT_OVERRIDE_RENDERED = {
    "JA": " Auster ",
    "ZH": " Auster ",
    "KO": " Auster ",
}


def compact_sha256(value) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_ccb9398_overlay_transition() -> dict:
    transition = json.loads(
        OVERLAY_TRANSITION_PATH.read_text(encoding="utf-8")
    )
    word_transition = json.loads(
        WORD_ANNO_TRANSITION_PATH.read_text(encoding="utf-8")
    )
    expected_top = {
        "schema_version", "transition", "source_app_commit",
        "word_anno_transition", "profiles", "global_rows",
        "candidate_raw_payload_sha256", "overlay_transition",
        "target_overlay_identity", "policy",
    }
    expected_move = {
        "unchanged_prefix": "R67H",
        "reordered_prefix": "R68W",
        "rows": 1012,
        "row_content_changes": 0,
        "source_set_changes": 0,
        "moved_source": " York ",
        "source_index_before": 862,
        "source_index_after": 1006,
        "shifted_intermediate_rows": 144,
        "sequence_moved_rows": 145,
        "sequence_descents": 1,
    }
    expected_policy = {
        "overlay_row_content_must_remain_identical": True,
        "overlay_source_set_must_remain_identical": True,
        "only_reviewed_order_transition_is_allowed": True,
        "three_language_source_order_must_match": True,
        "kanji_artifacts_must_remain_byte_identical": True,
    }
    word_authority = transition.get("word_anno_transition", {})
    if (
        set(transition) != expected_top
        or transition.get("schema_version") != 1
        or transition.get("transition")
        != "r68-new-york-order-transition-ccb9398"
        or transition.get("profiles")
        != {"source": "current-post-temis", "target": "current-ccb9398"}
        or transition.get("global_rows")
        != {
            "source_deployed": PRE_R94_DEPLOYED_GLOBAL_ROWS,
            "candidate_raw": 571_892,
            "target_after_overlay_restore": CCB9398_PRE_R81_GLOBAL_ROWS,
            "target_after_existing_postfix_layers": CCB9398_DEPLOYED_GLOBAL_ROWS,
        }
        or transition.get("overlay_transition") != expected_move
        or transition.get("target_overlay_identity")
        != CCB9398_EXPECTED_OVERLAYS
        or transition.get("policy") != expected_policy
        or word_authority.get("path")
        != WORD_ANNO_TRANSITION_PATH.relative_to(ROOT).as_posix()
        or word_authority.get("file_sha256")
        != file_sha256(WORD_ANNO_TRANSITION_PATH)
        or word_authority.get("required_added_key") != "New York"
        or "New York" not in word_transition.get("added_keys", [])
        or word_transition.get("policy", {}).get(
            "three_language_boundary_identity_required"
        ) is not True
        or word_transition.get("policy", {}).get(
            "kanji_master_decomposition_is_not_changed"
        ) is not True
    ):
        raise ValueError("invalid ccb9398 R67/R68 overlay transition")
    return transition


def load_dd55318_u2019_overlay_transition(
    raw_payloads: dict | None = None,
) -> dict:
    """Validate the immutable ccb9398 -> one-rule U+2019 successor."""
    transition = json.loads(
        SUCCESSOR_OVERLAY_TRANSITION_PATH.read_text(encoding="utf-8")
    )
    predecessor = load_ccb9398_overlay_transition()
    word_successor = json.loads(
        SUCCESSOR_WORD_ANNO_TRANSITION_PATH.read_text(encoding="utf-8")
    )
    expected_top = {
        "schema_version", "transition", "description", "source_app_commit",
        "authority", "profiles", "global_rows",
        "predecessor_raw_payload_sha256",
        "candidate_raw_payload_sha256", "raw_generation_delta",
        "overlay_transition", "target_overlay_identity", "kanji_artifacts",
        "policy",
    }
    authority = transition.get("authority", {})
    old_authority = authority.get("historical_overlay_transition", {})
    word_authority = authority.get("word_anno_successor_transition", {})
    expected_policy = {
        "historical_overlay_ledger_rewritten": False,
        "word_anno_successor_required": True,
        "only_one_reviewed_u2019_exact_rule_is_added": True,
        "case_sensitive": True,
        "ruby_only": True,
        "wildcard_or_substring_authorization": False,
        "overlay_row_content_must_remain_identical": True,
        "overlay_row_order_must_remain_identical": True,
        "overlay_source_set_must_remain_identical": True,
        "three_language_source_order_must_match": True,
        "kanji_artifacts_must_remain_byte_identical": True,
        "learner_master_changed": False,
        "corpus_changed": False,
    }
    raw_delta = transition.get("raw_generation_delta", {})
    expected_raw_delta_projection = {
        "added_surface": "Fukuwarai’",
        "added_source": " Fukuwarai’ ",
        "ascii_authority_surface": "Fukuwarai'",
        "word_anno_context_key": "@typed:Fukuwarai’:0",
        "target": "Fukuwarai/’",
        "typed_roles": "RL",
        "following_placeholder_delta": 1,
        "exact_only": True,
        "case_sensitive": True,
        "ruby_only": True,
        "wildcard_or_substring_authorization": False,
    }
    if (
        set(transition) != expected_top
        or transition.get("schema_version") != 1
        or transition.get("transition")
        != "r67-r68-overlay-dd55318-u2019-successor-v1"
        or transition.get("source_app_commit")
        != "6a707dd8da4be04da8dba0968b8de9255411af76"
        or transition.get("profiles")
        != {
            "source": "current-ccb9398",
            "target": "current-dd55318-u2019",
        }
        or transition.get("global_rows")
        != {
            "source_deployed": CCB9398_DEPLOYED_GLOBAL_ROWS,
            "predecessor_raw": 571_892,
            "candidate_raw": 571_893,
            "candidate_raw_delta": 1,
            "target_after_overlay_restore": CURRENT_PRE_R81_GLOBAL_ROWS,
            "target_after_existing_postfix_layers": CURRENT_DEPLOYED_GLOBAL_ROWS,
            "overlay_rows_restored": 1_348,
            "existing_postfix_rows": 58,
        }
        or transition.get("target_overlay_identity")
        != predecessor.get("target_overlay_identity")
        or transition.get("overlay_transition")
        != {
            "identity_source": (
                "historical_overlay_transition.target_overlay_identity"
            ),
            "unchanged_prefixes": ["R67H", "R68W"],
            "rows": 1_348,
            "row_content_changes": 0,
            "row_order_changes": 0,
            "source_set_changes": 0,
        }
        or transition.get("policy") != expected_policy
        or {
            key: raw_delta.get(key)
            for key in expected_raw_delta_projection
        } != expected_raw_delta_projection
        or old_authority.get("path")
        != OVERLAY_TRANSITION_PATH.relative_to(ROOT).as_posix()
        or old_authority.get("file_sha256")
        != file_sha256(OVERLAY_TRANSITION_PATH)
        or old_authority.get("required_transition")
        != predecessor.get("transition")
        or word_authority.get("path")
        != SUCCESSOR_WORD_ANNO_TRANSITION_PATH.relative_to(ROOT).as_posix()
        or word_authority.get("file_sha256")
        != file_sha256(SUCCESSOR_WORD_ANNO_TRANSITION_PATH)
        or word_authority.get("required_ledger_id")
        != word_successor.get("ledger_id")
        or word_authority.get("required_added_key")
        not in word_successor.get("delta", {}).get("added_keys", [])
    ):
        raise ValueError("invalid dd55318 U+2019 R67/R68 successor")
    if (
        set(transition.get("kanji_artifacts", {})) != set(LANGUAGES)
        or set(transition.get("candidate_raw_payload_sha256", {}))
        != set(LANGUAGES)
        or set(transition.get("predecessor_raw_payload_sha256", {}))
        != set(LANGUAGES)
    ):
        raise ValueError("invalid U+2019 language/hash closure")
    for language, artifacts in transition.get("kanji_artifacts", {}).items():
        if language not in LANGUAGES or not artifacts:
            raise ValueError("invalid U+2019 Kanji artifact closure")
        for relative, expected_sha256 in artifacts.items():
            if file_sha256(ROOT / relative) != expected_sha256:
                raise ValueError(
                    f"{language}: U+2019 changed Kanji artifact {relative}"
                )
    if raw_payloads is not None:
        if set(raw_payloads) != set(LANGUAGES):
            raise ValueError("U+2019 raw payload language closure drift")
        for language, payload in raw_payloads.items():
            _key, rows = global_bucket(payload)
            if (
                len(rows) != transition["global_rows"]["candidate_raw"]
                or compact_sha256(payload)
                != transition["candidate_raw_payload_sha256"][language]
                or any(overlay_rows(rows, prefix) for prefix in OVERLAY_PREFIXES)
            ):
                raise ValueError(
                    f"{language}: U+2019 raw payload authority drift"
                )
    return transition


def payload_path(language: str) -> Path:
    return (
        ROOT
        / f"Esperanto-Kanji-Ruby-{language}"
        / "app_data"
        / RUBY_PAYLOAD_NAME
    )


def load_payload(language: str, git_ref: str | None = None) -> dict:
    path = payload_path(language)
    if git_ref is None:
        return json.loads(path.read_text(encoding="utf-8"))
    relative = path.relative_to(ROOT).as_posix()
    raw = subprocess.check_output(
        ["git", "show", f"{git_ref}:{relative}"],
        cwd=ROOT,
    )
    return json.loads(raw.decode("utf-8"))


def global_bucket(payload: dict) -> tuple[str, list]:
    matches = [
        key
        for key, rows in payload.items()
        if GLOBAL_BUCKET_TOKEN in key and isinstance(rows, list)
    ]
    if len(matches) != 1:
        raise ValueError(f"global Ruby bucket drift: {matches!r}")
    return matches[0], payload[matches[0]]


def overlay_rows(rows: list, prefix: str) -> list:
    return [
        row
        for row in rows
        if (
            isinstance(row, list)
            and len(row) >= 3
            and isinstance(row[2], str)
            and f"${prefix}" in row[2]
        )
    ]


def validate_rows(
    language: str,
    prefix: str,
    rows: list,
    overlay_profile: str,
) -> dict:
    try:
        expected = OVERLAY_PROFILES[overlay_profile][language][prefix]
    except KeyError as error:
        raise ValueError(
            f"unsupported Ruby overlay profile: {overlay_profile!r}"
        ) from error
    if any(
        not isinstance(row, list)
        or len(row) != 3
        or not all(isinstance(value, str) for value in row)
        for row in rows
    ):
        raise ValueError(f"{language}/{prefix}: malformed overlay row")
    sources = [row[0] for row in rows]
    placeholders = [row[2] for row in rows]
    actual = {
        "count": len(rows),
        "rows_sha256": compact_sha256(rows),
        "sources_sha256": compact_sha256(sources),
    }
    if actual != expected:
        raise ValueError(
            f"{language}/{prefix}: reviewed overlay drift: "
            f"{actual!r} != {expected!r}"
        )
    if len(sources) != len(set(sources)):
        raise ValueError(f"{language}/{prefix}: duplicate source key")
    if len(placeholders) != len(set(placeholders)):
        raise ValueError(f"{language}/{prefix}: duplicate placeholder")
    return actual


def validate_overlay_matrix(
    matrix: dict,
    overlay_profile: str = "current-post-temis",
) -> dict:
    if overlay_profile not in OVERLAY_PROFILES:
        raise ValueError(
            f"unsupported Ruby overlay profile: {overlay_profile!r}"
        )
    if set(matrix) != set(LANGUAGES):
        raise ValueError("overlay snapshot must contain exactly JA/ZH/KO")
    report = {}
    for language in LANGUAGES:
        if set(matrix[language]) != set(OVERLAY_PREFIXES):
            raise ValueError(
                f"{language}: overlay prefixes are not closed"
            )
        report[language] = {}
        for prefix in OVERLAY_PREFIXES:
            report[language][prefix] = validate_rows(
                language, prefix, matrix[language][prefix], overlay_profile,
            )
    for prefix in OVERLAY_PREFIXES:
        source_lists = {
            tuple(row[0] for row in matrix[language][prefix])
            for language in LANGUAGES
        }
        if len(source_lists) != 1:
            raise ValueError(
                f"{prefix}: JA/ZH/KO source order mismatch"
            )
    for language in LANGUAGES:
        left = {
            row[0] for row in matrix[language]["R67H"]
        }
        right = {
            row[0] for row in matrix[language]["R68W"]
        }
        overlap = left & right
        if overlap:
            raise ValueError(
                f"{language}: R67/R68 source collision: "
                f"{sorted(overlap)[:5]!r}"
            )
    return report


def detect_current_overlay_profile(matrix: dict) -> str:
    matches = []
    for profile in CURRENT_PROFILE_GLOBAL_ROWS:
        try:
            validate_overlay_matrix(matrix, profile)
        except ValueError:
            continue
        matches.append(profile)
    if len(matches) != 1:
        raise ValueError(
            f"current overlay profile is ambiguous or unknown: {matches!r}"
        )
    return matches[0]


def target_overlay_profile(source_profile: str) -> str:
    if source_profile == "historical-r72-r73":
        return source_profile
    transition = load_ccb9398_overlay_transition()
    source = transition["profiles"]["source"]
    target = transition["profiles"]["target"]
    if source_profile not in {source, target}:
        raise ValueError(
            f"unsupported current overlay source profile: {source_profile!r}"
        )
    return target


def resolve_git_identity(git_ref: str) -> dict:
    commit = subprocess.check_output(
        ["git", "rev-parse", f"{git_ref}^{{commit}}"],
        cwd=ROOT,
        text=True,
    ).strip().upper()
    tree = subprocess.check_output(
        ["git", "rev-parse", f"{git_ref}^{{tree}}"],
        cwd=ROOT,
        text=True,
    ).strip().upper()
    return {"commit": commit, "tree": tree}


def capture_snapshot(output: Path, git_ref: str | None = None) -> dict:
    if git_ref is not None:
        overlay_profile = "historical-r72-r73"
        identity = resolve_git_identity(git_ref)
        expected = {
            "commit": PINNED_PARENT_COMMIT,
            "tree": PINNED_PARENT_TREE,
        }
        if identity != expected:
            raise ValueError(
                f"recovery parent identity drift: {identity!r} != {expected!r}"
            )
    else:
        overlay_profile = None
        identity = {
            "commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=ROOT,
                text=True,
            ).strip().upper(),
            "tree": subprocess.check_output(
                ["git", "rev-parse", "HEAD^{tree}"],
                cwd=ROOT,
                text=True,
            ).strip().upper(),
        }

    matrix = {}
    exact_overrides = {}
    deployed_counts = {}
    for language in LANGUAGES:
        payload = load_payload(language, git_ref)
        _key, rows = global_bucket(payload)
        matrix[language] = {
            prefix: overlay_rows(rows, prefix)
            for prefix in OVERLAY_PREFIXES
        }
        exact_rows = [
            row for row in rows
            if (
                isinstance(row, list)
                and len(row) >= 2
                and row[0] == EXACT_OVERRIDE_SOURCE
            )
        ]
        if len(exact_rows) != 1:
            raise ValueError(
                f"{language}: exact override source multiplicity drift"
            )
        if exact_rows[0][1] != EXACT_OVERRIDE_RENDERED[language]:
            raise ValueError(
                f"{language}: exact override rendering drift: "
                f"{exact_rows[0][1]!r}"
            )
        exact_overrides[language] = {
            "source": EXACT_OVERRIDE_SOURCE,
            "rendered": exact_rows[0][1],
        }
        deployed_counts[language] = len(rows)

    if overlay_profile is None:
        overlay_profile = detect_current_overlay_profile(matrix)
    overlay_report = validate_overlay_matrix(matrix, overlay_profile)
    if git_ref is not None and any(
        count != PINNED_PARENT_GLOBAL_ROWS
        for count in deployed_counts.values()
    ):
        raise ValueError(
            f"pinned parent global row count drift: {deployed_counts!r}"
        )
    if git_ref is None and any(
        count != CURRENT_PROFILE_GLOBAL_ROWS[overlay_profile]
        for count in deployed_counts.values()
    ):
        raise ValueError(
            f"current deployed global row count drift: "
            f"{deployed_counts!r}"
        )

    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "authority": "reviewed-r67-r68-deployed-carry-forward",
        "overlay_profile": overlay_profile,
        "source_identity": identity,
        "source_git_ref": git_ref,
        "global_rows_at_capture": deployed_counts,
        "overlay_report": overlay_report,
        "overlays": matrix,
        "exact_overrides": exact_overrides,
    }
    snapshot["snapshot_sha256"] = compact_sha256(snapshot)
    atomic_json_dump(output, snapshot, indent=2)
    return snapshot


def load_snapshot(path: Path) -> dict:
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    if snapshot.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported historical overlay snapshot schema")
    if (
        snapshot.get("authority")
        != "reviewed-r67-r68-deployed-carry-forward"
    ):
        raise ValueError("historical overlay authority drift")
    recorded = snapshot.get("snapshot_sha256")
    unsigned = dict(snapshot)
    unsigned.pop("snapshot_sha256", None)
    actual = compact_sha256(unsigned)
    if recorded != actual:
        raise ValueError(
            f"historical overlay snapshot digest drift: "
            f"{actual} != {recorded}"
        )
    overlay_profile = snapshot.get("overlay_profile")
    if overlay_profile not in OVERLAY_PROFILES:
        raise ValueError("historical overlay snapshot profile drift")
    overlay_report = validate_overlay_matrix(
        snapshot.get("overlays"), overlay_profile,
    )
    if snapshot.get("overlay_report") != overlay_report:
        raise ValueError("historical overlay report drift")
    captured_counts = snapshot.get("global_rows_at_capture")
    if (
        set(captured_counts or {}) != set(LANGUAGES)
        or len(set(captured_counts.values())) != 1
        or (
            overlay_profile == "historical-r72-r73"
            and not set(captured_counts.values())
            <= {PINNED_PARENT_GLOBAL_ROWS, EXPECTED_POST_R73_GLOBAL_ROWS}
        )
        or (
            overlay_profile in CURRENT_PROFILE_GLOBAL_ROWS
            and not set(captured_counts.values())
            <= ALLOWED_CURRENT_SNAPSHOT_ROWS[overlay_profile]
        )
    ):
        raise ValueError("historical overlay capture-count drift")
    if snapshot.get("source_git_ref") is not None:
        if overlay_profile != "historical-r72-r73":
            raise ValueError("recovery snapshot profile drift")
        if snapshot.get("source_identity") != {
            "commit": PINNED_PARENT_COMMIT,
            "tree": PINNED_PARENT_TREE,
        }:
            raise ValueError("recovery snapshot parent identity drift")
    elif overlay_profile not in CURRENT_PROFILE_GLOBAL_ROWS:
        raise ValueError("current snapshot profile drift")
    exact_overrides = snapshot.get("exact_overrides")
    if set(exact_overrides or {}) != set(LANGUAGES):
        raise ValueError("exact override language closure drift")
    for language in LANGUAGES:
        if exact_overrides[language] != {
            "source": EXACT_OVERRIDE_SOURCE,
            "rendered": EXACT_OVERRIDE_RENDERED[language],
        }:
            raise ValueError(
                f"{language}: exact override snapshot drift"
            )
    return snapshot


# This is the reviewed R68 insertion algorithm.  It reproduces the parent
# ordering exactly when R67 is prepended first (verified for all three
# 572,356-row parent payloads).
_BOL = chr(1)
_HAT12 = "".join(
    chr(code)
    for code in (264, 265, 284, 285, 292, 293, 308, 309, 348, 349, 364, 365)
)
_LATEXT = (
    chr(192) + "-" + chr(214)
    + chr(216) + "-" + chr(246)
    + chr(248) + "-" + chr(591)
)
_APOS = chr(39) + chr(8217)
_KEEP = (
    "A-Za-z0-9"
    + _HAT12
    + _LATEXT
    + chr(37)
    + chr(64)
    + _APOS
    + " "
    + chr(10)
    + chr(13)
    + chr(1)
)
_PAD = re.compile("([^" + _KEEP + "])")
_LTR = "A-Za-z" + _HAT12 + _LATEXT
_APOS_R = re.compile("[" + _APOS + "](?=[" + _LTR + "])")


def padkey(source: str) -> str:
    padded = _PAD.sub(
        lambda match: " " + _BOL + match.group(1) + _BOL + " ",
        source,
    )
    return _APOS_R.sub(
        lambda match: match.group(0) + _BOL + " ",
        padded,
    )


def splice_r68(base_rows: list, r68_rows: list) -> list:
    candidates = [
        (index, padkey(row[0]))
        for index, row in enumerate(base_rows)
        if (
            isinstance(row, list)
            and row
            and isinstance(row[0], str)
            and (
                " " in row[0].strip()
                or _PAD.search(row[0])
            )
        )
    ]
    groups = {}
    for row in r68_rows:
        key = padkey(row[0])
        position = 0
        for index, candidate in candidates:
            if len(candidate) > len(key) and key in candidate:
                position = max(position, index + 1)
        groups.setdefault(position, []).append(row)
    result = list(base_rows)
    for position in sorted(groups, reverse=True):
        result[position:position] = groups[position]
    return result


def restore_bucket(language: str, rows: list, snapshot: dict) -> list:
    clean = [
        row
        for row in rows
        if not (
            isinstance(row, list)
            and len(row) >= 3
            and isinstance(row[2], str)
            and any(
                f"${prefix}" in row[2]
                for prefix in OVERLAY_PREFIXES
            )
        )
    ]
    base_sources = Counter(
        row[0]
        for row in clean
        if isinstance(row, list) and row and isinstance(row[0], str)
    )
    if any(count != 1 for count in base_sources.values()):
        duplicates = sorted(
            source
            for source, count in base_sources.items()
            if count != 1
        )
        raise ValueError(
            f"{language}: duplicate base source keys: {duplicates[:5]!r}"
        )

    r67 = snapshot["overlays"][language]["R67H"]
    r68 = snapshot["overlays"][language]["R68W"]
    overlay_sources = {row[0] for row in r67 + r68}
    collisions = overlay_sources & set(base_sources)
    if collisions:
        raise ValueError(
            f"{language}: reviewed overlay/base collision: "
            f"{sorted(collisions)[:5]!r}"
        )

    exact_indexes = [
        index
        for index, row in enumerate(clean)
        if (
            isinstance(row, list)
            and len(row) >= 2
            and row[0] == EXACT_OVERRIDE_SOURCE
        )
    ]
    if len(exact_indexes) != 1:
        raise ValueError(
            f"{language}: exact override target multiplicity drift"
        )
    exact_index = exact_indexes[0]
    exact_row = list(clean[exact_index])
    exact_row[1] = EXACT_OVERRIDE_RENDERED[language]
    clean[exact_index] = exact_row

    restored = splice_r68(r67 + clean, r68)
    restored_sources = [
        row[0]
        for row in restored
        if isinstance(row, list) and row and isinstance(row[0], str)
    ]
    duplicates = [
        source
        for source, count in Counter(restored_sources).items()
        if count != 1
    ]
    if duplicates:
        raise ValueError(
            f"{language}: duplicate restored source keys: "
            f"{sorted(duplicates)[:5]!r}"
        )
    return restored


def audit_payloads(
    payloads: dict,
    expected_global_rows: int | None,
    overlay_profile: str = "current-post-temis",
) -> dict:
    matrix = {}
    counts = {}
    exact_values = {}
    for language in LANGUAGES:
        _key, rows = global_bucket(payloads[language])
        matrix[language] = {
            prefix: overlay_rows(rows, prefix)
            for prefix in OVERLAY_PREFIXES
        }
        counts[language] = len(rows)
        exact_rows = [
            row
            for row in rows
            if (
                isinstance(row, list)
                and len(row) >= 2
                and row[0] == EXACT_OVERRIDE_SOURCE
            )
        ]
        if len(exact_rows) != 1:
            raise ValueError(
                f"{language}: deployed exact override multiplicity drift"
            )
        exact_values[language] = exact_rows[0][1]
        if exact_rows[0][1] != EXACT_OVERRIDE_RENDERED[language]:
            raise ValueError(
                f"{language}: deployed exact override rendering drift"
            )
    overlay_report = validate_overlay_matrix(matrix, overlay_profile)
    if expected_global_rows is not None and any(
        count != expected_global_rows for count in counts.values()
    ):
        raise ValueError(
            f"global Ruby row count drift: {counts!r} != "
            f"{expected_global_rows}"
        )
    return {
        "gate": True,
        "languages": list(LANGUAGES),
        "global_rows": counts,
        "expected_global_rows": expected_global_rows,
        "overlay_profile": overlay_profile,
        "overlay_report": overlay_report,
        "exact_override_rendered": exact_values,
    }


def apply_snapshot(path: Path, expected_global_rows: int | None) -> dict:
    snapshot = load_snapshot(path)
    source_overlay_profile = snapshot["overlay_profile"]
    overlay_profile = target_overlay_profile(source_overlay_profile)
    payloads = {
        language: load_payload(language)
        for language in LANGUAGES
    }
    if source_overlay_profile == "current-ccb9398":
        # Current formal regeneration is authorized only for the sealed
        # one-rule U+2019 raw candidate.  Historical recovery deliberately
        # bypasses this successor-only check.
        load_dd55318_u2019_overlay_transition(payloads)
    candidates = {}
    for language in LANGUAGES:
        payload = payloads[language]
        bucket_key, rows = global_bucket(payload)
        candidate = dict(payload)
        candidate[bucket_key] = restore_bucket(
            language,
            rows,
            snapshot,
        )
        candidates[language] = candidate
    report = audit_payloads(
        candidates, expected_global_rows, overlay_profile,
    )
    report["source_overlay_profile"] = source_overlay_profile

    stages = {}
    rollbacks = {}
    replaced = []
    try:
        for language in LANGUAGES:
            destination = payload_path(language)
            stage = destination.with_name(
                destination.name + ".stage_r67_r68_overlay"
            )
            rollback = destination.with_name(
                destination.name + ".bak_preR67R68CarryForward"
            )
            atomic_json_dump(stage, candidates[language])
            stages[language] = stage
            rollbacks[language] = rollback
        for language in LANGUAGES:
            destination = payload_path(language)
            atomic_file_copy(destination, rollbacks[language])
        for language in LANGUAGES:
            os.replace(stages[language], payload_path(language))
            replaced.append(language)
        deployed = {
            language: load_payload(language)
            for language in LANGUAGES
        }
        deployed_report = audit_payloads(
            deployed, expected_global_rows, overlay_profile,
        )
        deployed_report["source_overlay_profile"] = source_overlay_profile
        if deployed_report != report:
            raise ValueError(
                "deployed overlay audit differs from staged audit"
            )
    except Exception:
        for language in reversed(replaced):
            rollback = rollbacks[language]
            if rollback.exists():
                os.replace(rollback, payload_path(language))
        raise
    finally:
        for stage in stages.values():
            if stage.exists():
                stage.unlink()
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Seal, restore, or audit the reviewed R67/R68 Ruby overlays."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    capture = subparsers.add_parser("capture")
    capture.add_argument("--output", required=True, type=Path)
    capture.add_argument(
        "--git-ref",
        help=(
            "Recovery-only source; must resolve to the pinned R72 parent."
        ),
    )

    apply = subparsers.add_parser("apply")
    apply.add_argument("--input", required=True, type=Path)
    apply.add_argument(
        "--expected-global-rows",
        type=int,
        default=CURRENT_PRE_R81_GLOBAL_ROWS,
    )

    audit = subparsers.add_parser("audit")
    audit.add_argument(
        "--expected-global-rows",
        type=int,
        default=CURRENT_DEPLOYED_GLOBAL_ROWS,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "capture":
        snapshot = capture_snapshot(args.output, args.git_ref)
        report = {
            "gate": True,
            "snapshot": str(args.output),
            "snapshot_sha256": snapshot["snapshot_sha256"],
            "source_identity": snapshot["source_identity"],
            "overlay_profile": snapshot["overlay_profile"],
            "global_rows_at_capture": snapshot["global_rows_at_capture"],
        }
    elif args.command == "apply":
        report = apply_snapshot(
            args.input,
            args.expected_global_rows,
        )
    else:
        payloads = {
            language: load_payload(language)
            for language in LANGUAGES
        }
        matrix = {}
        for language in LANGUAGES:
            _key, rows = global_bucket(payloads[language])
            matrix[language] = {
                prefix: overlay_rows(rows, prefix)
                for prefix in OVERLAY_PREFIXES
            }
        overlay_profile = detect_current_overlay_profile(matrix)
        report = audit_payloads(
            payloads, args.expected_global_rows, overlay_profile,
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(
            f"historical Ruby overlay gate failed: {error}",
            file=sys.stderr,
        )
        raise
