# -*- coding: utf-8 -*-
"""Fast unit checks for the no-worsening reference normalizer."""
from pathlib import Path
import importlib
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

    def test_historical_overlay_render_switches_generic_helper_by_app_path(self):
        class FakeRuntime:
            @staticmethod
            def orchestrate_comprehensive_esperanto_text_replacement(
                text, _skip, _local, _capture, _global, _two, _format,
            ):
                return text

        class LazyHistoricalOverlay:
            seen_markers = []

            @staticmethod
            def merge_overlay(global_rules, _baseline_entries):
                return global_rules

            @classmethod
            def autofix_render(
                cls, text, skip, local, capture, global_rules, two, fmt,
                _data_dir, _mode, orchestrate,
            ):
                helper = importlib.import_module(
                    "esp_replacement_json_make_module"
                )
                cls.seen_markers.append(helper.MARKER)
                return orchestrate(
                    text, skip, local, capture, global_rules, two, fmt,
                )

        payload = {
            "replacements_final_list": [],
            "localized_string": [],
            "replacements_list_for_2char": [],
        }
        previous_path = list(sys.path)
        previous_helper = sys.modules.get("esp_replacement_json_make_module")
        try:
            with tempfile.TemporaryDirectory() as temporary_directory:
                root = Path(temporary_directory)
                for marker in ("JA", "ZH", "KO"):
                    app_dir = root / f"App-{marker}"
                    app_dir.mkdir()
                    (app_dir / "app_data").mkdir()
                    (app_dir / "esp_replacement_json_make_module.py").write_text(
                        f"MARKER = {marker!r}\n", encoding="utf-8"
                    )
                    # This is the explicit activation performed immediately
                    # before each historical-overlay render in evaluate_language.
                    audit.load_app_replacement_helper(app_dir)
                    audit.render_signatures(
                        FakeRuntime, app_dir, payload, ["vorto"], 1,
                        placeholder_lists=([], []),
                        overlay=LazyHistoricalOverlay,
                        corrections=[],
                    )
            self.assertEqual(
                LazyHistoricalOverlay.seen_markers, ["JA", "ZH", "KO"]
            )
        finally:
            sys.path[:] = previous_path
            if previous_helper is None:
                sys.modules.pop("esp_replacement_json_make_module", None)
            else:
                sys.modules["esp_replacement_json_make_module"] = previous_helper

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

            @staticmethod
            def _ruby_csv(_data_dir):
                return "ruby.csv"

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            app_dir = root / "App"
            data_dir = app_dir / "app_data"
            data_dir.mkdir(parents=True)
            code_path = app_dir / "esp_replacement_json_make_module.py"
            code_path.write_bytes(b"same\r\ncode\r\n")
            # These working-tree bytes intentionally differ from HEAD.
            (data_dir / "char_widths.json").write_bytes(b"current-widths")
            (data_dir / "ruby.csv").write_bytes(b"current-ruby")
            (data_dir / "kanji.csv").write_bytes(b"current-kanji")
            isolated = root / "isolated"
            head_bytes = {
                "App/esp_replacement_json_make_module.py": b"same\ncode\n",
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
            self.assertEqual(len(fingerprints), 4)

    def test_head_overlay_code_dependency_must_still_match_head(self):
        class FakeOverlay:
            KANJI_CSV = "kanji.csv"

            @staticmethod
            def _ruby_csv(_data_dir):
                return "ruby.csv"

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            app_dir = root / "App"
            (app_dir / "app_data").mkdir(parents=True)
            (app_dir / "esp_replacement_json_make_module.py").write_bytes(
                b"working-tree-code"
            )
            with (
                mock.patch.object(audit, "ROOT", root),
                mock.patch.object(
                    audit, "load_head_bytes", return_value=b"head-code"
                ),
            ):
                with self.assertRaisesRegex(
                    ValueError, "HEAD overlay code dependency differs"
                ):
                    audit.materialize_head_overlay_dependencies(
                        app_dir, FakeOverlay, "HEAD", root / "isolated",
                    )

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
