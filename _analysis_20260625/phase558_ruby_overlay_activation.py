# -*- coding: utf-8 -*-
"""Activation gate for the five-surface Phase 558 Ruby sidecar."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import phase532_activation as parent
import phase558_ruby_overlay as overlay


HERE = Path(__file__).resolve().parent
ACTIVATION_PATH = HERE / "_phase558_ruby_overlay_activation.json"
ACTIVATION_SHA256 = (
    "8401FF7C54F5B93CEB435D9B47BEDC6491C110A8EE04EDFBDF638CBAD8A539D0"
)
MODE = "phase532_parent_with_phase558_five_surface_sidecar"
FALLBACK_POLICY = (
    "Fail closed; never silently fall back to Phase 532 after an activated "
    "Phase 558 overlay identity is present."
)


def activation_report(
    *, activation_path: Path = ACTIVATION_PATH,
    parent_scope_path: Path = parent.SCOPE_PATH,
    parent_strict_path: Path = parent.STRICT_PATH,
    parent_fake_reference_path: Path = parent.FAKE_REFERENCE_PATH,
) -> dict:
    raw = Path(activation_path).read_bytes()
    if hashlib.sha256(raw).hexdigest().upper() != ACTIVATION_SHA256:
        raise ValueError("Phase 558 Ruby overlay activation identity drift")
    payload = json.loads(raw.decode("utf-8"))
    parent_report = parent.activation_report(
        scope_path=parent_scope_path,
        strict_path=parent_strict_path,
        fake_reference_path=parent_fake_reference_path,
    )
    expected_parent = {
        "gold_sha256": parent_report["gold_sha256"],
        "reference_sha256": parent_report["reference_sha256"],
        "projection_sha256": parent_report["projection_sha256"],
        "fake_manifest_sha256": parent_report["fake_manifest_sha256"],
        "strict_entries_sha256": parent_report["strict_entries_sha256"],
    }
    expected_keys = {
        "schema_version", "active", "mode", "parent_phase532",
        "overlay_review", "fallback_policy",
    }
    if (
        set(payload) != expected_keys
        or payload.get("schema_version") != 1
        or payload.get("active") is not True
        or payload.get("mode") != MODE
        or parent_report.get("phase532_active") is not True
        or payload.get("parent_phase532") != expected_parent
        or payload.get("overlay_review") != overlay.review_identity()
        or payload.get("fallback_policy") != FALLBACK_POLICY
    ):
        raise ValueError("incoherent Phase 558 Ruby overlay activation state")
    return {
        "phase532_active": True,
        "phase558_ruby_overlay_active": True,
        "mode": MODE,
        "activation_sha256": ACTIVATION_SHA256,
        "parent": parent_report,
        "overlay_review": overlay.review_identity(),
        "gate": True,
    }


def phase558_ruby_overlay_active() -> bool:
    return activation_report()["phase558_ruby_overlay_active"]
