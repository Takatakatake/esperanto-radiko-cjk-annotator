# エスペラント文字変換・ルビ振りツール 技術解説書

## 目次

1. [アプリケーション構成概要](#1-アプリケーション構成概要)
2. [データフローと処理の流れ](#2-データフローと処理の流れ)
3. [コア機能の技術的実装](#3-コア機能の技術的実装)
4. [JSONファイル生成ロジック](#4-jsonファイル生成ロジック)
5. [並列処理の実装](#5-並列処理の実装)
6. [拡張と最適化](#6-拡張と最適化)

## 1. アプリケーション構成概要

このアプリケーションはStreamlitベースのWebアプリとして構成され、4つの主要Pythonファイルから成り立っています。

### ファイル構造と役割

- **main.py**
  - メインアプリケーションのエントリーポイント
  - Streamlitのページ設定、UI構築、ユーザー入力処理
  - 置換ロジックの実行とレンダリング制御

- **エスペラント文(漢字)置換用のJSONファイル生成ページ.py**
  - Streamlitの「pages」ディレクトリに配置される別ページ
  - 置換ルールを定義するJSONファイルを生成するためのUI/機能

- **esp_text_replacement_module.py**
  - エスペラント文字の変換と置換のためのコア関数を提供
  - プレースホルダー処理、特殊文字変換、文字列置換ロジック
  - 並列処理サポート関数

- **esp_replacement_json_make_module.py**
  - JSONファイル生成ロジックとユーティリティ関数
  - 文字幅測定、出力フォーマット、置換ルールビルド処理

### 依存関係とライブラリ

アプリケーションは以下の主要ライブラリに依存しています：

```
streamlit       # Webインターフェース構築
pandas          # データ処理とCSV操作
json            # JSON操作
re              # 正規表現処理
multiprocessing # 並列処理
typing          # 型アノテーション
```

### モジュール間の関係性

```
main.py
  ├── esp_text_replacement_module.py (インポート)
  │     └── 複数の関数をインポート (x_to_circumflex, replace_esperanto_chars など)
  └── 並列処理設定 (multiprocessing.set_start_method)

エスペラント文(漢字)置換用のJSONファイル生成ページ.py
  ├── esp_text_replacement_module.py (インポート)
  │     └── 複数の関数をインポート (convert_to_circumflex, safe_replace など)
  ├── esp_replacement_json_make_module.py (インポート)
  │     └── 複数の関数をインポート (output_format, parallel_build_pre_replacements_dict など)
  └── 並列処理設定 (multiprocessing.set_start_method)
```

## 2. データフローと処理の流れ

### メインアプリケーション（main.py）のデータフロー

1. **初期化と設定ロード**
   - JSONファイルのロード（`load_replacements_lists`関数）
   - 占位符（プレースホルダー）ファイルのインポート
   - Streamlit UIの構築

2. **ユーザー入力処理**
   - テキスト入力（直接入力またはファイルアップロード）
   - 出力形式の選択
   - 並列処理オプションの設定

3. **テキスト処理の実行フロー**
   - 送信ボタンクリック時に入力テキストを処理
   - 並列処理の有無によって処理関数を分岐
   - 文字形式変換の適用（上付き文字/x形式/^形式）
   - HTMLヘッダー・フッターの適用（必要な場合）

4. **結果表示とダウンロード**
   - 処理結果の表示（HTMLプレビュー/ソースコード/テキスト）
   - ダウンロードボタンの提供

### JSONファイル生成ページのデータフロー

1. **入力データの準備**
   - CSVファイルのアップロードまたはデフォルト選択
   - 語根分解法JSONファイルのアップロードまたはデフォルト選択
   - 置換後文字列JSONファイルのアップロードまたはデフォルト選択

2. **JSONファイル生成処理**
   - エスペラント語根のロード
   - 置換リストの作成と優先順位付け
   - 品詞ごとの派生形追加
   - 並列処理によるリスト構築

3. **JSONファイルのエクスポート**
   - 3つの置換リストを含む最終的なJSONファイルの作成
   - ダウンロードボタンの提供

### 核となる置換処理フロー

`orchestrate_comprehensive_esperanto_text_replacement`関数のフロー：

1. 空白の正規化とエスペラント文字の字上符形式への統一
2. `%...%`で囲まれた部分を一時的なプレースホルダーに置換（スキップ処理）
3. `@...@`で囲まれた部分を局所的置換用プレースホルダーに置換
4. 大域的置換リストによる文字列置換
5. 2文字語根置換（2回実行）
6. プレースホルダーを最終的な文字列に戻す
7. フォーマット固有の後処理（HTMLの場合は改行を`<br>`に変換など）

## 3. コア機能の技術的実装

### エスペラント文字の変換システム

アプリケーションは3つの主要なエスペラント文字表記形式を扱います：

1. **字上符形式**（ĉ, ĝ, ĥ, ĵ, ŝ, ŭ）
2. **x表記形式**（cx, gx, hx, jx, sx, ux）
3. **ハット記号形式**（c^, g^, h^, j^, s^, u^）

これらの変換用に双方向の変換辞書が定義されています：

```python
x_to_circumflex = {'cx': 'ĉ', 'gx': 'ĝ', ...}
circumflex_to_x = {'ĉ': 'cx', 'ĝ': 'gx', ...}
x_to_hat = {'cx': 'c^', 'gx': 'g^', ...}
hat_to_x = {'c^': 'cx', 'g^': 'gx', ...}
hat_to_circumflex = {'c^': 'ĉ', 'g^': 'ĝ', ...}
circumflex_to_hat = {'ĉ': 'c^', 'ĝ': 'g^', ...}
```

変換関数は単純な文字列置換を使用しています：

```python
def replace_esperanto_chars(text, char_dict: Dict[str, str]) -> str:
    for original_char, converted_char in char_dict.items():
        text = text.replace(original_char, converted_char)
    return text
```

### プレースホルダーメカニズム

複数回にわたる置換処理での干渉を防ぐために、巧妙なプレースホルダーメカニズムが採用されています：

```python
def safe_replace(text: str, replacements: List[Tuple[str, str, str]]) -> str:
    valid_replacements = {}
    # まず old→placeholder
    for old, new, placeholder in replacements:
        if old in text:
            text = text.replace(old, placeholder)
            valid_replacements[placeholder] = new
    # 次に placeholder→new
    for placeholder, new in valid_replacements.items():
        text = text.replace(placeholder, new)
    return text
```

この関数は3段階の置換を行います：
1. 元のテキストを一時的なプレースホルダーに置換
2. 他の置換処理を実行
3. プレースホルダーを最終的な置換テキストに置き換え

これにより、先に置換された部分が後の置換処理で誤って置換されるのを防ぎます。

### 特殊マーカー処理（%と@）

アプリケーションでは2種類の特殊マーカーが使用されています：

1. **%マーカー** - 置換をスキップするためのマーカー
   ```python
   # '%' で囲まれた箇所をスキップするための正規表現
   PERCENT_PATTERN = re.compile(r'%(.{1,50}?)%')
   ```

2. **@マーカー** - 局所的な置換のためのマーカー
   ```python
   # '@' で囲まれた箇所を局所置換するための正規表現
   AT_PATTERN = re.compile(r'@(.{1,18}?)@')
   ```

これらのマーカー内のテキストを検出して特別に処理するための関数が実装されています：

```python
def find_percent_enclosed_strings_for_skipping_replacement(text: str) -> List[str]:
    """'%foo%' の形を全て抽出。50文字以内に限定。"""
    # 実装詳細...

def create_replacements_list_for_intact_parts(text: str, placeholders: List[str]) -> List[Tuple[str, str]]:
    """
    '%xxx%' で囲まれた箇所を検出し、
    ( '%xxx%', placeholder ) という形で対応させるリストを作る
    """
    # 実装詳細...
```

### 出力フォーマット処理

アプリケーションは複数の出力フォーマットをサポートしています：

```python
def output_format(main_text, ruby_content, format_type, char_widths_dict):
    """
    エスペラント語根(main_text) と それに対応する訳/漢字(ruby_content) を
    指定の format_type で繋ぎ合わせる
    """
    if format_type == 'HTML格式_Ruby文字_大小调整':
        # ルビサイズ調整ロジック...
    elif format_type == 'HTML格式_Ruby文字_大小调整_汉字替换':
        # 漢字置換ロジック...
    elif format_type == 'HTML格式':
        return f'<ruby>{main_text}<rt>{ruby_content}</rt></ruby>'
    elif format_type == 'HTML格式_汉字替换':
        return f'<ruby>{ruby_content}<rt>{main_text}</rt></ruby>'
    elif format_type == '括弧(号)格式':
        return f'{main_text}({ruby_content})'
    elif format_type == '括弧(号)格式_汉字替换':
        return f'{ruby_content}({main_text})'
    elif format_type == '替换后文字列のみ(仅)保留(简单替换)':
        return f'{ruby_content}'
```

特に興味深いのは、HTMLのルビサイズ調整機能です。テキストとルビの幅比率に基づいて、異なるCSSクラスを適用します：

```python
width_ruby = measure_text_width_Arial16(ruby_content, char_widths_dict)
width_main = measure_text_width_Arial16(main_text, char_widths_dict)
ratio_1 = width_ruby / width_main
if ratio_1 > 6:
    return f'<ruby>{main_text}<rt class="XXXS_S">{insert_br_at_third_width(ruby_content, char_widths_dict)}</rt></ruby>'
elif ratio_1 > (9/3):
    return f'<ruby>{main_text}<rt class="XXS_S">{insert_br_at_half_width(ruby_content, char_widths_dict)}</rt></ruby>'
# 以下同様...
```

## 4. JSONファイル生成ロジック

JSONファイル生成ページの核となる部分は、エスペラント語根から包括的な置換リストを生成するロジックです。

### 1. 基本データ構造

生成されるJSONファイルには3つの主要リストが含まれます：

```json
{
  "全域替换用のリスト(列表)型配列(replacements_final_list)": [...],
  "二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)": [...],
  "局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)": [...]
}
```

各リストの要素は `[old, new, placeholder]` の形式です。

### 2. 置換ルールの優先順位付け

置換ルールには優先順位が設定され、文字数の多いものから処理されます：

```python
# 基本優先順位 = 文字数 × 10000
pre_replacements_dict_2[i.replace('/', '')]=
    [j[0].replace("</rt></ruby>","%%%").replace('/', '').replace("%%%","</rt></ruby>"),
     j[1],
     len(i.replace('/', ''))*10000]
```

### 3. 品詞別の派生形生成

名詞、形容詞、動詞などの品詞ごとに異なる派生形を生成します：

```python
# 名詞の例
if "名词" in j[1]:
    for k in ["o","on",'oj']:
        if not i+k in pre_replacements_dict_2:
            pre_replacements_dict_3[i+k]=[j[0]+k,j[2]+len(k)*10000-3000]
        # ...

# 動詞の例
if "动词" in j[1]:
    for k1,k2 in verb_suffix_2l_2.items():
        if not i+k1 in pre_replacements_dict_2:
            pre_replacements_dict_3[i+k1]=[j[0]+k2,j[2]+len(k1)*10000-3000]
        # ...
```

### 4. 特殊ケース処理

- **-an, -on 接尾辞処理**: 会員や分数を表す接尾辞の特別処理
- **2文字語根処理**: 接頭辞・接尾辞・単独使用パターン別の処理
- **大文字・小文字・文頭大文字**: 3パターンの変形を生成

```python
# 大文字・小文字・文頭大文字のパターン生成例
pre_replacements_list_4.append((old,new,place_holder))
pre_replacements_list_4.append((old.upper(),new.upper(),place_holder[:-1]+'up$'))
pre_replacements_list_4.append((old.capitalize(),capitalize_ruby_and_rt(new),place_holder[:-1]+'cap$'))
```

### 5. ユーザーカスタム設定の適用

JSONファイルからユーザー定義の語根分解法や置換後文字列を読み込み適用します：

```python
for i in custom_stemming_setting_list:
    if len(i)==3:
        esperanto_Word_before_replacement = i[0].replace('/', '')
        if i[1]=="dflt":
            replacement_priority_by_length=len(esperanto_Word_before_replacement)*10000
        elif i[1] in allowed_values:
            # 置換対象から除外する処理
        # ...
```

## 5. 並列処理の実装

アプリケーションは大きなテキストを効率的に処理するために並列処理を実装しています。

### 1. メインアプリケーションでの並列処理

```python
def parallel_process(
    text: str,
    num_processes: int,
    placeholders_for_skipping_replacements: List[str],
    # その他のパラメータ...
) -> str:
    """
    与えられた text を行単位で分割し、process_segment を
    マルチプロセスで並列実行した結果を結合する。
    """
    # 行ごとに分割
    lines = re.findall(r'.*?\n|.+$', text)
    num_lines = len(lines)

    # プロセス分割
    lines_per_process = max(num_lines // num_processes, 1)
    ranges = [(i * lines_per_process, (i + 1) * lines_per_process) for i in range(num_processes)]
    ranges[-1] = (ranges[-1][0], num_lines)  # 最後のプロセスに残りを割り当て

    # 並列実行
    with multiprocessing.Pool(processes=num_processes) as pool:
        results = pool.starmap(
            process_segment,
            [
                (
                    lines[start:end],
                    # その他のパラメータ...
                )
                for (start, end) in ranges
            ]
        )
    return ''.join(results)
```

### 2. JSONファイル生成での並列処理

```python
def parallel_build_pre_replacements_dict(
    E_stem_with_Part_Of_Speech_list: List[List[str]],
    replacements: List[Tuple[str, str, str]],
    num_processes: int = 4
) -> Dict[str, List[str]]:
    """
    データを num_processes 個に分割し、process_chunk_for_pre_replacements を並列実行
    最終的に辞書をマージして返す。
    """
    # チャンク分割
    total_len = len(E_stem_with_Part_Of_Speech_list)
    chunk_size = -(-total_len // num_processes)
    chunks = []
    # 分割ロジック...

    # 並列実行
    with multiprocessing.Pool(num_processes) as pool:
        partial_dicts = pool.starmap(
            process_chunk_for_pre_replacements,
            [(chunk, replacements) for chunk in chunks]
        )

    # 結果マージ
    merged_dict = {}
    # マージロジック...
    return merged_dict
```

### 3. multiprocessing初期化

macOSなどで発生する可能性がある `PicklingError` を避けるために、明示的に 'spawn' 開始方式を設定しています：

```python
try:
    multiprocessing.set_start_method("spawn")
except RuntimeError:
    pass  # すでに start method が設定済みの場合はここで無視する
```

## 6. 拡張と最適化

### 1. 文字幅計測とレイアウト最適化

ルビの表示に最適なレイアウトを実現するために、文字幅を計測して改行位置を決定するロジックが実装されています：

```python
def measure_text_width_Arial16(text, char_widths_dict: Dict[str, int]) -> int:
    """
    JSONで読み込んだ {文字: 幅(px)} の辞書を使い、
    text の合計幅を算出する
    """
    total_width = 0
    for ch in text:
        char_width = char_widths_dict.get(ch, 8)
        total_width += char_width
    return total_width

def insert_br_at_half_width(text, char_widths_dict: Dict[str, int]) -> str:
    """
    文字列幅が半分を超えたら <br> を入れる
    """
    # 実装詳細...
```

### 2. 重複ルビの最適化

バージョン202502で追加された機能で、親文字列とルビが同一の場合にルビを削除する最適化：

```python
def remove_redundant_ruby_if_identical(text: str) -> str:
    """
    <ruby>xxx<rt class="XXL_L">xxx</rt></ruby> のように、
    親文字列とルビ文字列が完全に同一の場合に <ruby> を取り除く
    """
    def replacer(match: re.Match) -> str:
        group1 = match.group(1)
        group2 = match.group(2)
        if group1 == group2:
            return group1
        else:
            return match.group(0)
    replaced_text = IDENTICAL_RUBY_PATTERN.sub(replacer, text)
    return replaced_text
```

### 3. セッション状態管理

Streamlitセッション状態を使用して、テキスト入力を保持しています：

```python
# 初期値取得
initial_text = st.session_state.get("text0_value", "")

# テキストエリア
text0 = st.text_area(
    "エスペラントの文章を入力してください",
    height=150,
    value=initial_text
)

# 送信時に保存
if submit_btn:
    # 入力テキストをセッションステートに保存しておく
    st.session_state["text0_value"] = text0
```

### 4. 大きなテキスト対応

大きなテキストを効率的に表示するための制限と対策：

```python
# 巨大テキスト対策ロジック（行数ベースで一部省略表示）
MAX_PREVIEW_LINES = 250  # 250行まで表示
lines = processed_text.splitlines()  # 改行区切りでリスト化
if len(lines) > MAX_PREVIEW_LINES:
    # 先頭247行 + "..." + 末尾3行のプレビュー
    first_part = lines[:247]
    last_part = lines[-3:]
    preview_text = "\n".join(first_part) + "\n...\n" + "\n".join(last_part)
    st.warning(
        f"テキストが長いため（総行数 {len(lines)} 行）、"
        "全文プレビューを一部省略しています。末尾3行も表示します。"
    )
else:
    preview_text = processed_text
```

## 7. テキスト処理アルゴリズムの詳細分析

エスペラント文字変換・ルビ振りツールの核心は、テキスト処理アルゴリズムです。ここでは、その詳細なメカニズムを掘り下げます。

### 7.1 多段階置換プロセス

`orchestrate_comprehensive_esperanto_text_replacement` 関数は、複数の置換処理を順序立てて実行する複合アルゴリズムです。この段階的アプローチには重要な理由があります：

```python
def orchestrate_comprehensive_esperanto_text_replacement(
    text,
    placeholders_for_skipping_replacements,
    replacements_list_for_localized_string,
    placeholders_for_localized_replacement,
    replacements_final_list,
    replacements_list_for_2char,
    format_type
) -> str:
    # 1) 空白の正規化 → 2) エスペラント文字の字上符形式統一
    text = unify_halfwidth_spaces(text)
    text = convert_to_circumflex(text)

    # 3) %で囲まれた部分をスキップ
    replacements_list_for_intact_parts = create_replacements_list_for_intact_parts(text, placeholders_for_skipping_replacements)
    # ...スキップ処理の実装...

    # 4) @で囲まれた部分を局所置換
    tmp_replacements_list_for_localized_string_2 = create_replacements_list_for_localized_replacement(
        text, placeholders_for_localized_replacement, replacements_list_for_localized_string
    )
    # ...局所置換の実装...

    # 5) 大域置換 (old, new, placeholder)
    valid_replacements = {}
    for old, new, placeholder in replacements_final_list:
        if old in text:
            text = text.replace(old, placeholder)
            valid_replacements[placeholder] = new

    # 6) 2文字語根置換(2回)
    # ...2文字語根置換の実装...

    # 7) 各種プレースホルダー復元
    # ...プレースホルダー復元の実装...

    # 8) HTML形式調整
    if "HTML" in format_type:
        text = text.replace("\n", "<br>\n")
        # ...HTML形式調整の実装...

    return text
```

この多段階アプローチには以下の利点があります：

1. **分離された関心事**: 各ステップが1つの明確な処理を担当
2. **防衛的プログラミング**: 前のステップで保護した要素（プレースホルダー化した部分）は後続の処理に影響されない
3. **拡張性**: 新しい処理ステップを挿入しやすい構造になっている

### 7.2 プレースホルダー置換技術の詳細

プレースホルダーシステムはこのアプリの基盤となる技術です。これにより、処理の順序に関係なく、テキストの特定部分を保護または特別処理できます。

プレースホルダーファイルの構成：
- `占位符(placeholders)_%1854%-%4934%_文字列替换skip用.txt`: スキップ用プレースホルダー
- `占位符(placeholders)_@5134@-@9728@_局部文字列替换结果捕捉用.txt`: 局所置換用プレースホルダー
- `占位符(placeholders)_$20987$-$499999$_全域替换用.txt`: 全域置換用プレースホルダー
- `占位符(placeholders)_$13246$-$19834$_二文字词根替换用.txt`: 2文字語根置換用プレースホルダー

プレースホルダー置換のアルゴリズム的優位性：

1. **文字列の衝突を避ける**: 通常の置換では、「rat」を「ネズミ」に置換し、その後「rat」を含む「rate」を「比率」に置換しようとすると、先に「rate」が「ネズミe」に変わってしまう問題が発生します。プレースホルダーを使うと、一旦「rat」を「#PH123#」のような一意の文字列に置き換え、最後にまとめて適切な結果に変換できます。

2. **保護と特別処理のメカニズム**: ユーザーが指定した範囲（%...%や@...@）を検出し、それを特別なプレースホルダーで一時的に置換します。これにより、メインの置換処理からそれらの部分を守ることができます。

```python
# %...%で囲まれた部分を検出してプレースホルダーに置換する処理の実装
def find_percent_enclosed_strings_for_skipping_replacement(text: str) -> List[str]:
    matches = []
    used_indices = set()
    for match in PERCENT_PATTERN.finditer(text):
        start, end = match.span()
        # 重複検出を避けるための処理
        if start not in used_indices and end-2 not in used_indices:
            matches.append(match.group(1))
            used_indices.update(range(start, end))
    return matches

def create_replacements_list_for_intact_parts(text: str, placeholders: List[str]) -> List[Tuple[str, str]]:
    matches = find_percent_enclosed_strings_for_skipping_replacement(text)
    replacements_list_for_intact_parts = []
    for i, match in enumerate(matches):
        if i < len(placeholders):
            replacements_list_for_intact_parts.append([f"%{match}%", placeholders[i]])
        else:
            break
    return replacements_list_for_intact_parts
```

### 7.3 大規模テキスト処理のアルゴリズム

大規模テキスト処理は、主に以下のアプローチで効率化されています：

1. **キャッシングの活用**: `@st.cache_data` デコレータを使用して大きなJSONファイルの読み込み結果をキャッシュします。

```python
@st.cache_data
def load_replacements_lists(json_path: str) -> Tuple[List, List, List]:
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # データの取り出し...
    return (
        replacements_final_list,
        replacements_list_for_localized_string,
        replacements_list_for_2char,
    )
```

2. **分割処理**: 大きなテキストは行単位で分割され、並列処理されます。これによりCPUコアを効率的に活用できます。

```python
def parallel_process(text: str, num_processes: int, ...):
    lines = re.findall(r'.*?\n|.+$', text)  # 行ごとに分割
    # ...分割処理の実装...
```

3. **最適化された置換順序**: 置換リストは文字数の多い順（長いマッチから先に処理）にソートされます。これにより、短い部分文字列が先に置換されて長い文字列のマッチングが壊れる問題を回避します。

```python
# 文字数順にソート（降順）
pre_replacements_list_2 = sorted(pre_replacements_list_1, key=lambda x: x[2], reverse=True)
```

## 8. データ構造と効率的な実装

### 8.1 主要データ構造

このアプリでは、様々なデータ構造が使われています。重要なものを分析します：

1. **置換リスト (Tuple[str, str, str])**

   置換リストは `(old, new, placeholder)` の3要素タプルのリストで、置換操作の核心部分です。
   ```python
   replacements_final_list: List[Tuple[str, str, str]] = []
   ```

   このデータ構造の利点：
   - タプルは不変（immutable）であり、データの整合性が保証される
   - 3要素の固定構造により、型安全性が向上する
   - リスト形式により、順序付けと繰り返し処理が容易

2. **多階層辞書 (Dictionary)**

   置換処理の中間段階では、辞書が頻繁に使用されます：
   ```python
   pre_replacements_dict_1 = {}  # {語根: [置換後文字列, 品詞]}
   pre_replacements_dict_2 = {}  # {置換対象: [置換後, 品詞, 優先度]}
   pre_replacements_dict_3 = {}  # {置換対象: [置換後, 優先度]}
   ```

   辞書を使う利点：
   - キーによる高速アクセス（O(1)の時間複雑性）
   - 中間データの蓄積と更新が容易
   - キーの一意性により重複防止

3. **文字幅辞書**

   文字の幅情報を保持するために特殊な辞書が使用されています：
   ```python
   with open("./Appの运行に使用する各类文件/Unicode_BMP全范围文字幅(宽)_Arial16.json", "r", encoding="utf-8") as fp:
       char_widths_dict = json.load(fp)
   ```

   この辞書は各Unicode文字の表示幅をピクセル単位で格納し、テキストの総幅計算やルビの改行位置決定に使用されます。

### 8.2 メモリ効率とパフォーマンス最適化

アプリにはいくつかの効率化戦略が組み込まれています：

1. **条件付き並列処理**

   並列処理はオーバーヘッドを伴うため、短いテキストでは単一プロセスを選択します：
   ```python
   if num_lines <= 1:
       # 行数が1以下なら並列化しても意味ないのでシングルで
       return orchestrate_comprehensive_esperanto_text_replacement(...)
   ```

2. **遅延計算とキャッシング**

   JSONファイルの読み込みは、Streamlitのキャッシング機能を使って最適化されています：
   ```python
   @st.cache_data
   def load_replacements_lists(json_path: str) -> Tuple[List, List, List]:
       # 実装...
   ```

3. **重複計算の回避**

   ルビと親文字が同一の場合、ルビタグを省略する最適化：
   ```python
   def remove_redundant_ruby_if_identical(text: str) -> str:
       def replacer(match: re.Match) -> str:
           group1 = match.group(1)  # 親文字
           group2 = match.group(2)  # ルビ文字
           if group1 == group2:
               return group1  # 同一ならルビタグなしで返す
           else:
               return match.group(0)  # 違うなら元のままで返す
       # 実装...
   ```

4. **早期終了パターン**

   不要な処理をスキップするための早期終了パターンが随所に使われています：
   ```python
   if not uploaded_file:
       st.warning("JSONファイルがアップロードされていません。処理を停止します。")
       st.stop()  # 早期終了
   ```

## 9. 拡張性とモジュール設計

### 9.1 モジュール分割と責任分離

アプリケーションは責任分離の原則に沿って4つの主要ファイルに分割されています：

1. **main.py**: ユーザーインターフェースと主要フロー制御
2. **エスペラント文(漢字)置換用のJSONファイル生成ページ.py**: JSONファイル生成機能
3. **esp_text_replacement_module.py**: テキスト置換のコア機能
4. **esp_replacement_json_make_module.py**: JSON生成のユーティリティ

この分割は以下の利点をもたらします：

- **関心の分離**: 各モジュールが特定の責任領域に集中できる
- **再利用性**: 共通機能が適切にモジュール化され、複数の場所から呼び出せる
- **テスト容易性**: 各モジュールを独立してテストしやすい
- **保守性**: 1つの機能を変更する際に影響範囲が限定される

### 9.2 インターフェース設計

モジュール間のインターフェースは明確に定義されています。例えば、`esp_text_replacement_module.py`から主要関数をインポートする部分：

```python
from esp_text_replacement_module import (
    x_to_circumflex,
    x_to_hat,
    hat_to_circumflex,
    circumflex_to_hat,
    replace_esperanto_chars,
    import_placeholders,
    orchestrate_comprehensive_esperanto_text_replacement,
    parallel_process,
    apply_ruby_html_header_and_footer
)
```

このような明示的なインポートは：
- 依存関係が明確になる
- 使用する機能だけをインポートできる
- 名前空間の汚染を防げる

### 9.3 拡張ポイント

アプリケーションには、新機能を追加しやすい拡張ポイントがいくつか用意されています：

1. **新しい出力形式の追加**

   `output_format` 関数に新しい条件分岐を追加するだけで、新しい出力形式をサポートできます：

   ```python
   def output_format(main_text, ruby_content, format_type, char_widths_dict):
       # 既存の形式...
       elif format_type == '新しい形式名':
           return f'新しい形式に変換した結果'
   ```

2. **カスタム置換ルールの適用**

   JSONファイル生成時にカスタムルールを組み込む仕組みが用意されています：

   ```python
   for i in custom_stemming_setting_list:
       if len(i)==3:
           # カスタムルールの処理...
   ```

3. **文字変換マッピングの拡張**

   新しい文字変換方式を追加する場合、辞書を追加するだけで対応可能です：

   ```python
   new_mapping = {'a': 'α', 'b': 'β', ...}  # 新しいマッピング

   def replace_with_new_mapping(text):
       return replace_esperanto_chars(text, new_mapping)
   ```

## 10. エラー処理と堅牢性

### 10.1 デフェンシブプログラミング手法

アプリケーション全体を通して、様々なデフェンシブプログラミング手法が適用されています：

1. **例外処理**

   JSONファイルのロードなど、失敗する可能性のある操作には適切な例外処理が施されています：

   ```python
   try:
       # デフォルトJSONをロード
       (replacements_final_list,
        replacements_list_for_localized_string,
        replacements_list_for_2char) = load_replacements_lists(default_json_path)
       st.success("デフォルトJSONの読み込みに成功しました。")
   except Exception as e:
       st.error(f"JSONファイルの読み込みに失敗: {e}")
       st.stop()
   ```

2. **早期入力検証**

   ユーザー入力は早い段階で検証され、問題があれば処理が中止されます：

   ```python
   if uploaded_file is None:
       st.warning("ファイルがアップロードされていません。")
       st.stop()
   ```

3. **フォールバック値**

   予期しない状況に備えて、フォールバック値が設定されています：

   ```python
   char_width = char_widths_dict.get(ch, 8)  # 文字幅情報がない場合は8px幅と仮定
   ```

4. **境界条件のチェック**

   リストのインデックス範囲チェックなど、境界条件が適切に処理されています：

   ```python
   for i, match in enumerate(matches):
       if i < len(placeholders):  # プレースホルダーの数を超えないようにチェック
           replacements_list_for_intact_parts.append([f"%{match}%", placeholders[i]])
       else:
           break  # プレースホルダーが足りなければ処理中止
   ```

### 10.2 ユーザーフィードバック

エラーや状態の変化はユーザーに明確に伝えられます：

```python
st.success("アップロードしたJSONの読み込みに成功しました。")
st.error(f"アップロードJSONファイルの読み込みに失敗: {e}")
st.warning("JSONファイルがアップロードされていません。処理を停止します。")
st.info("ファイルを読み込みました。")
```

これらのフィードバックは：
- 操作の結果を明確に示す
- 問題が発生したときのトラブルシューティングを支援する
- アプリケーションの状態を透明に保つ

### 10.3 型アノテーションの活用

コードベース全体を通して、型アノテーションが積極的に使用されています：

```python
def load_replacements_lists(json_path: str) -> Tuple[List, List, List]:
    # 実装...

def safe_replace(text: str, replacements: List[Tuple[str, str, str]]) -> str:
    # 実装...

replacements_final_list: List[Tuple[str, str, str]] = []
```

型アノテーションの利点：
- コードの自己文書化
- IDEによる補完と型チェックのサポート
- 意図しない型の使用による潜在的なバグの防止


## 11. HTML/CSSの技術的詳細とルビ表示の仕組み

このアプリケーションの重要な特徴の一つは、洗練されたHTMLルビ表示システムです。この仕組みを技術的に深く掘り下げていきましょう。

### 11.1 ルビ表示のHTML/CSS実装

アプリケーションは、標準のHTML5 `<ruby>` 要素を拡張して、より柔軟で視覚的に優れたルビ表示を実現しています。

#### 基本的なルビ構造

最もシンプルな形式では、標準的なHTML5のruby要素を使用しています：

```html
<ruby>親文字<rt>ルビ文字</rt></ruby>
```

しかし、実際のアプリケーションではより高度な形式を採用しています：

```html
<ruby>親文字<rt class="M_M">ルビ文字</rt></ruby>
```

このクラス属性が、ルビのサイズ調整の鍵となります。

#### CSSによるルビサイズ調整

`apply_ruby_html_header_and_footer` 関数は、出力形式が `HTML格式_Ruby文字_大小调整` または `HTML格式_Ruby文字_大小调整_汉字替换` の場合、以下のようなCSSスタイルシートを適用します：

```css
:root {
  --ruby-color: blue;
  --ruby-font-size: 0.5em;
}

html {
  font-size: 100%; /* 多くのブラウザは16px相当が標準 */
}

.text-M_M {
  font-size: 1rem!important;
  font-family: Arial, sans-serif;
  line-height: 2.0 !important;
  display: block;
  position: relative;
}

/* ルビのフレックスレイアウト */
ruby {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  vertical-align: top !important;
  line-height: 2.0 !important;
  margin: 0 !important;
  padding: 0 !important;
  font-size: 1rem !important;
}

/* ルビ文字のベーススタイル */
rt {
  display: block !important;
  font-size: var(--ruby-font-size);
  color: var(--ruby-color);
  line-height: 1.05;
  text-align: center;
}
```

#### ルビサイズクラスのカスケード

テキストの実際の比率に応じて、異なるサイズクラスが適用されます：

```css
rt.XXXS_S {
  --ruby-font-size: 0.3em;
  margin-top: -8.3em !important;
  transform: translateY(-0em) !important;
}    

rt.XXS_S {
  --ruby-font-size: 0.3em;
  margin-top: -7.2em !important;
  transform: translateY(-0em) !important;
}

/* 他のサイズクラス */
```

これらのサイズは、親テキストとルビテキストの比率に基づいて動的に選択されます：

```python
width_ruby = measure_text_width_Arial16(ruby_content, char_widths_dict)
width_main = measure_text_width_Arial16(main_text, char_widths_dict)
ratio_1 = width_ruby / width_main

if ratio_1 > 6:
    return f'<ruby>{main_text}<rt class="XXXS_S">{insert_br_at_third_width(ruby_content, char_widths_dict)}</rt></ruby>'
elif ratio_1 > (9/3):
    return f'<ruby>{main_text}<rt class="XXS_S">{insert_br_at_half_width(ruby_content, char_widths_dict)}</rt></ruby>'
# 以下、比率に応じた他のクラス...
```

### 11.2 文字幅計測と改行挿入アルゴリズム

ルビの適切な表示のため、テキストの幅を測定し、必要に応じて改行を挿入するアルゴリズムが実装されています。

#### 文字幅の測定

文字幅は、事前に作成されたJSONファイルから読み込まれた辞書を使って計算されます：

```python
def measure_text_width_Arial16(text, char_widths_dict: Dict[str, int]) -> int:
    total_width = 0
    for ch in text:
        char_width = char_widths_dict.get(ch, 8)  # 文字幅情報がない場合は8pxと仮定
        total_width += char_width
    return total_width
```

このJSONファイル（`Unicode_BMP全范围文字幅(宽)_Arial16.json`）には、Arial 16ptフォントでの各Unicode文字の幅（ピクセル単位）が格納されています。これにより、様々な言語や特殊文字を含むテキストでも正確な幅測定が可能になります。

#### 最適な改行位置の決定

ルビテキストが長い場合、視認性を向上させるために適切な位置で改行します。アプリケーションには2つの改行挿入アルゴリズムが実装されています：

1. **半分の幅で改行する**:
```python
def insert_br_at_half_width(text, char_widths_dict: Dict[str, int]) -> str:
    total_width = measure_text_width_Arial16(text, char_widths_dict)
    half_width = total_width / 2
    current_width = 0
    insert_index = None

    for i, ch in enumerate(text):
        char_width = char_widths_dict.get(ch, 8)
        current_width += char_width
        if current_width >= half_width:
            insert_index = i + 1
            break

    if insert_index is not None:
        result = text[:insert_index] + "<br>" + text[insert_index:]
    else:
        result = text
    return result
```

2. **三等分して2箇所に改行を挿入する**:
```python
def insert_br_at_third_width(text, char_widths_dict: Dict[str, int]) -> str:
    total_width = measure_text_width_Arial16(text, char_widths_dict)
    third_width = total_width / 3
    thresholds = [third_width, third_width*2]
    current_width = 0
    insert_indices = []
    found_first = False

    for i, ch in enumerate(text):
        char_width = char_widths_dict.get(ch, 8)
        current_width += char_width
        if not found_first and current_width >= thresholds[0]:
            insert_indices.append(i+1)
            found_first = True
        elif found_first and current_width >= thresholds[1]:
            insert_indices.append(i+1)
            break

    result = text
    for idx in reversed(insert_indices):
        result = result[:idx] + "<br>" + result[idx:]
    return result
```

これらのアルゴリズムの重要な点は：
- 文字の累積幅に基づいて改行位置を決定する
- 文字境界でのみ改行し、文字の途中で切らない
- 理想的な位置（半分や1/3の地点）に最も近い文字境界で改行する

### 11.3 ブラウザ互換性と表示最適化

アプリケーションはWebブラウザ環境での適切な表示を確保するために、いくつかの最適化を施しています：

```css
html, body {
  -webkit-text-size-adjust: 100%;
  -moz-text-size-adjust: 100%;
  -ms-text-size-adjust: 100%;
  text-size-adjust: 100%;
}
```

これらのプロパティは、モバイルブラウザが自動的にテキストサイズを調整するのを防ぎ、ルビレイアウトの一貫性を確保します。

さらに、HTMLソースコード内のインラインコメントには、レイアウトの意図や重要なスタイル設定の理由が記載されています：

```css
/* ルビの高さ位置はここで調節する。 */
margin-top: -8.3em !important;

/* text-M_Mのline-heightとrubyのline-heightは一致させる必要がある。 */
line-height: 2.0 !important;

/* ルビを改行するケースにおけるルビの行間 */
line-height: 1.05;
```

また、重複ルビ削除の最適化も実装されています（バージョン202502で追加）：

```python
def remove_redundant_ruby_if_identical(text: str) -> str:
    """
    <ruby>xxx<rt class="XXL_L">xxx</rt></ruby> のように、
    親文字列とルビ文字列が完全に同一の場合に <ruby> を取り除く
    """
    # 実装詳細...
```

この最適化は、親文字とルビが同一の場合に不要なルビマークアップを省略し、HTMLの簡潔さとレンダリングパフォーマンスを向上させます。

## 12. エスペラント語の語形変化と置換アルゴリズムの関係

エスペラント語は規則的な語形変化を持つ言語ですが、それでも語根分解と置換のプロセスには複雑さがあります。このセクションでは、アプリケーションがどのようにエスペラント語の特徴を処理しているかを探ります。

### 12.1 エスペラント語の形態的特徴

エスペラント語は、その規則性で知られる人工言語ですが、置換システムを設計する上で考慮すべき重要な形態的特徴があります：

1. **品詞を示す語尾**:
   - 名詞は `-o` で終わる (`libro` - 本)
   - 形容詞は `-a` で終わる (`bela` - 美しい)
   - 副詞は `-e` で終わる (`rapide` - 速く)
   - 動詞の不定形は `-i` で終わる (`paroli` - 話す)

2. **動詞の時制語尾**:
   - 現在形: `-as` (`mi parolas` - 私は話す)
   - 過去形: `-is` (`mi parolis` - 私は話した)
   - 未来形: `-os` (`mi parolos` - 私は話すだろう)
   - 条件法: `-us` (`mi parolus` - 私は話すかもしれない)
   - 命令法: `-u` (`parolu!` - 話せ！)

3. **接頭辞と接尾辞**:
   - `mal-` (反対): `bona` (良い) → `malbona` (悪い)
   - `-in` (女性): `patro` (父) → `patrino` (母)
   - `-ej` (場所): `lerni` (学ぶ) → `lernejo` (学校)
   - など多数

### 12.2 語根分解アプローチ

アプリケーションは、エスペラント語の複合語を構成要素に分解するために、以下のアプローチを採用しています：

#### 事前定義された語根リスト

アプリケーションは約11,137個のエスペラント語根を含むリストを使用します：

```python
with open("./Appの运行に使用する各类文件/世界语全部词根_约11137个_202501.txt", 'r', encoding='utf-8') as file:
    E_roots = file.readlines()
    for E_root in E_roots:
        E_root = E_root.strip()
        if not E_root.isdigit():  # 混入していた数字の'10'と'7'を削除
            temporary_replacements_dict[E_root]=[E_root,len(E_root)]
```

#### 品詞情報の維持

PEJVOデータベースから抽出された品詞情報が維持され、適切な派生形の生成に使用されます：

```python
with open("./Appの运行に使用する各类文件/PEJVO(世界语全部单词列表)'全部'について、词尾(a,i,u,e,o,n等)をcutし、comma(,)で隔てて词性と併せて记录した列表(E_stem_with_Part_Of_Speech_list).json", "r", encoding="utf-8") as g:
    E_stem_with_Part_Of_Speech_list = json.load(g)
```

#### 特殊な接辞の処理

`-an` (会員)、`-on` (分数) などの接尾辞は特別な処理が必要です：

```python
AN=[['dietan', '/diet/an/', '/diet/an'], ['afrikan', '/afrik/an/', '/afrik/an'], ...]
ON=[['duon', '/du/on/', '/du/on'], ['okon', '/ok/on/', '/ok/on'], ...]

# ANパターンの処理例
for an in AN:
    if an[1].endswith("/an/"):
        i2=an[1]
        i3 = re.sub(r"/an/$", "", i2)
        i4=i3+"/an/o"
        i5=i3+"/an/a"
        i6=i3+"/an/e"
        i7=i3+"/a/n/"
        # 各派生形に対する処理...
```

#### 2文字語根の特別処理

エスペラント語には、単独でも接頭辞・接尾辞としても使われる2文字の語根があります：

```python
suffix_2char_roots=['ad', 'ag', 'am', 'ar', 'as', ...]
prefix_2char_roots=['al', 'am', 'av', 'bo', 'di', ...]
standalone_2char_roots=['al', 'ci', 'da', 'de', 'di', ...]

# 各カテゴリに対する専用の置換リストを作成
replacements_list_for_suffix_2char_roots=[]
for i in range(len(suffix_2char_roots)):
    replaced_suffix = remove_redundant_ruby_if_identical(safe_replace(suffix_2char_roots[i],temporary_replacements_list_final))
    # 3つのパターン（通常・大文字・文頭大文字）を追加
    replacements_list_for_suffix_2char_roots.append(["$"+suffix_2char_roots[i],"$"+replaced_suffix,"$"+imported_placeholders_for_2char_replacement[i]])
    replacements_list_for_suffix_2char_roots.append(["$"+suffix_2char_roots[i].upper(),"$"+replaced_suffix.upper(),"$"+imported_placeholders_for_2char_replacement[i][:-1]+'up$'])
    replacements_list_for_suffix_2char_roots.append(["$"+suffix_2char_roots[i].capitalize(),"$"+capitalize_ruby_and_rt(replaced_suffix),"$"+imported_placeholders_for_2char_replacement[i][:-1]+'cap$'])
```

### 12.3 語形変化を考慮した置換生成

エスペラント語の語形変化に対応するため、アプリケーションは品詞ごとにさまざまな派生形を生成します：

#### 名詞派生形

名詞は `-o`（単数主格）、`-on`（単数対格）、`-oj`（複数主格）などの語尾を取ります：

```python
if "名词" in j[1]:
    for k in ["o","on",'oj']:
        if not i+k in pre_replacements_dict_2:
            pre_replacements_dict_3[i+k]=[j[0]+k,j[2]+len(k)*10000-3000]
        # ...
```

#### 形容詞派生形

形容詞は `-a`（単数）、`-aj`（複数）、`-an`（単数対格）などの語尾を取ります：

```python
if "形容词" in j[1]:
    for k in ["a","aj",'an']:
        if not i+k in pre_replacements_dict_2:
            pre_replacements_dict_3[i+k]=[j[0]+k,j[2]+len(k)*10000-3000]
        # ...
```

#### 動詞派生形

動詞は特に多様な語形変化を持ちます：

```python
if "动词" in j[1]:
    # verb_suffix_2l_2 には活用語尾(as, is, os, usなど)とその置換後の形が含まれている
    for k1,k2 in verb_suffix_2l_2.items():
        if not i+k1 in pre_replacements_dict_2:
            pre_replacements_dict_3[i+k1]=[j[0]+k2,j[2]+len(k1)*10000-3000]
        # ...

    # 命令法・不定法の処理
    for k in ["u ","i ","u","i"]:
        if not i+k in pre_replacements_dict_2:
            pre_replacements_dict_3[i+k]=[j[0]+k,j[2]+len(k)*10000-3000]
        # ...
```

### 12.4 置換優先順位の最適化

文字列置換の順序は結果に大きく影響します。アプリケーションは以下の戦略を使って優先順位を最適化しています：

1. **文字数による優先順位付け**:
   長い文字列から先に置換することで、短い部分文字列が先に置換されて意図しない結果になることを防ぎます。

   ```python
   # 基本優先順位 = 文字数 × 10000
   pre_replacements_list_2 = sorted(pre_replacements_list_1, key=lambda x: x[2], reverse=True)
   ```

2. **置換・非置換の区別**:
   置換しない単語（元の語根と置換後が同じ）は優先順位を下げて、実際に置換が必要な単語が先に処理されるようにします。

   ```python
   if i==j[0]:  # 置換しない単語
       pre_replacements_dict_2[i.replace('/', '')]=
           [j[0].replace("</rt></ruby>","%%%").replace('/', '').replace("%%%","</rt></ruby>"),
            j[1],
            len(i.replace('/', ''))*10000-3000]  # 優先順位を下げる
   else:
       pre_replacements_dict_2[i.replace('/', '')]=
           [j[0].replace("</rt></ruby>","%%%").replace('/', '').replace("%%%","</rt></ruby>"),
            j[1],
            len(i.replace('/', ''))*10000]
   ```

3. **語形変化形の順序調整**:
   派生形を追加する際、既存の単語との競合を避けるために優先順位を調整します。

   ```python
   # 既存でないものは優先順位を下げる
   pre_replacements_dict_3[i+k]=[j[0]+k,j[2]+len(k)*10000-5000]
   ```

4. **カスタム優先順位の設定**:
   ユーザー定義のJSONファイルで特定の単語の優先順位を明示的に設定できます。

   ```python
   if i[1]=="dflt":
       replacement_priority_by_length=len(esperanto_Word_before_replacement)*10000
   elif isinstance(i[1], int) or (isinstance(i[1], str) and i[1].isdigit()):
       replacement_priority_by_length = int(i[1])  # 明示的な優先順位
   ```

これらの戦略により、エスペラント語の複雑な語形変化に対応しながら、最適な置換結果を得ることができます。

## 13. スケーラビリティと将来の拡張可能性

このアプリケーションは、将来の拡張と大規模データ処理を考慮した設計になっています。

### 13.1 大規模テキスト処理の対応策

アプリケーションには、大量のテキストを効率的に処理するための仕組みがいくつか組み込まれています：

#### マルチプロセッシングによる並列処理

大規模テキストは行単位で分割され、複数のCPUコアを使って並列処理されます：

```python
def parallel_process(text: str, num_processes: int, ...):
    # 行に分割してチャンク化
    lines = re.findall(r'.*?\n|.+$', text)
    num_lines = len(lines)

    # 十分な行数がある場合のみ並列化
    if num_lines > 1:
        lines_per_process = max(num_lines // num_processes, 1)
        ranges = [(i * lines_per_process, (i + 1) * lines_per_process) for i in range(num_processes)]
        ranges[-1] = (ranges[-1][0], num_lines)

        # 並列実行
        with multiprocessing.Pool(processes=num_processes) as pool:
            results = pool.starmap(process_segment, [...])
        return ''.join(results)
    else:
        # 少ない行数の場合は単一プロセスで処理
        return orchestrate_comprehensive_esperanto_text_replacement(...)
```

#### JSONファイル生成の並列化

大量の語根に対する置換リスト生成も並列化されています：

```python
def parallel_build_pre_replacements_dict(
    E_stem_with_Part_Of_Speech_list,
    replacements,
    num_processes=4
):
    # データをチャンクに分割
    # 並列処理
    # 結果をマージ
    # ...
```

#### 巨大テキスト対応のUI

UIも大規模テキストに対応できるよう設計されています：

```python
# 巨大テキスト対策ロジック（行数ベースで一部省略表示）
MAX_PREVIEW_LINES = 250  # 250行まで表示
lines = processed_text.splitlines()
if len(lines) > MAX_PREVIEW_LINES:
    # 先頭247行 + "..." + 末尾3行のプレビュー
    first_part = lines[:247]
    last_part = lines[-3:]
    preview_text = "\n".join(first_part) + "\n...\n" + "\n".join(last_part)
    st.warning(f"テキストが長いため（総行数 {len(lines)} 行）、全文プレビューを一部省略しています。")
else:
    preview_text = processed_text
```

### 13.2 将来の拡張ポイント

アプリケーションは、将来の機能追加を容易にする拡張ポイントをいくつか持っています：

#### 新しい出力形式の追加

`output_format` 関数と `apply_ruby_html_header_and_footer` 関数を拡張することで、新しい出力形式を簡単に追加できます：

```python
def output_format(main_text, ruby_content, format_type, char_widths_dict):
    # 既存の形式...
    elif format_type == '新しい形式':
        # 新しい形式の実装
        return f'...新しい形式の出力...'
```

```python
def apply_ruby_html_header_and_footer(processed_text: str, format_type: str) -> str:
    if format_type == '新しい形式':
        # 新しい形式用のヘッダー/フッター
        return 新しいヘッダー + processed_text + 新しいフッター
    # 既存の形式...
```

#### カスタム置換ルールの拡張

JSONファイル生成ページは、カスタム置換ルールを拡張するためのフレームワークを提供しています：

```python
# 語根分解法の設定
custom_stemming_setting_list = [
    ["語根", "優先順位", ["接尾辞リスト"]],
    # 新しいカスタムルールを追加...
]

# 置換後文字列の設定
user_replacement_item_setting_list = [
    ["語根分解", "優先順位", ["接尾辞リスト"], "置換後文字列"],
    # 新しいカスタムルールを追加...
]
```

#### 新しい特殊マーカーの追加

%マーカー（スキップ）や@マーカー（局所置換）のように、新しい特殊マーカーを追加することも可能です：

```python
# 新しいマーカー用の正規表現パターン
NEW_MARKER_PATTERN = re.compile(r'#(.{1,30}?)#')

# 新しいマーカーを検出する関数
def find_new_marker_enclosed_strings(text: str) -> List[str]:
    matches = []
    used_indices = set()
    for match in NEW_MARKER_PATTERN.finditer(text):
        # マッチング処理...
    return matches

# 新しいマーカーの処理を orchestrate_comprehensive_esperanto_text_replacement に追加
```

#### 多言語サポートの拡張

現在はエスペラント語と日本語/漢字を中心にしていますが、他の言語のサポートを追加することも可能です：

```python
# 新しい言語の文字変換マッピング
new_lang_mapping = {'a': 'α', 'b': 'β', ...}

# 変換関数
def convert_to_new_lang(text: str) -> str:
    return replace_esperanto_chars(text, new_lang_mapping)
```

### 13.3 パフォーマンス最適化の余地

アプリケーションには、さらなるパフォーマンス最適化の余地がいくつかあります：

#### メモリ使用量の最適化

現在のアプリケーションは、置換リストを完全にメモリに読み込みます。大規模なデータセットでは、これがメモリ圧迫の原因になる可能性があります：

```python
# 代替案: データベースベースのアプローチ
# import sqlite3
# conn = sqlite3.connect(':memory:')  # インメモリDBを使用
# c = conn.cursor()
# c.execute('''CREATE TABLE replacements (old text, new text, placeholder text)''')
# # データの挿入...
# # クエリによる置換...
```

#### ストリーム処理

現在は全テキストを一度にメモリに読み込んでいますが、ストリーム処理に移行することで大規模ファイルのサポートを強化できます：

```python
# ストリーム処理のコンセプト
def process_file_stream(input_file, output_file, chunk_size=1024):
    while True:
        chunk = input_file.read(chunk_size)
        if not chunk:
            break
        processed_chunk = process_chunk(chunk)
        output_file.write(processed_chunk)
```

#### 置換アルゴリズムの最適化

現在の置換アルゴリズムは単純な文字列置換に基づいていますが、より高度なアルゴリズム（例：Aho-Corasick アルゴリズム）に移行することで、複数パターンのマッチングを効率化できます：

```python
# 例: pyahocorasick ライブラリを使用した最適化
# import ahocorasick
# automaton = ahocorasick.Automaton()
# for idx, (old, new, _) in enumerate(replacements_final_list):
#     automaton.add_word(old, (idx, new))
# automaton.make_automaton()
# # 高速一致検索...
```

## 14. 設計上の主要な決定事項とその背景

このアプリケーションの設計には、多くの重要な決定が含まれています。それぞれの決定の背景と理由を詳しく見ていきましょう。

### 14.1 Streamlitフレームワークの選択

アプリケーションはPythonのStreamlitフレームワークを使用して構築されています。この選択には以下の理由があります：

1. **迅速な開発**: Streamlitは最小限のコードでWebインターフェースを構築できます。
   ```python
   st.title("エスペラント文を漢字置換したり、HTML形式の訳ルビを振ったりする (拡張版)")
   st.write("---")
   ```

2. **Pythonエコシステムとの統合**: テキスト処理に適したPythonの豊富なライブラリ（re、pandas、multiprocessingなど）を直接活用できます。

3. **クラウドデプロイの容易さ**: Streamlit Cloud上での展開が容易で、サーバー設定などの複雑な作業が不要です。

4. **リアクティブな更新**: ユーザー入力に応じてUIが自動的に更新されるリアクティブなモデルを採用しています。

### 14.2 モジュール分割の哲学

アプリケーションは以下の原則に基づいて4つの主要ファイルに分割されています：

1. **単一責任の原則**: 各モジュールは明確に定義された単一の責任を持ちます。
   - `main.py`: UIとメインフロー制御
   - `エスペラント文(漢字)置換用のJSONファイル生成ページ.py`: 置換ルール生成
   - `esp_text_replacement_module.py`: テキスト置換アルゴリズム
   - `esp_replacement_json_make_module.py`: JSON生成ユーティリティ

2. **関心の分離**: UIロジック、ビジネスロジック、データ処理が明確に分離されています。

3. **再利用可能性**: 共通機能が再利用可能なモジュールにカプセル化されています。これにより、アプリケーションの異なる部分から同じ機能を呼び出すことができます。

### 14.3 プレースホルダーメカニズムの採用

文字列置換処理の核心となるプレースホルダーメカニズムの採用には、以下の理由があります：

1. **置換の順序依存性の解消**: 単純な置換では順序によって結果が変わる問題を解決します。

   ```
   例: "abc" → "XYZ", "ab" → "123" の順で置換すると
   "abc" → "XYZ" (正しい)

   しかし "ab" → "123", "abc" → "XYZ" の順で置換すると
   "abc" → "123c" → "123c" (誤り)
   ```

   プレースホルダーを使うと：
   ```
   "abc" → "#PH1#", "ab" → "#PH2#"
   その後、"#PH1#" → "XYZ", "#PH2#" → "123"
   ```
   これにより、置換順序に関係なく正しい結果を得られます。

2. **特殊処理の実現**: `%...%` (スキップ) や `@...@` (局所置換) などの特殊マーカーの処理が容易になります。

3. **デバッグの容易さ**: 中間状態でプレースホルダーが表示されるため、どの置換が適用されたかを追跡しやすくなります。

### 14.4 HTML/CSSアプローチ

ルビ表示のためのHTML/CSSアプローチについては、以下の考慮事項がありました：

1. **標準HTML5のruby要素の限界**: 標準の `<ruby>` 要素だけでは、日本語/漢字とエスペラント語の組み合わせを美しく表示するのに限界があります。

2. **フレキシブルレイアウト**: インラインフレックスボックスを使用することで、ルビと親テキストの位置関係を細かく制御できます。
   ```css
   ruby {
     display: inline-flex;
     flex-direction: column;
     align-items: center;
     vertical-align: top !important;
     /* ... */
   }
   ```

3. **動的なルビサイズ調整**: テキストの幅比率に基づいて異なるスタイルを適用することで、様々な長さの組み合わせに対応します。
   ```python
   if ratio_1 > 6:
       return f'<ruby>{main_text}<rt class="XXXS_S">{insert_br_at_third_width(ruby_content, char_widths_dict)}</rt></ruby>'
   elif ratio_1 > (9/3):
       # ...
   ```

4. **ブラウザ互換性**: 様々なブラウザで一貫した表示を確保するためのスタイル設定が含まれています。
   ```css
   html, body {
     -webkit-text-size-adjust: 100%;
     -moz-text-size-adjust: 100%;
     -ms-text-size-adjust: 100%;
     text-size-adjust: 100%;
   }
   ```

### 14.5 並列処理アプローチ

並列処理の実装には、いくつかの重要な設計上の決定がありました：

1. **行単位の分割**: テキストを行単位で分割することで、自然な並列処理単位を作り出しています。これにより、各行の処理結果を単純に連結するだけで最終結果を得ることができます。

2. **動的なプロセス数の設定**: ユーザーがUI上で並列処理の有無とプロセス数を制御できるようにしています。これにより、様々なハードウェア環境に適応できます。

3. **Spawnモードの使用**: Macプラットフォームなどでの問題を避けるため、明示的に 'spawn' 開始方法を設定しています。
   ```python
   try:
       multiprocessing.set_start_method("spawn")
   except RuntimeError:
       pass  # すでに設定済みの場合は無視
   ```

4. **適応的なチャンクサイズ**: 総行数に基づいて動的にチャンクサイズを計算します。これにより、様々な大きさのテキストに効率的に対応できます。
   ```python
   lines_per_process = max(num_lines // num_processes, 1)
   ```

### 14.6 エラー処理と堅牢性の設計

アプリケーションには、様々な予期しない状況に対処するための戦略が組み込まれています：

1. **早期検証と明確なフィードバック**: ユーザー入力や環境条件を早期に検証し、問題があればクリアなメッセージで伝えます。
   ```python
   if not uploaded_file:
       st.warning("ファイルがアップロードされていません。処理を停止します。")
       st.stop()
   ```

2. **段階的な処理とチェックポイント**: 複雑な処理は段階的に実行され、各段階でチェックポイントが設けられています。

3. **グレースフルデグラデーション**: 理想的な条件が満たされない場合でも、可能な限り機能を提供します。例えば、並列処理がサポートされていない環境では自動的に単一プロセス処理に切り替わります。

4. **明示的な型アノテーション**: コード全体を通して型アノテーションを使用することで、型関連のエラーを減らし、コードの意図を明確にしています。
   ```python
   def safe_replace(text: str, replacements: List[Tuple[str, str, str]]) -> str:
       # 実装...
   ```

この次のセクションでは、開発者向けのカスタマイズガイドを詳しく解説します。これにより、アプリケーションを拡張したり、特定のニーズに合わせて調整したりするための具体的な方法を提供します。


# エスペラント文字変換・ルビ振りツール 技術解説書（続き）

## 15. 開発者向けカスタマイズガイド

このセクションでは、アプリケーションを拡張したり、特定のニーズに合わせてカスタマイズしたりするための具体的な方法を説明します。

### 15.1 新しい置換ルールの追加

置換ルールを拡張する最も一般的な方法は、CSVファイルを編集することです。以下にその手順を説明します。

#### CSVファイルフォーマットの詳細

CSVファイルは以下の形式に従う必要があります：

```csv
エスペラント語根,日本語訳/漢字
esper,希望する
lingv,言語
ir,行く
...
```

CSVファイルを編集する際の注意点：

1. **一貫した文字形式**: エスペラント語根は字上符形式（ĉ, ĝなど）に統一することを推奨します。アプリケーションは他の形式（cx, gx や c^, g^）も字上符形式に変換しますが、CSVファイル内での一貫性を保つことが重要です。

2. **コメント行**: 行頭に `#` を付けることでコメント行を挿入できます。
   ```csv
   # 以下は基本的な語根
   viv,生きる
   ```

3. **空の行の取り扱い**: 空の行は無視されます。

#### カスタム語根分解ルールの追加

より高度なカスタマイズには、JSON形式の語根分解ルールファイルを編集します：

```json
[
  ["説明行：語根, 優先順位, [接尾辞リスト]"],
  ["am", "dflt", ["verbo_s1"]],
  ["esper", "40000", ["verbo_s1", "o", "a"]],
  ["lingv", "dflt", ["o", "a", "e"]]
]
```

各エントリの意味：

1. **第1要素（語根）**: カスタマイズするエスペラント語根
2. **第2要素（優先順位）**:
   - `"dflt"`: デフォルト優先順位（文字数×10000）
   - 数値: 明示的な優先順位値（高いほど先に処理）
   - `"-1"`: 置換対象から除外
3. **第3要素（接尾辞リスト）**:
   - `"verbo_s1"`: 動詞活用語尾（as, is, os, usなど）を追加
   - `"verbo_s2"`: 命令法・不定法語尾（u, i）を追加
   - `"o"`, `"a"`, `"e"`: 名詞・形容詞・副詞の語尾
   - `"ne"`: 語根単体も置換対象にする

カスタム語根分解ルールを実装するコード例：

```python
# 特定の語根に対する特別な分解ルール
for i in custom_stemming_setting_list:
    if len(i)==3:
        esperanto_Word_before_replacement = i[0].replace('/', '')
        if i[1]=="dflt":
            replacement_priority_by_length=len(esperanto_Word_before_replacement)*10000
        # ... 他の条件分岐 ...

        # 各接尾辞に対する処理
        if "verbo_s1" in i[2]:
            for k1,k2 in verb_suffix_2l_2.items():
                pre_replacements_dict_3[esperanto_Word_before_replacement + k1]=
                    [Replaced_String+k2, replacement_priority_by_length+len(k1)*10000]
            i[2].remove("verbo_s1")
        # ... 他の接尾辞の処理 ...
```

#### カスタム置換出力の追加

特定の語根に対して、独自の置換結果を指定したい場合は、2つ目のJSONファイルを編集します：

```json
[
  ["説明行：語根分解, 優先順位, [接尾辞リスト], 置換後文字列"],
  ["viv/o", "dflt", ["ne"], "生命/命"],
  ["san/a", "60000", ["ne"], "健康/康"]
]
```

各エントリの意味：

1. **第1要素**: 語根分解（スラッシュで区切られた形式）
2. **第2要素**: 優先順位（語根分解ルールと同様）
3. **第3要素**: 接尾辞リスト（語根分解ルールと同様）
4. **第4要素**: 独自の置換後文字列（スラッシュで区切られた形式）

この仕組みを使うと、CSVで定義された基本マッピングを上書きして、特定の単語に対して独自の置換結果を指定できます。

### 15.2 新しい出力形式の実装

アプリケーションに新しい出力形式を追加する方法を説明します。

#### 出力形式の基本構造

出力形式は `output_format` 関数で定義されています：

```python
def output_format(main_text, ruby_content, format_type, char_widths_dict):
    if format_type == 'HTML格式_Ruby文字_大小调整':
        # ルビサイズ調整ロジック...
    elif format_type == 'HTML格式_Ruby文字_大小调整_汉字替换':
        # 漢字置換ロジック...
    elif format_type == 'HTML格式':
        return f'<ruby>{main_text}<rt>{ruby_content}</rt></ruby>'
    # ... 他の形式 ...
```

新しい形式を追加するプロセス：

1. **JSONファイル生成ページのUIに選択肢を追加**:

```python
options = {
    'HTML形式＿ルビ文字のサイズ調整': 'HTML格式_Ruby文字_大小调整',
    # ... 既存の選択肢 ...
    '新しい形式の名前': '新しい形式の内部識別子',
}
```

2. **`output_format` 関数に条件分岐を追加**:

```python
def output_format(main_text, ruby_content, format_type, char_widths_dict):
    # ... 既存の条件分岐 ...
    elif format_type == '新しい形式の内部識別子':
        # 新しい形式の実装
        return f'...新しい形式の出力パターン...'
```

3. **必要に応じて `apply_ruby_html_header_and_footer` 関数も更新**:

```python
def apply_ruby_html_header_and_footer(processed_text: str, format_type: str) -> str:
    # ... 既存の条件分岐 ...
    elif format_type == '新しい形式の内部識別子':
        ruby_style_head = "...新しい形式用のヘッダー..."
        ruby_style_tail = "...新しい形式用のフッター..."
    # ...
```

#### 例：マークダウン形式の追加

マークダウン形式の出力を追加する例を示します：

1. **選択肢の追加**:

```python
options = {
    # ... 既存の選択肢 ...
    'マークダウン形式': 'Markdown_Format',
}
```

2. **出力関数の実装**:

```python
def output_format(main_text, ruby_content, format_type, char_widths_dict):
    # ... 既存の条件分岐 ...
    elif format_type == 'Markdown_Format':
        return f'{main_text} *({ruby_content})*'
```

3. **ヘッダー/フッターの設定**:

```python
def apply_ruby_html_header_and_footer(processed_text: str, format_type: str) -> str:
    # ... 既存の条件分岐 ...
    elif format_type == 'Markdown_Format':
        ruby_style_head = ""  # マークダウンでは特別なヘッダーは不要
        ruby_style_tail = ""
    # ...
```

### 15.3 特殊マーカーシステムの拡張

現在のアプリケーションでは `%...%`（置換スキップ）と `@...@`（局所置換）の2種類の特殊マーカーをサポートしています。新しい特殊マーカーを追加する方法を説明します。

#### 新しいマーカーの実装手順

例として、`#...#` マーカー（特定のフォーマットでハイライト表示）を実装する手順を示します：

1. **プレースホルダーファイルの準備**:
   新しいマーカー用のプレースホルダーテキストファイルを作成します：
   ```
   占位符(placeholders)_#1234#-#5678#_ハイライト表示用.txt
   ```
   このファイルには、一意のプレースホルダー文字列（`#1234#`など）を行ごとに記載します。

2. **マーカー検出用の正規表現を定義**:
   ```python
   # '#' で囲まれた箇所をハイライトするための正規表現
   HIGHLIGHT_PATTERN = re.compile(r'#(.{1,40}?)#')
   ```

3. **マーカー検出関数の実装**:
   ```python
   def find_highlight_enclosed_strings(text: str) -> List[str]:
       """'#foo#' の形を全て抽出。40文字以内に限定。"""
       matches = []
       used_indices = set()
       for match in HIGHLIGHT_PATTERN.finditer(text):
           start, end = match.span()
           if start not in used_indices and end-2 not in used_indices:
               matches.append(match.group(1))
               used_indices.update(range(start, end))
       return matches
   ```

4. **置換リスト生成関数の実装**:
   ```python
   def create_replacements_list_for_highlight(text: str, placeholders: List[str]) -> List[List[str]]:
       """
       '#xxx#' で囲まれた箇所を検出し、
       プレースホルダーとハイライト表示用のHTMLタグのマッピングを作成
       """
       matches = find_highlight_enclosed_strings(text)
       tmp_list = []
       for i, match in enumerate(matches):
           if i < len(placeholders):
               highlighted_match = f'<span class="highlight">{match}</span>'
               tmp_list.append([f"#{match}#", placeholders[i], highlighted_match])
           else:
               break
       return tmp_list
   ```

5. **メイン処理関数に新しいマーカー処理を追加**:
   ```python
   def orchestrate_comprehensive_esperanto_text_replacement(
       text,
       # ... 既存のパラメータ ...
       placeholders_for_highlight: List[str],
       # ... その他のパラメータ ...
   ) -> str:
       # 1) 空白の正規化 → 2) エスペラント文字の字上符形式統一
       text = unify_halfwidth_spaces(text)
       text = convert_to_circumflex(text)

       # 3) %で囲まれた部分をスキップ (既存の処理)
       # ...

       # 新しいマーカー処理: #で囲まれた部分をハイライト用プレースホルダーに置換
       tmp_replacements_list_for_highlight = create_replacements_list_for_highlight(
           text, placeholders_for_highlight
       )
       sorted_replacements_list_for_highlight = sorted(
           tmp_replacements_list_for_highlight, key=lambda x: len(x[0]), reverse=True
       )
       for original, place_holder_, highlighted_original in sorted_replacements_list_for_highlight:
           text = text.replace(original, place_holder_)

       # 既存の処理を続行...

       # プレースホルダー復元時にハイライト用プレースホルダーも復元
       for original, place_holder_, highlighted_original in sorted_replacements_list_for_highlight:
           text = text.replace(place_holder_, highlighted_original.replace("#",""))

       # ... 既存の処理の続き ...

       return text
   ```

6. **メイン関数に新しいパラメータを追加**:
   ```python
   # main.py の並列処理関数にパラメータを追加
   def parallel_process(
       text: str,
       num_processes: int,
       # ... 既存のパラメータ ...
       placeholders_for_highlight: List[str],
       # ... その他のパラメータ ...
   ) -> str:
       # ... 既存の実装 ...
   ```

7. **メインUI部分でプレースホルダーファイルの読み込みを追加**:
   ```python
   # main.py に追加
   placeholders_for_highlight: List[str] = import_placeholders(
       './Appの运行に使用する各类文件/占位符(placeholders)_#1234#-#5678#_ハイライト表示用.txt'
   )
   ```

8. **処理呼び出し部分に新しいパラメータを追加**:
   ```python
   # 送信ボタンクリック時の処理に追加
   if submit_btn:
       # ... 既存の処理 ...
       if use_parallel:
           processed_text = parallel_process(
               text=text0,
               num_processes=num_processes,
               # ... 既存のパラメータ ...
               placeholders_for_highlight=placeholders_for_highlight,
               # ... その他のパラメータ ...
           )
       else:
           processed_text = orchestrate_comprehensive_esperanto_text_replacement(
               text=text0,
               # ... 既存のパラメータ ...
               placeholders_for_highlight=placeholders_for_highlight,
               # ... その他のパラメータ ...
           )
       # ... 既存の処理の続き ...
   ```

9. **必要に応じてCSSスタイルを追加**:
   ```python
   # HTMLヘッダー内に追加
   ruby_style_head = """
   ... 既存のスタイル ...

   /* ハイライト表示用スタイル */
   .highlight {
     background-color: yellow;
     font-weight: bold;
   }
   """
   ```

これにより、テキスト内の `#キーワード#` のような部分が黄色背景でハイライト表示されるようになります。

### 15.4 パフォーマンス最適化テクニック

アプリケーションのパフォーマンスをさらに向上させるためのテクニックを紹介します。

#### キャッシュ戦略の拡張

Streamlitの `@st.cache_data` デコレータを使って、他の重い計算もキャッシュできます：

```python
@st.cache_data
def preprocess_text(text: str) -> str:
    """テキストの前処理（空白の正規化、エスペラント文字の統一など）をキャッシュ"""
    text = unify_halfwidth_spaces(text)
    text = convert_to_circumflex(text)
    return text
```

これにより、同じテキストが再入力された場合に前処理を繰り返す必要がなくなります。

#### 部分更新の最適化

テキストの一部だけが変更された場合、変更された部分だけを再処理するロジックを実装できます：

```python
def incremental_update(old_text: str, new_text: str, old_processed: str) -> str:
    """テキストの変更部分だけを特定し、その部分だけを再処理"""
    if old_text == new_text:
        return old_processed  # 変更なし

    # diff アルゴリズムを使って変更箇所を特定
    # 変更部分だけを処理
    # 結果をマージ
    # ...
```

#### メモリ使用量の最適化

大規模テキスト処理におけるメモリ使用量を最適化する方法：

```python
def process_large_text(text: str, chunk_size: int = 10000) -> str:
    """大きなテキストをチャンクに分割して処理し、メモリ消費を抑える"""
    result = []
    # テキストをチャンクに分割（ただし、文や段落の境界を尊重）
    chunks = split_text_into_chunks(text, chunk_size)

    for i, chunk in enumerate(chunks):
        # 進捗状況を表示
        progress = (i + 1) / len(chunks)
        st.progress(progress)

        # チャンク単位で処理
        processed_chunk = orchestrate_comprehensive_esperanto_text_replacement(chunk, ...)
        result.append(processed_chunk)

    # 結果を結合
    return ''.join(result)
```

#### 正規表現の最適化

正規表現パターンをコンパイルして再利用することで、パフォーマンスを向上させることができます：

```python
# 一度コンパイルして再利用
PERCENT_PATTERN = re.compile(r'%(.{1,50}?)%')
AT_PATTERN = re.compile(r'@(.{1,18}?)@')

def find_percent_enclosed_strings_for_skipping_replacement(text: str) -> List[str]:
    """事前コンパイルしたパターンを使用"""
    matches = []
    # ... 以下同様 ...
```

## 16. データフローと処理シーケンスの詳細分析

このセクションでは、アプリケーションのデータフローとテキスト処理のシーケンスを詳細に分析します。

### 16.1 メインアプリケーションのデータフロー

メインアプリケーション（main.py）のデータフローを詳細に分析します。

1. **初期化とファイルロード段階**:
   ```
   アプリケーション起動
   ↓
   multiprocessing.set_start_method("spawn") の設定
   ↓
   needed_functions from esp_text_replacement_module のインポート
   ↓
   JSONファイルのロード (load_replacements_lists)
    ├→ replacements_final_list
    ├→ replacements_list_for_localized_string
    └→ replacements_list_for_2char
   ↓
   プレースホルダーファイルのインポート (import_placeholders)
    ├→ placeholders_for_skipping_replacements
    └→ placeholders_for_localized_replacement
   ```

2. **ユーザー入力とパラメータ設定段階**:
   ```
   UIコンポーネントの表示
   ↓
   ユーザーによる入力
    ├→ JSONファイル選択（デフォルト or アップロード）
    ├→ 並列処理設定（使用有無、プロセス数）
    ├→ 出力形式選択
    ├→ 入力テキスト（手動入力 or ファイルアップロード）
    └→ 出力文字形式選択（上付き文字/x形式/^形式）
   ↓
   セッションステートへのテキスト保存
     st.session_state["text0_value"] = text0
   ```

3. **テキスト処理段階**:
   ```
   処理方法の選択
    ├→ 並列処理使用の場合: parallel_process
    └→ 単一プロセスの場合: orchestrate_comprehensive_esperanto_text_replacement
   ↓
   文字形式変換の適用
    ├→ 上付き文字の場合: replace_esperanto_chars(x_to_circumflex) + replace_esperanto_chars(hat_to_circumflex)
    ├→ x形式の場合: (デフォルトのまま)
    └→ ^形式の場合: replace_esperanto_chars(x_to_hat) + replace_esperanto_chars(circumflex_to_hat)
   ↓
   HTMLヘッダー/フッターの適用
     processed_text = apply_ruby_html_header_and_footer(processed_text, format_type)
   ↓
   表示用テキストの準備
    ├→ 巨大テキストの場合: 一部を省略表示
    └→ 通常サイズの場合: そのまま表示
   ```

4. **結果表示と出力段階**:
   ```
   フォーマット別の表示
    ├→ HTML形式の場合: HTMLプレビュータブ + HTMLソースコードタブ
    └→ その他の形式: テキストタブ
   ↓
   ダウンロードボタンの提供
     st.download_button("置換結果のダウンロード", ...)
   ```

### 16.2 JSONファイル生成プロセスの詳細分析

JSONファイル生成ページの処理プロセスを詳細に分析します。

1. **初期データの読み込み段階**:
   ```
   CSVファイルの読み込み (エスペラント語根-日本語訳対応表)
   ↓
   字上符形式への変換 (convert_to_circumflex)
   ↓
   語根分解法JSONファイルの読み込み (custom_stemming_setting_list)
   ↓
   置換後文字列JSONファイルの読み込み (user_replacement_item_setting_list)
   ```

2. **エスペラント語根の処理段階**:
   ```
   全語根リストの読み込み
     E_roots = file.readlines()
   ↓
   置換辞書の初期構築
     temporary_replacements_dict[E_root]=[E_root,len(E_root)]
   ↓
   CSVデータによる置換内容の更新
     temporary_replacements_dict[E_root] = [output_format(...),len(E_root)]
   ↓
   辞書からリストへの変換
     temporary_replacements_list_1.append((old,new[0],new[1]))
   ↓
   文字数によるソート
     temporary_replacements_list_2 = sorted(..., key=lambda x: x[2], reverse=True)
   ↓
   プレースホルダーの追加
     temporary_replacements_list_final.append([...])
   ```

3. **語根分解と置換リスト生成段階**:
   ```
   E_stem_with_Part_Of_Speech_list の処理
     ├→ 並列処理の場合: parallel_build_pre_replacements_dict
     └→ 単一プロセスの場合: 通常のループ処理
   ↓
   pre_replacements_dict_1 から pre_replacements_dict_2 への変換
     ├→ "/"の除去
     ├→ 置換優先順位の設定
     └→ HTML特殊文字の処理
   ↓
   pre_replacements_dict_2 から pre_replacements_dict_3 への変換
     ├→ 品詞による派生形生成（名詞、形容詞、動詞ごとに異なる処理）
     ├→ 特殊接辞（-an, -on）の処理
     └→ 2文字語根の特殊処理
   ↓
   カスタム設定の適用
     ├→ 語根分解法の適用
     └→ 置換後文字列の適用
   ↓
   リストへの変換とソート
     pre_replacements_list_2 = sorted(..., key=lambda x: x[2], reverse=True)
   ```

4. **最終リスト生成と大文字・小文字対応段階**:
   ```
   temporary_replacements_list_final から各種置換リストを生成
     ├→ replacements_final_list（基本的な置換リスト）
     ├→ replacements_list_for_2char（2文字語根用）
     └→ replacements_list_for_localized_string（局所置換用）
   ↓
   大文字・小文字・文頭大文字の3パターン生成
     ├→ original form: (old, new, placeholder)
     ├→ uppercase form: (old.upper(), new.upper(), placeholder[:-1]+'up$')
     └→ capitalized form: (old.capitalize(), capitalize_ruby_and_rt(new), placeholder[:-1]+'cap$')
   ↓
   結果の組み合わせとJSONの生成
     combined_data = {"全域替换用のリスト...": ..., "二文字词根替换用のリスト...": ..., "局部文字替换用のリスト...": ...}
   ```

### 16.3 コア置換アルゴリズムの詳細シーケンス

`orchestrate_comprehensive_esperanto_text_replacement` 関数の詳細な処理シーケンスを分析します。

1. **テキスト前処理**:
   ```
   空白の正規化 (unify_halfwidth_spaces)
   ↓
   エスペラント文字の字上符形式統一 (convert_to_circumflex)
   ```

2. **特殊マーカー処理**:
   ```
   %で囲まれた部分の検出 (find_percent_enclosed_strings_for_skipping_replacement)
   ↓
   %で囲まれた部分→プレースホルダーの置換リスト作成 (create_replacements_list_for_intact_parts)
   ↓
   %で囲まれた部分をプレースホルダーに置換
   ↓
   @で囲まれた部分の検出 (find_at_enclosed_strings_for_localized_replacement)
   ↓
   @で囲まれた部分を局所置換してプレースホルダーに置換 (create_replacements_list_for_localized_replacement)
   ```

3. **大域置換処理**:
   ```
   大域置換リストによる文字列→プレースホルダー置換
     for old, new, placeholder in replacements_final_list:
         if old in text:
             text = text.replace(old, placeholder)
             valid_replacements[placeholder] = new
   ↓
   2文字語根置換（1回目）
     for old, new, placeholder in replacements_list_for_2char:
         if old in text:
             text = text.replace(old, placeholder)
             valid_replacements_for_2char_roots[placeholder] = new
   ↓
   2文字語根置換（2回目）
     for old, new, placeholder in replacements_list_for_2char:
         if old in text:
             place_holder_second = "!" + placeholder + "!"
             text = text.replace(old, place_holder_second)
             valid_replacements_for_2char_roots_2[place_holder_second] = new
   ```

4. **プレースホルダー復元と後処理**:
   ```
   2回目の2文字語根プレースホルダー復元
     for place_holder_second, new in reversed(valid_replacements_for_2char_roots_2.items()):
         text = text.replace(place_holder_second, new)
   ↓
   1回目の2文字語根プレースホルダー復元
     for placeholder, new in reversed(valid_replacements_for_2char_roots.items()):
         text = text.replace(placeholder, new)
   ↓
   大域置換プレースホルダー復元
     for placeholder, new in valid_replacements.items():
         text = text.replace(placeholder, new)
   ↓
   局所置換(@)プレースホルダー復元
     for original, place_holder_, replaced_original in sorted_replacements_list_for_localized_string:
         text = text.replace(place_holder_, replaced_original.replace("@",""))
   ↓
   スキップ(%)プレースホルダー復元
     for original, place_holder_ in sorted_replacements_list_for_intact_parts:
         text = text.replace(place_holder_, original.replace("%",""))
   ↓
   HTML形式の後処理
     if "HTML" in format_type:
         text = text.replace("\n", "<br>\n")
         text = re.sub(r"   ", "&nbsp;&nbsp;&nbsp;", text)
         text = re.sub(r"  ", "&nbsp;&nbsp;", text)
   ```

この詳細なシーケンス分析により、テキスト処理の各ステップが明確になります。特に注目すべき点は、プレースホルダーの処理が複数段階で行われること、そして復元の順序が重要であることです。最後のプレースホルダーから最初のプレースホルダーへと逆順に復元することで、入れ子になった置換処理が正しく機能するようになっています。

## 17. 技術的課題と解決策

アプリケーションの開発過程で直面した主要な技術的課題と、それに対する解決策を分析します。

### 17.1 置換の順序依存性の問題

**課題**:  
単純な文字列置換では、置換の順序によって結果が変わる問題があります。例えば、「lingvistiko」という単語を処理する場合、「lingv」と「istiko」に分解したいとします。しかし、「ist」という部分も置換対象であれば、置換順序によって異なる結果が生じる可能性があります。

**解決策**:  
プレースホルダーメカニズムを導入することで、この問題を解決しています：

```python
def safe_replace(text: str, replacements: List[Tuple[str, str, str]]) -> str:
    valid_replacements = {}
    # まず元のテキスト→プレースホルダー
    for old, new, placeholder in replacements:
        if old in text:
            text = text.replace(old, placeholder)
            valid_replacements[placeholder] = new
    # 次にプレースホルダー→置換後テキスト
    for placeholder, new in valid_replacements.items():
        text = text.replace(placeholder, new)
    return text
```

このアプローチにより、置換操作は2段階に分けられ、元のテキストの各部分は一意のプレースホルダーに変換された後で最終的な置換結果に変換されます。これにより、置換の競合が防止されます。

### 17.2 エスペラント語の形態的複雑さへの対応

**課題**:  
エスペラント語は規則的ですが、語形変化や複合語の形成によって多様な形態を持ちます。例えば、「paroli」（話す）という動詞から「mi parolas」（私は話す）、「vi parolis」（あなたは話した）など、様々な形が派生します。これらすべての形態を事前に列挙するのは非効率です。

**解決策**:  
品詞情報を活用して、動的に派生形を生成するアプローチを採用しています：

```python
if "动词" in j[1]:  # 動詞の場合
    for k1,k2 in verb_suffix_2l_2.items():  # 様々な時制語尾に対して
        if not i+k1 in pre_replacements_dict_2:
            pre_replacements_dict_3[i+k1]=[j[0]+k2,j[2]+len(k1)*10000-3000]
        # ...
```

このアプローチにより、語根「parol」に対して、「parolas」「parolis」「parolos」などの形態が自動的に生成されます。これによって、辞書サイズを大幅に削減しながら、広範な語形変化をカバーすることができます。

### 17.3 HTMLルビの視覚的最適化

**課題**:  
標準のHTML5 `<ruby>` 要素では、親テキストに対してルビテキストが長い場合、視覚的に不均衡になり、読みにくくなる問題があります。

**解決策**:  
文字幅に基づいて動的にルビのサイズを調整し、必要に応じて改行を挿入するカスタムCSSアプローチを採用しています：

```python
width_ruby = measure_text_width_Arial16(ruby_content, char_widths_dict)
width_main = measure_text_width_Arial16(main_text, char_widths_dict)
ratio_1 = width_ruby / width_main

if ratio_1 > 6:  # ルビが親テキストの6倍以上の幅がある場合
    # サイズを最小にし、3分割で改行
    return f'<ruby>{main_text}<rt class="XXXS_S">{insert_br_at_third_width(ruby_content, char_widths_dict)}</rt></ruby>'
elif ratio_1 > (9/3):  # ルビが親テキストの3倍以上の幅がある場合
    # サイズを小さくし、半分で改行
    return f'<ruby>{main_text}<rt class="XXS_S">{insert_br_at_half_width(ruby_content, char_widths_dict)}</rt></ruby>'
# ... 他の比率に対する処理 ...
```

このアプローチにより、ルビテキストの長さに関わらず、視覚的にバランスの取れた表示が可能になります。さらに、CSSの独自クラスを使用することで、様々なブラウザでの一貫した表示を確保しています。

### 17.4 大規模テキスト処理のパフォーマンス問題

**課題**:  
大量のテキストを処理する場合、単純な逐次処理では時間がかかりすぎる問題があります。

**解決策**:  
並列処理と分割処理を組み合わせたアプローチを採用しています：

```python
def parallel_process(text: str, num_processes: int, ...):
    # テキストを行単位で分割
    lines = re.findall(r'.*?\n|.+$', text)
    num_lines = len(lines)

    # 十分な行数がある場合のみ並列化
    if num_lines > 1:
        # チャンク分割
        lines_per_process = max(num_lines // num_processes, 1)
        ranges = [(i * lines_per_process, (i + 1) * lines_per_process) for i in range(num_processes)]
        ranges[-1] = (ranges[-1][0], num_lines)

        # 並列実行
        with multiprocessing.Pool(processes=num_processes) as pool:
            results = pool.starmap(process_segment, [...])
        return ''.join(results)
    else:
        # 少ない行数の場合は単一プロセスで処理
        return orchestrate_comprehensive_esperanto_text_replacement(...)
```

このアプローチには以下の利点があります：

1. **CPU利用の最大化**: 複数のCPUコアを活用して並列処理を行う
2. **メモリ効率**: 行単位の分割により、各プロセスのメモリ使用量を抑制する
3. **自動的なフォールバック**: 小さなテキストでは並列化のオーバーヘッドを避ける

さらに、ユーザーが並列処理の使用有無とプロセス数を制御できるようにすることで、様々なハードウェア環境に適応できるようになっています。

### 17.5 大文字・小文字・文頭大文字の対応

**課題**:  
エスペラント文では、大文字、小文字、文頭大文字など、様々な形式が現れます。これらすべてに対応する必要がありますが、すべての組み合わせを事前に用意するのは非効率です。

**解決策**:  
3つの基本パターン（通常、大文字、文頭大文字）を動的に生成するアプローチを採用しています：

```python
for old, new, place_holder in pre_replacements_list_3:
    # 通常形（小文字）
    pre_replacements_list_4.append((old, new, place_holder))

    # 大文字形
    pre_replacements_list_4.append((
        old.upper(),
        new.upper(),
        place_holder[:-1]+'up$'
    ))

    # 文頭大文字形
    if old[0]==' ':  # 語頭が空白の場合
        pre_replacements_list_4.append((
            old[0] + old[1:].capitalize(),
            new[0] + capitalize_ruby_and_rt(new[1:]),
            place_holder[:-1]+'cap$'
        ))
    else:
        pre_replacements_list_4.append((
            old.capitalize(),
            capitalize_ruby_and_rt(new),
            place_holder[:-1]+'cap$'
        ))
```

HTMLルビの場合、単純な `capitalize()` だけでは不十分なため、専用の関数を実装しています：

```python
def capitalize_ruby_and_rt(text: str) -> str:
    """
    <ruby>〜</ruby> の親文字列 / ルビ文字列を大文字化する
    """
    def replacer(match):
        # ... ルビの親文字とルビ文字の両方を大文字化する処理 ...

    replaced_text = RUBY_PATTERN.sub(replacer, text)
    if replaced_text == text:
        replaced_text = text.capitalize()
    return replaced_text
```

このアプローチにより、様々な大文字・小文字パターンに効率的に対応できます。

これらの解決策は、アプリケーションの堅牢性と柔軟性を大幅に向上させています。特に興味深いのは、単純で直感的なアプローチ（プレースホルダー置換、並列処理など）を採用しながらも、複雑な問題に効果的に対処していることです。

## 18. 比較分析と設計上の選択肢

このセクションでは、アプリケーションの設計上の選択肢と、採用された解決策の比較分析を行います。

### 18.1 テキスト処理のアーキテクチャ選択

エスペラント文を処理するにあたり、いくつかのアーキテクチャ選択肢がありました：

1. **採用された解決策: 多段階プレースホルダー置換**
   ```python
   # 各種プレースホルダーを順番に適用し、最後に復元
   text = apply_special_markers(text)
   text = apply_global_replacements(text)
   text = apply_local_replacements(text)
   text = restore_placeholders(text)
   ```

2. **代替案1: 構文解析に基づくアプローチ**
   ```python
   # 言語構造を解析してから変換
   tokens = tokenize_esperanto(text)
   parsed = parse_grammar(tokens)
   processed = transform_parsed_structure(parsed)
   text = serialize_to_text(processed)
   ```

3. **代替案2: 正規表現ベースの単一パス処理**
   ```python
   # すべての置換を一度に行う
   for pattern, replacement in compiled_patterns:
       text = pattern.sub(replacement, text)
   ```

**比較分析**:

| アプローチ | 長所 | 短所 |
|------------|------|------|
| 多段階プレースホルダー置換 | ・単純で理解しやすい<br>・特殊マーカー対応が容易<br>・置換順序の影響を避けられる | ・複数回のテキスト走査が必要<br>・メモリ使用量が比較的多い |
| 構文解析ベース | ・言語学的に正確<br>・文法的一貫性を維持できる | ・実装が複雑<br>・エスペラントパーサーの開発が必要<br>・特殊マーカー対応が難しい |
| 正規表現ベース | ・効率的な単一パス処理<br>・メモリ使用量が少ない | ・置換の順序依存性<br>・複雑なパターンの管理が難しい<br>・特殊マーカー処理が複雑化 |

採用された多段階プレースホルダー置換アプローチは、実装の複雑さと柔軟性のバランスが優れています。構文解析アプローチは理論的には優れていますが、実装の複雑さとコスト（特に特殊マーカー処理）が大きな障壁となります。正規表現ベースのアプローチは効率的ですが、置換の順序依存性が深刻な問題となり、複雑なテキストでは予測不能な結果が生じる可能性があります。

### 18.2 並列処理の実装選択肢

並列処理において、以下の選択肢が検討されました：

1. **採用された解決策: multiprocessing による行単位分割**
   ```python
   # 行単位でテキストを分割し、複数プロセスで処理
   with multiprocessing.Pool(processes=num_processes) as pool:
       results = pool.starmap(process_segment, [...])
   ```

2. **代替案1: threading による並列処理**
   ```python
   # スレッドプールを使用
   with ThreadPoolExecutor(max_workers=num_threads) as executor:
       futures = [executor.submit(process_chunk, chunk) for chunk in chunks]
       results = [future.result() for future in futures]
   ```

3. **代替案2: asyncio による非同期処理**
   ```python
   # 非同期I/Oを活用
   async def process_all():
       tasks = [asyncio.create_task(process_chunk_async(chunk)) for chunk in chunks]
       results = await asyncio.gather(*tasks)
   ```

**比較分析**:

| アプローチ | 長所 | 短所 |
|------------|------|------|
| multiprocessing | ・真の並列処理（複数CPU活用）<br>・プロセス間のメモリ分離<br>・CPUバウンドな処理に最適 | ・プロセス起動オーバーヘッド<br>・データのシリアライズコスト<br>・Streamlitとの互換性に注意が必要 |
| threading | ・軽量なスレッド<br>・共有メモリによる効率的なデータアクセス<br>・I/Oバウンドな処理に適している | ・GILによる並列処理の制限（Python）<br>・スレッド安全性の確保が必要<br>・デバッグが難しい |
| asyncio | ・イベントループによる効率的なI/O処理<br>・単一スレッドでの並行処理<br>・スケーラビリティが高い | ・CPUバウンドな処理には不向き<br>・関数がすべて非同期対応する必要がある<br>・Streamlitとの統合が複雑 |

採用された multiprocessing アプローチは、このアプリケーションの特性（CPUバウンドなテキスト処理が中心）に最も適しています。Python の GIL（Global Interpreter Lock）の制約により、threading では真の並列処理が得られません。asyncio は I/O バウンドなアプリケーションに適していますが、このアプリケーションのテキスト処理のような CPU 集約的なタスクでは効果が限られます。

### 18.3 ユーザーインターフェース技術の選択

ユーザーインターフェースには以下の選択肢が考えられました：

1. **採用された解決策: Streamlit**
   ```python
   import streamlit as st
   st.title("エスペラント文を漢字置換したり、HTML形式の訳ルビを振ったりする")
   st.write("---")
   text0 = st.text_area("エスペラントの文章を入力してください", height=150)
   ```

2. **代替案1: Flask + HTML/CSS/JavaScript**
   ```python
   from flask import Flask, render_template, request
   @app.route('/', methods=['GET', 'POST'])
   def index():
       if request.method == 'POST':
           # 処理ロジック
       return render_template('index.html')
   ```

3. **代替案2: デスクトップアプリケーション（PyQt/Tkinter）**
   ```python
   import tkinter as tk
   from tkinter import ttk
   root = tk.Tk()
   root.title("エスペラント文字変換ツール")
   # UIコンポーネント定義
   ```

**比較分析**:

| アプローチ | 長所 | 短所 |
|------------|------|------|
| Streamlit | ・迅速な開発<br>・Pythonのみでのフルスタック開発<br>・デプロイが容易（Streamlit Cloud） | ・カスタマイズ性に制限がある<br>・特定のUI設計に適応する必要がある<br>・パフォーマンスがやや劣る |
| Flask + HTML/CSS/JS | ・高度なカスタマイズが可能<br>・フルスタックWebアプリの柔軟性<br>・多様なライブラリやフレームワークの利用 | ・開発期間が長い<br>・フロントエンドの専門知識が必要<br>・デプロイや保守が複雑 |
| デスクトップアプリ | ・ネイティブパフォーマンス<br>・オフライン操作が可能<br>・ローカルシステムリソースへのアクセス | ・クロスプラットフォーム対応が複雑<br>・配布やアップデートが難しい<br>・開発に特殊なスキルが必要 |

Streamlit の選択は、迅速な開発と簡単なデプロイを重視したものです。特にPythonのデータ処理機能とシームレスに統合できる点、および最小限のコードでインタラクティブなWebアプリケーションを構築できる点が大きな利点です。カスタマイズ性には一定の制限がありますが、このアプリケーションの要件（テキスト入力、処理オプション、結果表示）には十分対応できています。

### 18.4 ルビ表示アプローチの選択

ルビ表示のためのアプローチには以下の選択肢がありました：

1. **採用された解決策: カスタムCSS付きHTML5 Rubyタグ**
   ```html
   <ruby>親文字<rt class="M_M">ルビ文字</rt></ruby>
   ```
   ```css
   ruby {
     display: inline-flex;
     flex-direction: column;
     /* その他のスタイル */
   }
   ```

2. **代替案1: 標準HTML5 Rubyタグのみ**
   ```html
   <ruby>親文字<rt>ルビ文字</rt></ruby>
   ```

3. **代替案2: CSSのみによる擬似ルビ**
   ```html
   <span class="ruby-container">
     <span class="ruby-base">親文字</span>
     <span class="ruby-text">ルビ文字</span>
   </span>
   ```
   ```css
   .ruby-container { position: relative; }
   .ruby-text { position: absolute; top: -1em; font-size: 0.5em; }
   ```

**比較分析**:

| アプローチ | 長所 | 短所 |
|------------|------|------|
| カスタムCSS付きHTML5 Ruby | ・標準的なHTML5要素を使用<br>・CSSでの視覚的最適化<br>・ブラウザのアクセシビリティサポート | ・複雑なCSSが必要<br>・ブラウザ間の互換性への配慮が必要 |
| 標準HTML5 Rubyのみ | ・シンプルで標準的<br>・将来的な互換性<br>・実装が容易 | ・視覚的な制御が限定的<br>・長いルビに対応できない<br>・表示の一貫性に欠ける |
| CSSのみによる擬似ルビ | ・高度な視覚的カスタマイズ<br>・古いブラウザでも動作可能<br>・完全な配置制御 | ・非標準的な実装<br>・アクセシビリティ問題<br>・メンテナンス負荷が高い |

カスタムCSS付きHTML5 Rubyタグのアプローチは、標準性とカスタマイズ性のバランスが優れています。標準のHTML5要素を基盤としながら、CSSによる視覚的な拡張を行うことで、様々な長さのルビに対応できます。特に、ルビと親テキストの幅比率に基づいて動的にスタイルを適用する仕組みは、このアプリケーションの特徴的な機能です。

### 18.5 データストレージアプローチの選択

置換ルールのストレージには以下の選択肢がありました：

1. **採用された解決策: JSONファイル**
   ```python
   with open(json_path, 'r', encoding='utf-8') as f:
       data = json.load(f)
   ```

2. **代替案1: リレーショナルデータベース**
   ```python
   import sqlite3
   conn = sqlite3.connect('esperanto_replacements.db')
   cursor = conn.cursor()
   cursor.execute("SELECT old, new, placeholder FROM replacements")
   ```

3. **代替案2: インメモリデータ構造**
   ```python
   # コード内に直接定義
   REPLACEMENTS = [
       ("lingv", "言語", "%PH1234%"),
       # ... 他の置換ルール
   ]
   ```

**比較分析**:

| アプローチ | 長所 | 短所 |
|------------|------|------|
| JSONファイル | ・人間可読で編集しやすい<br>・外部ツールでの編集が容易<br>・バージョン管理しやすい | ・大規模データでパフォーマンスが低下<br>・一括読み込みによるメモリ消費<br>・同時書き込みに非対応 |
| リレーショナルDB | ・大規模データに効率的<br>・インデックスによる高速検索<br>・トランザクション処理 | ・セットアップが複雑<br>・移植性に制約<br>・編集のためのUI/ツールが必要 |
| インメモリ構造 | ・最高のパフォーマンス<br>・依存関係がない<br>・コードと一体化した設計 | ・大規模データでコードが煩雑<br>・外部編集が不可能<br>・拡張性と保守性に課題 |

JSONファイルの選択は、人間可読性と編集のしやすさを重視したものです。ユーザーが独自の置換ルールを作成したり編集したりする可能性を考慮すると、JSONは良いバランスを提供します。また、Streamlitのキャッシング機能（`@st.cache_data`）を使用することで、JSONの読み込みパフォーマンスの問題も部分的に緩和されています。

これらの比較分析から、アプリケーションの設計上の決定は、実装の容易さ、拡張性、ユーザーフレンドリーさのバランスを重視したものであることがわかります。特に注目すべきは、多くの場合、理論的に「最良」なアプローチではなく、実用的な妥協点が選択されていることです。これは、実際のソフトウェア開発においては一般的な方針であり、このアプリケーションもその例外ではありません。

## 19. 将来の拡張可能性と開発ロードマップ

このアプリケーションには、さらなる拡張と改善の余地があります。このセクションでは、今後の開発方向性について検討します。

### 19.1 言語サポートの拡張

現在のアプリケーションはエスペラント語と日本語/漢字に焦点を当てていますが、他の言語へのサポートを拡張することが可能です。

**実装アプローチ**:

1. **多言語置換ルールの導入**:
   ```python
   # 言語ごとに置換ルールを分離
   replacements_by_language = {
       "japanese": [...],
       "chinese": [...],
       "korean": [...],
       # 他の言語
   }
   ```

2. **言語検出機能**:
   ```python
   def detect_language(text):
       # 特徴パターンに基づいて言語を推定
       if re.search(r'[ĉĝĥĵŝŭĈĜĤĴŜŬ]', text):
           return "esperanto"
       elif re.search(r'[あ-んア-ン漢-龥]', text):
           return "japanese"
       # 他の言語の検出
       return "unknown"
   ```

3. **多言語UI**:
   ```python
   # UIの言語選択
   ui_language = st.selectbox(
       "UI言語 / UI Language / Interfaca Lingvo:",
       ["日本語", "English", "Esperanto", "中文"]
   )

   # 選択に基づいてUIテキストを表示
   ui_texts = {
       "日本語": {"title": "エスペラント文字変換ツール", ...},
       "English": {"title": "Esperanto Text Conversion Tool", ...},
       # 他の言語
   }

   st.title(ui_texts[ui_language]["title"])
   ```

### 19.2 高度な語形解析

現在のアプローチは文字列置換に基づいていますが、より高度な語形解析を導入することでさらに精度を向上させることができます。

**実装アプローチ**:

1. **形態素解析器の実装**:
   ```python
   class EsperantoMorphologicalAnalyzer:
       def __init__(self, roots_dict, affixes_dict):
           self.roots = roots_dict
           self.affixes = affixes_dict

       def analyze(self, word):
           # 語形解析のロジック
           # 最も可能性の高い分解を返す
           # 例: "parolas" → [("parol", "root"), ("as", "present_tense")]
   ```

2. **文脈を考慮した解析**:
   ```python
   def analyze_with_context(text):
       tokens = tokenize(text)
       for i, token in enumerate(tokens):
           # 周囲の単語に基づいて品詞を推定
           prev_token = tokens[i-1] if i > 0 else None
           next_token = tokens[i+1] if i < len(tokens)-1 else None
           token.pos = estimate_pos(token.word, prev_token, next_token)
   ```

3. **統計的手法の導入**:
   ```python
   # 頻度辞書に基づく解析
   with open('word_frequency.json', 'r') as f:
       frequency_dict = json.load(f)

   def score_decomposition(decomposition):
       # 分解の各部分の頻度スコアに基づいて評価
       return sum(frequency_dict.get(part, 0) for part in decomposition)
   ```

### 19.3 インタラクティブ翻訳インターフェース

ルビ表示を超えて、インタラクティブな翻訳機能を追加することが考えられます。

**実装アプローチ**:

1. **クリック可能な単語**:
   ```javascript
   // HTML出力に適用するJavaScript
   document.querySelectorAll('ruby').forEach(ruby => {
     ruby.addEventListener('click', function() {
       // クリックされた単語の詳細情報を表示
       showWordDetails(this.textContent, this.querySelector('rt').textContent);
     });
   });
   ```

2. **単語詳細表示モーダル**:
   ```python
   # Streamlit コンポーネント
   if st.button("単語詳細を表示"):
       with st.expander("単語の詳細情報"):
           st.write(f"語根: {root}")
           st.write(f"品詞: {pos}")
           st.write(f"語形変化: {morphology}")
           st.write(f"例文: {example_sentences}")
   ```

3. **辞書統合**:
   ```python
   # 外部APIと連携する例
   import requests

   def fetch_dictionary_entry(word):
       response = requests.get(f"https://api.esperanto-dictionary.example/lookup?word={word}")
       if response.status_code == 200:
           return response.json()
       return None
   ```

### 19.4 バックエンド最適化

大規模データセットと高負荷処理に対応するための最適化が考えられます。

**実装アプローチ**:

1. **データベースバックエンド**:
   ```python
   # SQLiteの例
   import sqlite3

   def setup_db():
       conn = sqlite3.connect('esperanto_replacements.db')
       c = conn.cursor()
       c.execute('''
       CREATE TABLE IF NOT EXISTS replacements (
           old TEXT PRIMARY KEY,
           new TEXT,
           placeholder TEXT
       )
       ''')
       conn.commit()
       return conn

   def query_replacements(conn, text):
       # 効率的なクエリで置換ルールを検索
       c = conn.cursor()
       # ...
   ```

2. **キャッシュ層の改善**:
   ```python
   # LRUキャッシュの導入
   from functools import lru_cache

   @lru_cache(maxsize=1024)
   def process_text_segment(segment):
       # セグメント単位でのキャッシュ
       # ...
   ```

3. **非同期バックグラウンド処理**:
   ```python
   # Celeryタスクキューの例
   from celery import Celery

   app = Celery('esperanto_processor', broker='redis://localhost:6379/0')

   @app.task
   def process_large_text(text_id):
       # バックグラウンドで大規模テキストを処理
       # 完了時に通知
       # ...
   ```

### 19.5 コミュニティとコラボレーション機能

ユーザー間の共有とコラボレーションを促進する機能が考えられます。

**実装アプローチ**:

1. **置換ルールの共有**:
   ```python
   # ルールセットの公開と共有
   if st.button("コミュニティと共有"):
       # アップロード処理
       share_id = upload_to_repository(custom_replacements_list)
       st.success(f"共有ID: {share_id} でコミュニティと共有されました。")

   # 共有ルールセットのインポート
   share_id = st.text_input("共有IDを入力")
   if st.button("インポート") and share_id:
       imported_rules = download_from_repository(share_id)
       if imported_rules:
           st.success("ルールセットをインポートしました。")
   ```

2. **コミュニティ辞書への貢献**:
   ```python
   # 単語定義の提案
   with st.form("新しい単語定義を提案"):
       word = st.text_input("エスペラント単語")
       definition = st.text_area("定義")
       if st.form_submit_button("提案"):
           submit_dictionary_proposal(word, definition)
           st.success("提案が送信されました。レビュー後に辞書に追加されます。")
   ```

3. **版管理とマージ**:
   ```python
   # 置換ルールの版管理
   revision_id = st.selectbox(
       "バージョンを選択",
       get_available_revisions()
   )

   if st.button("変更を確認"):
       diff = compare_revisions(current_revision, revision_id)
       st.code(diff)

   if st.button("マージ"):
       merged_rules = merge_revisions(current_revision, revision_id)
       if conflicts:
           st.warning("競合が検出されました。解決してください。")
           # 競合解決UI
       else:
           st.success("変更がマージされました。")
   ```

これらの拡張可能性は、このアプリケーションが単なる置換ツールから、エスペラント学習・翻訳プラットフォームへと進化する可能性を示しています。特に興味深いのは、言語学的知識と技術的実装を組み合わせることで、より高度な言語処理機能を追加できる点です。

開発のプライオリティとしては、まず使いやすさとパフォーマンスの向上に集中し、その後より高度な言語処理機能を段階的に導入することが推奨されます。また、ユーザーフィードバックを積極的に取り入れ、実際のニーズに基づいた機能拡張を行うことが重要です。
