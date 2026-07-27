# -*- coding: utf-8 -*-
"""Fail-closed audit of the two Kyoto HTML guides at b769 -> 7c04.

The audit is deliberately read-only.  It verifies:

* exact old/predecessor/current-main Git authorities and guide bytes;
* the closed +452/-101 guide-diff classification;
* the latest G8 translation checker in ``--require-zero`` mode;
* the read-only 168-file JA CSS scope, where nonzero raw mismatches are
  acceptable only when every item is a margin boundary skip and fixable=0;
* current JA/ZH/KO word-annotation boundary identity; and
* the exact raw-runtime rendering of ``ĵus``.

It never fetches, checks out, writes, fixes, commits, or pushes.
"""
from __future__ import annotations

import argparse
import collections
import difflib
import gc
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULT_LEDGER = HERE / "_latest_kyoto_guide_transition_7c04f97.json"

OLD_HEAD = "b769038ef15346a536ce93721d6f0f46849db0ea"
OLD_TREE = "47995a849c6f06dc536b533642ad6974ddd8586e"
NEW_HEAD = "7c04f97c51a7cecf88918d2abc2e6bf2f34601a6"
NEW_TREE = "52a92cafc2234eeea5b8d39a3ac0163f47e67462"
ACTIVE_HEAD = "d1642c276857c1fe400a6d597214ff7a923e7bd2"
ACTIVE_TREE = "6a202620a7de26f9b88b022c76a084bbff7b578c"
APP_BASELINE_HEAD = "3f338920f59efd80333616af6192e0f099c3d07c"

GUIDE_FILE_PINS = {
    "old": {
        "ja": (
            "1EEAA8B4E2C4518F72ACCDD89AA0FAB427DC012BC76429E25607B2BAB0CB9FA0",
            "c6211e2177640a19728ec97964b66a6184629b6f",
            115234,
            1653,
        ),
        "zh": (
            "4FDE80DD5B1B6BB822A5D7CF9BAF5FAA23AC7FE4C129F3E7BD128DE3DEBF8DCF",
            "7cf090405665231955b09481b4fee4d8d6d03391",
            106413,
            1738,
        ),
    },
    "new": {
        "ja": (
            "B8F21605E019A394560A6E4ED5238FE4BEDE7B2A949A0CBC6927189ADADFB965",
            "19bf6fd0457023f41951e4e4767a9e96f1a19575",
            131181,
            1835,
        ),
        "zh": (
            "A3AF2F18004A63A2C6ECB438B9ABBABF62A9B40D15494FC6B6FC0CADA7ECEA46",
            "148ebe9a0209f84af6eac2f7c27618df80f24087",
            118657,
            1907,
        ),
    },
}

APP_ARTIFACT_SHA256 = {
    "boundary_builder": (
        "71DBD617083DA3F63C26BCECD8259947AD28A62C4EDDF75ED49EEA21FC549B72"
    ),
    "boundary_manifest": (
        "17CF4AFEA6CCDE674DAB4AD1BCB531AB61FD7DA525AADD13BF5504D819050246"
    ),
    "width_policy": (
        "F3AF9A7084807ED6B5FD34C8970375E7820C74AF4179EFB95E3808847B76370E"
    ),
    "char_width": (
        "AC009C26AF1D7FAE05E8969D86042B5BAFF5F482B226C575E1CEF8D27AEA2C7B"
    ),
}

LANGUAGE_ARTIFACT_PINS = {
    "JA": {
        "word_anno": (
            "D298820FF370A7DFA59B4A0E83BFBED3BACB768068C9A45FDE48F5A8F4220AB4"
        ),
        "payload": (
            "591C7EA887504B9248F3406A971CAB8CC6EB3F4B06AAAFA824ED4ECF881FF40E"
        ),
        "runtime": (
            "61E1F0A9AE3CD045E3908295E6E072DE9449B5791E2BB1DF38D9EB4D10D385CA"
        ),
        "rendered": ' <ruby>ĵus<rt class="XXS_S">たっ<br>た今</rt></ruby> ',
        "effective_width_ratio": 0.469150872648,
    },
    "ZH": {
        "word_anno": (
            "EEFF53D0EA7F30CE60C6B82060A22B1E72EE9E4612770E23691D4235AE4800AE"
        ),
        "payload": (
            "277278C0C7A46AB1FCC93CDA54165EF4A235826EBAD76EDC379691169B95B6F1"
        ),
        "runtime": (
            "B0E7437961168203815BC5DD96FD624068AC9612FA054263C8A33349719C4E12"
        ),
        "rendered": ' <ruby>ĵus<rt class="M_M">刚才</rt></ruby> ',
        "effective_width_ratio": 0.781918121079,
    },
    "KO": {
        "word_anno": (
            "E0EEC71CE3728F19CA4D3AB5569C8A4DA59C45AE07CE8776FA0075B2360AB421"
        ),
        "payload": (
            "C0A83D84EF6AD98FA8F9FC4FBA18C57A3361992700E5CF54566C05FCEFDE30AC"
        ),
        "runtime": (
            "C29CD09925EF9C49F4AD6506B5FA83119E7536BEEF4C09BCA3AD9891F0E0AA7A"
        ),
        "rendered": ' <ruby>ĵus<rt class="L_L">방금</rt></ruby> ',
        "effective_width_ratio": 0.863530847338,
    },
}

JA_GUIDE = (
    "esperanto_html_redaktado/"
    "エスペラントルビHTML修正ガイド260328.txt"
)
ZH_GUIDE = (
    "esperanto_html_redaktado/"
    "世界语HTML修正指南_中文注释版.txt"
)
GUIDE_PATHS = (JA_GUIDE, ZH_GUIDE)
TRANSLATION_CHECKER = "esperanto_html_redaktado/translation_marking_checker.py"
CSS_VERIFIER = "esperanto_html_redaktado/ruby_css_verifier.py"
WIDTH_JSON = (
    "esperanto_html_redaktado/"
    "Unicode_BMP全范围文字幅(宽)_Arial16.json"
)
CONTENT_DIRS = ("lernolibroj", "legajxoj", "revuoj", "rondolegado")
KO_CSS_EXCLUSION = (
    "rondolegado/2026-03/"
    "rondolegada_materialoj_202603_enhavoj_KO.html"
)
RUBY_PAYLOAD_NAME = "置換リスト_ルビ.json"
RUNTIME_NAME = "esp_text_replacement_module.py"
WORD_ANNO_NAME = "word_anno.json"
RUNTIME_FORMAT = "HTML格式_Ruby文字_大小调整"
JUS = "ĵus"
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest().upper()

HUNK_CATEGORIES = {
    JA_GUIDE: (
        "ruby_semantic",
        "ruby_semantic",
        "provenance_pin",
        "provenance_pin",
        "provenance_pin",
        "g8_layout",
        "g8_layout",
        "stale_appendix_removal",
    ),
    ZH_GUIDE: (
        "provenance_pin",
        "provenance_pin",
        "g8_layout",
        "g8_layout",
        "g8_layout",
        "stale_appendix_removal",
    ),
}

GUIDE_ANCHORS = {
    JA_GUIDE: (
        "  ĵus     たった<br>今 / たっ<br>た今 → たっ<br>た今",
        "G8. 対訳レイアウト・訳有無表示ゲート（2026-07-25 制定）",
        "    同一行対応の学術版（粗い注釈ruby authority）は",
        "CSSクラスは「rt側のピクセル幅 ÷ rb側のピクセル幅」の比率（ratio）で",
        "【原則】複合語（多語根語）は語根単位に分解し、各語根を独立rubyとする。",
    ),
    ZH_GUIDE: (
        "G8. 对译版式・译文有无标示门控（2026-07-25 制定）",
        "    同行对应的学术版（粗粒度注音ruby权威）为",
        "CSS类由「rt侧像素宽度 ÷ rb侧像素宽度」的比率（ratio）决定。",
        "【原则】复合词（多词根词）按词根单位分解，各词根作独立ruby。",
    ),
}

CSS_CLASS_SCALE = {
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
RUNTIME_RUBY_RE = re.compile(
    r'^\s*<ruby>(?P<rb>[^<]+)<rt class="(?P<class>[A-Z_]+)">'
    r"(?P<rt>.*?)</rt></ruby>\s*$",
    re.DOTALL,
)


class GuideTransitionError(ValueError):
    """A fixed transition invariant was not satisfied."""


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def stable_json_sha256(value) -> str:
    raw = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("ascii")
    return sha256_bytes(raw)


def line_slice_sha256(lines: list[str]) -> str:
    return sha256_bytes("\n".join(lines).encode("utf-8"))


def _git(root: Path, *arguments: str, binary: bool = False):
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise GuideTransitionError(
            f"git {' '.join(arguments)} failed for {root}: {message}"
        )
    if binary:
        return result.stdout
    return result.stdout.decode("utf-8", errors="strict").strip()


def _git_is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "merge-base",
            "--is-ancestor",
            ancestor,
            descendant,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    message = result.stderr.decode("utf-8", errors="replace").strip()
    raise GuideTransitionError(
        "git merge-base --is-ancestor failed for "
        f"{root}: {message}"
    )


def app_lineage_gate(app_root: Path) -> dict:
    """Require an R73 descendant without serializing the moving current HEAD.

    The deployed artifact and boundary hashes below pin all semantically
    relevant app inputs.  Recording ``HEAD`` itself made the committed review
    stale as soon as the review was committed.  We still reject an unrelated
    history, but serialize only the immutable baseline and the verified
    ancestor relation so the ledger is identical immediately before and after
    a descendant commit.
    """
    current_head = _git(app_root, "rev-parse", "HEAD")
    if not _git_is_ancestor(
        app_root, APP_BASELINE_HEAD, current_head,
    ):
        raise GuideTransitionError(
            "app checkout is not a descendant of the sealed R73 baseline: "
            f"baseline={APP_BASELINE_HEAD}, current={current_head}"
        )
    return {
        "app_baseline_head_oid": APP_BASELINE_HEAD,
        "baseline_is_ancestor": True,
    }


def clean_git_state(root: Path) -> dict:
    root = root.resolve()
    if not root.is_dir():
        raise GuideTransitionError(f"checkout is not a directory: {root}")
    top = Path(_git(root, "rev-parse", "--show-toplevel")).resolve()
    if top != root:
        raise GuideTransitionError(
            f"checkout must be a Git toplevel: supplied={root}, actual={top}"
        )
    status = _git(
        root,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
        binary=True,
    )
    entries = len([item for item in status.split(b"\0") if item])
    if entries:
        raise GuideTransitionError(
            f"checkout must be clean: {root} has {entries} status entries"
        )
    return {
        "head_oid": _git(root, "rev-parse", "HEAD"),
        "tree_oid": _git(root, "rev-parse", "HEAD^{tree}"),
        "status_entries": entries,
        "status_sha256": sha256_bytes(status),
    }


def guide_fingerprint(path: Path) -> dict:
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="strict")
    blob_header = f"blob {len(raw)}\0".encode("ascii")
    return {
        "sha256": sha256_bytes(raw),
        "git_blob_sha1": hashlib.sha1(blob_header + raw).hexdigest(),
        "bytes": len(raw),
        "lines": len(text.splitlines()),
        "lf": raw.count(b"\n"),
        "crlf": raw.count(b"\r\n"),
        "bom": raw.startswith(b"\xef\xbb\xbf"),
        "final_lf": raw.endswith(b"\n"),
    }


def guide_set(root: Path) -> dict:
    files = {
        relative: guide_fingerprint(root / relative)
        for relative in GUIDE_PATHS
    }
    rows = [
        [
            relative,
            files[relative]["sha256"],
            files[relative]["bytes"],
            files[relative]["lines"],
        ]
        for relative in GUIDE_PATHS
    ]
    return {
        "files": files,
        "guide_set_sha256": stable_json_sha256(rows),
    }


def diff_hunks(old_text: str, new_text: str, relative: str) -> list[dict]:
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    operations = [
        item
        for item in difflib.SequenceMatcher(
            None, old_lines, new_lines, autojunk=False
        ).get_opcodes()
        if item[0] != "equal"
    ]
    categories = HUNK_CATEGORIES[relative]
    if len(operations) != len(categories):
        raise GuideTransitionError(
            f"{relative}: expected {len(categories)} diff hunks, "
            f"observed {len(operations)}"
        )
    rows = []
    for category, (tag, old_start, old_end, new_start, new_end) in zip(
        categories, operations
    ):
        rows.append(
            {
                "category": category,
                "tag": tag,
                "old_start_zero": old_start,
                "old_count": old_end - old_start,
                "new_start_zero": new_start,
                "new_count": new_end - new_start,
                "old_lines_sha256": line_slice_sha256(
                    old_lines[old_start:old_end]
                ),
                "new_lines_sha256": line_slice_sha256(
                    new_lines[new_start:new_end]
                ),
            }
        )
    return rows


def classify_guide_diff(old_root: Path, new_root: Path) -> dict:
    hunks = {}
    by_guide = {}
    categories = collections.defaultdict(
        lambda: {"insertions": 0, "deletions": 0, "hunks": 0}
    )
    for relative in GUIDE_PATHS:
        old_text = (old_root / relative).read_text(encoding="utf-8")
        new_text = (new_root / relative).read_text(encoding="utf-8")
        rows = diff_hunks(old_text, new_text, relative)
        hunks[relative] = rows
        additions = sum(row["new_count"] for row in rows)
        deletions = sum(row["old_count"] for row in rows)
        by_guide[relative] = {
            "insertions": additions,
            "deletions": deletions,
            "hunks": len(rows),
        }
        for row in rows:
            bucket = categories[row["category"]]
            bucket["insertions"] += row["new_count"]
            bucket["deletions"] += row["old_count"]
            bucket["hunks"] += 1
    return {
        "totals": {
            "insertions": sum(row["insertions"] for row in by_guide.values()),
            "deletions": sum(row["deletions"] for row in by_guide.values()),
            "hunks": sum(row["hunks"] for row in by_guide.values()),
        },
        "by_guide": by_guide,
        "by_category": dict(sorted(categories.items())),
        "hunks": hunks,
    }


def verify_guide_anchors(new_root: Path) -> dict:
    identities = {}
    for relative, anchors in GUIDE_ANCHORS.items():
        text = (new_root / relative).read_text(encoding="utf-8")
        for anchor in anchors:
            count = text.count(anchor)
            if count != 1:
                raise GuideTransitionError(
                    f"{relative}: authority anchor count is {count}, "
                    f"expected 1: {anchor!r}"
                )
        identities[relative] = stable_json_sha256(list(anchors))
    return {
        "anchor_set_sha256": identities,
        "ja_jus_canonical_break": "たっ<br>た今",
        "ruby_track": "coarse",
        "width_role": "CSS scale and rt line breaks only",
        "width_changes_root_boundaries": False,
        "effective_display_width_limit": 2.0,
    }


def parse_translation_report(output: str) -> dict:
    patterns = {
        "content_html_files": r"検査対象: 本文HTML\s+(\d+)\s+件",
        "ruby_with_ja_translation": r"ルビ\+和訳\s+(\d+)",
        "ruby_only": r"ルビのみ\s+(\d+)",
        "korean_translation": r"韓国語版\s+(\d+)",
        "zero_ruby_with_ja_translation": r"ルビ無し\+和訳\s+(\d+)",
        "title_mismatches": r"A\. title の表記ずれ\s*:\s*(\d+)\s+件",
        "index_badge_mismatches": r"B\. 一覧バッジのずれ\s*:\s*(\d+)\s+件",
        "long_translation_blocks": r"C\. 3文以上の塊\s*:\s*(\d+)\s+件",
        "missing_badge_css": r"D\. バッジCSSの欠落\s*:\s*(\d+)\s+件",
        "violations": r"違反合計:\s*(\d+)\s+件",
    }
    parsed = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, output)
        if match is None:
            raise GuideTransitionError(
                f"translation checker output lacks {key}: {output!r}"
            )
        parsed[key] = int(match.group(1))
    return parsed


def translation_gate(old_root: Path, new_root: Path, active_root: Path) -> dict:
    old_path = old_root / TRANSLATION_CHECKER
    new_path = new_root / TRANSLATION_CHECKER
    active_path = active_root / TRANSLATION_CHECKER
    if old_path.exists():
        raise GuideTransitionError(
            "translation checker unexpectedly exists in old authority"
        )
    new_fingerprint = guide_fingerprint(new_path)
    active_fingerprint = guide_fingerprint(active_path)
    if new_path.read_bytes() != active_path.read_bytes():
        raise GuideTransitionError(
            "active translation checker differs from latest authority"
        )
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [sys.executable, str(new_path), "--require-zero"],
        cwd=new_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
        check=False,
    )
    stdout = result.stdout.decode("utf-8", errors="strict")
    stderr = result.stderr.decode("utf-8", errors="strict")
    if result.returncode:
        raise GuideTransitionError(
            "translation checker --require-zero failed: "
            f"exit={result.returncode}, stderr={stderr!r}, stdout={stdout!r}"
        )
    if stderr.strip():
        raise GuideTransitionError(
            f"translation checker emitted stderr: {stderr!r}"
        )
    return {
        "old_exists": False,
        "new": new_fingerprint,
        "active": active_fingerprint,
        "command": [
            "python",
            TRANSLATION_CHECKER,
            "--require-zero",
        ],
        "exit_code": result.returncode,
        "report": parse_translation_report(stdout),
    }


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GuideTransitionError(f"cannot import module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def css_scope_paths(root: Path) -> tuple[list[Path], list[str]]:
    all_paths = []
    for directory in CONTENT_DIRS:
        all_paths.extend(
            sorted(
                path
                for path in (root / directory).rglob("*")
                if path.is_file() and path.suffix.lower() in {".html", ".htm"}
            )
        )
    relative = [path.relative_to(root).as_posix() for path in all_paths]
    if relative.count(KO_CSS_EXCLUSION) != 1:
        raise GuideTransitionError(
            "CSS scope must contain exactly the reviewed KO companion exclusion"
        )
    selected = [
        path
        for path in all_paths
        if path.relative_to(root).as_posix() != KO_CSS_EXCLUSION
    ]
    return selected, relative


def css_margin_gate(new_root: Path, active_root: Path) -> dict:
    verifier_path = new_root / CSS_VERIFIER
    active_verifier = active_root / CSS_VERIFIER
    width_path = new_root / WIDTH_JSON
    active_width = active_root / WIDTH_JSON
    if verifier_path.read_bytes() != active_verifier.read_bytes():
        raise GuideTransitionError("active CSS verifier differs from latest")
    if width_path.read_bytes() != active_width.read_bytes():
        raise GuideTransitionError("active width table differs from latest")

    verifier = _load_module(verifier_path, "latest_kyoto_ruby_css_verifier")
    width_data = verifier._load_width_data()
    margin = 0.05
    paths, all_relative = css_scope_paths(new_root)
    counts = collections.Counter()
    per_file = []
    pair_counts = collections.Counter()
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="strict")
        raw = verifier.count_raw_ruby_opens(text)
        rubies = verifier.parse_rubies(text)
        unparsed = raw - len(rubies)
        file_counts = collections.Counter()
        counts["files"] += 1
        counts["raw_ruby"] += raw
        counts["parsed_ruby"] += len(rubies)
        counts["unparsed"] += unparsed
        for (
            _match,
            rb,
            actual_css,
            rt_raw,
            rt_clean,
            needs_normalization,
        ) in rubies:
            expected_css, ratio = verifier.calc_css_class(
                rb, rt_clean, width_data
            )
            actual_class_rt = verifier.build_correct_rt(
                rt_clean, actual_css, width_data
            )
            class_mismatch = actual_css != expected_css
            break_mismatch = rt_raw != actual_class_rt
            break_only = not class_mismatch and break_mismatch
            if not (class_mismatch or needs_normalization or break_mismatch):
                continue
            distance = verifier.nearest_threshold_distance(ratio)
            gap = verifier.css_class_distance(actual_css, expected_css)
            boundary = (
                class_mismatch
                and not needs_normalization
                and distance < margin
                and gap <= 1
            )
            fixable = not boundary or break_mismatch
            for bucket, value in (
                ("mismatches", True),
                ("class_mismatches", class_mismatch),
                ("break_mismatches", break_mismatch),
                ("break_only_mismatches", break_only),
                ("smart_quote_mismatches", needs_normalization),
                ("boundary_skips", boundary),
                ("fixable", fixable),
            ):
                if value:
                    counts[bucket] += 1
                    file_counts[bucket] += 1
            pair_counts[
                (
                    rb,
                    rt_clean,
                    actual_css,
                    expected_css,
                    format(ratio, ".12g"),
                    format(distance, ".12g"),
                )
            ] += 1
        if file_counts["mismatches"]:
            counts["files_with_mismatches"] += 1
        per_file.append(
            [
                path.relative_to(new_root).as_posix(),
                raw,
                len(rubies),
                unparsed,
                file_counts["mismatches"],
                file_counts["boundary_skips"],
                file_counts["fixable"],
            ]
        )

    pair_rows = [
        [*key, count] for key, count in sorted(pair_counts.items())
    ]
    selected_relative = [
        path.relative_to(new_root).as_posix() for path in paths
    ]
    summary = {
        key: counts[key]
        for key in (
            "files",
            "raw_ruby",
            "parsed_ruby",
            "unparsed",
            "mismatches",
            "class_mismatches",
            "break_mismatches",
            "break_only_mismatches",
            "smart_quote_mismatches",
            "boundary_skips",
            "fixable",
            "files_with_mismatches",
        )
    }
    pass_gate = (
        summary["unparsed"] == 0
        and summary["fixable"] == 0
        and summary["mismatches"] == summary["boundary_skips"]
        and summary["break_mismatches"] == 0
        and summary["smart_quote_mismatches"] == 0
    )
    if not pass_gate:
        raise GuideTransitionError(
            f"CSS read-only margin classification failed: {summary!r}"
        )
    return {
        "verifier": guide_fingerprint(verifier_path),
        "width_table": guide_fingerprint(width_path),
        "margin": margin,
        "content_html_files_before_exclusion": len(all_relative),
        "excluded_paths": [KO_CSS_EXCLUSION],
        "selected_path_list_sha256": stable_json_sha256(selected_relative),
        "per_file_rows_sha256": stable_json_sha256(per_file),
        "boundary_pair_rows": len(pair_rows),
        "boundary_pair_rows_sha256": stable_json_sha256(pair_rows),
        "summary": summary,
        "interpretation": {
            "raw_cli_mismatches_are_not_fixable_count": True,
            "accepted_only_as_boundary_skips": True,
            "auto_fix_authorized": False,
            "corpus_edit_authorized": False,
        },
        "pass": pass_gate,
    }


def _extract_payload_lists(payload: dict):
    global_rules = next(
        value
        for key, value in payload.items()
        if "replacements_final_list" in key
    )
    local_rules = next(
        value for key, value in payload.items() if "localized_string" in key
    )
    two_char_rules = next(
        value
        for key, value in payload.items()
        if "replacements_list_for_2char" in key
    )
    return local_rules, global_rules, two_char_rules


def _runtime_css_scales(runtime_path: Path) -> dict[str, float]:
    scales = {
        name: float(value)
        for name, value in CSS_SCALE_RE.findall(
            runtime_path.read_text(encoding="utf-8")
        )
    }
    if scales != CSS_CLASS_SCALE:
        raise GuideTransitionError(
            f"deployed CSS scale mapping drift: {runtime_path}: {scales!r}"
        )
    return scales


def _runtime_width_probe(
    rendered: str,
    runtime_path: Path,
    char_width_path: Path,
) -> dict:
    match = RUNTIME_RUBY_RE.fullmatch(rendered)
    if match is None:
        raise GuideTransitionError(
            f"ĵus runtime output is not one exact ruby: {rendered!r}"
        )
    widths = json.loads(char_width_path.read_text(encoding="utf-8"))
    rb = match.group("rb")
    rt_lines = match.group("rt").split("<br>")
    characters = set(rb + "".join(rt_lines))
    missing = sorted(characters - set(widths))

    def width(text: str) -> float:
        return sum(float(widths.get(character, 8)) for character in text)

    rb_width = width(rb)
    line_widths = [width(line) for line in rt_lines]
    css_class = match.group("class")
    scale = _runtime_css_scales(runtime_path)[css_class]
    effective = max(line_widths) * scale / rb_width
    return {
        "rt": match.group("rt"),
        "class": css_class,
        "boundary_signature": [["ĵus", "R"]],
        "effective_max_line_width_ratio": round(effective, 12),
        "missing_width_characters": missing,
        "within_2x": not missing and effective <= 2.0,
    }


def _word_anno_boundary_gate(app_root: Path) -> dict:
    builder_path = HERE / "build_word_anno_boundary_manifest.py"
    manifest_path = HERE / "_word_anno_boundary_scope_manifest.json"
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    builder = _load_module(builder_path, "latest_guide_word_anno_boundary")
    maps = {}
    fingerprints = {}
    for language in ("ja", "zh", "ko"):
        path = (
            app_root
            / f"Esperanto-Kanji-Ruby-{language.upper()}"
            / "app_data"
            / WORD_ANNO_NAME
        )
        maps[language] = json.loads(path.read_text(encoding="utf-8"))
        fingerprints[language] = guide_fingerprint(path)
    actual = builder.build(maps)
    committed = json.loads(manifest_path.read_text(encoding="utf-8"))
    if actual != committed:
        raise GuideTransitionError(
            "current app word_anno boundary authority differs from manifest"
        )
    jus_entries = {language: maps[language].get(JUS) for language in maps}
    if any(
        entry is None
        or len(entry) != 1
        or entry[0][0] != JUS
        for entry in jus_entries.values()
    ):
        raise GuideTransitionError(
            f"ĵus is not one shared coarse Ruby root: {jus_entries!r}"
        )
    return {
        "builder": guide_fingerprint(builder_path),
        "manifest": guide_fingerprint(manifest_path),
        "word_anno": fingerprints,
        "expected_key_counts": actual["expected_key_counts"],
        "authority_keys": actual["authority_keys"],
        "authority_sha256": actual["authority_sha256"],
        "missing_by_language": {
            language: len(rows)
            for language, rows in actual[
                "expected_missing_by_language"
            ].items()
        },
        "jus_boundary_signature": [["ĵus", "R"]],
        "all_observed_cross_language_boundaries_identical": True,
    }


def runtime_gate(app_root: Path) -> dict:
    lineage = app_lineage_gate(app_root)
    languages = {}
    shared_char_width_fingerprint = None
    for language in ("JA", "ZH", "KO"):
        app_dir = app_root / f"Esperanto-Kanji-Ruby-{language}"
        data_dir = app_dir / "app_data"
        payload_path = data_dir / RUBY_PAYLOAD_NAME
        runtime_path = app_dir / RUNTIME_NAME
        char_width_path = data_dir / "char_widths.json"
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        local_rules, global_rules, two_char_rules = _extract_payload_lists(
            payload
        )
        runtime = _load_module(
            runtime_path, f"latest_guide_runtime_{language.lower()}"
        )
        skip = runtime.import_placeholders(
            str(data_dir / "placeholders_skip.txt")
        )
        local_capture = runtime.import_placeholders(
            str(data_dir / "placeholders_localcapture.txt")
        )
        rendered = runtime.orchestrate_comprehensive_esperanto_text_replacement(
            f" {JUS} ",
            skip,
            local_rules,
            local_capture,
            global_rules,
            two_char_rules,
            RUNTIME_FORMAT,
        )
        languages[language] = {
            "payload": guide_fingerprint(payload_path),
            "runtime": guide_fingerprint(runtime_path),
            "rendered": rendered,
            "probe": _runtime_width_probe(
                rendered, runtime_path, char_width_path
            ),
        }
        current_width_fingerprint = guide_fingerprint(char_width_path)
        if shared_char_width_fingerprint is None:
            shared_char_width_fingerprint = current_width_fingerprint
        elif current_width_fingerprint != shared_char_width_fingerprint:
            raise GuideTransitionError(
                "JA/ZH/KO deployed character-width tables are not identical"
            )
        del payload, local_rules, global_rules, two_char_rules, runtime
        gc.collect()

    signatures = {
        tuple(tuple(item) for item in row["probe"]["boundary_signature"])
        for row in languages.values()
    }
    if signatures != {(("ĵus", "R"),)}:
        raise GuideTransitionError(
            f"ĵus trilingual R/L boundary drift: {signatures!r}"
        )
    width_policy_path = HERE / "audit_master_3lang_full_snapshot.py"
    width_policy_text = width_policy_path.read_text(encoding="utf-8")
    for anchor in (
        'row["ruby_length_audit"]["max_effective_width_ratio"] <= 2',
        "Width never changes boundaries.",
    ):
        if width_policy_text.count(anchor) != 1:
            raise GuideTransitionError(
                f"width policy anchor missing or duplicated: {anchor!r}"
            )
    return {
        **lineage,
        "boundary_authority": _word_anno_boundary_gate(app_root),
        "width_policy_source": guide_fingerprint(width_policy_path),
        "shared_char_width_table": shared_char_width_fingerprint,
        "languages": languages,
        "policy": {
            "ruby_track": "coarse",
            "trilingual_boundary_identity_required": True,
            "effective_css_scaled_max_line_width_limit": 2.0,
            "width_changes_root_boundaries": False,
        },
    }


def build_review(
    old_root: Path,
    new_root: Path,
    active_root: Path,
    app_root: Path = ROOT,
) -> dict:
    states = {
        "old": clean_git_state(old_root),
        "new": clean_git_state(new_root),
        "active": clean_git_state(active_root),
    }
    guides = {
        "old": guide_set(old_root),
        "new": guide_set(new_root),
        "active": guide_set(active_root),
    }
    for relative in GUIDE_PATHS:
        if (new_root / relative).read_bytes() != (
            active_root / relative
        ).read_bytes():
            raise GuideTransitionError(
                f"active guide is not byte-identical to latest: {relative}"
            )
    review = {
        "schema_version": 1,
        "description": (
            "Read-only fail-closed audit of the two Kyoto HTML guides "
            "from b769038 to immutable predecessor 7c04f97 and current "
            "remote main d1642c2."
        ),
        "source": states,
        "guides": guides,
        "diff": classify_guide_diff(old_root, new_root),
        "guide_policy": verify_guide_anchors(new_root),
        "translation_marking": translation_gate(
            old_root, new_root, active_root
        ),
        "ruby_css_margin": css_margin_gate(new_root, active_root),
        "app_runtime": runtime_gate(app_root),
        "scope": {
            "corpus_or_guide_payload_edits": 0,
            "app_payload_edits": 0,
            "auto_fix_runs": 0,
            "commit_or_push": False,
        },
    }
    review["gate"] = {
        "exact_git_authorities": True,
        "active_guides_byte_identical_to_latest": True,
        "closed_diff_classification": True,
        "translation_require_zero": (
            review["translation_marking"]["report"]["violations"] == 0
        ),
        "css_fixable_zero": (
            review["ruby_css_margin"]["summary"]["fixable"] == 0
        ),
        "trilingual_boundaries_identical": review["app_runtime"][
            "boundary_authority"
        ]["all_observed_cross_language_boundaries_identical"],
        "jus_exact_runtime": all(
            row["probe"]["boundary_signature"] == [["ĵus", "R"]]
            for row in review["app_runtime"]["languages"].values()
        ),
        "pass": True,
    }
    return review


def _require_equal(label: str, actual, expected) -> None:
    if actual != expected:
        raise GuideTransitionError(
            f"{label} drift: expected={expected!r}, actual={actual!r}"
        )


def validate_authority(ledger: dict) -> None:
    """Reject a self-authorizing or weakened ledger before comparison."""
    _require_equal("schema_version", ledger.get("schema_version"), 1)
    _require_equal(
        "source pins",
        {
            key: (
                ledger["source"][key]["head_oid"],
                ledger["source"][key]["tree_oid"],
                ledger["source"][key]["status_entries"],
            )
            for key in ("old", "new", "active")
        },
        {
            "old": (OLD_HEAD, OLD_TREE, 0),
            "new": (NEW_HEAD, NEW_TREE, 0),
            "active": (ACTIVE_HEAD, ACTIVE_TREE, 0),
        },
    )
    _require_equal(
        "guide set pins",
        {
            key: ledger["guides"][key]["guide_set_sha256"]
            for key in ("old", "new", "active")
        },
        {
            "old": "3C552BB2E13407688DCB16C2211378293B4457B914A140C7710AED461AAF6D95",
            "new": "01AF3A4CEF661820BB8AFECFCA2E4E53CCECF2A1BAA3B9A2AB30DFD7D7BA6249",
            "active": "01AF3A4CEF661820BB8AFECFCA2E4E53CCECF2A1BAA3B9A2AB30DFD7D7BA6249",
        },
    )
    observed_guide_files = {}
    for checkout in ("old", "new", "active"):
        authority = "new" if checkout == "active" else checkout
        observed_guide_files[checkout] = {}
        for language, relative in (("ja", JA_GUIDE), ("zh", ZH_GUIDE)):
            row = ledger["guides"][checkout]["files"][relative]
            observed_guide_files[checkout][language] = (
                row["sha256"],
                row["git_blob_sha1"],
                row["bytes"],
                row["lines"],
                row["lf"],
                row["crlf"],
                row["bom"],
                row["final_lf"],
            )
            expected = GUIDE_FILE_PINS[authority][language]
            expected = (*expected, expected[3], 0, False, True)
            _require_equal(
                f"{checkout}/{language} guide file pin",
                observed_guide_files[checkout][language],
                expected,
            )
    _require_equal(
        "guide diff totals",
        ledger["diff"]["totals"],
        {"insertions": 452, "deletions": 101, "hunks": 14},
    )
    _require_equal(
        "guide diff category totals",
        ledger["diff"]["by_category"],
        {
            "g8_layout": {
                "insertions": 436,
                "deletions": 13,
                "hunks": 5,
            },
            "provenance_pin": {
                "insertions": 11,
                "deletions": 8,
                "hunks": 5,
            },
            "ruby_semantic": {
                "insertions": 5,
                "deletions": 1,
                "hunks": 2,
            },
            "stale_appendix_removal": {
                "insertions": 0,
                "deletions": 79,
                "hunks": 2,
            },
        },
    )
    _require_equal(
        "hunk category assignment",
        {
            relative: tuple(row["category"] for row in rows)
            for relative, rows in ledger["diff"]["hunks"].items()
        },
        HUNK_CATEGORIES,
    )
    _require_equal(
        "translation report",
        ledger["translation_marking"]["report"],
        {
            "content_html_files": 152,
            "ruby_with_ja_translation": 119,
            "ruby_only": 3,
            "korean_translation": 1,
            "zero_ruby_with_ja_translation": 29,
            "title_mismatches": 0,
            "index_badge_mismatches": 0,
            "long_translation_blocks": 0,
            "missing_badge_css": 0,
            "violations": 0,
        },
    )
    _require_equal(
        "translation checker sha256",
        ledger["translation_marking"]["new"]["sha256"],
        "0CE5A8F8283DABCCA257EF5A5798A77BE0B929A9FC0FA8211843BB686E51DBF0",
    )
    _require_equal(
        "CSS summary",
        ledger["ruby_css_margin"]["summary"],
        {
            "files": 168,
            "raw_ruby": 333941,
            "parsed_ruby": 333941,
            "unparsed": 0,
            "mismatches": 551,
            "class_mismatches": 551,
            "break_mismatches": 0,
            "break_only_mismatches": 0,
            "smart_quote_mismatches": 0,
            "boundary_skips": 551,
            "fixable": 0,
            "files_with_mismatches": 70,
        },
    )
    _require_equal(
        "CSS verifier/width pins",
        (
            ledger["ruby_css_margin"]["verifier"]["sha256"],
            ledger["ruby_css_margin"]["width_table"]["sha256"],
            ledger["ruby_css_margin"]["margin"],
            ledger["ruby_css_margin"]["excluded_paths"],
        ),
        (
            "67CBEEC6D4D6F3EB745FCE533CF224096959D6967C3C648F72E4CBA5C0FFE073",
            "AC009C26AF1D7FAE05E8969D86042B5BAFF5F482B226C575E1CEF8D27AEA2C7B",
            0.05,
            [KO_CSS_EXCLUSION],
        ),
    )
    _require_equal(
        "CSS selected-row pins",
        (
            ledger["ruby_css_margin"]["content_html_files_before_exclusion"],
            ledger["ruby_css_margin"]["selected_path_list_sha256"],
            ledger["ruby_css_margin"]["per_file_rows_sha256"],
            ledger["ruby_css_margin"]["boundary_pair_rows"],
            ledger["ruby_css_margin"]["boundary_pair_rows_sha256"],
        ),
        (
            169,
            "C731C78ED68D9A14DA6AD0794C226D9C76DBEB22A979B16A8A7C1E92657EBFF0",
            "87435CEFF499973AF650EAF34B345BBEED287AC192FD022CD9D4C17D46072E4E",
            57,
            "3CA01BCB660B8FE96BA37EAA0B8DFB06418AF385E18DE245E52F109A74CE79A8",
        ),
    )
    _require_equal(
        "app/boundary authority",
        (
            ledger["app_runtime"]["app_baseline_head_oid"],
            ledger["app_runtime"]["baseline_is_ancestor"],
            ledger["app_runtime"]["boundary_authority"]["authority_keys"],
            ledger["app_runtime"]["boundary_authority"]["authority_sha256"],
            ledger["app_runtime"]["boundary_authority"]["expected_key_counts"],
        ),
        (
            APP_BASELINE_HEAD,
            True,
            49348,
            "198D130AAEAA02216C3B28EFE0FF38DC9CF54E4145822C91BDE293E574D73637",
            {"ja": 49309, "zh": 49348, "ko": 49348},
        ),
    )
    _require_equal(
        "app artifact pins",
        (
            ledger["app_runtime"]["boundary_authority"]["builder"]["sha256"],
            ledger["app_runtime"]["boundary_authority"]["manifest"]["sha256"],
            ledger["app_runtime"]["width_policy_source"]["sha256"],
            ledger["app_runtime"]["shared_char_width_table"]["sha256"],
        ),
        (
            APP_ARTIFACT_SHA256["boundary_builder"],
            APP_ARTIFACT_SHA256["boundary_manifest"],
            APP_ARTIFACT_SHA256["width_policy"],
            APP_ARTIFACT_SHA256["char_width"],
        ),
    )
    _require_equal(
        "deployed word-annotation pins",
        {
            language: ledger["app_runtime"]["boundary_authority"]["word_anno"][
                language.lower()
            ]["sha256"]
            for language in ("JA", "ZH", "KO")
        },
        {
            language: row["word_anno"]
            for language, row in LANGUAGE_ARTIFACT_PINS.items()
        },
    )
    _require_equal(
        "deployed payload/runtime/probe pins",
        {
            language: (
                row["payload"]["sha256"],
                row["runtime"]["sha256"],
                row["rendered"],
                row["probe"]["boundary_signature"],
                row["probe"]["effective_max_line_width_ratio"],
                row["probe"]["missing_width_characters"],
                row["probe"]["within_2x"],
            )
            for language, row in ledger["app_runtime"]["languages"].items()
        },
        {
            language: (
                row["payload"],
                row["runtime"],
                row["rendered"],
                [[JUS, "R"]],
                row["effective_width_ratio"],
                [],
                True,
            )
            for language, row in LANGUAGE_ARTIFACT_PINS.items()
        },
    )
    _require_equal(
        "guide/runtime policy",
        (
            ledger["guide_policy"]["ruby_track"],
            ledger["guide_policy"]["width_changes_root_boundaries"],
            ledger["app_runtime"]["policy"]["ruby_track"],
            ledger["app_runtime"]["policy"]["width_changes_root_boundaries"],
            ledger["app_runtime"]["policy"][
                "effective_css_scaled_max_line_width_limit"
            ],
        ),
        ("coarse", False, "coarse", False, 2.0),
    )
    if ledger.get("scope") != {
        "corpus_or_guide_payload_edits": 0,
        "app_payload_edits": 0,
        "auto_fix_runs": 0,
        "commit_or_push": False,
    }:
        raise GuideTransitionError("ledger authorizes out-of-scope writes")
    if ledger.get("gate", {}).get("pass") is not True:
        raise GuideTransitionError("ledger gate.pass is not true")


def require_review_match(committed: dict, actual: dict) -> None:
    if committed != actual:
        raise GuideTransitionError(
            "recomputed review differs from committed transition ledger"
        )


def resolve_checkout(argument: Path | None, environment_name: str) -> Path:
    raw = str(argument) if argument is not None else os.environ.get(environment_name)
    if not raw:
        raise GuideTransitionError(
            f"supply --{environment_name.removeprefix('ESP_CORPUS_').lower()} "
            f"or set {environment_name}"
        )
    return Path(raw).expanduser().resolve()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old", type=Path, help="clean b769038 checkout")
    parser.add_argument(
        "--new",
        type=Path,
        help="clean immutable predecessor 7c04f97 checkout",
    )
    parser.add_argument(
        "--active",
        type=Path,
        help="clean current remote-main d1642c2 checkout",
    )
    parser.add_argument("--app-root", type=Path, default=ROOT)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument(
        "--print-review",
        action="store_true",
        help="print recomputed JSON instead of comparing (still read-only)",
    )
    args = parser.parse_args(argv)
    try:
        old_root = resolve_checkout(args.old, "ESP_CORPUS_OLD_PATH")
        new_root = resolve_checkout(args.new, "ESP_CORPUS_NEW_PATH")
        active_root = resolve_checkout(
            args.active, "ESP_CORPUS_ACTIVE_PATH"
        )
        actual = build_review(
            old_root,
            new_root,
            active_root,
            args.app_root.expanduser().resolve(),
        )
        if args.print_review:
            print(json.dumps(actual, ensure_ascii=False, indent=1))
        else:
            committed = json.loads(args.ledger.read_text(encoding="utf-8"))
            validate_authority(committed)
            require_review_match(committed, actual)
            print(
                "PASS latest Kyoto guides b769038->7c04f97: "
                "+452/-101 classified; current-main d164 byte-identical; "
                "G8 violations=0; JA CSS boundary-skip=551/fixable=0; "
                "ĵus JA=たっ<br>た今 and JA/ZH/KO boundary=R"
            )
        return 0
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        GuideTransitionError,
        StopIteration,
    ) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
