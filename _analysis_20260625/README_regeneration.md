# 道B: 大JSON再生成パイプライン(正式ルート)

このディレクトリには、3言語アプリの置換用大JSON(ルビ/漢字/純粋置換)を再生成する
**唯一の正式ルート**が収録されています。アプリ内の旧「JSON生成ページ」は
最新の品質修正を含まないため撤去されました。

## 明示trackで一括実行
    $env:ESP_GOLD_PATH = '<監査済みgold snapshot>'
    $env:ESP_ACADEMIC_GOLD_PATH = '<同一行対応の学術版snapshot>'
    $env:ESP_PEJVO_ORIGINAL_PATH = '<監査済み原典PEJVO snapshot>'
    $env:ESP_PHASE558_PARENT_CORPUS_PATH = '<cleanな歴史b769京大HTML repo>'
    $env:ESP_LATEST_KYOTO_MAIN_PATH = '<read-onlyのcleanな不変7c04比較基準>'
    $env:ESP_PHASE558_CURRENT_CORPUS_PATH = '<cleanな歴史e373京大HTML repo>'
    $env:ESP_CORPUS_PATH = '<cleanな現行d164京大HTML repo>'
    $env:ESP_PHASE597_CANDIDATE_DIR = '<Phase598裁定の固定入力一式>'
    $env:ESP_PHASE532_BASELINE_DIR = '<固定Phase532親snapshot>'
    $env:ESP_PHASE532_CANDIDATE_DIR = '<固定Phase532候補snapshot>'
    $env:ESP_PHASE558_CANDIDATE_DIR = '<固定Phase558候補snapshot>'
    $env:ESP_PHASE558_RUBY_DISPOSITION_LEDGER = '<固定Phase558裁定台帳>'
    $env:ESP_RUBY_HTML_GUIDE_JA = '<歴史Phase558日本語ガイド>'
    $env:ESP_RUBY_HTML_GUIDE_ZH = '<歴史Phase558中国語ガイド>'
    $env:ESP_PHASE558_FAKE_COARSE_MANIFEST = '<固定Phase558粗分解manifest>'
    $env:ESP_PHASE558_TRANSITION_DISPOSITIONS = '<固定Phase558移行裁定>'
    python _analysis_20260625/regenerate_all.py --ruby-only

漢字成果物も意図的に再構築する場合だけ、固定漢字正本を追加して実行する。

    $env:ESP_KANJI_MASTER_PATH = '<監査済み漢字割当正本ディレクトリ>'
    $env:ESP_ALLOW_UNREVIEWED_KANJI_CANDIDATE = '1'  # 隔離worktree限定
    python _analysis_20260625/regenerate_all.py --all-tracks

track modeは必須であり、引数なしでは最初の書き込み前に停止する。
Ruby-onlyでも上記の固定入力をすべて明示し、all-tracksではさらに漢字正本を必須とする。
`ESP_LATEST_KYOTO_MAIN_PATH` は後方互換の変数名であり、実際には段落・形式を整えた
不変の7c04比較基準を指す。`ESP_CORPUS_PATH` はその後、孤立した `iniciatoro` 補正だけを
取り込んだ現行remote main d164を指し、両者を同じ役割として扱わない。
さらにall-tracksは、Phase511由来21件のKanji authority gateが未整備である間は
candidate-onlyとし、`ESP_ALLOW_UNREVIEWED_KANJI_CANDIDATE=1`を明示した隔離worktreeでしか
実行できない。候補は個別裁定前に配備成果物へ昇格してはならない。
学習者版・学術版・原典PEJVOは
`_fake_coarse_reference_manifest.json` のbytes/line count/SHA-256と一致し、
正式生成は書き込み前に全62,313行の対応、偽分解3,492行の語義gloss一致、
および粗い分解参照表を`--check`で再構成する。goldは
`_no_worsening_scope_manifest.json` のbytes/SHA-256と一致し、corpusは2つの
exact manifestが記録したHEAD/status/content hashと一致すること。漢字正本は
all-tracksの場合に限り、`_kanji_master_scope_manifest.json` の4ファイルの
bytes/SHA-256と一致すること。
いずれかが異なれば最初の書き込み前に停止する。

Ruby-onlyは24・25・26・28の漢字書込工程と37のbackup一括掃除を計画から除外する。
開始時に配備済み漢字成果物9本がHEADと同一であることを確認し、各工程の成功時・
失敗時の双方でbytes/SHA-256不変を再確認する。27の偽分解/deep分解照合は
read-only gateとして残す。これにより、Rubyの粗境界修正を漢字成果物へ暗黙に
伝播させない。漢字を更新する場合はall-tracksを明示し、差分を別途裁定する。

Phase598 technical-on サイドカーは、Phase558を親として8見出しだけを追加採用する。
`fonon/foton/ganglion/magneton/mezon/nukleon/termoelektron` の7語幹は
`ruby_track_only` と予約文脈注釈で、通常10語尾×lower/initial/upperの210形を
京大エス研級の粗い1語根Rubyにする。裸の同綴対格形を守るため `ne` は付けない。
`gigaelektronvolto` は小文字完全一致の `RRRL + ruby_only` 1形だけを採用する。
漢字側は学習者版の偽分解・deep分解を従来どおり使用し、一般の
`on=分数/분수` は変更しない。正式ゲートは正例211形・負例159形を各言語で描画し、
JA/ZH/KOのR/L境界とrb配列を完全一致、各言語rtを固定manifest一致にする。
Arial 16の `char_widths.json` と実配備CSSで幅を再計算し、未知文字0・自動改行0・
実効幅比2以下を要求する。Phase597の入力はlive masterではなく、bytes/行数/
SHA-256を固定した `ESP_PHASE597_CANDIDATE_DIR` からのみ再認証する。

R67/R68の語頭保護は、再生成元マスターへ混ぜ戻さない歴史sidecarである。
再生成前に `preserve_r67_r68_ruby_overlays.py capture` が配備済み
`R67H` 336行・`R68W` 1,013行/言語と `Auster` exact overrideをsealし、
全面再生成後に同じ行triples・順序をJA/ZH/KOへtransactionalにcarry-forwardする。
各言語のrows SHA-256と親R72 commit/treeを固定し、衝突・欠落・順序変化は停止する。
旧R68 discoveryをlive master上で再実行してscopeを広げてはならない。
復元後は全域572,501行/言語を要求し、
`phase598_parent_payload_delta_gate.py` が親R72との差を
R73正例211形（旧66規則の置換を含む）だけへ閉じる。

Phase599は、文頭の動詞 `Temis pri ...` を固有名詞 `Temis` と混同しないための
文脈限定Ruby補正である。京大HTMLに実在する完全一致5句（6出現）だけを
JA/ZH/KOへ同時に5行ずつ追加し、`Tem/is` の境界を三言語で完全一致させる。
裸の `Temis`、`Temiso`、女神名を含む文、大小文字違い、句読点違いには広げない。
Phase599だけの中間状態は572,506行/言語となる。幅はArial 16と実CSSで2倍以内を検査し、
漢字成果物9本はバイト不変とする。これはルビ側だけの粗い文脈補正であり、
学習者版の偽分解を使う漢字トラックには介入しない。

Phase600は、固定Phase597マスターの全数監査で残った普通語4見出しを、固有名詞より
優先して直す閉集合Ruby補正である。`glu-glu-glu` は一般の `glu=糊` を反復せず、
七面鳥の鳴き声を表す一体の語として注釈する。`nor` は辞書見出しと
`nor-adrenalin` / `nor-epinefrin` の2語幹×8語尾×3大小文字＝48形だけへ限定し、
`kuku-nor` / `lob-nor` の既存出力を守る2行も含めて52行/言語を追加する。
最終状態は572,558行/言語である。正例50・負例21、JA/ZH/KOのR/L境界とrb列の
完全一致、Arial 16と実CSSで実効幅比2未満、漢字成果物のバイト不変を要求する。
歴史R68行は削除・改変せず、専用placeholder・固定位置・完全行一致で後発層だけを
識別する。Phase600配備後にPhase599を再監査し、52行を一時正規化して同一順序で
戻せない部分配備・改変・並べ替えをfail-closedで拒否する。

Phase513 Ruby設定を固定Kanji snapshotへ隔離再生成した比較では、配備版に対して
全域表16表層（追加10・削除6）のsemantic差が生じた。偽分解/deep分解53件×3言語は
不一致0だが、この16件はRuby設定由来であり、今回のRuby-only更新には吸収しない。
62K実機差分8行には改善（celulozo、laktozo、siria系、nen）と同時に、bifeniloが
部分漢字化から全裸文字へ戻る退行が1件含まれる。改善だけを理由に巨大JSONを一括昇格せず、
Phase511 transition 21件のKanji authorityとfail-closed gateを整備してから、
次回all-tracks更新時に固定候補treeで個別裁定する。

実行順(2026-07-27版。番号は論理工程順):
1. build_fake_coarse_reference_manifest.py --check … Phase513学習者版・学術版・PEJVO原典を再読し、62,313行対応・語義一致・3,213行の粗分解authorityを検証
2. build_fake_coarse_transition_review.py --check … 歴史的C679→B090 manifestのraw 136行を由来ごと改変せず固定
3. build_fake_coarse_ff33_transition_review.py --check … FF33で新たに偽分解となったTomisto 1行を別scopeとして固定
4. build_fake_coarse_5e_transition_review.py --check … final 5Eのpromilo 1行を別scopeとして固定（Ruby=promil/o、Kanji=pro/mil）
5. build_fake_coarse_phase511_transition_review.py --check … Phase511由来でRuby用に閉集合裁定した21行をPhase513 snapshotで再認証し、歴史manifestのline 45205を後発authorityでsupersede
6. build_fake_coarse_transition_app_review.py --check … アプリ移行対象を固定authorityと照合
7. build_corpus_7c04_transition_review.py --check … b769→7c04を全172 pathで照合し、重複390削除・綴り15修正・注釈2追加以外を拒否
8. check_latest_kyoto_guide_transition.py … 最新2ガイドを読取専用で照合し、G8違反0・CSS修正対象0・`ĵus`三言語境界を検査
9. build_corpus_exact_manifest.py --check … 現行d164の426 exact表記とclean HEAD・内容hashを照合
10. build_corpus_reviewed_exact_transition.py＋build_corpus_reviewed_exact_manifest.py … 旧628表記から綴り誤り3表記だけを退役し、現行625表記を再構成
11. build_bare_word_review_7c04f97.py＋bare_word_audit_7c04f97.py … b769→7c04のreanchorを固定し、7c04→d164で裸語投影不変を検査
12. Phase532/558 source review＋deployed runtime gates … 歴史authorityを再認証
13. preserve_r67_r68_ruby_overlays.py capture … 配備済みR67/R68行を固定snapshotへseal
14. apply_corpus_word_anno.py --write … 現行コーパス確定注釈・exact境界・予約文脈キーを日中韓へ同期
15. build_word_anno_boundary_manifest.py＋transition test … 日中韓の語根境界signatureとd164移行を照合
16. apply_confirmed_now.py 30 --settings-audit/--write … 三言語設定監査後にRuby候補を一括反映
17. preserve_r67_r68_ruby_overlays.py apply＋fix_ruby_postregen.py＋audit … 歴史行を三言語一括復元
18. Phase532/558/598 runtime gates＋phase598_parent_payload_delta_gate.py … 親R73までの差分閉包を再実行
19. phase599_temis_context_promotion.py apply/audit … 5完全一致句だけを三言語同時に昇格し、負例・幅・漢字不介入を検査
20. phase600_master_ruby_repair.py apply/audit … `glu-glu-glu` と `nor` 閉集合の正例50・負例21・三言語境界・幅・漢字不介入を検査
21. phase599_temis_context_promotion.py audit --deployed … 最終572,558行で後発52行を完全保存するno-op再監査
22. check_latest_kyoto_guide_transition.py（再検査）… 再生成後も最新ガイド基準を満たすことを確認
23. test/check_canonical_corpus_surfaces.py … 21,438表記を日中韓runtimeで全数検査し、`Temis`の生残差は閉じた文脈台帳へ明示
24. resync_kanji_master.py --write … all-tracksのみ。漢字正本と全面再同期
25. apply_kanji_now.py --write … all-tracksのみ。漢字3言語を学習者版の偽分解authorityで再生成
26. fix_kanji_2890.py --apply … all-tracksのみ。旧互換安全網
27. check_kanji_fake_decomposition.py … 深分解piece列と漢字割当を3言語で全件照合
28. derive_pure_kanji.py … all-tracksのみ。純粋置換版JSON再導出
29. anomaly_scan.py … 配備JSON異常スキャン
30. generation/Phase558/598/599/600/transition tests … 生成規則・三言語・歴史sidecar・後継台帳の回帰
31. test_reviewed_exact_manifest.py … 残差manifest回帰
32. check_multilingual_structure.py … 全域ルールの日中韓語根分節一致
33. check_raw_apostrophe_structure.py … U+2019原表記の全コーパス3言語runtime回帰
34. run_phase558_no_worsening.py … Phase558 parent/current・full historical sidecarを歴史authorityとして検証
35. run_current_corpus_no_worsening.py … 7c04を不変reference、d164を現行として三言語全数描画し、`iniciatoro` 1改善だけを許可
36. run_phase597_full_master_successor.py … Phase597固定6ファイルの全62,313行を3言語runtimeで監査し、`atletiko` 1件だけを二軌道sidecarへ明示保留
37. prune_baks.py … all-tracksのみ。全工程合格後に一時バックアップを掃除

Phase511由来の `_fake_coarse_phase511_transition_review.json` は、裁定済み21行だけを
`ruby_track_only` で固定する。歴史manifestのraw 136行は変更せず、重なるline 45205
（arabinozo）だけをPhase511側からsupersedeする。このためfull-masterの正式scopeは
歴史effective 135＋FF33 1＋final-5E 1＋Phase511 21＝158行である。一方、単語投影の
no-worsening scopeは歴史側のmultiword 1行を含まないため157行であり、両数値を混同しない。
このreviewが固定するのは学術版に沿う粗いRuby境界だけで、漢字側は学習者版のdeep/偽分解を
そのままauthorityとして保持する。line 60166 `deoksioz/o` とline 60735
`deoksi/riboz/o` は、深いRubyで酸素・病症・スグリの同綴語義を誤表示したため、
語と片位置に限定した日中韓注釈を伴う完全一致ルールとしてのみ採用する。追加の15表層
（糖名13、standalone `deoksi`、過細な `stakiozo`）も同じ閉集合方式である。
`exact_only`・`case_sensitive`・`ruby_track_only` を必須とし、融合語根を一般設定へ昇格
させない。`kalozo` は同綴2義を片方へ潰さず、三言語とも植物義と解剖義を併記する。
`nitrato` の訳語補完も既存 `@typed:nitrato:0` のみで行い、plain `nitrat` を追加して
`nitrata acido` / `sennitratigo` の深境界へ波及させない。

`adopt_phase513_no_worsening_candidate.py` は、`--references-only` で作ったpin済み候補から
この21行を保持し、通常分解delta `nen -> ne/n` だけを加え、scope/conflict manifestと
strict exact台帳を933件へ再束縛する
一回限りの専用adopterである。通常の一括再生成には含めず、候補・gold・corpusの全identityを
照合してから明示的に実行する。Phase512/513で増加・深化したfake 11行の一括採用には使用しない。

`run_phase597_full_master_successor.py` は、live masterではなく固定Phase597の6ファイルだけを
generic candidateとして監査する。Phase532/558固有引数と
`--enforce-all-fake-coarse` は渡さない。raw監査は入力62,313行からコメント202行を明示除外し、
runtime候補62,111行、render union 62,305表層をJA/ZH/KOですべて評価する（未評価0）。
三言語境界8指標、runtime error、可視失敗、placeholder、空rb/rt、zero-token outputはすべて0。
CSSとArial 16の実文字幅を反映した実効幅2倍超も3言語とも0で、最大は
JA 1.533750、ZH 1.366875、KO 1.104375、幅字形欠落・未知rt classは0である。

偽分解/coarse authority 3,608行は各言語で一致1,047／不一致2,561である。
2,561件は三言語で完全同一だが、包括的な意味承認ではなく未裁定キューとして
countとstable projection SHAを固定する。R73で裁定済みのtechnical-on 8見出しだけが
直前報告の2,569件から消え、共通2,561件への追加・変更は0である。
段階的transitionは157/157一致する一方、`atletiko` は
Ruby=`atletik/o`、Kanji/master=`atlet/ik/o` の二軌道として1件だけ明示保留する。
したがってrawは `complete=true` / `candidate_audit.runtime_gate=true` だが、
top-level gate、master promotion、full fake/coarse semantic gateは意図的にfalseである。
後継sidecarだけが配備runtimeの健全性をtrueにし、master全体を昇格させない。

2026-07-27のfresh reportは
`out/_audit_master_3lang_phase597_successor.json`（最終commit前再走は8,333,034 bytes、
SHA-256 `A36097B8E8BBFA0E2F8D2A71D5658CAF897D2D66A7A13EDD892B9E842E23254F`）。
raw bytesには各言語の実測`render_seconds`が含まれるため、再走の意味同一性は時間だけを
除外したstable semantic projection
`B574021AF5DC842494C177FA81979D6D16626B2D6C318B55A9CF121873BC7FC2`
で認証する。
実行秒数を除いた安定意味投影SHAは
`B574021AF5DC842494C177FA81979D6D16626B2D6C318B55A9CF121873BC7FC2`、
未裁定queue SHAは
`BD4F9A1CC41086FB8C93FE24B3F2EAAA129D3FE71B8303086341F40A25110C2B`。
正式一括生成では同じraw＋sidecarをOS一時ディレクトリへ再生成し、実行時間だけの差を無視するが、
境界・訳語・幅・issue・queue・payloadの差は拒否する。

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
Ruby用の衝突判定・語尾派生には、pinした学術版（粗分解）を使います。学習者版の
deep/偽分解（例: `et/an`, `met/an`）をRuby設定へ流用して短い語根を過剰に一般化せず、
学習者版は漢字トラックの深分解authorityとしてのみ使います。このため正式生成では
`ESP_ACADEMIC_GOLD_PATH` も必須で、学術版のbytes/line count/SHA-256がmanifestと
一致しなければ設定生成前に停止します。
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
外部環境では、この文書冒頭「明示trackで一括実行」に列挙した全authority環境変数で
場所を指定します（`--all-tracks`だけはさらに`ESP_KANJI_MASTER_PATH`が必須）。
正式生成時は場所だけでなく、gold・漢字正本の
固定bytes/SHA-256も一致しなければ停止します。`ESP_CORPUS_PATH` は固定manifestを生成した
cleanな京大HTML repoを指し、HEAD・status・169文書の内容hashが一致しない場合は
書き込み工程の前に停止します。manifest内の`source.branch`は取得時の来歴表示だけであり、
同じcommitを`main`・監査branch・detached HEADのどれでcheckoutしたかは意味的同一性に
含めない。
漢字正本の既定位置は作者PCの絶対パスではなく、このrepoの親ディレクトリにある
兄弟フォルダとして解決します。正式工程は `_kanji_master_scope_manifest.json` を
再同期工程と旧互換パッチの双方へ渡し、各正本ファイルのbytes/SHA-256を工程途中でも再検証します。

## マスター更新への追従(監視ツール)
- audit_master_62k.py         … gold⇔E_stemのドリフト検出
- absorb_master_drift.py      … A型(マスター一体化)ドリフトのルビ吸収(CORPUS_SPLIT_KEEP除外つき)
- resync_kanji_master.py      … 漢字正本の全面再同期(単独実行可)
- run_phase597_full_master_successor.py … Phase597の固定6入力を
  `audit_master_3lang_full_snapshot.py`で全行描画し、明示snapshot SHA・全行accounting・
  入力安定性に加え、Phase532/558/598の配備済み前段gateと`atletiko`二軌道裁定を
  fail-closed sidecarで検証する正式62K×3言語gate。正式一括生成はこのrunnerだけを使う。
- audit_master_candidate_delta.py … 直前の正式全件報告と新しい固定snapshotの
  runtime表層投影が完全同一の場合だけ、commitおよび実worktreeのruntime依存物を
  拘束して描画結果を条件つきで継承し、変更された分解表層と新しい偽分解authorityを
  3言語で再評価する候補専用監査。snapshot・台帳・実行依存物は解析開始前から
  SHA-256で拘束し、出力先が入力snapshotやapp配下と重なる指定は拒否する。
  旧正式報告はPython/pandas等の版を記録していないため、delta報告は
  `complete_delta_proof=false`とし、昇格前には現環境で正式全件監査を必ず再実行する。
  `candidate_only=true`・`promotion_gate=false`を固定し、正式全件監査の代用や
  moving masterの自動昇格には使わない。
- audit_master_3lang_fast.py  … moving absolute pathを読む`--monitor-only`高速診断。
  空白・約物等を除外するため正式証明には使用禁止。不一致時は非0終了する。

## コーパス(京大エス研HTML)すり合わせツール
- _corpus_full_audit.py       … 全文書の境界監査(コーパス⇔アプリ、gold裁定つき)
- cross_doc_inconsistency.py  … 同一語の文書間分解揺れ検出(固有名詞誤分解の信号)
- build_corpus_exact_manifest.py … 空白・拡張文字等を含む426表記のcase-sensitive exact固定
- build_corpus_reviewed_exact_manifest.py … 汎用規則後に残るevaluable表記を
  typed signatureと文脈注釈ごと固定（監査reportとclean corpus hashを照合）
- build_corpus_7c04_transition_review.py … b769→不変比較基準7c04の構造差を閉集合で固定
- check_latest_kyoto_guide_transition.py … 2ガイドを一切書き換えず、最新版・翻訳標識・
  CSS境界・三言語runtimeを読み取り専用で照合
- build_corpus_reviewed_exact_transition.py … d164で退役した綴り誤り3表記を明示し、
  現行625表記を歴史628表記と混同しない
- build_bare_word_review_7c04f97.py / bare_word_audit_7c04f97.py …
  不変7c04でのreanchorと現行remote main d164投影を別authorityとして検査
- check_raw_apostrophe_structure.py … canonical化でASCIIと統合されるU+2019表記を
  raw visibleのまま3言語runtimeに通し、可視文字とruby/literal役割を全数検証
- check_canonical_corpus_surfaces.py … 現行169文書・348,580 rubyから得た
  evaluable 269,577件/21,438表記を3言語の配置済みruntimeで再描画し、reviewed
  625表記を含むtyped signature・可視文字・placeholder残留を検査。文頭動詞
  `Temis` の生残差3言語分はPhase599完全一致文脈台帳でのみ許可し、隠さず別掲する
- `_strict_gold_reference_fixes.json` … no-worsening参照に残った辞書語を、
  case-sensitive・bounded・typed exact規則として参照hash付きで固定する
  （Phase513 pinでは933件）。
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

R74以降の正式再生成では、上記の歴史監査ファイルを上書きしない。
`run_current_corpus_no_worsening.py` が別の出力
`out/_audit_no_worsening_current_d1642c2.json` を作り、e373→7c04の
110 weight-row差と、7c04→d164の `iniciatoro` 1改善だけをsidecarで許可する。
JA/ZH/KO全68,429表層の境界fingerprintが一致しなければ失敗する。

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
