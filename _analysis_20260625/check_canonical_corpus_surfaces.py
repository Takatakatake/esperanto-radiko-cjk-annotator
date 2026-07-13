# -*- coding: utf-8 -*-
"""Fail-closed runtime gate for all canonical Kyoto-corpus word surfaces.

The non-evaluable, punctuated and multi-word exact units are covered by
``test_reviewed_exact_manifest.py``.  This gate covers the complementary set:
every app-alphabet surface parsed from the 169 pinned corpus documents.

``ESP_CORPUS_PATH`` is mandatory.  It must name the clean checkout pinned by
``_corpus_exact_app_manifest.json``.  By default the deployed JA/ZH/KO Ruby
payloads are rendered exactly as the baseline app runtime renders them.
"""
from __future__ import annotations

import argparse
import collections
import gc
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from atomic_json import atomic_json_dump
import no_worsening_audit as audit


RUBY_PAYLOAD_NAME = "置換リスト_ルビ.json"
DEFAULT_REPORT = HERE / "out" / "_audit_canonical_corpus_surfaces.json"
PLACEHOLDER_RE = re.compile(r"\$(?:[A-Za-z]+)?\d+\$")
EXPECTED_SCOPE = {
    "content_files": 169,
    "raw_ruby": 349006,
    "parsed_ruby": 349006,
    "parsed_units": 271065,
    "evaluable_instances": 269879,
    "canonical_surfaces": 21443,
    "reviewed_overrides": 628,
}
ALGORITHM = {
    "id": "canonical-corpus-surfaces-v1",
    "steps": [
        "Verify the corpus checkout is clean and matches the pinned HEAD/content hash.",
        "Parse CONTENT_DIRS with no_worsening_audit.parse_corpus_words.",
        "Canonicalize Esperanto notation and retain only audit.evaluable surfaces.",
        "Group every observed typed signature by canonical surface.",
        "Narrow all reviewed evaluable surfaces to their reviewed-manifest signature.",
        "Render every surface through each selected deployed Ruby runtime/payload.",
        "Require visible identity, expected typed signature, and no placeholder token.",
    ],
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def algorithm_sha256() -> str:
    encoded = json.dumps(
        ALGORITHM, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def validate_scope(scope: dict) -> None:
    differences = {
        key: {"expected": expected, "actual": scope.get(key)}
        for key, expected in EXPECTED_SCOPE.items()
        if scope.get(key) != expected
    }
    if differences:
        raise ValueError(f"canonical corpus scope changed: {differences!r}")


def verify_pinned_corpus(corpus_root: Path, exact_manifest: dict):
    state = audit.git_repo_state(corpus_root)
    if state["status_entries"]:
        raise ValueError(
            "canonical corpus gate requires a clean checkout: "
            f"status_entries={state['status_entries']}"
        )
    fingerprint = audit.corpus_content_fingerprint(corpus_root)
    source = exact_manifest.get("source", {})
    expected = (source.get("head_oid"), source.get("content_sha256"))
    actual = (state["head_oid"], fingerprint["sha256"])
    if actual != expected:
        raise ValueError(
            "corpus does not match the pinned exact manifest: "
            f"expected head/content={expected!r}, actual={actual!r}"
        )
    return state, fingerprint


def collect_canonical_cases(corpus_root: Path):
    cases = {}
    counts = collections.Counter()
    for content_dir in audit.CONTENT_DIRS:
        for path in sorted((corpus_root / content_dir).rglob("*")):
            if not path.is_file() or path.suffix.lower() not in {".html", ".htm"}:
                continue
            counts["content_files"] += 1
            text = path.read_text(encoding="utf-8", errors="strict")
            counts["raw_ruby"] += len(audit.RAW_RUBY_OPEN_RE.findall(text))
            counts["parsed_ruby"] += len(audit.RUBY_RE.findall(text))
            for raw_surface, typed_parts in audit.parse_corpus_words(text):
                counts["parsed_units"] += 1
                surface = audit.canonical(raw_surface)
                if not audit.evaluable(surface):
                    continue
                counts["evaluable_instances"] += 1
                signature = audit.signature_from_typed_parts(typed_parts)
                if signature[0] != surface:
                    raise ValueError(
                        f"canonical reconstruction failed: {path}: "
                        f"{surface!r} != {signature[0]!r}"
                    )
                case = cases.setdefault(surface, {
                    "options": collections.Counter(),
                    "instances": 0,
                })
                case["options"][signature] += 1
                case["instances"] += 1
    counts["canonical_surfaces"] = len(cases)
    return cases, dict(counts)


def apply_reviewed_overrides(cases: dict, reviewed_rows: list[dict]) -> None:
    for row in reviewed_rows:
        surface = audit.canonical(row["surface"])
        if surface not in cases:
            raise ValueError(
                f"reviewed surface is outside canonical corpus scope: {surface!r}"
            )
        signature = audit.signature_from_payload(row["signature"])
        if signature[0] != surface:
            raise ValueError(
                f"reviewed signature reconstruction mismatch: {surface!r}"
            )
        cases[surface]["options"] = collections.Counter({
            signature: cases[surface]["instances"],
        })


def inspect_rendered_surface(surface: str, rendered: str, expected_options):
    actual = audit.signature_from_typed_parts(
        audit.rendered_typed_parts(rendered),
    )
    visible_ok = actual[0] == surface
    structure_ok = actual in expected_options
    placeholder = bool(PLACEHOLDER_RE.search(rendered))
    return {
        "actual": actual,
        "visible_ok": visible_ok,
        "structure_ok": structure_ok,
        "placeholder": placeholder,
        "pass": visible_ok and structure_ok and not placeholder,
    }


def signature_text(signature) -> str:
    return audit.display_typed_parts(list(signature[1]))


def render_language(language: str, cases: dict, batch_size: int):
    app_dir = ROOT / f"Esperanto-Kanji-Ruby-{language}"
    data_dir = app_dir / "app_data"
    payload_path = data_dir / RUBY_PAYLOAD_NAME
    runtime_path = app_dir / "esp_text_replacement_module.py"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    local_rules, global_rules, two_char_rules = audit.extract_lists(payload)
    module = audit.runtime_module(app_dir, f"canonical_corpus_{language}")
    skip = module.import_placeholders(str(data_dir / "placeholders_skip.txt"))
    local_capture = module.import_placeholders(
        str(data_dir / "placeholders_localcapture.txt")
    )
    surfaces = sorted(cases)
    failures = []
    visible_failures = []
    placeholder_surfaces = []
    started = time.time()
    for start in range(0, len(surfaces), batch_size):
        batch = surfaces[start:start + batch_size]
        rendered = module.orchestrate_comprehensive_esperanto_text_replacement(
            "\n".join(f" {surface} " for surface in batch),
            skip,
            local_rules,
            local_capture,
            global_rules,
            two_char_rules,
            audit.FORMAT,
        )
        lines = rendered.splitlines()
        if len(lines) != len(batch):
            raise ValueError(
                f"{language} runtime line accounting failed: "
                f"{len(lines)} != {len(batch)}"
            )
        for surface, line in zip(batch, lines):
            expected_options = set(cases[surface]["options"])
            result = inspect_rendered_surface(surface, line, expected_options)
            if not result["visible_ok"]:
                visible_failures.append({
                    "surface": surface,
                    "actual_visible": result["actual"][0],
                })
            if result["placeholder"]:
                placeholder_surfaces.append(surface)
            if not result["structure_ok"]:
                failures.append({
                    "surface": surface,
                    "instances": cases[surface]["instances"],
                    "actual": signature_text(result["actual"]),
                    "expected": sorted(
                        signature_text(option) for option in expected_options
                    ),
                })
        print(
            f"[{language}] canonical surfaces "
            f"{min(start + len(batch), len(surfaces))}/{len(surfaces)}",
            flush=True,
        )
    result = {
        "language": language,
        "payload_path": str(payload_path),
        "payload_sha256": sha256_file(payload_path),
        "runtime_path": str(runtime_path),
        "runtime_sha256": sha256_file(runtime_path),
        "global_rules": len(global_rules),
        "render_seconds": time.time() - started,
        "residual_surfaces": len(failures),
        "residual_instances": sum(row["instances"] for row in failures),
        "visible_failures": len(visible_failures),
        "placeholder_residual_surfaces": len(placeholder_surfaces),
        "pass": not failures and not visible_failures and not placeholder_surfaces,
        "residuals": failures,
        "visible_failure_rows": visible_failures,
        "placeholder_surfaces": placeholder_surfaces,
    }
    del payload, local_rules, global_rules, two_char_rules
    gc.collect()
    return result


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--languages", nargs="+", default=["JA", "ZH", "KO"],
        choices=("JA", "ZH", "KO"),
    )
    parser.add_argument("--batch-size", type=int, default=1500)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args(argv)


def run(args):
    corpus_value = os.environ.get("ESP_CORPUS_PATH", "").strip()
    if not corpus_value:
        raise ValueError("ESP_CORPUS_PATH is required")
    if args.batch_size <= 0:
        raise ValueError("--batch-size must be positive")
    corpus_root = Path(corpus_value).resolve()
    exact_path = HERE / "_corpus_exact_app_manifest.json"
    reviewed_path = HERE / "_corpus_reviewed_exact_app_manifest.json"
    exact_manifest = json.loads(exact_path.read_text(encoding="utf-8"))
    reviewed_manifest = json.loads(reviewed_path.read_text(encoding="utf-8"))
    state, fingerprint = verify_pinned_corpus(corpus_root, exact_manifest)
    cases, scope = collect_canonical_cases(corpus_root)
    reviewed_rows = reviewed_manifest["exact_surfaces"]
    scope["reviewed_overrides"] = len(reviewed_rows)
    validate_scope(scope)
    apply_reviewed_overrides(cases, reviewed_rows)
    language_results = [
        render_language(language, cases, args.batch_size)
        for language in args.languages
    ]
    report = {
        "schema_version": 1,
        "algorithm": ALGORITHM,
        "algorithm_sha256": algorithm_sha256(),
        "script_path": str(Path(__file__).resolve()),
        "script_sha256": sha256_file(Path(__file__).resolve()),
        "corpus": {
            "path": str(corpus_root),
            "head_oid": state["head_oid"],
            "content_sha256": fingerprint["sha256"],
        },
        "exact_manifest_sha256": sha256_file(exact_path),
        "reviewed_manifest_sha256": sha256_file(reviewed_path),
        "scope": scope,
        "languages": language_results,
        "residual_language_surfaces": sum(
            row["residual_surfaces"] for row in language_results
        ),
        "visible_failures": sum(
            row["visible_failures"] for row in language_results
        ),
        "placeholder_residual_surfaces": sum(
            row["placeholder_residual_surfaces"] for row in language_results
        ),
        "pass": all(row["pass"] for row in language_results),
    }
    return report


def main(argv=None) -> None:
    args = parse_args(argv)
    try:
        report = run(args)
    except Exception as error:
        failure_report = {
            "schema_version": 1,
            "algorithm": ALGORITHM,
            "algorithm_sha256": algorithm_sha256(),
            "script_path": str(Path(__file__).resolve()),
            "script_sha256": sha256_file(Path(__file__).resolve()),
            "pass": False,
            "fatal_error": f"{type(error).__name__}: {error}",
        }
        atomic_json_dump(args.report, failure_report, indent=2)
        raise
    atomic_json_dump(args.report, report, indent=2)
    print(json.dumps({
        "report": str(args.report),
        "algorithm_sha256": report["algorithm_sha256"],
        "scope": report["scope"],
        "residual_language_surfaces": report["residual_language_surfaces"],
        "visible_failures": report["visible_failures"],
        "placeholder_residual_surfaces": report[
            "placeholder_residual_surfaces"
        ],
        "pass": report["pass"],
    }, ensure_ascii=False))
    if not report["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
