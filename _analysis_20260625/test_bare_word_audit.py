# -*- coding: utf-8 -*-
import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("bare_word_audit.py")
SPEC = importlib.util.spec_from_file_location("bare_word_audit", MODULE_PATH)
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class BareWordAuditPolicyTests(unittest.TestCase):
    def scan_fixture_result(self, html):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "fixture.html"
            path.write_text(html, encoding="utf-8")
            original_corpus = AUDIT.CORP
            AUDIT.CORP = root
            try:
                return AUDIT.scan_document(path)
            finally:
                AUDIT.CORP = original_corpus

    def scan_fixture(self, html):
        return self.scan_fixture_result(html)[0]

    def test_unicode_word_tokens_are_not_fragmented(self):
        text = "Oświęcim Universität István L'Espérantiste Китейаŭa"
        self.assertEqual(
            [match.group() for match in AUDIT.WORD_RE.finditer(text)],
            ["Oświęcim", "Universität", "István", "L'Espérantiste", "Китейаŭa"],
        )

    def test_between_ruby_en_is_composite_e_plus_n(self):
        self.assertEqual(
            AUDIT.allowed_attached_kind("en", True, True),
            "internal_composite_e_n",
        )

    def test_leading_en_before_ruby_is_not_exempt(self):
        self.assertIsNone(AUDIT.allowed_attached_kind("en", False, True))

    def test_terminal_en_after_ruby_is_allowed(self):
        self.assertEqual(
            AUDIT.allowed_attached_kind("en", True, False),
            "terminal_ending",
        )

    def test_finite_endings_are_not_bare_exemptions(self):
        for ending in ("as", "is", "os", "us"):
            self.assertIsNone(AUDIT.allowed_attached_kind(ending, True, False))

    def test_excluded_mixed_line_recovers_only_ruby_bearing_segment(self):
        rows = self.scan_fixture(
            '<ruby>La<rt>the</rt></ruby> Qi <ruby>ven<rt>come</rt></ruby>'
            '<ruby>as<rt>present</rt></ruby>.'
            '<br>日本語訳 Tokyo kaj dol<br>\n'
        )
        self.assertEqual([row["token"] for row in rows], ["Qi"])

    def test_ruby_base_evidence_recovers_quoted_cjk_sign_sentence(self):
        rows = self.scan_fixture(
            '<ruby>En<rt>中で</rt></ruby> <ruby>Kore<rt>韓国</rt></ruby>io '
            '<ruby>aper<rt>現れる</rt></ruby><ruby>is<rt>過去</rt></ruby> '
            '<ruby>la<rt>the</rt></ruby> '
            '<ruby>sign<rt>符号</rt></ruby>oj 乭 ( dol, '
            '<ruby>ŝton<rt>石</rt></ruby>o) <ruby>kaj<rt>and</rt></ruby> 畓.'
            '<br>\n'
        )
        self.assertEqual([row["token"] for row in rows], ["dol"])

    def test_scannable_legacy_line_keeps_whole_line_coverage(self):
        rows = self.scan_fixture(
            '<ruby>La<rt>the</rt></ruby> Qi<br>'
            '<ruby>Kaj<rt>and</rt></ruby> Ki<br>\n'
        )
        self.assertEqual([row["token"] for row in rows], ["Qi", "Ki"])

    def test_translation_segment_with_one_ruby_does_not_leak_latin_names(self):
        rows = self.scan_fixture(
            '日本語の翻訳では <ruby>Esperant<rt>エスペラント</rt></ruby>o '
            'Tokyo NASA という表記を説明します。<br>\n'
        )
        self.assertEqual(rows, [])

    def test_multiline_ruby_uses_global_span_and_masks_rt_break(self):
        html = (
            '<ruby>La\n'
            '<rt>the<br>article</rt></ruby> Qi<br>日本語訳 Tokyo<br>\n'
        )
        masked = AUDIT.mask_same_length(html, AUDIT.RUBY_RE)
        second_line = masked.splitlines(keepends=True)[1]
        # Only the two prose <br> boundaries split this line; the reading's
        # <br> is inside the globally masked ruby span.
        meaningful_spans = [
            (start, end)
            for start, end in AUDIT.segment_spans(second_line)
            if second_line[start:end].strip("\x00\r\n ")
        ]
        self.assertEqual(len(meaningful_spans), 2)
        rows = self.scan_fixture(html)
        self.assertEqual(
            [(row["line"], row["token"]) for row in rows],
            [(2, "Qi")],
        )

    def test_reflow_keeps_candidate_multiset_and_attached_counts(self):
        esperanto = " ".join(
            '<ruby>vort<rt>word</rt></ruby>o' for _ in range(20)
        ) + " Qi."
        # One CJK character is deliberately below the old whole-line CJK
        # threshold.  Without segment-first handling the joined form leaked
        # Tokyo/NASA even though the line-per-segment form did not.
        translation = '訳 Tokyo NASA'
        old_rows, old_stats = self.scan_fixture_result(
            esperanto + '<br>\n' + translation + '<br>\n'
        )
        new_rows, new_stats = self.scan_fixture_result(
            esperanto + '<br>' + translation + '<br>\n'
        )
        self.assertEqual(
            [row["token"] for row in old_rows],
            [row["token"] for row in new_rows],
        )
        self.assertEqual([row["token"] for row in new_rows], ["Qi"])
        for key in (
            "attached",
            "attached_internal",
            "attached_terminal",
            "attached_unexpected",
        ):
            self.assertEqual(old_stats[key], new_stats[key], key)


if __name__ == "__main__":
    unittest.main()
