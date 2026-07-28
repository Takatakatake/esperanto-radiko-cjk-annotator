# -*- coding: utf-8 -*-
"""Activation gate for the seven ordinary-word Phase 619 Ruby repairs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import phase598_technical_on_activation as parent
import phase619_ordinary_ruby_policy as policy


HERE = Path(__file__).resolve().parent
ACTIVATION_PATH = HERE / "_phase619_ordinary_ruby_activation.json"
ACTIVATION_SHA256 = (
    "ED36C43C04CA37232874C8FA905783B99D69907B2F1C0BA3388A08A27193F268"
)
MODE = "phase598_parent_with_phase619_seven_ordinary_word_sidecar"
FALLBACK_POLICY = (
    "Fail closed; never silently omit the adopted Phase 619 ordinary-word "
    "Ruby sidecar or let it alter the Kanji track."
)


def activation_report(*, activation_path: Path = ACTIVATION_PATH) -> dict:
    raw = Path(activation_path).read_bytes()
    if hashlib.sha256(raw).hexdigest().upper() != ACTIVATION_SHA256:
        raise ValueError("Phase 619 ordinary Ruby activation identity drift")
    payload = json.loads(raw.decode("utf-8"))
    parent_report = parent.activation_report()
    expected_parent = {
        "activation_sha256": parent_report["activation_sha256"],
        "mode": parent_report["mode"],
        "review_sha256": parent_report["phase598_review"]["review_sha256"],
        "entries_sha256": parent_report["phase598_review"]["entries_sha256"],
    }
    expected_keys = {
        "schema_version", "active", "mode", "parent_phase598",
        "phase619_review", "fallback_policy",
    }
    if (
        set(payload) != expected_keys
        or payload.get("schema_version") != 1
        or payload.get("active") is not True
        or payload.get("mode") != MODE
        or parent_report.get("phase598_technical_on_active") is not True
        or payload.get("parent_phase598") != expected_parent
        or payload.get("phase619_review") != policy.review_identity()
        or payload.get("fallback_policy") != FALLBACK_POLICY
    ):
        raise ValueError(
            "incoherent Phase 619 ordinary Ruby activation state"
        )
    return {
        "phase532_active": True,
        "phase558_ruby_overlay_active": True,
        "phase598_technical_on_active": True,
        "phase619_ordinary_ruby_active": True,
        "mode": MODE,
        "activation_sha256": ACTIVATION_SHA256,
        "parent": parent_report,
        "phase619_review": policy.review_identity(),
        "gate": True,
    }


def phase619_ordinary_ruby_active() -> bool:
    return activation_report()["phase619_ordinary_ruby_active"]
