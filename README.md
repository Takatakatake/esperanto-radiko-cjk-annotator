# エスペラント文の注釈ルビ・漢字化ツール (日中韓3言語版)

エスペラント文を入力すると、**高精度な語根分解**にもとづいて

1. **注釈ルビ** — 語根の上に日本語/中国語/韓国語の訳をルビ表示（学習用）
2. **漢字化(ルビつき)** — 漢字が本文・エスペラント語根がルビ
3. **漢字化(純粋置換)** — タグなしの漢字テキスト（例: `Mi amas la amikecon.` → `我 爱as la 友性on.`）

に変換する Streamlit アプリです。

## 🌐 今すぐ使う (Live Apps)

| 言語 | URL |
|---|---|
| 日本語版 | https://esperanto-radiko-cjk-annotator.streamlit.app/ |
| 中文版 | https://esperanto-radiko-cjk-annotator-zh.streamlit.app/ |
| 한국어판 | https://esperanto-radiko-cjk-annotator-ko.streamlit.app/ |

使い方: メインページで「📝 サンプル文を入力する」→「🔁 変換する」の2クリックで体験できます。
字上符付き文字は `cx / c^ / ĉ` のどの表記でも入力可能です。

## 📄 アプリのページ構成（各言語版共通）

- **メイン（変換）** — 4モード切替（注釈ルビ / 漢字ルビ / 純粋置換 / 自作JSONアップロード）。
  出力形式は自動選択。結果はプレビュー・編集・ダウンロード・コピー可能。
  手元の `user_corrections.json` をその場で読み込んで適用することもできます。
- **語根分解の手動補正** — 誤分解を見つけたらGUIで即修正（例: `s/port/i` → `sport/i`）。
  補正は自分のセッションにだけ即反映され、`user_corrections.json` としてダウンロード/復元/他言語版への移植が可能。
- **最新データのダウンロード** — アプリが実際に使っている最新の大JSON（ルビ日中韓3本+漢字1本+純粋置換1本）
  と辞書・設定ファイルを入手できます。

## 📁 リポジトリ構成

```
Esperanto-Kanji-Ruby-JA/   日本語版アプリ (main.py, pages/, esp_*_module.py, app_data/)
Esperanto-Kanji-Ruby-ZH/   中文版アプリ
Esperanto-Kanji-Ruby-KO/   한국어版アプリ
_analysis_20260625/        大JSON再生成パイプライン+品質監査スクリプト群
_project_root_misc/        コーパス(京大エス研HTML文書群)・修正ガイド等の作業資料
```

## 🔧 大JSONの再生成（正式パイプライン）

```bash
python _analysis_20260625/regenerate_all.py --ruby-only
# 漢字候補を隔離worktreeで監査する場合だけ:
ESP_ALLOW_UNREVIEWED_KANJI_CANDIDATE=1 python _analysis_20260625/regenerate_all.py --all-tracks
```

track modeの明示は必須です。通常の注釈ルビ更新は `--ruby-only` を使い、配備済み
漢字成果物9点をHEAD・SHA-256で保護します。漢字正本も含めて再構築する場合だけ
`--all-tracks` を指定します。ただしPhase511の漢字21件gateが未整備のため、現時点の
all-tracksは隔離worktree内のcandidate-onlyで、上記環境変数がなければ書込前に停止します。
候補を配備成果物へ昇格してはいけません。外部入力は `ESP_GOLD_PATH` / `ESP_ACADEMIC_GOLD_PATH` /
`ESP_PEJVO_ORIGINAL_PATH` / `ESP_CORPUS_PATH` を明示し、all-tracksではさらに
`ESP_KANJI_MASTER_PATH` を指定します。詳細は
`_analysis_20260625/README_regeneration.md` を参照してください。

## 🧠 品質の設計原則

- **二本立て**: 注釈ルビ=粗い一体（学習向け・コーパス基準） / 漢字=偽分解を尊重した深い語根分解
- **日中韓で語根分解は完全一致**（全コーパス語彙13,112語で実測検証済み）
- **決定論**: 一つの文字列=一つの分解。精度は3層（語根リスト→E_stem→語単位の確定リスト）で担保
- 京大エス研コーパス(123文書)との一致率 **99.796%**（残差は全て文書化済みの意図的差異）
- 権威階層: 2890重要単語集(Unified_Level) → PEJVO由来(1-44104行) → PIV専用(44105行〜)

## 📚 データソース

- PEJVO/PIV統合の学習者版マスター辞書（約62,000語・語根分解済み）
- 2890 Gravaj Esperantaj Vortoj（日中韓訳つき最重要語彙集）
- エスペラント語根→漢字割り当てマスター（約7,800語根）
- 京大エス研 エスペラントHTML文書群（注釈ルビの実運用コーパス）

> このリポジトリは、元の3アプリ GitHub リポジトリ（`Takatakatake/Esperanto-Kanji-Converter-...` 等）とは
> **完全に独立した別リポジトリ**です。元リポジトリには一切変更を加えていません。
