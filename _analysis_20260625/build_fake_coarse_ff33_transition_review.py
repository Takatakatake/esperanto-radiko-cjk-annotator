# -*- coding: utf-8 -*-
"""Build/check the Tomisto transition introduced by the FF33 snapshot.

The historical 136-row C679/B090 transition is provenance-frozen.  FF33 adds
one new evaluable fake row, Tom/ist/o, whose annotation-ruby authority is the
paired academic Tomist/o.  It persists unchanged in the final 5E snapshot;
keep its lineage scope separate from the later 5E promil delta.
"""
import argparse
import hashlib
import json
from pathlib import Path

from atomic_json import atomic_json_dump


HERE = Path(__file__).resolve().parent
REFERENCE = HERE / "_phase513_fake_coarse_reference_manifest.json"
OUTPUT = HERE / "_fake_coarse_ff33_transition_review.json"
EXPECTED_LEARNER_SHA256 = (
    "1435F5B1CD1B0BB8224521A8262E3CA740B07B7523E805545A4E3CA7447A286C"
)
EXPECTED_ACADEMIC_SHA256 = (
    "4C813C48B3C4919601FA51E25B6AA3628A0A6793A39C49F1DDFB22A9112E1A0A"
)
EXPECTED_ENTRIES_SHA256 = (
    "3296A91605BCDD1E946966B72AEAC9855F3488347CA6A12913C679F86430ED31"
)
REASON = (
    "FF33 paired-master delta: the learner keeps Tom/ist/o only on the "
    "fake/Kanji track; annotation ruby follows the paired academic Tomist/o "
    "lexical root."
)


def compact_sha256(value):
    raw = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


def build_payload():
    reference_raw = REFERENCE.read_bytes()
    reference = json.loads(reference_raw.decode("utf-8"))
    sources = reference.get("sources", {})
    if (
        sources.get("learner", {}).get("sha256") != EXPECTED_LEARNER_SHA256
        or sources.get("academic", {}).get("sha256")
        != EXPECTED_ACADEMIC_SHA256
    ):
        raise ValueError("final paired-master source identity changed")
    selected = [
        entry for entry in reference.get("entries", [])
        if entry.get("learner_line") == 56273
    ]
    if len(selected) != 1:
        raise ValueError("FF33 transition must select exactly learner line 56273")
    source = selected[0]
    expected_source = {
        "surface": "Tomisto",
        "learner_decomposition": "Tom/ist/o",
        "coarse_decomposition": "Tomist/o",
        "academic_decomposition": "Tomist/o",
        "authority": "paired_academic",
    }
    if any(source.get(key) != value for key, value in expected_source.items()):
        raise ValueError(f"FF33 Tomisto authority changed: {source!r}")
    entry = {
        "learner_line": 56273,
        **expected_source,
        "target": "Tomist/o",
        "typed_roles": "RL",
        "case_sensitive": True,
        "category": "reviewed_ff33_new_fake_marker",
        "reason": REASON,
    }
    entries = [entry]
    entries_sha256 = compact_sha256(entries)
    if entries_sha256 != EXPECTED_ENTRIES_SHA256:
        raise ValueError("FF33 transition entry fingerprint changed")

    # The exact rule may be deployed only while every language can annotate
    # the single lexical root as one unit.
    localized = {}
    for language in ("ja", "zh", "ko"):
        path = HERE / "out" / f"word_anno_{language}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        matches = [
            (key, pairs) for key, pairs in data.items()
            if key.casefold() == "tomist"
        ]
        if (
            len(matches) != 1
            or len(matches[0][1]) != 1
            or matches[0][1][0][0].casefold() != "tomist"
            or not matches[0][1][0][1]
        ):
            raise ValueError(f"{language}: Tomist localized root is unavailable")
        localized[language] = matches[0][1][0][1]
    return {
        "schema_version": 1,
        "source_fake_coarse_manifest_sha256": hashlib.sha256(
            reference_raw
        ).hexdigest().upper(),
        "source_fake_coarse_entries_sha256": reference["entries_sha256"],
        "sources": {
            "learner": sources["learner"],
            "academic": sources["academic"],
        },
        "counts": {
            "entries": 1,
            "evaluable_entries": 1,
            "new_fake_marker_rows": 1,
        },
        "localized_glosses": localized,
        "entries_sha256": entries_sha256,
        "entries": entries,
    }


def validate(payload):
    rebuilt = build_payload()
    if payload != rebuilt:
        raise ValueError("FF33 transition review is stale")
    return rebuilt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    payload = build_payload()
    if args.write:
        atomic_json_dump(OUTPUT, payload, indent=1)
    else:
        validate(json.loads(OUTPUT.read_text(encoding="utf-8")))
    print(json.dumps({
        "manifest": str(OUTPUT),
        "mode": "write" if args.write else "check",
        "counts": payload["counts"],
        "entries_sha256": payload["entries_sha256"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
