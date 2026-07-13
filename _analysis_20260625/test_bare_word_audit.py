# -*- coding: utf-8 -*-
import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("bare_word_audit.py")
SPEC = importlib.util.spec_from_file_location("bare_word_audit", MODULE_PATH)
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class BareWordAuditPolicyTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
