# -*- coding: utf-8 -*-
"""nonfaithful_words.json を workflow agent 用にチャンク分割。"""
import json, sys, os
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from extract_lib import lp
OUT = BASE + r"\_analysis_20260625\out"
CH = OUT + r"\nf_chunks"
os.makedirs(lp(CH), exist_ok=True)
with open(lp(OUT + r"\nonfaithful_words.json"), encoding="utf-8") as f:
    data = json.load(f)
SIZE = 40
n = 0
for i in range(0, len(data), SIZE):
    chunk = data[i:i+SIZE]
    # agentが扱いやすいよう簡素化: word, decomp, def, 各断片(root,ja_gloss), bad(問題断片)
    simplified = []
    for e in chunk:
        simplified.append({
            'word': e['word'], 'decomp': e['decomp'], 'def': e['def'],
            'ja_pieces': e['ja'], 'flagged': e['bad'],
        })
    with open(lp(CH + f"\\chunk_{n:03d}.json"), "w", encoding="utf-8") as g:
        json.dump(simplified, g, ensure_ascii=False, indent=1)
    n += 1
print(f"{len(data)}語 を {n}チャンク(各最大{SIZE}語)に分割: out/nf_chunks/chunk_000..{n-1:03d}.json")
