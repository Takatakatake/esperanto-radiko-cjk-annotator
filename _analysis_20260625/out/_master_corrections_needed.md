# マスター側で修正が必要な注釈誤り（read-only・アプリ外）

敵対監査(2026-06-29, 専門家2名+調停)で確定。これらは参照1注釈版/参照2マスター由来の**誤訳**で、
アプリは忠実に再現しているだけ。**マスターを修正→アプリ再生成**で反映されます。

## A. 明確な誤訳（語義が違う）
| 語根 | 言語 | 現在 | 正しい訳 | 理由 |
|---|---|---|---|---|
| `drag` | ZH/KO | 龙 / 용（＝竜） | 疏浚 / 준설（浚渫する） | `dragi`=浚渫。`drako`(竜)との同綴り誤友 |
| `didelf` | ZH | 袋鼠（カンガルー） | 负鼠（オポッサム） | 別動物 |
| `hipocentr` | JA(+zh/ko欠落) | 爆心地 | 震源 / 진원 | PIVでは地震の震源。爆心地は誤 |
| `balote` | JA/ZH | ヤマガラシ属 / 夏至草属 | バロタ属(Ballota) | 別科・別属の誤同定 |
| `bum` | JA/KO | ブーム / 붐 | 帆桁(下桁) | PIV `bumo`=帆の下桁。経済好況は別語 |
| `elafr` | ZH | 步甲属(Carabus) | 圆步甲属(Elaphrus) | 別属 |
| `didelf`/`balote`/`elafr` 等 | — | — | — | 動植物の属・科の同定誤り(専門語) |

## B. 不正確・音写のみ（語義不明）
| 語根 | 言語 | 現在 | 改善 |
|---|---|---|---|
| `angin` | JA/KO | アンギナ / 앙기나 | 咽峡炎 / 인두염 |
| `bistr` | JA | ビスタ色 | ビスター色(焦げ茶) |
| `akĉent` | KO | 억양(抑揚) | 사투리/악센트 |
| `enu` | ZH | 生厌(嫌悪寄り) | 厌倦(退屈) |
| `foin` | KO | 담비(テン一般) | 흰목도리담비(石貂・種特定) |
| `afekci` | JA | 作用 | 影響(中韓と並行) |
| `hebefreni` | KO | 파과형조현(途切れ) | 파과형 정신분열/파과병 |

## C. 偽分解が偽友グロスを生む語（マスターの分解方針の再考が必要）
マスターが国際語を過分割し、語源破片に無関係な訳が付く。**一語に戻す**か**per-root訳を修正**:
| 語 | 誤分割→誤グロス | 正 |
|---|---|---|
| `antibiotik` | anti/bio/**tik**(被套布/티킹=寝具生地) | 一語 or tik無訳 |
| `ekologi` | **ek**(开始/시작=起動接頭)/ologi | eko(環境)/logi |
| `dialog` | **dia**(通过/통과)/log | 一語(対話) |
| `telefon` | tele/**fon**(音) | 一語(電話) |
| `trompita` | **romp**(打破)/it | tromp(欺く)/it |
| `ofendita` | **fend**(劈开)/it | ofend(侮辱)/it |
| `inflamigi` | **flam**(火焰)/ig | inflam(炎症)/ig |
| `nebuligi` | **ne/bul**(不/球) | nebul(霧)/ig |
| `hidratigi` | **drat**(金属线)/ig | hidrat(水和)/ig |
| `ideogramo` | ide/o/**gram**(克=質量単位) | gram(記録/字) |
| `resumi` | **re/sum**(再び/総和) | 一語(要約) |
| `montenegrano` | mont/negr(山/黒) | montenegr(地名一語)/an |
| `kortegano` | kort/eg(庭/大) | korteg(宮廷)/an |
| `radiofonio` | **radio**(光线/광선=光) | radio(無線/ラジオ) |

※ ご方針「注釈は偽分解尊重で粗め可」に沿えば、Cは**ZH/KOも一語保持**(JA同様)が最も整合的で偽友も消える。

データ全件: `out/_anno_issues_by_cause.json`（136件・語/現訳→正訳・理由つき）
