# -*- coding: utf-8 -*-
"""第79R: 別セッションの Phase 600 から、**注釈が増える2件だけ**を取り込む。DRY既定 / --apply。

■ 経緯(第78Rの測定漏れの是正)
  第78Rで r74 を丸ごと外したとき、差分を**キー辞書**で測ったため
  **同一キーを重ねる49行を見落としていた**(r74は57行増だが新規キーは8件だけ)。
  行単位で測り直すと、外した57行のうち49行は純粋な改善だった。

■ 取り込む内容(いずれも gold 実在の見出し。訳語の発明はしない)
  1. nor-adrenalin* / nor-epinefrin* の48語形
        現行: nor-<ruby>adrenalin<rt>アドレナリン</rt></ruby>o   (nor- が無注釈)
        以後: <ruby>nor<rt>ノル</rt></ruby>-<ruby>adrenalin…</ruby>o
     gold: `nor-adrenalin/o:【PIV】…Sin. nor-epinefrino.` / `nor/:【化】【PIV】Pref.…`
     3言語グロス JA=ノル / ZH=降碳 / KO=노르
  2. glu-glu-glu(+ 文頭形・全大文字形)
        現行: 無注釈のラテン素通し
        以後: <ruby>glu-glu-glu<rt>七面鳥の鳴き声</rt></ruby>
     gold: `glu-glu-glu:【PIV】Onomatopeo por la bleko de meleagro.`(一語の擬音語)
     3言語 JA=七面鳥の鳴き声 / ZH=火鸡叫声 / KO=칠면조 울음소리
     ※相手は**小文字形しか直していない**。Glu-glu-glu / GLU-GLU-GLU のキーは
       存在するのに無注釈で残るので、同じ訳語でこちらが補完する。

■ 取り込まない8行(第78Rの判断を維持)
  - 裸の ' nor ' 根と ' kuku-nor ' / ' lob-nor ' ガード3行
    相手のガードは**小文字形しか塞いでいない**ため、実文に現れる大文字形
    `Kuku-nor` は `Kuku[カッコウ] - nor[ノル]` と誤ルビが増える(実測)。
    gold の nor- 複合語は上記48語形で尽きるので、裸の根に利得が無い。
  - ' Temis pri … ' の語句5行(ユーザー裁定「常に Tem+is でいい」により不要)

■ 適用方式(相手と2点変える)
  (a) 相手は52行を**既存行の前に重ねて**入れる(重複キーが49種できる)。
      こちらは**既存行の値を差し替える**。描画は同じで重複キーを作らない。
  (b) 相手の値を**丸写ししない**。(base, 訳語)の対だけを取り出し、
      アプリ本体の output_format でこのリポジトリの幅方針に従って組み直す。
      ★実測: 相手の glu-glu-glu は rt class="XXL_L" だが、このリポジトリの
        char_widths では "L_L" が正しく、丸写しすると幅ゲートが赤になる。
"""
import json, os, re, sys, argparse, subprocess, collections
sys.stdout.reconfigure(encoding='utf-8')
BS = chr(92); PFX = BS * 2 + chr(63) + BS
def LP(p): return PFX + os.path.abspath(p)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, '_analysis_20260625'))
from atomic_json import atomic_file_copy, atomic_json_dump
from gen_replacement import load_app_replacement_helper

ap = argparse.ArgumentParser()
ap.add_argument('--apply', action='store_true')
ap.add_argument('--base', default='3f33892', help='移植元の親(取り込み済みの世代)')
ap.add_argument('--source', default='47d1620', help='Phase 600 を含むコミット')
A = ap.parse_args()
DRY = not A.apply
KEY = '全域替换用のリスト(列表)型配列(replacements_final_list)'
FMT = 'HTML格式_Ruby文字_大小调整'
RUBY = re.compile(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', re.S)
TAG = re.compile(r'<[^>]+>')
BR = re.compile(r'<br\s*/?>', re.I)

def wanted(k):
    s = k.strip().lower()
    return s.startswith(('nor-adrenalin', 'nor-epinefrin')) or s == 'glu-glu-glu'

def gitrows(rev, rel):
    r = subprocess.run(['git', '-C', ROOT, 'show', f'{rev}:{rel}'], capture_output=True)
    if r.returncode != 0: raise SystemExit(f'git show 失敗: {rev}:{rel}')
    return json.loads(r.stdout.decode('utf-8'))[KEY]

def parse(v):
    """値を [(literal文字列) | (base, 訳語)] の列に分解する。"""
    out = []; pos = 0
    for m in RUBY.finditer(v):
        if m.start() > pos:
            lit = TAG.sub('', v[pos:m.start()])
            if lit: out.append(lit)
        out.append((TAG.sub('', m.group(1)), BR.sub('', TAG.sub('', m.group(2)))))
        pos = m.end()
    if pos < len(v):
        lit = TAG.sub('', v[pos:])
        if lit: out.append(lit)
    return out

def surface(parts):
    # 値の前後の空白パディングは表層ではないので落とす
    return ''.join(p if isinstance(p, str) else p[0] for p in parts).strip()

def seg(parts):
    return '/'.join(p[0] for p in parts if not isinstance(p, str))

def render(parts, helper, cw):
    return ''.join(p if isinstance(p, str) else helper.output_format(p[0], p[1], FMT, cw)
                   for p in parts)

def recase(parts, want):
    """base側だけ want の綴りに合わせ直す(訳語はそのまま)。表層長が同じ前提。"""
    out = []; i = 0
    for p in parts:
        n = len(p) if isinstance(p, str) else len(p[0])
        piece = want[i:i+n]; i += n
        out.append(piece if isinstance(p, str) else (piece, p[1]))
    return out if i == len(want) else None

plan = {}
for lang in ('JA', 'ZH', 'KO'):
    rel = f'Esperanto-Kanji-Ruby-{lang}/app_data/置換リスト_ルビ.json'
    base = {}; src = {}
    for e in gitrows(A.base, rel):
        if isinstance(e[0], str) and wanted(e[0]): base.setdefault(e[0], e[1])
    for e in gitrows(A.source, rel):
        if isinstance(e[0], str) and wanted(e[0]): src.setdefault(e[0], e[1])
    plan[lang] = (base, src)
    print(f'[{lang}] 対象キー base={len(base)} source={len(src)}')

ks = [set(v[1]) for v in plan.values()]
if not (ks[0] == ks[1] == ks[2]):
    raise SystemExit('3言語で対象キー集合が違う: 中止')
keys = sorted(ks[0])
print(f'対象キー {len(keys)} (3言語一致)')

# 3言語で分節が一致していることを先に確かめる(ユーザーの絶対要件)
bad = [k for k in keys if len({seg(parse(plan[L][1][k])) for L in ('JA', 'ZH', 'KO')}) != 1]
if bad:
    raise SystemExit(f'★分節が3言語で食い違う: {bad[:5]}')
print('3言語の分節一致: ○')

for lang in ('JA', 'ZH', 'KO'):
    rel = f'Esperanto-Kanji-Ruby-{lang}/app_data/置換リスト_ルビ.json'
    path = os.path.join(ROOT, rel.replace('/', os.sep))
    app_dir = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}')
    helper = load_app_replacement_helper(app_dir)
    cw = json.load(open(LP(os.path.join(app_dir, 'app_data', 'char_widths.json')), encoding='utf-8'))
    d = json.load(open(LP(path), encoding='utf-8'))
    base, src = plan[lang]
    n = nv = 0; skip = []
    glu_parts = None
    for e in d[KEY]:
        if not (isinstance(e[0], str) and e[0] in src): continue
        want = e[0].strip()
        parts = parse(src[e[0]])
        if surface(parts) != want:
            skip.append((e[0], f'表層不一致 {surface(parts)!r} != {want!r}')); continue
        # 変種の再構成は表層長で位置合わせするので、前後パディングを外した形を持つ。
        # ★小文字形だけを雛形にする(大文字形も wanted に入るため、条件を .lower() に
        #   すると無注釈の変種で雛形が上書きされて補完が空振りする)。
        if want == 'glu-glu-glu':
            cand = parse(src[e[0]].strip())
            if any(not isinstance(x, str) for x in cand): glu_parts = cand
        new = render(parts, helper, cw)
        cur = e[1]
        if new.strip() == cur.strip(): continue
        if cur.strip() != base.get(e[0], '').strip() and RUBY.search(cur):
            skip.append((e[0], '現行値が移植元の親と違う(既に手当て済み?)')); continue
        pad_l = cur[:len(cur) - len(cur.lstrip())]; pad_r = cur[len(cur.rstrip()):]
        e[1] = pad_l + new.strip() + pad_r
        n += 1
    # 大小変種の補完(相手は小文字形しか直していない)
    if glu_parts:
        for e in d[KEY]:
            if not (isinstance(e[0], str) and e[0].strip().lower() == 'glu-glu-glu'): continue
            want = e[0].strip()
            if want == 'glu-glu-glu': continue
            rp = recase(glu_parts, want)
            if rp is None or surface(rp) != want:
                skip.append((e[0], '変種の再構成に失敗')); continue
            new = render(rp, helper, cw)
            cur = e[1]
            if new.strip() == cur.strip(): continue
            pad_l = cur[:len(cur) - len(cur.lstrip())]; pad_r = cur[len(cur.rstrip()):]
            e[1] = pad_l + new.strip() + pad_r
            nv += 1
    kc = collections.Counter(e[0] for e in d[KEY] if isinstance(e[0], str))
    dup = sum(1 for v in kc.values() if v > 1)
    print(f'[{lang}] 差し替え {n} + 大小変種 {nv} / skip {len(skip)} / '
          f'全域 {len(d[KEY])} (重複キー {dup})')
    for k, why in skip[:6]: print(f'     skip {k!r}: {why}')
    if not DRY:
        atomic_file_copy(LP(path), LP(path + '.bak_preR79'))
        atomic_json_dump(LP(path), d)
print('\n(DRY-RUN: --apply で書込)' if DRY else '\n適用完了')
