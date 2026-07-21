# -*- coding: utf-8 -*-
"""Fast unit checks for the no-worsening reference normalizer."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import no_worsening_audit as audit


class ExpectedPiecePolicyTests(unittest.TestCase):
    def test_resume_context_allows_only_pinned_render_code_revision(self):
        current = {"reference_sha256": "r", "audit_code_sha256": "new"}
        self.assertTrue(audit.resume_context_matches(current, current))
        predecessor = {
            "reference_sha256": "r",
            "audit_code_sha256": next(
                iter(audit.RESUME_COMPATIBLE_AUDIT_CODE_SHA256)
            ),
        }
        self.assertTrue(audit.resume_context_matches(predecessor, current))
        self.assertFalse(audit.resume_context_matches(
            {**predecessor, "reference_sha256": "other"}, current,
        ))
        self.assertFalse(audit.resume_context_matches(
            {"reference_sha256": "r", "audit_code_sha256": "unknown"},
            current,
        ))

    def test_identical_runtime_code_has_identical_full_and_data_only_delta(self):
        """A swallowed sibling-import error must not create fake full deltas."""
        class FakeRuntime:
            @staticmethod
            def orchestrate_comprehensive_esperanto_text_replacement(
                text, _skip, _local, _capture, _global, _two, _format,
            ):
                return text.replace(
                    "belo", "b<ruby>el<rt>x</rt></ruby>o",
                )

        payload = {
            "replacements_final_list": [],
            "localized_string": [],
            "replacements_list_for_2char": [],
        }
        overlay_source = b'''\
import importlib.util
import os

def _replacement_helper():
    path = os.path.join(os.path.dirname(__file__), "esp_replacement_json_make_module.py")
    spec = importlib.util.spec_from_file_location("synthetic_first_char_helper", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def merge_overlay(global_rules, _entries):
    return global_rules

def auto_overlay_entries(html, _data_dir, _mode):
    try:
        return _replacement_helper().repair_first_char(html)
    except Exception:
        return None

def autofix_render(text, ps, local, capture, global_rules, two, fmt,
                   data_dir, mode, orchestrate):
    first = orchestrate(text, ps, local, capture, global_rules, two, fmt)
    return auto_overlay_entries(first, data_dir, mode) or first
'''
        helper_source = b'''\
def repair_first_char(html):
    return html.replace(
        "b<ruby>el<rt>x</rt></ruby>o",
        "<ruby>bel<rt>x</rt></ruby>o",
    )
'''
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            app_dir = root / "App"
            app_dir.mkdir()
            (app_dir / "app_data").mkdir()
            (app_dir / "esp_overlay_module.py").write_bytes(overlay_source)
            (app_dir / "esp_replacement_json_make_module.py").write_bytes(
                helper_source
            )
            current_overlay = audit.overlay_module(app_dir, "JA")

            head_sources = {
                "App/esp_overlay_module.py": overlay_source,
                "App/esp_replacement_json_make_module.py": helper_source,
            }
            with (
                mock.patch.object(audit, "ROOT", root),
                mock.patch.object(
                    audit, "load_head_bytes",
                    side_effect=lambda relative, _revision: head_sources[
                        relative.as_posix()
                    ],
                ),
            ):
                historical_overlay, _fingerprints = audit.head_overlay_module(
                    app_dir, "JA", "HEAD", root / "App-head",
                )

            common = dict(
                module=FakeRuntime,
                app_dir=app_dir,
                payload=payload,
                surfaces=["belo"],
                batch_size=1,
                placeholder_lists=([], []),
                corrections=[],
            )
            data_isolated_baseline = audit.render_signatures(
                overlay=current_overlay, **common,
            )
            comprehensive_baseline = audit.render_signatures(
                overlay=historical_overlay, **common,
            )
            current = audit.render_signatures(
                overlay=current_overlay, **common,
            )
        expected_signature = current["belo"]["signature"]
        cases = {
            "synthetic": {
                "surface": "belo",
                "signature": expected_signature,
                "expected": "bel/o",
                "sources": {"synthetic": 1},
            },
        }
        data_delta = audit.compare_outputs(
            "JA", "data_isolated", data_isolated_baseline, current,
            cases, ["belo"],
        )["signature_changes"]
        full_delta = audit.compare_outputs(
            "JA", "comprehensive", comprehensive_baseline, current,
            cases, ["belo"],
        )["signature_changes"]
        self.assertEqual(full_delta, data_delta)
        self.assertEqual(full_delta, [])

    def test_current_fingerprint_tracks_the_kanji_csv_used_by_overlay(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            app_dir = root / "Esperanto-Kanji-Ruby-JA"
            data_dir = app_dir / "app_data"
            data_dir.mkdir(parents=True)
            for filename in (
                "main.py",
                "esp_text_replacement_module.py",
                "esp_overlay_module.py",
                "esp_replacement_json_make_module.py",
            ):
                (app_dir / filename).write_bytes(filename.encode())
            for filename in (
                "置換リスト_ルビ.json",
                "placeholders_skip.txt",
                "placeholders_localcapture.txt",
                "char_widths.json",
                "エスペラント語根-日本語訳ルビ対応リスト.csv",
                "世界语词根-汉字对应列表_参照2新割当_7791.csv",
                "user_corrections.json",
            ):
                (data_dir / filename).write_bytes(filename.encode("utf-8"))
            with mock.patch.object(audit, "ROOT", root):
                before = audit.current_app_fingerprint(app_dir)
                (data_dir / "世界语词根-汉字对应列表_参照2新割当_7791.csv").write_bytes(
                    b"changed"
                )
                after = audit.current_app_fingerprint(app_dir)
            self.assertNotEqual(before, after)

    def test_head_overlay_data_is_materialized_from_git_not_worktree(self):
        class FakeOverlay:
            KANJI_CSV = "kanji.csv"
            _LANG_CSV = {"app": "ruby.csv"}

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            app_dir = root / "App"
            data_dir = app_dir / "app_data"
            data_dir.mkdir(parents=True)
            # These working-tree bytes intentionally differ from HEAD.
            (data_dir / "char_widths.json").write_bytes(b"current-widths")
            (data_dir / "ruby.csv").write_bytes(b"current-ruby")
            (data_dir / "kanji.csv").write_bytes(b"current-kanji")
            isolated = root / "isolated"
            head_bytes = {
                "App/app_data/char_widths.json": b"head-widths",
                "App/app_data/ruby.csv": b"head-ruby",
                "App/app_data/kanji.csv": b"head-kanji",
            }

            def load_head(relative, _revision):
                return head_bytes[relative.as_posix()]

            with (
                mock.patch.object(audit, "ROOT", root),
                mock.patch.object(audit, "load_head_bytes", side_effect=load_head),
            ):
                fingerprints = audit.materialize_head_overlay_dependencies(
                    app_dir, FakeOverlay, "HEAD", isolated,
                )

            self.assertEqual(
                (isolated / "char_widths.json").read_bytes(), b"head-widths"
            )
            self.assertEqual((isolated / "ruby.csv").read_bytes(), b"head-ruby")
            self.assertEqual((isolated / "kanji.csv").read_bytes(), b"head-kanji")
            self.assertEqual(len(fingerprints), 3)

    def test_head_overlay_and_sibling_helper_are_exact_real_files(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            app_dir = root / "App"
            app_dir.mkdir()
            (app_dir / "esp_overlay_module.py").write_bytes(b"worktree-overlay")
            (app_dir / "esp_replacement_json_make_module.py").write_bytes(
                b"worktree-helper"
            )
            overlay_source = b'''\
import importlib.util
import os
def helper_marker():
    path = os.path.join(os.path.dirname(__file__), "esp_replacement_json_make_module.py")
    spec = importlib.util.spec_from_file_location("exact_head_helper", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.MARKER
'''
            helper_source = b'MARKER = "HEAD"\n'
            sources = {
                "App/esp_overlay_module.py": overlay_source,
                "App/esp_replacement_json_make_module.py": helper_source,
            }
            isolated = root / "isolated-App"
            with (
                mock.patch.object(audit, "ROOT", root),
                mock.patch.object(
                    audit, "load_head_bytes",
                    side_effect=lambda relative, _revision: sources[
                        relative.as_posix()
                    ],
                ),
            ):
                module, fingerprints = audit.head_overlay_module(
                    app_dir, "JA", "HEAD", isolated,
                )
            self.assertEqual(module.helper_marker(), "HEAD")
            self.assertEqual(Path(module.__file__).resolve(), (
                isolated / "esp_overlay_module.py"
            ).resolve())
            self.assertEqual(
                (isolated / "esp_overlay_module.py").read_bytes(),
                overlay_source,
            )
            self.assertEqual(
                (isolated / "esp_replacement_json_make_module.py").read_bytes(),
                helper_source,
            )
            self.assertEqual(len(fingerprints), 2)

    def test_internal_an_is_ruby_but_adjective_accusative_is_bare(self):
        self.assertEqual(
            audit.expected_typed_parts("ter/an/o"),
            [("ter", True), ("an", True), ("o", False)],
        )
        self.assertEqual(
            audit.expected_typed_parts("plat/a/n"),
            [("plat", True), ("a", False), ("n", False)],
        )

    def test_internal_on_is_ruby(self):
        self.assertEqual(
            audit.expected_typed_parts("du/on/o"),
            [("du", True), ("on", True), ("o", False)],
        )

    def test_finite_verb_endings_are_ruby_but_i_u_are_bare(self):
        for ending in ("as", "is", "os", "us"):
            with self.subTest(ending=ending):
                self.assertEqual(
                    audit.expected_typed_parts(f"kant/{ending}"),
                    [("kant", True), (ending, True)],
                )
        for ending in ("u", "i"):
            with self.subTest(ending=ending):
                self.assertEqual(
                    audit.expected_typed_parts(f"kant/{ending}"),
                    [("kant", True), (ending, False)],
                )

    def test_standalone_word_matching_an_ending_is_ruby(self):
        self.assertEqual(audit.expected_typed_parts("en"), [("en", True)])
        self.assertEqual(audit.expected_typed_parts("ajn"), [("ajn", True)])

    def test_country_io_ia_endings_are_bare_only_after_a_root(self):
        for ending in (
            "io", "ia", "ion", "ian", "ioj", "iojn", "iaj", "iajn",
        ):
            with self.subTest(ending=ending):
                self.assertEqual(
                    audit.expected_typed_parts(f"Japan/{ending}"),
                    [("Japan", True), (ending, False)],
                )
                self.assertEqual(
                    audit.expected_typed_parts(ending),
                    [(ending, True)],
                )
        self.assertEqual(
            audit.expected_signature("Katalun/io/n"),
            ("Katalunion", (("Katalun", True), ("ion", False))),
        )
        self.assertEqual(
            audit.expected_typed_parts("ia/manier/e"),
            [("ia", True), ("manier", True), ("e", False)],
        )

    def test_adjacent_bare_pieces_have_no_observable_internal_cut(self):
        self.assertEqual(
            audit.expected_signature("plat/a/n"),
            ("platan", (("plat", True), ("an", False))),
        )
        self.assertEqual(
            audit.expected_signature("elektr/o/n"),
            ("elektron", (("elektr", True), ("on", False))),
        )

    def test_ruby_and_literal_role_reversal_is_not_equivalent(self):
        expected = audit.signature_from_typed_parts(
            [("man", True), ("on", False)]
        )
        reversed_roles = audit.signature_from_typed_parts(
            [("man", False), ("on", True)]
        )
        self.assertNotEqual(expected, reversed_roles)

    def test_hyphen_inside_gold_piece_is_compound_punctuation(self):
        self.assertEqual(
            audit.expected_typed_parts("dent/alveol-son/o"),
            [
                ("dent", True), ("alveol", True), ("-", False),
                ("son", True), ("o", False),
            ],
        )
        self.assertEqual(
            audit.expected_typed_parts("kabl/o-ret/o"),
            [
                ("kabl", True), ("o", False), ("-", False),
                ("ret", True), ("o", False),
            ],
        )

    def test_plural_ending_before_hyphen_remains_literal(self):
        self.assertEqual(
            audit.expected_typed_parts("majstr/oj-kant/ist/oj"),
            [
                ("majstr", True), ("oj", False), ("-", False),
                ("kant", True), ("ist", True), ("oj", False),
            ],
        )
        # ``on`` here is the fractional suffix, not a grammatical plural or
        # accusative ending, and therefore remains an annotated ruby unit.
        self.assertEqual(
            audit.expected_typed_parts("du/on-teori/o"),
            [
                ("du", True), ("on", True), ("-", False),
                ("teori", True), ("o", False),
            ],
        )
        expected = audit.expected_signature("dent/alveol-son/o")
        self.assertNotEqual(expected, audit.expected_signature("dent/alveol/son/o"))
        self.assertNotEqual(expected, audit.expected_signature("dent/alveol--son/o"))

    def test_manifest_can_declare_a_hyphenated_proper_name_atomic(self):
        self.assertEqual(
            audit.expected_signature(
                "BUENOS-AIRES/O", frozenset({"BUENOS-AIRES"})
            ),
            (
                "BUENOS-AIRESO",
                (("BUENOS-AIRES", True), ("O", False)),
            ),
        )

    def test_rendered_standalone_hyphen_is_retained(self):
        rendered = (
            "<ruby>dent<rt>x</rt></ruby>"
            "<ruby>alveol<rt>x</rt></ruby>-"
            "<ruby>son<rt>x</rt></ruby>o"
        )
        self.assertEqual(
            audit.signature_from_typed_parts(
                audit.rendered_typed_parts(rendered)
            ),
            audit.expected_signature("dent/alveol/-/son/o"),
        )

    def test_multiline_ruby_base_does_not_desynchronize_later_words(self):
        html = (
            "<body><ruby>DEGUĈI\n Kurenai<rt>name</rt></ruby> "
            "<ruby>salut<rt>greet</rt></ruby>"
            "<ruby>is<rt>past</rt></ruby></body>"
        )
        parsed = list(audit.parse_corpus_words(html))
        self.assertEqual(
            [(surface, audit.display_typed_parts(parts))
             for surface, parts in parsed],
            [
                ("DEGUĈI\n Kurenai", "R:DEGUĈI Kurenai"),
                ("salutis", "R:salut|R:is"),
            ],
        )

    def test_multiline_phrase_surface_is_normalized_and_evaluable(self):
        parts = [("DEGUĈI\r\n    Kurenai", True)]
        self.assertEqual(
            audit.signature_from_typed_parts(parts),
            ("DEGUĈI Kurenai", (("DEGUĈI Kurenai", True),)),
        )

    def test_cjk_and_hangul_literals_end_latin_corpus_units(self):
        html = (
            "<body><ruby>Sun<rt>name</rt></ruby>氏は本当に "
            "<ruby>Foli<rt>leaf</rt></ruby>o에서도</body>"
        )
        parsed = [
            (audit.canonical(surface), audit.display_typed_parts(parts))
            for surface, parts in audit.parse_corpus_words(html)
        ]
        self.assertEqual(parsed, [("Sun", "R:Sun"), ("Folio", "R:Foli|L:o")])

    def test_latin_extended_literal_remains_in_corpus_unit(self):
        html = (
            "<body><ruby>Chełmno<rt>place</rt></ruby>-"
            "<ruby>region<rt>region</rt></ruby>on</body>"
        )
        parsed = list(audit.parse_corpus_words(html))
        self.assertEqual(len(parsed), 1)
        self.assertEqual(audit.canonical(parsed[0][0]), "Chełmno-regionon")
        self.assertEqual(
            audit.display_typed_parts(parsed[0][1]),
            "R:Chełmno|L:-|R:region|L:on",
        )

    def test_renderer_preserves_spaces_and_non_esperanto_literal_text(self):
        rendered = (
            " <ruby>Sun<rt>name</rt></ruby>氏は "
            "<ruby>DEGUĈI Kurenai<rt>name</rt></ruby> "
        )
        self.assertEqual(
            audit.signature_from_typed_parts(
                audit.rendered_typed_parts(rendered)
            ),
            (
                "Sun氏は DEGUĈI Kurenai",
                (
                    ("Sun", True),
                    ("氏は ", False),
                    ("DEGUĈI Kurenai", True),
                ),
            ),
        )

    def test_renderer_trims_probe_padding_inside_output_wrapper(self):
        rendered = (
            "<span> <ruby>Brit<rt>Britain</rt></ruby>aj "
            "<ruby>Insul<rt>island</rt></ruby>oj </span>"
        )
        self.assertEqual(
            audit.signature_from_typed_parts(
                audit.rendered_typed_parts(rendered)
            )[0],
            "Britaj Insuloj",
        )

    def test_atomic_honorific_keeps_hyphen_inside_ruby(self):
        self.assertEqual(
            audit.expected_signature("s-ro"),
            ("s-ro", (("s-ro", True),)),
        )

    def test_gold_proper_name_hyphen_is_atomic_but_common_compound_is_not(self):
        reviewed = {"Abu-Dabio": frozenset({"Abu-Dabi"})}
        proper = audit.reviewed_atomic_hyphen_pieces(
            "Abu-Dabio", "Abu-Dabi/o", reviewed,
        )
        self.assertEqual(
            audit.expected_signature("Abu-Dabi/o", proper),
            ("Abu-Dabio", (("Abu-Dabi", True), ("o", False))),
        )
        common = audit.reviewed_atomic_hyphen_pieces(
            "kablo-reto", "kabl/o-ret/o", reviewed,
        )
        self.assertEqual(common, frozenset())
        self.assertEqual(
            audit.expected_signature("kabl/o-ret/o", common),
            (
                "kablo-reto",
                (("kabl", True), ("o-", False), ("ret", True), ("o", False)),
            ),
        )

    def test_standalone_one_letter_gold_entry_is_literal(self):
        self.assertEqual(audit.expected_signature("a"), ("a", (("a", False),)))
        self.assertEqual(audit.expected_signature("o"), ("o", (("o", False),)))
        self.assertEqual(audit.expected_signature("ar"), ("ar", (("ar", True),)))

    def test_guide_overrides_proper_kioto_and_common_hyphen_expressions(self):
        self.assertEqual(
            audit.expected_signature(
                audit.OFFICIAL_LONG_ROOT_OVERRIDES["Kioto-protokolo"]
            ),
            (
                "Kioto-protokolo",
                (("Kioto", True), ("-", False), ("protokol", True), ("o", False)),
            ),
        )
        for surface in ("glu-glu-glu", "pli-ol-unu"):
            signature = audit.expected_signature(
                audit.OFFICIAL_LONG_ROOT_OVERRIDES[surface]
            )
            self.assertEqual(signature[0], surface)
            self.assertEqual([span[1] for span in signature[1]], [True, False, True, False, True])

    def test_two_track_project_boundary_reviews_remain_coarse_for_ruby(self):
        self.assertEqual(
            audit.PROJECT_RUBY_BOUNDARY_OVERRIDES,
            {"Ionia": "Ioni/a", "alternanco": "alternanc/o"},
        )
        self.assertEqual(
            {
                review["decision"]
                for review in audit.PROJECT_RUBY_BOUNDARY_REVIEWS.values()
            },
            {
                "project_conservative_ruby_display_override",
                "project_piv_long_root",
            },
        )
        for surface, review in audit.PROJECT_RUBY_BOUNDARY_REVIEWS.items():
            self.assertTrue(review["authority"])
            self.assertTrue(review["counterevidence"])
            self.assertTrue(review["reason"])
            self.assertEqual(
                audit.expected_signature(
                    review["selected_decomposition"]
                )[0],
                surface,
            )

    def test_project_boundary_override_requires_its_exact_signature(self):
        cases = {}
        coarse = audit.expected_signature("Ioni/a")
        fine = audit.expected_signature("Ion/i/a")
        audit.add_case(
            cases, "Ionia", coarse, "Ioni/a",
            "gold_project_ruby_boundary_override", 1,
        )
        # A second contextual authority can make the surface generally
        # acceptable, but it must not silently neutralize the explicit
        # project-level Ruby display decision.
        audit.add_case(
            cases, "Ionia", fine, "Ion/i/a", "unit_alternative", 1,
        )
        fine_output = {
            "Ionia": {
                "signature": fine,
                "decomposition": "Ion/i/a",
                "typed_decomposition": "R:Ion|R:i|L:a",
            }
        }
        result = audit.compare_outputs(
            "JA", "unit", fine_output, fine_output, cases, ["Ionia"]
        )
        self.assertFalse(result["current_unreferenced_wrong_surfaces"])
        self.assertEqual(
            len(result["current_project_ruby_boundary_override_wrong_cases"]),
            1,
        )
        self.assertEqual(
            result["sources"]["gold_project_ruby_boundary_override"][
                "current_correct_weight"
            ],
            0,
        )
        self.assertFalse(result["gate"])

    def test_phase532_policy_source_cannot_hide_behind_an_alternative(self):
        cases = {}
        selected = audit.expected_signature("lul/u")
        legacy = audit.expected_signature("lulu")
        audit.add_case(
            cases, "lulu", selected, "lul/u",
            audit.PHASE532_REFERENCE_SOURCE, 1,
        )
        audit.add_case(
            cases, "lulu", legacy, "lulu", "unit_alternative", 1,
        )
        legacy_output = {
            "lulu": {
                "signature": legacy,
                "decomposition": "lulu",
                "typed_decomposition": "R:lulu",
            }
        }
        result = audit.compare_outputs(
            "JA", "phase532_exact", legacy_output, legacy_output,
            cases, ["lulu"],
        )
        self.assertFalse(result["current_unreferenced_wrong_surfaces"])
        self.assertEqual(
            result["current_exact_required_wrong_cases"][0][
                "exact_required_sources"
            ],
            [audit.PHASE532_REFERENCE_SOURCE],
        )
        self.assertEqual(
            result["sources"][audit.PHASE532_REFERENCE_SOURCE][
                "current_correct_weight"
            ],
            0,
        )
        self.assertFalse(result["gate"])

    def test_case_is_preserved_in_reference_signature(self):
        self.assertEqual(
            audit.expected_signature("Kac/um/i"),
            (
                "Kacumi",
                (("Kac", True), ("um", True), ("i", False)),
            ),
        )

    def test_unchanged_current_wrong_is_a_gate_failure(self):
        cases = {}
        audit.add_case(
            cases, "manon", audit.expected_signature("man/on"),
            "man/on", "html_corpus", 1,
        )
        wrong = {
            "manon": {
                "signature": audit.signature_from_typed_parts(
                    [("man", False), ("on", True)]
                ),
                "decomposition": "man/on",
                "typed_decomposition": "L:man|R:on",
            }
        }
        result = audit.compare_outputs(
            "JA", "unit", wrong, wrong, cases, ["manon"]
        )
        self.assertFalse(result["gate"])
        self.assertEqual(len(result["current_unreferenced_wrong_surfaces"]), 1)

    def test_reviewed_conflict_resolution_keeps_only_allowed_roles(self):
        cases = {}
        whole = audit.expected_signature("Ivo")
        declined = audit.expected_signature("Iv/o")
        audit.add_case(cases, "Ivo", whole, "Ivo", "html_corpus", 2)
        audit.add_case(cases, "Ivo", declined, "Iv/o", "gold_unmarked", 1)
        resolved = audit.resolve_reviewed_reference_cases(
            cases, {"Ivo": {whole}}
        )
        self.assertEqual(len(resolved), 1)
        self.assertEqual(next(iter(resolved.values()))["signature"], whole)

    def test_contextual_conflict_can_retain_two_reviewed_roles(self):
        cases = {}
        verb = audit.expected_signature("Tem/is")
        name = audit.expected_signature("Temis")
        audit.add_case(cases, "Temis", verb, "Tem/is", "html_corpus", 1)
        audit.add_case(cases, "Temis", name, "Temis", "gold_unmarked", 1)
        resolved = audit.resolve_reviewed_reference_cases(
            cases, {"Temis": {verb, name}}
        )
        self.assertEqual(len(resolved), 2)

    def test_switch_between_contextual_alternatives_is_not_a_regression(self):
        cases = {}
        verb = audit.expected_signature("Tem/is")
        name = audit.expected_signature("Temis")
        audit.add_case(cases, "Temis", verb, "Tem/is", "html_corpus", 6)
        audit.add_case(cases, "Temis", name, "Temis", "gold_unmarked", 1)
        baseline = {
            "Temis": {
                "signature": name,
                "decomposition": "Temis",
                "typed_decomposition": "R:Temis",
            }
        }
        current = {
            "Temis": {
                "signature": verb,
                "decomposition": "Tem/is",
                "typed_decomposition": "R:Tem|R:is",
            }
        }
        result = audit.compare_outputs(
            "JA", "contextual", baseline, current, cases, ["Temis"]
        )
        self.assertTrue(result["gate"])
        self.assertEqual(result["regression_cases"], [])
        self.assertEqual(result["signature_changes"], [{
            "surface": "Temis",
            "baseline": "Temis",
            "baseline_typed": "R:Temis",
            "baseline_signature": audit.signature_payload(name),
            "current": "Tem/is",
            "current_typed": "R:Tem|R:is",
            "current_signature": audit.signature_payload(verb),
        }])
        current_only = audit.compare_outputs(
            "JA", "current_only", current, current, cases, ["Temis"]
        )
        self.assertNotIn("signature_changes", current_only)

    def test_deployed_strand_autofix_is_applied_only_to_initial_consonant(self):
        class FakeOverlay:
            calls = []

            @classmethod
            def autofix_decomp(cls, surface, _data_dir):
                cls.calls.append(surface)
                return {"paĝoj": "paĝ/oj", "oferis": "ofer/is"}.get(surface)

        fixed = audit.apply_strand_autofix(
            "paĝoj", [("p", False), ("aĝ", True), ("oj", False)],
            FakeOverlay, ".",
        )
        self.assertEqual(
            audit.signature_from_typed_parts(fixed),
            ("paĝoj", (("paĝ", True), ("oj", False))),
        )
        unchanged = audit.apply_strand_autofix(
            "oferis", [("o", False), ("fer", True), ("is", False)],
            FakeOverlay, ".",
        )
        self.assertEqual(
            unchanged,
            [("o", False), ("fer", True), ("is", False)],
        )
        self.assertEqual(FakeOverlay.calls, ["paĝoj"])


if __name__ == "__main__":
    unittest.main()
