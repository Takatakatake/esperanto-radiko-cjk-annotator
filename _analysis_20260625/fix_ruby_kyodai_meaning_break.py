# -*- coding: utf-8 -*-
"""第81R: 京大コーパス水準の照合で見つかった**意味が壊れる**ルビを語スコープで直す。
   DRY既定 / --apply。

■ 何を直すか
  第80Rの全数測定(京大エス研HTML 172本 / 20,819語)で「appが細かい・不整合」18件のうち、
  固有名詞と粒度差のみの語を除いた**普通のエスペラント語で意味が壊れている**ものだけを扱う。

    語形        現行の描画                    正しい読み        京大コーパスの実ルビ
    korona      kor[心] «ona»                 koron[コロナ]+a   korona[コロナ]
    koronan     kor[心] «onan»                koron+an
    koronaj     kor[心] «onaj»                koron+aj
    koronajn    kor[心] «onajn»               koron+ajn
    portut      port[運ぶ;携帯] «ut»          por[ために]+tut[全部の]   por|tut
    bombaj      bombaj[ボンベイ]              bomb[爆弾]+aj     bomb[爆弾]+«aj»
    bombajn     bombaj[ボンベイ] «n»          bomb[爆弾]+ajn

  ★bombaj は固有名詞 Bombaj(ボンベイ)のキーが**小文字語形まで食っている**例。
    ユーザー明言の優先順位「普通の単語 > 固有名詞」に照らし、小文字だけ普通名詞に戻す。
    大文字形 Bombaj / BOMBAJ は ボンベイ のまま**触らない**。

■ 発明ゼロの根拠(実測で確認済み)
  使う語根グロスは**3言語すべての語根CSVに既に実在する**:
    koron : JA=コロナ / ZH=日冕 / KO=코로나
    bomb  : JA=爆弾   / ZH=炸弹 / KO=폭탄
    por   : JA=ために / ZH=为;给 / KO=위해
    tut   : JA=全部の / ZH=全体 / KO=전체의
  新しい訳語は一切作らない。分節は3言語で同一になるよう**同じ片リストから**組む。

■ 触らないと決めたもの
  - animea: 京大は anime[[日]アニメ] と振るが、語根 anime のグロスは**3言語CSVのどれにも無い**。
    ZH/KO のグロスを作れば発明になるため見送る(現状 anim[魂]+ea のまま。マスターへ照会)。
  - video: 現行 vide[映像]+o は gold の vide/o と一致しており**正しい**。
    京大が video を一語で振っているのは京大側が粗いだけ。二軌道原則で問題なし。
  - koron 単独: これは koro(心)の対格 koro+n であり kor[心]+«on» が正しい。
    綴りが corona 語根と衝突するが、語形が違うので触らない。
  - kvardek(四+十) / revu / pedagogio: 粒度差のみで意味は保たれている。過分解軸の再flag禁止裁定に従う。
  - 固有名詞9件(Bikini/Kinrjuu/Manĉua/Piast/Radio/Kontakto/onkjo/Ŝinkyoo/Bombaj大文字形)。

■ 安全設計
  1. 訳語は各言語の語根CSVから引く。1つでも欠けている言語があればその語ごと中止(fail-closed)。
  2. 片リストは全言語共通。組み上げ後に**3言語の分節が同一**であることを検証する。
  3. ルビの体裁はアプリ本体の output_format で組む(幅クラスをこのリポジトリの方針に合わせる)。
  4. 既にキーがあれば値を差し替え、無ければ第68Rで確定した作法で挿入する
     (自分を部分文字列として含む既存キーの直後、無ければ先頭。包含判定は約物パディング後)。
  5. 再実行できるように、前回の投入分($R81K)を外してから入れ直す。
"""
import json, os, re, sys, csv, glob, argparse, collections
sys.stdout.reconfigure(encoding='utf-8')
BS = chr(92); PFX = BS * 2 + chr(63) + BS
def LP(p): return PFX + os.path.abspath(p)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, '_analysis_20260625'))
from atomic_json import atomic_file_copy, atomic_json_dump
from gen_replacement import load_app_replacement_helper

ap = argparse.ArgumentParser()
ap.add_argument('--apply', action='store_true')
A = ap.parse_args()
DRY = not A.apply
KEY = '全域替换用のリスト(列表)型配列(replacements_final_list)'
FMT = 'HTML格式_Ruby文字_大小调整'
MARK = '$R81K'
RUBY = re.compile(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', re.S)
TAG = re.compile(r'<[^>]+>')

# ── 対象(手検証済み。片は (語根 or None=文法語尾, 綴り) の列) ────────────
#    None の片はルビを付けない素のラテン(文法語尾)。
#    cases: 与える大小変種。'lower'/'title'/'upper'
TARGETS = [
    # korona 族: koron(コロナ) + 文法語尾
    ('korona',   [('koron', 'koron'), (None, 'a')],           ['lower', 'title', 'upper']),
    ('koronan',  [('koron', 'koron'), (None, 'an')],          ['lower', 'title', 'upper']),
    ('koronaj',  [('koron', 'koron'), (None, 'aj')],          ['lower', 'title', 'upper']),
    ('koronajn', [('koron', 'koron'), (None, 'ajn')],         ['lower', 'title', 'upper']),
    # portut: por(ために) + tut(全部の)
    ('portut',   [('por', 'por'), ('tut', 'tut')],            ['lower', 'title', 'upper']),
    # bombaj 族: ★小文字のみ。大文字形は固有名詞ボンベイのまま据置
    ('bombaj',   [('bomb', 'bomb'), (None, 'aj')],            ['lower']),
    ('bombajn',  [('bomb', 'bomb'), (None, 'ajn')],           ['lower']),
    # miriad 族(第83Rで追加): gold は miria/d/o ##偽分解。ルビ側は一語根に粗くするのが正しい。
    #   現行 miria[万]«do» は語根 miriad(無数) を miria(万)+d に割ってしまい、
    #   しかも d が裸で落ちる。miriadoj は京大コーパスに実在する。
    #   ★miriadoj だけは以前のラウンドで既に miriad[無数] に直っていたが、
    #     miriado / miriadon / miriadojn と裸の語根形が miria[万]+d のまま取り残されていた
    #     (「見出しの一部だけ直して語尾変化形を落とす」型の残骸)。族ごと揃える。
    #     なお miria(万)自体は別語根で miriametro=万メートル に使われるので触らない。
    ('miriad',   [('miriad', 'miriad')],                      ['lower', 'title', 'upper']),
    ('miriado',  [('miriad', 'miriad'), (None, 'o')],         ['lower', 'title', 'upper']),
    ('miriadoj', [('miriad', 'miriad'), (None, 'oj')],        ['lower', 'title', 'upper']),
    ('miriadon', [('miriad', 'miriad'), (None, 'on')],        ['lower', 'title', 'upper']),
    ('miriadojn',[('miriad', 'miriad'), (None, 'ojn')],       ['lower', 'title', 'upper']),
    # ── 第89R: 京大コーパス21,321語との全数照合(分節一致 99.597%)で残った
    #    「接尾辞が裸で落ちる」8語。いずれも**アプリ自身の同族が既に正しく振れている**
    #    取り残しであり、京大コーパスの実ルビとも、マスターの分解とも一致する。
    #        venis -> ven[(に)来る] is[過去形]   ↔ fortis  -> fort[強い]«is»      ✘
    #        duono -> du[二] on[分数]«o»        ↔ duon    -> du[二]«on»          ✘
    #        urbano-> urb[都市] an[成員]«o»     ↔ klasano -> klas[クラス]«ano»    ✘
    #        deveno-> de[の;から] ven[来る]«o»  ↔ devenaj -> deven[起源]«aj»     ✘(アプリ内で不一致)
    #        promenado -> promen ad[継続行為]«o» ↔ misiad -> misi[使命]«ad»      ✘
    #    gold も両版とも du/on/…・de/ven/…・kvar/on/o で一致(照合済み)。
    ('duon',     [('du', 'du'), ('on', 'on')],                ['lower', 'title', 'upper']),
    ('kvaron',   [('kvar', 'kvar'), ('on', 'on')],            ['lower', 'title', 'upper']),
    ('fortis',   [('fort', 'fort'), ('is', 'is')],            ['lower', 'title', 'upper']),
    ('klasano',  [('klas', 'klas'), ('an', 'an'), (None, 'o')],   ['lower', 'title', 'upper']),
    ('klasanoj', [('klas', 'klas'), ('an', 'an'), (None, 'oj')],  ['lower', 'title', 'upper']),
    ('klasanon', [('klas', 'klas'), ('an', 'an'), (None, 'on')],  ['lower', 'title', 'upper']),
    ('klasanojn',[('klas', 'klas'), ('an', 'an'), (None, 'ojn')], ['lower', 'title', 'upper']),
    ('misiad',   [('misi', 'misi'), ('ad', 'ad')],            ['lower', 'title', 'upper']),
    ('misiado',  [('misi', 'misi'), ('ad', 'ad'), (None, 'o')],   ['lower', 'title', 'upper']),
    ('vortanim', [('vort', 'vort'), ('anim', 'anim')],        ['lower', 'title', 'upper']),
    # ── 第91R: roman/o の語義が**両軌道で食い違っていた**(ルビ=ローマの / 漢字=小说)。
    #    gold は roman/o を2見出し持ち、**無印(主要義)が「{Ｂ}小説,長編小説」**、
    #    「【史】ローマ人」の方に ##偽分解(衝突語) が付く。つまりルビは衝突語側を出していた。
    #    京大コーパス本体も名詞形は全て長編小説:
    #        romano ×16 / romanojn ×10 / romanoj ×6 / romanon ×5 / Romano ×2 /
    #        Romanojn ×2 / romaneto ×4 / romaneton ×2  すべて roman[長編小説]
    #    語根CSVも roman=長編小説/小说/소설・et=弱小/小/작은 で一致(発明ゼロ)。
    #    ★形容詞形 romana* は触らない: gold が「小説の」と「ローマ人の##偽分解(衝突語)」の
    #      両方を持ち、京大はさらに第3の語義(ロマンス系の/ロマ)を使っているため。
    ('romano',    [('roman', 'roman'), (None, 'o')],          ['lower', 'title', 'upper']),
    ('romanoj',   [('roman', 'roman'), (None, 'oj')],         ['lower', 'title', 'upper']),
    ('romanon',   [('roman', 'roman'), (None, 'on')],         ['lower', 'title', 'upper']),
    ('romanojn',  [('roman', 'roman'), (None, 'ojn')],        ['lower', 'title', 'upper']),
    ('romaneto',  [('roman', 'roman'), ('et', 'et'), (None, 'o')],   ['lower', 'title', 'upper']),
    ('romanetoj', [('roman', 'roman'), ('et', 'et'), (None, 'oj')],  ['lower', 'title', 'upper']),
    ('romaneton', [('roman', 'roman'), ('et', 'et'), (None, 'on')],  ['lower', 'title', 'upper']),
    ('romanetojn',[('roman', 'roman'), ('et', 'et'), (None, 'ojn')], ['lower', 'title', 'upper']),
    # ★deven* は**意図的に外した**(第89Rで一度入れて実測で取り消した)。
    #   単独形は京大も de/ven と振る(deveno ×6, devenis ×4, devenaj ×1)が、
    #   **複合語の中では京大自身が deven[出身] を一語根として扱う**(hungardevena ×2)。
    #     アプリ before: hungar[ハンガリー] deven[起源] «a»   = 京大と一致
    #     入れた後     : hungar[ハンガリー] de[の;から] ven[来る] «a» = ★京大と食い違う
    #   このリストのキーは**パディング無し**の既存キーを差し替えるため語境界で止まらず、
    #   devenaj(1件)を直すと hungardevena(2件)を壊す。差し引きで損なので入れない。
    #   単独形と複合語内で扱いを変えるには語境界付きの別機構が要る(保留)。
]

# ── 約物パディング(エンジンの照合形を再現) ──────────────────────────
_BOL = chr(1)
_HAT12 = ''.join(chr(c) for c in (264, 265, 284, 285, 292, 293, 308, 309, 348, 349, 364, 365))
_LATEXT = chr(192) + '-' + chr(214) + chr(216) + '-' + chr(246) + chr(248) + '-' + chr(591)
_APOS = chr(39) + chr(8217)
_KEEP = ('A-Za-z0-9' + _HAT12 + _LATEXT + chr(37) + chr(64) + _APOS
         + ' ' + chr(10) + chr(13) + chr(1))
_PAD = re.compile('([^' + _KEEP + '])')
_LTR = 'A-Za-z' + _HAT12 + _LATEXT
_APOS_R = re.compile('[' + _APOS + '](?=[' + _LTR + '])')
def padkey(s):
    s = _PAD.sub(lambda m: ' ' + _BOL + m.group(1) + _BOL + ' ', s)
    return _APOS_R.sub(lambda m: m.group(0) + _BOL + ' ', s)

def splice(GG, new_rows):
    cand = [(i, padkey(e[0])) for i, e in enumerate(GG)
            if isinstance(e[0], str) and (' ' in e[0].strip() or _PAD.search(e[0]))]
    groups = collections.defaultdict(list)
    for r in new_rows:
        k = padkey(r[0]); p = 0
        for i, mk in cand:
            if len(mk) > len(k) and k in mk: p = max(p, i + 1)
        groups[p].append(r)
    out = list(GG)
    for p in sorted(groups, reverse=True):
        out[p:p] = groups[p]
    return out

def load_gloss(lang):
    d = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}', 'app_data')
    path = max(glob.glob(os.path.join(d, '*.csv')), key=os.path.getsize)
    g = {}
    with open(LP(path), encoding='utf-8', newline='') as fh:
        for row in csv.reader(fh):
            if row and row[0].strip():
                g.setdefault(row[0].strip(), row[1] if len(row) > 1 else '')
    return g, os.path.basename(path)

def cased(s, mode):
    if mode == 'lower': return s
    if mode == 'title': return s[:1].upper() + s[1:]
    return s.upper()

# ★語根CSVの値と**配信の実態**が食い違う接辞は、配信の多数派に合わせる。
#   実測(第91R): et は JA 弱小×8,019 / ZH 弱小×7,925 / KO 작음×7,952 が圧倒的多数で、
#   CSVの 小 / 작은 は少数派。CSVから引き直すと7,900行超と食い違う接辞になる。
#   京大コーパスも et[弱小] と振っている。 → aĵ(事物×9,834 vs CSV 物品×8) と同型の罠。
GLOSS_DEPLOYED_OVERRIDE = {
    'et': {'JA': '弱小', 'ZH': '弱小', 'KO': '작음'},
}
def gloss_of(lang, root, csv_map):
    ov = GLOSS_DEPLOYED_OVERRIDE.get(root)
    return ov[lang] if ov and lang in ov else csv_map[root]

# ── 語根グロスの在庫確認(1言語でも欠けたらその語を中止) ────────────────
GL = {}
for lang in ('JA', 'ZH', 'KO'):
    GL[lang], name = load_gloss(lang)
    print(f'[{lang}] 語根CSV: {name} ({len(GL[lang])} 語根)')
roots = sorted({r for _, ps, _ in TARGETS for r, _ in ps if r})
missing = {lang: [r for r in roots if r not in GL[lang]] for lang in GL}
print('必要な語根:', roots)
for lang, ms in missing.items():
    print(f'  [{lang}] 欠落: {ms if ms else "無し"}  ' +
          ' / '.join(f'{r}={GL[lang].get(r, "★")}' for r in roots))
bad_roots = {r for ms in missing.values() for r in ms}
if bad_roots:
    print(f'★グロスが欠けている語根があるため、それを含む対象は中止: {sorted(bad_roots)}')

plan = []
for word, pieces, cases in TARGETS:
    if any(r in bad_roots for r, _ in pieces if r):
        print(f'  skip {word}: グロス欠落'); continue
    for mode in cases:
        w = cased(word, mode)
        cp = []
        pos = 0
        for r, txt in pieces:
            seg = w[pos:pos + len(txt)]; pos += len(txt)
            cp.append((r, seg))
        if pos != len(w): raise SystemExit(f'片の長さが語形と合わない: {word}/{mode}')
        plan.append((w, cp))
print(f'\n対象語形 {len(plan)}: {[w for w, _ in plan]}')

# ── 3言語に適用 ────────────────────────────────────────────────
seg_of = {}
for lang in ('JA', 'ZH', 'KO'):
    app_dir = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}')
    path = os.path.join(app_dir, 'app_data', '置換リスト_ルビ.json')
    helper = load_app_replacement_helper(app_dir)
    cw = json.load(open(LP(os.path.join(app_dir, 'app_data', 'char_widths.json')), encoding='utf-8'))
    d = json.load(open(LP(path), encoding='utf-8'))
    gg = [e for e in d[KEY] if not (len(e) > 2 and isinstance(e[2], str) and MARK in e[2])]
    removed_prev = len(d[KEY]) - len(gg)
    used = {e[2] for e in gg if len(e) > 2 and isinstance(e[2], str)}
    where = {}
    for i, e in enumerate(gg):
        if isinstance(e[0], str): where.setdefault(e[0], i)

    rows = []; n_rep = 0
    for n, (w, cp) in enumerate(plan):
        val = ''.join(seg if r is None
                      else helper.output_format(seg, gloss_of(lang, r, GL[lang]), FMT, cw)
                      for r, seg in cp)
        # 検証: ルビを剥いだ表層が語形と一致するか
        vis = ''.join(TAG.sub('', m.group(1)) if m else '' for m in [None])  # placeholder
        vis = ''
        pos = 0
        for m in RUBY.finditer(val):
            if m.start() > pos: vis += TAG.sub('', val[pos:m.start()])
            vis += TAG.sub('', m.group(1)); pos = m.end()
        if pos < len(val): vis += TAG.sub('', val[pos:])
        if vis != w: raise SystemExit(f'表層不一致 {lang} {w}: {vis!r}')
        seg_of.setdefault(w, {})[lang] = '/'.join(TAG.sub('', m.group(1)) for m in RUBY.finditer(val))
        # 既存キー(パディング無し/有りの両方)を探す
        j = where.get(w)
        if j is None: j = where.get(' ' + w + ' ')
        if j is not None:
            gg[j] = [gg[j][0], val, gg[j][2] if len(gg[j]) > 2 else None]; n_rep += 1; continue
        ph = f' {MARK}{n:05d}{"" if lang == "JA" else lang}$ '
        if ph in used: raise SystemExit(f'placeholder collision: {ph}')
        rows.append([' ' + w + ' ', ' ' + val + ' ', ph])
    gg2 = splice(gg, rows)
    print(f'[{lang}] 既存値の差替 {n_rep} / 新規挿入 {len(rows)} '
          f'(前回投入 {removed_prev} 件を除去 / 全域 {len(d[KEY])} -> {len(gg2)})')
    if not DRY:
        d[KEY] = gg2
        atomic_file_copy(LP(path), LP(path + '.bak_preR81K'))
        atomic_json_dump(LP(path), d)

bad = [w for w, s in seg_of.items() if len(set(s.values())) != 1]
print(f'\n★3言語の分節一致: {"○ (不一致0)" if not bad else "× " + str(bad)}')
if bad: raise SystemExit('3言語で分節が食い違う: 中止')
for w, s in sorted(seg_of.items()):
    print(f'   {w:<12} {s["JA"]}')
print('\n(DRY-RUN: --apply で書込)' if DRY else '\n適用完了')
