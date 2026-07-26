# Phase 595 / 第71R 二軌道監査ログ（2026-07-26）

## 結論

この変更は、注釈ルビだけを次の2語で粗くする。

- `dinamismo`: `dinam/ism/o` → `dinamism/o`
- `elektrodinamismo`: `elektr/o/dinam/ism/o` → `elektr/o/dinamism/o`

学習者版マスターの偽分解、および漢字トラックの `dinam/ism` は変更しない。
日中韓のルビ境界は同一であり、漢字JSONには差分がない。

全偽分解行の自動吸収は行っていない。Phase 595 の粗ルビauthority
3,607行のうち、変更後も2,569行が未裁定であるため、全件昇格gateは
意図どおり `false` のままである。

## 固定入力

- app base HEAD:
  `e79a477f09980235d928246b4bfab7f3bc2ca542`
- learner master:
  - 62,313行
  - SHA-256
    `4B18BE755C4522678E6089CF68CB9F098E495293D9B6C68FCA706A530BCF5E6C`
- academic master:
  - 62,313行
  - SHA-256
    `63DAB5BAF932605A2D94843AD249FBE32CB1E8A40B8D244714A17744C0384261`
- fake-coarse candidate manifest:
  - 3,320 entries
  - file SHA-256
    `13E8D54C6E96B9DA3F61A3B99F7F23319BB5418C46733DB121AC6E00481E2810`
  - entries SHA-256
    `6621B58BE89A7442E0DC036612C5A9F09E4FA4A08F1D5A2E927BB2BAE2807FF7`

監査中の入力安定性は、gold、academic、HEAD、tracked worktree、
app runtime入力、監査コード、authority manifests、candidate files の
全項目で `true`。

## 根拠

- `dinamismo` の粗い正本は PEJVO original の `dinamism/o`。
- `elektrodinamismo` は PEJVO disagreement review で
  `elektr/o/dinamism/o` を採用済み（`paired_academic`）。
- 学習者版の `dinam/ism` は漢字割当用の偽分解として保持する。
- 表示幅を短くするための分解ではなく、語彙authorityに従った境界修正である。

## デプロイJSONの限定差分

JA・ZH・KOの各ルビJSONで、変更は各6 entryだけである。

- `dinamism`, `DINAMISM`, `Dinamism`
- `elektrodinamism`, `ELEKTRODINAMISM`, `Elektrodinamism`

各entryの old key、priority metadata、語形復元は不変。変わるのは
`dinam` と `ism` の2個のruby境界を `dinamism` 1個へ統合する部分だけ。

訳語は連結前後で意味を変えていない。

- JA: `力動` + `主義` → `力動主義`
- ZH: `动力` + `主义` → `动力主义`
- KO: `역동` + `주의` → `역동주의`
- `elektr` は既存どおり JA=`電気`, ZH=`电`, KO=`전기`

## 62,313行×3言語の正式監査

対象:

- 入力 62,313行
- コメント除外 202行
- runtime候補 62,111行
- runtime unique 61,844表層
- render union 62,305表層
- 旧fast subset 55,383表層

結果:

- JA/ZH/KO render-union境界不一致: 0
- full-exact境界不一致: 0
- legacy-fast境界不一致: 0
- token context境界不一致: 0
- runtime error: 0
- visible reconstruction failure: 0
- placeholder残留: 0
- empty `rt`: 0
- empty `rb`: 0
- unknown width character: 0

実効CSS表示幅の最大比:

- JA: 1.533750021457672
- ZH: 1.366875010728836
- KO: 1.1043750286102294

いずれも「元アルファベット幅のおおむね2倍以内」を満たす。
文字数比やCSS縮小前のraw比だけで境界を変更していない。

## 基準版との差集合

全言語で同一:

- coarse matched: 1,036 → 1,038
- coarse mismatched: 2,571 → 2,569
- removed mismatch:
  - learner line 6,889 `dinamismo`
  - learner line 8,902 `elektrodinamismo`
- added mismatch: 0
- reviewed transition: 157/157のまま

したがって、この変更で改善したauthority surfaceは上記2語だけであり、
他の未裁定2,569行を暗黙に正しいとは扱わない。

## 監査成果物

完全レポートは大容量のためGitへ重複格納せず、ハッシュで固定した。

- baseline report:
  - `D:\tmp\esperanto_stage_20260726_phase595_audit\phase595_full_3lang_report.json`
  - 8,357,094 bytes
  - SHA-256
    `F37204F41A74F20BE584DF535053274F2976E26FCC360851877B7CDF3418A7DA`
- candidate report:
  - `D:\tmp\esperanto_stage_20260726_phase595_audit\phase595_r71_dinamism_full_3lang_report.json`
  - 8,352,697 bytes
  - SHA-256
    `406A2F43BE513AF1C7B4C17064CEFAB26C4B33E5B001AF6CFFFBB892B437751A`
- candidate stdout:
  - 13,823 bytes
  - SHA-256
    `F87A34671AB4D3CCB4202CBD54CC48A5FA2297E3B5CC7D7E8592339BF457FC76`
- candidate stderr:
  - 550 bytes（GitのLF/CRLF予告のみ）
  - SHA-256
    `3CE8EF396FA1E5B4F9222C05224736732E5202678E66A5ECA62FA5F2F2FD2EEC`

## 回帰ゲート

- `python -m unittest _analysis_20260625.test_generation_regressions -v`
  - 60/60 PASS
- `python _analysis_20260625/check_multilingual_structure.py`
  - JA/ZH/KO各572,356 global rules
  - duplicate old key 0
  - keyed R/L/PAD structure diff 0
- `python _analysis_20260625/anomaly_scan.py`
  - Ruby/漢字の6 JSONすべて異常0
- `python _analysis_20260625/test_reviewed_exact_manifest.py -v`
  - 5/5 PASS
- `python _analysis_20260625/check_kanji_fake_decomposition.py`
  - JA/ZH/KO各53件、mismatch 0
- `python _analysis_20260625/check_kanji_structure.py`
  - 3言語 source保持・duplicate 0・pure derivation diff 0
- `python _analysis_20260625/check_raw_apostrophe_structure.py`
  - pinned corpus `b769038ef15346a536ce93721d6f0f46849db0ea`
  - 27 surfaces / 41 instances / 3 languages、failure 0

## 別キュー（この変更へ混ぜない）

- Phase 597 は Phase 595 後に動いた別snapshotであり、自動吸収しない。
- `Temis` は女神名と普通動詞過去形の同綴衝突。globalな
  `Temis → Tem/is` は禁止し、確認済み実文だけの文脈限定ルールを別審査する。
- 神学語の `di` がRubyで「二」と表示される意味衝突を発見した。
  科学接頭辞 `di-` は「二」が正しいため、神学語だけを語別に別審査する。
- 京大HTMLの `iniciatoro` 1件は `iniciator/o` が正しいが、
  appの旧no-worsening conflict ledger同期を済ませてから別commitにする。
- 未裁定fake-coarse 2,569行は、通常語を固有名詞より優先し、
  authority・意味・近傍負例を1件ずつ確認して縮める。
