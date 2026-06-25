# -*- coding: utf-8 -*-
"""
PEJVO形式ファイル(word/with/slashes:def)から
  - E_stem_with_Part_Of_Speech_list  (品詞付き語幹リスト)
  - 語根リスト (全ユニーク語根)
を抽出するライブラリ。
アプリ同梱ノートブックのロジックを忠実に移植したもの。
"""
import re

def lp(path):
    r"""Windowsロングパス(>260)対策。ローカルドライブ絶対パスに \\?\ を前置。"""
    if path.startswith('\\\\?\\'):
        return path
    if path.startswith('\\\\'):          # UNC (例: \\wsl.localhost\...)
        return '\\\\?\\UNC' + path[1:]
    if len(path) > 2 and path[1] == ':':  # ローカル絶対 (例: d:\...)
        return '\\\\?\\' + path
    return path

hat_to_circumflex = {'c^':'ĉ','g^':'ĝ','h^':'ĥ','j^':'ĵ','s^':'ŝ','u^':'ŭ',
                     'C^':'Ĉ','G^':'Ĝ','H^':'Ĥ','J^':'Ĵ','S^':'Ŝ','U^':'Ŭ'}

def replace_esperanto_chars(text, d):
    for a,b in d.items():
        text = text.replace(a,b)
    return text

def contains_digit(s):
    return any(c.isdigit() for c in s)

def normalize_lines(path, skip_marker_lines=False):
    """ファイルを読み、hat→字上符変換＋小文字化した行リストを返す。"""
    with open(lp(path), 'r', encoding='utf-8') as f:
        text = f.read()
    text = replace_esperanto_chars(text, hat_to_circumflex)
    text = text.lower()
    lines = text.split('\n')
    if skip_marker_lines:
        lines = [ln for ln in lines if not ln.startswith('##')]
    return lines

# ---------- E_stem 抽出 (詳細説明ノートブック cell を忠実移植) ----------
def extract_estem(lines):
    E_stem_with_Part_Of_Speech_list = []
    for line in lines:
        line = line.replace('-', '/')   # 20240618
        E_wordS = line.split(":")[0]
        E_wordS = E_wordS.lstrip('/')
        E_wordS_list = re.split('-| |,', E_wordS)
        for jj in range(len(E_wordS_list)):
            E_word = E_wordS_list[jj]
            if '#' in E_word:           # マーカー混入除去 (gold対応)
                continue
            if not (contains_digit(E_word) or len(E_word) < 2):
                if "/" in E_word:
                    E_stem_w = ["/".join(E_word.split("/")[:-1])]
                    if E_word.endswith(('/o','/on','/oj','/o!','/ojn','/on!')):
                        E_stem_w.append('名词')
                    elif E_word.endswith(('/a','/aj','/an','/an!')):
                        E_stem_w.append('形容词')
                    elif E_word.endswith(('/e','/e!')):
                        E_stem_w.append('副词')
                    elif E_word.endswith(('/e/n','/e/n!')):
                        E_stem_w = [E_word, "無詞"]
                    elif E_word.endswith(('/i','/u','/u!')):
                        E_stem_w.append('动词')
                    elif E_word.endswith(('/n')):
                        E_stem_w.append('n词')
                    # 上記いずれにも該当しない場合、要素1個のまま append される
                    # (元コードと同じ挙動: stem のみで品詞無し)
                else:
                    E_stem_w = [E_word, "无词"]
                E_stem_with_Part_Of_Speech_list.append(E_stem_w)
    return E_stem_with_Part_Of_Speech_list

# ---------- 語根抽出 (抽出ノートブック cell を忠実移植) ----------
def extract_roots(lines):
    roots = set()
    for line in lines:
        line = line.replace('-', '/')
        word = line.split(":")[0]
        word = word.lstrip('/')
        parts = re.split('-| |,', word)
        part = parts[0]                 # ★先頭トークンのみ
        subparts = re.split('/| ', part)
        for subpart in subparts:
            x = subpart.strip()
            if '#' in x:
                continue
            if len(x) >= 2:
                roots.add(x)
    unique = list(set(roots))
    sorted_roots = sorted(unique, key=lambda r: (-len(r), r))
    return sorted_roots
