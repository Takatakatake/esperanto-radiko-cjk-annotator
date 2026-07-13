# -*- coding: utf-8 -*-
"""Build the exact-line reviewed inventory for bare_word_audit.py.

Run only after every guide-mandatory omission has been fixed.  Classification
is intentionally path/context-specific; an unrecognized row aborts generation
instead of silently receiving a broad exemption.
"""
from __future__ import annotations

import collections
import json
import os
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]
REPORT = BASE / "_analysis_20260625" / "out" / "_audit_annotation_coverage.json"
OUTPUT = BASE / "_analysis_20260625" / "_bare_word_reviewed.json"


def classification(row):
    path, line, token, kind = row["path"], row["line"], row["token"], row["kind"]

    if token == "Hejmo" and "vere-aux-fantazie" in path and line == 126:
        return (
            "navigation_link",
            "Chapter navigation label; it is interface text, not annotated reading prose.",
        )
    if kind == "attached_unexpected_token" and token in {
        "ii", "u", "no", "n-o", "a-a-a-a-a-a-blo", "a'n",
    }:
        return (
            "grammar_or_pronunciation_notation",
            "Deliberate stutter, repeated ending, or segmented sound/letter notation; not a missing lexical ruby.",
        )
    if "lernolibroj/fujimaki/" in path:
        return (
            "foreign_or_constructed_example",
            "Quoted phonotactic, historical-language, or constructed-language example retained in its source spelling.",
        )
    if "lernolibroj/esperanto-express/" in path:
        return (
            "foreign_language_example",
            "Japanese example phrase shown for comparison, outside Esperanto reading prose.",
        )
    if path.endswith("legajxoj/eseoj-kaj-artikoloj/tokipona_esperanto.html"):
        return (
            "quoted_tokipona",
            "Toki Pona word or example intentionally retained in Toki Pona spelling.",
        )
    if "rondolegado/2026-03/" in path:
        return (
            "quoted_source_language",
            "Toki Pona, Chinese, or Korean source term/readout explicitly discussed as foreign-language data.",
        )
    if path.endswith("legajxoj/eseoj-kaj-artikoloj/pola_retradio.html"):
        return (
            "roman_numeral_notation",
            "Roman numeral used as a historical ordinal or structural label, not an unannotated word.",
        )
    if path.endswith("legajxoj/eseoj-kaj-artikoloj/La_eseo_pri_Butano.html"):
        return (
            "quoted_english_term",
            "English discipline name quoted as the source-language equivalent, not Esperanto prose.",
        )
    if path.endswith("legajxoj/kunvenoj-kaj-prelegoj/20250521_komuna_kunveno_en_la_japana.html"):
        return (
            "source_credit",
            "Image license/attribution text retained verbatim outside the annotated prose.",
        )
    if "vere-aux-fantazie" in path:
        if token == "No":
            return (
                "quoted_english_phrase",
                "The English sign text 'No standing' is the object of the linguistic discussion.",
            )
        if token == "Eeeeeeej":
            return (
                "onomatopoeia",
                "Expressive drawn-out cry whose spelling is intentionally preserved.",
            )
        if token == "ĵan":
            return (
                "pronunciation_transcription",
                "Pronunciation rendering following the already annotated full personal name.",
            )

    if "202504_Revuo" in path:
        if line == 285:
            return (
                "quoted_source_term",
                "Chinese/Japanese technical term and romanization explicitly quoted for comparison.",
            )
        return (
            "source_credit",
            "English Nobel lecture/photo credit or copyright line retained verbatim.",
        )
    if "202505_Revuo" in path:
        if line in {410, 416}:
            return (
                "source_credit",
                "English Nobel lecture/copyright credit retained verbatim.",
            )
        return (
            "grammar_or_code_example",
            "Letter/blank puzzle or explicitly isolated grammar fragment, not continuous reading prose.",
        )
    if "202506_Revuo" in path:
        if line == 127:
            return (
                "image_text",
                "Erroneous English wording transcribed from an AI-generated image.",
            )
        if 468 <= line <= 478:
            return (
                "foreign_language_example",
                "Source-language data in a linguistics problem retained verbatim.",
            )
        if line == 490:
            return (
                "file_name",
                "PDF file name, not prose.",
            )
        if line == 778:
            return (
                "postal_address",
                "Romanized postal address outside the annotated article prose.",
            )
    if "202507_Revuo" in path:
        if line == 156:
            return (
                "foreign_language_example",
                "Romanized Japanese phrase explicitly presented as a source-language expression.",
            )
        return (
            "postal_address",
            "Romanized postal address outside the annotated article prose.",
        )
    if "202510_Revuo" in path:
        return (
            "quoted_tokipona",
            "Toki Pona word or sentence intentionally retained in Toki Pona spelling.",
        )
    if "202602_Revuo" in path:
        if line == 106:
            return (
                "wordplay_notation",
                "Parenthesized expansion of the event-name wordplay, not a bare Esperanto omission.",
            )
        if line == 265:
            return (
                "quoted_source_term",
                "Italicized Japanese food name discussed as a loan/source term.",
            )
    if "202603_Revuo" in path:
        if line == 680:
            return (
                "postal_address",
                "Romanized postal address outside the annotated article prose.",
            )
        return (
            "quoted_source_language",
            "German, Vietnamese, English, Korean, Chinese, or Toki Pona example retained verbatim.",
        )
    if "202604_Revuo" in path:
        return (
            "quoted_catalan",
            "Catalan phrase in a side-by-side language lesson, intentionally not Esperanto-annotated.",
        )
    if "202606_Revuo" in path:
        return (
            "postal_address",
            "Telephone/fax label or romanized postal address outside the annotated article prose.",
        )

    raise ValueError(f"unclassified reviewed candidate: {path}:{line}:{token} ({kind})")


def main():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    # A successful audited report has all rows under ``reviewed``; a report
    # made with no/empty inventory has them under ``unresolved``.  Supporting
    # both makes regeneration idempotent instead of replacing a valid config
    # with an empty one after a PASS run.
    source_rows = report["unresolved"] or report["reviewed"]
    if not source_rows:
        raise RuntimeError("refusing to replace reviewed inventory with zero rows")
    grouped = collections.defaultdict(lambda: {"lines": set(), "count": 0})
    for row in source_rows:
        category, reason = classification(row)
        key = (row["path"], row["token"], category, reason)
        grouped[key]["lines"].add(row["line"])
        grouped[key]["count"] += 1

    entries = []
    for (path, token, category, reason), values in sorted(grouped.items()):
        entries.append({
            "path": path,
            "token": token,
            "lines": sorted(values["lines"]),
            "expected_count": values["count"],
            "category": category,
            "reason": reason,
        })
    payload = {
        "schema_version": 2,
        "scope": "Exact reviewed non-annotation occurrences after mandatory ruby omissions were fixed",
        "entries": entries,
    }
    temp = OUTPUT.with_suffix(OUTPUT.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, OUTPUT)
    print(f"wrote {len(entries)} exact entries / {len(source_rows)} occurrences: {OUTPUT}")


if __name__ == "__main__":
    main()
