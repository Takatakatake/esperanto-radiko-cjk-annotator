# Phase 597 / 第72R `di`（神／二）意味衝突監査ログ（2026-07-26）

## 結論

同綴りの `di` には、通常語根「神」と科学結合辞「二／di-」がある。
現行の注釈ルビでは、宗教・神学語25キーの `di` に科学義が誤って
割り当てられていた。

この変更は、レビュー済みの宗教語だけを次のように直す。

- JA: `二` → `神`
- ZH: `二` → `神`
- KO: `이` → `신`

語根境界、置換元、placeholder、CSS class、他の `rb/rt`、漢字トラックは
変更しない。科学語22キーは「二／二／이」のまま、一般動詞
`send/i` は「送る／送／보내다」のままである。

## 二軌道と閉集合

ポリシー正本は
`_analysis_20260625/reviewed_di_semantic_policy.py` に集約した。

- word_anno authority: 宗教語25キー
- 明示的な科学陰性 authority: 22キー
- 配信ルビ authority: casefold一意89表層
- 配信global規則: 273規則／言語、計819規則
- local / two-char規則: 対象0

配信修正は表層名だけでなく、既存の粗ルビpiece署名も照合する。
対象表層でpiece位置、個数、旧／新glossが想定外ならfail closedとする。
汎用 `di` 置換や前方一致は導入していない。
さらに、配信規則を総数だけで認証せず、87表層は各3規則、
`diigi`・`diigu` は各6規則という表層別Counterまで固定した。
1表層の欠落を別表層の重複で相殺することも許さない。

特に次を分離した。

- `sen/di/a`, `sen/di/e`, `sen/di/o`: `di=神`
- `send/i`: `send=送る`、`di` pieceなし
- `di/oksid/o`, `karbon/di/oksid/o` 等: `di=二`

## 正本 word_anno の限定差分

JA・ZH・KOの canonical out と app_data copy について、親commitとの差を
JSON意味単位で全キー比較した。

- 変更キー: 各言語ちょうど25
- 追加／削除キー: 0
- 各キーの変更piece: 唯一の `di` だけ
- `di` 以外のpiece、gloss、並び: 全て不変
- canonical と app_data の対象集合: 完全一致

三言語境界manifestは変更前後で同一である。

- authority keys: 49,344
- authority SHA-256:
  `BCC54D10968FE1BF628C1A2B2764BC32E142C85A6084E523C1BAB6CF13E65D01`
- JA key count: 49,305
- ZH key count: 49,344
- KO key count: 49,344

最終canonical word_anno SHA-256:

- JA:
  `44E8E02846C32B6185F2DA94DAAADA000F2DABD247BB6113CC8B2ACF223FFFE5`
- ZH:
  `05FF5B8E63723553FEBB727A7D41851F3A6EE6500184388D9A9131797CE1236C`
- KO:
  `D97557E91445F9C54847C6C3D5C5E88C1BDB9BBA343A6996945BDAC133764924`

## 配信ルビJSONの限定差分

親commitと最終候補の全規則を、bucket・順序・各配列要素ごとに比較した。

- JA: 273規則、89 casefold表層だけ変更
- ZH: 273規則、89 casefold表層だけ変更
- KO: 273規則、89 casefold表層だけ変更
- 規則追加／削除／並べ替え: 0
- `old` key: 全て不変
- placeholder と追加metadata: 全て不変
- 変更規則内の差: 唯一の `di` の `rt` 一字だけ
- `rb`、CSS class、`<br>`、他のruby、裸文字: 全て不変
- 対象外の全規則: JSON意味単位で完全同一

`diigi` と `diigu` には末尾境界違いの既存規則が各2系列あるため、
89表層×3 caseの267に6規則を加え、273規則／言語となる。

最終配信ルビJSON SHA-256:

- JA:
  `23EF953A9FB8540A668903E04A27D41C3EF70AD9691EDD09FB9153079BCF6029`
- ZH:
  `B9DBE076E7B0E1FB9BAACE360022C7E275F731127205550460A13FDFCDE9A12D`
- KO:
  `47386A47492045316B0AD2CEBCF26E727A30B35B68AA7527D5A22B6AD50B275E`

postregenの2回目実行は JA/ZH/KO 全て変更0で、冪等である。

## 表示幅

変更前後の文字幅は言語ごとに同値である。

- JA/ZH: `二=16`, `神=16`
- KO: `이=14.725000381469727`, `신=14.725000381469727`

従ってCSS classと改行位置を変えていない。幅を短くするために語根を
細分化した変更でもない。

## 漢字トラック非変更

Git差分に漢字成果物はなく、SHA-256も親commitと同一である。

- JA HTML漢字:
  `92EE01E3C78D84A726D611F60B0068C0BFA764518795E447D503C11C9ECC06D6`
- JA 純粋漢字:
  `BA21672B9C89913622BB1CCF0A280D7FB32B779ED9DE89CB30B8D69C3125D507`
- ZH HTML漢字:
  `A0F9881BD10404C8DA92FA3458DB01DB2D77262A8AD0EE81BB8949D5C8698C77`
- KO HTML漢字:
  `90E838156C7009B6C950E409EE84CD74DA086BA89B72F32B0C0E27E2E6D9B2EF`

学習者版の偽分解・深分解を含む漢字authorityには触れていない。

## 固定Phase 597全件監査

入力:

- app parent:
  `2e05403756db6a4d1081bdd0ef95add77c3bfa87`
  （第71R `dinamism` 粗ルビ候補）
- learner:
  - 62,313行
  - SHA-256
    `9A610D086E60A1863E1D59D61FE0F844B3EACF4DCEBDBF6AE6354E0D16D99700`
- academic:
  - SHA-256
    `63DAB5BAF932605A2D94843AD249FBE32CB1E8A40B8D244714A17744C0384261`

会計:

- input lines: 62,313
- comment exclusions: 202
- runtime candidate lines: 62,111
- runtime unique surfaces: 61,844
- render union surfaces: 62,305
- legacy fast subset: 55,383
- 未評価runtime行: 0

結果:

- JA/ZH/KO render-union境界不一致: 0
- full exact境界不一致: 0
- legacy fast境界不一致: 0
- token context境界不一致: 0
- runtime error: 0
- visible reconstruction failure: 0
- placeholder残留: 0
- empty `rt` / `rb`: 0
- unknown width character: 0

CSS適用後の最大行幅比:

- JA: `1.533750021457672`
- ZH: `1.366875010728836`
- KO: `1.1043750286102294`

全言語で実効幅2超過は0。

Phase 597 fake/coarse authorityは各言語:

- matched: 1,039
- mismatched: 2,569
- reviewed transition: 157/157

clean Phase 597の1,037/2,571との差2件は、親第71Rの
`dinamismo`, `elektrodinamismo` 粗化であり、今回のgloss変更は境界数を
変えていない。

top-level `gate=false` は意図どおりである。未裁定2,569件と
retired transition 1件を一括で本番認証しないためのpromotion gateであり、
今回のruntime gateは `true` である。

完全レポート:

- path:
  `D:\tmp\phase597_r72_di_full_3lang_audit_20260726.json`
- bytes: 8,353,393
- SHA-256:
  `4F6F0B9271A76498868DBF726557F80D13084CD9FD7A5DC40C00A1034086BFA4`
- 全入力安定性:
  gold / academic / HEAD / tracked worktree / app inputs / audit script /
  authority manifests / candidate files = 全てtrue

共有ポリシーへのコード整理はこの全件描画後に行ったが、配信JSONは
postregen再実行で三言語とも変更0、上記payload SHAのままである。
整理後に62件の生成回帰と三言語構造・異常監査を再実行している。
独立レビューで指摘された前方一致、全bucket走査、CSS class再生成、
`send` の任意gloss許容、表層別多重度未固定も全て閉じた。

## 回帰ゲート

- `python _analysis_20260625/test_generation_regressions.py`
  - 62/62 PASS
- `python _analysis_20260625/check_multilingual_structure.py`
  - 各572,356 global rules
  - duplicate old key 0
  - visible reconstruction diff 0
  - 三言語 keyed R/L/PAD structure diff 0
- `python _analysis_20260625/anomaly_scan.py`
  - Ruby/漢字6 JSONすべて異常0
- `python _analysis_20260625/build_word_anno_boundary_manifest.py --check`
  - pin一致
- Phase 532 deployed runtime gate
  - 58/58、三言語不一致0、gate true
- Phase 558 deployed runtime gate
  - scope/gloss/payload variant全gate true、三言語不一致0
- `python _analysis_20260625/test_canonical_corpus_surfaces.py`
  - 5/5 PASS
- `python _analysis_20260625/test_phase558_ruby_overlay.py`
  - 18 PASS、external-source 2 skip
- `python _analysis_20260625/test_phase558_no_worsening_sidecar_gate.py`
  - 22/22 PASS
- `python _analysis_20260625/test_reviewed_exact_manifest.py`
  - 5/5 PASS
- `python _analysis_20260625/check_kanji_fake_decomposition.py`
  - 各53件、mismatch 0
- `python _analysis_20260625/check_kanji_structure.py`
  - source保持、duplicate 0、pure derivation diff 0

## 監査根拠と残キュー

read-only意味監査:

- `D:\tmp\phase597_di_semantic_audit_20260726.md`
- SHA-256:
  `E13F40BA39886EA3BB91EC7B4943F9DB01463215F00EC6E14902BF8060FCA1B1`

全62Kの形式監査は、全語の訳語意味を自動認証するものではない。
未裁定2,569件は引き続き個別審査する。既に別のread-only監査で、
物理語 `fonono/fotono/gangliono/gigaelektronvolto/magnetono/mezono/
nukleono/termoelektrono` の `on` 意味衝突を次の通常語優先キューとして
閉集合化しているが、この第72Rへは混ぜていない。

京大HTMLの `iniciatoro` 1件も別commit候補である。最新remote
`7c04f97c51a7cecf88918d2abc2e6bf2f34601a6` 上の1行修正だけを保持し、
旧Phase 532/558 authorityを直接書き換えず、corpus commit確定後に
versioned successor ledgerを生成する。
