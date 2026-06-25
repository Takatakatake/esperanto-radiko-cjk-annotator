# esperanto-radiko-cjk-annotator

エスペラント文を入力すると、**高精度な語根分解**にもとづいて、各語根の上に
**HTML形式のルビ注釈（日本語・中国語・韓国語）**を付与したり、**漢字化**したりする
Streamlit アプリ（日中韓3版）の **徹底ブラッシュアップ版** リポジトリ。

> このリポジトリは、元の3アプリ GitHub リポジトリ（`Takatakatake/Esperanto-Kanji-Converter-...` 等）とは
> **完全に独立した別リポジトリ**です。元リポジトリには一切変更を加えていません。

## 構成
- `Esperanto-Kanji-Converter-and-Ruby-Annotation-Tool/` — 日本語版アプリ
- `Esperanto-Hanzi-Converter-and-Ruby-Annotation-Tool-Chinese/` — 中文版アプリ
- `Esperanto-Kanji-Converter-and-Ruby-Annotation-Tool-Korean/` — 한국어版アプリ
  - 各アプリ: `main.py`（置換実行）, `pages/`（置換用JSON生成）, `esp_*_module.py`, `Appの运行に使用する各类文件/`（ランタイムデータ）
- `_analysis_20260625/` — ブラッシュアップ用の検証・生成・監査スクリプト群（再利用可能）
- `esperanto_html_redaktado/` — ルビ表示品質の参考資料（`ruby_css_verifier.py` 等）

## 語根分解の仕組み（このアプリの思想）
**「一つの文字列＝一つの分解」**（決定論的）。精度向上の3層：
1. **語根リスト**（長い語根優先の貪欲マッチ）
2. **E_stem**（`/`分解済みPEJVO語＝デフォルト分解）
3. **`世界语单词词根分解方法の使用者自定义设置.json`**（語単位の人手キュレーション上書き＝精度lever）

## このブラッシュアップで行ったこと（要点）
- 最先端の語根分解（PEJVO/PIV統合・学習者版）で E_stem・語根リストを刷新（gold化）。
- **語ごと・文脈依存**の日中韓注釈（注釈版由来）を統合（`kultur`=文化/飼育/養殖 等）。訳カバレッジ ≈100%。
- **語根↔ルビ対応**の徹底：人工グロス・同綴り衝突の誤形態素を約300件、語根忠実な意味へ補正（`anestezio`→否定/感覚 等）。
- ルビ表示品質ゲート（サイズ階級・`<br>`整合）、2890→PEJVO→PIV のティア別分解精度監査の仕組み。
- 漢字化モード用の語根→漢字（参照2 漢字注入版）統合は進行中。

※生成物（最終置換JSON）は再生成可能。ソース（CSV/語根/E_stem/設定/word_anno）＋スクリプトから `_analysis_20260625` のツールで再構築できます。
