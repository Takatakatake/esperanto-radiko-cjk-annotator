# -*- coding: utf-8 -*-
"""参照HTML(理想の語根分解)とアプリ現行分解を1語ずつ比較。
参照のrubyベース列=理想の語根境界。アプリでルビモード分解し境界一致率を出す。
  python compare_html_reference.py <html名>
"""
import re, sys, json, html as htmllib, collections
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
from extract_lib import hat_to_circumflex, replace_esperanto_chars
HTML = sys.argv[1] if len(sys.argv)>1 else "Esperanto_meznivela_sola_lernolibro_verkita_de_sro_fujximaki_260215.html"
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()

# アプリ(JP)ルビ分解
appdir = BASE + r"\Esperanto-Kanji-Converter-and-Ruby-Annotation-Tool"
sys.path.insert(0, appdir)
import esp_text_replacement_module as m
DATA = appdir + r"\Appの运行に使用する各类文件"
with open(lp(DATA + r"\最终的な替换用リスト(列表)(合并3个JSON文件).json"), encoding="utf-8") as f: dd = json.load(f)
GL = dd["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]; G2 = dd["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]; GG = dd["全域替换用のリスト(列表)型配列(replacements_final_list)"]
ps = m.import_placeholders(lp(DATA + r"\占位符(placeholders)_%1854%-%4934%_文字列替换skip用.txt")); pl = m.import_placeholders(lp(DATA + r"\占位符(placeholders)_@5134@-@9728@_局部文字列替换结果捕捉用.txt"))
def app_roots(word):
    h = m.orchestrate_comprehensive_esperanto_text_replacement(word, ps, GL, pl, GG, G2, "HTML格式_Ruby文字_大小调整")
    toks=[]; pos=0
    for mm in re.finditer(r'<ruby>(.*?)<rt[^>]*>.*?</rt></ruby>', h):
        pre=re.sub(r'<[^>]+>','',h[pos:mm.start()])
        for ch in re.findall(r'[A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ]+', pre): toks.append(ch)
        toks.append(mm.group(1)); pos=mm.end()
    tail=re.sub(r'<[^>]+>','',h[pos:])
    for ch in re.findall(r'[A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ]+', tail): toks.append(ch)
    return [norm(t) for t in toks if norm(t)]

# 参照HTMLパース: ruby→\x01base\x01, タグ除去, 語ごとに(roots, word)
t = open(BASE + "\\" + HTML, encoding="utf-8").read()
t = t[t.find('<body'):] if '<body' in t else t
t = re.sub(r'<ruby>(.*?)<rt[^>]*>.*?</rt></ruby>', lambda x: '\x01'+x.group(1)+'\x01', t)
t = re.sub(r'<[^>]+>', ' ', t)
t = htmllib.unescape(t)
# 語境界=空白/記号。語=ruby根(\x01..\x01)と素片(語尾)の連なり
ref_words=[]
# トークン列: \x01root\x01 か 素のテキスト
i=0; cur_roots=[]; cur_letters=''
def flush():
    global cur_roots, cur_letters
    w=''.join(cur_roots)+cur_letters if False else None
    cur_roots=[]; cur_letters=''
# 文字走査
roots=[]; word_chars=[]; words=[]
parts=re.split(r'(\x01.*?\x01)', t)
buf_roots=[]; buf_word=''
def is_letter(c): return c.isalpha()
for part in parts:
    if part.startswith('\x01') and part.endswith('\x01') and len(part)>=2:
        r=part[1:-1]
        buf_roots.append(norm(r)); buf_word+=r
    else:
        # 素テキスト: 文字は語に付加、空白/記号で語確定
        seg=''
        for ch in part:
            if is_letter(ch) or ch in "-'":
                seg+=ch
            else:
                if seg: buf_word+=seg; buf_roots.append(('LIT',seg)); seg=''
                # 語境界
                if buf_word.strip():
                    words.append((buf_word, buf_roots));
                buf_word=''; buf_roots=[]
        if seg: buf_word+=seg; buf_roots.append(('LIT',seg))
if buf_word.strip(): words.append((buf_word, buf_roots))

# 境界集合(語根境界=rubyベース間。LIT素片も境界として扱う)
def ref_pieces(buf_roots):
    out=[]
    for r in buf_roots:
        if isinstance(r,tuple): out.append(norm(r[1]))
        else: out.append(r)
    return [p for p in out if p]
def cuts(pieces):
    b=set(); c=0
    for p in pieces[:-1]: c+=len(p); b.add(c)
    return b

total=0; match=0; mismatches=[]
multi=0
for word, br in words:
    rp=ref_pieces(br)
    if len(rp)<2: continue   # 分解されていない語(1語根)は対象外(境界比較不能)
    nz=norm(word)
    if not re.fullmatch(r'[a-zĉĝĥĵŝŭ\-]+', nz): continue
    ap=app_roots(nz)
    if ''.join(ap)!=nz: continue
    total+=1
    if cuts(rp)==cuts(ap): match+=1
    else:
        mismatches.append((word, '/'.join(rp), '/'.join(ap)))

print(f"=== {HTML} ===")
print(f"分解語(2語根以上)比較可 {total}  境界一致 {match}  ({match*100//max(total,1)}%)")
print(f"不一致 {len(mismatches)}")
seen=set(); uniq=[]
for w,r,a in mismatches:
    k=(r,a)
    if k in seen: continue
    seen.add(k); uniq.append((w,r,a))
print(f"ユニーク不一致 {len(uniq)} (先頭60):")
for w,r,a in uniq[:60]:
    print(f"  ref={r:32s} app={a}")
json.dump(uniq, open(lp(BASE+r'\_analysis_20260625\out\html_mismatch.json'),'w',encoding='utf-8'), ensure_ascii=False, indent=1)
