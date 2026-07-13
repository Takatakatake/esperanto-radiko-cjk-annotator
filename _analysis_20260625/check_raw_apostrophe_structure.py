# -*- coding: utf-8 -*-
"""Gate corpus-observed U+2019 spellings against all deployed Ruby apps.

The normal no-worsening audit intentionally canonicalizes the typographic
apostrophe (U+2019) to ASCII.  That is useful when combining references, but it
can hide a runtime rule that accepts only the ASCII spelling.  This gate keeps
the browser-visible corpus spelling as its runtime input while comparing the
result with the corpus's canonical typed (ruby/literal) signature.

``ESP_CORPUS_PATH`` must identify the clean corpus checkout pinned by
``_corpus_exact_app_manifest.json``.  The deployed JA/ZH/KO Ruby payloads and
runtime modules are then exercised directly.
"""
from __future__ import annotations

import collections
import gc
import json
import os
from pathlib import Path
import re
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import check_multilingual_structure as structure
import no_worsening_audit as audit


RIGHT_SINGLE_QUOTATION_MARK = "\u2019"
RUBY_PAYLOAD_NAME = "置換リスト_ルビ.json"


def browser_visible_surface(raw_surface: str) -> str:
    """Collapse HTML formatting whitespace without normalizing punctuation."""
    return re.sub(r"\s+", " ", raw_surface).strip()


def collect_cases(corpus_root: Path):
    """Collect raw U+2019 spellings and every corpus-authorized signature."""
    cases = {}
    file_count = 0
    raw_ruby = 0
    parsed_ruby = 0
    parsed_units = 0

    for content_dir in audit.CONTENT_DIRS:
        for path in sorted((corpus_root / content_dir).rglob("*")):
            if not path.is_file() or path.suffix.lower() not in {".html", ".htm"}:
                continue
            file_count += 1
            relative = path.relative_to(corpus_root).as_posix()
            text = path.read_text(encoding="utf-8", errors="strict")
            raw_ruby += len(audit.RAW_RUBY_OPEN_RE.findall(text))
            parsed_ruby += len(audit.RUBY_RE.findall(text))
            for raw_surface, typed_parts in audit.parse_corpus_words(text):
                parsed_units += 1
                raw_visible = browser_visible_surface(raw_surface)
                if (
                    RIGHT_SINGLE_QUOTATION_MARK not in raw_visible
                    or raw_visible == audit.canonical(raw_visible)
                ):
                    continue
                signature = audit.signature_from_typed_parts(typed_parts)
                if signature[0] != audit.canonical(raw_visible):
                    raise ValueError(
                        "raw apostrophe reconstruction failed: "
                        f"{relative}: {raw_visible!r} -> {signature[0]!r}"
                    )
                case = cases.setdefault(raw_visible, {
                    "signatures": collections.Counter(),
                    "paths": collections.Counter(),
                    "count": 0,
                })
                case["signatures"][signature] += 1
                case["paths"][relative] += 1
                case["count"] += 1

    if file_count != audit.EXPECTED_CONTENT_FILES:
        raise ValueError(
            f"HTML scope changed: {file_count} != {audit.EXPECTED_CONTENT_FILES}"
        )
    if raw_ruby != parsed_ruby:
        raise ValueError(f"unparsed ruby: {raw_ruby} != {parsed_ruby}")
    return cases, {
        "content_files": file_count,
        "raw_ruby": raw_ruby,
        "parsed_ruby": parsed_ruby,
        "parsed_units": parsed_units,
    }


def verify_pinned_corpus(corpus_root: Path):
    """Require the exact clean corpus snapshot used by the app manifest."""
    state = audit.git_repo_state(corpus_root)
    if state["status_entries"]:
        raise ValueError(
            "raw apostrophe gate requires a clean corpus checkout: "
            f"status_entries={state['status_entries']}"
        )
    fingerprint = audit.corpus_content_fingerprint(corpus_root)
    manifest = json.loads(
        (HERE / "_corpus_exact_app_manifest.json").read_text(encoding="utf-8")
    )
    source = manifest.get("source", {})
    expected = (source.get("head_oid"), source.get("content_sha256"))
    actual = (state["head_oid"], fingerprint["sha256"])
    if actual != expected:
        raise ValueError(
            "corpus does not match the pinned exact manifest: "
            f"expected head/content={expected!r}, actual={actual!r}"
        )
    return state, fingerprint


def canonical_signature_from_rendered(rendered: str):
    """Convert the shared structural helper's R/L output to audit identity."""
    typed_parts = []
    for item in structure.structural_signature(rendered)[1:]:
        kind, text = item.split(":", 1)
        if kind not in {"R", "L"}:
            raise ValueError(f"unexpected structural item: {item!r}")
        typed_parts.append((text, kind == "R"))
    return audit.signature_from_typed_parts(typed_parts)


def render_language(language: str, surfaces: list[str]):
    """Render one newline-delimited probe through a deployed app."""
    app_dir = ROOT / f"Esperanto-Kanji-Ruby-{language}"
    data_dir = app_dir / "app_data"
    payload = json.loads(
        (data_dir / RUBY_PAYLOAD_NAME).read_text(encoding="utf-8")
    )
    local_rules, global_rules, two_char_rules = audit.extract_lists(payload)
    module = audit.runtime_module(app_dir, f"raw_apostrophe_{language}")
    skip = module.import_placeholders(str(data_dir / "placeholders_skip.txt"))
    local_capture = module.import_placeholders(
        str(data_dir / "placeholders_localcapture.txt")
    )
    rendered = module.orchestrate_comprehensive_esperanto_text_replacement(
        "\n".join(f" {surface} " for surface in surfaces),
        skip,
        local_rules,
        local_capture,
        global_rules,
        two_char_rules,
        audit.FORMAT,
    )
    lines = rendered.splitlines()
    if len(lines) != len(surfaces):
        raise ValueError(
            f"{language} runtime line accounting failed: "
            f"{len(lines)} != {len(surfaces)}"
        )
    results = dict(zip(surfaces, lines))
    del payload, local_rules, global_rules, two_char_rules
    gc.collect()
    return results


def display_signature(signature) -> str:
    return audit.display_typed_parts(list(signature[1]))


def main() -> None:
    corpus_root = Path(os.environ.get(
        "ESP_CORPUS_PATH",
        ROOT / "_project_root_misc" / "京大エス研html文書＿Github",
    ))
    state, fingerprint = verify_pinned_corpus(corpus_root)
    cases, parser_counts = collect_cases(corpus_root)
    surfaces = sorted(cases)
    instance_count = sum(case["count"] for case in cases.values())
    signature_option_count = sum(
        len(case["signatures"]) for case in cases.values()
    )
    print(json.dumps({
        "corpus_head": state["head_oid"],
        "corpus_content_sha256": fingerprint["sha256"],
        **parser_counts,
        "raw_apostrophe_surfaces": len(surfaces),
        "raw_apostrophe_instances": instance_count,
        "expected_signature_options": signature_option_count,
    }, ensure_ascii=False))

    failures = []
    for language in ("JA", "ZH", "KO"):
        rendered_by_surface = render_language(language, surfaces)
        language_failures = 0
        for surface in surfaces:
            rendered = rendered_by_surface[surface]
            visible = structure.rendered_visible(rendered).strip()
            actual_signature = canonical_signature_from_rendered(rendered)
            expected_options = set(cases[surface]["signatures"])
            visible_ok = visible == surface
            structure_ok = actual_signature in expected_options
            if visible_ok and structure_ok:
                continue
            language_failures += 1
            failure = {
                "language": language,
                "surface": surface,
                "count": cases[surface]["count"],
                "visible_ok": visible_ok,
                "expected_visible": surface,
                "actual_visible": visible,
                "structure_ok": structure_ok,
                "expected_signatures": sorted(
                    display_signature(option) for option in expected_options
                ),
                "actual_signature": display_signature(actual_signature),
                "paths": [
                    {"path": path, "count": count}
                    for path, count in sorted(cases[surface]["paths"].items())
                ],
            }
            failures.append(failure)
            print(json.dumps(failure, ensure_ascii=False))
        print(
            f"[{language}] raw apostrophe structure: "
            f"surfaces={len(surfaces)} failures={language_failures}"
        )
        del rendered_by_surface
        gc.collect()

    if failures:
        print(
            "raw apostrophe structure: FAIL "
            f"({len(failures)} language/surface failures)"
        )
        raise SystemExit(1)
    print(
        "raw apostrophe structure: PASS "
        f"({len(surfaces)} surfaces / {instance_count} corpus instances / 3 languages)"
    )


if __name__ == "__main__":
    main()
