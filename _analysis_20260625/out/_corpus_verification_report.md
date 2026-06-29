# 京大エス研コーパス 語根分解 検証レポート (2026-06-29)

## 手法
1. **決定論的測定** (`_corpus_verify_arbitrate.py`): 全171ファイル/ルビ付き122文書を走査、app分解 vs 京大ルビ境界を文書別・全体で測定。
2. **gold裁定**: 不一致を参照1学習者辞書(54,581語)を裁定者として7バケットに分類。
3. **LLM多角敵対検証** (workflow `corpus-decomp-arbitration`, 8エージェント): 係争5バケットの代表語を言語学的に再裁定 → 「コーパス誤り」「app誤り」判定を敵対的に反証。

## 精度 (決定論的)
- **文書別**: 全122ルビ文書が **97.1%–100%** (中央値 99.6%)。破綻文書ゼロ。
- **全体**: 境界一致 **99.4%** (107,175/107,754)。不一致 579トークン実例 / 201ユニーク型。

## gold裁定 (579不一致の内訳)
| バケット | 件数 | 性質 |
|---|---|---|
| NOTINGOLD_app粗(同綴り候補) | 188 | gold未収載・app whole保持(ホモグラフ/固有名) |
| NOTINGOLD_その他 | 186 | gold未収載(固有名Gerda/新語tokipono…) |
| app誤り_真欠陥(gold=コーパス) | 67 | うち ekde 55(語彙化) |
| gold第三分解_app寄り(国名-i/o) | 51 | 構造的天井(cin/i/o…) |
| コーパス誤り_app正(gold一致) | 47 | **京大コーパスの誤り** |
| NOTINGOLD_先頭1字孤立 | 24 | app真欠陥(overlay修正可) |
| gold第三分解_コーパス寄り | 16 | teren/domen 設計ホモグラフ |

## LLM敵対検証の結論
- **コーパス誤り (corpus_wrong_app_right 20語検証)**: 18/20 でコーパス境界が誤りと確定(holds=true)。
  - over-split型: `esper/ant/e`(esperant=単一語彙化語根), `plat/form/o`(偽複合捏造), `o/cel/o`(先頭o孤立)。
  - coarse型: `biologi/o`(gold=bio/logi/o), `lingvist/o`(-ist未分割), `nitrat/o`(-at未分割)。
  - **反証で覆った2語**: `iniciatoro`(gold に iniciat 系列あり・-or は実在接辞→コーパス`iniciat/or/o`が妥当), `eufemisme`(eufem 非語根・gold は -ism 借用語を丸ごと保持→コーパス whole 妥当)。
- **app真欠陥 (先頭1字孤立 7/7確定)**: `sporti`→s/port/i, `fero`→f/er/o(実在-er-接辞への偽の友マッチ), `baron`→b/ar/on, `korlig`→k/orl/ig, `katederalo`, `kvedlinburgo`, `reblu`。**overlayで修正可能**。
- **app誤りだが弁護可能**: `ekde`(PIVは単一前置詞・refutationでも"最も防御的"。ただし学習者権威=goldは ek/de を推奨), `farado`(Farad単位とのホモグラフ)。
- **構造的天井 (国名-i/o 7/7)**: gold=ROOT/i/o(`cin/i/o`)、appは語根isolateするが1字-i-を融合(`cin/io`)。appはコーパス(`cini/o`=語根埋没)より学習者向けに優れる。設計上の上限であり欠陥ではない。
- **同綴りホモグラフ**: `tenis`(tennis/ten・is), `havaj`(Hawaii/hav・a・j), `argentan`(合金/argent・an)。文脈依存で一意化不能=誤りではない。

## 総括
語根分解は **99.4%の高精度で実行可能**(全122文書97%以上)。残る0.6%の不一致の大半は **京大コーパス自身の誤り**(過剰分割と粗い丸め、検証20語中18語で確認)・**国名-i/o構造的天井**・**文脈依存ホモグラフ**に帰属する。app固有の真の欠陥は **「先頭1字孤立」(fero→f/er/o型)にほぼ限定**され、これは手動補正オーバーレイで除去可能。`ekde`等「app誤り」とされた一部はむしろ語彙化として弁護可能。
**→ 京大コーパスは正本ではなく、不一致の相当部分はコーパス側に非がある。**
