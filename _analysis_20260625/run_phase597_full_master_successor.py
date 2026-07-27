# -*- coding: utf-8 -*-
"""Run one fresh Phase 597 raw audit, then its fail-closed successor sidecar.

The generic raw candidate is expected to exit 1: its deployed-runtime gate is
true, but its top-level adoption/promotion gate is deliberately false.  A
return code of 0, any other failure code, a missing/stale report, or a report
that does not have exactly that reviewed high-level state is rejected.

The initial successor review is intentionally unsealed.  The runner can
produce the fresh report needed for independent sealing, but the sidecar will
continue to fail closed until all fresh-report-dependent pins are explicitly
recorded and the review identity is updated.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import no_worsening_audit as audit
import phase597_full_master_successor_sidecar_gate as sidecar


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RAW_AUDITOR = HERE / "audit_master_3lang_full_snapshot.py"
SIDECAR = HERE / "phase597_full_master_successor_sidecar_gate.py"
REPORT = HERE / "out" / "_audit_master_3lang_phase597_successor.json"
SOURCE_ENVIRONMENT = "ESP_PHASE597_SOURCE_DIR"
LANGUAGES = ("JA", "ZH", "KO")
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


def _file_identity(path: Path) -> dict:
    raw = path.read_bytes()
    return {
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest().upper(),
    }


def _formal_input_state(phase597_dir: Path) -> dict:
    """Fingerprint all top-level analysis inputs and deployed app inputs."""
    review = sidecar.load_review()
    sidecar.validate_phase597_source_directory(phase597_dir, review)
    dependencies = sorted(
        {*HERE.glob("*.py"), *HERE.glob("*.json")},
        key=lambda path: path.name,
    )
    analysis_identities = {}
    for path in dependencies:
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(
                f"formal audit dependency is not a regular file: {path}"
            )
        analysis_identities[path.name] = _file_identity(path)
    source_identities = {}
    for spec in review["sources"].values():
        path = Path(phase597_dir) / spec["path"]
        source_identities[spec["path"]] = _file_identity(path)
    app_inputs = {
        language: audit.current_app_fingerprint(
            ROOT / f"Esperanto-Kanji-Ruby-{language}"
        )
        for language in LANGUAGES
    }
    return {
        "analysis_dependencies": analysis_identities,
        "phase597_sources": source_identities,
        "deployed_app_inputs": app_inputs,
    }


def _remove_report(path: Path) -> None:
    path = Path(path)
    if path.is_symlink():
        raise RuntimeError(f"refusing to remove report symlink: {path}")
    if path.exists() and not path.is_file():
        raise RuntimeError(f"report path is not a regular file: {path}")
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    if path.exists() or path.is_symlink():
        raise RuntimeError(f"could not remove stale report: {path}")


def _read_fresh_candidate_failure(path: Path, label: str) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"{label} did not create a regular report: {path}")
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"{label} report is unreadable: {error}") from error
    candidate = report.get("candidate_audit") if isinstance(report, dict) else None
    if (
        not isinstance(report, dict)
        or report.get("complete") is not True
        or report.get("gate") is not False
        or not isinstance(candidate, dict)
        or candidate.get("runtime_gate") is not True
    ):
        raise RuntimeError(
            f"{label} did not produce a fresh complete candidate report "
            "with runtime_gate=true and top gate=false"
        )
    return report


def build_raw_command(
    phase597_dir: Path,
    expected_head: str,
    *,
    report_path: Path = REPORT,
    batch_size: int = 1000,
) -> list[str]:
    review = sidecar.load_review()
    sources = review["sources"]
    phase597_dir = Path(phase597_dir)
    if not isinstance(batch_size, int) or batch_size < 1:
        raise ValueError("Phase 597 raw batch size must be positive")
    command = [
        sys.executable,
        str(RAW_AUDITOR),
        "--gold",
        str(phase597_dir / sources["learner"]["path"]),
        "--expected-gold-sha256",
        sources["learner"]["sha256"],
        "--academic",
        str(phase597_dir / sources["academic"]["path"]),
        "--expected-academic-sha256",
        sources["academic"]["sha256"],
        "--expected-head",
        expected_head,
        "--candidate-fake-coarse-manifest",
        str(
            phase597_dir
            / sources["candidate_fake_coarse_manifest"]["path"]
        ),
        "--candidate-transition-dispositions",
        str(
            phase597_dir
            / sources["candidate_transition_dispositions"]["path"]
        ),
        "--allow-stable-tracked-changes",
        "--batch-size",
        str(batch_size),
        "--report",
        str(report_path),
    ]
    forbidden = (
        "--phase532-baseline-dir",
        "--phase532-candidate-dir",
        "--phase532-runtime-mode",
        "--phase558-candidate-dir",
        "--phase558-ruby-disposition-ledger",
        "--phase558-japanese-guide",
        "--phase558-chinese-guide",
        "--phase558-runtime-mode",
        "--enforce-all-fake-coarse",
    )
    if any(option in command for option in forbidden):
        raise RuntimeError("Phase 597 generic raw command broadened its authority")
    return command


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
    command,
    report_path: Path,
    *,
    environment,
    run_process=None,
) -> dict:
    _remove_report(report_path)
    completed = _run_process(
        command,
        environment=environment,
        run_process=run_process,
    )
    if completed.returncode != 1:
        raise RuntimeError(
            "Phase 597 raw audit returned "
            f"{completed.returncode}; expected exactly 1"
        )
    return _read_fresh_candidate_failure(
        report_path, "Phase 597 raw audit",
    )


def build_sidecar_command(
    phase597_dir: Path,
    *,
    report_path: Path = REPORT,
    batch_size: int = 20,
) -> list[str]:
    return [
        sys.executable,
        str(SIDECAR),
        "--audit",
        str(report_path),
        "--phase597-dir",
        str(phase597_dir),
        "--deployed",
        "--batch-size",
        str(batch_size),
    ]


def run_formal_successor(
    phase597_dir: Path,
    *,
    report_path: Path = REPORT,
    raw_batch_size: int = 1000,
    sidecar_batch_size: int = 20,
    environ=None,
    run_process=None,
    head_reader=None,
    state_reader=None,
) -> dict:
    phase597_dir = Path(phase597_dir)
    report_path = Path(report_path)
    if environ is None:
        environ = os.environ
    if head_reader is None:
        head_reader = _git_head
    review = sidecar.load_review()
    sidecar.validate_phase597_source_directory(phase597_dir, review)
    for required in (RAW_AUDITOR, SIDECAR):
        if required.is_symlink() or not required.is_file():
            raise RuntimeError(
                f"required Phase 597 successor input is missing: {required}"
            )
    if not 1 <= sidecar_batch_size <= 20:
        raise ValueError("Phase 597 sidecar batch size must be in 1..20")
    if state_reader is None:
        state_reader = lambda: _formal_input_state(phase597_dir)

    start_head = head_reader()
    start_state = state_reader()

    def assert_state(label: str) -> None:
        if state_reader() != start_state:
            raise RuntimeError(
                "formal audit inputs changed during Phase 597 successor: "
                f"{label}"
            )

    environment = dict(environ)
    environment.update(UTF8_ENVIRONMENT)
    raw_command = build_raw_command(
        phase597_dir,
        start_head,
        report_path=report_path,
        batch_size=raw_batch_size,
    )
    assert_state("before-raw")
    raw_report = _run_expected_raw_failure(
        raw_command,
        report_path,
        environment=environment,
        run_process=run_process,
    )
    assert_state("after-raw")

    sidecar_command = build_sidecar_command(
        phase597_dir,
        report_path=report_path,
        batch_size=sidecar_batch_size,
    )
    completed = _run_process(
        sidecar_command,
        environment=environment,
        run_process=run_process,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "Phase 597 successor sidecar returned "
            f"{completed.returncode}; the fresh raw report was preserved"
        )
    assert_state("after-sidecar")
    end_head = head_reader()
    if end_head != start_head:
        raise RuntimeError(
            "worktree HEAD changed during Phase 597 successor: "
            f"{start_head} -> {end_head}"
        )
    return raw_report


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase597-dir",
        type=Path,
        help=(
            "Exact six-file Phase 597 source directory; defaults to "
            f"${SOURCE_ENVIRONMENT}."
        ),
    )
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument("--raw-batch-size", type=int, default=1000)
    parser.add_argument("--sidecar-batch-size", type=int, default=20)
    args = parser.parse_args(argv)
    phase597_dir = args.phase597_dir
    if phase597_dir is None:
        raw = os.environ.get(SOURCE_ENVIRONMENT)
        if not raw:
            raise RuntimeError(
                "Phase 597 successor requires --phase597-dir or explicit "
                f"{SOURCE_ENVIRONMENT}"
            )
        phase597_dir = Path(raw)
    report = run_formal_successor(
        phase597_dir,
        report_path=args.report,
        raw_batch_size=args.raw_batch_size,
        sidecar_batch_size=args.sidecar_batch_size,
    )
    print(json.dumps({
        "phase": 597,
        "report": str(args.report.resolve()),
        "complete": report["complete"],
        "candidate_runtime_gate": report["candidate_audit"]["runtime_gate"],
        "raw_top_gate": report["gate"],
        "sidecar_gate": True,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
