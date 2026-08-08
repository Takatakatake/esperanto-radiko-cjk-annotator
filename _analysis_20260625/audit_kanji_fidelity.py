# -*- coding: utf-8 -*-
"""漢字トラックのgold忠実度監査:
   gold(学習者版)が深く分解する語(gold⇔ドラフト食い違い943語)について、
   デプロイ済み漢字トラックの分解が gold にどれだけ忠実かを分類。
   分類: FOLLOW(gold通り) / COARSER(goldより粗い) / BARE(無変換) / OTHER"""
import os, re, sys, json
sys.stdout.reconfigure(encoding='utf-8')
ROOT = r"D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\エスペラントの漢字化プロジェクト総結集20260630"
BASE = ROOT + r"\語根分解、注釈ルビ振り、漢字化アプリ徹底ブラッシュアップ20260630"
GOLD = ROOT + r"\エスペラント辞書徹底語根分解_20260630\世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416.txt"
DRAFT = ROOT + r"\エスペラント辞書徹底語根分解_20260630\世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416_日中韓注釈版_ドラフト.txt"
PFX = chr(92) + chr(92) + chr(63) + chr(92)
def LP(p): return PFX + os.path.abspath(p)
X = {'c^':'ĉ','g^':'ĝ','h^':'ĥ','j^':'ĵ','s^':'ŝ','u^':'ŭ','C^':'Ĉ','G^':'Ĝ','H^':'Ĥ','J^':'Ĵ','S^':'Ŝ','U^':'Ŭ'}
def circ(s):
    for a, b in X.items(): s = s.replace(a, b)
    return s

gm = {}
for ln in open(LP(GOLD), encoding='utf-8'):
    w = ln.split(':', 1)[0].strip()
    if not w or ' ' in w or w.startswith('#'): continue
    cw = circ(w).replace('-', '')
    gm.setdefault(cw.replace('/', '').lower(), cw.lower())
dm = {}
for ln in open(LP(DRAFT), encoding='utf-8'):
    m = re.match(r'^([^【]+)【', ln)
    if m:
        d = circ(m.group(1).strip()).replace('-', '')
        if ' ' in d: continue
        dm.setdefault(d.replace('/', '').lower(), d.lower())
targets = []
L = "a-zĉĝĥĵŝŭ"
for n, dec in gm.items():
    if n in dm and dm[n] != dec and re.fullmatch('[' + L + ']{3,30}', n):
        targets.append((n, dec, dm[n]))
print(f"gold⇔ドラフト食い違い(監査対象): {len(targets)}")

# 漢字トラックのデプロイ分解
APP = BASE + r"\Esperanto-Kanji-Ruby-JA"; DATA = APP + r"\app_data"
sys.path.insert(0, APP)
import importlib, esp_text_replacement_module as M; importlib.reload(M)
dd = json.load(open(LP(DATA + r"\置換リスト_漢字.json"), encoding="utf-8"))
GL = dd["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]
G2 = dd["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]
GG = dd["全域替换用のリスト(列表)型配列(replacements_final_list)"]
ps = M.import_placeholders(DATA + r"\placeholders_skip.txt"); pl = M.import_placeholders(DATA + r"\placeholders_localcapture.txt")
RTP = re.compile(r'<ruby>([^<]+)<rt[^>]*>((?:[^<]|<br\s*/?>)*?)</rt></ruby>')
SEP = '◆'
def convert(text):
    return M.orchestrate_comprehensive_esperanto_text_replacement(text, ps, GL, pl, GG, G2, "HTML格式_Ruby文字_大小调整_汉字替换")
def seg_decomp(seg):
    """漢字モード: main=漢字/rt=エス片。rt(エス片)列で境界を得る。裸部分はそのまま。"""
    toks = []; pos = 0
    for m in RTP.finditer(seg):
        pre = re.sub(r'<[^>]+>', '', seg[pos:m.start()])
        for ch in re.findall('[' + L + "A-ZĈĜĤĴŜŬ']+", pre): toks.append(ch.lower())
        toks.append(re.sub(r'<br\s*/?>|\s', '', m.group(2)).lower()); pos = m.end()
    for ch in re.findall('[' + L + "A-ZĈĜĤĴŜŬ']+", re.sub(r'<[^>]+>', '', seg[pos:])): toks.append(ch.lower())
    return toks

ENDS = {'o','a','i','e','u','n','j','oj','on','aj','an','en','as','is','os'}
def stemtok(toks):
    t = list(toks)
    while t and t[-1] in ENDS: t.pop()
    return t

cls = {'FOLLOW': [], 'COARSER': [], 'BARE': [], 'OTHER': []}
words = [n for n, _, _ in targets]
gold_dec = {n: g for n, g, _ in targets}
B = 400
for i in range(0, len(words), B):
    chunk = words[i:i + B]
    out = convert(' ' + (' ' + SEP + ' ').join(chunk) + ' ')
    parts = out.split(SEP)
    if len(parts) != len(chunk):
        parts = [convert(' ' + w + ' ') for w in chunk]
    for w, seg in zip(chunk, parts):
        ktoks = stemtok(seg_decomp(seg))
        gparts = stemtok([p for p in gold_dec[w].split('/') if p])
        if ktoks == gparts:
            cls['FOLLOW'].append(w)
        elif len(ktoks) == 1 and ktoks[0] == w.rstrip('oaieun'):
            cls['BARE'].append(w)
        elif len(ktoks) < len(gparts):
            cls['COARSER'].append((w, '/'.join(ktoks), '/'.join(gparts)))
        else:
            cls['OTHER'].append((w, '/'.join(ktoks), '/'.join(gparts)))
print(f"\nFOLLOW(gold通り)={len(cls['FOLLOW'])} / COARSER={len(cls['COARSER'])} / BARE={len(cls['BARE'])} / OTHER={len(cls['OTHER'])}")
print("\nCOARSER例:")
for w, k, g in cls['COARSER'][:12]: print(f"  {w:20s} 漢字側={k:24s} gold={g}")
print("\nBARE例:", cls['BARE'][:10])
print("\nOTHER例:")
for w, k, g in cls['OTHER'][:8]: print(f"  {w:20s} 漢字側={k:24s} gold={g}")
json.dump({k: v for k, v in cls.items()}, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kanji_fidelity.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
