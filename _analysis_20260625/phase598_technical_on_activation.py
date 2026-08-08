# -*- coding: utf-8 -*-
"""Activation gate for the Phase 598 technical-``on`` Ruby sidecar."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import phase558_ruby_overlay_activation as parent
import phase598_technical_on_policy as policy


HERE = Path(__file__).resolve().parent
ACTIVATION_PATH = HERE / "_phase598_technical_on_activation.json"
ACTIVATION_SHA256 = (
    "06E5E4944EA5B61BCF21E02D26FA11B9D48BEF13270A207D21294029B23C2069"
)
MODE = "phase558_parent_with_phase598_eight_technical_on_sidecar"
FALLBACK_POLICY = (
    "Fail closed; never silently fall back to Phase 558 or broaden generic "
    "on after the activated Phase 598 technical-on identity is present."
)


def activation_report(*, activation_path: Path = ACTIVATION_PATH) -> dict:
    raw = Path(activation_path).read_bytes()
    if hashlib.sha256(raw).hexdigest().upper() != ACTIVATION_SHA256:
        raise ValueError("Phase 598 technical-on activation identity drift")
    payload = json.loads(raw.decode("utf-8"))
    parent_report = parent.activation_report()
    expected_parent = {
        "activation_sha256": parent_report["activation_sha256"],
        "mode": parent_report["mode"],
        "overlay_review_sha256": (
            parent_report["overlay_review"]["review_sha256"]
        ),
        "overlay_entries_sha256": (
            parent_report["overlay_review"]["entries_sha256"]
        ),
    }
    expected_keys = {
        "schema_version", "active", "mode", "parent_phase558",
        "phase598_review", "fallback_policy",
    }
    if (
        set(payload) != expected_keys
        or payload.get("schema_version") != 1
        or payload.get("active") is not True
        or payload.get("mode") != MODE
        or parent_report.get("phase558_ruby_overlay_active") is not True
        or payload.get("parent_phase558") != expected_parent
        or payload.get("phase598_review") != policy.review_identity()
        or payload.get("fallback_policy") != FALLBACK_POLICY
    ):
        raise ValueError("incoherent Phase 598 technical-on activation state")
    return {
        "phase532_active": True,
        "phase558_ruby_overlay_active": True,
        "phase598_technical_on_active": True,
        "mode": MODE,
        "activation_sha256": ACTIVATION_SHA256,
        "parent": parent_report,
        "phase598_review": policy.review_identity(),
        "gate": True,
    }


def phase598_technical_on_active() -> bool:
    return activation_report()["phase598_technical_on_active"]
