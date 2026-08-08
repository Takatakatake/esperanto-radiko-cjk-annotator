# -*- coding: utf-8 -*-
"""Build/check the gloss-independent three-language word_anno boundary pin."""
import argparse
import hashlib
import json
from pathlib import Path

from atomic_json import atomic_json_dump
from gen_replacement import word_anno_boundary_signature


HERE = Path(__file__).resolve().parent
DEFAULT_MANIFEST = HERE / "_word_anno_boundary_scope_manifest.json"
LANGUAGES = ("ja", "zh", "ko")


def build(maps=None):
    if maps is None:
        maps = {
            language: json.loads(
                (HERE / "out" / f"word_anno_{language}.json").read_text(
                    encoding="utf-8"
                )
            )
            for language in LANGUAGES
        }
    if set(maps) != set(LANGUAGES):
        raise ValueError("word_anno candidate must contain exactly ja/zh/ko")
    key_union = set().union(*(set(mapping) for mapping in maps.values()))
    authority = {}
    for key in sorted(key_union):
        observed = {
            language: word_anno_boundary_signature(key, maps[language][key])
            for language in LANGUAGES if key in maps[language]
        }
        if len(set(observed.values())) != 1:
            raise ValueError(
                f"word_anno multilingual boundary conflict for {key!r}: {observed!r}"
            )
        authority[key] = next(iter(observed.values()))
    serialized = json.dumps(
        [[key, list(authority[key])] for key in sorted(authority)],
        ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    return {
        "schema_version": 1,
        "languages": list(LANGUAGES),
        "expected_key_counts": {
        language: len(maps[language]) for language in LANGUAGES
        },
        "authority_keys": len(authority),
        "authority_sha256": hashlib.sha256(serialized).hexdigest().upper(),
        "expected_missing_by_language": {
            language: sorted(key_union - set(maps[language]))
            for language in LANGUAGES
        },
        "note": (
            "Boundary keys/pieces are shared authority; gloss values remain "
            "language-local and are intentionally not hashed here."
        ),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    payload = build()
    if args.write:
        atomic_json_dump(args.manifest, payload, indent=1)
        label = "write"
    else:
        expected = json.loads(args.manifest.read_text(encoding="utf-8"))
        if payload != expected:
            raise SystemExit("word_anno boundary manifest drift")
        label = "check"
    print(json.dumps({
        "manifest": str(args.manifest.resolve()),
        "mode": label,
        "expected_key_counts": payload["expected_key_counts"],
        "authority_keys": payload["authority_keys"],
        "authority_sha256": payload["authority_sha256"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
