# -*- coding: utf-8 -*-
"""Isolated, snapshot-explicit three-language runtime audit for the full gold master.

Unlike ``audit_master_3lang_fast.py``, this audit has no live/default gold path,
keeps spaces, punctuation and hyphens, accounts for every input line, loads the
three runtimes under distinct module names, and mirrors the effective app
overlay/autofix path.  It never regenerates app data.
"""
from __future__ import annotations

import argparse
import collections
import gc
import hashlib
import heapq
import html as htmllib
import json
from pathlib import Path
import re
import subprocess
import sys
import time


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from atomic_json import atomic_json_dump
import build_phase532_authority_carry_forward as phase532_carry_builder
import build_phase532_ruby_policy_review as phase532_builder
import build_phase558_ruby_overlay_review as phase558_builder
import no_worsening_audit as audit
import phase532_authority_carry_forward as phase532_carry
import phase532_ruby_policy as phase532_policy
import phase532_runtime_signature_gate as phase532_runtime_gate
import phase558_ruby_overlay as phase558_policy
import phase558_ruby_overlay_activation as phase558_activation
import phase558_ruby_overlay_runtime_gate as phase558_runtime_gate


LANGUAGES = ("JA", "ZH", "KO")
RUBY_PAYLOAD_NAME = "置換リスト_ルビ.json"
DEFAULT_REPORT = HERE / "out" / "_audit_master_3lang_current_gold.json"
PLACEHOLDER_RE = re.compile(r"\$(?:[A-Za-z]+)?\d+\$")
ESP_LETTERS = "A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ"
ESP_LETTER_RE = re.compile(rf"[{ESP_LETTERS}]")
TOKEN_RE = re.compile(
    rf"[{ESP_LETTERS}]+(?:[-'’][{ESP_LETTERS}]+)*",
)
ALPHA_APOSTROPHE_RE = re.compile(
    rf"[{ESP_LETTERS}]+(?:['’][{ESP_LETTERS}]+)*",
)
FAST_RE = re.compile(rf"[{ESP_LETTERS}]{{3,30}}")
RUBY_DETAIL_RE = re.compile(
    r"<ruby\b[^>]*>\s*(?P<rb>.*?)\s*"
    r"<rt\b(?P<attrs>[^>]*)>(?P<rt>.*?)</rt\s*>\s*</ruby\s*>",
    re.IGNORECASE | re.DOTALL,
)
BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")
CLASS_RE = re.compile(r"\bclass\s*=\s*(['\"])(.*?)\1", re.IGNORECASE | re.DOTALL)
NOTE_LIKE_RE = re.compile(
    r"[\[\]［］【】{}（）()]|(?:^|\s)(?:abbr\.?|prefix|suffix)(?:\s|$)|"
    r"(?:略|接頭|接尾|語尾|文法|地名|人名|固有|学名|化学|音楽|品詞|"
    r"简称|缩写|前缀|后缀|语法|地名|人名|专名|学名|化学|"
    r"약어|접두|접미|문법|지명|인명|고유|학명|화학)",
    re.IGNORECASE,
)
CLASS_SCALE = {
    "XXXS_S": 0.3,
    "XXS_S": 0.3,
    "XS_S": 0.3,
    "S_S": 0.4,
    "M_M": 0.5,
    "L_L": 0.6,
    "XL_L": 0.7,
    "XXL_L": 0.8,
}
CSS_SCALE_RE = re.compile(
    r"rt\.([A-Z_]+)\s*\{[^}]*?--ruby-font-size\s*:\s*([0-9.]+)em",
    re.DOTALL,
)
TOP_LIMIT = 120
LEGACY_HAT_MAP = {
    "c^": "ĉ", "g^": "ĝ", "h^": "ĥ", "j^": "ĵ", "s^": "ŝ", "u^": "ŭ",
    "C^": "Ĉ", "G^": "Ĝ", "H^": "Ĥ", "J^": "Ĵ", "S^": "Ŝ", "U^": "Ŭ",
}
DUPLICATE_METADATA_PREFIX = "##重複語"
FAKE_COARSE_MANIFEST = HERE / "_fake_coarse_reference_manifest.json"
PHASE513_FAKE_COARSE_EVIDENCE = (
    HERE / "_phase513_fake_coarse_reference_manifest.json"
)
FAKE_TRANSITION_MANIFEST = HERE / "_fake_coarse_transition_review.json"
FAKE_FF33_TRANSITION_MANIFEST = (
    HERE / "_fake_coarse_ff33_transition_review.json"
)
FAKE_5E_TRANSITION_MANIFEST = (
    HERE / "_fake_coarse_5e_transition_review.json"
)
FAKE_PHASE511_TRANSITION_MANIFEST = (
    HERE / "_fake_coarse_phase511_transition_review.json"
)
PHASE558_FAKE_MANIFEST_SHA256 = (
    "6C72C51EF8DB434E62D614D58CB5A9DB0D55352A642576BEC30B523C4F420D15"
)
PHASE558_TRANSITION_DISPOSITIONS_SHA256 = (
    "35F1531BAC29B4842CED0F1F7E6FC1F5D588349FBF6A51D3BDCBA4EA533AF9A2"
)
ATOMIC_HYPHEN_REVIEW, _ATOMIC_HYPHEN_IDENTITY = audit.load_atomic_hyphen_review()


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def deployed_css_class_scale(app_dir: Path) -> dict[str, float]:
    runtime_path = app_dir / "esp_text_replacement_module.py"
    observed = {
        name: float(value)
        for name, value in CSS_SCALE_RE.findall(
            runtime_path.read_text(encoding="utf-8")
        )
    }
    if observed != CLASS_SCALE:
        raise ValueError(
            f"deployed Ruby CSS scale mapping drift: {app_dir.name}: "
            f"{observed!r}"
        )
    return observed


def git_text(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def tracked_status() -> list[str]:
    rows = []
    for args in (("diff", "--name-only"), ("diff", "--cached", "--name-only")):
        value = git_text(*args)
        rows.extend(row for row in value.splitlines() if row)
    return sorted(set(rows))


def html_text(fragment: str, preserve_breaks: bool = False) -> str:
    if preserve_breaks:
        fragment = BR_RE.sub("\n", fragment)
    else:
        fragment = BR_RE.sub("", fragment)
    return htmllib.unescape(TAG_RE.sub("", fragment))


def ratio_bin(value: float | None) -> str:
    if value is None:
        return "unmeasurable"
    if value <= 2:
        return "le_2"
    if value <= 2.5:
        return "gt_2_le_2_5"
    if value <= 3:
        return "gt_2_5_le_3"
    return "gt_3"


def cumulative_bins(counter: collections.Counter) -> dict:
    return {
        "le_2": counter["le_2"],
        "gt_2": (
            counter["gt_2_le_2_5"]
            + counter["gt_2_5_le_3"]
            + counter["gt_3"]
        ),
        "gt_2_5": counter["gt_2_5_le_3"] + counter["gt_3"],
        "gt_3": counter["gt_3"],
        "unmeasurable": counter["unmeasurable"],
        "exclusive": dict(counter),
    }


def push_top(heap: list, score: float, serial: int, payload: dict) -> None:
    item = (float(score), serial, payload)
    if len(heap) < TOP_LIMIT:
        heapq.heappush(heap, item)
    elif item[:2] > heap[0][:2]:
        heapq.heapreplace(heap, item)


def top_payload(heap: list) -> list[dict]:
    return [item[2] for item in sorted(heap, reverse=True)]


def structural_payload(key) -> dict:
    visible, spans, tokens = key
    return {
        "visible": visible,
        "line_signature": audit.display_typed_parts(list(spans)),
        "tokens": [
            {
                "token": token,
                "signature": audit.display_typed_parts(list(token_spans)),
            }
            for token, token_spans in tokens
        ],
    }


def expected_expression_structure(decomposition: str):
    """Project a slash decomposition to the runtime-observable R/L structure.

    Spaces delimit separate words even when no slash surrounds them.  Digits
    and punctuation remain literal outside Ruby; lexical letter runs retain
    the Ruby/bare role assigned by the ordinary morphology projection.
    """
    parts = []
    for chunk in re.split(r"(\s+)", decomposition):
        if not chunk:
            continue
        if chunk.isspace():
            parts.append((chunk, False))
            continue
        word_surface = audit.canonical(chunk.replace("/", ""))
        atomic_pieces = audit.reviewed_atomic_hyphen_pieces(
            word_surface, chunk, ATOMIC_HYPHEN_REVIEW,
        )
        for piece, is_ruby in audit.expected_typed_parts(chunk, atomic_pieces):
            if not is_ruby or piece in atomic_pieces:
                parts.append((piece, is_ruby))
                continue
            position = 0
            for match in ALPHA_APOSTROPHE_RE.finditer(piece):
                if match.start() > position:
                    parts.append((piece[position:match.start()], False))
                parts.append((match.group(0), True))
                position = match.end()
            if position < len(piece):
                parts.append((piece[position:], False))
    visible, spans = audit.signature_from_typed_parts(parts)
    return visible, spans, token_projection(visible, spans)


def token_projection(visible: str, spans) -> tuple:
    located = []
    offset = 0
    for text, is_ruby in spans:
        located.append((offset, offset + len(text), text, bool(is_ruby)))
        offset += len(text)
    if offset != len(visible):
        raise ValueError("typed-span reconstruction length changed")
    tokens = []
    for match in TOKEN_RE.finditer(visible):
        parts = []
        for start, end, _text, is_ruby in located:
            left = max(start, match.start())
            right = min(end, match.end())
            if left >= right:
                continue
            piece = visible[left:right]
            if parts and not is_ruby and not parts[-1][1]:
                parts[-1] = (parts[-1][0] + piece, False)
            else:
                parts.append((piece, is_ruby))
        tokens.append((match.group(0), tuple(parts)))
    return tuple(tokens)


def legacy_fast_candidate(decomposition: str) -> str:
    """Reproduce audit_master_3lang_fast.py's exact pre-filter transform."""
    candidate = decomposition
    for original, converted in LEGACY_HAT_MAP.items():
        candidate = candidate.replace(original, converted)
    return candidate.replace("/", "").replace("-", "")


def fast_scope_class(decomposition: str) -> tuple[str, str | None]:
    candidate = legacy_fast_candidate(decomposition)
    if " " in candidate:
        return "excluded_space", None
    if "!" in candidate or "." in candidate:
        return "excluded_bang_or_dot", None
    if FAST_RE.fullmatch(candidate):
        return "included", candidate
    if re.fullmatch(rf"[{ESP_LETTERS}]+", candidate):
        if len(candidate) < 3:
            return "excluded_length_lt_3", None
        if len(candidate) > 30:
            return "excluded_length_gt_30", None
    return "excluded_non_fast_alphabet_or_punctuation", None


def surface_features(decomposition: str, surface: str) -> list[str]:
    features = []
    if " " in surface:
        features.append("contains_ascii_space")
    if any(character.isspace() for character in surface):
        features.append("contains_whitespace")
    if decomposition.startswith("-") or decomposition.endswith("-"):
        features.append("edge_hyphen_affix_entry")
    if any(character.isdigit() for character in surface):
        features.append("contains_digit")
    if "." in surface:
        features.append("contains_period")
    if "!" in surface:
        features.append("contains_exclamation")
    if "?" in surface:
        features.append("contains_question")
    if "…" in surface:
        features.append("contains_ellipsis")
    if re.search(rf"[^{ESP_LETTERS}'’\-\s]", surface):
        features.append("contains_non_esperanto_or_punctuation")
    token_count = len(TOKEN_RE.findall(surface))
    if token_count == 0:
        features.append("zero_esperanto_tokens")
    elif token_count > 1:
        features.append("multiple_esperanto_tokens")
    return features


def parse_gold(path: Path, expected_sha256: str):
    raw = path.read_bytes()
    digest = sha256_bytes(raw)
    if digest != expected_sha256.upper():
        raise ValueError(f"gold SHA256 changed: {digest} != {expected_sha256.upper()}")
    text = raw.decode("utf-8", errors="strict")
    records = []
    exclusions = collections.Counter()
    exclusion_rows = collections.defaultdict(list)
    feature_counts = collections.Counter()
    fast_counts = collections.Counter()
    for line_number, line in enumerate(text.splitlines(), 1):
        clean = line.lstrip("\ufeff")
        if not clean.strip():
            exclusions["blank"] += 1
            exclusion_rows["blank"].append(line_number)
            continue
        if clean.lstrip().startswith("#"):
            exclusions["comment"] += 1
            exclusion_rows["comment"].append(line_number)
            continue
        if ":" not in clean:
            exclusions["missing_colon"] += 1
            exclusion_rows["missing_colon"].append(line_number)
            continue
        decomposition = clean.split(":", 1)[0].strip()
        if not decomposition:
            exclusions["empty_decomposition"] += 1
            exclusion_rows["empty_decomposition"].append(line_number)
            continue
        surface = audit.canonical(decomposition.replace("/", ""))
        if not surface:
            exclusions["empty_surface"] += 1
            exclusion_rows["empty_surface"].append(line_number)
            continue
        features = surface_features(decomposition, surface)
        for feature in features:
            feature_counts[feature] += 1
        fast_class, fast_key = fast_scope_class(decomposition)
        fast_counts[fast_class] += 1
        records.append({
            "line_number": line_number,
            "decomposition": audit.canonical(decomposition),
            "surface": surface,
            "features": features,
            "fast_scope": fast_class,
            "fast_key": fast_key,
        })
    return raw, text, records, exclusions, exclusion_rows, feature_counts, fast_counts


def strip_duplicate_metadata(decomposition: str) -> tuple[str, bool]:
    cleaned = decomposition.lstrip("\ufeff").strip()
    if cleaned.startswith(DUPLICATE_METADATA_PREFIX):
        return cleaned[len(DUPLICATE_METADATA_PREFIX):], True
    return cleaned, False


def normalize_slash_decomposition(decomposition: str) -> str:
    return "/".join(
        audit.canonical(piece)
        for piece in decomposition.split("/") if audit.canonical(piece)
    )


def load_fake_coarse_authority(
    learner_raw: bytes, learner_text: str, academic_path: Path,
    expected_academic_sha256: str,
    candidate_manifest_path: Path | None = None,
    candidate_dispositions_path: Path | None = None,
    phase532_reference_review: dict | None = None,
):
    """Return every fake-marked line authority and its staged scope.

    Every line is sense-aligned by exact gloss equality after removing the
    learner marker suffix.  Single-word/evaluable rows use the committed
    academic/PEJVO review manifest; the remaining rows are retained as explicit
    multiword, numeric/punctuation, or metadata-prefix rows.
    """
    academic_raw = academic_path.read_bytes()
    academic_digest = sha256_bytes(academic_raw)
    if academic_digest != expected_academic_sha256.upper():
        raise ValueError(
            "academic SHA256 changed: "
            f"{academic_digest} != {expected_academic_sha256.upper()}"
        )
    academic_text = academic_raw.decode("utf-8", errors="strict")
    learner_lines = learner_text.splitlines()
    academic_lines = academic_text.splitlines()
    if len(learner_lines) != len(academic_lines):
        raise ValueError("learner/academic line counts differ")

    candidate_mode = candidate_manifest_path is not None
    phase532_enabled = phase532_reference_review is not None
    if candidate_dispositions_path is not None and not candidate_mode:
        raise ValueError(
            "candidate transition dispositions require an external manifest"
        )
    provenance_manifest_raw = PHASE513_FAKE_COARSE_EVIDENCE.read_bytes()
    provenance_manifest = json.loads(provenance_manifest_raw.decode("utf-8"))
    if provenance_manifest.get("schema_version") != 1:
        raise ValueError("unsupported provenance fake-coarse authority schema")
    manifest_path = (
        candidate_manifest_path.resolve()
        if candidate_mode else FAKE_COARSE_MANIFEST
    )
    manifest_raw = manifest_path.read_bytes()
    manifest = json.loads(manifest_raw.decode("utf-8"))
    if manifest.get("schema_version") != 1:
        raise ValueError("unsupported fake-coarse authority schema")
    if phase532_enabled:
        if (
            phase532_reference_review.get("manifest_path")
            != manifest_path.resolve()
            or phase532_reference_review.get("manifest_sha256")
            != sha256_bytes(manifest_raw)
            or phase532_reference_review.get("identity")
            != phase532_policy.review_identity()
        ):
            raise ValueError("Phase 532 full-audit reference identity changed")
    elif (
        sha256_bytes(manifest_raw)
        == phase532_policy.CANDIDATE_MANIFEST_SHA256
    ):
        raise ValueError(
            "Phase 532 manifest requires its exact Ruby policy context"
        )
    serialized_entries = json.dumps(
        manifest.get("entries", []), ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    if sha256_bytes(serialized_entries) != manifest.get("entries_sha256"):
        raise ValueError("fake-coarse authority entry fingerprint mismatch")
    source_identity = manifest.get("sources", {})
    provenance_source_identity = provenance_manifest.get("sources", {})
    for label, raw, lines in (
        ("learner", learner_raw, learner_lines),
        ("academic", academic_raw, academic_lines),
    ):
        expected = source_identity.get(label, {})
        actual = {
            "bytes": len(raw), "sha256": sha256_bytes(raw), "lines": len(lines),
        }
        if any(expected.get(key) != value for key, value in actual.items()):
            raise ValueError(f"fake-coarse {label} source identity changed")
    entries_by_line = {}
    for entry in manifest["entries"]:
        line = entry.get("learner_line")
        if not isinstance(line, int) or line in entries_by_line:
            raise ValueError(f"invalid/reused fake-coarse line: {line!r}")
        entries_by_line[line] = entry

    transition_raw = FAKE_TRANSITION_MANIFEST.read_bytes()
    transition = json.loads(transition_raw.decode("utf-8"))
    expected_transition_counts = {
        "entries": 136,
        "unique_surfaces": 135,
        "duplicate_surface_rows": 1,
        "categories": {
            "reviewed_c679_to_b090_fake_transition": 133,
            "reviewed_b090_marker_only_delta": 3,
        },
        "authority_adjustments": 2,
    }
    if transition.get("schema_version") != 1:
        raise ValueError("unsupported fake-coarse transition schema")
    serialized_transition = json.dumps(
        transition.get("entries", []), ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    if (
        sha256_bytes(serialized_transition) != transition.get("entries_sha256")
        or transition.get("entries_sha256")
        != "B8B1036BF0164960429B2FD079EBF62A71FA02425FC0A4D8EB7B84F127BCCF01"
        or sha256_bytes(transition_raw)
        != "D20633B41904776B5A6954F6EAC8F72335DCE3FEE51213AA9245A360E3027E34"
        or transition.get("counts") != expected_transition_counts
        or len(transition.get("entries", [])) != 136
    ):
        raise ValueError("fake-coarse transition entry fingerprint mismatch")
    transition_by_line = {}
    for entry in transition["entries"]:
        line = entry.get("learner_line")
        if not isinstance(line, int) or line in transition_by_line:
            raise ValueError(f"invalid/reused transition line: {line!r}")
        transition_by_line[line] = entry

    ff33_transition_raw = FAKE_FF33_TRANSITION_MANIFEST.read_bytes()
    ff33_transition = json.loads(ff33_transition_raw.decode("utf-8"))
    ff33_entries = ff33_transition.get("entries", [])
    serialized_ff33 = json.dumps(
        ff33_entries, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    expected_ff33_counts = {
        "entries": 1,
        "evaluable_entries": 1,
        "new_fake_marker_rows": 1,
    }
    if (
        ff33_transition.get("schema_version") != 1
        or sha256_bytes(serialized_ff33)
        != "3296A91605BCDD1E946966B72AEAC9855F3488347CA6A12913C679F86430ED31"
        or ff33_transition.get("entries_sha256")
        != "3296A91605BCDD1E946966B72AEAC9855F3488347CA6A12913C679F86430ED31"
        or ff33_transition.get("counts") != expected_ff33_counts
        or ff33_transition.get("source_fake_coarse_entries_sha256")
        != provenance_manifest.get("entries_sha256")
        or ff33_transition.get("sources", {}).get("learner")
        != provenance_source_identity.get("learner")
        or ff33_transition.get("sources", {}).get("academic")
        != provenance_source_identity.get("academic")
        or len(ff33_entries) != 1
    ):
        raise ValueError("FF33 fake-coarse transition entry fingerprint mismatch")
    ff33_transition_by_line = {}
    for entry in ff33_entries:
        line = entry.get("learner_line")
        if (
            line != 56273
            or line in transition_by_line
            or line in ff33_transition_by_line
        ):
            raise ValueError(f"invalid/reused FF33 transition line: {line!r}")
        ff33_transition_by_line[line] = entry
    final_5e_transition_raw = FAKE_5E_TRANSITION_MANIFEST.read_bytes()
    final_5e_transition = json.loads(final_5e_transition_raw.decode("utf-8"))
    final_5e_entries = final_5e_transition.get("entries", [])
    serialized_final_5e = json.dumps(
        final_5e_entries, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    expected_final_5e_hash = (
        "B0CF495ECDEA78DEA86AEB72CFF5252140C67D342947A391200CA9936BF41E1F"
    )
    expected_final_5e_counts = {
        "entries": 1,
        "evaluable_entries": 1,
        "new_fake_marker_rows": 1,
    }
    if (
        final_5e_transition.get("schema_version") != 1
        or sha256_bytes(serialized_final_5e) != expected_final_5e_hash
        or final_5e_transition.get("entries_sha256") != expected_final_5e_hash
        or final_5e_transition.get("counts") != expected_final_5e_counts
        or final_5e_transition.get("source_fake_coarse_entries_sha256")
        != provenance_manifest.get("entries_sha256")
        or final_5e_transition.get("sources", {}).get("learner")
        != provenance_source_identity.get("learner")
        or final_5e_transition.get("sources", {}).get("academic")
        != provenance_source_identity.get("academic")
        or len(final_5e_entries) != 1
    ):
        raise ValueError("5E fake-coarse transition entry fingerprint mismatch")
    final_5e_transition_by_line = {}
    for entry in final_5e_entries:
        line = entry.get("learner_line")
        if (
            line != 53890
            or line in transition_by_line
            or line in ff33_transition_by_line
            or line in final_5e_transition_by_line
        ):
            raise ValueError(f"invalid/reused 5E transition line: {line!r}")
        final_5e_transition_by_line[line] = entry

    phase511_transition_raw = FAKE_PHASE511_TRANSITION_MANIFEST.read_bytes()
    phase511_transition = json.loads(phase511_transition_raw.decode("utf-8"))
    phase511_entries = phase511_transition.get("entries", [])
    serialized_phase511 = json.dumps(
        phase511_entries, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    expected_phase511_hash = (
        "3F7DBBB34ECE9D3657444818F753755176C89E66307E4AE0E0297A59B8919BFF"
    )
    expected_phase511_counts = {
        "entries": 21,
        "historical_authority_supersessions": 1,
        "strict_authority_carry_forwards": 1,
        "strict_authority_supersessions": 2,
        "strict_authority_additions": 17,
        "reviewed_exact_localized_annotations": 19,
    }
    expected_phase511_supersedes = {
        "historical_manifest": {
            "sha256": (
                "D20633B41904776B5A6954F6EAC8F72335DCE3FEE51213AA9245A360E3027E34"
            ),
            "entries_sha256": (
                "B8B1036BF0164960429B2FD079EBF62A71FA02425FC0A4D8EB7B84F127BCCF01"
            ),
            "learner_lines": [45205],
        },
        "strict_ledger_entries": {
            "learner_lines": [45818, 4785, 21361],
            "entry_sha256": {
                "45818": (
                    "D34E079717436B166B9305D7F1A32C6A366654E100F903873DB79003AB409997"
                ),
                "4785": (
                    "41F3FCFF4911615606DAC601641786B1334C9724A6CDE835D6AF86C1004E4EC0"
                ),
                "21361": (
                    "70BE599AC4B88BE6A9248A771E0D415B90B81586F50B7000361A1918A7C1D5F3"
                ),
            },
        },
    }
    expected_phase511_source = {
        "sha256": (
            "8C507321A27ACD3FE9F919E82C1C380833D6D51760C122467D49757511004504"
        ),
        "entries_sha256": (
            "A542BC4464CDA30FBE39C28F0EFBEE51EECE83EEABBEA5D3A201388DA3AA7DEB"
        ),
    }
    if (
        set(phase511_transition) != {
            "schema_version", "phase", "source_fake_coarse_manifest", "sources",
            "supersedes", "counts", "entries_sha256", "entries",
        }
        or set(phase511_transition.get("sources", {})) != {"learner", "academic"}
        or phase511_transition.get("schema_version") != 2
        or phase511_transition.get("phase") != 511
        or sha256_bytes(provenance_manifest_raw)
        != expected_phase511_source["sha256"]
        or provenance_manifest.get("entries_sha256")
        != expected_phase511_source["entries_sha256"]
        or sha256_bytes(serialized_phase511) != expected_phase511_hash
        or phase511_transition.get("entries_sha256") != expected_phase511_hash
        or phase511_transition.get("counts") != expected_phase511_counts
        or phase511_transition.get("source_fake_coarse_manifest")
        != expected_phase511_source
        or phase511_transition.get("sources", {}).get("learner")
        != provenance_source_identity.get("learner")
        or phase511_transition.get("sources", {}).get("academic")
        != provenance_source_identity.get("academic")
        or phase511_transition.get("supersedes")
        != expected_phase511_supersedes
        or len(phase511_entries) != 21
    ):
        raise ValueError("Phase 511 fake-coarse transition entry fingerprint mismatch")
    phase511_transition_by_line = {}
    expected_phase511_lines = {
        45205, 45818, 4785, 21361, 60166, 60735,
        24033, 34886, 44893, 46627, 48081, 49821, 51048, 54151,
        54383, 55369, 59757, 60165, 60167, 60168, 60169,
    }
    for entry in phase511_entries:
        line = entry.get("learner_line")
        if (
            line not in expected_phase511_lines
            or line in phase511_transition_by_line
            or line in ff33_transition_by_line
            or line in final_5e_transition_by_line
        ):
            raise ValueError(f"invalid/reused Phase 511 transition line: {line!r}")
        phase511_transition_by_line[line] = entry
    if set(phase511_transition_by_line) != expected_phase511_lines:
        raise ValueError("Phase 511 transition line set changed")

    superseded_historical_lines = set(
        expected_phase511_supersedes["historical_manifest"]["learner_lines"]
    )
    if set(phase511_transition_by_line) & set(transition_by_line) != (
        superseded_historical_lines
    ):
        raise ValueError("unexpected Phase 511/historical transition overlap")
    for line in superseded_historical_lines:
        historical_entry = transition_by_line.get(line)
        phase511_entry = phase511_transition_by_line.get(line)
        serialized_historical_entry = json.dumps(
            historical_entry, ensure_ascii=False, separators=(",", ":"),
        ).encode("utf-8")
        if (
            historical_entry is None
            or phase511_entry is None
            or sha256_bytes(serialized_historical_entry)
            != phase511_entry.get("supersedes_historical_entry_sha256")
        ):
            raise ValueError(
                f"Phase 511 historical supersession identity drift at line {line}"
            )
    historical_effective_by_line = {
        line: entry for line, entry in transition_by_line.items()
        if line not in superseded_historical_lines
    }
    combined_transition_by_line = {
        **historical_effective_by_line,
        **ff33_transition_by_line,
        **final_5e_transition_by_line,
        **phase511_transition_by_line,
    }
    if (
        len(historical_effective_by_line) != 135
        or len(combined_transition_by_line) != 158
    ):
        raise ValueError("effective staged-transition scope count changed")

    phase532_transition_by_line = {}
    if phase532_enabled:
        carried_lines = phase532_carry.authority_lines()
        if (
            set(phase511_transition_by_line)
            != set(carried_lines["phase511_transition"])
            or set(ff33_transition_by_line)
            != set(carried_lines["ff33_transition"])
            or set(final_5e_transition_by_line)
            != set(carried_lines["5e_transition"])
        ):
            raise ValueError("Phase 532 carried transition scope changed")
        for reviewed in phase532_reference_review["policy"]["fake"]["entries"]:
            line = reviewed["learner_line"]
            manifest_entry = entries_by_line.get(line)
            target = reviewed["target"]
            if (
                line in combined_transition_by_line
                or line in phase532_transition_by_line
                or manifest_entry is None
                or manifest_entry.get("surface") != reviewed["surface"]
                or audit.expected_signature(target)[0]
                != audit.canonical(reviewed["surface"])
            ):
                raise ValueError(
                    f"invalid Phase 532 full-audit transition: {line!r}"
                )
            phase532_transition_by_line[line] = {
                "learner_line": line,
                "surface": reviewed["surface"],
                "coarse_decomposition": target,
                "category": reviewed["disposition"],
            }
        if len(phase532_transition_by_line) != 35:
            raise ValueError("Phase 532 full-audit transition count changed")
        combined_transition_by_line.update(phase532_transition_by_line)
        if len(combined_transition_by_line) != 193:
            raise ValueError("Phase 532 pre-retirement transition union changed")

    retired_transition_by_line = {}
    candidate_disposition_identity = None
    if phase532_enabled:
        retired = phase532_reference_review["policy"]["fake"][
            "retired_historical_entries"
        ]
        if len(retired) != 1:
            raise ValueError("Phase 532 historical retirement count changed")
        disposition = retired[0]
        line = disposition["learner_line"]
        previous = combined_transition_by_line.get(line)
        learner_line = learner_lines[line - 1]
        academic_line = academic_lines[line - 1]
        if (
            line != 2704
            or previous != {
                "learner_line": 2704,
                "surface": "atletiko",
                "coarse_decomposition": "atletik/o",
                "category": "reviewed_c679_to_b090_fake_transition",
            }
            or audit.FAKE_MARKER_RE.search(learner_line)
            or audit.FAKE_MARKER_RE.search(academic_line)
            or disposition.get("historical_coarse_decomposition")
            != previous["coarse_decomposition"]
            or disposition.get("candidate_learner_decomposition")
            != normalize_slash_decomposition(
                learner_line.lstrip("\ufeff").split(":", 1)[0].strip()
            )
            or disposition.get("candidate_academic_decomposition")
            != normalize_slash_decomposition(
                academic_line.lstrip("\ufeff").split(":", 1)[0].strip()
            )
        ):
            raise ValueError("Phase 532 atletiko retirement context changed")
        retired_transition_by_line[line] = disposition
        candidate_disposition_identity = {
            "source": "phase532_ruby_policy",
            "source_phase": phase532_policy.PHASE,
            "entries": 1,
            "entries_sha256": (
                phase532_policy.RETIRED_HISTORICAL_ENTRIES_SHA256
            ),
            "review_identity": phase532_reference_review["identity"],
            "carry_forward_identity": phase532_carry.review_identity(),
        }
    elif candidate_dispositions_path is not None:
        dispositions_path = candidate_dispositions_path.resolve()
        dispositions_raw = dispositions_path.read_bytes()
        dispositions = json.loads(dispositions_raw.decode("utf-8"))
        expected_disposition_sources = {
            "learner_sha256": sha256_bytes(learner_raw),
            "academic_sha256": academic_digest,
            "candidate_manifest_sha256": sha256_bytes(manifest_raw),
            "candidate_manifest_entries_sha256": manifest["entries_sha256"],
        }
        if (
            set(dispositions) != {
                "schema_version", "candidate_only", "source_phase",
                "sources", "entries",
            }
            or dispositions.get("schema_version") != 1
            or dispositions.get("candidate_only") is not True
            or not isinstance(dispositions.get("source_phase"), int)
            or dispositions.get("sources") != expected_disposition_sources
            or not isinstance(dispositions.get("entries"), list)
            or not dispositions["entries"]
        ):
            raise ValueError("invalid candidate transition dispositions")
        for disposition in dispositions["entries"]:
            line = disposition.get("learner_line")
            previous = combined_transition_by_line.get(line)
            if (
                not isinstance(line, int)
                or line in retired_transition_by_line
                or previous is None
                or disposition.get("surface") != previous.get("surface")
                or disposition.get("previous_coarse_decomposition")
                != previous.get("coarse_decomposition")
                or disposition.get("status")
                != "retired_fake_marker_transition_pending_review"
                or disposition.get("decision") != "pending_review"
            ):
                raise ValueError(
                    f"invalid candidate transition disposition at line {line!r}"
                )
            learner_line = learner_lines[line - 1]
            academic_line = academic_lines[line - 1]
            if (
                audit.FAKE_MARKER_RE.search(learner_line)
                or audit.FAKE_MARKER_RE.search(academic_line)
            ):
                raise ValueError(
                    f"retired transition still has a fake marker at line {line}"
                )
            learner_decomposition = normalize_slash_decomposition(
                strip_duplicate_metadata(
                    learner_line.lstrip("\ufeff").split(":", 1)[0].strip()
                )[0]
            )
            academic_decomposition = normalize_slash_decomposition(
                strip_duplicate_metadata(
                    academic_line.lstrip("\ufeff").split(":", 1)[0].strip()
                )[0]
            )
            current_surface = audit.canonical(
                learner_decomposition.replace("/", "")
            )
            if (
                disposition.get("current_learner_decomposition")
                != learner_decomposition
                or disposition.get("current_academic_decomposition")
                != academic_decomposition
                or learner_decomposition != academic_decomposition
                or disposition.get("surface") != current_surface
            ):
                raise ValueError(
                    f"candidate transition disposition context drift at line {line}"
                )
            expected_scope = (
                "phase511_supersession"
                if line in phase511_transition_by_line
                else "final_5e_delta"
                if line in final_5e_transition_by_line
                else "ff33_delta"
                if line in ff33_transition_by_line
                else "historical_c679_b090"
            )
            if disposition.get("previous_transition_scope") != expected_scope:
                raise ValueError(
                    f"candidate transition scope drift at line {line}"
                )
            retired_transition_by_line[line] = disposition
        candidate_disposition_identity = {
            "path": str(dispositions_path),
            "sha256": sha256_bytes(dispositions_raw),
            "source_phase": dispositions["source_phase"],
            "entries": len(dispositions["entries"]),
            "statuses": dict(collections.Counter(
                row["status"] for row in dispositions["entries"]
            )),
        }

    active_transition_by_line = {
        line: entry for line, entry in combined_transition_by_line.items()
        if line not in retired_transition_by_line
    }
    if len(active_transition_by_line) != (
        len(combined_transition_by_line) - len(retired_transition_by_line)
    ):
        raise ValueError("candidate transition retirement accounting changed")
    active_transition_scope_rows = collections.Counter()
    for line in active_transition_by_line:
        if line in phase532_transition_by_line:
            active_transition_scope_rows["phase532_selected_ruby"] += 1
        elif line in phase511_transition_by_line:
            active_transition_scope_rows["phase511_supersession"] += 1
        elif line in final_5e_transition_by_line:
            active_transition_scope_rows["final_5e_delta"] += 1
        elif line in ff33_transition_by_line:
            active_transition_scope_rows["ff33_delta"] += 1
        else:
            active_transition_scope_rows["historical_c679_b090"] += 1

    authority_rows = []
    used_entries = set()
    used_transition = set()
    invariant = collections.Counter()
    categories = collections.Counter()
    for line_number, (learner_line, academic_line) in enumerate(
        zip(learner_lines, academic_lines), 1
    ):
        if audit.FAKE_MARKER_RE.search(academic_line):
            raise ValueError(f"academic fake marker at line {line_number}")
        invariant["academic_rows_without_fake_marker"] += 1
        learner_raw_decomposition = learner_line.lstrip("\ufeff").split(":", 1)[0].strip()
        academic_raw_decomposition = academic_line.lstrip("\ufeff").split(":", 1)[0].strip()
        marked = bool(audit.FAKE_MARKER_RE.search(learner_line))
        if not marked:
            invariant["unmarked_rows"] += 1
            if learner_raw_decomposition != academic_raw_decomposition:
                raise ValueError(
                    f"unmarked learner/academic decomposition drift at line {line_number}"
                )
            invariant["unmarked_identical_decomposition"] += 1
            continue
        invariant["marked_rows"] += 1
        if learner_raw_decomposition == academic_raw_decomposition:
            raise ValueError(
                f"fake-marked decomposition did not differ at line {line_number}"
            )
        invariant["marked_different_decomposition"] += 1
        learner_without_marker = audit.FAKE_MARKER_RE.split(
            learner_line, maxsplit=1,
        )[0]
        if ":" not in learner_without_marker or ":" not in academic_line:
            raise ValueError(f"fake-marked gloss unavailable at line {line_number}")
        if (
            learner_without_marker.split(":", 1)[1]
            != academic_line.split(":", 1)[1]
        ):
            raise ValueError(
                f"fake-marked learner/academic sense drift at line {line_number}"
            )
        invariant["marked_gloss_context_matches_academic"] += 1

        academic_decomposition, has_metadata = strip_duplicate_metadata(
            academic_raw_decomposition,
        )
        learner_decomposition, _learner_has_metadata = strip_duplicate_metadata(
            learner_raw_decomposition,
        )
        academic_decomposition = normalize_slash_decomposition(
            academic_decomposition,
        )
        learner_decomposition = normalize_slash_decomposition(
            learner_decomposition,
        )
        entry = entries_by_line.get(line_number)
        if entry is not None:
            used_entries.add(line_number)
            if entry.get("academic_decomposition") != academic_decomposition:
                raise ValueError(
                    f"fake-coarse academic provenance drift at line {line_number}"
                )
            phase532_transition_entry = phase532_transition_by_line.get(
                line_number
            )
            selected_decomposition = (
                phase532_transition_entry["coarse_decomposition"]
                if phase532_transition_entry is not None
                else entry["coarse_decomposition"]
            )
            surface = entry["surface"]
            category = "single_word_evaluable_manifest"
            source = (
                audit.PHASE532_REFERENCE_SOURCE
                if phase532_transition_entry is not None
                else entry["authority"]
            )
        else:
            selected_decomposition = academic_decomposition
            surface = audit.canonical(academic_decomposition.replace("/", ""))
            if has_metadata:
                category = "duplicate_metadata_prefix"
            elif " " in academic_decomposition:
                category = "multiword_expression"
            elif any(character.isdigit() for character in surface):
                category = "numeric_or_punctuation_expression"
            else:
                category = "unclassified_manifest_exclusion"
            source = "paired_academic_excluded_single_word_scope"
        expected = expected_expression_structure(selected_decomposition)
        if expected[0] != surface:
            raise ValueError(
                f"fake-coarse full expression reconstruction drift at line {line_number}: "
                f"{selected_decomposition!r} -> {expected[0]!r} != {surface!r}"
            )
        learner_surface = audit.canonical(learner_decomposition.replace("/", ""))
        if learner_surface.casefold() != surface.casefold():
            raise ValueError(f"fake-coarse learner surface drift at line {line_number}")
        transition_entry = active_transition_by_line.get(line_number)
        transition_scope = None
        if line_number in phase532_transition_by_line:
            transition_scope = "phase532_selected_ruby"
        elif line_number in historical_effective_by_line:
            transition_scope = "historical_c679_b090"
        elif line_number in ff33_transition_by_line:
            transition_scope = "ff33_delta"
        elif line_number in final_5e_transition_by_line:
            transition_scope = "final_5e_delta"
        elif line_number in phase511_transition_by_line:
            transition_scope = "phase511_supersession"
        if transition_entry is not None:
            if (
                transition_entry.get("surface") != surface
                or transition_entry.get("coarse_decomposition")
                != selected_decomposition
            ):
                raise ValueError(
                    f"staged transition authority drift at line {line_number}"
                )
            used_transition.add(line_number)
        categories[category] += 1
        authority_rows.append({
            "learner_line": line_number,
            "surface": surface,
            "learner_decomposition": learner_decomposition,
            "academic_decomposition": academic_decomposition,
            "selected_decomposition": selected_decomposition,
            "authority_source": source,
            "coverage_category": category,
            "transition_required": transition_entry is not None,
            "transition_scope": transition_scope,
            "transition_category": (
                transition_entry.get("category") if transition_entry else None
            ),
            "expected": expected,
        })
    if used_entries != set(entries_by_line):
        raise ValueError(
            "unused fake-coarse manifest lines: "
            f"{sorted(set(entries_by_line) - used_entries)[:20]!r}"
        )
    if used_transition != set(active_transition_by_line):
        raise ValueError(
            "unused staged-transition lines: "
            f"{sorted(set(active_transition_by_line) - used_transition)[:20]!r}"
        )
    if categories["unclassified_manifest_exclusion"]:
        raise ValueError(
            "unclassified fake-coarse exclusions: "
            f"{categories['unclassified_manifest_exclusion']}"
        )
    expected_invariant = manifest.get("paired_invariant")
    if dict(invariant) != expected_invariant:
        raise ValueError(
            f"paired-master invariant changed: {dict(invariant)!r} "
            f"!= {expected_invariant!r}"
        )
    if len(authority_rows) != invariant["marked_rows"]:
        raise ValueError("not every fake-marked line received an authority row")
    return authority_rows, {
        "academic": {
            "path": str(academic_path.resolve()),
            "bytes": len(academic_raw),
            "sha256": academic_digest,
            "lines": len(academic_lines),
        },
        "fake_coarse_manifest": {
            "path": (
                str(manifest_path.relative_to(ROOT))
                if manifest_path.is_relative_to(ROOT)
                else str(manifest_path)
            ),
            "sha256": sha256_bytes(manifest_raw),
            "entries_sha256": manifest["entries_sha256"],
            "entries": len(manifest["entries"]),
            "candidate_only": candidate_mode,
            "provenance_manifest_path": str(
                PHASE513_FAKE_COARSE_EVIDENCE.relative_to(ROOT)
            ),
            "provenance_manifest_sha256": sha256_bytes(
                provenance_manifest_raw
            ),
        },
        "transition_manifests": {
            "historical_c679_b090": {
                "path": str(FAKE_TRANSITION_MANIFEST.relative_to(ROOT)),
                "sha256": sha256_bytes(transition_raw),
                "entries_sha256": transition["entries_sha256"],
                "counts": transition["counts"],
                "effective_entries": len(historical_effective_by_line),
                "superseded_lines": sorted(superseded_historical_lines),
            },
            "ff33_delta": {
                "path": str(FAKE_FF33_TRANSITION_MANIFEST.relative_to(ROOT)),
                "sha256": sha256_bytes(ff33_transition_raw),
                "entries_sha256": ff33_transition["entries_sha256"],
                "counts": ff33_transition["counts"],
            },
            "final_5e_delta": {
                "path": str(FAKE_5E_TRANSITION_MANIFEST.relative_to(ROOT)),
                "sha256": sha256_bytes(final_5e_transition_raw),
                "entries_sha256": final_5e_transition["entries_sha256"],
                "counts": final_5e_transition["counts"],
            },
            "phase511_supersession": {
                "path": str(
                    FAKE_PHASE511_TRANSITION_MANIFEST.relative_to(ROOT)
                ),
                "sha256": sha256_bytes(phase511_transition_raw),
                "entries_sha256": phase511_transition["entries_sha256"],
                "counts": phase511_transition["counts"],
                "supersedes": phase511_transition["supersedes"],
            },
            **({
                "phase532_selected_ruby": {
                    "entries": len(phase532_transition_by_line),
                    "entries_sha256": (
                        phase532_policy.FAKE_TRANSITION_ENTRIES_SHA256
                    ),
                    "review_identity": phase532_reference_review["identity"],
                },
            } if phase532_enabled else {}),
            "combined_entries": len(combined_transition_by_line),
            "active_entries": len(active_transition_by_line),
            "active_scope_rows": dict(active_transition_scope_rows),
            "retired_pending_entries": len(retired_transition_by_line),
            "historical_entries": len(transition_by_line),
            "historical_effective_entries": len(historical_effective_by_line),
            "ff33_entries": len(ff33_transition_by_line),
            "final_5e_entries": len(final_5e_transition_by_line),
            "phase511_entries": len(phase511_transition_by_line),
            "phase532_entries": len(phase532_transition_by_line),
        },
        "candidate_transition_dispositions": candidate_disposition_identity,
        "paired_invariant": dict(invariant),
        "coverage_categories": dict(categories),
    }


def app_input_fingerprints() -> dict:
    return {
        language: audit.current_app_fingerprint(
            ROOT / f"Esperanto-Kanji-Ruby-{language}"
        )
        for language in LANGUAGES
    }


def render_language(language: str, surfaces: list[str], surface_records: dict,
                    batch_size: int):
    app_dir = ROOT / f"Esperanto-Kanji-Ruby-{language}"
    data_dir = app_dir / "app_data"
    payload_path = data_dir / RUBY_PAYLOAD_NAME
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    local_rules, global_rules, two_char_rules = audit.extract_lists(payload)
    module = audit.runtime_module(app_dir, f"master_full_{language}")
    overlay = audit.overlay_module(app_dir, f"master_full_{language}")
    corrections = json.loads(
        (data_dir / "user_corrections.json").read_text(encoding="utf-8")
    )
    correction_entries = audit.overlay_entries_from_corrections(corrections, "ruby")
    effective_global = overlay.merge_overlay(global_rules, correction_entries)
    skip = module.import_placeholders(str(data_dir / "placeholders_skip.txt"))
    local_capture = module.import_placeholders(
        str(data_dir / "placeholders_localcapture.txt")
    )
    char_width_path = data_dir / "char_widths.json"
    char_widths = json.loads(char_width_path.read_text(encoding="utf-8"))
    css_class_scale = deployed_css_class_scale(app_dir)

    structural = {}
    issue_rows = {
        "runtime_errors": [],
        "visible_failures": [],
        "placeholder_residuals": [],
        "empty_rt": [],
        "empty_rb": [],
        "zero_token_outputs": [],
    }
    naked = collections.Counter()
    naked_examples = collections.defaultdict(list)
    ruby_stats = {
        "unique_ruby_occurrences": 0,
        "line_weighted_ruby_occurrences": 0,
        "empty_rt_unique": 0,
        "empty_rt_line_weighted": 0,
        "empty_rb_unique": 0,
        "empty_rb_line_weighted": 0,
        "annotation_like_over_2_unique": 0,
        "annotation_like_over_2_line_weighted": 0,
        "plain_gloss_over_2_unique": 0,
        "plain_gloss_over_2_line_weighted": 0,
        "missing_width_characters": collections.Counter(),
        "unknown_rt_classes": collections.Counter(),
        "rt_class_unique": collections.Counter(),
        "rt_class_line_weighted": collections.Counter(),
        "br_count_unique": collections.Counter(),
        "br_count_line_weighted": collections.Counter(),
        "char_ratio_bins_unique": collections.Counter(),
        "char_ratio_bins_line_weighted": collections.Counter(),
        "raw_width_ratio_bins_unique": collections.Counter(),
        "raw_width_ratio_bins_line_weighted": collections.Counter(),
        "effective_width_ratio_bins_unique": collections.Counter(),
        "effective_width_ratio_bins_line_weighted": collections.Counter(),
        "max_char_ratio": None,
        "max_raw_width_ratio": None,
        "max_effective_width_ratio": None,
    }
    top_width = []
    top_chars = []
    top_annotation = []
    top_plain = []
    heap_serial = 0
    root_stats = {}
    render_started = time.perf_counter()

    def width(text: str) -> float:
        total = 0.0
        for character in text:
            if character not in char_widths:
                ruby_stats["missing_width_characters"][character] += 1
            total += float(char_widths.get(character, 8))
        return total

    def render_batch(batch: list[str]):
        source = "\n".join(f" {surface} " for surface in batch)
        output = overlay.autofix_render(
            source, skip, local_rules, local_capture, effective_global,
            two_char_rules, audit.FORMAT, str(data_dir), "ruby",
            module.orchestrate_comprehensive_esperanto_text_replacement,
        )
        lines = output.splitlines()
        if len(lines) == len(batch):
            return lines
        fallback = []
        for surface in batch:
            one = overlay.autofix_render(
                f" {surface} ", skip, local_rules, local_capture,
                effective_global, two_char_rules, audit.FORMAT,
                str(data_dir), "ruby",
                module.orchestrate_comprehensive_esperanto_text_replacement,
            )
            one_lines = one.splitlines()
            if len(one_lines) != 1:
                raise ValueError(
                    f"{language} line accounting failed for {surface!r}: "
                    f"batch={len(lines)}/{len(batch)}, single={len(one_lines)}"
                )
            fallback.append(one_lines[0])
        return fallback

    for start in range(0, len(surfaces), batch_size):
        batch = surfaces[start:start + batch_size]
        try:
            rendered_lines = render_batch(batch)
        except Exception as error:
            for surface in batch:
                issue_rows["runtime_errors"].append({
                    "surface": surface,
                    "line_numbers": surface_records[surface]["line_numbers"],
                    "error": f"{type(error).__name__}: {error}",
                })
            continue
        for surface, rendered in zip(batch, rendered_lines):
            record = surface_records[surface]
            # Width/naked-fragment distributions are strictly for the exact
            # 62K master-line surfaces.  Synthetic hyphen-stripped fast keys
            # are rendered for the labelled legacy subset but carry zero
            # weight here unless they are also exact master surfaces.
            weight = record["full_line_count"]
            typed = audit.rendered_typed_parts(rendered)
            visible, spans = audit.signature_from_typed_parts(typed)
            tokens = token_projection(visible, spans)
            structural[surface] = (visible, spans, tokens)
            if visible != surface:
                issue_rows["visible_failures"].append({
                    "surface": surface,
                    "actual_visible": visible,
                    "line_numbers": record["line_numbers"],
                    "scopes": record["scopes"],
                })
            placeholders = sorted(set(PLACEHOLDER_RE.findall(rendered)))
            if placeholders:
                issue_rows["placeholder_residuals"].append({
                    "surface": surface,
                    "placeholders": placeholders,
                    "line_numbers": record["line_numbers"],
                    "scopes": record["scopes"],
                })
            if not tokens:
                issue_rows["zero_token_outputs"].append({
                    "surface": surface,
                    "actual_visible": visible,
                    "line_numbers": record["line_numbers"],
                    "scopes": record["scopes"],
                })
            if not record["full_scope"]:
                continue

            for token_index, (token, token_spans) in enumerate(tokens):
                ruby_letter = any(
                    is_ruby and ESP_LETTER_RE.search(piece)
                    for piece, is_ruby in token_spans
                )
                literal_letter_parts = [
                    (part_index, piece)
                    for part_index, (piece, is_ruby) in enumerate(token_spans)
                    if not is_ruby and ESP_LETTER_RE.search(piece)
                ]
                if not literal_letter_parts:
                    naked["fully_annotated_tokens_unique"] += 1
                    naked["fully_annotated_tokens_line_weighted"] += weight
                    continue
                if not ruby_letter:
                    naked["fully_naked_tokens_unique"] += 1
                    naked["fully_naked_tokens_line_weighted"] += weight
                    category = "fully_naked_grammar_or_short" if (
                        token.lower() in audit.TERMINAL_BARE_PIECES
                        or len(token) < 2
                    ) else "fully_naked_lexical_review_candidate"
                    naked[category + "_unique"] += 1
                    naked[category + "_line_weighted"] += weight
                    if len(naked_examples[category]) < TOP_LIMIT:
                        naked_examples[category].append({
                            "surface": surface,
                            "token": token,
                            "token_index": token_index,
                            "signature": audit.display_typed_parts(list(token_spans)),
                            "line_numbers": record["line_numbers"],
                        })
                else:
                    naked["mixed_ruby_literal_tokens_unique"] += 1
                    naked["mixed_ruby_literal_tokens_line_weighted"] += weight
                for part_index, piece in literal_letter_parts:
                    naked["literal_letter_fragments_unique"] += 1
                    naked["literal_letter_fragments_line_weighted"] += weight
                    expected_terminal = (
                        part_index == len(token_spans) - 1
                        and piece.lower() in audit.TERMINAL_BARE_PIECES
                    )
                    category = (
                        "expected_terminal_or_grammar_fragment"
                        if expected_terminal or len(piece) < 2
                        else "nonterminal_naked_fragment_review_candidate"
                    )
                    naked[category + "_unique"] += 1
                    naked[category + "_line_weighted"] += weight
                    if len(naked_examples[category]) < TOP_LIMIT:
                        naked_examples[category].append({
                            "surface": surface,
                            "token": token,
                            "fragment": piece,
                            "signature": audit.display_typed_parts(list(token_spans)),
                            "line_numbers": record["line_numbers"],
                        })

            for ruby_index, match in enumerate(RUBY_DETAIL_RE.finditer(rendered)):
                base = audit.canonical(html_text(match.group("rb")))
                rt_break_text = html_text(match.group("rt"), preserve_breaks=True)
                rt_visible = "".join(rt_break_text.splitlines()).strip()
                class_match = CLASS_RE.search(match.group("attrs"))
                rt_class = class_match.group(2).strip() if class_match else ""
                rt_class = rt_class.split()[0] if rt_class else "(none)"
                br_count = len(BR_RE.findall(match.group("rt")))
                ruby_stats["unique_ruby_occurrences"] += 1
                ruby_stats["line_weighted_ruby_occurrences"] += weight
                ruby_stats["rt_class_unique"][rt_class] += 1
                ruby_stats["rt_class_line_weighted"][rt_class] += weight
                ruby_stats["br_count_unique"][str(br_count)] += 1
                ruby_stats["br_count_line_weighted"][str(br_count)] += weight
                if not base:
                    ruby_stats["empty_rb_unique"] += 1
                    ruby_stats["empty_rb_line_weighted"] += weight
                    issue_rows["empty_rb"].append({
                        "surface": surface,
                        "rt": rt_visible,
                        "line_numbers": record["line_numbers"],
                    })
                if not rt_visible:
                    ruby_stats["empty_rt_unique"] += 1
                    ruby_stats["empty_rt_line_weighted"] += weight
                    issue_rows["empty_rt"].append({
                        "surface": surface,
                        "base": base,
                        "line_numbers": record["line_numbers"],
                    })

                base_letters = len(ESP_LETTER_RE.findall(base))
                rt_chars = sum(not character.isspace() for character in rt_visible)
                char_ratio = rt_chars / base_letters if base_letters else None
                base_width = width(base)
                rt_width = width(rt_visible)
                raw_width_ratio = rt_width / base_width if base_width else None
                lines = rt_break_text.splitlines() or [rt_visible]
                max_line_width = max((width(line) for line in lines), default=0.0)
                scale = css_class_scale.get(rt_class)
                if scale is None:
                    ruby_stats["unknown_rt_classes"][rt_class] += weight
                effective_width_ratio = (
                    max_line_width * scale / base_width
                    if base_width and scale is not None else None
                )
                for key, value in (
                    ("char_ratio", char_ratio),
                    ("raw_width_ratio", raw_width_ratio),
                    ("effective_width_ratio", effective_width_ratio),
                ):
                    bin_name = ratio_bin(value)
                    ruby_stats[key + "_bins_unique"][bin_name] += 1
                    ruby_stats[key + "_bins_line_weighted"][bin_name] += weight
                    max_key = "max_" + key
                    if value is not None and (
                        ruby_stats[max_key] is None or value > ruby_stats[max_key]
                    ):
                        ruby_stats[max_key] = value

                note_like = bool(NOTE_LIKE_RE.search(rt_visible))
                context = {
                    "surface": surface,
                    "decompositions": record["decompositions"],
                    "line_numbers": record["line_numbers"],
                    "line_count": weight,
                    "ruby_index": ruby_index,
                    "base": base,
                    "rt": rt_visible,
                    "rt_class": rt_class,
                    "br_count": br_count,
                    "base_alphabet_chars": base_letters,
                    "rt_visible_chars": rt_chars,
                    "char_ratio": round(char_ratio, 6) if char_ratio is not None else None,
                    "base_width": round(base_width, 6),
                    "rt_width": round(rt_width, 6),
                    "raw_width_ratio": (
                        round(raw_width_ratio, 6)
                        if raw_width_ratio is not None else None
                    ),
                    "effective_max_line_width_ratio": (
                        round(effective_width_ratio, 6)
                        if effective_width_ratio is not None else None
                    ),
                    "annotation_like": note_like,
                }
                heap_serial += 1
                if raw_width_ratio is not None:
                    push_top(top_width, raw_width_ratio, heap_serial, context)
                if char_ratio is not None:
                    push_top(top_chars, char_ratio, heap_serial, context)
                if raw_width_ratio is not None and raw_width_ratio > 2:
                    prefix = "annotation_like" if note_like else "plain_gloss"
                    ruby_stats[prefix + "_over_2_unique"] += 1
                    ruby_stats[prefix + "_over_2_line_weighted"] += weight
                    push_top(
                        top_annotation if note_like else top_plain,
                        raw_width_ratio, heap_serial, context,
                    )

                root = root_stats.setdefault(base, {
                    "base": base,
                    "unique_contexts": 0,
                    "line_weighted_contexts": 0,
                    "rt_values": collections.Counter(),
                    "max_raw_width_ratio": None,
                    "max_char_ratio": None,
                    "max_context": None,
                })
                root["unique_contexts"] += 1
                root["line_weighted_contexts"] += weight
                root["rt_values"][rt_visible] += weight
                if raw_width_ratio is not None and (
                    root["max_raw_width_ratio"] is None
                    or raw_width_ratio > root["max_raw_width_ratio"]
                ):
                    root["max_raw_width_ratio"] = raw_width_ratio
                    root["max_context"] = context
                if char_ratio is not None and (
                    root["max_char_ratio"] is None
                    or char_ratio > root["max_char_ratio"]
                ):
                    root["max_char_ratio"] = char_ratio

        print(
            f"[{language}] {min(start + len(batch), len(surfaces))}/"
            f"{len(surfaces)} unique surfaces",
            flush=True,
        )

    root_top = []
    for root in root_stats.values():
        if root["max_raw_width_ratio"] is None:
            continue
        root_top.append({
            "base": root["base"],
            "unique_contexts": root["unique_contexts"],
            "line_weighted_contexts": root["line_weighted_contexts"],
            "rt_values_top": [
                {"rt": rt, "line_weighted_count": count}
                for rt, count in root["rt_values"].most_common(10)
            ],
            "max_raw_width_ratio": round(root["max_raw_width_ratio"], 6),
            "max_char_ratio": (
                round(root["max_char_ratio"], 6)
                if root["max_char_ratio"] is not None else None
            ),
            "max_context": root["max_context"],
        })
    root_top.sort(
        key=lambda row: (row["max_raw_width_ratio"], row["line_weighted_contexts"]),
        reverse=True,
    )
    root_top = root_top[:TOP_LIMIT]

    ruby_serial = {
        key: value for key, value in ruby_stats.items()
        if not isinstance(value, collections.Counter)
    }
    for key, value in ruby_stats.items():
        if not isinstance(value, collections.Counter):
            continue
        if "_bins_" in key:
            ruby_serial[key] = cumulative_bins(value)
        else:
            ruby_serial[key] = dict(value)
    ruby_serial["top_contexts_by_raw_width_ratio"] = top_payload(top_width)
    ruby_serial["top_contexts_by_character_ratio"] = top_payload(top_chars)
    ruby_serial["top_annotation_like_over_2"] = top_payload(top_annotation)
    ruby_serial["top_plain_gloss_review_candidates_over_2"] = top_payload(top_plain)
    ruby_serial["top_roots_by_raw_width_ratio"] = root_top
    ruby_serial["classification_note"] = (
        "annotation_like is a conservative regex heuristic (brackets or explicit "
        "abbreviation/grammar/name/science markers); plain_gloss rows are review "
        "candidates, not automatically errors. Boundaries are never changed."
    )

    result = {
        "language": language,
        "render_seconds": round(time.perf_counter() - render_started, 3),
        "runtime_sha256": sha256_file(app_dir / "esp_text_replacement_module.py"),
        "overlay_sha256": sha256_file(app_dir / "esp_overlay_module.py"),
        "payload_sha256": sha256_file(payload_path),
        "char_widths_sha256": sha256_file(char_width_path),
        "css_class_scale": css_class_scale,
        "global_rules": len(global_rules),
        "localized_rules": len(local_rules),
        "two_char_rules": len(two_char_rules),
        "correction_entries": len(correction_entries),
        "rendered_unique_surfaces": len(structural),
        "rendered_full_exact_surfaces": sum(
            row["full_scope"] for row in surface_records.values()
        ),
        "rendered_legacy_fast_surfaces": sum(
            row["fast_scope"] for row in surface_records.values()
        ),
        "issues": issue_rows,
        "issue_counts": {
            key: len(rows) for key, rows in issue_rows.items()
        },
        "naked_fragment_audit": {
            "counts": dict(naked),
            "examples": dict(naked_examples),
            "note": (
                "Terminal/one-letter literal pieces are separated from lexical "
                "fully-naked and nonterminal review candidates. Review candidates "
                "may still be legitimate proper names or unsupported dictionary text."
            ),
        },
        "ruby_length_audit": ruby_serial,
    }

    del payload, local_rules, global_rules, two_char_rules, effective_global
    del module, overlay, corrections, char_widths, root_stats
    gc.collect()
    return structural, result


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--expected-gold-sha256", required=True)
    parser.add_argument("--academic", type=Path, required=True)
    parser.add_argument("--expected-academic-sha256", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument(
        "--candidate-fake-coarse-manifest", type=Path,
        help=(
            "External candidate-only coarse authority. A generic candidate "
            "requires --candidate-transition-dispositions; the exact Phase "
            "532 candidate instead requires both frozen source directories."
        ),
    )
    parser.add_argument(
        "--candidate-transition-dispositions", type=Path,
        help=(
            "Fail-closed ledger for reviewed historical transitions that the "
            "candidate master retired or changed."
        ),
    )
    parser.add_argument("--phase532-baseline-dir", type=Path)
    parser.add_argument("--phase532-candidate-dir", type=Path)
    parser.add_argument(
        "--phase532-runtime-mode",
        choices=phase532_runtime_gate.MODES,
        help=(
            "Required for the exact Phase 532 authority: pre-regen for the "
            "deployed safe-seven state, post-regen after formal regeneration."
        ),
    )
    parser.add_argument("--phase558-candidate-dir", type=Path)
    parser.add_argument("--phase558-ruby-disposition-ledger", type=Path)
    parser.add_argument("--phase558-japanese-guide", type=Path)
    parser.add_argument("--phase558-chinese-guide", type=Path)
    parser.add_argument(
        "--phase558-runtime-mode",
        choices=phase558_runtime_gate.MODES,
        help=(
            "Enable the exact five-surface Phase 558 Ruby sidecar over its "
            "Phase 532 parent. Formal promotion requires post-regen."
        ),
    )
    parser.add_argument(
        "--enforce-all-fake-coarse", action="store_true",
        help=(
            "Fail on every fake-row coarse mismatch.  Without this flag the "
            "full queue remains exhaustive in the report, while only the "
            "independently reviewed transition scopes are required gates."
        ),
    )
    parser.add_argument(
        "--allow-stable-tracked-changes",
        action="store_true",
        help=(
            "Allow formal regeneration outputs already present at audit start; "
            "the exact tracked-status set must remain unchanged during the audit."
        ),
    )
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args(argv)


def run(args):
    if args.batch_size <= 0:
        raise ValueError("--batch-size must be positive")
    candidate_mode = args.candidate_fake_coarse_manifest is not None
    phase532_dirs = (
        args.phase532_baseline_dir,
        args.phase532_candidate_dir,
    )
    phase558_options = (
        args.phase558_candidate_dir,
        args.phase558_ruby_disposition_ledger,
        args.phase558_japanese_guide,
        args.phase558_chinese_guide,
        args.phase558_runtime_mode,
    )
    phase558_enabled = any(value is not None for value in phase558_options)
    if phase558_enabled and not all(
        value is not None for value in phase558_options
    ):
        raise ValueError("all Phase 558 Ruby sidecar options are required")
    if any(path is not None for path in phase532_dirs) and not all(
        path is not None for path in phase532_dirs
    ):
        raise ValueError(
            "Phase 532 baseline and candidate directories are both required"
        )
    effective_manifest_path = (
        args.candidate_fake_coarse_manifest.resolve()
        if candidate_mode else FAKE_COARSE_MANIFEST
    )
    effective_manifest_sha256 = sha256_file(effective_manifest_path)
    phase532_enabled = (
        effective_manifest_sha256
        == phase532_policy.CANDIDATE_MANIFEST_SHA256
    )
    if phase532_enabled:
        if phase558_enabled:
            raise ValueError(
                "Phase 558 sidecar requires its exact external candidate manifest"
            )
        if args.candidate_transition_dispositions is not None:
            raise ValueError(
                "Phase 532 retirement is owned by the exact Ruby policy"
            )
        if args.phase532_runtime_mode is None:
            raise ValueError("Phase 532 runtime mode is required")
        if candidate_mode and not all(path is not None for path in phase532_dirs):
            raise ValueError(
                "external Phase 532 audit requires both frozen source directories"
            )
        phase532_reference_review = audit.load_phase532_reference_review(
            effective_manifest_path
        )
        if all(path is not None for path in phase532_dirs):
            phase532_source_review = phase532_builder.validate_frozen_closure(
                args.phase532_baseline_dir,
                args.phase532_candidate_dir,
                effective_manifest_path,
            )
            phase532_carry_review = (
                phase532_carry_builder.validate_frozen_closure(
                    args.phase532_baseline_dir,
                    args.phase532_candidate_dir,
                    effective_manifest_path,
                )
            )
            if (
                phase532_source_review["review_identity"]
                != phase532_reference_review["identity"]
                or phase532_carry_review["review_identity"]
                != phase532_carry.review_identity()
            ):
                raise ValueError("Phase 532 frozen authority identities differ")
        else:
            phase532_source_review = None
            phase532_carry_review = None
        phase532_parent_reference_review = phase532_reference_review
        phase558_source_review = None
        phase558_activation_report = None
    else:
        if candidate_mode != (
            args.candidate_transition_dispositions is not None
        ):
            raise ValueError(
                "generic candidate manifest and transition dispositions "
                "are both required"
            )
        if phase558_enabled:
            if (
                not candidate_mode
                or not all(path is not None for path in phase532_dirs)
                or args.phase532_runtime_mode != "post-regen"
                or args.phase558_runtime_mode != "post-regen"
                or effective_manifest_sha256
                != PHASE558_FAKE_MANIFEST_SHA256
                or sha256_file(args.candidate_transition_dispositions.resolve())
                != PHASE558_TRANSITION_DISPOSITIONS_SHA256
                or args.expected_gold_sha256.upper()
                != phase558_policy.EXPECTED_SOURCES[
                    "phase558_learner"
                ]["sha256"]
                or args.expected_academic_sha256.upper()
                != phase558_policy.EXPECTED_SOURCES[
                    "phase558_academic"
                ]["sha256"]
            ):
                raise ValueError("Phase 558 Ruby sidecar authority identity drift")
            parent_manifest_path = FAKE_COARSE_MANIFEST.resolve()
            phase532_parent_reference_review = (
                audit.load_phase532_reference_review(parent_manifest_path)
            )
            phase532_source_review = phase532_builder.validate_frozen_closure(
                args.phase532_baseline_dir,
                args.phase532_candidate_dir,
                parent_manifest_path,
            )
            phase532_carry_review = (
                phase532_carry_builder.validate_frozen_closure(
                    args.phase532_baseline_dir,
                    args.phase532_candidate_dir,
                    parent_manifest_path,
                )
            )
            phase558_activation_report = phase558_activation.activation_report()
            phase558_source_review = phase558_builder.validate_frozen_closure(
                args.phase532_candidate_dir,
                args.phase558_candidate_dir,
                args.phase558_ruby_disposition_ledger,
                args.phase558_japanese_guide,
                args.phase558_chinese_guide,
            )
            if (
                phase532_source_review["review_identity"]
                != phase532_parent_reference_review["identity"]
                or phase532_carry_review["review_identity"]
                != phase532_carry.review_identity()
                or phase558_source_review["review_identity"]
                != phase558_policy.review_identity()
                or phase558_activation_report.get(
                    "phase558_ruby_overlay_active"
                ) is not True
                or phase558_activation_report["overlay_review"]
                != phase558_policy.review_identity()
            ):
                raise ValueError("Phase 532/558 parent-sidecar closure differs")
            # Generic Phase 558 fake authority remains report-only outside its
            # staged reviewed transitions; it must not be reinterpreted as the
            # exact Phase 532 fake-policy manifest.
            phase532_reference_review = None
        else:
            if (
                any(path is not None for path in phase532_dirs)
                or args.phase532_runtime_mode is not None
            ):
                raise ValueError("Phase 532 options require its exact manifest")
            phase532_reference_review = None
            phase532_parent_reference_review = None
            phase532_source_review = None
            phase532_carry_review = None
            phase558_source_review = None
            phase558_activation_report = None
    phase532_parent_enabled = phase532_enabled or phase558_enabled
    head_at_start = git_text("rev-parse", "HEAD")
    if head_at_start != args.expected_head:
        raise ValueError(f"app HEAD changed: {head_at_start} != {args.expected_head}")
    tracked_at_start = tracked_status()
    if tracked_at_start and not args.allow_stable_tracked_changes:
        raise ValueError(f"isolated clone has tracked changes: {tracked_at_start}")
    app_inputs_at_start = app_input_fingerprints()
    script_sha256 = sha256_file(Path(__file__).resolve())
    authority_manifest_paths = [
        FAKE_COARSE_MANIFEST,
        PHASE513_FAKE_COARSE_EVIDENCE,
        FAKE_TRANSITION_MANIFEST,
        FAKE_FF33_TRANSITION_MANIFEST,
        FAKE_5E_TRANSITION_MANIFEST,
        FAKE_PHASE511_TRANSITION_MANIFEST,
        HERE / "_fake_coarse_pejvo_disagreement_review.json",
        HERE / "_fake_coarse_project_boundary_review.json",
        HERE / "localized_atomic_root_families.json",
    ]
    if phase532_parent_enabled:
        authority_manifest_paths.extend((
            phase532_policy.UNMARKED_REVIEW_PATH,
            phase532_policy.FAKE_TRANSITION_PATH,
            phase532_carry.LEDGER_PATH,
            Path(phase532_policy.__file__).resolve(),
            Path(phase532_carry.__file__).resolve(),
            Path(phase532_runtime_gate.__file__).resolve(),
            Path(phase532_builder.__file__).resolve(),
            Path(phase532_carry_builder.__file__).resolve(),
            Path(audit.__file__).resolve(),
        ))
    if phase558_enabled:
        authority_manifest_paths.extend((
            phase558_policy.REVIEW_PATH,
            phase558_activation.ACTIVATION_PATH,
            Path(phase558_policy.__file__).resolve(),
            Path(phase558_activation.__file__).resolve(),
            Path(phase558_runtime_gate.__file__).resolve(),
            Path(phase558_builder.__file__).resolve(),
        ))
    authority_manifest_hashes_at_start = {
        str(path.relative_to(ROOT)): sha256_file(path)
        for path in authority_manifest_paths
    }
    candidate_files = []
    if candidate_mode:
        candidate_files.append(args.candidate_fake_coarse_manifest.resolve())
    if args.candidate_transition_dispositions is not None:
        candidate_files.append(args.candidate_transition_dispositions.resolve())
    if phase558_enabled:
        candidate_files.extend((
            args.phase558_ruby_disposition_ledger.resolve(),
            args.phase558_japanese_guide.resolve(),
            args.phase558_chinese_guide.resolve(),
        ))
    candidate_file_hashes_at_start = {
        str(path): sha256_file(path) for path in candidate_files
    }

    (gold_raw, gold_text, records, exclusions, exclusion_rows,
     feature_counts, fast_counts) = parse_gold(
        args.gold.resolve(), args.expected_gold_sha256,
    )
    fake_authority_rows, fake_authority_identity = load_fake_coarse_authority(
        gold_raw, gold_text, args.academic.resolve(),
        args.expected_academic_sha256,
        args.candidate_fake_coarse_manifest,
        args.candidate_transition_dispositions,
        phase532_reference_review,
    )
    phase532_signature_report = (
        phase532_runtime_gate.validate_generated_payloads(
            phase532_runtime_gate.load_deployed_payloads(),
            args.phase532_runtime_mode,
        )
        if phase532_parent_enabled else None
    )
    phase558_signature_report = (
        phase558_runtime_gate.validate_deployed_payloads(
            args.phase558_runtime_mode,
            batch_size=33,
        )
        if phase558_enabled else None
    )
    # Exact master surfaces retain spaces/punctuation/hyphens.  In parallel,
    # reproduce the legacy fast script's hyphen-stripped keys exactly.  Render
    # their union once so both the 62K and labelled 55K scopes are measured.
    full_surface_records = {}
    fast_key_records = {}
    authority_surface_records = {}
    for row in records:
        target = full_surface_records.setdefault(row["surface"], {
            "surface": row["surface"],
            "line_numbers": [],
            "decompositions": [],
        })
        target["line_numbers"].append(row["line_number"])
        if row["decomposition"] not in target["decompositions"]:
            target["decompositions"].append(row["decomposition"])
        if row["fast_key"] is not None:
            fast = fast_key_records.setdefault(row["fast_key"], {
                "line_numbers": [],
                "decompositions": [],
            })
            fast["line_numbers"].append(row["line_number"])
            if row["decomposition"] not in fast["decompositions"]:
                fast["decompositions"].append(row["decomposition"])
    for row in fake_authority_rows:
        authority = authority_surface_records.setdefault(row["surface"], {
            "line_numbers": [],
            "decompositions": [],
        })
        authority["line_numbers"].append(row["learner_line"])
        if row["selected_decomposition"] not in authority["decompositions"]:
            authority["decompositions"].append(row["selected_decomposition"])
    for target in full_surface_records.values():
        target["line_count"] = len(target["line_numbers"])
    full_surfaces = sorted(full_surface_records)
    fast_surfaces = sorted(fast_key_records)
    surface_records = {}
    authority_surfaces = sorted(authority_surface_records)
    for surface in sorted(
        set(full_surfaces) | set(fast_surfaces) | set(authority_surfaces)
    ):
        full = full_surface_records.get(surface)
        fast = fast_key_records.get(surface)
        authority = authority_surface_records.get(surface)
        line_numbers = sorted(set(
            (full or {}).get("line_numbers", [])
            + (fast or {}).get("line_numbers", [])
            + (authority or {}).get("line_numbers", [])
        ))
        decompositions = list(dict.fromkeys(
            (full or {}).get("decompositions", [])
            + (fast or {}).get("decompositions", [])
            + (authority or {}).get("decompositions", [])
        ))
        surface_records[surface] = {
            "surface": surface,
            "line_numbers": line_numbers,
            "decompositions": decompositions,
            "line_count": len(line_numbers),
            "full_line_count": (full or {}).get("line_count", 0),
            "fast_line_count": len((fast or {}).get("line_numbers", [])),
            "authority_line_count": len(
                (authority or {}).get("line_numbers", [])
            ),
            "full_scope": full is not None,
            "fast_scope": fast is not None,
            "authority_scope": authority is not None,
            "scopes": [
                scope for scope, present in (
                    ("full_exact", full is not None),
                    ("legacy_fast", fast is not None),
                    ("fake_coarse_authority", authority is not None),
                ) if present
            ],
        }
    render_surfaces = sorted(surface_records)

    input_token_line_count = sum(
        len(TOKEN_RE.findall(row["surface"])) for row in records
    )
    unique_token_values = sorted({
        token
        for surface in full_surfaces
        for token in TOKEN_RE.findall(surface)
    })

    baseline = None
    mismatch_map = {}
    language_results = []
    fake_authority_results = []
    for language in LANGUAGES:
        structural, language_result = render_language(
            language, render_surfaces, surface_records, args.batch_size,
        )
        fake_mismatches = []
        fake_counts = collections.Counter()
        fake_category_counts = collections.defaultdict(collections.Counter)
        fake_source_counts = collections.defaultdict(collections.Counter)
        fake_transition_scope_counts = collections.defaultdict(
            collections.Counter
        )
        for authority_row in fake_authority_rows:
            fake_counts["rows"] += 1
            expected_structure = authority_row["expected"]
            observed_structure = structural.get(authority_row["surface"])
            matched = observed_structure == expected_structure
            state = "matched" if matched else "mismatched"
            fake_counts[state] += 1
            fake_category_counts[authority_row["coverage_category"]][state] += 1
            fake_source_counts[authority_row["authority_source"]][state] += 1
            if authority_row["transition_required"]:
                fake_counts["transition_rows"] += 1
                fake_counts[f"transition_{state}"] += 1
                fake_transition_scope_counts[
                    authority_row["transition_scope"]
                ][state] += 1
            if not matched:
                fake_mismatches.append({
                    "learner_line": authority_row["learner_line"],
                    "surface": authority_row["surface"],
                    "learner_decomposition": authority_row["learner_decomposition"],
                    "academic_decomposition": authority_row["academic_decomposition"],
                    "selected_decomposition": authority_row["selected_decomposition"],
                    "authority_source": authority_row["authority_source"],
                    "coverage_category": authority_row["coverage_category"],
                    "transition_required": authority_row["transition_required"],
                    "transition_scope": authority_row["transition_scope"],
                    "transition_category": authority_row["transition_category"],
                    "expected": structural_payload(expected_structure),
                    "observed": (
                        structural_payload(observed_structure)
                        if observed_structure is not None else None
                    ),
                })
        fake_authority_results.append({
            "language": language,
            "counts": dict(fake_counts),
            "coverage_categories": {
                key: dict(value)
                for key, value in sorted(fake_category_counts.items())
            },
            "authority_sources": {
                key: dict(value)
                for key, value in sorted(fake_source_counts.items())
            },
            "transition_scopes": {
                key: dict(value)
                for key, value in sorted(fake_transition_scope_counts.items())
            },
            "mismatches": fake_mismatches,
        })
        language_results.append(language_result)
        if baseline is None:
            baseline = structural
        else:
            for surface in render_surfaces:
                current = structural.get(surface)
                expected = baseline.get(surface)
                if current == expected:
                    continue
                mismatch = mismatch_map.setdefault(surface, {
                    "surface": surface,
                    "line_numbers": surface_records[surface]["line_numbers"],
                    "decompositions": surface_records[surface]["decompositions"],
                    "full_line_numbers": (
                        full_surface_records.get(surface, {}).get("line_numbers", [])
                    ),
                    "fast_line_numbers": (
                        fast_key_records.get(surface, {}).get("line_numbers", [])
                    ),
                    "full_exact_scope": surface_records[surface]["full_scope"],
                    "fast_subset": surface_records[surface]["fast_scope"],
                    "scopes": surface_records[surface]["scopes"],
                    "observed": {},
                })
                if "JA" not in mismatch["observed"]:
                    mismatch["observed"]["JA"] = structural_payload(expected) if expected else None
                mismatch["observed"][language] = structural_payload(current) if current else None
        del structural
        gc.collect()

    # Fill languages which matched JA for a surface that differed in another language.
    for surface, mismatch in mismatch_map.items():
        ja_payload = mismatch["observed"].get("JA")
        for language in LANGUAGES:
            mismatch["observed"].setdefault(language, ja_payload)

    mismatches = [mismatch_map[surface] for surface in sorted(mismatch_map)]
    token_mismatches = []
    for mismatch in mismatches:
        observed = mismatch["observed"]
        token_lists = {
            language: (payload or {}).get("tokens", [])
            for language, payload in observed.items()
        }
        maximum = max((len(rows) for rows in token_lists.values()), default=0)
        for index in range(maximum):
            rows = {
                language: (tokens[index] if index < len(tokens) else None)
                for language, tokens in token_lists.items()
            }
            serialized = {
                language: json.dumps(value, ensure_ascii=False, sort_keys=True)
                for language, value in rows.items()
            }
            if len(set(serialized.values())) > 1:
                token_mismatches.append({
                    "surface": mismatch["surface"],
                    "line_numbers": mismatch["line_numbers"],
                    "token_index": index,
                    "observed": rows,
                })

    gold_digest_at_end = sha256_file(args.gold.resolve())
    academic_digest_at_end = sha256_file(args.academic.resolve())
    head_at_end = git_text("rev-parse", "HEAD")
    tracked_at_end = tracked_status()
    app_inputs_at_end = app_input_fingerprints()
    all_runtime_assessed = all(
        row["rendered_unique_surfaces"] == len(render_surfaces)
        and row["issue_counts"]["runtime_errors"] == 0
        for row in language_results
    )
    issue_gate = all(
        all(row["issue_counts"][key] == 0 for key in (
            "runtime_errors", "visible_failures", "placeholder_residuals",
            "empty_rt", "empty_rb",
        ))
        for row in language_results
    )
    inputs_stable = {
        "gold": gold_digest_at_end == sha256_bytes(gold_raw),
        "academic": (
            academic_digest_at_end
            == fake_authority_identity["academic"]["sha256"]
        ),
        "head": head_at_end == head_at_start == args.expected_head,
        "tracked_worktree": (
            tracked_at_end == tracked_at_start
            if args.allow_stable_tracked_changes
            else not tracked_at_start and not tracked_at_end
        ),
        "app_inputs": app_inputs_at_end == app_inputs_at_start,
        "audit_script": sha256_file(Path(__file__).resolve()) == script_sha256,
        "authority_manifests": {
            str(path.relative_to(ROOT)): sha256_file(path)
            for path in authority_manifest_paths
        } == authority_manifest_hashes_at_start,
        "candidate_files": {
            str(path): sha256_file(path) for path in candidate_files
        } == candidate_file_hashes_at_start,
    }
    if phase532_parent_enabled:
        parent_manifest_at_end = (
            effective_manifest_path if phase532_enabled
            else FAKE_COARSE_MANIFEST.resolve()
        )
        phase532_reference_at_end = audit.load_phase532_reference_review(
            parent_manifest_at_end
        )
        inputs_stable["phase532_policy"] = (
            phase532_reference_at_end["identity"]
            == phase532_parent_reference_review["identity"]
            and phase532_carry.review_identity()
            == phase532_carry_review["review_identity"]
            if phase532_carry_review is not None
            else phase532_reference_at_end["identity"]
            == phase532_parent_reference_review["identity"]
        )
        if phase532_source_review is not None:
            phase532_source_at_end = phase532_builder.validate_frozen_closure(
                args.phase532_baseline_dir,
                args.phase532_candidate_dir,
                parent_manifest_at_end,
            )
            phase532_carry_at_end = (
                phase532_carry_builder.validate_frozen_closure(
                    args.phase532_baseline_dir,
                    args.phase532_candidate_dir,
                    parent_manifest_at_end,
                )
            )
            inputs_stable["phase532_frozen_closure"] = (
                phase532_source_at_end == phase532_source_review
                and phase532_carry_at_end == phase532_carry_review
            )
    if phase558_enabled:
        phase558_source_at_end = phase558_builder.validate_frozen_closure(
            args.phase532_candidate_dir,
            args.phase558_candidate_dir,
            args.phase558_ruby_disposition_ledger,
            args.phase558_japanese_guide,
            args.phase558_chinese_guide,
        )
        phase558_activation_at_end = phase558_activation.activation_report()
        inputs_stable["phase558_ruby_overlay"] = (
            phase558_source_at_end == phase558_source_review
            and phase558_activation_at_end == phase558_activation_report
            and phase558_policy.review_identity()
            == phase558_source_review["review_identity"]
        )
    fake_authority_all_assessed = all(
        row["counts"].get("rows", 0) == len(fake_authority_rows)
        for row in fake_authority_results
    )
    expected_transition_scope_rows = dict(
        fake_authority_identity["transition_manifests"]["active_scope_rows"]
    )
    expected_transition_rows = sum(expected_transition_scope_rows.values())
    fake_transition_gate = all(
        row["counts"].get("transition_rows", 0) == expected_transition_rows
        and row["counts"].get("transition_matched", 0)
        == expected_transition_rows
        and row["counts"].get("transition_mismatched", 0) == 0
        and {
            scope: counts.get("matched", 0)
            for scope, counts in row["transition_scopes"].items()
        } == expected_transition_scope_rows
        and all(
            counts.get("mismatched", 0) == 0
            for counts in row["transition_scopes"].values()
        )
        for row in fake_authority_results
    )
    fake_all_coarse_gate = all(
        row["counts"].get("mismatched", 0) == 0
        for row in fake_authority_results
    )
    width_gate = all(
        not row["ruby_length_audit"]["missing_width_characters"]
        and not row["ruby_length_audit"]["unknown_rt_classes"]
        and (
            row["ruby_length_audit"]["max_effective_width_ratio"] is None
            or row["ruby_length_audit"]["max_effective_width_ratio"] <= 2
        )
        for row in language_results
    )
    runtime_gate = (
        all_runtime_assessed
        and fake_authority_all_assessed
        and fake_transition_gate
        and (
            phase532_signature_report is None
            or phase532_signature_report["gate"]
        )
        and (
            phase558_signature_report is None
            or (
                phase558_signature_report["gate"]
                and phase558_signature_report["scope_guard_gate"]
                and phase558_signature_report["payload_variant_gate"]
                and phase558_signature_report["payload_gloss_gate"]
                and phase558_signature_report[
                    "deployed_snapshot_revalidated"
                ]
            )
        )
        and (fake_all_coarse_gate or not args.enforce_all_fake_coarse)
        and not mismatches
        and not token_mismatches
        and issue_gate
        and width_gate
        and all(inputs_stable.values())
    )
    ruby_overlay_adoption_authorized = not candidate_mode or phase558_enabled
    master_candidate_promotion_authorized = (
        not candidate_mode
        or (
            phase558_enabled
            and phase558_source_review["master_candidate_promotion_gate"]
        )
    )
    report = {
        "schema_version": 1,
        "algorithm": {
            "id": "full-master-three-language-runtime-v1",
            "batch_size": args.batch_size,
            "production_path": (
                "runtime + committed user corrections + overlay autofix; no regeneration"
            ),
            "line_surface": (
                "substring before first colon, slash decomposition markers removed; "
                "spaces, hyphens, punctuation, digits and case retained"
            ),
            "boundary_signature": (
                "exact visible R/L spans plus per-token projections; rt gloss ignored"
            ),
            "fast_scope_reproduction": (
                "audit_master_3lang_fast.py filter reproduced only as a labelled subset"
            ),
            "ruby_width": (
                "char_widths.json Arial16 sum with missing-char default 8; raw ratio, "
                "visible-codepoint ratio, and CSS-scaled maximum-line ratio"
            ),
        },
        "script_path": str(Path(__file__).resolve()),
        "script_sha256": script_sha256,
        "app": {
            "root": str(ROOT),
            "head_oid": head_at_start,
            "tracked_status_at_start": tracked_at_start,
            "tracked_status_at_end": tracked_at_end,
        },
        "gold": {
            "path": str(args.gold.resolve()),
            "bytes": len(gold_raw),
            "sha256": sha256_bytes(gold_raw),
            "lines": len(gold_text.splitlines()),
            "sha256_at_end": gold_digest_at_end,
        },
        "coarse_authority": {
            **fake_authority_identity,
            "academic_sha256_at_end": academic_digest_at_end,
            "authority_rows": len(fake_authority_rows),
            "all_rows_assessed_in_all_languages": fake_authority_all_assessed,
            "staged_transition_gate": fake_transition_gate,
            "staged_transition_expected_rows": {
                **expected_transition_scope_rows,
                "combined": expected_transition_rows,
                "historical_total_before_candidate_dispositions": 158,
            },
            "all_fake_coarse_gate": fake_all_coarse_gate,
            "all_fake_coarse_enforced": args.enforce_all_fake_coarse,
            "effective_ruby_width_within_2x": width_gate,
            "languages": fake_authority_results,
            **({
                "phase532_ruby_policy": (
                    phase532_parent_reference_review["identity"]
                ),
                "phase532_authority_carry_forward": (
                    phase532_carry.review_identity()
                ),
                "phase532_runtime_signature_gate": phase532_signature_report,
            } if phase532_parent_enabled else {}),
            **({
                "phase558_ruby_overlay": phase558_policy.review_identity(),
                "phase558_activation": phase558_activation_report,
                "phase558_frozen_closure": phase558_source_review,
                "phase558_runtime_signature_gate": phase558_signature_report,
            } if phase558_enabled else {}),
            "staging_note": (
                "Every currently fake-marked row remains in this line-keyed "
                "report. Historical transition manifests remain byte-frozen. "
                "In candidate mode, an exact fail-closed disposition ledger may "
                "move a retired marker transition to pending review; that makes "
                "the report non-promotable. The broader gloss/semantic queue "
                "remains unreviewed; --enforce-all-fake-coarse is not implied."
            ),
        },
        "accounting": {
            "input_lines": len(gold_text.splitlines()),
            "excluded_lines": sum(exclusions.values()),
            "exclusions_by_reason": dict(exclusions),
            "exclusion_line_numbers": dict(exclusion_rows),
            "runtime_candidate_lines": len(records),
            "runtime_unique_surfaces": len(full_surfaces),
            "duplicate_surface_line_excess": len(records) - len(full_surfaces),
            "duplicate_surface_groups": sum(
                row["line_count"] > 1 for row in full_surface_records.values()
            ),
            "input_token_occurrences_line_weighted": input_token_line_count,
            "unique_input_token_values": len(unique_token_values),
            "zero_token_candidate_lines": sum(
                "zero_esperanto_tokens" in row["features"] for row in records
            ),
            "feature_counts_line_weighted": dict(feature_counts),
            "fast_filter_rows": dict(fast_counts),
            "fast_filter_included_unique_surfaces": len(fast_surfaces),
            "render_union_unique_surfaces": len(render_surfaces),
            "fake_coarse_authority_unique_surfaces": len(authority_surfaces),
            "fake_coarse_authority_line_rows": len(fake_authority_rows),
            "legacy_fast_only_synthetic_surfaces": len(
                set(fast_surfaces) - set(full_surfaces)
            ),
            "all_candidate_lines_mapped_to_surface": len(records) + sum(exclusions.values()) == len(gold_text.splitlines()),
            "all_runtime_candidates_assessed_in_all_languages": all_runtime_assessed,
            "unevaluated_runtime_candidate_lines": (
                0 if all_runtime_assessed else len(records)
            ),
        },
        "three_language_boundary": {
            "render_union_mismatch_unique_surfaces": len(mismatches),
            "full_exact_mismatch_unique_surfaces": sum(
                row["full_exact_scope"] for row in mismatches
            ),
            "full_exact_mismatch_line_occurrences": sum(
                len(row["full_line_numbers"])
                for row in mismatches if row["full_exact_scope"]
            ),
            "legacy_fast_mismatch_unique_surfaces": sum(
                row["fast_subset"] for row in mismatches
            ),
            "legacy_fast_mismatch_line_occurrences": sum(
                len(row["fast_line_numbers"])
                for row in mismatches if row["fast_subset"]
            ),
            "token_mismatch_unique_contexts": len(token_mismatches),
            "full_exact_token_mismatch_unique_contexts": sum(
                mismatch_map[row["surface"]]["full_exact_scope"]
                for row in token_mismatches
            ),
            "legacy_fast_token_mismatch_unique_contexts": sum(
                mismatch_map[row["surface"]]["fast_subset"]
                for row in token_mismatches
            ),
            "all_mismatches": mismatches,
            "all_token_mismatches": token_mismatches,
        },
        "languages": language_results,
        "inputs_stable": inputs_stable,
        "candidate_audit": {
            "candidate_only": candidate_mode,
            "source_phase": (
                fake_authority_identity.get(
                    "candidate_transition_dispositions"
                ) or {}
            ).get("source_phase"),
            "runtime_gate": runtime_gate,
            "promotion_gate": (
                runtime_gate and master_candidate_promotion_authorized
            ),
            "master_candidate_promotion_authorized": (
                master_candidate_promotion_authorized
            ),
            "master_candidate_promotion_blockers": (
                phase558_source_review[
                    "master_candidate_promotion_blockers"
                ] if phase558_enabled else []
            ),
            "ruby_overlay_adoption_gate": (
                runtime_gate and ruby_overlay_adoption_authorized
            ),
            "retired_transition_pending_review": (
                fake_authority_identity["transition_manifests"]
                ["retired_pending_entries"]
            ),
            "phase532_policy_active": phase532_parent_enabled,
            "phase532_runtime_mode": (
                args.phase532_runtime_mode if phase532_parent_enabled else None
            ),
            "phase558_ruby_overlay_active": phase558_enabled,
            "phase558_runtime_mode": (
                args.phase558_runtime_mode if phase558_enabled else None
            ),
            "ruby_overlay_adoption_authorized_by_closed_phase558_sidecar": (
                candidate_mode and phase558_enabled
            ),
        },
        "complete": all_runtime_assessed and fake_authority_all_assessed,
        # Top-level gate describes the deployed Ruby runtime and its exact
        # sidecar. It intentionally does not promote the broader Phase 558
        # moving-master candidate; see candidate_audit.promotion_gate.
        "gate": runtime_gate and ruby_overlay_adoption_authorized,
        "interpretation": {
            "naked_fragments": (
                "Not automatically a failure: terminal grammar is intentionally "
                "literal. Lexical/nonterminal rows are separated as review candidates."
            ),
            "ruby_length": (
                "Raw text-width ratios above 2 remain review indicators; the "
                "CSS-scaled maximum-line ratio must stay at or below 2 and all "
                "width characters must be known. Width never changes boundaries."
            ),
            "candidate_promotion": (
                "The five-surface Ruby overlay may pass independently while "
                "the broader master candidate remains blocked by its disposition "
                "ledger. Top-level gate must not be read as full-master semantic "
                "promotion."
            ),
        },
    }
    return report


def main(argv=None):
    args = parse_args(argv)
    report = run(args)
    atomic_json_dump(args.report, report, indent=1)
    print(json.dumps({
        "report": str(args.report.resolve()),
        "gate": report["gate"],
        "candidate_audit": report["candidate_audit"],
        "accounting": report["accounting"],
        "three_language_boundary": {
            key: value for key, value in report["three_language_boundary"].items()
            if not key.startswith("all_")
        },
        "language_issue_counts": {
            row["language"]: row["issue_counts"] for row in report["languages"]
        },
        "coarse_authority": {
            "rows": report["coarse_authority"]["authority_rows"],
            "staged_transition_gate": report["coarse_authority"]["staged_transition_gate"],
            "all_fake_coarse_gate": report["coarse_authority"]["all_fake_coarse_gate"],
            "all_fake_coarse_enforced": report["coarse_authority"]["all_fake_coarse_enforced"],
            "languages": {
                row["language"]: row["counts"]
                for row in report["coarse_authority"]["languages"]
            },
        },
        "inputs_stable": report["inputs_stable"],
    }, ensure_ascii=False, indent=2), flush=True)
    if not report["gate"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
