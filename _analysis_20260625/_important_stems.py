# -*- coding: utf-8 -*-
"""重要語彙2890(の単語)とその語幹の集合を返す。gen_replacement.generate(important_stems=...)
   へ渡し、同長タイの時だけ重要語を勝たせるタイブレークに使う。
   gen_replacement._destem と同一の語尾剥がしで語幹を作り、単語と語幹の双方を入れる
   (派生・屈折形は語幹一致で拾える)。"""
import csv, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_replacement import lp
from extract_lib import hat_to_circumflex, replace_esperanto_chars
def _norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()
_GSUF = ("ojn", "oj", "on", "o", "ajn", "aj", "an", "a", "en", "e", "jn", "j", "n",
         "as", "is", "os", "us", "u", "i")
def _destem(w):
    w = w.strip()
    for s in _GSUF:
        if w.endswith(s) and len(w) - len(s) >= 2:
            return w[:-len(s)]
    return w
CSV_2890 = r"D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\漢字化・語彙資料\エスペラント語根＿漢字割り当て＿20260621\30_重要語彙CSV_日中対照_2890語\2890 Gravaj Esperantaj Vortoj kun Signifoj en la Japana, Ĉina.csv"
def load_important_stems(path=CSV_2890):
    out = set()
    if not os.path.exists(lp(path)):
        return out
    for r in list(csv.reader(open(lp(path), encoding="utf-8")))[1:]:
        if not r or not r[0].strip():
            continue
        e = r[0].strip()
        if " " in e or e.startswith("-") or e.endswith("-"):
            continue
        w = _norm(e)
        if not re.fullmatch(r"[a-zĉĝĥĵŝŭ]+", w):
            continue
        out.add(w)
        out.add(_destem(w))
    return out
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    s = load_important_stems()
    print(f"重要語幹セット: {len(s)} 件  例: {sorted(s)[:15]}")
