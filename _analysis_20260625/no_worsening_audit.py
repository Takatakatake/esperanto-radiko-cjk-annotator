# -*- coding: utf-8 -*-
"""Prove that regenerated Ruby data did not introduce morphology regressions.

Two baselines are evaluated.  The data-isolated baseline is ``git HEAD``'s Ruby
JSON rendered through the *current* runtime.  The comprehensive baseline uses
both ``git HEAD``'s runtime and Ruby JSON.  The candidate uses the working-tree
runtime and Ruby JSON.  Runtime changes also have focused coverage in
``test_generation_regressions.py``.

Reference cases are the union of:

* every ruby-bearing word/decomposition in the 169 Kyoto HTML content files;
* the path-specific 74-instance place-repair manifest;
* the learner gold dictionary's unmarked rows;
* a line-paired academic/PEJVO coarse authority for every evaluable learner
  row marked ``##偽分解`` (the learner's fake deep boundaries are excluded);
* explicitly reviewed official long-root overrides and project-level Ruby
  boundary decisions.

The gate rejects every old-correct -> current-wrong case, every changed output
which remains wrong, any weighted decrease, and any current mismatch in the
place manifest or either reviewed override set.
"""
from __future__ import annotations

import argparse
import collections
import gc
import hashlib
import html as htmllib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import types
import unicodedata


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from extract_lib import hat_to_circumflex, replace_esperanto_chars
from atomic_json import atomic_json_dump
from gold_snapshot import consistent_snapshot
from gen_replacement import load_app_replacement_helper
import build_fake_coarse_phase511_transition_review as phase511_builder


CONTENT_DIRS = ("lernolibroj", "legajxoj", "revuoj", "rondolegado")
EXPECTED_CONTENT_FILES = 169
CHECKPOINT_SCHEMA_VERSION = 2
RESUME_COMPATIBLE_AUDIT_CODE_SHA256 = {
    # This exact revision differs only by the fail-closed language-result
    # resume loader below; its rendering and comparison functions are byte-for-
    # byte the producers of the saved JA/ZH results.
    "DA2317DB1E4CED0BE2AF5313829C77903C834414A92186DE5EBD7CF1195E10F1",
}
REFERENCE_SCHEMA_VERSION = 5
FORMAT = "HTML格式_Ruby文字_大小调整"
ESP_LETTERS = "a-zĉĝĥĵŝŭ"
WORD_RE = re.compile(rf"(?=.*[{ESP_LETTERS}])[{ESP_LETTERS}'-]+", re.IGNORECASE)
VISIBLE_TOKEN_RE = re.compile(rf"[{ESP_LETTERS}]+|[-']+", re.IGNORECASE)
RAW_RUBY_OPEN_RE = re.compile(r"<ruby\b", re.IGNORECASE)
RUBY_RE = re.compile(
    r"<ruby\b[^>]*>\s*(?P<rb>.*?)\s*"
    r"<rt\b[^>]*>.*?</rt\s*>\s*</ruby\s*>",
    re.IGNORECASE | re.DOTALL,
)
FAKE_MARKER_RE = re.compile(r"##偽分解(?:\([^)]*\))?")

# Adjacent grammatical pieces are one literal run in rendered HTML.  Treating
# o/n as an observable o/n boundary would manufacture a false regression.
SPECIAL_COUNTRY_ENDINGS = {
    "io", "ia", "ion", "ian", "ioj", "iojn", "iaj", "iajn",
}
GRAM_ENDINGS = {
    "o", "oj", "on", "ojn", "a", "aj", "an", "ajn", "e", "en",
    "n", "j", "jn",
} | SPECIAL_COUNTRY_ENDINGS
ALWAYS_BARE_PIECES = {
    "o", "a", "e", "i", "u", "n", "j", "jn",
}
# The guides require as/is/os/us to be independent ruby annotations.  Only
# nominal/adverbial endings plus infinitive/imperative i/u remain literal.
TERMINAL_BARE_PIECES = GRAM_ENDINGS | {"u", "i"}
PRE_HYPHEN_BARE_PIECES = {"oj", "ojn", "aj", "ajn"}

# These are intentionally independent of learner-dictionary ``##偽分解``
# rows.  They were reviewed against the official long-root analyses used by
# the corpus/app correction set.
OFFICIAL_LONG_ROOT_OVERRIDES = {
    "biologio": "biologi/o",
    "fiziologio": "fiziologi/o",
    "fiziologia": "fiziologi/a",
    "aroganta": "arogant/a",
    "arogantaĵo": "arogant/aĵ/o",
    "kriptografio": "kriptografi/o",
    "moravio": "moravi/o",
    "anestezi": "anestez/i",
    # The HTML guides are stronger than the learner-gold spellings here.
    # Kioto is the proper-name body (not Kiot/o), while ordinary compound
    # hyphens in the two lexical expressions remain literal between roots.
    "Kioto-protokolo": "Kioto/-/protokol/o",
    "glu-glu-glu": "glu/-/glu/-/glu",
    "pli-ol-unu": "pli/-/ol/-/unu",
}

# These unmarked-gold exceptions are reviewed annotation-boundary decisions,
# not claims that their recorded counteranalyses are linguistically false.
PROJECT_RUBY_BOUNDARY_REVIEWS = {
    "Ionia": {
        "selected_decomposition": "Ioni/a",
        "decision": "project_conservative_ruby_display_override",
        "authority": (
            "reviewed Ionia Maro/Ionio/ioniano family, paired academic and "
            "PEJVO coarse forms, and pinned Kanji master Ioni/a"
        ),
        "counterevidence": (
            "PIV derives Ionia from Ion/o, and the pinned moving-gold row "
            "49535 is the unmarked fine form Ion/i/a"
        ),
        "reason": (
            "keep one coherent Ioni family in annotation Ruby while the "
            "deeper Ion/i analysis remains documented in PIV and moving-gold "
            "counterevidence for a future track-specific review"
        ),
    },
    "alternanco": {
        "selected_decomposition": "alternanc/o",
        "decision": "project_piv_long_root",
        "authority": (
            "PIV2020 has an independent alternanc/o head; fixed PEJVO and "
            "the pinned Kanji master also use alternanc/o"
        ),
        "counterevidence": (
            "PIV also registers productive scientific suffix -anc/, and the "
            "moving-gold row 1352 uses the finer altern/anc/o analysis"
        ),
        "reason": (
            "Kyoto HTML supplies no family instance, so conservative Ruby "
            "retains the three-authority long root instead of forcing the "
            "otherwise plausible suffix reanalysis"
        ),
    },
}
PROJECT_RUBY_BOUNDARY_OVERRIDES = {
    surface: review["selected_decomposition"]
    for surface, review in PROJECT_RUBY_BOUNDARY_REVIEWS.items()
}
EXACT_REQUIRED_REFERENCE_SOURCES = frozenset({
    "html_place_manifest",
    "gold_official_override",
    "gold_project_ruby_boundary_override",
})
REVIEWED_GOLD_OVERRIDES = {
    **OFFICIAL_LONG_ROOT_OVERRIDES,
    **PROJECT_RUBY_BOUNDARY_OVERRIDES,
}
if len(REVIEWED_GOLD_OVERRIDES) != (
    len(OFFICIAL_LONG_ROOT_OVERRIDES)
    + len(PROJECT_RUBY_BOUNDARY_OVERRIDES)
):
    raise ValueError("reviewed gold override surfaces overlap")


def normalize_visible(value: str) -> str:
    """Normalize visible text while retaining meaningful internal spacing."""
    normalized = unicodedata.normalize(
        "NFC", replace_esperanto_chars(value, hat_to_circumflex)
    ).replace("’", "'")
    return re.sub(r"\s+", " ", normalized)


def canonical(value: str) -> str:
    """Normalize Esperanto notation while preserving case and word spacing."""
    return normalize_visible(value).strip()


def norm(value: str) -> str:
    """Case-insensitive lookup form used only by deployed overlay helpers."""
    return canonical(value).lower()


def evaluable(surface: str) -> bool:
    return bool(WORD_RE.fullmatch(surface))


def clean_piece(piece: str) -> str:
    """Normalize a visible piece without discarding punctuation or case."""
    return normalize_visible(piece)


def is_latin_word_character(character: str) -> bool:
    """True for visible Latin-script word material outside ruby tags."""
    if character in "-'’":
        return True
    category = unicodedata.category(character)
    if category.startswith("M"):
        return True
    if not category.startswith("L"):
        return False
    return unicodedata.name(character, "").startswith("LATIN ")


def signature_from_typed_parts(parts: list[tuple[str, bool]]):
    """Return exact visible text and typed spans.

    A span records both its text and whether it was inside ``<ruby>``. Adjacent
    literal pieces are merged because ``a`` + ``n`` and literal ``an`` expose
    the same HTML structure; adjacent ruby pieces remain separate roots.
    """
    normalized: list[tuple[str, bool]] = []
    for raw_piece, is_ruby in parts:
        piece = clean_piece(raw_piece)
        if not piece:
            continue
        # Adjacent literal pieces expose no boundary.  Ruby pieces never merge
        # merely because their spelling happens to be a grammatical ending.
        if normalized and not is_ruby and not normalized[-1][1]:
            normalized[-1] = (normalized[-1][0] + piece, False)
        else:
            normalized.append((piece, is_ruby))
    reconstruction = "".join(piece for piece, _ in normalized)
    spans = tuple((piece, bool(is_ruby)) for piece, is_ruby in normalized)
    return reconstruction, spans


def signature_payload(signature):
    reconstruction, spans = signature
    return {
        "reconstruction": reconstruction,
        "spans": [
            {"text": text, "ruby": is_ruby}
            for text, is_ruby in spans
        ],
    }


def signature_from_payload(payload):
    return (
        payload["reconstruction"],
        tuple(
            (span["text"], bool(span["ruby"]))
            for span in payload["spans"]
        ),
    )


def expected_typed_parts(
    decomposition: str, atomic_hyphen_pieces: frozenset[str] = frozenset(),
) -> list[tuple[str, bool]]:
    parts: list[tuple[str, bool]] = []
    raw_parts = [raw for raw in decomposition.split("/") if canonical(raw)]
    # Gold dictionary compounds often write the hyphen inside a slash piece
    # (``alveol-son`` or ``o-ret``).  A hyphen is punctuation outside ruby,
    # not a license to turn both sides into one synthetic root.  Conversely,
    # a one-piece entry such as the guide-defined honorific ``s-ro`` is an
    # atomic abbreviation whose hyphen intentionally remains inside ruby.
    expanded: list[str] = []
    for raw_piece in raw_parts:
        if (
            len(raw_parts) > 1
            and canonical(raw_piece) not in atomic_hyphen_pieces
        ):
            expanded.extend(
                piece for piece in re.split(r"(-+)", raw_piece) if piece
            )
        else:
            expanded.append(raw_piece)
    lexical_total = sum(any(character.isalpha() for character in piece)
                        for piece in expanded)
    lexical_index = 0
    for expanded_index, raw_piece in enumerate(expanded):
        piece = canonical(raw_piece)
        if not any(character.isalpha() for character in piece):
            parts.append((piece, False))
            continue
        piece_lookup = piece.lower()
        is_bare = (
            # Both guides scope ordinary root annotation to roots of at least
            # two letters.  Standalone alphabet/ending entries such as ``a``
            # and ``o`` therefore remain literal; two-letter correlatives and
            # lexical roots (io, ar, et, ...) remain eligible ruby units.
            (lexical_total == 1 and len(piece) < 2)
            or (
                lexical_total > 1
                and (
                    piece_lookup in ALWAYS_BARE_PIECES
                or (
                    piece_lookup in PRE_HYPHEN_BARE_PIECES
                    and expanded_index + 1 < len(expanded)
                    and not any(
                        character.isalpha()
                        for character in expanded[expanded_index + 1]
                    )
                    and "-" in expanded[expanded_index + 1]
                )
                or (
                    lexical_index > 0
                    and piece_lookup in SPECIAL_COUNTRY_ENDINGS
                )
                or (
                    lexical_index == lexical_total - 1
                    and piece_lookup in TERMINAL_BARE_PIECES
                )
                )
            )
        )
        is_ruby = not is_bare
        parts.append((piece, is_ruby))
        lexical_index += 1
    return parts


def expected_signature(
    decomposition: str, atomic_hyphen_pieces: frozenset[str] = frozenset(),
):
    return signature_from_typed_parts(
        expected_typed_parts(decomposition, atomic_hyphen_pieces)
    )


def load_atomic_hyphen_review():
    """Load the closed, guide-reviewed proper-name hyphen authority."""
    path = HERE / "_no_worsening_atomic_hyphen_roots.json"
    raw = path.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("unsupported atomic-hyphen review schema")
    entries = payload.get("entries", [])
    if len(entries) != payload.get("expected_entries"):
        raise ValueError("atomic-hyphen review entry count changed")
    reviewed = {}
    for entry in entries:
        surface = canonical(entry.get("surface", ""))
        pieces = tuple(canonical(piece) for piece in entry.get("atomic_pieces", []))
        if (
            not surface or surface in reviewed or not pieces
            or any("-" not in piece for piece in pieces)
            or entry.get("category") != "proper_name"
            or not entry.get("reason")
        ):
            raise ValueError(f"invalid atomic-hyphen review entry: {entry!r}")
        reviewed[surface] = frozenset(pieces)
    return reviewed, {
        "path": path.relative_to(ROOT).as_posix(),
        "entries": len(entries),
        "sha256": hashlib.sha256(raw).hexdigest().upper(),
    }


def reviewed_atomic_hyphen_pieces(surface, decomposition, reviewed):
    pieces = reviewed.get(canonical(surface), frozenset())
    decomposition_pieces = {
        canonical(piece) for piece in decomposition.split("/") if canonical(piece)
    }
    if not pieces.issubset(decomposition_pieces):
        raise ValueError(
            f"reviewed atomic hyphen is absent from gold decomposition: "
            f"{surface!r} / {decomposition!r} / {sorted(pieces)!r}"
        )
    return pieces


def rendered_typed_parts(rendered: str) -> list[tuple[str, bool]]:
    rendered = rendered.strip()
    parts: list[tuple[str, bool]] = []
    position = 0
    for match in RUBY_RE.finditer(rendered):
        literal = htmllib.unescape(
            re.sub(r"<[^>]+>", "", rendered[position:match.start()])
        )
        if literal:
            parts.append((literal, False))
        rb = htmllib.unescape(re.sub(r"<[^>]+>", "", match.group("rb")))
        if canonical(rb):
            parts.append((rb, True))
        position = match.end()
    literal = htmllib.unescape(re.sub(r"<[^>]+>", "", rendered[position:]))
    if literal:
        parts.append((literal, False))
    # ``render_signatures`` pads every probe with one outer space.  Output
    # wrappers can move that padding just inside a closing tag, where a plain
    # ``rendered.strip()`` cannot reach it.  Trim only literal edge padding;
    # internal spaces remain observable reference structure.
    while parts and not parts[0][1]:
        trimmed = parts[0][0].lstrip()
        if trimmed:
            parts[0] = (trimmed, False)
            break
        parts.pop(0)
    while parts and not parts[-1][1]:
        trimmed = parts[-1][0].rstrip()
        if trimmed:
            parts[-1] = (trimmed, False)
            break
        parts.pop()
    return parts


def display_parts(parts: list[tuple[str, bool]]) -> str:
    return "/".join(canonical(piece) for piece, _ in parts if canonical(piece))


def display_typed_parts(parts: list[tuple[str, bool]]) -> str:
    return "|".join(
        f"{'R' if is_ruby else 'L'}:"
        f"{canonical(piece) if canonical(piece) else '<SPACE>'}"
        for piece, is_ruby in parts if normalize_visible(piece)
    )


def apply_strand_autofix(surface, parts, overlay, data_dir):
    """Apply the deployed first-consonant-strand repair to parsed pieces."""
    normalized_parts = []
    for piece, _is_ruby in parts:
        cleaned = clean_piece(piece)
        if cleaned:
            normalized_parts.append(cleaned)
    is_stranded = (
        len(normalized_parts) >= 2
        and len(normalized_parts[0]) == 1
        and normalized_parts[0] not in "aeiou"
    )
    if not is_stranded or overlay is None:
        return parts
    decomposition = overlay.autofix_decomp(norm(surface), str(data_dir))
    if (
        decomposition
        and clean_piece(decomposition.replace("/", ""))
        == clean_piece(surface)
    ):
        return expected_typed_parts(decomposition)
    return parts


def parse_corpus_words(text: str):
    """Yield ``(surface, typed_parts)`` exactly as the HTML exposes them."""
    body_match = re.search(r"<body\b", text, re.IGNORECASE)
    if body_match:
        text = text[body_match.start():]
    text = RUBY_RE.sub(lambda match: "\x01" + match.group("rb").strip() + "\x01", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = htmllib.unescape(text)
    # Ruby bases can contain line breaks (notably multi-word proper names).
    # Without DOTALL, marker pairing drifts at the first such base and later
    # unrelated words are silently fused into a fake reference unit.
    chunks = re.split(r"(\x01.*?\x01)", text, flags=re.DOTALL)
    surface_parts: list[str] = []
    pieces: list[tuple[str, bool]] = []
    has_ruby = False
    for chunk in chunks:
        if chunk.startswith("\x01") and chunk.endswith("\x01") and len(chunk) >= 2:
            rb = chunk[1:-1]
            surface_parts.append(rb)
            pieces.append((rb, True))
            has_ruby = True
            continue
        token_chars: list[str] = []
        for character in chunk:
            if (
                is_latin_word_character(character)
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
                pieces.append((token, False))
                token_chars = []
            if surface_parts and has_ruby:
                surface = "".join(surface_parts)
                if surface.strip():
                    yield surface, pieces
            surface_parts = []
            pieces = []
            has_ruby = False
        if token_chars:
            token = "".join(token_chars)
            surface_parts.append(token)
            pieces.append((token, False))
    if surface_parts and has_ruby:
        surface = "".join(surface_parts)
        if surface.strip():
            yield surface, pieces


def stable_json_sha256(value) -> str:
    raw = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("ascii")
    return hashlib.sha256(raw).hexdigest().upper()


def add_case(cases, surface, signature, expected, source, weight=1):
    normalized_surface = canonical(surface)
    if not normalized_surface:
        return
    reconstruction, _spans = signature
    if reconstruction != normalized_surface:
        raise ValueError(
            f"reference reconstruction failed: {surface!r} / {expected!r} "
            f"-> {reconstruction!r}"
        )
    key = (normalized_surface, signature)
    case = cases.setdefault(key, {
        "surface": normalized_surface,
        "expected": expected,
        "signature": signature,
        "sources": collections.Counter(),
    })
    case["sources"][source] += weight


def corpus_cases(cases, corpus_root: Path):
    file_count = raw_ruby = parsed_ruby = parsed_units = eligible_units = 0
    word_alphabet_units = 0
    case_changed_instances = 0
    file_hashes = []
    extended = collections.Counter()
    for content_dir in CONTENT_DIRS:
        for path in sorted((corpus_root / content_dir).rglob("*")):
            if not path.is_file() or path.suffix.lower() not in {".html", ".htm"}:
                continue
            file_count += 1
            raw = path.read_bytes()
            text = raw.decode("utf-8", errors="strict")
            relative = path.relative_to(corpus_root).as_posix()
            file_hashes.append((relative, hashlib.sha256(raw).hexdigest().upper()))
            raw_ruby += len(RAW_RUBY_OPEN_RE.findall(text))
            parsed_ruby += len(RUBY_RE.findall(text))
            counts = collections.Counter()
            displays = {}
            for raw_surface, typed_parts in parse_corpus_words(text):
                parsed_units += 1
                surface = canonical(raw_surface)
                if not surface:
                    raise ValueError(f"empty corpus surface: {path}")
                eligible_units += 1
                if evaluable(surface):
                    word_alphabet_units += 1
                else:
                    reason = (
                        "contains_space" if any(ch.isspace() for ch in surface)
                        else "outside_app_word_alphabet"
                    )
                    extended[(
                        relative, surface,
                        display_typed_parts(typed_parts), reason,
                    )] += 1
                if surface != surface.lower():
                    case_changed_instances += 1
                signature = signature_from_typed_parts(typed_parts)
                if signature[0] != surface:
                    raise ValueError(
                        f"corpus reconstruction failed: {path} {raw_surface!r} "
                        f"{display_parts(typed_parts)!r}"
                    )
                key = (surface, signature)
                counts[key] += 1
                displays.setdefault(key, display_parts(typed_parts))
            for (surface, signature), count in counts.items():
                add_case(
                    cases, surface, signature, displays[(surface, signature)],
                    "html_corpus", count,
                )
    if file_count != EXPECTED_CONTENT_FILES:
        raise ValueError(f"HTML scope changed: {file_count} != {EXPECTED_CONTENT_FILES}")
    if raw_ruby != parsed_ruby:
        raise ValueError(f"unparsed ruby: raw={raw_ruby} parsed={parsed_ruby}")
    extended_rows = [
        {
            "path": path,
            "surface": surface,
            "typed": typed,
            "reason": reason,
            "count": count,
        }
        for (path, surface, typed, reason), count in sorted(extended.items())
    ]
    return {
        "files": file_count,
        "raw_ruby": raw_ruby,
        "parsed_ruby": parsed_ruby,
        "parsed_units": parsed_units,
        "eligible_units": eligible_units,
        "word_alphabet_units": word_alphabet_units,
        "extended_reference_units": sum(extended.values()),
        "extended_reference_unique_rows": len(extended_rows),
        "extended_reference_unique_surfaces": len({
            row["surface"] for row in extended_rows
        }),
        "extended_reference_reasons": dict(sorted(collections.Counter(
            row["reason"] for row in extended_rows for _ in range(row["count"])
        ).items())),
        "extended_reference_sha256": stable_json_sha256(extended_rows),
        "extended_reference_manifest": extended_rows,
        "case_preserved_instances": case_changed_instances,
        "excluded_units": 0,
        "content_sha256": stable_json_sha256(file_hashes),
    }


def place_cases(cases):
    payload = json.loads(
        (HERE / "_place_alignment_manifest.json").read_text(encoding="utf-8")
    )
    rows = payload["rows"]
    if len(rows) != payload["expected_rows"]:
        raise ValueError("place manifest row count changed")
    if sum(row["count"] for row in rows) != payload["expected_instances"]:
        raise ValueError("place manifest instance count changed")
    for row in rows:
        atomic_hyphen_pieces = frozenset(
            canonical(piece) for piece in row["ruby"] if "-" in piece
        )
        add_case(
            cases, row["surface"], expected_signature(
                row["expected"], atomic_hyphen_pieces
            ),
            row["expected"], "html_place_manifest", row["count"],
        )
    return {"rows": len(rows), "instances": sum(row["count"] for row in rows)}


def gold_path() -> Path:
    configured = os.environ.get("ESP_GOLD_PATH")
    if configured:
        return Path(configured)
    return (
        ROOT.parent / "エスペラント辞書徹底語根分解_20260630"
        / "世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416.txt"
    )


def load_fake_coarse_reference(
    gold_raw: bytes, gold_lines: list[str], eligible_marked_rows: dict[int, dict],
    marker_exclusions: collections.Counter,
):
    """Load the fixed non-fake boundary for every evaluable fake-marked row.

    The committed manifest is generated from line-paired learner/academic
    snapshots plus matching PEJVO evidence.  This loader intentionally checks
    the learner identity and every selected learner line again: a stale or
    surface-collapsed manifest must fail before it can influence the audit.
    """
    path = HERE / "_fake_coarse_reference_manifest.json"
    raw = path.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("unsupported fake-coarse reference schema")
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise ValueError("fake-coarse entries must be a list")
    serialized_entries = json.dumps(
        entries, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    entries_sha256 = hashlib.sha256(serialized_entries).hexdigest().upper()
    if entries_sha256 != payload.get("entries_sha256"):
        raise ValueError("fake-coarse entry fingerprint mismatch")
    review_path = HERE / "_fake_coarse_pejvo_disagreement_review.json"
    review_raw = review_path.read_bytes()
    review_payload = json.loads(review_raw.decode("utf-8"))
    review_identity = payload.get("pejvo_disagreement_review", {})
    if (
        review_payload.get("schema_version") != 1
        or len(review_payload.get("entries", []))
        != review_payload.get("expected_entries")
        or review_identity.get("path") != review_path.name
        or review_identity.get("entries") != len(review_payload["entries"])
        or review_identity.get("sha256")
        != hashlib.sha256(review_raw).hexdigest().upper()
    ):
        raise ValueError("fake-coarse PEJVO disagreement review drift")
    review_by_line = {
        entry["learner_line"]: entry for entry in review_payload["entries"]
    }
    project_review_path = HERE / "_fake_coarse_project_boundary_review.json"
    project_review_raw = project_review_path.read_bytes()
    project_review_payload = json.loads(project_review_raw.decode("utf-8"))
    project_review_identity = payload.get("project_boundary_review", {})
    if (
        project_review_payload.get("schema_version") != 1
        or len(project_review_payload.get("entries", []))
        != project_review_payload.get("expected_entries")
        or project_review_identity.get("path") != project_review_path.name
        or project_review_identity.get("entries")
        != len(project_review_payload["entries"])
        or project_review_identity.get("sha256")
        != hashlib.sha256(project_review_raw).hexdigest().upper()
    ):
        raise ValueError("fake-coarse project boundary review drift")
    project_review_by_line = {
        entry["learner_line"]: entry
        for entry in project_review_payload["entries"]
    }

    learner_source = payload.get("sources", {}).get("learner", {})
    actual_gold = {
        "bytes": len(gold_raw),
        "sha256": hashlib.sha256(gold_raw).hexdigest().upper(),
        "lines": len(gold_lines),
    }
    if any(learner_source.get(key) != value for key, value in actual_gold.items()):
        raise ValueError(
            "fake-coarse manifest learner snapshot differs from audit gold"
        )

    by_line = {}
    source_counts = collections.Counter()
    exact_counts = collections.Counter()
    casefold_counts = collections.Counter()
    nonmatching_pejvo = 0
    used_project_reviews = set()
    for entry in entries:
        line_number = entry.get("learner_line")
        if (
            not isinstance(line_number, int) or line_number < 1
            or line_number > len(gold_lines) or line_number in by_line
        ):
            raise ValueError(f"invalid/reused fake-coarse learner line: {line_number!r}")
        learner_row = eligible_marked_rows.get(line_number)
        if learner_row is None:
            raise ValueError(
                f"fake-coarse entry does not name an eligible marked line: {line_number}"
            )
        if (
            entry.get("learner_surface") != learner_row["surface"]
            or entry.get("learner_decomposition") != learner_row["decomposition"]
        ):
            raise ValueError(
                f"fake-coarse learner provenance drift at line {line_number}"
            )
        surface = canonical(entry.get("surface", ""))
        coarse = entry.get("coarse_decomposition", "")
        academic = entry.get("academic_decomposition", "")
        if (
            not surface or not evaluable(surface)
            or expected_signature(coarse)[0] != surface
            or expected_signature(academic)[0] != surface
            or surface.casefold() != learner_row["surface"].casefold()
        ):
            raise ValueError(
                f"fake-coarse reconstruction/case drift at line {line_number}"
            )
        authority = entry.get("authority")
        if authority not in {
            "paired_academic", "pejvo_original", "pejvo_reviewed_override",
            "project_reviewed_override",
        }:
            raise ValueError(
                f"unsupported fake-coarse authority at line {line_number}: {authority!r}"
            )
        if authority == "pejvo_original" and coarse != academic:
            raise ValueError(
                f"PEJVO may corroborate but not override paired academic line {line_number}"
            )
        candidates = entry.get("nonmatching_pejvo_candidates", [])
        if candidates:
            review = review_by_line.get(line_number)
            if review is None:
                raise ValueError(
                    f"nonmatching PEJVO row lacks review at line {line_number}"
                )
            available = sorted(
                candidate.get("decomposition", "") for candidate in candidates
            )
            if (
                review.get("surface") != surface
                or review.get("academic_decomposition") != academic
                or review.get("pejvo_decompositions") != available
                or review.get("selected_decomposition") != coarse
                or entry.get("disagreement_review_decision")
                != review.get("decision")
                or (
                    review.get("decision") == "paired_academic"
                    and authority != "paired_academic"
                )
                or (
                    review.get("decision") == "pejvo_coarse"
                    and authority != "pejvo_reviewed_override"
                )
            ):
                raise ValueError(
                    f"nonmatching PEJVO review selection drift at line {line_number}"
                )
            nonmatching_pejvo += 1
            for candidate in candidates:
                candidate_decomposition = candidate.get("decomposition", "")
                if (
                    expected_signature(candidate_decomposition)[0] != surface
                    or candidate_decomposition == academic
                    or not candidate.get("lines")
                ):
                    raise ValueError(
                        f"invalid nonmatching PEJVO evidence at line {line_number}"
                    )
        elif line_number in review_by_line:
            raise ValueError(f"stale PEJVO disagreement review at line {line_number}")
        project_review = project_review_by_line.get(line_number)
        if project_review is not None:
            if (
                project_review.get("surface") != surface
                or project_review.get("academic_decomposition") != academic
                or project_review.get("selected_decomposition") != coarse
                or project_review.get("decision") not in {
                    "project_piv_long_root",
                    "project_conservative_ruby_display_override",
                }
                or entry.get("project_boundary_review_decision")
                != project_review.get("decision")
                or authority != "project_reviewed_override"
                or not project_review.get("evidence")
            ):
                raise ValueError(
                    f"project boundary review selection drift at line {line_number}"
                )
            used_project_reviews.add(line_number)
        elif authority == "project_reviewed_override":
            raise ValueError(
                f"project override lacks review at line {line_number}"
            )
        by_line[line_number] = entry
        source_counts[authority] += 1
        exact_counts[surface] += 1
        casefold_counts[surface.casefold()] += 1

    if used_project_reviews != set(project_review_by_line):
        raise ValueError(
            "unused project boundary reviews: "
            f"{sorted(set(project_review_by_line) - used_project_reviews)!r}"
        )

    if set(by_line) != set(eligible_marked_rows):
        missing = sorted(set(eligible_marked_rows) - set(by_line))
        extra = sorted(set(by_line) - set(eligible_marked_rows))
        raise ValueError(
            "fake-coarse marked-line coverage changed: "
            f"missing={missing[:10]!r}, extra={extra[:10]!r}"
        )
    counts = payload.get("counts", {})
    actual_counts = {
        "entries": len(entries),
        "marker_excluded_rows": sum(marker_exclusions.values()),
        "marker_exclusions_by_reason": dict(marker_exclusions),
        "source_rows": dict(source_counts),
        "academic_rows_with_nonmatching_pejvo_homographs": nonmatching_pejvo,
        "exact_surfaces": len(exact_counts),
        "duplicate_exact_surface_rows": sum(
            count - 1 for count in exact_counts.values() if count > 1
        ),
        "casefold_surfaces": len(casefold_counts),
        "duplicate_casefold_surface_rows": sum(
            count - 1 for count in casefold_counts.values() if count > 1
        ),
    }
    if counts != actual_counts:
        raise ValueError(
            f"fake-coarse manifest counts changed: {actual_counts!r} != {counts!r}"
        )
    paired = payload.get("paired_invariant", {})
    marker_rows = sum(bool(FAKE_MARKER_RE.search(line)) for line in gold_lines)
    if (
        paired.get("marked_rows") != marker_rows
        or paired.get("marked_different_decomposition") != marker_rows
        or paired.get("marked_gloss_context_matches_academic") != marker_rows
        or paired.get("unmarked_rows") != len(gold_lines) - marker_rows
        or paired.get("unmarked_identical_decomposition")
        != len(gold_lines) - marker_rows
        or paired.get("academic_rows_without_fake_marker") != len(gold_lines)
    ):
        raise ValueError("fake-coarse paired invariant no longer covers all gold lines")
    return by_line, {
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest().upper(),
        "entries_sha256": entries_sha256,
        "academic_sha256": payload["sources"]["academic"]["sha256"],
        "pejvo_original_sha256": payload["sources"]["pejvo_original"]["sha256"],
        "pejvo_disagreement_review": review_identity,
        "project_boundary_review": project_review_identity,
        "paired_invariant": paired,
        "counts": counts,
    }


def compact_json_sha256(value):
    raw = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


def load_fake_coarse_transition(
    fake_coarse_by_line, superseded_historical_entries,
):
    path = HERE / "_fake_coarse_transition_review.json"
    raw = path.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    entries = payload.get("entries", [])
    serialized = json.dumps(
        entries, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    if (
        payload.get("schema_version") != 1
        or hashlib.sha256(serialized).hexdigest().upper()
        != payload.get("entries_sha256")
        or payload.get("entries_sha256")
        != "B8B1036BF0164960429B2FD079EBF62A71FA02425FC0A4D8EB7B84F127BCCF01"
    ):
        raise ValueError("fake-coarse transition review drift")
    evaluable_lines = set()
    excluded_lines = []
    superseded_lines = []
    seen = set()
    for entry in entries:
        line = entry.get("learner_line")
        if not isinstance(line, int) or line in seen:
            raise ValueError(f"invalid/reused fake transition line: {line!r}")
        seen.add(line)
        coarse_entry = fake_coarse_by_line.get(line)
        superseding_entry = superseded_historical_entries.get(line)
        if superseding_entry is not None:
            if (
                line != 45205
                or entry.get("surface") != superseding_entry.get("surface")
                or entry.get("coarse_decomposition")
                != superseding_entry.get("previous_target")
                or compact_json_sha256(entry)
                != superseding_entry.get(
                    "supersedes_historical_entry_sha256"
                )
            ):
                raise ValueError(
                    f"invalid historical supersession at line {line}"
                )
            superseded_lines.append(line)
            continue
        if coarse_entry is None:
            excluded_lines.append(line)
            continue
        if (
            entry.get("surface") != coarse_entry.get("surface")
            or entry.get("coarse_decomposition")
            != coarse_entry.get("coarse_decomposition")
        ):
            raise ValueError(f"fake transition authority drift at line {line}")
        evaluable_lines.add(line)
    counts = payload.get("counts", {})
    expected_counts = {
        "entries": 136,
        "unique_surfaces": 135,
        "duplicate_surface_rows": 1,
        "categories": {
            "reviewed_c679_to_b090_fake_transition": 133,
            "reviewed_b090_marker_only_delta": 3,
        },
        "authority_adjustments": 2,
    }
    if (
        counts != expected_counts
        or len(entries) != counts["entries"]
        or len(seen) != len(entries)
    ):
        raise ValueError("fake transition review counts changed")
    # The single excluded entry is the reviewed multiword Ionia Maro; the
    # full-master audit renders and gates it without collapsing to a word key.
    if len(excluded_lines) != 1 or superseded_lines != [45205]:
        raise ValueError(
            "unexpected historical transition disposition: "
            f"full-master-only={excluded_lines!r}, "
            f"superseded={superseded_lines!r}"
        )
    return evaluable_lines, {
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest().upper(),
        "entries_sha256": payload["entries_sha256"],
        "entries": len(entries),
        "effective_entries": len(entries) - len(superseded_lines),
        "evaluable_entries": len(evaluable_lines),
        "full_master_only_entries": len(excluded_lines),
        "full_master_only_lines": excluded_lines,
        "superseded_entries": len(superseded_lines),
        "superseded_lines": superseded_lines,
    }


def load_fake_coarse_ff33_transition(fake_coarse_by_line):
    path = HERE / "_fake_coarse_ff33_transition_review.json"
    raw = path.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    entries = payload.get("entries", [])
    serialized = json.dumps(
        entries, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    expected_counts = {
        "entries": 1,
        "evaluable_entries": 1,
        "new_fake_marker_rows": 1,
    }
    if (
        payload.get("schema_version") != 1
        or hashlib.sha256(serialized).hexdigest().upper()
        != "3296A91605BCDD1E946966B72AEAC9855F3488347CA6A12913C679F86430ED31"
        or payload.get("entries_sha256")
        != "3296A91605BCDD1E946966B72AEAC9855F3488347CA6A12913C679F86430ED31"
        or payload.get("counts") != expected_counts
        or len(entries) != 1
    ):
        raise ValueError("FF33 fake-coarse transition review drift")
    entry = entries[0]
    line = entry.get("learner_line")
    coarse_entry = fake_coarse_by_line.get(line)
    if (
        line != 56273
        or coarse_entry is None
        or entry.get("surface") != coarse_entry.get("surface")
        or entry.get("learner_decomposition")
        != coarse_entry.get("learner_decomposition")
        or entry.get("coarse_decomposition")
        != coarse_entry.get("coarse_decomposition")
        or entry.get("target") != coarse_entry.get("coarse_decomposition")
        or entry.get("typed_roles") != "RL"
        or entry.get("case_sensitive") is not True
    ):
        raise ValueError("FF33 Tomisto transition authority drift")
    return {line}, {
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest().upper(),
        "entries_sha256": payload["entries_sha256"],
        "entries": 1,
        "evaluable_entries": 1,
        "full_master_only_entries": 0,
    }


def load_fake_coarse_5e_transition(fake_coarse_by_line):
    path = HERE / "_fake_coarse_5e_transition_review.json"
    raw = path.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    entries = payload.get("entries", [])
    serialized = json.dumps(
        entries, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    expected_hash = (
        "B0CF495ECDEA78DEA86AEB72CFF5252140C67D342947A391200CA9936BF41E1F"
    )
    expected_counts = {
        "entries": 1,
        "evaluable_entries": 1,
        "new_fake_marker_rows": 1,
    }
    if (
        payload.get("schema_version") != 1
        or hashlib.sha256(serialized).hexdigest().upper() != expected_hash
        or payload.get("entries_sha256") != expected_hash
        or payload.get("counts") != expected_counts
        or len(entries) != 1
    ):
        raise ValueError("5E fake-coarse transition review drift")
    entry = entries[0]
    line = entry.get("learner_line")
    coarse_entry = fake_coarse_by_line.get(line)
    if (
        line != 53890
        or coarse_entry is None
        or entry.get("surface") != coarse_entry.get("surface")
        or entry.get("learner_decomposition")
        != coarse_entry.get("learner_decomposition")
        or entry.get("coarse_decomposition")
        != coarse_entry.get("coarse_decomposition")
        or entry.get("target") != coarse_entry.get("coarse_decomposition")
        or entry.get("typed_roles") != "RL"
        or entry.get("case_sensitive") is not True
    ):
        raise ValueError("5E promil transition authority drift")
    return {line}, {
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest().upper(),
        "entries_sha256": payload["entries_sha256"],
        "entries": 1,
        "evaluable_entries": 1,
        "full_master_only_entries": 0,
    }


def load_fake_coarse_phase511_transition(
    fake_coarse_by_line, fake_coarse_identity,
):
    path = HERE / "_fake_coarse_phase511_transition_review.json"
    raw = path.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    entries = payload.get("entries", [])
    expected_entries_hash = (
        "3F7DBBB34ECE9D3657444818F753755176C89E66307E4AE0E0297A59B8919BFF"
    )
    expected_counts = {
        "entries": 21,
        "historical_authority_supersessions": 1,
        "strict_authority_carry_forwards": 1,
        "strict_authority_supersessions": 2,
        "strict_authority_additions": 17,
        "reviewed_exact_localized_annotations": 19,
    }
    source_reference = payload.get("source_fake_coarse_manifest", {})
    supersedes = payload.get("supersedes", {})
    historical = supersedes.get("historical_manifest", {})
    if (
        payload.get("schema_version") != 2
        or payload.get("phase") != 511
        or compact_json_sha256(entries) != expected_entries_hash
        or payload.get("entries_sha256") != expected_entries_hash
        or payload.get("counts") != expected_counts
        or len(entries) != 21
        or source_reference.get("sha256")
        != fake_coarse_identity.get("sha256")
        or source_reference.get("entries_sha256")
        != fake_coarse_identity.get("entries_sha256")
        or historical != {
            "sha256": (
                "D20633B41904776B5A6954F6EAC8F72335DCE3FEE51213AA9245A360E3027E34"
            ),
            "entries_sha256": (
                "B8B1036BF0164960429B2FD079EBF62A71FA02425FC0A4D8EB7B84F127BCCF01"
            ),
            "learner_lines": [45205],
        }
    ):
        raise ValueError("Phase 511 fake-coarse transition review drift")

    # The builder owns the verbose closed-set semantics.  Revalidate it here,
    # while retaining independent pins for the payload hash, counts and exact
    # line membership so a coordinated edit cannot silently widen this gate.
    phase511_builder.validate(payload)
    expected_lines = {
        45205, 45818, 4785, 21361, 60166, 60735,
        24033, 34886, 44893, 46627, 48081, 49821, 51048, 54151,
        54383, 55369, 59757, 60165, 60167, 60168, 60169,
    }
    if set(phase511_builder.REVIEW) != expected_lines:
        raise ValueError("Phase 511 closed-set review membership drift")
    expected = {
        line: {
            key: review[key] for key in (
                "surface", "target", "typed_roles", "category",
                "previous_target",
            )
        }
        for line, review in phase511_builder.REVIEW.items()
    }
    by_line = {}
    for entry in entries:
        line = entry.get("learner_line")
        wanted = expected.get(line)
        reference = fake_coarse_by_line.get(line)
        if (
            wanted is None
            or line in by_line
            or reference is None
            or any(entry.get(key) != value for key, value in wanted.items())
            or entry.get("learner_decomposition")
            != reference.get("learner_decomposition")
            or entry.get("coarse_decomposition")
            != reference.get("coarse_decomposition")
            or entry.get("academic_decomposition")
            != reference.get("academic_decomposition")
            or entry.get("target") != entry.get("coarse_decomposition")
            or entry.get("case_sensitive") is not True
            or entry.get("ruby_track_only") is not True
        ):
            raise ValueError(
                f"Phase 511 transition authority drift at line {line}"
            )
        by_line[line] = entry
    if set(by_line) != set(expected):
        raise ValueError("Phase 511 transition line coverage changed")
    expected_exact = {
        line: review["exact_annotations"]
        for line, review in phase511_builder.REVIEW.items()
        if review.get("exact_annotations")
    }
    if any(
        by_line[line].get("exact_annotations") != annotations
        for line, annotations in expected_exact.items()
    ):
        raise ValueError("Phase 511 localized annotation drift")
    if any(
        by_line[line].get("adds_strict_entry") is not True
        for line in {
            60166, 60735, 24033, 34886, 44893, 46627, 48081,
            49821, 51048, 54151, 54383, 55369, 59757, 60165,
            60167, 60168, 60169,
        }
    ):
        raise ValueError("Phase 511 semantic strict additions drift")
    return set(by_line), by_line, {
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest().upper(),
        "entries_sha256": payload["entries_sha256"],
        "entries": len(entries),
        "evaluable_entries": len(entries),
        "full_master_only_entries": 0,
        "historical_supersessions": 1,
    }


def gold_cases(
    cases, path: Path, raw: bytes, snapshot_identity, expected_sha256,
    enforce_all_fake_coarse=False,
):
    digest = hashlib.sha256(raw).hexdigest().upper()
    expected_sha256 = expected_sha256.upper()
    if digest != expected_sha256:
        raise ValueError(f"gold SHA256 changed: {digest} != {expected_sha256}")
    atomic_hyphen_review, atomic_hyphen_identity = load_atomic_hyphen_review()
    used_atomic_hyphen_reviews = set()
    records = collections.defaultdict(list)
    eligible_marked_rows = {}
    marker_exclusions = collections.Counter()
    text = raw.decode("utf-8", errors="strict")
    lines = text.splitlines()
    for line_number, line in enumerate(lines, 1):
        marker = bool(FAKE_MARKER_RE.search(line))
        if ":" not in line:
            if marker:
                marker_exclusions["missing_colon"] += 1
            continue
        decomposition, gloss = line.split(":", 1)
        decomposition = decomposition.lstrip("\ufeff").strip()
        if not decomposition:
            if marker:
                marker_exclusions["empty_decomposition"] += 1
            continue
        if " " in decomposition:
            if marker:
                marker_exclusions["contains_space"] += 1
            continue
        if decomposition.startswith("-") or decomposition.endswith("-"):
            if marker:
                marker_exclusions["edge_affix"] += 1
            continue
        surface = canonical(
            "".join(piece for piece in decomposition.split("/") if piece)
        )
        if not evaluable(surface):
            if marker:
                marker_exclusions["non_evaluable_surface"] += 1
            continue
        record = {
            "decomposition": "/".join(
                canonical(piece)
                for piece in decomposition.split("/") if canonical(piece)
            ),
            "marker": marker,
            "line": line_number,
            "surface": surface,
        }
        records[surface].append(record)
        if marker:
            eligible_marked_rows[line_number] = record

    fake_coarse_by_line, fake_coarse_identity = load_fake_coarse_reference(
        raw, lines, eligible_marked_rows, marker_exclusions,
    )
    (
        phase511_transition_lines,
        phase511_transition_by_line,
        phase511_transition_identity,
    ) = load_fake_coarse_phase511_transition(
        fake_coarse_by_line, fake_coarse_identity,
    )
    historical_transition_lines, historical_transition_identity = load_fake_coarse_transition(
        fake_coarse_by_line,
        {45205: phase511_transition_by_line[45205]},
    )
    ff33_transition_lines, ff33_transition_identity = (
        load_fake_coarse_ff33_transition(fake_coarse_by_line)
    )
    final_5e_transition_lines, final_5e_transition_identity = (
        load_fake_coarse_5e_transition(fake_coarse_by_line)
    )
    transition_scopes = (
        historical_transition_lines,
        ff33_transition_lines,
        final_5e_transition_lines,
        phase511_transition_lines,
    )
    if sum(len(scope) for scope in transition_scopes) != len(
        set().union(*transition_scopes)
    ):
        raise ValueError("fake transition scopes overlap")
    transition_lines = set().union(*transition_scopes)
    transition_identity = {
        "historical_c679_b090": historical_transition_identity,
        "ff33_delta": ff33_transition_identity,
        "final_5e_delta": final_5e_transition_identity,
        "phase511_delta": phase511_transition_identity,
        "evaluable_entries": len(transition_lines),
        "full_master_only_entries": historical_transition_identity[
            "full_master_only_entries"
        ],
    }

    included = excluded_fake = 0
    official_overridden = project_boundary_overridden = 0
    mixed_marker_surfaces = []
    unmarked_conflicts = []
    duplicate_surfaces = sum(len(rows) > 1 for rows in records.values())
    duplicate_rows = sum(max(0, len(rows) - 1) for rows in records.values())
    for surface, surface_records in sorted(records.items()):
        has_marked = any(record["marker"] for record in surface_records)
        has_unmarked = any(not record["marker"] for record in surface_records)
        if has_marked and has_unmarked:
            mixed_marker_surfaces.append(surface)
        if surface in REVIEWED_GOLD_OVERRIDES:
            decompositions = [REVIEWED_GOLD_OVERRIDES[surface]]
            if surface in PROJECT_RUBY_BOUNDARY_OVERRIDES:
                sources = ["gold_project_ruby_boundary_override"]
                project_boundary_overridden += 1
            else:
                sources = ["gold_official_override"]
                official_overridden += 1
        elif not has_unmarked:
            excluded_fake += 1
            continue
        else:
            by_signature = {}
            for record in surface_records:
                if record["marker"]:
                    continue
                decomposition = record["decomposition"]
                atomic_hyphen_pieces = reviewed_atomic_hyphen_pieces(
                    surface, decomposition, atomic_hyphen_review,
                )
                if atomic_hyphen_pieces:
                    used_atomic_hyphen_reviews.add(surface)
                by_signature.setdefault(
                    expected_signature(decomposition, atomic_hyphen_pieces),
                    decomposition,
                )
            decompositions = list(by_signature.values())
            sources = ["gold_unmarked"] * len(decompositions)
            included += 1
            if len(decompositions) > 1:
                unmarked_conflicts.append({
                    "surface": surface,
                    "decompositions": sorted(decompositions),
                    "lines": sorted(
                        record["line"] for record in surface_records
                        if not record["marker"]
                    ),
                })
        for decomposition, source in zip(decompositions, sources):
            atomic_hyphen_pieces = reviewed_atomic_hyphen_pieces(
                surface, decomposition, atomic_hyphen_review,
            )
            if atomic_hyphen_pieces:
                used_atomic_hyphen_reviews.add(surface)
            add_case(
                cases, surface, expected_signature(
                    decomposition, atomic_hyphen_pieces,
                ),
                decomposition, source, 1,
            )
    fake_coarse_surfaces = set()
    fake_coarse_sources = collections.Counter()
    selected_fake_lines = (
        set(fake_coarse_by_line) if enforce_all_fake_coarse
        else transition_lines
    )
    for line_number, entry in sorted(fake_coarse_by_line.items()):
        if line_number not in selected_fake_lines:
            continue
        surface = entry["surface"]
        decomposition = entry["coarse_decomposition"]
        if surface in REVIEWED_GOLD_OVERRIDES:
            # Reviewed gold overrides remain the stronger project authority,
            # but the paired line is still exhaustively validated by the
            # manifest loader above.
            continue
        atomic_hyphen_pieces = reviewed_atomic_hyphen_pieces(
            surface, decomposition, atomic_hyphen_review,
        )
        if atomic_hyphen_pieces:
            used_atomic_hyphen_reviews.add(surface)
        source = f"gold_fake_coarse_{entry['authority']}"
        add_case(
            cases, surface,
            expected_signature(decomposition, atomic_hyphen_pieces),
            decomposition, source, 1,
        )
        fake_coarse_surfaces.add(surface)
        fake_coarse_sources[source] += 1
    for surface, decomposition in REVIEWED_GOLD_OVERRIDES.items():
        if surface in records:
            continue
        if surface in PROJECT_RUBY_BOUNDARY_OVERRIDES:
            source = "gold_project_ruby_boundary_override"
            project_boundary_overridden += 1
        else:
            source = "gold_official_override"
            official_overridden += 1
        add_case(
            cases, surface, expected_signature(decomposition), decomposition,
            source, 1,
        )
    if used_atomic_hyphen_reviews != set(atomic_hyphen_review):
        missing = sorted(set(atomic_hyphen_review) - used_atomic_hyphen_reviews)
        raise ValueError(f"unused atomic-hyphen reviews: {missing!r}")
    return {
        "path": str(path.resolve()),
        "sha256": digest,
        "expected_sha256": expected_sha256,
        "bytes": len(raw),
        "mtime_ns": snapshot_identity["mtime_ns"],
        "consistent_snapshot": True,
        "lines": len(lines),
        "nul_bytes": raw.count(b"\x00"),
        "replacement_chars": text.count("\ufffd"),
        "selected_records": len(records),
        "included_unmarked": included,
        "excluded_fake": excluded_fake,
        "included_fake_coarse_entries": sum(fake_coarse_sources.values()),
        "included_fake_coarse_surfaces": len(fake_coarse_surfaces),
        "fake_coarse_sources": dict(fake_coarse_sources),
        "fake_coarse_reference": fake_coarse_identity,
        "fake_coarse_transition": transition_identity,
        "fake_coarse_enforcement": (
            "all_evaluable" if enforce_all_fake_coarse else "reviewed_transitions"
        ),
        "official_overrides": official_overridden,
        "project_ruby_boundary_overrides": project_boundary_overridden,
        "duplicate_surfaces": duplicate_surfaces,
        "duplicate_rows": duplicate_rows,
        "mixed_marker_surfaces": len(mixed_marker_surfaces),
        "mixed_marker_surface_list": mixed_marker_surfaces,
        "unmarked_conflicts": unmarked_conflicts,
        "atomic_hyphen_review": atomic_hyphen_identity,
    }


def reference_conflicts(cases):
    by_surface = collections.defaultdict(list)
    for case in cases.values():
        by_surface[case["surface"]].append(case)
    conflicts = []
    for surface, surface_cases in sorted(by_surface.items()):
        signatures = {case["signature"] for case in surface_cases}
        if len(signatures) <= 1:
            continue
        conflicts.append({
            "surface": surface,
            "options": sorted([
                {
                    "expected": case["expected"],
                    "signature": signature_payload(case["signature"]),
                    "sources": dict(sorted(case["sources"].items())),
                }
                for case in surface_cases
            ], key=lambda item: json.dumps(item, ensure_ascii=True, sort_keys=True)),
        })
    return conflicts


def reference_fingerprint(cases):
    rows = sorted([
        {
            "surface": case["surface"],
            "expected": case["expected"],
            "signature": signature_payload(case["signature"]),
            "sources": dict(sorted(case["sources"].items())),
        }
        for case in cases.values()
    ], key=lambda item: json.dumps(item, ensure_ascii=True, sort_keys=True))
    return stable_json_sha256(rows)


def corpus_content_fingerprint(corpus_root: Path):
    rows = []
    for content_dir in CONTENT_DIRS:
        for path in sorted((corpus_root / content_dir).rglob("*")):
            if path.is_file() and path.suffix.lower() in {".html", ".htm"}:
                rows.append([
                    path.relative_to(corpus_root).as_posix(),
                    hashlib.sha256(path.read_bytes()).hexdigest().upper(),
                ])
    return {"files": len(rows), "sha256": stable_json_sha256(rows)}


def git_head_oid():
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if completed.returncode:
        raise RuntimeError(
            completed.stderr.decode("utf-8", errors="replace")
        )
    return completed.stdout.decode("ascii").strip()


def git_repo_state(repo: Path):
    def run(*args, binary=False):
        completed = subprocess.run(
            ["git", *args], cwd=repo, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=False,
        )
        if completed.returncode:
            raise RuntimeError(
                completed.stderr.decode("utf-8", errors="replace")
            )
        return completed.stdout if binary else completed.stdout.decode(
            "utf-8", errors="strict"
        ).strip()

    status = run(
        "status", "--porcelain=v2", "-z", "--untracked-files=all",
        binary=True,
    )
    return {
        "head_oid": run("rev-parse", "HEAD"),
        "branch": run("branch", "--show-current"),
        "status_entries": status.count(b"\x00"),
        "status_sha256": hashlib.sha256(status).hexdigest().upper(),
    }


def scope_projection(scope, cases, surfaces, conflicts):
    corpus = scope["corpus"]
    gold = scope["gold"]
    return {
        "schema_version": REFERENCE_SCHEMA_VERSION,
        "case_count": len(cases),
        "surface_count": len(surfaces),
        "reference_sha256": reference_fingerprint(cases),
        "reference_conflict_count": len(conflicts),
        "reference_conflicts_sha256": stable_json_sha256(conflicts),
        "corpus": {
            key: corpus[key]
            for key in (
                "files", "raw_ruby", "parsed_ruby", "parsed_units",
                "eligible_units", "word_alphabet_units",
                "extended_reference_units",
                "extended_reference_unique_rows",
                "extended_reference_unique_surfaces",
                "extended_reference_reasons",
                "extended_reference_sha256", "case_preserved_instances",
                "excluded_units", "content_sha256",
            )
        },
        "corpus_repository": scope["corpus_repository"],
        "place_manifest": scope["place_manifest"],
        "gold": {
            key: gold[key]
            for key in (
                "sha256", "bytes", "lines", "nul_bytes",
                "replacement_chars", "selected_records",
                "included_unmarked", "excluded_fake", "official_overrides",
                "project_ruby_boundary_overrides",
                "included_fake_coarse_entries",
                "included_fake_coarse_surfaces", "fake_coarse_sources",
                "fake_coarse_reference", "fake_coarse_transition",
                "fake_coarse_enforcement",
                "duplicate_surfaces", "duplicate_rows",
                "mixed_marker_surfaces",
                "atomic_hyphen_review",
            )
        },
    }


def validate_reviewed_reference_scope(projection, conflicts):
    scope_path = HERE / "_no_worsening_scope_manifest.json"
    conflict_path = HERE / "_no_worsening_reference_conflicts.json"
    expected_scope = json.loads(scope_path.read_text(encoding="utf-8"))
    if expected_scope.get("manifest_schema_version") != 1:
        raise ValueError("unsupported no-worsening scope manifest schema")
    if expected_scope.get("projection_sha256") != stable_json_sha256(projection):
        raise ValueError("scope manifest projection fingerprint mismatch")
    if expected_scope.get("expected") != projection:
        raise ValueError(
            "reference scope changed; inspect the references-only candidate "
            "before updating _no_worsening_scope_manifest.json"
        )
    reviewed_conflicts = json.loads(conflict_path.read_text(encoding="utf-8"))
    if reviewed_conflicts.get("manifest_schema_version") != 1:
        raise ValueError("unsupported reference-conflict manifest schema")
    if (
        reviewed_conflicts.get("reference_schema_version")
        != REFERENCE_SCHEMA_VERSION
    ):
        raise ValueError("reference-conflict manifest uses a stale schema")
    if (
        reviewed_conflicts.get("raw_conflicts_sha256")
        != stable_json_sha256(conflicts)
    ):
        raise ValueError("reference-conflict manifest fingerprint mismatch")
    reviewed_entries = reviewed_conflicts.get("entries", [])
    expected_conflicts = [
        {
            "surface": entry["surface"],
            "options": entry["options"],
        }
        for entry in reviewed_entries
    ]
    if expected_conflicts != conflicts:
        raise ValueError(
            "unreviewed reference conflict change; inspect and update "
            "_no_worsening_reference_conflicts.json"
        )
    allowed_by_surface = {}
    for entry, conflict in zip(reviewed_entries, conflicts):
        if not entry.get("category") or not entry.get("reason"):
            raise ValueError(
                f"reference conflict lacks review rationale: {entry['surface']}"
            )
        available = {
            signature_from_payload(option["signature"])
            for option in conflict["options"]
        }
        allowed_payloads = entry.get("allowed_signatures", [])
        allowed = {
            signature_from_payload(payload) for payload in allowed_payloads
        }
        if not allowed or not allowed <= available:
            raise ValueError(
                "reference conflict has an empty or foreign resolution: "
                + entry["surface"]
            )
        if len(allowed) != len(allowed_payloads):
            raise ValueError(
                f"duplicate allowed signature: {entry['surface']}"
            )
        allowed_by_surface[entry["surface"]] = allowed
    metadata = {
        "scope_manifest": str(scope_path),
        "scope_manifest_sha256": hashlib.sha256(
            scope_path.read_bytes()
        ).hexdigest().upper(),
        "conflict_manifest": str(conflict_path),
        "conflict_manifest_sha256": hashlib.sha256(
            conflict_path.read_bytes()
        ).hexdigest().upper(),
        "reviewed_conflicts": len(conflicts),
        "contextual_multi_signature_conflicts": sum(
            len(allowed) > 1 for allowed in allowed_by_surface.values()
        ),
    }
    return metadata, allowed_by_surface


def resolve_reviewed_reference_cases(cases, allowed_by_surface):
    """Apply the human-reviewed decision for every conflicting surface."""
    resolved = {}
    for key, case in cases.items():
        allowed = allowed_by_surface.get(case["surface"])
        if allowed is None or case["signature"] in allowed:
            resolved[key] = case
    for surface, allowed in allowed_by_surface.items():
        retained = {
            case["signature"]
            for case in resolved.values() if case["surface"] == surface
        }
        if retained != allowed:
            raise ValueError(
                f"reviewed conflict resolution did not retain exactly its "
                f"allowed signatures: {surface}"
            )
    return resolved


def runtime_module(app_dir: Path, language: str):
    path = app_dir / "esp_text_replacement_module.py"
    spec = importlib.util.spec_from_file_location(
        f"no_worsening_runtime_{language}", path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def overlay_module(app_dir: Path, language: str):
    path = app_dir / "esp_overlay_module.py"
    if str(app_dir) not in sys.path:
        sys.path.insert(0, str(app_dir))
    spec = importlib.util.spec_from_file_location(
        f"no_worsening_overlay_{language}", path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def head_runtime_module(app_dir: Path, language: str, revision: str):
    relative_path = (
        app_dir.relative_to(ROOT) / "esp_text_replacement_module.py"
    )
    module = types.ModuleType(f"head_no_worsening_runtime_{language}")
    module.__file__ = "HEAD:" + relative_path.as_posix()
    source = load_head_text(relative_path, revision)
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    return module


def head_overlay_module(app_dir: Path, language: str, revision: str):
    relative_path = app_dir.relative_to(ROOT) / "esp_overlay_module.py"
    module = types.ModuleType(f"head_no_worsening_overlay_{language}")
    module.__file__ = "HEAD:" + relative_path.as_posix()
    source = load_head_text(relative_path, revision)
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    return module


def extract_lists(payload):
    global_rules = next(
        value for key, value in payload.items() if "replacements_final_list" in key
    )
    local_rules = next(
        value for key, value in payload.items() if "localized_string" in key
    )
    two_char_rules = next(
        value for key, value in payload.items() if "replacements_list_for_2char" in key
    )
    return local_rules, global_rules, two_char_rules


def load_head_payload(relative_path: Path, revision: str):
    command = ["git", "show", revision + ":" + relative_path.as_posix()]
    process = subprocess.Popen(
        command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    try:
        text_stream = io.TextIOWrapper(process.stdout, encoding="utf-8")
        payload = json.load(text_stream)
        text_stream.detach()
        stderr = process.stderr.read().decode("utf-8", errors="replace")
        return_code = process.wait()
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
    if return_code:
        raise RuntimeError(f"git show failed ({return_code}): {stderr}")
    return payload


def load_head_bytes(relative_path: Path, revision: str) -> bytes:
    completed = subprocess.run(
        ["git", "show", revision + ":" + relative_path.as_posix()],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(
            "git show failed: "
            + completed.stderr.decode("utf-8", errors="replace")
        )
    return completed.stdout


def load_head_text(relative_path: Path, revision: str):
    return load_head_bytes(relative_path, revision).decode("utf-8")


def overlay_entries_from_corrections(corrections, mode="ruby"):
    entries = []
    for index, correction in enumerate(corrections):
        if not isinstance(correction, dict):
            continue
        for pair_index, pair in enumerate(correction.get(mode, [])):
            if len(pair) >= 2 and pair[0] and pair[1]:
                entries.append([
                    pair[0], pair[1],
                    f"${9000000 + index * 10 + pair_index}$",
                ])
    return entries


def render_effective_text(
    module, overlay, text, skip, local_rules, local_capture,
    global_rules, two_char_rules, data_dir, corrections,
):
    """Mirror ``main.py`` baseline overlay and automatic second pass."""
    if overlay is None:
        return module.orchestrate_comprehensive_esperanto_text_replacement(
            text, skip, local_rules, local_capture, global_rules,
            two_char_rules, FORMAT,
        )
    baseline_entries = overlay_entries_from_corrections(corrections, "ruby")
    effective_global = overlay.merge_overlay(global_rules, baseline_entries)
    return overlay.autofix_render(
        text, skip, local_rules, local_capture, effective_global,
        two_char_rules, FORMAT, str(data_dir), "ruby",
        module.orchestrate_comprehensive_esperanto_text_replacement,
    )


def render_signatures(
    module, app_dir: Path, payload, surfaces, batch_size,
    placeholder_lists=None, overlay=None, corrections=None,
    data_dir_override: Path | None = None,
):
    local_rules, global_rules, two_char_rules = extract_lists(payload)
    data_dir = (
        Path(data_dir_override)
        if data_dir_override is not None
        else app_dir / "app_data"
    )
    if placeholder_lists is None:
        skip = module.import_placeholders(str(data_dir / "placeholders_skip.txt"))
        local_capture = module.import_placeholders(
            str(data_dir / "placeholders_localcapture.txt")
        )
    else:
        skip, local_capture = placeholder_lists
    results = {}
    for start in range(0, len(surfaces), batch_size):
        batch = surfaces[start:start + batch_size]
        rendered = render_effective_text(
            module, overlay,
            "\n".join(f" {surface} " for surface in batch),
            skip, local_rules, local_capture, global_rules, two_char_rules,
            data_dir, corrections or [],
        )
        lines = rendered.splitlines()
        if len(lines) != len(batch):
            raise RuntimeError(
                f"runtime line accounting failed: {len(lines)} != {len(batch)}"
            )
        for surface, line in zip(batch, lines):
            parts = rendered_typed_parts(line)
            results[surface] = {
                "signature": signature_from_typed_parts(parts),
                "decomposition": display_parts(parts),
                "typed_decomposition": display_typed_parts(parts),
            }
        print(
            f"    rendered {min(start + len(batch), len(surfaces))}/{len(surfaces)}",
            flush=True,
        )
    return results


def save_phase_checkpoint(
    language, phase, results, input_fingerprint, checkpoint_context,
):
    path = HERE / "out" / f"_no_worsening_checkpoint_{language}_{phase}.json"
    serial_results = {
        surface: {
            "signature": signature_payload(value["signature"]),
            "decomposition": value["decomposition"],
            "typed_decomposition": value["typed_decomposition"],
        }
        for surface, value in results.items()
    }
    atomic_json_dump(path, {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "language": language,
        "phase": phase,
        "surface_count": len(results),
        "input_fingerprint": input_fingerprint,
        "context": checkpoint_context,
        "results": serial_results,
    })
    print(f"[{language}] atomic checkpoint saved: {phase}", flush=True)


def resume_context_matches(saved_context, current_context):
    """Accept a partial audit only from the identical render/comparison code.

    The explicitly pinned predecessor hash is allowed solely because the only
    source change is this loader.  Every reference, repository and manifest
    identity remains mandatory.
    """
    if not isinstance(saved_context, dict):
        return False
    saved = dict(saved_context)
    current = dict(current_context)
    saved_audit = saved.pop("audit_code_sha256", None)
    current_audit = current.pop("audit_code_sha256", None)
    return (
        saved == current
        and saved_audit in (
            {current_audit} | RESUME_COMPATIBLE_AUDIT_CODE_SHA256
        )
    )


def current_app_fingerprint(app_dir):
    language_csv = {
        "Esperanto-Kanji-Ruby-JA": "エスペラント語根-日本語訳ルビ対応リスト.csv",
        "Esperanto-Kanji-Ruby-ZH": "世界语词根-中文注释对应列表.csv",
        "Esperanto-Kanji-Ruby-KO": "에스페란토 어근-한국어 번역 루비 대응 목록.csv",
    }[app_dir.name]
    paths = [
        app_dir / "main.py",
        app_dir / "esp_text_replacement_module.py",
        app_dir / "esp_overlay_module.py",
        app_dir / "esp_replacement_json_make_module.py",
        app_dir / "app_data" / "置換リスト_ルビ.json",
        app_dir / "app_data" / "placeholders_skip.txt",
        app_dir / "app_data" / "placeholders_localcapture.txt",
        app_dir / "app_data" / "char_widths.json",
        app_dir / "app_data" / language_csv,
        app_dir / "app_data" / "世界语词根-汉字对应列表_参照2新割当_7791.csv",
        app_dir / "app_data" / "user_corrections.json",
    ]
    return {
        str(path.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(
            path.read_bytes()
        ).hexdigest().upper()
        for path in paths
    }


def _semantic_text_bytes(raw: bytes) -> bytes:
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def materialize_head_overlay_dependencies(
    app_dir, overlay, revision, isolated_data_dir,
):
    """Materialize HEAD overlay data without reading working-tree dictionaries.

    ``esp_overlay_module`` builds automatic corrections from the language Ruby
    CSV, the shared Kanji CSV, and ``char_widths.json``.  Those dictionaries are
    legitimate generated outputs of this change, so requiring them to equal
    HEAD would make the historical baseline impossible to render.  Instead,
    copy their exact HEAD bytes into an isolated directory and point only the
    HEAD-overlay phase there.

    The helper module imported lazily by the overlay remains code, not data. It
    is therefore required to be semantically identical to HEAD; otherwise a
    subprocess/import sandbox would be needed to reproduce it faithfully.
    """
    current_data_dir = app_dir / "app_data"
    ruby_csv = Path(overlay._ruby_csv(str(current_data_dir))).name
    code_relative = (
        app_dir.relative_to(ROOT) / "esp_replacement_json_make_module.py"
    )
    head_code = load_head_bytes(code_relative, revision)
    current_code = (ROOT / code_relative).read_bytes()
    if _semantic_text_bytes(head_code) != _semantic_text_bytes(current_code):
        raise ValueError(
            f"HEAD overlay code dependency differs in working tree: "
            f"{code_relative}"
        )

    data_relatives = [
        app_dir.relative_to(ROOT) / "app_data" / "char_widths.json",
        app_dir.relative_to(ROOT) / "app_data" / ruby_csv,
        app_dir.relative_to(ROOT) / "app_data" / overlay.KANJI_CSV,
    ]
    isolated_data_dir = Path(isolated_data_dir)
    isolated_data_dir.mkdir(parents=True, exist_ok=True)
    fingerprints = {}
    fingerprints[code_relative.as_posix()] = hashlib.sha256(
        _semantic_text_bytes(head_code)
    ).hexdigest().upper()
    for relative in data_relatives:
        head_raw = load_head_bytes(relative, revision)
        destination = isolated_data_dir / relative.name
        destination.write_bytes(head_raw)
        if destination.read_bytes() != head_raw:
            raise IOError(f"failed to materialize HEAD overlay data: {relative}")
        fingerprints[relative.as_posix()] = hashlib.sha256(
            _semantic_text_bytes(head_raw)
        ).hexdigest().upper()
    return fingerprints


def compare_outputs(language, label, baseline, current, cases, surfaces):
    source_stats = collections.defaultdict(lambda: collections.Counter())
    regressions = []
    changed_to_unreferenced_wrong = []
    current_unreferenced_wrong = []
    current_manifest_wrong = []
    current_override_wrong = []
    current_project_boundary_override_wrong = []
    expected_signatures_by_surface = collections.defaultdict(set)
    cases_by_surface = collections.defaultdict(list)
    for case in cases.values():
        expected_signatures_by_surface[case["surface"]].add(case["signature"])
        cases_by_surface[case["surface"]].append(case)
    for surface in surfaces:
        old_result = baseline[surface]
        current_result = current[surface]
        old_surface_ok = (
            old_result["signature"] in expected_signatures_by_surface[surface]
        )
        current_surface_ok = (
            current_result["signature"] in expected_signatures_by_surface[surface]
        )
        if old_surface_ok and not current_surface_ok:
            regressions.append({
                "surface": surface,
                "expected_options": sorted({
                    case["expected"] for case in cases_by_surface[surface]
                }),
                "sources": sorted({
                    source
                    for case in cases_by_surface[surface]
                    for source in case["sources"]
                }),
                "baseline": old_result["decomposition"],
                "baseline_typed": old_result["typed_decomposition"],
                "current": current_result["decomposition"],
                "current_typed": current_result["typed_decomposition"],
            })
        if current_result["signature"] not in expected_signatures_by_surface[surface]:
            current_unreferenced_wrong.append({
                "surface": surface,
                "expected_options": sorted({
                    case["expected"] for case in cases_by_surface[surface]
                }),
                "expected_signatures": [
                    signature_payload(signature)
                    for signature in sorted(
                        expected_signatures_by_surface[surface], key=repr
                    )
                ],
                "sources": sorted({
                    source
                    for case in cases_by_surface[surface]
                    for source in case["sources"]
                }),
                "baseline": old_result["decomposition"],
                "baseline_typed": old_result["typed_decomposition"],
                "current": current_result["decomposition"],
                "current_typed": current_result["typed_decomposition"],
                "current_signature": signature_payload(
                    current_result["signature"]
                ),
            })
        if (
            old_result["signature"] != current_result["signature"]
            and current_result["signature"] not in expected_signatures_by_surface[surface]
        ):
            changed_to_unreferenced_wrong.append({
                "surface": surface,
                "expected_options": sorted({
                    case["expected"] for case in cases_by_surface[surface]
                }),
                "sources": sorted({
                    source
                    for case in cases_by_surface[surface]
                    for source in case["sources"]
                }),
                "baseline": old_result["decomposition"],
                "baseline_typed": old_result["typed_decomposition"],
                "current": current_result["decomposition"],
                "current_typed": current_result["typed_decomposition"],
            })
    for case in cases.values():
        surface = case["surface"]
        expected = case["signature"]
        old_result = baseline[surface]
        current_result = current[surface]
        allowed = expected_signatures_by_surface[surface]
        # Multiple reviewed signatures are contextual alternatives, not
        # simultaneous obligations on a context-free app renderer.
        old_ok = old_result["signature"] in allowed
        current_ok = current_result["signature"] in allowed
        exact_current_ok = current_result["signature"] == expected
        record = {
            "surface": surface,
            "expected": case["expected"],
            "sources": dict(case["sources"]),
            "baseline": old_result["decomposition"],
            "baseline_typed": old_result["typed_decomposition"],
            "current": current_result["decomposition"],
            "current_typed": current_result["typed_decomposition"],
            "expected_signature": signature_payload(expected),
        }
        if "html_place_manifest" in case["sources"] and not exact_current_ok:
            current_manifest_wrong.append(record)
        if "gold_official_override" in case["sources"] and not exact_current_ok:
            current_override_wrong.append(record)
        if (
            "gold_project_ruby_boundary_override" in case["sources"]
            and not exact_current_ok
        ):
            current_project_boundary_override_wrong.append(record)
        for source, weight in case["sources"].items():
            stats = source_stats[source]
            source_old_ok = (
                old_result["signature"] == expected
                if source in EXACT_REQUIRED_REFERENCE_SOURCES
                else old_ok
            )
            source_current_ok = (
                current_result["signature"] == expected
                if source in EXACT_REQUIRED_REFERENCE_SOURCES
                else current_ok
            )
            stats["total_weight"] += weight
            stats["total_cases"] += 1
            if source_old_ok:
                stats["baseline_correct_weight"] += weight
                stats["baseline_correct_cases"] += 1
            if source_current_ok:
                stats["current_correct_weight"] += weight
                stats["current_correct_cases"] += 1
            if source_old_ok and not source_current_ok:
                stats["regression_weight"] += weight
                stats["regression_cases"] += 1
            if not source_old_ok and source_current_ok:
                stats["improvement_weight"] += weight
                stats["improvement_cases"] += 1

    weighted_worsening = []
    serial_stats = {}
    metric_keys = (
        "total_weight", "total_cases",
        "baseline_correct_weight", "baseline_correct_cases",
        "current_correct_weight", "current_correct_cases",
        "regression_weight", "regression_cases",
        "improvement_weight", "improvement_cases",
    )
    for source, stats in sorted(source_stats.items()):
        serial_stats[source] = {key: stats[key] for key in metric_keys}
        if stats["current_correct_weight"] < stats["baseline_correct_weight"]:
            weighted_worsening.append(source)
        print(
            f"[{language}/{label}] {source}: total={stats['total_weight']} "
            f"correct {stats['baseline_correct_weight']} -> "
            f"{stats['current_correct_weight']}, "
            f"regressions={stats['regression_weight']}, "
            f"improvements={stats['improvement_weight']}",
            flush=True,
        )
    combined = {
        key: sum(stats[key] for stats in source_stats.values())
        for key in metric_keys
    }
    if combined["current_correct_weight"] < combined["baseline_correct_weight"]:
        weighted_worsening.append("combined")
    print(
        f"[{language}/{label}] combined: total={combined['total_weight']} "
        f"correct {combined['baseline_correct_weight']} -> "
        f"{combined['current_correct_weight']}, "
        f"regressions={combined['regression_weight']}, "
        f"improvements={combined['improvement_weight']}",
        flush=True,
    )

    result = {
        "comparison": label,
        "sources": serial_stats,
        "combined": combined,
        "regression_cases": regressions,
        "changed_to_unreferenced_wrong_surfaces": changed_to_unreferenced_wrong,
        "current_unreferenced_wrong_surfaces": current_unreferenced_wrong,
        "current_place_manifest_wrong_cases": current_manifest_wrong,
        "current_official_override_wrong_cases": current_override_wrong,
        "current_project_ruby_boundary_override_wrong_cases": (
            current_project_boundary_override_wrong
        ),
        "weighted_worsening_sources": weighted_worsening,
    }
    result["gate"] = not any((
        regressions,
        changed_to_unreferenced_wrong,
        current_unreferenced_wrong,
        current_manifest_wrong,
        current_override_wrong,
        current_project_boundary_override_wrong,
        weighted_worsening,
    ))
    return result


def evaluate_language(
    language, cases, surfaces, batch_size, revision, checkpoint_context,
    expected_input_fingerprint,
):
    app_dir = ROOT / f"Esperanto-Kanji-Ruby-{language}"
    ruby_relative = app_dir.relative_to(ROOT) / "app_data" / "置換リスト_ルビ.json"
    input_fingerprint_before = current_app_fingerprint(app_dir)
    if input_fingerprint_before != expected_input_fingerprint:
        raise ValueError(f"{language} input changed before its audit started")
    current_module = runtime_module(app_dir, language)
    current_overlay = overlay_module(app_dir, language)
    historical_module = head_runtime_module(app_dir, language, revision)
    historical_overlay = head_overlay_module(app_dir, language, revision)
    corrections_relative = (
        app_dir.relative_to(ROOT) / "app_data" / "user_corrections.json"
    )
    current_corrections = json.loads(
        (ROOT / corrections_relative).read_text(encoding="utf-8")
    )
    head_corrections = json.loads(
        load_head_text(corrections_relative, revision)
    )
    head_placeholder_lists = tuple(
        [
            line.strip()
            for line in load_head_text(
                app_dir.relative_to(ROOT) / "app_data" / filename,
                revision,
            ).splitlines()
            if line.strip()
        ]
        for filename in ("placeholders_skip.txt", "placeholders_localcapture.txt")
    )

    with tempfile.TemporaryDirectory(
        prefix=f"no_worsening_head_overlay_{language.lower()}_"
    ) as temporary_directory:
        isolated_head_data_dir = Path(temporary_directory) / "app_data"
        head_overlay_dependencies = materialize_head_overlay_dependencies(
            app_dir, historical_overlay, revision, isolated_head_data_dir,
        )

        print(f"[{language}] HEAD data + current runtime rendering", flush=True)
        baseline_payload = load_head_payload(ruby_relative, revision)
        data_isolated_baseline = render_signatures(
            current_module, app_dir, baseline_payload, surfaces, batch_size,
            overlay=current_overlay, corrections=current_corrections,
        )
        save_phase_checkpoint(
            language, "head_data_current_runtime", data_isolated_baseline,
            input_fingerprint_before, checkpoint_context,
        )
        print(f"[{language}] HEAD data + HEAD runtime rendering", flush=True)
        # The historical overlay imports its helper lazily under a generic
        # module name.  Activate this language's exact sibling path before the
        # render so a preceding JA/ZH/KO phase cannot leak its cached helper.
        load_app_replacement_helper(app_dir)
        comprehensive_baseline = render_signatures(
            historical_module, app_dir, baseline_payload, surfaces, batch_size,
            placeholder_lists=head_placeholder_lists,
            overlay=historical_overlay, corrections=head_corrections,
            data_dir_override=isolated_head_data_dir,
        )
        save_phase_checkpoint(
            language, "head_data_head_runtime", comprehensive_baseline,
            input_fingerprint_before, checkpoint_context,
        )
    del baseline_payload
    gc.collect()

    print(f"[{language}] current data + current runtime rendering", flush=True)
    current_payload = json.loads(
        (ROOT / ruby_relative).read_text(encoding="utf-8")
    )
    current = render_signatures(
        current_module, app_dir, current_payload, surfaces, batch_size,
        overlay=current_overlay, corrections=current_corrections,
    )
    save_phase_checkpoint(
        language, "current_data_current_runtime", current,
        input_fingerprint_before, checkpoint_context,
    )
    del current_payload
    gc.collect()

    data_isolated = compare_outputs(
        language, "data_isolated", data_isolated_baseline, current,
        cases, surfaces,
    )
    comprehensive = compare_outputs(
        language, "comprehensive", comprehensive_baseline, current,
        cases, surfaces,
    )
    input_fingerprint_after = current_app_fingerprint(app_dir)
    current_input_stable = input_fingerprint_after == input_fingerprint_before
    result = {
        "language": language,
        "data_isolated_definition": (
            "HEAD Ruby JSON + current runtime -> working-tree Ruby JSON + current runtime"
        ),
        "comprehensive_definition": (
            "HEAD Ruby JSON + HEAD runtime -> working-tree Ruby JSON + current runtime"
        ),
        "data_isolated": data_isolated,
        "comprehensive": comprehensive,
        "current_input_fingerprint": input_fingerprint_before,
        "head_overlay_dependency_fingerprint": head_overlay_dependencies,
        "current_input_stable_during_language_audit": current_input_stable,
        "gate": (
            current_input_stable
            and data_isolated["gate"]
            and comprehensive["gate"]
        ),
    }
    del data_isolated_baseline, comprehensive_baseline, current
    gc.collect()
    return result


def benchmark_batches(language, surfaces, batch_sizes, sample_size):
    """Read-only timing helper; validates the same renderer and line accounting."""
    app_dir = ROOT / f"Esperanto-Kanji-Ruby-{language}"
    ruby_path = app_dir / "app_data" / "置換リスト_ルビ.json"
    module = runtime_module(app_dir, language)
    overlay = overlay_module(app_dir, language)
    corrections = json.loads(
        (app_dir / "app_data" / "user_corrections.json").read_text(
            encoding="utf-8"
        )
    )
    payload = json.loads(ruby_path.read_text(encoding="utf-8"))
    sample_size = min(sample_size, len(surfaces))
    if sample_size == len(surfaces):
        sample = list(surfaces)
    else:
        sample = [
            surfaces[index * len(surfaces) // sample_size]
            for index in range(sample_size)
        ]
    timings = []
    for batch_size in batch_sizes:
        started = time.perf_counter()
        rendered = render_signatures(
            module, app_dir, payload, sample, batch_size,
            overlay=overlay, corrections=corrections,
        )
        elapsed = time.perf_counter() - started
        if len(rendered) != len(sample):
            raise RuntimeError(
                f"benchmark result accounting failed: {len(rendered)} != {len(sample)}"
            )
        timings.append({
            "batch_size": batch_size,
            "sample_surfaces": len(sample),
            "seconds": round(elapsed, 3),
        })
        print(json.dumps(timings[-1], ensure_ascii=False), flush=True)
        del rendered
        gc.collect()
    del payload
    gc.collect()
    print(json.dumps({"benchmark": timings}, ensure_ascii=False, indent=1))


def evaluate_current_only(
    language, cases, surfaces, batch_size, expected_input_fingerprint,
):
    """Fast preflight: render only deployed current inputs, with full gate."""
    app_dir = ROOT / f"Esperanto-Kanji-Ruby-{language}"
    before = current_app_fingerprint(app_dir)
    if before != expected_input_fingerprint:
        raise ValueError(f"{language} input changed before current-only audit")
    module = runtime_module(app_dir, language)
    overlay = overlay_module(app_dir, language)
    corrections = json.loads(
        (app_dir / "app_data" / "user_corrections.json").read_text(
            encoding="utf-8"
        )
    )
    ruby_path = app_dir / "app_data" / "置換リスト_ルビ.json"
    payload = json.loads(ruby_path.read_text(encoding="utf-8"))
    current = render_signatures(
        module, app_dir, payload, surfaces, batch_size,
        overlay=overlay, corrections=corrections,
    )
    comparison = compare_outputs(
        language, "current_only", current, current, cases, surfaces
    )
    after = current_app_fingerprint(app_dir)
    return {
        "language": language,
        "comparison": comparison,
        "input_fingerprint": before,
        "input_stable": after == before,
        "gate": comparison["gate"] and after == before,
    }


def print_comparison_result(language, label, comparison):
    print(
            f"[{language}/{label}] "
            f"old-correct->current-wrong="
            f"{len(comparison['regression_cases'])}, "
            f"changed-current-unreferenced-wrong="
            f"{len(comparison['changed_to_unreferenced_wrong_surfaces'])}, "
            f"all-current-unreferenced-wrong="
            f"{len(comparison['current_unreferenced_wrong_surfaces'])}, "
            f"current-place-wrong="
            f"{len(comparison['current_place_manifest_wrong_cases'])}, "
            f"current-official-override-wrong="
            f"{len(comparison['current_official_override_wrong_cases'])}, "
            f"current-project-boundary-override-wrong="
            f"{len(comparison['current_project_ruby_boundary_override_wrong_cases'])}, "
            f"gate={'PASS' if comparison['gate'] else 'FAIL'}",
            flush=True,
        )


def print_language_result(result):
    for label in ("data_isolated", "comprehensive"):
        print_comparison_result(result["language"], label, result[label])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=2000)
    parser.add_argument(
        "--languages", nargs="+", choices=("JA", "ZH", "KO"),
        default=["JA", "ZH", "KO"],
    )
    parser.add_argument("--benchmark-batch-sizes", nargs="+", type=int)
    parser.add_argument("--benchmark-surfaces", type=int, default=6000)
    parser.add_argument(
        "--references-only", action="store_true",
        help="Build the pinned reference candidate without rendering apps.",
    )
    parser.add_argument(
        "--enforce-all-fake-coarse", action="store_true",
        help=(
            "Promote every evaluable fake-row coarse authority to the gate. "
            "Default formal scope gates only the independently reviewed "
            "transition while the full-master audit reports the remaining queue."
        ),
    )
    parser.add_argument(
        "--current-only-diagnostic", action="store_true",
        help="Render only current deployed inputs as a faster strict preflight.",
    )
    parser.add_argument(
        "--resume-language-results", action="store_true",
        help=(
            "Resume a partial full audit only after validating its exact "
            "scope, HEAD, reference and per-app input fingerprints."
        ),
    )
    parser.add_argument(
        "--expected-gold-sha256",
        default=os.environ.get("ESP_EXPECTED_GOLD_SHA256"),
        help="Required hash of the pre-audited consistent gold snapshot.",
    )
    args = parser.parse_args()
    if not args.expected_gold_sha256:
        parser.error(
            "--expected-gold-sha256 (or ESP_EXPECTED_GOLD_SHA256) is required"
        )

    corpus_root = Path(os.environ.get(
        "ESP_CORPUS_PATH",
        ROOT / "_project_root_misc" / "京大エス研html文書＿Github",
    ))
    revision = git_head_oid()
    audit_code_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper()
    place_path = HERE / "_place_alignment_manifest.json"
    place_sha256 = hashlib.sha256(place_path.read_bytes()).hexdigest().upper()
    cases = {}
    gold_file = gold_path()
    gold_raw, gold_identity = consistent_snapshot(gold_file)
    scope = {
        "corpus": corpus_cases(cases, corpus_root),
        "corpus_repository": git_repo_state(corpus_root),
        "place_manifest": place_cases(cases),
        "gold": gold_cases(
            cases, gold_file, gold_raw, gold_identity,
            args.expected_gold_sha256,
            enforce_all_fake_coarse=args.enforce_all_fake_coarse,
        ),
    }
    del gold_raw
    surfaces = sorted({case["surface"] for case in cases.values()})
    conflicts = reference_conflicts(cases)
    projection = scope_projection(scope, cases, surfaces, conflicts)
    print(
        f"reference union: {len(cases)} cases / {len(surfaces)} surfaces / "
        f"conflicts={len(conflicts)} / gold SHA256={scope['gold']['sha256']}",
        flush=True,
    )
    if args.references_only:
        candidate_path = HERE / "out" / "_audit_no_worsening_references.json"
        atomic_json_dump(candidate_path, {
            "projection": projection,
            "conflicts": conflicts,
            "scope": scope,
            "scope_manifest_candidate": {
                "manifest_schema_version": 1,
                "projection_sha256": stable_json_sha256(projection),
                "expected": projection,
            },
            "conflict_manifest_skeleton": {
                "manifest_schema_version": 1,
                "reference_schema_version": REFERENCE_SCHEMA_VERSION,
                "raw_conflicts_sha256": stable_json_sha256(conflicts),
                "entries": [
                    {
                        "surface": conflict["surface"],
                        "options": conflict["options"],
                        "allowed_signatures": [],
                        "category": "TODO",
                        "reason": "TODO",
                    }
                    for conflict in conflicts
                ],
            },
        }, indent=1)
        print(f"saved reference candidate: {candidate_path}", flush=True)
        return
    reviewed_reference, allowed_by_surface = validate_reviewed_reference_scope(
        projection, conflicts
    )
    resolved_cases = resolve_reviewed_reference_cases(
        cases, allowed_by_surface
    )
    resolved_surfaces = sorted({
        case["surface"] for case in resolved_cases.values()
    })
    if resolved_surfaces != surfaces:
        raise ValueError("reviewed conflict resolution changed surface coverage")
    resolved_reference = {
        "case_count": len(resolved_cases),
        "surface_count": len(resolved_surfaces),
        "reference_sha256": reference_fingerprint(resolved_cases),
    }
    if args.benchmark_batch_sizes:
        benchmark_batches(
            args.languages[0], surfaces, args.benchmark_batch_sizes,
            args.benchmark_surfaces,
        )
        return
    app_fingerprints_at_start = {
        language: current_app_fingerprint(
            ROOT / f"Esperanto-Kanji-Ruby-{language}"
        )
        for language in args.languages
    }
    checkpoint_context = {
        "checkpoint_schema_version": CHECKPOINT_SCHEMA_VERSION,
        "reference_schema_version": REFERENCE_SCHEMA_VERSION,
        "head_oid": revision,
        "raw_reference_sha256": projection["reference_sha256"],
        "reference_sha256": resolved_reference["reference_sha256"],
        "surface_sha256": stable_json_sha256(resolved_surfaces),
        "corpus_sha256": projection["corpus"]["content_sha256"],
        "corpus_head_oid": projection["corpus_repository"]["head_oid"],
        "corpus_status_sha256": projection["corpus_repository"]["status_sha256"],
        "place_manifest_sha256": place_sha256,
        "gold_sha256": scope["gold"]["sha256"],
        "audit_code_sha256": audit_code_sha256,
        "scope_manifest_sha256": reviewed_reference["scope_manifest_sha256"],
        "conflict_manifest_sha256": reviewed_reference["conflict_manifest_sha256"],
    }
    if args.current_only_diagnostic:
        diagnostics = [
            evaluate_current_only(
                language, resolved_cases, resolved_surfaces,
                args.batch_size, app_fingerprints_at_start[language],
            )
            for language in args.languages
        ]
        for result in diagnostics:
            print_comparison_result(
                result["language"], "current_only", result["comparison"]
            )
        _diagnostic_gold_raw, diagnostic_gold_identity = consistent_snapshot(
            gold_file
        )
        diagnostic_corpus = corpus_content_fingerprint(corpus_root)
        diagnostic_stability = {
            "gold": diagnostic_gold_identity["sha256"] == scope["gold"]["sha256"],
            "head": git_head_oid() == revision,
            "corpus": (
                diagnostic_corpus["files"] == projection["corpus"]["files"]
                and diagnostic_corpus["sha256"]
                == projection["corpus"]["content_sha256"]
                and git_repo_state(corpus_root)
                == projection["corpus_repository"]
            ),
            "place_manifest": (
                hashlib.sha256(place_path.read_bytes()).hexdigest().upper()
                == place_sha256
            ),
            "audit_code": (
                hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper()
                == audit_code_sha256
            ),
            "review_manifests": all((
                hashlib.sha256(
                    Path(reviewed_reference["scope_manifest"]).read_bytes()
                ).hexdigest().upper()
                == reviewed_reference["scope_manifest_sha256"],
                hashlib.sha256(
                    Path(reviewed_reference["conflict_manifest"]).read_bytes()
                ).hexdigest().upper()
                == reviewed_reference["conflict_manifest_sha256"],
            )),
            "app_inputs": all(
                current_app_fingerprint(
                    ROOT / f"Esperanto-Kanji-Ruby-{language}"
                ) == app_fingerprints_at_start[language]
                for language in args.languages
            ),
        }
        diagnostic_output = {
            "scope": scope,
            "case_count": len(resolved_cases),
            "raw_case_count": len(cases),
            "surface_count": len(resolved_surfaces),
            "languages": diagnostics,
            "reference_projection": projection,
            "resolved_reference": resolved_reference,
            "reviewed_reference": reviewed_reference,
            "checkpoint_context": checkpoint_context,
            "inputs_stable": diagnostic_stability,
            "complete": True,
            "gate": (
                all(diagnostic_stability.values())
                and all(result["gate"] for result in diagnostics)
            ),
        }
        diagnostic_path = (
            HERE / "out" / "_audit_no_worsening_current_only.json"
        )
        atomic_json_dump(diagnostic_path, diagnostic_output, indent=1)
        print(f"saved: {diagnostic_path}", flush=True)
        if not diagnostic_output["gate"]:
            raise SystemExit(1)
        print("current-only strict diagnostic: PASS", flush=True)
        return
    output_path = HERE / "out" / "_audit_no_worsening.json"
    results = []
    resumed_audit_code_sha256 = None
    if args.resume_language_results and output_path.exists():
        partial = json.loads(output_path.read_text(encoding="utf-8"))
        partial_languages = partial.get("languages", [])
        partial_codes = [result.get("language") for result in partial_languages]
        expected_prefix = args.languages[:len(partial_codes)]
        if not (
            partial.get("complete") is False
            and partial.get("requested_languages") == args.languages
            and partial.get("head_oid") == revision
            and partial.get("scope") == scope
            and partial.get("reference_projection") == projection
            and partial.get("resolved_reference") == resolved_reference
            and partial.get("reviewed_reference") == reviewed_reference
            and partial_codes == expected_prefix
            and all(result.get("gate") is True for result in partial_languages)
            and resume_context_matches(
                partial.get("checkpoint_context"), checkpoint_context,
            )
            and all(
                result.get("current_input_fingerprint")
                == app_fingerprints_at_start[result["language"]]
                for result in partial_languages
            )
            and partial.get("gold_source_matches_snapshot_so_far") is True
            and partial.get("latest_gold_sha256") == scope["gold"]["sha256"]
        ):
            raise ValueError("partial no-worsening audit is not safe to resume")
        results = partial_languages
        resumed_audit_code_sha256 = partial["checkpoint_context"][
            "audit_code_sha256"
        ]
        print(
            "resumed validated language results: "
            + ", ".join(partial_codes),
            flush=True,
        )
    for language in args.languages[len(results):]:
        language_started = time.perf_counter()
        result = evaluate_language(
            language, resolved_cases, resolved_surfaces, args.batch_size, revision,
            checkpoint_context, app_fingerprints_at_start[language],
        )
        result["elapsed_seconds"] = round(time.perf_counter() - language_started, 3)
        results.append(result)
        print_language_result(result)
        _partial_raw, partial_gold_identity = consistent_snapshot(gold_file)
        partial_gold_sha256 = partial_gold_identity["sha256"]
        atomic_json_dump(output_path, {
            "scope": scope,
            "case_count": len(resolved_cases),
            "surface_count": len(resolved_surfaces),
            "raw_case_count": len(cases),
            "languages": results,
            "requested_languages": args.languages,
            "head_oid": revision,
            "reference_projection": projection,
            "resolved_reference": resolved_reference,
            "reviewed_reference": reviewed_reference,
            "checkpoint_context": checkpoint_context,
            "complete": False,
            "gold_source_matches_snapshot_so_far": (
                partial_gold_sha256 == scope["gold"]["sha256"]
            ),
            "latest_gold_sha256": partial_gold_sha256,
            "gate": None,
        }, indent=1)
        print(
            f"[{language}] language checkpoint saved; "
            f"elapsed={result['elapsed_seconds']}s",
            flush=True,
        )
    _final_gold_raw, final_gold_identity = consistent_snapshot(gold_file)
    final_gold_sha256 = final_gold_identity["sha256"]
    gold_source_matches_snapshot_at_end = (
        final_gold_sha256 == scope["gold"]["sha256"]
    )
    head_stable_at_end = git_head_oid() == revision
    corpus_at_end = corpus_content_fingerprint(corpus_root)
    corpus_repo_at_end = git_repo_state(corpus_root)
    corpus_stable_at_end = (
        corpus_at_end["files"] == projection["corpus"]["files"]
        and corpus_at_end["sha256"] == projection["corpus"]["content_sha256"]
        and corpus_repo_at_end == projection["corpus_repository"]
    )
    place_stable_at_end = (
        hashlib.sha256(place_path.read_bytes()).hexdigest().upper()
        == place_sha256
    )
    audit_code_stable_at_end = (
        hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper()
        == audit_code_sha256
    )
    review_manifests_stable_at_end = all((
        hashlib.sha256(
            Path(reviewed_reference["scope_manifest"]).read_bytes()
        ).hexdigest().upper() == reviewed_reference["scope_manifest_sha256"],
        hashlib.sha256(
            Path(reviewed_reference["conflict_manifest"]).read_bytes()
        ).hexdigest().upper() == reviewed_reference["conflict_manifest_sha256"],
    ))
    app_fingerprints_at_end = {
        language: current_app_fingerprint(
            ROOT / f"Esperanto-Kanji-Ruby-{language}"
        )
        for language in args.languages
    }
    all_app_inputs_stable_at_end = (
        app_fingerprints_at_end == app_fingerprints_at_start
    )
    output = {
        "scope": scope,
        "case_count": len(resolved_cases),
        "surface_count": len(resolved_surfaces),
        "raw_case_count": len(cases),
        "languages": results,
        "requested_languages": args.languages,
        "head_oid": revision,
        "head_stable_at_end": head_stable_at_end,
        "reference_projection": projection,
        "resolved_reference": resolved_reference,
        "reviewed_reference": reviewed_reference,
        "checkpoint_context": checkpoint_context,
        "resumed_from_audit_code_sha256": resumed_audit_code_sha256,
        "corpus_stable_at_end": corpus_stable_at_end,
        "corpus_repository_at_end": corpus_repo_at_end,
        "place_manifest_stable_at_end": place_stable_at_end,
        "audit_code_stable_at_end": audit_code_stable_at_end,
        "review_manifests_stable_at_end": review_manifests_stable_at_end,
        "all_app_inputs_stable_at_end": all_app_inputs_stable_at_end,
        "app_fingerprints_at_start": app_fingerprints_at_start,
        "app_fingerprints_at_end": app_fingerprints_at_end,
        "complete": True,
        "final_gold_sha256": final_gold_sha256,
        "gold_source_matches_snapshot_at_end": gold_source_matches_snapshot_at_end,
        "gold_snapshot_isolated_from_external_changes": True,
        "gold_snapshot_source_stable_during_audit": (
            gold_source_matches_snapshot_at_end
        ),
        "gate": (
            gold_source_matches_snapshot_at_end
            and head_stable_at_end
            and corpus_stable_at_end
            and place_stable_at_end
            and audit_code_stable_at_end
            and review_manifests_stable_at_end
            and all_app_inputs_stable_at_end
            and all(result["gate"] for result in results)
        ),
    }
    atomic_json_dump(output_path, output, indent=1)
    print(f"saved: {output_path}", flush=True)
    if not output["gate"]:
        raise SystemExit(1)
    for checkpoint in (HERE / "out").glob("_no_worsening_checkpoint_*.json"):
        checkpoint.unlink()
    print("3-language no-worsening gate: PASS", flush=True)


if __name__ == "__main__":
    main()
