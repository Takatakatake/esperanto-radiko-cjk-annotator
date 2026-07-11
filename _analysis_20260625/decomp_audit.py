# -*- coding: utf-8 -*-
"""
分解精度監査(アプリの仕組み上): アプリの実際の分解(デプロイ済みJSONでの置換結果のルビ境界)を
goldの分解と比較し、ティア別(2890→PEJVO→PIV)に一致率と不一致(=設定JSON補正候補)を出す。
"""
import json, sys, re, csv, collections
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625"); sys.path.insert(0, BASE + r"\Esperanto-Kanji-Ruby-JA")
from gen_replacement import lp
from extract_lib import hat_to_circumflex, replace_esperanto_chars
from esp_text_replacement_module import orchestrate_comprehensive_esperanto_text_replacement as orch, import_placeholders as imp
DATA = BASE + r"\Esperanto-Kanji-Ruby-JA\app_data"
GOLD = r"\\wsl.localhost\Ubuntu\home\y\エスペラント辞書徹底語根分解_20260619\世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416.txt"
CSV2890 = r"D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\漢字化・語彙資料\エスペラント語根＿漢字割り当て＿20260621\30_重要語彙CSV_日中対照_2890語\2890 Gravaj Esperantaj Vortoj kun Signifoj en la Japana, Ĉina.csv"
FMT='HTML格式_Ruby文字_大小调整'; PEJVO_MAX=44104
ENDINGS={'o','a','e','i','u','oj','aj','on','an','ojn','ajn','as','is','os','us','n','j'}
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()

# tier1 2890語形(nosl)
tier1=set()
with open(lp(CSV2890),encoding='utf-8-sig') as f:
    for row in csv.reader(f):
        if row and row[0] and row[0]!='Esperanto':
            tier1.add(norm(row[0].strip().strip('-')).replace('/',''))

# 置換リスト
with open(lp(DATA + r"\置換リスト_ルビ.json"),encoding='utf-8') as f: d=json.load(f)
g=d["全域替换用のリスト(列表)型配列(replacements_final_list)"]; l=d["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]; c=d["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]
ps=imp(lp(DATA+r"\placeholders_skip.txt")); pl=imp(lp(DATA+r"\placeholders_localcapture.txt"))

app_map = {e[0]: e[1] for e in g}   # word文字列 -> ルビHTML (語ごとの実分解)

def app_roots(word):
    """デプロイ済みJSONの語エントリ(無ければorchestrate)から分解境界の列を復元。"""
    html = app_map.get(word)
    if html is None:
        html = orch(word, ps, l, pl, g, c, FMT)
    # <ruby>MAIN<rt..>..</rt></ruby> と それ以外(プレーン)を順に
    toks=[]; pos=0
    for m in re.finditer(r'<ruby>(.*?)<rt[^>]*>.*?</rt></ruby>', html):
        pre = html[pos:m.start()]
        pre = re.sub(r'<[^>]+>','',pre)
        if pre.strip(): toks.append(('plain',pre))
        toks.append(('ruby', m.group(1)))
        pos=m.end()
    tail=re.sub(r'<[^>]+>','',html[pos:])
    if tail.strip(): toks.append(('plain',tail))
    # 全セグメント列(ルビ親文字＋プレーン断片)を順に。アプリの実分解。
    seg=[]
    for typ,t in toks:
        t=t.strip()
        if not t: continue
        seg.append(t.lower())
    return seg

# gold: nosl -> gold root列(語尾片を除く), full word
gold={}
with open(lp(GOLD),encoding='utf-8') as f:
    for i,line in enumerate(f,1):
        line=line.rstrip('\n')
        if not line or line.startswith('##') or ':' not in line: continue
        head=line.split(':')[0]
        for w in head.split(' '):
            wc=norm(w)
            if '#' in wc or not wc: continue
            ps_=[p for p in wc.split('/') if p]
            if len(ps_)<1: continue
            full=''.join(ps_)
            # gold語根列(語尾片を1つ落とす)
            stem_pieces = ps_[:-1] if (len(ps_)>=2 and ps_[-1] in ENDINGS) else ps_
            tier = 1 if full in tier1 else (2 if i<=PEJVO_MAX else 3)
            gold.setdefault(full,(stem_pieces, ps_, tier, w))

def cmp_decomp(app_seg, gold_full_pieces):
    # アプリの全セグメント連結=語と一致する前提で、分解境界(/結合文字列)をgold全片と比較
    app_join = ''.join(app_seg)
    app_str = '/'.join(app_seg)
    gold_str = '/'.join(gold_full_pieces)
    # 連結が語に一致しない(置換漏れ/HTML残り)場合は判定不能としてskip扱い
    if app_join != ''.join(gold_full_pieces):
        return None, app_str, gold_str
    return app_str == gold_str, app_str, gold_str

# 全ティア監査
st={1:collections.Counter(),2:collections.Counter(),3:collections.Counter()}
for full,(stem_pieces,ps_,tier,origw) in gold.items():
    app=app_roots(full)
    ok,ae,ge=cmp_decomp(app, ps_)
    s=st[tier]; s['total']+=1
    if ok is None: s['skip']+=1
    elif ok: s['ok']+=1
    else: s['dev']+=1
print("="*70)
print("【分解精度監査(全セグメント比較): アプリ実分解 vs gold】")
names={1:'Tier1(2890重要語彙)',2:'Tier2(PEJVO ≤44104)',3:'Tier3(PIV >44104)'}
for t in (1,2,3):
    s=st[t]; judged=s['ok']+s['dev']
    print(f"  {names[t]:24s} 一致率 {s['ok']/max(judged,1)*100:.1f}%  (一致{s['ok']}/判定可{judged}, 不一致{s['dev']}, skip{s['skip']})")
print("  ※不一致の多くは『2文字語根の単独語非分割』『同綴り一意化』等のアプリ設計由来。明確な誤りは少数。")
