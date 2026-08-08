# -*- coding: utf-8 -*-
"""注釈版パースのスキップ原因と、注釈版でも埋まらない語根を診断。"""
import re, sys, csv, collections
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from extract_lib import lp, hat_to_circumflex, replace_esperanto_chars
ANNO = r"\\wsl.localhost\Ubuntu\home\y\エスペラント辞書徹底語根分解_20260619\世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416_日中韓注釈版_ドラフト.txt"
NEW_ROOTS = BASE + r"\_analysis_20260625\out\new_rootlist.txt"
LINE_RE = re.compile(r'^(.*?)【日=(.*?)｜中=(.*?)｜韓=(.*?)】')

skips = []
n=0
with open(lp(ANNO), encoding="utf-8") as f:
    for line in f:
        line=line.rstrip('\n')
        if not line or line.startswith('##'): continue
        m=LINE_RE.match(line)
        if not m:
            if len(skips)<0: pass
            continue
        head,sja,szh,sko=m.group(1).strip(),m.group(2),m.group(3),m.group(4)
        if '#' in head: continue
        hw=head.split(' ')
        for li,s in (('ja',sja),('zh',szh),('ko',sko)):
            if len(s.split(' '))!=len(hw):
                if len(skips)<12: skips.append((li,head,s))
                break
        else:
            # word単位の片数不一致
            for wi,h in enumerate(hw):
                hp=[p for p in h.split('/') if p]
                for li,s in (('ja',sja),('zh',szh),('ko',sko)):
                    tp=[p for p in s.split(' ')[wi].split('/') if p]
                    if len(tp)!=len(hp):
                        if len(skips)<24: skips.append((li,h,s.split(' ')[wi]))
                        break

print("="*70); print("【スキップ(片数不一致)の実例】")
for li,h,s in skips[:24]:
    print(f"  [{li}] head='{h}'  trans='{s}'")
