# -*- coding: utf-8 -*-
"""Run the fresh 7c04-reference / d1642c2-current no-worsening audit.

The raw renderer deliberately receives the immutable 7c04 corpus as its
reference source.  The successor gate receives all three clean corpus
checkouts and proves e373 -> 7c04's 110-row weight-only transition plus
7c04 -> d1642c2's single reviewed ``iniciatoro`` improvement.
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
SIDECAR_GATE = HERE / "current_corpus_no_worsening_sidecar_gate.py"
SCOPE = HERE / "_current_corpus_scope_d1642c2.json"
REPORT = HERE / "out" / "_audit_no_worsening_current_d1642c2.json"
RAW_DEFAULT_REPORT = HERE / "out" / "_audit_no_worsening_current_only.json"
GOLD_SHA256 = (
    "6B403AA30BBCBBA4C9E41A2CF48D1AD2FC1D5A5DB1154CAF1260A361566E3226"
)
BASELINE_REVISION = "dcfca809b711075788ee00b6323cdd2ea31618ff"
RAW_BATCH_SIZE = 20_000
REQUIRED_ENVIRONMENT = (
    "ESP_GOLD_PATH",
    "ESP_CURRENT_CORPUS_E373_PATH",
    "ESP_CURRENT_CORPUS_REFERENCE_PATH",
    "ESP_CURRENT_CORPUS_ACTIVE_PATH",
)
UTF8_ENVIRONMENT = {
    "PYTHONIOENCODING": "utf-8",
    "PYTHONUTF8": "1",
}


def _file_identity(path: Path):
    if not path.exists():
        return None
    raw = path.read_bytes()
    return {
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest().upper(),
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


def _formal_input_state(environ: dict | None = None) -> dict:
    if environ is None:
        environ = os.environ
    import no_worsening_audit as audit

    dependencies = sorted(
        {*HERE.glob("*.py"), *HERE.glob("*.json")},
        key=lambda path: path.name,
    )
    analysis = {}
    for path in dependencies:
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(
                f"formal dependency is not a regular file: {path}"
            )
        analysis[path.name] = _file_identity(path)
    app_inputs = {
        language: audit.current_app_fingerprint(
            ROOT / f"Esperanto-Kanji-Ruby-{language}"
        )
        for language in ("JA", "ZH", "KO")
    }
    corpus_inputs = {}
    for name in (
        "ESP_CURRENT_CORPUS_E373_PATH",
        "ESP_CURRENT_CORPUS_REFERENCE_PATH",
        "ESP_CURRENT_CORPUS_ACTIVE_PATH",
    ):
        root = Path(environ[name]).resolve()
        corpus_inputs[name] = {
            "repository": audit.git_repo_state(root),
            "content": audit.corpus_content_fingerprint(root),
        }
    return {
        "analysis_dependencies": analysis,
        "deployed_app_inputs": app_inputs,
        "corpus_inputs": corpus_inputs,
        "gold": _file_identity(Path(environ["ESP_GOLD_PATH"]).resolve()),
    }


def _remove_stale_report(path: Path) -> None:
    if path.is_symlink():
        raise RuntimeError(f"refusing report symlink: {path}")
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    if path.exists():
        raise RuntimeError(f"could not remove stale report: {path}")


def _load_fresh_reviewed_failure(path: Path) -> dict:
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"raw audit did not create a regular report: {path}")
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"raw audit report is unreadable: {error}") from error
    if (
        not isinstance(report, dict)
        or report.get("complete") is not True
        or report.get("gate") is not False
    ):
        raise RuntimeError(
            "raw audit did not produce the complete reviewed gate-false report"
        )
    return report


def _activate_successor_reference_overrides(audit) -> None:
    """Install only the reviewed successor reference deltas in memory.

    The parent auditor and all Phase-558 evidence stay byte-immutable.  R74
    changes the exact ``glu-glu-glu`` authority from three misleading
    ``glu=glue``-shaped pieces to one atomic onomatopoeic lexeme.  Keeping
    this adjustment local to the successor runner prevents that new decision
    from retroactively rewriting historical reports.
    """
    surface = "glu-glu-glu"
    expected = surface
    if (
        audit.OFFICIAL_LONG_ROOT_OVERRIDES.get(surface)
        != "glu/-/glu/-/glu"
        or audit.REVIEWED_GOLD_OVERRIDES.get(surface)
        != "glu/-/glu/-/glu"
    ):
        raise RuntimeError("successor glu reference precondition drift")
    audit.OFFICIAL_LONG_ROOT_OVERRIDES[surface] = expected
    audit.REVIEWED_GOLD_OVERRIDES[surface] = expected


def _run_raw_child() -> None:
    """Redirect only the raw auditor's hard-coded current-only report."""
    import no_worsening_audit as audit

    _activate_successor_reference_overrides(audit)
    source = RAW_DEFAULT_REPORT.resolve()
    destination = REPORT.resolve()
    if source == destination:
        raise RuntimeError("successor report is not isolated")
    original_dump = audit.atomic_json_dump
    original_render = audit.render_signatures
    signature_sha256 = {}
    surface_counts = {}

    def captured_render(
        module, app_dir, payload, surfaces, batch_size, *args, **kwargs
    ):
        rendered = original_render(
            module,
            app_dir,
            payload,
            surfaces,
            batch_size,
            *args,
            **kwargs,
        )
        language = app_dir.name.rsplit("-", 1)[-1]
        rows = [
            [
                surface,
                audit.signature_payload(rendered[surface]["signature"]),
            ]
            for surface in surfaces
        ]
        signature_sha256[language] = audit.stable_json_sha256(rows)
        surface_counts[language] = len(rows)
        return rendered

    def redirected_dump(path, value, *args, **kwargs):
        target = Path(path).resolve()
        if target == source:
            target = destination
            languages = ["JA", "ZH", "KO"]
            if (
                list(signature_sha256) != languages
                or list(surface_counts) != languages
                or len(set(surface_counts.values())) != 1
            ):
                raise RuntimeError(
                    "full trilingual signature capture is incomplete"
                )
            equal = len(set(signature_sha256.values())) == 1
            value = {
                **value,
                "successor_trilingual_boundaries": {
                    "schema_version": 1,
                    "surface_count": next(iter(surface_counts.values())),
                    "languages": languages,
                    "signature_sha256": dict(signature_sha256),
                    "mismatches": 0 if equal else 1,
                    "gate": equal,
                },
            }
        return original_dump(target, value, *args, **kwargs)

    audit.atomic_json_dump = redirected_dump
    audit.render_signatures = captured_render
    try:
        audit.main([
            "--current-only-diagnostic",
            "--batch-size",
            str(RAW_BATCH_SIZE),
            "--scope-manifest",
            str(SCOPE),
            "--languages",
            "JA",
            "ZH",
            "KO",
            "--expected-gold-sha256",
            GOLD_SHA256,
            "--baseline-revision",
            BASELINE_REVISION,
        ])
    finally:
        audit.atomic_json_dump = original_dump
        audit.render_signatures = original_render


def _run_process(command, *, environment, run_process=None):
    if run_process is None:
        run_process = subprocess.run
    return run_process(
        command,
        cwd=ROOT,
        env=environment,
        check=False,
    )


def run_formal_audit(
    *,
    environ=None,
    run_process=None,
    head_reader=None,
    state_reader=None,
) -> dict:
    if environ is None:
        environ = os.environ
    if head_reader is None:
        head_reader = _git_head
    missing = [name for name in REQUIRED_ENVIRONMENT if not environ.get(name)]
    if missing:
        raise RuntimeError(
            "current-corpus formal audit requires explicit "
            + ", ".join(missing)
        )
    for path in (RAW_AUDITOR, SIDECAR_GATE, SCOPE):
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"required successor input is missing: {path}")
    for name in REQUIRED_ENVIRONMENT:
        path = Path(environ[name]).resolve()
        if name == "ESP_GOLD_PATH":
            valid = path.is_file() and not path.is_symlink()
        else:
            valid = path.is_dir() and not path.is_symlink()
        if not valid:
            raise RuntimeError(f"invalid formal input {name}: {path}")

    if state_reader is None:
        state_reader = lambda: _formal_input_state(environ)
    start_head = head_reader()
    start_state = state_reader()

    def assert_stable(label: str) -> None:
        if state_reader() != start_state:
            raise RuntimeError(
                f"formal successor inputs changed during audit: {label}"
            )

    environment = dict(environ)
    environment.update(UTF8_ENVIRONMENT)
    # Do not inherit the moving active corpus as the raw reference source.
    environment["ESP_CORPUS_PATH"] = environ[
        "ESP_CURRENT_CORPUS_REFERENCE_PATH"
    ]

    _remove_stale_report(REPORT)
    assert_stable("before-raw")
    child_command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--_raw-child",
    ]
    completed = _run_process(
        child_command,
        environment=environment,
        run_process=run_process,
    )
    if completed.returncode != 1:
        raise RuntimeError(
            f"raw current-corpus audit returned {completed.returncode}; "
            "expected the reviewed gate-false status 1"
        )
    report = _load_fresh_reviewed_failure(REPORT)
    assert_stable("after-raw")

    gate_command = [
        sys.executable,
        str(SIDECAR_GATE),
        "--audit",
        str(REPORT),
        "--e373-corpus",
        environ["ESP_CURRENT_CORPUS_E373_PATH"],
        "--reference-corpus",
        environ["ESP_CURRENT_CORPUS_REFERENCE_PATH"],
        "--active-corpus",
        environ["ESP_CURRENT_CORPUS_ACTIVE_PATH"],
        "--deployed",
        "--batch-size",
        "33",
    ]
    completed = _run_process(
        gate_command,
        environment=environment,
        run_process=run_process,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"current-corpus successor sidecar returned "
            f"{completed.returncode}"
        )
    assert_stable("after-sidecar")
    end_head = head_reader()
    if end_head != start_head:
        raise RuntimeError(
            f"worktree HEAD changed during successor audit: "
            f"{start_head} -> {end_head}"
        )
    return {
        "report": str(REPORT),
        "reference_corpus": environment["ESP_CORPUS_PATH"],
        "active_corpus": environ["ESP_CURRENT_CORPUS_ACTIVE_PATH"],
        "worktree_head": start_head,
        "complete": True,
        "gate": True,
    }


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--_raw-child",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args(argv)
    if args._raw_child:
        _run_raw_child()
        return
    summary = run_formal_audit()
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
