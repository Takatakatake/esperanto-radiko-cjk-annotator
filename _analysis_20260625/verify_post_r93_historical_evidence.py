# -*- coding: utf-8 -*-
"""Verify immutable post-R93 evidence without comparing it to post-R98 apps."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

import post_r93_no_worsening_gate as gate


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SOURCE_COMMIT = "15e2f7fc19db08e332a797c9703019790ea23c36"
EXPECTED = {
    gate.REPORT_RELATIVE_PATH.as_posix(): (
        "A2E0E8333737C133B82AA39383397EB2C98B9DE200DB397811F2DBA4A819BA5F"
    ),
    gate.MANIFEST_RELATIVE_PATH.as_posix(): (
        "D426327CE438C74B78DDE5FC5938158F8BB85AF889A8C5B10E8027DDE139EFEA"
    ),
}


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def git_blob(relative: str) -> bytes:
    return subprocess.check_output(
        ["git", "show", f"{SOURCE_COMMIT}:{relative}"], cwd=ROOT,
    )


def validate() -> dict:
    current = {}
    for relative, expected in EXPECTED.items():
        raw = (ROOT / relative).read_bytes()
        if sha256(raw) != expected:
            raise ValueError(f"post-R93 historical blob SHA drift: {relative}")
        if raw != git_blob(relative):
            raise ValueError(f"post-R93 blob differs from {SOURCE_COMMIT[:7]}: {relative}")
        current[relative] = raw

    manifest_raw = current[gate.MANIFEST_RELATIVE_PATH.as_posix()]
    manifest = json.loads(manifest_raw.decode("utf-8"))
    gate.validate_manifest(manifest)
    if sha256(manifest_raw) != gate.EXPECTED_MANIFEST_SHA256:
        raise ValueError("post-R93 code/manifest historical seal drift")
    report_raw = current[gate.REPORT_RELATIVE_PATH.as_posix()]
    result = gate.validate_report_bytes(
        report_raw,
        manifest=manifest,
        current_fingerprints=manifest["sealed"]["app_input_fingerprints"],
    )
    result.update({
        "source_commit": SOURCE_COMMIT,
        "report_sha256": EXPECTED[gate.REPORT_RELATIVE_PATH.as_posix()],
        "manifest_sha256": EXPECTED[gate.MANIFEST_RELATIVE_PATH.as_posix()],
        "historical_only": True,
        "deployed_post_r98_fingerprints_not_compared": True,
    })
    return result


def main() -> None:
    print(json.dumps(validate(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
