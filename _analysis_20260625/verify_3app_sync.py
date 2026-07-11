# -*- coding: utf-8 -*-
"""コメント/docstring/整形を除いたロジック構造(AST)で3アプリのモジュールを比較。"""
import ast, sys, os
sys.stdout.reconfigure(encoding='utf-8')
BASE=r"D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\エスペラントの漢字化プロジェクト総結集20260630\語根分解、注釈ルビ振り、漢字化アプリ徹底ブラッシュアップ20260630"
PFX=chr(92)*2+chr(63)+chr(92)
def LP(p): return PFX+os.path.abspath(p)
def strip_docstrings(tree):
    for node in ast.walk(tree):
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef,ast.Module)):
            b=node.body
            if b and isinstance(b[0],ast.Expr) and isinstance(getattr(b[0],'value',None),ast.Constant) and isinstance(b[0].value.value,str):
                node.body=b[1:]
    return tree
def norm(p):
    src=open(LP(p),encoding='utf-8').read()
    t=strip_docstrings(ast.parse(src))
    return ast.dump(t)  # フィールドのみ、位置情報なし
MODS=['esp_text_replacement_module.py','esp_replacement_json_make_module.py','esp_overlay_module.py',
      'esp_generation_module.py','main.py','pages/1_🔧_語根分解の手動補正.py','pages/2_📦_最新データのダウンロード.py']
for m in MODS:
    dumps={}
    for L in ('JA','ZH','KO'):
        p=os.path.join(BASE,f'Esperanto-Kanji-Ruby-{L}',m.replace('/',os.sep))
        try: dumps[L]=norm(p)
        except Exception as e: dumps[L]=f'ERR:{e}'
    same=len(set(dumps.values()))==1
    print(f"{'✓ロジック同一' if same else '✗ロジック乖離!'} {m}")
    if not same:
        import difflib
        # JA↔ZH, JA↔KO のノード差を粗く
        for pair in (('JA','ZH'),('JA','KO')):
            if dumps['JA']!=dumps[pair[1]]:
                # 関数単位で比較
                ta=strip_docstrings(ast.parse(open(LP(os.path.join(BASE,'Esperanto-Kanji-Ruby-JA',m.replace('/',os.sep))),encoding='utf-8').read()))
                tb=strip_docstrings(ast.parse(open(LP(os.path.join(BASE,f'Esperanto-Kanji-Ruby-{pair[1]}',m.replace('/',os.sep))),encoding='utf-8').read()))
                fa={n.name:ast.dump(n) for n in ast.walk(ta) if isinstance(n,ast.FunctionDef)}
                fb={n.name:ast.dump(n) for n in ast.walk(tb) if isinstance(n,ast.FunctionDef)}
                onlyA=set(fa)-set(fb); onlyB=set(fb)-set(fa)
                difff=[k for k in fa if k in fb and fa[k]!=fb[k]]
                print(f"   [{pair[0]}↔{pair[1]}] JA限定関数={onlyA or '-'} {pair[1]}限定={onlyB or '-'} ロジック差関数={difff or '-'}")
