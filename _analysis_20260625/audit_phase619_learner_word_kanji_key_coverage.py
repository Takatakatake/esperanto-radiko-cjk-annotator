# -*- coding: utf-8 -*-
"""Audit direct Phase 619 learner-master alignment with ``word_kanji``.

This is deliberately a coverage-only, source-alignment audit.  It proves that
every *directly covered* projected learner key has the same Esperanto piece
sequence in the pinned ``word_kanji`` source.  It does not render the deployed
Kanji payload, evaluate per-root/fallback/literal paths, or classify uncovered
keys as defects.

The distinction is essential to the project's two-track policy:

* annotation Ruby remains at the reviewed coarse Kyoto-HTML level;
* Kanji may follow the learner master's fake/deep decomposition.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from atomic_json import atomic_json_dump
import build_phase619_ordinary_ruby_review as phase619_builder
import no_worsening_audit as audit
import phase619_ordinary_ruby_policy as phase619_policy


WORD_KANJI_PATH = HERE / "out" / "word_kanji.json"
GRAM = frozenset({
    "o", "a", "i", "e", "u", "n", "j", "oj", "on", "aj",
    "as", "is", "os", "us",
})
EXPECTED_WORD_KANJI = {
    "bytes": 2_442_258,
    "entries": 44_575,
    "sha256": (
        "3BA6773B07293E8FF736BD37DD03E0BB5E2A6D3A4514E0A59F5B42F23FB5F78A"
    ),
}
EXPECTED_COUNTS = {
    "input_lines": 62_313,
    "parse_evaluable_rows": 62_111,
    "parse_excluded_rows": 202,
    "empty_projection_rows": 26,
    "projectable_rows": 62_085,
    "unique_projected_keys": 52_775,
    "direct_covered_keys": 44_284,
    "direct_uncovered_keys": 8_491,
    "direct_covered_rows": 52_636,
    "direct_uncovered_rows": 9_449,
    "raw_fake_marker_lines": 3_656,
    "evaluable_fake_rows": 3_644,
    "projectable_fake_rows": 3_644,
    "direct_covered_fake_rows": 3_445,
    "direct_uncovered_fake_rows": 199,
    "covered_piece_drift": 0,
}
EXPECTED_HASHES = {
    "parse_excluded_rows": (
        "49C5D2FFC36F6B15C39F570BEFF604FD72847A7A6DB1E8B1F1E07B5E2D983F1C"
    ),
    "empty_projection_rows": (
        "4495E924740DF471168F3F2027C3A1A8F060A71E6C34CB0D6A59B5F632B68A6B"
    ),
    "projectable_rows": (
        "E7AACE9576C10D66AE6CE26FFA14A488621A2DB8A884729C2E93F19FAD71B6B2"
    ),
    "unique_projected_keys": (
        "E74C60D62531F537F9BA44EBC338A809E45C7A36CFF7B04A5F558BBC7EB9AF88"
    ),
    "direct_covered_keys": (
        "2FF11E7E8078090680057E4DD33D89ACED0077AB29F9C11041E72E5A99917B86"
    ),
    "direct_uncovered_keys": (
        "88D76DD583FB30C1003B08A5D207E506DFA103654A289A0C5744BFB43B0CC774"
    ),
    "direct_covered_rows": (
        "196B5E21C75E5E8DE8802077B7BA4D07D75B4FF0007442593A522793B9AF523F"
    ),
    "direct_uncovered_rows": (
        "CE128437F1393E38B3905DD2C7270EB087661CAB183AAE1F1EEE710394E0935E"
    ),
    "raw_fake_marker_lines": (
        "1BF13FB2E22D2FE275CF0EDE68E0FD59EE6276F3799C31111934FA4BA5AF2FBA"
    ),
    "evaluable_fake_rows": (
        "0FE3E689F498CE585E0022F85BC84E46171EC168F4585B04798AE52ACB52D7B6"
    ),
    "direct_covered_fake_rows": (
        "33A25A53797F9BED952AA22FAC507032FDA8E5DC9CDC2DF7DB8C1541640FC360"
    ),
    "direct_uncovered_fake_rows": (
        "CE007CF099BCC12EF2797C1F0B31B38AF8F469705A319CB7A72F4BE0811F517C"
    ),
}


def compact_sha256(value) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


def source_identity(path: Path, raw: bytes, *, lines=None, entries=None) -> dict:
    result = {
        "path": str(path.resolve()),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest().upper(),
    }
    if lines is not None:
        result["lines"] = lines
    if entries is not None:
        result["entries"] = entries
    return result


def project_line(line: str, line_number: int) -> tuple[dict | None, str | None]:
    """Project one learner row to the key shape used by ``word_kanji``."""
    candidate = line.lstrip("\ufeff")
    if not candidate.strip():
        return None, "blank"
    if candidate.lstrip().startswith("#"):
        return None, "comment"
    if ":" not in candidate:
        return None, "no_colon"
    decomposition = audit.canonical(
        candidate.split(":", 1)[0].strip()
    ).replace("-", "")
    pieces = [piece for piece in decomposition.split("/") if piece]
    if not pieces:
        return None, "empty_decomposition"
    full_key = "/".join(piece.lower() for piece in pieces)
    stem = list(pieces)
    while stem and stem[-1].lower() in GRAM:
        stem.pop()
    key = "/".join(piece.lower() for piece in stem)
    return {
        "line": line_number,
        "decomposition": decomposition,
        "full_key": full_key,
        "key": key,
        "fake": bool(audit.FAKE_MARKER_RE.search(candidate)),
    }, None


def _assert_identity(actual: dict, expected: dict, label: str) -> None:
    projected = {key: actual.get(key) for key in expected}
    if projected != expected:
        raise ValueError(
            f"{label} identity drift: expected={expected!r}, "
            f"actual={projected!r}"
        )


def build_report(phase619_dir: Path, word_kanji_path: Path) -> dict:
    learner_path = phase619_builder.find_bound_file(
        Path(phase619_dir),
        phase619_policy.EXPECTED_SOURCES["phase619_learner"],
    )
    learner_raw = learner_path.read_bytes()
    learner_lines = learner_raw.decode("utf-8", errors="strict").splitlines()
    learner_identity = source_identity(
        learner_path, learner_raw, lines=len(learner_lines),
    )
    _assert_identity(
        learner_identity,
        phase619_policy.EXPECTED_SOURCES["phase619_learner"],
        "Phase 619 learner",
    )

    word_kanji_path = Path(word_kanji_path).resolve()
    word_kanji_raw = word_kanji_path.read_bytes()
    word_kanji = json.loads(word_kanji_raw.decode("utf-8", errors="strict"))
    if not isinstance(word_kanji, dict):
        raise ValueError("word_kanji must be a JSON object")
    word_kanji_identity = source_identity(
        word_kanji_path, word_kanji_raw, entries=len(word_kanji),
    )
    _assert_identity(
        word_kanji_identity, EXPECTED_WORD_KANJI, "word_kanji",
    )

    excluded = []
    parsed = []
    raw_fake_lines = []
    for line_number, line in enumerate(learner_lines, 1):
        if audit.FAKE_MARKER_RE.search(line):
            raw_fake_lines.append(line_number)
        row, reason = project_line(line, line_number)
        if row is None:
            excluded.append([line_number, reason])
        else:
            parsed.append(row)

    empty_projection = [row for row in parsed if not row["key"]]
    projectable = [row for row in parsed if row["key"]]
    unique_keys = sorted({row["key"] for row in projectable})
    covered_keys = sorted(set(unique_keys) & set(word_kanji))
    uncovered_keys = sorted(set(unique_keys) - set(word_kanji))
    covered_key_set = set(covered_keys)
    covered_rows = [
        row for row in projectable if row["key"] in covered_key_set
    ]
    uncovered_rows = [
        row for row in projectable if row["key"] not in covered_key_set
    ]
    evaluable_fake_rows = [row for row in parsed if row["fake"]]
    projectable_fake_rows = [
        row for row in evaluable_fake_rows if row["key"]
    ]
    covered_fake_rows = [
        row for row in projectable_fake_rows
        if row["key"] in covered_key_set
    ]
    uncovered_fake_rows = [
        row for row in projectable_fake_rows
        if row["key"] not in covered_key_set
    ]

    piece_drift = []
    for key in covered_keys:
        pairs = word_kanji[key]
        if (
            not isinstance(pairs, list)
            or any(
                not isinstance(pair, list)
                or len(pair) != 2
                or not isinstance(pair[0], str)
                for pair in pairs
            )
        ):
            piece_drift.append({
                "key": key,
                "expected": key.split("/"),
                "actual": None,
                "reason": "invalid_word_kanji_pair_shape",
            })
            continue
        actual_pieces = [pair[0].lower() for pair in pairs]
        expected_pieces = key.split("/")
        if actual_pieces != expected_pieces:
            piece_drift.append({
                "key": key,
                "expected": expected_pieces,
                "actual": actual_pieces,
                "reason": "esperanto_piece_sequence_mismatch",
            })

    counts = {
        "input_lines": len(learner_lines),
        "parse_evaluable_rows": len(parsed),
        "parse_excluded_rows": len(excluded),
        "empty_projection_rows": len(empty_projection),
        "projectable_rows": len(projectable),
        "unique_projected_keys": len(unique_keys),
        "direct_covered_keys": len(covered_keys),
        "direct_uncovered_keys": len(uncovered_keys),
        "direct_covered_rows": len(covered_rows),
        "direct_uncovered_rows": len(uncovered_rows),
        "raw_fake_marker_lines": len(raw_fake_lines),
        "evaluable_fake_rows": len(evaluable_fake_rows),
        "projectable_fake_rows": len(projectable_fake_rows),
        "direct_covered_fake_rows": len(covered_fake_rows),
        "direct_uncovered_fake_rows": len(uncovered_fake_rows),
        "covered_piece_drift": len(piece_drift),
    }
    hashes = {
        "parse_excluded_rows": compact_sha256(excluded),
        "empty_projection_rows": compact_sha256([
            [row["line"], row["decomposition"], row["full_key"]]
            for row in empty_projection
        ]),
        "projectable_rows": compact_sha256([
            [row["line"], row["key"], row["fake"]]
            for row in projectable
        ]),
        "unique_projected_keys": compact_sha256(unique_keys),
        "direct_covered_keys": compact_sha256(covered_keys),
        "direct_uncovered_keys": compact_sha256(uncovered_keys),
        "direct_covered_rows": compact_sha256([
            [row["line"], row["key"], row["fake"]]
            for row in covered_rows
        ]),
        "direct_uncovered_rows": compact_sha256([
            [row["line"], row["key"], row["fake"]]
            for row in uncovered_rows
        ]),
        "raw_fake_marker_lines": compact_sha256(raw_fake_lines),
        "evaluable_fake_rows": compact_sha256([
            [row["line"], row["key"]] for row in evaluable_fake_rows
        ]),
        "direct_covered_fake_rows": compact_sha256([
            [row["line"], row["key"]] for row in covered_fake_rows
        ]),
        "direct_uncovered_fake_rows": compact_sha256([
            [row["line"], row["key"]] for row in uncovered_fake_rows
        ]),
    }
    if counts != EXPECTED_COUNTS:
        raise ValueError(
            "Phase 619 learner/word_kanji coverage count drift: "
            f"expected={EXPECTED_COUNTS!r}, actual={counts!r}"
        )
    if hashes != EXPECTED_HASHES:
        raise ValueError(
            "Phase 619 learner/word_kanji coverage identity drift: "
            f"expected={EXPECTED_HASHES!r}, actual={hashes!r}"
        )
    if piece_drift:
        raise ValueError(
            "covered Phase 619 learner keys disagree with word_kanji pieces: "
            f"{piece_drift[:5]!r}"
        )

    if (
        hashlib.sha256(learner_path.read_bytes()).hexdigest().upper()
        != learner_identity["sha256"]
        or hashlib.sha256(word_kanji_path.read_bytes()).hexdigest().upper()
        != word_kanji_identity["sha256"]
    ):
        raise ValueError("coverage input changed during audit")

    return {
        "schema_version": 1,
        "algorithm": "phase619-learner-word-kanji-direct-key-coverage-v1",
        "coverage_only": True,
        "direct_word_kanji_source_alignment": True,
        "full_deployed_render_fidelity_certified": False,
        "per_root_rendering_evaluated": False,
        "fallback_rendering_evaluated": False,
        "literal_rendering_evaluated": False,
        "uncovered_is_not_failure": True,
        "uncovered_keys_are_defects": False,
        "sources": {
            "phase619_learner": learner_identity,
            "word_kanji": word_kanji_identity,
        },
        "projection": {
            "terminal_grammar_pieces": sorted(GRAM),
            "hyphen_policy": "remove_before_key_projection",
            "empty_projection_policy": (
                "report_separately_and_exclude_from_coverage_denominator"
            ),
            "comment_fake_marker_policy": (
                "report_raw_and_parse-evaluable counts separately"
            ),
        },
        "counts": counts,
        "coverage_percent": {
            "unique_projected_keys": round(
                100 * len(covered_keys) / len(unique_keys), 6,
            ),
            "projectable_rows": round(
                100 * len(covered_rows) / len(projectable), 6,
            ),
            "projectable_fake_rows": round(
                100 * len(covered_fake_rows)
                / len(projectable_fake_rows),
                6,
            ),
        },
        "hashes": hashes,
        "covered_piece_drift": 0,
        "limitations": [
            (
                "Direct word_kanji key coverage is not a certification of "
                "all deployed Kanji rendering."
            ),
            (
                "Uncovered keys may render through per-root, fallback, or "
                "literal paths and are not classified as defects here."
            ),
            (
                "A separate all-tracks audit is required before absorbing "
                "a newer moving Kanji master."
            ),
        ],
        "inputs_stable": True,
        "gate": True,
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase619-dir", type=Path, required=True)
    parser.add_argument(
        "--word-kanji",
        type=Path,
        default=WORD_KANJI_PATH,
    )
    parser.add_argument("--report", type=Path)
    parser.add_argument("--check", action="store_true", required=True)
    return parser.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)
    report = build_report(
        args.phase619_dir.resolve(),
        args.word_kanji.resolve(),
    )
    if args.report:
        atomic_json_dump(args.report.resolve(), report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
