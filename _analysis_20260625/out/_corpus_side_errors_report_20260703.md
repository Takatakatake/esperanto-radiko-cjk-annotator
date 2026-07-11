# 京大エス研コーパス側の分解誤り報告(最終版) 2026-07-03

全数すり合わせ最終監査(123ルビ文書/108,537境界, 一致99.671%)によるコーパス側修正候補。
アプリ=gold一致を正とした23語38件 + 裁定確定3語。

| 語 | コーパスの分解(誤) | 正しい分解(gold=app一致) | 件数 |
|---|---|---|---|
| esperante | esper/ant/e | esperant/e | 9 |
| indonezio | indonez/io | indonezi/o | 6 |
| komunumo | komunum/o | komun/um/o | 2 |
| malajzio | malajz/io | malajzi/o | 2 |
| zoologia | zoologi/a | zo/o/logi/a | 1 |
| etnologio | etno/log/io | etn/o/logi/o | 1 |
| anestezi | anestez/i | an/estez/i | 1 |
| meningito | meningit/o | mening/it/o | 1 |
| geologio | geologi/o | geo/logi/o | 1 |
| nitrato | nitrat/o | nitr/at/o | 1 |
| biografio | biografi/o | bio/grafi/o | 1 |
| neŭrokirurgio | neŭro/kirurgi/o | neŭr/o/kirurgi/o | 1 |
| urologio | urologi/o | uro/logi/o | 1 |
| laringologio | laring/o/log/io | laring/o/logi/o | 1 |
| ginekologio | ginekologi/o | ginek/o/logi/o | 1 |
| kronologia | kronologi/a | kron/o/logi/a | 1 |
| lingvisto | lingvist/o | lingv/ist/o | 1 |
| anarkisto | anarkist/o | anark/ist/o | 1 |
| biologio | biologi/o | bio/logi/o | 1 |
| fonologio | fon/o/log/io | fon/o/logi/o | 1 |
| lastatempe | lastatemp/e | last/a/temp/e | 1 |
| mitologio | mitologi/o | mit/o/logi/o | 1 |
| eŭfemisme | eŭfemism/e | eŭfem/ism/e | 1 |

## 裁定ワークフロー確定分

- **antoni**: Antoni(例: Antoni Grabowski等のポーランド語名)は固有名詞全体保持が正で、コーパスのanton/iは語尾iを不当に切った境界ずれ。
- **pense**: 正しくはpens/e(考え+副詞語尾)で、コーパスのpen/seは境界ずれの明白な誤り(同語の別エントリではpens/eと正しく分解されている)。
- **nemunas**: リトアニアの川名ネムナスは固有名詞全体保持(app)が正で、corpusのn/em/u/nasは明白な過分解。

## 特記
- anestezi: コーパスは anestez/i と切っているが、正は an(無)/estez(感覚)/i(gold一致)。
  ※本プロジェクトの語根忠実性原則の原点例。アプリ側は修正済み。
- アプリ側の残差13件(firmao×11, kajo×2)は『ルビは荒くてよい』原則による意図的な一体保持
  (グロスは商会/波止場で正確)。漢字トラックは firma/o・kaj/o の深分解でマスター準拠。