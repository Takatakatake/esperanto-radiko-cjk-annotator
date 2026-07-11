# 道B: 大JSON再生成パイプライン(正式ルート)

このディレクトリには、3言語アプリの置換用大JSON(ルビ/漢字/純粋置換)を再生成する
**唯一の正式ルート**が収録されています。アプリ内の旧「JSON生成ページ」は
最新の品質修正を含まないため撤去されました。

## 一括実行
    python _analysis_20260625/regenerate_all.py

実行順(2026-07-06版):
1. apply_confirmed_now.py 30 --write … 確定リスト適用+ルビ3言語再生成
2. fix_ruby_postregen.py            … ルビ事後修正(偽の友グロス等)
3. resync_kanji_master.py --write   … 漢字マスター正本と全面再同期(CSV 7,666語根+word_kanji 43k語形)
4. apply_kanji_now.py --write       … 漢字3言語再生成(偽分解尊重の深分解)
5. fix_kanji_2890.py --apply        … 旧安全網(resync後は実質no-op・互換のため維持)
6. derive_pure_kanji.py             … 純粋置換版JSON再導出(忘れると陳腐化する成果物)
7. anomaly_scan.py                  … 6JSON異常スキャン(逆転/破損/番兵/hat)

## 構成
- gen_replacement.py      … 置換リスト生成の中核(AN/ONリスト等の拡張点を含む)
- out/confirmed_tier30.json … 単語レベルの分解確定リスト(語根分解のピン, 約580行)
- out/word_anno_*.json      … 言語別の語ごと注釈上書き(固有名詞等)
- out/kanji_root.csv / word_kanji.json … 漢字マスター正本からの派生(resyncが再構築)

## 生きた正本(いずれも更新が続く。編集禁止・読むだけ)
- 語根分解: `エスペラント辞書徹底語根分解_20260630\`
  (学習者版=gold深分解 / 日中韓注釈版ドラフト=ルビ粗分解)
- 漢字割当: `エスペラント語根＿漢字割り当て＿20260630\`
  (_kanji_map_master.tsv + _identifier_sidecar.tsv + 漢字注入_学習者版)
外部環境では ESP_GOLD_PATH / ESP_KANJI_MASTER_PATH 環境変数で場所を指定できます。

## マスター更新への追従(監視ツール)
- audit_master_62k.py         … gold⇔E_stemのドリフト検出
- absorb_master_drift.py      … A型(マスター一体化)ドリフトのルビ吸収(CORPUS_SPLIT_KEEP除外つき)
- resync_kanji_master.py      … 漢字正本の全面再同期(単独実行可)
- audit_master_3lang_fast.py  … マスター全55k語×3言語の分解一致 全数監査(約10分)

## コーパス(京大エス研HTML)すり合わせツール
- _corpus_full_audit.py       … 全文書の境界監査(コーパス⇔アプリ、gold裁定つき)
- cross_doc_inconsistency.py  … 同一語の文書間分解揺れ検出(固有名詞誤分解の信号)

## 品質原則
- ルビ=粗い一体(学習向け・日中韓で分解完全一致) / 漢字=偽分解尊重の深分解
- ルビの粗さの裁定者は京大エス研コーパス > 注釈ドラフト > gold
- 同長タイの言語間差は全体規則でなく単語ピン(confirmed)で直す
- -an-成員接尾の語はconfirmedでなくgen_replacement.pyのANリストへ(機構衝突回避)
- 固有名詞+対格n(afanti/n型)の境界はword_anno(wa)登録で発火する
- 語根CSVへ追加したら修正ガイド§7へも鏡映する
