# -*- coding: utf-8 -*-
"""corpus_vocab_extract.py の全HTML/本文HTMLスコープ境界。"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("corpus_vocab_extract.py")
CONTENT_DIRS = ("lernolibroj", "legajxoj", "revuoj", "rondolegado")


def _run(corpus: Path, out: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--corpus",
            str(corpus),
            "--out",
            str(out),
            *extra,
        ],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )


def _write_html(path: Path, word: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"<html><body><p>{word}</p></body></html>", encoding="utf-8")


class CorpusVocabularyScopeTests(unittest.TestCase):
    def test_default_all_preserves_keys_and_content_scope_excludes_index(self):
        with tempfile.TemporaryDirectory() as temporary:
            tmp_path = Path(temporary)
            corpus = tmp_path / "corpus"
            expected_content_words = set()
            for index, name in enumerate(CONTENT_DIRS):
                word = f"contentword{chr(ord('a') + index)}"
                expected_content_words.add(word)
                _write_html(corpus / name / "sample.html", word)
            _write_html(corpus / "index.html", "technicalindexword")

            all_out = tmp_path / "all.json"
            result = _run(corpus, all_out)
            self.assertEqual(result.returncode, 0, result.stderr)
            all_payload = json.loads(all_out.read_text(encoding="utf-8"))
            self.assertEqual(
                set(all_payload),
                {"files", "words", "capitalized", "freq_top"},
            )
            self.assertEqual(all_payload["files"], 5)
            self.assertEqual(
                set(all_payload["words"]),
                expected_content_words | {"technicalindexword"},
            )

            content_out = tmp_path / "content.json"
            result = _run(corpus, content_out, "--scope", "content")
            self.assertEqual(result.returncode, 0, result.stderr)
            content_payload = json.loads(
                content_out.read_text(encoding="utf-8")
            )
            self.assertEqual(
                set(content_payload),
                {"files", "words", "capitalized", "freq_top"},
            )
            self.assertEqual(content_payload["files"], 4)
            self.assertEqual(
                set(content_payload["words"]), expected_content_words,
            )

    def test_content_scope_fails_closed_when_required_directory_missing(self):
        with tempfile.TemporaryDirectory() as temporary:
            tmp_path = Path(temporary)
            corpus = tmp_path / "corpus"
            for name in CONTENT_DIRS[:-1]:
                _write_html(corpus / name / "sample.html", f"{name}word")

            out = tmp_path / "content.json"
            result = _run(corpus, out, "--scope", "content")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing: rondolegado", result.stderr)
            self.assertFalse(out.exists())

    def test_content_scope_fails_closed_when_required_directory_empty(self):
        with tempfile.TemporaryDirectory() as temporary:
            tmp_path = Path(temporary)
            corpus = tmp_path / "corpus"
            for name in CONTENT_DIRS:
                (corpus / name).mkdir(parents=True)
            for name in CONTENT_DIRS[:-1]:
                _write_html(corpus / name / "sample.html", f"{name}word")

            out = tmp_path / "content.json"
            result = _run(corpus, out, "--scope", "content")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("empty: rondolegado", result.stderr)
            self.assertFalse(out.exists())

    def test_content_scope_fails_closed_when_matched_html_unreadable(self):
        with tempfile.TemporaryDirectory() as temporary:
            tmp_path = Path(temporary)
            corpus = tmp_path / "corpus"
            for name in CONTENT_DIRS:
                _write_html(corpus / name / "sample.html", f"{name}word")
            # A directory whose name ends in .html is returned by glob but
            # cannot be opened as a file on Windows or POSIX.  This exercises
            # read failure without depending on chmod semantics.
            (corpus / CONTENT_DIRS[0] / "unreadable.html").mkdir()

            out = tmp_path / "content.json"
            result = _run(corpus, out, "--scope", "content")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("content HTML could not be read", result.stderr)
            self.assertIn("unreadable.html", result.stderr)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
