# -*- coding: utf-8 -*-
"""Build, but never overwrite, the post-R98 no-worsening manifest."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from atomic_json import atomic_json_dump
import post_r98_no_worsening_gate as gate


def build_from_path(report_path: Path) -> tuple[dict, bytes]:
    report_path = Path(report_path)
    raw = report_path.read_bytes()
    report = json.loads(raw.decode("utf-8"))
    fingerprints = gate.deployed_app_fingerprints()
    manifest = gate.build_manifest_from_report(
        report, raw, current_fingerprints=fingerprints,
    )
    return manifest, gate.manifest_bytes(manifest)


def write_manifest(path: Path, manifest: dict, expected_raw: bytes) -> None:
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise FileExistsError(
            f"refusing to overwrite post-R98 successor evidence: {path}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_json_dump(path, manifest, indent=2)
    if path.read_bytes() != expected_raw:
        raise IOError("atomic manifest serialization differs from reviewed bytes")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=gate.REPORT_PATH)
    parser.add_argument("--output", type=Path, default=gate.MANIFEST_PATH)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    manifest, raw = build_from_path(args.report)
    digest = gate.raw_sha256(raw)
    if args.write:
        write_manifest(args.output, manifest, raw)
    print(json.dumps({
        "gate_id": gate.GATE_ID,
        "report": manifest["report"],
        "manifest_path": str(args.output),
        "manifest_bytes": len(raw),
        "manifest_sha256": digest,
        "written": bool(args.write),
        "seal_instruction": (
            "Review this manifest and set "
            "post_r98_no_worsening_gate.EXPECTED_MANIFEST_SHA256 to "
            + digest
        ),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
