# -*- coding: utf-8 -*-
"""Apply/check the explicit b769 -> d1642c2 reviewed-exact transition.

The original 628-row residual report is historical evidence and must never be
presented as if it had been rendered against the newer corpus.  This successor
therefore reads the parent manifest from its pinned app commit, retires exactly
three source-typo rows, rebuilds all 625 survivors from the clean candidate
corpus, and records the transition-ledger identity as the new report authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from atomic_json import atomic_json_dump
import build_corpus_reviewed_exact_manifest as reviewed
import no_worsening_audit as audit


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
LEDGER_PATH = HERE / "_corpus_reviewed_exact_transition_d1642c2.json"
OUTPUT = HERE / "_corpus_reviewed_exact_app_manifest.json"


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def canonical_hash(value) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256_bytes(raw)


def git_blob(commit: str, path: str) -> bytes:
    completed = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        raise ValueError(
            "cannot read pinned parent manifest: "
            + completed.stderr.decode("utf-8", errors="replace")
        )
    return completed.stdout


def git_tree(repo: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD^{tree}"],
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        raise ValueError(
            "cannot read candidate corpus tree: "
            + completed.stderr.decode("utf-8", errors="replace")
        )
    return completed.stdout.decode("ascii").strip()


def validate_ledger(ledger: dict) -> None:
    if ledger.get("schema_version") != 1:
        raise ValueError("unsupported reviewed-exact transition schema")
    parent = ledger.get("parent", {})
    candidate = ledger.get("candidate", {})
    if (
        parent.get("manifest_path")
        != "_analysis_20260625/_corpus_reviewed_exact_app_manifest.json"
        or parent.get("counts")
        != {
            "exact_surfaces": 628,
            "exact_instances": 2743,
            "ruby_context_annotations": 930,
        }
        or candidate.get("counts")
        != {
            "exact_surfaces": 625,
            "exact_instances": 2740,
            "ruby_context_annotations": 924,
        }
    ):
        raise ValueError("reviewed-exact transition count closure changed")

    retirements = ledger.get("retirements")
    if not isinstance(retirements, list):
        raise ValueError("retirements must be a list")
    expected = {
        "bonŝanĉulo": (
            1,
            {
                "@typed:bonŝanĉulo:0",
                "@typed:bonŝanĉulo:1",
                "@typed:bonŝanĉulo:2",
            },
            "bonŝanculo",
        ),
        "fronantaj": (
            1,
            {"@typed:fronantaj:0", "@typed:fronantaj:1"},
            "frontantaj",
        ),
        "jurnal": (
            1,
            {"@typed:jurnal:0"},
            "ĵurnal",
        ),
    }
    actual = {}
    for row in retirements:
        surface = row.get("surface")
        if surface in actual:
            raise ValueError(f"duplicate retirement: {surface!r}")
        actual[surface] = (
            row.get("count"),
            set(row.get("annotation_keys", [])),
            row.get("replacement_surface"),
        )
    if actual != expected:
        raise ValueError(f"reviewed-exact retirement closure changed: {actual!r}")
    policy = ledger.get("policy", {})
    if policy != {
        "old_residual_report_reuse": False,
        "source_only_refresh": False,
        "retirement_scope_closed": True,
        "retain_bounded_jurnalisto_compatibility": True,
        "require_standard_ĵurnalisto_runtime": True,
    }:
        raise ValueError("reviewed-exact transition policy changed")


def load_parent(ledger: dict) -> dict:
    parent = ledger["parent"]
    raw = git_blob(parent["app_commit"], parent["manifest_path"])
    if sha256_bytes(raw) != parent["manifest_sha256"]:
        raise ValueError("pinned parent reviewed-exact manifest hash changed")
    payload = json.loads(raw.decode("utf-8"))
    if payload.get("source", {}).get("report", {}).get("sha256") != (
        parent["residual_report_sha256"]
    ):
        raise ValueError("historical residual-report identity changed")
    if payload.get("source", {}).get("head_oid") != parent["source"]["head_oid"]:
        raise ValueError("historical reviewed-exact corpus head changed")
    if payload.get("source", {}).get("content_sha256") != (
        parent["source"]["content_sha256"]
    ):
        raise ValueError("historical reviewed-exact corpus content changed")
    if payload.get("counts") != parent["counts"]:
        raise ValueError("historical reviewed-exact counts changed")
    return payload


def build(corpus_root: Path) -> dict:
    ledger_raw = LEDGER_PATH.read_bytes()
    ledger = json.loads(ledger_raw.decode("utf-8"))
    validate_ledger(ledger)
    parent = load_parent(ledger)

    retired = {row["surface"] for row in ledger["retirements"]}
    parent_rows = parent.get("exact_surfaces", [])
    observed_retired = {
        row["surface"] for row in parent_rows if row["surface"] in retired
    }
    if observed_retired != retired:
        raise ValueError("one or more reviewed retirement rows are absent from parent")
    selected = {
        row["surface"]: set(row["available_expected_options"])
        for row in parent_rows
        if row["surface"] not in retired
    }
    if len(selected) != 625:
        raise ValueError(f"reviewed survivor selection changed: {len(selected)}")

    report_meta = {
        "kind": "explicit_retirement_transition",
        "filename": LEDGER_PATH.name,
        "sha256": sha256_bytes(ledger_raw),
        "schema_version": ledger["schema_version"],
        "parent_residual_report_sha256": ledger["parent"][
            "residual_report_sha256"
        ],
        "retired_surfaces": sorted(retired),
    }
    payload = reviewed.build(corpus_root, selected, report_meta)

    candidate = ledger["candidate"]
    source = payload["source"]
    state = audit.git_repo_state(corpus_root)
    expected_source = {
        "head_oid": candidate["head_oid"],
        "tree_oid": candidate["tree_oid"],
        "content_sha256": candidate["content_sha256"],
        "content_files": candidate["content_files"],
        "raw_ruby": candidate["raw_ruby"],
        "parsed_ruby": candidate["parsed_ruby"],
        "parsed_units": candidate["parsed_units"],
    }
    actual_source = {
        "head_oid": source["head_oid"],
        "tree_oid": git_tree(corpus_root),
        "content_sha256": source["content_sha256"],
        "content_files": source["content_files"],
        "raw_ruby": source["raw_ruby"],
        "parsed_ruby": source["parsed_ruby"],
        "parsed_units": source["parsed_units"],
    }
    if actual_source != expected_source:
        raise ValueError(
            f"reviewed-exact candidate source changed: {actual_source!r}"
        )
    if payload["counts"] != candidate["counts"]:
        raise ValueError("reviewed-exact candidate counts changed")

    hashes = {
        "exact_surfaces_sha256": canonical_hash(payload["exact_surfaces"]),
        "annotations_sha256": canonical_hash(payload["annotations"]),
        "survivor_payload_sha256": canonical_hash({
            key: value
            for key, value in payload.items()
            if key not in {"source", "description"}
        }),
    }
    expected_hashes = {
        key: value
        for key, value in ledger["survivor_hashes"].items()
        if key.endswith("_sha256")
    }
    if hashes != expected_hashes:
        raise ValueError(
            f"reviewed-exact survivor payload changed: {hashes!r}"
        )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    corpus_value = os.environ.get("ESP_CORPUS_PATH", "").strip()
    if not corpus_value:
        raise SystemExit("ESP_CORPUS_PATH is required")
    payload = build(Path(corpus_value).resolve())
    if args.write:
        atomic_json_dump(OUTPUT, payload, indent=1)
    else:
        current = json.loads(OUTPUT.read_text(encoding="utf-8"))
        if reviewed.semantic_manifest(current) != reviewed.semantic_manifest(
            payload
        ):
            raise SystemExit("active reviewed-exact manifest is stale")
    print(json.dumps({
        "mode": "write" if args.write else "check",
        "output": str(OUTPUT),
        "corpus_head": payload["source"]["head_oid"],
        "content_sha256": payload["source"]["content_sha256"],
        **payload["counts"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
