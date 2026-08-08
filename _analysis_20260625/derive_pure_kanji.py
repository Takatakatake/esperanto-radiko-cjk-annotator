# -*- coding: utf-8 -*-
"""純粋置換版JSONの再導出(漢字HTML JSON→rt/rubyタグ除去)。
   漢字JSONを再生成したら必ずこれも再導出する(3アプリ共有・JA配下に1本)。"""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, '_analysis_20260625'))
from atomic_json import atomic_json_dump
PFX = chr(92) + chr(92) + chr(63) + chr(92)
def LP(p): return PFX + os.path.abspath(p)

src = os.path.join(BASE, 'Esperanto-Kanji-Ruby-JA', 'app_data', '置換リスト_漢字.json')
dst = os.path.join(BASE, 'Esperanto-Kanji-Ruby-JA', 'app_data', '置換リスト_漢字_純粋置換.json')
d = json.load(open(LP(src), encoding='utf-8'))
def strip(v):
    v = re.sub(r'<rt[^>]*>.*?</rt>', '', v)
    return v.replace('<ruby>', '').replace('</ruby>', '')
out = {k: [[e[0], strip(e[1])] + list(e[2:]) for e in arr] for k, arr in d.items()}
atomic_json_dump(LP(dst), out)
n = sum(len(v) for v in out.values())
print(f"純粋置換版 再導出: {os.path.getsize(LP(dst))//1024//1024}MB / {n}エントリ")
