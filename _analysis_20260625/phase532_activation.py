# -*- coding: utf-8 -*-
"""Fail-closed activation gate for the formally adopted Phase 532 rules.

The policy files may exist before adoption, but their seven managed Ruby
settings must not influence generation until scope, strict ledger and the
tracked fake/coarse authority have moved to one coherent Phase 532 state.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import phase532_authority_carry_forward as carry
import phase532_ruby_policy as policy


HERE = Path(__file__).resolve().parent
SCOPE_PATH = HERE / "_no_worsening_scope_manifest.json"
STRICT_PATH = HERE / "_strict_gold_reference_fixes.json"
FAKE_REFERENCE_PATH = HERE / "_fake_coarse_reference_manifest.json"

PHASE513_PROJECTION_SHA256 = (
    "361505F0B7CE0966085089346F8619F13A09D1DC9D3536408CECB12BBEB35444"
)
PHASE513_REFERENCE_SHA256 = (
    "EB81086916F181D657D683EC5E983C5E0D3FE287E71AA9D059ABA98D1A33E357"
)
PHASE513_STRICT_ENTRIES_SHA256 = (
    "61B497E12602D03DF51FA82ACC49653070476E81216FCB9733FC40CAB7A75AAA"
)
PHASE532_PROJECTION_SHA256 = (
    "75AC6732AACD145F91EE7866738E57D073A998F1634AADA9D28CCFE3FBCAD3D6"
)
PHASE532_REFERENCE_SHA256 = (
    "308121D186957A792073F1620C5A4E5EA80D3B7EAA87DFE39573E05A2FE822A9"
)
PHASE532_STRICT_ENTRIES_SHA256 = (
    "CA736E47CEAC5F128FFB491A976C930C0B37895D498ECF7656A9AC17F2C3B017"
)


def stable_json_sha256(value) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


def compact_sha256(value) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


def activation_report(
    *, scope_path: Path = SCOPE_PATH, strict_path: Path = STRICT_PATH,
    fake_reference_path: Path = FAKE_REFERENCE_PATH,
) -> dict:
    scope = json.loads(Path(scope_path).read_text(encoding="utf-8"))
    expected = scope.get("expected", {})
    projection_sha256 = stable_json_sha256(expected)
    if (
        set(scope) != {
            "manifest_schema_version", "projection_sha256", "expected",
        }
        or scope.get("manifest_schema_version") != 1
        or scope.get("projection_sha256") != projection_sha256
    ):
        raise ValueError("no-worsening scope identity mismatch")

    strict = json.loads(Path(strict_path).read_text(encoding="utf-8"))
    strict_entries = strict.get("entries", [])
    if (
        strict.get("schema_version") != 1
        or strict.get("reference_schema_version") != 5
        or strict.get("expected_entries") != len(strict_entries)
        or strict.get("entries_sha256") != compact_sha256(strict_entries)
    ):
        raise ValueError("strict reference identity mismatch")
    fake_sha256 = hashlib.sha256(
        Path(fake_reference_path).read_bytes()
    ).hexdigest().upper()
    gold_sha256 = expected.get("gold", {}).get("sha256")
    reference_sha256 = expected.get("reference_sha256")

    if gold_sha256 == policy.BASELINE_LEARNER_SHA256:
        if (
            projection_sha256 != PHASE513_PROJECTION_SHA256
            or reference_sha256 != PHASE513_REFERENCE_SHA256
            or "phase532_ruby_policy" in expected
            or "phase532_authority_carry_forward" in expected
            or fake_sha256 != carry.PHASE513_FAKE_MANIFEST_SHA256
            or strict.get("gold_sha256") != policy.BASELINE_LEARNER_SHA256
            or strict.get("reference_sha256") != PHASE513_REFERENCE_SHA256
            or strict.get("expected_entries") != 933
            or strict.get("entries_sha256")
            != PHASE513_STRICT_ENTRIES_SHA256
        ):
            raise ValueError("incoherent Phase 513 activation state")
        active = False
    elif gold_sha256 == policy.CANDIDATE_LEARNER_SHA256:
        if (
            projection_sha256 != PHASE532_PROJECTION_SHA256
            or reference_sha256 != PHASE532_REFERENCE_SHA256
            or expected.get("phase532_ruby_policy")
            != policy.review_identity()
            or expected.get("phase532_authority_carry_forward")
            != carry.review_identity()
            or fake_sha256 != policy.CANDIDATE_MANIFEST_SHA256
            or strict.get("gold_sha256") != policy.CANDIDATE_LEARNER_SHA256
            or strict.get("reference_sha256") != PHASE532_REFERENCE_SHA256
            or strict.get("expected_entries") != 932
            or strict.get("entries_sha256")
            != PHASE532_STRICT_ENTRIES_SHA256
        ):
            raise ValueError("incoherent Phase 532 activation state")
        active = True
    else:
        raise ValueError(f"unsupported activation gold identity: {gold_sha256!r}")
    return {
        "phase532_active": active,
        "gold_sha256": gold_sha256,
        "reference_sha256": reference_sha256,
        "projection_sha256": projection_sha256,
        "fake_manifest_sha256": fake_sha256,
        "strict_entries_sha256": strict["entries_sha256"],
        "gate": True,
    }


def phase532_active() -> bool:
    return activation_report()["phase532_active"]
