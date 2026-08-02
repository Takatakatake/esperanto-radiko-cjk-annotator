# -*- coding: utf-8 -*-
"""Canonical post-Phase619 Ruby policy for the omitted ``mukoz`` base family.

Phase619 deliberately remains a sealed seven-entry review.  R88 found that its
reviewed ``mukoz/aĵ`` sibling supplied the same coarse root and gloss required
by the base word ``mukozo``.  This module supplies the reviewed annotation and
bounded target to the formal R88 post-generation step.  R88 intentionally
stays after ordinary generation: moving it into normal settings renumbers
hundreds of thousands of otherwise stable placeholder identifiers.

The rule is Ruby-only.  Kanji generation must continue to use the learner
master's deeper ``muk/oz`` decomposition.
"""
from __future__ import annotations

import phase619_ordinary_ruby_policy as phase619


PHASE = 88
SURFACE = "mukozo"
TARGET = "mukoz/o"
STEM = "mukoz"
SIBLING_CONTEXT_KEY = "mukoz/aĵ"
CONTEXT_KEY = "@phase619-ruby:mukoz"
EXPECTED_GLOSSES = {
    "ja": "粘膜",
    "zh": "黏膜",
    "ko": "점막",
}


def normalize_existing_payload_row(
    row: list | tuple, *, surface: str, rendered: str,
) -> list[str]:
    """Return a word-boundary-safe row while retaining its placeholder core.

    The twelve pre-R88 noun rows used unpadded keys and placeholders.  Merely
    replacing their rendered Ruby therefore made the coarse ``mukoz`` gloss
    match inside ``amukozo``.  R88 must put exactly one outer space on all
    three fields together.  The placeholder identifier itself is retained so
    this safety repair does not renumber any unrelated generated row.
    """
    if not isinstance(row, (list, tuple)) or len(row) != 3:
        raise ValueError("R88 existing payload row must have exactly 3 fields")
    old, _old_rendered, placeholder = row
    if not isinstance(old, str):
        raise ValueError("R88 existing payload surface must be text")
    if not isinstance(surface, str) or not surface or surface != surface.strip():
        raise ValueError("R88 target surface must be non-empty unpadded text")
    if old.strip() != surface:
        raise ValueError(
            f"R88 existing payload surface drift: {old!r} != {surface!r}"
        )
    if not isinstance(rendered, str) or not rendered.strip():
        raise ValueError("R88 rendered replacement must be non-empty text")
    if not isinstance(placeholder, str):
        raise ValueError("R88 existing payload placeholder must be text")
    placeholder_core = placeholder.strip()
    if (
        not placeholder_core
        or not placeholder_core.startswith("$")
        or not placeholder_core.endswith("$")
        or any(character.isspace() for character in placeholder_core)
    ):
        raise ValueError(
            f"R88 existing payload placeholder core is invalid: "
            f"{placeholder!r}"
        )
    return [
        f" {surface} ",
        f" {rendered.strip()} ",
        f" {placeholder_core} ",
    ]


def _reviewed_annotation() -> dict:
    rows = phase619.split_context_annotations().get(SIBLING_CONTEXT_KEY)
    if not isinstance(rows, list):
        raise ValueError("R88 source sibling is missing from sealed Phase619")
    matches = [row for row in rows if row.get("piece") == STEM]
    if len(matches) != 1:
        raise ValueError("R88 source sibling must expose exactly one mukoz piece")
    annotation = matches[0]
    if (
        set(annotation) != {"piece", "glosses"}
        or annotation["piece"] != STEM
        or annotation["glosses"] != EXPECTED_GLOSSES
    ):
        raise ValueError(f"R88 reviewed mukoz annotation drift: {annotation!r}")
    return {
        "piece": STEM,
        "glosses": dict(annotation["glosses"]),
    }


def morph_context_annotations() -> dict[str, dict]:
    """Return the single contextual annotation inherited from Phase619."""
    return {CONTEXT_KEY: _reviewed_annotation()}


def managed_morph_targets() -> dict[str, dict]:
    """Return the bounded Ruby-only base-family rule."""
    _reviewed_annotation()
    return {
        SURFACE: {
            "target": TARGET,
            "ruby_track_only": True,
            "ruby_context_annotation": CONTEXT_KEY,
        },
    }


def identity_report() -> dict:
    return {
        "phase": PHASE,
        "surface": SURFACE,
        "target": TARGET,
        "context_key": CONTEXT_KEY,
        "source_phase619_review": phase619.review_identity(),
        "glosses": dict(EXPECTED_GLOSSES),
        "ruby_track_only": True,
    }
