# Phase 619 京大基準・普通語ルビ再認証 監査ログ

記録日: 2026-07-29（Asia/Tokyo）

## 1. 結論

今回アプリへ採用したのは、凍結した Phase 619 マスターから人手で選別した
**普通語7語の注釈ルビ修正だけ**である。

- 注釈ルビは、京大エス研 HTML 程度の粗い語根境界を採用した。
- 漢字化は、学習者版マスターの偽分解・深い分解を従来どおり保持した。
- JA/ZH/KO の `R`（Ruby）/`L`（literal）境界と `rb` は完全一致した。
- 幅を短くする目的で語根を細分化していない。
- 実表示幅は、全62,313入力行の正式監査でも全言語2倍未満だった。
- 固有名詞の変換規則は追加・変更していない。
- 京大エス研 HTML 本文は、最新 `origin/main` がすでに修正済みだったため変更していない。
- 漢字成果物9本は親コミットとバイト単位で同一である。

したがって、今回の変更は「ルビを粗く、漢字を偽分解に忠実に」という二軌道原則を
崩さず、既存の普通語処理を狭い閉集合から汎用的な語尾展開へ改善したものである。

## 2. 絶対に崩さない原則

1. 注釈ルビと漢字化を別トラックとして扱う。
2. 注釈ルビは京大エス研 HTML 程度の粗さを基準にする。
3. 漢字化は学習者版マスターの偽分解・エス的分解・過細分解指定を尊重する。
4. 粗さが違っても、注釈ルビの JA/ZH/KO 境界は完全一致させる。
5. ルビの実表示幅を原アルファベット幅のおおむね2倍以内にする。
6. 幅だけを理由に、意味のある長い語根を細かく割らない。
7. 更新中の live master を直接認証しない。bytes・行数・SHA-256 を固定した
   snapshot だけを認証する。
8. 固有名詞より普通のエスペラント語を優先する。
9. 京大エス研 HTML と修正ガイドは、既に磨かれた基準資料として扱い、
   明白な誤りがない限り一括書換えしない。
10. 不一致候補を直ちに誤りとみなさず、二軌道上の意図的差異を残す。

## 3. 作業場所と親状態

### アプリ

- 独立 worktree: `D:\tmp\r78_root_app_20260729`
- branch: `agent/r87-phase619-kyoto-recert`
- 親 commit:
  `8af4c19f50ea34d8c84767173c716e9b3f45ec5c`
- repository:
  `https://github.com/Takatakatake/esperanto-radiko-cjk-annotator.git`

### 京大エス研 HTML

- 独立 worktree: `D:\tmp\r78_root_corpus_20260729`
- branch: `main`
- `HEAD == origin/main`:
  `d1642c276857c1fe400a6d597214ff7a923e7bd2`
- worktree: clean
- 内容ファイル: 169

共有 Google Drive 作業ツリーへ直接書き込まず、独立 worktree だけで調査・再生成した。

## 4. 以前の長時間捜査ログ

以前の約6時間にわたる監査の根拠は、次の tracked 文書に残っている。

- `_analysis_20260625/PHASE532_537_CONSOLIDATED_AUDIT_LOG_20260718.md`
- `_analysis_20260625/PHASE558_RUBY_OVERLAY_AUDIT_LOG_20260722.md`
- `_analysis_20260625/PHASE595_R71_TWO_TRACK_AUDIT_LOG_20260726.md`
- `_analysis_20260625/PHASE597_R72_DI_SEMANTIC_AUDIT_LOG_20260726.md`
- `_analysis_20260625/PHASE598_R73_TECHNICAL_ON_AUDIT_LOG_20260726.md`

`D:\tmp` や `D:\fuyou` の snapshot・巨大レポートは補助証拠であり、一時領域が
消えても判断根拠を追跡できるよう、本ログ、review JSON、activation JSON、
transition ledger、再生成スクリプト、テストを repository 内へ残した。

## 5. Phase 619 の凍結入力

snapshot directory:
`D:\tmp\r78_phase619_snapshot_20260729`

| 入力 | bytes | 行数 | SHA-256 |
|---|---:|---:|---|
| 学習者版 | 4,374,847 | 62,313 | `4D89CD96F27D635DDC0EBC08F37DC7B211481F844C1AAE6922EB65749ACBB0D2` |
| 学術版 | 4,277,594 | 62,313 | `8E5D317521F2399168BA37DD4AA6A9944B98E1E1D717BE6B0989AE753E6CC7F5` |
| PEJVO 原典 | 2,841,948 | 44,104 | `EFE44C8E85F76CAA8C2C55F3FE1F64CCD2001B381E520D6386670D29D57DBB34` |
| fake/coarse manifest | 1,028,015 | 40,650 | `003FAE11D93499AD3D737EE6D31A759F4D0A9BF9EDBCC916B64B22BCBB6AF420` |
| transition dispositions | 1,100 | 24 | `42D30B155CCEF9832189C382EE2049B89350DA0BFAD5C774E4268D86D90164F6` |

マスターがこの後も更新され得ることは前提に含めた。今回認証したのは上記 snapshot
だけであり、これより新しい live master の全差分を吸収したとは主張しない。

## 6. 京大ガイドの照合

参照元:
`D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\Esperanto_HTML文書\京大エス研html文書＿Github\esperanto_html_redaktado`

| ガイド | bytes | 行数 | SHA-256 |
|---|---:|---:|---|
| `エスペラントルビHTML修正ガイド260328.txt` | 131,181 | 1,835 | `B8F21605E019A394560A6E4ED5238FE4BEDE7B2A949A0CBC6927189ADADFB965` |
| `世界语HTML修正指南_中文注释版.txt` | 118,657 | 1,907 | `A3AF2F18004A63A2C6ECB438B9ABBABF62A9B40D15494FC6B6FC0CADA7ECEA46` |

旧コピーではなく、段落・形式が整えられた最新 remote 系列のガイドを使用した。
ガイド本文自体には変更を加えていない。

## 7. 採用した普通語7件

| 表層 | 注釈ルビの分解 | JA / ZH / KO | 漢字側に残す学習者版分解 |
|---|---|---|---|
| `imperialisto` | `imperialist/o` | 帝国主義者 / 帝国主义者 / 제국주의자 | `imperialist/o` |
| `provincialismo` | `provincialism/o` | 地方なまり / 地方口音 / 지방 사투리 | `provincialism/o` |
| `endoskopio` | `endoskopi/o` | 内視鏡検査 / 内镜检查 / 내시경 검사 | `endo/skop/i/o` |
| `mikroskopio` | `mikroskopi/o` | 顕微鏡検査 / 显微镜检查 / 현미경 검사 | `mikro/skop/i/o` |
| `mukozaĵo` | `mukoz/aĵ/o` | 粘膜＋事物 / 黏膜＋事物 / 점막＋사물 | `muk/oz/aĵ/o` |
| `ditionato` | `ditionat/o` | ジチオン酸塩 / 连二硫酸盐 / 디티온산염 | `di/tion/at/o` |
| `tetrationato` | `tetrationat/o` | テトラチオン酸塩 / 连四硫酸盐 / 테트라티온산염 | `tetra/tion/at/o` |

6件は注釈ルビ上の長い一語根、`mukozaĵo` だけは実在する接尾辞 `aĵ` を保つ
`mukoz/aĵ/o` とした。学習者版の深い分解をルビへ流用していない。

review:
`_analysis_20260625/_phase619_ordinary_ruby_review.json`

- raw SHA-256:
  `5BA83778181568ED90D989A4AFE866059F759DA2F46B7F6D8746FAFCEAAD4C4F`
- entries SHA-256:
  `D96EED41AE3E8716052E2138E0E9D8E7286974A1EF522E399DFB9175E4CB8CC1`

activation:
`_analysis_20260625/_phase619_ordinary_ruby_activation.json`

- raw SHA-256:
  `ED36C43C04CA37232874C8FA905783B99D69907B2F1C0BA3388A08A27193F268`

## 8. 汎用化の範囲

7語を単発の表示置換だけで直すのではなく、既存のアプリ生成機構へ次の制約付きで
統合した。

- `ruby_track_only=true`
- 語全体境界付き
- 通常10語尾:
  `a, aj, ajn, an, e, en, o, oj, ojn, on`
- 3 case variants:
  lower / initial / upper
- 7語 × 10語尾 × 3 case = 210 positive surface / language
- JA/ZH/KO に同じ型付き境界を生成
- 局所化注釈は各言語で個別に与える
- 漢字生成規則・漢字 payload へは適用しない

64 negative surface については、Phase 619 専用注釈の漏洩がないことと
JA/ZH/KO 境界一致だけを確認する。現在の誤解析や誤訳まで正解として固定しない。

## 9. 京大 corpus の最新化

親アプリが参照していた corpus 系列から、最新
`d1642c276857c1fe400a6d597214ff7a923e7bd2` へ authority を更新した。

- raw Ruby: 348,580
- parsed Ruby: 348,580
- parsed units: 270,763
- canonical evaluable instances: 269,577
- canonical surfaces: 21,438
- reviewed exact surfaces: 625

最新 HTML で既に修正された次の旧 typo exact rule 3件だけを閉集合で retire した。

- `bonŝanĉulo` → `bonŝanculo`
- `fronantaj` → `frontantaj`
- `jurnal` → `ĵurnal`

`fronantaj` の旧 case-sensitive pin を退役した後、正しい `frontantaj` は既存の
生産的 `fron/ant/aj` 経路で処理される。`jurnalisto` の境界付き互換規則は残し、
標準綴り `ĵurnalisto` も別途 runtime で確認した。

transition ledger:

- `_analysis_20260625/_corpus_reviewed_exact_transition_d1642c2.json`
  - SHA-256:
    `E4A77FD506FE17FC04543DE37560EBAB3A1E869AAD0E5C231C718DF1530AABD8`
- `_analysis_20260625/_word_anno_boundary_transition_d1642c2.json`
  - SHA-256:
    `B1D463020035272B9A9C5C64AD881603E2609371FD8EA3EF590E82CB5BF6E2D4`

typo retirement 後の authority 49,348 key に Phase 619 の7 key を加え、最終
authority は 49,355 key となった。

- authority SHA-256:
  `521A26E54F7C124652A9D7F3F375AAA620D7E13DAE7302197992A43FA50D9A08`
- final key counts:
  JA 49,316 / ZH 49,355 / KO 49,355

言語ごとの総 key 数は既存の言語固有注釈のため同数ではないが、同じ Esperanto
表層に対する型付き `R/L` 境界は完全一致する。

## 10. 再生成と歴史 overlay の保護

1. R67/R68 overlay を再生成前に capture した。
2. Phase 532/558/598/619 の prewrite gate を通した。
3. 3言語の Ruby 設定・置換リストを再生成した。
4. R67/R68 overlay を同じ行・同じ順序で復元した。
5. postregen、京大 meaning-break、hyphen-joiner、ZH/KO diminutive を順番どおり再適用した。
6. 全 gate と overlay identity を再検証した。

R67/R68 capture:
`D:\tmp\r87_phase619_r67_r68_overlay_snapshot.json`

- SHA-256:
  `4A8A0686B27128E69D2F0F0891743461FE9206C1A707EC6FFCC2FEF4A59535CD`

| 段階 | JA | ZH | KO |
|---|---:|---:|---:|
| R67/R68 復元直後 | 572,713 | 572,713 | 572,713 |
| 全 post overlay 後 | 572,729 | 572,729 | 572,729 |

R67/R68 の行内容・順序・言語別 SHA は capture と完全一致した。

## 11. 62,313行 × 3言語の正式監査

正式レポート:
`D:\tmp\r87_phase619_full_report_after7_authorized_20260729.json`

- bytes: 8,346,547
- SHA-256:
  `7C7549784D4E8D8B92FEA693DE07DFE498DBC79AFCEF5D3F1DC27682325916B3`
- `complete=true`
- `gate=true`
- broader Phase 619 master promotion: `false`
- seven ordinary-word Ruby sidecar adoption: `true`

| 指標 | 結果 |
|---|---:|
| 入力行 | 62,313 |
| コメント除外 | 202 |
| runtime 行 | 62,111 |
| unique runtime 見出し | 61,844 |
| render union | 62,305 |
| legacy fast scope | 55,383 |

JA/ZH/KO の次の不一致・異常はすべて0だった。

- render union boundary mismatch
- full exact boundary mismatch
- line occurrence boundary mismatch
- legacy fast boundary mismatch
- token context mismatch
- runtime error
- visible failure
- placeholder residual
- empty `rt`
- empty `rb`

これは三言語の分解境界・HTML構造一致の証明であり、62,313入力行に関する全訳語が
意味論的に完璧であるという主張ではない。訳語の自然さは別の個別監査対象である。

## 12. ルビ幅

全62,313入力行の最終 CSS 適用後実表示幅:

| 言語 | 最大比 | 2倍超過 |
|---|---:|---:|
| JA | 1.533750 | 0 |
| ZH | 1.366875 | 0 |
| KO | 1.104375 | 0 |

Phase 619 の210 positive surfaceだけでは、最大比は次のとおりだった。

- JA: 0.899598 以下
- ZH: 0.898876 以下
- KO: 0.868610 以下
- 自動 `<br>`: 0

幅は表示ゲートとして用いたが、幅を短くする目的の追加分解は行っていない。

## 13. 漢字トラックの非破壊確認

次の9成果物は親 `8af4c19` と bytes・SHA-256 が完全一致した。

| 成果物 | bytes | SHA-256 |
|---|---:|---|
| 3言語の master CSV と `out/kanji_root.csv`（各ファイル） | 152,797 | `89ABFF590A9D0306534A3F7BA3DE58DB93CAD1186FA236D2C8F3C63C78270CF3` |
| JA Kanji JSON | 57,249,401 | `644B823BD1C8D6ACCCEE75FBA6A3E6E2D7870B6AAB37CF158460817A066488FE` |
| ZH Kanji JSON | 57,254,585 | `DE0A149325B481C30F82B8F4669920132DD34CACD4C30FE9D2B0A643FDB63FEF` |
| KO Kanji JSON | 57,254,585 | `29B7D78681402AA65C0B99DE009CDE0F3CCDB9B6E07526D6A7579ABE3A09C71B` |
| JA pure replacement JSON | 21,417,477 | `988E2A5616976D2A7B6E872AA8089ED49AB5A13830BD516F967AC304C446F285` |
| `out/word_kanji.json` | 2,442,258 | `3BA6773B07293E8FF736BD37DD03E0BB5E2A6D3A4514E0A59F5B42F23FB5F78A` |

偽分解漢字の reviewed 53件 × 3言語も mismatch 0 だった。

### coverage-only 監査

report:
`D:\tmp\r87_phase619_kanji_coverage_report_20260729.json`

- bytes: 3,266
- SHA-256:
  `7C60382CC08EA4AF55F43FAC757DBF61D871F88D4E296BEAC2045EAED9244506`

| 指標 | 結果 |
|---|---:|
| 学習者版入力 | 62,313 |
| projectable rows | 62,085 |
| unique nonempty key | 52,775 |
| direct-covered key | 44,284 |
| direct-covered rows | 52,636 |
| uncovered key | 8,491 |
| uncovered rows | 9,449 |
| covered piece drift | 0 |
| evaluable fake rows | 3,644 |
| direct-covered fake rows | 3,445 |
| uncovered fake rows | 199 |

- unique-key coverage: 83.910943%
- row coverage: 84.780543%
- fake-row coverage: 94.538968%

これは direct `word_kanji` key の coverage と、対応済み piece 列の一致だけを
証明する監査である。未対応8,491 key を欠陥と断定せず、fallback・literal・
per-root 経路を含む全配信漢字レンダリングの意味忠実性も証明済みとはしない。

report 内でも明示的に次を記録した。

- `coverage_only=true`
- `direct_word_kanji_source_alignment=true`
- `full_deployed_render_fidelity_certified=false`
- `per_root_rendering_evaluated=false`
- `uncovered_is_not_failure=true`

## 14. 最終テスト

| テスト / gate | 結果 |
|---|---|
| generation regressions | 62/62 |
| Phase 619 ordinary Ruby | 12/12 |
| Phase 619 Kanji coverage-only | 3/3 |
| Phase 558 overlay | 18 pass / 2 skip / 0 fail |
| Phase 598 technical-on | 9 pass / 1 skip / 0 fail |
| R67/R68 carry-forward | 4/4 |
| Phase 558 no-worsening sidecar | 22/22 |
| reviewed exact manifest | 5/5 |
| corpus reviewed-exact transition | 5/5 |
| word-anno boundary transition | 4/4 |
| fake/coarse review drift | 4/4 |
| canonical corpus surfaces | 5/5 |
| multilingual structure | 572,729 × 3、duplicate 0、structure diff 0 |
| raw apostrophe structure | 27 surfaces / 41 instances × 3、failure 0 |
| canonical runtime | 21,438 × 3、residual 0、visible failure 0、placeholder 0 |
| Phase 619 deployed runtime gate | positive 210、negative 64、境界不一致 0、leakage 0 |
| Kanji fake decomposition | reviewed 53 × 3、mismatch 0 |
| Kanji structure | global 515,995 / two-char 330 / local 31,210、diff 0 |
| anomaly scan | 6 JSON、anomaly 0 |
| Python syntax compile | pass |
| `git diff --check` | error 0 |

skip 3件は、今回の正式 Phase 619 snapshot とは別の過去の凍結 source がローカルに
存在しない場合だけ skip する歴史テストであり、失敗ではない。今回の Phase 619
builder、activation、runtime、full snapshot、coverage はすべて実行して pass した。

## 15. 意図的に変更しなかったもの

- 京大エス研 HTML 169文書
- 日本語・中国語の京大修正ガイド
- 漢字マスターおよび配信漢字成果物
- 広範な固有名詞規則
- 語義が曖昧な固有名詞のラテン化・漢字化
- Phase 619 snapshot より後の moving master
- fake/coarse 不一致2,560件の一括強制

`Asirio`、`Moravio`、`Bonaero` に関する ledger 上の分類更新はあるが、関連する
18 case-row の配信結果は親 commit と意味的に同一であり、固有名詞 runtime の
一括変更ではない。

## 16. 残る課題の正確な意味

1. fake/coarse 3,656行のうち、粗いルビ境界と一致したものは1,096、
   深い学習者版分解と異なるものは2,560だった。
   2,560は二軌道原則から期待される候補を含み、自動修正対象ではない。
2. coverage-only で未対応の8,491 keyは、直ちに変換欠陥を意味しない。
   fallback・literal・per-rootを含む別経路の個別監査が必要である。
3. 今回の漢字成果物は親と同一であり、「壊していない」ことは証明したが、
   全62,313語の最終漢字表示を意味論的に一語ずつ証明したわけではない。
4. 新しい master を吸収するときは、再度 snapshot を固定し、今回と同じ
   三言語・幅・二軌道・京大 corpus・漢字非破壊ゲートを通す。
5. 固有名詞は、意味が明確に通るものだけを個別裁定し、普通語を優先する。

## 17. 再現性

正式再生成入口は `_analysis_20260625/regenerate_all.py` である。
Phase 619 では次を明示的に要求する。

- `ESP_GOLD_PATH`
- `ESP_ACADEMIC_GOLD_PATH`
- `ESP_PEJVO_ORIGINAL_PATH`
- `ESP_CORPUS_PATH`
- `ESP_PHASE558_CURRENT_CORPUS_PATH`
- `ESP_PHASE597_CANDIDATE_DIR`
- `ESP_PHASE619_CANDIDATE_DIR`
- `ESP_PHASE619_RUBY_HTML_GUIDE_JA`
- `ESP_PHASE619_RUBY_HTML_GUIDE_ZH`

各入力の場所だけでなく bytes・行数・SHA-256 を照合し、途中で source、app payload、
review JSON、activation JSON が変化した場合は fail-close する。
`apply_confirmed_now.py` も、最初の永続書込み前に Phase 619 deployed runtime gate を
実行する。

本ログを含む commit と remote branch が、今回の永続的な捜査記録となる。
