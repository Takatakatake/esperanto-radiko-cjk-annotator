# -*- coding: utf-8 -*-
"""Run the three closed Phase 558 no-worsening audits without report reuse.

The raw auditor deliberately exits 1 for each reviewed Phase 558 delta.  This
runner accepts that exit status only after a fresh, complete, gate-false report
has been written, and then delegates the closed exception decision to the
Phase 558 sidecar.  The parent-current diagnostic is never overwritten by the
current-e373 audit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RAW_AUDITOR = HERE / "no_worsening_audit.py"
SIDECAR = HERE / "phase558_no_worsening_sidecar_gate.py"
FULL_REPORT = HERE / "out" / "_audit_no_worsening.json"
PARENT_CURRENT_REPORT = HERE / "out" / "_audit_no_worsening_current_only.json"
CURRENT_E373_REPORT = HERE / "out" / "_audit_no_worsening_current_e373.json"
CURRENT_E373_SCOPE = HERE / "_phase558_current_corpus_scope_manifest.json"
CHECKPOINT_DIR = HERE / "out"
CHECKPOINT_GLOB = "_no_worsening_checkpoint_*.json"

BASELINE_REVISION = "dcfca809b711075788ee00b6323cdd2ea31618ff"
PHASE532_GOLD_SHA256 = (
    "6B403AA30BBCBBA4C9E41A2CF48D1AD2FC1D5A5DB1154CAF1260A361566E3226"
)
REQUIRED_ENVIRONMENT = (
    "ESP_GOLD_PATH",
    "ESP_PHASE532_PEJVO_DISAGREEMENT_REVIEW",
    "ESP_PHASE558_PARENT_CORPUS_PATH",
    "ESP_PHASE558_CURRENT_CORPUS_PATH",
)
UTF8_ENVIRONMENT = {
    "PYTHONIOENCODING": "utf-8",
    "PYTHONUTF8": "1",
}


def _git_head() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(
            completed.stderr.decode("utf-8", errors="replace")
        )
    return completed.stdout.decode("ascii").strip()


def _file_identity(path: Path):
    if not path.exists():
        return None
    raw = path.read_bytes()
    return {
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest().upper(),
    }


def _formal_input_state(environ=None) -> dict:
    """Seal the dirty-worktree audit meaning, not merely its Git HEAD.

    The formal audit intentionally runs before commit, so HEAD alone cannot
    detect edits to the runner, auditor, sidecar, policy, or manifests while
    its long-lived children are executing.  All top-level analysis Python and
    JSON inputs are therefore hashed, together with the deployed app inputs
    used by the three runtimes.  Reports/checkpoints live under ``out`` and
    are deliberately outside this immutable input set.
    """
    if environ is None:
        environ = os.environ
    dependencies = sorted(
        {*HERE.glob("*.py"), *HERE.glob("*.json")},
        key=lambda path: path.name,
    )
    identities = {}
    for path in dependencies:
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(
                f"formal audit dependency is not a regular file: {path}"
            )
        identities[path.name] = _file_identity(path)

    import no_worsening_audit as audit

    app_inputs = {
        language: audit.current_app_fingerprint(
            ROOT / f"Esperanto-Kanji-Ruby-{language}"
        )
        for language in ("JA", "ZH", "KO")
    }
    review_value = environ.get("ESP_PHASE532_PEJVO_DISAGREEMENT_REVIEW")
    review_path = Path(review_value).resolve() if review_value else None
    return {
        "analysis_dependencies": identities,
        "deployed_app_inputs": app_inputs,
        "external_phase532_pejvo_review": {
            "path": str(review_path) if review_path is not None else None,
            "identity": (
                _file_identity(review_path)
                if review_path is not None else None
            ),
        },
    }


def _remove_report(path: Path) -> None:
    if path.is_symlink():
        raise RuntimeError(f"refusing to remove report symlink: {path}")
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    if path.exists():
        raise RuntimeError(f"could not remove stale report: {path}")


def _checkpoint_paths() -> list[Path]:
    return sorted(CHECKPOINT_DIR.glob(CHECKPOINT_GLOB), key=lambda path: path.name)


def _remove_checkpoints() -> None:
    """Remove only regular audit checkpoints, refusing every symlink.

    This is called before every explicit fresh raw audit.  It is called again
    only after the matching sidecar succeeds, so a failed raw audit or sidecar
    retains that invocation's checkpoints for forensic inspection.
    """
    checkpoints = _checkpoint_paths()
    for path in checkpoints:
        if path.is_symlink():
            raise RuntimeError(f"refusing to remove checkpoint symlink: {path}")
        if not path.is_file():
            raise RuntimeError(f"checkpoint is not a regular file: {path}")
    for path in checkpoints:
        if path.is_symlink():
            raise RuntimeError(f"checkpoint became a symlink: {path}")
        path.unlink()
    remaining = _checkpoint_paths()
    if remaining:
        raise RuntimeError(f"checkpoint cleanup incomplete: {remaining}")


def _load_fresh_reviewed_failure(path: Path, label: str) -> dict:
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"{label} did not create a regular report: {path}")
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"{label} report is unreadable: {error}") from error
    if (
        not isinstance(report, dict)
        or report.get("complete") is not True
        or report.get("gate") is not False
    ):
        raise RuntimeError(
            f"{label} did not produce the complete reviewed gate-false report"
        )
    return report


def _raw_common_arguments(pejvo_review_path=None) -> list[str]:
    arguments = [
        "--languages", "JA", "ZH", "KO",
        "--expected-gold-sha256", PHASE532_GOLD_SHA256,
        "--baseline-revision", BASELINE_REVISION,
    ]
    if pejvo_review_path is not None:
        arguments.extend([
            "--fake-coarse-pejvo-disagreement-review",
            str(pejvo_review_path),
        ])
    return arguments


def _current_e373_audit_arguments(pejvo_review_path=None) -> list[str]:
    return [
        "--current-only-diagnostic",
        "--scope-manifest", str(CURRENT_E373_SCOPE),
        *_raw_common_arguments(pejvo_review_path),
    ]


def _run_current_e373_child() -> None:
    """Run current-only with its hard-coded parent output redirected safely."""
    import no_worsening_audit as audit

    source = (audit.HERE / "out" / "_audit_no_worsening_current_only.json").resolve()
    destination = CURRENT_E373_REPORT.resolve()
    if source == destination:
        raise RuntimeError("current-e373 report is not isolated")
    original_dump = audit.atomic_json_dump

    def redirected_dump(path, value, *args, **kwargs):
        resolved = Path(path).resolve()
        if resolved == source:
            resolved = destination
        return original_dump(resolved, value, *args, **kwargs)

    audit.atomic_json_dump = redirected_dump
    try:
        audit.main(_current_e373_audit_arguments(
            os.environ.get("ESP_PHASE532_PEJVO_DISAGREEMENT_REVIEW")
        ))
    finally:
        audit.atomic_json_dump = original_dump


def _run_process(command, *, environment, run_process=None):
    if run_process is None:
        run_process = subprocess.run
    return run_process(
        command,
        cwd=ROOT,
        env=environment,
        check=False,
    )


def _run_expected_raw_failure(
    command, report_path: Path, label: str, *, environment, run_process=None,
) -> dict:
    _remove_report(report_path)
    completed = _run_process(
        command, environment=environment, run_process=run_process,
    )
    if completed.returncode != 1:
        raise RuntimeError(
            f"{label} raw audit returned {completed.returncode}; expected 1"
        )
    return _load_fresh_reviewed_failure(report_path, label)


def _run_sidecar(
    audit_kind: str, report_path: Path, *, environment, run_process=None,
) -> None:
    command = [
        sys.executable,
        str(SIDECAR),
        "--audit-kind", audit_kind,
        "--audit", str(report_path),
        "--deployed",
        "--batch-size", "33",
    ]
    completed = _run_process(
        command, environment=environment, run_process=run_process,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Phase 558 {audit_kind} sidecar returned {completed.returncode}"
        )


def _run_fresh_closed_audit(
    command, report_path: Path, label: str, audit_kind: str, *,
    environment, run_process=None, after_raw=None, state_guard=None,
) -> dict:
    # A fresh invocation never resumes or reuses a preceding partial audit.
    _remove_checkpoints()
    if state_guard is not None:
        state_guard(f"{label}:before-raw")
    report = _run_expected_raw_failure(
        command,
        report_path,
        label,
        environment=environment,
        run_process=run_process,
    )
    if state_guard is not None:
        state_guard(f"{label}:after-raw")
    if after_raw is not None:
        after_raw()
    _run_sidecar(
        audit_kind,
        report_path,
        environment=environment,
        run_process=run_process,
    )
    if state_guard is not None:
        state_guard(f"{label}:after-sidecar")
    # Deliberately after sidecar success.  On failure, preserve evidence.
    _remove_checkpoints()
    return report


def run_formal_audits(
    *, environ=None, run_process=None, head_reader=None, state_reader=None,
) -> None:
    if environ is None:
        environ = os.environ
    if head_reader is None:
        head_reader = _git_head
    if state_reader is None:
        state_reader = lambda: _formal_input_state(environ)
    missing = [name for name in REQUIRED_ENVIRONMENT if not environ.get(name)]
    if missing:
        raise RuntimeError(
            "Phase 558 formal no-worsening requires explicit "
            + ", ".join(missing)
        )
    for required_file in (RAW_AUDITOR, SIDECAR, CURRENT_E373_SCOPE):
        if not required_file.is_file():
            raise RuntimeError(f"required Phase 558 input is missing: {required_file}")

    start_head = head_reader()
    start_state = state_reader()

    def assert_formal_state(label):
        current_state = state_reader()
        if current_state != start_state:
            raise RuntimeError(
                "formal audit inputs changed during Phase 558 audits: "
                f"{label}"
            )
    common_environment = dict(environ)
    common_environment.update(UTF8_ENVIRONMENT)

    parent_environment = dict(common_environment)
    # The historical Phase558 parent gate is pinned to b769038, whereas the
    # current exact/canonical corpus gate is pinned to d1642c2.  They cannot
    # safely share the top-level ESP_CORPUS_PATH authority.
    parent_environment["ESP_CORPUS_PATH"] = environ[
        "ESP_PHASE558_PARENT_CORPUS_PATH"
    ]
    parent_command = [
        sys.executable,
        str(RAW_AUDITOR),
        "--current-only-diagnostic",
        *_raw_common_arguments(
            environ["ESP_PHASE532_PEJVO_DISAGREEMENT_REVIEW"]
        ),
    ]
    _run_fresh_closed_audit(
        parent_command,
        PARENT_CURRENT_REPORT,
        "Phase 558 parent current-only",
        "parent-current",
        environment=parent_environment,
        run_process=run_process,
        state_guard=assert_formal_state,
    )

    full_environment = dict(parent_environment)
    full_command = [
        sys.executable,
        str(RAW_AUDITOR),
        *_raw_common_arguments(
            environ["ESP_PHASE532_PEJVO_DISAGREEMENT_REVIEW"]
        ),
    ]
    _run_fresh_closed_audit(
        full_command,
        FULL_REPORT,
        "Phase 558 full old-to-new",
        "full-old-to-new",
        environment=full_environment,
        run_process=run_process,
        state_guard=assert_formal_state,
    )

    parent_current_identity = _file_identity(PARENT_CURRENT_REPORT)
    current_environment = dict(common_environment)
    current_environment["ESP_CORPUS_PATH"] = environ[
        "ESP_PHASE558_CURRENT_CORPUS_PATH"
    ]
    current_command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--_current-e373-child",
    ]
    def assert_parent_current_unchanged():
        if _file_identity(PARENT_CURRENT_REPORT) != parent_current_identity:
            raise RuntimeError(
                "current-e373 audit modified the parent-current diagnostic"
            )

    _run_fresh_closed_audit(
        current_command,
        CURRENT_E373_REPORT,
        "Phase 558 current e373",
        "current-e373",
        environment=current_environment,
        run_process=run_process,
        after_raw=assert_parent_current_unchanged,
        state_guard=assert_formal_state,
    )

    assert_formal_state("all-audits:final")
    end_head = head_reader()
    if start_head != end_head:
        raise RuntimeError(
            "worktree HEAD changed during Phase 558 formal no-worsening audits: "
            f"{start_head} -> {end_head}"
        )
    print(
        "Phase 558 formal no-worsening: parent-current + full old-to-new + "
        "current e373 PASS "
        f"(stable worktree HEAD {start_head})"
    )


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--_current-e373-child",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args(argv)
    if args._current_e373_child:
        _run_current_e373_child()
        return
    run_formal_audits()


if __name__ == "__main__":
    main()
