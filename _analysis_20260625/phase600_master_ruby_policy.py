#!/usr/bin/env python3
"""Closed Phase-600 Ruby repair policy for four fixed-master findings.

The policy is deliberately independent of the Phase-599 implementation so
that the Temis promotion can recognize, validate, temporarily remove, and
restore this later layer without a circular import.

Managed rows:

* one atomic lowercase ``glu-glu-glu`` annotation whose gloss describes the
  turkey call instead of reusing generic ``glu=glue``;
* one lowercase ``nor`` annotation (the dictionary prefix head), preceded by
  two exact guards for the deployed lowercase ``kuku-nor``/``lob-nor`` forms;
* 48 exact ``nor-adrenalin``/``nor-epinefrin`` inflected and case variants.

The 48 compound sources intentionally duplicate historical R68 sources.  A
Phase-600 row is therefore identified only by its dedicated placeholder,
never by source text.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ("JA", "ZH", "KO")
PHASE = 600
GLOBAL_BUCKET_TOKEN = "replacements_final_list"
LOCAL_BUCKET_TOKEN = "replacements_list_for_localized_string"
TWO_CHAR_BUCKET_TOKEN = "replacements_list_for_2char"
MANAGED_PLACEHOLDER_PREFIX = "$600600600"
PHASE599_PLACEHOLDER_PREFIX = "$599599599"
PHASE599_ROWS = 5
MANAGED_ROWS = 52
NORMALIZED_GLOBAL_ROWS = 572_506
PROMOTED_GLOBAL_ROWS = 572_558

LANGUAGE_DIGIT = {"JA": "1", "ZH": "2", "KO": "3"}
GLU_GLOSS = {
    "JA": "七面鳥の鳴き声",
    "ZH": "火鸡叫声",
    "KO": "칠면조 울음소리",
}
NOR_GLOSS = {
    "JA": "ノル",
    "ZH": "降碳",
    "KO": "노르",
}
NOR_RENDERED = {
    "JA": '<ruby>nor<rt class="L_L">ノル</rt></ruby>',
    "ZH": '<ruby>nor<rt class="L_L">降碳</rt></ruby>',
    "KO": '<ruby>nor<rt class="XL_L">노르</rt></ruby>',
}
GLU_RENDERED = {
    language: (
        '<ruby>glu-glu-glu<rt class="XXL_L">'
        + GLU_GLOSS[language]
        + "</rt></ruby>"
    )
    for language in LANGUAGES
}
STEMS = ("nor-adrenalin", "nor-epinefrin")
ENDINGS = ("o", "on", "oj", "ojn", "a", "aj", "an", "ajn")
CASE_MODES = ("lower", "capitalized", "upper")
NOR_SUFFIX_GUARD_ROOTS = ("kuku", "lob")


def compact_sha256(value) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


def _bucket_key(payload: dict, token: str) -> str:
    matches = [
        key for key, rows in payload.items()
        if token in key and isinstance(rows, list)
    ]
    if len(matches) != 1:
        raise ValueError(f"Phase 600 payload bucket drift for {token!r}")
    return matches[0]


def rule_keys(payload: dict) -> tuple[str, str, str]:
    return (
        _bucket_key(payload, LOCAL_BUCKET_TOKEN),
        _bucket_key(payload, GLOBAL_BUCKET_TOKEN),
        _bucket_key(payload, TWO_CHAR_BUCKET_TOKEN),
    )


def _case_form(value: str, mode: str) -> str:
    if mode == "lower":
        return value
    if mode == "capitalized":
        return value[0].upper() + value[1:]
    if mode == "upper":
        return value.upper()
    raise ValueError(f"unsupported Phase 600 case mode: {mode!r}")


def compound_surfaces() -> tuple[str, ...]:
    rows = []
    for stem in STEMS:
        for mode in CASE_MODES:
            cased_stem = _case_form(stem, mode)
            for ending in ENDINGS:
                rows.append(
                    cased_stem
                    + (ending.upper() if mode == "upper" else ending)
                )
    if len(rows) != 48 or len(set(rows)) != 48:
        raise ValueError("Phase 600 compound surface closure drift")
    return tuple(rows)


def managed_sources() -> tuple[str, ...]:
    return (
        " glu-glu-glu ",
        *(f" {root}-nor " for root in NOR_SUFFIX_GUARD_ROOTS),
        " nor ",
        *(f" {surface} " for surface in compound_surfaces()),
    )


def positive_surfaces() -> tuple[str, ...]:
    return ("glu-glu-glu", "nor", *compound_surfaces())


def negative_surfaces() -> tuple[str, ...]:
    return (
        "Glu-glu-glu",
        "GLU-GLU-GLU",
        "glu",
        "glui",
        "Nor",
        "NOR",
        "nor-",
        "kuku-nor",
        "lob-nor",
        "Lob-Noro",
        "Kuku-Noro",
        "nordo",
        "norno",
        "honoro",
        "sonoro",
        "norio",
        "norito",
        "Noriko",
        "noradrenalino",
        "norepinefrino",
        "nor-X",
    )


def _placeholder(language: str, index: int) -> str:
    return (
        f" {MANAGED_PLACEHOLDER_PREFIX}"
        f"{LANGUAGE_DIGIT[language]}{index:02d}$ "
    )


def is_managed_row(row) -> bool:
    return (
        isinstance(row, (list, tuple))
        and len(row) >= 3
        and isinstance(row[2], str)
        and MANAGED_PLACEHOLDER_PREFIX in row[2]
    )


def is_phase599_row(row) -> bool:
    return (
        isinstance(row, (list, tuple))
        and len(row) >= 3
        and isinstance(row[2], str)
        and PHASE599_PLACEHOLDER_PREFIX in row[2]
    )


def _unique_row(rows: list, predicate, label: str) -> list[str]:
    matches = [row for row in rows if predicate(row)]
    if len(matches) != 1:
        raise ValueError(f"Phase 600 {label} multiplicity drift")
    row = matches[0]
    if (
        not isinstance(row, list)
        or len(row) != 3
        or not all(isinstance(value, str) for value in row)
    ):
        raise ValueError(f"Phase 600 malformed {label} row")
    return row


def _localized_render(payload: dict, source: str, language: str) -> str:
    local_key, _global_key, _two_char_key = rule_keys(payload)
    row = _unique_row(
        payload[local_key],
        lambda candidate: (
            isinstance(candidate, list)
            and candidate
            and candidate[0] == source
        ),
        f"{language} localized {source!r}",
    )
    if source == "nor":
        expected = NOR_RENDERED[language]
    else:
        expected = None
    if expected is not None and row[1] != expected:
        raise ValueError(
            f"Phase 600 {language} localized {source!r} rendering drift"
        )
    return row[1]


def _global_render(payload: dict, source: str, language: str) -> str:
    _local_key, global_key, _two_char_key = rule_keys(payload)
    row = _unique_row(
        payload[global_key],
        lambda candidate: (
            isinstance(candidate, list)
            and candidate
            and candidate[0] == source
        ),
        f"{language} global {source!r}",
    )
    if "<ruby>" not in row[1] or f">{source}<rt " not in row[1]:
        raise ValueError(
            f"Phase 600 {language} global {source!r} rendering drift"
        )
    return row[1]


def _r68_compound_rows(payload: dict, language: str) -> dict[str, list[str]]:
    _local_key, global_key, _two_char_key = rule_keys(payload)
    targets = {
        f" {surface} " for surface in compound_surfaces()
    }
    found = {}
    for row in payload[global_key]:
        if (
            isinstance(row, list)
            and len(row) == 3
            and row[0] in targets
            and isinstance(row[2], str)
            and "$R68W" in row[2]
        ):
            if row[0] in found:
                raise ValueError(
                    f"Phase 600 {language} duplicate historical R68 source"
                )
            found[row[0]] = row
    if set(found) != targets:
        missing = sorted(targets - set(found))
        extra = sorted(set(found) - targets)
        raise ValueError(
            f"Phase 600 {language} historical R68 closure drift: "
            f"missing={missing[:3]!r}, extra={extra[:3]!r}"
        )
    return found


def _cased_nor_render(payload: dict, surface: str, language: str) -> str:
    prefix = surface.split("-", 1)[0]
    return _localized_render(payload, prefix, language)


def build_expected_rows(payload: dict, language: str) -> list[list[str]]:
    """Build the exact 52-row layer from sealed deployed ingredients."""
    if language not in LANGUAGES:
        raise ValueError(f"unsupported Phase 600 language: {language!r}")
    historical = _r68_compound_rows(payload, language)
    rows = [
        [
            " glu-glu-glu ",
            f" {GLU_RENDERED[language]} ",
            _placeholder(language, 0),
        ],
    ]
    for root in NOR_SUFFIX_GUARD_ROOTS:
        rows.append([
            f" {root}-nor ",
            f" {_global_render(payload, root, language)}-nor ",
            _placeholder(language, len(rows)),
        ])
    rows.append([
        " nor ",
        f" {_localized_render(payload, 'nor', language)} ",
        _placeholder(language, len(rows)),
    ])
    compound_sources = tuple(
        f" {surface} " for surface in compound_surfaces()
    )
    for source in compound_sources:
        index = len(rows)
        old = historical[source]
        surface = source.strip()
        prefix = surface.split("-", 1)[0]
        expected_start = f" {prefix}-"
        if not old[1].startswith(expected_start):
            raise ValueError(
                f"Phase 600 {language} R68 prefix drift: {source!r}"
            )
        rendered_nor = _cased_nor_render(payload, surface, language)
        remainder = old[1][len(f" {prefix}"):]
        if not remainder.startswith("-<ruby>"):
            raise ValueError(
                f"Phase 600 {language} R68 body drift: {source!r}"
            )
        rows.append([
            source,
            f" {rendered_nor}{remainder}",
            _placeholder(language, index),
        ])
    if (
        len(rows) != MANAGED_ROWS
        or [row[0] for row in rows] != list(managed_sources())
        or len({row[0] for row in rows}) != MANAGED_ROWS
        or len({row[2] for row in rows}) != MANAGED_ROWS
    ):
        raise ValueError("Phase 600 expected-row closure drift")
    return rows


def validate_optional_layer(
    payload: dict,
    language: str,
    *,
    require_present: bool = False,
    require_position: bool = True,
) -> list[list[str]]:
    """Return zero or the exact 52 managed rows; reject every partial layer."""
    discovered = [
        row
        for rows in payload.values()
        if isinstance(rows, list)
        for row in rows
        if is_managed_row(row)
    ]
    if not discovered:
        if require_present:
            raise ValueError(f"Phase 600 {language} layer is absent")
        return []
    local_key, global_key, two_char_key = rule_keys(payload)
    leaks = [
        (key, row)
        for key in (local_key, two_char_key)
        for row in payload[key]
        if is_managed_row(row)
    ]
    if leaks:
        raise ValueError(
            f"Phase 600 {language} managed row leaked outside global bucket"
        )
    global_rows = payload[global_key]
    managed = [row for row in global_rows if is_managed_row(row)]
    if not managed:
        raise ValueError(
            f"Phase 600 {language} rows exist outside the global bucket"
        )
    expected = build_expected_rows(payload, language)
    if managed != expected:
        raise ValueError(f"Phase 600 {language} managed rows drift")
    if require_position and global_rows[
        PHASE599_ROWS:PHASE599_ROWS + MANAGED_ROWS
    ] != expected:
        raise ValueError(f"Phase 600 {language} managed-row position drift")
    if global_rows[:PHASE599_ROWS] == expected[:PHASE599_ROWS]:
        raise ValueError("Phase 600 rows displaced Phase 599 precedence")
    return managed


def strip_optional_layer(
    payload: dict,
    language: str,
    *,
    require_present: bool = False,
) -> tuple[dict, list[list[str]]]:
    """Return a shallow payload without only the validated Phase-600 rows."""
    managed = validate_optional_layer(
        payload, language, require_present=require_present,
    )
    if not managed:
        return payload, []
    local_key, global_key, two_char_key = rule_keys(payload)
    stripped = dict(payload)
    stripped[global_key] = [
        row for row in payload[global_key] if not is_managed_row(row)
    ]
    if (
        stripped[local_key] is not payload[local_key]
        or stripped[two_char_key] is not payload[two_char_key]
    ):
        raise ValueError("Phase 600 strip escaped the global Ruby bucket")
    return stripped, managed


def layer_identity(payload: dict, language: str) -> dict:
    rows = validate_optional_layer(payload, language, require_present=True)
    return {
        "phase": PHASE,
        "language": language,
        "managed_rows": len(rows),
        "sources_sha256": compact_sha256([row[0] for row in rows]),
        "rows_sha256": compact_sha256(rows),
        "placeholder_prefix": MANAGED_PLACEHOLDER_PREFIX,
        "gate": True,
    }
