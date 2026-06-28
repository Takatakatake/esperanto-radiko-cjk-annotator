# -*- coding: utf-8 -*-
"""
検証済み確定リスト out/confirmed_tier{N}.json (各 {w, target}) を元に、
3アプリの語根分解法設定JSONを補正(競合nosl棚卸し＋target分解を高優先度で強制)し、
再生成→検証。 target はgold分解(または検証で修正された分解)。
  python apply_confirmed.py <tier> [--write]
"""
import json, sys, re, shutil, os
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import generate, lp
from extract_lib import hat_to_circumflex, replace_esperanto_chars
OUT = BASE + r"\_analysis_20260625\out"
GOLD = r"\\wsl.localhost\Ubuntu\home\y\エスペラント辞書徹底語根分解_20260619\世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416.txt"
if not os.path.exists(lp(GOLD)):
    # WSL不通時はDownloadsバックアップのgoldを使用
    import glob
    _bks=sorted(glob.glob(os.path.join(os.environ['USERPROFILE'],'Downloads','エスペラント_backup_*')))
    for _b in reversed(_bks):
        _g=os.path.join(_b,'語根分解辞書_WSL','世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416.txt')
        if os.path.exists(lp(_g)): GOLD=_g; break
    print(f"[gold] WSL不通→backup使用: {GOLD[:60]}...")
TIER=int(sys.argv[1]); WRITE='--write' in sys.argv
def _norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()

# gold辞書マップ: word_nosl -> 分解pieces(正規化)。屈折生成のgold照合に使用。
gold_map={}
with open(lp(GOLD),encoding='utf-8') as f:
    for line in f:
        line=line.rstrip('\n')
        if not line or line.startswith('##') or ':' not in line: continue
        for w in line.split(':')[0].split(' '):
            wc=_norm(w)
            if '#' in wc or not wc: continue
            ps=[p for p in wc.split('/') if p]
            if not ps: continue
            gold_map.setdefault(''.join(ps), ps)
# gold語根集合(全分解片)。stem+語尾がそれ自体gold語根なら分割しない(spontane等の保全)。
gold_roots=set()
for ps in gold_map.values():
    for p in ps: gold_roots.add(p)

with open(lp(OUT+f"\\confirmed_tier{TIER}.json"),encoding='utf-8') as f:
    confirmed=json.load(f)

_NOMINAL=["o","oj","on","ojn","a","aj","an","ajn","e","en"]
def make_correction(decomp):
    """target分解→設定エントリ。屈折語尾はgold照合で生成:
      候補(名詞/形容詞/副詞語尾)のうち、stem+語尾がgoldに「別分解で」存在する形だけ除外。
      → 多品詞語根(esperant=名詞esperanto/形容詞esperanta/副詞esperante)の兄弟形を1項目から自動カバーしつつ、
        衝突(名詞tramet+i=gold tra/met/i、spontan+e=gold語根spontane)は回避。
      動詞形(verbo)は gold語尾がiか stem+iがgold整合の場合のみ付与。
    """
    pieces=[p for p in decomp.split('/') if p]
    if not pieces: return None
    nosl=''.join(pieces)
    last=pieces[-1]
    if len(pieces)>=2 and last in ('o','a','e','i') and len(last)==1:
        stem='/'.join(pieces[:-1]); stem_nosl=''.join(pieces[:-1]); stem_pieces=pieces[:-1]
        suffixes=[]
        for end in _NOMINAL:
            form=stem_nosl+end
            if form==nosl:
                suffixes.append(end); continue              # 確定語自身は常に採用(私の意図分解が正本)
            if form in gold_roots and [form]!=stem_pieces+[end]:
                continue                                    # 兄弟形がそれ自体gold語根(spontane等)→分割しない
            gd=gold_map.get(form)
            if gd is not None and gd!=stem_pieces+[end]:
                continue                                    # 兄弟形がgoldで別分解→侵食しない(trameti等)
            suffixes.append(end)
        addverb=(last=='i')
        if not addverb:
            gi=gold_map.get(stem_nosl+'i')
            if gi is not None and gi==stem_pieces+['i']: addverb=True
        if addverb:
            suffixes=["verbo_s1","verbo_s2"]+suffixes
    else:
        stem=decomp; stem_nosl=nosl
        suffixes=["ne"]                                     # 固定形(全体強制)
    prio=len(stem_nosl)*10000+4000
    return {'stem':stem,'stem_nosl':stem_nosl,'prio':prio,'suffixes':suffixes,'word_nosl':nosl}

# 同一語幹は語尾を和集合マージ(例 sugesti/o + sugesti/a + sugesti/i → 名詞+形容詞+動詞)
corrs={}; remove_nosl=set()
for e in confirmed:
    c=make_correction(e['target'])
    if not c: continue
    sn=c['stem_nosl']
    if sn in corrs and corrs[sn]['stem']==c['stem']:
        ex=corrs[sn]
        for s in c['suffixes']:
            if s not in ex['suffixes']: ex['suffixes'].append(s)
        ex['prio']=max(ex['prio'], c['prio'])
    else:
        corrs[sn]=c
    remove_nosl.add(sn); remove_nosl.add(c['word_nosl'])
print(f"Tier{TIER} 確定 {len(confirmed)} → 補正エントリ {len(corrs)}")

APPS={'JP':(r"\Esperanto-Kanji-Ruby-JA",r"\エスペラント語根-日本語訳ルビ対応リスト.csv",'ja'),
      'ZH':(r"\Esperanto-Kanji-Ruby-ZH",r"\世界语词根-中文注释对应列表.csv",'zh'),
      'KO':(r"\Esperanto-Kanji-Ruby-KO",r"\에스페란토 어근-한국어 번역 루비 대응 목록.csv",'ko')}
ESTEM=r"\PEJVO(世界语全部单词列表)'全部'について、词尾(a,i,u,e,o,n等)をcutし、comma(,)で隔てて词性と併せて记录した列表(E_stem_with_Part_Of_Speech_list).json"
ROOTS=r"\世界语全部词根_约11137个_202501.txt"; FINAL=r"\最终的な替换用リスト(列表)(合并3个JSON文件).json"
STEM=r"\世界语单词词根分解方法の使用者自定义设置.json"; USER=r"\替换后文字列(汉字)の使用者自定义设置(基本上完全不推荐).json"; FMT='HTML格式_Ruby文字_大小调整'

def process(key, write):
    d,csvn,lang=APPS[key]; APPDIR=BASE+d; DATA=APPDIR+r"\Appの运行に使用する各类文件"
    sp=DATA+STEM
    # 冪等化: pristine版(.bak)があれば復元してから適用(再実行で.bakが汚れない)
    bak=sp+".bak_preTier"+str(TIER)+"confirmed"
    if write and os.path.exists(lp(bak)):
        shutil.copy2(lp(bak),lp(sp))
    with open(lp(sp),encoding='utf-8') as f: settings=json.load(f)
    removed=0; kept=[]
    for e in settings:
        if isinstance(e,list) and len(e)==3 and isinstance(e[0],str):
            ns=e[0].replace('/','').strip()
            if ns in remove_nosl: removed+=1; continue
        kept.append(e)
    settings=kept
    for sn,c in corrs.items():
        settings.append([c['stem'], c['prio'], list(c['suffixes'])])
    tmp=DATA+r"\_settings_confirmed_tmp.json"
    with open(lp(tmp),'w',encoding='utf-8') as g: json.dump(settings,g,ensure_ascii=False,indent=1)
    with open(lp(OUT+f"\\word_anno_{lang}.json"),encoding='utf-8') as f: word_anno=json.load(f)
    combined=generate(APPDIR,DATA,DATA+csvn,tmp,DATA+USER,DATA+ESTEM,DATA+ROOTS,FMT,word_anno=word_anno)
    if write:
        shutil.copy2(lp(sp),lp(sp+".bak_preTier"+str(TIER)+"confirmed"))
        with open(lp(sp),'w',encoding='utf-8') as g: json.dump(settings,g,ensure_ascii=False,indent=1)
        with open(lp(DATA+FINAL),'w',encoding='utf-8') as g: json.dump(combined,g,ensure_ascii=False,indent=2)
        os.remove(lp(tmp))
        print(f"  [{key}] 除去{removed} 追加{len(corrs)} → 書込完了")
    else:
        os.remove(lp(tmp)); print(f"  [{key}] 除去{removed} 追加{len(corrs)} (未書込)")
    return combined

# JP検証 (SKIP_VERIFY=1 で省略=反復高速化)
if not os.environ.get('SKIP_VERIFY'):
    combined=process('JP', False)
    sys.path.insert(0, BASE+APPS['JP'][0])
    from esp_text_replacement_module import orchestrate_comprehensive_esperanto_text_replacement as orch, import_placeholders as imp
    DATA=BASE+APPS['JP'][0]+r"\Appの运行に使用する各类文件"
    ps=imp(lp(DATA+r"\占位符(placeholders)_%1854%-%4934%_文字列替换skip用.txt")); pl=imp(lp(DATA+r"\占位符(placeholders)_@5134@-@9728@_局部文字列替换结果捕捉用.txt"))
    g_=combined["全域替换用のリスト(列表)型配列(replacements_final_list)"]; l_=combined["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]; c_=combined["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]
    def segplain(w): return re.sub(r'<[^>]+>','',orch(w,ps,l_,pl,g_,c_,FMT))
    print("\n  検証(確定語の再分解):")
    for e in confirmed[:40]:
        full=''.join(p for p in e['target'].split('/') if p)
        print(f"    {full:20s} -> {segplain(full)}")
if WRITE:
    process('ZH', True); process('KO', True); process('JP', True)
    print("\n3アプリ書込完了")
