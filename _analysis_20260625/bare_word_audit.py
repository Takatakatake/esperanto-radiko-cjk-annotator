# -*- coding: utf-8 -*-
"""京大エス研HTMLの注釈coverage監査。

語根境界監査はruby付き語だけを扱うため、本文中に丸ごと裸で残った語を
別レイヤーで検査する。本スクリプトは次を明示的に分離する。

* 全169本文HTMLのうち、注釈対象123文書
* navigation/index 17、Gerda plain-source 28、bilingual plain-source 1
* rubyに隣接する正当な文法語尾
* URL、翻訳・注記、外国語原文ブロック
* 注釈対象本文に残るエスペラント語・固有名・略語候補

通常実行:
    python _analysis_20260625/bare_word_audit.py
gate付き:
    python _analysis_20260625/bare_word_audit.py --require-zero

通常モードは修正を行わない。``--propose-rules`` などの提案モードと
``--apply-bulk`` は、確認済みの完全一致置換を行う内部補助モードである。

除外票 ``_bare_word_reviewed.json`` は schema_version 2 とし、各項目を
``path + token + lines`` で限定する。ワイルドカードは禁止し、記録した全行が
実際に候補を含むこと、かつ実出現数が ``expected_count`` と一致することも
coverage gate の一部として検査する。
"""
from __future__ import annotations

import argparse
import base64
import collections
import html as htmllib
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(__file__).resolve().parents[1]
CORP = Path(os.environ.get(
    "ESP_CORPUS_PATH",
    BASE / "_project_root_misc" / "京大エス研html文書＿Github",
))
CONTENT_DIRS = ("lernolibroj", "legajxoj", "revuoj", "rondolegado")
OUT = BASE / "_analysis_20260625" / "out" / "_audit_annotation_coverage.json"
REVIEWED = BASE / "_analysis_20260625" / "_bare_word_reviewed.json"
VERIFIER = CORP / "esperanto_html_redaktado" / "ruby_css_verifier.py"

RUBY_RE = re.compile(
    r'<ruby\b[^>]*>\s*(?P<rb>[^<]+?)\s*'
    r'<rt\b[^>]*>.*?</rt\s*>\s*</ruby\s*>',
    re.IGNORECASE | re.DOTALL,
)
TAG_RE = re.compile(r"<[^>]+>", re.DOTALL)
# Full Unicode-letter tokens.  Latin Extended is needed for names such as
# Oświęcim/István/Universität; Cyrillic is needed so a mixed title such as
# Китейаŭa is not reduced to the meaningless fragment ``ŭa``.  CJK is
# deliberately absent.  Apostrophes and hyphens are allowed only internally.
NON_CJK_LETTER = r"A-Za-z\u00c0-\u024f\u1e00-\u1eff\u0400-\u052f"
LETTER_UNIT = rf"[{NON_CJK_LETTER}][\u0300-\u036f]*"
WORD_RE = re.compile(
    rf"(?:{LETTER_UNIT})+(?:[-\u2010\u2011'\u2019\u02bc](?:{LETTER_UNIT})+)*"
)
URL_RE = re.compile(
    r"(?:https?://|www\.)[^\s<>]+|\b[^\s<>]+\.(?:com|org|net|jp|html?)(?:/[^\s<>]*)?",
    re.IGNORECASE,
)
HEAD_SCRIPT_STYLE_RE = re.compile(
    r"<(head|script|style|nav|header|footer|aside)\b[^>]*>.*?</\1\s*>", re.IGNORECASE | re.DOTALL
)
CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]")
NON_CJK_LETTER_RE = re.compile(rf"[{NON_CJK_LETTER}]")

MUST_FUNCTION = {
    "la", "kaj", "de", "en", "al", "el", "por", "kun", "pri", "pro", "per",
    "sur", "sub", "ĉe", "ĝis", "dum", "laŭ", "post", "inter", "kontraŭ", "tra",
    "trans", "sen", "je", "da", "do", "ja", "jes", "ne", "nur", "ankaŭ",
    "ankoraŭ", "jam", "tuj", "eĉ", "tre", "tro", "pli", "plej", "plu", "ol",
    "se", "ke", "ĉu", "ĉar", "sed", "aŭ", "nek", "mi", "vi", "li", "ŝi", "ĝi",
    "ni", "ili", "oni", "si", "unu", "du", "tri", "kvar", "kvin", "ses", "sep",
    "ok", "naŭ", "dek",
}
GRAMMAR_ENDINGS = {
    "a", "e", "i", "o", "u", "j", "n", "aj", "an", "en", "oj", "on", "jn",
    "ajn", "ojn", "ian", "ion", "io", "ia", "iaj", "iajn",
}
# Only these endings are intentionally bare even *between* two annotated
# roots.  Longer endings are permitted solely as a terminal suffix after a
# ruby; treating an/on/en/io/ia as position-independent would hide roots.
ALWAYS_BARE_INTERNAL = {"o", "a", "e", "i", "n", "j", "jn"}
# Between two roots, literal ``en`` in forms such as supr-en-ir and
# antaŭ-en-ig represents the two bare grammatical endings e+n, not root en.
# This exception is position-specific: leading ``en<ruby>...`` remains an
# unexpected candidate and therefore still detects a genuine missing en root.
INTERNAL_COMPOSITE_BARE = {"en"}
# Corpus-wide empirical invariant: infinitive/imperative and nominal endings
# are intentionally outside ruby, whereas all finite/conditional verb endings
# are ruby-annotated.  Do not add i/u here (8,356/1,739 legitimate bare uses).
ANNOTATED_FINITE_ENDINGS = {"as", "is", "os", "us"}
ATTACHED_WATCH_TOKENS = {"an", "on", "en", "io", "ia"}
METADATA_WORDS = {
    "category", "categories", "source", "photo", "id", "page", "pages",
    "en", "ja", "ko", "eo", "p", "pp", "http", "https", "www",
}
FOREIGN_COMMON = {
    "the", "and", "or", "to", "of", "for", "from", "by", "with", "is", "are",
    "was", "were", "be", "as", "at", "in", "it", "its", "that", "this", "when",
    "who", "said", "on", "a", "an", "not", "but", "have", "has", "had", "will",
}
ENDS = ("ojn", "ajn", "oj", "aj", "on", "an", "en", "as", "is", "os", "us", "jn", "o", "a", "e", "i", "u", "j", "n")


def relpath(path: Path) -> str:
    return path.relative_to(CORP).as_posix()


def iter_html():
    for dirname in CONTENT_DIRS:
        root = CORP / dirname
        if root.is_dir():
            yield from root.rglob("*.html")


def zero_ruby_exclusion(path: Path) -> str:
    name = path.name.lower()
    rel = relpath(path).lower()
    if name.startswith("index"):
        return "navigation/index"
    if "gerda_malaperis_txt" in rel or name.endswith("_txt.html"):
        return "plain-source/Gerda"
    if name == "vere_aux_fantazie_du-lingva.html":
        return "plain-source/bilingual"
    return "UNEXPECTED_zero_ruby"


def mask_same_length(text: str, regex: re.Pattern) -> str:
    """Mask matches without changing offsets or line numbers."""
    chars = list(text)
    for match in regex.finditer(text):
        for i in range(match.start(), match.end()):
            if chars[i] not in "\r\n":
                chars[i] = "\x00"
    return "".join(chars)


def line_offsets(text: str):
    offset = 0
    for number, line in enumerate(text.splitlines(keepends=True), 1):
        yield number, offset, line
        offset += len(line)
    if not text:
        return
    if offset < len(text):
        yield number + 1, offset, text[offset:]


def load_stems():
    path = BASE / "Esperanto-Kanji-Ruby-JA" / "app_data" / "E_stem.json"
    data = json.load(open(path, encoding="utf-8"))
    stems = set()
    for entry in data:
        stem = entry[0] if isinstance(entry, list) else entry
        stems.add(str(stem).replace("/", "").lower())
    return stems


STEMS = load_stems()


def is_esperanto(word: str) -> bool:
    lower = word.lower()
    if lower in MUST_FUNCTION or lower in STEMS:
        return True
    for ending in ENDS:
        if lower.endswith(ending) and len(lower) - len(ending) >= 2 and lower[:-len(ending)] in STEMS:
            return True
    return False


def allowed_attached_kind(lower: str, before_ruby: bool, after_ruby: bool):
    """Return the narrowly permitted bare-morphology position, or None."""
    if before_ruby and after_ruby:
        if lower in ALWAYS_BARE_INTERNAL:
            return "internal_single_ending"
        if lower in INTERNAL_COMPOSITE_BARE:
            return "internal_composite_e_n"
        return None
    if before_ruby and not after_ruby and lower in GRAMMAR_ENDINGS:
        return "terminal_ending"
    # Material immediately before a ruby is never exempted by spelling alone.
    return None


def visible_line(masked_line: str) -> str:
    # Existing ruby is already NUL-masked; tags can now be removed safely.
    return htmllib.unescape(TAG_RE.sub(" ", masked_line))


def classify_line(visible: str, has_ruby: bool):
    cjk_count = len(CJK_RE.findall(visible))
    latin_count = len(NON_CJK_LETTER_RE.findall(visible))
    raw_tokens = [m.group() for m in WORD_RE.finditer(visible.replace("\x00", " "))]
    lowercase_lexical = [
        w for w in raw_tokens
        if len(w) >= 2 and w[0].islower()
        and w.lower() not in FOREIGN_COMMON | METADATA_WORDS | GRAMMAR_ENDINGS
        and not is_esperanto(w)
    ]
    esp_tokens = sum(1 for w in raw_tokens if is_esperanto(w))
    if cjk_count >= 2 and cjk_count > latin_count * 0.08:
        return "translation_or_note"
    if has_ruby:
        if len(lowercase_lexical) >= 4:
            return "foreign_source_block"
        return "annotated_body"
    if raw_tokens and esp_tokens / len(raw_tokens) >= 0.60:
        return "plain_line_in_annotated_document"
    return "non_annotation_block"


def mask_urls(line: str) -> tuple[str, int]:
    chars = list(line)
    count = 0
    for match in URL_RE.finditer(line):
        count += 1
        for i in range(match.start(), match.end()):
            if chars[i] not in "\r\n":
                chars[i] = "\x00"
    return "".join(chars), count


def scan_document(path: Path):
    raw = path.read_text(encoding="utf-8", errors="ignore")
    ruby_matches = list(RUBY_RE.finditer(raw))
    if not ruby_matches:
        return [], {
            "raw_ruby": 0, "url_spans": 0, "attached": 0,
            "attached_internal": 0, "attached_terminal": 0,
            "attached_unexpected": 0, "attached_watch": {}, "line_classes": {},
        }
    masked = mask_same_length(raw, HEAD_SCRIPT_STYLE_RE)
    masked = mask_same_length(masked, RUBY_RE)
    occurrences = []
    url_spans = attached = attached_internal = attached_terminal = attached_unexpected = 0
    attached_watch = collections.Counter()
    line_classes = collections.Counter()
    raw_lines = raw.splitlines(keepends=True)
    ruby_index = 0
    for (line_no, offset, line), raw_line in zip(line_offsets(masked), raw_lines):
        raw_line_start, raw_line_end = offset, offset + len(raw_line)
        while ruby_index < len(ruby_matches) and ruby_matches[ruby_index].end() <= raw_line_start:
            ruby_index += 1
        has_ruby = (
            ruby_index < len(ruby_matches)
            and ruby_matches[ruby_index].start() < raw_line_end
            and ruby_matches[ruby_index].end() > raw_line_start
        )
        vis = visible_line(line)
        vis, n_urls = mask_urls(vis)
        url_spans += n_urls
        line_class = classify_line(vis, has_ruby)
        line_classes[line_class] += 1
        if line_class not in {"annotated_body", "plain_line_in_annotated_document"}:
            continue
        for match in WORD_RE.finditer(vis):
            token = match.group()
            before = vis[match.start() - 1] if match.start() else ""
            after = vis[match.end()] if match.end() < len(vis) else ""
            lower = token.lower()
            before_ruby = before == "\x00"
            after_ruby = after == "\x00"
            is_attached = before_ruby or after_ruby
            if is_attached and lower in ATTACHED_WATCH_TOKENS:
                position = (
                    "between_rubies" if before_ruby and after_ruby
                    else "after_ruby_terminal" if before_ruby
                    else "before_ruby"
                )
                attached_watch[f"{lower}:{position}"] += 1
            allowed_kind = allowed_attached_kind(lower, before_ruby, after_ruby)
            allowed_internal = allowed_kind in {
                "internal_single_ending", "internal_composite_e_n",
            }
            allowed_terminal = allowed_kind == "terminal_ending"
            if is_attached and (allowed_internal or allowed_terminal):
                attached += 1
                attached_internal += int(allowed_internal)
                attached_terminal += int(allowed_terminal)
                continue
            if not is_attached and (len(token) == 1 or lower in GRAMMAR_ENDINGS | METADATA_WORDS):
                continue
            candidate_kind = None
            if is_attached:
                # Unexpected attached material must be visible even when it is
                # not in the Esperanto stem list.  This catches both missing
                # as/is/os/us rubies and a-Litovia-style hyphenated omissions.
                attached_unexpected += 1
                candidate_kind = (
                    "attached_finite_ending_omission"
                    if lower in ANNOTATED_FINITE_ENDINGS
                    else "attached_unexpected_token"
                )
            elif token[0].isupper() or token.isupper():
                candidate_kind = "proper_or_acronym"
            elif is_esperanto(token):
                candidate_kind = "esperanto_word"
            if candidate_kind is None:
                continue
            occurrences.append({
                "path": relpath(path),
                "line": line_no,
                "token": token,
                "kind": candidate_kind,
                "line_class": line_class,
                "context": re.sub(
                    r"\s+", " ", re.sub(r"\x00+", "[R]", vis)
                ).strip()[:500],
            })
    return occurrences, {
        "raw_ruby": len(RUBY_RE.findall(raw)),
        "url_spans": url_spans,
        "attached": attached,
        "attached_internal": attached_internal,
        "attached_terminal": attached_terminal,
        "attached_unexpected": attached_unexpected,
        "attached_watch": dict(attached_watch),
        "line_classes": dict(line_classes),
    }


def load_reviewed():
    """Load exact, line-scoped review entries.

    A review decision is deliberately unable to match the same token on a new line.
    This prevents a previously reviewed quotation/nav label from hiding a later true
    annotation omission.
    """
    if not REVIEWED.is_file():
        return {}, {"schema_version": 2, "entries": []}, []
    data = json.load(open(REVIEWED, encoding="utf-8"))
    if data.get("schema_version") != 2:
        raise ValueError("reviewed coverage requires schema_version 2")
    if not isinstance(data.get("entries"), list):
        raise ValueError("reviewed coverage entries must be a list")

    index = {}
    normalized_entries = []
    for entry_id, entry in enumerate(data["entries"]):
        if "paths" in entry:
            raise ValueError(f"review entry {entry_id}: legacy 'paths' is prohibited")
        path = entry.get("path")
        token = entry.get("token")
        lines = entry.get("lines")
        expected = entry.get("expected_count")
        if not isinstance(path, str) or not path or path == "*":
            raise ValueError(f"review entry {entry_id}: exact non-wildcard path required")
        path = path.replace("\\", "/")
        if not isinstance(token, str) or not token:
            raise ValueError(f"review entry {entry_id}: non-empty token required")
        if (
            not isinstance(lines, list)
            or not lines
            or any(not isinstance(line, int) or isinstance(line, bool) or line < 1 for line in lines)
            or len(lines) != len(set(lines))
        ):
            raise ValueError(f"review entry {entry_id}: unique positive integer lines required")
        if not isinstance(expected, int) or isinstance(expected, bool) or expected < 1:
            raise ValueError(f"review entry {entry_id}: positive integer expected_count required")
        if not isinstance(entry.get("category"), str) or not entry["category"]:
            raise ValueError(f"review entry {entry_id}: category required")
        if not isinstance(entry.get("reason"), str) or not entry["reason"]:
            raise ValueError(f"review entry {entry_id}: reason required")

        normalized = {**entry, "path": path, "lines": sorted(lines)}
        normalized_entries.append(normalized)
        for line in normalized["lines"]:
            key = (path, line, token)
            if key in index:
                raise ValueError(f"reviewed coverage key duplicated: {key}")
            index[key] = (entry_id, normalized)
    return index, data, normalized_entries


def reviewed_for(index, occurrence):
    return index.get((occurrence["path"], occurrence["line"], occurrence["token"]))


def build_report():
    files = list(iter_html())
    zero = []
    annotated = []
    all_occurrences = []
    totals = collections.Counter()
    attached_watch_totals = collections.Counter()
    for path in files:
        raw = path.read_text(encoding="utf-8", errors="ignore")
        if not RUBY_RE.search(raw):
            zero.append({"path": relpath(path), "exclusion": zero_ruby_exclusion(path)})
            continue
        annotated.append(relpath(path))
        occurrences, stats = scan_document(path)
        all_occurrences.extend(occurrences)
        totals["ruby"] += stats["raw_ruby"]
        totals["url_spans"] += stats["url_spans"]
        totals["attached_morphology_tokens"] += stats["attached"]
        totals["attached_allowed_internal"] += stats["attached_internal"]
        totals["attached_allowed_terminal"] += stats["attached_terminal"]
        totals["attached_unexpected_tokens"] += stats["attached_unexpected"]
        attached_watch_totals.update(stats["attached_watch"])
        for key, value in stats["line_classes"].items():
            totals[f"lines_{key}"] += value

    reviewed_index, reviewed_data, review_entries = load_reviewed()
    unresolved = []
    reviewed = []
    used_review_keys = set()
    actual_review_counts = collections.Counter()
    for occurrence in all_occurrences:
        review_match = reviewed_for(reviewed_index, occurrence)
        if review_match:
            entry_id, review = review_match
            item = {**occurrence, "review_category": review["category"], "reason": review["reason"]}
            reviewed.append(item)
            key = (occurrence["path"], occurrence["line"], occurrence["token"])
            used_review_keys.add(key)
            actual_review_counts[entry_id] += 1
        else:
            unresolved.append(occurrence)

    unused_review_keys = [
        {"path": path, "line": line, "token": token}
        for path, line, token in sorted(set(reviewed_index) - used_review_keys)
    ]
    review_count_mismatches = []
    for entry_id, entry in enumerate(review_entries):
        actual = actual_review_counts[entry_id]
        if actual != entry["expected_count"]:
            review_count_mismatches.append({
                "path": entry["path"],
                "token": entry["token"],
                "lines": entry["lines"],
                "expected_count": entry["expected_count"],
                "actual_count": actual,
            })
    review_config_gate = not unused_review_keys and not review_count_mismatches

    zero_tally = collections.Counter(x["exclusion"] for x in zero)
    accounted = len(files) == len(annotated) + len(zero)
    gate = (
        accounted
        and zero_tally.get("UNEXPECTED_zero_ruby", 0) == 0
        and len(unresolved) == 0
        and review_config_gate
    )
    report = {
        "scope": "all_corpus_content_html",
        "files": len(files),
        "annotated_documents": len(annotated),
        "annotated_document_paths": sorted(annotated),
        "zero_ruby_documents": len(zero),
        "zero_ruby_tally": dict(zero_tally),
        "zero_ruby_paths": sorted(zero, key=lambda x: x["path"]),
        "document_accounting_gate": accounted,
        "totals": dict(totals),
        "attached_watch_inventory": dict(sorted(attached_watch_totals.items())),
        "candidate_occurrences": len(all_occurrences),
        "candidate_unique_path_token": len({(x["path"], x["token"]) for x in all_occurrences}),
        "reviewed_occurrences": len(reviewed),
        "unresolved_true_missing": len(unresolved),
        "coverage_gate": gate,
        "review_config_entries": len(reviewed_data.get("entries", [])),
        "review_keys_used": len(used_review_keys),
        "review_config_gate": review_config_gate,
        "review_unused_keys": unused_review_keys,
        "review_count_mismatches": review_count_mismatches,
        "unresolved": unresolved,
        "reviewed": reviewed,
    }
    return report


def rule_proposals(
    rules: dict[str, str], selection=None,
    include_path_regex: str | None = None,
    exclude_path_regex: str | None = None,
    local_fragments: bool = False,
):
    """Return safe line replacements; existing ruby and URLs stay masked."""
    selected = set(tuple(x) for x in selection) if selection else None
    proposals = []
    patterns = [
        (token, re.compile(rf"(?<![A-Za-zĈĜĤĴŜŬĉĝĥĵŝŭ]){re.escape(token)}(?![A-Za-zĈĜĤĴŜŬĉĝĥĵŝŭ])"), ruby)
        for token, ruby in sorted(rules.items(), key=lambda x: -len(x[0]))
    ]
    for path in iter_html():
        rel = relpath(path)
        if include_path_regex and not re.search(include_path_regex, rel):
            continue
        if exclude_path_regex and re.search(exclude_path_regex, rel):
            continue
        raw = path.read_text(encoding="utf-8", errors="ignore")
        ruby_matches = list(RUBY_RE.finditer(raw))
        if not ruby_matches:
            continue
        masked = mask_same_length(mask_same_length(raw, HEAD_SCRIPT_STYLE_RE), RUBY_RE)
        raw_lines = raw.splitlines(keepends=True)
        ruby_index = 0
        for (line_no, offset, masked_line), raw_line in zip(line_offsets(masked), raw_lines):
            if selected is not None and (rel, line_no) not in selected:
                continue
            raw_line_start, raw_line_end = offset, offset + len(raw_line)
            while ruby_index < len(ruby_matches) and ruby_matches[ruby_index].end() <= raw_line_start:
                ruby_index += 1
            has_ruby = (
                ruby_index < len(ruby_matches)
                and ruby_matches[ruby_index].start() < raw_line_end
                and ruby_matches[ruby_index].end() > raw_line_start
            )
            vis = visible_line(masked_line)
            vis_url_masked, _ = mask_urls(vis)
            line_class = classify_line(vis_url_masked, has_ruby)
            if line_class not in {"annotated_body", "plain_line_in_annotated_document"}:
                continue

            # Locate rule tokens on the same-length masked raw line.  Tags do
            # not alter offsets; ruby/URL spans are NUL and cannot match.
            protected = masked_line
            for url_match in URL_RE.finditer(protected):
                chars = list(protected)
                for i in range(url_match.start(), url_match.end()):
                    if chars[i] not in "\r\n":
                        chars[i] = "\x00"
                protected = "".join(chars)
            replacements = []
            for token, pattern, ruby_html in patterns:
                for match in pattern.finditer(protected):
                    replacements.append((match.start(), match.end(), ruby_html, token))
            if not replacements:
                continue
            replacements.sort(reverse=True)
            new_line = raw_line
            used = []
            chosen = []
            last_start = len(raw_line) + 1
            for start, end, ruby_html, token in replacements:
                if end > last_start:
                    continue
                new_line = new_line[:start] + ruby_html + new_line[end:]
                last_start = start
                used.append(token)
                chosen.append((start, end, ruby_html, token))
            if new_line != raw_line:
                if local_fragments:
                    # Long corpus lines can exceed 40 kB, which makes a
                    # whole-line patch fragile.  Emit bounded, non-overlapping
                    # fragments clustered around nearby replacements instead.
                    ordered = sorted(chosen)
                    clusters = []
                    for replacement in ordered:
                        if clusters and replacement[0] - clusters[-1][-1][1] <= 200:
                            clusters[-1].append(replacement)
                        else:
                            clusters.append([replacement])
                    for index, cluster in enumerate(clusters):
                        previous_end = clusters[index - 1][-1][1] if index else 0
                        next_start = (
                            clusters[index + 1][0][0]
                            if index + 1 < len(clusters) else len(raw_line)
                        )
                        frag_start = max(previous_end, cluster[0][0] - 100)
                        frag_end = min(next_start, cluster[-1][1] + 100)
                        old_fragment = raw_line[frag_start:frag_end]
                        new_fragment = old_fragment
                        fragment_tokens = []
                        for start, end, ruby_html, token in reversed(cluster):
                            local_start, local_end = start - frag_start, end - frag_start
                            new_fragment = (
                                new_fragment[:local_start] + ruby_html
                                + new_fragment[local_end:]
                            )
                            fragment_tokens.append(token)
                        proposals.append({
                            "path": rel, "line": line_no,
                            "old": old_fragment, "new": new_fragment,
                            "tokens": sorted(fragment_tokens),
                            "old_length": len(old_fragment),
                        })
                    continue
                proposals.append({
                    "path": rel, "line": line_no,
                    "old": raw_line.rstrip("\r\n"), "new": new_line.rstrip("\r\n"),
                    "tokens": sorted(used), "old_length": len(raw_line),
                })
    return proposals


def decode_b64_json(value):
    return json.loads(base64.b64decode(value).decode("utf-8"))


def ruby_rules_from_rt(rt_rules: dict[str, str]) -> dict[str, str]:
    """Build verifier-consistent ruby HTML from surface -> clean rt text."""
    spec = importlib.util.spec_from_file_location("coverage_ruby_css_verifier", VERIFIER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rules = {}
    for surface, rt_clean in rt_rules.items():
        css_class, _ratio = module.calc_css_class(surface, rt_clean)
        rt_html = module.build_correct_rt(rt_clean, css_class)
        rules[surface] = (
            f'<ruby>{surface}<rt class="{css_class}">{rt_html}</rt></ruby>'
        )
    return rules


def ruby_rules_from_structured(spec_rules: dict[str, dict]) -> dict[str, str]:
    """Build rules whose matched surface has text outside the ruby boundary."""
    spec = importlib.util.spec_from_file_location("coverage_ruby_css_verifier", VERIFIER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rules = {}
    for surface, row in spec_rules.items():
        before, rb, after = row.get("before", ""), row["rb"], row.get("after", "")
        if before + rb + after != surface:
            raise ValueError(f"structured surface mismatch: {surface!r}")
        rt_clean = row["rt"]
        css_class, _ratio = module.calc_css_class(rb, rt_clean)
        rt_html = module.build_correct_rt(rt_clean, css_class)
        rules[surface] = (
            before + f'<ruby>{rb}<rt class="{css_class}">{rt_html}</rt></ruby>' + after
        )
    return rules


def apply_exact_line_proposals(proposals):
    """Apply audited bulk rewrites only when every old line matches exactly."""
    grouped = collections.defaultdict(list)
    for row in proposals:
        grouped[row["path"]].append(row)
    # Complete preflight before the first write.
    prepared = {}
    for rel, rows in grouped.items():
        path = CORP / rel
        raw_bytes = path.read_bytes()
        bom = raw_bytes.startswith(b"\xef\xbb\xbf")
        raw = raw_bytes.decode("utf-8-sig" if bom else "utf-8")
        lines = raw.splitlines(keepends=True)
        for row in rows:
            index = row["line"] - 1
            current = lines[index]
            core = current.rstrip("\r\n")
            ending = current[len(core):]
            if core != row["old"]:
                raise RuntimeError(
                    f"exact-line preflight failed: {rel}:{row['line']}"
                )
            lines[index] = row["new"] + ending
        prepared[path] = (bom, "".join(lines))
    for path, (bom, text_value) in prepared.items():
        encoded = text_value.encode("utf-8")
        path.write_bytes((b"\xef\xbb\xbf" if bom else b"") + encoded)
    return {"files": len(prepared), "rows": len(proposals)}


def fragment_visible(fragment):
    """Project an HTML fragment to visible base text for no-text-change checks."""
    return TAG_RE.sub("", RUBY_RE.sub(lambda match: match.group("rb"), fragment))


def apply_exact_fragment_rules(rules):
    """Apply audited in-line rewrites with complete count and visibility preflight.

    This is for very long corpus lines for which a unified whole-line patch is
    fragile.  Every rule is scoped to an exact path and line, declares the exact
    old-fragment count, and must preserve the visible base text.
    """
    grouped = collections.defaultdict(list)
    seen = set()
    for rule_id, row in enumerate(rules):
        path = row.get("path")
        line = row.get("line")
        old = row.get("old")
        new = row.get("new")
        expected = row.get("expected_count", 1)
        if not isinstance(path, str) or not path or path == "*":
            raise ValueError(f"fragment rule {rule_id}: exact path required")
        path = path.replace("\\", "/")
        if not isinstance(line, int) or isinstance(line, bool) or line < 1:
            raise ValueError(f"fragment rule {rule_id}: positive line required")
        if not isinstance(old, str) or not old or not isinstance(new, str):
            raise ValueError(f"fragment rule {rule_id}: non-empty old and string new required")
        if not isinstance(expected, int) or isinstance(expected, bool) or expected < 1:
            raise ValueError(f"fragment rule {rule_id}: positive expected_count required")
        if fragment_visible(old) != fragment_visible(new):
            raise ValueError(f"fragment rule {rule_id}: visible base text would change")
        key = (path, line, old)
        if key in seen:
            raise ValueError(f"fragment rule duplicated: {key}")
        seen.add(key)
        grouped[path].append({**row, "path": path, "expected_count": expected})

    # Preflight every rule against the same original snapshot before any write.
    prepared = {}
    occurrences = 0
    for rel, rows in grouped.items():
        path = CORP / rel
        raw_bytes = path.read_bytes()
        bom = raw_bytes.startswith(b"\xef\xbb\xbf")
        raw = raw_bytes.decode("utf-8-sig" if bom else "utf-8")
        lines = raw.splitlines(keepends=True)
        for row in rows:
            if row["line"] > len(lines):
                raise RuntimeError(f"fragment line out of range: {rel}:{row['line']}")
            core = lines[row["line"] - 1].rstrip("\r\n")
            actual = core.count(row["old"])
            if actual != row["expected_count"]:
                raise RuntimeError(
                    f"fragment preflight failed: {rel}:{row['line']} "
                    f"expected={row['expected_count']} actual={actual}"
                )
            occurrences += actual
        # Longest old fragments first prevents a component rule consuming a
        # phrase that a more specific rule is intended to merge.
        for row in sorted(rows, key=lambda value: -len(value["old"])):
            index = row["line"] - 1
            current = lines[index]
            core = current.rstrip("\r\n")
            ending = current[len(core):]
            core = core.replace(row["old"], row["new"])
            lines[index] = core + ending
        prepared[path] = (bom, "".join(lines))

    for path, (bom, text_value) in prepared.items():
        encoded = text_value.encode("utf-8")
        path.write_bytes((b"\xef\xbb\xbf" if bom else b"") + encoded)
    return {"files": len(prepared), "rules": len(rules), "occurrences": occurrences}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-zero", action="store_true")
    parser.add_argument("--propose-rules", help="base64 UTF-8 JSON: token -> ruby HTML")
    parser.add_argument(
        "--propose-rt-rules",
        help="base64 UTF-8 JSON: surface -> clean rt (CSS and br are calculated)",
    )
    parser.add_argument(
        "--propose-structured-rules",
        help="base64 UTF-8 JSON: surface -> {rb, rt, before?, after?}",
    )
    parser.add_argument("--selection", help="base64 UTF-8 JSON: [[path,line], ...]")
    parser.add_argument("--include-path-regex", help="proposal paths must match this regex")
    parser.add_argument("--exclude-path-regex", help="proposal paths matching this regex are skipped")
    parser.add_argument("--metadata-only", action="store_true")
    parser.add_argument(
        "--local-fragments", action="store_true",
        help="emit bounded patch fragments instead of fragile whole lines",
    )
    parser.add_argument(
        "--apply-bulk", action="store_true",
        help="apply proposed whole-line rewrites after an all-lines exact-match preflight",
    )
    parser.add_argument(
        "--grouped-manifest", action="store_true",
        help="compact proposal manifest: path -> [[line, old_length], ...]",
    )
    parser.add_argument(
        "--apply-fragment-rules",
        help="base64 UTF-8 JSON exact path/line/old/new rules; applies after full preflight",
    )
    args = parser.parse_args()

    if args.apply_fragment_rules:
        print(json.dumps(
            apply_exact_fragment_rules(decode_b64_json(args.apply_fragment_rules)),
            ensure_ascii=False,
        ))
        return

    if args.propose_rules or args.propose_rt_rules or args.propose_structured_rules:
        if args.propose_rules:
            rules = decode_b64_json(args.propose_rules)
        elif args.propose_rt_rules:
            rules = ruby_rules_from_rt(decode_b64_json(args.propose_rt_rules))
        else:
            rules = ruby_rules_from_structured(
                decode_b64_json(args.propose_structured_rules)
            )
        proposals = rule_proposals(
            rules,
            decode_b64_json(args.selection) if args.selection else None,
            args.include_path_regex,
            args.exclude_path_regex,
            args.local_fragments,
        )
        if args.apply_bulk:
            if args.local_fragments:
                parser.error("--apply-bulk cannot be combined with --local-fragments")
            print(json.dumps(apply_exact_line_proposals(proposals), ensure_ascii=False))
            return
        if args.grouped_manifest:
            grouped = collections.defaultdict(list)
            for row in proposals:
                grouped[row["path"]].append([row["line"], row["old_length"]])
            print(json.dumps(dict(sorted(grouped.items())), ensure_ascii=False))
            return
        if args.metadata_only:
            proposals = [
                {k: row[k] for k in ("path", "line", "tokens", "old_length")}
                for row in proposals
            ]
        print(json.dumps(proposals, ensure_ascii=False))
        return

    report = build_report()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    json.dump(report, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(
        f"HTML {report['files']} = annotated {report['annotated_documents']} + "
        f"zero-ruby {report['zero_ruby_documents']} / "
        f"candidates {report['candidate_occurrences']} / "
        f"reviewed {report['reviewed_occurrences']} / "
        f"true_missing {report['unresolved_true_missing']} / "
        f"gate {'PASS' if report['coverage_gate'] else 'FAIL'}"
    )
    print(f"保存: {OUT}")
    if args.require_zero and not report["coverage_gate"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
