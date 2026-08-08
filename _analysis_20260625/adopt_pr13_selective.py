# -*- coding: utf-8 -*-
"""第99R: 別セッションのPR#13(bc56874)から、**良いと判定した変更だけ**を選択的に取り込む。
   DRY既定 / --apply。読み取りは git show のみで、PRブランチをマージしない。

■ なぜ選択取り込みか
  PR#13 は現main(cfa1fcb=第98R)を親に持ち、私の第91〜98Rの訳語裁定は保存されている。
  GL(局部50,546行)・G2(330行)は完全不変で、変更は GG のみ:
      純追加 528行(3言語とも) / 同キーの置き換え 51行
  実描画で検証した結果、**大半は良い改善**だが**1件だけ退行**が混じっていた。

■ ★除外する変更: mukoz 族のパディング付与(12キー×3言語)
      PR#13:  ' mukozo ' → mukoz[粘膜]     を新設(パディング付き)
              しかし裸の語幹 'mukoz' は muk[粘液] oz[膜] のまま
      結果:   submukozo が sub[下に] mukoz[粘膜]o → sub[下に] muk[粘液] oz[膜]o に**退行**
              (パディング付きキーは語境界で止まるので、複合語が古い分解の裸キーへ落ちる)
  ★これは第94Rで私が実測し「直すと退行するので採用しない」と判定した現象そのもの。
    ルビ軌道は粗い側なので mukoz[粘膜] が正しく、muk+oz は漢字軌道の深い分解。
    実害は限定的(マスター62k・京大22,133語に mukozo を含む別語は0件)だが、
    退行を1件でも入れない方針に従って除外する。

■ 取り込む変更(実描画で改善を確認済み)
  ・radio 系のキー単位追加(97行): radioprogramojn/radio-elsendojn 等
      radioprogramo が radi[光線]o program → radio[ラジオ] program に改善。
      ★裸の radio 語根は不変なので sunradioj → sun[太陽] radi[光線]oj は無傷
      (私の第98R裁定「radio の裸の語根は触らない」と完全に整合)
  ・miksdeven 系: miks de ven → miks[混ぜる] deven[起源] に改善
  ・aŭg./sept. 等の略語タグ整合
  ・hongkong/sam/nederland/kore/premi/ĉin/mult/dek/reprezent/apud 等の語尾変化形の充填

■ ★★現mainの「並び順」を保つ(第99Rで実際に踏んだ罠)
  PR は GG を再生成しており、**行の集合が同じでも並び順が変わっている**。
  `preserve_r67_r68_ruby_overlays.py` の封印ゲートは
      sources = [row[0] for row in rows]   # ★順序付きリスト
      sources_sha256 = sha256(json.dumps(sources))
  と順序込みで SHA を取るため、R68W(1,012行)の並びが変わっただけで fail した
  (件数1012も集合も同一なのに SHA だけ違う。集合で比較していると気づけない)。
  → 本スクリプトは **PR の並びを採らず、現main の並びを完全に保持**する。
     新規行だけを「PR で直前に来る既存行」の後ろに差し込む。
     こうすると R67H/R68W の相対順序は不変なので封印ゲートが緑のまま通る。

■ 安全設計
  1. PRブランチを**マージしない**。git show で読み、行単位で選別して現mainへ適用する。
  2. 除外リスト(EXCLUDE_STEMS)に該当するキーは、追加も置換も一切行わない。
  3. GL/G2 は触らない(PR側も不変であることを fail-closed で検証)。
  4. ★現mainの行順を保持し、共通キーの行は**値だけ** PR 版に更新する。
  5. 適用後、キー数・重複キー・分節の3言語一致・封印オーバーレイの順序を検証する。
  6. 冪等(同じ内容なら何度実行しても差分ゼロ)。
"""
import argparse, collections, json, os, re, subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')
BS = chr(92); PFX = BS * 2 + chr(63) + BS
def LP(p): return PFX + os.path.abspath(p)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, '_analysis_20260625'))
from atomic_json import atomic_file_copy, atomic_json_dump

ap = argparse.ArgumentParser()
ap.add_argument('--apply', action='store_true')
ap.add_argument('--source', default='bc56874', help='取り込み元のリビジョン')
ap.add_argument('--report', default='')
A = ap.parse_args()
DRY = not A.apply
LISTS = ['局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)',
         '二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)',
         '全域替换用のリスト(列表)型配列(replacements_final_list)']
GGK = LISTS[2]
RUBY = re.compile(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', re.S)
TAG = re.compile(r'<[^>]+>'); BR = re.compile(r'<br\s*/?>')

# ★除外: mukoz 族のパディング付与(裸の語幹が古い分解のままなので複合語が退行する)
EXCLUDE_STEMS = ('mukoz',)
def excluded(key):
    k = key.strip().lower()
    return any(k.startswith(s) for s in EXCLUDE_STEMS)

def load(rev, lang):
    rel = f'Esperanto-Kanji-Ruby-{lang}/app_data/置換リスト_ルビ.json'
    out = subprocess.run(['git', '-C', ROOT, 'show', f'{rev}:{rel}'], capture_output=True)
    if out.returncode != 0:
        raise SystemExit(f'★git show 失敗 {rev} {lang}')
    return json.loads(out.stdout.decode('utf-8'))

plan = {}; stat = collections.Counter(); samples = collections.defaultdict(list)
for lang in ('JA', 'ZH', 'KO'):
    cur = json.load(open(LP(os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}',
                                         'app_data', '置換リスト_ルビ.json')), encoding='utf-8'))
    src = load(A.source, lang)
    # GL/G2 が本当に不変か検証(fail-closed)
    for i in (0, 1):
        if cur[LISTS[i]] != src[LISTS[i]]:
            raise SystemExit(f'★{lang} の {("GL","G2")[i]} が PR 側で変わっている: 中止')
    a, b = cur[GGK], src[GGK]
    ca = collections.Counter((str(e[0]), str(e[1])) for e in a)
    cb = collections.Counter((str(e[0]), str(e[1])) for e in b)
    add = list((cb - ca).elements()); rem = list((ca - cb).elements())
    # 取り込む行 = PR側にあって現mainに無い行のうち、除外対象でないもの
    take = [(k, v) for k, v in add if not excluded(k)]
    skip_add = [(k, v) for k, v in add if excluded(k)]
    # 現mainにあってPR側に無い行のうち、除外対象でないもの = 置換の旧側(消してよい)
    drop = [(k, v) for k, v in rem if not excluded(k)]
    keep_rem = [(k, v) for k, v in rem if excluded(k)]
    stat[f'{lang}:取り込む追加'] += len(take)
    stat[f'{lang}:★除外した追加'] += len(skip_add)
    stat[f'{lang}:置換で消す旧行'] += len(drop)
    stat[f'{lang}:★除外で残す旧行'] += len(keep_rem)
    plan[lang] = {'take': take, 'drop': drop, 'src': b}
    if lang == 'JA':
        for k, v in sorted(skip_add)[:6]:
            samples['除外(追加)'].append((k, v[:70]))
        for k, v in sorted(keep_rem)[:6]:
            samples['除外(残す)'].append((k, v[:70]))
        roots = collections.Counter()
        for k, v in take:
            m = RUBY.search(v)
            roots[TAG.sub('', m.group(1)).lower() if m else '(なし)'] += 1
        samples['取り込む語根'] = roots.most_common(14)
print('内訳: ' + ' / '.join(f'{k}={v}' for k, v in sorted(stat.items())))
print('\n取り込む行の語根内訳(JA): ' + str(samples['取り込む語根']))
print('\n★除外した行(JA):')
for k, v in samples['除外(追加)']: print(f'   追加せず  {k!r} -> {v!r}')
for k, v in samples['除外(残す)']: print(f'   残す      {k!r} -> {v!r}')

# 3言語で取り込む行数が揃っているか
n = [len(plan[l]['take']) for l in ('JA', 'ZH', 'KO')]
print(f'\n3言語の取り込み行数: JA={n[0]} ZH={n[1]} KO={n[2]}')
ka = [set(k for k, _ in plan[l]['take']) for l in ('JA', 'ZH', 'KO')]
if not (ka[0] == ka[1] == ka[2]):
    d = (ka[0] ^ ka[1]) | (ka[1] ^ ka[2])
    print(f'  ★3言語で取り込むキー集合が違う {len(d)} 件: {sorted(d)[:6]}')
else:
    print('  3言語で取り込むキー集合が同一: ○')

if A.report:
    json.dump({'stat': dict(stat),
               'take_sample': {l: [[k, v[:120]] for k, v in plan[l]['take'][:20]] for l in plan},
               'excluded': {'add': samples['除外(追加)'], 'keep': samples['除外(残す)']}},
              open(LP(A.report), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
if DRY:
    print('\n(DRY-RUN: --apply で書込)'); sys.exit(0)

for lang in ('JA', 'ZH', 'KO'):
    path = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}', 'app_data', '置換リスト_ルビ.json')
    d = json.load(open(LP(path), encoding='utf-8'))
    src = plan[lang]['src']
    cur_rows = d[GGK]
    cur_keys = [str(e[0]) for e in cur_rows]
    cur_set = set(cur_keys)
    # ---- ① PR側で「新規キー」を、直前に来る共通キーへ紐づける(アンカー) ----
    pr_by_key = {}
    anchored = collections.defaultdict(list)   # anchor_key -> [新規行…]
    head_new = []                              # 先頭(共通キーより前)の新規行
    last_common = None
    for e in src:
        k = str(e[0])
        if excluded(k): continue               # 除外キーはPR側から一切採らない
        if k in cur_set:
            pr_by_key[k] = e
            last_common = k
        else:
            (anchored[last_common] if last_common is not None else head_new).append(e)
    # ---- ①-b 新規行のIDを、現mainの未使用番号帯へ振り直す ----
    #   ★PRは全体を再生成してIDを振り直しているため、PRのIDをそのまま使うと
    #     現mainの既存IDと衝突する(実測305件)。IDは置換の内部トークンなので
    #     重複すると壊れる。現mainのIDは1つも動かさず、新規行にだけ新番号を配る。
    IDPAT = re.compile(r'^(\s*)\$(\d+)(up|cap|pc)?\$(\s*)$')
    used = set()
    maxn = 0
    for e in cur_rows:
        s = str(e[2]) if len(e) > 2 else ''
        used.add(s)
        m = IDPAT.match(s)
        if m: maxn = max(maxn, int(m.group(2)))
    counter = [maxn + 1]                        # 次に配る基番号(リストで包んで可変に)
    remap = {}                                  # PRの基番号 -> 新しい基番号
    def fresh(pr_id):
        m = IDPAT.match(str(pr_id))
        if not m:
            raise SystemExit(f'★新規行のIDが想定書式でない: {pr_id!r}')
        base, suf = int(m.group(2)), (m.group(3) or '')
        if base not in remap:
            remap[base] = counter[0]; counter[0] += 1
        nid = f' ${remap[base]}{suf}$ '
        if nid in used:
            raise SystemExit(f'★採番したIDが既存と衝突: {nid!r}')
        return nid
    # ---- ② 現mainの並びを保ったまま出力。共通キーは値だけPR版へ ----
    out = list(head_new)
    n_val = n_new = n_drop = n_keep_ex = 0
    for e in cur_rows:
        k = str(e[0])
        if excluded(k):
            out.append(e); n_keep_ex += 1      # 除外キーは現mainのまま温存
        elif k in pr_by_key:
            pe = pr_by_key[k]
            if str(pe[1]) != str(e[1]):
                # ★値だけ更新し、IDは現mainのものを保つ(IDチャーンを起こさない)
                out.append([e[0], pe[1]] + list(e[2:])); n_val += 1
            else:
                out.append(e)                  # 完全に同じなら現mainの行をそのまま
        else:
            n_drop += 1                        # PR が消したキー(置換の旧側)
            continue
        for ne in anchored.get(k, []):
            out.append([ne[0], ne[1], fresh(ne[2] if len(ne) > 2 else '')]); n_new += 1
    # 採番後の重複検査(fail-closed)
    ids = [str(r[2]) for r in out if len(r) > 2]
    if len(ids) != len(set(ids)):
        c = collections.Counter(ids)
        raise SystemExit(f'★ID重複 {sum(1 for v in c.values() if v > 1)} 件: 中止')
    ks = [str(r[0]) for r in out]
    if len(ks) != len(set(ks)):
        raise SystemExit('★キー重複: 中止')
    d[GGK] = out
    atomic_file_copy(LP(path), LP(path + '.bak_preR99A'))
    atomic_json_dump(LP(path), d)
    print(f'[{lang}] GG {len(cur_rows):,} -> {len(out):,}  '
          f'(新規挿入 {n_new} / 値更新 {n_val} / 旧行削除 {n_drop} / 除外キー温存 {n_keep_ex})')
print('適用完了')
