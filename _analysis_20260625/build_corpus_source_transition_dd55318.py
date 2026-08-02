# -*- coding: utf-8 -*-
"""Fail-closed proof for the ccb9398 -> dd55318 corpus source transition.

The successor commit corrects one *corpus expectation* (the media root
``radio`` in one singular ``radioelsendo``).  It does not authorize a new app
rule, a word_anno change, a Kanji change, or a learner-master decomposition
change.  The parent tree is materialized with ``git archive`` so historical
evidence can be rechecked without moving the live corpus checkout.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile

import build_corpus_exact_manifest as exact
import build_corpus_reviewed_exact_manifest as reviewed
import no_worsening_audit as audit


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
LEDGER_PATH = HERE / "_corpus_source_transition_dd55318.json"
BOUNDARY_SUCCESSOR_PATH = (
    HERE / "_word_anno_boundary_transition_dd55318_u2019.json"
)
BOUNDARY_SUCCESSOR_SHA256 = (
    "149B0E3C085D99E3269504FA6AC23E65F0375DA65B9783C270817350F368317F"
)

PARENT = "ccb9398eef2a81eaf7e038e67848f89ad3997029"
PARENT_TREE = "250af9cf8dd9011cd296604787584c516ed2fb79"
CANDIDATE = "dd55318c33b36128e64561d4ae7fca587ad974fa"
CANDIDATE_TREE = "8ceca918f5a54fd04a09f1af73c8ee4c65accd81"
EMPTY_SHA256 = "E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855"
CHANGED_PATH = (
    "revuoj/revuo-orienta/2025/"
    "2512_revuo_hasegawa_teru_kun_japana_traduko.html"
)
EXPECTED_SCOPE = {
    "content_files": 170,
    "raw_ruby": 350519,
    "parsed_ruby": 350519,
    "parsed_units": 272297,
    "evaluable_instances": 271079,
    "canonical_surfaces": 21572,
    "canonical_case_rows": 21580,
}
EXPECTED_DELTA = {
    "removed": [{
        "surface": "radioelsendo",
        "typed": "R:radi|L:o|R:el|R:send|L:o",
        "count": 1,
    }],
    "added": [{
        "surface": "radioelsendo",
        "typed": "R:radio|R:el|R:send|L:o",
        "count": 1,
    }],
}
EXPECTED_POLICY = {
    "source_only_transition": True,
    "corpus_change_reviewed": True,
    "ruby_track_coarse_media_root": "radio",
    "split_for_width_allowed": False,
    "app_runtime_rules_changed_by_transition": False,
    "word_anno_changed_by_transition": False,
    "kanji_track_changed_by_transition": False,
    "learner_fake_decomposition_changed_by_transition": False,
    "ja_zh_ko_boundary_gate_required": True,
    "historical_ccb9398_evidence_rewritten": False,
}
EXPECTED_BOUNDARY_SUCCESSOR_CANDIDATE = {
    "manifest_path": (
        "_analysis_20260625/_word_anno_boundary_scope_manifest.json"
    ),
    "file_sha256": (
        "D98112F876B1D59134BA65FA26DF117AEB87AB6FBB3203C6988629666BC987A4"
    ),
    "canonical_payload_sha256": (
        "37F68DC06D157D31E3DDD084EA5D29DB503A8DFE54C62964B6CDD54BAF54D6DC"
    ),
    "authority_keys": 49388,
    "authority_sha256": (
        "E8170C94E71542A33940102317BA68AEE0E351B4F3AA1D7BC47B99364C172DEE"
    ),
    "expected_key_counts": {"ja": 49349, "zh": 49388, "ko": 49388},
}
BOUNDARY_SPEC_KEYS = {
    "manifest_path", "file_sha256", "canonical_payload_sha256",
    "authority_keys", "authority_sha256", "expected_key_counts",
}


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def canonical_hash(value) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return sha256_bytes(raw)


def git(repo: Path, *args: str, binary: bool = False):
    completed = subprocess.run(
        ["git", *args], cwd=repo, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False,
    )
    if completed.returncode:
        raise ValueError(
            f"git {' '.join(args)} failed: "
            + completed.stderr.decode("utf-8", errors="replace").strip()
        )
    if binary:
        return completed.stdout
    return completed.stdout.decode("utf-8", errors="strict").strip()


def read_json_with_hash(relative: str, expected_sha256: str) -> dict:
    path = ROOT / relative
    raw = path.read_bytes()
    if sha256_bytes(raw) != expected_sha256:
        raise ValueError(f"sealed file hash changed: {relative}")
    return json.loads(raw.decode("utf-8"))


def source_boundary_parent(ledger: dict) -> dict:
    """Project the former active boundary seal as immutable parent evidence."""
    spec = ledger["active_manifests"]["word_anno_boundary"]
    if set(spec) != {
        "path", "file_sha256", "canonical_payload_sha256",
        "authority_keys", "authority_sha256", "expected_key_counts",
    }:
        raise ValueError("historical word_anno boundary schema changed")
    return {
        "manifest_path": spec["path"],
        "file_sha256": spec["file_sha256"],
        "canonical_payload_sha256": spec["canonical_payload_sha256"],
        "authority_keys": spec["authority_keys"],
        "authority_sha256": spec["authority_sha256"],
        "expected_key_counts": spec["expected_key_counts"],
    }


def read_boundary_successor() -> dict:
    raw = BOUNDARY_SUCCESSOR_PATH.read_bytes()
    if sha256_bytes(raw) != BOUNDARY_SUCCESSOR_SHA256:
        raise ValueError("sealed U+2019 boundary successor ledger changed")
    return json.loads(raw.decode("utf-8"))


def validate_boundary_successor_link(ledger: dict, successor: dict) -> None:
    """Close dd55318 source evidence into the one-key U+2019 successor."""
    if set(successor) != {
        "schema_version", "ledger_id", "description", "authority",
        "parent", "candidate", "delta", "languages", "policy",
    }:
        raise ValueError("U+2019 boundary successor top-level schema changed")
    if successor.get("schema_version") != 1 or successor.get("ledger_id") != (
        "word-anno-boundary-dd55318-u2019-successor-v1"
    ):
        raise ValueError("U+2019 boundary successor identity changed")

    authority = successor.get("authority", {})
    if set(authority) != {
        "corpus", "historical_ccb9398_transition",
        "corpus_source_transition", "r94_residual_ledger",
    }:
        raise ValueError("U+2019 boundary successor authority schema changed")
    candidate_corpus = ledger["corpus"]["candidate"]
    if authority["corpus"] != {
        "branch": ledger["corpus"]["branch"],
        "head_oid": candidate_corpus["head_oid"],
        "tree_oid": candidate_corpus["tree_oid"],
        "content_sha256": candidate_corpus["content_sha256"],
    }:
        raise ValueError("U+2019 boundary successor corpus authority changed")
    historical = ledger["historical_evidence"]
    if authority["historical_ccb9398_transition"] != (
        historical["word_anno_transition"]
    ):
        raise ValueError("historical ccb9398 boundary transition link changed")
    if authority["r94_residual_ledger"] != {
        key: historical["r94_residual_ledger"][key]
        for key in ("path", "file_sha256")
    }:
        raise ValueError("historical R94 residual link changed")
    source_link = authority["corpus_source_transition"]
    if source_link != {
        "path": "_analysis_20260625/_corpus_source_transition_dd55318.json",
        "file_sha256": sha256_bytes(LEDGER_PATH.read_bytes()),
    }:
        raise ValueError("dd55318 source-transition back-link changed")

    parent = successor.get("parent", {})
    if set(parent) != BOUNDARY_SPEC_KEYS or parent != source_boundary_parent(ledger):
        raise ValueError(
            "U+2019 successor does not exactly preserve the historical parent"
        )
    candidate = successor.get("candidate", {})
    if (
        set(candidate) != BOUNDARY_SPEC_KEYS
        or candidate != EXPECTED_BOUNDARY_SUCCESSOR_CANDIDATE
    ):
        raise ValueError("U+2019 boundary successor candidate identity changed")
    if candidate["manifest_path"] != parent["manifest_path"]:
        raise ValueError("U+2019 boundary successor manifest path changed")


def verify_active_boundary_successor(ledger: dict, successor: dict) -> None:
    """Require the live manifest to be the byte- and meaning-sealed candidate."""
    validate_boundary_successor_link(ledger, successor)
    candidate = successor["candidate"]
    raw = (ROOT / candidate["manifest_path"]).read_bytes()
    if sha256_bytes(raw) != candidate["file_sha256"]:
        raise ValueError("active word_anno boundary file is not U+2019 candidate")
    boundary = json.loads(raw.decode("utf-8"))
    if canonical_hash(boundary) != candidate["canonical_payload_sha256"]:
        raise ValueError("active word_anno boundary payload changed")
    for key in ("authority_keys", "authority_sha256", "expected_key_counts"):
        if boundary.get(key) != candidate[key]:
            raise ValueError(
                f"active word_anno boundary successor changed: {key}"
            )


def validate_ledger(ledger: dict) -> None:
    if set(ledger) != {
        "schema_version", "ledger_id", "description", "corpus",
        "changed_file", "canonical_transition", "active_manifests",
        "historical_evidence", "policy",
    }:
        raise ValueError("source-transition top-level schema changed")
    if ledger.get("schema_version") != 1:
        raise ValueError("unsupported source-transition schema")
    if ledger.get("ledger_id") != (
        "corpus-source-radioelsendo-ccb9398-to-dd55318-v1"
    ):
        raise ValueError("source-transition ledger identity changed")
    corpus = ledger["corpus"]
    if corpus.get("branch") != "agent/r94-kyoto-ruby-audit":
        raise ValueError("candidate corpus branch changed")
    if corpus.get("empty_status_sha256") != EMPTY_SHA256:
        raise ValueError("clean-status identity changed")
    if corpus.get("scope") != EXPECTED_SCOPE:
        raise ValueError("corpus scope closure changed")
    if corpus.get("parent") != {
        "head_oid": PARENT,
        "tree_oid": PARENT_TREE,
        "content_sha256": (
            "05C4A95250515BF3CBCBE382843DC2A48BC255B4A34FDF6F96771237F7D8B79B"
        ),
    }:
        raise ValueError("parent corpus identity changed")
    if corpus.get("candidate") != {
        "head_oid": CANDIDATE,
        "tree_oid": CANDIDATE_TREE,
        "content_sha256": (
            "33ED6EA94E45A5434B3AAE035F8C44D97278ACABA9A83714A0167EC0754C70B8"
        ),
    }:
        raise ValueError("candidate corpus identity changed")
    changed = ledger["changed_file"]
    expected_changed = {
        "path": CHANGED_PATH,
        "added_lines": 1,
        "removed_lines": 1,
        "parent_blob_oid": "f4958b169db2cfdfa8df24ea592f976e6003fc55",
        "candidate_blob_oid": "ffe5ae1b604e657153e0ae2b10ae6be39139f25a",
        "parent_bytes": 65232,
        "candidate_bytes": 65227,
        "parent_sha256": (
            "FE0AA029FF6610CF108EAE041B7E318FE73AA186ACDC9750112B24C57B9494D0"
        ),
        "candidate_sha256": (
            "8C9840590D9C166E545CDCC5ECA4D2757C7CD958F1594844FF864A54556A4400"
        ),
        "full_index_binary_diff_bytes": 3451,
        "full_index_binary_diff_sha256": (
            "AC415D61AEE263DA4F8CC8EEDE942796815EADB464CB6ABB07C06118BB4AD571"
        ),
    }
    if changed != expected_changed:
        raise ValueError("one-file diff closure changed")
    transition = ledger["canonical_transition"]
    if {key: transition.get(key) for key in ("removed", "added")} != EXPECTED_DELTA:
        raise ValueError("canonical radioelsendo delta changed")
    if transition.get("delta_sha256") != canonical_hash(EXPECTED_DELTA):
        raise ValueError("canonical delta hash changed")
    if transition.get("parent_projection_sha256") != (
        "B084464B63875973B1AEFF3941785B825549EDB7B99DA7C921378BA8FC64A9FA"
    ) or transition.get("candidate_projection_sha256") != (
        "9DCBA41A7C2D0690AAA51BA9738F7C83863F0CBDB6735DD106841A66FA6A306B"
    ):
        raise ValueError("canonical projection identity changed")
    if ledger.get("policy") != EXPECTED_POLICY:
        raise ValueError("two-track source-transition policy changed")


def verify_live_git(corpus_root: Path, ledger: dict) -> None:
    corpus = ledger["corpus"]
    if git(corpus_root, "rev-parse", "HEAD") != CANDIDATE:
        raise ValueError("live corpus is not the dd55318 candidate")
    if git(corpus_root, "rev-parse", "HEAD^{tree}") != CANDIDATE_TREE:
        raise ValueError("live corpus candidate tree changed")
    if git(corpus_root, "rev-parse", "HEAD^") != PARENT:
        raise ValueError("dd55318 is no longer the direct ccb9398 successor")
    if git(corpus_root, "rev-parse", f"{PARENT}^{{tree}}") != PARENT_TREE:
        raise ValueError("historical ccb9398 tree changed")
    if git(corpus_root, "branch", "--show-current") != corpus["branch"]:
        raise ValueError("live corpus branch changed")
    status = git(
        corpus_root, "status", "--porcelain=v2", "-z",
        "--untracked-files=all", binary=True,
    )
    if status.count(b"\x00") or sha256_bytes(status) != EMPTY_SHA256:
        raise ValueError("live corpus checkout is dirty")


def verify_one_file_diff(corpus_root: Path, ledger: dict) -> None:
    expected = ledger["changed_file"]
    names = git(
        corpus_root, "diff", "--name-only", "-z", PARENT, CANDIDATE, "--",
        binary=True,
    ).decode("utf-8").split("\x00")
    names = [name for name in names if name]
    if names != [CHANGED_PATH]:
        raise ValueError(f"corpus changed-file closure drifted: {names!r}")
    numstat = git(
        corpus_root, "diff", "--numstat", PARENT, CANDIDATE, "--",
        CHANGED_PATH,
    ).split("\t")
    if numstat != ["1", "1", CHANGED_PATH]:
        raise ValueError(f"radioelsendo line delta changed: {numstat!r}")
    parent_blob = git(corpus_root, "rev-parse", f"{PARENT}:{CHANGED_PATH}")
    candidate_blob = git(
        corpus_root, "rev-parse", f"{CANDIDATE}:{CHANGED_PATH}",
    )
    if parent_blob != expected["parent_blob_oid"]:
        raise ValueError("parent HTML blob changed")
    if candidate_blob != expected["candidate_blob_oid"]:
        raise ValueError("candidate HTML blob changed")
    parent_raw = git(
        corpus_root, "show", f"{PARENT}:{CHANGED_PATH}", binary=True,
    )
    candidate_raw = git(
        corpus_root, "show", f"{CANDIDATE}:{CHANGED_PATH}", binary=True,
    )
    for label, raw in (("parent", parent_raw), ("candidate", candidate_raw)):
        if len(raw) != expected[f"{label}_bytes"]:
            raise ValueError(f"{label} HTML byte count changed")
        if sha256_bytes(raw) != expected[f"{label}_sha256"]:
            raise ValueError(f"{label} HTML hash changed")
    if (corpus_root / CHANGED_PATH).read_bytes() != candidate_raw:
        raise ValueError("working-tree HTML differs from candidate blob")
    binary_diff = git(
        corpus_root, "diff", "--binary", "--full-index", PARENT,
        CANDIDATE, "--", binary=True,
    )
    if (
        len(binary_diff) != expected["full_index_binary_diff_bytes"]
        or sha256_bytes(binary_diff)
        != expected["full_index_binary_diff_sha256"]
    ):
        raise ValueError("sealed full-index corpus diff changed")


def archive_revision(corpus_root: Path, revision: str, destination: Path) -> None:
    raw = git(
        corpus_root, "archive", "--format=zip", revision, binary=True,
    )
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        archive.extractall(destination)


def project_corpus(corpus_root: Path):
    cases = {}
    scope = audit.corpus_cases(cases, corpus_root)
    rows = []
    for (surface, signature), case in cases.items():
        if not audit.evaluable(surface):
            continue
        sources = case["sources"]
        if set(sources) != {"html_corpus"}:
            raise ValueError(f"unexpected corpus case source: {surface!r}")
        rows.append({
            "surface": surface,
            "typed": audit.display_typed_parts(list(signature[1])),
            "count": sources["html_corpus"],
        })
    rows.sort(key=lambda row: (row["surface"], row["typed"]))
    projected_scope = {
        "content_files": scope["files"],
        "raw_ruby": scope["raw_ruby"],
        "parsed_ruby": scope["parsed_ruby"],
        "parsed_units": scope["parsed_units"],
        "evaluable_instances": scope["word_alphabet_units"],
        "canonical_surfaces": len({row["surface"] for row in rows}),
        "canonical_case_rows": len(rows),
    }
    if sum(row["count"] for row in rows) != scope["word_alphabet_units"]:
        raise ValueError("canonical case instance closure changed")
    return projected_scope, rows


def rows_counter(rows: list[dict]) -> collections.Counter:
    return collections.Counter({
        (row["surface"], row["typed"]): row["count"] for row in rows
    })


def counter_rows(counter: collections.Counter) -> list[dict]:
    return [
        {"surface": surface, "typed": typed, "count": count}
        for (surface, typed), count in sorted(counter.items())
        if count
    ]


def rich_radioelsendo(corpus_root: Path) -> list[dict]:
    text = (corpus_root / CHANGED_PATH).read_text(
        encoding="utf-8", errors="strict",
    )
    matches = [
        parts for surface, parts in reviewed.parse_corpus_words_rich(text)
        if audit.canonical(surface) == "radioelsendo"
    ]
    if len(matches) != 1:
        raise ValueError(
            f"expected exactly one singular radioelsendo: {len(matches)}"
        )
    return [
        {"piece": piece, "ruby": is_ruby, "rt": gloss}
        for piece, is_ruby, gloss in matches[0]
    ]


def verify_corpus_transition(corpus_root: Path, ledger: dict) -> None:
    current_fingerprint = audit.corpus_content_fingerprint(corpus_root)
    candidate = ledger["corpus"]["candidate"]
    if current_fingerprint != {
        "files": EXPECTED_SCOPE["content_files"],
        "sha256": candidate["content_sha256"],
    }:
        raise ValueError("candidate corpus content fingerprint changed")
    with tempfile.TemporaryDirectory(prefix="corpus_ccb9398_") as raw_temp:
        parent_root = Path(raw_temp)
        archive_revision(corpus_root, PARENT, parent_root)
        parent_fingerprint = audit.corpus_content_fingerprint(parent_root)
        if parent_fingerprint != {
            "files": EXPECTED_SCOPE["content_files"],
            "sha256": ledger["corpus"]["parent"]["content_sha256"],
        }:
            raise ValueError("archived parent corpus fingerprint changed")
        parent_scope, parent_rows = project_corpus(parent_root)
        candidate_scope, candidate_rows = project_corpus(corpus_root)
        if parent_scope != EXPECTED_SCOPE or candidate_scope != EXPECTED_SCOPE:
            raise ValueError("parent/candidate corpus scope is not identical")
        transition = ledger["canonical_transition"]
        if canonical_hash(parent_rows) != transition["parent_projection_sha256"]:
            raise ValueError("parent canonical projection changed")
        if canonical_hash(candidate_rows) != transition["candidate_projection_sha256"]:
            raise ValueError("candidate canonical projection changed")
        parent_counter = rows_counter(parent_rows)
        candidate_counter = rows_counter(candidate_rows)
        delta = {
            "removed": counter_rows(parent_counter - candidate_counter),
            "added": counter_rows(candidate_counter - parent_counter),
        }
        if delta != EXPECTED_DELTA or canonical_hash(delta) != transition["delta_sha256"]:
            raise ValueError(f"canonical transition is not one closed case: {delta!r}")
        if rich_radioelsendo(parent_root) != transition["parent_rich"]:
            raise ValueError("parent radioelsendo rb/rt evidence changed")
        if rich_radioelsendo(corpus_root) != transition["candidate_rich"]:
            raise ValueError("candidate radioelsendo rb/rt evidence changed")


def manifest_hashes(payload: dict, row_key: str) -> dict:
    return {
        "rows_sha256": canonical_hash(payload[row_key]),
        "annotations_sha256": canonical_hash(payload["annotations"]),
        "non_source_sha256": canonical_hash({
            # Description prose is documentation, not an executable rule.
            key: value for key, value in payload.items()
            if key not in {"source", "description"}
        }),
    }


def verify_active_manifests(corpus_root: Path, ledger: dict) -> None:
    sections = ledger["active_manifests"]
    exact_spec = sections["exact"]
    active_exact = read_json_with_hash(
        exact_spec["path"], exact_spec["file_sha256"],
    )
    rebuilt_exact = exact.build(corpus_root)
    if exact.semantic_manifest(active_exact) != exact.semantic_manifest(rebuilt_exact):
        raise ValueError("active exact manifest is stale for dd55318")
    if active_exact.get("counts") != exact_spec["counts"]:
        raise ValueError("exact manifest counts changed")
    if manifest_hashes(active_exact, "exact_surfaces") != {
        key: exact_spec[key]
        for key in ("rows_sha256", "annotations_sha256", "non_source_sha256")
    }:
        raise ValueError("exact manifest runtime content changed")

    reviewed_spec = sections["reviewed"]
    active_reviewed = read_json_with_hash(
        reviewed_spec["path"], reviewed_spec["file_sha256"],
    )
    if (
        active_reviewed.get("source", {}).get("report", {}).get("sha256")
        != reviewed_spec["report_sha256"]
    ):
        raise ValueError("reviewed ccb selection authority changed")
    selected = {
        row["surface"]: set(row["available_expected_options"])
        for row in active_reviewed["exact_surfaces"]
    }
    rebuilt_reviewed = reviewed.build(
        corpus_root, selected, active_reviewed["source"]["report"],
    )
    if (
        reviewed.semantic_manifest(active_reviewed)
        != reviewed.semantic_manifest(rebuilt_reviewed)
    ):
        raise ValueError("active reviewed-exact manifest is stale for dd55318")
    if active_reviewed.get("counts") != reviewed_spec["counts"]:
        raise ValueError("reviewed-exact manifest counts changed")
    if manifest_hashes(active_reviewed, "exact_surfaces") != {
        key: reviewed_spec[key]
        for key in ("rows_sha256", "annotations_sha256", "non_source_sha256")
    }:
        raise ValueError("reviewed-exact runtime content changed")

    for payload in (active_exact, active_reviewed):
        source = payload.get("source", {})
        for key, expected in (
            ("head_oid", CANDIDATE),
            ("content_sha256", ledger["corpus"]["candidate"]["content_sha256"]),
            ("content_files", EXPECTED_SCOPE["content_files"]),
            ("raw_ruby", EXPECTED_SCOPE["raw_ruby"]),
            ("parsed_ruby", EXPECTED_SCOPE["parsed_ruby"]),
            ("parsed_units", EXPECTED_SCOPE["parsed_units"]),
        ):
            if source.get(key) != expected:
                raise ValueError(f"active manifest source changed: {key}")

    # The boundary seal embedded in this immutable source-transition ledger is
    # no longer the live state: it is the exact parent of the separately
    # reviewed U+2019 one-key successor.  Validate both links instead of
    # silently treating the historical parent as current.
    verify_active_boundary_successor(ledger, read_boundary_successor())


def verify_historical_evidence(ledger: dict) -> None:
    evidence = ledger["historical_evidence"]
    residual = read_json_with_hash(
        evidence["r94_residual_ledger"]["path"],
        evidence["r94_residual_ledger"]["file_sha256"],
    )
    if (
        residual.get("authority", {}).get("corpus", {}).get("head_oid")
        != PARENT
        or evidence["r94_residual_ledger"].get("corpus_head_oid") != PARENT
    ):
        raise ValueError("historical R94 residual authority changed")
    reviewed_transition = read_json_with_hash(
        evidence["reviewed_evidence_transition"]["path"],
        evidence["reviewed_evidence_transition"]["file_sha256"],
    )
    if reviewed_transition.get("candidate", {}).get("head_oid") != PARENT:
        raise ValueError("historical reviewed transition no longer ends at ccb9398")
    boundary_transition = read_json_with_hash(
        evidence["word_anno_transition"]["path"],
        evidence["word_anno_transition"]["file_sha256"],
    )
    if boundary_transition.get("corpus_authority", {}).get("head_oid") != PARENT:
        raise ValueError("historical word_anno transition authority changed")


def check(corpus_root: Path) -> dict:
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    validate_ledger(ledger)
    verify_live_git(corpus_root, ledger)
    verify_one_file_diff(corpus_root, ledger)
    verify_corpus_transition(corpus_root, ledger)
    verify_active_manifests(corpus_root, ledger)
    verify_historical_evidence(ledger)
    return {
        "ledger_id": ledger["ledger_id"],
        "parent": PARENT,
        "candidate": CANDIDATE,
        "changed_files": 1,
        "canonical_removed": 1,
        "canonical_added": 1,
        "scope": EXPECTED_SCOPE,
        "app_runtime_rules_changed": False,
        "word_anno_changed": False,
        "kanji_track_changed": False,
        "ja_zh_ko_gate_required": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args()
    raw_corpus = os.environ.get("ESP_CORPUS_PATH", "").strip()
    if not raw_corpus:
        raise SystemExit("ESP_CORPUS_PATH is required")
    corpus_root = Path(raw_corpus).resolve()
    if not corpus_root.is_dir():
        raise SystemExit(f"ESP_CORPUS_PATH is not a directory: {corpus_root}")
    print(json.dumps(check(corpus_root), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
