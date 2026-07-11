# -*- coding: utf-8 -*-
"""全デプロイ(ルビ3+漢字3)の異常全域スキャン: 向き逆転/空/タグ崩れ/br規則/PH漏れ/混入。"""
import os,  json, sys, re, collections
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repoルート自動検出
RT=re.compile(r'<ruby>((?:[^<]|<br\s*/?>)*?)<rt class="([^"]*)">((?:[^<]|<br\s*/?>)*?)</rt></ruby>')
CJK=re.compile(r'[一-鿿]')
HANGUL=re.compile(r'[가-힣]')
KANA=re.compile(r'[ぁ-んァ-ヶ]')
LATIN=re.compile(r'[a-zA-Zĉĝĥĵŝŭ]')
BR=re.compile(r'<br\s*/?>')
SUP=re.compile(r'[ᴬ-ᶿʰ-˿ⱼⱽ̀-ͯ]')  # 識別子上付き・結合

def scan(app, kind):
    path=rf"{ROOT}\Esperanto-Kanji-Ruby-{app}\app_data\置換リスト_{'漢字' if kind=='K' else 'ルビ'}.json"
    d=json.load(open(path,encoding="utf-8"))
    stats=collections.Counter(); ex=collections.defaultdict(list)
    def note(cat,s):
        stats[cat]+=1
        if len(ex[cat])<5: ex[cat].append(s[:70])
    for k in d:
        for e in d[k]:
            if len(e)<2 or not isinstance(e[1],str): continue
            h=e[1]
            # タグバランス
            if h.count('<ruby>')!=h.count('</ruby>') or h.count('<rt')!=h.count('</rt>'):
                note('タグ不均衡', f"{e[0]}:{h}")
            # PH漏れ($..$)
            if re.search(r'\$[0-9a-z]{2,}\$', h): note('PH漏れ', f"{e[0]}:{h}")
            for m in RT.finditer(h):
                main, cls, rt = m.group(1), m.group(2), BR.sub('',m.group(3))
                main_s=BR.sub('',main)
                nobr_main=SUP.sub('',main_s); nobr_rt=SUP.sub('',rt)
                if not main_s.strip(): note('main空', f"{e[0]}:{h[:60]}")
                if not rt.strip(): note('rt空', f"{e[0]}:{main_s}<rt:空>")
                nbr=len(BR.findall(m.group(3)))
                if nbr>=2 and cls!='XXXS_S': note('br2でXXXS_S以外', f"{main_s}[{cls}]{rt[:20]}")
                if nbr==1 and cls!='XXS_S': note('br1でXXS_S以外', f"{main_s}[{cls}]{rt[:20]}")
                if nbr==0 and cls in ('XXS_S','XXXS_S'): note('br0で縮小級', f"{main_s}[{cls}]{rt[:20]}")
                if nbr>2: note('br3以上', f"{main_s}[{cls}]")
                if kind=='K':
                    # 漢字モード: main=漢字系(or固有名ラテン保持=ルビ無なのでここに来ない), rt=エス
                    if CJK.search(nobr_rt) or HANGUL.search(nobr_rt) or KANA.search(nobr_rt):
                        note('K:rtにCJK(逆転?)', f"{main_s}<rt:{rt[:15]}>")
                    if LATIN.search(nobr_main) and not CJK.search(nobr_main):
                        note('K:mainがラテンのみ(逆転?)', f"{main_s}<rt:{rt[:15]}>")
                else:
                    # ルビモード: main=エス(ラテン), rt=訳
                    if CJK.search(nobr_main) or HANGUL.search(nobr_main) or KANA.search(nobr_main):
                        note('R:mainにCJK(逆転?)', f"{main_s}<rt:{rt[:15]}>")
    print(f"\n===== {app} {'漢字' if kind=='K' else 'ルビ'} =====")
    if not stats: print("  異常なし")
    for c,n in stats.most_common():
        print(f"  {c}: {n}")
        for s in ex[c]: print(f"     例: {s}")

for app in ("JA","ZH","KO"):
    scan(app,'R')
for app in ("JA","ZH","KO"):
    scan(app,'K')
