# -*- coding: utf-8 -*-
"""第129R: 大文字化キーのrt小文字残り2語(Metu/Organiziĝis=第118R合成の取りこぼし)を是正。
   値手術=先頭rtの1字目を大文字化するだけ(漢字グリフ・発火位置・ID不変)。DRY既定/--apply。
   fail-closed: 対象キーの現在値が期待の小文字形であること / 手術後 surface==キー /
   漢字フラット(disp)不変 / 3言語同一。冪等(既に大文字なら対象0)。"""
import json, os, re, sys, argparse
sys.stdout.reconfigure(encoding='utf-8')
PFX = chr(92)+chr(92)+chr(63)+chr(92)
def LP(p): return PFX + os.path.abspath(p)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AN = os.path.join(ROOT, '_analysis_20260625')
sys.path.insert(0, AN)
from atomic_json import atomic_file_copy, atomic_json_dump

ap = argparse.ArgumentParser()
ap.add_argument('--apply', action='store_true')
A = ap.parse_args()
DRY = not A.apply
KEY = '全域替换用のリスト(列表)型配列(replacements_final_list)'
TARGETS = ['Metu', 'Organiziĝis']

RT = re.compile(r'<rt([^>]*)>((?:[^<]|<br\s*/?>)*?)</rt>', re.S)
TAG = re.compile(r'<[^>]+>')
RUBY = re.compile(r'<ruby>(.*?)<rt[^>]*>((?:[^<]|<br\s*/?>)*?)</rt>\s*</ruby>', re.S)
BR = re.compile(r'<br\s*/?>')
def surf(v):
    out, pos = [], 0
    for m in RUBY.finditer(v):
        out.append(TAG.sub('', v[pos:m.start()])); out.append(BR.sub('', m.group(2))); pos = m.end()
    out.append(TAG.sub('', v[pos:]))
    return ''.join(out)
def disp(v): return TAG.sub('', RT.sub('', v))
def cap_first_rt(v):
    done = [False]
    def r(m):
        if done[0]: return m.group(0)
        done[0] = True
        c = m.group(2)
        return f'<rt{m.group(1)}>' + c[:1].upper() + c[1:] + '</rt>'
    return RT.sub(lambda m: r(m), v, count=1)

for lang in ('JA', 'ZH', 'KO'):
    path = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}', 'app_data', '置換リスト_漢字.json')
    d = json.load(open(LP(path), encoding='utf-8'))
    gg = d[KEY]
    fixed = 0
    for e in gg:
        if isinstance(e[0], str) and e[0].strip() in TARGETS:
            w = e[0].strip()
            cur = surf(e[1]).strip()
            if cur == w:
                continue  # 冪等: 既に正
            if cur != w.lower() and cur.lower() != w.lower():
                raise SystemExit(f'fail-closed: {lang} {w} 現在値が想定外: {cur!r}')
            old_disp = disp(e[1])
            nv = cap_first_rt(e[1])
            if surf(nv).strip() != w:
                raise SystemExit(f'fail-closed: {lang} {w} 手術後surface不一致: {surf(nv)!r}')
            if disp(nv) != old_disp:
                raise SystemExit(f'fail-closed: {lang} {w} 漢字フラットが変わった')
            e[1] = nv
            fixed += 1
            print(f'  [{lang}] {w}: rt先頭を大文字化 -> {nv.strip()!r}')
    if fixed not in (0, len(TARGETS)):
        raise SystemExit(f'{lang}: 対象数が不完全 {fixed}')
    if DRY:
        print(f'  [{lang}] DRY: {fixed}件(--applyで書込)')
        continue
    if fixed:
        atomic_file_copy(LP(path), LP(path + '.bak_preR129'))
        atomic_json_dump(LP(path), d)
        print(f'  [{lang}] 書込 {fixed}件')
print('完了。漢字3ゲート+綴り忠実性ゲート+派生ゲートを回すこと。')
