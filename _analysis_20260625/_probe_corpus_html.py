# -*- coding: utf-8 -*-
"""京大コーパスHTML中で、指定エラー語が実際にどの<ruby>列で書かれているかを抽出して表示。
   修正ツールを作る前に、タグ構造・既存グロス・CSSクラス・前後の文法語尾の扱いを目視確認する。"""
import re, os, sys, html as htmllib, collections
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from extract_lib import hat_to_circumflex, replace_esperanto_chars
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()
CORP = BASE + r"\_project_root_misc\京大エス研html文書＿Github"

RUBY = re.compile(r"<ruby>(.*?)<rt[^>]*>.*?</rt></ruby>", re.S)
# 対象エラー語(lowercase lemma)
TARGETS = {"esperante","platformo","lingvisto","komunumo","biologio","meningito",
           "ocelo","pense","amon","dion","kvardeko","nitrato","disdegni"}

def units(h):
    """HTMLを (種別,テキスト,生HTML,開始,終了) の列に。種別R=ruby, B=bare(タグ除去текст)"""
    out=[]; pos=0
    for m in RUBY.finditer(h):
        if m.start()>pos: out.append(("B", h[pos:m.start()], h[pos:m.start()], pos, m.start()))
        out.append(("R", m.group(1), m.group(0), m.start(), m.end())); pos=m.end()
    if pos<len(h): out.append(("B", h[pos:], h[pos:], pos, len(h)))
    return out

def find_words(h):
    """ruby列から「語」を復元: 連続するruby + 間/後の裸アルファベット(語尾)。
       返り: (surface, lemma_norm, 生HTMLスパン)"""
    us=units(h); words=[]; i=0
    while i<len(us):
        if us[i][0]!="R": i+=1; continue
        j=i; surface=""; raw=""
        while j<len(us):
            if us[j][0]=="R":
                surface+=us[j][1]; raw+=us[j][2]; j+=1
            else:
                bt=re.sub(r"<[^>]+>"," ",us[j][1]); bt=htmllib.unescape(bt)
                m=re.match(r"^([A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ'\-]+)", bt)
                # 直後が「語尾だけ+語境界」なら語の一部, それ以外で打ち切り
                if m and j+1<len(us) and us[j+1][0]=="R" and re.fullmatch(r"[a-zĉĝĥĵŝŭ'\-]{1,4}", norm(m.group(1))):
                    surface+=m.group(1); raw+=us[j][2]; j+=1
                else:
                    # 末尾語尾を取り込む(語境界まで)
                    if m: surface+=m.group(1); raw+=us[j][2][:m.end()]
                    break
        words.append((surface, norm(surface), raw)); i=j
    return words

hits=collections.defaultdict(list)
for root,_d,files in os.walk(CORP):
    for f in files:
        if not f.lower().endswith((".html",".htm")): continue
        t=open(os.path.join(root,f),encoding="utf-8",errors="ignore").read()
        body=t[t.find("<body"):] if "<body" in t else t
        for surface,lemma,raw in find_words(body):
            if lemma in TARGETS and len(hits[lemma])<3:
                hits[lemma].append((f, surface, raw))

for w in sorted(TARGETS):
    print(f"\n===== {w}  ({len(hits[w])}例表示) =====")
    for f,surface,raw in hits[w]:
        print(f"  [{f[:40]}] surface={surface!r}")
        print(f"    HTML: {raw[:400]}")
