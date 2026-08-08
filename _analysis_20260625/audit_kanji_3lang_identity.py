# -*- coding: utf-8 -*-
"""第111R新設: 漢字トラックの3言語(JA/ZH/KO)同一性ゲート。測定のみ・無変更。

check_kanji_structure.py はGGのキー集合一致しか見ないため、
 (a) 値(漢字)の言語間差、(b) 並び順(=置換優先度)の言語間差、(c) GL/G2の言語間差、
 (d) 共有ロジック.pyの挙動差
は全て死角だった。是正スクリプトはJA→ZH→KOの順に独立ループするため、途中失敗や
片言語だけの手当てがあるとここが割れる(漢字値は言語非依存が設計)。本ゲートで検知する。

検査1: 置換リスト_漢字.json の GG/G2/GL を (key, value) の【位置つき】完全一致で比較。
       第3要素(タグ)は言語接尾辞($R110A00001ZH$等)を持つ設計なので比較除外。
検査2: 共有ロジック4本のASTをdocstring除去で比較。裁定済みの差のみ許容:
       - apply_ruby_html_header_and_footer … <title>のi18n+コメント差のみ(CSS実値は
         3言語一致を第111Rで実読確認)
       - create_replacements_list_for_localized_replacement … KOの変数リネーム
         (tmp_replacements_list_for_localized_string→tmp_list)のみ。ロジック同一
       - esp_replacement_json_make_module の output_format/<toplevel> … .format↔f-string
         の書式リファクタとJA残置のformat_type変数(未使用)。閾値ロジック(ratio_1>6等)は同一
       許容外の新たな差が出たらFAIL(非0終了)。

第111R実測(2026-08-05, app b0f84af): 全PASS。端到端(各自モジュール+各自データで同一文変換)
もバイト一致を確認済み。
"""
import ast, json, gc, os, sys, itertools
sys.stdout.reconfigure(encoding='utf-8')
BS = chr(92); PFX = BS * 2 + chr(63) + BS
def LP(p): return p if p.startswith(PFX) else PFX + os.path.abspath(p)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANGS = ('JA', 'ZH', 'KO')
KEYS = ('全域替换用のリスト(列表)型配列(replacements_final_list)',
        '二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)',
        '局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)')
MODS = ('esp_text_replacement_module.py', 'esp_overlay_module.py',
        'esp_replacement_json_make_module.py', 'esp_generation_module.py')
# 裁定済みの許容差(第111R)。新規追加は必ず実ソースを読み挙動同一を確認してから。
ALLOWED_AST_DIFF = {
    ('esp_text_replacement_module.py', 'def', 'apply_ruby_html_header_and_footer'),
    ('esp_text_replacement_module.py', 'def', 'create_replacements_list_for_localized_replacement'),
    ('esp_replacement_json_make_module.py', 'def', 'output_format'),
    ('esp_replacement_json_make_module.py', 'module', '<toplevel-stmts>'),
}
failed = False

# ── 検査1: データ同一性(位置つき) ─────────────────────────────────
def kv(e):
    if isinstance(e, list):
        return (e[0] if e else None, e[1] if len(e) > 1 else None)
    return (e, None)

def load_json(L):
    p = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{L}', 'app_data', '置換リスト_漢字.json')
    with open(LP(p), encoding='utf-8') as f:
        return json.load(f)

ja = load_json('JA')
for L in ('ZH', 'KO'):
    d = load_json(L)
    if set(d) != set(ja):
        failed = True
        print(f'[{L}] ★トップレベルキー集合が不一致: {sorted(set(d) ^ set(ja))}')
    for k in KEYS:
        a, b = ja.get(k), d.get(k)
        if not (isinstance(a, list) and isinstance(b, list)):
            failed = True; print(f'[{L}] {k}: ★リスト欠落/型差'); continue
        pos_diff = sum(1 for x, y in zip(a, b) if kv(x) != kv(y))
        ok = (pos_diff == 0 and len(a) == len(b))
        print(f'[{L}] {k.split("(")[0]}: len {len(a)} vs {len(b)} / 位置つき差 {pos_diff}'
              f'  {"OK" if ok else "★DIFF"}')
        if not ok:
            failed = True
            shown = 0
            for i, (x, y) in enumerate(zip(a, b)):
                if kv(x) != kv(y):
                    print(f'   @{i}: {kv(x)!r} vs {kv(y)!r}'); shown += 1
                    if shown >= 5: break
    del d; gc.collect()
del ja; gc.collect()

# ── 検査2: 共有ロジックAST比較 ────────────────────────────────────
def strip_docstrings(tree):
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, 'body', None)
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                node.body = body[1:] or [ast.Pass()]
    return tree

def top_map(path):
    tree = strip_docstrings(ast.parse(open(LP(path), encoding='utf-8').read()))
    out, other = {}, []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out[('def', node.name)] = ast.dump(node)
        else:
            other.append(ast.dump(node))
    out[('module', '<toplevel-stmts>')] = chr(10).join(other)
    return out

for mod in MODS:
    maps = {L: top_map(os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{L}', mod)) for L in LANGS}
    for a, b in itertools.combinations(LANGS, 2):
        diff = [k for k in (set(maps[a]) | set(maps[b]))
                if maps[a].get(k) != maps[b].get(k)]
        new = [k for k in diff if (mod, k[0], k[1]) not in ALLOWED_AST_DIFF]
        note = '' if not diff else f' (裁定済み差 {len(diff) - len(new)})'
        if new:
            failed = True
            print(f'[{mod}] {a} vs {b}: ★許容外のAST差 {len(new)}: '
                  + ', '.join(str(k) for k in new[:6]) + note)
        else:
            print(f'[{mod}] {a} vs {b}: OK{note}')

if failed:
    print('★3言語同一性: FAIL'); raise SystemExit(1)
print('漢字トラック3言語同一性(データ順序込み+共有ロジック): PASS')
