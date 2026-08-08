# -*- coding: utf-8 -*-
"""Load the reviewed Phase 513 -> Phase 532 authority carry-forward ledger.

This ledger does not make new Ruby decisions.  It records the five existing
decision scopes whose fake/coarse manifest entries and paired master rows are
byte-for-byte unchanged between the two frozen phases.  The companion builder
rechecks that source closure; this module keeps consumers fail-closed on the
reviewed line sets and their aggregate fingerprints.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
LEDGER_PATH = HERE / "_phase532_derived_authority_carry_forward.json"

PHASE_FROM = 513
PHASE_TO = 532
EXPECTED_MASTER_LINES = 62313
POLICY = (
    "Carry forward only previously reviewed fake/coarse and localized atomic "
    "authorities whose complete manifest entries and paired learner/academic "
    "source rows are exactly unchanged from the frozen Phase 513 baseline to "
    "the frozen Phase 532 candidate."
)

PHASE513_FAKE_MANIFEST_SHA256 = (
    "8C507321A27ACD3FE9F919E82C1C380833D6D51760C122467D49757511004504"
)
PHASE513_FAKE_ENTRIES_SHA256 = (
    "A542BC4464CDA30FBE39C28F0EFBEE51EECE83EEABBEA5D3A201388DA3AA7DEB"
)
PHASE532_FAKE_MANIFEST_SHA256 = (
    "5F743A916742BE022EFDEC30D24B5ACA0EB2A9156A2086FBB01740DDC356A060"
)
PHASE532_FAKE_ENTRIES_SHA256 = (
    "8F823A44A62AFB38321662FB843F52D9E97FB5953962CD5B75406B2F1EBC4368"
)
PHASE513_LEARNER_SHA256 = (
    "1435F5B1CD1B0BB8224521A8262E3CA740B07B7523E805545A4E3CA7447A286C"
)
PHASE513_ACADEMIC_SHA256 = (
    "4C813C48B3C4919601FA51E25B6AA3628A0A6793A39C49F1DDFB22A9112E1A0A"
)
PHASE532_LEARNER_SHA256 = (
    "6B403AA30BBCBBA4C9E41A2CF48D1AD2FC1D5A5DB1154CAF1260A361566E3226"
)
PHASE532_ACADEMIC_SHA256 = (
    "FE632820E7752A555787C926C0A843CD82B2F79D4177A6D8D1E9622CA96393A5"
)
PEJVO_SHA256 = (
    "B551510513C1924E65E64CF87EA4CE39128E80717E3A3F53847753F8A0557CBF"
)

# A raw-byte pin makes newline or manual metadata drift visible to every
# consumer in addition to the semantic pins below.
LEDGER_SHA256 = (
    "D4D4CD8BFC274A006BDA89C8B5E250B4EE1D4286969552F484237E1FF3B97A90"
)

EXPECTED_SOURCES = {
    "phase513_fake_manifest": {
        "sha256": PHASE513_FAKE_MANIFEST_SHA256,
        "entries_sha256": PHASE513_FAKE_ENTRIES_SHA256,
        "entries": 3213,
    },
    "phase532_fake_manifest": {
        "sha256": PHASE532_FAKE_MANIFEST_SHA256,
        "entries_sha256": PHASE532_FAKE_ENTRIES_SHA256,
        "entries": 3238,
    },
    "phase513_learner": {
        "sha256": PHASE513_LEARNER_SHA256,
        "lines": EXPECTED_MASTER_LINES,
    },
    "phase513_academic": {
        "sha256": PHASE513_ACADEMIC_SHA256,
        "lines": EXPECTED_MASTER_LINES,
    },
    "phase532_learner": {
        "sha256": PHASE532_LEARNER_SHA256,
        "lines": EXPECTED_MASTER_LINES,
    },
    "phase532_academic": {
        "sha256": PHASE532_ACADEMIC_SHA256,
        "lines": EXPECTED_MASTER_LINES,
    },
}

DECISION_SOURCE_SPECS = {
    "phase511_transition": {
        "path": "_fake_coarse_phase511_transition_review.json",
        "sha256": (
            "72D3CDE187680F4CD0DD178915FEBF9DD1FA421B1C4AC17B25374720FDB9CEA8"
        ),
        "semantic_key": "entries",
        "semantic_sha256": (
            "3F7DBBB34ECE9D3657444818F753755176C89E66307E4AE0E0297A59B8919BFF"
        ),
        "decision_records": 21,
        "learner_lines": 21,
    },
    "ff33_transition": {
        "path": "_fake_coarse_ff33_transition_review.json",
        "sha256": (
            "BD5E4B5A2BC7D6D37AB910E2A250F203CF402DFAF8BDF933265863D1FF3F247A"
        ),
        "semantic_key": "entries",
        "semantic_sha256": (
            "3296A91605BCDD1E946966B72AEAC9855F3488347CA6A12913C679F86430ED31"
        ),
        "decision_records": 1,
        "learner_lines": 1,
    },
    "5e_transition": {
        "path": "_fake_coarse_5e_transition_review.json",
        "sha256": (
            "4DB426E02930B87B9581C820DA0AF04F993180BBFC0DC16D39619A501AE59783"
        ),
        "semantic_key": "entries",
        "semantic_sha256": (
            "B0CF495ECDEA78DEA86AEB72CFF5252140C67D342947A391200CA9936BF41E1F"
        ),
        "decision_records": 1,
        "learner_lines": 1,
    },
    "app_review": {
        "path": "_fake_coarse_transition_app_review.json",
        "sha256": (
            "490044D49D5C49F295D21BC2B932B50AA16718E0FA69743C52F6041BE9D19804"
        ),
        "semantic_key": "entries",
        "semantic_sha256": (
            "216E85708B4419EE0D7BE9F36068C19EBDB7666B55A1E3B7077590973729EA5A"
        ),
        "decision_records": 85,
        "learner_lines": 86,
    },
    "atomic_families": {
        "path": "localized_atomic_root_families.json",
        "sha256": (
            "BCB852B525953F2440299FB93CC86245129773CDD5BD99998822D0BA1EBEE267"
        ),
        "semantic_key": "families",
        "semantic_sha256": (
            "B047D6177321BC1E3B0C73D57B57A8B20EA79679E309AC8E3BCFBAABCF57BB61"
        ),
        "decision_records": 2,
        "learner_lines": 4,
    },
}

EXPECTED_AUTHORITY_GROUPS = {
    "phase511_transition": {
        "learner_lines": [
            4785, 21361, 24033, 34886, 44893, 45205, 45818, 46627,
            48081, 49821, 51048, 54151, 54383, 55369, 59757, 60165,
            60166, 60167, 60168, 60169, 60735,
        ],
        "learner_lines_sha256": (
            "28098878BA4329F600F336B2DF995C752480534EB3165C66DDF1AABF2CBE2E4E"
        ),
        "phase513_fake_entries_sha256": (
            "BBF1A181F67DDE239DFE1EE1B49A67E88C64FC4235A1B0C5E5F60A0668067CA6"
        ),
        "phase532_fake_entries_sha256": (
            "BBF1A181F67DDE239DFE1EE1B49A67E88C64FC4235A1B0C5E5F60A0668067CA6"
        ),
        "phase513_learner_lines_sha256": (
            "C0E6F91F4B30AE4787686DCECD34D7A6179350D2A9813085248298FD06A4CF61"
        ),
        "phase532_learner_lines_sha256": (
            "C0E6F91F4B30AE4787686DCECD34D7A6179350D2A9813085248298FD06A4CF61"
        ),
        "phase513_academic_lines_sha256": (
            "BDDEB2FEE03097A5DEBE4AF3989587EA02E82E21EB3069E16534EE87BD482F10"
        ),
        "phase532_academic_lines_sha256": (
            "BDDEB2FEE03097A5DEBE4AF3989587EA02E82E21EB3069E16534EE87BD482F10"
        ),
    },
    "ff33_transition": {
        "learner_lines": [56273],
        "learner_lines_sha256": (
            "AC6DF18E94AA24DFCF4BE17C5EE33D8FE09974798BC30BE2789D2611F63B352E"
        ),
        "phase513_fake_entries_sha256": (
            "79E7309CA041594B466647FCC044B219C538E44ED259B3255F28D52F0DCE0CF3"
        ),
        "phase532_fake_entries_sha256": (
            "79E7309CA041594B466647FCC044B219C538E44ED259B3255F28D52F0DCE0CF3"
        ),
        "phase513_learner_lines_sha256": (
            "2FAD01C8FE26159E3BBEF973E9462939724D6089BFBE8667987BA769EF8A4407"
        ),
        "phase532_learner_lines_sha256": (
            "2FAD01C8FE26159E3BBEF973E9462939724D6089BFBE8667987BA769EF8A4407"
        ),
        "phase513_academic_lines_sha256": (
            "F91BB9B221E66C5997D3529904038E8B0658AA2F9FD9F6988C9459D6DDEC95B5"
        ),
        "phase532_academic_lines_sha256": (
            "F91BB9B221E66C5997D3529904038E8B0658AA2F9FD9F6988C9459D6DDEC95B5"
        ),
    },
    "5e_transition": {
        "learner_lines": [53890],
        "learner_lines_sha256": (
            "3063C3A8B6AD13C97FDFCAF8087F063597A25366628964C7CF480BCA559F330E"
        ),
        "phase513_fake_entries_sha256": (
            "1A9E50D34FFA10D59A81C6C91C6A8A8EB54F8318E51B4CDDE685CFB18EC32504"
        ),
        "phase532_fake_entries_sha256": (
            "1A9E50D34FFA10D59A81C6C91C6A8A8EB54F8318E51B4CDDE685CFB18EC32504"
        ),
        "phase513_learner_lines_sha256": (
            "0025380F7E596CB731F95C901E1A6C0AE0BBD89D4FAC05002EEFD2C1334CA840"
        ),
        "phase532_learner_lines_sha256": (
            "0025380F7E596CB731F95C901E1A6C0AE0BBD89D4FAC05002EEFD2C1334CA840"
        ),
        "phase513_academic_lines_sha256": (
            "79B935271CE6D4B4820F93C5F504E635AC8AD0B2C05E21DFAD1B6C8A74245D70"
        ),
        "phase532_academic_lines_sha256": (
            "79B935271CE6D4B4820F93C5F504E635AC8AD0B2C05E21DFAD1B6C8A74245D70"
        ),
    },
    "app_review": {
        "learner_lines": [
            1782, 2748, 6807, 9812, 17849, 18310, 21783, 34793, 34885,
            38127, 39909, 41711, 42834, 44554, 44618, 44739, 44868,
            45393, 45942, 46000, 46394, 46788, 46995, 47129, 47213,
            47413, 47815, 47922, 48239, 48359, 48437, 48588, 48836,
            48840, 49006, 49065, 49069, 49190, 49519, 49686, 49781,
            49967, 49992, 50266, 50687, 50906, 51082, 51120, 51158,
            51434, 51619, 51870, 52025, 52129, 52695, 52870, 52997,
            53017, 53020, 53022, 53191, 53385, 53444, 53627, 54301,
            54393, 54530, 54568, 54621, 54673, 54793, 55014, 55461,
            55534, 55564, 55964, 55968, 56065, 56093, 56235, 56523,
            56728, 58136, 58547, 61139, 61371,
        ],
        "learner_lines_sha256": (
            "71DC52BC02031A5C69502B579FD55F09400ADCD01463359815B7C6DC9929F0E1"
        ),
        "phase513_fake_entries_sha256": (
            "386620F0B0FAC34B01AF1551D1596655C2C176E44E6B154417EC311A5D14347E"
        ),
        "phase532_fake_entries_sha256": (
            "386620F0B0FAC34B01AF1551D1596655C2C176E44E6B154417EC311A5D14347E"
        ),
        "phase513_learner_lines_sha256": (
            "285D37C7C0D2CB36CD5FDE4860221A902A86E7CAF5D9B53F99B9C6472F1F1BD9"
        ),
        "phase532_learner_lines_sha256": (
            "285D37C7C0D2CB36CD5FDE4860221A902A86E7CAF5D9B53F99B9C6472F1F1BD9"
        ),
        "phase513_academic_lines_sha256": (
            "6308E98B597E2E91C8071EDF03B5B7DBECA53475F39959DA11D9E904876866A5"
        ),
        "phase532_academic_lines_sha256": (
            "6308E98B597E2E91C8071EDF03B5B7DBECA53475F39959DA11D9E904876866A5"
        ),
    },
    "atomic_families": {
        "learner_lines": [4042, 27866, 27867, 27869],
        "learner_lines_sha256": (
            "C07CCC18A716DFA5A63A2B56E8FE513C3DBB3E904328D8AD50E00356EF7EE4A9"
        ),
        "phase513_fake_entries_sha256": (
            "FE1BA5A6D64DBBD2DDF175F9F9C4603383676DD35816849985D1DA3AFAB60FBD"
        ),
        "phase532_fake_entries_sha256": (
            "FE1BA5A6D64DBBD2DDF175F9F9C4603383676DD35816849985D1DA3AFAB60FBD"
        ),
        "phase513_learner_lines_sha256": (
            "63091CD1AF6AF9375D81AB27182079A69CDDEBF9CEF0E70BAEF18BD616E32997"
        ),
        "phase532_learner_lines_sha256": (
            "63091CD1AF6AF9375D81AB27182079A69CDDEBF9CEF0E70BAEF18BD616E32997"
        ),
        "phase513_academic_lines_sha256": (
            "73860676EF1B36273BDE3C6A8AD198291B9EF0D882F57530CE8927441920DB73"
        ),
        "phase532_academic_lines_sha256": (
            "73860676EF1B36273BDE3C6A8AD198291B9EF0D882F57530CE8927441920DB73"
        ),
    },
}

EXPECTED_COUNTS = {
    "authority_groups": 5,
    "decision_records": 110,
    "reviewed_learner_lines": 113,
    "phase511_lines": 21,
    "ff33_lines": 1,
    "5e_lines": 1,
    "app_review_entries": 85,
    "app_review_lines": 86,
    "atomic_families": 2,
    "atomic_authority_lines": 4,
}
REVIEWED_LINE_UNION_SHA256 = (
    "29A7E25096900620BF3919F90893BC5C146C303D5A14609622C85DA6007AE365"
)


def compact_sha256(value) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def validate_ledger_payload(payload: dict) -> dict:
    expected_keys = {
        "schema_version", "phase_from", "phase_to", "candidate_only",
        "policy", "sources", "decision_sources", "expected_counts",
        "reviewed_line_union_sha256", "authorities",
    }
    if set(payload) != expected_keys:
        raise ValueError("unsupported Phase 532 carry-forward ledger keys")
    if (
        payload.get("schema_version") != 1
        or payload.get("phase_from") != PHASE_FROM
        or payload.get("phase_to") != PHASE_TO
        or payload.get("candidate_only") is not False
        or payload.get("policy") != POLICY
        or payload.get("sources") != EXPECTED_SOURCES
        or payload.get("decision_sources") != DECISION_SOURCE_SPECS
        or payload.get("expected_counts") != EXPECTED_COUNTS
        or payload.get("reviewed_line_union_sha256")
        != REVIEWED_LINE_UNION_SHA256
        or payload.get("authorities") != EXPECTED_AUTHORITY_GROUPS
    ):
        raise ValueError("Phase 532 carry-forward reviewed identity drift")

    line_sets = []
    for name, expected in EXPECTED_AUTHORITY_GROUPS.items():
        lines = expected["learner_lines"]
        if (
            lines != sorted(lines)
            or len(lines) != len(set(lines))
            or compact_sha256(lines) != expected["learner_lines_sha256"]
            or len(lines) != DECISION_SOURCE_SPECS[name]["learner_lines"]
        ):
            raise ValueError(f"invalid carry-forward line scope: {name}")
        if (
            expected["phase513_fake_entries_sha256"]
            != expected["phase532_fake_entries_sha256"]
            or expected["phase513_learner_lines_sha256"]
            != expected["phase532_learner_lines_sha256"]
            or expected["phase513_academic_lines_sha256"]
            != expected["phase532_academic_lines_sha256"]
        ):
            raise ValueError(f"non-identical carry-forward fingerprint: {name}")
        line_sets.append(set(lines))
    if any(
        left & right
        for index, left in enumerate(line_sets)
        for right in line_sets[index + 1:]
    ):
        raise ValueError("carry-forward authority scopes overlap")
    union = sorted(set().union(*line_sets))
    if (
        len(union) != EXPECTED_COUNTS["reviewed_learner_lines"]
        or compact_sha256(union) != REVIEWED_LINE_UNION_SHA256
    ):
        raise ValueError("carry-forward authority union drift")
    return payload


def load_phase532_authority_carry_forward() -> dict:
    raw = LEDGER_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest().upper() != LEDGER_SHA256:
        raise ValueError("Phase 532 carry-forward ledger raw identity drift")
    return validate_ledger_payload(json.loads(raw.decode("utf-8")))


def authority_lines() -> dict[str, tuple[int, ...]]:
    """Return the reviewed, mutually disjoint source lines by authority."""
    payload = load_phase532_authority_carry_forward()
    return {
        name: tuple(reviewed["learner_lines"])
        for name, reviewed in payload["authorities"].items()
    }


def review_identity() -> dict:
    """Return the compact identity consumed by downstream audit manifests."""
    payload = load_phase532_authority_carry_forward()
    return {
        "phase_from": payload["phase_from"],
        "phase_to": payload["phase_to"],
        "ledger_sha256": LEDGER_SHA256,
        "phase513_fake_manifest_sha256": PHASE513_FAKE_MANIFEST_SHA256,
        "phase513_fake_entries_sha256": PHASE513_FAKE_ENTRIES_SHA256,
        "phase532_fake_manifest_sha256": PHASE532_FAKE_MANIFEST_SHA256,
        "phase532_fake_entries_sha256": PHASE532_FAKE_ENTRIES_SHA256,
        "authority_groups": EXPECTED_COUNTS["authority_groups"],
        "reviewed_learner_lines": EXPECTED_COUNTS["reviewed_learner_lines"],
        "reviewed_line_union_sha256": REVIEWED_LINE_UNION_SHA256,
    }
