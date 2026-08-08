# Phase 532〜537 統合捜査ログ

記録日: 2026-07-18（Asia/Tokyo）

## 1. この記録の目的

この文書は、約6時間にわたって行った京大エス研HTML、62,000語超マスター、
日中韓3言語ルビ、偽分解、ルビ幅、アプリ生成物の捜査について、散在していた
証拠を一つの追跡可能な台帳へまとめたものである。

これは「端末に表示された全コマンドと全stdoutを時系列で録画した生ログ」ではない。
元の作業時に、その形式の単一セッションログは採取していなかったため、後から存在した
ことにはできない。一方、判断の根拠になった入力SHA、生成物SHA、監査JSON、テスト、
差分、Gitコミットは残っている。本書はそれらを相互参照できる形で恒久化する。

## 2. 絶対に崩さない原則

1. 注釈ルビと漢字化は別軌道で扱う。
   - 注釈ルビは京大エス研HTML程度の粗さを基準とする。
   - 漢字化は必要に応じて偽分解・エス的分解・過細分解を尊重する。
   - 漢字用の深い分解を、機械的に注釈ルビへ流用しない。
2. 注釈ルビの分解境界は、日本語・中国語・韓国語で完全一致させる。
3. ルビ長は元アルファベットの約2倍を目安に監査するが、幅を短くする目的で
   語根を細分化しない。CSSクラス適用後の実効幅と、意味・分解の妥当性を分けて判定する。
4. 更新中のマスターを、その時々の作業ツリーから無条件でビルドしない。
   SHA固定した凍結スナップショットと、入力同一性ゲートを通した場合だけ採用する。
5. 京大エス研HTMLは既に人手確認歴のある基準資料として尊重する。
   機械的一括置換はせず、真の誤りを立証できた箇所だけを修正する。
6. 非悪化ゲート、3言語境界ゲート、生成物同一性ゲートのどれかが落ちた場合は停止する。

## 3. 現在地

監査カットオフ: 2026-07-18 22:49:25 +09:00

| 対象 | 状態 | 判定 |
|---|---|---|
| アプリ監査pin | 691e0462734fd13c23dd6287b012e3ac2aed506d | Phase 532採用前の凍結基底 |
| アプリGitHub main | 89fa012a3f80a1547b73c4d98d6ceab9fd548257 | 外部操作でPR #6をmerge済み |
| Phase 532実装 | 93a887e559171acb18122e31fd146c1822a015e1 | 現mainの第2親、配信側へ採用済み |
| PR #6 | Adopt Phase 532 safe trilingual Ruby boundaries | MERGED |
| 本統合ログ | 現mainから文書専用branchへ追加 | mainへ直接pushしない |
| 京大corpus GitHub main | 8f7c9b5fee9fdb5a9b3e15cf634722eca0f402fa | 監査後はガイド2点のみ、HTML差分0 |
| 京大エス研HTML本文 | 169ファイルを監査 | referenceすり合わせ不一致0、本文修正なし |
| Phase 533〜534 | 累積13行の辞書差分を暗号学的に再現・意味監査 | 調査済み、アプリ未吸収 |
| Phase 535 | 記録上の意味説明を精密化、マスター本文はPhase 534から不変 | 調査済み、アプリ未吸収 |
| Phase 536 | 学習者版11行を追加是正、学術版不変 | 差分確認済み、アプリ未吸収 |
| Phase 537 | 22:49時点で調査中、snapshot本文はPhase 536と同一 | 未確定・隔離 |
| 漢字マスター | remote main=1faf026、作業ツリー変更53件 | 後続差分を未監査のため未吸収 |

このセッションからmainを直接書き換えてはいない。ただしPR #6は別の外部操作により
作業中にmergeされ、Phase 532は配信側へ入った。Phase 533〜536は辞書差分を調査済み
だが、アプリ用の凍結・再生成・全ゲート通過前なので未吸収である。Phase 537は進行中の
ため、22:49の観測点で隔離した。これが正確な現在地である。

現main 89fa012と検証済み93a887eのtree SHAは、どちらも
46A631D1CA07E6E42A4885D143A925A14C80EFDAで完全一致する。merge commitに
追加内容はなく、本番treeは検証済み候補とバイト単位で同じである。

## 4. Phase 532 正式候補の捜査結果

### 4.1 入力と凍結

- 学習者版SHA:
  6B403AA30BBCBBA4C9E41A2CF48D1AD2FC1D5A5DB1154CAF1260A361566E3226
- 学術版SHA:
  FE632820E7752A555787C926C0A843CD82B2F79D4177A6D8D1E9622CA96393A5
- PEJVO由来入力SHA:
  B551510513C1924E65E64CF87EA4CE39128E80717E3A3F53847753F8A0557CBF
- tracked Phase 532偽分解manifestのraw SHA:
  5F743A916742BE022EFDEC30D24B5ACA0EB2A9156A2086FBB01740DDC356A060
- 同manifestのentries SHA:
  8F823A44A62AFB38321662FB843F52D9E97FB5953962CD5B75406B2F1EBC4368

gold、academic、HEAD、tracked worktree、アプリ入力、監査スクリプト、authority manifest、
候補ファイル、Phase 532 policy、凍結closureの全安定性チェックはtrueだった。

### 4.2 safe7

Phase 532でルビ境界を変更したのは次の7件だけである。

| 軌道 | 表層 | 注釈ルビ境界 |
|---|---|---|
| 共通 | lulu | lul/u |
| 共通 | suprenglisi | supr/e/n/glis/i |
| 共通 | pasivaĵo | pasiv/aĵ/o |
| 共通 | pasivigi | pasiv/ig/i |
| ルビ専用 | neologismemo | neologism/em/o |
| ルビ専用 | neologismemulo | neologism/em/ul/o |
| ルビ専用 | stenografistino | stenograf/ist/in/o |

Phase 532の対象表現は合計58件で、変更7件、粗い現行ルビ維持51件である。
ただし、維持51件のうち21表現（unmarked側17、fake側4）は正式な個別裁定が
まだ完了していない。現行挙動と3言語署名は固定・検査したが、意味上の最終裁定済み
51件という意味ではない。
ritma gimnastiko は多語表現なので、単語用パーサーへ押し込まず、
R:ritm、L:"a "、R:gimnastik、L:o という専用の有界署名で固定した。

strict entriesは932件。Phase 532採用後のruntime signature SHAは次のとおり。

6B5234B6904961388E5F322B4E8E372AC97AF5D058603D73D79213CF2A6741BC

### 4.3 最終テスト

- focused/unitテスト: 124/124合格
  - Phase 532固有: 36/36
  - 歴代生成回帰: 53/53
  - no-worsening監査単体: 35/35
  - 本統合ログ作成時にも上記3群を分割再実行し、合計124/124を再確認
- 歴代の実機回帰ケース: 合格
- Phase 532 full runtime audit: complete=true、gate=true
- no-worsening audit: complete=true、gate=true
- 日中韓3言語の境界不一致: 0
- runtime error、visible failure、placeholder残留: 0
- 保護対象の漢字化9ファイル: 親コミットとバイト同一
- git diff --check: 合格

候補のruntime生成差分は、新規生成表層272件とluluの小文字表層変更に限定された。
既存570,672件のdisplay HTMLは不変で、削除は0だった。

## 5. 62,000語超マスターの全体監査

完全監査レポート:

D:\tmp\esperanto_master_3lang_phase532_postregen_06fdb7b_20260718.json

- ファイルサイズ: 8,384,813 bytes
- SHA-256:
  CDF34C3EF894CF8C1C6FD3243320186E41035E0D109062F9D2482719726783AF
- complete=true
- gate=true

| 指標 | 件数 |
|---|---:|
| 入力行 | 62,313 |
| コメント除外 | 202 |
| runtime候補 | 62,111 |
| unique render surfaces | 62,299 |
| exact master surfaces | 61,844 |
| legacy fast surfaces | 55,383 |
| 偽分解行 | 3,517 |
| staged transition | 192/192 |

全ての3言語境界不一致カテゴリは0だった。これはtyped Ruby/literal spanの一致であり、
62,000語超の各訳語の意味的正しさを全件証明する数値ではない。
言語別global rulesは各570,945件。
localized rulesはJA 50,546、ZH 50,549、KO 50,540だった。

偽分解3,517行のうち、粗い現行ルビと一致したものは942、深い偽分解と異なるものは
2,575だった。この2,575は直ちに誤りを意味しない。漢字軌道の深い分解と、
ルビ軌道の粗い分解を意図的に分ける対象を含むため、個別裁定なしに自動一致させない。

各言語でfully-naked lexical review候補45件、nonterminal naked fragment候補202件も
抽出された。これらは誤り確定ではないが、未注釈・非終端断片の妥当性を確認する残査である。

## 6. 日中韓3言語のルビ境界完全一致

no-worseningのtracked結果:

_analysis_20260625/out/_audit_no_worsening_current_only.json

- ファイルサイズ: 183,881 bytes
- SHA-256:
  31CF40BABF0426B4EBAE233C989640923B2CB0F1080201961FE117A558DA769C
- raw cases: 68,524
- resolved cases: 68,485
- surfaces: 68,435
- raw projection SHA:
  308121D186957A792073F1620C5A4E5EA80D3B7EAA87DFE39573E05A2FE822A9
- resolved reference SHA:
  C6409A1F5CBF5C4ECB14D16592FA5238A141800A3DC69C3676EAF4016A5092A6
- raw projection conflicts: 89
- raw conflict SHA:
  16FD7BFCF7C1FC1840400FC4D09B83BCA96B987971C12C5BDE1A5D6A5D42404E

JA、ZH、KOそれぞれについて次を確認した。

- combined: 重み付き323,527/323,527一致、unique case 74,300/74,300、regression 0
- 京大HTML corpus: 重み付き271,065/271,065一致、unique case 21,877/21,877
- Phase 532 selected ordinary exact: 57/57境界一致
- official、project、place、exactの誤適用: 0

重み付き件数はHTML内の反復出現を含む。同一表層に複数の許容署名がある場合もあるため、
各出現の言語学的正しさを互いに独立して証明した件数ではない。この監査が直接証明するのは、
同じエスペラント表層に対するtyped Ruby/literal境界がJA/ZH/KOで一致し、固定referenceに
対して非悪化だったことである。62,000語超の全訳語の意味的正しさは、別の語彙監査対象である。

## 7. 京大エス研HTML全文書群

- HTMLファイル: 169
- raw ruby: 348,971
- parsed ruby: 348,971
- parsed/eligible units: 271,065
- excluded units: 0
- corpus content SHA:
  264E4217BE484ABC2DC5EF7A22D83C56076C255BFB389F8218A0C215DD2420B6
- 監査時corpus pin: b769038

監査時点で、抽出したHTML referenceに対する未参照境界は0、app側の参照外境界も0、
residualも0だった。そのため、誤りの証明なしにHTML本文を変更することはしなかった。
これは「HTML自身の全語根分解が言語学的に独立証明済み」という意味ではなく、
現行アプリとの境界すり合わせで立証できる不一致が0だったという意味である。

監査後、corpus remote mainは外部セッションにより8f7c9b5へ進んだが、
b769038から8f7c9b5までのHTML差分は0で、変更は2つのガイドtxtだけだった。
したがって上記169 HTMLの監査対象本文は不変である。

## 8. ルビ幅「約2倍」監査

各言語のunique ruby occurrencesは110,790件だった。

| 言語 | CSS実効幅が2倍超 | 最大CSS実効比 | 欠落文字 |
|---|---:|---:|---:|
| JA | 0 | 1.533750021457672 | 0 |
| ZH | 0 | 1.366875010728836 | 0 |
| KO | 0 | 1.1043750286102294 | 0 |

単純な文字数比や注釈文字列の生比率には2を超えるものがある。これは隠していない。
しかし、実際のCSSクラス適用後の実効幅は全件2倍以内だった。
この基準は表示上の見直しを促すゲートであり、意味的に不自然な細分化を正当化しない。

## 9. Phase 533〜537 後続差分の捜査

### 9.1 暗号学的な差分再現

Phase 534/535の監査pin（Phase 535では本文不変）:

- SHA-256:
  5C585494EE744912C77DBF246F77C8AB6D56428293FCB7B672E75C41623A5587
- bytes: 4,373,016
- CRLF行: 62,313
- bare LF: 0
- BOM: なし

Phase 532からPhase 534は同じ行位置の13行だけが変化し、
Phase 533からPhase 534は5行だけが変化した。

Phase 534から5行を逆適用するとPhase 533 SHAを完全再現した。

4F55DCB6E2570962C5B5A7D5A836454372349E7BBEA84B48B16BD1E7D2E458C2

13行全てを逆適用するとPhase 532学習者版SHAを完全再現した。

6B403AA30BBCBBA4C9E41A2CF48D1AD2FC1D5A5DB1154CAF1260A361566E3226

学術版はPhase 532からバイト不変である。

FE632820E7752A555787C926C0A843CD82B2F79D4177A6D8D1E9622CA96393A5

### 9.2 累積13行

Phase 533の8行:

- h^et/o/gnat/oj
- ket/o/gnat/oj
- nere/id/o
- oligo/h^et/o
- oligo/ket/oj
- poli/h^et/oj
- poli/ket/oj
- trih^/o/pter/oj

Phase 534の5行:

- igvan/odont/o##偽分解##エス的分解
- an/odont/o##偽分解##エス的分解##過細分解 a/n/odont/o
- di/odont/o##偽分解##エス的分解##過細分解 d/i/odont/o
- mega/teri/o##偽分解##エス的分解
- pter/an/odont/o##偽分解##エス的分解##過細分解 pter/a/n/odont/o

13行とも、スラッシュ除去後の見出し、定義、行数、改行形式は不変だった。
Phase 534の5語は、現在のアプリではJA/ZH/KOとも旧来の粗いルビ境界を維持し、
3言語境界は一致している。5語のCSS実効幅比はいずれも0.90未満だった。

### 9.3 意味監査上の注意

5件全てを「独立したPIV登録語根」と一括説明するのは正確ではない。
正確な記述は次のとおりである。

「PIV登録根・接頭要素、またはプロジェクト内で既に確立した拘束形式として、
各語の定義・先例・ユーザー裁定を個別に照合した。」

特にodont、否定an、語源的大のmega、pterは、独立PIV見出しの有無と、
プロジェクト上の偽分解裁定を混同しない。この注意はPhase 535の公式記録でも精密化された。

新しいPhase 534外部候補manifest:

D:\tmp\phase534_fake_coarse_reference_candidate.json

- bytes: 992,292
- SHA-256:
  3E7EA483AC171A1F2A195C6B856D7B7B2E901328A10BFA500554A3B0CF5B1358
- entries: 3,251
- entries SHA:
  C5066A4728FA4D88A5ACF6C0E1ABFC0F72F7EE051BB2FC60E614F3C1789DAD4B
- Phase 532 manifestとの差: 追加13、削除0、既存変更0

これは捜査証拠であり、現時点のアプリtracked authorityへはまだ採用していない。

### 9.4 Phase 536の11行

Phase 536はPhase 535から学習者版だけを同じ行位置の11行で変更した。

| 行 | 旧境界 | Phase 536 |
|---:|---|---|
| 25187 | metazo/oj | meta/zo/oj##偽分解##エス的分解 |
| 32434 | protozo/oj | proto/zo/oj##偽分解(PIV正式分解) |
| 46064 | briozo/oj | bri/o/zo/oj##偽分解##エス的分解 |
| 47035 | ekinozo/oj | ekin/o/zo/oj##偽分解##エス的分解 |
| 51860 | mejbomit/o | mejbom/it/o##偽分解(PIV正式分解) |
| 51962 | metazo/o | meta/zo/o##偽分解##エス的分解 |
| 51998 | mezozo/oj | mez/o/zo/oj##偽分解##エス的分解 |
| 53060 | parazo/oj | para/zo/oj##偽分解##エス的分解 |
| 53963 | protozo/o | proto/zo/o##偽分解(PIV正式分解) |
| 55348 | sporozo/oj | spor/o/zo/oj##偽分解(PIV正式分解) |
| 61795 | protozo/oz/o | proto/zo/oz/o##偽分解(PIV正式分解) |

Phase 536学習者版:

- bytes: 4,373,339
- SHA-256:
  91196CE5CEAC8E0B6A3EBF108B3B3F4E66EE35CD96EB7107E52DEE3DE227DA89
- 行数: 62,313
- CRLF: 62,313
- bare LF: 0
- BOM: なし
- 偽分解: 3,541
- PIV正式分解マーカー: 1,495
- 衝突語: 62
- 過細分解: 682
- 強語根: 206
- エス的分解: 85

学術版は引き続き次のSHAでバイト不変だった。

FE632820E7752A555787C926C0A843CD82B2F79D4177A6D8D1E9622CA96393A5

11行を仮想的に逆適用するとPhase 535学習者版SHA
5C585494EE744912C77DBF246F77C8AB6D56428293FCB7B672E75C41623A5587
を完全再現した。見出し文字、定義、行数、改行形式は不変である。

この11行は辞書・漢字化軌道の深い分解候補であり、ルビ軌道へ自動注入していない。
Phase 536を凍結入力としてアプリ全体を再生成・再認証する作業もまだ行っていない。

### 9.5 Phase 537の観測点

22:49:25時点でPhase 537用の読み取り調査ファイルがD:\tmpに生成中だったが、
公式Phase 537記録はまだ存在しなかった。phase537 snapshotの全15ファイルは、
ファイル名と内容SHAがPhase 536 snapshotと全件一致し、学習者版・学術版も
それぞれバイト同一だった。

- 学習者版SHA:
  91196CE5CEAC8E0B6A3EBF108B3B3F4E66EE35CD96EB7107E52DEE3DE227DA89
- 学術版SHA:
  FE632820E7752A555787C926C0A843CD82B2F79D4177A6D8D1E9622CA96393A5
- Phase 536からの本文差分: 0

よって本ログはPhase 537を「完了」と扱わず、上記時刻で調査中として隔離する。
後続書込みがあれば、別の凍結pinとして改めて監査する。

## 10. 漢字化軌道

最初の歴史pin:

775c3692be7b39aea9d8cd8481d6bce86182120e

このpinまでの関連コミット:

- ab143f7: Phase 533の8行
- faaea07: Phase 534の辞書5行に加え、neornit、ortognat、prognat族、
  pterodaktilの漢字false-friendを修正
- 74f7a66: Diodon、Megatherium、Pteranodonと、学習者版megafonを修正
- 775c369: 学術版megafonをmillion系からgiant系へ修正

22:49時点のlive HEADとremote mainは同じ次のcommitまで進んでいた。

1faf02686f3f8f04fb07f26b1435e4117df1b5da

775c369以後の4コミット:

- 9782f43: 学習者版のlit、mi、bat、haloの4系列を是正
- 4b049bf: 学術版7語のfalse-friend修正と、Phase 536の-zoo/mejbom同期
- 6b103f9: akant系列を是正
- 1faf026: ant、bi、kromの3系列を両版で是正

同時点の漢字マスター作業ツリーはtracked/untracked合計53件で、status本文SHAは
FEB1ED19346D53CF6B562CB74E0E239198D4960A7E049C849B128C57AE442566
だった。この件数は時点付き観測値であり、後続セッションにより変化し得る。

775c369や1faf026というcommit自体はimmutableで、clean checkoutできる。吸収を保留する
理由はcommitが「汚れている」からではなく、775c369以後の4コミットと作業ツリー上の
後続変更をアプリ側でまだ全監査しておらず、別の変化を混ぜないためである。
現在の注入結果には深い分解が反映される一方、odontなど未割当の拘束形式は
リテラルとして残る場合がある。これは漢字マスター側の別軌道で裁定する。

Phase 532アプリ候補では、漢字化の保護対象9ファイルは親コミットとバイト同一であり、
注釈ルビの修正が漢字化を壊していない。

## 11. 証拠ファイル一覧

| 種類 | 所在 | SHA-256または識別子 | 保存状態 |
|---|---|---|---|
| Phase 532 full report | D:\tmp\esperanto_master_3lang_phase532_postregen_06fdb7b_20260718.json | CDF34C3EF894CF8C1C6FD3243320186E41035E0D109062F9D2482719726783AF | ローカル一時領域 |
| no-worsening結果 | _analysis_20260625/out/_audit_no_worsening_current_only.json | 31CF40BABF0426B4EBAE233C989640923B2CB0F1080201961FE117A558DA769C | Git追跡・main採用済み |
| Phase 532候補authority | _analysis_20260625/out/_audit_no_worsening_references_phase532_candidate.json | 7DE0A31F6BD455EDB5E8730284E6B8EB04A5557BACE4BD5B719313DE67182C92 | Git追跡・main採用済み |
| Phase 534 learner snapshot | D:\tmp\phase534_learner.txt | 5C585494EE744912C77DBF246F77C8AB6D56428293FCB7B672E75C41623A5587 | ローカル一時領域 |
| Phase 534 candidate manifest | D:\tmp\phase534_fake_coarse_reference_candidate.json | 3E7EA483AC171A1F2A195C6B856D7B7B2E901328A10BFA500554A3B0CF5B1358 | ローカル一時領域 |
| Phase 534初期記録（表現過大・後に訂正） | D:\tmp\phase534_record.md | D07F5BCF1B8B13238BBE59CBC8607508F8D846FDA8361CE0BD924CC6035E48D8 | 歴史証拠 |
| Phase 532修正版記録 | phase535 snapshot内のPhase532記録 | AC7BAF45E2E27AE59ACD3D3E1BA1392E5003D6A568D9BA88FF53D9F1781F430D | ローカルsnapshot |
| Phase 533修正版記録 | phase535 snapshot内のPhase533記録 | 11BDE17C6260EA8EEEEEA80E85BCD23553760C9FCB3A14C27CA0CC26E326C756 | ローカルsnapshot |
| Phase 534修正版記録 | phase535 snapshot内のPhase534記録 | E8D8F7046D1E47747C3875809A1DD0FB86E43F50BDEFAA0C5454A90B8149E62D | ローカルsnapshot |
| Phase 535公式記録 | phase535/536 snapshot内のPhase535記録 | 07B75FAB3374C228BEF241323136606553705FD0D1D6E074A123FFC5255B9FEC | ローカルsnapshot |
| Phase 536 learner | canonical辞書とphase536/537 snapshot | 91196CE5CEAC8E0B6A3EBF108B3B3F4E66EE35CD96EB7107E52DEE3DE227DA89 | Google Drive正典＋snapshot |
| Phase 536公式記録 | Phase536_PIV親根再監査とzo動物族遡及整合_記録_20260718.md | 4510A2718BA6F33B097F6195837E7A1DF4F7BDEAEBCB1D466A68719C1303DB97 | Google Drive正典＋snapshot |
| Phase 537調査代表 | D:\tmp\phase537_target_logs.txt | F0BFAD23DF3008ABCF0E0AA4B0704FDF1C9AD9E07CBC2B0A857F89247694B195 | 未確定の一時調査物 |
| Phase 537最新観測物 | D:\tmp\phase537_piv_suffix_headers.txt | 14EEEDC099EE82D6EECA3D01D18D606FB0E672554D2463DB0D80567B8912D613 | 未確定の一時調査物 |
| Phase 532実装・テスト・台帳 | Git commit 93a887e559171acb18122e31fd146c1822a015e1 | commit | PR #6経由でmain採用済み |
| Phase 532 merge | Git commit 89fa012a3f80a1547b73c4d98d6ceab9fd548257 | commit | GitHub main |
| 漢字live pin | Git commit 1faf02686f3f8f04fb07f26b1435e4117df1b5da | commit | 漢字remote main |
| 本統合ログ | 本ファイル | commit後に固定 | 文書専用draft PR |

一時領域の大型ファイルそのものはGitHubへ入れていないため、消失耐性はGit追跡物より低い。
表に掲げた各証拠は完全なSHA-256と主要集計値を本書へ固定したので、残存ファイルの
別内容へのすり替えは検出できる。ただし、消失したファイルをSHAだけから復元はできない。
次回の正式再生成では、必要な凍結入力をGit追跡または再構築可能なmanifestへ移す。

## 12. 再検証の入口

主要な実装・検証入口は次のファイルである。

- _analysis_20260625/phase532_ruby_policy.py
- _analysis_20260625/phase532_activation.py
- _analysis_20260625/phase532_runtime_signature_gate.py
- _analysis_20260625/phase532_authority_carry_forward.py
- _analysis_20260625/adopt_phase532_no_worsening_candidate.py
- _analysis_20260625/no_worsening_audit.py
- _analysis_20260625/test_phase532_ruby_policy.py
- _analysis_20260625/test_phase532_activation.py
- _analysis_20260625/test_phase532_authority_carry_forward.py
- _analysis_20260625/test_no_worsening_audit.py

再実行時には、入力SHAとworktree clean条件を先に確認し、候補生成、runtime signature、
full master audit、no-worsening、3言語一致、幅、生成物diffの順にゲートを通す。
最初のwriterより前にpre-runtime permission gateを置き、失敗時の部分更新を防ぐ。

## 13. まだ完了していないもの

1. Phase 533〜536をcleanな凍結点からアプリへ再生成し、全ゲートを再実行すること。
2. Phase 537が正式記録と本文を確定した場合、別pinとして差分を再監査すること。
3. 漢字マスター1faf026までの後続4コミットを監査し、clean checkoutから別軌道で吸収すること。
4. Phase 532で現行ルビを維持した51表現中、未裁定21表現を個別に最終裁定すること。
5. 偽分解と粗いルビの不一致2,575件を、自動同一化せず個別に裁定すること。
6. fully-naked lexical候補45件とnonterminal naked fragment候補202件を言語別に残査すること。
7. 一時領域だけにある大型監査証拠の再構築可能性をさらに高めること。
8. 京大HTMLに将来真の誤りが見つかった場合だけ、最小修正を別コミットで行うこと。

## 14. 結論

約6時間分の「逐語的な端末録画」は存在しない。しかし、捜査の再現に必要な主要入力、
SHA、差分、監査結果、テスト、Git履歴は残っている。本書をGitへcommitし、
一つの恒久台帳として固定する。

Phase 532では、京大エス研HTML169ファイル、master 62,313行、JA/ZH/KOの境界、
非悪化、CSS実効幅、漢字保護面を検証し、採用必須ゲートは全て合格した。
全偽分解3,517行を粗いルビへ一致させるall-fake-coarse gateは意図的に非強制であり、
2,575件は個別裁定待ちである。その実装93a887eは、外部merge commit 89fa012を通じて
アプリmainへ採用済みである。

Phase 533〜534の13行とPhase 536の11行は差分と意味を調査済みだが、まだアプリへ
吸収していない。Phase 535は本文不変、Phase 537は未確定調査中である。
この線引きを守り、このセッションからmainへ直接pushせず、文書専用draft PR上で
本ログを固定して、次の凍結・再生成・再認証を待つ。
