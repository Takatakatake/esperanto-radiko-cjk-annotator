# -*- coding: utf-8 -*-
"""Regression tests for morphology generation and deployed ruby JSONs."""
import gc
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import types
import unittest
import tempfile


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import gen_replacement as canonical
from atomic_json import atomic_binary_copy, atomic_file_copy, atomic_json_dump
import apply_corpus_word_anno as corpus_data
import check_multilingual_structure as multilingual_structure
import check_kanji_structure as kanji_structure
import fix_ruby_postregen as postregen
from gold_snapshot import consistent_snapshot


RUBY_RE = re.compile(r"<ruby>(.*?)<rt[^>]*>.*?</rt></ruby>", re.DOTALL)
FINAL_RUBY_RE = re.compile(
    r'<ruby>([^<]+)<rt class="[^"]+">((?:[^<]|<br>)*)</rt></ruby>',
    re.IGNORECASE,
)
LATIN_RE = re.compile(r"[A-Za-zĈĉĜĝĤĥĴĵŜŝŬŭ]+")


def _decomposition(rendered):
    pieces = []
    pos = 0
    for match in RUBY_RE.finditer(rendered):
        literal = re.sub(r"<[^>]+>", "", rendered[pos:match.start()])
        pieces.extend(LATIN_RE.findall(literal))
        pieces.append(re.sub(r"<[^>]+>", "", match.group(1)))
        pos = match.end()
    literal = re.sub(r"<[^>]+>", "", rendered[pos:])
    pieces.extend(LATIN_RE.findall(literal))
    return "/".join(p.lower() for p in pieces if p)


def _manifest_decomposition(row):
    pieces = []
    for span in row["signature"]["spans"]:
        if span["ruby"]:
            pieces.append(span["text"])
        else:
            pieces.extend(LATIN_RE.findall(span["text"]))
    return "/".join(piece.lower() for piece in pieces if piece)


def _target_structural_signature(target):
    parts = [piece for piece in target.split("/") if piece]
    spans = []
    for index, piece in enumerate(parts):
        is_ruby = not canonical.setting_piece_is_bare(piece, index, len(parts))
        kind = "R" if is_ruby else "L"
        if spans and kind == "L" and spans[-1][0] == "L":
            spans[-1] = ("L", spans[-1][1] + piece)
        else:
            spans.append((kind, piece))
    return tuple(f"{kind}:{piece}" for kind, piece in spans)


def _target_decomposition(target):
    pieces = []
    for span in _target_structural_signature(target):
        kind, text = span.split(":", 1)
        if kind == "R":
            pieces.append(text)
        else:
            pieces.extend(LATIN_RE.findall(text))
    return "/".join(piece.lower() for piece in pieces if piece)


def _runtime_module(app_dir, language):
    path = app_dir / "esp_text_replacement_module.py"
    spec = importlib.util.spec_from_file_location(f"esp_text_replacement_{language}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _overlay_module(app_dir, language):
    path = app_dir / "esp_overlay_module.py"
    spec = importlib.util.spec_from_file_location(f"esp_overlay_{language}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GenerationRuleTests(unittest.TestCase):
    def test_consistent_snapshot_reports_line_count(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "authority.txt"
            raw = b"alpha\r\nbeta\ngamma"
            source.write_bytes(raw)
            observed_raw, identity = consistent_snapshot(source)
        self.assertEqual(observed_raw, raw)
        self.assertEqual(identity["bytes"], len(raw))
        self.assertEqual(identity["lines"], 3)
        self.assertEqual(
            identity["sha256"], hashlib.sha256(raw).hexdigest().upper(),
        )

    def test_short_overlay_cannot_preempt_longer_reviewed_exact_rule(self):
        for language in ("JA", "ZH", "KO"):
            overlay = _overlay_module(
                ROOT / f"Esperanto-Kanji-Ruby-{language}", language,
            )
            rules = [
                [" Nov-Kaledoniano ", " LONG ", " $LONG$ "],
                ["Nov", "OLD", "$NOV$"],
            ]
            merged = overlay.merge_overlay(
                rules, [["Nov", "AUTO", "$AUTO$"]],
            )
            self.assertEqual(merged[0], rules[0], language)
            self.assertEqual(merged[1][0], " Nov ", language)
            self.assertEqual(merged[1][1], " AUTO ", language)
            self.assertEqual(merged[2][0], "Nov", language)
            self.assertEqual(merged[2][1], "AUTO", language)

            new_exact = overlay.merge_overlay(
                [["sporti", "SHORT", "$SHORT$"]],
                [["sportino", "EXACT", "$EXACT$"]],
            )
            self.assertEqual(new_exact[0][0], " sportino ", language)
            self.assertEqual(new_exact[1][0], "sporti", language)

    def test_explicit_typed_ruby_keeps_authored_apostrophe_atomic(self):
        self.assertEqual(
            canonical.split_typed_ruby_piece_punctuation("klak'", "カチ音'"),
            ("klak'", "カチ音'", ""),
        )

    def test_typed_annotation_failure_policy_distinguishes_ruby_and_kanji(self):
        source = (HERE / "gen_replacement.py").read_text(encoding="utf-8")
        self.assertIn("elif '汉字替换' in format_type:", source)
        self.assertIn("_parts.append(_pc)", source)
        self.assertIn("typed ruby piece lacks contextual annotation", source)
        self.assertIn("Replaced_String = _stem_ns", source)
        self.assertEqual(
            canonical.split_trailing_sentence_punctuation("klak'", "カチ音'"),
            ("klak", "カチ音", "'"),
        )

    def test_canonical_generator_switches_to_each_apps_exact_helper(self):
        module_name = "esp_replacement_json_make_module"
        original_module = sys.modules.get(module_name)
        original_path = list(sys.path)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                app_a = Path(tmp) / "app-a"
                app_b = Path(tmp) / "app-b"
                app_a.mkdir()
                app_b.mkdir()
                (app_a / f"{module_name}.py").write_text(
                    "MARKER = 'a'\n", encoding="utf-8",
                )
                (app_b / f"{module_name}.py").write_text(
                    "MARKER = 'b'\n", encoding="utf-8",
                )

                helper_a = canonical.load_app_replacement_helper(app_a)
                helper_b = canonical.load_app_replacement_helper(app_b)

                self.assertEqual(helper_a.MARKER, "a")
                self.assertEqual(helper_b.MARKER, "b")
                self.assertEqual(
                    Path(helper_a.__file__).resolve(),
                    (app_a / f"{module_name}.py").resolve(),
                )
                self.assertEqual(
                    Path(helper_b.__file__).resolve(),
                    (app_b / f"{module_name}.py").resolve(),
                )
                self.assertIsNot(helper_a, helper_b)
        finally:
            sys.path[:] = original_path
            if original_module is None:
                sys.modules.pop(module_name, None)
            else:
                sys.modules[module_name] = original_module

    def test_each_overlay_loads_its_own_sibling_helper(self):
        helpers = []
        for language in ("JA", "ZH", "KO"):
            app_dir = ROOT / f"Esperanto-Kanji-Ruby-{language}"
            overlay_path = app_dir / "esp_overlay_module.py"
            spec = importlib.util.spec_from_file_location(
                f"esp_overlay_exact_helper_test_{language}", overlay_path,
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            helper = module._replacement_helper()
            self.assertEqual(
                Path(helper.__file__).resolve(),
                (app_dir / "esp_replacement_json_make_module.py").resolve(),
            )
            helpers.append(helper)
        self.assertEqual(len({id(helper) for helper in helpers}), 3)

    def test_typed_authority_errors_are_not_swallowed(self):
        source = Path(canonical.__file__).read_text(encoding="utf-8")
        self.assertIn(
            "except ValueError:\n                # Invalid typed roles", source,
        )
        self.assertNotRegex(source, r"(?m)^\s*except\s*:\s*$")

    def test_kanji_master_defaults_are_portable_and_manifest_pinned(self):
        fix_source = (HERE / "fix_kanji_2890.py").read_text(encoding="utf-8")
        resync_source = (HERE / "resync_kanji_master.py").read_text(
            encoding="utf-8",
        )
        pipeline_source = (HERE / "regenerate_all.py").read_text(
            encoding="utf-8",
        )
        for source in (fix_source, resync_source):
            self.assertNotIn(r"D:\GoogleDrive", source)
            self.assertIn("ESP_KANJI_MASTER_PATH", source)
        self.assertIn("ESP_EXPECTED_KANJI_MASTER_MANIFEST", pipeline_source)
        self.assertIn("ESP_EXPECTED_KANJI_MASTER_SHA256", pipeline_source)
        self.assertIn("expected_master_bytes", fix_source)

    def test_pinned_base_stemming_settings_manifest(self):
        path = HERE / "_base_stemming_settings.json"
        manifest = json.loads(
            (HERE / "_base_stemming_settings_manifest.json").read_text(
                encoding="utf-8",
            )
        )
        disk_raw = path.read_bytes()
        self.assertEqual(manifest["line_endings"], "canonical_lf")
        raw = disk_raw.replace(b"\r\n", b"\n")
        self.assertNotIn(b"\r", raw)
        self.assertEqual(manifest["schema_version"], 1)
        self.assertEqual(len(raw), manifest["bytes"])
        self.assertEqual(
            hashlib.sha256(raw).hexdigest().upper(), manifest["sha256"],
        )
        payload = json.loads(raw.decode("utf-8"))
        self.assertEqual(len(payload), manifest["rows"])
        semantic = json.dumps(
            payload[manifest["header_rows"]:],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        self.assertEqual(
            hashlib.sha256(semantic).hexdigest().upper(),
            manifest["semantic_sha256"],
        )
        self.assertTrue(
            manifest["provenance"]["head_three_language_semantic_equal"],
        )
        self.assertEqual(
            manifest["provenance"]["stale_backup_audit"]
            ["zh_word_boundary_only_action_diffs"],
            619,
        )
        source_paths = manifest["provenance"]["source_paths"]
        source_semantic_hashes = set()
        for language, source_path in source_paths.items():
            expected_blob = manifest["provenance"][f"{language}_blob"]
            commit_path = (
                f"{manifest['provenance']['git_head']}:{source_path}"
            )
            actual_blob = subprocess.check_output(
                ["git", "rev-parse", commit_path], cwd=ROOT, text=True,
            ).strip()
            self.assertEqual(actual_blob, expected_blob)
            source_raw = subprocess.check_output(
                ["git", "cat-file", "blob", expected_blob], cwd=ROOT,
            )
            source_payload = json.loads(source_raw.decode("utf-8"))
            source_semantic = json.dumps(
                source_payload[manifest["header_rows"]:],
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
            source_semantic_hashes.add(
                hashlib.sha256(source_semantic).hexdigest().upper()
            )
            self.assertEqual(payload[1:], source_payload[1:])
        self.assertEqual(
            source_semantic_hashes, {manifest["semantic_sha256"]},
        )

    def test_authored_rt_break_is_restored_without_splitting_its_tag(self):
        rendered = '<ruby>Sin<rt class="XS_S">[人名]シン</rt></ruby>'
        authored = '[人名<br>]シン'
        restored = canonical.restore_authored_rt_breaks(rendered, authored)
        self.assertEqual(
            restored,
            '<ruby>Sin<rt class="XS_S">[人名<br>]シン</rt></ruby>',
        )
        self.assertIsNone(re.search(r'<[^>]*<br\s*/?>', restored, re.I))
        self.assertEqual(
            canonical.restore_authored_rt_breaks(rendered, "plain gloss"),
            rendered,
        )
        with self.assertRaises(ValueError):
            canonical.restore_authored_rt_breaks(
                rendered + rendered, authored,
            )

    def test_case_sensitive_correction_removal_preserves_casefold_homograph(self):
        exact_removals = {
            canonical.correction_removal_identity("Sin", True),
        }
        self.assertIn(
            canonical.correction_removal_identity("Sin", True),
            exact_removals,
        )
        self.assertNotIn(
            canonical.correction_removal_identity("si/n", True),
            exact_removals,
        )
        self.assertEqual(
            canonical.correction_removal_identity("SIN", False),
            canonical.correction_removal_identity("si/n", False),
        )
        self.assertEqual(
            canonical.correction_removal_identity("Cxinio", True),
            canonical.correction_removal_identity("Ĉinio", True),
        )
        self.assertNotEqual(
            canonical.correction_removal_identity("cxinio", True),
            canonical.correction_removal_identity("Ĉinio", True),
        )
        settings = [
            ["si/n", 34000, ["ne"]],
            ["Sin", 39000, ["ne"]],
            ["kacumi", 69000, ["ne"]],
        ]
        kept, removed = canonical.filter_settings_for_correction_removals(
            settings, exact_removals, set(),
        )
        self.assertEqual(removed, 1)
        self.assertEqual([row[0] for row in kept], ["si/n", "kacumi"])
        kept, removed = canonical.filter_settings_for_correction_removals(
            settings, set(), {"sin"},
        )
        self.assertEqual(removed, 2)
        self.assertEqual([row[0] for row in kept], ["kacumi"])

    def test_exact_only_removal_preserves_productive_sibling_actions(self):
        settings = [
            ["teren", 54000, ["o", "oj", "on", "a", "e", "en"]],
            ["sample", 64000, ["ne", "o", "word_boundary"]],
            ["atomic", 64000, [
                "ne", "atomic_no_split", "boundary_noop_guard",
                "word_boundary",
            ]],
        ]
        kept, removed = canonical.filter_settings_for_correction_removals(
            settings,
            set(),
            set(),
            {"teren", "sample", "atomic"},
            set(),
        )
        self.assertEqual(removed, 2)
        self.assertEqual(kept, [
            ["teren", 54000, ["o", "oj", "on", "a", "e", "en"]],
            ["sample", 64000, ["o", "word_boundary"]],
        ])
        # A productive correction owns the full identity and therefore wins
        # when the same identity is also present in the exact-only set.
        kept, removed = canonical.filter_settings_for_correction_removals(
            [["teren", 54000, ["o", "oj"]]],
            {"teren"},
            set(),
            {"teren"},
            set(),
        )
        self.assertEqual((kept, removed), ([], 1))
        # A case-sensitive exact proper name must not erase its lowercase
        # grammatical/lexical homograph.
        kept, removed = canonical.filter_settings_for_correction_removals(
            [["Aŭdu", 44000, ["ne"]], ["aŭdu", 44000, ["ne"]]],
            set(),
            set(),
            {"Aŭdu"},
            set(),
        )
        self.assertEqual((kept, removed), ([['aŭdu', 44000, ['ne']]], 1))

    def test_postregen_respects_all_authoritative_exact_surfaces(self):
        self.assertTrue(postregen.is_authoritative_exact_surface("anestezi"))
        self.assertTrue(postregen.is_authoritative_exact_surface("ANESTEZI"))
        self.assertTrue(postregen.is_authoritative_exact_surface("Aŭdun"))
        self.assertFalse(postregen.is_authoritative_exact_surface("aŭdun"))
        formatter = lambda piece, gloss: f"<{piece}:{gloss}>"
        self.assertIsNone(
            postregen.rewrite_surface_core("anestezi", "JA", formatter)
        )
        self.assertEqual(
            postregen.rewrite_surface_core("anestezio", "JA", formatter),
            "<an:無><estez:感覚>io",
        )

    def test_typed_ruby_annotation_prefers_context_then_exact_plain(self):
        annotations = {
            "kaj": [["kaj", "and"]],
            "@typed:kajo:0": [["kaj", "wharf"]],
            "ChatGPT": [["ChatGPT", "AI"]],
            "aŭdu": [["aŭdu", "hear"]],
        }
        self.assertEqual(
            canonical.lookup_typed_ruby_annotation(
                annotations, "kajo", 0, "kaj",
            ),
            [["kaj", "wharf"]],
        )
        self.assertEqual(
            canonical.lookup_typed_ruby_annotation(
                annotations, "ChatGPT-on", 0, "ChatGPT",
            ),
            [["ChatGPT", "AI"]],
        )
        self.assertIsNone(
            canonical.lookup_typed_ruby_annotation(
                annotations, "Aŭdu", 0, "Aŭdu",
            )
        )
        with self.assertRaisesRegex(ValueError, "invalid exact word annotation"):
            canonical.lookup_typed_ruby_annotation(
                {"piece": [["pi", "one"], ["ece", "two"]]},
                "piece", 0, "piece",
            )
        with self.assertRaisesRegex(ValueError, "invalid typed context annotation"):
            canonical.lookup_typed_ruby_annotation(
                {
                    "piece": [["piece", "plain"]],
                    "@typed:surface:0": [["wrong", "context"]],
                },
                "surface", 0, "piece",
            )

    def test_casefold_fallback_index_rejects_ambiguous_homographs(self):
        ambiguous = set()
        index = canonical.build_unique_casefold_index({
            "sekretari": [["sekretari", "secretary"]],
            "same": [["same", "one"]],
            "SAME": [["same", "one"]],
            "Tang": [["Tang", "dynasty"]],
            "tang": [["tang", "pitch"]],
        }, ambiguous)
        self.assertEqual(index["sekretari"], [["sekretari", "secretary"]])
        self.assertIn("same", index)
        self.assertNotIn("tang", index)
        self.assertEqual(ambiguous, {"tang"})
        with self.assertRaises(canonical.AmbiguousCasefoldError):
            canonical.lookup_unique_casefold(
                index, ambiguous, "TANG", "test dictionary",
            )
        self.assertTrue(
            canonical.explicit_piece_allows_casefold_fallback("Sekretari"),
        )
        self.assertFalse(
            canonical.explicit_piece_allows_casefold_fallback("ttt"),
        )
        self.assertFalse(
            canonical.explicit_piece_allows_casefold_fallback("uk"),
        )

    def test_elided_article_meaning_is_optional_for_kanji_only_data(self):
        self.assertEqual(
            canonical.resolve_elided_article_meaning(
                {"la": [["la", "article"]]}, {"la": [["la", "article"]]}, {},
            ),
            "article",
        )
        self.assertEqual(
            canonical.resolve_elided_article_meaning({}, {}, {"la": "article"}),
            "article",
        )
        self.assertIsNone(
            canonical.resolve_elided_article_meaning({}, {}, {}),
        )

    def test_atomic_json_replacement_truncates_longer_previous_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "deployed.json"
            path.write_text(json.dumps({"old": "x" * 10000}), encoding="utf-8")
            expected = {"new": ["短い", 1]}
            atomic_json_dump(path, expected)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), expected)
            self.assertFalse(path.with_name(path.name + ".tmp_atomic_write").exists())

    def test_atomic_file_copy_replaces_destination_completely(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.json"
            destination = Path(directory) / "destination.json"
            source.write_bytes(b'{"valid":true}')
            destination.write_bytes(b"x" * 10000)
            atomic_file_copy(source, destination)
            self.assertEqual(destination.read_bytes(), source.read_bytes())
            self.assertFalse(destination.with_name(destination.name + ".tmp_atomic_copy").exists())

    def test_atomic_file_copy_rejects_corrupt_source_and_preserves_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "corrupt.json"
            destination = Path(directory) / "live.json"
            source.write_bytes(b"\x00" * 1024)
            original = b'{"preserved":true}'
            destination.write_bytes(original)
            with self.assertRaises((json.JSONDecodeError, UnicodeDecodeError)):
                atomic_file_copy(source, destination)
            self.assertEqual(destination.read_bytes(), original)
            self.assertFalse(destination.with_name(destination.name + ".tmp_atomic_copy").exists())

    def test_atomic_binary_copy_rejects_empty_source(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "empty.csv"
            destination = Path(directory) / "live.csv"
            source.write_bytes(b"")
            destination.write_bytes(b"preserved")
            with self.assertRaises(ValueError):
                atomic_binary_copy(source, destination)
            self.assertEqual(destination.read_bytes(), b"preserved")

    def test_multilingual_word_anno_boundary_scope_is_fail_closed(self):
        manifest = json.loads(
            (HERE / "_word_anno_boundary_scope_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        maps = {
            language: json.loads(
                (HERE / "out" / f"word_anno_{language}.json").read_text(
                    encoding="utf-8"
                )
            )
            for language in manifest["languages"]
        }
        authority = canonical.validate_multilingual_word_anno_boundaries(
            maps, manifest,
        )
        self.assertEqual(len(authority), manifest["authority_keys"])
        self.assertEqual(authority["@typed:hokkajdon:0"], ("hokkajdo",))
        self.assertIn("pat", authority)
        self.assertNotIn("pat", maps["ja"])

        # Glosses are deliberately language-local and are not copied or
        # hashed; changing one translation cannot change the boundary scope.
        localized = dict(maps["ja"])
        localized["@typed:hokkajdon:0"] = [["hokkajdo", "別の日本語訳"]]
        gloss_variant = dict(maps)
        gloss_variant["ja"] = localized
        canonical.validate_multilingual_word_anno_boundaries(
            gloss_variant, manifest,
        )

        conflicting = dict(maps["zh"])
        conflicting["@typed:hokkajdon:0"] = [["hokkajd", "北海道"]]
        boundary_variant = dict(maps)
        boundary_variant["zh"] = conflicting
        with self.assertRaisesRegex(ValueError, "boundary conflict"):
            canonical.validate_multilingual_word_anno_boundaries(
                boundary_variant, manifest,
            )

        missing = dict(maps["ko"])
        del missing["@typed:hokkajdon:0"]
        key_variant = dict(maps)
        key_variant["ko"] = missing
        with self.assertRaisesRegex(ValueError, "key count drift"):
            canonical.validate_multilingual_word_anno_boundaries(
                key_variant, manifest,
            )

    def test_reviewed_local_exact_scope_preserves_unreviewed_local_semantics(self):
        review = json.loads(
            (HERE / "localized_global_exact_reviewed.json").read_text(
                encoding="utf-8"
            )
        )
        reviewed_forms = {
            form
            for row in review["targets"]
            for form in (
                row["root"], row["root"].capitalize(), row["root"].upper(),
            )
        }
        self.assertEqual(len(reviewed_forms), 36)
        glosses = {
            "JA": "[地名]北海道",
            "ZH": "[地名]北海道",
            "KO": "[지명]홋카이도",
        }
        format_type = "HTML格式_Ruby文字_大小调整"
        for language in ("JA", "ZH", "KO"):
            app_dir = ROOT / f"Esperanto-Kanji-Ruby-{language}"
            module = _runtime_module(app_dir, f"reviewed_local_{language}")
            helper = canonical.load_app_replacement_helper(app_dir)
            char_widths = json.loads(
                (app_dir / "app_data" / "char_widths.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                module._LOCALIZED_GLOBAL_EXACT_REVIEWED,
                reviewed_forms,
                language,
            )
            hokkaido = helper.output_format(
                "hokkajdo", glosses[language], format_type, char_widths,
            ) + "n"
            local_rules = [
                ["hok", "<ruby>hok<rt class=\"S_S\">LOCAL-HOK</rt></ruby>", "@HOK@"],
                ["kaj", "<ruby>kaj<rt class=\"S_S\">LOCAL-KAJ</rt></ruby>", "@KAJ@"],
                ["don", "<ruby>don<rt class=\"S_S\">LOCAL-DON</rt></ruby>", "@DON@"],
                ["re", "<ruby>re<rt class=\"S_S\">LOCAL-RE</rt></ruby>", "@RE@"],
                ["sum", "<ruby>sum<rt class=\"S_S\">LOCAL-SUM</rt></ruby>", "@SUM@"],
                ["i", "i", "@I@"],
            ]
            global_rules = [
                [" hokkajdon ", f" {hokkaido} ", " $HOKKAIDO$ "],
                ["kaj", "GLOBAL-KAJ", "$GLOBAL-KAJ$"],
                ["resumi", "GLOBAL-RESUM-I", "$GLOBAL-RESUM-I$"],
            ]
            rows = module.create_replacements_list_for_localized_replacement(
                "@hokkajdon@ @kaj@ @resumi@",
                ["@L0@", "@L1@", "@L2@"],
                local_rules,
                global_rules,
            )
            rendered = {row[0]: row[2] for row in rows}
            self.assertEqual(rendered["@hokkajdon@"], hokkaido, language)
            self.assertIn(glosses[language], rendered["@hokkajdon@"])
            self.assertEqual(
                rendered["@kaj@"], module.safe_replace("kaj", local_rules),
                language,
            )
            self.assertIn("LOCAL-KAJ", rendered["@kaj@"])
            self.assertNotIn("GLOBAL-KAJ", rendered["@kaj@"])
            self.assertEqual(
                rendered["@resumi@"], module.safe_replace("resumi", local_rules),
                language,
            )
            self.assertNotIn("GLOBAL-RESUM-I", rendered["@resumi@"])
            with self.assertRaisesRegex(ValueError, "lacks an exact global rule"):
                module.create_replacements_list_for_localized_replacement(
                    "@ddt@", ["@MISSING@"], local_rules, global_rules,
                )

    def test_kanji_resync_rejects_piece_count_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            master = Path(directory)
            (master / "_kanji_map_master.tsv").write_text(
                "id\troot\t根\n", encoding="utf-8",
            )
            (master / "_identifier_sidecar.tsv").write_text("", encoding="utf-8")
            (master / "漢字注入_学習者版_20260620.txt").write_text(
                "bad/a⟦坏⟧\n", encoding="utf-8",
            )
            environment = dict(os.environ)
            environment["ESP_KANJI_MASTER_PATH"] = str(master)
            # This fixture deliberately supplies a tiny synthetic authority so
            # it can reach the piece-count guard.  Formal regeneration exports
            # pins for the real master; do not let those unrelated parent pins
            # make the subprocess fail earlier on fixture identity.
            for pin_name in (
                "ESP_EXPECTED_KANJI_MASTER_MANIFEST",
                "ESP_EXPECTED_KANJI_MASTER_SHA256",
            ):
                environment.pop(pin_name, None)
            result = subprocess.run(
                [sys.executable, str(HERE / "resync_kanji_master.py")],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Kanji master resync aborted: 1", result.stderr)

    def test_formal_regeneration_uses_snapshot_full_master_audit(self):
        pipeline = (HERE / "regenerate_all.py").read_text(encoding="utf-8")
        fast = (HERE / "audit_master_3lang_fast.py").read_text(encoding="utf-8")
        self.assertIn("audit_master_3lang_full_snapshot.py", pipeline)
        self.assertNotIn("'audit_master_3lang_fast.py'", pipeline)
        self.assertIn("--expected-gold-sha256", pipeline)
        self.assertIn("--expected-head", pipeline)
        self.assertIn("--monitor-only", fast)
        self.assertIn("if mism:", fast)

    def test_case_sensitive_bounded_phrase_runtime_padding(self):
        module = _runtime_module(ROOT / "Esperanto-Kanji-Ruby-JA", "phrase_padding")
        latin_ruby = '<ruby>Global Voices<rt class="S_S">entity</rt></ruby>'
        mixed_ruby = '<ruby>Abc Жук<rt class="S_S">person</rt></ruby>'
        apostrophe_ruby = '<ruby>L\'Espérantiste<rt class="S_S">magazine</rt></ruby>'
        rules = [
            (" Global Voices ", " " + latin_ruby + " ", " @PHRASE_LATIN@ "),
            (" Abc Жук ", " " + mixed_ruby + " ", " @PHRASE_MIXED@ "),
            (" L'Espérantiste ", " " + apostrophe_ruby + " ", " @PHRASE_APOS@ "),
        ]
        rendered = module.orchestrate_comprehensive_esperanto_text_replacement(
            "Global Voices, Global voices; XGlobal VoicesY. Abc Жук! L'Espérantiste,",
            [], [], [], rules, [], "HTML格式_Ruby文字_大小调整",
        )
        self.assertEqual(rendered.count(latin_ruby), 1)
        self.assertEqual(rendered.count(mixed_ruby), 1)
        self.assertEqual(rendered.count(apostrophe_ruby), 1)
        self.assertIn("Global voices", rendered)
        self.assertIn("XGlobal VoicesY", rendered)
        self.assertIn(latin_ruby + ",", rendered)
        self.assertIn(mixed_ruby + "!", rendered)
        self.assertIn(apostrophe_ruby + ",", rendered)

    def test_curly_apostrophe_runtime_matches_ascii_elision_without_leaking(self):
        article = '<ruby>l’<rt class="S_S">article</rt></ruby>'
        god = '<ruby>Di<rt class="S_S">god</rt></ruby>o'
        rules = [
            (" Dio", " " + god, " $DIO$"),
            (" l’", " " + article, " $ARTICLE$"),
        ]
        for language in ("JA", "ZH", "KO"):
            module = _runtime_module(
                ROOT / f"Esperanto-Kanji-Ruby-{language}",
                f"curly_apostrophe_{language}",
            )
            rendered = module.orchestrate_comprehensive_esperanto_text_replacement(
                "l’Dio xl’Dio",
                [], [], [], rules, [],
                "HTML格式_Ruby文字_大小调整",
            )
            self.assertEqual(
                rendered,
                article + god + " xl’" + god,
                language,
            )
            self.assertNotIn("$ARTICLE$", rendered)
            self.assertNotIn("$DIO$", rendered)

    def test_dictionary_sentence_punctuation_policy(self):
        self.assertEqual(
            canonical.split_trailing_sentence_punctuation("pat!", "frying pan!"),
            ("pat", "frying pan", "!"),
        )
        self.assertEqual(
            canonical.split_trailing_sentence_punctuation("ĉu?!", "question?!"),
            ("ĉu", "question", "?!"),
        )
        self.assertEqual(
            canonical.split_trailing_sentence_punctuation("dank'", "thanks"),
            ("dank", "thanks", "'"),
        )
        self.assertEqual(
            canonical.split_trailing_sentence_punctuation("l’", "article"),
            ("l’", "article", ""),
        )
        # Abbreviation dots are an explicit guide exception and stay atomic.
        self.assertEqual(
            canonical.split_trailing_sentence_punctuation("ekz.", "example."),
            ("ekz.", "example.", ""),
        )

    def test_annotated_multiword_entity_keeps_final_apostrophe(self):
        for apostrophe in ("'", "’"):
            root = "La Ŝodfon" + apostrophe
            meaning = "place" + apostrophe
            self.assertEqual(
                canonical.split_annotated_piece_punctuation(root, meaning),
                (root, meaning, ""),
            )
        self.assertEqual(
            canonical.split_annotated_piece_punctuation("dank'", "thanks"),
            ("dank", "thanks", "'"),
        )

    def test_an_inflections_are_data_driven_and_collision_safe(self):
        word_anno = {
            "ter/an": [["ter", "land"], ["an", "member"]],
            "bon/lingv/an": [["bon", "good"], ["lingv", "language"], ["an", "member"]],
            "seul/an": [["seul", "Seoul"], ["an", "member"]],
            "sud/an": [["sud", "south"], ["an", "member"]],
            # Atomic country root + its derivative: skip the whole ambiguous
            # sud/an paradigm, including capitalized variants such as Sudano.
            "sudan": [["sudan", "Sudan"]],
            "sudan/an": [["sudan", "Sudan"], ["an", "member"]],
            "sud-sud/an": [["sud", "south"], ["sudan", "Sudan"]],
            # The final component happens to spell atomic rikan, but the
            # pre-an base porto-rik is itself an atomic source, so this is a
            # legitimate derivative and must not be suppressed.
            "rikan": [["rikan", "sneering"]],
            "porto-rik": [["porto-rik", "Puerto Rico"]],
            "porto-rik/an": [["porto-rik", "Puerto Rico"], ["an", "member"]],
        }
        rules = set(canonical.iter_word_anno_an_inflections(word_anno))
        self.assertIn(("teranoj", "ter/an", "oj"), rules)
        self.assertIn(("bonlingvanojn", "bon/lingv/an", "ojn"), rules)
        self.assertIn(("seulanoj", "seul/an", "oj"), rules)
        self.assertFalse(any(stem_key == "sud/an" for _, stem_key, _ in rules))
        self.assertFalse(any(stem_key == "sud-sud/an" for _, stem_key, _ in rules))
        self.assertIn(("porto-rikanoj", "porto-rik/an", "oj"), rules)

    def test_later_exact_rule_cannot_unbound_generated_an_inflection(self):
        generated = [" generated-ter/an/oj ", 85000]
        later_custom = ["custom-ter/an/oj", 74000]
        replacements = {
            " teranoj ": generated,
            # Mirrors the legacy ter/an/oj + ``ne`` setting which is processed
            # after the word_anno-derived bounded paradigm.
            "teranoj": later_custom,
        }
        canonical.enforce_boundary_only_surfaces(replacements, {"teranoj"})
        self.assertNotIn("teranoj", replacements)
        self.assertEqual(replacements[" teranoj "], [" custom-ter/an/oj ", 74000])

    def test_onin_uses_confirmed_pipeline(self):
        confirmed = json.loads((HERE / "out" / "confirmed_tier30.json").read_text(encoding="utf-8"))
        confirmed_words = [entry.get("w") for entry in confirmed]
        def _track(entry):
            if entry.get("kanji_track_only"):
                return "kanji"
            if entry.get("ruby_track_only") or entry.get("ruby_only"):
                return "ruby"
            return "shared"
        for label, key in (
            ("surface", lambda entry: entry["w"]),
            ("slashless target", lambda entry: entry["target"].replace("/", "")),
        ):
            groups = {}
            for entry in confirmed:
                groups.setdefault(key(entry), []).append(entry)
            invalid = {
                value: rows for value, rows in groups.items()
                if len(rows) > 1
                and {_track(row) for row in rows} != {"ruby", "kanji"}
            }
            self.assertEqual(invalid, {}, f"unsafe duplicate confirmed {label}")
        for entry in confirmed:
            self.assertEqual(
                canonical.normalize_esperanto_surface_notation(entry["w"]),
                canonical.normalize_esperanto_surface_notation(entry["target"].replace("/", "")),
                f"confirmed surface changed by decomposition: {entry}",
            )
        matches = [entry for entry in confirmed if entry.get("w") == "onin"]
        self.assertEqual(matches, [{"w": "onin", "target": "oni/n", "boundary_only": True}])
        novjorko = [entry for entry in confirmed if entry.get("w") == "novjorko"]
        self.assertEqual(novjorko, [{
            "w": "novjorko", "target": "novjork/o",
            "corpus_managed": True,
        }])
        self.assertEqual(
            [entry for entry in confirmed if entry.get("w") in {
                "novjork", "Bonaer", "BONAER",
            }],
            [
                {
                    "w": "Bonaer", "target": "Bonaer",
                    "exact_only": True, "ruby_left_boundary": True,
                    "case_sensitive": True, "corpus_managed": True,
                    "ruby_context_annotation": "@atomic-family:Bonaer",
                },
                {
                    "w": "BONAER", "target": "BONAER",
                    "exact_only": True, "ruby_left_boundary": True,
                    "case_sensitive": True, "corpus_managed": True,
                    "ruby_context_annotation": "@atomic-family:BONAER",
                },
                {
                    "w": "novjork", "target": "novjork",
                    "exact_only": True, "ruby_left_boundary": True,
                    "case_sensitive": False, "corpus_managed": True,
                },
            ],
        )
        self.assertIn({
            "w": "bonaer", "target": "bon/aer", "exact_only": True,
            "allow_substring": True, "corpus_managed": True,
            "localized_compositional": True,
        }, confirmed)
        self.assertIn({
            "w": "novjorka", "target": "novjork/a",
            "corpus_managed": True,
        }, confirmed)
        self.assertIn({
            "w": "novjorkano", "target": "novjork/an/o",
            "corpus_managed": True, "ruby_track_only": True,
        }, confirmed)
        self.assertIn({
            "w": "promilo", "target": "promil/o", "typed_roles": "RL",
            "exact_only": True, "boundary_only": True,
            "case_sensitive": True, "corpus_managed": True,
            "fake_coarse_5e_transition_managed": True,
            "ruby_only": True,
        }, confirmed)
        self.assertIn({
            "w": "promilo", "target": "pro/mil/o",
            "kanji_track_only": True, "corpus_managed": True,
            "fake_coarse_5e_transition_managed": True,
        }, confirmed)
        self.assertFalse(
            any(entry.get("w") == "novjorkon" for entry in confirmed),
            "productive novjork/o must replace the legacy nov/jork/on pin",
        )
        meritokrati = [entry for entry in confirmed if entry.get("w") == "meritokrati"]
        self.assertEqual(meritokrati, [{
            "w": "meritokrati", "target": "merit/o/krati",
            "corpus_managed": True,
        }])
        anon = [entry for entry in confirmed if entry.get("w") == "anon"]
        self.assertEqual(anon, [{"w": "anon", "target": "an/on", "boundary_with_noop_guard": True}])
        exact_gold = {
            entry["w"]: entry for entry in confirmed
            if entry.get("w") in {"argentano", "butanono", "domeno", "konstantano"}
        }
        self.assertEqual(
            exact_gold,
            {
                "argentano": {"w": "argentano", "target": "argentan/o", "exact_only": True, "boundary_only": True},
                "butanono": {"w": "butanono", "target": "butanon/o", "exact_only": True, "boundary_only": True},
                "domeno": {"w": "domeno", "target": "domen/o", "exact_only": True, "boundary_only": True},
                "konstantano": {"w": "konstantano", "target": "konstantan/o", "exact_only": True, "boundary_only": True},
            },
        )
        ursulanina = [entry for entry in confirmed if entry.get("w") == "ursulanina"]
        self.assertEqual(ursulanina, [{"w": "ursulanina", "target": "ursul/an/in/a"}])
        general_roots = {
            entry["w"]: entry for entry in confirmed
            if entry.get("w") in {
                "koninda", "biologio", "fiziologio", "aroganta",
                "mezazio", "kriptografio", "svislando", "sovetunio",
                "aparteni", "italujo", "katmando", "nurnbergo", "burno",
                "kievo", "mukdeno", "mezoriento", "kamakuro", "enoŝimo",
                "tuskolo", "taragono", "ĝirono", "smolenko", "kaŭno",
                "bikini-atolo", "buenos-aireso", "kievon", "kamakuron",
                "enoŝimon", "moravio", "golfoflu", "afero", "meti",
                "etoso", "amaso", "radono",
            }
        }
        self.assertEqual(
            general_roots,
            {
                "koninda": {"w": "koninda", "target": "kon/ind/a"},
                "biologio": {"w": "biologio", "target": "biologi/o"},
                "fiziologio": {"w": "fiziologio", "target": "fiziologi/o"},
                "aroganta": {"w": "aroganta", "target": "arogant/a"},
                "mezazio": {"w": "mezazio", "target": "mez/azi/o"},
                "kriptografio": {"w": "kriptografio", "target": "kriptografi/o"},
                "svislando": {"w": "svislando", "target": "svis/land/o"},
                "sovetunio": {"w": "sovetunio", "target": "sovet/uni/o"},
                "aparteni": {"w": "aparteni", "target": "aparten/i"},
                "italujo": {"w": "italujo", "target": "ital/uj/o"},
                "katmando": {"w": "katmando", "target": "katmand/o"},
                "nurnbergo": {"w": "nurnbergo", "target": "nurnberg/o"},
                "burno": {"w": "burno", "target": "burn/o"},
                "kievo": {"w": "kievo", "target": "kiev/o"},
                "mukdeno": {"w": "mukdeno", "target": "mukden/o"},
                "mezoriento": {"w": "mezoriento", "target": "mez/orient/o"},
                "kamakuro": {"w": "kamakuro", "target": "kamakur/o"},
                "enoŝimo": {"w": "enoŝimo", "target": "enoŝim/o"},
                "tuskolo": {"w": "tuskolo", "target": "tuskol/o"},
                "taragono": {"w": "taragono", "target": "taragon/o"},
                "ĝirono": {"w": "ĝirono", "target": "ĝiron/o"},
                "smolenko": {"w": "smolenko", "target": "smolenk/o"},
                "kaŭno": {"w": "kaŭno", "target": "kaŭn/o"},
                "bikini-atolo": {"w": "bikini-atolo", "target": "bikini/-/atol/o"},
                "buenos-aireso": {"w": "buenos-aireso", "target": "buenos-aires/o"},
                "kievon": {"w": "kievon", "target": "kiev/o/n"},
                "kamakuron": {"w": "kamakuron", "target": "kamakur/o/n"},
                "enoŝimon": {"w": "enoŝimon", "target": "enoŝim/o/n"},
                "moravio": {"w": "moravio", "target": "moravi/o"},
                "golfoflu": {"w": "golfoflu", "target": "golf/o/flu"},
                "afero": {"w": "afero", "target": "afer/o"},
                "meti": {"w": "meti", "target": "met/i"},
                "etoso": {"w": "etoso", "target": "etos/o"},
                "amaso": {"w": "amaso", "target": "amas/o"},
                "radono": {"w": "radono", "target": "radon/o"},
            },
        )
        mixed_case = [entry for entry in confirmed if entry.get("w") == "RenKEJtiĝon"]
        self.assertEqual(mixed_case, [{
            "w": "RenKEJtiĝon", "target": "RenKEJtiĝo/n",
            "exact_only": True, "boundary_only": True, "corpus_managed": True,
        }])
        corpus_entries = [entry for entry in confirmed if entry.get("corpus_managed")]
        self.assertFalse(
            corpus_data.MANAGED_REMOVED_SURFACES & set(confirmed_words),
            "obsolete managed surfaces must not retain a competing pin",
        )
        self.assertEqual(
            len(corpus_entries),
            len(corpus_data.MANAGED_EXACT_TARGETS)
            + len(corpus_data.PRODUCTIVE_RUBY_LEFT_TARGETS)
            + len(corpus_data.COMPOSITIONAL_FAMILY_TARGETS)
            + len(corpus_data.KANJI_TRACK_PRODUCTIVE_TARGETS)
            + len(corpus_data.MANAGED_MORPH_TARGETS)
            + len(corpus_data.MANAGED_TYPED_EXACT_TARGETS)
            + len(corpus_data.REVIEWED_TYPED_EXACT_TARGETS),
        )
        for word, (target, case_sensitive) in corpus_data.MANAGED_EXACT_TARGETS.items():
            expected = {
                "w": word, "target": target, "exact_only": True,
                "boundary_only": True, "corpus_managed": True,
            }
            if case_sensitive:
                expected["case_sensitive"] = True
            self.assertIn(expected, corpus_entries)
        for word, spec in corpus_data.MANAGED_MORPH_TARGETS.items():
            expected = {
                "w": word, "target": spec["target"], "corpus_managed": True,
            }
            if spec.get("case_sensitive"):
                expected["case_sensitive"] = True
            if spec.get("context_annotation"):
                expected["context_annotation"] = spec["context_annotation"]
            if spec.get("ruby_context_annotation"):
                expected["ruby_context_annotation"] = spec[
                    "ruby_context_annotation"
                ]
            if spec.get("ruby_track_only"):
                expected["ruby_track_only"] = True
            self.assertIn(expected, corpus_entries)
        for word, spec in corpus_data.MANAGED_TYPED_EXACT_TARGETS.items():
            expected = {
                "w": word,
                "target": spec["target"],
                "typed_roles": spec["typed_roles"],
                "exact_only": True,
                "boundary_only": True,
                "case_sensitive": bool(spec.get("case_sensitive", True)),
                "corpus_managed": True,
            }
            if word in corpus_data.FAKE_COARSE_TYPED_SURFACES:
                expected["fake_coarse_transition_managed"] = True
            if word in corpus_data.FAKE_COARSE_FF33_TYPED_SURFACES:
                expected["fake_coarse_ff33_transition_managed"] = True
            if word in corpus_data.FAKE_COARSE_5E_TYPED_SURFACES:
                expected["fake_coarse_5e_transition_managed"] = True
            if spec.get("ruby_only"):
                expected["ruby_only"] = True
            self.assertIn(expected, corpus_entries)
        for word, spec in corpus_data.KANJI_TRACK_PRODUCTIVE_TARGETS.items():
            self.assertIn({
                "w": word,
                "target": spec["target"],
                "kanji_track_only": True,
                "corpus_managed": True,
                "fake_coarse_5e_transition_managed": True,
            }, corpus_entries)
        for word, spec in corpus_data.PRODUCTIVE_RUBY_LEFT_TARGETS.items():
            expected = {
                "w": word, "target": spec["target"],
                "exact_only": True, "ruby_left_boundary": True,
                "case_sensitive": spec["case_sensitive"],
                "corpus_managed": True,
            }
            if spec.get("ruby_context_annotation"):
                expected["ruby_context_annotation"] = spec[
                    "ruby_context_annotation"
                ]
            if spec.get("ruby_track_only"):
                expected["ruby_track_only"] = True
            self.assertIn(expected, corpus_entries)
        for word, spec in corpus_data.COMPOSITIONAL_FAMILY_TARGETS.items():
            self.assertIn({
                "w": word, "target": spec["target"],
                "exact_only": True, "allow_substring": True,
                "corpus_managed": True,
                "localized_compositional": True,
            }, corpus_entries)
        for word, spec in corpus_data.REVIEWED_TYPED_EXACT_TARGETS.items():
            self.assertIn({
                "w": word,
                "target": spec["target"],
                "typed_roles": spec["typed_roles"],
                "exact_only": True,
                "boundary_only": True,
                "case_sensitive": True,
                "corpus_managed": True,
                "reviewed_residual": True,
            }, corpus_entries)

    def test_no_worsening_guard_manifest_is_exact_and_bounded(self):
        guards = json.loads((HERE / "no_worsening_guards.json").read_text(encoding="utf-8"))
        self.assertEqual(len(guards), 87)
        words = [entry["w"] for entry in guards]
        self.assertEqual(len(words), len(set(words)))
        self.assertIn({
            "w": "kacumi",
            "target": "kac/um/i",
            "exact_only": True,
            "boundary_only": True,
            "no_worsening_guard": True,
        }, guards)
        for entry in guards:
            self.assertTrue(entry.get("exact_only"), entry)
            self.assertTrue(entry.get("boundary_only"), entry)
            self.assertTrue(entry.get("no_worsening_guard"), entry)
            self.assertEqual(
                canonical.normalize_esperanto_surface_notation(entry["w"]),
                canonical.normalize_esperanto_surface_notation(
                    entry["target"].replace("/", "")
                ),
                entry,
            )

    def test_strict_gold_fix_manifest_is_pinned_typed_and_bounded(self):
        payload = json.loads(
            (HERE / "_strict_gold_reference_fixes.json").read_text(
                encoding="utf-8",
            )
        )
        scope = json.loads(
            (HERE / "_no_worsening_scope_manifest.json").read_text(
                encoding="utf-8",
            )
        )["expected"]
        entries = payload["entries"]
        compact = json.dumps(
            entries, ensure_ascii=False, separators=(",", ":"),
        ).encode("utf-8")
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["reference_schema_version"], 5)
        self.assertEqual(len(entries), payload["expected_entries"])
        self.assertEqual(len(entries), 914)
        self.assertEqual(
            hashlib.sha256(compact).hexdigest().upper(),
            payload["entries_sha256"],
        )
        self.assertEqual(payload["gold_sha256"], scope["gold"]["sha256"])
        self.assertEqual(payload["reference_sha256"], scope["reference_sha256"])
        self.assertEqual(len({entry["w"] for entry in entries}), len(entries))
        newly_adjudicated = {
            "Argolando": ("Arg/o/land/o", "RLRL"),
            "Eolia": ("Eol/ia", "RL"),
            "Eoliano": ("Eol/i/an/o", "RLRL"),
            "Eolio": ("Eol/io", "RL"),
            "Frigio": ("Frig/io", "RL"),
            "Ligurio": ("Ligur/io", "RL"),
            "Ohiorivero": ("Ohi/o/river/o", "RLRL"),
            "Retio": ("Ret/io", "RL"),
            "Umbrio": ("Umbr/io", "RL"),
            "psikokirurgio": ("psik/o/kirurg/io", "RLRL"),
            "tienvojaĝo": ("tie/n/vojaĝ/o", "RLRL"),
        }
        by_surface = {entry["w"]: entry for entry in entries}
        for surface, (target, roles) in newly_adjudicated.items():
            self.assertEqual(by_surface[surface]["target"], target)
            self.assertEqual(by_surface[surface]["typed_roles"], roles)
            self.assertIs(by_surface[surface].get("ruby_track_only"), True)
        for entry in entries:
            parts = [part for part in entry["target"].split("/") if part]
            self.assertTrue(entry["exact_only"], entry)
            self.assertTrue(entry["boundary_only"], entry)
            self.assertEqual(len(entry["typed_roles"]), len(parts), entry)
            self.assertEqual(
                entry.get("case_sensitive"),
                True,
                entry,
            )
            self.assertEqual("".join(parts), entry["w"], entry)

    def test_corpus_atomic_annotations_are_mirrored(self):
        for code, language in (("ja", "JA"), ("zh", "ZH"), ("ko", "KO")):
            out_data = json.loads((HERE / "out" / f"word_anno_{code}.json").read_text(encoding="utf-8"))
            app_data = json.loads((ROOT / f"Esperanto-Kanji-Ruby-{language}" / "app_data" / "word_anno.json").read_text(encoding="utf-8"))
            self.assertEqual(out_data, app_data)
            for legacy in (
                "bon/aer", "bonaer", "Bonaer", "BONAER",
                "nov/jork", "nov/jork/an",
            ):
                self.assertNotIn(legacy, out_data)
            for surface in ("bonaer", "Bonaer", "BONAER"):
                context_key = f"@atomic-family:{surface}"
                self.assertEqual(
                    out_data[context_key],
                    [[surface, corpus_data.ANNOTATIONS[code][surface]]],
                )
            for root in corpus_data.ANNOTATIONS[code]:
                if root in corpus_data.ATOMIC_FAMILY_CONTEXT_KEYS:
                    continue
                self.assertEqual(out_data[root][0][0], root)
            for key, pairs in corpus_data.SPLIT_CONTEXT_ANNOTATIONS[code].items():
                self.assertEqual(out_data[key], pairs)
            for (surface, index, piece), glosses in corpus_data.TYPED_CONTEXT_GLOSSES.items():
                self.assertEqual(
                    out_data[f"@typed:{surface}:{index}"],
                    [[piece, glosses[code]]],
                )
            for key, row in corpus_data.REVIEWED_TYPED_ANNOTATIONS.items():
                self.assertEqual(
                    out_data[key], [[row["piece"], row["glosses"][code]]],
                )
            for root, source in corpus_data.MIRRORED_ATOMIC_ROOTS.items():
                self.assertEqual(out_data[root], [[root, out_data[source][0][1]]])

    def test_explicit_setting_piece_position_policy(self):
        # Internal linking/inflection letters stay bare.
        for piece in ("o", "a", "e", "i", "n", "j", "jn"):
            self.assertTrue(canonical.setting_piece_is_bare(piece, 1, 3))
        # Country-name io/ia endings and their inflections stay literal only
        # after an explicit preceding root.  A one-piece ion/iaj is lexical,
        # and io at position zero of io/n is a correlative root.
        for piece in ("io", "ia", "ion", "ian", "ioj", "iojn", "iaj", "iajn"):
            self.assertTrue(canonical.setting_piece_is_bare(piece, 1, 3))
            self.assertTrue(canonical.setting_piece_is_bare(piece, 2, 3))
            self.assertFalse(canonical.setting_piece_is_bare(piece, 0, 1))
        self.assertTrue(canonical.setting_piece_is_bare("IO", 1, 3))
        self.assertTrue(canonical.setting_piece_is_bare("O", 2, 3))
        self.assertFalse(canonical.setting_piece_is_bare("IO", 0, 1))
        # Finite verb endings are independent ruby annotations; only i/u are
        # bare terminal verb endings.
        for piece in ("as", "is", "os", "us"):
            self.assertFalse(canonical.setting_piece_is_bare(piece, 2, 3))
        for piece in ("i", "u"):
            self.assertTrue(canonical.setting_piece_is_bare(piece, 2, 3))
        # Exact corpus phrases may expose quotation marks or hyphens as
        # explicit literal pieces around an atomic ruby base.
        for piece in ("-", "'", "’", '"', "(", ")", "."):
            self.assertTrue(canonical.setting_piece_is_bare(piece, 1, 3))
        # Ambiguous lexical affixes are rendered atomically when internal,
        # while the same spelling is a bare inflection at word end.
        for piece in ("an", "on"):
            self.assertFalse(canonical.setting_piece_is_bare(piece, 1, 3))
            self.assertTrue(canonical.setting_piece_is_bare(piece, 2, 3))
        parts = ["kun", "hejm", "an"]
        self.assertEqual(canonical.setting_effective_part_total(parts, ["o", "oj"]), 4)
        self.assertFalse(canonical.setting_piece_is_bare("an", 2, 4))
        self.assertEqual(canonical.setting_effective_part_total(parts, ["ne"]), 3)
        self.assertTrue(canonical.setting_suffix_rules_need_boundary(["ar", "an"], ["a", "o"]))
        self.assertTrue(canonical.setting_suffix_rules_need_boundary(["kun", "hejm", "an"], ["o"]))
        self.assertFalse(canonical.setting_suffix_rules_need_boundary(["ar", "an"], ["ne"]))
        self.assertFalse(canonical.setting_suffix_rules_need_boundary(["kant"], ["o"]))

        actions = ["ne", "typed_roles:RLR", "word_boundary"]
        self.assertEqual(canonical.extract_typed_roles(actions, 3), "RLR")
        self.assertEqual(actions, ["ne", "word_boundary"])
        with self.assertRaises(ValueError):
            canonical.extract_typed_roles(["typed_roles:RL"], 3)
        with self.assertRaises(ValueError):
            canonical.extract_typed_roles(["typed_roles:RXR"], 3)
        actions = ["o", "context_annotation:@typed:alo:0"]
        self.assertEqual(
            canonical.extract_context_annotation(actions), "@typed:alo:0",
        )
        self.assertEqual(actions, ["o"])
        actions = ["ne", "ruby_track_only", "ruby_context_annotation:@x"]
        self.assertTrue(
            canonical.consume_track_only_metadata(
                actions, kanji_format=False,
            )
        )
        self.assertEqual(actions, ["ne", "ruby_context_annotation:@x"])
        actions = ["ne", "ruby_track_only"]
        self.assertFalse(
            canonical.consume_track_only_metadata(
                actions, kanji_format=True,
            )
        )
        self.assertEqual(actions, ["ne", "ruby_track_only"])
        actions = ["o", "kanji_track_only"]
        self.assertTrue(
            canonical.consume_track_only_metadata(
                actions, kanji_format=True,
            )
        )
        self.assertEqual(actions, ["o"])
        actions = ["o", "kanji_track_only"]
        self.assertFalse(
            canonical.consume_track_only_metadata(
                actions, kanji_format=False,
            )
        )
        self.assertEqual(actions, ["o", "kanji_track_only"])
        for invalid in (
            ["ruby_track_only", "kanji_track_only"],
            ["ruby_track_only", "ruby_track_only"],
            ["ruby_track_only", "ruby_only"],
            ["kanji_track_only", "ruby_left_boundary"],
            ["kanji_track_only", "ruby_context_annotation:@x"],
        ):
            with self.assertRaises(ValueError):
                canonical.consume_track_only_metadata(
                    invalid, kanji_format=False,
                )
        # Explicitly confirmed word families keep their productive endings, but
        # no generated sibling may fire inside an unrelated longer lexeme.
        self.assertTrue(
            canonical.setting_suffix_rules_need_boundary(
                ["fer"], ["i", "o"], explicit_boundary=True,
            )
        )

    def test_kanji_track_row_bypasses_reviewed_coarse_root_filter(self):
        reviewed = {"promil"}
        self.assertFalse(canonical.setting_forces_reviewed_coarse_root(
            [
                "pro/mil", 69000,
                ["o", "a", "e", "word_boundary", "kanji_track_only"],
            ],
            reviewed,
        ))
        self.assertTrue(canonical.setting_forces_reviewed_coarse_root(
            [
                "promil/o", 69000,
                ["ne", "word_boundary", "ruby_only"],
            ],
            reviewed,
        ))
        self.assertTrue(canonical.setting_forces_reviewed_coarse_root(
            ["pro/mil", 69000, ["ne"]],
            reviewed,
        ))
        with self.assertRaises(ValueError):
            canonical.setting_forces_reviewed_coarse_root(
                [
                    "pro/mil", 69000,
                    ["ruby_track_only", "kanji_track_only"],
                ],
                reviewed,
            )

    def test_global_rule_tie_break_is_language_independent(self):
        # Equal-priority/equal-length rules cannot contain one another; lexical
        # old-key ordering is therefore a safe deterministic final tie-break.
        rules = [("instruad", "ja", 80000), ("instruig", "zh", 80000)]
        ordered = sorted(
            rules,
            key=lambda rule: canonical.stable_replacement_sort_key(rule, lambda _: False),
            reverse=True,
        )
        self.assertEqual([rule[0] for rule in ordered], ["instruig", "instruad"])

    def test_boundary_noop_guard_priority_layers(self):
        bounded, naked = canonical.guarded_boundary_priorities(40000)
        self.assertGreater(bounded, naked)
        self.assertGreater(naked, 40000)
        # A genuinely longer surface still wins by the normal 10,000-per-char
        # length tier.
        self.assertLess(bounded, 50000)

    def test_confirmed_priority_wins_same_surface_without_crossing_length_tier(self):
        stem = "kriptografi"
        confirmed = canonical.confirmed_priority_for_stem(stem)
        generated_peer = len(stem) * 10000 + 5000
        next_length_tier = (len(stem) + 1) * 10000
        self.assertGreater(confirmed, generated_peer)
        self.assertLess(confirmed, next_length_tier)

    def test_suffix_priority_ignores_boundary_padding(self):
        self.assertEqual(canonical.suffix_priority_length("i"), 1)
        self.assertEqual(canonical.suffix_priority_length("i "), 1)
        self.assertEqual(canonical.suffix_priority_length("us"), 2)

    def test_first_wins_dedupe_is_stable(self):
        rules = [
            ("same", "correct", "p1"),
            ("other", "value", "p2"),
            ("same", "dead", "p3"),
            ("other", "also-dead", "p4"),
        ]
        self.assertEqual(canonical.stable_dedupe_first_wins(rules), rules[:2])
        self.assertEqual(multilingual_structure.duplicate_old_keys(rules), ["same", "other"])

    def test_cap_after_hyphen_handles_ruby_rb_without_changing_rt(self):
        rendered = (
            '<ruby>Bikini<rt class="S_S">place</rt></ruby>-'
            '<ruby>atol<rt class="S_S">lowercase gloss</rt></ruby>'
        )
        self.assertEqual(
            canonical._cap_after_hyphen(rendered),
            '<ruby>Bikini<rt class="S_S">place</rt></ruby>-'
            '<ruby>Atol<rt class="S_S">lowercase gloss</rt></ruby>',
        )
        self.assertEqual(canonical._cap_after_hyphen("Abu-dabi"), "Abu-Dabi")
        kanji = (
            '<ruby>港<rt class="S_S">bandar</rt></ruby>-'
            '<ruby>系列<rt class="S_S">seri</rt></ruby>'
        )
        self.assertEqual(
            canonical._cap_after_hyphen(kanji, source_in_rt=True),
            '<ruby>港<rt class="S_S">bandar</rt></ruby>-'
            '<ruby>系列<rt class="S_S">Seri</rt></ruby>',
        )
        self.assertEqual(
            canonical._cap_after_hyphen(kanji + "-begavano", source_in_rt=True),
            '<ruby>港<rt class="S_S">bandar</rt></ruby>-'
            '<ruby>系列<rt class="S_S">Seri</rt></ruby>-Begavano',
        )

    def test_multilingual_signature_preserves_ruby_unicode_and_padding(self):
        ruby = '<ruby>Он Heeyeon<rt class="S_S">person</rt></ruby>'
        ruby_signature = multilingual_structure.structural_signature(" " + ruby + " ")
        literal_signature = multilingual_structure.structural_signature(" Он Heeyeon ")
        no_padding_signature = multilingual_structure.structural_signature(ruby)
        self.assertEqual(ruby_signature, ("PAD:11", "R:Он Heeyeon"))
        self.assertEqual(literal_signature, ("PAD:11", "L:Он Heeyeon"))
        self.assertEqual(no_padding_signature, ("PAD:00", "R:Он Heeyeon"))
        self.assertNotEqual(ruby_signature, literal_signature)
        self.assertNotEqual(ruby_signature, no_padding_signature)
        self.assertNotEqual(
            multilingual_structure.structural_signature('<ruby>UK<rt>x</rt></ruby>'),
            multilingual_structure.structural_signature('<ruby>uk<rt>x</rt></ruby>'),
        )
        padded_ruby = " " + ruby + " "
        self.assertTrue(multilingual_structure.rule_padding_matches(" foo ", padded_ruby))
        self.assertFalse(multilingual_structure.rule_padding_matches(" foo ", ruby))
        self.assertFalse(multilingual_structure.rule_padding_matches("foo", padded_ruby))
        self.assertEqual(multilingual_structure.rendered_visible(padded_ruby), " Он Heeyeon ")

    def test_kanji_source_reconstruction_and_pure_strip(self):
        rendered = (
            ' <ruby>字<rt class="S_S">Abu<br>-Dabi</rt></ruby>'
            '-<ruby>環礁<rt>atol</rt></ruby>o '
        )
        self.assertEqual(
            kanji_structure.esperanto_source_from_kanji(rendered),
            " Abu-Dabi-atolo ",
        )
        self.assertEqual(kanji_structure.strip_kanji_html(rendered), " 字-環礁o ")

    def test_exact_word_anno_key_beats_slashless_collision(self):
        split = [["neŭtr", "neutral"], ["on", "particle"]]
        atomic = [["neŭtron", "neutron"]]
        word_anno = {"neŭtr/on": split, "neŭtron": atomic}
        slashless = {"neŭtron": split}
        self.assertIs(canonical.lookup_word_anno_exact_first(word_anno, slashless, "neŭtron"), atomic)

    def test_app_generation_facades_share_canonical_function(self):
        paths = [ROOT / f"Esperanto-Kanji-Ruby-{language}" / "esp_generation_module.py" for language in ("JA", "ZH", "KO")]
        sources = [path.read_text(encoding="utf-8") for path in paths]
        self.assertEqual(sources[0], sources[1])
        self.assertEqual(sources[1], sources[2])
        self.assertNotIn("\nfrom gen_replacement import *", sources[0])

        # A host may already have an unrelated generic module of this name.
        # The facades must resolve by canonical __file__, not sys.modules name.
        original = sys.modules.get("gen_replacement")
        fake = types.ModuleType("gen_replacement")
        fake.__file__ = str(ROOT / "unrelated" / "gen_replacement.py")
        sys.modules["gen_replacement"] = fake
        sys.modules.pop("_esperanto_canonical_gen_replacement", None)
        try:
            modules = []
            for language, path in zip(("JA", "ZH", "KO"), paths):
                spec = importlib.util.spec_from_file_location(f"esp_generation_{language}", path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                modules.append(module)
                self.assertEqual(Path(module.generate.__code__.co_filename).resolve(), Path(canonical.__file__).resolve())
            self.assertIs(modules[0].generate, modules[1].generate)
            self.assertIs(modules[1].generate, modules[2].generate)
        finally:
            if original is None:
                sys.modules.pop("gen_replacement", None)
            else:
                sys.modules["gen_replacement"] = original
            sys.modules.pop("_esperanto_canonical_gen_replacement", None)


_PARADIGM_ENDINGS = ("o", "oj", "on", "ojn", "a", "aj", "an", "ajn", "e", "en")
NOVJORK_PARADIGM_EXPECTED = {}
for _surface_stem, _target_stem in (
    ("novjork", "novjork"),
    ("novjorkan", "novjork/an"),
):
    for _ending in _PARADIGM_ENDINGS:
        _lower_surface = _surface_stem + _ending
        _target = _target_stem + "/" + _ending
        for _surface in (
            _lower_surface,
            _lower_surface.capitalize(),
            _lower_surface.upper(),
        ):
            NOVJORK_PARADIGM_EXPECTED[_surface] = _target_decomposition(_target)
if len(NOVJORK_PARADIGM_EXPECTED) != 60:
    raise AssertionError("Novjork two-stem/three-case paradigm must contain 60 forms")
BONAER_PARADIGM_EXPECTED = {}
for _ending in _PARADIGM_ENDINGS:
    _lower_surface = "bonaer" + _ending
    for _surface in (
        _lower_surface,
        _lower_surface.capitalize(),
        _lower_surface.upper(),
    ):
        BONAER_PARADIGM_EXPECTED[_surface] = _target_decomposition(
            "bonaer/" + _ending
        )
if len(BONAER_PARADIGM_EXPECTED) != 30:
    raise AssertionError("Bonaer bounded three-case paradigm must contain 30 forms")


class DeployedRubyRegressionTests(unittest.TestCase):
    EXPECTED = {
        "onin": "oni/n",
        "anon": "an/on",
        "anona": "anona",
        "traktata": "trakt/at/a",
        "spirante": "spir/ant/e",
        "signifhavaj": "signif/hav/aj",
        "argentano": "argentan/o",
        "butanono": "butanon/o",
        "domeno": "domen/o",
        "konstantano": "konstantan/o",
        "kanto": "kant/o",
        "Kantoa": "kanto/a",
        "ursulanina": "ursul/an/in/a",
        "paiŭanan": "paiŭan/an",
        "ŝonaan": "ŝona/an",
        "RenKEJtiĝon": "renkejtiĝo/n",
        "kunhejmano": "kun/hejm/an/o",
        "neŭtronoj": "neŭtron/oj",
        "jutubo": "jutub/o",
        "jutubaj": "jutub/aj",
        "Taranaki": "taranaki",
        "s-ino": "s-ino",
        "s-ro": "s-ro",
        "S-ro": "s-ro",
        "d-ro": "d-ro",
        "D-ro": "d-ro",
        "prof.": "prof.",
        "Prof.": "prof.",
        "teranoj,": "ter/an/oj",
        "Urewera": "urewera",
        "Whanganui": "whanganui",
        "Egmont": "egmont",
        "koninda": "kon/ind/a",
        "biologio": "biologi/o",
        "fiziologio": "fiziologi/o",
        "aroganta": "arogant/a",
        "Mezazio": "mez/azi/o",
        "kriptografio": "kriptografi/o",
        "svislando": "svis/land/o",
        "sovetunio": "sovet/uni/o",
        "aparteni": "aparten/i",
        "italujo": "ital/uj/o",
        "Katmando": "katmand/o",
        "Nurnbergo": "nurnberg/o",
        "Burno": "burn/o",
        "Kievon": "kiev/on",
        "Mukdeno": "mukden/o",
        "Mezorienton": "mez/orient/on",
        "Sovetunia": "sovet/uni/a",
        "Kamakuron": "kamakur/on",
        "Enoŝimon": "enoŝim/on",
        "Tuskolo": "tuskol/o",
        "Taragono": "taragon/o",
        "Ĝirono": "ĝiron/o",
        "Smolenko": "smolenk/o",
        "Kaŭno": "kaŭn/o",
        "Bikini-Atolo": "bikini/atol/o",
        "Abu-Dabi": "abu/dab/i",
        "BUENOS-AIRESO": "buenos-aires/o",
        "Ukrainio": "ukrain/io",
        "Ukrainia": "ukrain/ia",
        "Sovetio": "sovet/io",
        "Sovetia": "sovet/ia",
        "Iberio": "iber/io",
        "Eŭrazio": "eŭrazi/o",
        "Bohemio": "bohem/io",
        "Etiopio": "etiop/io",
        "Kroatio": "kroat/io",
        "Pomerio": "pomer/io",
        "Ĉeĥion": "ĉeĥ/ion",
        "Moravio": "moravi/o",
        "golfoflu": "golf/o/flu",
        "afero": "afer/o",
        "meti": "met/i",
        "etoso": "etos/o",
        "etos": "et/os",
        "amaso": "amas/o",
        "amase": "amas/e",
        "amasa": "amas/a",
        "amas": "am/as",
        "radono": "radon/o",
        "leonino": "leon/in/o",
        "teranoj": "ter/an/oj",
        "bonlingvanojn": "bon/lingv/an/ojn",
        "seulanoj": "seul/an/oj",
        "porto-rikanoj": "porto-rik/an/oj",
        "bonaero": "bonaer/o",
        "Bonaero": "bonaer/o",
        "BONAERO": "bonaer/o",
        "novjorko": "novjork/o",
        "Novjorko": "novjork/o",
        "NOVJORKO": "novjork/o",
        "Novjorkon": "novjork/on",
        "novjorkaj": "novjork/aj",
        "novjorkan": "novjork/an",
        "Tomisto": "tomist/o",
        "natria klorido": "natri/a/klor/id/o",
        # Consecutive bare inflection letters are one observable literal run in
        # rendered HTML.  Their conceptual splits are asserted below at HTML
        # fragment level (there must be no ruby boundary between the letters).
        "elektron": "elektr/on",
        "platan": "plat/an",
        "alten": "alt/en",
        "meritokrati": "merit/o/krati",
        # The data-driven rule must preserve this recorded homograph.
        "sudanan": "sudan/an",
        "sud-sudana": "sud/sudan/a",
        "sud-sudano": "sud/sudan/o",
        "UK": "uk",
        "UK-oj": "uk/oj",
        "UK-on": "uk/on",
        "SAT": "sat",
        "UEA": "uea",
        "JEI": "jei",
        "IJK": "ijk",
        "TEJO": "tejo",
        "UN": "un",
        "KLEG": "kleg",
        "KS": "ks",
        "EPA": "epa",
        "ILEI": "ilei",
        "LKK": "lkk",
        "PS": "ps",
        "PS2.0": "ps2.0",
        "Google": "google",
        "DeepL": "deepl",
        # Lowercase Esperanto homographs must retain their ordinary rules.
        "sat": "sat",
        "un": "un",
        "ks": "ks",
        "ps": "ps",
        "tejo": "tejo",
        "pet": "pet",
        "maria": "mari/a",
        "mari-a": "mari/a",
        "Maria-Virgulino": "maria/virg/ul/in/o",
        "Davaon": "davao/n",
        "pat!": "pat",
        "halt!": "halt",
        "ekz.": "ekz.",
        "alo": "al/o",
        "kajo": "kaj/o",
        "kajon": "kaj/on",
        "videaĵo": "vide/aĵ/o",
        "diplomatio": "diplomati/o",
        "sindevigo": "sin/dev/ig/o",
        "singarde": "sin/gard/e",
        "sinmortigo": "sin/mort/ig/o",
        "Sejong-kampuso": "sejong/kampus/o",
        "Ivo": "ivo",
        "f-ino": "f-ino",
        "Aŭdu": "aŭdu",
        "aŭdu": "aŭd/u",
        "ChatGPT-on": "chatgpt/on",
        "anestezi": "anestez/i",
        "tereno": "teren/o",
        "terenoj": "teren/oj",
        "terenon": "teren/on",
        "ĉasterenoj": "ĉas/teren/oj",
        "akordigos": "akord/ig/os",
        "difinitaj": "difin/it/aj",
        "difinitan": "difin/it/an",
        "memoriganta": "memor/ig/ant/a",
        "rehonorigante": "re/honor/ig/ant/e",
        "akordigas": "akord/ig/as",
        "difinite": "difin/it/e",
        "memorigantoj": "memor/ig/ant/oj",
        "rehonorigantan": "re/honor/ig/ant/an",
        "agrablas": "agrabl/as",
        "legeblas": "leg/ebl/as",
        "malsamas": "mal/sam/as",
        "mankis": "mank/is",
        "d-ron": "d-ro/n",
        "s-ron": "s-ro/n",
        "S-ron": "s-ro/n",
        "-at-": "at",
        "re-agi": "re/ag/i",
        "el-meti": "el/met/i",
        "re-meti": "re/met/i",
        "en-meti": "en/met/i",
        "el-metu": "el/met/u",
        "el-teni": "el/ten/i",
        "ge-soli": "ge/sol/i",
        "duon-horo": "du/on/hor/o",
        "don-it-aĵo": "don/it/aĵ/o",
        "unu-op-ulo": "unu/op/ul/o",
        "Dank'": "dank",
        "Di'": "di",
        "ni'": "ni",
        "man'": "man",
        "l'": "l'",
        "l'Dio": "l'/di/o",
        "Di’": "di",
        "L'": "l'",
        "L'Dio": "l'/di/o",
        "l’": "l’",
        "l’Dio": "l’/di/o",
        "L’": "l’",
        "L’Dio": "l’/di/o",
        "xl'Dio": "xl/di/o",
        "xl’Dio": "xl/di/o",
        "Japanion": "japan/ion",
        "Koreion": "kore/ion",
        "Rusion": "rus/ion",
        "Ukrainion": "ukrain/ion",
        "Vjetnamion": "vjetnam/ion",
        "Ĉinion": "ĉin/ion",
        "Eŭrazion": "eŭrazi/on",
        "ioj": "ioj",
        "iojn": "iojn",
        "hongkongan": "hongkong/an",
        "Butanon": "butan/on",
        "Jokohaman": "jokoham/an",
        "firmao": "firma/o",
        "Rumanio": "ruman/io",
        "Jugoslavio": "jugoslav/io",
        "Skanu": "skan/u",
        "kriptaĵoscienco": "kript/aĵ/o/scienc/o",
        "retroen": "retro/en",
        "ĉinaangla": "ĉin/a/angl/a",
        "memeo": "meme/o",
        "Tang-imperifamilio": "tang/imperi/famili/o",
        "bizaraĵon": "bizar/aĵ/on",
        "jurnalisto": "jurnal/ist/o",
        "dudekon": "du/dek/on",
        "subeniri": "sub/en/ir/i",
        "kriptologio": "kript/o/logi/o",
        "areopologio": "are/op/o/logi/o",
        "fotografio": "fot/o/grafi/o",
        "pasigrafio": "pasi/grafi/o",
        "meritokratio": "merit/o/krati/o",
        "meritokratia": "merit/o/krati/a",
        "meritokratian": "merit/o/krati/an",
        "hipermeritokratio": "hiper/merit/o/krati/o",
        "Brazilio": "brazili/o",
        "Sirio": "siri/o",
        "Oceania": "oceani/a",
        "radiofonio": "radiofoni/o",
        "resumi": "resum/i",
        "hokkajdon": "hokkajdo/n",
        "Hokkajdon": "hokkajdo/n",
        "HOKKAJDON": "hokkajdo/n",
        "promilo": "promil/o",
        # The formal 62,313-row audit found these 13 pre-existing residuals:
        # 11 exact Ruby-track corrections plus two reviewed coarse displays.
        # No root is made finer merely to shorten a ruby label.
        "Argolando": "arg/o/land/o",
        "Eolia": "eol/ia",
        "Eoliano": "eol/i/an/o",
        "Eolio": "eol/io",
        "Frigio": "frig/io",
        "Ionia": "ioni/a",
        "Ligurio": "ligur/io",
        "Ohiorivero": "ohi/o/river/o",
        "Retio": "ret/io",
        "Umbrio": "umbr/io",
        "alternanco": "alternanc/o",
        "psikokirurgio": "psik/o/kirurg/io",
        "tienvojaĝo": "tie/n/vojaĝ/o",
        # Approved coarse/fake-decomposition neighbours must retain their
        # own exact rules despite the capitalized Ionia/Ligurio additions.
        "Ionia Maro": "ioni/a/mar/o",
        "Ionio": "ioni/o",
        "ioniano": "ioni/an/o",
        "ligurio": "liguri/o",
        # Case-sensitive proper names must coexist with their lowercase
        # grammatical/lexical homographs.
        "sin": "si/n",
        "kacumi": "kac/um/i",
        **{
            surface: surface.lower()
            for surface in corpus_data.CASE_SENSITIVE_EXACT_GLOSSES
        },
        **{
            surface: _target_decomposition(target)
            for surface, (target, _case_sensitive)
            in corpus_data.MANAGED_EXACT_TARGETS.items()
        },
        **{
            row["surface"]: _manifest_decomposition(row)
            for row in corpus_data.EXACT_MANIFEST["exact_surfaces"]
        },
        **{
            surface: _target_decomposition(spec["target"])
            for surface, spec in corpus_data.MANAGED_MORPH_TARGETS.items()
        },
        **{
            row["surface"]: _manifest_decomposition(row)
            for row in corpus_data.REVIEWED_EXACT_MANIFEST["exact_surfaces"]
        },
        **NOVJORK_PARADIGM_EXPECTED,
        **BONAER_PARADIGM_EXPECTED,
    }

    LOWERCASE_HOMOGRAPHS = ("SAT", "UN", "KS", "PS", "TEJO", "PET", "Maria")

    REQUIRED_RUBY_COMPONENTS = {
        "sin": ("si",),
        "kacumi": ("kac", "um"),
        "Sin": ("Sin",),
        "Kacumi": ("Kacumi",),
        "Katmando": ("Katmand",),
        "Nurnbergo": ("Nurnberg",),
        "Burno": ("Burn",),
        "Kievon": ("Kiev",),
        "Mukdeno": ("Mukden",),
        "Mezorienton": ("Mez", "orient"),
        "Kamakuron": ("Kamakur",),
        "Enoŝimon": ("Enoŝim",),
        "Tuskolo": ("Tuskol",),
        "Taragono": ("Taragon",),
        "Ĝirono": ("Ĝiron",),
        "Smolenko": ("Smolenk",),
        "Kaŭno": ("Kaŭn",),
        "Bikini-Atolo": ("Bikini", "Atol"),
        "BUENOS-AIRESO": ("BUENOS-AIRES",),
        "Bonaero": ("Bonaer",),
        "BONAERO": ("BONAER",),
        "Novjorko": ("Novjork",),
        "Novjorkon": ("Novjork",),
        "novjorkaj": ("novjork",),
        "novjorkan": ("novjork",),
        "Tomisto": ("Tomist",),
        "natria klorido": ("natri", "klor", "id"),
        "kriptografio": ("kriptografi",),
        "Moravio": ("Moravi",),
        "golfoflu": ("golf", "flu"),
        "afero": ("afer",),
        "meti": ("met",),
        "etoso": ("etos",),
        "amaso": ("amas",),
        "amase": ("amas",),
        "amasa": ("amas",),
        "radono": ("radon",),
        "alo": ("al",),
        "kajo": ("kaj",),
        "videaĵo": ("vide", "aĵ"),
        "diplomatio": ("diplomati",),
        "sindevigo": ("sin", "dev", "ig"),
        "singarde": ("sin", "gard"),
        "sinmortigo": ("sin", "mort", "ig"),
        "Sejong-kampuso": ("Sejong", "kampus"),
        "Ivo": ("Ivo",),
        "f-ino": ("f-ino",),
        "Aŭdu": ("Aŭdu",),
        "aŭdu": ("aŭd",),
        "ChatGPT-on": ("ChatGPT",),
        "anestezi": ("anestez",),
        "tereno": ("teren",),
        "terenoj": ("teren",),
        "terenon": ("teren",),
        "ĉasterenoj": ("ĉas", "teren"),
        "akordigos": ("akord", "ig", "os"),
        "difinitaj": ("difin", "it"),
        "difinitan": ("difin", "it"),
        "memoriganta": ("memor", "ig", "ant"),
        "rehonorigante": ("re", "honor", "ig", "ant"),
        "akordigas": ("akord", "ig", "as"),
        "difinite": ("difin", "it"),
        "memorigantoj": ("memor", "ig", "ant"),
        "rehonorigantan": ("re", "honor", "ig", "ant"),
        "agrablas": ("agrabl", "as"),
        "legeblas": ("leg", "ebl", "as"),
        "malsamas": ("mal", "sam", "as"),
        "mankis": ("mank", "is"),
        "d-ron": ("d-ro",),
        "s-ron": ("s-ro",),
        "S-ron": ("S-ro",),
        "-at-": ("at",),
        "re-agi": ("re", "ag"),
        "el-meti": ("el", "met"),
        "re-meti": ("re", "met"),
        "en-meti": ("en", "met"),
        "el-metu": ("el", "met"),
        "el-teni": ("el", "ten"),
        "ge-soli": ("ge", "sol"),
        "duon-horo": ("du", "on", "hor"),
        "don-it-aĵo": ("don", "it", "aĵ"),
        "unu-op-ulo": ("unu", "op", "ul"),
        "Dank'": ("Dank",),
        "Di'": ("Di",),
        "ni'": ("ni",),
        "man'": ("man",),
        "l'": ("l'",),
        "l'Dio": ("l'", "Di"),
        "Di’": ("Di",),
        "L'": ("L'",),
        "L'Dio": ("L'", "Di"),
        "l’": ("l’",),
        "l’Dio": ("l’", "Di"),
        "L’": ("L’",),
        "L’Dio": ("L’", "Di"),
        "xl'Dio": ("Di",),
        "xl’Dio": ("Di",),
        "Japanion": ("Japan",),
        "Koreion": ("Kore",),
        "Rusion": ("Rus",),
        "Ukrainion": ("Ukrain",),
        "Vjetnamion": ("Vjetnam",),
        "Ĉinion": ("Ĉin",),
        "Eŭrazion": ("Eŭrazi",),
        "ioj": ("ioj",),
        "iojn": ("iojn",),
        "hongkongan": ("hongkong",),
        "Butanon": ("Butan",),
        "Jokohaman": ("Jokoham",),
        "firmao": ("firma",),
        "Rumanio": ("Ruman",),
        "Jugoslavio": ("Jugoslav",),
        "Skanu": ("Skan",),
        "kriptaĵoscienco": ("kript", "aĵ", "scienc"),
        "retroen": ("retro",),
        "ĉinaangla": ("ĉin", "angl"),
        "memeo": ("meme",),
        "Tang-imperifamilio": ("Tang", "imperi", "famili"),
        "bizaraĵon": ("bizar", "aĵ"),
        "jurnalisto": ("jurnal", "ist"),
        "dudekon": ("du", "dek"),
        "subeniri": ("sub", "ir"),
        "kriptologio": ("kript", "logi"),
        "areopologio": ("are", "op", "logi"),
        "fotografio": ("fot", "grafi"),
        "pasigrafio": ("pasi", "grafi"),
        "meritokratio": ("merit", "krati"),
        "meritokratia": ("merit", "krati"),
        "meritokratian": ("merit", "krati"),
        "hipermeritokratio": ("hiper", "merit", "krati"),
        "Brazilio": ("Brazili",),
        "Sirio": ("Siri",),
        "Oceania": ("Oceani",),
        "radiofonio": ("radiofoni",),
        "hokkajdon": ("hokkajdo",),
        "Hokkajdon": ("Hokkajdo",),
        "HOKKAJDON": ("HOKKAJDO",),
        "promilo": ("promil",),
    }

    def test_all_language_apps(self):
        for language in ("JA", "ZH", "KO"):
            with self.subTest(language=language):
                app_dir = ROOT / f"Esperanto-Kanji-Ruby-{language}"
                data_dir = app_dir / "app_data"
                module = _runtime_module(app_dir, language)
                payload = json.loads((data_dir / "置換リスト_ルビ.json").read_text(encoding="utf-8"))
                settings = json.loads(
                    (data_dir / "分解設定.json").read_text(encoding="utf-8")
                )
                ruby_left_rows = [
                    row for row in settings
                    if isinstance(row, list) and len(row) == 3
                    and "ruby_left_boundary" in row[2]
                ]
                self.assertEqual(
                    {row[0] for row in ruby_left_rows},
                    {"Bonaer", "BONAER", "novjork"},
                    f"{language} productive Ruby-left scope",
                )
                self.assertEqual(
                    {row[0]: set(row[2]) for row in ruby_left_rows},
                    {
                        "Bonaer": {
                            "ne", "atomic_no_split", "ruby_left_boundary",
                            "case_sensitive",
                            "ruby_context_annotation:@atomic-family:Bonaer",
                        },
                        "BONAER": {
                            "ne", "atomic_no_split", "ruby_left_boundary",
                            "case_sensitive",
                            "ruby_context_annotation:@atomic-family:BONAER",
                        },
                        "novjork": {
                            "ne", "atomic_no_split", "ruby_left_boundary",
                        },
                    },
                )
                compositional_rows = [
                    row for row in settings
                    if isinstance(row, list) and len(row) == 3
                    and row[0] == "bon/aer" and set(row[2]) == {"ne"}
                ]
                self.assertEqual(len(compositional_rows), 1, language)
                bonaer_morph_rows = [
                    row for row in settings
                    if isinstance(row, list) and len(row) == 3
                    and row[0] == "bonaer"
                    and "word_boundary" in row[2]
                    and "ruby_context_annotation:@atomic-family:bonaer" in row[2]
                    and "ruby_track_only" not in row[2]
                    and "kanji_track_only" not in row[2]
                ]
                self.assertEqual(len(bonaer_morph_rows), 1, language)
                self.assertTrue(all(
                    row[1] > compositional_rows[0][1]
                    for row in ruby_left_rows if row[0].casefold() == "bonaer"
                ))
                novjork_morph_rows = [
                    row for row in settings
                    if isinstance(row, list) and len(row) == 3
                    and row[0] == "novjork"
                    and "word_boundary" in row[2]
                    and "ruby_track_only" not in row[2]
                    and "kanji_track_only" not in row[2]
                    and any(ending in row[2] for ending in _PARADIGM_ENDINGS)
                ]
                self.assertEqual(len(novjork_morph_rows), 1, language)
                novjorkan_morph_rows = [
                    row for row in settings
                    if isinstance(row, list) and len(row) == 3
                    and row[0] == "novjork/an"
                    and "word_boundary" in row[2]
                    and "ruby_track_only" in row[2]
                    and any(ending in row[2] for ending in _PARADIGM_ENDINGS)
                ]
                self.assertEqual(len(novjorkan_morph_rows), 1, language)
                self.assertFalse(any(
                    "ruby_left_boundary" in row[2]
                    and "word_boundary" in row[2]
                    for row in settings
                    if isinstance(row, list) and len(row) == 3
                ))
                ruby_only_rows = [
                    row for row in settings
                    if isinstance(row, list) and len(row) == 3
                    and "ruby_only" in row[2]
                ]
                self.assertEqual(len(ruby_only_rows), 1, language)
                self.assertEqual(ruby_only_rows[0][0], "promil/o")
                ruby_track_rows = [
                    row for row in settings
                    if isinstance(row, list) and len(row) == 3
                    and "ruby_track_only" in row[2]
                ]
                strict_payload = json.loads(
                    (HERE / "_strict_gold_reference_fixes.json").read_text(
                        encoding="utf-8"
                    )
                )
                strict_ruby_track = {
                    entry["target"]: entry
                    for entry in strict_payload["entries"]
                    if entry.get("ruby_track_only")
                }
                self.assertEqual(
                    {row[0] for row in ruby_track_rows},
                    {"novjork/an", *strict_ruby_track},
                )
                for row in ruby_track_rows:
                    if row[0] == "novjork/an":
                        self.assertIn("word_boundary", row[2])
                        self.assertTrue(any(
                            ending in row[2] for ending in _PARADIGM_ENDINGS
                        ))
                        continue
                    entry = strict_ruby_track[row[0]]
                    self.assertEqual(
                        set(row[2]),
                        {
                            "ne", "word_boundary", "case_sensitive",
                            f"typed_roles:{entry['typed_roles']}",
                            "ruby_track_only",
                        },
                    )
                kanji_track_rows = [
                    row for row in settings
                    if isinstance(row, list) and len(row) == 3
                    and "kanji_track_only" in row[2]
                ]
                self.assertEqual(len(kanji_track_rows), 1, language)
                self.assertEqual(kanji_track_rows[0][0], "pro/mil")
                self.assertIn("word_boundary", kanji_track_rows[0][2])
                self.assertTrue(
                    set(_PARADIGM_ENDINGS).issubset(kanji_track_rows[0][2])
                )
                self.assertFalse(any(
                    {"ruby_track_only", "kanji_track_only"}.issubset(row[2])
                    or (
                        "ruby_only" in row[2]
                        and (
                            "ruby_track_only" in row[2]
                            or "kanji_track_only" in row[2]
                        )
                    )
                    for row in settings
                    if isinstance(row, list) and len(row) == 3
                ))
                global_rules = next(value for key, value in payload.items() if "replacements_final_list" in key)
                local_rules = next(value for key, value in payload.items() if "localized_string" in key)
                two_char_rules = next(value for key, value in payload.items() if "2char" in key)
                replacement_helper = canonical.load_app_replacement_helper(app_dir)
                char_widths = json.loads(
                    (data_dir / "char_widths.json").read_text(encoding="utf-8")
                )
                width_cache = {}
                for label, rules in (
                    ("global", global_rules),
                    ("local", local_rules),
                    ("two_char", two_char_rules),
                ):
                    old_sequence = [rule[0] for rule in rules]
                    self.assertEqual(
                        len(old_sequence), len(set(old_sequence)),
                        f"{language} {label} contains duplicate old keys",
                    )
                    malformed_break_tags = [
                        (rule[0], rule[1])
                        for rule in rules
                        if re.search(r'<[^>]*<br\s*/?>', rule[1], re.I)
                    ]
                    self.assertEqual(
                        malformed_break_tags[:20], [],
                        f"{language} {label} malformed inline break tags="
                        f"{len(malformed_break_tags)}",
                    )
                    invalid_rt_markup = []
                    for rule in rules:
                        for inner in re.findall(
                            r'<rt\b[^>]*>(.*?)</rt>', rule[1], re.I | re.S,
                        ):
                            residue = re.sub(r'<br\s*/?>', '', inner, flags=re.I)
                            if '<' in residue or '>' in residue:
                                invalid_rt_markup.append((rule[0], inner))
                    self.assertEqual(
                        invalid_rt_markup[:20], [],
                        f"{language} {label} invalid rt markup="
                        f"{len(invalid_rt_markup)}",
                    )
                    width_mismatches = []
                    for old, new, _placeholder in rules:
                        for match in FINAL_RUBY_RE.finditer(new):
                            rb = match.group(1)
                            rt = re.sub(
                                r"<br\s*/?>", "", match.group(2),
                                flags=re.IGNORECASE,
                            )
                            cache_key = (rb, rt)
                            expected_ruby = width_cache.get(cache_key)
                            if expected_ruby is None:
                                expected_ruby = replacement_helper.output_format(
                                    rb,
                                    rt,
                                    "HTML格式_Ruby文字_大小调整",
                                    char_widths,
                                )
                                width_cache[cache_key] = expected_ruby
                            if match.group(0) != expected_ruby:
                                width_mismatches.append(
                                    (old, match.group(0), expected_ruby)
                                )
                    self.assertEqual(
                        width_mismatches[:20], [],
                        f"{language} {label} final rt width mismatches="
                        f"{len(width_mismatches)}",
                    )
                visible_mismatches = [
                    (rule[0], multilingual_structure.rendered_visible(rule[1]))
                    for rule in global_rules
                    if rule[0] != multilingual_structure.rendered_visible(rule[1])
                ]
                self.assertEqual(
                    visible_mismatches[:20], [],
                    f"{language} global old/visible-new mismatch count={len(visible_mismatches)}",
                )
                edge_mismatches = []
                for old, new, placeholder in global_rules:
                    edge = lambda value: (
                        len(value) - len(value.lstrip(" ")),
                        len(value) - len(value.rstrip(" ")),
                    )
                    if len({edge(old), edge(new), edge(placeholder)}) != 1:
                        edge_mismatches.append((old, new, placeholder))
                self.assertEqual(
                    edge_mismatches[:20], [],
                    f"{language} global edge-space invariant failures="
                    f"{len(edge_mismatches)}",
                )
                placeholder_cores = [
                    placeholder.strip(" ")
                    for _old, _new, placeholder in global_rules
                ]
                self.assertTrue(all(placeholder_cores))
                self.assertEqual(
                    len(placeholder_cores), len(set(placeholder_cores)),
                    f"{language} duplicate global placeholder cores",
                )
                old_rules = {rule[0] for rule in global_rules}
                self.assertNotIn("novjork", old_rules)
                self.assertTrue({
                    " novjork", " Novjork", " NOVJORK",
                    " Bonaer", " BONAER",
                }.issubset(old_rules))
                # The learner-authoritative E_stem bon/aer rule stays naked
                # and reusable in lowercase/token-internal compositions.
                self.assertIn("bonaer", old_rules)
                self.assertNotIn(" bonaer", old_rules)
                rule_order = {rule[0]: index for index, rule in enumerate(global_rules)}
                for surface in ("Bonaer", "BONAER"):
                    self.assertIn(surface, rule_order)
                    self.assertLess(
                        rule_order[f" {surface}"], rule_order[surface],
                        (language, surface, "token-left atomic must win"),
                    )
                self.assertIn("novjorki", rule_order)
                self.assertLess(rule_order["novjorki"], rule_order[" novjork"])
                sentence_punctuation_inside_rb = [
                    rule[0] for rule in global_rules
                    if re.search(r'<ruby>[^<]*[!?]<rt', rule[1], re.IGNORECASE)
                ]
                self.assertEqual(sentence_punctuation_inside_rb, [])
                self.assertNotIn("onin", old_rules)
                self.assertTrue({" onin ", " ONIN ", " Onin "}.issubset(old_rules))
                # Exact anon uses the longer bounded split rule, while the
                # unbounded no-op guard protects the non-Esperanto word anona.
                self.assertIn("anon", old_rules)
                self.assertTrue({" anon ", " ANON ", " Anon "}.issubset(old_rules))
                anon_guard = next(rule for rule in global_rules if rule[0] == "anon")
                self.assertEqual(anon_guard[1], "anon")
                # Completed -an inflections and suffix expansions are bounded;
                # they must not consume substrings inside proper names.
                for naked, bounded in (("teranoj", " teranoj "), ("arana", " arana ")):
                    self.assertNotIn(naked, old_rules)
                    self.assertIn(bounded, old_rules)
                self.assertNotIn("Taranaki", old_rules)
                self.assertIn(" Taranaki ", old_rules)
                self.assertNotIn("s-ino", old_rules)
                self.assertIn(" s-ino ", old_rules)
                for surface, (_, case_sensitive) in corpus_data.MANAGED_EXACT_TARGETS.items():
                    if not case_sensitive:
                        continue
                    self.assertNotIn(surface, old_rules)
                    self.assertIn(f" {surface} ", old_rules)
                for surface in corpus_data.REVIEWED_TYPED_EXACT_TARGETS:
                    self.assertNotIn(surface, old_rules)
                    self.assertIn(f" {surface} ", old_rules)
                for surface in corpus_data.MANAGED_TYPED_EXACT_TARGETS:
                    self.assertNotIn(surface, old_rules)
                    self.assertIn(f" {surface} ", old_rules)
                for surface in ("Whanganui", "Taranaki", "Urewera", "Egmont"):
                    rule = next(rule for rule in global_rules if rule[0] == f" {surface} ")
                    self.assertIn(corpus_data.ANNOTATIONS[language.lower()][surface], rule[1])
                skip = module.import_placeholders(str(data_dir / "placeholders_skip.txt"))
                local_capture = module.import_placeholders(str(data_dir / "placeholders_localcapture.txt"))
                words = list(self.EXPECTED)
                rendered = module.orchestrate_comprehensive_esperanto_text_replacement(
                    "\n".join(f" {word} " for word in words),
                    skip,
                    local_rules,
                    local_capture,
                    global_rules,
                    two_char_rules,
                    "HTML格式_Ruby文字_大小调整",
                )
                lines = rendered.splitlines()
                self.assertEqual(len(lines), len(words))
                actual = {word: _decomposition(line) for word, line in zip(words, lines)}
                self.assertEqual(actual, self.EXPECTED)
                rendered_by_word = dict(zip(words, lines))

                # Reviewed proper roots are productive only at a token's left
                # edge. Novjork allows all three cases; Bonaer deliberately
                # excludes arbitrary lowercase derivatives because bon+aer is
                # a genuine compositional reading.
                family_probes = (
                    "novjorkdevena", "Novjorkdevena", "NOVJORKDEVENA",
                    "Bonaerdevena", "BONAERDEVENA",
                    "bonaerdevena", "xnovjorkdevena", "supernovjorko",
                    "malbonaero", "trebonaero", "xBonaerdevena",
                    "novjorki", "novjorkio",
                    "Novjorkdevena!",
                )
                family_html = module.orchestrate_comprehensive_esperanto_text_replacement(
                    "\n".join(family_probes),
                    skip, local_rules, local_capture, global_rules, two_char_rules,
                    "HTML格式_Ruby文字_大小调整",
                ).splitlines()
                self.assertEqual(len(family_html), len(family_probes))
                family_rendered = dict(zip(family_probes, family_html))
                flat = lambda value: re.sub(
                    r"<br\s*/?>", "", value, flags=re.IGNORECASE,
                )
                novjork_marker = corpus_data.ANNOTATIONS[language.lower()]["novjork"]
                bonaer_marker = corpus_data.ANNOTATIONS[language.lower()]["bonaer"]
                for surface, root in (
                    ("novjorkdevena", "novjork"),
                    ("Novjorkdevena", "Novjork"),
                    ("NOVJORKDEVENA", "NOVJORK"),
                ):
                    signature = multilingual_structure.structural_signature(
                        family_rendered[surface]
                    )
                    self.assertIn(f"R:{root}", signature, (language, surface))
                    self.assertIn(novjork_marker, flat(family_rendered[surface]))
                for surface, root in (
                    ("Bonaerdevena", "Bonaer"),
                    ("BONAERDEVENA", "BONAER"),
                ):
                    signature = multilingual_structure.structural_signature(
                        family_rendered[surface]
                    )
                    self.assertIn(f"R:{root}", signature, (language, surface))
                    self.assertIn(bonaer_marker, flat(family_rendered[surface]))
                for surface in (
                    "xnovjorkdevena", "supernovjorko",
                    "malbonaero", "trebonaero", "xBonaerdevena",
                    "bonaerdevena",
                ):
                    normalized = flat(family_rendered[surface])
                    self.assertNotIn(novjork_marker, normalized, (language, surface))
                    self.assertNotIn(bonaer_marker, normalized, (language, surface))
                    self.assertFalse(any(
                        span.casefold() in {"r:novjork", "r:bonaer"}
                        for span in multilingual_structure.structural_signature(
                            family_rendered[surface]
                        )
                    ))
                lower_bonaer_signature = tuple(
                    span.casefold() for span in multilingual_structure.structural_signature(
                        family_rendered["bonaerdevena"]
                    )
                )
                self.assertIn("r:bon", lower_bonaer_signature)
                self.assertIn("r:aer", lower_bonaer_signature)
                self.assertNotIn("r:bonaer", lower_bonaer_signature)
                for surface in (
                    "malbonaero", "trebonaero", "xBonaerdevena",
                ):
                    signature = tuple(
                        span.casefold() for span in
                        multilingual_structure.structural_signature(
                            family_rendered[surface]
                        )
                    )
                    self.assertIn("r:bon", signature, (language, surface))
                    self.assertIn("r:aer", signature, (language, surface))
                    self.assertNotIn("r:bonaer", signature, (language, surface))
                for surface in ("novjorki", "novjorkio"):
                    normalized = flat(family_rendered[surface])
                    self.assertNotIn(novjork_marker, normalized)
                    self.assertIn(
                        "r:novjorki",
                        tuple(
                            span.casefold() for span in
                            multilingual_structure.structural_signature(
                                family_rendered[surface]
                            )
                        ),
                    )
                punctuated = family_rendered["Novjorkdevena!"]
                self.assertIn("R:Novjork", multilingual_structure.structural_signature(punctuated))
                self.assertRegex(punctuated, r"!\s*(?:<br>)?\s*$")

                protected, local_family = (
                    module.orchestrate_comprehensive_esperanto_text_replacement(
                        "%novjorkdevena%\n@novjorkdevena@",
                        skip, local_rules, local_capture, global_rules,
                        two_char_rules, "HTML格式_Ruby文字_大小调整",
                    ).splitlines()
                )
                self.assertEqual(
                    re.sub(r"<br\s*/?>", "", protected, flags=re.IGNORECASE).strip(),
                    "novjorkdevena",
                )
                self.assertNotIn("<ruby", protected.casefold())
                self.assertIn(
                    "R:novjork",
                    multilingual_structure.structural_signature(local_family),
                )

                reviewed_local = json.loads(
                    (HERE / "localized_global_exact_reviewed.json").read_text(
                        encoding="utf-8"
                    )
                )
                local_specs = []
                for spec in reviewed_local["targets"]:
                    for surface in (
                        spec["root"],
                        spec["root"].capitalize(),
                        spec["root"].upper(),
                    ):
                        local_specs.append((surface, spec["signature_casefold"]))
                reviewed_rendered = module.orchestrate_comprehensive_esperanto_text_replacement(
                    "\n".join(f"@{surface}@" for surface, _signature in local_specs),
                    skip,
                    local_rules,
                    local_capture,
                    global_rules,
                    two_char_rules,
                    "HTML格式_Ruby文字_大小调整",
                ).splitlines()
                self.assertEqual(len(reviewed_rendered), len(local_specs))
                reviewed_global = module.orchestrate_comprehensive_esperanto_text_replacement(
                    "\n".join(surface for surface, _signature in local_specs),
                    skip,
                    local_rules,
                    local_capture,
                    global_rules,
                    two_char_rules,
                    "HTML格式_Ruby文字_大小调整",
                ).splitlines()
                self.assertEqual(
                    reviewed_rendered,
                    reviewed_global,
                    f"{language} reviewed @local must reuse exact global HTML",
                )
                for (surface, expected_signature), local_html in zip(
                    local_specs, reviewed_rendered,
                ):
                    actual_signature = tuple(
                        part.casefold()
                        for part in multilingual_structure.structural_signature(
                            local_html
                        )[1:]
                    )
                    self.assertEqual(
                        actual_signature,
                        tuple(expected_signature),
                        f"{language} reviewed @local {surface!r}",
                    )
                hokkaido_marker = {
                    "JA": "[地名]北海道",
                    "ZH": "[地名]北海道",
                    "KO": "[지명]홋카이도",
                }[language]
                for surface in ("hokkajdon", "Hokkajdon", "HOKKAJDON"):
                    index = next(
                        i for i, (candidate, _signature) in enumerate(local_specs)
                        if candidate == surface
                    )
                    self.assertIn(
                        hokkaido_marker,
                        re.sub(
                            r"<br\s*/?>", "", reviewed_rendered[index],
                            flags=re.IGNORECASE,
                        ),
                        f"{language} @local {surface!r} localized gloss",
                    )

                # The guide intentionally gives @kaj@ a broader local gloss;
                # reviewed exact reuse must not flatten it to the global word.
                kaj_local, kaj_global = (
                    module.orchestrate_comprehensive_esperanto_text_replacement(
                        "@kaj@\nkaj",
                        skip,
                        local_rules,
                        local_capture,
                        global_rules,
                        two_char_rules,
                        "HTML格式_Ruby文字_大小调整",
                    ).splitlines()
                )
                self.assertNotEqual(kaj_local, kaj_global, language)
                for word, components in self.REQUIRED_RUBY_COMPONENTS.items():
                    signature = multilingual_structure.structural_signature(rendered_by_word[word])
                    for component in components:
                        self.assertIn(
                            f"R:{component}", signature,
                            f"{language} {word}: {component!r} must be ruby, not literal",
                        )
                for row in corpus_data.REVIEWED_EXACT_MANIFEST["exact_surfaces"]:
                    expected_signature = tuple(
                        ("R:" if span["ruby"] else "L:") + span["text"]
                        for span in row["signature"]["spans"]
                    )
                    self.assertEqual(
                        multilingual_structure.structural_signature(
                            rendered_by_word[row["surface"]]
                        )[1:],
                        expected_signature,
                        f"{language} reviewed typed exact {row['surface']!r}",
                    )
                for row in corpus_data.EXACT_MANIFEST["exact_surfaces"]:
                    expected_signature = tuple(
                        ("R:" if span["ruby"] else "L:") + span["text"]
                        for span in row["signature"]["spans"]
                    )
                    self.assertEqual(
                        multilingual_structure.structural_signature(
                            rendered_by_word[row["surface"]]
                        )[1:],
                        expected_signature,
                        f"{language} extended typed exact {row['surface']!r}",
                    )
                for surface, spec in corpus_data.MANAGED_MORPH_TARGETS.items():
                    self.assertEqual(
                        multilingual_structure.structural_signature(
                            rendered_by_word[surface]
                        )[1:],
                        _target_structural_signature(spec["target"]),
                        f"{language} managed morphology {surface!r}",
                    )
                for surface, expected_signature in {
                    "Dank'": ("R:Dank", "L:'"),
                    "Di'": ("R:Di", "L:'"),
                    "ni'": ("R:ni", "L:'"),
                    "man'": ("R:man", "L:'"),
                    "l'": ("R:l'",),
                    "l'Dio": ("R:l'", "R:Di", "L:o"),
                    "Di’": ("R:Di", "L:’"),
                    "L'": ("R:L'",),
                    "L'Dio": ("R:L'", "R:Di", "L:o"),
                    "l’": ("R:l’",),
                    "l’Dio": ("R:l’", "R:Di", "L:o"),
                    "L’": ("R:L’",),
                    "L’Dio": ("R:L’", "R:Di", "L:o"),
                    "xl'Dio": ("L:xl'", "R:Di", "L:o"),
                    "xl’Dio": ("L:xl’", "R:Di", "L:o"),
                }.items():
                    self.assertEqual(
                        multilingual_structure.structural_signature(
                            rendered_by_word[surface]
                        )[1:],
                        expected_signature,
                        f"{language} Esperanto elision {surface!r}",
                    )
                for lower, upper in (("l'", "L'"), ("l’", "L’")):
                    def normalized_first_rt(surface):
                        match = re.search(
                            r"<rt[^>]*>(.*?)</rt>",
                            rendered_by_word[surface],
                            flags=re.IGNORECASE | re.DOTALL,
                        )
                        self.assertIsNotNone(match, f"{language} {surface}: missing rt")
                        return re.sub(
                            r"<[^>]+>|\s+", "", match.group(1),
                        ).casefold()
                    self.assertEqual(
                        normalized_first_rt(lower),
                        normalized_first_rt(upper),
                        f"{language} {upper}: case variant changed article meaning",
                    )
                self.assertEqual(
                    multilingual_structure.structural_signature(rendered_by_word["golfoflu"])[1:],
                    ("R:golf", "L:o", "R:flu"),
                )
                bikini_html = rendered_by_word["Bikini-Atolo"]
                self.assertRegex(
                    bikini_html,
                    r'<ruby>Bikini<rt[^>]*>.*?</rt></ruby>-'
                    r'<ruby>Atol<rt[^>]*>.*?</rt></ruby>o',
                )
                self.assertRegex(
                    rendered_by_word["Abu-Dabi"],
                    r'Abu-<ruby>Dab<rt[^>]*>.*?</rt></ruby>i',
                )
                for word in ("Kievon", "Mezorienton", "Kamakuron", "Enoŝimon"):
                    signature = multilingual_structure.structural_signature(rendered_by_word[word])
                    self.assertIn("L:on", signature)
                    # Conceptually this is bare grammatical o+n.  It must not
                    # regress to an atomic -o stem ruby followed by bare n.
                    self.assertFalse(any(piece.startswith("R:") and piece.endswith("o") for piece in signature))
                # o+n, a+n and e+n are deliberately adjacent bare grammatical
                # pieces.  The extractor cannot put a slash inside that literal
                # run, so verify the underlying HTML representation directly.
                for word, bare_tail in (("elektron", "on"), ("platan", "an"), ("alten", "en")):
                    self.assertRegex(rendered_by_word[word], rf"</ruby>{bare_tail}\s*(?:<br>)?\s*$")
                # Exact uppercase/mixed-case corpus labels must not leak into
                # ordinary lowercase Esperanto homographs.
                for exact in self.LOWERCASE_HOMOGRAPHS:
                    marker = corpus_data.CASE_SENSITIVE_EXACT_GLOSSES[exact][language.lower()]
                    exact_html = re.sub(r"<br\s*/?>", "", rendered_by_word[exact], flags=re.IGNORECASE)
                    lower_html = re.sub(r"<br\s*/?>", "", rendered_by_word[exact.lower()], flags=re.IGNORECASE)
                    self.assertIn(marker, exact_html)
                    self.assertNotIn(marker, lower_html)
                for exact, glosses in (
                    corpus_data.MANAGED_TYPED_EXACT_GLOSSES.items()
                ):
                    marker = glosses[language.lower()]
                    exact_html = re.sub(
                        r"<br\s*/?>", "", rendered_by_word[exact],
                        flags=re.IGNORECASE,
                    )
                    lower_html = re.sub(
                        r"<br\s*/?>", "", rendered_by_word[exact.lower()],
                        flags=re.IGNORECASE,
                    )
                    self.assertIn(marker, exact_html)
                    self.assertNotIn(marker, lower_html)
                maria_marker = corpus_data.CASE_SENSITIVE_EXACT_GLOSSES["Maria"][language.lower()]
                maria_compound = re.sub(
                    r"<br\s*/?>", "", rendered_by_word["Maria-Virgulino"], flags=re.IGNORECASE
                )
                self.assertIn(maria_marker, maria_compound)
                self.assertNotIn(maria_marker, rendered_by_word["mari-a"])
                self.assertRegex(
                    maria_compound,
                    r'<ruby>Maria<rt[^>]*>.*?</rt></ruby>-'
                    r'<ruby>Virg<rt[^>]*>.*?</rt></ruby>'
                    r'<ruby>ul<rt[^>]*>.*?</rt></ruby>'
                    r'<ruby>in<rt[^>]*>.*?</rt></ruby>o\s*$',
                )
                # Every centrally managed exact surface gets its localized full
                # unit gloss; this automatically covers newly added phrases.
                for surface, glosses in corpus_data.CASE_SENSITIVE_EXACT_GLOSSES.items():
                    rendered_gloss = re.sub(r"<br\s*/?>", "", rendered_by_word[surface], flags=re.IGNORECASE)
                    expected_gloss = re.sub(r"<br\s*/?>", "", glosses[language.lower()], flags=re.IGNORECASE)
                    self.assertIn(expected_gloss, rendered_gloss)
                probe_specs = []
                exact_surfaces = set(corpus_data.CASE_SENSITIVE_EXACT_GLOSSES)
                for surface in exact_surfaces:
                    probe_specs.append((surface, "x" + surface + "y"))
                    lowercase = surface.lower()
                    if lowercase != surface and lowercase not in exact_surfaces:
                        probe_specs.append((surface, lowercase))
                probe_rendered = module.orchestrate_comprehensive_esperanto_text_replacement(
                    "\n".join(f" {probe} " for _, probe in probe_specs),
                    skip, local_rules, local_capture, global_rules, two_char_rules,
                    "HTML格式_Ruby文字_大小调整",
                ).splitlines()
                self.assertEqual(len(probe_rendered), len(probe_specs))
                for (surface, _), probe_html in zip(probe_specs, probe_rendered):
                    marker = corpus_data.CASE_SENSITIVE_EXACT_GLOSSES[surface][language.lower()]
                    normalized_probe = re.sub(r"<br\s*/?>", "", probe_html, flags=re.IGNORECASE)
                    normalized_marker = re.sub(r"<br\s*/?>", "", marker, flags=re.IGNORECASE)
                    self.assertNotIn(normalized_marker, normalized_probe)
                for word in ("UK-oj", "UK-on"):
                    self.assertRegex(
                        rendered_by_word[word],
                        r"</ruby>-(?:oj|on)\s*(?:<br>)?\s*$",
                    )
                # The period is part of this conventional atomic abbreviation.
                self.assertRegex(
                    rendered_by_word["prof."],
                    r"<ruby>prof\.<rt[^>]*>.*?</rt></ruby>\s*(?:<br>)?\s*$",
                )
                for word in ("pat!", "halt!"):
                    self.assertRegex(rendered_by_word[word], r"</ruby>!\s*(?:<br>)?\s*$")
                # Guide exception: the dot of a true abbreviation is inside rb.
                self.assertRegex(
                    rendered_by_word["ekz."],
                    r"<ruby>ekz\.<rt[^>]*>.*?</rt></ruby>\s*(?:<br>)?\s*$",
                )
                del payload, global_rules, local_rules, two_char_rules
                gc.collect()


if __name__ == "__main__":
    unittest.main()
