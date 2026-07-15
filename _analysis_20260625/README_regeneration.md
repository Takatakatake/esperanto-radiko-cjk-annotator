# 道B: 大JSON再生成パイプライン(正式ルート)

このディレクトリには、3言語アプリの置換用大JSON(ルビ/漢字/純粋置換)を再生成する
**唯一の正式ルート**が収録されています。アプリ内の旧「JSON生成ページ」は
最新の品質修正を含まないため撤去されました。

## 一括実行
    $env:ESP_GOLD_PATH = '<監査済みgold snapshot>'
    $env:ESP_ACADEMIC_GOLD_PATH = '<同一行対応の学術版snapshot>'
    $env:ESP_PEJVO_ORIGINAL_PATH = '<監査済み原典PEJVO snapshot>'
    $env:ESP_CORPUS_PATH = '<cleanな京大HTML repo>'
    $env:ESP_KANJI_MASTER_PATH = '<監査済み漢字割当正本ディレクトリ>'
    python _analysis_20260625/regenerate_all.py

この5環境変数は正式一括実行では必須である。学習者版・学術版・原典PEJVOは
`_fake_coarse_reference_manifest.json` のbytes/line count/SHA-256と一致し、
正式生成は書き込み前に全62,313行の対応、偽分解3,383行の語義gloss一致、
および粗い分解参照表を`--check`で再構成する。goldは
`_no_worsening_scope_manifest.json` のbytes/SHA-256と一致し、corpusは2つの
exact manifestが記録したHEAD/status/content hashと一致すること。漢字正本は
`_kanji_master_scope_manifest.json` の4ファイルのbytes/SHA-256と一致すること。
いずれかが異なれば最初の書き込み前に停止する。

実行順(2026-07-15版。番号は `regenerate_all.py` の `STEPS` と一致):
1. build_fake_coarse_reference_manifest.py --check … final 5E学習者版・0462学術版・PEJVO原典を再読し、全行対応・語義一致・3,113行の粗分解authorityを検証
2. build_fake_coarse_transition_review.py --check … 歴史的C679→B090の136行（135表層、word gate 135行＋full-master-only 1行）を由来を変えず固定
3. build_fake_coarse_ff33_transition_review.py --check … FF33で新たに偽分解となったTomisto 1行を別scopeとして固定
4. build_fake_coarse_5e_transition_review.py --check … final 5Eのpromilo 1行を別scopeとして固定（Ruby=promil/o、Kanji=pro/mil）
5. build_fake_coarse_transition_app_review.py --check … アプリ移行対象を固定authorityと照合
6. build_corpus_exact_manifest.py --check … 固定exact manifestと指定コーパスのclean HEAD・内容hashを照合
7. build_corpus_reviewed_exact_manifest.py --check … 汎用規則後に残ったevaluable表記のtyped exact固定を照合
8. bare_word_audit.py --require-zero … ガイド必須rubyの裸語レビュー漏れを0件に固定
9. apply_corpus_word_anno.py --write … コーパス確定注釈とexact境界ルールを日中韓へ同期
10. build_word_anno_boundary_manifest.py --check … 日中韓の語根境界signatureを照合
11. apply_confirmed_now.py 30 --settings-audit … 補正後の設定が日中韓で意味的に同一か検査
12. apply_confirmed_now.py 30 --write … 確定リスト適用＋Ruby 3言語再生成
13. fix_ruby_postregen.py … Ruby事後修正
14. test_canonical_corpus_surfaces.py … canonical全数ゲートの純粋関数回帰
15. check_canonical_corpus_surfaces.py … 21,443表記を日中韓runtimeで全数検査
16. resync_kanji_master.py --write … 漢字正本と全面再同期（CSVはヘッダーなし9,813語根・未対応13を含む、互換パッチ前word_kanji 43,738語幹）
17. apply_kanji_now.py --write … 漢字3言語再生成（偽分解を深分解authorityへ戻す）
18. fix_kanji_2890.py --apply … 38語の旧互換安全網（適用後word_kanji 43,776語幹）
19. check_kanji_fake_decomposition.py … 深分解piece列と漢字割当を3言語で全件照合
20. derive_pure_kanji.py … 純粋置換版JSON再導出
21. anomaly_scan.py … 6JSON異常スキャン
22. test_generation_regressions.py … 生成規則＋配置済み3言語の実機回帰
23. test_reviewed_exact_manifest.py … 残差manifest回帰
24. check_multilingual_structure.py … 全域ルールの日中韓語根分節一致
25. check_raw_apostrophe_structure.py … U+2019原表記の全コーパス3言語runtime回帰
26. no_worsening_audit.py --current-only-diagnostic … 固定referenceに対する現行runtime残差0を再確認
27. audit_master_3lang_full_snapshot.py … final 5E学習者版・0462学術版の全62,313行を3言語runtimeで正式監査
28. prune_baks.py … 全工程合格後に一時バックアップを掃除

`audit_master_3lang_full_snapshot.py` は偽分解指定3,383行を毎回すべて測定するが、
正式既定ゲートで粗いルビ境界を強制するのは、独立に裁定済みの移行対象138行だけである。
2026-07-15固定snapshotでは各言語802行が粗い境界に一致し、2,581行は未裁定キューとして
報告される（`all_fake_coarse_gate=false` / `all_fake_coarse_enforced=false`）。未裁定行を
一括で粗分解へ昇格してはならず、個別の語義・京大コーパス・日中韓境界を確認してから
review manifestへ追加する。`--enforce-all-fake-coarse` は全件裁定後だけ使用する。
また、完全無注釈の語彙候補45件と非終端無注釈断片候補202件も報告専用の確認キューであり、
自動修正や幅合わせのための細分化対象ではない。ルビ幅は原綴りのおおむね2倍以内を表示ゲートで
検査するが、幅を短くする目的だけで語根境界を増やさない。

## 構成
- gen_replacement.py      … 置換リスト生成の中核(AN/ONリスト等の拡張点を含む)
- _base_stemming_settings.json … 3言語共通の語根分解設定正本(説明行を除く1778行)
- _base_stemming_settings_manifest.json … 正本のLF正規化bytes/SHA-256・HEAD blob由来を固定
- out/confirmed_tier30.json … 単語レベルの分解確定リスト(語根分解のピン)
- out/word_anno_*.json      … 言語別の語ごと注釈上書き(固有名詞等)
- out/kanji_root.csv / word_kanji.json … 漢字マスター正本からの派生(resyncが再構築)

`gen_replacement.py` が生成ロジックの唯一の正本です。各アプリの
`esp_generation_module.py` は後方互換用ファサードで、必ずこの正本を再エクスポートします。
同名Pythonモジュールの衝突を避けるため、ファサードは読み込み済みモジュールの
`__file__` を正本の絶対パスと照合します。この構成はリポジトリ全体を前提とし、
アプリディレクトリだけを単独コピーした環境では生成機能を利用できません。
日中韓を同一Pythonプロセスで連続生成するときも、`gen_replacement.py` と各
`esp_overlay_module.py` は言語別の兄弟 `esp_replacement_json_make_module.py` を
実ファイルパスで検証して読み直し、先に生成した言語のmodule cacheを流用しません。
各アプリの `分解設定.json` や `.bak_*` は再生成の入力正本ではありません。
`apply_confirmed_now.py` は常に固定された `_base_stemming_settings.json` から組み立て、
各言語から引き継ぐのは先頭の説明行だけです。これにより過去の生成済み行が
バックアップ経由で正本へ逆流することを防ぎ、`--settings-audit` は補正後の意味的
SHA-256が日中韓で一致しない場合、成果物を書き込む前に停止します。
また、`word_anno` で末尾が独立片 `/an` と確定した語幹は、
`o/oj/on/ojn/a/aj/an/ajn/e/en` を自動派生します。同じ綴りに別の `word_anno`
分解がある場合は自動生成せず、同綴異義語を保全します。

`confirmed_tier30.json` の境界メタデータ:

- `boundary_only`: 完全一致の空白境界ルールだけを登録し、裸の部分一致キーを除去する。
- `boundary_with_noop_guard`: 境界付き分解に加え、語内に同綴りが現れる場合の無変更ガードも登録する。
- `ruby_left_boundary`: レビュー済み語根を語トークン左端だけで生産的に適用する。
  `exact_only` と組み合わせ、通常の whole-word 境界指定とは併用しない。
- `exact_only`: 通常の品詞派生を広げず、`target` の語形だけを固定ルールにする。
  同綴りの既存設定に生産的な接尾規則がある場合はその派生を保持し、裸語を作る
  `ne` 動作だけをexact規則へ引き渡す（`teren` と `tereno/terenoj` の共存など）。
- `case_sensitive`: 指定された大小文字表記だけを生成し、通常の upper/cap 変種を作らない。
- `typed_roles`: exact target各片の `R`(ruby) / `L`(literal) を固定し、`an/on/en`
  などの語根・文法語尾両義をスラッシュ境界だけで推測しない。
- `context_annotation`: 生産的な語幹に予約済み `word_anno` キーを適用し、
  `kaj`=波止場 / `kaj`=そしてのような同綴異義を独立語へ漏らさない。
- `ruby_context_annotation`: Ruby生成だけで使う予約注釈。漢字生成ではその設定行全体を
  適用せず、漢字マスター由来の通常規則へ委ねる。
- `ruby_track_only` / `kanji_track_only`: 相互排他的なトラック指定。同じトラックでは
  メタデータを除いて設定を処理し、反対トラックでは設定行全体を適用しない。
  両方の併記、および従来の `ruby_only` との併記は生成前に拒否する。
- `ruby_only`: exact・typed Ruby規則向けの従来メタデータ。漢字トラックでは設定行を
  適用しない。一般的なトラック分離には上記2メタデータを用いる。

辞書表層末尾の文末記号 `!` / `?` はガイド8.1に従ってルビ外へ出す。
略語のピリオド（`k.t.p.`、`t.e.`、`ekz.` 等）は例外として原子的rb内に保持する。

生成規則とデプロイ済みJSONの回帰テスト:

    python -m unittest _analysis_20260625.test_generation_regressions -v

## 生きた正本(いずれも更新が続く。編集禁止・読むだけ)
- 語根分解: `エスペラント辞書徹底語根分解_20260630\`
  (学習者版=gold深分解 / 日中韓注釈版ドラフト=ルビ粗分解)
- 漢字割当: `エスペラント語根＿漢字割り当て＿20260630\`
  (_kanji_map_master.tsv + _identifier_sidecar.tsv + 漢字注入_学習者版)
外部環境では ESP_GOLD_PATH / ESP_ACADEMIC_GOLD_PATH /
ESP_PEJVO_ORIGINAL_PATH / ESP_KANJI_MASTER_PATH / ESP_CORPUS_PATH
環境変数で場所を指定します。正式生成時は場所だけでなく、gold・漢字正本の
固定bytes/SHA-256も一致しなければ停止します。`ESP_CORPUS_PATH` は固定manifestを生成した
cleanな京大HTML repoを指し、HEAD・branch・status・169文書の内容hashが一致しない場合は
書き込み工程の前に停止します。
漢字正本の既定位置は作者PCの絶対パスではなく、このrepoの親ディレクトリにある
兄弟フォルダとして解決します。正式工程は `_kanji_master_scope_manifest.json` を
再同期工程と旧互換パッチの双方へ渡し、各正本ファイルのbytes/SHA-256を工程途中でも再検証します。

## マスター更新への追従(監視ツール)
- audit_master_62k.py         … gold⇔E_stemのドリフト検出
- absorb_master_drift.py      … A型(マスター一体化)ドリフトのルビ吸収(CORPUS_SPLIT_KEEP除外つき)
- resync_kanji_master.py      … 漢字正本の全面再同期(単独実行可)
- audit_master_3lang_full_snapshot.py … 明示snapshot SHA・全行accounting・入力安定性を
  必須化した正式62K×3言語gate。正式一括生成はこれだけを使う。
- audit_master_3lang_fast.py  … moving absolute pathを読む`--monitor-only`高速診断。
  空白・約物等を除外するため正式証明には使用禁止。不一致時は非0終了する。

## コーパス(京大エス研HTML)すり合わせツール
- _corpus_full_audit.py       … 全文書の境界監査(コーパス⇔アプリ、gold裁定つき)
- cross_doc_inconsistency.py  … 同一語の文書間分解揺れ検出(固有名詞誤分解の信号)
- build_corpus_exact_manifest.py … 空白・拡張文字等を含む426表記のcase-sensitive exact固定
- build_corpus_reviewed_exact_manifest.py … 汎用規則後に残るevaluable表記を
  typed signatureと文脈注釈ごと固定（監査reportとclean corpus hashを照合）
- check_raw_apostrophe_structure.py … canonical化でASCIIと統合されるU+2019表記を
  raw visibleのまま3言語runtimeに通し、可視文字とruby/literal役割を全数検証
- check_canonical_corpus_surfaces.py … 169文書・348,971 rubyから得た
  evaluable 269,879件/21,443表記を3言語の配置済みruntimeで再描画し、reviewed
  628表記を含むtyped signature・可視文字・placeholder残留を残差0に固定
- `_strict_gold_reference_fixes.json` … no-worsening参照に残った辞書語を、
  case-sensitive・bounded・typed exact規則として参照hash付きで固定する。
  通常CSVにない略語・医学語・固有名片のJA/ZH/KO注釈は
  `apply_corpus_word_anno.py` の表記＋片位置限定グロスから生成し、同綴異義語へ漏らさない。

### 厳密な no-worsening / 全現状正解ゲート

`no_worsening_audit.py` は、文字列だけでなく `ruby/literal` の役割、大小文字、
ハイフン・空白を含む typed signature を比較する。複数語の固有名、略語、
Latin Extended を含む ruby も除外せず、全参照単位を評価する。

1. `verify_no_worsening_parser_equivalence.py` で独立 tokenizer と全169文書を照合する。
2. 固定した gold snapshot の SHA-256 を指定し、`--references-only` で候補を作る。
3. `_no_worsening_scope_manifest.json` と
   `_no_worsening_reference_conflicts.json` を人手裁定後に固定する。
4. `--current-only-diagnostic` で現行アプリの全誤りを先にゼロ化する。
5. 最後に JA/ZH/KO の3言語を省略せず実行する。

```powershell
$env:ESP_GOLD_PATH = '<監査済みsnapshot>'
$env:ESP_CORPUS_PATH = '<監査対象の京大HTML repo>'
$hash = '<snapshotのSHA-256>'
python _analysis_20260625/verify_no_worsening_parser_equivalence.py
python _analysis_20260625/no_worsening_audit.py --references-only --expected-gold-sha256 $hash
python _analysis_20260625/no_worsening_audit.py --current-only-diagnostic --languages JA --expected-gold-sha256 $hash
python _analysis_20260625/no_worsening_audit.py --languages JA ZH KO --expected-gold-sha256 $hash
# 長時間実行が端末上限で止まった場合のみ。完了済み言語のscope/HEAD/app入力/
# 監査コードhashが完全一致しなければfail-closedで拒否する。
python _analysis_20260625/no_worsening_audit.py --languages JA ZH KO --resume-language-results --expected-gold-sha256 $hash
```

各renderer checkpointはschema v2、参照投影はschema v5で、app全入力、参照、corpus HEAD/status、
gold、監査コード、review manifestのfingerprintが完全一致するときだけ再評価できる。
言語単位のresumeは、原子的に保存されたprefix言語のgateがPASSで、上記fingerprintと明示的に
互換指定した監査コードhashがすべて一致する場合だけ許可する。旧schemaや未検証の部分一致
checkpointを証拠として再利用しない。

## 品質原則
- ルビ=粗い一体(学習向け・日中韓で分解完全一致) / 漢字=偽分解尊重の深分解
- ルビの粗さの裁定者は京大エス研コーパス > 注釈ドラフト > gold
- 同長タイの言語間差は全体規則でなく単語ピン(confirmed)で直す
- -an-成員接尾の語はconfirmedでなくgen_replacement.pyのANリストへ(機構衝突回避)
- 固有名詞+対格n(afanti/n型)の境界はword_anno(wa)登録で発火する
- 語根CSVへ追加したら修正ガイド§7へも鏡映する
