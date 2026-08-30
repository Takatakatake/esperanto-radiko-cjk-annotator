# 公開標準フロー — 漢字化エスペラント日記

- Workflow ID: `WF-20260830-001`
- Status: `Active`
- Maintainer: `Takatakatake`
- As of: 2026-08-30
- Scope: 日記素材の整理、自然なエスペラント化、漢字化、厳密校正、知乎投稿用の日付と中国語タイトル
- Privacy boundary: 手順だけを保存する。個別の日記本文や会話履歴は、別の明示承認なしに保存しない

## 目的

新しいChatGPT、Codex、Claude等が、漢字化エスペラント日記の手順を
毎回ゼロから再構築しないようにする。この公開文書を共通の運用正本として
読み、実装とデータの現在状態を確認してから処理する。

この公開文書はモデル学習でも自動同期でもない。AIがこのファイルと、
ここから参照する公開source repositoryを実際に読める場合にのみ再利用できる。
この文書には手順だけを記録し、個別の日記本文や会話履歴を保存しない。

## 権威と鮮度

優先順位は次のとおり。

1. 現在のユーザー指示
2. 対象リポジトリの現在の実ファイルとデータ
3. この公開標準フロー
4. 過去の会話、例示、AIの推測

この文書のcommit snapshotは再接続用の検証点であり、永久固定ではない。
source repositoryの`main`が動いた場合は、関連ファイルを再読してから使う。

## 標準フロー

### 1. 日本語日記を整える

- 音声文字起こしや口頭の内容を、自然で読みやすい日本語日記に整える。
- 出来事、時系列、感情、重要な具体性を保つ。
- 冗長な言いよどみは整理するが、内容を薄めたり、事実を補作したりしない。
- 必要ならユーザー確認を経て日本語版を確定する。

### 2. エスペラント原文を確定する

- 内容を薄めず、簡潔で平易な自然なエスペラントにする。
- 固有名詞、日付、段落、時系列、語調を保つ。
- 漢字化しやすさだけを理由に、不自然な表現や意味の変更を採用しない。
- 漢字化前の確定全文を監査用の`Esperanto source`として保持する。
- 一次変換後の校正は、必ずこの確定原文と一対一で比較する。

### 3. 一次漢字化を行う

#### 優先方法A — repositoryと同じ処理をローカル実行

実行環境が利用できる場合は、
[`Takatakatake/esperanto-radiko-cjk-annotator`](https://github.com/Takatakatake/esperanto-radiko-cjk-annotator)
の日本語版実装を取得し、現在の実ファイルを読んでから実行する。

必須参照:

- `Esperanto-Kanji-Ruby-JA/main.py`
- `Esperanto-Kanji-Ruby-JA/esp_text_replacement_module.py`
- `Esperanto-Kanji-Ruby-JA/esp_overlay_module.py`
- `Esperanto-Kanji-Ruby-JA/app_data/置換リスト_漢字_純粋置換.json`
- `Esperanto-Kanji-Ruby-JA/app_data/user_corrections.json`
- `Esperanto-Kanji-Ruby-JA/app_data/placeholders_skip.txt`
- `Esperanto-Kanji-Ruby-JA/app_data/placeholders_localcapture.txt`

Webアプリの「✂️ 漢字化・純粋置換（タグなしテキスト）」と同じ設定:

```text
format_type = 替换后文字列のみ(仅)保留(简单替换)
use_parallel = False
letter_type = ĉ ĝ ĥ ĵ ŝ ŭ (標準)
```

現在の`main.py`と同じ方法で純粋置換JSON、placeholder、overlayを読み、
`orchestrate_comprehensive_esperanto_text_replacement()`を直接呼ぶ。
記憶だけで関数引数や前処理を再実装せず、現在の`main.py`を正本とする。

`esp_overlay_module.py`の承認済みbaselineを読み、対象modeのentryを生成し、
`merge_overlay()`を通して大域置換リストへ統合する。overlayの読み込みに
失敗した場合や0件の場合は、適用したと偽ってはならない。

現在の`main.py`は、1回目の後に`auto_overlay_entries()`を試し、entryが
返れば2回目を実行する。ただし、静的に確認した検出処理はruby blockを前提と
しており、タグなしの純粋置換出力で自動検出が確実に働くとは確認できていない。
自動補正を保証された機能として扱わず、実際にentryが生成され2回目が走った
場合だけ、その事実を報告する。必要な補正は検証して明示適用し、再変換する。

#### 代替方法B — Webアプリを直接操作

ローカル実行が利用できず、ブラウザ操作が可能な場合は、
[Webアプリ](https://esperanto-radiko-cjk-annotator.streamlit.app/)で
「✂️ 漢字化・純粋置換（タグなしテキスト）」を選び、確定した
エスペラント全文を一次変換する。

#### 代替方法C — ユーザー提示のアプリ出力を校正

ローカル実行もWebアプリの直接操作もできない場合は、できない境界を明示し、
ユーザーにアプリ出力の提示を依頼する。その出力を確定原文と参照データに
照らして校正する。

### 4. 一次変換を厳密に校正する

漢字割当と識別子の正本は、
[`Takatakatake/kanji_assign`](https://github.com/Takatakatake/kanji_assign)
の現在の次のファイルとする。

- `_kanji_map_master.tsv` — 語根と漢字割当のmachine-readable master
- `_identifier_sidecar.tsv` — 現在の識別子と最終表示
- `kanji.html` — 人が確認する表示
- `漢字化方針_v2_20260613.md` — 割当・固有名詞・語尾等の方針

校正規則:

- 自動変換結果をそのまま正しいと判断しない。
- 確定したエスペラント原文と、語ごと・語根ごとに照合する。
- 最終出力では語根間にスラッシュを入れない。
- 文法語尾・接辞・複数・対格・動詞語尾を確認し、漢字化された語根の後ろへ
  ラテン文字で自然につなげる。
- 偽分解、過細分解、複合語の誤分解、接辞の誤認、語尾の誤吸収を確認する。
- masterで独立語根とされるものを、見かけの綴りだけで再分解しない。
- 固有名詞を通常語根として誤分解した場合は、無理に漢字化せず元の
  ラテン文字へ戻す。
- 参照データにない語根、固有名詞、不確かな語根には新しい漢字割当を作らず、
  ラテン文字のまま残す。
- 反対に、masterにある基本語や漢字化可能な語が不必要にラテン文字で
  残っていないか確認する。
- 上付き識別子は記憶や過去の例から転記せず、現在の
  `_identifier_sidecar.tsv`と、必要な文脈依存の純粋置換ruleから取得する。
- sidecarの一般語根表示と、pure JSONの文脈依存出力を混同しない。

識別子はデータ更新で変わりうる。同じ漢字でも語根を取り違えてはならない。
このsnapshotでは`pas -> 过ᴾ`、`preter -> 过ᴾᴿ`であり、両者は別語根の
正しい表示である。また、`ĉielo -> 天ᶜ̂o`のように文脈依存のpure JSON
出力として確認すべき例もある。必ずsource root、実データ、文脈で決める。

### 5. 必要なら修正して再変換する

- エスペラント自体が不自然、または同じ意味のより自然で漢字化しやすい表現が
  ある場合だけ、意味を変えずに原文を修正する。
- 原文を変えたら、部分的な手直しで済ませず全文を再変換する。
- 語根分解補正が必要なら、補正候補と理由をユーザーへ示す。
- 永続的な`user_corrections.json`追加やsource repositoryへの書き込みは、
  ユーザーまたはrepository maintainerの別の明示承認を得てから行う。
- 補正を適用した場合は2回目の変換結果を再び原文・master・sidecarと照合する。

### 6. 完成物を整える

- 最終的な漢字化エスペラント日記を作る。
- 知乎投稿用に、`YYYY年M月D日｜中国語タイトル`形式の日付と、内容に合う
  自然で誇張のない中国語タイトルを作る。
- 中間成果をどこまで表示するかは、現在のユーザー指示に従う。
- 表示しない場合でも、確定エスペラント原文は校正の比較対象として保持する。

## 実行方法の開示

一次変換を行った場合は、次のどれを実際に行ったかを正確に述べる。

```text
変換方法:
- Webアプリを直接操作した
- アプリと同じsource code/dataをローカル実行した
- ユーザー提示のWebアプリ出力を校正した
- 一次変換は実行できなかった
```

複数が該当する場合だけ複数を書く。実際には行っていない方法を述べない。
可能なら、参照したrepository commitも併記する。

## Source snapshot

| Repository | Ref | Inspected commit | Relevant state |
|---|---|---|---|
| `Takatakatake/esperanto-radiko-cjk-annotator` | `main` | [`5a5778b25086335d9112930bf2fdf514ce4ca475`](https://github.com/Takatakatake/esperanto-radiko-cjk-annotator/commit/5a5778b25086335d9112930bf2fdf514ce4ca475) | pure mode、exact format、default non-parallel、overlayと、未実証のauto-overlay試行pathを確認 |
| `Takatakatake/kanji_assign` | `main` | [`e43f924dff01ed0ddf2c62c4572a07c23a116ebc`](https://github.com/Takatakatake/kanji_assign/commit/e43f924dff01ed0ddf2c62c4572a07c23a116ebc) | master、sidecar、human-readable map、policyの存在を確認 |

Snapshot時点の
`Esperanto-Kanji-Ruby-JA/app_data/user_corrections.json`は正確に`[]`で、
承認済みbaseline補正は0件だった。将来の実行時は現在のファイルを再確認する。

## 防止すべき失敗

- Chatごとにフローを推測で再構築する。
- アプリ出力だけを見て、確定エスペラント原文と比較しない。
- ローカル実行、Web操作、ユーザー提示出力の区別を偽る。
- 内容を薄める、時系列や感情を変える。
- スラッシュを最終出力へ残す。
- 語尾、接辞、複合語、固有名詞を誤って分解する。
- 古い識別子例を現在の正本として使う。
- 不明な語根へ独自の漢字を割り当てる。
- ユーザーまたはrepository maintainerの承認なしに、補正データ、日記本文、またはsource repositoryを書き換える。

## 完了条件

- 自然な日本語とエスペラントの意味が保たれている。
- 確定エスペラント原文と最終漢字化文を一対一で照合した。
- master、sidecar、pure JSON、固有名詞、未変換語、接辞・語尾を確認した。
- 不明点をラテン文字または`UNKNOWN`として残し、推測で埋めていない。
- 実際の変換方法と確認範囲を正確に開示した。
- 日付と自然な中国語タイトルを作成した。

## 更新条件

次の場合は、この公開標準フローの適用前にsourceを再読し、必要ならrepository maintainerの承認のもと、branch＋PRで更新する。

- 参照repositoryの`main` commitが変わった。
- pure mode、JSON schema、function signature、overlay、identifier生成が変わった。
- ユーザーが標準フローまたは出力形式を変更した。
- 実際の利用で新しい反復失敗または有効な補正が確認された。
