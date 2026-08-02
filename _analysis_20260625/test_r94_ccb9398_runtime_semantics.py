# -*- coding: utf-8 -*-
"""Deployed-runtime semantic and width gate for the ccb9398 R94 closure.

The residual ledger is the independent boundary oracle.  This test deliberately
renders through the same overlay/correction path as the application: inspecting
``word_anno.json`` or generated rule settings alone cannot prove rule priority,
contextual meaning, or the final ``rt`` CSS class.
"""
from __future__ import annotations

from functools import lru_cache
import hashlib
import html
import json
from pathlib import Path
import re
import sys
import unittest


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
LEDGER_PATH = HERE / "_corpus_r94_ccb9398_residual_closure.json"
PAYLOAD_NAME = "置換リスト_ルビ.json"
LANGUAGES = ("JA", "ZH", "KO")

sys.path.insert(0, str(HERE))
from gen_replacement import load_app_replacement_helper
import no_worsening_audit as audit
import phase619_ordinary_ruby_runtime_gate as phase619_gate


MEDIA_GLOSS = {"JA": "ラジオ", "ZH": "广播", "KO": "라디오"}
PHYSICS_GLOSS = {"JA": "光線", "ZH": "光线", "KO": "광선"}
PRIZE_GLOSS = {"JA": "賞品", "ZH": "奖品", "KO": "상품"}
PRESS_GLOSS = {"JA": "押える", "ZH": "压", "KO": "누르다"}
ORIGIN_GLOSS = {"JA": "起源", "ZH": "来源", "KO": "기원"}

RADIO_MEDIA_EXPECTED = {
    "radioprogramo": "R:radio|R:program|L:o",
    "radioprogramoj": "R:radio|R:program|L:oj",
    "radioelsendo": "R:radio|R:el|R:send|L:o",
    "radioelsendoj": "R:radio|R:el|R:send|L:oj",
    "radio-elsendo": "R:radio|L:-|R:el|R:send|L:o",
    "radio-elsendoj": "R:radio|L:-|R:el|R:send|L:oj",
}

PHYSICS_RADI_GUARDS = {
    "radio": "R:radi|L:o",
    "radioj": "R:radi|L:oj",
    "radia": "R:radi|L:a",
    "radiado": "R:radi|R:ad|L:o",
    "radiometro": "R:radi|L:o|R:metr|L:o",
}

PRESS_PREM_GUARDS = {
    "premi": "R:prem|L:i",
    "premis": "R:prem|R:is",
    "premas": "R:prem|R:as",
    "premado": "R:prem|R:ad|L:o",
    "sub-premi": "R:sub|L:-|R:prem|L:i",
}

DE_VEN_GUARDS = {
    "deveni": "R:de|R:ven|L:i",
    "devenas": "R:de|R:ven|R:as",
    "deveno": "R:de|R:ven|L:o",
    "subdeveni": "R:sub|R:de|R:ven|L:i",
}

HONGKONG_LEAKAGE_PROBES = {
    "xhongkongano": "hongkongano",
    "superhongkongano": "hongkongano",
    "xhongkongano-japanaj": "hongkongano-japanaj",
    "xkoreo-hongkongano": "koreo-hongkongano",
    "xnederlandano-hongkongano": "nederlandano-hongkongano",
}
RAW_APOSTROPHE_PROBES = ("Fukuwarai’", "fukuwarai’")

TAG_RE = re.compile(r"<[^>]+>")
RT_ELEMENT_RE = re.compile(r"<rt\b[^>]*>.*?</rt>", re.IGNORECASE | re.DOTALL)
BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
CSS_SCALE_RE = re.compile(
    r"rt\.([A-Z_]+)\s*\{[^}]*?--ruby-font-size\s*:\s*([0-9.]+)em",
    re.DOTALL,
)


@lru_cache(maxsize=1)
def ledger() -> dict:
    return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))


def _ordered_unique(values):
    return tuple(dict.fromkeys(values))


@lru_cache(maxsize=1)
def runtime_surfaces() -> tuple[str, ...]:
    proper_lowercase = (
        surface.lower()
        for surface in ledger()["policy"]["proper_foreign"]["surfaces"]
    )
    return _ordered_unique((
        *(row["surface"] for row in ledger()["residuals"]),
        *RADIO_MEDIA_EXPECTED,
        *PHYSICS_RADI_GUARDS,
        *PRESS_PREM_GUARDS,
        *DE_VEN_GUARDS,
        *HONGKONG_LEAKAGE_PROBES,
        *RAW_APOSTROPHE_PROBES,
        *proper_lowercase,
    ))


def app_dir(language: str) -> Path:
    return ROOT / f"Esperanto-Kanji-Ruby-{language}"


@lru_cache(maxsize=None)
def deployed_payload(language: str) -> dict:
    path = app_dir(language) / "app_data" / PAYLOAD_NAME
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def render_ordered_records(language: str, surfaces: tuple[str, ...]) -> dict:
    """Render one ordered batch through the complete effective app path."""
    current_app = app_dir(language)
    data_dir = current_app / "app_data"
    runtime = audit.runtime_module(current_app, f"r94_runtime_{language}")
    overlay = audit.overlay_module(current_app, f"r94_overlay_{language}")
    local_rules, global_rules, two_char_rules = audit.extract_lists(
        deployed_payload(language)
    )
    skip = runtime.import_placeholders(str(data_dir / "placeholders_skip.txt"))
    local_capture = runtime.import_placeholders(
        str(data_dir / "placeholders_localcapture.txt")
    )
    corrections = json.loads(
        (data_dir / "user_corrections.json").read_text(encoding="utf-8")
    )
    rendered = audit.render_effective_text(
        runtime,
        overlay,
        "\n".join(f" {surface} " for surface in surfaces),
        skip,
        local_rules,
        local_capture,
        global_rules,
        two_char_rules,
        data_dir,
        corrections,
    )
    lines = rendered.splitlines()
    if len(lines) != len(surfaces):
        raise AssertionError(
            f"{language} R94 runtime line accounting failed: "
            f"{len(lines)} != {len(surfaces)}"
        )
    records = {}
    for surface, fragment in zip(surfaces, lines):
        parts = audit.rendered_typed_parts(fragment)
        records[surface] = {
            "html": fragment,
            "signature": audit.signature_from_typed_parts(parts),
            "typed": audit.display_typed_parts(parts),
            "annotations": audit.rendered_ruby_annotations(fragment),
        }
    return records


@lru_cache(maxsize=None)
def deployed_records(language: str) -> dict:
    """Render every positive and leakage probe through the effective app path."""
    return render_ordered_records(language, runtime_surfaces())


def annotation_for(records: dict, surface: str, rb: str) -> dict:
    matches = [
        row for row in records[surface]["annotations"]
        if row["rb"] == rb
    ]
    if len(matches) != 1:
        raise AssertionError(
            f"{surface!r} must have exactly one {rb!r} annotation: {matches!r}"
        )
    return matches[0]


def visible(value: str) -> str:
    # ``rt`` is annotation text, not part of the authored base spelling.
    # Remove the whole element before stripping the remaining markup; merely
    # deleting tags would concatenate the gloss into the visible base.
    return html.unescape(TAG_RE.sub("", RT_ELEMENT_RE.sub("", value)))


def strict_width(value: str, widths: dict) -> float:
    missing = sorted({character for character in value if character not in widths})
    if missing:
        raise AssertionError(f"char-width table lacks {missing!r}")
    return sum(float(widths[character]) for character in value)


class R94Ccb9398RuntimeSemanticsTests(unittest.TestCase):
    def test_exact_26_boundaries_are_deployed_and_trilingual(self):
        rows = ledger()["residuals"]
        expected_surfaces = {row["surface"] for row in rows}
        self.assertEqual(len(expected_surfaces), 26)
        comparisons = 0
        for row in rows:
            observed = []
            for language in LANGUAGES:
                with self.subTest(language=language, surface=row["surface"]):
                    record = deployed_records(language)[row["surface"]]
                    expected = row["languages"][language]["expected_typed"]
                    self.assertEqual(record["typed"], expected)
                    self.assertEqual(record["signature"][0], row["surface"])
                    self.assertNotIn("$", record["html"])
                    observed.append(record["typed"])
                    comparisons += 1
            self.assertEqual(
                len(set(observed)), 1,
                f"JA/ZH/KO runtime boundary mismatch: {row['surface']}",
            )
        self.assertEqual(comparisons, 26 * len(LANGUAGES))

    def test_authored_curly_apostrophe_uses_the_same_exact_bounded_rule(self):
        expected_typed = "R:Fukuwarai|L:'"
        for language in LANGUAGES:
            records = deployed_records(language)
            ascii_record = records["Fukuwarai'"]
            curly_record = records["Fukuwarai’"]
            lower_record = records["fukuwarai’"]
            with self.subTest(language=language, surface="Fukuwarai’"):
                self.assertEqual(
                    visible(curly_record["html"]).strip(), "Fukuwarai’"
                )
                self.assertEqual(curly_record["typed"], expected_typed)
                self.assertEqual(
                    curly_record["annotations"],
                    ascii_record["annotations"],
                )
                self.assertNotIn("$", curly_record["html"])
            with self.subTest(language=language, surface="fukuwarai’"):
                self.assertEqual(
                    visible(lower_record["html"]).strip(), "fukuwarai’"
                )
                self.assertNotEqual(lower_record["typed"], expected_typed)
                self.assertTrue({
                    row["rt"] for row in ascii_record["annotations"]
                }.isdisjoint(
                    row["rt"] for row in lower_record["annotations"]
                ))

    def test_radio_media_meaning_is_bounded_and_physics_radi_survives(self):
        for language in LANGUAGES:
            records = deployed_records(language)
            for surface, expected_typed in RADIO_MEDIA_EXPECTED.items():
                with self.subTest(language=language, surface=surface, sense="media"):
                    self.assertEqual(records[surface]["typed"], expected_typed)
                    self.assertEqual(
                        annotation_for(records, surface, "radio")["rt"],
                        MEDIA_GLOSS[language],
                    )
                    self.assertNotIn(
                        "radi", {row["rb"] for row in records[surface]["annotations"]}
                    )
                    self.assertNotIn(
                        PHYSICS_GLOSS[language],
                        {row["rt"] for row in records[surface]["annotations"]},
                    )
            for surface, expected_typed in PHYSICS_RADI_GUARDS.items():
                with self.subTest(language=language, surface=surface, sense="physics"):
                    self.assertEqual(records[surface]["typed"], expected_typed)
                    self.assertEqual(
                        annotation_for(records, surface, "radi")["rt"],
                        PHYSICS_GLOSS[language],
                    )
                    self.assertNotIn(
                        "radio", {row["rb"] for row in records[surface]["annotations"]}
                    )
                    self.assertNotIn(
                        MEDIA_GLOSS[language],
                        {row["rt"] for row in records[surface]["annotations"]},
                    )

    def test_prize_premi_context_does_not_capture_press_verb(self):
        positive = "premi-ceremonio"
        for language in LANGUAGES:
            records = deployed_records(language)
            with self.subTest(language=language, surface=positive, sense="prize"):
                self.assertEqual(
                    records[positive]["typed"],
                    "R:premi|L:-|R:ceremoni|L:o",
                )
                self.assertEqual(
                    annotation_for(records, positive, "premi")["rt"],
                    PRIZE_GLOSS[language],
                )
            for surface, expected_typed in PRESS_PREM_GUARDS.items():
                with self.subTest(language=language, surface=surface, sense="press"):
                    self.assertEqual(records[surface]["typed"], expected_typed)
                    self.assertEqual(
                        annotation_for(records, surface, "prem")["rt"],
                        PRESS_GLOSS[language],
                    )
                    self.assertNotIn(
                        "premi", {row["rb"] for row in records[surface]["annotations"]}
                    )
                    self.assertNotIn(
                        PRIZE_GLOSS[language],
                        {row["rt"] for row in records[surface]["annotations"]},
                    )

    def test_coarse_deven_is_limited_to_two_kyoto_contexts(self):
        positives = {
            "miksdevena": "R:miks|R:deven|L:a",
            "multdevenuloj": "R:mult|R:deven|R:ul|L:oj",
        }
        for language in LANGUAGES:
            records = deployed_records(language)
            for surface, expected_typed in positives.items():
                with self.subTest(language=language, surface=surface, sense="origin"):
                    self.assertEqual(records[surface]["typed"], expected_typed)
                    self.assertEqual(
                        annotation_for(records, surface, "deven")["rt"],
                        ORIGIN_GLOSS[language],
                    )
            for surface, expected_typed in DE_VEN_GUARDS.items():
                with self.subTest(language=language, surface=surface, sense="de_plus_ven"):
                    self.assertEqual(records[surface]["typed"], expected_typed)
                    self.assertNotIn(
                        "deven", {row["rb"] for row in records[surface]["annotations"]}
                    )
                    self.assertNotIn(
                        ORIGIN_GLOSS[language],
                        {row["rt"] for row in records[surface]["annotations"]},
                    )

    def test_final_r94_markup_is_recomputed_and_within_two_times_base(self):
        width_hashes = set()
        maxima = {}
        row_by_surface = {
            row["surface"]: row for row in ledger()["residuals"]
        }
        for language in LANGUAGES:
            current_app = app_dir(language)
            data_dir = current_app / "app_data"
            width_path = data_dir / "char_widths.json"
            width_hashes.add(
                hashlib.sha256(width_path.read_bytes()).hexdigest().upper()
            )
            widths = json.loads(width_path.read_text(encoding="utf-8"))
            helper = load_app_replacement_helper(current_app)
            css_text = (current_app / "esp_text_replacement_module.py").read_text(
                encoding="utf-8"
            )
            scales = {
                class_name.upper(): float(scale)
                for class_name, scale in CSS_SCALE_RE.findall(css_text)
            }
            self.assertEqual(scales, phase619_gate.CSS_CLASS_SCALE)
            maximum = 0.0
            for surface, row in row_by_surface.items():
                fragment = deployed_records(language)[surface]["html"]
                ruby_matches = list(audit.RUBY_RE.finditer(fragment))
                with self.subTest(language=language, surface=surface):
                    self.assertEqual(
                        len(ruby_matches), row["planned"]["roles"].count("R")
                    )
                for ruby_match in ruby_matches:
                    block = ruby_match.group(0)
                    rt_match = phase619_gate.RT_RE.search(block)
                    self.assertIsNotNone(rt_match, (language, surface, block))
                    class_name = rt_match.group("class").upper()
                    self.assertIn(class_name, scales)
                    rb = visible(ruby_match.group("rb"))
                    rt_html = rt_match.group("rt")
                    rt = visible(rt_html)
                    expected_block = helper.output_format(
                        rb, rt, audit.FORMAT, widths
                    )
                    self.assertEqual(
                        block,
                        expected_block,
                        f"{language} stale rt class/markup for {surface!r}",
                    )
                    rb_width = strict_width(rb, widths)
                    self.assertGreater(rb_width, 0)
                    # ``output_format`` may intentionally insert ``<br>`` for
                    # a short rb such as ``is``.  The user's 2x constraint is
                    # a displayed-line constraint: concatenating both lines
                    # would reject the formatter's own safe layout.  Requiring
                    # exact formatter recomputation above prevents an
                    # arbitrary/manual break from hiding an over-wide label.
                    rt_lines = [
                        visible(piece) for piece in BR_RE.split(rt_html)
                    ]
                    self.assertTrue(all(rt_lines), (language, surface, block))
                    ratio = max(
                        strict_width(line, widths) * scales[class_name] / rb_width
                        for line in rt_lines
                    )
                    maximum = max(maximum, ratio)
                    self.assertLessEqual(
                        ratio,
                        2.0,
                        f"{language} {surface!r} {rb!r}/{rt!r} ratio={ratio}",
                    )
            maxima[language] = maximum
        self.assertEqual(
            width_hashes, {phase619_gate.CHAR_WIDTHS_SHA256},
            f"three-language char-width authority drift: {maxima!r}",
        )

    def test_case_exact_proper_glosses_do_not_leak_to_lowercase(self):
        proper_surfaces = ledger()["policy"]["proper_foreign"]["surfaces"]
        self.assertEqual(len(proper_surfaces), 11)
        for language in LANGUAGES:
            records = deployed_records(language)
            for surface in proper_surfaces:
                lower = surface.lower()
                positive_glosses = {
                    row["rt"] for row in records[surface]["annotations"]
                }
                with self.subTest(language=language, surface=surface, probe=lower):
                    self.assertTrue(positive_glosses)
                    self.assertTrue(
                        positive_glosses.isdisjoint(
                            row["rt"] for row in records[lower]["annotations"]
                        ),
                        f"case-sensitive R94 gloss leaked: {surface!r} -> {lower!r}",
                    )

    def test_watanabe_case_semantics_are_batch_order_independent(self):
        expected = {
            "Watanabe": "R:Watanabe",
            "watanabe": "L:watanabe",
            "WATANABE": "L:WATANABE",
        }
        orders = (
            ("Watanabe", "watanabe", "WATANABE"),
            ("WATANABE", "watanabe", "Watanabe"),
        )
        for language in LANGUAGES:
            for order in orders:
                records = render_ordered_records(language, order)
                for surface, typed in expected.items():
                    with self.subTest(
                        language=language, order=order, surface=surface,
                    ):
                        self.assertEqual(records[surface]["typed"], typed)

    def test_hongkong_closed_family_does_not_match_inside_larger_tokens(self):
        expected_by_surface = {
            row["surface"]: row["languages"]["JA"]["expected_typed"]
            for row in ledger()["residuals"]
        }
        for language in LANGUAGES:
            records = deployed_records(language)
            for probe, licensed_surface in HONGKONG_LEAKAGE_PROBES.items():
                licensed_signature = expected_by_surface[licensed_surface].casefold()
                observed = records[probe]["typed"].casefold()
                with self.subTest(
                    language=language, probe=probe, licensed=licensed_surface,
                ):
                    self.assertNotIn(
                        licensed_signature,
                        observed,
                        "closed Hongkong correction matched as a substring",
                    )


if __name__ == "__main__":
    unittest.main()
