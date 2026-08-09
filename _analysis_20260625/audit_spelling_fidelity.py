# -*- coding: utf-8 -*-
"""表示綴り忠実性ゲート(第129R新設)。全行の構造的不変量:
 ルビ行: タグ剥がし後の可視エスペラント == キー(注釈しても綴りが変わらない)
 漢字行: rt連結+裸ラテン == キー(漢字化してもルビから元綴りが完全復元できる)
対象: 3言語 × (ルビ/漢字) × (GG/GL/G2) 全行(約350万行・数分)。違反で非0終了。
初回(第129R)は Metu/Organiziĝis のrt小文字残り(第118R取りこぼし)2件を検出し是正済。"""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
PFX = chr(92)+chr(92)+chr(63)+chr(92)
def LP(p): return PFX + os.path.abspath(p)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = '全域替换用のリスト(列表)型配列(replacements_final_list)'
KGL = '局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)'
KG2 = '二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)'
RT = re.compile(r'<rt[^>]*>(?:[^<]|<br\s*/?>)*?</rt>', re.S)
TAG = re.compile(r'<[^>]+>')
RUBY = re.compile(r'<ruby>(.*?)<rt[^>]*>((?:[^<]|<br\s*/?>)*?)</rt>\s*</ruby>', re.S)
BR = re.compile(r'<br\s*/?>')

def ruby_visible(v):
    return TAG.sub('', RT.sub('', v))

def kanji_surface(v):
    out, pos = [], 0
    for m in RUBY.finditer(v):
        out.append(TAG.sub('', v[pos:m.start()])); out.append(BR.sub('', m.group(2))); pos = m.end()
    out.append(TAG.sub('', v[pos:]))
    return ''.join(out)

def norm(s):
    return re.sub(r'\s+', ' ', s).strip()

fail = False
for lang in ('JA', 'ZH', 'KO'):
    ad = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}', 'app_data')
    for track, fname, fn in (('ruby', '置換リスト_ルビ.json', ruby_visible),
                             ('kanji', '置換リスト_漢字.json', kanji_surface)):
        d = json.load(open(LP(os.path.join(ad, fname)), encoding='utf-8'))
        bad = []
        n = 0
        for lk in (KEY, KGL, KG2):
            for e in d[lk]:
                if not (isinstance(e, list) and len(e) >= 2
                        and isinstance(e[0], str) and isinstance(e[1], str)):
                    continue
                n += 1
                if norm(e[0]) != norm(fn(e[1])):
                    bad.append((lk[:2], e[0], norm(fn(e[1]))))
        print(f'[{lang}/{track}] {n}行 綴り不一致 {len(bad)} -> {"PASS" if not bad else "FAIL"}')
        for lk, k, v in bad[:10]:
            print(f'   [{lk}] key={k!r} -> 可視={v!r}')
        fail |= bool(bad)
sys.exit(1 if fail else 0)
