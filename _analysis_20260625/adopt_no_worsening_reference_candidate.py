# -*- coding: utf-8 -*-
"""Adopt a reviewed B090 references-only candidate and rebind strict fixes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

from atomic_json import atomic_json_dump
import no_worsening_audit as audit
from gold_snapshot import consistent_snapshot


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCOPE_PATH = HERE / "_no_worsening_scope_manifest.json"
CONFLICT_PATH = HERE / "_no_worsening_reference_conflicts.json"
STRICT_PATH = HERE / "_strict_gold_reference_fixes.json"


def typed_signature(entry):
    pieces = [piece for piece in entry["target"].split("/") if piece]
    roles = entry["typed_roles"]
    return audit.signature_from_typed_parts([
        (piece, role == "R") for piece, role in zip(pieces, roles)
    ])


def atomic_compact_entries_dump(path, payload):
    """Write review manifests with one compact object per review entry.

    The strict-fix ledger is intentionally human-reviewable in diffs.  The
    generic pretty-printer expands every six-field entry to several lines and
    obscures the small semantic change that this adoption performs.
    """
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise ValueError("compact review manifest must contain an entries list")
    lines = ["{"]
    for key, value in payload.items():
        if key == "entries":
            continue
        lines.append(
            f" {json.dumps(key, ensure_ascii=False)}: "
            f"{json.dumps(value, ensure_ascii=False, separators=(',', ':'))},"
        )
    lines.append(' "entries": [')
    for index, entry in enumerate(entries):
        comma = "," if index + 1 < len(entries) else ""
        lines.append(
            "  "
            + json.dumps(entry, ensure_ascii=False, separators=(",", ":"))
            + comma
        )
    lines.extend([" ]", "}", ""])
    raw = "\n".join(lines).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="wb", dir=path.parent, prefix=f".{path.name}.", delete=False,
    )
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def preserve_tracked_entry_order(entries):
    """Keep the reviewed ledger's established order and append new entries."""
    relative = STRICT_PATH.relative_to(ROOT).as_posix()
    completed = subprocess.run(
        ["git", "show", f"HEAD:{relative}"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if completed.returncode:
        return entries
    tracked = json.loads(completed.stdout.decode("utf-8"))["entries"]
    tracked_rank = {entry["w"]: index for index, entry in enumerate(tracked)}
    current_rank = {entry["w"]: index for index, entry in enumerate(entries)}
    fallback = len(tracked_rank)
    return sorted(
        entries,
        key=lambda entry: (
            tracked_rank.get(entry["w"], fallback),
            current_rank[entry["w"]],
        ),
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--expected-gold-sha256", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
    projection = candidate["projection"]
    scope_candidate = candidate["scope_manifest_candidate"]
    conflicts = candidate["conflicts"]
    if (
        projection.get("schema_version") != audit.REFERENCE_SCHEMA_VERSION
        or projection.get("gold", {}).get("sha256")
        != args.expected_gold_sha256.upper()
        or scope_candidate.get("expected") != projection
        or scope_candidate.get("projection_sha256")
        != audit.stable_json_sha256(projection)
        or projection.get("reference_conflict_count") != len(conflicts)
        or projection.get("reference_conflicts_sha256")
        != audit.stable_json_sha256(conflicts)
    ):
        raise ValueError("references-only candidate identity is inconsistent")

    old_review = json.loads(CONFLICT_PATH.read_text(encoding="utf-8"))
    old_by_surface = {entry["surface"]: entry for entry in old_review["entries"]}
    conflict_by_surface = {entry["surface"]: entry for entry in conflicts}
    added_conflicts = set(conflict_by_surface) - set(old_by_surface)
    if added_conflicts not in (set(), {"resumi"}) or "resumi" not in conflict_by_surface:
        raise ValueError(
            "B090 candidate must contain exactly the reviewed resumi addition"
        )
    reviewed_entries = []
    for conflict in conflicts:
        surface = conflict["surface"]
        if surface != "resumi":
            old = old_by_surface.get(surface)
            if old is None or old.get("options") != conflict["options"]:
                raise ValueError(f"existing reference conflict drift: {surface!r}")
            reviewed = dict(old)
            reviewed["options"] = conflict["options"]
            reviewed_entries.append(reviewed)
            continue
        expected_options = {option["expected"] for option in conflict["options"]}
        if expected_options != {"resum/i", "re/sum/i"}:
            raise ValueError(f"unexpected resumi options: {expected_options!r}")
        reviewed_entries.append({
            "surface": "resumi",
            "options": conflict["options"],
            "allowed_signatures": [
                option["signature"] for option in conflict["options"]
            ],
            "category": "lexical_homograph_context",
            "reason": (
                "B090 line 33885 is the summary verb resum/i (also the Kyoto "
                "HTML reading), while line 33886 is the distinct productive "
                "re/sum/i sense 'sum again'. A context-free app may expose "
                "either reviewed signature; deployed ordinary resumi remains resum/i."
            ),
        })
    reviewed_entries.sort(key=lambda entry: entry["surface"])
    conflict_manifest = {
        "manifest_schema_version": 1,
        "reference_schema_version": audit.REFERENCE_SCHEMA_VERSION,
        "raw_conflicts_sha256": audit.stable_json_sha256(conflicts),
        "entries": reviewed_entries,
    }

    # Rebuild the raw reference union independently, then prove every strict
    # exact setting is still a real B090/corpus reference before rebinding its
    # metadata to the new projection.
    gold_raw, gold_identity = consistent_snapshot(args.gold.resolve())
    cases = {}
    scope = {
        "corpus": audit.corpus_cases(cases, args.corpus.resolve()),
        "corpus_repository": audit.git_repo_state(args.corpus.resolve()),
        "place_manifest": audit.place_cases(cases),
        "gold": audit.gold_cases(
            cases, args.gold.resolve(), gold_raw, gold_identity,
            args.expected_gold_sha256,
        ),
    }
    surfaces = sorted({case["surface"] for case in cases.values()})
    rebuilt_conflicts = audit.reference_conflicts(cases)
    rebuilt_projection = audit.scope_projection(
        scope, cases, surfaces, rebuilt_conflicts,
    )
    if rebuilt_projection != projection or rebuilt_conflicts != conflicts:
        raise ValueError("candidate does not match independently rebuilt references")

    strict = json.loads(STRICT_PATH.read_text(encoding="utf-8"))
    app_review = json.loads(
        (HERE / "_fake_coarse_transition_app_review.json").read_text(
            encoding="utf-8"
        )
    )
    app_by_surface = {
        entry["surface"]: entry for entry in app_review["entries"]
    }
    strict_by_surface = {entry["w"]: entry for entry in strict["entries"]}
    for surface, reviewed in app_by_surface.items():
        strict_entry = strict_by_surface.get(surface)
        if strict_entry is None:
            strict_entry = {
                "w": surface,
                "exact_only": True,
                "boundary_only": True,
                "case_sensitive": True,
            }
            strict["entries"].append(strict_entry)
            strict_by_surface[surface] = strict_entry
        strict_entry["target"] = reviewed["target"]
        strict_entry["typed_roles"] = reviewed["typed_roles"]
        strict_entry["exact_only"] = True
        strict_entry["boundary_only"] = True
        strict_entry["case_sensitive"] = True
    strict["entries"] = preserve_tracked_entry_order(strict["entries"])
    available = {
        (case["surface"], case["signature"]) for case in cases.values()
    }
    for entry in strict["entries"]:
        signature = typed_signature(entry)
        if signature[0] != entry["w"] or (entry["w"], signature) not in available:
            raise ValueError(
                f"strict exact fix is absent from B090 reference union: {entry!r}"
            )
    compact = json.dumps(
        strict["entries"], ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    strict.update({
        "reference_schema_version": audit.REFERENCE_SCHEMA_VERSION,
        "gold_sha256": projection["gold"]["sha256"],
        "reference_sha256": projection["reference_sha256"],
        "expected_entries": len(strict["entries"]),
        "entries_sha256": hashlib.sha256(compact).hexdigest().upper(),
    })
    if args.write:
        atomic_json_dump(SCOPE_PATH, scope_candidate, indent=1)
        atomic_json_dump(CONFLICT_PATH, conflict_manifest, indent=1)
        atomic_compact_entries_dump(STRICT_PATH, strict)
    print(json.dumps({
        "mode": "write" if args.write else "check",
        "projection_sha256": scope_candidate["projection_sha256"],
        "gold_sha256": projection["gold"]["sha256"],
        "case_count": projection["case_count"],
        "surface_count": projection["surface_count"],
        "conflicts": len(conflicts),
        "strict_entries": len(strict["entries"]),
        "strict_entries_sha256": strict["entries_sha256"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
