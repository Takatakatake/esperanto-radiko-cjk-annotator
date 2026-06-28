# -*- coding: utf-8 -*-
"""指定アプリの esp_text_replacement_module(fixpoint化後) を読み込み、
   正常分解＋エラー無しを確認。 python _verify_fixpoint.py <JP|ZH|KO>"""
import json, sys, re
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')
from gen_replacement import lp
BASE = r'd:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624'
APPS = {'JP': r'\Esperanto-Kanji-Converter-and-Ruby-Annotation-Tool',
        'ZH': r'\Esperanto-Hanzi-Converter-and-Ruby-Annotation-Tool-Chinese',
        'KO': r'\Esperanto-Kanji-Converter-and-Ruby-Annotation-Tool-Korean'}
key = sys.argv[1]
d = APPS[key]
sys.path.insert(0, BASE + d)
import esp_text_replacement_module as m
DATA = BASE + d + r'\Appの运行に使用する各类文件'
dd = json.load(open(lp(DATA + r'\最终的な替换用リスト(列表)(合并3个JSON文件).json'), encoding='utf-8'))
GL = dd['局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)']
G2 = dd['二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)']
GG = dd['全域替换用のリスト(列表)型配列(replacements_final_list)']
ps = m.import_placeholders(lp(DATA + r'\占位符(placeholders)_%1854%-%4934%_文字列替换skip用.txt'))
pl = m.import_placeholders(lp(DATA + r'\占位符(placeholders)_@5134@-@9728@_局部文字列替换结果捕捉用.txt'))
def roots(t):
    h = m.orchestrate_comprehensive_esperanto_text_replacement(t, ps, GL, pl, GG, G2, 'HTML格式_Ruby文字_大小调整')
    toks = []; pos = 0
    for mm in re.finditer(r'<ruby>(.*?)<rt[^>]*>.*?</rt></ruby>', h):
        for ch in re.findall(r'[a-zĉĝĥĵŝŭ]+', re.sub(r'<[^>]+>', '', h[pos:mm.start()]), re.I): toks.append(ch)
        toks.append(mm.group(1)); pos = mm.end()
    for ch in re.findall(r'[a-zĉĝĥĵŝŭ]+', re.sub(r'<[^>]+>', '', h[pos:]), re.I): toks.append(ch)
    return '/'.join(toks)
# 正常語(壊れていないこと)＋fixpointが効く語＋文章
tests = ['esperanto', 'fari', 'vino', 'lernejeto', 'malsanulejo', 'grandega',
         'beligejeto', 'fariĝemulo', 'La rapida bruna vulpo saltas.']
print(f'=== {key} (fixpoint後) ===')
ok = True
for t in tests:
    try:
        print(f'  {t:32s}-> {roots(t)}')
    except Exception as e:
        print(f'  {t:32s}-> ERROR: {e}'); ok = False
print('  判定:', 'OK(エラー無し)' if ok else 'NG')
