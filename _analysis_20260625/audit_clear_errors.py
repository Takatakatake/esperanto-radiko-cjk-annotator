# -*- coding: utf-8 -*-
"""
ティア別 分解「明確な誤り」抽出: アプリ実分解 vs gold で、
 - 設計由来(粗化: app境界 ⊆ gold境界。2文字単独語非分割・語尾非分割等) は除外
 - 明確な誤り(app境界がgoldに無い=別位置で分割。a/kompani型) のみ抽出
し、設定JSON補正候補(gold分解)として出力。
  python audit_clear_errors.py <1|2|3>   (tier)
"""
import json, sys, re, csv, collections
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
from extract_lib import hat_to_circumflex, replace_esperanto_chars
DATA = BASE + r"\Esperanto-Kanji-Ruby-JA\app_data"
GOLD = r"\\wsl.localhost\Ubuntu\home\y\エスペラント辞書徹底語根分解_20260619\世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416.txt"
CSV2890 = r"D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\漢字化・語彙資料\エスペラント語根＿漢字割り当て＿20260621\30_重要語彙CSV_日中対照_2890語\2890 Gravaj Esperantaj Vortoj kun Signifoj en la Japana, Ĉina.csv"
OUT = BASE + r"\_analysis_20260625\out"
TIER = int(sys.argv[1]) if len(sys.argv)>1 else 2
PEJVO_MAX=44104; ENDINGS={'o','a','e','i','u','oj','aj','on','an','ojn','ajn','as','is','os','us','n','j'}
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()

tier1=set()
with open(lp(CSV2890),encoding='utf-8-sig') as f:
    for row in csv.reader(f):
        if row and row[0] and row[0]!='Esperanto': tier1.add(norm(row[0].strip().strip('-')).replace('/',''))

with open(lp(DATA + r"\置換リスト_ルビ.json"),encoding='utf-8') as f: d=json.load(f)
app_map={e[0]: e[1] for e in d["全域替换用のリスト(列表)型配列(replacements_final_list)"]}
GL=d["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]; G2=d["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]
GG=d["全域替换用のリスト(列表)型配列(replacements_final_list)"]
sys.path.insert(0, BASE + r"\Esperanto-Kanji-Ruby-JA")
from esp_text_replacement_module import orchestrate_comprehensive_esperanto_text_replacement as _orch, import_placeholders as _imp
_ps=_imp(lp(DATA+r"\占位符(placeholders)_%1854%-%4934%_文字列替换skip用.txt")); _pl=_imp(lp(DATA+r"\占位符(placeholders)_@5134@-@9728@_局部文字列替换结果捕捉用.txt"))
FALLBACK = ('--full' in sys.argv)

_batch={}   # 未収録語を1回のorchestrateで処理した結果(word->html)
def batch_orch(words):
    if not words: return
    text="\n".join(words)
    out=_orch(text,_ps,GL,_pl,GG,G2,"HTML格式_Ruby文字_大小调整")
    parts=out.split("\n")
    if len(parts)==len(words):
        for w,h in zip(words, parts):
            _batch[w]=h[:-4] if h.endswith("<br>") else h
    else:
        # 行数不一致時は個別フォールバック(稀)
        for w in words:
            _batch[w]=_orch(w,_ps,GL,_pl,GG,G2,"HTML格式_Ruby文字_大小调整")

def app_seg(word):
    html=app_map.get(word)
    if html is None:
        if not FALLBACK: return None
        html=_batch.get(word)
        if html is None: return None
    toks=[]; pos=0
    for m in re.finditer(r'<ruby>(.*?)<rt[^>]*>.*?</rt></ruby>', html):
        pre=re.sub(r'<[^>]+>','',html[pos:m.start()]).strip()
        if pre: toks.append(pre)
        toks.append(m.group(1)); pos=m.end()
    tail=re.sub(r'<[^>]+>','',html[pos:]).strip()
    if tail: toks.append(tail)
    return [t.lower() for t in toks if t.strip()]

def bounds(pieces):
    b=set(); c=0
    for p in pieces[:-1]: c+=len(p); b.add(c)
    return b

# 1) 対象語収集
targets=[]; seen=set()
with open(lp(GOLD),encoding='utf-8') as f:
    for i,line in enumerate(f,1):
        line=line.rstrip('\n')
        if not line or line.startswith('##') or ':' not in line: continue
        head=line.split(':')[0]
        for w in head.split(' '):
            wc=norm(w)
            if '#' in wc or not wc: continue
            ps=[p for p in wc.split('/') if p]
            if not ps: continue
            full=''.join(ps)
            if full in seen: continue
            seen.add(full)
            tier = 1 if full in tier1 else (2 if i<=PEJVO_MAX else 3)
            if tier!=TIER: continue
            targets.append((w, ps, full))
# 2) app_mapに無い語をバッチorchestrate
if FALLBACK:
    absent=[full for (w,ps,full) in targets if full not in app_map]
    print(f"  バッチorchestrate対象 {len(absent)} 語 ...", flush=True)
    B=2000
    for k in range(0,len(absent),B):
        batch_orch(absent[k:k+B])
# 3) 監査
clear=[]; design=0; judged=0; skip=0
for (w,ps,full) in targets:
    seg=app_seg(full)
    if seg is None: skip+=1; continue
    if ''.join(seg)!=full: skip+=1; continue
    judged+=1
    gb=bounds(ps); ab=bounds(seg)
    if ab==gb: continue
    if ab <= gb:
        design+=1
    else:
        clear.append((w, '/'.join(ps), '/'.join(seg)))

names={1:'Tier1(2890)',2:'Tier2(PEJVO)',3:'Tier3(PIV)'}
print(f"【{names[TIER]} 明確な分解誤り抽出】 判定可{judged} skip{skip}")
print(f"  設計由来(粗化) {design}")
print(f"  明確な誤り(別位置分割) {len(clear)}")
with open(lp(OUT+f"\\clear_errors_tier{TIER}.json"),"w",encoding="utf-8") as g:
    json.dump([{'word':w,'gold':gd,'app':ap} for w,gd,ap in clear],g,ensure_ascii=False,indent=1)
print(f"  保存: out/clear_errors_tier{TIER}.json")
print("\n--- 明確な誤り 例(最大40) ---")
for w,gd,ap in clear[:40]:
    print(f"  [{w}]  gold={gd}  app={ap}")
