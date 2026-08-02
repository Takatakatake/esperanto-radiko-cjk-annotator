# -*- coding: utf-8 -*-
"""Fail-closed deployed-payload tests for the post-generation R88 repair.

R88 is intentionally replayed *after* ordinary Ruby generation.  Its purpose
is narrow: reuse Phase619's reviewed ``mukoz`` annotation for the base family
without adding the rule to the ordinary generator and thereby renumbering
hundreds of thousands of unrelated placeholders.  These tests seal both the
linguistic behaviour and that minimal-diff property.
"""
from __future__ import annotations

from functools import lru_cache
import html
import json
from pathlib import Path
import re
import sys
import unittest


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import no_worsening_audit as audit
import phase619_ordinary_ruby_runtime_gate as phase619_gate
import r88_mukoz_ruby_policy as policy


LANGUAGES = ("JA", "ZH", "KO")
ENDINGS = ("o", "oj", "on", "ojn", "a", "aj", "an", "ajn", "e", "en")
CASE_MODES = ("lower", "title", "upper")
NEGATIVE_SURFACES = (
    "mukozito",
    "mukoziton",
    "mukozitoj",
    "mukozitojn",
    "mukoz",
    "amukozo",
)
SIBLING_SURFACE = "mukozaĵo"
R88_MARKER = "$R88M"
EXPECTED_ACTIONS = {
    *ENDINGS,
    "word_boundary",
    f"ruby_context_annotation:{policy.CONTEXT_KEY}",
    "ruby_track_only",
}

# The twelve noun rows predated R88.  R94 legitimately rebuilt the ordinary
# payload after adopting 528 reviewed rows, so its sequential internal IDs
# differ from R93.  The values below seal the deterministic R94 successor
# baseline: a repeat post-generation R88 replay may change the rendered value
# and normalize the outer ``word_boundary`` spaces, but must not silently
# renumber the already-generated successor rows.  Placeholder IDs are internal
# sentinels (their source/render mapping is validated elsewhere), not a Ruby or
# Kanji linguistic authority.  The old unspaced rows remain unsafe: rewriting
# only their Ruby value makes ``amukozo`` inherit the R88 annotation.
PREEXISTING_PLACEHOLDER_IDS = {
    "JA": {
        "mukozojn": 84773,
        "mukozon": 134705,
        "mukozoj": 134706,
        "mukozo": 175949,
    },
    "ZH": {
        "mukozojn": 84784,
        "mukozon": 134698,
        "mukozoj": 134699,
        "mukozo": 175981,
    },
    "KO": {
        "mukozojn": 84846,
        "mukozon": 134738,
        "mukozoj": 134739,
        "mukozo": 176022,
    },
}

RUBY_WITH_CLASS_RE = re.compile(
    r"<ruby>(?P<rb>.*?)<rt\s+class=[\"'](?P<class>[A-Z_]+)[\"']>"
    r"(?P<rt>.*?)</rt></ruby>",
    re.IGNORECASE | re.DOTALL,
)
TAG_RE = re.compile(r"<[^>]+>")
BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
CSS_SCALE_RE = re.compile(
    r"rt\.([A-Z_]+)\s*\{[^}]*?--ruby-font-size\s*:\s*([0-9.]+)em",
    re.DOTALL,
)


def cased_stem(mode: str) -> str:
    if mode == "lower":
        return policy.STEM
    if mode == "title":
        return policy.STEM[:1].upper() + policy.STEM[1:]
    if mode == "upper":
        return policy.STEM.upper()
    raise AssertionError(f"unknown case mode: {mode!r}")


def cased_ending(ending: str, mode: str) -> str:
    return ending.upper() if mode == "upper" else ending


def positive_surface(ending: str, mode: str) -> str:
    return cased_stem(mode) + cased_ending(ending, mode)


POSITIVE_SURFACES = tuple(
    positive_surface(ending, mode)
    for ending in ENDINGS
    for mode in CASE_MODES
)
ALL_RUNTIME_SURFACES = (
    *POSITIVE_SURFACES,
    *NEGATIVE_SURFACES,
    SIBLING_SURFACE,
)


def payload_path(language: str) -> Path:
    return (
        ROOT / f"Esperanto-Kanji-Ruby-{language}" / "app_data"
        / "置換リスト_ルビ.json"
    )


@lru_cache(maxsize=None)
def deployed_payload(language: str) -> dict:
    return json.loads(payload_path(language).read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def all_payload_rows(language: str) -> tuple:
    return tuple(
        row
        for rules in audit.extract_lists(deployed_payload(language))
        for row in rules
    )


@lru_cache(maxsize=None)
def payload_rows_by_surface(language: str) -> dict[str, tuple]:
    rows_by_surface: dict[str, list] = {}
    for row in all_payload_rows(language):
        if (
            isinstance(row, (list, tuple))
            and len(row) >= 3
            and isinstance(row[0], str)
        ):
            rows_by_surface.setdefault(row[0].strip(), []).append(row)
    return {
        surface: tuple(rows)
        for surface, rows in rows_by_surface.items()
    }


def matching_rows(language: str, surface: str) -> tuple:
    return payload_rows_by_surface(language).get(surface, ())


def expected_r88_marker_rows(language: str) -> dict[str, str]:
    suffix = "" if language == "JA" else language
    expected = {}
    for ending_index, ending in enumerate(ENDINGS):
        for case_index, mode in enumerate(CASE_MODES):
            marker_number = ending_index * len(CASE_MODES) + case_index
            # o/oj/on/ojn (indices 0..11) are the twelve pre-existing rows.
            if marker_number < 12:
                continue
            surface = positive_surface(ending, mode)
            expected[surface] = f" {R88_MARKER}{marker_number:05d}{suffix}$ "
    return expected


def expected_preexisting_placeholders(language: str) -> dict[str, str]:
    expected = {}
    for lower_surface, identifier in PREEXISTING_PLACEHOLDER_IDS[language].items():
        expected[lower_surface] = f"${identifier}$"
        expected[lower_surface.upper()] = f"${identifier}up$"
        expected[
            lower_surface[:1].upper() + lower_surface[1:]
        ] = f"${identifier}cap$"
    return expected


@lru_cache(maxsize=1)
def deployed_runtime_results() -> dict:
    results = {}
    for language in LANGUAGES:
        app_dir = ROOT / f"Esperanto-Kanji-Ruby-{language}"
        runtime = audit.runtime_module(app_dir, f"r88_postregen_{language}")
        overlay = audit.overlay_module(
            app_dir, f"r88_postregen_overlay_{language}",
        )
        corrections = json.loads(
            (app_dir / "app_data" / "user_corrections.json").read_text(
                encoding="utf-8"
            )
        )
        results[language] = audit.render_signatures(
            runtime,
            app_dir,
            deployed_payload(language),
            list(ALL_RUNTIME_SURFACES),
            batch_size=50,
            overlay=overlay,
            corrections=corrections,
            include_annotations=True,
        )
    return results


def visible(fragment: str) -> str:
    return html.unescape(TAG_RE.sub("", fragment))


def text_width(text: str, widths: dict) -> float:
    missing = sorted({character for character in text if character not in widths})
    if missing:
        raise AssertionError(f"char-width table lacks {missing!r}")
    return sum(float(widths[character]) for character in text)


class R88PostGenerationStructureTests(unittest.TestCase):
    def test_policy_normalizes_all_three_edges_and_fails_closed(self):
        rendered = '<ruby>mukoz<rt class="XXL_L">粘膜</rt></ruby>o'
        self.assertEqual(
            policy.normalize_existing_payload_row(
                ["mukozo", "old", "$175774$"],
                surface="mukozo",
                rendered=rendered,
            ),
            [" mukozo ", f" {rendered} ", " $175774$ "],
        )
        self.assertEqual(
            policy.normalize_existing_payload_row(
                [" mukozo ", " old ", " $175774$ "],
                surface="mukozo",
                rendered=f" {rendered} ",
            ),
            [" mukozo ", f" {rendered} ", " $175774$ "],
        )
        with self.assertRaisesRegex(ValueError, "placeholder must be text"):
            policy.normalize_existing_payload_row(
                ["mukozo", "old", None],
                surface="mukozo",
                rendered=rendered,
            )
        with self.assertRaisesRegex(ValueError, "surface drift"):
            policy.normalize_existing_payload_row(
                ["foreign", "old", "$175774$"],
                surface="mukozo",
                rendered=rendered,
            )

    def test_setting_is_unique_and_immediately_precedes_phase619_sibling(self):
        expected_row = [policy.STEM, 59000, list(ENDINGS) + [
            "word_boundary",
            f"ruby_context_annotation:{policy.CONTEXT_KEY}",
            "ruby_track_only",
        ]]
        for language in LANGUAGES:
            with self.subTest(language=language):
                app_data = (
                    ROOT / f"Esperanto-Kanji-Ruby-{language}" / "app_data"
                )
                settings = json.loads(
                    (app_data / "分解設定.json").read_text(encoding="utf-8")
                )
                base_indexes = [
                    index for index, row in enumerate(settings)
                    if isinstance(row, list) and row and row[0] == policy.STEM
                ]
                sibling_indexes = [
                    index for index, row in enumerate(settings)
                    if (
                        isinstance(row, list)
                        and row
                        and row[0] == policy.SIBLING_CONTEXT_KEY
                    )
                ]
                self.assertEqual(len(base_indexes), 1)
                self.assertEqual(len(sibling_indexes), 1)
                self.assertEqual(base_indexes[0] + 1, sibling_indexes[0])
                self.assertEqual(settings[base_indexes[0]], expected_row)
                self.assertEqual(
                    set(settings[base_indexes[0]][2]), EXPECTED_ACTIONS,
                )

                annotations = json.loads(
                    (app_data / "word_anno.json").read_text(encoding="utf-8")
                )
                self.assertEqual(
                    annotations.get(policy.CONTEXT_KEY),
                    [[
                        policy.STEM,
                        policy.EXPECTED_GLOSSES[language.lower()],
                    ]],
                )

    def test_payload_has_exactly_the_eighteen_reserved_r88_rows(self):
        for language in LANGUAGES:
            with self.subTest(language=language):
                marker_rows = [
                    row for row in all_payload_rows(language)
                    if (
                        isinstance(row, (list, tuple))
                        and len(row) >= 3
                        and isinstance(row[2], str)
                        and R88_MARKER in row[2]
                    )
                ]
                self.assertEqual(len(marker_rows), 18)
                self.assertEqual(
                    len({row[2] for row in marker_rows}), 18,
                    "R88 placeholders must be unique",
                )
                self.assertEqual(
                    {row[0].strip(): row[2] for row in marker_rows},
                    expected_r88_marker_rows(language),
                )
                for row in marker_rows:
                    self.assertEqual(row[0], f" {row[0].strip()} ")

    def test_twelve_preexisting_placeholder_cores_keep_the_r94_successor_ids(self):
        for language in LANGUAGES:
            for surface, expected in expected_preexisting_placeholders(
                language
            ).items():
                with self.subTest(language=language, surface=surface):
                    rows = matching_rows(language, surface)
                    self.assertEqual(len(rows), 1)
                    self.assertEqual(rows[0][0], f" {surface} ")
                    self.assertEqual(rows[0][2], f" {expected} ")
                    self.assertEqual(rows[0][2].strip(), expected)
                    self.assertTrue(rows[0][1].startswith(" "))
                    self.assertTrue(rows[0][1].endswith(" "))
                    self.assertNotIn(R88_MARKER, rows[0][2])
                    self.assertEqual(
                        policy.normalize_existing_payload_row(
                            rows[0], surface=surface, rendered=rows[0][1],
                        ),
                        list(rows[0]),
                    )

    def test_all_thirty_positive_payload_rows_are_exact_and_trilingual(self):
        signatures_by_language = {language: {} for language in LANGUAGES}
        for language in LANGUAGES:
            expected_gloss = policy.EXPECTED_GLOSSES[language.lower()]
            for ending in ENDINGS:
                for mode in CASE_MODES:
                    surface = positive_surface(ending, mode)
                    with self.subTest(language=language, surface=surface):
                        rows = matching_rows(language, surface)
                        self.assertEqual(len(rows), 1)
                        self.assertEqual(rows[0][0], f" {surface} ")
                        signature = audit.signature_from_typed_parts(
                            audit.rendered_typed_parts(rows[0][1])
                        )
                        expected_signature = audit.signature_from_typed_parts([
                            (cased_stem(mode), True),
                            (cased_ending(ending, mode), False),
                        ])
                        self.assertEqual(signature, expected_signature)
                        self.assertEqual(
                            audit.rendered_ruby_annotations(rows[0][1]),
                            [{
                                "rb": cased_stem(mode),
                                "rt": expected_gloss,
                            }],
                        )
                        signatures_by_language[language][surface] = signature
        for surface in POSITIVE_SURFACES:
            self.assertEqual(
                len({
                    signatures_by_language[language][surface]
                    for language in LANGUAGES
                }),
                1,
                f"JA/ZH/KO typed R/L boundary mismatch: {surface}",
            )

    def test_all_positive_effective_ruby_widths_are_within_two_times_base(self):
        for language in LANGUAGES:
            app_dir = ROOT / f"Esperanto-Kanji-Ruby-{language}"
            widths = json.loads(
                (app_dir / "app_data" / "char_widths.json").read_text(
                    encoding="utf-8"
                )
            )
            css_text = (app_dir / "esp_text_replacement_module.py").read_text(
                encoding="utf-8"
            )
            scales = {
                class_name.upper(): float(scale)
                for class_name, scale in CSS_SCALE_RE.findall(css_text)
            }
            self.assertEqual(scales, phase619_gate.CSS_CLASS_SCALE)
            for surface in POSITIVE_SURFACES:
                row = matching_rows(language, surface)[0]
                matches = list(RUBY_WITH_CLASS_RE.finditer(row[1]))
                with self.subTest(language=language, surface=surface):
                    self.assertEqual(len(matches), 1)
                    match = matches[0]
                    self.assertIsNone(BR_RE.search(match.group("rt")))
                    rb = visible(match.group("rb"))
                    rt = visible(match.group("rt"))
                    class_name = match.group("class").upper()
                    self.assertIn(class_name, scales)
                    rb_width = text_width(rb, widths)
                    self.assertGreater(rb_width, 0)
                    effective_ratio = (
                        text_width(rt, widths) * scales[class_name] / rb_width
                    )
                    self.assertLessEqual(effective_ratio, 2.0)


class R88PostGenerationRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = deployed_runtime_results()

    def test_runtime_positive_paradigm_is_exact_and_trilingual(self):
        for ending in ENDINGS:
            for mode in CASE_MODES:
                surface = positive_surface(ending, mode)
                expected_signature = audit.signature_from_typed_parts([
                    (cased_stem(mode), True),
                    (cased_ending(ending, mode), False),
                ])
                observed_signatures = []
                for language in LANGUAGES:
                    with self.subTest(language=language, surface=surface):
                        result = self.results[language][surface]
                        self.assertEqual(result["signature"], expected_signature)
                        self.assertEqual(
                            result["annotations"],
                            [{
                                "rb": cased_stem(mode),
                                "rt": policy.EXPECTED_GLOSSES[
                                    language.lower()
                                ],
                            }],
                        )
                        observed_signatures.append(result["signature"])
                self.assertEqual(len(set(observed_signatures)), 1)

    def test_r88_root_and_gloss_do_not_leak_to_six_guard_surfaces(self):
        for language in LANGUAGES:
            r88_gloss = policy.EXPECTED_GLOSSES[language.lower()]
            for surface in NEGATIVE_SURFACES:
                result = self.results[language][surface]
                with self.subTest(language=language, surface=surface):
                    self.assertEqual(result["signature"][0], surface)
                    self.assertFalse(any(
                        audit.canonical(annotation["rb"]).lower()
                        == policy.STEM
                        for annotation in result["annotations"]
                    ))
                    self.assertFalse(any(
                        annotation["rt"] == r88_gloss
                        for annotation in result["annotations"]
                    ))

    def test_phase619_mukozaĵo_sibling_is_unchanged(self):
        signatures, _signature_digest = (
            phase619_gate.positive_expected_signatures()
        )
        annotations, _annotation_digest = (
            phase619_gate.positive_expected_annotations()
        )
        expected_signature = signatures[SIBLING_SURFACE]
        observed = []
        for language in LANGUAGES:
            with self.subTest(language=language):
                result = self.results[language][SIBLING_SURFACE]
                self.assertEqual(result["signature"], expected_signature)
                self.assertEqual(
                    result["annotations"],
                    annotations[language][SIBLING_SURFACE],
                )
                observed.append(result["signature"])
        self.assertEqual(len(set(observed)), 1)


if __name__ == "__main__":
    unittest.main()
