# -*- coding: utf-8 -*-
"""RO_2026-07_esperanto_sentences_ja.md の各EO文に、現状の日本語版アプリ(tier15/16)で
   ルビ注釈を付与し、ルビ本文+日本語訳を並べたHTMLを出力する。"""
import re, sys, json, os
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625"); from gen_replacement import lp
APPDIR = BASE + r"\Esperanto-Kanji-Converter-and-Ruby-Annotation-Tool"; sys.path.insert(0, APPDIR)
import esp_text_replacement_module as m
DATA = APPDIR + r"\Appの运行に使用する各类文件"
FMT = 'HTML格式_Ruby文字_大小调整'
dd = json.load(open(lp(DATA + r"\最终的な替换用リスト(列表)(合并3个JSON文件).json"), encoding="utf-8"))
GL = dd["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]
G2 = dd["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]
GG = dd["全域替换用のリスト(列表)型配列(replacements_final_list)"]
ps = m.import_placeholders(lp(DATA + r"\占位符(placeholders)_%1854%-%4934%_文字列替换skip用.txt"))
pl = m.import_placeholders(lp(DATA + r"\占位符(placeholders)_@5134@-@9728@_局部文字列替换结果捕捉用.txt"))

SRC = BASE + r"\RO_2026-07_esperanto_sentences_ja.md"
items = []  # (type, a, b)
for line in open(lp(SRC), encoding="utf-8"):
    line = line.rstrip("\n")
    mo = re.match(r'^## (.+)', line)
    if mo and 'PDFページ' in line: items.append(('page', mo.group(1), '')); continue
    mo = re.match(r'^### (.+)', line)
    if mo: items.append(('sec', mo.group(1), '')); continue
    mo = re.match(r'^\*\*EO (\d+)\.\*\* (.+)', line)
    if mo: items.append(('eo', mo.group(1), mo.group(2))); continue
    mo = re.match(r'^\*\*JA (\d+)\.\*\* (.+)', line)
    if mo: items.append(('ja', mo.group(1), mo.group(2))); continue

# EO文をバッチorchestrate(改行区切り)
eos = [b for t, a, b in items if t == 'eo']
text = "\n".join(eos)
h = m.orchestrate_comprehensive_esperanto_text_replacement(text, ps, GL, pl, GG, G2, FMT)
ruby_lines = h.split("\n")
assert len(ruby_lines) == len(eos), f"{len(ruby_lines)} != {len(eos)}"
ruby_map = {}
i = 0
for t, a, b in items:
    if t == 'eo': ruby_map[a] = ruby_lines[i]; i += 1

# アプリCSSヘッダを取得(本文構造は自前)
full = m.apply_ruby_html_header_and_footer("@@@", FMT)
head = full.split('<p class="text-M_M">')[0]
EXTRA = """
      body { max-width: 980px; margin: 0 auto; padding: 1.2em 1.4em; }
      h1 { font-size: 1.5rem; color:#1a2a4a; }
      h2 { font-size: 1.25rem; color:#1a2a4a; border-bottom: 2px solid #4466aa; padding-bottom:0.2em; margin-top: 1.8em; }
      h3 { font-size: 1.05rem; color:#3a4a6a; margin-top: 1.3em; }
      .pair { margin: 0.2em 0 1.7em; border-left: 3px solid #cfd8e8; padding-left: 0.9em; }
      p.text-M_M { margin: 0.1em 0 0.2em; }
      .ja { color:#333; font-size: 0.95rem; line-height: 1.7; margin: 0.5em 0 0; }
      .num { color:#9aa; font-size: 0.8rem; font-weight: bold; margin-right: 0.4em; }
      .intro { color:#555; font-size:0.9rem; background:#f6f8fc; padding:0.8em 1em; border-radius:6px; }
"""
head = head.replace("    </style>", EXTRA + "    </style>")

body = ['<h1>RO_2026-07 エスペラント本文 ルビ注釈版（日本語）</h1>',
        '<p class="intro">現状の日本語版アプリ（tier15/16 適用・コーパス境界一致99.4%）で各エスペラント本文の語根上に日本語訳ルビを付与。各文の下に日本語全訳を併記。ルビ＝語根ごとの意味、全訳＝文意。</p>']
ja_map = {a: b for t, a, b in items if t == 'ja'}
for t, a, b in items:
    if t == 'page': body.append(f'<h2>{a}</h2>')
    elif t == 'sec': body.append(f'<h3>{a}</h3>')
    elif t == 'eo':
        body.append('<div class="pair">')
        body.append(f'<p class="text-M_M"><span class="num">{a}</span>{ruby_map.get(a,"")}</p>')
        if a in ja_map: body.append(f'<p class="ja">{ja_map[a]}</p>')
        body.append('</div>')

out = head + "\n".join(body) + "\n</body></html>"
OUTP = BASE + r"\RO_2026-07_esperanto_sentences_ruby_ja.html"
with open(lp(OUTP), "w", encoding="utf-8") as f: f.write(out)
print(f"出力: {OUTP}\n文数: {len(eos)} / サイズ: {os.path.getsize(lp(OUTP)):,}B")
# サンプル(ルビのプレーン抽出)で確認
def plain_ruby(hh):
    toks=[];pos=0
    for mm in re.finditer(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>',hh):
        for ch in re.findall(r'\S+',re.sub('<[^>]+>','',hh[pos:mm.start()])): toks.append(ch)
        toks.append(f'{mm.group(1)}[{mm.group(2)}]'); pos=mm.end()
    for ch in re.findall(r'\S+',re.sub('<[^>]+>','',hh[pos:])): toks.append(ch)
    return ' '.join(toks)
print("\n--- サンプル(語根[訳]) ---")
for n in ['3','19','71']:
    print(f"EO {n}: {plain_ruby(ruby_map[n])}")
