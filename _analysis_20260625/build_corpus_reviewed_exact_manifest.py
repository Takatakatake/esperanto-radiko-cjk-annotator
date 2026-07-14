# -*- coding: utf-8 -*-
"""Build typed exact rules for reviewed evaluable corpus residuals.

The ordinary Esperanto generator remains authoritative for productive roots,
affixes and inflections.  After those rules have been exercised against the
full Kyoto corpus, the remaining case-sensitive proper names, foreign words,
abbreviations and document-specific spellings are passed here as an audit
report.  Each selected surface is re-read from the clean corpus checkout; the
builder pins every ruby/literal span and its context-localized annotation.

Usage::

    python build_corpus_reviewed_exact_manifest.py --write --report REPORT.json
    python build_corpus_reviewed_exact_manifest.py --refresh-source
    python build_corpus_reviewed_exact_manifest.py --check

``ESP_CORPUS_PATH`` must point at the reviewed clean Kyoto HTML repository.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import html as htmllib
import json
import os
from pathlib import Path
import re
import unicodedata

from atomic_json import atomic_json_dump
import build_corpus_exact_manifest as extended
import no_worsening_audit as audit


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUTPUT = HERE / "_corpus_reviewed_exact_app_manifest.json"
MARKER_RE = re.compile(r"(\x01\d+\x01)")


def require_source_only_refresh(current: dict, refreshed: dict) -> None:
    """Permit a corpus re-pin only when all reviewed rules are unchanged.

    A small reviewed corpus edit can legitimately change the clean repository
    identity without changing any of the selected residual surfaces.  Reusing
    the original residual-report authority is safe only when rebuilding from
    the new corpus produces byte-for-byte equivalent counts, exact rules and
    annotations.  This guard makes that condition explicit and fail-closed.
    """
    if current.get("schema_version") != 1:
        raise ValueError("unsupported reviewed exact manifest schema")
    if current.get("source", {}).get("report") != refreshed.get("source", {}).get(
        "report"
    ):
        raise ValueError("reviewed residual report authority changed during refresh")
    current_rules = {key: value for key, value in current.items() if key != "source"}
    refreshed_rules = {
        key: value for key, value in refreshed.items() if key != "source"
    }
    if current_rules != refreshed_rules:
        raise ValueError(
            "reviewed rules changed; a new residual report and full review are required"
        )


def normalize_rich(parts):
    """Match :func:`audit.signature_from_typed_parts`, retaining ruby rt."""
    normalized = []
    for raw_piece, is_ruby, gloss in parts:
        piece = audit.clean_piece(raw_piece)
        if not piece:
            continue
        if normalized and not is_ruby and not normalized[-1][1]:
            normalized[-1] = (normalized[-1][0] + piece, False, None)
        else:
            normalized.append((piece, bool(is_ruby), gloss))
    return normalized


def parse_corpus_words_rich(text: str):
    """Yield ``surface, [(piece, is_ruby, rt)]`` with audit-identical tokens."""
    body_match = re.search(r"<body\b", text, re.IGNORECASE)
    if body_match:
        text = text[body_match.start():]
    records = []

    def replace_ruby(match):
        rb = extended.clean_rb(match.group("rb"))
        rt_match = extended.RT_RE.search(match.group(0))
        if rt_match is None:
            raise ValueError(f"ruby lacks rt: {match.group(0)[:120]!r}")
        gloss = extended.clean_rt(rt_match.group("rt"))
        if not rb or not gloss:
            raise ValueError("ruby rb/rt must not be empty")
        index = len(records)
        records.append((rb, gloss))
        return f"\x01{index}\x01"

    text = audit.RUBY_RE.sub(replace_ruby, text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = htmllib.unescape(text)
    chunks = MARKER_RE.split(text)
    surface_parts = []
    pieces = []
    has_ruby = False
    for chunk in chunks:
        marker = re.fullmatch(r"\x01(\d+)\x01", chunk)
        if marker:
            rb, gloss = records[int(marker.group(1))]
            surface_parts.append(rb)
            pieces.append((rb, True, gloss))
            has_ruby = True
            continue
        token_chars = []
        for character in chunk:
            if (
                audit.is_latin_word_character(character)
                and (
                    not unicodedata.category(character).startswith("M")
                    or bool(token_chars)
                )
            ):
                token_chars.append(character)
                continue
            if token_chars:
                token = "".join(token_chars)
                surface_parts.append(token)
                pieces.append((token, False, None))
                token_chars = []
            if surface_parts and has_ruby:
                surface = "".join(surface_parts)
                if surface.strip():
                    yield surface, normalize_rich(pieces)
            surface_parts = []
            pieces = []
            has_ruby = False
        if token_chars:
            token = "".join(token_chars)
            surface_parts.append(token)
            pieces.append((token, False, None))
    if surface_parts and has_ruby:
        surface = "".join(surface_parts)
        if surface.strip():
            yield surface, normalize_rich(pieces)


def target_from_spans(spans) -> str:
    pieces = []
    for text, _is_ruby in spans:
        if "/" in text:
            raise ValueError(f"slash cannot be encoded in exact target: {text!r}")
        pieces.append(text)
    return "/".join(pieces)


def load_report(path: Path, corpus_sha256: str):
    report_bytes = path.read_bytes()
    report = json.loads(report_bytes.decode("utf-8"))
    if report.get("schema_version") != 1:
        raise ValueError("unsupported residual report schema")
    if report.get("clone_content_sha256") != corpus_sha256:
        raise ValueError("residual report was rendered against another corpus snapshot")
    rows = report.get("residuals")
    if not isinstance(rows, list):
        raise ValueError("residual report rows must be a list")
    selected = {}
    for row in rows:
        surface = audit.canonical(row.get("surface", ""))
        expected = row.get("expected")
        if not surface or not isinstance(expected, list) or not expected:
            raise ValueError(f"invalid residual row: {row!r}")
        if not audit.evaluable(surface):
            raise ValueError(f"reviewed residual must be app-evaluable: {surface!r}")
        if surface in selected:
            raise ValueError(f"duplicate residual surface: {surface!r}")
        selected[surface] = set(expected)
    if report.get("temp_mismatch") != len(selected):
        raise ValueError(
            f"residual count drift: header={report.get('temp_mismatch')} "
            f"rows={len(selected)}"
        )
    return selected, {
        "filename": path.name,
        "sha256": hashlib.sha256(report_bytes).hexdigest().upper(),
        "schema_version": report["schema_version"],
        "surface_count": report.get("surface_count"),
        "temp_mismatch": report.get("temp_mismatch"),
    }


def select_compatible_signature(surface, observed_cases, expected_options):
    """Select the one corpus signature that a surface-wide exact rule can encode.

    One bounded exact rule necessarily produces the same typed signature at
    every occurrence of ``surface``.  Silently choosing the most frequent of
    several compatible signatures would therefore overwrite a legitimate
    context-specific minority analysis.  The residual report must narrow the
    choice to exactly one signature before this builder may emit a rule.
    """
    compatible = []
    for signature, count in observed_cases.items():
        typed = audit.display_typed_parts(list(signature[1]))
        if typed in expected_options:
            compatible.append((signature, count, typed))
    if not compatible:
        observed = sorted(
            audit.display_typed_parts(list(signature[1]))
            for signature in observed_cases
        )
        raise ValueError(
            f"report/corpus signature mismatch for {surface!r}: "
            f"expected={sorted(expected_options)}, observed={observed}"
        )
    if len(compatible) != 1:
        raise ValueError(
            f"surface-wide reviewed exact rule is ambiguous for {surface!r}: "
            f"compatible={sorted(typed for _signature, _count, typed in compatible)}; "
            "review the contexts and retain exactly one signature"
        )
    return compatible[0]


def build(corpus_root: Path, selected, report_meta=None) -> dict:
    repo_state = audit.git_repo_state(corpus_root)
    if repo_state["status_entries"]:
        raise ValueError("reviewed exact manifest requires a clean corpus checkout")
    fingerprint = audit.corpus_content_fingerprint(corpus_root)

    cases = collections.defaultdict(collections.Counter)
    rich_occurrences = collections.defaultdict(list)
    paths_by_case = collections.defaultdict(collections.Counter)
    raw_ruby = parsed_ruby = parsed_units = rich_units = 0
    files = 0
    for content_dir in audit.CONTENT_DIRS:
        for path in sorted((corpus_root / content_dir).rglob("*")):
            if not path.is_file() or path.suffix.lower() not in {".html", ".htm"}:
                continue
            files += 1
            relative = path.relative_to(corpus_root).as_posix()
            text = path.read_text(encoding="utf-8", errors="strict")
            raw_ruby += len(audit.RAW_RUBY_OPEN_RE.findall(text))
            parsed_ruby += len(audit.RUBY_RE.findall(text))
            ordinary_rows = list(audit.parse_corpus_words(text))
            rich_rows = list(parse_corpus_words_rich(text))
            parsed_units += len(ordinary_rows)
            rich_units += len(rich_rows)
            ordinary_projection = [
                (audit.canonical(surface), audit.signature_from_typed_parts(parts))
                for surface, parts in ordinary_rows
            ]
            rich_projection = []
            for surface, parts in rich_rows:
                canonical_surface = audit.canonical(surface)
                signature = audit.signature_from_typed_parts(
                    [(piece, is_ruby) for piece, is_ruby, _gloss in parts]
                )
                rich_projection.append((canonical_surface, signature))
            if ordinary_projection != rich_projection:
                raise ValueError(f"rich parser drift: {relative}")
            for (surface, signature), (_same_surface, rich_parts) in zip(
                ordinary_projection, rich_rows,
            ):
                if surface not in selected:
                    continue
                cases[surface][signature] += 1
                paths_by_case[(surface, signature)][relative] += 1
                rich_occurrences[(surface, signature)].append((relative, rich_parts))

    if files != audit.EXPECTED_CONTENT_FILES or fingerprint["files"] != files:
        raise ValueError(f"HTML scope changed: {files}")
    if raw_ruby != parsed_ruby or parsed_units != rich_units:
        raise ValueError("corpus parser coverage mismatch")
    missing = sorted(set(selected) - set(cases))
    if missing:
        raise ValueError(f"selected surfaces absent from corpus: {missing}")

    exact_surfaces = []
    annotations = {}
    for surface in sorted(selected):
        signature, count, typed = select_compatible_signature(
            surface, cases[surface], selected[surface]
        )
        spans = list(signature[1])
        roles = "".join("R" if is_ruby else "L" for _piece, is_ruby in spans)
        annotation_keys = {}
        occurrences = rich_occurrences[(surface, signature)]
        for index, (piece, is_ruby) in enumerate(spans):
            if not is_ruby:
                continue
            by_language = collections.defaultdict(collections.Counter)
            for relative, rich_parts in occurrences:
                observed_piece, observed_ruby, gloss = rich_parts[index]
                if observed_piece != piece or not observed_ruby or not gloss:
                    raise ValueError(f"rich annotation drift: {surface!r}[{index}]")
                language = extended.source_language(relative, gloss)
                by_language[language][gloss] += 1
            ja = extended.select_gloss(by_language.get("ja", collections.Counter()))
            ko = extended.select_gloss(by_language.get("ko", collections.Counter()))
            if ja is None or ja == piece:
                ja = f"[語]{piece}"
            key = f"@typed:{surface}:{index}"
            if key in annotations:
                raise ValueError(f"duplicate context annotation key: {key}")
            annotations[key] = {
                "piece": piece,
                "glosses": {
                    "ja": ja,
                    "zh": extended.fallback_gloss(piece, ja, "zh"),
                    "ko": (
                        ko if ko and ko != piece
                        else extended.fallback_gloss(piece, ja, "ko")
                    ),
                },
                "variants": {
                    language: [
                        {"gloss": gloss, "count": variant_count}
                        for gloss, variant_count in sorted(values.items())
                    ]
                    for language, values in sorted(by_language.items())
                },
            }
            annotation_keys[str(index)] = key
        exact_surfaces.append({
            "surface": surface,
            "target": target_from_spans(spans),
            "typed_roles": roles,
            "signature": audit.signature_payload(signature),
            "typed": typed,
            "count": count,
            "available_expected_options": sorted(selected[surface]),
            "annotation_keys": annotation_keys,
            "paths": [
                {"path": relative, "count": path_count}
                for relative, path_count in sorted(
                    paths_by_case[(surface, signature)].items()
                )
            ],
        })

    return {
        "schema_version": 1,
        "description": (
            "Pinned case-sensitive typed exact app rules for reviewed "
            "evaluable residuals after productive morphology."
        ),
        "source": {
            **repo_state,
            "content_files": fingerprint["files"],
            "content_sha256": fingerprint["sha256"],
            "raw_ruby": raw_ruby,
            "parsed_ruby": parsed_ruby,
            "parsed_units": parsed_units,
            "report": report_meta,
        },
        "counts": {
            "exact_surfaces": len(exact_surfaces),
            "exact_instances": sum(row["count"] for row in exact_surfaces),
            "ruby_context_annotations": len(annotations),
        },
        "exact_surfaces": exact_surfaces,
        "annotations": annotations,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--refresh-source", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    corpus_root = Path(os.environ.get(
        "ESP_CORPUS_PATH",
        ROOT / "_project_root_misc" / "京大エス研html文書＿Github",
    ))
    fingerprint = audit.corpus_content_fingerprint(corpus_root)
    if args.write:
        if args.report is None:
            raise SystemExit("--write requires --report")
        selected, report_meta = load_report(args.report, fingerprint["sha256"])
        payload = build(corpus_root, selected, report_meta)
        atomic_json_dump(OUTPUT, payload, indent=1)
    elif args.refresh_source:
        if args.report is not None:
            raise SystemExit("--refresh-source does not accept --report")
        if not OUTPUT.exists():
            raise SystemExit("reviewed corpus exact manifest is missing")
        current = json.loads(OUTPUT.read_text(encoding="utf-8"))
        selected = {
            row["surface"]: set(row["available_expected_options"])
            for row in current.get("exact_surfaces", [])
        }
        payload = build(corpus_root, selected, current.get("source", {}).get("report"))
        require_source_only_refresh(current, payload)
        atomic_json_dump(OUTPUT, payload, indent=1)
    else:
        if args.report is not None:
            raise SystemExit("--check does not accept --report")
        if not OUTPUT.exists():
            raise SystemExit(
                "reviewed corpus exact manifest is missing; build it with "
                "--write --report REPORT.json"
            )
        current = json.loads(OUTPUT.read_text(encoding="utf-8"))
        if current.get("schema_version") != 1:
            raise SystemExit("unsupported reviewed exact manifest schema")
        selected = {
            row["surface"]: set(row["available_expected_options"])
            for row in current.get("exact_surfaces", [])
        }
        payload = build(corpus_root, selected, current["source"].get("report"))
        if current != payload:
            raise SystemExit("reviewed corpus exact manifest is stale")
    print(json.dumps({
        "output": str(OUTPUT),
        "mode": (
            "write" if args.write else
            ("refresh-source" if args.refresh_source else "check")
        ),
        **payload["counts"],
        "corpus_head": payload["source"]["head_oid"],
        "content_sha256": payload["source"]["content_sha256"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
