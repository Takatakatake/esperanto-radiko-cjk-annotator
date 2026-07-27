# -*- coding: utf-8 -*-
"""Build the pinned exact-rule manifest for non-app-alphabet corpus units.

Multi-word names, Latin-Extended spellings and punctuated abbreviations cannot
be derived safely by the ordinary Esperanto stemmer.  This builder records
their *observed typed signature* and localized atomic annotations once, so the
three apps can install case-sensitive whole-surface rules without broadening a
substring or inflection rule.

Usage::

    python build_corpus_exact_manifest.py --write
    python build_corpus_exact_manifest.py --check

``ESP_CORPUS_PATH`` may point at an isolated, reviewed corpus checkout.
"""
from __future__ import annotations

import argparse
import collections
import html as htmllib
import json
import os
from pathlib import Path
import re
import sys

from atomic_json import atomic_json_dump
import no_worsening_audit as audit


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUTPUT = HERE / "_corpus_exact_app_manifest.json"
RT_RE = re.compile(r"<rt\b[^>]*>(?P<rt>.*?)</rt\s*>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"^\[([^]]+)\]")
HANGUL_RE = re.compile(r"[\uac00-\ud7a3]")
BR_SENTINEL = "\x02"

TAG_TRANSLATIONS = {
    "人名": ("人名", "인명"),
    "地名": ("地名", "지명"),
    "団体": ("团体", "단체"),
    "企業": ("企业", "기업"),
    "雑誌": ("杂志", "잡지"),
    "書": ("书", "책"),
    "言語名": ("语言名", "언어명"),
    "宗教": ("宗教", "종교"),
    "架空国": ("虚构国家", "가상국"),
    "略": ("简称", "약"),
    "敬称": ("敬称", "경칭"),
    "語": ("词", "어휘"),
    "劇": ("剧", "극"),
    "作品": ("作品", "작품"),
    "商品名": ("商品名", "상품명"),
    "サービス": ("服务", "서비스"),
    "時代": ("时代", "시대"),
    "植": ("植物", "식물"),
    "文字": ("文字", "문자"),
    "化学式": ("化学式", "화학식"),
    "AI": ("AI", "AI"),
}


def clean_rb(raw: str) -> str:
    return audit.canonical(htmllib.unescape(re.sub(r"<[^>]+>", "", raw)))


def clean_rt(raw: str) -> str:
    value = re.sub(r"<br\s*/?>", BR_SENTINEL, raw, flags=re.IGNORECASE)
    value = htmllib.unescape(re.sub(r"<[^>]+>", "", value))
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(rf"\s*{BR_SENTINEL}\s*", "<br>", value)
    return value


def source_language(relative: str, gloss: str) -> str:
    if relative.lower().endswith("_ko.html") or HANGUL_RE.search(gloss):
        return "ko"
    return "ja"


def select_gloss(counter: collections.Counter[str]) -> str | None:
    if not counter:
        return None
    # Prefer frequency first, then a guide tag, then the compact normalized
    # spelling.  The full variant multiset remains in the manifest for audit.
    return sorted(
        counter,
        key=lambda gloss: (
            -counter[gloss],
            0 if TAG_RE.match(gloss) else 1,
            len(gloss),
            gloss,
        ),
    )[0]


def fallback_gloss(root: str, japanese_gloss: str, language: str) -> str:
    match = TAG_RE.match(japanese_gloss or "")
    tag = match.group(1) if match else None
    if tag in TAG_TRANSLATIONS:
        localized = TAG_TRANSLATIONS[tag][0 if language == "zh" else 1]
    elif tag:
        localized = "专名" if language == "zh" else "고유명"
    elif "." in root or (root.isupper() and len(root) <= 12):
        localized = "简称" if language == "zh" else "약"
    else:
        localized = "词" if language == "zh" else "어휘"
    return f"[{localized}]{root}"


def target_from_signature(signature) -> str:
    _surface, spans = signature
    pieces = []
    for text, _is_ruby in spans:
        if "/" in text:
            raise ValueError(f"slash cannot be encoded in exact target: {text!r}")
        pieces.append(text)
    return "/".join(pieces)


def semantic_manifest(payload: dict) -> dict:
    """Exclude only the checkout branch label from manifest identity.

    A commit can be checked out on ``main``, a temporary audit branch, or in
    detached-HEAD state without changing a single corpus byte.  The immutable
    HEAD/content/status pins remain authoritative; ``source.branch`` is kept
    solely as acquisition provenance.
    """
    projected = dict(payload)
    source = dict(projected.get("source", {}))
    source.pop("branch", None)
    projected["source"] = source
    return projected


def build(corpus_root: Path) -> dict:
    repo_state = audit.git_repo_state(corpus_root)
    if repo_state["status_entries"]:
        raise ValueError("exact manifest requires a clean corpus checkout")

    cases = collections.defaultdict(collections.Counter)
    paths_by_case = collections.defaultdict(collections.Counter)
    raw_ruby = parsed_ruby = parsed_units = 0
    files: list[tuple[Path, str, str]] = []
    for content_dir in audit.CONTENT_DIRS:
        for path in sorted((corpus_root / content_dir).rglob("*")):
            if not path.is_file() or path.suffix.lower() not in {".html", ".htm"}:
                continue
            text = path.read_text(encoding="utf-8", errors="strict")
            relative = path.relative_to(corpus_root).as_posix()
            files.append((path, relative, text))
            raw_ruby += len(audit.RAW_RUBY_OPEN_RE.findall(text))
            parsed_ruby += len(audit.RUBY_RE.findall(text))
            for raw_surface, typed_parts in audit.parse_corpus_words(text):
                parsed_units += 1
                surface = audit.canonical(raw_surface)
                if audit.evaluable(surface):
                    continue
                signature = audit.signature_from_typed_parts(typed_parts)
                cases[surface][signature] += 1
                paths_by_case[(surface, signature)][relative] += 1

    if len(files) != audit.EXPECTED_CONTENT_FILES:
        raise ValueError(f"HTML scope changed: {len(files)}")
    if raw_ruby != parsed_ruby:
        raise ValueError(f"unparsed ruby: {raw_ruby} != {parsed_ruby}")
    conflicts = {surface: options for surface, options in cases.items() if len(options) != 1}
    if conflicts:
        raise ValueError(f"extended corpus signatures are not unique: {sorted(conflicts)}")

    exact_surfaces = []
    needed_roots = set()
    for surface in sorted(cases):
        signature, count = next(iter(cases[surface].items()))
        for text, is_ruby in signature[1]:
            if is_ruby and not audit.evaluable(text):
                needed_roots.add(text)
        exact_surfaces.append({
            "surface": surface,
            "target": target_from_signature(signature),
            "signature": audit.signature_payload(signature),
            "typed": audit.display_typed_parts(list(signature[1])),
            "count": count,
            "paths": [
                {"path": relative, "count": path_count}
                for relative, path_count in sorted(
                    paths_by_case[(surface, signature)].items()
                )
            ],
        })

    annotation_counts = collections.defaultdict(
        lambda: collections.defaultdict(collections.Counter)
    )
    for _path, relative, text in files:
        for match in audit.RUBY_RE.finditer(text):
            root = clean_rb(match.group("rb"))
            if root not in needed_roots:
                continue
            rt_match = RT_RE.search(match.group(0))
            if rt_match is None:
                raise ValueError(f"missing rt for {root!r}: {relative}")
            gloss = clean_rt(rt_match.group("rt"))
            if not gloss:
                raise ValueError(f"empty rt for {root!r}: {relative}")
            annotation_counts[root][source_language(relative, gloss)][gloss] += 1

    missing = sorted(needed_roots - set(annotation_counts))
    if missing:
        raise ValueError(f"missing exact annotations: {missing}")
    annotations = {}
    for root in sorted(needed_roots):
        by_language = annotation_counts[root]
        ja = select_gloss(by_language.get("ja", collections.Counter()))
        ko = select_gloss(by_language.get("ko", collections.Counter()))
        if ja is None:
            # The current corpus has a JA counterpart for every reviewed exact
            # base.  Keep a deterministic fallback for future KO-only sources.
            ja = f"[語]{root}"
        if ja == root:
            ja = f"[語]{root}"
        annotations[root] = {
            "glosses": {
                "ja": ja,
                "zh": fallback_gloss(root, ja, "zh"),
                "ko": ko if ko and ko != root else fallback_gloss(root, ja, "ko"),
            },
            "variants": {
                language: [
                    {"gloss": gloss, "count": count}
                    for gloss, count in sorted(values.items())
                ]
                for language, values in sorted(by_language.items())
            },
        }

    fingerprint = audit.corpus_content_fingerprint(corpus_root)
    return {
        "schema_version": 1,
        "description": (
            "Pinned exact case-sensitive app rules for every non-app-alphabet "
            "ruby-bearing unit in the reviewed Kyoto corpus."
        ),
        "source": {
            **repo_state,
            "content_files": fingerprint["files"],
            "content_sha256": fingerprint["sha256"],
            "raw_ruby": raw_ruby,
            "parsed_ruby": parsed_ruby,
            "parsed_units": parsed_units,
        },
        "counts": {
            "exact_surfaces": len(exact_surfaces),
            "exact_instances": sum(row["count"] for row in exact_surfaces),
            "atomic_whole_surfaces": sum(
                len(row["signature"]["spans"]) == 1
                and row["signature"]["spans"][0]["ruby"]
                for row in exact_surfaces
            ),
            "component_surfaces": sum(
                len(row["signature"]["spans"]) != 1
                for row in exact_surfaces
            ),
            "annotation_roots": len(annotations),
        },
        "exact_surfaces": exact_surfaces,
        "annotations": annotations,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    corpus_root = Path(os.environ.get(
        "ESP_CORPUS_PATH",
        ROOT / "_project_root_misc" / "京大エス研html文書＿Github",
    ))
    payload = build(corpus_root)
    if args.write:
        atomic_json_dump(OUTPUT, payload, indent=1)
    elif args.check:
        current = json.loads(OUTPUT.read_text(encoding="utf-8"))
        if semantic_manifest(current) != semantic_manifest(payload):
            raise SystemExit("corpus exact manifest is stale")
    print(json.dumps({
        "output": str(OUTPUT),
        "mode": "write" if args.write else ("check" if args.check else "dry-run"),
        **payload["counts"],
        "corpus_head": payload["source"]["head_oid"],
        "content_sha256": payload["source"]["content_sha256"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
