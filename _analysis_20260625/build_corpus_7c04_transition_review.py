# -*- coding: utf-8 -*-
"""Build and verify the fail-closed Kyoto-corpus b769 -> 7c04 review.

This module is intentionally independent of the app regeneration and
no-worsening implementations.  It reads two *clean local Git checkouts*,
recomputes the transition facts, and compares the resulting JSON value with
the committed review ledger.

The command never fetches, checks out, commits, or pushes anything.

Examples::

    python build_corpus_7c04_transition_review.py \
        --old D:/tmp/corpus-b769 --new D:/tmp/corpus-7c04 --check

    set ESP_CORPUS_OLD_PATH=D:/tmp/corpus-b769
    set ESP_CORPUS_NEW_PATH=D:/tmp/corpus-7c04
    python build_corpus_7c04_transition_review.py --check

``--write`` is deliberately guarded by the same immutable authority checks as
``--check``.  It cannot adopt a different transition merely because a caller
points it at a newer checkout.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import html as htmllib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import unicodedata


HERE = Path(__file__).resolve().parent
DEFAULT_REVIEW = HERE / "_corpus_7c04_transition_review.json"
CONTENT_DIRS = ("lernolibroj", "legajxoj", "revuoj", "rondolegado")
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest().upper()

OLD_HEAD = "b769038ef15346a536ce93721d6f0f46849db0ea"
OLD_TREE = "47995a849c6f06dc536b533642ad6974ddd8586e"
OLD_CONTENT_SHA256 = (
    "264E4217BE484ABC2DC5EF7A22D83C56076C255BFB389F8218A0C215DD2420B6"
)
NEW_HEAD = "7c04f97c51a7cecf88918d2abc2e6bf2f34601a6"
NEW_TREE = "52a92cafc2234eeea5b8d39a3ac0163f47e67462"
NEW_CONTENT_SHA256 = (
    "4F04FD2F3DBE0FC79909CBBEA61ED2848FC093AE2DFE3F0ADEB79882AEB04F52"
)
HTML_PATH_SET_SHA256 = (
    "8D69D6CF4AD403C2F25224F4E0D36A22A28B8BA9B3C238A68A45BC5B7B47A093"
)

RAW_RUBY_OPEN_RE = re.compile(r"<ruby\b", re.IGNORECASE)
RAW_RUBY_CLOSE_RE = re.compile(r"</ruby\s*>", re.IGNORECASE)
RAW_RT_OPEN_RE = re.compile(r"<rt\b", re.IGNORECASE)
RAW_RT_CLOSE_RE = re.compile(r"</rt\s*>", re.IGNORECASE)
RAW_RB_OPEN_RE = re.compile(r"<rb\b", re.IGNORECASE)
RAW_RB_CLOSE_RE = re.compile(r"</rb\s*>", re.IGNORECASE)
RUBY_RE = re.compile(
    r"<ruby\b(?P<ruby_attrs>[^>]*)>\s*(?P<rb>.*?)\s*"
    r"<rt\b(?P<rt_attrs>[^>]*)>(?P<rt>.*?)</rt\s*>\s*</ruby\s*>",
    re.IGNORECASE | re.DOTALL,
)
CLASS_RE = re.compile(
    r"""\bclass\s*=\s*(?P<quote>["'])(?P<value>.*?)(?P=quote)""",
    re.IGNORECASE | re.DOTALL,
)
BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>", re.DOTALL)
BODY_RE = re.compile(r"<body\b", re.IGNORECASE)
SCRIPT_STYLE_RE = re.compile(
    r"<(?:script|style)\b[^>]*>.*?</(?:script|style)\s*>",
    re.IGNORECASE | re.DOTALL,
)
RT_ELEMENT_RE = re.compile(
    r"<rt\b[^>]*>.*?</rt\s*>", re.IGNORECASE | re.DOTALL
)
SPAN_RE = re.compile(
    r"<span\b(?P<attrs>[^>]*)>.*?</span\s*>",
    re.IGNORECASE | re.DOTALL,
)
ALLOWED_RT_CLASSES = frozenset(
    {"XXXS_S", "XXS_S", "XS_S", "S_S", "M_M", "L_L", "XL_L", "XXL_L"}
)


class TransitionReviewError(ValueError):
    """A fail-closed transition invariant was not satisfied."""


class RubyRecord(tuple):
    """Hashable semantic view of one corpus ruby element."""

    __slots__ = ()

    def __new__(cls, rb: str, rt_lines: tuple[str, ...], css_class: str):
        return tuple.__new__(cls, (rb, tuple(rt_lines), css_class))

    @property
    def rb(self) -> str:
        return self[0]

    @property
    def rt_lines(self) -> tuple[str, ...]:
        return self[1]

    @property
    def css_class(self) -> str:
        return self[2]

    def payload(self) -> dict:
        return {
            "rb": self.rb,
            "rt_lines": list(self.rt_lines),
            "class": self.css_class,
        }


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def stable_json_sha256(value) -> str:
    raw = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("ascii")
    return sha256_bytes(raw)


def _run_git(root: Path, *arguments: str, binary: bool = False):
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise TransitionReviewError(
            f"git {' '.join(arguments)} failed for {root}: {stderr}"
        )
    if binary:
        return result.stdout
    return result.stdout.decode("utf-8", errors="strict").strip()


def git_repo_state(root: Path) -> dict:
    root = root.resolve()
    if not root.is_dir():
        raise TransitionReviewError(f"corpus checkout is not a directory: {root}")
    top = Path(_run_git(root, "rev-parse", "--show-toplevel")).resolve()
    if top != root:
        raise TransitionReviewError(
            f"corpus path must be the Git toplevel: supplied={root}, actual={top}"
        )
    status_raw = _run_git(
        root, "status", "--porcelain=v1", "-z", "--untracked-files=all",
        binary=True,
    )
    status_entries = len([entry for entry in status_raw.split(b"\0") if entry])
    if status_entries:
        raise TransitionReviewError(
            f"corpus checkout must be clean: {root} has {status_entries} entries"
        )
    return {
        "head_oid": _run_git(root, "rev-parse", "HEAD"),
        "tree_oid": _run_git(root, "rev-parse", "HEAD^{tree}"),
        "status_entries": status_entries,
        "status_sha256": sha256_bytes(status_raw),
    }


def html_paths(root: Path, *, content_only: bool) -> list[Path]:
    paths: list[Path] = []
    bases = [root / directory for directory in CONTENT_DIRS] if content_only else [root]
    for base in bases:
        if not base.is_dir():
            raise TransitionReviewError(f"missing corpus directory: {base}")
        current = []
        for path in base.rglob("*"):
            if (
                path.is_file()
                and path.suffix.lower() in {".html", ".htm"}
                and ".git" not in path.relative_to(root).parts
            ):
                current.append(path)
        # Match the established manifest builder's Windows Path ordering while
        # remaining reproducible on other hosts.  The Gerda directory contains
        # mixed-case filenames, so a plain POSIX-host sort would change the
        # otherwise identical pinned content fingerprint.
        current.sort(
            key=lambda path: path.relative_to(root).as_posix().casefold()
        )
        paths.extend(current)
    if content_only:
        # This is the established 169-file fingerprint order used by the
        # no-worsening manifests: CONTENT_DIRS order, then path order.
        return paths
    return sorted(set(paths), key=lambda path: path.relative_to(root).as_posix())


def file_fingerprint(root: Path, paths: list[Path]) -> dict:
    rows = [
        (
            path.relative_to(root).as_posix(),
            sha256_bytes(path.read_bytes()),
        )
        for path in paths
    ]
    return {
        "files": len(rows),
        "sha256": stable_json_sha256(rows),
        "rows": rows,
    }


def _normalized_text(raw: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", raw)).strip()


def _one_class_attribute(attrs: str, relative: str, index: int) -> str:
    matches = list(CLASS_RE.finditer(attrs))
    if len(matches) != 1:
        raise TransitionReviewError(
            f"{relative}: ruby #{index} rt must have exactly one class attribute"
        )
    remainder = attrs[:matches[0].start()] + attrs[matches[0].end():]
    if remainder.strip():
        raise TransitionReviewError(
            f"{relative}: ruby #{index} has unsupported rt attributes: "
            f"{remainder.strip()!r}"
        )
    css_class = matches[0].group("value").strip()
    if css_class not in ALLOWED_RT_CLASSES:
        raise TransitionReviewError(
            f"{relative}: ruby #{index} has unsupported class {css_class!r}"
        )
    return css_class


def extract_ruby_records(text: str, relative: str) -> tuple[list[RubyRecord], dict]:
    raw_counts = {
        "ruby_open": len(RAW_RUBY_OPEN_RE.findall(text)),
        "ruby_close": len(RAW_RUBY_CLOSE_RE.findall(text)),
        "rt_open": len(RAW_RT_OPEN_RE.findall(text)),
        "rt_close": len(RAW_RT_CLOSE_RE.findall(text)),
        "rb_open": len(RAW_RB_OPEN_RE.findall(text)),
        "rb_close": len(RAW_RB_CLOSE_RE.findall(text)),
    }
    if (
        raw_counts["ruby_open"] != raw_counts["ruby_close"]
        or raw_counts["rt_open"] != raw_counts["rt_close"]
        or raw_counts["ruby_open"] != raw_counts["rt_open"]
        or raw_counts["rb_open"] != raw_counts["rb_close"]
        or raw_counts["rb_open"] != 0
    ):
        raise TransitionReviewError(
            f"{relative}: malformed or unsupported ruby structure: {raw_counts}"
        )

    records: list[RubyRecord] = []
    for index, match in enumerate(RUBY_RE.finditer(text)):
        if match.group("ruby_attrs").strip():
            raise TransitionReviewError(
                f"{relative}: ruby #{index} has unsupported ruby attributes"
            )
        rb_raw = match.group("rb")
        if TAG_RE.search(rb_raw):
            raise TransitionReviewError(
                f"{relative}: ruby #{index} has nested markup in its base"
            )
        rb = _normalized_text(htmllib.unescape(rb_raw))
        if not rb:
            raise TransitionReviewError(f"{relative}: ruby #{index} has empty base")

        css_class = _one_class_attribute(match.group("rt_attrs"), relative, index)
        rt_with_sentinels = BR_RE.sub("\x02", match.group("rt"))
        if TAG_RE.search(rt_with_sentinels):
            raise TransitionReviewError(
                f"{relative}: ruby #{index} has unsupported rt markup"
            )
        rt_lines = tuple(
            _normalized_text(part)
            for part in htmllib.unescape(rt_with_sentinels).split("\x02")
        )
        if not rt_lines or any(not part for part in rt_lines):
            raise TransitionReviewError(
                f"{relative}: ruby #{index} has an empty rt line"
            )
        records.append(RubyRecord(rb, rt_lines, css_class))

    if len(records) != raw_counts["ruby_open"]:
        raise TransitionReviewError(
            f"{relative}: parsed ruby {len(records)} != raw "
            f"{raw_counts['ruby_open']}"
        )
    return records, raw_counts


def is_latin_word_character(character: str) -> bool:
    if character in "-'’":
        return True
    category = unicodedata.category(character)
    if category.startswith("M"):
        return True
    if not category.startswith("L"):
        return False
    return unicodedata.name(character, "").startswith("LATIN ")


def count_parsed_units(text: str) -> int:
    """Count corpus word units without importing the app/no-worsening code."""
    body_match = BODY_RE.search(text)
    if body_match:
        text = text[body_match.start():]
    text = RUBY_RE.sub(
        lambda match: "\x01" + match.group("rb").strip() + "\x01", text
    )
    text = TAG_RE.sub(" ", text)
    text = htmllib.unescape(text)
    chunks = re.split(r"(\x01.*?\x01)", text, flags=re.DOTALL)
    surface_parts: list[str] = []
    has_ruby = False
    units = 0
    for chunk in chunks:
        if chunk.startswith("\x01") and chunk.endswith("\x01") and len(chunk) >= 2:
            surface_parts.append(chunk[1:-1])
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
                surface_parts.append("".join(token_chars))
                token_chars = []
            if surface_parts and has_ruby and "".join(surface_parts).strip():
                units += 1
            surface_parts = []
            has_ruby = False
        if token_chars:
            surface_parts.append("".join(token_chars))
    if surface_parts and has_ruby and "".join(surface_parts).strip():
        units += 1
    return units


def normalized_visible_body(text: str) -> str:
    """Visible-body text used only to distinguish formatting from content.

    Translation-status badges and newly added sentence-number spans are
    presentation metadata.  ``rt`` is audited independently as RubyRecord.
    Whitespace is formatting for this classification.
    """
    body_match = BODY_RE.search(text)
    if body_match:
        text = text[body_match.start():]
    text = SCRIPT_STYLE_RE.sub("", text)
    text = RT_ELEMENT_RE.sub("", text)

    def drop_presentation_span(match: re.Match) -> str:
        class_match = CLASS_RE.search(match.group("attrs"))
        classes = (
            set(class_match.group("value").split()) if class_match else set()
        )
        return "" if classes.intersection({"tr-tag", "num"}) else match.group(0)

    previous = None
    while previous != text:
        previous = text
        text = SPAN_RE.sub(drop_presentation_span, text)
    text = TAG_RE.sub(" ", text)
    return re.sub(r"\s+", "", unicodedata.normalize(
        "NFC", htmllib.unescape(text)
    ))


def scan_checkout(root: Path) -> dict:
    state = git_repo_state(root)
    all_paths = html_paths(root, content_only=False)
    content_paths = html_paths(root, content_only=True)
    all_fingerprint = file_fingerprint(root, all_paths)
    content_fingerprint = file_fingerprint(root, content_paths)
    content_set = set(content_paths)

    records: dict[str, list[RubyRecord]] = {}
    raw_bytes: dict[str, bytes] = {}
    visible: dict[str, str] = {}
    total_raw_ruby = total_parsed_ruby = total_parsed_units = 0
    total_rt = total_rb = 0
    for path in all_paths:
        relative = path.relative_to(root).as_posix()
        raw = path.read_bytes()
        text = raw.decode("utf-8", errors="strict")
        file_records, raw_counts = extract_ruby_records(text, relative)
        records[relative] = file_records
        raw_bytes[relative] = raw
        visible[relative] = normalized_visible_body(text)
        if path in content_set:
            total_raw_ruby += raw_counts["ruby_open"]
            total_parsed_ruby += len(file_records)
            total_parsed_units += count_parsed_units(text)
            total_rt += raw_counts["rt_open"]
            total_rb += raw_counts["rb_open"]

    return {
        "root": root,
        "state": state,
        "all_paths": [
            path.relative_to(root).as_posix() for path in all_paths
        ],
        "all_fingerprint": all_fingerprint,
        "content_fingerprint": content_fingerprint,
        "records": records,
        "raw_bytes": raw_bytes,
        "visible": visible,
        "content_summary": {
            "files": len(content_paths),
            "content_sha256": content_fingerprint["sha256"],
            "raw_ruby": total_raw_ruby,
            "parsed_ruby": total_parsed_ruby,
            "rt": total_rt,
            "rb": total_rb,
            "parsed_units": total_parsed_units,
        },
    }


def record(rb: str, rt: str, css_class: str) -> RubyRecord:
    return RubyRecord(rb, (rt,), css_class)


# Grouped by path and exact old/new record.  Counts sum to 15.  Keeping this
# path-specific prevents a same-spelling edit in another document from being
# silently accepted.
SPELLING_CHANGES = (
    ("legajxoj/eseoj-kaj-artikoloj/pola_retradio.html",
     record("ŝanĉ", "幸運", "XXL_L"), record("ŝanc", "幸運", "XXL_L"), 1),
    ("legajxoj/eseoj-kaj-artikoloj/pola_retradio.html",
     record("fron", "面する", "M_M"), record("front", "面する", "L_L"), 1),
    ("legajxoj/eseoj-kaj-artikoloj/pola_retradio.html",
     record("lecjon", "レッスン", "M_M"),
     record("lecion", "レッスン", "M_M"), 1),
    ("legajxoj/historio-kaj-biografioj/osakakenji.html",
     record("jurnal", "新聞", "XXL_L"), record("ĵurnal", "新聞", "XXL_L"), 2),
    ("lernolibroj/fujimaki/"
     "Esperanto_meznivela_sola_lernolibro_verkita_de_sro_fujximaki_260215.html",
     record("argent", "銀", "XXL_L"), record("arĝent", "銀", "XXL_L"), 1),
    ("lernolibroj/fujimaki/fujimaki4.html",
     record("argent", "銀", "XXL_L"), record("arĝent", "銀", "XXL_L"), 1),
    ("lernolibroj/fujimaki/"
     "Esperanto_meznivela_sola_lernolibro_verkita_de_sro_fujximaki_260215.html",
     record("pseudonim", "偽名", "XXL_L"),
     record("pseŭdonim", "偽名", "XXL_L"), 1),
    ("lernolibroj/fujimaki/fujimaki10.html",
     record("pseudonim", "偽名", "XXL_L"),
     record("pseŭdonim", "偽名", "XXL_L"), 1),
    ("lernolibroj/fujimaki/"
     "Esperanto_meznivela_sola_lernolibro_verkita_de_sro_fujximaki_260215.html",
     record("adekv", "適切な", "XXL_L"),
     record("adekvat", "適切な", "XXL_L"), 1),
    ("lernolibroj/fujimaki/fujimaki13.html",
     record("adekv", "適切な", "XXL_L"),
     record("adekvat", "適切な", "XXL_L"), 1),
    ("lernolibroj/fujimaki/"
     "Esperanto_meznivela_sola_lernolibro_verkita_de_sro_fujximaki_260215.html",
     record("ŝang", "交換する", "S_S"), record("ŝanĝ", "交換する", "S_S"), 1),
    ("lernolibroj/fujimaki/fujimaki14.html",
     record("ŝang", "交換する", "S_S"), record("ŝanĝ", "交換する", "S_S"), 1),
    ("rondolegado/2026-03/rondolegada_materialoj_202603_enhavoj_JA.html",
     record("distrik", "[政]地区", "L_L"),
     record("distrikt", "[政]地区", "XL_L"), 1),
    ("rondolegado/2026-03/rondolegada_materialoj_202603_enhavoj_KO.html",
     record("distrik", "구역", "XXL_L"),
     record("distrikt", "구역", "XXL_L"), 1),
)

ANNOTATION_CHANGES = (
    ("lernolibroj/fujimaki/"
     "Esperanto_meznivela_sola_lernolibro_verkita_de_sro_fujximaki_260215.html",
     record("Aposterior", "ア・ポステリオリ", "M_M"),
     record("Aposterior", "後天的", "XXL_L"), 1),
    ("lernolibroj/fujimaki/fujimaki10.html",
     record("Aposterior", "ア・ポステリオリ", "M_M"),
     record("Aposterior", "後天的", "XXL_L"), 1),
)

DUPLICATE_PATHS = (
    "rondolegado/2026-03/rondolegada_materialoj_202603_enhavoj_JA.html",
    "rondolegado/2026-03/rondolegada_materialoj_202603_enhavoj_KO.html",
)
DUPLICATE_BLOCK_SIZE = 195


def _record_list_payload(records: list[RubyRecord]) -> list[dict]:
    return [item.payload() for item in records]


def _all_occurrences(haystack: list[RubyRecord], needle: list[RubyRecord]) -> list[int]:
    if not needle:
        raise TransitionReviewError("empty duplicate block")
    first = needle[0]
    length = len(needle)
    return [
        index for index in range(len(haystack) - length + 1)
        if haystack[index] == first
        and haystack[index:index + length] == needle
    ]


def prove_duplicate_transition(
    old_records: list[RubyRecord],
    new_records: list[RubyRecord],
    *,
    block_size: int = DUPLICATE_BLOCK_SIZE,
) -> tuple[list[RubyRecord], list[int], list[int]]:
    candidates = []
    for index in range(len(old_records) - 2 * block_size + 1):
        if old_records[index] != old_records[index + block_size]:
            continue
        left = old_records[index:index + block_size]
        if left == old_records[index + block_size:index + 2 * block_size]:
            old_hits = _all_occurrences(old_records, left)
            new_hits = _all_occurrences(new_records, left)
            if old_hits == [index, index + block_size] and len(new_hits) == 1:
                candidates.append((left, old_hits, new_hits))
    if len(candidates) != 1:
        raise TransitionReviewError(
            f"expected exactly one adjacent {block_size}-ruby 2->1 duplicate, "
            f"found {len(candidates)}"
        )
    return candidates[0]


def _change_payload(path: str, old: RubyRecord, new: RubyRecord, count: int) -> dict:
    return {
        "path": path,
        "old": old.payload(),
        "new": new.payload(),
        "count": count,
    }


def _counter_delta(
    old_records: list[RubyRecord], new_records: list[RubyRecord]
) -> tuple[collections.Counter, collections.Counter]:
    old_counter = collections.Counter(old_records)
    new_counter = collections.Counter(new_records)
    return old_counter - new_counter, new_counter - old_counter


def build_transition_review(old_root: Path, new_root: Path) -> dict:
    old = scan_checkout(old_root.resolve())
    new = scan_checkout(new_root.resolve())

    old_paths = set(old["all_paths"])
    new_paths = set(new["all_paths"])
    added = sorted(new_paths - old_paths)
    removed = sorted(old_paths - new_paths)
    old_hashes = dict(old["all_fingerprint"]["rows"])
    new_hashes = dict(new["all_fingerprint"]["rows"])
    renamed = []
    for old_path in list(removed):
        matches = [
            new_path for new_path in added
            if old_hashes[old_path] == new_hashes[new_path]
        ]
        if len(matches) == 1:
            renamed.append({"old": old_path, "new": matches[0]})

    duplicate_reviews = []
    duplicate_blocks: dict[str, list[RubyRecord]] = {}
    for path in DUPLICATE_PATHS:
        block, old_hits, new_hits = prove_duplicate_transition(
            old["records"][path], new["records"][path]
        )
        duplicate_blocks[path] = block
        duplicate_reviews.append({
            "path": path,
            "ruby_records": len(block),
            "old_occurrences": len(old_hits),
            "new_occurrences": len(new_hits),
            "old_start_indices_zero_based": old_hits,
            "new_start_indices_zero_based": new_hits,
            "record_block_sha256": stable_json_sha256(
                _record_list_payload(block)
            ),
            "rb_sequence_sha256": stable_json_sha256(
                [item.rb for item in block]
            ),
            "first_rb": [item.rb for item in block[:5]],
            "last_rb": [item.rb for item in block[-5:]],
            "old_file_sha256": sha256_bytes(old["raw_bytes"][path]),
            "new_file_sha256": sha256_bytes(new["raw_bytes"][path]),
        })

    expected_removed: dict[str, collections.Counter] = collections.defaultdict(
        collections.Counter
    )
    expected_added: dict[str, collections.Counter] = collections.defaultdict(
        collections.Counter
    )
    for path, old_record, new_record, count in (
        SPELLING_CHANGES + ANNOTATION_CHANGES
    ):
        expected_removed[path][old_record] += count
        expected_added[path][new_record] += count
    for path, block in duplicate_blocks.items():
        expected_removed[path].update(block)

    actual_removed_total = actual_added_total = 0
    unexplained_removed = unexplained_added = 0
    counter_changed_paths = []
    sequence_changed_paths = []
    for path in sorted(old_paths | new_paths):
        old_records = old["records"].get(path, [])
        new_records = new["records"].get(path, [])
        if old_records != new_records:
            sequence_changed_paths.append(path)
        actual_removed, actual_added = _counter_delta(old_records, new_records)
        if actual_removed or actual_added:
            counter_changed_paths.append(path)
        actual_removed_total += sum(actual_removed.values())
        actual_added_total += sum(actual_added.values())
        residual_removed = actual_removed - expected_removed[path]
        residual_added = actual_added - expected_added[path]
        missing_removed = expected_removed[path] - actual_removed
        missing_added = expected_added[path] - actual_added
        unexplained_removed += sum(residual_removed.values()) + sum(
            missing_removed.values()
        )
        unexplained_added += sum(residual_added.values()) + sum(
            missing_added.values()
        )

    categories = {
        "byte_identical": [],
        "format_order_preserved": [],
        "reorder_multiset_preserved": [],
        "reviewed_content_delta": [],
    }
    for path in sorted(old_paths | new_paths):
        old_raw = old["raw_bytes"].get(path)
        new_raw = new["raw_bytes"].get(path)
        old_visible = old["visible"].get(path, "")
        new_visible = new["visible"].get(path, "")
        if old_raw == new_raw:
            category = "byte_identical"
        elif old_visible == new_visible:
            category = "format_order_preserved"
        elif collections.Counter(old_visible) == collections.Counter(new_visible):
            category = "reorder_multiset_preserved"
        else:
            category = "reviewed_content_delta"
        categories[category].append(path)

    category_payload = {
        key: {
            "files": len(paths),
            "path_list_sha256": stable_json_sha256(paths),
        }
        for key, paths in categories.items()
    }
    category_payload["reviewed_content_delta"]["paths"] = (
        categories["reviewed_content_delta"]
    )

    spelling_payload = [
        _change_payload(path, old_record, new_record, count)
        for path, old_record, new_record, count in SPELLING_CHANGES
    ]
    annotation_payload = [
        _change_payload(path, old_record, new_record, count)
        for path, old_record, new_record, count in ANNOTATION_CHANGES
    ]
    spelling_kinds = sorted({
        (entry["old"]["rb"], entry["new"]["rb"])
        for entry in spelling_payload
    })

    old_source = {
        **old["state"],
        "all_html_files": len(old["all_paths"]),
        "html_path_set_sha256": stable_json_sha256(old["all_paths"]),
        **old["content_summary"],
    }
    new_source = {
        **new["state"],
        "all_html_files": len(new["all_paths"]),
        "html_path_set_sha256": stable_json_sha256(new["all_paths"]),
        **new["content_summary"],
    }

    return {
        "schema_version": 1,
        "description": (
            "Independent fail-closed review of Kyoto HTML corpus "
            "b769038 -> 7c04f97."
        ),
        "normalization": {
            "hash": (
                "SHA-256 uppercase over JSON ensure_ascii=true, "
                "sort_keys=true, separators=(',', ':')"
            ),
            "ruby_record": "NFC(rb), NFC rt lines split at <br>, exact CSS class",
            "visible_body": (
                "NFC; remove head/script/style/rt, tr-tag and num spans, "
                "HTML tags and whitespace"
            ),
        },
        "source": {"old": old_source, "new": new_source},
        "file_set": {
            "added": added,
            "removed": removed,
            "renamed": sorted(renamed, key=lambda row: (row["old"], row["new"])),
        },
        "classification": category_payload,
        "ruby_transition": {
            "old_ruby": old_source["raw_ruby"],
            "new_ruby": new_source["raw_ruby"],
            "ruby_delta": new_source["raw_ruby"] - old_source["raw_ruby"],
            "old_parsed_units": old_source["parsed_units"],
            "new_parsed_units": new_source["parsed_units"],
            "parsed_units_delta": (
                new_source["parsed_units"] - old_source["parsed_units"]
            ),
            "record_counter_removed": actual_removed_total,
            "record_counter_added": actual_added_total,
            "sequence_changed_files": len(sequence_changed_paths),
            "sequence_changed_path_list_sha256": stable_json_sha256(
                sequence_changed_paths
            ),
            "counter_changed_files": len(counter_changed_paths),
            "counter_changed_path_list_sha256": stable_json_sha256(
                counter_changed_paths
            ),
            "duplicate_removal": {
                "files": len(duplicate_reviews),
                "ruby_records_per_file": DUPLICATE_BLOCK_SIZE,
                "removed_ruby_total": sum(
                    row["ruby_records"]
                    * (row["old_occurrences"] - row["new_occurrences"])
                    for row in duplicate_reviews
                ),
                "rows": duplicate_reviews,
            },
            "spelling_corrections": {
                "kinds": len(spelling_kinds),
                "instances": sum(row["count"] for row in spelling_payload),
                "path_rows": len(spelling_payload),
                "rows_sha256": stable_json_sha256(spelling_payload),
                "rows": spelling_payload,
            },
            "annotation_corrections": {
                "kinds": 1,
                "instances": sum(row["count"] for row in annotation_payload),
                "path_rows": len(annotation_payload),
                "rows_sha256": stable_json_sha256(annotation_payload),
                "rows": annotation_payload,
            },
            "boundary_only_changes": 0,
            "unexplained_removed_records": unexplained_removed,
            "unexplained_added_records": unexplained_added,
        },
        "gate": {
            "clean_checkouts": (
                old_source["status_entries"] == 0
                and new_source["status_entries"] == 0
            ),
            "same_html_path_set": old["all_paths"] == new["all_paths"],
            "ruby_fully_parsed": (
                old_source["raw_ruby"] == old_source["parsed_ruby"]
                and new_source["raw_ruby"] == new_source["parsed_ruby"]
            ),
            "no_rb_elements": old_source["rb"] == new_source["rb"] == 0,
            "no_unexplained_record_delta": (
                unexplained_removed == unexplained_added == 0
            ),
            "pass": False,
        },
    }


def authority_projection(review: dict) -> dict:
    source = review["source"]
    ruby = review["ruby_transition"]
    classification = review["classification"]
    return {
        "old": source["old"],
        "new": source["new"],
        "file_set": review["file_set"],
        "classification": classification,
        "record_counter_removed": ruby["record_counter_removed"],
        "record_counter_added": ruby["record_counter_added"],
        "sequence_changed_files": ruby["sequence_changed_files"],
        "sequence_changed_path_list_sha256": (
            ruby["sequence_changed_path_list_sha256"]
        ),
        "counter_changed_files": ruby["counter_changed_files"],
        "counter_changed_path_list_sha256": (
            ruby["counter_changed_path_list_sha256"]
        ),
        "duplicate_removal": ruby["duplicate_removal"],
        "spelling_corrections": ruby["spelling_corrections"],
        "annotation_corrections": ruby["annotation_corrections"],
        "boundary_only_changes": ruby["boundary_only_changes"],
        "unexplained_removed_records": ruby["unexplained_removed_records"],
        "unexplained_added_records": ruby["unexplained_added_records"],
        "gates_without_pass": {
            key: value for key, value in review["gate"].items() if key != "pass"
        },
    }


# Populated from the independently recomputed fixed snapshots.  It is kept in
# code as a second authority so ``--write`` cannot bless arbitrary movement.
EXPECTED_AUTHORITY = {
    "old_head_oid": OLD_HEAD,
    "old_tree_oid": OLD_TREE,
    "old_content_sha256": OLD_CONTENT_SHA256,
    "new_head_oid": NEW_HEAD,
    "new_tree_oid": NEW_TREE,
    "new_content_sha256": NEW_CONTENT_SHA256,
    "html_path_set_sha256": HTML_PATH_SET_SHA256,
    "all_html_files": 172,
    "content_files": 169,
    "old_raw_ruby": 348971,
    "new_raw_ruby": 348581,
    "old_parsed_units": 271065,
    "new_parsed_units": 270763,
    "record_counter_removed": 407,
    "record_counter_added": 17,
    "duplicate_removed": 390,
    "spelling_instances": 15,
    "spelling_kinds": 9,
    "annotation_instances": 2,
    "boundary_only_changes": 0,
    "unexplained_removed": 0,
    "unexplained_added": 0,
    "classification_counts": {
        "byte_identical": 24,
        "format_order_preserved": 110,
        "reorder_multiset_preserved": 29,
        "reviewed_content_delta": 9,
    },
}


def validate_authority(review: dict) -> None:
    if review.get("schema_version") != 1:
        raise TransitionReviewError("unsupported transition review schema")
    source = review["source"]
    ruby = review["ruby_transition"]
    actual = {
        "old_head_oid": source["old"]["head_oid"],
        "old_tree_oid": source["old"]["tree_oid"],
        "old_content_sha256": source["old"]["content_sha256"],
        "new_head_oid": source["new"]["head_oid"],
        "new_tree_oid": source["new"]["tree_oid"],
        "new_content_sha256": source["new"]["content_sha256"],
        "html_path_set_sha256": source["new"]["html_path_set_sha256"],
        "all_html_files": source["new"]["all_html_files"],
        "content_files": source["new"]["files"],
        "old_raw_ruby": source["old"]["raw_ruby"],
        "new_raw_ruby": source["new"]["raw_ruby"],
        "old_parsed_units": source["old"]["parsed_units"],
        "new_parsed_units": source["new"]["parsed_units"],
        "record_counter_removed": ruby["record_counter_removed"],
        "record_counter_added": ruby["record_counter_added"],
        "duplicate_removed": ruby["duplicate_removal"]["removed_ruby_total"],
        "spelling_instances": ruby["spelling_corrections"]["instances"],
        "spelling_kinds": ruby["spelling_corrections"]["kinds"],
        "annotation_instances": ruby["annotation_corrections"]["instances"],
        "boundary_only_changes": ruby["boundary_only_changes"],
        "unexplained_removed": ruby["unexplained_removed_records"],
        "unexplained_added": ruby["unexplained_added_records"],
        "classification_counts": {
            key: value["files"]
            for key, value in review["classification"].items()
        },
    }
    if actual != EXPECTED_AUTHORITY:
        raise TransitionReviewError(
            "transition does not match immutable b769->7c04 authority: "
            + first_difference(EXPECTED_AUTHORITY, actual)
        )
    if source["old"]["html_path_set_sha256"] != HTML_PATH_SET_SHA256:
        raise TransitionReviewError("old HTML path-set authority mismatch")
    if source["old"]["all_html_files"] != 172 or source["old"]["files"] != 169:
        raise TransitionReviewError("old HTML scope authority mismatch")
    if source["old"]["status_sha256"] != EMPTY_SHA256:
        raise TransitionReviewError("old checkout is not clean")
    if source["new"]["status_sha256"] != EMPTY_SHA256:
        raise TransitionReviewError("new checkout is not clean")
    if review["file_set"] != {"added": [], "removed": [], "renamed": []}:
        raise TransitionReviewError("HTML file set changed")
    failed_gates = [
        key for key, value in review["gate"].items()
        if key != "pass" and value is not True
    ]
    if failed_gates:
        raise TransitionReviewError(
            f"transition gates failed: {', '.join(failed_gates)}"
        )


def first_difference(expected, actual, path: str = "$") -> str:
    if type(expected) is not type(actual):
        return (
            f"{path}: type {type(expected).__name__} != "
            f"{type(actual).__name__}"
        )
    if isinstance(expected, dict):
        if set(expected) != set(actual):
            return (
                f"{path}: keys {sorted(expected)} != {sorted(actual)}"
            )
        for key in expected:
            if expected[key] != actual[key]:
                return first_difference(expected[key], actual[key], f"{path}.{key}")
        return f"{path}: unknown dict difference"
    if isinstance(expected, list):
        if len(expected) != len(actual):
            return f"{path}: list length {len(expected)} != {len(actual)}"
        for index, (left, right) in enumerate(zip(expected, actual)):
            if left != right:
                return first_difference(left, right, f"{path}[{index}]")
        return f"{path}: unknown list difference"
    return f"{path}: expected {expected!r}, got {actual!r}"


def require_review_match(expected: dict, actual: dict) -> None:
    if expected != actual:
        raise TransitionReviewError(
            "recomputed transition differs from committed ledger: "
            + first_difference(expected, actual)
        )


def finalized_review(review: dict) -> dict:
    validate_authority(review)
    result = json.loads(json.dumps(review, ensure_ascii=False))
    result["gate"]["pass"] = True
    return result


def atomic_json_dump(path: Path, value: dict) -> None:
    temporary = path.with_name(path.name + ".tmp_atomic_write")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=1)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def resolve_checkout(
    cli_value: Path | None, environment_name: str
) -> Path:
    raw = str(cli_value) if cli_value is not None else os.environ.get(environment_name)
    if not raw:
        raise TransitionReviewError(
            f"provide --{'old' if 'OLD' in environment_name else 'new'} "
            f"or set {environment_name}"
        )
    return Path(raw).expanduser().resolve()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old", type=Path, help="clean checkout at b769038")
    parser.add_argument("--new", type=Path, help="clean checkout at 7c04f97")
    parser.add_argument(
        "--review", type=Path, default=DEFAULT_REVIEW,
        help="committed transition-review JSON",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="verify ledger (default)")
    mode.add_argument("--write", action="store_true", help="atomically write ledger")
    args = parser.parse_args(argv)

    try:
        old_root = resolve_checkout(args.old, "ESP_CORPUS_OLD_PATH")
        new_root = resolve_checkout(args.new, "ESP_CORPUS_NEW_PATH")
        review = finalized_review(build_transition_review(old_root, new_root))
        if args.write:
            atomic_json_dump(args.review, review)
            print(f"WROTE verified transition review: {args.review}")
        else:
            committed = json.loads(args.review.read_text(encoding="utf-8"))
            validate_authority(committed)
            if committed.get("gate", {}).get("pass") is not True:
                raise TransitionReviewError("committed ledger gate.pass is not true")
            require_review_match(committed, review)
            print(
                "PASS corpus transition b769038->7c04f97: "
                "172 paths, 169 content files, ruby -390, "
                "spelling 15, annotation 2, unexplained 0"
            )
        return 0
    except (
        OSError, UnicodeError, json.JSONDecodeError, TransitionReviewError
    ) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
