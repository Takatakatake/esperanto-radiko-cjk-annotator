# -*- coding: utf-8 -*-
"""第63R: マスター残差の語スコープ再構築(fix_kanji_2890と同機構のデータ駆動版)。DRY既定/--apply。

対象 = _residual_targets_20260724.json の288語(62R後残差411からハイフン表示のみ122と
語根map層のtropを除いたもの: map欠落根126語 + 分解深度差162語)。
各語を漢字注入_学習者版の⟦⟧分解どおりに、配信置換リスト上の当該語エントリ
(完全形+文法語尾拡張+大小文字変種)だけ再構築する。

安全ガード(fix_kanji_2890との差分):
 1) 語尾拡張先が別のマスター見出し語(an→ano, di→dio等)なら不変更
    (その語自身の注入行/監査が管轄。跨ぎ捕獲=salon/salo型の防止)。
 2) 表示(タグ除去後)が変わる場合のみ書換。マークアップ差のみの空回り書換禁止。
 3) 表示差がハイフンのみなら不変更(アプリの複合語接合表示規約を保全)。
 4) マスター新値が、アプリ現行表示に無い語根様ラテン断片(2字以上かつ文法語尾でない、
    例: 结核素化行→结ᵀin化行 の in)を新たに露出させる場合は保留(defer)。
    これは注入版が旧世代mapから生成されたことによる一時的劣化(マスター第2段/オーファン
    精査待ち)の疑いがあるため、マスター側の裁定を待つ。アプリ現行に漢字が一切無い語
    (素通し)は例外的に無条件採用(何を貰っても純増のため)。
"""
import os, json, sys, re, unicodedata
sys.stdout.reconfigure(encoding="utf-8")
DRY = "--apply" not in sys.argv
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT + r"\_analysis_20260625")
from atomic_json import atomic_file_copy, atomic_json_dump
from gold_snapshot import consistent_snapshot
from gen_replacement import load_app_replacement_helper
DEFAULT_REF2 = os.path.join(
    os.path.dirname(ROOT), "エスペラント語根＿漢字割り当て＿20260630",
)
REF2 = os.environ.get('ESP_KANJI_MASTER_PATH', DEFAULT_REF2)
X={'c^':'ĉ','g^':'ĝ','h^':'ĥ','j^':'ĵ','s^':'ŝ','u^':'ŭ','C^':'Ĉ','G^':'Ĝ','H^':'Ĥ','J^':'Ĵ','S^':'Ŝ','U^':'Ŭ'}
def xconv(s):
    for a,b in X.items(): s=s.replace(a,b)
    return unicodedata.normalize('NFC',s)

# 2026-07-25 第65R: マスター世代更新のたびに残差対象を再計測して差し替える。
# 最新世代のファイルがあればそれを使い、無ければ従来世代へフォールバックする。
_t_candidates = ['_residual_targets_20260726.json', '_residual_targets_20260725.json',
                 '_residual_targets_20260724.json']
_t_path = None
for _cand in _t_candidates:
    _p = os.path.join(ROOT, '_analysis_20260625', _cand)
    if os.path.exists(_p):
        _t_path = _p
        break
if _t_path is None:
    raise SystemExit('残差対象リストが見つからない: ' + ' / '.join(_t_candidates))
print(f'残差対象リスト: {os.path.basename(_t_path)}')
with open(_t_path, encoding='utf-8') as f:
    _tdata = json.load(f)
# 監査駆動で退行を出した対象は除外リストへ回す(prefix-bleed同形異義=grafi動詞/grafio名詞型など)。
_exclude = set(_tdata.get('exclude', []))
_exc_path = os.path.join(ROOT, '_analysis_20260625', '_residual_exclude_20260724.json')
if os.path.exists(_exc_path):
    with open(_exc_path, encoding='utf-8') as f:
        _exclude |= set(json.load(f).get('exclude', []))
TARGET = [w for w in _tdata['targets'] if w.lower() not in {e.lower() for e in _exclude}]
print(f"対象語 {len(TARGET)} (除外 {len(_tdata['targets'])-len(TARGET)})")

RE=re.compile(r'^([^⟦:]+)⟦([^⟧]+)⟧')
master_path=REF2+r"\漢字注入_学習者版_20260620.txt"
master_raw, master_identity = consistent_snapshot(master_path)
print(f"漢字master bytes={master_identity['bytes']} sha256={master_identity['sha256']}", flush=True)
_expected = _tdata.get('master_injection_sha256', '').upper()
if _expected and master_identity['sha256'].upper() != _expected:
    raise SystemExit(
        '残差対象リストとマスター世代が不一致: 対象リストを新世代の監査(r129系)で再計測してから実行'
    )

inj={}
inj_surfaces=set()   # マスターの実在見出し語(空白なし)の表層。部品数不一致行も含める。
                     # これに含まれる表層は「その語自身の見出し」なので、より短い対象語幹に
                     # 捕獲させない(graf動詞语幹が-grafio名詞を捕獲する跨ぎ退行の防止)。
for line in master_raw.decode('utf-8').splitlines():
    m=RE.match(line)
    if not m: continue
    w=xconv(m.group(1).strip())
    if ' ' in w: continue
    surf=w.replace('/','').replace('-','').lower()
    inj_surfaces.add(surf)
    k=xconv(m.group(2).strip())
    wp=w.replace('-','').split('/'); kp=k.replace('-','').split('/')
    if len(wp)!=len(kp): continue
    if surf not in inj: inj[surf]=(wp,kp)

plans={}
for t in TARGET:
    e=inj.get(t.lower())
    if e: plans[t.lower()]=e
    else: print(f"  [警告] 注入に無し: {t}")
print(f"再構築対象 {len(plans)}語")

ENDSET={'','o','on','oj','ojn','a','aj','an','ajn','e','en','i','as','is','os','us','u','j','n'}
TAG=re.compile(r'<[^>]+>'); RT=re.compile(r'<rt[^>]*>(?:[^<]|<br\s*/?>)*?</rt>')
def display(s):
    return TAG.sub('', RT.sub('', s)).strip()

CJK=re.compile(r'[一-鿿]')
LAT=re.compile(r'[A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ]+')
def new_rootlike_runs(d_cur, d_new):
    """マスター新表示にだけ現れる語根様ラテン断片(ガード4)。"""
    cur = {r.lower() for r in LAT.findall(d_cur)}
    return [r for r in LAT.findall(d_new)
            if len(r) >= 2 and r.lower() not in ENDSET and r.lower() not in cur]

def rebuild(src, wp, kp, M, cw, FMT):
    stem=''.join(wp)
    if len(src)<len(stem) or src.lower()[:len(stem)]!=stem.lower(): return None
    ending=src[len(stem):]
    if ending.lower() not in ENDSET: return None
    if wp[-1] in ('i','as','is','os','us','u','e') and ending: return None
    out=[]; pos=0
    for w,k in zip(wp,kp):
        seg=src[pos:pos+len(w)]; pos+=len(w)
        if k==w or not re.search(r'[一-鿿]',k):
            out.append(seg)
        else:
            kk = k.upper() if seg.isupper() else k
            out.append(M.output_format(kk, seg, FMT, cw))
    return ''.join(out)+ending

wk_path=ROOT+r"\_analysis_20260625\out\word_kanji.json"
wk=json.load(open(wk_path,encoding="utf-8"))
all_deferred=set()

for app in ("JA","ZH","KO"):
    base=rf"{ROOT}\Esperanto-Kanji-Ruby-{app}\app_data"
    dep_path=base+r"\置換リスト_漢字.json"
    d=json.load(open(dep_path,encoding="utf-8"))
    M = load_app_replacement_helper(rf"{ROOT}\Esperanto-Kanji-Ruby-{app}")
    cw=json.load(open(base+r"\char_widths.json",encoding="utf-8")); FMT='HTML格式_Ruby文字_大小调整'
    stems=sorted(plans.keys(),key=len,reverse=True)
    n=0; skip_cross=0; skip_markup=0; skip_hyphen=0; skip_defer=0; samples=[]; deferred={}
    for k in d:
        for e in d[k]:
            if len(e)<2 or not isinstance(e[0],str) or not isinstance(e[1],str): continue
            src=unicodedata.normalize('NFC',e[0].strip())
            sl=src.lower()
            for st in stems:
                wp,kp=plans[st]
                stem=''.join(wp)
                if sl.startswith(stem.lower()):
                    # ガード1: 語尾拡張先が別のマスター見出し語なら不変更
                    if sl != stem.lower() and sl in inj_surfaces:
                        skip_cross+=1; break
                    nb=rebuild(src,wp,kp,M,cw,FMT)
                    if nb and nb!=e[1].strip():
                        d_new=display(nb); d_cur=display(e[1])
                        if d_new == d_cur:
                            skip_markup+=1; break        # ガード2: 表示同一
                        if d_new.replace('-','') == d_cur.replace('-',''):
                            skip_hyphen+=1; break        # ガード3: ハイフンのみ
                        if CJK.search(d_cur):
                            nr=new_rootlike_runs(d_cur, d_new)
                            if nr:                       # ガード4: 語根様断片の新規露出
                                skip_defer+=1
                                deferred.setdefault(st, (d_cur, d_new, nr))
                                break
                        n+=1
                        if len(samples)<20:
                            samples.append((e[0], d_cur, d_new))
                        if not DRY:
                            pad_l=e[1][:len(e[1])-len(e[1].lstrip())]; pad_r=e[1][len(e[1].rstrip()):]
                            e[1]=pad_l+nb+pad_r
                    break
    print(f"[{app}] 漢字deployed 再構築 {n} (跨ぎ回避 {skip_cross} / 表示同一 {skip_markup} / ハイフンのみ {skip_hyphen} / 保留 {skip_defer})")
    all_deferred |= set(deferred)
    if deferred and app == "JA":
        print(f"     保留語(map第2段/オーファン精査待ち) {len(deferred)}語:")
        for st,(dc,dn,nr) in sorted(deferred.items()):
            print(f"       {st}: 現行 {dc!r} / master {dn!r} / 新規断片 {nr}")
    if DRY:
        for old, cur, new in samples:
            print(f"     {old!r}: {cur!r} -> {new!r}")
    if not DRY:
        atomic_file_copy(dep_path, dep_path+".bak_preResidual")
        atomic_json_dump(dep_path, d)
        print("     保存(.bak_preResidual)")
added=0
for t,(wp,kp) in plans.items():
    if t in all_deferred: continue   # 保留語のキーは追加しない(将来のapplyで発火させない)
    key='/'.join(wp)
    if key not in wk:
        wk[key]=[[w,k] for w,k in zip(wp,kp)]
        added+=1
print(f"word_kanji 追記 {added} (保留除外 {len(all_deferred)}語)")
if not DRY:
    atomic_file_copy(wk_path, wk_path+".bak_preResidual")
    atomic_json_dump(wk_path, wk)
    print("word_kanji 保存")
