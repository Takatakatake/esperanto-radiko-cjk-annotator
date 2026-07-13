"""Gate keyed Ruby structure across JA/ZH/KO; report array order diagnostically."""
import gc
import html
import json
from pathlib import Path
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parents[1]
RUBY = re.compile(r"<ruby>(.*?)<rt[^>]*>.*?</rt></ruby>", re.DOTALL | re.IGNORECASE)
RT = re.compile(r"<rt[^>]*>.*?</rt>", re.DOTALL | re.IGNORECASE)
TAG = re.compile(r"<[^>]+>")
LEADING_WHITESPACE = re.compile(r"^\s*")
TRAILING_WHITESPACE = re.compile(r"\s*$")


def _normalized_visible(value):
    """Preserve Unicode letters, digits and punctuation; normalize whitespace."""
    visible = html.unescape(TAG.sub("", value))
    return " ".join(visible.split())


def rendered_visible(value):
    """Return exact user-visible text, excluding ruby annotations and tags."""
    return html.unescape(TAG.sub("", RT.sub("", value)))


def edge_padding(value):
    """Return the exact leading and trailing whitespace carried by a rule."""
    return (
        LEADING_WHITESPACE.match(value).group(0),
        TRAILING_WHITESPACE.search(value).group(0),
    )


def rule_padding_matches(old, new):
    """A replacement must preserve both edge-padding strings exactly."""
    return edge_padding(old) == edge_padding(new)


def duplicate_old_keys(rules):
    """Return duplicate replacement surfaces in first-seen order."""
    seen = set()
    duplicate_set = set()
    duplicates = []
    for rule in rules:
        old = rule[0]
        if old in seen and old not in duplicate_set:
            duplicate_set.add(old)
            duplicates.append(old)
        seen.add(old)
    return duplicates


def structural_signature(rendered):
    """Return ordered ``R:`` ruby and ``L:`` literal pieces.

    Keeping the kind prefix prevents a localized app with a missing annotation
    (literal ``foo``) from comparing equal to another app's atomic ruby ``foo``.
    Unicode is retained instead of being restricted to an ASCII/Esperanto regex.
    """
    pieces = [
        "PAD:"
        + ("1" if rendered[:1].isspace() else "0")
        + ("1" if rendered[-1:].isspace() else "0")
    ]
    position = 0
    for match in RUBY.finditer(rendered):
        literal = _normalized_visible(rendered[position:match.start()])
        if literal:
            pieces.append("L:" + literal)
        rb = _normalized_visible(match.group(1))
        pieces.append("R:" + rb)
        position = match.end()
    literal = _normalized_visible(rendered[position:])
    if literal:
        pieces.append("L:" + literal)
    return tuple(pieces)


def load_rules(language):
    path = ROOT / f"Esperanto-Kanji-Ruby-{language}" / "app_data" / "置換リスト_ルビ.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    rules = next(value for key, value in data.items() if "replacements_final_list" in key)
    duplicate_violations = {}
    for key, candidate_rules in data.items():
        if "replacements_final_list" in key:
            label = "global"
        elif "replacements_list_for_2char" in key:
            label = "two_char"
        elif "replacements_list_for_localized_string" in key:
            label = "local"
        else:
            continue
        duplicates = duplicate_old_keys(candidate_rules)
        if duplicates:
            duplicate_violations[label] = duplicates
        print(f"[{language}] {label}_duplicate_old={len(duplicates)}")
        for old in duplicates[:20]:
            print(f"  duplicate[{label}]={old!r}")
    old_sequence = [rule[0] for rule in rules]
    signatures = [structural_signature(rule[1]) for rule in rules]
    padding_violations = [
        index for index, rule in enumerate(rules)
        if not rule_padding_matches(rule[0], rule[1])
    ]
    visible_violations = [
        index for index, rule in enumerate(rules)
        if rule[0] != rendered_visible(rule[1])
    ]
    print(f"[{language}] global rules={len(rules)}")
    print(f"[{language}] old/new_padding_invariant_diff={len(padding_violations)}")
    for index in padding_violations[:20]:
        old, new, *_ = rules[index]
        print(
            f"  padding[{index}] old={old!r} new={new!r} "
            f"old_edges={edge_padding(old)!r} new_edges={edge_padding(new)!r}"
        )
    print(f"[{language}] old/visible_new_exact_diff={len(visible_violations)}")
    for index in visible_violations[:20]:
        old, new, *_ = rules[index]
        print(f"  visible[{index}] old={old!r} visible_new={rendered_visible(new)!r}")
    return (
        old_sequence, signatures, padding_violations,
        duplicate_violations, visible_violations,
    )


def main():
    (
        baseline_old, baseline_signatures, baseline_padding,
        baseline_duplicates, baseline_visible,
    ) = load_rules("JA")
    failed = bool(baseline_padding or baseline_duplicates or baseline_visible)
    baseline_by_old = dict(zip(baseline_old, baseline_signatures))
    for language in ("ZH", "KO"):
        (
            candidate_old, candidate_signatures, candidate_padding,
            candidate_duplicates, candidate_visible,
        ) = load_rules(language)
        if candidate_padding or candidate_duplicates or candidate_visible:
            failed = True
        old_differences = [
            index for index, (ja, candidate) in enumerate(zip(baseline_old, candidate_old))
            if ja != candidate
        ]
        if len(baseline_old) != len(candidate_old):
            old_differences.append(min(len(baseline_old), len(candidate_old)))
        candidate_by_old = dict(zip(candidate_old, candidate_signatures))
        old_set_differences = sorted(set(baseline_by_old) ^ set(candidate_by_old))
        keyed_structure_differences = sorted(
            old for old in set(baseline_by_old) & set(candidate_by_old)
            if baseline_by_old[old] != candidate_by_old[old]
        )
        print(
            f"[{language}] ordered_old_diff={len(old_differences)} "
            f"old_set_diff={len(old_set_differences)} "
            f"keyed_structure_diff={len(keyed_structure_differences)}"
        )
        # Historical language-specific CSV coverage changes the numeric priority
        # of some rules, so exact array order is diagnostic only (HEAD already
        # differs by >400k positions).  Runtime-safe gates are key-set identity,
        # per-key R/L/PAD identity and uniqueness.  Representative overlap
        # runtime behavior is covered separately by test_generation_regressions.
        if old_set_differences or keyed_structure_differences:
            failed = True
            for old in old_set_differences[:20]:
                print(f"  old_set {old!r}: JA={old in baseline_by_old} {language}={old in candidate_by_old}")
            for old in keyed_structure_differences[:20]:
                print(
                    f"  keyed_structure {old!r}: JA={baseline_by_old[old]!r} "
                    f"{language}={candidate_by_old[old]!r}"
                )
        del (
            candidate_old, candidate_signatures, candidate_padding,
            candidate_duplicates, candidate_visible,
        )
        gc.collect()

    if failed:
        raise SystemExit(1)
    print("3言語Ruby全域（old集合・重複・R/L/PAD構造）一致: PASS")


if __name__ == "__main__":
    main()
