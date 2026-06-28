# -*- coding: utf-8 -*-
"""漢字注入マスターの真の規模を分解。何がベンチ対象で何が除外されていたか。"""
import re, sys, collections
sys.stdout.reconfigure(encoding="utf-8")
INJ = r"D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\漢字化・語彙資料\エスペラント語根＿漢字割り当て＿20260621\漢字注入_学習者版_20260620.txt"
LINE = re.compile(r'^(.*?)⟦(.*?)⟧')
total = 0; has_kanji = 0
cat = collections.Counter()
uniq_words = set()
uniq_single_lower = set()
uniq_capital = set(); uniq_hyphen = set(); uniq_phrase = set(); uniq_special = set()
with open(INJ, encoding="utf-8") as f:
    for line in f:
        line = line.rstrip("\n")
        total += 1
        m = LINE.match(line)
        if not m:
            cat["A_⟦無し(注釈/見出し等)"] += 1
            continue
        has_kanji += 1
        head = m.group(1).strip()
        if "#" in head:
            cat["B_head に#(偽分解別案等)"] += 1
            continue
        word = "".join(p for p in head.split("/") if p)
        if " " in head:
            cat["C_複合句(空白)"] += 1; uniq_phrase.add(word.replace(" ", "")); continue
        uniq_words.add(word)
        if re.fullmatch(r"[a-zĉĝĥĵŝŭ]+", word):
            cat["D_単一語・小文字(現ベンチ対象)"] += 1; uniq_single_lower.add(word)
        elif "-" in word:
            cat["E_ハイフン複合(固有名等)"] += 1; uniq_hyphen.add(word)
        elif re.search(r"[A-ZĈĜĤĴŜŬ]", word):
            cat["F_大文字含む(固有名詞)"] += 1; uniq_capital.add(word)
        else:
            cat["G_その他(数字/記号等)"] += 1; uniq_special.add(word)
print(f"総行数 {total} / ⟦漢字⟧付き {has_kanji}")
print("\n=== 行カテゴリ別 ===")
for k, v in cat.most_common(): print(f"  {k}: {v}")
print(f"\n=== ユニーク語数 ===")
print(f"  単一語・小文字(現ベンチ対象) : {len(uniq_single_lower)}")
print(f"  大文字含む固有名詞           : {len(uniq_capital)}")
print(f"  ハイフン複合                 : {len(uniq_hyphen)}")
print(f"  複合句(空白)                 : {len(uniq_phrase)}")
print(f"  その他                       : {len(uniq_special)}")
print(f"  --- 単一語トークン合計(小文字+大文字+ハイフン) : {len(uniq_single_lower)+len(uniq_capital)+len(uniq_hyphen)}")
print("\n  大文字固有名詞の例:", sorted(uniq_capital)[:15])
print("  ハイフン複合の例:", sorted(uniq_hyphen)[:10])
print("  複合句の例:", sorted(uniq_phrase)[:10])
