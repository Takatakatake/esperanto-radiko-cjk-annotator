# 道B: 大JSON再生成パイプライン(正式ルート)

このディレクトリには、3言語アプリの置換用大JSON(ルビ/漢字/純粋置換)を再生成する
**唯一の正式ルート**が収録されています。アプリ内の旧「JSON生成ページ」は
最新の品質修正を含まないため撤去されました。

2026-07-29 Phase619 の凍結入力、京大最新版、普通語7件、三言語境界、ルビ幅、
漢字非破壊、未証明範囲を含む詳細な判断記録は
`PHASE619_KYOTO_ORDINARY_RUBY_RECERT_AUDIT_LOG_20260729.md` を参照してください。

## 明示trackで一括実行
    $env:ESP_GOLD_PATH = '<監査済みgold snapshot>'
    $env:ESP_ACADEMIC_GOLD_PATH = '<同一行対応の学術版snapshot>'
    $env:ESP_PEJVO_ORIGINAL_PATH = '<監査済み原典PEJVO snapshot>'
    $env:ESP_CORPUS_PATH = '<cleanな京大HTML repo>'
    $env:ESP_PHASE558_CURRENT_CORPUS_PATH = '<同じcleanな京大HTML repo>'
    $env:ESP_PHASE597_CANDIDATE_DIR = '<Phase598裁定の固定入力一式>'
    $env:ESP_PHASE619_CANDIDATE_DIR = '<Phase619裁定の固定入力一式>'
    $env:ESP_PHASE619_RUBY_HTML_GUIDE_JA = '<現行日本語ガイド>'
    $env:ESP_PHASE619_RUBY_HTML_GUIDE_ZH = '<現行中国語ガイド>'
    python _analysis_20260625/regenerate_all.py --ruby-only

漢字成果物も意図的に再構築する場合だけ、固定漢字正本を追加して実行する。

    $env:ESP_KANJI_MASTER_PATH = '<監査済み漢字割当正本ディレクトリ>'
    $env:ESP_ALLOW_UNREVIEWED_KANJI_CANDIDATE = '1'  # 隔離worktree限定
    python _analysis_20260625/regenerate_all.py --all-tracks

track modeは必須であり、引数なしでは最初の書き込み前に停止する。
上記に加え、activeなPhase532/558 authorityを閉じる
`ESP_PHASE532_BASELINE_DIR`、`ESP_PHASE532_CANDIDATE_DIR`、
`ESP_PHASE558_CANDIDATE_DIR`、disposition ledger、歴史ガイド、fake-coarse
manifest、transition dispositionsも明示する。固定本数ではなく、
`regenerate_all.py` の `required_inputs` と各active sidecarが要求する入力を
すべて指定し、場所だけでなくbytes/行数/SHA-256が一致しなければならない。
さらにall-tracksは、Phase511由来21件のKanji authority gateが未整備である間は
candidate-onlyとし、`ESP_ALLOW_UNREVIEWED_KANJI_CANDIDATE=1`を明示した隔離worktreeでしか
実行できない。候補は個別裁定前に配備成果物へ昇格してはならない。
学習者版・学術版・原典PEJVOは
`_fake_coarse_reference_manifest.json` のbytes/line count/SHA-256と一致し、
正式生成は書き込み前に全62,313行の対応、Phase619の偽分解3,656行の
学術版との語義gloss一致、
および粗い分解参照表を`--check`で再構成する。goldは
`_no_worsening_scope_manifest.json` のbytes/SHA-256と一致し、corpusは2つの
exact manifestが記録したHEAD/status/content hashと一致すること。漢字正本は
all-tracksの場合に限り、`_kanji_master_scope_manifest.json` の4ファイルの
bytes/SHA-256と一致すること。
いずれかが異なれば最初の書き込み前に停止する。

Ruby-onlyは漢字正本resync、漢字JSON生成、旧互換patch、pure漢字再導出、
backup一括掃除を計画から除外する。
開始時に配備済み漢字成果物9本がHEADと同一であることを確認し、各工程の成功時・
失敗時の双方でbytes/SHA-256不変を再確認する。偽分解/deep分解照合は
read-only gateとして残す。これにより、Rubyの粗境界修正を漢字成果物へ暗黙に
伝播させない。漢字を更新する場合はall-tracksを明示し、差分を別途裁定する。

さらに `audit_phase619_learner_word_kanji_key_coverage.py --check` を
Ruby-onlyでも実行する。ただしこれは学習者版から投影したdirect
`word_kanji` keyとEsperanto piece列の一致だけを測るcoverage-only監査である。
Phase619では62,313入力行中62,085行を非空keyへ投影し、52,775 unique keyのうち
44,284（83.910943%）、偽分解3,644評価行のうち3,445（94.538968%）を直接照合し、
covered piece driftは0だった。未被覆8,491 key／偽分解199行は
per-root・fallback・literal経路を含むため欠陥件数ではない。
`full_deployed_render_fidelity_certified=false` であり、全経路の配備漢字描画保証を
この数字から主張してはならない。

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

Phase619 ordinary-Ruby サイドカーは、Phase598を親として普通語7見出しだけを
追加採用する。対象は `imperialisto`、`provincialismo`、`endoskopio`、
`mikroskopio`、`mukozaĵo`、`ditionato`、`tetrationato` で、固有名詞変更は0。
6件は粗いatomic語幹、`mukozaĵo`だけは `mukoz/aĵ/o` の2 Ruby片とし、
全件を `ruby_track_only`・whole-word boundary・通常10語尾へ閉じる。
10語尾×lower/initial/upperで210表層/言語、240注釈/言語を実機描画し、
negative 64表層への専用注釈漏洩0、JA/ZH/KO境界・rb不一致0だった。
実効幅比の最大はJA 0.899599、ZH 0.898877、KO 0.868610で、2倍超過・
自動`<br>`とも0。漢字側は学習者版のdeep/偽分解を維持し、ルビの粗い境界を
漢字へ流用しない。

R67/R68の語頭保護は、再生成元マスターへ混ぜ戻さない歴史sidecarである。
再生成前に `preserve_r67_r68_ruby_overlays.py capture` が配備済み
`R67H` 336行・`R68W` 1,012行/言語と `Auster` exact overrideをsealし、
全面再生成後に同じ行triples・順序をJA/ZH/KOへtransactionalにcarry-forwardする。
各言語のrows SHA-256と親R72 commit/treeを固定し、衝突・欠落・順序変化は停止する。
旧R68 discoveryをlive master上で再実行してscopeを広げてはならない。
carry-forward直後は全域572,713行/言語を要求する。その後、
`fix_ruby_postregen.py`、京大meaning-break、hyphen-joiner、
ZH/KO diminutive-glossの4層を順に再適用し、最終572,729行/言語を要求する。
Phase619を含むpre/post runtime gateと最終overlay auditで閉じ、
削除済みの歴史的 `phase598_parent_payload_delta_gate.py` には依存しない。

（歴史記録）Phase513 Ruby設定を固定Kanji snapshotへ隔離再生成した比較では、配備版に対して
全域表16表層（追加10・削除6）のsemantic差が生じた。偽分解/deep分解53件×3言語は
不一致0だが、この16件はRuby設定由来であり、今回のRuby-only更新には吸収しない。
62K実機差分8行には改善（celulozo、laktozo、siria系、nen）と同時に、bifeniloが
部分漢字化から全裸文字へ戻る退行が1件含まれる。改善だけを理由に巨大JSONを一括昇格せず、
Phase511 transition 21件のKanji authorityとfail-closed gateを整備してから、
次回all-tracks更新時に固定候補treeで個別裁定する。

実行順（2026-07-29 Phase619正式経路。番号は論理グループ）:
1. fake-coarse reference／歴史transition／FF33／5E／Phase511／app-reviewをすべて`--check`
2. 京大corpus exact・reviewed exact・d1642c2 typo-retirement transitionをclean HEADと照合
3. `bare_word_audit.py --require-zero`
4. active Phase532 policy/carryとPhase558 overlayの固定source closureを再検証
5. `build_phase619_ordinary_ruby_review.py --check`でPhase597→619、両現行ガイド、7普通語を閉じる
6. Phase532/558/598/619 deployed runtime gateを最初の書込み前に実行
7. `preserve_r67_r68_ruby_overlays.py capture`
8. `apply_corpus_word_anno.py --write`でcorpus authorityとPhase619 7注釈keyを日中韓同期
9. `build_word_anno_boundary_manifest.py --check`
10. `apply_confirmed_now.py 30 --settings-audit`後、候補3言語をメモリ生成し全active gate後に`--write`
11. R67/R68を復元して572,713行を要求
12. postregen／京大meaning-break／hyphen-joiner／ZH-KO diminutiveを順に再適用
13. R67/R68を最終572,729行で監査し、Phase532/558/598/619 post gateを再実行
14. canonical 21,438表層とraw apostropheをclean d1642c2 corpusから日中韓全数検査
15. all-tracksだけ漢字正本resync・漢字3言語生成・旧互換patchを実行
16. `audit_phase619_learner_word_kanji_key_coverage.py --check`（coverage-only）
17. `check_kanji_fake_decomposition.py`でreview済み53件×3言語を配備描画照合
18. all-tracksだけpure漢字を再導出し、6 JSONを異常scan
19. generation／Phase558／Phase598／Phase619／coverage／R67-R68／transition各test
20. multilingual structureとraw apostrophe structureを検査
21. Phase558 no-worsening parent/currentと歴史sidecarを別authorityで検証
22. Phase619 learner/academic/manifest/dispositions＋現行両ガイドで全62,313行×3言語を正式監査
23. all-tracksだけ、全工程合格後に一時backupを掃除

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

`audit_master_3lang_full_snapshot.py` は指定snapshotの偽分解行を毎回すべて測定する。
Phase619では3,656行を測定し、正式既定ゲートで粗いルビ境界を強制するのは
candidate retirement後のactive transition 157行と閉じた7普通語sidecarだけである。
その他の不一致は
未裁定キューとして報告し、個別の語義・京大コーパス・日中韓境界を確認してからreview
manifestへ追加する。`--enforce-all-fake-coarse` は全件裁定後だけ使用する。
また、Phase619全量報告の完全無注釈語彙候補53件と非終端無注釈断片候補203件も
報告専用の確認キューであり、
自動修正や幅合わせのための細分化対象ではない。ルビ幅は原綴りのおおむね2倍以内を表示ゲートで
検査するが、幅を短くする目的だけで語根境界を増やさない。

（歴史参考。現行Phase619認証値ではない）2026-07-16のPhase513固定snapshotによる
Ruby-only正式再走は、入力62,313行からコメント
202行を明示除外し、runtime候補62,111行をJA/ZH/KOすべてで評価した（未評価0）。render
union 62,299表層の3言語境界不一致、runtime error、可視文字列不一致、placeholder残留はすべて0。
偽分解authority 3,492行は各言語で一致910／不一致2,582であり、一致910の内数である
段階的transition 158行は158/158一致した。不一致2,582行は未裁定キューとして強制しない。
この`gate=true`はstaged transition等の現段階の正式ゲート合格を表し、3,492行すべての
粗境界一致認証ではない（`all_fake_coarse_gate=false` / `all_fake_coarse_enforced=false`）。
文字数比2倍超のunique review指標はJA 199、ZH 78、KO 329（行重み付き202／78／330）だが、
CSSと実文字幅を反映した
実効幅2倍超は3言語とも0（最大JA 1.533750、ZH 1.366875、KO 1.104375、幅字形欠落0）。
入力・HEAD・tracked worktree・アプリ入力・監査script・authority manifestは終始不変で、
`complete=true` / `gate=true`。正式report SHA-256は
`8E0E8568A80A985178C69004CBDBE039422D9368DADA8ABD02906627C46C0201`。
reportは正式工程がOS一時ディレクトリの`esperanto_master_3lang_formal_report.json`へ再生成する。

2026-07-29のPhase619固定snapshotによる全量再認証は、入力62,313行からコメント202行を
除外し、runtime候補62,111行・unique 61,844表層をJA/ZH/KOすべてで評価した。
境界不一致、runtime error、可視文字不一致、placeholder残留、empty rt/rbはすべて0。
偽分解authority 3,656行は各言語で一致1,096／未裁定不一致2,560、段階的transition
157行は157/157一致した。7普通語だけを閉じたRuby sidecarとして認可し、より広い
Phase619 master promotionは明示的にfalseのままである。実効幅2倍超は0で、最大は
JA 1.533750、ZH 1.366875、KO 1.104375。`complete=true`／`gate=true`、
report SHA-256は
`7C7549784D4E8D8B92FEA693DE07DFE498DBC79AFCEF5D3F1DC27682325916B3`。

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
外部環境では ESP_GOLD_PATH / ESP_ACADEMIC_GOLD_PATH /
ESP_PEJVO_ORIGINAL_PATH / ESP_KANJI_MASTER_PATH / ESP_CORPUS_PATH /
ESP_PHASE558_CURRENT_CORPUS_PATH / ESP_PHASE597_CANDIDATE_DIR /
ESP_PHASE619_CANDIDATE_DIR / ESP_PHASE619_RUBY_HTML_GUIDE_JA /
ESP_PHASE619_RUBY_HTML_GUIDE_ZH
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
- fix_kanji_latinlock_inflections.py … ラテン固定語根(Petr/Krist/Oceani/ĉin/eŭrop/kaf)の
  語尾変化形・接尾辞形の穴を語スコープ完全一致キーで是正(第108R)。冪等($R108A投入分を
  外して測り直す)。漢字JSONを再生成した場合は--frozen(凍結マスター)付きで再適用する。
- audit_master_3lang_full_snapshot.py … 明示snapshot SHA・全行accounting・入力安定性を
  必須化した正式62K×3言語gate。正式一括生成はこれだけを使う。
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
- audit_ruby_master_coarsening.py … ★ルビの分節がマスター分節の**併合**になっているかのゲート
  (第114R新設)。粗いのは可・マスターが認めない位置で切るのは不可、を機械化する。
  62kゲートが「ルビが1つでもあれば注釈あり」と数えるため見逃す**語頭・語中の裸断片**
  (alteon→alt|«eon» / ocelon→«o»cel|«on»)を検出する。基線217件(ハイフン複合135・
  感嘆詞`!`約60・コーパスがアプリを支持する同綴り衝突)を超えたら非0終了。
- fix_ruby_inflection_resegment.py … 上記で見つかった「語幹が切られた語尾変化形」を
  アプリ自身の基本形キーの訳語で組み直す(第114R新設・発明ゼロ・冪等)。
- ★第125R教訓(2026-08-09): 置換リスト_漢字_純粋置換.json は置換リスト_漢字.jsonの
  **派生物**(derive_pure_kanji.pyでrt/rubyタグ剥がし・3アプリ共有・JA配下1本)なのに、
  第116R〜124Rの9ラウンドで再導出を怠り第110R世代(8/5)のまま配信していた
  (ユーザーが実機で francajn 誤分解を発見)。**漢字JSONに書き込む全ツールの適用後は
  derive_pure_kanji.py を必ず実行**(regenerate_all.py経由なら自動)。再導出後の検証は
  **audit_pure_kanji_derivation.py**(第125R新設・常設ゲート)=①派生同一性全行
  ②マーカー集計一致 ③コーパス実使用22,259語(out/_r109_corpus_words.json)で
  純粋置換出力==ルビ付き出力のタグ剥がし(不一致0)。不一致で非0終了。app cf4f303。
- fix_kanji_compose_r124.py … 第123R照会リストB類の裁定と是正(第124R)。★12語中10語
  (kafeja=kaf所a/ruslanda=rus国a/ĉinlingvaj=ĉin语aj等)は**既に正描画**=第123R署名
  「語頭1-3字ラテン+CJK」がラテン固定短語根(kaf/rus/ĉin/jud)+接尾辞漢字の正当パターンを
  誤検出していた(再flag禁止)。真に壊れていたのは psikanalizisto(psi渠化家o=渠が食う)と
  rasistaj(r辅aj=辅が食う)の2語のみ → マスター実在部品の実描画連結で合成
  (心ᴾˢ析家o/种ᴿ家aj。rt連結+ラテン=元表層の完全性検査付き)。冪等($R124C)。
  残る照会は taŭismo/romiajn(語根がマスター外)のみ。
- fix_kanji_ruby_bareout_r123.py … マスター外残余5,139語のガーブル署名スイープ(第123R、
  scratchpad r123_residue_sweep.py: 漢字頭食い署名408+ルビ語頭裸6)の是正。外国固有名詞・
  外国語引用347語を漢字裸化(Cambridge→C龙香子双 / Adam→A妃 型の根絶)+ルビ6語
  (Witold→Witol[糖アルコール]d 型)。★ラテン固定語根族の派生(tajvana/vienaj/kansaja/maoria等)は
  マスター実測(Tajvan/o→Tajvano等)に基づき裸化=正解。据置: 実文0件・コーパス側タイポ
  (lauta/rakonis等)・★B類=マスター既存部品で合成可能なEo実語14語(kafeja→kaf所a型)は
  out/_r123_compose_referral.tsv に照会リスト化(第124R軸)。冪等($R123B)。
- fix_tracks_participle_r122.py … 分詞/ad派生スイープ(第122R、scratchpad r122_participle_sweep.py:
  旧・導出不能のうち分詞形1,050語を初検査)の真欠陥を両軌道で是正。漢字=Jamada/Okada恒等
  (人名を份/木ᴷᴰが食う)+met族分詞(甲过e→置过e)+telefon族(int素通し→过)。
  両軌道=tempopasigadon(★専用GG行の保存値が生成時から a+don 誤読。値置換で ad[継続]on/行on)。
  ★このa+don誤読は**京大コーパスHTML自身の誤注釈由来**で、コーパス側も3正本を是正
  (radioelsendo前例の機械的誤分解クラス。corpus eea5786)。
  ★接尾辞グリフはマスター合議確認済(ant=在/int=过/ad=行)のみ使用可 — 'ota'行は耳ᴼᵀ=語彙
  衝突行で、未確認グリフ(at/it/ot/ont)での兄弟形生成は発明になるため禁止(第122R実測)。
  据置: diskantis=dis+kant+is(コーパス詩文が支持)/prante=実文0件。冪等($R122P)。
- fix_ruby_bareout_r120.py … ルビ軌道×コーパス実使用語彙の分節健全性スイープ(第120R初、
  scratchpad r120_ruby_corpus_sweep.py: 導出可能8,819語で境界違反3・無注釈14)の唯一の真欠陥
  Kanae(人名・Kan[アシ]aeと語頭食い)を単独語形だけ裸化(冪等$R120K)。実文の句は京大由来の
  句スコープキーが先勝ちして無傷なことをfail-closedで検証。★教訓: プレースホルダに可読語
  (SIM/TEST等)を使うと**実在キーに食われてプレースホルダ自体がルビ化けし復元不能**になる。
  $R+数字混在の実績形式のみ使用可。実使用語彙ゲートの注釈数は21,465→21,464(-1=Kanaeの
  ゴミ注釈が正しく裸になった分)が新基線。
- audit_kanji_3lang_identity.py … 漢字トラックのJA/ZH/KO同一性ゲート(第111R新設)。
  置換リスト_漢字.json のGG/G2/GLを(key,value)の位置つき(=並び順込み)で比較し、
  共有ロジック4本をAST比較する(裁定済みの翻訳/リネーム差のみ許容)。是正スクリプトの
  3言語ループが途中失敗した際の非対称を検知する。不一致時は非0終了する。
- fix_kanji_latin_maintained_r116.py … 第65R台帳(_latin_maintained_adjudication_20260725.json)
  の closable_survived を閉じる(第116R)。「マスターexportがラテン維持と定める語をappが
  漢字化する」型276語を、A型=既存全語キーの値だけ恒等ラテンに置換(111キー・発火位置不変)、
  B型/新規=空白パディング完全一致キーの挿入(基本形165+現に壊れている語尾変化形695)で是正。
  EXCLUDE(esperant*=ユーザー裁定, pol/et=照会中の衝突表層のみ)・Blanka則・同綴り漢字実在
  スキップ・全対象の事前シミュレーションを fail-closed で通す。冪等($R116L)。原状は
  out/r116_valuefix_ledger.json。★これによりエクスポート忠実度ゲートの基線は
  不一致931→655に更新。
- fix_kanji_ujo_country_adjudication_r117.py … ★ユーザー裁定(2026-08-08):
  **国名 -ujo 型107語は漢字トラックで 器 を用いる**(Afgan器o。esperanto=望在o と同じ
  「ユーザー裁定>マスター」方式)。第116Rでラテン化した107語族の全キー431個の値だけを
  「語幹ラテン+<ruby>器<rt>uj</rt></ruby>+語尾」に差し替え(キー・位置・ID不変)。
  ★Lakonujo/Lombardujo/Trakujo の3語は第116R前が 简ᴸ器o 型の欠陥だったので
  巻き戻しではなくクリーン形。裁定台帳 _ujo_country_adjudication_20260808.json を
  fix_kanji_latin_maintained_r116.py が EXCLUDE 参照する(再実行でも巻き戻らない)。
  マスター側への変更提案107行は out/_master_proposal_ujo_kanji_20260808.tsv(照会中)。
  ★エクスポート忠実度ゲートの基線: **762 = 655+裁定107**(98.616%。第117R以降は762超で退行扱い。
  新規不一致が裁定107語と集合一致することを2026-08-08に実測確認済)。
- fix_kanji_corpus_inflections_r118.py … 漢字軌道×コーパス実使用語彙22,201語の**初の全数診断**
  (第118R)で見つかった語尾変化形の欠陥68表層を是正。A恒等29=ラテン維持族の複数・対格の穴
  (francaj→f哈喇aj / dukatojn→二猫ojn / japanojn→ja面包ojn 型。第69Rは基本形しか守っていなかった)
  +コーパス実文脈裁定の固有名(Bene/Kanae/Lucien/Pekinon/Valerie)。B合成39=健全な基本形と
  別経路に落ちる変化形(metas→甲as vs meti→置i / reprezentas→表ᴿas vs 再呈i / sintenojn→怀持ojn
  vs 己n持o)を**アプリ自身の基本形描画から語尾挿げ替え**で構築(発明ゼロ・表示をマスター期待と
  fail-closed照合)。冪等($R118C)。診断の残77は全て裁定済み据置(望在8/文頭普通語支配24/
  基線既知の変化形9/人名・メタ言語断片・裸同綴り36 — Aŭdu=人名・spirante=呼吸の意でアプリが正、
  をコーパス実文で確認)。診断器は scratchpad の r118_kanji_corpus_sweep.py(将来はここへ昇格可)。

## コーパス(京大エス研HTML)すり合わせツール
- _corpus_full_audit.py       … 全文書の境界監査(コーパス⇔アプリ、gold裁定つき)
- cross_doc_inconsistency.py  … 同一語の文書間分解揺れ検出(固有名詞誤分解の信号)
- build_corpus_exact_manifest.py … 空白・拡張文字等を含む426表記のcase-sensitive exact固定
- build_corpus_reviewed_exact_manifest.py … 汎用規則後に残るevaluable表記を
  typed signatureと文脈注釈ごと固定（監査reportとclean corpus hashを照合）
- check_raw_apostrophe_structure.py … canonical化でASCIIと統合されるU+2019表記を
  raw visibleのまま3言語runtimeに通し、可視文字とruby/literal役割を全数検証
- check_canonical_corpus_surfaces.py … 169文書・348,580 rubyから得た
  evaluable 269,577件/21,438表記を3言語の配置済みruntimeで再描画し、reviewed
  625表記を含むtyped signature・可視文字・placeholder残留を残差0に固定
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
