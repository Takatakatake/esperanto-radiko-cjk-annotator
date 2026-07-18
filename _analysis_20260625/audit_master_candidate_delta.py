# -*- coding: utf-8 -*-
"""Fail-closed candidate audit by exact render-input delta equivalence.

This is deliberately a candidate-only companion to
``audit_master_3lang_full_snapshot.py``.  It does not regenerate app assets.
It proves that two frozen masters project to the same ordered runtime surface
union, inherits only deterministic render facts from an exact baseline report,
and re-renders every changed decomposition surface in all three languages.
Fake/coarse authority is recomputed separately and is never inherited blindly.
"""
from __future__ import annotations

import argparse
import ast
import collections
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import re
import subprocess
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from atomic_json import atomic_json_dump
import audit_master_3lang_full_snapshot as full
import no_worsening_audit as audit


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def semantic_text_sha256(raw: bytes) -> str:
    """Normalize only line endings, which Python and JSON treat identically."""
    return sha256_bytes(raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n"))


def canonical_json(value) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")


def json_sha256(value) -> str:
    return sha256_bytes(canonical_json(value))


def environment_identity() -> dict:
    packages = {}
    for name in ("pandas", "numpy", "streamlit"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "packages": packages,
    }


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True, encoding="utf-8",
    ).strip()


def git_bytes(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=ROOT)


APP_RUNTIME_DEPENDENCY_PATHS = (
    "Esperanto-Kanji-Ruby-JA",
    "Esperanto-Kanji-Ruby-ZH",
    "Esperanto-Kanji-Ruby-KO",
)
# no_worsening_audit imports these local modules at module load.  Only
# extract_lib and the atomic-hyphen review feed the render path directly, but
# every imported local module is bound as an execution dependency so import
# side effects cannot be hidden by a dirty worktree.
ANALYSIS_RUNTIME_DEPENDENCY_PATHS = (
    "_analysis_20260625/no_worsening_audit.py",
    "_analysis_20260625/extract_lib.py",
    "_analysis_20260625/atomic_json.py",
    "_analysis_20260625/gold_snapshot.py",
    "_analysis_20260625/gen_replacement.py",
    "_analysis_20260625/build_fake_coarse_phase511_transition_review.py",
    "_analysis_20260625/_no_worsening_atomic_hyphen_roots.json",
)
RUNTIME_DEPENDENCY_PATHS = (
    *APP_RUNTIME_DEPENDENCY_PATHS,
    *ANALYSIS_RUNTIME_DEPENDENCY_PATHS,
)
PHASE513_DEFAULT_AUTHORITY_SHA256 = (
    "5D8A5671E810FB191924CEE696E65E69A0BBE4CAF37160CEC5973876C20DAEA3"
)
HARNESS_CANDIDATE_ONLY_FUNCTIONS = {
    "load_fake_coarse_authority", "parse_args", "run", "main",
}


def render_harness_ast_sha256(raw: bytes) -> str:
    """Fingerprint render semantics while excluding candidate orchestration.

    Candidate authority loading and report assembly intentionally differ from
    the baseline.  Imports, constants and every parsing/rendering helper must
    remain AST-identical before deterministic full-render facts are inherited.
    """
    module = ast.parse(raw.decode("utf-8-sig"))
    module.body = [
        node for node in module.body
        if not (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name in HARNESS_CANDIDATE_ONLY_FUNCTIONS
        )
    ]
    return sha256_bytes(
        ast.dump(module, annotate_fields=True, include_attributes=False)
        .encode("utf-8")
    )


def runtime_dependency_identity(commit: str) -> dict:
    return {
        path: git("rev-parse", f"{commit}:{path}")
        for path in RUNTIME_DEPENDENCY_PATHS
    }


def commit_app_input_fingerprints(commit: str, actual: dict) -> dict:
    """Hash the exact committed blobs for every runtime input read on disk."""
    return {
        language: {
            path: sha256_bytes(git_bytes("show", f"{commit}:{path}"))
            for path in paths
        }
        for language, paths in actual.items()
    }


def committed_file_fingerprints(commit: str, paths: tuple[str, ...]) -> dict:
    return {
        path: semantic_text_sha256(git_bytes("show", f"{commit}:{path}"))
        for path in paths
    }


def working_file_fingerprints(paths: tuple[str, ...]) -> dict:
    return {
        path: semantic_text_sha256((ROOT / path).read_bytes()) for path in paths
    }


def working_runtime_dependency_state() -> dict:
    """Reject tracked, staged, or untracked runtime dependency drift."""
    commands = {
        "unstaged_clean": [
            "git", "diff", "--quiet", "--", *RUNTIME_DEPENDENCY_PATHS,
        ],
        "staged_clean": [
            "git", "diff", "--cached", "--quiet", "HEAD", "--",
            *RUNTIME_DEPENDENCY_PATHS,
        ],
    }
    state = {}
    for label, command in commands.items():
        completed = subprocess.run(command, cwd=ROOT, check=False)
        if completed.returncode not in (0, 1):
            raise subprocess.CalledProcessError(completed.returncode, command)
        state[label] = completed.returncode == 0
    untracked = git(
        "ls-files", "--others", "--exclude-standard", "--",
        *RUNTIME_DEPENDENCY_PATHS,
    ).splitlines()
    state["untracked"] = untracked
    state["clean"] = (
        state["unstaged_clean"] and state["staged_clean"] and not untracked
    )
    return state


def validate_candidate_control_identity(
    candidate_manifest: dict, transition_dispositions: dict, ledger: dict,
) -> tuple[dict, int]:
    source_hashes = ledger.get("sources")
    candidate_phase = ledger.get("source_phase")
    if (
        not isinstance(source_hashes, dict)
        or not isinstance(candidate_phase, int)
        or transition_dispositions.get("source_phase") != candidate_phase
    ):
        raise ValueError("candidate ledger source phases differ")
    manifest_sources = candidate_manifest.get("sources", {})
    if (
        manifest_sources.get("learner", {}).get("sha256")
        != source_hashes.get("candidate_learner_sha256")
        or manifest_sources.get("academic", {}).get("sha256")
        != source_hashes.get("candidate_academic_sha256")
        or not manifest_sources.get("pejvo_original", {}).get("sha256")
    ):
        raise ValueError("candidate manifest and Ruby ledger sources differ")
    return source_hashes, candidate_phase


def transition_scope_gate(results: list[dict], expected_scopes: dict) -> bool:
    expected_rows = sum(expected_scopes.values())
    return all(
        row["counts"].get("transition_rows", 0) == expected_rows
        and row["counts"].get("transition_matched", 0) == expected_rows
        and row["counts"].get("transition_mismatched", 0) == 0
        and {
            scope: counts.get("matched", 0)
            for scope, counts in row["transition_scopes"].items()
        } == expected_scopes
        and all(
            counts.get("mismatched", 0) == 0
            for counts in row["transition_scopes"].values()
        )
        for row in results
    )


def validate_report_path(
    report_path: Path, input_paths: list[Path], protected_roots: tuple[Path, ...],
) -> None:
    if (
        report_path in input_paths
        or any(report_path.is_relative_to(root) for root in protected_roots)
    ):
        raise ValueError(
            "candidate report path overlaps a bound input or protected runtime/"
            "snapshot directory"
        )


def porcelain_status() -> list[str]:
    return git("status", "--porcelain=v1", "--untracked-files=all").splitlines()


def find_by_sha(directory: Path, expected_sha256: str) -> Path:
    matches = [
        path for path in directory.iterdir()
        if path.is_file() and sha256_file(path) == expected_sha256.upper()
    ]
    if len(matches) != 1:
        raise ValueError(
            f"expected exactly one {expected_sha256} file in {directory}, "
            f"found {matches!r}"
        )
    return matches[0]


def metadata_free_rhs(line: str) -> str:
    if ":" not in line:
        return line.strip()
    return re.split(r"\s*##", line.split(":", 1)[1], maxsplit=1)[0].strip()


def decomposition(line: str) -> str:
    return line.lstrip("\ufeff").split(":", 1)[0].strip()


def changed_raw_rows(old_text: str, new_text: str) -> list[dict]:
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    if len(old_lines) != len(new_lines):
        raise ValueError("master line count changed")
    rows = []
    for line_number, (old_line, new_line) in enumerate(
        zip(old_lines, new_lines), 1,
    ):
        if old_line == new_line:
            continue
        old_decomposition = decomposition(old_line)
        new_decomposition = decomposition(new_line)
        old_surface = audit.canonical(old_decomposition.replace("/", ""))
        new_surface = audit.canonical(new_decomposition.replace("/", ""))
        old_gloss = metadata_free_rhs(old_line)
        new_gloss = metadata_free_rhs(new_line)
        rows.append({
            "line": line_number,
            "surface": old_surface,
            "old_decomposition": audit.canonical(old_decomposition),
            "new_decomposition": audit.canonical(new_decomposition),
            "surface_unchanged": old_surface == new_surface,
            "gloss_unchanged_before_metadata": old_gloss == new_gloss,
        })
    return rows


def parse_snapshot(
    directory: Path, learner_sha: str, academic_sha: str,
    *, learner_path: Path | None = None, academic_path: Path | None = None,
) -> dict:
    directory = directory.resolve()
    learner = (
        learner_path.resolve() if learner_path is not None
        else find_by_sha(directory, learner_sha)
    )
    academic = (
        academic_path.resolve() if academic_path is not None
        else find_by_sha(directory, academic_sha)
    )
    if learner.parent != directory or academic.parent != directory:
        raise ValueError("bound snapshot path escaped its frozen directory")
    if (
        sha256_file(learner) != learner_sha.upper()
        or sha256_file(academic) != academic_sha.upper()
    ):
        raise ValueError("bound snapshot identity changed before parsing")
    learner_parsed = full.parse_gold(learner, learner_sha)
    academic_parsed = full.parse_gold(academic, academic_sha)
    return {
        "directory": directory,
        "learner": learner,
        "academic": academic,
        "learner_parsed": learner_parsed,
        "academic_parsed": academic_parsed,
    }


def record_projection(records: list[dict]) -> list[dict]:
    return [{
        "line": row["line_number"],
        "surface": row["surface"],
        "features": row["features"],
        "fast_scope": row["fast_scope"],
        "fast_key": row["fast_key"],
    } for row in records]


def parse_accounting(parsed) -> dict:
    (_raw, text, records, exclusions, exclusion_rows,
     feature_counts, fast_counts) = parsed
    projection = record_projection(records)
    return {
        "lines": len(text.splitlines()),
        "runtime_candidate_lines": len(records),
        "excluded_lines": sum(exclusions.values()),
        "exclusions": dict(exclusions),
        "exclusion_rows_sha256": json_sha256(dict(exclusion_rows)),
        "feature_counts": dict(feature_counts),
        "fast_counts": dict(fast_counts),
        "projection_sha256": json_sha256(projection),
    }


def surface_scopes(records: list[dict], authority_rows: list[dict]) -> dict:
    full_surfaces = sorted({row["surface"] for row in records})
    fast_surfaces = sorted({
        row["fast_key"] for row in records if row["fast_key"] is not None
    })
    authority_surfaces = sorted({row["surface"] for row in authority_rows})
    render_union = sorted(
        set(full_surfaces) | set(fast_surfaces) | set(authority_surfaces)
    )
    return {
        "full": full_surfaces,
        "fast": fast_surfaces,
        "authority": authority_surfaces,
        "render_union": render_union,
    }


def scope_identity(scopes: dict) -> dict:
    full_set = set(scopes["full"])
    fast_set = set(scopes["fast"])
    authority_set = set(scopes["authority"])
    return {
        "full_unique": len(full_set),
        "full_sha256": json_sha256(scopes["full"]),
        "fast_unique": len(fast_set),
        "fast_sha256": json_sha256(scopes["fast"]),
        "legacy_fast_only": len(fast_set - full_set),
        "authority_unique": len(authority_set),
        "authority_only": len(authority_set - full_set - fast_set),
        "authority_only_sha256": json_sha256(sorted(
            authority_set - full_set - fast_set
        )),
        "render_union_unique": len(scopes["render_union"]),
        "render_union_sha256": json_sha256(scopes["render_union"]),
    }


def build_delta_surface_records(
    surfaces: list[str], records: list[dict], authority_rows: list[dict],
) -> dict:
    by_surface = collections.defaultdict(list)
    for row in records:
        by_surface[row["surface"]].append(row)
    authority_by_surface = collections.defaultdict(list)
    for row in authority_rows:
        authority_by_surface[row["surface"]].append(row)
    result = {}
    for surface in surfaces:
        rows = by_surface[surface]
        if not rows:
            raise ValueError(f"changed surface disappeared: {surface!r}")
        line_numbers = sorted({row["line_number"] for row in rows})
        fast_scope = any(row["fast_key"] == surface for row in rows)
        authority_scope = surface in authority_by_surface
        result[surface] = {
            "surface": surface,
            "line_numbers": line_numbers,
            "decompositions": list(dict.fromkeys(
                row["decomposition"] for row in rows
            )),
            "line_count": len(line_numbers),
            "full_line_count": len(rows),
            "fast_line_count": sum(row["fast_key"] == surface for row in rows),
            "authority_line_count": len(authority_by_surface[surface]),
            "full_scope": True,
            "fast_scope": fast_scope,
            "authority_scope": authority_scope,
            "scopes": [
                scope for scope, present in (
                    ("full_exact", True),
                    ("legacy_fast", fast_scope),
                    ("fake_coarse_authority", authority_scope),
                ) if present
            ],
        }
    return result


def payload_key(payload: dict) -> str:
    return canonical_json(payload).decode("utf-8")


def baseline_observed_by_surface(
    baseline: dict, old_authority: list[dict], language: str,
) -> dict[str, dict]:
    language_row = next(
        row for row in baseline["coarse_authority"]["languages"]
        if row["language"] == language
    )
    mismatches = {
        row["learner_line"]: row for row in language_row["mismatches"]
    }
    observed = {}
    reproduced_matches = 0
    reproduced_mismatches = 0
    for row in old_authority:
        payload = (
            mismatches[row["learner_line"]]["observed"]
            if row["learner_line"] in mismatches
            else full.structural_payload(row["expected"])
        )
        expected = full.structural_payload(row["expected"])
        if payload_key(payload) == payload_key(expected):
            reproduced_matches += 1
        else:
            reproduced_mismatches += 1
        previous = observed.setdefault(row["surface"], payload)
        if payload_key(previous) != payload_key(payload):
            raise ValueError(
                f"baseline runtime structure differs for duplicate {row['surface']}"
            )
    expected_counts = language_row["counts"]
    if (
        reproduced_matches != expected_counts.get("matched")
        or reproduced_mismatches != expected_counts.get("mismatched")
    ):
        raise ValueError(f"could not reproduce baseline authority for {language}")
    return observed


def candidate_authority_result(
    rows: list[dict], observed_by_surface: dict[str, dict],
) -> dict:
    counts = collections.Counter()
    scope_counts = collections.defaultdict(collections.Counter)
    outcomes = []
    mismatched_lines = []
    matched_lines = []
    for row in rows:
        counts["rows"] += 1
        observed = observed_by_surface.get(row["surface"])
        if observed is None:
            raise ValueError(
                f"candidate authority surface was not assessed: {row['surface']}"
            )
        expected = full.structural_payload(row["expected"])
        matched = payload_key(observed) == payload_key(expected)
        state = "matched" if matched else "mismatched"
        counts[state] += 1
        (matched_lines if matched else mismatched_lines).append(
            row["learner_line"]
        )
        if row["transition_required"]:
            counts["transition_rows"] += 1
            counts[f"transition_{state}"] += 1
            scope_counts[row["transition_scope"]][state] += 1
        outcomes.append({
            "line": row["learner_line"],
            "surface": row["surface"],
            "matched": matched,
            "selected_decomposition": row["selected_decomposition"],
            "transition_required": row["transition_required"],
            "transition_scope": row["transition_scope"],
        })
    return {
        "counts": dict(counts),
        "transition_scopes": {
            scope: dict(values) for scope, values in sorted(scope_counts.items())
        },
        "matched_line_numbers_sha256": json_sha256(sorted(matched_lines)),
        "mismatched_line_numbers_sha256": json_sha256(sorted(mismatched_lines)),
        "all_outcomes_sha256": json_sha256(outcomes),
        "outcomes": outcomes,
    }


def validate_ledger(path: Path, changed_surfaces: set[str], sources: dict) -> dict:
    raw = path.read_bytes()
    ledger = json.loads(raw.decode("utf-8"))
    if (
        ledger.get("schema_version") != 1
        or ledger.get("candidate_only") is not True
        or not isinstance(ledger.get("source_phase"), int)
        or ledger.get("promotion_gate") is not False
        or ledger.get("sources") != sources
    ):
        raise ValueError("candidate Ruby-track disposition identity changed")
    groups = ledger.get("groups", {})
    values = [surface for rows in groups.values() for surface in rows]
    if len(values) != len(set(values)):
        raise ValueError("candidate Ruby-track groups overlap")
    if set(values) != changed_surfaces:
        raise ValueError(
            "candidate Ruby-track groups do not cover the exact changed surface set"
        )
    generic_counts = {
        group: len(rows) for group, rows in groups.items()
    }
    generic_counts["union"] = len(values)
    legacy_counts = None
    if set(groups) == {
        "A_kanji_only_deep_boundary_keep_ruby_coarse",
        "B_ruby_alignment_candidate_or_already_aligned",
        "C_ruby_granularity_pending_human_review",
    }:
        legacy_counts = {
            "A": len(groups["A_kanji_only_deep_boundary_keep_ruby_coarse"]),
            "B": len(groups["B_ruby_alignment_candidate_or_already_aligned"]),
            "C": len(groups["C_ruby_granularity_pending_human_review"]),
            "union": len(values),
        }
    counts = (
        legacy_counts
        if ledger["expected_counts"] == legacy_counts
        else generic_counts
    )
    if counts != ledger["expected_counts"]:
        raise ValueError("candidate Ruby-track group counts changed")
    return {
        "path": str(path.resolve()),
        "sha256": sha256_bytes(raw),
        "source_phase": ledger["source_phase"],
        "policy": ledger["policy"],
        "groups": groups,
        "counts": counts,
        "promotion_blockers": ledger["promotion_blockers"],
    }


def inherited_runtime_facts(baseline: dict) -> dict:
    facts = {
        "accounting": {
            key: baseline["accounting"][key] for key in (
                "input_lines", "excluded_lines", "runtime_candidate_lines",
                "runtime_unique_surfaces", "fast_filter_included_unique_surfaces",
                "render_union_unique_surfaces", "legacy_fast_only_synthetic_surfaces",
            )
        },
        "three_language_boundary": {
            key: value for key, value in baseline["three_language_boundary"].items()
            if not isinstance(value, list)
        },
        "languages": [],
    }
    for row in baseline["languages"]:
        width = row["ruby_length_audit"]
        facts["languages"].append({
            "language": row["language"],
            "rendered_unique_surfaces": row["rendered_unique_surfaces"],
            "issue_counts": row["issue_counts"],
            "runtime_sha256": row["runtime_sha256"],
            "overlay_sha256": row["overlay_sha256"],
            "payload_sha256": row["payload_sha256"],
            "char_widths_sha256": row["char_widths_sha256"],
            "effective_width_over_2_unique": (
                width["effective_width_ratio_bins_unique"]["gt_2"]
            ),
            "max_effective_width_ratio": width["max_effective_width_ratio"],
        })
    return facts


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--baseline-master-dir", "--phase513-dir", dest="baseline_master_dir",
        type=Path, required=True,
    )
    parser.add_argument(
        "--candidate-dir", "--phase527-dir", dest="candidate_dir",
        type=Path, required=True,
    )
    parser.add_argument("--baseline-report", type=Path, required=True)
    parser.add_argument("--expected-baseline-report-sha256", required=True)
    parser.add_argument("--candidate-manifest", type=Path, required=True)
    parser.add_argument("--transition-dispositions", type=Path, required=True)
    parser.add_argument("--ruby-dispositions", type=Path, required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--expected-tree", required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args(argv)


def run(args) -> dict:
    baseline_report_path = args.baseline_report.resolve()
    candidate_manifest_path = args.candidate_manifest.resolve()
    transition_dispositions_path = args.transition_dispositions.resolve()
    ruby_dispositions_path = args.ruby_dispositions.resolve()
    baseline_raw = baseline_report_path.read_bytes()
    candidate_manifest_raw = candidate_manifest_path.read_bytes()
    transition_dispositions_raw = transition_dispositions_path.read_bytes()
    ledger_bytes = ruby_dispositions_path.read_bytes()
    baseline = json.loads(baseline_raw.decode("utf-8"))
    candidate_manifest = json.loads(candidate_manifest_raw.decode("utf-8"))
    transition_dispositions = json.loads(
        transition_dispositions_raw.decode("utf-8")
    )
    ledger_raw = json.loads(ledger_bytes.decode("utf-8"))
    source_hashes, candidate_phase = validate_candidate_control_identity(
        candidate_manifest, transition_dispositions, ledger_raw,
    )
    manifest_sources = candidate_manifest["sources"]

    baseline_master_dir = args.baseline_master_dir.resolve()
    candidate_dir = args.candidate_dir.resolve()
    old_learner_path = find_by_sha(
        baseline_master_dir, source_hashes["baseline_learner_sha256"]
    )
    old_academic_path = find_by_sha(
        baseline_master_dir, source_hashes["baseline_academic_sha256"]
    )
    new_learner_path = find_by_sha(
        candidate_dir, source_hashes["candidate_learner_sha256"]
    )
    new_academic_path = find_by_sha(
        candidate_dir, source_hashes["candidate_academic_sha256"]
    )
    candidate_pejvo_path = find_by_sha(
        candidate_dir,
        manifest_sources["pejvo_original"]["sha256"],
    )
    input_paths = [
        baseline_report_path, candidate_manifest_path,
        transition_dispositions_path, ruby_dispositions_path,
        Path(__file__).resolve(), Path(full.__file__).resolve(),
        *(ROOT / path for path in ANALYSIS_RUNTIME_DEPENDENCY_PATHS),
        full.FAKE_COARSE_MANIFEST.resolve(),
        full.FAKE_TRANSITION_MANIFEST.resolve(),
        full.FAKE_FF33_TRANSITION_MANIFEST.resolve(),
        full.FAKE_5E_TRANSITION_MANIFEST.resolve(),
        full.FAKE_PHASE511_TRANSITION_MANIFEST.resolve(),
        old_learner_path, old_academic_path,
        new_learner_path, new_academic_path, candidate_pejvo_path,
    ]
    report_path = args.report.resolve()
    protected_output_roots = (
        baseline_master_dir, candidate_dir,
        *(ROOT / path for path in APP_RUNTIME_DEPENDENCY_PATHS),
    )
    validate_report_path(report_path, input_paths, protected_output_roots)
    input_hashes_at_start = {str(path): sha256_file(path) for path in input_paths}
    current_environment = environment_identity()
    captured_file_hashes = {
        str(baseline_report_path): sha256_bytes(baseline_raw),
        str(candidate_manifest_path): sha256_bytes(candidate_manifest_raw),
        str(transition_dispositions_path): sha256_bytes(
            transition_dispositions_raw
        ),
        str(ruby_dispositions_path): sha256_bytes(ledger_bytes),
    }
    if any(
        input_hashes_at_start[path] != digest
        for path, digest in captured_file_hashes.items()
    ):
        raise ValueError("candidate control file changed while binding inputs")
    status_at_start = porcelain_status()
    runtime_worktree_state_at_start = working_runtime_dependency_state()
    if not runtime_worktree_state_at_start["clean"]:
        raise ValueError("runtime dependencies are dirty in the candidate clone")
    head_at_start = git("rev-parse", "HEAD")
    tree_at_start = git("rev-parse", "HEAD^{tree}")
    app_inputs_at_start = full.app_input_fingerprints()
    if head_at_start != args.expected_head:
        raise ValueError("candidate app HEAD changed")
    if tree_at_start != args.expected_tree:
        raise ValueError("candidate app tree changed")

    if sha256_bytes(baseline_raw) != args.expected_baseline_report_sha256.upper():
        raise ValueError("baseline report identity changed")
    baseline_head = baseline["app"]["head_oid"]
    baseline_tree = git("rev-parse", f"{baseline_head}^{{tree}}")
    head_app_inputs = commit_app_input_fingerprints(
        head_at_start, app_inputs_at_start,
    )
    working_app_inputs_equal_head = app_inputs_at_start == head_app_inputs
    if not working_app_inputs_equal_head:
        raise ValueError("working runtime input bytes differ from candidate HEAD")
    head_analysis_inputs = committed_file_fingerprints(
        head_at_start, ANALYSIS_RUNTIME_DEPENDENCY_PATHS,
    )
    working_analysis_inputs = working_file_fingerprints(
        ANALYSIS_RUNTIME_DEPENDENCY_PATHS,
    )
    working_analysis_input_semantics_equal_head = (
        working_analysis_inputs == head_analysis_inputs
    )
    if not working_analysis_input_semantics_equal_head:
        raise ValueError(
            "working analysis dependency semantics differ from HEAD"
        )
    current_runtime_dependencies = runtime_dependency_identity(head_at_start)
    baseline_runtime_dependencies = runtime_dependency_identity(baseline_head)
    current_harness_sha256 = render_harness_ast_sha256(
        Path(full.__file__).resolve().read_bytes()
    )
    baseline_harness_sha256 = render_harness_ast_sha256(git_bytes(
        "show",
        f"{baseline_head}:_analysis_20260625/audit_master_3lang_full_snapshot.py",
    ))
    baseline_runtime_dependencies_equal = (
        current_runtime_dependencies == baseline_runtime_dependencies
        and current_harness_sha256 == baseline_harness_sha256
    )
    baseline_valid = (
        baseline.get("complete") is True
        and baseline.get("gate") is True
        and all(baseline["inputs_stable"].values())
        and baseline["three_language_boundary"]
        ["render_union_mismatch_unique_surfaces"] == 0
        and baseline["three_language_boundary"]
        ["token_mismatch_unique_contexts"] == 0
        and all(
            all(value == 0 for value in row["issue_counts"].values())
            for row in baseline["languages"]
        )
    )
    if not baseline_valid or not baseline_runtime_dependencies_equal:
        raise ValueError(
            "baseline cannot support exact runtime-dependency inheritance"
        )

    old = parse_snapshot(
        baseline_master_dir,
        source_hashes["baseline_learner_sha256"],
        source_hashes["baseline_academic_sha256"],
        learner_path=old_learner_path,
        academic_path=old_academic_path,
    )
    new = parse_snapshot(
        candidate_dir,
        source_hashes["candidate_learner_sha256"],
        source_hashes["candidate_academic_sha256"],
        learner_path=new_learner_path,
        academic_path=new_academic_path,
    )
    old_learner = old["learner_parsed"]
    old_academic = old["academic_parsed"]
    new_learner = new["learner_parsed"]
    new_academic = new["academic_parsed"]

    old_authority, old_authority_identity = full.load_fake_coarse_authority(
        old_learner[0], old_learner[1], old["academic"],
        source_hashes["baseline_academic_sha256"],
    )
    old_authority_sha256 = json_sha256(old_authority)
    if old_authority_sha256 != PHASE513_DEFAULT_AUTHORITY_SHA256:
        raise ValueError("Phase 513 default coarse authority changed")
    new_authority, new_authority_identity = full.load_fake_coarse_authority(
        new_learner[0], new_learner[1], new["academic"],
        source_hashes["candidate_academic_sha256"],
        candidate_manifest_path,
        transition_dispositions_path,
    )
    if (
        new_authority_identity["candidate_transition_dispositions"]
        ["source_phase"] != candidate_phase
    ):
        raise ValueError("transition and Ruby disposition phases differ")

    old_learner_accounting = parse_accounting(old_learner)
    new_learner_accounting = parse_accounting(new_learner)
    old_academic_accounting = parse_accounting(old_academic)
    new_academic_accounting = parse_accounting(new_academic)
    projection_equal = (
        record_projection(old_learner[2]) == record_projection(new_learner[2])
        and record_projection(old_academic[2]) == record_projection(new_academic[2])
        and old_learner_accounting == new_learner_accounting
        and old_academic_accounting == new_academic_accounting
    )
    if not projection_equal:
        raise ValueError("runtime line projection changed")

    learner_changes = changed_raw_rows(old_learner[1], new_learner[1])
    academic_changes = changed_raw_rows(old_academic[1], new_academic[1])
    if not all(
        row["surface_unchanged"] and row["gloss_unchanged_before_metadata"]
        for row in learner_changes + academic_changes
    ):
        raise ValueError("surface or gloss changed in candidate master")
    changed_surfaces = {
        row["surface"] for row in learner_changes + academic_changes
    }
    ledger = validate_ledger(
        ruby_dispositions_path, changed_surfaces, source_hashes,
    )

    old_scopes = surface_scopes(old_learner[2], old_authority)
    new_scopes = surface_scopes(new_learner[2], new_authority)
    old_scope_identity = scope_identity(old_scopes)
    new_scope_identity = scope_identity(new_scopes)
    baseline_accounting = baseline["accounting"]
    baseline_source_and_accounting_match = (
        baseline["gold"]["sha256"]
        == source_hashes["baseline_learner_sha256"]
        and baseline["coarse_authority"]["academic"]["sha256"]
        == source_hashes["baseline_academic_sha256"]
        and baseline_accounting["runtime_candidate_lines"]
        == old_learner_accounting["runtime_candidate_lines"]
        and baseline_accounting["excluded_lines"]
        == old_learner_accounting["excluded_lines"]
        and baseline_accounting["runtime_unique_surfaces"]
        == old_scope_identity["full_unique"]
        and baseline_accounting["fast_filter_included_unique_surfaces"]
        == old_scope_identity["fast_unique"]
        and baseline_accounting["render_union_unique_surfaces"]
        == old_scope_identity["render_union_unique"]
        and baseline["coarse_authority"]["authority_rows"]
        == len(old_authority)
    )
    if not baseline_source_and_accounting_match:
        raise ValueError("baseline source/accounting does not match Phase 513")
    render_union_equal = old_scopes["render_union"] == new_scopes["render_union"]
    if not render_union_equal:
        raise ValueError("final runtime render union changed")

    delta_surfaces = sorted(changed_surfaces)
    delta_records = build_delta_surface_records(
        delta_surfaces, new_learner[2], new_authority,
    )
    delta_structural = {}
    delta_language_results = []
    for language in full.LANGUAGES:
        structural, language_result = full.render_language(
            language, delta_surfaces, delta_records, len(delta_surfaces),
        )
        delta_structural[language] = structural
        delta_language_results.append(language_result)
    delta_boundary_mismatches = [
        surface for surface in delta_surfaces
        if len({
            json_sha256(full.structural_payload(
                delta_structural[language][surface]
            ))
            for language in full.LANGUAGES
        }) != 1
    ]
    delta_issue_gate = all(
        all(value == 0 for value in row["issue_counts"].values())
        for row in delta_language_results
    )
    if delta_boundary_mismatches or not delta_issue_gate:
        raise ValueError("changed-surface runtime delta failed")

    authority_results = []
    for language in full.LANGUAGES:
        observed = baseline_observed_by_surface(
            baseline, old_authority, language,
        )
        for surface, structure in delta_structural[language].items():
            observed[surface] = full.structural_payload(structure)
        result = candidate_authority_result(new_authority, observed)
        changed_outcomes = [
            row for row in result.pop("outcomes")
            if row["surface"] in changed_surfaces
        ]
        result["language"] = language
        result["changed_surface_outcomes"] = changed_outcomes
        authority_results.append(result)

    authority_signature = {
        language["language"]: {
            "counts": language["counts"],
            "matched": language["matched_line_numbers_sha256"],
            "mismatched": language["mismatched_line_numbers_sha256"],
        }
        for language in authority_results
    }
    authority_three_language_equal = len({
        json_sha256(value) for value in authority_signature.values()
    }) == 1
    expected_transition_scopes = new_authority_identity[
        "transition_manifests"
    ]["active_scope_rows"]
    expected_transition_rows = sum(expected_transition_scopes.values())
    transition_gate = transition_scope_gate(
        authority_results, expected_transition_scopes,
    )

    old_by_line = {row["learner_line"]: row for row in old_authority}
    new_by_line = {row["learner_line"]: row for row in new_authority}
    authority_added = sorted(set(new_by_line) - set(old_by_line))
    authority_removed = sorted(set(old_by_line) - set(new_by_line))

    group_for_surface = {
        surface: group for group, surfaces in ledger["groups"].items()
        for surface in surfaces
    }
    changed_surface_rows = []
    old_learner_by_surface = {
        row["surface"]: row for row in old_learner[2]
    }
    new_learner_by_surface = {
        row["surface"]: row for row in new_learner[2]
    }
    old_academic_by_surface = {
        row["surface"]: row for row in old_academic[2]
    }
    new_academic_by_surface = {
        row["surface"]: row for row in new_academic[2]
    }
    ja_structural = delta_structural["JA"]
    for surface in delta_surfaces:
        observed = ja_structural[surface]
        new_learner_expected = full.expected_expression_structure(
            new_learner_by_surface[surface]["decomposition"]
        )
        new_academic_expected = full.expected_expression_structure(
            new_academic_by_surface[surface]["decomposition"]
        )
        changed_surface_rows.append({
            "surface": surface,
            "group": group_for_surface[surface],
            "line": new_learner_by_surface[surface]["line_number"],
            "baseline_learner": old_learner_by_surface[surface]["decomposition"],
            "candidate_learner": new_learner_by_surface[surface]["decomposition"],
            "baseline_academic": old_academic_by_surface[surface]["decomposition"],
            "candidate_academic": new_academic_by_surface[surface]["decomposition"],
            "runtime_matches_candidate_learner_boundary": (
                observed == new_learner_expected
            ),
            "runtime_matches_candidate_academic_boundary": (
                observed == new_academic_expected
            ),
            "three_language_boundary_equal": True,
            "runtime_line_signature": full.structural_payload(observed)[
                "line_signature"
            ],
        })

    inherited = inherited_runtime_facts(baseline)
    inherited_proof = {
        "baseline_report_valid": baseline_valid,
        "baseline_source_and_accounting_match": (
            baseline_source_and_accounting_match
        ),
        "baseline_runtime_dependencies_equal": (
            baseline_runtime_dependencies_equal
        ),
        "working_runtime_dependencies_clean": (
            runtime_worktree_state_at_start["clean"]
        ),
        "working_app_input_bytes_equal_head": working_app_inputs_equal_head,
        "working_analysis_input_semantics_equal_head": (
            working_analysis_input_semantics_equal_head
        ),
        "baseline_runtime_dependencies": baseline_runtime_dependencies,
        "current_runtime_dependencies": current_runtime_dependencies,
        "working_runtime_dependency_state": runtime_worktree_state_at_start,
        "head_app_input_fingerprints": head_app_inputs,
        "head_analysis_input_fingerprints": head_analysis_inputs,
        "baseline_render_harness_ast_sha256": baseline_harness_sha256,
        "current_render_harness_ast_sha256": current_harness_sha256,
        "phase513_default_authority_sha256": old_authority_sha256,
        "learner_and_academic_runtime_projection_equal": projection_equal,
        "ordered_render_union_equal": render_union_equal,
        "ordered_render_union_sha256": new_scope_identity[
            "render_union_sha256"
        ],
        "deterministic_inputs_equal": all(
            row["rendered_unique_surfaces"]
            == new_scope_identity["render_union_unique"]
            for row in inherited["languages"]
        ),
        "non_inherited_fields": [
            "gold/academic source identity",
            "fake/coarse expected signatures and match counts",
            "transition gate",
            "baseline complete/gate labels",
            "decomposition-bearing examples",
            "render_seconds",
        ],
        "baseline_environment_bound": False,
        "environment_assumption": (
            "The Phase 513 report did not record Python/package versions. "
            "This delta gate therefore requires a new full three-language "
            "audit before promotion."
        ),
        "current_environment": current_environment,
    }

    runtime_gate = (
        all(inherited_proof[key] for key in (
            "baseline_report_valid", "baseline_source_and_accounting_match",
            "baseline_runtime_dependencies_equal",
            "working_runtime_dependencies_clean",
            "working_app_input_bytes_equal_head",
            "working_analysis_input_semantics_equal_head",
            "learner_and_academic_runtime_projection_equal",
            "ordered_render_union_equal", "deterministic_inputs_equal",
        ))
        and not delta_boundary_mismatches
        and delta_issue_gate
        and authority_three_language_equal
        and transition_gate
    )

    retired_surfaces = sorted(
        row["surface"] for row in transition_dispositions["entries"]
    )
    promotion_reason = (
        "Candidate-only; no master or app asset is promoted. Ruby ledger "
        f"blockers: {'; '.join(ledger['promotion_blockers'])}. "
        "Retired transition rows pending review: "
        f"{', '.join(retired_surfaces)}."
    )
    report = {
        "schema_version": 1,
        "algorithm": (
            f"phase513-to-phase{candidate_phase}-exact-render-input-delta-v2"
        ),
        "candidate_only": True,
        "source_phase": candidate_phase,
        "complete_delta_proof": False,
        "complete_delta_proof_reason": (
            "Source, code, data, changed surfaces, and candidate authority are "
            "bound exactly, but the baseline report did not bind interpreter "
            "and package versions. A fresh full audit is required."
        ),
        "runtime_gate": runtime_gate,
        "promotion_gate": False,
        "promotion_gate_reason": promotion_reason,
        "app": {
            "head": head_at_start,
            "tree": tree_at_start,
            "baseline_head": baseline_head,
            "baseline_tree": baseline_tree,
            "status_at_start": status_at_start,
        },
        "baseline": {
            "path": str(args.baseline_report.resolve()),
            "bytes": len(baseline_raw),
            "sha256": sha256_bytes(baseline_raw),
            "proof": inherited_proof,
            "safely_inherited_runtime_facts": inherited,
        },
        "snapshots": {
            "baseline_phase513": {
                "learner": str(old["learner"]),
                "academic": str(old["academic"]),
                "learner_sha256": sha256_file(old["learner"]),
                "academic_sha256": sha256_file(old["academic"]),
            },
            f"candidate_phase{candidate_phase}": {
                "learner": str(new["learner"]),
                "academic": str(new["academic"]),
                "learner_sha256": sha256_file(new["learner"]),
                "academic_sha256": sha256_file(new["academic"]),
            },
        },
        "raw_delta": {
            "learner_changed_lines": len(learner_changes),
            "academic_changed_lines": len(academic_changes),
            "changed_surface_union": len(changed_surfaces),
            "all_surfaces_unchanged": True,
            "all_glosses_unchanged_before_metadata": True,
            "learner_rows": learner_changes,
            "academic_rows": academic_changes,
        },
        "runtime_projection": {
            "equal": projection_equal,
            "baseline_learner": old_learner_accounting,
            "candidate_learner": new_learner_accounting,
            "baseline_academic": old_academic_accounting,
            "candidate_academic": new_academic_accounting,
        },
        "surface_scopes": {
            "equal_ordered_render_union": render_union_equal,
            "baseline": old_scope_identity,
            "candidate": new_scope_identity,
            "render_union_added": sorted(
                set(new_scopes["render_union"]) - set(old_scopes["render_union"])
            ),
            "render_union_removed": sorted(
                set(old_scopes["render_union"]) - set(new_scopes["render_union"])
            ),
        },
        "ruby_track_dispositions": ledger,
        "changed_surface_runtime": {
            "surfaces": len(delta_surfaces),
            "three_language_boundary_mismatches": delta_boundary_mismatches,
            "issue_gate": delta_issue_gate,
            "languages": [{
                "language": row["language"],
                "rendered_unique_surfaces": row["rendered_unique_surfaces"],
                "issue_counts": row["issue_counts"],
                "max_effective_width_ratio": row["ruby_length_audit"]
                ["max_effective_width_ratio"],
                "effective_width_over_2_unique": row["ruby_length_audit"]
                ["effective_width_ratio_bins_unique"]["gt_2"],
            } for row in delta_language_results],
            "rows": changed_surface_rows,
        },
        "candidate_coarse_authority": {
            "old_rows": len(old_authority),
            "new_rows": len(new_authority),
            "old_unique_surfaces": len({row["surface"] for row in old_authority}),
            "new_unique_surfaces": len({row["surface"] for row in new_authority}),
            "added_lines": authority_added,
            "added_surfaces": [new_by_line[line]["surface"] for line in authority_added],
            "removed_lines": authority_removed,
            "removed_surfaces": [old_by_line[line]["surface"] for line in authority_removed],
            "historical_transition_total": 158,
            "active_transition_rows": expected_transition_rows,
            "active_transition_scopes": expected_transition_scopes,
            "retired_pending_transition_rows": new_authority_identity[
                "transition_manifests"
            ]["retired_pending_entries"],
            "three_language_outcomes_equal": authority_three_language_equal,
            "transition_gate": transition_gate,
            "languages": authority_results,
            "candidate_manifest": new_authority_identity["fake_coarse_manifest"],
            "transition_dispositions": new_authority_identity[
                "candidate_transition_dispositions"
            ],
        },
        "stability": {
            "all_inputs_bound_before_parsing": True,
            "input_hashes": input_hashes_at_start,
        },
    }

    status_at_end = porcelain_status()
    head_at_end = git("rev-parse", "HEAD")
    tree_at_end = git("rev-parse", "HEAD^{tree}")
    app_inputs_at_end = full.app_input_fingerprints()
    runtime_worktree_state_at_end = working_runtime_dependency_state()
    hashes_at_end = {str(path): sha256_file(path) for path in input_paths}
    report["app"]["status_at_end"] = status_at_end
    report["stability"].update({
        "head_stable": head_at_end == head_at_start,
        "tree_stable": tree_at_end == tree_at_start,
        "status_stable": status_at_end == status_at_start,
        "app_inputs_stable": app_inputs_at_end == app_inputs_at_start,
        "runtime_dependencies_clean_at_end": (
            runtime_worktree_state_at_end["clean"]
        ),
        "all_inputs_stable": hashes_at_end == input_hashes_at_start,
    })
    if not all(report["stability"][key] for key in (
        "head_stable", "tree_stable", "status_stable", "app_inputs_stable",
        "runtime_dependencies_clean_at_end", "all_inputs_stable",
    )):
        raise ValueError("candidate audit inputs changed while auditing")
    if not runtime_gate:
        raise ValueError("candidate runtime gate failed")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_json_dump(report_path, report, indent=2)
    return report


def main(argv=None) -> None:
    args = parse_args(argv)
    report = run(args)
    print(json.dumps({
        "report": str(args.report.resolve()),
        "candidate_only": report["candidate_only"],
        "runtime_gate": report["runtime_gate"],
        "promotion_gate": report["promotion_gate"],
        "render_union": report["surface_scopes"]["candidate"]
        ["render_union_unique"],
        "changed_surfaces": report["changed_surface_runtime"]["surfaces"],
        "boundary_mismatches": len(report["changed_surface_runtime"]
        ["three_language_boundary_mismatches"]),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
