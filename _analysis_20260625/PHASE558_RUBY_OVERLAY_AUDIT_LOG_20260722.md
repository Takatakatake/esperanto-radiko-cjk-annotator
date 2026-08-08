# Phase 558 注釈ルビ側車・最終捜査ログ

記録日: 2026-07-22 JST

## 1. この記録の位置づけ

この記録は、Phase 532〜537 の約6時間の捜査をまとめた
`PHASE532_537_CONSOLIDATED_AUDIT_LOG_20260718.md` の続編である。
今回の主眼は、動き続ける62,000語超マスターの Phase 558 凍結点から、
注釈ルビ側で明示裁定した5項目だけを三言語同時に安全採用することである。

作業は実ワークスペースへ直接書かず、次の独立cloneだけで行った。

- app clone: `D:\tmp\codex_app_phase558_overlay_candidate_20260721`
- branch: `codex/phase558-ruby-overlay-candidate`
- 作業開始HEAD: `dcfca809b711075788ee00b6323cdd2ea31618ff`
- corpus current clone: `D:\tmp\codex_corpus_e373378_audit_20260721`
- corpus current HEAD: `e37337822cf31529ba50b8534227721e4ec39a38`

## 2. 固定原則

1. 注釈ルビは京大エス研HTML程度の粗さを基準とする。
2. 漢字化は別軌道で、必要な偽分解・過細分解を尊重する。
3. 注釈ルビのEsperanto原文上のRuby/literal境界はJA/ZH/KOで完全一致させる。
4. JA/ZH/KOの訳語本文は同一文字列にはしない。各言語固有の裁定訳語を使う。
5. ルビ幅は原アルファベット幅のおおむね2倍以内を表示ゲートとする。
6. 幅を短くするために語根を細分化しない。
7. 動くマスターを直接認証しない。学習者版と学術版を同一Phaseで凍結し、SHA-256で固定する。
8. 広い候補を一括採用せず、裁定済みの閉じた範囲だけを採用する。

このため、ルビ側の総合gateが通っても、広いPhase 558マスター候補のpromotionは
自動的には通らない設計である。

## 3. 凍結入力

### 3.1 Phase 532 親

- directory: `D:\tmp\esperanto_stage_20260718_phase532_candidate`
- 学習者版 SHA-256: `6B403AA30BBCBBA4C9E41A2CF48D1AD2FC1D5A5DB1154CAF1260A361566E3226`
- 学術版 SHA-256: `FE632820E7752A555787C926C0A843CD82B2F79D4177A6D8D1E9622CA96393A5`

Phase 532 の差分基準は
`D:\tmp\esperanto_stage_20260715_phase513` である。

### 3.2 Phase 558 候補

- directory: `D:\tmp\esperanto_stage_20260721_phase558_audit`
- 学習者版: 62,313行、4,373,188 bytes
- 学習者版 SHA-256: `21D8B88C79D8D1E45A23CF9987006688EB0308084652AE50FFA2ED337215E4D4`
- 学術版: 62,313行、4,277,592 bytes
- 学術版 SHA-256: `6BAF43D0A2981B0ED48A576178991B48A33AF9AFCA9795D8ED213B2FD460FCFB`

外部裁定物は次の値で固定した。

- fake/coarse candidate SHA-256: `6C72C51EF8DB434E62D614D58CB5A9DB0D55352A642576BEC30B523C4F420D15`
- transition dispositions SHA-256: `35F1531BAC29B4842CED0F1F7E6FC1F5D588349FBF6A51D3BDCBA4EA533AF9A2`
- Ruby軌道裁定台帳 SHA-256: `F1810CDA6B801DADC445380A48D6C35A30D29982960A0707166763D0DCC85708`

### 3.3 京大エス研修正ガイド

- 日本語ガイド SHA-256: `2B678BFCA362A359BD4367C8C869E1ECAEFF497812937AFD15F4D6A14DD80284`
- 中国語ガイド SHA-256: `992FE8E84244BA5AD4BF9B98706E52F74D32398FF6D0B5D2D226FA448028F953`

いずれも corpus `e373378...` clone 内のユーザー指定ファイルを直接使った。
監査中に凍結入力・ガイド・台帳・app入力・監査コードの開始/終了SHAを比較し、
全項目が不変だった。

## 4. Phase 558で採用した注釈ルビ裁定

| 表層 | 注釈ルビ側 | 種別 |
|---|---|---|
| `kateĥismo` | `kateĥism/o` | 生産的Ruby-only |
| `kateĥisto` | `kateĥist/o` | 生産的Ruby-only |
| `magnetito` | `magnetit/o` | 完全一致・大小文字限定 |
| `Izraelio` | `Izrael/io` | 完全一致・大小文字限定 |
| `tia-tia` | `tia/-/tia` | 完全一致・大小文字限定 |

`monarĥio` と `oligarĥio` は粗い注釈ルビのまま保護した。
漢字側の偽分解指定を、この判断によって削除・粗化していない。

5つの裁定行と、生成payload上の展開形は別に数える。

- 生産的規則: 2
- 語尾: 10 (`a, aj, ajn, an, e, en, o, oj, ojn, on`)
- 大小文字形: 3 (`lower, initial, upper`)
- 生産的展開: 2 × 10 × 3 = 60
- exact形: 3
- payload展開形合計: 63
- `tia-tia` はRuby注釈を2つ持つため、実`rb/rt`注釈数は各言語64

境界manifest SHA-256は
`5971B203E379C8F7D3AD07C13E9A34480C071E9EA113B2DF36B2C32327DB5A35`、
訳語manifest SHA-256は
`77F2FD0EB8F87B59DFBDD041ADCFBF2B9BFD6D3DB34BEBCCB27FFA99CCB546F0`
である。

## 5. 独立レビューで見つけ、commit前に塞いだ穴

最初の62K監査は総合gateを通ったが、その後の独立レビューで、
現行データの誤りではなく監査器の将来耐性に4点の不足を見つけた。
そのため最初の結果を最終認証に使わず、補強後に全件監査をやり直した。

### 5.1 無悪化監査のsource絶対封印

旧ゲートは差分分類を厳しく見ていた一方、参照source集合の丸ごとの欠落を
絶対件数で封印していなかった。schema v2で次を固定した。

- 必須source: 9種の完全一致集合
- parent-current
- full data-isolated
- full comprehensive
- current-e373
- 各profileのsource絶対統計の正準SHA-256
- combined絶対統計
- `combined == sum(sources)`
- sourceの欠落、余分、ゼロ化、総数改変、combined改変を全てfail-close

sidecar manifest SHA-256:
`7468D660EC39089E9F931BE9F79BF45D0AD5DFEC38F6281651F489D94FAE7FBA`

### 5.2 63形の三言語`rt`本文ゲート

旧ゲートは63形のRuby/literal境界を見たが、同じ境界のまま誤訳された`rt`を
直接は拒否しなかった。補強後は実ランタイムで81ユニークprobeを描画し、
63形について次を同時に検査する。

- typed boundary
- `rb`本文
- JA固有`rt`
- ZH固有`rt`
- KO固有`rt`
- 三言語の`rb`一致
- payloadを描画後に再読込し、semantic hashとapp fingerprintを再比較

同じ境界のままZHの`magnetito`訳だけを誤らせる変異試験は、
新しい訳語ゲートで正常に拒否された。

### 5.3 長時間監査中のdirty worktree不変性

未commit状態ではHEADだけを比較しても監査コードの途中編集を検出できない。
runnerは、`_analysis_20260625`直下の全Python/JSON入力と、三言語の配信app入力を
開始時・各raw audit前後・各sidecar後・全終了時に再ハッシュするようにした。
途中改変の故障注入試験はsidecar実行前にfail-closeし、checkpointを証拠として残す。

### 5.4 rollback登録順

三言語6ファイルtransactionで、rollbackコピーが置換された直後の検査例外でも
残骸を回収できるよう、コピー前にrollbackパスをcleanup対象へ登録した。
コピー後検査失敗を注入し、原本6ファイルのbytes不変とtransaction残骸0を確認した。

## 6. 補強後の62,313行・三言語全件監査

正式報告:
`_analysis_20260625/out/_audit_master_3lang_phase558.json`

- report SHA-256: `67A4BD932738D3A23DCA0EADCF2225F410869193E6809A56B036D10E0DFCF8ED`
- report bytes: 8,403,571
- `complete`: true
- top-level `gate`: true
- 入力行: 62,313
- コメント除外: 202
- runtime候補行: 62,111
- runtime固有表層: 61,844
- legacy範囲を含む描画union: 62,299
- 旧fast範囲: 55,383
- 未評価候補行: 0

### 6.1 三言語境界

- render union mismatch: 0
- full exact mismatch: 0
- full exact line occurrence mismatch: 0
- legacy fast mismatch: 0
- token context mismatch: 0

### 6.2 三言語の実行・HTML構造

JA/ZH/KOの各言語で、次は全て0だった。

- runtime errors
- visible failures
- placeholder residuals
- empty `rt`
- empty `rb`
- zero-token outputs

### 6.3 63形の境界と訳語

- 5裁定行: mismatch 0
- 28近傍scope guard: mismatch 0
- 63 payload形: boundary mismatch 0
- 63 payload形: `rt` mismatch 0
- 各言語64注釈
- 三言語`rb` mismatch 0
- deployed snapshot revalidated: true

配信payloadのsemantic SHA-256:

- JA: `5F75AA77ED9F3EE79DF127365B2FF7467814DFCFA9DC071E78725C497C26239F`
- ZH: `15F0AC59964CB4571502B0B2F3D3073A9B67E727B8F3FEDA855D8B9C337B0D6F`
- KO: `A49AE00521C08C885A9B51A3D8A8B2B9E575247C4E044E6D7B7545765AC5DB9C`

### 6.4 ルビ幅

三言語の `char_widths.json` は同一で、SHA-256は
`AC009C26AF1D7FAE05E8969D86042B5BAFF5F482B226C575E1CEF8D27AEA2C7B`
だった。

| 言語 | CSS実効幅>2 | 未知文字 | 未知CSS class | 最大CSS実効幅比 |
|---|---:|---:|---:|---:|
| JA | 0 | 0 | 0 | 1.5337500215 |
| ZH | 0 | 0 | 0 | 1.3668750107 |
| KO | 0 | 0 | 0 | 1.1043750286 |

raw幅比は長い注釈のreview指標として2を超え得るが、改行と実CSS classを適用した
最大行の実効幅比は全件2以下である。raw幅や実効幅は分解を変更しない。

### 6.5 二軌道の非混同

広いfake/coarse authorityは3,563行で、各言語とも次の結果だった。

- matched: 986
- mismatched: 2,577
- 裁定済みtransition: 157
- transition matched: 157/157

2,577は隠された失敗ではない。深い/偽分解を含むマスター候補と、
粗い注釈ルビの差を報告する未裁定キューである。
`--enforce-all-fake-coarse` は意図的に使わず、一括採用を防いだ。

- Ruby側の5裁定 adoption gate: true
- 広いPhase 558 master promotion: false
- `monarĥio`, `oligarĥio`: 粗いまま
- 未裁定のouter-ik群、`termoreguligilo`, `atletiko`等: promotion blockerとして保持

## 7. 無悪化監査

### 7.1 parent current-only

- file: `_analysis_20260625/out/_audit_no_worsening_current_only.json`
- SHA-256: `0F03B1A8697750749F75892758CA214A0AD5F8D6A23FEF093F1A2EDDE6B6C4D9`
- raw audit: complete=true / gate=false
- sidecar: gate=true
- 9 source総重み: 323,527
- reference alignment improvements: 3
- reviewed expectation replacements: 2
- unadjudicated findings: 0
- trilingual mismatches: 0

raw gate=falseは、`Izraelio`と`tia-tia`の新しい裁定が旧参照と異なるための
予期済み結果である。sidecarがこの2表層だけを閉じた例外として認証する。

### 7.2 full old-to-new

- file: `_analysis_20260625/out/_audit_no_worsening.json`
- SHA-256: `2FDA0DCA9C288907021689C95490E0607053C7ACCD9CC7D52EA13F7B39747AAA`
- raw audit: complete=true / gate=false
- sidecar: gate=true
- 各言語・各比較の総重み: 323,527
- baseline correct: 323,527
- current correct: 323,525
- signature changes: 2 (`Izraelio`, `tia-tia`)
- unadjudicated signature changes: 0
- trilingual signature delta mismatches: 0
- trilingual runtime mismatches: 0

### 7.3 current corpus e373

- file: `_analysis_20260625/out/_audit_no_worsening_current_e373.json`
- SHA-256: `7828580B8F2FE2D89BEC3B2240EB3FEC5E0EC42BDF1648497D835E463D00FFAE`
- raw audit: complete=true / gate=false
- sidecar: gate=true
- corpus HEAD: `e37337822cf31529ba50b8534227721e4ec39a38`
- formal content HTML: 169 files
- HTML unit weight: 271,065
- HTML mismatches: 0
- unadjudicated findings: 0
- trilingual mismatches: 0

## 8. 京大エス研HTML corpusの判断

repository内のHTMLは172ファイルで、正式content scopeは169ファイルである。
残る3ファイルはindex/navigation系であり、本文content監査の対象外である。

current e373の正式169ファイルについて、Ruby HTML 348,971個を全てparseし、
271,065 unitを参照へ照合した。除外unit 0、HTML mismatch 0だった。
corpus content SHA-256は
`9AC90579B5A935FCDF432BB0CC37CA6D6A0131A5049CFD4215B69FC7F6C369C6`
である。

したがって今回、corpusへ意味のない追加編集や空commitを作らない。
corpus mainは既に監査対象の`e373378...`でcleanであり、追加修正を正当化する
不一致は見つからなかった。app側の汎用修正だけをcommit対象とする。

## 9. 漢字化軌道の保護

次の9出力を作業開始HEADと比較し、全て差分0だった。

- 三言語 `世界语词根-汉字对应列表_参照2新割当_7791.csv`
- 三言語 `置換リスト_漢字.json`
- JA `置換リスト_漢字_純粋置換.json`
- `_analysis_20260625/out/kanji_root.csv`
- `_analysis_20260625/out/word_kanji.json`

代表SHA-256:

- 漢字CSV / `kanji_root.csv`: `3BEF29AC615F5B3F5FA267D27C78919E87BB7B97075B249F9833CBD05C03E6EC`
- 三言語漢字JSON: `DF0E05AE9242A2CF5690CECE61E214DCBBEC12E1479EC2E8F7AFFDBB1CB7275D`
- 純粋置換: `F92A1D831C4CEC900AAD3E00969C6804F3897B4741097766BFCCBBAD148A465B`
- `word_kanji.json`: `2BD570963A1A8390E1C4FE4FA629696FD4AEDB27B39446BA2A443275C39B09A3`

注釈ルビの粗化が漢字化データへ流入していない。

## 10. 回帰・故障注入試験

補強後に次を再実行した。

- `test_generation_regressions.py`: 59/59 PASS
- `test_phase558_ruby_overlay.py`: 20/20 PASS
- `test_phase558_no_worsening_sidecar_gate.py`: 22/22 PASS
- `test_run_phase558_no_worsening.py`: 8/8 PASS
- `test_no_worsening_audit.py`: 35/35 PASS
- `test_phase532_ruby_policy.py`: 18/18 PASS
- `test_reviewed_exact_manifest.py`: 5/5 PASS
- `test_canonical_corpus_surfaces.py`: 5/5 PASS
- `check_multilingual_structure.py`: PASS
  - 各言語global rules: 571,007
  - duplicate: 0
  - old set diff: 0
  - keyed R/L/PAD structure diff: 0
- `check_canonical_corpus_surfaces.py`: PASS
  - b769固定169文書
  - canonical surfaces: 21,443
  - residual language surfaces: 0
  - visible failures: 0
  - placeholder residual surfaces: 0
  - report SHA-256: `6F52E8F86DB34F46CE526083DE519778315662268EDD5200FF071D38C3ADA2F2`
- `check_raw_apostrophe_structure.py`: PASS
  - b769固定169文書
  - U+2019原表記: 27表層 / 41 corpus出現
  - JA/ZH/KO failures: 0
- Phase 532 deployed runtime: 58/58、三言語不一致0、gate=true
- Phase 558 deployed runtime: 63形、各言語64注釈、境界/訳語不一致0、gate=true
- 変更対象Python: 20本を`py_compile`、PASS
- 変更対象JSON: 23本を実行環境と同じPython parserで読取、PASS
- `git diff --check`: PASS
- transaction/checkpoint一時残骸: 0
- 漢字保護9ファイル: HEADとの差分0

canonical/apostropheゲートへ現行e373を誤って渡した試行は、期待するb769
HEAD/content SHAと異なるため正常にfail-closeした。正式結果には、指定どおり
b769 clean cloneで再実行してPASSした値だけを採用した。

## 11. 捜査ログの保存状態

前回の約6時間捜査は、次の恒久ログに統合して残っている。

- `_analysis_20260625/PHASE532_537_CONSOLIDATED_AUDIT_LOG_20260718.md`

今回の証拠は本ファイルと次のJSON群に残した。

- `_audit_master_3lang_phase558.json`
- `_audit_no_worsening_current_only.json`
- `_audit_no_worsening.json`
- `_audit_no_worsening_current_e373.json`
- `_audit_canonical_corpus_surfaces.json`
- `_phase558_ruby_overlay_review.json`
- `_phase558_ruby_overlay_activation.json`
- `_phase558_no_worsening_sidecar.json`
- `_phase558_current_corpus_scope_manifest.json`

端末の全スクロールをそのまま保存した生ログではないが、入力SHA、報告SHA、
裁定、全件数、gate、再実行入口を恒久化しているため、同じ凍結入力から再現できる。

独立レビュー前の最初の62K報告はSHA-256
`C7AA61FE2381384C9011862E033D21BAB584FB8013FB6534DD4F8F75EE02E580`
だった。この中間報告は総合PASSだったが、訳語・絶対source封印の補強前なので
正式認証から外し、補強後の`67A4BD...CF8ED`で上書き再認証した。

## 12. 限界と次の境界

今回証明したのは、凍結Phase 558の62,313行が三言語runtimeで構造的に処理でき、
境界・表示・幅が一致し、選定5裁定の三言語訳語が閉じていること、ならびに
京大HTML参照を悪化させていないことである。

62,313行の全訳語を人手で一語ずつ意味監査した、という主張はしない。
また、Phase 558より後に進んだlive masterは今回の認証対象ではない。
2,577件のgeneric fake/coarse差を一括で注釈ルビへ採用してもいない。

今後live masterを吸収する場合は、静止点を新しく凍結し、累積差分を裁定し、
同じ三言語境界・訳語・幅・無悪化・入力不変ゲートを再実行する。

## 13. commit / push記録

実装commit: `adc2982ad8d7953cc364b2a7a2e278b1d87daafe`
（tree `ba47c79fb02176ed364e3f03b769f33dfb04ba80`）。

監査ログ確定commit: 上記実装commitの直後に、本節の確定だけを独立commitとする。

push前確認時点でapp origin/mainは作業開始点
`dcfca809b711075788ee00b6323cdd2ea31618ff`のまま、corpus origin/mainは
`e37337822cf31529ba50b8534227721e4ec39a38`かつcleanだった。appはこの記録の
確定commitまでをfast-forwardのみでpushし、corpusは不一致0のため無変更とする。
