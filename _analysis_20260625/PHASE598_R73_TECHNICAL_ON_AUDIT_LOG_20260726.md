# Phase 598 / 第73R 技術語 `on` 二軌道監査ログ

監査日: 2026-07-26 (Asia/Tokyo)

## 結論

本変更は、分数語根 `on` と綴りが衝突した技術語8見出しだけを閉集合で
是正する。

- 注釈ルビ: 京大エス研HTML程度の粗さを採り、技術語根を一体化する。
- 漢字化: 学習者版マスターの偽分解・深分解を変更しない。
- JA/ZH/KO: 211表記すべてでR/L境界を完全一致させる。
- `on=分数` の一般規則: 変更しない。
- 語根を短くしてルビ幅を稼ぐ処理: 行わない。

親commitは
`4682D32496F166802B4A2CF28626F376E12AAE3E`
（tree
`2C494DB69EBAC28EF63A192BEFA017A22710CCD7`）である。

## 固定入力

Phase 597 の同時点snapshotを使用した。動いているmasterは直接読んでいない。

| 入力 | 行数 | bytes | SHA-256 |
|---|---:|---:|---|
| 学習者版 | 62,313 | 4,373,830 | `9A610D086E60A1863E1D59D61FE0F844B3EACF4DCEBDBF6AE6354E0D16D99700` |
| 学術版 | 62,313 | 4,277,601 | `63DAB5BAF932605A2D94843AD249FBE32CB1E8A40B8D244714A17744C0384261` |
| PEJVO原典 | 44,621 | 2,211,329 | `B551510513C1924E65E64CF87EA4CE39128E80717E3A3F53847753F8A0557CBF` |

裁定本体は `_phase598_technical_on_review.json` に保存した。

## 8見出しの裁定

| 表記 | 学習者版（漢字track） | 注釈ルビtrack |
|---|---|---|
| `fonono` | `fon/on/o` | `fonon/o` |
| `fotono` | `fot/on/o` | `foton/o` |
| `gangliono` | `gangli/on/o` | `ganglion/o` |
| `gigaelektronvolto` | `giga/elektr/on/volt/o` | `giga/elektron/volt/o` |
| `magnetono` | `magnet/on/o` | `magneton/o` |
| `mezono` | `mez/on/o` | `mezon/o` |
| `nukleono` | `nukle/on/o` | `nukleon/o` |
| `termoelektrono` | `term/o/elektr/on/o` | `termoelektron/o` |

7語根は10語尾×3 caseを限定生成し、`gigaelektronvolto` は小文字の
完全一致1表記だけを登録した。正例は合計211、負例は159、実機監査集合は
各言語370表記である。

## 実機結果

`phase598_technical_on_runtime_gate.py --deployed`:

- 正例: 211/211（各言語）
- 負例: 159/159（各言語）
- JA/ZH/KO境界不一致: 0
- JA/ZH/KO base文字不一致: 0
- payload内正例重複: 0
- unknown幅文字: 0
- 自動`<br>`: 0
- 最大実効幅比:
  - JA `0.8858131458658227`
  - ZH `0.8991469835727427`
  - KO `0.8274962297566243`
- 2倍幅gate: PASS

ルビ幅はArial 16pxの固定幅表を使って実測した。2倍以内に収めるための
追加分解は一切していない。

## 親payloadとの差分閉包

最初の再生成で、後段の歴史的R67/R68 overlayを落とす問題を検出したため、
その状態ではcommit/pushしなかった。
`preserve_r67_r68_ruby_overlays.py` を追加し、親commitから次だけを
transactionalにcarry-forwardするよう修正した。

- R67H: 336行/言語
- R68W: 1,013行/言語
- Auster完全一致override

修正後、57万行級の全payloadを親と比較した。

| 言語 | 親global | 候補global | 許可scopeの削除/追加 | scope外の順序付き保持 |
|---|---:|---:|---:|---:|
| JA | 572,356 | 572,501 | 66 / 211 | 572,290 |
| ZH | 572,356 | 572,501 | 66 / 211 | 572,290 |
| KO | 572,356 | 572,501 | 66 / 211 | 572,290 |

三言語のsource deltaは完全同一で、非global bucketも親と同一である。

最終Ruby payload SHA-256:

- JA `3D9EDF76DC2857350742D9473388AF97C49823DCAF523CD56EE6491C478C6873`
- ZH `0557CBD1DB91F30CF824E27E894E8008F61E2789B24AEEF6922089F1256FE37A`
- KO `CFF51B7F9AA9D251311D78DA5349891350E9379618C8365F00C4BFE6E9CD50E0`

## 漢字track非破壊

Ruby-only保護対象の漢字成果物はすべてHEADと同一である。

- 三言語の漢字割当CSV:
  `6B46C0998D924C6D1A2708061668C307B497F2FF2CC37C2A9F9320525942958C`
- JA漢字JSON:
  `92EE01E3` で始まる既存hashのまま
- ZH漢字JSON:
  `A0F9881B` で始まる既存hashのまま
- KO漢字JSON:
  `90E83815` で始まる既存hashのまま
- JA純粋置換:
  `BA21672B` で始まる既存hashのまま
- `word_kanji.json`:
  `F7DF25BF` で始まる既存hashのまま

## 回帰バッテリー

- Phase 598 policy/runtime: 10/10 PASS
- R67/R68 carry-forward: 4/4 PASS
- generation regressions: 62/62 PASS
- Phase 558 runtime: PASS
- Phase 558 tests: 20（2 skip）
- Phase 558 no-worsening sidecar tests: 22/22 PASS
- canonical gate純粋関数tests: 5/5 PASS
- multilingual structure: PASS
- anomaly scan: 異常0

## 京大corpusに関する別残件

本変更のscope外として、旧 `b769038` と最新 `7c04f97` の双方に、
既存runtime由来の同じ2表記の残差を発見した。

- `Temis` 6例: corpusは普通動詞 `Tem/is`、runtimeは女神名を守ってwhole。
- `iniciatoro` 1例: corpus mainは `iniciat/or/o`、runtimeは
  京大基準の粗い `iniciator/o`。

これはPhase 598追加前の親payloadでも同じ挙動であり、本8語修正による
退行ではない。ただし「残差0」とする過去のtracked canonical reportと
現在の実payloadが一致しないことを確認したため、最新版corpus追従commitで
次のように別裁定する。

- `iniciatoro`: corpus側の限定修正commit `d1642c2` をauthorityにする。
- `Temis`: global分解を禁止し、確認済み長文脈だけを限定修正する。
- 旧canonical reportを合格証拠として再利用しない。

この残件を技術語 `on` の汎用規則へ混ぜないことが、
本commitの非悪化条件である。
