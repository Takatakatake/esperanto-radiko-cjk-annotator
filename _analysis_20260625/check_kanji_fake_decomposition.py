# -*- coding: utf-8 -*-
"""Fail-closed deployed gate for reviewed Kanji-track fake decomposition.

Ruby annotations deliberately stay coarse, while the Kanji track may use the
deep/fake pieces listed by ``gold_revert_roots.json``.  For every such root
that has a pinned ``word_kanji`` entry, this gate requires all three deployed
Kanji JSONs to preserve both its Esperanto piece sequence and its assigned
Kanji text.  The exact unevaluable set is pinned so missing source coverage can
never make the gate pass vacuously.
"""
import hashlib
import json
from pathlib import Path
import re
import sys


# Windows' inherited cp932 console encoding cannot represent every reviewed
# annotation glyph (for example U+1D3E).  Configure both diagnostic streams
# before loading any manifests so a failing gate can report every mismatch.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="backslashreplace")


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "out"
MANIFEST_PATH = HERE / "_kanji_fake_decomposition_scope_manifest.json"
FF33_TRANSITION_PATH = HERE / "_fake_coarse_ff33_transition_review.json"
FINAL_5E_TRANSITION_PATH = HERE / "_fake_coarse_5e_transition_review.json"
ATOMIC_FAMILY_PATH = HERE / "localized_atomic_root_families.json"
KANJI_JSON = "置換リスト_漢字.json"
RUBY = re.compile(
    r'<ruby>([^<]+)<rt\b[^>]*>((?:[^<]|<br\s*/?>)*)</rt></ruby>',
    re.IGNORECASE,
)
BR = re.compile(r"<br\s*/?>", re.IGNORECASE)
CJK = re.compile(r"[⺀-鿿豈-﫿]")


def compact_sha(payload):
    raw = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


def expected_signature(pairs):
    spans = []
    literal = ""
    for piece, kanji in pairs:
        if kanji != piece and CJK.search(kanji):
            if literal:
                spans.append(("L", literal))
                literal = ""
            spans.append(("R", piece, kanji))
        else:
            literal += piece
    if literal:
        spans.append(("L", literal))
    return tuple(spans)


def deployed_signature(rendered):
    spans = []
    position = 0
    for match in RUBY.finditer(rendered):
        literal = re.sub(r"<[^>]+>", "", rendered[position:match.start()])
        if literal:
            spans.append(("L", literal))
        kanji = BR.sub("", match.group(1))
        piece = re.sub(r"\s+", "", BR.sub("", match.group(2)))
        spans.append(("R", piece, kanji))
        position = match.end()
    literal = re.sub(r"<[^>]+>", "", rendered[position:])
    if literal:
        spans.append(("L", literal))
    return tuple(spans)


def global_exact_rules(path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    rules = next(
        value for key, value in payload.items()
        if "replacements_final_list" in key
    )
    exact = {}
    for old, new, _placeholder in rules:
        surface = old.strip(" ")
        exact.setdefault(surface, new.strip(" "))
    return exact


def main():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise SystemExit("unsupported Kanji fake-decomposition manifest schema")
    atomic_policy = manifest.get("localized_atomic_policy", {})
    if (
        compact_sha(atomic_policy)
        != manifest.get("localized_atomic_policy_sha256")
        or manifest.get("localized_atomic_policy_sha256")
        != "A0E90778850C4A9CA46039867A6D464BFD62E33F212413A8A64B9837B690A8C7"
    ):
        raise SystemExit("localized atomic-root Kanji policy drift")
    atomic_family_raw = ATOMIC_FAMILY_PATH.read_bytes()
    if (
        hashlib.sha256(atomic_family_raw).hexdigest().upper()
        != atomic_policy.get("family_manifest_sha256")
        or atomic_policy.get("learner_sha256")
        != "1435F5B1CD1B0BB8224521A8262E3CA740B07B7523E805545A4E3CA7447A286C"
    ):
        raise SystemExit("localized atomic-root Kanji source identity drift")
    atomic_families = json.loads(atomic_family_raw.decode("utf-8"))["families"]
    reviewed_authority = {
        (family["root"], row["learner_line"], row["surface"])
        for family in atomic_families
        for row in family["authority"]
    }
    atomic_probes = atomic_policy.get("probes", [])
    probe_authority = {
        (row.get("family_root"), row.get("learner_line"), row.get("surface"))
        for row in atomic_probes
    }
    if (
        len(atomic_probes) != 4
        or probe_authority != reviewed_authority
        or any(
            not row.get("learner_decomposition")
            or row["learner_decomposition"].replace("/", "")
            != row.get("surface")
            or not row.get("kanji_signature")
            for row in atomic_probes
        )
    ):
        raise SystemExit("localized atomic-root Kanji probe coverage drift")
    final_5e_policy = manifest.get("final_5e_policy", {})
    if (
        compact_sha(final_5e_policy)
        != manifest.get("final_5e_policy_sha256")
        or manifest.get("final_5e_policy_sha256")
        != "C21E7FA515401C1D2EDDF346B9952A1691195A242E65D336BFD8784CE977C067"
    ):
        raise SystemExit("final-5E promil Kanji policy drift")
    final_5e_transition = json.loads(
        FINAL_5E_TRANSITION_PATH.read_text(encoding="utf-8")
    )
    final_5e_entries = final_5e_transition.get("entries", [])
    if (
        final_5e_transition.get("entries_sha256")
        != final_5e_policy.get("transition_entries_sha256")
        or len(final_5e_entries) != 1
        or final_5e_entries[0].get("learner_line")
        != final_5e_policy.get("learner_line")
        or final_5e_entries[0].get("target")
        != final_5e_policy.get("ruby_decomposition")
        or final_5e_entries[0].get("learner_decomposition")
        != final_5e_policy.get("kanji_decomposition")
        or len(final_5e_policy.get("probes", [])) != 7
    ):
        raise SystemExit("final-5E promil transition/probe authority drift")
    ff33_policy = manifest.get("ff33_policy", {})
    if (
        compact_sha(ff33_policy) != manifest.get("ff33_policy_sha256")
        or manifest.get("ff33_policy_sha256")
        != "0CB1EF358C9FEB36AD1E6FAFF915FB478735C40CA4C498594A660DADAB8E89B1"
    ):
        raise SystemExit("FF33 Kanji literal/deep-probe policy drift")
    ff33_transition = json.loads(
        FF33_TRANSITION_PATH.read_text(encoding="utf-8")
    )
    ff33_entries = ff33_transition.get("entries", [])
    tomisto_policy = ff33_policy.get("tomisto", {})
    if (
        ff33_transition.get("entries_sha256")
        != "3296A91605BCDD1E946966B72AEAC9855F3488347CA6A12913C679F86430ED31"
        or len(ff33_entries) != 1
        or ff33_entries[0].get("learner_line")
        != tomisto_policy.get("learner_line")
        or ff33_entries[0].get("learner_decomposition")
        != tomisto_policy.get("learner_decomposition")
        or ff33_entries[0].get("coarse_decomposition")
        != tomisto_policy.get("annotation_decomposition")
        or tomisto_policy.get("decision")
        != "reviewed_literal_fallback_no_proper_name_kanji_authority"
    ):
        raise SystemExit("FF33 Tomisto learner/annotation authority drift")
    deep_probe = ff33_policy.get("natria_klorido", {})
    if (
        deep_probe.get("learner_line") != 26746
        or deep_probe.get("decomposition") != "natri/a klor/id/o"
        or len(deep_probe.get("tokens", [])) != 2
    ):
        raise SystemExit("FF33 natria-klorido deep probe drift")
    roots = sorted(
        set(json.loads((OUT / "gold_revert_roots.json").read_text(encoding="utf-8")))
        | {"esperant"}
    )
    if (
        len(roots) != manifest.get("decompose_roots")
        or compact_sha(roots) != manifest.get("decompose_roots_sha256")
    ):
        raise SystemExit("Kanji fake-decomposition root scope drift")

    word_kanji = json.loads((OUT / "word_kanji.json").read_text(encoding="utf-8"))
    if word_kanji.get(final_5e_policy["word_kanji_key"]) != final_5e_policy[
        "word_kanji_pairs"
    ]:
        raise SystemExit("final-5E pro/mil word_kanji overlay drift")
    by_surface = {}
    for key, pairs in word_kanji.items():
        surface = key.replace("/", "")
        if surface not in roots:
            continue
        if surface in by_surface:
            raise SystemExit(f"duplicate word_kanji normalized surface: {surface!r}")
        by_surface[surface] = (key, pairs)
    covered = {
        root: by_surface[root]
        for root in roots
        if root in by_surface
    }
    missing = sorted(set(roots) - set(covered))
    covered_payload = [
        [root, key, pairs]
        for root, (key, pairs) in covered.items()
    ]
    if missing != manifest.get("expected_missing_word_kanji"):
        raise SystemExit(
            "Kanji fake-decomposition word_kanji coverage drift: "
            f"expected_missing={manifest.get('expected_missing_word_kanji')!r}, "
            f"actual_missing={missing!r}"
        )
    if (
        len(covered) != manifest.get("evaluable_word_kanji")
        or compact_sha(covered_payload)
        != manifest.get("evaluable_word_kanji_sha256")
    ):
        raise SystemExit("Kanji fake-decomposition word_kanji authority drift")

    fallback_rows = manifest.get("fallback_reviewed", [])
    if (
        len(fallback_rows) != manifest.get("fallback_reviewed_count")
        or compact_sha(fallback_rows) != manifest.get("fallback_reviewed_sha256")
    ):
        raise SystemExit("Kanji fake-decomposition fallback authority drift")
    fallback = {}
    for row in fallback_rows:
        root = row.get("root")
        surface = row.get("surface")
        signature = row.get("signature")
        if (
            root in fallback
            or root not in missing
            or not isinstance(surface, str)
            or not isinstance(signature, list)
            or not signature
        ):
            raise SystemExit(f"invalid Kanji fallback row: {row!r}")
        fallback[root] = (surface, tuple(tuple(span) for span in signature))
    if set(fallback) != set(missing):
        raise SystemExit(
            "Kanji fallback roots do not exactly cover missing word_kanji scope"
        )

    total_mismatches = 0
    for language in ("JA", "ZH", "KO"):
        exact = global_exact_rules(
            ROOT / f"Esperanto-Kanji-Ruby-{language}" / "app_data" / KANJI_JSON
        )
        mismatches = []
        for surface, (_key, pairs) in covered.items():
            rendered = exact.get(surface)
            expected = expected_signature(pairs)
            actual = deployed_signature(rendered) if rendered is not None else None
            if actual != expected:
                mismatches.append((surface, expected, actual))
        for root, (surface, expected) in fallback.items():
            rendered = exact.get(surface)
            actual = deployed_signature(rendered) if rendered is not None else None
            if actual != expected:
                mismatches.append((root, surface, expected, actual))
        for probe in atomic_probes:
            expected = tuple(
                tuple(span) for span in probe["kanji_signature"]
            )
            rendered = exact.get(probe["surface"])
            actual = deployed_signature(rendered) if rendered is not None else None
            if actual != expected:
                mismatches.append((
                    "localized_atomic_deep_kanji",
                    probe["surface"], probe["learner_decomposition"],
                    expected, actual,
                ))
        for probe in final_5e_policy["probes"]:
            expected = tuple(tuple(span) for span in probe["signature"])
            rendered = exact.get(probe["surface"])
            actual = deployed_signature(rendered) if rendered is not None else None
            if actual != expected:
                mismatches.append((
                    "final_5e_promil_deep_kanji", probe["surface"],
                    expected, actual,
                ))
        tomisto_surface = tomisto_policy["kanji_surface"]
        tomisto_expected = tuple(
            tuple(span) for span in tomisto_policy["kanji_signature"]
        )
        tomisto_rendered = exact.get(tomisto_surface)
        tomisto_actual = (
            deployed_signature(tomisto_rendered)
            if tomisto_rendered is not None else None
        )
        if tomisto_actual != tomisto_expected:
            mismatches.append((
                "ff33_literal_fallback", tomisto_surface,
                tomisto_expected, tomisto_actual,
            ))
        for token in deep_probe["tokens"]:
            expected = tuple(tuple(span) for span in token["signature"])
            rendered = exact.get(token["surface"])
            actual = deployed_signature(rendered) if rendered is not None else None
            if actual != expected:
                mismatches.append((
                    "ff33_unmarked_deep_probe", token["surface"],
                    expected, actual,
                ))
        total_mismatches += len(mismatches)
        print(
            f"[{language}] evaluated={len(covered) + len(fallback)} "
            f"word_kanji={len(covered)} reviewed_fallback={len(fallback)} "
            f"localized_atomic_probes={len(atomic_probes)} "
            f"final_5e_probes={len(final_5e_policy['probes'])} "
            "ff33_policy_probes=3 "
            f"mismatches={len(mismatches)}"
        )
        for mismatch in mismatches:
            print(f"  {mismatch!r}")
    if total_mismatches:
        raise SystemExit(1)
    print(
        "Kanji fake-decomposition gate PASS: "
        f"languages=3 evaluated_each={len(covered) + len(fallback)} "
        f"word_kanji={len(covered)} reviewed_fallback={len(fallback)} "
        f"localized_atomic_probes={len(atomic_probes)} "
        f"final_5e_probes={len(final_5e_policy['probes'])} "
        "ff33_policy_probes=3 "
        "mismatches=0"
    )


if __name__ == "__main__":
    main()
