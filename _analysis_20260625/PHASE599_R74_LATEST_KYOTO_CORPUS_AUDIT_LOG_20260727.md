# Phase599 / R74 最新京大コーパス整合監査ログ

監査日: 2026-07-26～27 JST
作業ブランチ: `agent/r74-latest-kyoto-corpus`
親HEAD: `3f338920f59efd80333616af6192e0f099c3d07c`（R73）
状態: 隔離worktree。app `main`への直接commit・push・mergeなし。
京大HTMLの隔離PR #6は監査後にremote側でmergeされ、corpus `main`は
`d1642c276857c1fe400a6d597214ff7a923e7bd2`となった。
app remote `main`も別系列で`b4392fd02bb8b16ebcd13bea9a8088332e7f0d8a`へ進んだため、
R74の再現可能性を守って親R73を途中rebaseせず、moving mainは別監視とした。

## 1. 監査原則

1. 注釈Rubyは京大エス研HTML級の粗い分解を採る。
2. RubyのR/L境界はJA・ZH・KOで完全一致させる。
3. 漢字トラックは学習者版マスターの偽分解・過細分解を保持する。
4. 幅はArial 16の文字幅と実CSSで実効2倍以内を検査するが、幅を縮めるために
   語根境界を細分化しない。
5. 固有名詞より既存の普通エスペラント語を優先する。
6. moving masterを途中で吸収せず、固定snapshot単位で監査する。
7. 京大HTMLと2ガイドは既に磨かれた基準資料として読み取り専用で扱い、
   自動修正・一括整形をしない。

## 2. コーパスauthority

| 役割 | path | HEAD | content SHA-256 |
|---|---|---|---|
| 歴史親 | `D:\tmp\codex_corpus_pinned_b769_20260726` | `b769038ef15346a536ce93721d6f0f46849db0ea` | `264E4217BE484ABC2DC5EF7A22D83C56076C255BFB389F8218A0C215DD2420B6` |
| 不変比較基準（旧main） | `D:\tmp\codex_corpus_remote_7c04f97_audit_20260726` | `7c04f97c51a7cecf88918d2abc2e6bf2f34601a6` | `4F04FD2F3DBE0FC79909CBBEA61ED2848FC093AE2DFE3F0ADEB79882AEB04F52` |
| 現行remote main | `D:\tmp\codex_corpus_iniciator_candidate_20260726` | `d1642c276857c1fe400a6d597214ff7a923e7bd2` | `C8CAA1940F7F4685CE317B4107E9AA36AF28CBC47A06630CD24092D3C045BE1B` |

ユーザー指定の二つの最新ローカルrepositoryは、監査開始時にはいずれもcleanな
`main...origin/main`、HEAD `7c04f97`、同一remoteであることを確認した。
その後remote `main`が上記d164へ進んだことを`ls-remote`とfetchで再確認した。
exact/reviewed manifestの`source.branch`は取得時の来歴であり、意味的identityは
HEAD・clean status・本文content hashで固定する。したがって同じd164をcleanな`main`で
checkoutしても監査結果は変わらない。

### b769→7c04

- 全path 172、本文HTML 169。追加・削除・renameなし。
- raw Ruby `348,971 → 348,581`（-390）。
- -390は同一重複ブロックの削除（JA -195、KO -195）で、固有内容の消失ではない。
- その他は綴り修正15件と注釈追加2件。
- 共通canonical 21,433表記のtyped option set変更0。
- 非アプリexact manifestは426表記・1,186出現・420注釈で不変。
- U+2019は27表記・41出現・27 optionsで不変。
- 実行結果:
  `PASS corpus transition b769038->7c04f97: 172 paths, 169 content files,
  ruby -390, spelling 15, annotation 2, unexplained 0`

### 7c04→d164

変更は1ファイル・`iniciatoro` 1件だけ。

- 旧: `R:iniciat|R:or|L:o`
- 現行: `R:iniciator|L:o`
- bare projectionは完全同一。
- reviewed-exactは旧628表記から、最新版で綴り訂正された
  `bonŝanĉulo`・`fronantaj`・`jurnal` だけを退役し、625表記。
- active HTML corpusのsemantic wrongは0。
- コーパス変更はDraft PR #6に隔離してpushした。2026-07-26 23:11 JSTに
  remote側でmergeされ、現在のcorpus `main`と隔離worktree HEADはともにd164。
- 7c04→d164で2冊のガイドはバイト不変。

## 3. 最新ガイドの読み取り専用監査

最新2ガイド:

| guide | bytes | SHA-256 |
|---|---:|---|
| `エスペラントルビHTML修正ガイド260328.txt` | 131,181 | `B8F21605E019A394560A6E4ED5238FE4BEDE7B2A949A0CBC6927189ADADFB965` |
| `世界语HTML修正指南_中文注释版.txt` | 118,657 | `A3AF2F18004A63A2C6ECB438B9ABBABF62A9B40D15494FC6B6FC0CADA7ECEA46` |

- b769→7c04差分は +452/-101。
- G8 layout/translation checker追加が中心。
- `translation_marking_checker.py --require-zero`: 違反0。
- Ruby semantic差の代表 `ĵus`: JA `たっ<br>た今`、ZH `刚才`、KO `방금`。
  三言語とも境界 `R:ĵus`。
- CSS verifierのraw mismatch 551は全件margin境界skip、`fixable=0`。
- ガイド・HTMLのauto-fix、payload edit、commit、pushはいずれも0。
- 実行結果:
  `PASS latest Kyoto guides b769038->7c04f97: +452/-101 classified;
  active d164 byte-identical; G8 violations=0;
  JA CSS boundary-skip=551/fixable=0`

## 4. Phase599 `Temis` 文脈限定補正

文頭の動詞 `Temis` は `tem/is` だが、表層だけで全域分解すると女神名等を壊す。
そのため京大HTMLに実在する次の完全一致5句（6出現）だけを採用した。

1. `Temis tamen pri aparatoj`
2. `Temis pri tre noveca`
3. `Temis pri la volo`
4. `Temis pri la distrikto`
5. `Temis pri malnovaj`（2出現）

各言語5行、全域Ruby rows `572,501 → 572,506`。

- 正例15 language-cases: 全件 `R:Tem|R:is`。
- 負例18 language-cases: 裸 `Temis`、`Temiso`、`TEMIS`、女神文脈、
  語順・句読点違いを全件不変。
- JA/ZH/KOの境界とrb列は完全一致。
- 最大実効幅比: JA/ZH `0.8303`、KO `0.7642`（上限2）。
- 再適用時 `writes_required=0`。
- 漢字トラック非介入: true。

Phase600を後段に配備した最終状態は572,558行/言語。Phase599の再監査は
後発52行を一時的に正規化して同一順序で復元し、歴史状態572,501行、
Phase599中間572,506行、最終572,558行を全て再現した。
最終deployed auditはpositive 15 language-cases、negative 18、
後発52行保存、`writes_required=0`、JA/ZH/KO境界・rb不一致0。

Phase600の閉集合は各言語52行:

- `glu-glu-glu` を七面鳥の鳴き声として一体Ruby化。
- lowercase `nor` 1形。
- `nor-adrenalin` / `nor-epinefrin` 2語幹×8語尾×3大小形の48形。
- `kuku-nor` / `lob-nor` の2 exact guard。

正例50・負例21、三言語境界・rb不一致0、Kanji変更0。
最大実効幅比はJA 1.1985、ZH 0.8683、KO 1.1030で全て2未満。
幅を縮めるための分解追加は行っていない。

## 5. 漢字トラック不変

R74はRuby-onlyであり、次のKanji payloadは親HEADとバイト同一。

| 言語 | `置換リスト_漢字.json` SHA-256 |
|---|---|
| JA | `92EE01E3C78D84A726D611F60B0068C0BFA764518795E447D503C11C9ECC06D6` |
| ZH | `A0F9881BD10404C8DA92FA3458DB01DB2D77262A8AD0EE81BB8949D5C8698C77` |
| KO | `90E838156C7009B6C950E409EE84CD74DA086BA89B72F32B0C0E27E2E6D9B2EF` |

CSV 3本、JA pure-Kanji、`out/kanji_root.csv`、`out/word_kanji.json`を含む
保護9成果物にも変更を許可しない。

## 6. 62,313行マスターとmoving master

R74の固定authorityはPhase597。

| 版 | bytes | rows | SHA-256 |
|---|---:|---:|---|
| 学習者Phase597 | 4,373,830 | 62,313 | `9A610D086E60A1863E1D59D61FE0F844B3EACF4DCEBDBF6AE6354E0D16D99700` |
| 学術Phase597 | 4,277,601 | 62,313 | `63DAB5BAF932605A2D94843AD249FBE32CB1E8A40B8D244714A17744C0384261` |

2026-07-27 07:13 JST時点のlive masterはPhase608へ進んでいる。

| 版 | bytes | rows | SHA-256 | Phase597比 |
|---|---:|---:|---|---|
| 学習者live | 4,374,545 | 62,313 | `B961606244AD42941A4D542C807A1D1E5ABEB57BC0D58F2190E27451DD4422EB` | 35行置換、+715 bytes |
| 学術live | 4,277,597 | 62,313 | `A70935B989747E5D941C9BF9E40F03965F60F35FA84E0CF7EDF9483427F87D14` | 4行置換、-4 bytes |

追加・削除行および定義本文変更は0。差分は語根境界・偽分解marker調整。
Phase534の5件
`igvanodont/anodont/diodont/megaterio/pteranodonto` は、学習者版の深分解と
学術版の粗分解を含め、Phase597・liveの双方で全文字同一。

Phase597→liveの変更は34見出し（learner 35行、academic 4行）。
learnerは境界変更31行、marker記載変更33行で、
`##偽分解` 3,608→3,634、`##過細分解` 686→690、
`##エス的分解` 93→93。academicのmarker増減は0。
`atletiko` も両版で `atlet/ik/o:運動競技;【運】陸上競技` のまま不変。

34見出しはPhase598 4、599 1、600 1、601 5、603～604 9、
605 2、606 1、607 3、608 8へ由来別に分離した。
R74完了前にPhase608を混ぜず、次回pin更新ではこの34見出しを個別に
Ruby粗分解／Kanji偽分解へ裁定してからregenする。

## 7. 回帰試験

- latest transition / reviewed exact / bare / boundary transition:
  30 tests PASS（skip 3）。
- Phase599 / Phase600 / R67-R68 transaction:
  37 tests PASS（skip 2）。
- current/historical no-worsening:
  46 tests PASS（skip 1）。
- canonical / latest guide / R74 pipeline:
  23 tests PASS。
- Phase597 successor: 18 tests PASS。
- `py_compile`: PASS。
- `git diff --check`: PASS。

skipは実コーパス環境未指定等の明示的integration skipであり、失敗ではない。

## 8. 長時間正式ゲート

- canonical 21,438表記×JA/ZH/KO: PASS。
  - content 169、raw/parsed Ruby 348,580、units 270,763、
    evaluable 269,577、reviewed 625。
  - raw contextual residualは `Temis` の3 language-surfacesだけ。
  - Phase599台帳で3件を明示的にadmitし、未裁定残差0。
  - visible failure 0、placeholder residual 0。
  - algorithm SHA-256:
    `E1DE302311B3DD60F0B156B9541938AC50A1448B86B450DA9DDE3BDEE98077E0`
  - 最終commit前再走report SHA-256:
    `251AB8E2672A8A83E6BFB1EA6B46096BB61C2BA9C1728F22A70004BB56D07784`。
    reportには絶対pathと実測`render_seconds`を含むため、再走の認証軸は上記
    algorithm SHA、固定scope、残差0・可視失敗0とする。
- current no-worseningのPhase600後fresh全数描画: PASS。
  - 全言語 total 323,225 / 74,295 cases。
  - current correct 323,215 / 74,290 cases。
  - regression 0、improvement 0。
  - raw findingは三言語同一で
    `Izraelio`、`Temis`、`iniciatoro`、`tia-tia` の4表層だけ。
  - `glu-glu-glu`、`nor`、`nor-adrenalino`、`nor-epinefrino` は解消。
  - 三言語fingerprint
    `3CA7979E3AE68D39BED1DEC229757B56C8AF51394F73EF9EB70C0F2ED8D673E9`、
    不一致0。
  - report 195,056 bytes、SHA-256
    `DEE2A40DC388B786E72DCE4B71716FDCD4AB687690C145E963B9071E8EDABB15`。
  - semantic wrong 0、boundary mismatch 0、sidecar gate true。
  - 全コード・台帳更新後の2026-07-27 10:44 JST最終再走でも同じreport SHAを再現。
    stderr 0B、formal stdout SHA-256
    `1A0ED0CFCB8E1013D4C24F91759126E51F21398BC5939D2E7F037E4E888647CE`。
  - 最終再走の最初の起動は4つのauthority環境変数を明示しなかったため、
    描画・report削除・payload書き込み前に停止。固定gold/e373/7c04/d164を
    明示して再起動し、上記PASSを得た。
- fixed Phase597 62,313行×JA/ZH/KO: PASS（runtime integrityのみ）。
  - コメント202行を除く62,111行、runtime unique 61,844、
    render union 62,305、未評価0。
  - 三言語境界8指標0、全issue bucket 0。
  - 実効幅2倍超0。最大JA 1.533750、ZH 1.366875、KO 1.104375。
  - fake/coarse 3,608行は一致1,047／未裁定不一致2,561。
    2,561件は三言語完全同一だが、意味承認はfalse。
  - raw `complete=true` / `runtime_gate=true` / top gate=false。
  - sidecar `runtime_integrity_gate=true`、許可残差は
    Ruby=`atletik/o`／Kanji-master=`atlet/ik/o` の`atletiko` 1件だけ。
  - master promotion、full fake/coarse semantic gateはfalse。
  - 最終commit前再走のfresh report 8,333,034 bytes、SHA-256
    `A36097B8E8BBFA0E2F8D2A71D5658CAF897D2D66A7A13EDD892B9E842E23254F`。
    raw bytesには実測`render_seconds`が含まれるため、再走ごとの意味同一性は
    下記stable semantic projectionで判定する。
  - 実行秒数を除くstable semantic projection SHA
    `B574021AF5DC842494C177FA81979D6D16626B2D6C318B55A9CF121873BC7FC2`。

Phase597 successor初回deployed gateは、Phase532/558とPhase598で
同じpayloadのsemantic hash化規則が違うのにhash文字列を直接比較した新規gateの
実装ミスを検出してfail-closed。payload/fingerprintは一致していた。
比較を実内容＋raw SHAへ限定修正し、2回目はstderr 0B、
stdout SHA-256 `92F6F67869B50F5D22F93E2A4C841E4B275F753992B9D06382058CF385B0CC8F`
でPASSした。またraw semantic projectionから各言語の`render_seconds`を除外し、
時間だけの変化は同SHA、意味値変化はFAILとなる回帰を追加した。

### current no-worsening 第1回全数描画のfail-closed記録

第1回は全68,429表層をJA・ZH・KOで描画し、三言語fingerprintは
`A4F30C1BDED6DE7BDDC15D9210E7E9292A14555BA077EE117992511F6AD8BD09`
で完全一致（不一致0）した。ただし旧successor sidecarが想定していた3表層ではなく、
次の8表層が生の不一致として現れたため、ゲートは意図どおりFAILで停止した。

- 既裁定の粗いRuby: `Izraelio`、`tia-tia`
- 文脈限定でのみ直す同綴異義: `Temis`
- active corpusのreviewed improvement: `iniciatoro`
- 要修正として新たに露出: `glu-glu-glu`、`nor`、
  `nor-adrenalino`、`nor-epinefrino`

第1回実行時のreport:
`out/_audit_no_worsening_current_d1642c2.json`、bytes `210,842`。
これはPhase600前の歴史値で、同pathは最終再走により上記195,056 bytesのPASS reportへ
意図的に置換済みである。
combinedは各言語とも total `323,225 / 74,295 cases`、
current correct `323,211 / 74,286 cases`。このFAILを例外拡張で隠さず、
後4表層を独立に再監査した。

再監査の結論:

- `glu-glu-glu` はPIV定義が「七面鳥の鳴き声」で、generic `glu=糊/粘/붙이다`
  を3回当てるのは意味破壊。lowercase完全一致の語全体一体Rubyにする。
- `nor` 3件はPhase597の学習者版・学術版で同じ無標境界。現行
  `word_anno` にJA `ノル`、ZH `降碳`、KO `노르`が既にあり、
  R68当時の「訳語なし」回避策だけが陳腐化していた。
- `nor` はlowercase単独1形、化合物は2語幹×8語尾×3大小形の48形だけを
  完全一致で直す。`Nor`/`NOR`単独、`nordo`、`norno`、固有名、
  非hyphen形、未知の`nor-X`は不変にする。
- 修正はRuby-only後段とし、歴史的R68行、Kanji payload、master、HTML、
  ガイドを変更しない。

この実失敗の是正・再描画が終わるまで、current no-worseningをPASSとは記録しない。

Phase600後の再描画では上記4欠陥表層がraw findingから消え、
残る4表層だけを既裁定sidecarへ通して正式PASSした。
途中、focused rendererへ上限50を超える`batch-size=100`を誤指定した試行が
書き込み前の引数検査で停止した。payloadへの書き込みは0。
正式値50で再実行し、上記結果を得た。

## 9. 固有名詞の扱い

R74へ固有名詞の一括変換を混ぜない。大文字始まりは文頭の普通語を大量に含むため、
大文字判定だけでラテン固定または漢字化しない。

引用の「大文字始まり2,888」は候補総数ではなかった。全172 HTMLでは
大文字開始4,107形、CJK化2,969形で、master exportラテン維持なのにappが
CJK化する81形を引いた補集合 `2,969 - 81 = 2,888` だった。

引用の32語は次の内訳で再現した。

- 誤り候補8
- 意味が通る8
- `-ujo` 10
- `Esperanto` / `Temis` 2
- 要約から脱落した `Alpoj` / `Antarkto` / `Arkto` / `Biblio` 4

ただし「誤り候補8」の一括ラテン化は棄却する。

- 明白な偽matchで、完全一致・大小文字限定のラテン維持候補:
  `Usono`、`Brazilio`、`Filipinoj`、`Ivo`、`NRO`、`SEK` の6語。
- `Bonaero` はlearner `Bon/aer/o##偽分解` と語義「良い空気」に沿うためKEEP。
- `Odiseado` はlearner `Odise/ad/o` で小文字普通名詞用法があり、
  `ad=行`を語幹単位で消すと通常語退行になるためKEEP。
- 意味が通る8とstructural 4はmaster境界に沿うためKEEP。
- `-ujo` 10は国名用法の `器` が不自然だが、global `uj→国` は容器語を破壊する。
  master側で国名senseを裁定後、大文字完全一致語だけを別branchで扱う。
- `Esperanto` / `Temis` は既裁定を維持し、動詞 `Temis` はPhase599文脈限定とする。

- どの語義でも意味が壊れる表層だけを語単位でラテン維持。
- 意味が成立し、学習者版マスターの分解・割当と整合するものは漢字化を維持。
- `-ujo`国名、同綴異義、文頭大文字は普通語を殺さない個別裁定を必須とする。
- 6語候補もR74とは混ぜず、別の狭いbranch/commitで正負例を固定してから扱う。

## 10. 変更していないもの

- 最新京大HTML main `d1642c2`（R74監査中のHTML追加変更なし）
- 2冊の最新ガイド
- Phase597およびlive Phase608マスター
- 学習者版の偽分解・過細分解authority
- Kanji設定・CSV・JSON・pure-Kanji payload
- generic `Temis`、generic `on=分数/분수`
- app `main`への直接push/merge
- corpus `main`への直接push（変更は隔離PR #6経由でremote側merge）
