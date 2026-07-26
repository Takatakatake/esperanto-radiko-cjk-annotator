# -*- coding: utf-8 -*-
"""第68R: ルビの語頭食い込み/境界欠陥を、マスター全語+実使用語彙の全数走査で是正する。
   DRY既定 / --apply で書込。

■ 何が壊れているか(実測)
  エンジンには「語頭から始まる一致を優先する」概念が無い。全域置換リストは
  生キー長に近い並びで上から text.replace していくだけなので、語の途中から始まる
  別語根が先に当たると語頭が裸で残り、**まったく別の語の訳語**が表示される。
      hore        → h + ore(漏出)          正: hor(一時間) + e
      portan      → p + ort(直角の) + an   正: port(運ぶ) + an   ※ortan(5字)がport(4字)に勝つ
      teatristoj  → trist(悲しい) + oj     正: teatr(劇場) + ist(従事者)
      fleganto    → f + leg(読む) + ant    正: fleg(看護する) + ant
      povuloj     → p + ov(卵) + ul + oj   正: pov(できる) + ul
      world       → w + orl(縁縫い) + d    英語にエス語根の誤ルビ
  約物入りキーはさらに厄介で、**パディング後の形**で照合されるのに位置は生キー長で
  決まる。接辞 'al-' (生3字) が 'mal-granda' の途中に当たり 'mal' を食う。

■ なぜ再生成ではなく後処理か
  ルビ軌道は Phase513→532→558 の認証連鎖にピン留めされており、生成物の並び順は
  こちらから作り直せない(apply_confirmed_now は gold ドリフトで fail-closed)。
  そこで漢字側 fix_kanji_master_residual.py と同じ「語スコープ後処理」で閉じる。

■ 適用方針(3階層。機械任せにしない)
  (1) MANUAL   : 手で組んだ部品列。既存エントリの描画のみ流用する。
  (2) RESEG    : 明示ホワイトリストの語だけ再分割する。
                 機械提案は実測で **悪化する例が多い**(apatia: pati(感受)→pat(フライパン)、
                 Kokoro: kor(心)→Kok(ニワトリ)+or(金) など)ため自動採用しない。
  (3) 自動全裸 : 語頭に語根が1つも一致しない語(=非エスペラント語・固有名詞)は
                 ルビを外す。誤った訳語を出すより無注釈のほうが学習者に無害。
  上記いずれにも該当しない欠陥語は **触らずに報告**する(マスター照会に回す)。

■ 安全設計
  1. 追加キーは空白パディングの完全一致キー。その語形にしか発火しない。
  2. 値は既存エントリの描画をそのまま連結。訳語を発明しない。
  3. 3言語で同じ部品列を使うので分節同一性は構成上保たれる。適用直前に再検証する。
  4. 現在の出力が実際に欠陥である語だけを対象にする。
"""
import json, os, re, sys, argparse, collections, hashlib
sys.stdout.reconfigure(encoding='utf-8')
BS = chr(92); PFX = BS * 2 + chr(63) + BS
def LP(p): return PFX + os.path.abspath(p)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, '_analysis_20260625'))
from atomic_json import atomic_file_copy, atomic_json_dump

MASTER = (r'D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学'
          r'\エスペラントの漢字化プロジェクト総結集20260630\エスペラント辞書徹底語根分解_20260630')
ap = argparse.ArgumentParser()
ap.add_argument('--apply', action='store_true')
ap.add_argument('--gold', default=os.path.join(
    MASTER, '世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416.txt'))
ap.add_argument('--corpus-words', default='')
ap.add_argument('--report', default='')
A = ap.parse_args()
DRY = not A.apply

KEY = '全域替换用のリスト(列表)型配列(replacements_final_list)'
RUBY = re.compile(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', re.S)
TAG = re.compile(r'<[^>]+>')
def struct(v): return re.sub(r'<rt[^>]*>.*?</rt>', '<rt/>', v, flags=re.S)
X = {'c^':'ĉ','g^':'ĝ','h^':'ĥ','j^':'ĵ','s^':'ŝ','u^':'ŭ',
     'C^':'Ĉ','G^':'Ĝ','H^':'Ĥ','J^':'Ĵ','S^':'Ŝ','U^':'Ŭ'}
def circ(s):
    for a, b in X.items(): s = s.replace(a, b)
    return s
L = "A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ"
END_RE = re.compile(r"(?:o|a|e|i|u|as|is|os|us)?j?n?'?", re.I)

# ── (1) 手組み: 既存エントリの描画を流用しつつ、gold の1片を保つ ──────────
#   RB(srckey, base) = srckey の描画から base のルビブロックだけを取り出して使う
MANUAL = {
    # gold は nor-adrenalin を1片とするが、その綴りの訳語は無い。ハイフン前を裸にして
    # adrenalin(アドレナリン) だけ残す。現状の or([化]金) という誤訳が消える。
    'nor-adrenalin': [('B', 'nor-'), ('R', 'adrenalin')],
    'nor-epinefrin': [('B', 'nor-'), ('R', 'epinefrin')],
    # kil(竜骨) が当たっている。kilometr(キロメートル) に粗化し、il は skribil から流用。
    'kilometril':    [('R', 'kilometr'), ('RB', 'skribil', 'il')],
    # gold=iniciator/o。現状 iniciat(始める)+or([化]金) と誤って割れている。
    'iniciator':     [('R', 'iniciator')],
    # gold=rin/o/plasti/o。現状 plast(プラスチック)。plasti(形成)が正しい。
    'rinoplasti':    [('R', 'rin'), ('B', 'o'), ('R', 'plasti')],
    # gold=a/toni/o。現状 ton(楽音)。toni(緊張)が正しい(【病】弛緩症)。
    'atoni':         [('B', 'a'), ('R', 'toni')],
    # gold=fleg/ant/o。現状 leg(読む)。
    'flegant':       [('R', 'flegant')],
    # gold=Kab/o-Verd/。現状 bo(姻戚)。
    'Kabo-Verd':     [('R', 'Kab'), ('B', 'o-'), ('R', 'Verd')],
    # gold=mal-vort/o。現状 al(~の方へ)。
    'mal-vort':      [('R', 'mal'), ('B', '-'), ('R', 'vort')],
}
MANUAL_ENDINGS = {
    'nor-adrenalin': ['o','on','oj','ojn','a','aj','an','ajn'],
    'nor-epinefrin': ['o','on','oj','ojn','a','aj','an','ajn'],
    'kilometril':    ['o','on','oj','ojn','a','aj','an','ajn'],
    'iniciator':     ['o','on','oj','ojn','a','aj','an','ajn','e','en'],
    'rinoplasti':    ['o','on','oj','ojn','a','aj','an','ajn'],
    'atoni':         ['o','on','oj','ojn','a','aj','an','ajn','e','en'],
    'flegant':       ['o','on','oj','ojn','a','aj','an','ajn','e','en'],
    'Kabo-Verd':     ['o','on','oj','ojn','a','aj','an','ajn'],
    'mal-vort':      ['o','on','oj','ojn','a','aj','an','ajn','e','en'],
}
MANUAL_CASES = {          # 固有名詞は綴り通りの大小のみ(小文字化すると別語になる)
    'Kabo-Verd': ['as-is'], 'nor-adrenalin': ['lower','Cap','UPPER'],
    'nor-epinefrin': ['lower','Cap','UPPER'], 'kilometril': ['lower','Cap','UPPER'],
    'iniciator': ['lower','Cap','UPPER'], 'rinoplasti': ['lower','Cap','UPPER'],
    'atoni': ['lower','Cap','UPPER'], 'flegant': ['lower','Cap','UPPER'],
    'mal-vort': ['lower','Cap','UPPER'],
}

# ── (2) 再分割を許す語(実測で提案が現状より良いと確認したものだけ) ────────
RESEG = {
    'for-': 'or([化]金) → for(遠くへ)',
    'mal-': 'al(~の方へ) → mal(正反対)',
    'vir-': 'ir(行く) → vir(男)',
    '-pov-': 'ov(卵) → pov(できる)',
    '-gene': 'en(中で) → gen(遺伝子)',
    '-stomi': 'tomi(切開) → stom(気孔)',
    'hore': 'ore(漏出) → hor(一時間)',
    'monulo': 'nul(ゼロ) → mon(かね)+ul(人)',
    'paperaĵojn': 'aper(現われる) → paper(紙)+aĵ(物)',
    'povuloj': 'ov(卵) → pov(できる)+ul(人)',
    'povulon': 'ov(卵) → pov(できる)+ul(人)',
    'teatristoj': 'trist(悲しい) → teatr(劇場)+ist(従事者)',
    'ŝtatuloj': 'tul(チュール) → ŝtat(国家)+ul(人)',
    'terara': 'erar(誤る) → ter(土地)+ar(群)',
    'portan': 'ort(直角の) → port(運ぶ)',
    'nekante': 'ek(開始) → nek(~もまた~ない)+ant',
    'nita': 'it(受動完了) → nit(リベット)',
    # ── 第69R追加: 京大エス研コーパスとの分節比較で見つかった**語中**の欠陥 ──
    #   第68Rは語頭食い込みだけを対象にしていたため、語頭から始まっていても
    #   途中の分節が誤っている語を取りこぼしていた。いずれも実在の普通の語。
    'eksterkastuloj': 'ek(開始)+sterk(家畜糞肥)+as+tul → ekster(外)+kast+ul  ※京大=ekster/kast/ul',
    'ordinarajn': 'or([化]金)+dinar(ディナール) → ordinar(普通の)  ※ordinara は正しいのに -ajn だけ壊れる',
    'ordinaraj': '同上',
    'fabrikistoj': 'fabrik+is(過去形) → fabrik(工場)+ist(従事者)  ※京大=fabrik/ist',
    'fabrikisto': '同上', 'fabrikiston': '同上', 'fabrikistojn': '同上',
    'teriĝi': 'teri(獣類) → ter(土地)+iĝ(なる)  ※京大=ter/iĝ',
    'teriĝo': '同上', 'teriĝis': '同上', 'teriĝas': '同上',
    'korona': 'kor(心) → koron(冠)+a  ※京大=korona',
    'bombaj': 'bombaj(ボンベイ) → bomb(爆弾)+aj  ※小文字形は爆弾の形容詞',
    'bombajn': '同上',
}
# RESEG は「語頭欠陥」の有無に関わらず処理する(語中の欠陥も対象にするため)
RESEG_FORCE = {'eksterkastuloj', 'ordinarajn', 'ordinaraj', 'fabrikistoj', 'fabrikisto',
               'fabrikiston', 'fabrikistojn', 'teriĝi', 'teriĝo', 'teriĝis', 'teriĝas',
               'korona', 'bombaj', 'bombajn'}
# ── 明示的に全裸化する語(語頭に語根はあるが、当てると意味を成さない) ──────
FORCE_BARE = {
    'glu-glu-glu': '擬音語(七面鳥の鳴き声)。glu(糊)を3つ当てるのは誤り',
    'mega-': 'SI接頭辞。訳語がマスターに無い(eg=強大 は別語)',
    'ultra-': '接頭辞。訳語がマスターに無い(tra=通って は別語)',
    'giga-': 'SI接頭辞。訳語がマスターに無い(gig=ギグ は別語)',
    'nano-': 'SI接頭辞。訳語がマスターに無い(nan=矮小 は別語)',
    'ramen': '借用語(ラーメン)。amen(アーメン)も ram(破城槌)も誤り',
    'SATan': 'SAT(世界無国民協会)の会員。訳語がマスターに無い。Tan(なめす)は誤り',
    'SieraNevad': 'gold=SieraNevad/o(1片)。Si(自分)は誤り',
    'Temis': 'gold=Temis(正義の女神)。Tem(主題)+is(過去)は誤り',
    'Kokoro': '日本語の固有名詞。Kok(ニワトリ)+or(金)も kor(心)も語形として偶然',
    'Kurenai': '日本語の固有名詞', 'MURAKAMI': '日本語の姓', 'LOMANOV': '固有名詞',
    'Merento': '固有名詞', 'Naviado': '固有名詞', 'Sagrada': '固有名詞(西語)',
    'Tusiama': '固有名詞', 'Suvan': '固有名詞', 'Ruta': '固有名詞', 'Pulau': '固有名詞(馬来語)',
    'Pitois': '固有名詞(仏語)', 'SUMI': '日本語の固有名詞', 'Lema': '固有名詞',
    'Bene': '固有名詞', 'HORI': '日本語の姓', 'derailed': '英語', 'dozen': '英語',
    'familje': '外国語', 'inatanon': '外国語', 'ĉikara': '日本語(力)のローマ字',
    'huma': 'URL断片(huma-num)', 'malkom': '行末ハイフン分割の断片(malkomforto)',
    'arbori': 'or([化]金)が誤り。語として不確実なため無注釈にする',
}
# ── 触らない(機械提案が現状より劣る/同綴異義)。マスター照会に回す ──────────
KEEP = {
    'sendota': 'gold=sen/dot/a(持参金のない)と実用 send/ot/a(送られるべき)の同綴異義',
    'pneŭmonokoniozo': 'gold準拠だと「肺+塵肺」。現状の「塵肺+症」のほうが明快',
    'hemoglobinurio': 'uri の訳語が鳥(ウミガラス属)のみ。gold準拠だと悪化',
    'hemoglobinemio': '単独emiキーはem(傾向)。現状の複合emi(血中量)が正しい',
    'kolesterolemio': '同上',
    'makrofago': '単独fagキーは「ブナ」。現状の複合fag(食)が正しい',
    'apatia': '現状 pati(感受) が正しい。提案 pat(フライパン) は誤り',
    'apatio': '同上', 'apatiulo': '同上',
    'ateismo': '現状 te(神)+ism(主義) のほうが情報量が多い',
    'atrofiiĝi': '現状 trofi(栄養)+iĝ(なる) のほうが情報量が多い',
    'abiogenezo': '現状 bio(生命)+genez(発生) のほうが情報量が多い',
    'agamia': '提案 ag(行動)+mi(私) は無意味',
    'aklimatizi': '現状 klimat(気候)+iz(化) のほうが情報量が多い',
    'anaerobia': '現状 aer(空気)+bi(生命) のほうが情報量が多い',
    'atonala': '現状 ton(調)+al(性) が正しい。提案 ton(楽音) は語義違い',
    'avitaminozo': '現状 vitamin+oz(症) のほうが情報量が多い',
    'arĥeologio': '現状 arĥe(考古)+logi(学) は意味として正しい(gold境界とのみ相違)',
    'arĥeologo': '同上', 'ektodermo': '現状 ekt(外)+derm(皮膚) は正しい',
    '-oto': '現状 ot(受動将然) が正しい',
}

# ── 3言語エントリ ────────────────────────────────────────────────
idx = {}
for lang in ('JA', 'ZH', 'KO'):
    p = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}', 'app_data', '置換リスト_ルビ.json')
    d = json.load(open(LP(p), encoding='utf-8'))
    m = {}
    for e in d[KEY]:
        if len(e) >= 2 and isinstance(e[0], str) and e[0] not in m:
            m[e[0]] = e[1]
    idx[lang] = m
SAFE = {}
for k, v in idx['JA'].items():
    if k != k.strip(): continue
    b, c = idx['ZH'].get(k), idx['KO'].get(k)
    if b is None or c is None: continue
    if struct(v) == struct(b) == struct(c): SAFE[k] = True
print(f'流用可能な部品キー(3言語で構造一致): {len(SAFE)}', flush=True)

gold_txt = open(LP(A.gold), 'rb').read()
print(f'gold: {os.path.basename(A.gold)} sha256={hashlib.sha256(gold_txt).hexdigest()[:16]}')
decomp, gold_words = {}, []
for ln in gold_txt.decode('utf-8', 'replace').splitlines():
    head = ln.split(':', 1)[0].strip()
    if not head or head.startswith('#'): continue
    h = circ(head); surf = h.replace('/', '')
    if ' ' in surf: continue
    if not re.fullmatch('[' + L + r"\-']{1,40}", surf): continue
    if surf in decomp: continue
    decomp[surf] = h; gold_words.append(surf)
print(f'gold 見出し語: {len(gold_words)}')
corpus_words = []
if A.corpus_words and os.path.exists(LP(A.corpus_words)):
    corpus_words = json.load(open(LP(A.corpus_words), encoding='utf-8'))['words']
    print(f'実使用語彙(コーパス): {len(corpus_words)}')

sys.path.insert(0, os.path.join(ROOT, 'Esperanto-Kanji-Ruby-JA'))
import esp_text_replacement_module as M
dJA = json.load(open(LP(os.path.join(ROOT, 'Esperanto-Kanji-Ruby-JA',
                                     'app_data', '置換リスト_ルビ.json')), encoding='utf-8'))
GLj = dJA['局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)']
G2j = dJA['二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)']
# 前回の投入分($R68W)を外した状態で「本来どう出るか」を測る(再実行できるように)。
# これをしないと、適用済みのリストに対して走査してしまい欠陥が0件に見える。
GGj = [e for e in dJA[KEY] if not (len(e) > 2 and isinstance(e[2], str) and '$R68W' in e[2])]
psj = M.import_placeholders(os.path.join(ROOT, 'Esperanto-Kanji-Ruby-JA', 'app_data', 'placeholders_skip.txt'))
plj = M.import_placeholders(os.path.join(ROOT, 'Esperanto-Kanji-Ruby-JA', 'app_data', 'placeholders_localcapture.txt'))
def conv(t):
    return M.orchestrate_comprehensive_esperanto_text_replacement(
        t, psj, GLj, plj, GGj, G2j, 'HTML格式_Ruby文字_大小调整')

def head_defect(word, out):
    ms = list(RUBY.finditer(out))
    if not ms: return False
    head = TAG.sub('', out[:ms[0].start()]).strip()
    if not head: return False
    if re.fullmatch(r"[-']+", head): return False
    if re.fullmatch('[' + L + r"]{1,4}-", head): return False     # E- A- esp- 等の略号接頭辞
    # gold の第1片がそのまま裸で残っているだけなら正常(欠如の a-, 前置詞的要素など)。
    #   afonio = a/fon/i/o → 'a' が裸なのは仕様どおり。ここを欠陥にすると偽陽性が20件出る。
    g = decomp.get(word)
    if g:
        first = [p for p in g.split('/') if p]
        if first and head.lower() == first[0].lower(): return False
    return True

def bare_ok(s): return bool(s) and END_RE.fullmatch(s) is not None

def dp_segment(w):
    """語頭から始まる分割。第一語根を最長にし、次に被覆最大・片数最小。
       語頭に語根が無ければ None (=非エスペラント語と判定)。"""
    memo = {}
    def best(i):
        if i == len(w): return (0, 0, [])
        if i in memo: return memo[i]
        cands = []
        for ln in range(min(len(w) - i, 24), 1, -1):
            c = w[i:i+ln]
            if c in SAFE:
                sub = best(i + ln)
                if sub is not None:
                    cands.append((sub[0] + ln, sub[1] + 1, [('R', c)] + sub[2]))
        if w[i] in "-'":
            sub = best(i + 1)
            if sub is not None: cands.append((sub[0], sub[1] + 1, [('B', w[i])] + sub[2]))
        if i > 0 and w[i].lower() in 'aeiouĉŭ' and i + 1 < len(w):
            sub = best(i + 1)
            if sub is not None: cands.append((sub[0], sub[1] + 1, [('B', w[i])] + sub[2]))
        if i > 0 and bare_ok(w[i:]):
            cands.append((0, 1, [('B', w[i:])]))
        memo[i] = max(cands, key=lambda x: (x[0], -x[1])) if cands else None
        return memo[i]
    # 第一語根を最長にする: 語頭で取れる最長の語根を固定してから残りを解く
    for ln in range(min(len(w), 24), 1, -1):
        c = w[:ln]
        if c not in SAFE: continue
        memo.clear()
        sub = best(ln)
        if sub is not None: return [('R', c)] + sub[2]
    if w and w[0] in "-'":
        memo.clear(); sub = best(1)
        if sub is not None: return [('B', w[0])] + sub[2]
    return None

def gold_segment(w, gold_h):
    out = []
    for p in [x for x in gold_h.split('/') if x]:
        if p in SAFE: out.append(('R', p)); continue
        sub = [s for s in re.split(r"([-'])", p) if s]
        tmp, ok = [], True
        for s in sub:
            if s in SAFE: tmp.append(('R', s))
            elif s in "-'" or bare_ok(s): tmp.append(('B', s))
            else: ok = False; break
        out.extend(tmp if ok else [('B', p)])
    return out

def rb_block(srckey, base):
    """srckey の描画から base のルビブロックだけを取り出す(言語ごと)。"""
    res = {}
    for lang in ('JA', 'ZH', 'KO'):
        v = idx[lang].get(srckey)
        if v is None: return None
        hit = None
        for m in RUBY.finditer(v):
            if m.group(1) == base: hit = m.group(0); break
        if hit is None: return None
        res[lang] = hit
    return res

def compose(word, pieces):
    res = {}
    for lang in ('JA', 'ZH', 'KO'):
        buf = []
        for pc in pieces:
            if pc[0] == 'R':
                v = idx[lang].get(pc[1])
                if v is None: return None
                buf.append(v)
            elif pc[0] == 'RB':
                blk = rb_block(pc[1], pc[2])
                if blk is None: return None
                buf.append(blk[lang])
            else: buf.append(pc[1])
        res[lang] = ''.join(buf)
    if not (struct(res['JA']) == struct(res['ZH']) == struct(res['KO'])): return None
    plain = TAG.sub('', re.sub(r'<rt[^>]*>.*?</rt>', '', res['JA'], flags=re.S))
    if plain != word: return None
    return res

def case_apply(pieces, mode):
    if mode == 'lower': f = str.lower
    elif mode == 'UPPER': f = str.upper
    else: f = None
    out = []
    for n, pc in enumerate(pieces):
        if mode == 'Cap':
            if n == 0:
                if pc[0] == 'R': out.append(('R', pc[1][0].upper() + pc[1][1:]))
                elif pc[0] == 'RB': out.append(('RB', pc[1][0].upper() + pc[1][1:], pc[2][0].upper() + pc[2][1:]))
                else: out.append(('B', pc[1][0].upper() + pc[1][1:]))
            else: out.append(pc)
        elif f is None: out.append(pc)
        else:
            out.append((pc[0],) + tuple(f(x) for x in pc[1:]))
    return out

# ── 走査 ────────────────────────────────────────────────────────
targets, seen = [], set()
for src, lst in (('gold', gold_words), ('corpus', corpus_words)):
    for w in lst:
        if w in seen: continue
        seen.add(w); targets.append((src, w))
print(f'走査対象: {len(targets)} 語', flush=True)
SEP = '◆'; B = 600
cur = {}
allw = [w for _, w in targets]
for i in range(0, len(allw), B):
    ch = allw[i:i+B]
    o = conv(' ' + (' ' + SEP + ' ').join(ch) + ' ')
    parts = o.split(SEP)
    if len(parts) != len(ch): parts = [conv(' ' + w + ' ') for w in ch]
    for w, s in zip(ch, parts): cur[w] = s.strip()
    if i % 15000 == 0: print(f'  走査 {i}/{len(allw)}', flush=True)

# ── 追加キーの構築 ──────────────────────────────────────────────
entries = []        # (キー(素), {lang: 値}, 理由)
_pieces_of = {}     # 語 -> 部品列(大小変種の展開に使う)
_added = set()
def add(word, pieces, why):
    if word in _added: return False            # 二重登録の防止
    built = compose(word, pieces)
    if built is None: return False
    if word in cur and struct(built['JA']).strip() == struct(cur[word]).strip(): return False
    entries.append((word, built, why)); _added.add(word)
    _pieces_of[word] = pieces
    return True

def bases(v): return '/'.join(m.group(1) for m in RUBY.finditer(v))

# (1) 手組み(語尾・大小変種つき)
man_added = 0
for stem, pieces in MANUAL.items():
    modes = MANUAL_CASES.get(stem, ['as-is'])
    for mode in modes:
        ps_ = pieces if mode == 'as-is' else case_apply(pieces, mode)
        stem_c = stem if mode == 'as-is' else (
            stem.lower() if mode == 'lower' else stem.upper() if mode == 'UPPER'
            else stem[0].upper() + stem[1:])
        for end in MANUAL_ENDINGS[stem]:
            e2 = end.upper() if mode == 'UPPER' else end
            w = stem_c + e2
            if add(w, ps_ + [('B', e2)], f'MANUAL:{stem}'): man_added += 1
# 語尾を持たない固有名詞・擬音語
for w, why in (('Temis', FORCE_BARE['Temis']), ('Temiso', FORCE_BARE['Temis']),
               ('glu-glu-glu', FORCE_BARE['glu-glu-glu'])):
    add(w, [('B', w)], f'BARE:{why}')

# (2)(3) 走査結果に基づく処理
stat = collections.Counter()
skipped = []
for src, w in targets:
    out = cur[w]
    # RESEG_FORCE は語頭欠陥が無くても処理する(語中の分節誤りを拾うため)
    if not head_defect(w, out) and w not in RESEG_FORCE: continue
    if w in _added: stat['手組みで対応済'] += 1; continue
    if w in KEEP: stat['据置(照会)'] += 1; skipped.append((w, 'KEEP: ' + KEEP[w])); continue
    base = w
    for s in FORCE_BARE:
        if w == s or (w.startswith(s) and bare_ok(w[len(s):])): base = s; break
    if base in FORCE_BARE:
        if add(w, [('B', w)], f'BARE:{FORCE_BARE[base]}'): stat['全裸(明示)'] += 1
        continue
    if w in RESEG:
        pieces = gold_segment(w, decomp[w]) if w in decomp else dp_segment(w)
        if pieces and add(w, pieces, f'RESEG:{RESEG[w]}'): stat['再分割(承認)'] += 1
        continue
    if dp_segment(w) is None:                       # 語頭に語根が無い = 非エスペラント語
        if add(w, [('B', w)], 'BARE:語頭に語根が一致しない(非エスペラント語と判定)'):
            stat['全裸(自動)'] += 1
        continue
    stat['未処理(要照会)'] += 1
    skipped.append((w, '未処理: 語頭欠陥だが再分割の妥当性が未確認'))

# ── RESEG_FORCE の取りこぼし補完 ────────────────────────────────
#   走査対象は gold見出し + コーパス語彙なので、そこに無い語形(fabrikisto 等の
#   常用語の別活用)は上の走査で処理されない。明示ホワイトリストは必ず処理する。
_rf = [w for w in RESEG_FORCE if w not in _added and w not in cur]
if _rf:
    for i in range(0, len(_rf), B):
        ch = _rf[i:i+B]
        o = conv(' ' + (' ' + SEP + ' ').join(ch) + ' ')
        parts = o.split(SEP)
        if len(parts) != len(ch): parts = [conv(' ' + w + ' ') for w in ch]
        for w, s_ in zip(ch, parts): cur[w] = s_.strip()
    _n = 0
    for w in _rf:
        pieces = gold_segment(w, decomp[w]) if w in decomp else dp_segment(w)
        if pieces and add(w, pieces, f'RESEG:{RESEG.get(w, "")}'): _n += 1
    print(f'RESEG_FORCE の取りこぼし補完: {_n} 件(候補 {len(_rf)})')

# ── 大小変種の補完 ──────────────────────────────────────────────
#   走査対象(gold見出し+コーパス語彙)に現れなかった変種は素通りしてしまう。
#   実測: teatristoj は直ったが **文頭大文字の Teatristoj は trist(悲しい) のまま**だった。
#   文頭大文字は実文で頻出するので、同じ欠陥が出る変種にだけ同じ是正を与える。
_var_todo = []
for _w in list(_added):
    for _v in (_w[0].upper() + _w[1:], _w.upper(), _w.lower()):
        if _v == _w or _v in _added: continue
        # 固有名詞・略号は綴りの大小自体が語を決めるので、小文字化は行わない
        if _v == _w.lower() and _w != _w.lower(): continue
        _var_todo.append((_v, _w))
_seen_v = set()
_var_todo = [(v, w) for v, w in _var_todo if not (v in _seen_v or _seen_v.add(v))]
if _var_todo:
    _vw = [v for v, _ in _var_todo]
    for i in range(0, len(_vw), B):
        ch = _vw[i:i+B]
        o = conv(' ' + (' ' + SEP + ' ').join(ch) + ' ')
        parts = o.split(SEP)
        if len(parts) != len(ch): parts = [conv(' ' + w + ' ') for w in ch]
        for w, s in zip(ch, parts): cur[w] = s.strip()
    _nv = 0
    for v, w in _var_todo:
        # RESEG_FORCE 由来は「語中の欠陥」なので head_defect では捕まらない。
        # その変種も同じ誤り方をしているため、明示的に通す(最終の検証パスで
        # 描画が変わらないものは落ちる)。
        if not head_defect(v, cur[v]) and w not in RESEG_FORCE: continue
        ps_v = case_apply(_pieces_of[w], 'UPPER' if v == w.upper() else 'Cap')
        if add(v, ps_v, f'VAR:{w}'): _nv += 1
    print(f'大小変種の補完: {_nv} 件を追加(候補 {len(_var_todo)})')

def show(v): return ' + '.join(f'{b}({TAG.sub("", g)[:14]})' for b, g in RUBY.findall(v)) or '(ルビ無)'

# ── 検証パス: 候補語をすべて実変換し、現状と描画が変わるものだけ残す ──────
#   (手組み展開は未走査の語形を含む。現状が既に正しい語にキーを足さない。)
todo = [w for w, _, _ in entries if w not in cur]
for i in range(0, len(todo), B):
    ch = todo[i:i+B]
    o = conv(' ' + (' ' + SEP + ' ').join(ch) + ' ')
    parts = o.split(SEP)
    if len(parts) != len(ch): parts = [conv(' ' + w + ' ') for w in ch]
    for w, s in zip(ch, parts): cur[w] = s.strip()
before = len(entries)
entries = [(w, b, why) for w, b, why in entries if bases(cur.get(w, '')) != bases(b['JA'])]
print(f'検証パス: {before} → {len(entries)} 件 (現状と描画が同一のものを {before-len(entries)} 件除外)')
print()
print('=' * 96)
print(f'追加キー候補: {len(entries)} 件  内訳: ' + ' / '.join(f'{k}={v}' for k, v in stat.most_common())
      + f' / 手組み展開={man_added}')
for w, built, why in entries:
    if why.startswith('BARE:語頭'): continue
    print(f'  {w:<22} {show(cur.get(w, "")):<40} → {show(built["JA"]):<34} [{why[:46]}]')
auto = [e for e in entries if e[2].startswith('BARE:語頭')]
print(f'  --- 自動全裸(非エスペラント語) {len(auto)} 件。例20 ---')
for w, built, why in auto[:20]:
    print(f'     {w:<20} {show(cur.get(w, ""))}')
print(f'\n未処理・据置 {len(skipped)} 件(マスター照会へ)')
for w, r in skipped[:40]: print(f'     {w:<22} {r[:70]}')

if A.report:
    json.dump({'entries': [{'w': w, 'why': why, 'cur': cur.get(w, ''), 'new': b}
                           for w, b, why in entries],
               'skipped': skipped, 'stat': dict(stat)},
              open(LP(A.report), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'report saved: {A.report}')

if DRY:
    print('\n(DRY-RUN: --apply で書込)')
    sys.exit(0)

# ── 適用 ────────────────────────────────────────────────────────
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
    """エンジンが照合時に使う「約物パディング後の形」を再現する。"""
    s = _PAD.sub(lambda m: ' ' + _BOL + m.group(1) + _BOL + ' ', s)
    return _APOS_R.sub(lambda m: m.group(0) + _BOL + ' ', s)

def splice(GG, new_rows):
    """新エントリを「自分を部分文字列として含む既存キーの直後、無ければ先頭」に差し込む。

    ★単純な先頭挿入は不可(実測):
      ' Aires ' を先頭に置くと語句キー ' Buenos Aires ' より先に発火し、
      審査済みの語句単位エントリ(REVIEWED_TYPED_EXACT_TARGETS)を潰す。
      test_generation_regressions が Buenos Aires 等 164語で落ちた。
    ★「長さ順の位置」も不可(実測):
      全域リストは厳密な長さ降順ではないため「長さ>=Lの最終index」が 505,220 まで下がり、
      パディング無しの旧全語キー(例 'atonio' idx=497,304)に負けて是正が効かなかった。
    ★包含判定は **パディング後の形** で行う(実測):
      'Buraku-min' はテキスト側が ' Buraku ␁-␁ min ' になるため、生の文字列では
      ' Buraku ' を含まないのに実際には内部一致する(Mikulicz-Radecki 等15語で落ちた)。
    """
    cand = [(i, padkey(e[0])) for i, e in enumerate(GG)
            if isinstance(e[0], str) and (' ' in e[0].strip() or _PAD.search(e[0]))]
    groups = collections.defaultdict(list)
    for r in new_rows:
        k = padkey(r[0]); p = 0
        for i, mk in cand:
            if len(mk) > len(k) and k in mk: p = max(p, i + 1)
        groups[p].append(r)
    out = list(GG)
    for p in sorted(groups, reverse=True):          # 後ろの位置から順に挿入
        out[p:p] = groups[p]
    return out

for lang in ('JA', 'ZH', 'KO'):
    path = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}', 'app_data', '置換リスト_ルビ.json')
    d = json.load(open(LP(path), encoding='utf-8'))
    # 再実行できるように、前回の投入分($R68W)をいったん取り除いてから入れ直す
    GG = [e for e in d[KEY]
          if not (len(e) > 2 and isinstance(e[2], str) and '$R68W' in e[2])]
    used = {e[2] for e in GG if len(e) > 2}
    # 既に同じ語境界キーがある場合は **その場で値を差し替える**。
    # 同キーを別途足すとリスト内に重複キーが生まれ、test_generation_regressions の
    # "global contains duplicate old keys" で落ちる(実測: ' Auster ')。
    where = {}
    for i, e in enumerate(GG):
        if isinstance(e[0], str) and e[0] not in where: where[e[0]] = i
    rows, replaced = [], 0
    for n, (w, built, why) in enumerate(entries):
        key = ' ' + w + ' '
        val = ' ' + built[lang] + ' '
        j = where.get(key)
        if j is not None:
            GG[j] = [key, val, GG[j][2]]
            replaced += 1
            continue
        ph = f' $R68W{n:05d}{"" if lang == "JA" else lang}$ '
        if ph in used: raise SystemExit(f'placeholder collision: {ph}')
        rows.append([key, val, ph])
    d[KEY] = splice(GG, rows)
    atomic_file_copy(LP(path), LP(path + '.bak_preR68W'))
    atomic_json_dump(LP(path), d)
    print(f'[{lang}] 語句キーの直後/先頭に挿入 {len(rows)} / 既存値の差替 {replaced} '
          f'(全域 {len(GG)} -> {len(d[KEY])})')
print('適用完了')
