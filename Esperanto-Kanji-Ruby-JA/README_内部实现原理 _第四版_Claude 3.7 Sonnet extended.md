# エスペラント文 漢字置換・ルビ注釈ツール 技術解説書

## 1. アプリケーション概要

このアプリケーションは、エスペラント語のテキストを処理し、漢字への置換やルビ注釈の付与を行うStreamlitベースのウェブアプリケーションです。中核となる機能は、エスペラント語の単語や文法要素を体系的に認識し、それらを日本語訳や漢字表現に変換することです。

このアプリケーションは以下の主要コンポーネントから構成されています：

1. `main.py` - メインアプリケーション（ユーザー入力処理と文字列置換）
2. `エスペラント文(漢字)置換用のJSONファイル生成ページ.py` - 置換ルールJSONファイルの生成
3. `esp_text_replacement_module.py` - テキスト置換の中核機能
4. `esp_replacement_json_make_module.py` - 置換ルールJSON作成用機能

## 2. 技術アーキテクチャ

### 2.1 全体アーキテクチャ

```
[ユーザー] <-> [Streamlit UI] <-> [テキスト処理エンジン] <-> [置換ルールDB(JSON)]
```

このアプリケーションは、Streamlitをフロントエンド兼バックエンドとして使用し、テキスト処理エンジンを介してユーザー入力を処理します。処理ルールは外部JSONファイルとして保存・ロードされ、カスタマイズが可能です。

### 2.2 主要コンポーネントの関係

```
main.py  -------imports------>  esp_text_replacement_module.py
  ^                                     ^
  |                                     |
  |                                     |
  v                                     v
JSONファイル生成ページ.py --imports--> esp_replacement_json_make_module.py
```

両方のPythonファイルが共通のモジュールからテキスト処理関数をインポートし、連携して動作します。

## 3. コンポーネント詳細分析

### 3.1 main.py - メインアプリケーション

`main.py`は、ユーザーインターフェイスと置換処理の中心的な役割を担います。

#### 3.1.1 主要機能

- Streamlit UIの構築と管理
- JSONファイルからの置換ルールのロードとキャッシュ
- テキスト入力の処理（手動入力またはファイルアップロード）
- マルチプロセス並列処理のオプション提供
- プレースホルダー（占位符）の管理
- HTML/非HTMLフォーマットの出力生成

#### 3.1.2 コードフロー

1. ページ設定とUIコンポーネントの初期化
2. JSONファイルのロード（デフォルトまたはアップロード）
3. プレースホルダーのインポート
4. 高度な設定（並列処理）の設定
5. 出力形式の選択
6. テキスト入力ソースの選択
7. フォーム内でのテキスト処理
8. 置換処理の実行（並列または単一プロセス）
9. 結果の表示とダウンロードオプションの提供

#### 3.1.3 重要な関数

- `load_replacements_lists()` - JSONファイルから3種類の置換リストをロード
- `orchestrate_comprehensive_esperanto_text_replacement()` - テキスト置換メイン関数
- `parallel_process()` - 並列処理を使用したテキスト置換実行

#### 3.1.4 キャッシュ戦略

`@st.cache_data`デコレータを使用して、JSONファイルの読み込み結果をキャッシュしています。これにより、大きなJSONファイル（50MB程度）の読み込み速度を向上させています。

```python
@st.cache_data
def load_replacements_lists(json_path: str) -> Tuple[List, List, List]:
    # JSONファイルのロードとキャッシュ処理
```

### 3.2 エスペラント文(漢字)置換用のJSONファイル生成ページ.py

このファイルは、置換ルールを定義するJSONファイルを生成するためのStreamlitページです。

#### 3.2.1 主要機能

- CSV入力からの置換ルールの生成
- 複数の置換ルールの統合と優先順位付け
- ルールのカスタマイズと調整
- 品詞情報に基づいた語形変化の処理
- 3種類の置換リストの生成（全域置換、局所置換、二文字語根）
- 大文字/小文字/文頭大文字の3パターン対応

#### 3.2.2 置換リスト生成プロセス

1. CSVファイルからエスペラント語根と訳語/漢字のペアを読み込み
2. 初期置換辞書の構築と文字数によるソート
3. プレースホルダーの割り当て
4. 辞書構造から最終的な置換リストへの変換
5. 品詞情報に基づいた語形変化の追加（動詞活用など）
6. 大文字/小文字/文頭大文字の3パターン対応
7. JSON形式での結果の保存

#### 3.2.3 データ構造

置換ルールのJSONは3つの主要リストを含みます：

1. `全域替换用のリスト` - 基本的な置換ルール
2. `局部文字替换用のリスト` - @...@で囲まれた部分の置換用
3. `二文字词根替换用のリスト` - 接頭辞・接尾辞など短い語根の置換用

各リスト内のエントリは次の形式です：
```
[元のテキスト, 置換後テキスト, プレースホルダー]
```

#### 3.2.4 カスタマイズルール

エスペラント語の語根分解とカスタム置換に対応するための二種類のJSONファイルが使用されます：

1. 語根分解法設定JSON：
   ```
   ["am", "dflt", ["verbo_s1"]]
   ```
   - 「am」: エスペラント語根
   - 「dflt」: 置換優先度（文字数×10000）
   - ["verbo_s1"]: 処理オプション（動詞活用語尾を追加など）

2. 置換後文字列設定JSON：
   特定の語根に対して独自の漢字や文字列を割り当て

### 3.3 esp_text_replacement_module.py

このモジュールはテキスト置換の中核機能を提供します。

#### 3.3.1 主要機能

- エスペラント文字変換（字上符形式、x形式、^形式）
- 特殊な半角スペースの統一
- プレースホルダーを使った安全な置換
- %...%で囲まれた部分の置換スキップ
- @...@で囲まれた部分の局所置換
- 並列処理によるテキスト処理
- HTML形式の出力フォーマット

#### 3.3.2 プレースホルダーベースの置換アルゴリズム

プレースホルダーを使った置換は、このアプリケーションの核心的なアルゴリズムです：

1. 元のテキスト内の置換対象をプレースホルダーに置き換え
2. プレースホルダーを最終的な置換テキストに置き換え

この方法により、置換処理の競合や重複を避けることができます。

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

#### 3.3.3 特殊記法の処理

- `%...%`記法: 置換をスキップするための記法。最大50文字まで。
- `@...@`記法: 局所的に置換するための記法。最大18文字まで。

これらの記法は正規表現を使って抽出されます：

```python
PERCENT_PATTERN = re.compile(r'%(.{1,50}?)%')
AT_PATTERN = re.compile(r'@(.{1,18}?)@')
```

#### 3.3.4 マルチプロセッシング実装

テキスト処理の高速化のために、マルチプロセッシングが実装されています：

1. テキストを行単位で分割
2. 分割されたチャンクを複数のプロセスで並列処理
3. 結果を結合

```python
def parallel_process(
    text: str,
    num_processes: int,
    # その他のパラメータ
) -> str:
    # テキストを分割し、並列処理を実行
```

### 3.4 esp_replacement_json_make_module.py

このモジュールは置換ルールJSONの作成支援機能を提供します。

#### 3.4.1 主要機能

- エスペラント文字変換関数
- 文字幅測定と改行挿入
- 出力フォーマット設定
- プレースホルダーインポート
- 並列処理による事前置換辞書構築
- 冗長なルビの削除

#### 3.4.2 文字幅測定アルゴリズム

テキスト幅を測定し、適切な場所で改行を入れる機能：

```python
def measure_text_width_Arial16(text, char_widths_dict: Dict[str, int]) -> int:
    total_width = 0
    for ch in text:
        char_width = char_widths_dict.get(ch, 8)
        total_width += char_width
    return total_width
```

#### 3.4.3 出力フォーマット

`output_format`関数は、エスペラント語根とその訳/漢字を指定された形式で組み合わせます：

```python
def output_format(main_text, ruby_content, format_type, char_widths_dict):
    # 異なる出力形式に基づいて文字列を生成
```

この関数は、HTMLルビ形式や括弧形式など様々な出力形式に対応しています。

## 4. 重要なアルゴリズムと設計パターン

### 4.1 置換優先順位の設計

単語の長さに基づく置換優先度を設定することで、より長い単語から置換していくアプローチを採用しています。これにより、短い語根が長い単語の一部として誤って置換されることを防ぎます。

```python
# 置換優先度の計算：単語長×10000
replacement_priority_by_length = len(esperanto_Word_before_replacement) * 10000
```

### 4.2 複合置換処理フロー（orchestrate_comprehensive_esperanto_text_replacement）

複数の変換ルールを順に適用するフロー：

1. 空白の正規化とエスペラント字上符形式への変換
2. %で囲まれた部分をスキップするための一時置換
3. @で囲まれた部分の局所置換
4. 大域置換
5. 2文字語根置換（2回実行）
6. プレースホルダーの復元
7. HTML形式であれば追加整形

### 4.3 並列処理の実装

行単位でのテキスト分割と並列処理：

```python
def parallel_process(text, num_processes, ...):
    lines = re.findall(r'.*?\n|.+$', text)  # 行ごとに分割
    lines_per_process = max(num_lines // num_processes, 1)
    ranges = [(i * lines_per_process, (i + 1) * lines_per_process) for i in range(num_processes)]
    ranges[-1] = (ranges[-1][0], num_lines)  # 最後のプロセスは残りすべて
    
    with multiprocessing.Pool(processes=num_processes) as pool:
        results = pool.starmap(process_segment, [...])
        
    return ''.join(results)
```

### 4.4 キャッシュ戦略

`@st.cache_data`デコレータを使用して、JSONロードをキャッシュし、アプリのパフォーマンスを向上させています。

### 4.5 正規表現を活用したテキスト処理

特殊記法（%...%や@...@）を検出し、それらの内容を適切に処理するために正規表現を活用しています。

## 5. データフロー詳細

### 5.1 メインアプリケーションにおけるデータフロー

```
[入力テキスト] -> [空白正規化&文字変換] -> [%...%検出&スキップ] -> [局所置換@...@] 
-> [優先順位に基づく大域置換] -> [2文字語根置換] -> [プレースホルダー復元] 
-> [出力形式整形] -> [結果表示&ダウンロード]
```

### 5.2 JSONファイル生成におけるデータフロー

```
[CSV入力] -> [語根-訳/漢字ペア抽出] -> [置換辞書構築] -> [品詞情報に基づく拡張] 
-> [大文字/小文字/文頭大文字の3パターン作成] -> [プレースホルダー割り当て] 
-> [3種類の置換リスト統合] -> [JSON出力]
```

### 5.3 置換リストの構造とフロー

最終的な置換JSONは3つの主要リストで構成されています：

1. `全域替换用のリスト`:
   最初に適用される一般的な置換ルール。

2. `局部文字替换用のリスト`:
   @...@で囲まれた部分に対して適用される特殊な置換ルール。

3. `二文字词根替换用のリスト`:
   接頭辞や接尾辞などの短い語根に対応する置換ルール。文脈依存で正確な置換を確保するために、このリストは2回適用されます。

これらのリストは、メインアプリケーションでロードされ、`orchestrate_comprehensive_esperanto_text_replacement`関数によって順次適用されます。

## 6. コアアルゴリズム詳細解析

### 6.1 プレースホルダー置換メカニズム

置換の最大の課題は、置換順序による影響を避けることです。プレースホルダーを使用することで、この問題を解決しています：

1. まず、元のテキスト内の検索対象を一意のプレースホルダーに置き換えます。
2. すべての置換が完了した後、プレースホルダーを最終的な置換テキストに変換します。

このアプローチにより、次のような問題を回避できます：
- 置換対象が別の置換対象の一部になる場合（例：「am」と「amas」）
- 置換後のテキストに新たな置換対象が発生する場合

### 6.2 語根分解と優先順位付け

エスペラント語の語構造を考慮した語根分解と優先順位付け：

1. 単語の長さに基づく基本優先順位（長い単語ほど優先）
2. 品詞情報に基づく語形変化の追加：
   - 名詞：-o, -on, -oj の追加
   - 形容詞：-a, -aj, -an の追加
   - 副詞：-e の追加
   - 動詞：-as, -is, -os, -us, -i, -u などの活用形追加
3. 接頭辞・接尾辞（二文字語根）の特別処理

このアプローチにより、エスペラント語の文法規則に基づいた正確な置換が可能になります。

### 6.3 特殊文字処理

エスペラント固有の文字（ĉ, ĝ, ĥ, ĵ, ŝ, ŭなど）の3つの表記形式間の変換：

1. 字上符形式（ĉ）
2. x形式（cx）
3. ^形式（c^）

それぞれの形式間の変換マッピングが定義され、ユーザー選択に応じて適用されます。

### 6.4 HTML-Rubyフォーマッティング

日本語注釈（ルビ）のフォーマッティングでは、特に長い注釈に対して自動的にサイズ調整と改行が行われます：

1. メインテキストとルビテキストの幅比率を計算
2. 比率に基づいてルビのクラスを選択（XXS_S, XS_S, S_S, M_M, L_L, XL_L, XXL_L）
3. 長いルビテキストの場合、適切な位置で改行を挿入

このアプローチにより、見やすく読みやすいルビ表示が可能になります。

## 7. パフォーマンス最適化技術

### 7.1 マルチプロセシング

大量のテキストを効率的に処理するために、マルチプロセシングが実装されています：

```python
def parallel_process(text, num_processes, ...):
    # テキストを分割し、並列処理
```

この実装では、テキストを行単位で分割し、指定された数のプロセスで並列処理します。ただし、テキストが短い場合や行数が少ない場合は、オーバーヘッドを避けるために単一プロセスでの処理に切り替わります。

### 7.2 キャッシュ戦略

Streamlitのキャッシュ機能を活用して、重い処理（特にJSONファイルのロード）の結果をキャッシュしています：

```python
@st.cache_data
def load_replacements_lists(json_path: str) -> Tuple[List, List, List]:
    # JSONファイルのロードとキャッシュ処理
```

このキャッシュにより、同じJSONファイルを何度も読み込む必要がなくなり、アプリのレスポンスが向上します。

### 7.3 段階的処理とプレースホルダー

テキスト置換プロセスを複数段階に分け、プレースホルダーを使用することで、処理効率を向上させています。これにより、複雑な置換ルールを順序立てて適用できます。

### 7.4 デモデータとプレビューの最適化

長いテキストのプレビュー表示時には、全行を表示するのではなく、先頭247行と末尾3行のみを表示する最適化が行われています：

```python
if len(lines) > MAX_PREVIEW_LINES:
    # 先頭247行 + "..." + 末尾3行のプレビュー
    first_part = lines[:247]
    last_part = lines[-3:]
    preview_text = "\n".join(first_part) + "\n...\n" + "\n".join(last_part)
```

これにより、非常に長いテキストでもUIのレスポンス性が保たれます。

## 8. 拡張とカスタマイズのポイント

このアプリケーションは、さまざまな方法で拡張とカスタマイズが可能です。以下に主なポイントを示します：

### 8.1 新しい出力形式の追加

`output_format`関数を拡張することで、新しい出力形式を追加できます：

```python
def output_format(main_text, ruby_content, format_type, char_widths_dict):
    # 既存の形式に加えて、新しいformat_typeに対応する条件を追加
    elif format_type == '新しい形式':
        return f'<新しい形式>{main_text}<新しい形式>{ruby_content}'
```

### 8.2 カスタム置換ルールの作成

CSVファイルとJSONファイルを通じて、独自の置換ルールを定義できます：

1. CSVファイルでエスペラント語根と対応する訳語/漢字を定義
2. 語根分解設定JSONで、特定の語根に対する処理方法をカスタマイズ
3. 置換後文字列設定JSONで、より細かい置換ルールを定義

### 8.3 新しい特殊記法の追加

現在の%...%（スキップ）や@...@（局所置換）に加えて、新しい特殊記法を追加することも可能です。例えば、新しい特殊記法を追加する場合：

1. 新しい正規表現パターンを定義
2. 検出関数と置換リスト作成関数を実装
3. `orchestrate_comprehensive_esperanto_text_replacement`関数に新しい処理ステップを追加

### 8.4 パフォーマンス最適化の拡張

より大きなテキストを処理するためのパフォーマンス最適化も可能です：

1. マルチプロセシングの改良（チャンクサイズの動的調整など）
2. メモリ効率の向上（ジェネレータの活用など）
3. より効率的なアルゴリズムの実装

## 9. エスペラント言語処理の言語学的側面

このアプリケーションは、エスペラント語の特徴を活かした設計になっています：

### 9.1 エスペラントの語構造の活用

エスペラント語は規則的な語構造を持ちます：

- 名詞は -o で終わる（amiko = 友人）
- 形容詞は -a で終わる（bona = 良い）
- 副詞は -e で終わる（bone = 良く）
- 動詞の不定形は -i で終わる（ami = 愛する）
- 動詞の現在形は -as（amas = 愛する）
- 動詞の過去形は -is（amis = 愛した）
- 動詞の未来形は -os（amos = 愛するだろう）
- 動詞の条件法は -us（amus = 愛するだろう（条件付き））

アプリケーションは、これらの語尾を自動的に処理し、基本語根に基づいて様々な形態の単語を正確に置換します。

### 9.2 接頭辞・接尾辞システムの処理

エスペラント語は豊富な接頭辞と接尾辞を持ち、それらを組み合わせて新しい単語を作ります：

- mal- = 反対（bona = 良い、malbona = 悪い）
- -in- = 女性（amiko = 友人、amikino = 女友達）
- re- = 再び（veni = 来る、reveni = 戻る）

アプリケーションは、これらの接頭辞・接尾辞を「二文字語根」として特別に処理し、正確な置換を実現しています。

## 10. コード拡張のサンプル

このセクションでは、アプリケーションを拡張するためのサンプルコードを示します。

### 10.1 新しい出力形式の追加

```python
# esp_replacement_json_make_module.py に追加
def output_format(main_text, ruby_content, format_type, char_widths_dict):
    # 既存のコード...
    
    elif format_type == 'ルビ下線形式':
        # ルビ付きで下線も引く形式
        return f'<ruby>{main_text}<rt>{ruby_content}</rt></ruby><u>{main_text}</u>'
        
    # 既存のコード...
```

### 10.2 新しい特殊記法の追加

```python
# esp_text_replacement_module.py に追加

# #...# で囲まれた箇所を強調するための正規表現
HASH_PATTERN = re.compile(r'#(.{1,30}?)#')

def find_hash_enclosed_strings_for_emphasis(text: str) -> List[str]:
    """'#foo#' の形を全て抽出。30文字以内に限定。"""
    matches = []
    used_indices = set()
    for match in HASH_PATTERN.finditer(text):
        start, end = match.span()
        if start not in used_indices and end-2 not in used_indices:
            matches.append(match.group(1))
            used_indices.update(range(start, end))
    return matches

def create_replacements_list_for_emphasis(text: str, placeholders: List[str]) -> List[Tuple[str, str]]:
    """
    '#xxx#' で囲まれた箇所を検出し、
    ( '#xxx#', placeholder ) という形で対応させるリストを作る
    """
    matches = find_hash_enclosed_strings_for_emphasis(text)
    replacements_list_for_emphasis = []
    for i, match in enumerate(matches):
        if i < len(placeholders):
            replacements_list_for_emphasis.append([f"#{match}#", placeholders[i]])
        else:
            break
    return replacements_list_for_emphasis
```

### 10.3 パフォーマンス最適化

```python
# esp_text_replacement_module.py に追加

def chunk_generator(text: str, chunk_size: int = 1000):
    """テキストを指定サイズのチャンクに分割するジェネレータ"""
    start = 0
    while start < len(text):
        chunk = text[start:start + chunk_size]
        yield chunk
        start += chunk_size

def streaming_parallel_process(
    text: str,
    num_processes: int,
    chunk_size: int = 1000,
    # その他のパラメータ...
) -> str:
    """
    ストリーミング方式で大きなテキストを処理し、メモリ効率を向上
    """
    chunks = list(chunk_generator(text, chunk_size))
    with multiprocessing.Pool(processes=num_processes) as pool:
        processed_chunks = pool.map(
            # チャンク処理関数
            lambda chunk: orchestrate_comprehensive_esperanto_text_replacement(
                chunk,
                # その他のパラメータ...
            ),
            chunks
        )
    return ''.join(processed_chunks)
```

## 11. まとめ

「エスペラント文 漢字置換・ルビ注釈ツール」は、エスペラント語の規則的な構造を活かして、テキストを効率的に加工するStreamlitアプリケーションです。このアプリケーションの主な技術的特徴は以下の通りです：

1. プレースホルダーベースの段階的置換処理
2. マルチプロセシングによる並列テキスト処理
3. エスペラント語の文法規則を考慮した語根分解と優先順位付け
4. 柔軟なHTMLルビフォーマットと自動サイズ調整
5. 特殊記法による置換スキップと局所置換の制御
6. カスタマイズ可能な置換ルールとフォーマット

このアプリケーションは、エスペラント語学習者やエスペラント文学の読者を支援するだけでなく、言語処理アプリケーションの設計パターンとしても参考になる実装です。Streamlitフレームワークを活用したUI設計と、効率的なテキスト処理アルゴリズムの組み合わせが、使いやすく拡張性のあるアプリケーションを実現しています。