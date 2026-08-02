# -*- coding: utf-8 -*-
"""Deployed no-worsening gate for the exact post-R98 Ruby snapshot.

The post-R93 evidence remains immutable historical evidence.  This successor
uses the same reviewed 68,559-surface semantic contract, but seals the deployed
app fingerprints after the exact R95/R96/R98 gloss carry-forward.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import post_r93_no_worsening_gate as base


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPORT_RELATIVE_PATH = Path(
    "_analysis_20260625/out/_audit_no_worsening_post_r98.json"
)
MANIFEST_RELATIVE_PATH = Path(
    "_analysis_20260625/_post_r98_no_worsening_residual_manifest.json"
)
REPORT_PATH = ROOT / REPORT_RELATIVE_PATH
MANIFEST_PATH = ROOT / MANIFEST_RELATIVE_PATH
EXPECTED_MANIFEST_SHA256 = (
    "87898697EB4FC90CFE02C55754652FD6DA282F085F205A4B32C5F1800645878F"
)
GATE_ID = "post_r98_current_only_no_worsening"


raw_sha256 = base.raw_sha256
deployed_app_fingerprints = base.deployed_app_fingerprints


def validate_manifest(manifest):
    return base.validate_manifest(
        manifest, gate_id=GATE_ID,
        report_relative_path=REPORT_RELATIVE_PATH,
    )


def validate_report(report, *, manifest=None, current_fingerprints=None):
    return base.validate_report(
        report, manifest=manifest,
        current_fingerprints=current_fingerprints,
        gate_id=GATE_ID, report_relative_path=REPORT_RELATIVE_PATH,
    )


def build_manifest_from_report(
    report, report_raw, *, current_fingerprints,
):
    return base.build_manifest_from_report(
        report, report_raw, current_fingerprints=current_fingerprints,
        gate_id=GATE_ID, report_relative_path=REPORT_RELATIVE_PATH,
    )


def manifest_bytes(manifest):
    return base.manifest_bytes(
        manifest, gate_id=GATE_ID,
        report_relative_path=REPORT_RELATIVE_PATH,
    )


def load_manifest(
    path=MANIFEST_PATH, *, expected_sha256=EXPECTED_MANIFEST_SHA256,
):
    return base.load_manifest(
        path, expected_sha256=expected_sha256, gate_id=GATE_ID,
        report_relative_path=REPORT_RELATIVE_PATH,
    )


def validate_report_bytes(
    report_raw, *, manifest, current_fingerprints,
):
    return base.validate_report_bytes(
        report_raw, manifest=manifest,
        current_fingerprints=current_fingerprints,
        gate_id=GATE_ID, report_relative_path=REPORT_RELATIVE_PATH,
    )


def validate_deployed(
    *, report_path=REPORT_PATH, manifest_path=MANIFEST_PATH,
    expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
):
    return base.validate_deployed(
        report_path=report_path, manifest_path=manifest_path,
        expected_manifest_sha256=expected_manifest_sha256,
        gate_id=GATE_ID, report_relative_path=REPORT_RELATIVE_PATH,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument(
        "--expected-manifest-sha256", default=EXPECTED_MANIFEST_SHA256,
    )
    args = parser.parse_args(argv)
    result = validate_deployed(
        report_path=args.report,
        manifest_path=args.manifest,
        expected_manifest_sha256=args.expected_manifest_sha256,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
