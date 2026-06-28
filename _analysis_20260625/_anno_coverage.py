# -*- coding: utf-8 -*-
"""注釈の系統的検証: gold(44100)＋漢字マスター(62283行の単一語)の和集合=最大語リストに対し、
   JP/ZH/KO 3アプリのルビ注釈で「各語根が訳を持つ(被覆)」割合を定量測定。
   偽分解語(an/emi等)が語根忠実に注釈されるかもサンプル確認。"""
import re, sys, json, os, glob, collections
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
from extract_lib import hat_to_circumflex, replace_esperanto_chars
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()
# 語リスト: gold + 漢字注入(単一語)
words=set()
GOLD=r"\\wsl.localhost\Ubuntu\home\y\エスペラント辞書徹底語根分解_20260619\世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416.txt"
if not os.path.exists(GOLD):
    for b in reversed(sorted(glob.glob(os.path.join(os.environ['USERPROFILE'],'Downloads','エスペラント_backup_*')))):
        g=os.path.join(b,'語根分解辞書_WSL','世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416.txt')
        if os.path.exists(g): GOLD=g; break
with open(GOLD,encoding='utf-8') as f:
    for line in f:
        if ':' not in line: continue
        d=line.split(':',1)[0].strip()
        if ' ' in d or d.startswith('-') or d.endswith('-'): continue
        w=norm(''.join(p for p in d.split('/') if p))
        if re.fullmatch(r'[a-zĉĝĥĵŝŭ]+', w): words.add(w)
INJ=r"D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\漢字化・語彙資料\エスペラント語根＿漢字割り当て＿20260621\漢字注入_学習者版_20260620.txt"
L=re.compile(r'^(.*?)⟦')
with open(lp(INJ),encoding='utf-8') as f:
    for line in f:
        m=L.match(line.rstrip('\n'))
        if not m: continue
        h=m.group(1).strip()
        if ' ' in h or '#' in h: continue
        w=norm(''.join(p for p in h.split('/') if p))
        if re.fullmatch(r'[a-zĉĝĥĵŝŭ]+', w): words.add(w)
words=sorted(words)
print(f"検証語リスト(gold∪漢字マスター単一語) = {len(words)} 語")
APPS={'JP':(r"\Esperanto-Kanji-Ruby-JA"),
      'ZH':(r"\Esperanto-Kanji-Ruby-ZH"),
      'KO':(r"\Esperanto-Kanji-Ruby-KO")}
LATIN=re.compile(r'[a-zĉĝĥĵŝŭ]', re.I)
for key,d in APPS.items():
    APPDIR=BASE+d; DATA=APPDIR+r"\app_data"; sys.path.insert(0,APPDIR)
    import importlib, esp_text_replacement_module as m; importlib.reload(m)
    dd=json.load(open(lp(DATA+r"\置換リスト_ルビ.json"),encoding='utf-8'))
    GL=dd["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]
    G2=dd["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]
    GG=dd["全域替换用のリスト(列表)型配列(replacements_final_list)"]
    ps=m.import_placeholders(lp(DATA+r"\占位符(placeholders)_%1854%-%4934%_文字列替换skip用.txt"))
    pl=m.import_placeholders(lp(DATA+r"\占位符(placeholders)_@5134@-@9728@_局部文字列替换结果捕捉用.txt"))
    total=fully=partial=none=0; CH=2500
    for s in range(0,len(words),CH):
        b=words[s:s+CH]
        h=m.orchestrate_comprehensive_esperanto_text_replacement("\n".join(" "+w+" " for w in b),ps,GL,pl,GG,G2,'HTML格式_Ruby文字_大小调整')
        lines=h.split("\n")
        if len(lines)!=len(b): continue
        for w,ln in zip(b,lines):
            total+=1
            roots=re.findall(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>',ln)
            content=[(r,g) for r,g in roots if len(norm(r))>=2]  # 内容語根(2字以上)
            if not content:
                none+=1; continue
            glossed=sum(1 for r,g in content if g and not LATIN.fullmatch(g) and g!=r)
            if glossed==len(content): fully+=1
            elif glossed>0: partial+=1
            else: none+=1
    print(f"  [{key}] 全語根に訳あり(完全被覆) {fully}/{total} = {fully*1000//max(total,1)/10}%  / 部分 {partial} / 無 {none}")
