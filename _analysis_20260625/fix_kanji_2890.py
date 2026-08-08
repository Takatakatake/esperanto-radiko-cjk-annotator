# -*- coding: utf-8 -*-
"""2890漢字違反38語をマスター注入どおりに再構築(3アプリ・全語形・大小文字変種)。DRY既定/--apply。"""
import os,  json, sys, re, unicodedata, shutil
sys.stdout.reconfigure(encoding="utf-8")
DRY = "--apply" not in sys.argv
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repoルート自動検出
sys.path.insert(0, ROOT+r"\_analysis_20260625")
from atomic_json import atomic_file_copy, atomic_json_dump
from gold_snapshot import consistent_snapshot
from gen_replacement import load_app_replacement_helper
DEFAULT_REF2 = os.path.join(
    os.path.dirname(ROOT), "エスペラント語根＿漢字割り当て＿20260630",
)
REF2 = os.environ.get('ESP_KANJI_MASTER_PATH', DEFAULT_REF2)  # 外部漢字マスター(正本)。他環境では環境変数で指定
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
master_path=REF2+r"\漢字注入_学習者版_20260620.txt"
master_raw, master_identity = consistent_snapshot(master_path)
print(
    f"漢字master bytes={master_identity['bytes']} sha256={master_identity['sha256']}",
    flush=True,
)
expected_master_sha = os.environ.get('ESP_EXPECTED_KANJI_MASTER_SHA256', '').strip().upper()
expected_master_bytes = None
expected_manifest_path = os.environ.get(
    'ESP_EXPECTED_KANJI_MASTER_MANIFEST', ''
).strip()
if expected_manifest_path:
    with open(expected_manifest_path, encoding='utf-8') as handle:
        expected_manifest = json.load(handle)
    if expected_manifest.get('schema_version') != 1:
        raise RuntimeError('unsupported Kanji master manifest schema')
    injection_rows = [
        row for row in expected_manifest.get('files', [])
        if row.get('name') == '漢字注入_学習者版_20260620.txt'
    ]
    if len(injection_rows) != 1:
        raise RuntimeError('Kanji master manifest must pin one injection file')
    manifest_row = injection_rows[0]
    manifest_sha = str(manifest_row['sha256']).upper()
    if expected_master_sha and expected_master_sha != manifest_sha:
        raise RuntimeError('conflicting Kanji master SHA expectations')
    expected_master_sha = manifest_sha
    expected_master_bytes = int(manifest_row['bytes'])
if (
    expected_master_bytes is not None
    and master_identity['bytes'] != expected_master_bytes
):
    raise RuntimeError(
        f"kanji master byte mismatch: expected {expected_master_bytes}, "
        f"got {master_identity['bytes']}"
    )
if expected_master_sha and master_identity['sha256'] != expected_master_sha:
    raise RuntimeError(
        f"kanji master SHA mismatch: expected {expected_master_sha}, "
        f"got {master_identity['sha256']}"
    )
for line in master_raw.decode('utf-8').splitlines():
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
    M = load_app_replacement_helper(rf"{ROOT}\Esperanto-Kanji-Ruby-{app}")
    cw=json.load(open(base+r"\char_widths.json",encoding="utf-8")); FMT='HTML格式_Ruby文字_大小调整'
    stems=sorted(plans.keys(),key=len,reverse=True)
    n=0; samples=[]
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
                        if len(samples)<15:
                            samples.append((e[0], e[1], nb))
                        if not DRY:
                            pad_l=e[1][:len(e[1])-len(e[1].lstrip())]; pad_r=e[1][len(e[1].rstrip()):]
                            e[1]=pad_l+nb+pad_r
                    break
    print(f"[{app}] 漢字deployed 再構築 {n}")
    if DRY:
        for old, current, proposed in samples:
            print(f"     {old!r}: {current!r} -> {proposed!r}")
    if not DRY:
        atomic_file_copy(dep_path, dep_path+".bak_preKanji2890")
        atomic_json_dump(dep_path, d)
        print("     保存(.bak_preKanji2890)")
if not DRY:
    atomic_file_copy(wk_path, wk_path+".bak_preKanji2890")
    atomic_json_dump(wk_path, wk)
    print("word_kanji 保存")
