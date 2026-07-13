# -*- coding: utf-8 -*-
"""Compare the linear parser with an independent Unicode-category tokenizer."""
from __future__ import annotations

import collections
import html as htmllib
import itertools
import os
from pathlib import Path
import re
import sys
import unicodedata

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import no_worsening_audit as audit


def category_reference_parser(text):
    body_match = re.search(r"<body\b", text, re.IGNORECASE)
    if body_match:
        text = text[body_match.start():]
    text = audit.RUBY_RE.sub(
        lambda match: "\x01" + match.group("rb").strip() + "\x01", text
    )
    text = re.sub(r"<[^>]+>", " ", text)
    text = htmllib.unescape(text)
    # Scan marker pairs without relying on regex dot mode.  This remains
    # independent from the production split and handles multiline ruby bases.
    chunks = []
    cursor = 0
    while True:
        opening = text.find("\x01", cursor)
        if opening < 0:
            chunks.append(text[cursor:])
            break
        closing = text.find("\x01", opening + 1)
        if closing < 0:
            raise ValueError("unpaired ruby marker in independent parser")
        chunks.append(text[cursor:opening])
        chunks.append(text[opening:closing + 1])
        cursor = closing + 1
    surface_parts = []
    pieces = []
    has_ruby = False

    def finish():
        nonlocal surface_parts, pieces, has_ruby
        result = None
        if surface_parts and has_ruby:
            surface = "".join(surface_parts)
            if surface.strip():
                result = surface, pieces
        surface_parts = []
        pieces = []
        has_ruby = False
        return result

    for chunk in chunks:
        if chunk.startswith("\x01") and chunk.endswith("\x01") and len(chunk) >= 2:
            rb = chunk[1:-1]
            surface_parts.append(rb)
            pieces.append((rb, True))
            has_ruby = True
            continue
        groups = itertools.groupby(
            chunk,
            key=lambda character: (
                (
                    unicodedata.category(character).startswith("L")
                    and unicodedata.name(character, "").startswith("LATIN ")
                )
                or unicodedata.category(character).startswith("M")
                or character in "-'’"
            ),
        )
        for is_token, characters in groups:
            token = "".join(characters)
            if not is_token:
                result = finish()
                if result is not None:
                    yield result
                continue
            surface_parts.append(token)
            pieces.append((token, False))
    result = finish()
    if result is not None:
        yield result


def counter(parser, text):
    result = collections.Counter()
    for raw_surface, typed_parts in parser(text):
        surface = audit.canonical(raw_surface)
        signature = audit.signature_from_typed_parts(typed_parts)
        if signature[0] != surface:
            raise ValueError(
                f"reconstruction failed: {raw_surface!r} / "
                f"{audit.display_parts(typed_parts)!r}"
            )
        result[(surface, signature)] += 1
    return result


def main():
    corpus_root = Path(os.environ.get(
        "ESP_CORPUS_PATH",
        ROOT / "_project_root_misc" / "京大エス研html文書＿Github",
    ))
    files = []
    for content_dir in audit.CONTENT_DIRS:
        files.extend(
            path for path in (corpus_root / content_dir).rglob("*")
            if path.is_file() and path.suffix.lower() in {".html", ".htm"}
        )
    mismatches = []
    total_linear = total_reference = 0
    for index, path in enumerate(sorted(files), 1):
        text = path.read_text(encoding="utf-8", errors="strict")
        linear = counter(audit.parse_corpus_words, text)
        reference = counter(category_reference_parser, text)
        total_linear += sum(linear.values())
        total_reference += sum(reference.values())
        if linear != reference:
            mismatches.append({
                "path": str(path.relative_to(corpus_root)).replace("\\", "/"),
                "linear_only": list((linear - reference).items())[:10],
                "reference_only": list((reference - linear).items())[:10],
            })
        if index % 20 == 0 or index == len(files):
            print(f"checked {index}/{len(files)}", flush=True)
    print(
        f"files={len(files)} linear={total_linear} reference={total_reference} "
        f"counter_mismatches={len(mismatches)}"
    )
    if len(files) != audit.EXPECTED_CONTENT_FILES or mismatches:
        for mismatch in mismatches[:10]:
            print(mismatch)
        raise SystemExit(1)
    print("no-worsening parser equivalence: PASS")


if __name__ == "__main__":
    main()
