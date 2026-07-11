# -*- coding: utf-8 -*-
"""2890漢字違反38語をマスター注入どおりに再構築(3アプリ・全語形・大小文字変種)。DRY既定/--apply。"""
import os,  json, sys, re, unicodedata, importlib, shutil
sys.stdout.reconfigure(encoding="utf-8")
DRY = "--apply" not in sys.argv
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repoルート自動検出
REF2 = os.environ.get('ESP_KANJI_MASTER_PATH', r"D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\エスペラントの漢字化プロジェクト総結集20260630\エスペラント語根＿漢字割り当て＿20260630")  # 外部漢字マスター(正本)。他環境では環境変数で指定
X={'c^':'ĉ','g^':'ĝ','h^':'ĥ','j^':'ĵ','s^':'ŝ','u^':'ŭ','C^':'Ĉ','G^':'Ĝ','H^':'Ĥ','J^':'Ĵ','S^':'Ŝ','U^':'Ŭ'}
def xconv(s):
    for a,b in X.items(): s=s.replace(a,b)
    return unicodedata.normalize('NFC',s)
TARGET=['valoro','ĉielo','ĉiela','vetero','voĉo','volonte','averti','vigla','volonta','valizo','varii',
 'fotografi','logi','vazo','vermo','verso','vergo','verto','aŭtomobilo','kajo','mekanismo','verbo',
 'astronomio','teleskopo','termo','vaki','ve','viruso','volupto','vulgara','kolektiva','ortografio',
 'valida','varti','violono','volumo','vertico','vespo','ĉaro']
# 注入マスターから対象の分解を取得
inj={}
RE=re.compile(r'^([^⟦:]+)⟦([^⟧]+)⟧')
for line in open(REF2+r"\漢字注入_学習者版_20260620.txt",encoding="utf-8"):
    m=RE.match(line)
    if not m: continue
    w=xconv(m.group(1).strip())
    if ' ' in w: continue
    k=xconv(m.group(2).strip())
    wp=w.split('/'); kp=k.split('/')
    if len(wp)==len(kp): inj[w.replace('/','').lower()]=(wp,kp)
plans={}
for t in TARGET:
    e=inj.get(t.lower())
    if e: plans[t.lower()]=e
    else: print(f"  [警告] 注入に無し: {t}")
print(f"再構築対象 {len(plans)}語")

ENDSET={'','o','on','oj','ojn','a','aj','an','ajn','e','en','i','as','is','os','us','u','j','n'}
def rebuild(src, wp, kp, M, cw, FMT):
    """src(実表記) を wp の各断片字数でスライス。kp が語尾(=断片と同一表記)なら平文、それ以外はruby(main=漢字,rt=エス断片)。"""
    stem=''.join(wp)
    if len(src)<len(stem) or src.lower()[:len(stem)]!=stem.lower(): return None
    ending=src[len(stem):]
    if ending.lower() not in ENDSET: return None
    # 語幹が語尾つき(例 logi=log+i)なら、追加語尾は不可(logiじたいが完形)…ただしo/a語幹は複数/対格可
    if wp[-1] in ('i','as','is','os','us','u','e') and ending: return None
    out=[]; pos=0
    for w,k in zip(wp,kp):
        seg=src[pos:pos+len(w)]; pos+=len(w)
        if k==w or not re.search(r'[一-鿿]',k):   # 語尾・無漢字断片は平文
            out.append(seg)
        else:
            kk = k.upper() if seg.isupper() else k
            out.append(M.output_format(kk, seg, FMT, cw))
    return ''.join(out)+ending

wk_path=ROOT+r"\_analysis_20260625\out\word_kanji.json"
wk=json.load(open(wk_path,encoding="utf-8"))
added=0
for t,(wp,kp) in plans.items():
    key='/'.join(wp)
    if key not in wk:
        wk[key]=[[w,k] for w,k in zip(wp,kp)]
        added+=1
print(f"word_kanji 追記 {added}")

for app in ("JA","ZH","KO"):
    base=rf"{ROOT}\Esperanto-Kanji-Ruby-{app}\app_data"
    dep_path=base+r"\置換リスト_漢字.json"
    d=json.load(open(dep_path,encoding="utf-8"))
    sys.path.insert(0, rf"{ROOT}\Esperanto-Kanji-Ruby-{app}")
    import esp_replacement_json_make_module as M; importlib.reload(M)
    cw=json.load(open(base+r"\char_widths.json",encoding="utf-8")); FMT='HTML格式_Ruby文字_大小调整'
    stems=sorted(plans.keys(),key=len,reverse=True)
    n=0
    for k in d:
        for e in d[k]:
            if len(e)<2 or not isinstance(e[0],str) or not isinstance(e[1],str): continue
            src=unicodedata.normalize('NFC',e[0].strip())
            sl=src.lower()
            for st in stems:
                wp,kp=plans[st]
                stem=''.join(wp)
                if sl.startswith(stem.lower()):
                    nb=rebuild(src,wp,kp,M,cw,FMT)
                    if nb and nb!=e[1].strip():
                        n+=1
                        if not DRY:
                            pad_l=e[1][:len(e[1])-len(e[1].lstrip())]; pad_r=e[1][len(e[1].rstrip()):]
                            e[1]=pad_l+nb+pad_r
                    break
    print(f"[{app}] 漢字deployed 再構築 {n}")
    if not DRY:
        shutil.copy2(dep_path, dep_path+".bak_preKanji2890")
        json.dump(d, open(dep_path,"w",encoding="utf-8"), ensure_ascii=False)
        print("     保存(.bak_preKanji2890)")
if not DRY:
    shutil.copy2(wk_path, wk_path+".bak_preKanji2890")
    json.dump(wk, open(wk_path,"w",encoding="utf-8"), ensure_ascii=False)
    print("word_kanji 保存")
