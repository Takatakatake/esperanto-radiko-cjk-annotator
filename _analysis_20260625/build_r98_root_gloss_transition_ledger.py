# -*- coding: utf-8 -*-
"""Build and verify the exact R95/R96/R98 Ruby-gloss transition ledger.

The three upstream rounds changed a reviewed set of Ruby glosses after the
R94 full regeneration had already started.  This builder derives authority
from the two pinned app commits themselves.  It authorizes only the exact
language/list/source-key/Ruby-segment tuples that actually changed; it never
turns a root name into a wildcard replacement rule.

Without ``--write`` this is a dry run.  ``--check`` additionally requires the
tracked ledger to be byte-identical to the derivation and to its reviewed
SHA-256 seal.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from atomic_json import atomic_json_dump


PREDECESSOR_COMMIT = "6a707dd8da4be04da8dba0968b8de9255411af76"
TARGET_COMMIT = "cfa1fcb6870ee6d2a6af314c5014bdcb14b4aff9"
LEDGER_PATH = HERE / "_r98_root_gloss_transition_ledger.json"
# Filled only after the generated ledger has been reviewed byte-for-byte.
EXPECTED_LEDGER_SHA256 = (
    "43255301C1439258383A65BB4A648BE4103FA1F8B24E35518B79AD90A6313B11"
)

LANGUAGES = ("JA", "ZH", "KO")
PAYLOAD_NAME = "置換リスト_ルビ.json"
LISTS = {
    "GL": "局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)",
    "G2": "二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)",
    "GG": "全域替换用のリスト(列表)型配列(replacements_final_list)",
}
LIST_ORDER = {code: index for index, code in enumerate(LISTS)}
RUBY = re.compile(r"<ruby>(.*?)<rt([^>]*)>(.*?)</rt></ruby>", re.S)
TAG = re.compile(r"<[^>]+>")
BR = re.compile(r"<br\s*/?>", re.I)

PHASE_ROOTS = {
    "R95": {
        "anarki", "arm", "fleksi", "kiom", "legi", "likvid", "loĝi",
        "orient", "pneŭmatik", "poezi", "sensaci", "sugesti", "teren",
    },
    "R96": {
        "administraci", "facet", "harmoni", "narkotik", "prunel", "roman",
    },
    "R98": {
        "absorb", "asociaci", "ekspon", "filozof", "firma", "instanc",
        "instituci", "kirurg", "konvert", "kvot", "lir", "meti", "metro",
        "pilot", "radikal", "skolt", "solv", "viktim",
    },
}
EXPECTED_ROOTS = set().union(*PHASE_ROOTS.values())
EXPECTED_CHANGED_ROWS = {"JA": 1874, "ZH": 1218, "KO": 1497}


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def payload_relative_path(language: str) -> str:
    return f"Esperanto-Kanji-Ruby-{language}/app_data/{PAYLOAD_NAME}"


def git_blob(commit: str, relative_path: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{commit}:{relative_path}"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(
            f"git show failed for {commit}:{relative_path}: "
            f"{result.stderr.decode('utf-8', errors='replace')}"
        )
    return result.stdout


def load_payload(commit: str, language: str) -> tuple[dict, bytes]:
    raw = git_blob(commit, payload_relative_path(language))
    return json.loads(raw.decode("utf-8")), raw


def clean_base(value: str) -> str:
    return TAG.sub("", value)


def clean_gloss(value: str) -> str:
    return BR.sub("", TAG.sub("", value))


def ruby_segments(value: str) -> list[dict]:
    return [
        {
            "base": clean_base(match.group(1)),
            "gloss": clean_gloss(match.group(3)),
            "raw": match.group(0),
        }
        for match in RUBY.finditer(value)
    ]


def ruby_skeleton(value: str) -> str:
    return RUBY.sub(
        lambda match: f"<ruby>{match.group(1)}<rt></rt></ruby>",
        value,
    )


def compact_ledger_bytes(value: dict) -> bytes:
    return json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")


def phase_for(root: str) -> str:
    matches = [phase for phase, roots in PHASE_ROOTS.items() if root in roots]
    if len(matches) != 1:
        raise AssertionError(f"root phase is not unique: {root!r} -> {matches}")
    return matches[0]


def derive() -> dict:
    grouped: dict[str, dict[str, dict[tuple[str, str], list[dict]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    payload_fingerprints: dict[str, dict[str, str]] = {}
    changed_rows: dict[str, int] = {}
    changed_segments: dict[str, int] = {}

    for language in LANGUAGES:
        before, before_raw = load_payload(PREDECESSOR_COMMIT, language)
        after, after_raw = load_payload(TARGET_COMMIT, language)
        if set(before) != set(after):
            raise AssertionError(f"{language}: payload top-level keys changed")
        for key in before:
            if key not in LISTS.values() and before[key] != after[key]:
                raise AssertionError(
                    f"{language}: non-replacement payload field changed: {key!r}"
                )

        row_changes = 0
        segment_changes = 0
        for code, list_name in LISTS.items():
            old_rows = before[list_name]
            new_rows = after[list_name]
            if len(old_rows) != len(new_rows):
                raise AssertionError(
                    f"{language}/{code}: row count changed "
                    f"{len(old_rows)} -> {len(new_rows)}"
                )
            source_counts = Counter(
                row[0] for row in old_rows
                if isinstance(row, list) and row and isinstance(row[0], str)
            )
            for row_index, (old_row, new_row) in enumerate(zip(old_rows, new_rows)):
                if old_row == new_row:
                    continue
                row_changes += 1
                if not (
                    isinstance(old_row, list)
                    and isinstance(new_row, list)
                    and len(old_row) >= 2
                    and len(new_row) == len(old_row)
                    and isinstance(old_row[0], str)
                    and isinstance(old_row[1], str)
                    and isinstance(new_row[1], str)
                ):
                    raise AssertionError(
                        f"{language}/{code}/{row_index}: changed row schema"
                    )
                if old_row[0] != new_row[0] or old_row[2:] != new_row[2:]:
                    raise AssertionError(
                        f"{language}/{code}/{row_index}: key/placeholder/tail changed"
                    )
                if source_counts[old_row[0]] != 1:
                    raise AssertionError(
                        f"{language}/{code}: targeted key is not unique: {old_row[0]!r}"
                    )
                if ruby_skeleton(old_row[1]) != ruby_skeleton(new_row[1]):
                    raise AssertionError(
                        f"{language}/{code}/{old_row[0]!r}: non-rt structure changed"
                    )
                old_segments = ruby_segments(old_row[1])
                new_segments = ruby_segments(new_row[1])
                if not old_segments or len(old_segments) != len(new_segments):
                    raise AssertionError(
                        f"{language}/{code}/{old_row[0]!r}: Ruby count changed"
                    )
                if [item["base"] for item in old_segments] != [
                    item["base"] for item in new_segments
                ]:
                    raise AssertionError(
                        f"{language}/{code}/{old_row[0]!r}: Ruby boundary changed"
                    )
                changed_here = 0
                for segment_index, (old_segment, new_segment) in enumerate(
                    zip(old_segments, new_segments)
                ):
                    if old_segment["gloss"] == new_segment["gloss"]:
                        if old_segment["raw"] != new_segment["raw"]:
                            raise AssertionError(
                                f"{language}/{code}/{old_row[0]!r}: "
                                f"untargeted Ruby class changed at segment {segment_index}"
                            )
                        continue
                    root = old_segment["base"].lower()
                    if root not in EXPECTED_ROOTS:
                        raise AssertionError(
                            f"{language}/{code}/{old_row[0]!r}: "
                            f"unexpected changed root {root!r}"
                        )
                    grouped[root][language][(code, old_row[0])].append({
                        "index": segment_index,
                        "before": old_segment["gloss"],
                        "after": new_segment["gloss"],
                        "before_rendered": old_segment["raw"],
                        "after_rendered": new_segment["raw"],
                    })
                    changed_here += 1
                    segment_changes += 1
                if not changed_here:
                    raise AssertionError(
                        f"{language}/{code}/{old_row[0]!r}: "
                        "raw row changed without a gloss transition"
                    )

        changed_rows[language] = row_changes
        changed_segments[language] = segment_changes
        payload_fingerprints[language] = {
            "predecessor_sha256": sha256(before_raw),
            "target_sha256": sha256(after_raw),
        }

    if changed_rows != EXPECTED_CHANGED_ROWS:
        raise AssertionError(
            f"changed-row count drift: {changed_rows!r} != {EXPECTED_CHANGED_ROWS!r}"
        )
    if set(grouped) != EXPECTED_ROOTS:
        raise AssertionError(
            "changed-root set drift: "
            f"missing={sorted(EXPECTED_ROOTS - set(grouped))!r} "
            f"extra={sorted(set(grouped) - EXPECTED_ROOTS)!r}"
        )

    confirmed = []
    for root in sorted(grouped):
        transitions = {}
        gloss_summary = {}
        for language in LANGUAGES:
            rows = []
            old_values = set()
            new_values = set()
            for (code, key), segments in sorted(
                grouped[root][language].items(),
                key=lambda item: (LIST_ORDER[item[0][0]], item[0][1]),
            ):
                segments = sorted(segments, key=lambda item: item["index"])
                rows.append({"list": code, "key": key, "segments": segments})
                old_values.update(item["before"] for item in segments)
                new_values.update(item["after"] for item in segments)
            transitions[language] = rows
            gloss_summary[language] = {
                "before": sorted(old_values),
                "after": sorted(new_values),
                "rows": len(rows),
                "segments": sum(len(row["segments"]) for row in rows),
            }
        confirmed.append({
            "root": root,
            "phase": phase_for(root),
            "source": (
                f"Pinned {PREDECESSOR_COMMIT[:7]}→{TARGET_COMMIT[:7]} "
                "reviewed R95/R96/R98 deployed Ruby transition"
            ),
            "gloss_summary": gloss_summary,
            "transitions": transitions,
        })

    return {
        "schema_version": 1,
        "ledger_id": "r95-r96-r98-root-gloss-exact-transition-v1",
        "description": (
            "Exact reviewed Ruby-gloss transitions imported after the R94 "
            "frozen full regeneration; boundaries, keys, placeholders and "
            "Kanji artifacts are outside this authorization."
        ),
        "authority": {
            "predecessor_commit": PREDECESSOR_COMMIT,
            "target_commit": TARGET_COMMIT,
            "payload_fingerprints": payload_fingerprints,
        },
        "summary": {
            "roots": len(confirmed),
            "roots_by_phase": {
                phase: len(roots) for phase, roots in PHASE_ROOTS.items()
            },
            "changed_rows": changed_rows,
            "changed_segments": changed_segments,
        },
        "policy": {
            "ruby_only": True,
            "gloss_and_size_class_only": True,
            "source_key_must_remain_exact": True,
            "list_bucket_must_remain_exact": True,
            "ruby_segment_index_must_remain_exact": True,
            "before_value_must_match_or_after_value_must_already_hold": True,
            "wildcard_or_substring_authorization": False,
            "boundary_change_authorized": False,
            "placeholder_change_authorized": False,
            "kanji_change_authorized": False,
            "learner_master_change_authorized": False,
            "corpus_change_authorized": False,
        },
        "confirmed": confirmed,
    }


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=LEDGER_PATH)
    args = parser.parse_args(argv)

    ledger = derive()
    raw = compact_ledger_bytes(ledger)
    digest = sha256(raw)
    if args.write:
        if args.output.exists():
            raise FileExistsError(
                f"refusing to overwrite transition ledger: {args.output}"
            )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        atomic_json_dump(args.output, ledger, indent=2)
        if args.output.read_bytes() != raw:
            raise IOError("atomic ledger serialization differs from derivation")
    if args.check:
        if not args.output.is_file():
            raise FileNotFoundError(args.output)
        observed = args.output.read_bytes()
        if observed != raw:
            raise AssertionError("tracked ledger differs from pinned derivation")
        if not EXPECTED_LEDGER_SHA256:
            raise AssertionError("EXPECTED_LEDGER_SHA256 is not sealed")
        if sha256(observed) != EXPECTED_LEDGER_SHA256:
            raise AssertionError("tracked ledger SHA-256 differs from reviewed seal")
    print(json.dumps({
        "ledger_id": ledger["ledger_id"],
        "roots": ledger["summary"]["roots"],
        "changed_rows": ledger["summary"]["changed_rows"],
        "changed_segments": ledger["summary"]["changed_segments"],
        "ledger_bytes": len(raw),
        "ledger_sha256": digest,
        "written": bool(args.write),
        "checked": bool(args.check),
        "seal_instruction": (
            "Review this ledger and set EXPECTED_LEDGER_SHA256 to " + digest
        ),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
