# -*- coding: utf-8 -*-
"""Verify the immutable Phase 558 no-worsening evidence.

The three reports and their closed five-surface sidecar describe the state
adopted at ``adc2982``.  Later Ruby rounds must not regenerate those reports
against a newer payload.  Normal execution is read-only.  ``--restore`` is an
explicit recovery operation that copies the already-reviewed Git blobs from
the adoption commit and then performs the same byte and object checks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
ADOPTION_COMMIT = "adc2982ad8d7953cc364b2a7a2e278b1d87daafe"
EXPECTED = {
    "_analysis_20260625/out/_audit_no_worsening.json": {
        "blob": "2e69b9a6d49633f4294124a950913c0261b2589c",
        "bytes": 236715,
        "sha256": "2FDA0DCA9C288907021689C95490E0607053C7ACCD9CC7D52EA13F7B39747AAA",
    },
    "_analysis_20260625/out/_audit_no_worsening_current_only.json": {
        "blob": "3bbb3e9d9a72feeef2183950b16e5d8aae448f53",
        "bytes": 189318,
        "sha256": "0F03B1A8697750749F75892758CA214A0AD5F8D6A23FEF093F1A2EDDE6B6C4D9",
    },
    "_analysis_20260625/out/_audit_no_worsening_current_e373.json": {
        "blob": "5e74dc0585c82b9e99bfa36071c0e0cb8994e64b",
        "bytes": 189321,
        "sha256": "7828580B8F2FE2D89BEC3B2240EB3FEC5E0EC42BDF1648497D835E463D00FFAE",
    },
    "_analysis_20260625/_phase558_no_worsening_sidecar.json": {
        "blob": "cc5264a04a3f900bab925cfd874810efc74ce89b",
        "bytes": 11530,
        "sha256": "7468D660EC39089E9F931BE9F79BF45D0AD5DFEC38F6281651F489D94FAE7FBA",
    },
}


def _run_git(*arguments: str, input_bytes: bytes | None = None) -> bytes:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        raise ValueError(
            "Git evidence check failed: "
            + completed.stderr.decode("utf-8", errors="replace").strip()
        )
    return completed.stdout


def _adoption_blob(relative: str) -> str:
    return _run_git("rev-parse", f"{ADOPTION_COMMIT}:{relative}").decode(
        "ascii"
    ).strip()


def restore_historical_evidence() -> None:
    for relative, expected in EXPECTED.items():
        adoption_blob = _adoption_blob(relative)
        if adoption_blob != expected["blob"]:
            raise ValueError(
                f"Phase 558 adoption blob drift for {relative}: "
                f"{adoption_blob} != {expected['blob']}"
            )
        raw = _run_git("cat-file", "blob", adoption_blob)
        if (
            len(raw) != expected["bytes"]
            or hashlib.sha256(raw).hexdigest().upper() != expected["sha256"]
        ):
            raise ValueError(f"Phase 558 adoption bytes drift for {relative}")
        path = ROOT / relative
        temporary = path.with_name(path.name + ".phase558-restore.tmp")
        temporary.write_bytes(raw)
        os.replace(temporary, path)


def verify_historical_evidence() -> dict:
    files = {}
    for relative, expected in EXPECTED.items():
        path = ROOT / relative
        raw = path.read_bytes()
        actual = {
            "blob": _run_git(
                "hash-object", f"--path={relative}", "--", relative
            ).decode("ascii").strip(),
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest().upper(),
        }
        if actual != expected:
            raise ValueError(
                f"Phase 558 historical evidence drift for {relative}: "
                f"expected={expected!r}, actual={actual!r}"
            )
        if _adoption_blob(relative) != expected["blob"]:
            raise ValueError(
                f"Phase 558 adoption commit no longer resolves {relative}"
            )
        files[relative] = actual
    return {
        "phase": 558,
        "adoption_commit": ADOPTION_COMMIT,
        "files": files,
        "immutable_historical_evidence": True,
        "gate": True,
    }


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--restore",
        action="store_true",
        help="explicitly restore the four reviewed blobs from adc2982",
    )
    args = parser.parse_args(argv)
    if args.restore:
        restore_historical_evidence()
    print(json.dumps(verify_historical_evidence(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
