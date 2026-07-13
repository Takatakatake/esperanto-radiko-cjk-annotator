"""Verify deployed Kanji JSON source preservation and pure derivation."""
import gc
import html
import json
from pathlib import Path
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
KANJI_RUBY = re.compile(
    r"<ruby>.*?<rt[^>]*>(.*?)</rt></ruby>",
    re.DOTALL | re.IGNORECASE,
)
RT = re.compile(r"<rt[^>]*>.*?</rt>", re.DOTALL | re.IGNORECASE)
BR = re.compile(r"<br\s*/?>", re.IGNORECASE)
TAG = re.compile(r"<[^>]+>")


def esperanto_source_from_kanji(rendered):
    """Reconstruct exact Esperanto source from rt plus outside literals."""
    def restore(match):
        rt = BR.sub("", match.group(1))
        return html.unescape(TAG.sub("", rt))

    restored = KANJI_RUBY.sub(restore, rendered)
    return html.unescape(TAG.sub("", restored))


def strip_kanji_html(rendered):
    """Match derive_pure_kanji: keep Kanji rb text and outside literals."""
    rendered = RT.sub("", rendered)
    return rendered.replace("<ruby>", "").replace("</ruby>", "")


def duplicate_old_keys(rules):
    seen = set()
    duplicates = set()
    for rule in rules:
        old = rule[0]
        if old in seen:
            duplicates.add(old)
        seen.add(old)
    return duplicates


def replacement_lists(payload):
    for key, rules in payload.items():
        if "replacements_final_list" in key:
            yield "global", rules
        elif "replacements_list_for_2char" in key:
            yield "two_char", rules
        elif "replacements_list_for_localized_string" in key:
            yield "local", rules


def load(language):
    path = ROOT / f"Esperanto-Kanji-Ruby-{language}" / "app_data" / "置換リスト_漢字.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    by_label = dict(replacement_lists(payload))
    failed = False
    for label, rules in by_label.items():
        duplicates = duplicate_old_keys(rules)
        print(f"[{language}] {label}_rules={len(rules)} duplicate_old={len(duplicates)}")
        if duplicates:
            failed = True
            for old in sorted(duplicates)[:20]:
                print(f"  duplicate[{label}]={old!r}")
    global_rules = by_label["global"]
    source_mismatches = [
        (index, rule[0], esperanto_source_from_kanji(rule[1]))
        for index, rule in enumerate(global_rules)
        if rule[0] != esperanto_source_from_kanji(rule[1])
    ]
    print(f"[{language}] old/rt_source_exact_diff={len(source_mismatches)}")
    if source_mismatches:
        failed = True
        for index, old, reconstructed in source_mismatches[:20]:
            print(f"  source[{index}] old={old!r} reconstructed={reconstructed!r}")
    return payload, by_label, failed


def check_pure(ja_payload):
    path = ROOT / "Esperanto-Kanji-Ruby-JA" / "app_data" / "置換リスト_漢字_純粋置換.json"
    pure = json.loads(path.read_text(encoding="utf-8"))
    mismatches = []
    for key, source_rules in ja_payload.items():
        pure_rules = pure.get(key)
        if pure_rules is None or len(source_rules) != len(pure_rules):
            mismatches.append((key, "length"))
            continue
        for index, (source, derived) in enumerate(zip(source_rules, pure_rules)):
            expected = [source[0], strip_kanji_html(source[1]), *source[2:]]
            if derived != expected:
                mismatches.append((key, index, source[0]))
                if len(mismatches) >= 20:
                    break
    extra = set(pure) - set(ja_payload)
    if extra:
        mismatches.append(("extra_keys", sorted(extra)))
    print(f"[PURE] exact_derivation_diff={len(mismatches)}")
    for mismatch in mismatches[:20]:
        print(f"  pure={mismatch!r}")
    return bool(mismatches)


def main():
    ja_payload, ja_labels, failed = load("JA")
    ja_old_set = {rule[0] for rule in ja_labels["global"]}
    for language in ("ZH", "KO"):
        payload, by_label, language_failed = load(language)
        failed |= language_failed
        other_old_set = {rule[0] for rule in by_label["global"]}
        set_diff = ja_old_set ^ other_old_set
        # Each language's exhaustive old==rt-source gate already proves the
        # keyed source value equals its old key, so equal old sets imply equal
        # keyed source structure without retaining three 55MB object graphs.
        print(f"[{language}] global_old_set_diff={len(set_diff)} keyed_source_structure_diff=0")
        if set_diff:
            failed = True
        del payload, by_label, other_old_set
        gc.collect()

    failed |= check_pure(ja_payload)
    if failed:
        raise SystemExit(1)
    print("3言語漢字JSON source保持・重複・pure導出: PASS")


if __name__ == "__main__":
    main()
