# -*- coding: utf-8 -*-
"""ルビ再生成後の同綴り共存fixup(恒久運用)。E_stem語幹キーと衝突する語形限定の上書き:
 - 相関詞 ĉiel(単独/ĉiele) → 色々に/以各种方式/여러모로 (名詞ĉielo=空はword_anno側)
 - 形容詞 lama/laman/lamaj/lamajn/lame → lam+語尾 (僧lamao=ラマ僧はword_anno側)
再生成のたびに実行: python fix_ruby_postregen.py
"""
import json, sys, re, importlib, shutil, unicodedata
sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\エスペラントの漢字化プロジェクト総結集20260630\語根分解、注釈ルビ振り、漢字化アプリ徹底ブラッシュアップ20260630"

CORR_CIEL={'JA':'色々に','ZH':'以各种方式','KO':'여러모로'}
# E_stem語幹キーがwa未収録/別noslで root既定に落ちる語の per-word piece 再構築
WORD_PIECES={
  'anestezi': [('an',{'JA':'無','ZH':'无','KO':'무'}),
               ('estez',{'JA':'感覚','ZH':'感觉','KO':'감각'}),
               ('i',None)],
  # 医学-it-(炎症)・化学-at-(塩)は分詞ではなく「偽の友」。E_stem既定の it=受動完了/at=受動継続
  # を、既存 wa['mening/it']/wa['nitr/at'] と同じ正しいグロス(炎/酸塩)へ後処理で是正。
  # (コーパスの粗ルビ meningit=髄膜炎/nitrat=硝酸塩 とも意味整合。漢字トラックは元より正)
  'meningit': [('mening',{'JA':'髄膜','ZH':'脑膜','KO':'수막'}),
               ('it',{'JA':'炎','ZH':'炎','KO':'염'})],
  'nitrat':   [('nitr',{'JA':'窒素','ZH':'氮','KO':'질소'}),
               ('at',{'JA':'酸塩','ZH':'酸盐','KO':'산염'})],
}
_WP_END={'','o','on','oj','ojn','a','aj','an','ajn','e','en','ist','isto','iston','istoj'}
ADJ_LAM={'JA':'足が不自由な','ZH':'跛行的','KO':'다리 저는'}
CIEL_FORMS={'ĉiel','ĉiele'}
LAMA_FORMS={'lama','laman','lamaj','lamajn','lame'}

for app in ("JA","ZH","KO"):
    base=rf"{ROOT}\Esperanto-Kanji-Ruby-{app}\app_data"
    dep=base+r"\置換リスト_ルビ.json"
    d=json.load(open(dep,encoding="utf-8"))
    sys.path.insert(0, rf"{ROOT}\Esperanto-Kanji-Ruby-{app}")
    import esp_replacement_json_make_module as M; importlib.reload(M)
    cw=json.load(open(base+r"\char_widths.json",encoding="utf-8")); FMT='HTML格式_Ruby文字_大小调整'
    n=0
    for k in d:
        for e in d[k]:
            if len(e)<2 or not isinstance(e[0],str) or not isinstance(e[1],str): continue
            src=unicodedata.normalize('NFC',e[0].strip()); sl=src.lower()
            if sl in CIEL_FORMS:
                stem=src[:4]  # ĉiel(cased)
                nb=M.output_format(stem, CORR_CIEL[app], FMT, cw)+src[4:]
                if nb!=e[1]: e[1]=nb; n+=1
            elif any(sl.startswith(st) and sl[len(st):] in _WP_END for st in WORD_PIECES):
                st=next(s for s in WORD_PIECES if sl.startswith(s) and sl[len(s):] in _WP_END)
                pos=0; parts=[]
                for pc,gl in WORD_PIECES[st]:
                    seg=src_w=src[pos:pos+len(pc)]; pos+=len(pc)
                    parts.append(seg if gl is None else M.output_format(seg, gl[app], FMT, cw))
                nb=''.join(parts)+src[pos:]
                if nb!=e[1]: e[1]=nb; n+=1
            elif sl in LAMA_FORMS:
                stem=src[:3]; ending=src[3:]
                nb=M.output_format(stem, ADJ_LAM[app], FMT, cw)+ending
                if nb!=e[1]: e[1]=nb; n+=1
    shutil.copy2(dep,dep+".bak_postregen")
    json.dump(d,open(dep,"w",encoding="utf-8"),ensure_ascii=False)
    print(f"[{app}] postregen fixup {n}")
print("完了")
