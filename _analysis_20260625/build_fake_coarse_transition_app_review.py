# -*- coding: utf-8 -*-
"""Build/check the 85-surface staged app correction manifest.

Only independently reviewed runtime mismatches from the 132-surface B090
transition are selected.  Rules are exact and typed; they do not bulk-enable
the remaining fake-row queue.  Existing localized CSV/word_anno glosses are
required in all languages, except the one explicitly reviewed synonym-level
display annotation for tefoliin.
"""
import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path

from atomic_json import atomic_json_dump
import no_worsening_audit as boundary_audit


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULT_MANIFEST = HERE / "_fake_coarse_transition_app_review.json"
TRANSITION_MANIFEST = HERE / "_fake_coarse_transition_review.json"
FAKE_AUTHORITY_MANIFEST = HERE / "_fake_coarse_reference_manifest.json"
AUTHORITY_AUDIT_SHA256 = (
    "F50456E073043BAD432736C0EAAC7C8240AEC96EC67A04A17D512B561E58C3D0"
)
EXPECTED_ENTRIES_SHA256 = (
    "216E85708B4419EE0D7BE9F36068C19EBDB7666B55A1E3B7077590973729EA5A"
)
EXPECTED_COUNTS = {
    "entries": 85,
    "existing_localized_gloss": 84,
    "reviewed_exact_localized_annotation": 1,
    "html_intersection_surfaces": 0,
}
LANGUAGES = {"ja": "JA", "zh": "ZH", "ko": "KO"}
EXPLICIT_LOCALIZED = {
    "tefoliino": {
        "piece": "tefoliin",
        "glosses": {
            "ja": "テオフィリン",
            "zh": "茶碱",
            "ko": "테오필린",
        },
        "review_basis": (
            "Conservative synonym-level Ruby display. Academic te/foliin/o and "
            "PIV's internal te+foli+ino analysis are recorded counterevidence; "
            "tefoliin is not asserted to be an official indivisible PIV root."
        ),
    },
}


def sha256_bytes(raw):
    return hashlib.sha256(raw).hexdigest().upper()


def entries_sha256(entries):
    return sha256_bytes(json.dumps(
        entries, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8"))


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def localized_root_sets():
    result = {}
    identities = {}
    for language, app_code in LANGUAGES.items():
        data_dir = ROOT / f"Esperanto-Kanji-Ruby-{app_code}" / "app_data"
        # The language-local annotation CSV is the largest CSV in each app;
        # the smaller files are shared Kanji/foreign-language auxiliaries.
        csv_path = max(data_dir.glob("*.csv"), key=lambda path: path.stat().st_size)
        roots = set()
        with csv_path.open(encoding="utf-8", newline="") as handle:
            for row in csv.reader(handle):
                if row and row[0].strip():
                    roots.add(row[0].strip())
        word_anno_path = HERE / "out" / f"word_anno_{language}.json"
        word_anno = load_json(word_anno_path)
        roots.update(key for key in word_anno if not key.startswith("@typed:"))
        result[language] = roots
        identities[language] = {
            "csv": csv_path.relative_to(ROOT).as_posix(),
            "csv_sha256": sha256_bytes(csv_path.read_bytes()),
            "csv_rows": len(roots),
        }
    return result, identities


def transition_by_surface():
    payload = load_json(TRANSITION_MANIFEST)
    rows = collections.defaultdict(list)
    for row in payload["entries"]:
        rows[row["surface"]].append(row)
    return payload, rows


def build(audit_path):
    raw = audit_path.read_bytes()
    if sha256_bytes(raw) != AUTHORITY_AUDIT_SHA256:
        raise ValueError("revised transition authority audit SHA256 changed")
    authority_audit = json.loads(raw.decode("utf-8-sig"))
    transition, transitions = transition_by_surface()
    root_sets, gloss_sources = localized_root_sets()
    selected = [
        row for row in authority_audit["rows"]
        if row.get("runtime_correction_required") is True
    ]
    if len(selected) != 85 or len({row["surface"] for row in selected}) != 85:
        raise ValueError("revised authority audit no longer selects exactly 85 surfaces")
    entries = []
    explicit_used = set()
    for row in selected:
        surface = row["surface"]
        audited_target = row["proposed_safe_coarse_decomposition"]
        transition_rows = transitions.get(surface, [])
        paired_lines = sorted(
            mapping["line"] for mapping in row.get("paired_line_mapping", [])
        )
        transition_targets = {
            item["coarse_decomposition"] for item in transition_rows
        }
        if (
            not transition_rows
            or sorted(item["learner_line"] for item in transition_rows)
            != paired_lines
            or len(transition_targets) != 1
        ):
            raise ValueError(f"app review is outside staged transition: {surface!r}")
        target = next(iter(transition_targets))
        pieces = [piece for piece in target.split("/") if piece]
        typed_parts = boundary_audit.expected_typed_parts(target)
        visible, normalized_spans = boundary_audit.signature_from_typed_parts(
            typed_parts,
        )
        spans = [
            {"text": piece, "ruby": is_ruby}
            for piece, is_ruby in normalized_spans
        ]
        if visible != surface or len(pieces) != len(spans):
            raise ValueError(f"typed transition reconstruction drift: {surface!r}")
        typed_roles = "".join("R" if span["ruby"] else "L" for span in spans)
        if any(span["text"] != piece for span, piece in zip(spans, pieces)):
            raise ValueError(f"typed transition piece drift: {surface!r}")
        missing = collections.defaultdict(list)
        for piece, role in zip(pieces, typed_roles):
            if role != "R":
                continue
            for language, roots in root_sets.items():
                if piece not in roots:
                    missing[piece].append(language)
        explicit = EXPLICIT_LOCALIZED.get(surface)
        if explicit is None:
            if missing:
                raise ValueError(
                    f"transition root lacks localized gloss: {surface!r}: {dict(missing)!r}"
                )
            gloss_mode = "existing_localized_csv_or_word_anno"
        else:
            if (
                dict(missing) != {explicit["piece"]: ["ja", "zh", "ko"]}
                or explicit["piece"] not in pieces
                or typed_roles[pieces.index(explicit["piece"])] != "R"
            ):
                raise ValueError(f"explicit localized exception drift: {surface!r}")
            explicit_used.add(surface)
            gloss_mode = "reviewed_exact_localized_annotation"
        runtime = row["runtime_snapshot"]
        before = {language: runtime[language]["typed_decomposition"] for language in ("JA", "ZH", "KO")}
        if len(set(before.values())) != 1:
            raise ValueError(f"transition runtime was not three-language aligned: {surface!r}")
        html_row = row.get("html", {})
        entry = {
            "surface": surface,
            "target": target,
            "typed_roles": typed_roles,
            "learner_lines": paired_lines,
            "authority_source": (
                "PROJECT_REVIEW_OVERRIDE"
                if target != audited_target else row["authority_source"]
            ),
            "rule_mode": "exact_typed_case_sensitive",
            "gloss_mode": gloss_mode,
            "runtime_before_typed": before["JA"],
            "runtime_after_expected_typed": "/".join(
                f"{'R' if span['ruby'] else 'L'}:{span['text']}"
                for span in spans
            ),
            "semantic_change": "collapse_rejected_fake_internal_boundaries",
            "html_intersection": {
                "annotated_token_count": html_row.get("annotated_token_count", 0),
                "visible_text_token_count": html_row.get("visible_text_token_count", 0),
                "files": html_row.get("files", {}),
            },
        }
        if explicit is not None:
            entry["exact_annotation"] = explicit
        if target != audited_target:
            entry["audited_academic_target"] = audited_target
            entry["authority_adjustment"] = next(
                item.get("authority_adjustment") for item in transition_rows
                if item.get("authority_adjustment")
            )
        entries.append(entry)
    if explicit_used != set(EXPLICIT_LOCALIZED):
        raise ValueError(
            f"unused explicit localized reviews: {sorted(set(EXPLICIT_LOCALIZED) - explicit_used)!r}"
        )
    entries.sort(key=lambda row: row["surface"])
    return {
        "schema_version": 1,
        "authority_audit_sha256": AUTHORITY_AUDIT_SHA256,
        "transition_manifest": {
            "sha256": sha256_bytes(TRANSITION_MANIFEST.read_bytes()),
            "entries_sha256": transition["entries_sha256"],
        },
        "fake_authority_manifest": {
            "sha256": sha256_bytes(FAKE_AUTHORITY_MANIFEST.read_bytes()),
            "entries_sha256": load_json(FAKE_AUTHORITY_MANIFEST)["entries_sha256"],
        },
        "localized_sources": gloss_sources,
        "counts": {
            "entries": len(entries),
            "existing_localized_gloss": sum(
                row["gloss_mode"] == "existing_localized_csv_or_word_anno"
                for row in entries
            ),
            "reviewed_exact_localized_annotation": sum(
                row["gloss_mode"] == "reviewed_exact_localized_annotation"
                for row in entries
            ),
            "html_intersection_surfaces": sum(
                bool(row["html_intersection"]["annotated_token_count"])
                for row in entries
            ),
        },
        "entries_sha256": entries_sha256(entries),
        "entries": entries,
    }


def validate(payload):
    if payload.get("schema_version") != 1:
        raise ValueError("unsupported transition app-review schema")
    entries = payload.get("entries", [])
    if (
        entries_sha256(entries) != payload.get("entries_sha256")
        or payload.get("entries_sha256") != EXPECTED_ENTRIES_SHA256
    ):
        raise ValueError("transition app-review entry fingerprint mismatch")
    if payload.get("authority_audit_sha256") != AUTHORITY_AUDIT_SHA256:
        raise ValueError("transition app-review provenance changed")
    transition, transitions = transition_by_surface()
    fake_authority = load_json(FAKE_AUTHORITY_MANIFEST)
    if payload.get("transition_manifest") != {
        "sha256": sha256_bytes(TRANSITION_MANIFEST.read_bytes()),
        "entries_sha256": transition["entries_sha256"],
    }:
        raise ValueError("transition app review uses a stale transition manifest")
    if payload.get("fake_authority_manifest") != {
        "sha256": sha256_bytes(FAKE_AUTHORITY_MANIFEST.read_bytes()),
        "entries_sha256": fake_authority["entries_sha256"],
    }:
        raise ValueError("transition app review uses a stale fake authority manifest")
    if len(entries) != 85 or len({row.get("surface") for row in entries}) != 85:
        raise ValueError("transition app review must contain exactly 85 surfaces")
    root_sets, gloss_sources = localized_root_sets()
    if payload.get("localized_sources") != gloss_sources:
        raise ValueError("transition localized CSV identity changed")
    explicit_used = set()
    for row in entries:
        surface = row.get("surface")
        pieces = [piece for piece in row.get("target", "").split("/") if piece]
        roles = row.get("typed_roles", "")
        if (
            "".join(pieces) != surface or len(pieces) != len(roles)
            or any(role not in "RL" for role in roles)
            or row.get("rule_mode") != "exact_typed_case_sensitive"
            or row.get("semantic_change")
            != "collapse_rejected_fake_internal_boundaries"
        ):
            raise ValueError(f"invalid transition app row: {row!r}")
        transition_rows = transitions.get(surface, [])
        if (
            sorted(item["learner_line"] for item in transition_rows)
            != row.get("learner_lines")
            or any(item["coarse_decomposition"] != row["target"] for item in transition_rows)
        ):
            raise ValueError(f"transition app row escaped reviewed scope: {surface!r}")
        missing = collections.defaultdict(list)
        for piece, role in zip(pieces, roles):
            if role == "R":
                for language, roots in root_sets.items():
                    if piece not in roots:
                        missing[piece].append(language)
        exact = row.get("exact_annotation")
        if exact is None:
            if missing or row.get("gloss_mode") != "existing_localized_csv_or_word_anno":
                raise ValueError(f"untranslated transition root: {surface!r}")
        else:
            if exact != EXPLICIT_LOCALIZED.get(surface):
                raise ValueError(f"unreviewed exact transition annotation: {surface!r}")
            if dict(missing) != {exact["piece"]: ["ja", "zh", "ko"]}:
                raise ValueError(f"exact transition annotation coverage drift: {surface!r}")
            explicit_used.add(surface)
    if explicit_used != set(EXPLICIT_LOCALIZED):
        raise ValueError("explicit transition annotation set changed")
    actual_counts = {
        "entries": len(entries),
        "existing_localized_gloss": sum(
            row["gloss_mode"] == "existing_localized_csv_or_word_anno"
            for row in entries
        ),
        "reviewed_exact_localized_annotation": sum(
            row["gloss_mode"] == "reviewed_exact_localized_annotation"
            for row in entries
        ),
        "html_intersection_surfaces": sum(
            bool(row["html_intersection"]["annotated_token_count"])
            for row in entries
        ),
    }
    if actual_counts != EXPECTED_COUNTS or payload.get("counts") != actual_counts:
        raise ValueError("transition app-review counts changed")
    return actual_counts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write-from-audit", type=Path)
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.write_from_audit:
        payload = build(args.write_from_audit.resolve())
        validate(payload)
        atomic_json_dump(args.manifest, payload, indent=1)
        label = "write"
    else:
        payload = load_json(args.manifest)
        validate(payload)
        label = "check"
    print(json.dumps({
        "manifest": str(args.manifest.resolve()),
        "mode": label,
        "counts": payload["counts"],
        "entries_sha256": payload["entries_sha256"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
