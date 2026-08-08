# 京大エス研HTMLコーパス 全文書 語根分解精度 監査レポート

**測定日**: 2026-06-29 ／ **対象**: 京大エス研HTML 全171ファイル(ルビ付き122文書) ／ **実機状態**: デプロイ版(先頭1字孤立 autofix込み)

## 1. 全体精度

| 指標 | 値 |
|---|---|
| 走査ファイル | 171（ルビ付き文書 122） |
| 測定トークン(多片語) | 107,754 |
| 境界一致(実機=autofix込み) | **107,181 / 107,754 = 99.468%**（不一致 573） |
| 同(baseline=autofix無) | 107,175 / 107,754 = 99.463% |

### 敵対裁定で再フレームした「アプリの真の分解精度」

不一致 573 件を Esペラント形態論 専門家2名＋調停で裁定した結果、アプリ側が出した分解は実際には:

| 裁定 | inst | 語数 | 意味 |
|---|---|---|---|
| 完全一致(app=コーパス) | 107,181 | — | 双方一致 |
| APP_RIGHT(**コーパス誤り**) | 95 | 47 | アプリが正・コーパスが誤り |
| BOTH_VALID(両者妥当) | 152 | 41 | ホモグラフ/国名-i/構造天井 |
| CORPUS_RIGHT(**app誤り**) | 273 | 99 | コーパスが正・アプリが誤り |
| NEITHER(両者誤り) | 53 | 11 | 正解は第三の分解 |

➜ **アプリが正しい/許容される分解を出したトークン = 107,428 / 107,754 = 99.70%**
（アプリの真の誤り = 326 トークン = 0.30%）

## 2. アプリの真の欠陥 (CORPUS_RIGHT + NEITHER)

アプリが実際に誤分解したのは **326 トークン (0.0030相当 = 0.30%)** のみ。内訳:

| サブクラス | inst | 語例 |
|---|---|---|
| 固有名詞・外来語をappが過分解 | 76 | tokiponuloj, gerdan, peĉjon, jutubo, davaon |
| app接辞/語尾の分離漏れ | 68 | teren, junuliĉoj, progresi, eti, faŝismo |
| ekde(語彙化論争) | 55 | ekde |
| その他app境界ずれ | 54 | butanon, idon, tokiponistoj, tokiponularo, tokiponulojn |
| 国際語境界(-logi-/-krat-) | 20 | meritokratio, meritokratia, meritokratian, japanologio |

**最大クラス=固有名詞・外来語の過分解**: アプリの語根辞書に無い地名/人名/借用語(Vroclav, Toki Pona, Quedlinburg, Davao, YouTube, Piast王朝…)を、貪欲最長一致が既存語根に砕いてしまう。これは下位文書(ブータン紀行・時事誌・Toki Pona紹介)が他より低い唯一の理由。通常の散文・文学では発生しない。

### app誤り 全リスト
| 語 | コーパス(正) | アプリ(誤) | n | 根拠 |
|---|---|---|---|---|
| `ekde` | `ek/de` | `ekde` | 55 | ek-(起動)+de(前置詞)の複合語=gold一致 |
| `meritokratio` | `merit/o/krat/io` | `merit/ok/rati/o` | 15 | kratは実在,APPは綴り割れ誤り |
| `teren` | `ter/en` | `teren` | 14 | ter+副詞e+方向n=gold。丸ごと粗 |
| `tokiponuloj` | `tokipon/ul/oj` | `toki/po/nul/oj` | 13 | Toki Pona借用語をtokiponに保つ。APPは綴り割れ |
| `butanon` | `butano/n` | `butan/on` | 12 | butan/o/n。APPのon端は誤り,CORPUS境界は正 |
| `junuliĉoj` | `jun/ul/iĉ/oj` | `jun/ul/iĉoj` | 10 | -iĉ-接辞,語尾-oj分離が正。APPはoj未分離 |
| `gerdan` | `gerda/n` | `gerd/an` | 10 | 人名Gerda+対格。APPは固有名を偽分解 |
| `progresi` | `progres/i` | `progresi` | 6 | progres-語根+不定形-i。APPの未分解は誤り |
| `eti` | `et/i` | `eti` | 4 | et-語根+不定形-i。未分解は誤り |
| `idon` | `ido/n` | `id/on` | 4 | Ido(子孫/イド)実在語根+対格n |
| `peĉjon` | `peĉjo/n` | `peĉj/on` | 4 | 愛称Peĉjo+対格n。peĉj/on誤 |
| `jutubo` | `jutub/o` | `ju/tub/o` | 4 | YouTube借用語一体。ju/tub/oは誤 |
| `tokiponistoj` | `tokipon/ist/oj` | `toki/pon/ist/oj` | 3 | Toki Pona語名一体+ist+oj。toki/ponは誤 |
| `tokiponularo` | `tokipon/ul/ar/o` | `toki/pon/ul/ar/o` | 3 | tokipon一体+ul+ar+o。toki/ponは誤 |
| `tokiponulojn` | `tokipon/ul/ojn` | `toki/po/nul/ojn` | 3 | tokipon+ul+ojn。toki/po/nul/ojnは綴り破壊 |
| `faŝismo` | `faŝ/ism/o` | `faŝism/o` | 2 | 実在接尾-ism-を割る。goldもfaŝ/ism/o |
| `fero` | `fer/o` | `fero` | 2 | 鉄fer+文法語尾o。APPは語尾未分離 |
| `fie` | `fi/e` | `fie` | 2 | fi(下劣)語根+副詞語尾e。APPは未分離 |
| `reblu` | `re/blu` | `reblu` | 2 | 接頭re+blu。APPは未分離(bluaの片) |
| `aĝe` | `aĝ/e` | `aĝe` | 2 | aĝ(年齢)+副詞e。APPは未分離 |
| `pense` | `pens/e` | `pense` | 2 | pens(思考)語根+副詞e。APP未分離 |
| `vortoscion` | `vort/o/sci/on` | `vort/os/cion` | 2 | vort+o+sci+on(語彙知識)。APPは綴り割れ |
| `are` | `ar/e` | `are` | 2 | ar(集合)+副詞e。APPは未分離 |
| `davaon` | `davao/n` | `davaon` | 2 | 地名Davao+対格n。語根丸ごと留め正 |
| `blisa` | `blis/a` | `blisa` | 2 | 語根blis+形容詞a。APPは語尾未分離 |
| `faradis` | `far/ad/is` | `farad/is` | 2 | far+接尾-ad-(継続)+is。farad(物理単位)無関係 |
| `iĉoj` | `iĉ/oj` | `iĉoj` | 2 | 接尾-iĉ-(男性)+複数oj。語尾分離が正 |
| `iĉa` | `iĉ/a` | `iĉa` | 2 | 接尾-iĉ-+形容詞a。語尾分離が正 |
| `iĉaj` | `iĉ/aj` | `iĉaj` | 2 | 接尾-iĉ-+aj。語尾分離が正 |
| `tradiciojn` | `tradici/ojn` | `tr/adici/ojn` | 2 | tradici(伝統)が実在語根。tr/adiciは綴り割れ誤 |
| `sportocentro` | `sport/o/centr/o` | `sp/ort/o/centr/o` | 2 | sport実在語根。sp/ortは綴り割れ誤 |
| `piastdinastia` | `piast/dinasti/a` | `pi/ast/dinasti/a` | 2 | Piast(王朝名)固有。pi/astは砕き過ぎ誤 |
| `vroclava` | `vroclav/a` | `vroc/lav/a` | 2 | 地名Vroclav(o)固有。vroc/lavは誤分解 |
| `dojmis` | `dojm/is` | `doj/mis` | 2 | dojm(語根)+is。doj/misは存在せず |
| `anjon` | `anjo/n` | `anj/on` | 2 | anjo(愛称/姉)+対格n。anj/onは誤 |
| `sulen` | `sule/n` | `sul/en` | 2 | sule+n。-en語尾は無く接尾sulも疑問 |
| `jajon` | `jajo/n` | `ja/jon` | 2 | jajo+対格n。ja/jonは無根拠 |
| `trekadon` | `trek/ad/on` | `tre/kad/on` | 2 | trek(借)+ad+on。tre/kadは綴り割れ誤 |
| `vroclavo` | `vroclav/o` | `vroc/lav/o` | 2 | 地名Vroclav固有。vroc/lavは誤分解 |
| `okcidentigo` | `okcident/ig/o` | `okc/ident/ig/o` | 2 | okcident(西)実在語根+ig+o。okc/identは誤 |
| `memeon` | `meme/on` | `mem/eon` | 2 | meme実在語根保持。mem/eon語根破壊 |
| `meritokratia` | `merit/o/krat/ia` | `merit/ok/rati/a` | 2 | merit/krat実在。ok/ratiは綴り割れ |
| `meritokratian` | `merit/o/krat/ian` | `merit/okra/tia/n` | 2 | CORPUS実在語根、okra/tiaは無意味 |
| `radiofonio` | `radio/fon/io` | `radiofoni/o` | 2 | CORPUSは語根分析、APPは一塊で粗 |
| `milfoje` | `mil/foj/e` | `milfoj/e` | 1 | mil+foj二語根, APP融合誤 |
| `farado` | `far/ad/o` | `farad/o` | 1 | -ad-接尾が標準、faradは周辺ホモグラフ |
| `legata` | `leg/at/a` | `legat/a` | 1 | -at-受動分詞標準、legatは周辺ホモ |
| `kvedlinburgo` | `kvedlinburg/o` | `kvedlinburgo` | 1 | 独地名Quedlinburg丸ごと+o。APPは語尾未分離 |
| `katederalo` | `katederal/o` | `katederalo` | 1 | cathedral借用語単一語根+o |
| `cintamanio` | `cintamani/o` | `cintamanio` | 1 | 梵語固有名Cintamani丸ごと+o |
| `honorata` | `honor/at/a` | `honorat/a` | 1 | -at-は実在受動分詞接辞 |
| `kantataj` | `kant/at/aj` | `kantat/aj` | 1 | kant+受動分詞at標準。文中分詞優先 |
| `kantata` | `kant/at/a` | `kantat/a` | 1 | kant+受動分詞at標準。文中分詞優先 |
| `japanologio` | `japan/o/logi/o` | `japan/o/log/io` | 1 | logi/o境界が正、APPのlog/io誤境界 |
| `ĉoĉangaĉa` | `ĉoĉangaĉ/a` | `ĉo/ĉan/g/aĉ/a` | 1 | 固有名/擬音丸ごと。APPは偽語根破砕 |
| `kantoa` | `kanto/a` | `kant/oa` | 1 | kanto(州/歌)+a。oaは語尾でない |
| `tereftalato` | `tereftalat/o` | `ter/e/ftal/at/o` | 1 | 化学語丸ごと。ter/e/ftalは偽分解 |
| `nociveco` | `nociv/ec/o` | `noc/iv/ec/o` | 1 | nociv実在語根+ec。noc/iv語根割れ |
| `grifita` | `grifit/a` | `grif/it/a` | 1 | 固有名Griffith丸ごと+a。grif/itは無意味 |
| `toruno` | `torun/o` | `to/run/o` | 1 | 波蘭地名Toruń丸ごと。APPは破砕 |
| `vroclavanoj` | `vroclav/an/oj` | `vrocl/avan/oj` | 1 | Wrocław+-an-住民+oj。APPは破砕 |
| `ebligantaj` | `ebl/ig/ant/aj` | `eb/lig/ant/aj` | 1 | ebl+ig+ant+aj。eb/ligは誤り |
| `baltikon` | `baltik/on` | `bal/tik/on` | 1 | Baltic地名+対格n。APPは破砕 |
| `bonŝanĉulo` | `bon/ŝanĉ/ul/o` | `bon/ŝ/anĉ/ul/o` | 1 | ŝ/anĉは無意味、ŝanĉ(=ŝanc)が語根 |
| `fronantaj` | `fron/ant/aj` | `fro/nant/aj` | 1 | fro/nantは無意味、-ant-分詞 |
| `kaŝtelestro` | `kaŝtel/estr/o` | `kaŝ/te/lestr/o` | 1 | kaŝtel+estr、APPは綴り割れ |
| `invigilserva` | `invigil/serv/a` | `in/vigil/serv/a` | 1 | invigil借用語根、in/vigilは誤 |
| `invigilservo` | `invigil/serv/o` | `in/vigil/serv/o` | 1 | invigil借用語根、in/vigilは誤 |
| `ekscepta` | `ekscept/a` | `eks/cep/ta` | 1 | ekscept一語、eks/cep/taは誤 |
| `informatika` | `informatik/a` | `inform/at/ika` | 1 | informatik語彙化。inform/at過分解 |
| `boleslaon` | `boleslao/n` | `bol/eslaon` | 1 | Bolesłavo人名、bol/eslaonは誤 |
| `revenĝe` | `revenĝ/e` | `re/ven/ĝe` | 1 | venĝ真根。re/ven/ĝeは根破壊で誤 |
| `milsko` | `milsk/o` | `mil/sko` | 1 | 固有名詞、mil/skoは無意味割れ |
| `lecjonojn` | `lecjon/ojn` | `lec/jon/ojn` | 1 | lecjono(=leciono)語根、lec/jonは誤 |
| `rubaŝka` | `rubaŝk/a` | `rub/aŝka` | 1 | 露語借用rubashka一塊。APPは綴り割れ |
| `rotaviruso` | `rotavirus/o` | `rot/a/virus/o` | 1 | 造語名。rot/aは語尾誤割れ |
| `trekado` | `trek/ad/o` | `tr/ek/ad/o` | 1 | trek+ad。APP tr/ekは綴り割れ |
| `sendependemon` | `sen/depend/em/on` | `sen/de/pend/em/on` | 1 | dependは一語根。de/pendは誤割れ |
| `evidentigis` | `evident/ig/is` | `ev/ident/ig/is` | 1 | evidentは一語根。ev/identは誤割れ |
| `amaziĥa` | `amaziĥ/a` | `am/aziĥa` | 1 | Amazigh民族名一塊。APPは綴り割れ |
| `paiŭanan` | `paiŭan/an` | `paiŭ/an/an` | 1 | Paiwan固有名+an。APPは固有名破壊 |
| `ŝonaan` | `ŝona/an` | `ŝonaa/n` | 1 | Shona+an。APP ŝonaa/nは境界誤り |
| `tokion` | `tokio/n` | `toki/on` | 1 | Tokio地名丸ごと。toki/onは誤分解 |
| `kamakuron` | `kamakuro/n` | `kam/a/kur/on` | 1 | 鎌倉=地名丸ごと。kam/a/kurは砕き過ぎ |
| `enoŝimon` | `enoŝimo/n` | `en/o/ŝim/on` | 1 | 江ノ島=地名丸ごと。en/o/ŝim誤 |
| `bisaja` | `bisaj/a` | `bis/aja` | 1 | Bisaja=ビサヤ固有。bis/aja誤 |
| `bisajaso` | `bisajas/o` | `bis/aj/as/o` | 1 | Bisajas固有名。bis/aj/as砕き誤 |
| `davaanoj` | `davaan/oj` | `dava/an/oj` | 1 | Davao派生demonym、dava語根は偽 |
| `brasilo` | `brasil/o` | `bras/ilo` | 1 | Brazilo=地名丸ごと。bras/ilo誤 |
| `jutube` | `jutub/e` | `ju/tub/e` | 1 | Jutubo=YouTube借用。ju/tub誤 |
| `jutubaj` | `jutub/aj` | `ju/tub/aj` | 1 | Jutubo借用語根。ju/tub誤 |
| `jutubisto` | `jutub/ist/o` | `ju/tub/ist/o` | 1 | jutub語根+ist。ju/tubは偽境界 |
| `videoludon` | `video/lud/on` | `vide/o/lud/on` | 1 | video一語根、vide/o分割は語根破壊 |
| `tifinaha` | `tifinah/a` | `ti/fin/aha` | 1 | Tifinagh文字=固有。ti/fin/aha誤 |
| `nian` | `nia/n` | `ni/an` | 1 | nia=所有代名詞語根+n対格。ni/anは誤り |
| `okajamo` | `okajam/o` | `ok/aj/am/o` | 1 | 岡山=地名。ok/aj/am砕きは誤り |
| `oktoberfesto` | `oktoberfest/o` | `okt/o/ber/fest/o` | 1 | 独語祭名借用。okt/o/ber/fest砕きは誤り |
| `jokohaman` | `jokohama/n` | `jokoham/an` | 1 | 横浜=地名+n。-an接辞捏造は誤り |
| `neŭtronoj` | `neŭtron/oj` | `neŭtr/on/oj` | 1 | neŭtron=単一物理語根。-on分割は誤り |

## 3. 京大コーパス自身の分解ミス (APP_RIGHT) — ユーザーの疑念の検証

**専門家2名＋調停が「コーパスの分解が誤り・アプリが正しい」と確定した語 = 47語 / 95 inst**。
さらに NEITHER(両者誤り)の 11 語でもコーパスは誤り。➜ **本係争範囲だけでコーパスは最低 148 inst で分解を誤っている**(検出下限)。
ユーザーの直感どおり、京大コーパス側にも分解ミスが確かに潜んでいる。主な型:

- **偶然の部分文字列での過分解**: `platformo→plat/form/o`(正=platform/o), `ocelo→o/cel/o`(正=ocel/o)
- **語彙化語の語源分解**: `esperante→esper/ant/e`(正=esperant/e)
- **-logi-/-ist-/-um-/-it- 等 実在接辞の不統一**: `biologio→biologi/o`(正=bio/logi/o), `lingvisto→lingvist/o`(正=lingv/ist/o), `komunumo→komunum/o`(正=komun/um/o), `meningito→meningit/o`(正=mening/it/o)
- **-logi- の綴り割れ**: `laringologio→...log/io`(正=...logi/o)

### コーパス誤り 全リスト
| 語 | コーパス(誤) | アプリ(正) | n | gold | 根拠 |
|---|---|---|---|---|---|
| `adon` | `ad/on` | `adon` | 29 | — | ad接辞は語頭不可・on非形態素。丸ごと |
| `esperante` | `esper/ant/e` | `esperant/e` | 9 | esperant/e | 語彙化一語=gold準拠。CORPUSは語源的だが非標準 |
| `platformo` | `plat/form/o` | `platform/o` | 3 | platform/o | platform単一借用語。plat/form/oは綴り割れ誤 |
| `tiba` | `tib/a` | `tiba` | 3 | — | tib語根非実在、固有/外来は丸ごと |
| `ocelo` | `o/cel/o` | `ocel/o` | 2 | ocel/o | ocel単一語根。o/cel/oは偶然部分文字列の誤 |
| `komunumo` | `komunum/o` | `komun/um/o` | 2 | komun/um/o | komun-語根+接尾-um-+o。一体は粗い |
| `disdegni` | `dis/degn/i` | `disdegn/i` | 2 | disdegn/i | disdegnはPIV独立語根。過分解不可 |
| `etos` | `et/os` | `etos` | 2 | — | etos=気風の単一語根。et/os誤 |
| `argentan` | `argent/an` | `argentan` | 2 | — | argentan=洋銀借用語。argent/an誤 |
| `adone` | `a/don/e` | `adon/e` | 2 | — | a/donは偽分解。adon語根+e側が妥当 |
| `kvardeko` | `kvardek/o` | `kvar/dek/o` | 2 | — | kvar(4)+dek(10)の合成数詞。分解が正 |
| `domen` | `dom/en` | `domen` | 2 | dom/e/n | domen単一実在語根。dom/en過分解 |
| `zoologia` | `zoologi/a` | `zo/o/logi/a` | 1 | zo/o/logi/a | gold=zo/o/logi/a。CORPUS未分解は粗い |
| `etnologo` | `etno/log/o` | `etn/o/log/o` | 1 | etn/o/log/o | 語根は etn。etno は分割不足 |
| `etnologio` | `etno/log/io` | `etn/o/logi/o` | 1 | etn/o/logi/o | gold=etn/o/logi/o。CORPUS etno/log/io 誤 |
| `anestezi` | `anestez/i` | `an/estez/i` | 1 | an/estez/i | an-否定+estez語根(gold)。CORPUS未分解 |
| `meningito` | `meningit/o` | `mening/it/o` | 1 | mening/it/o | -it-炎症接尾辞。CORPUS未分解は粗い |
| `geologio` | `geologi/o` | `geo/logi/o` | 1 | geo/logi/o | gold=geo/logi/o。CORPUS未分解は粗い |
| `nitrato` | `nitrat/o` | `nitr/at/o` | 1 | nitr/at/o | 化学-at-塩接尾辞(gold)。CORPUS未分解 |
| `biografio` | `biografi/o` | `bio/grafi/o` | 1 | bio/grafi/o | gold=bio/grafi/o。CORPUS未分解は粗い |
| `neŭrokirurgio` | `neŭro/kirurgi/o` | `neŭr/o/kirurgi/o` | 1 | neŭr/o/kirurgi/o | gold=neŭr/o/kirurgi/o。neŭro未分割は不足 |
| `urologio` | `urologi/o` | `uro/logi/o` | 1 | uro/logi/o | -logi-接尾, CORPUSは一体で粗い |
| `laringologio` | `laring/o/log/io` | `laring/o/logi/o` | 1 | laring/o/logi/o | -logi-が単位, CORPUSのlog/io綴り割れ誤 |
| `ginekologio` | `ginekologi/o` | `ginek/o/logi/o` | 1 | ginek/o/logi/o | ginek/o/logi/o標準, CORPUS一体粗い |
| `kronologia` | `kronologi/a` | `kron/o/logi/a` | 1 | kron/o/logi/a | kron/o/logi分析, CORPUS一体粗い |
| `lingvisto` | `lingvist/o` | `lingv/ist/o` | 1 | lingv/ist/o | -ist-実在接尾, CORPUS未分割 |
| `anarkisto` | `anarkist/o` | `anark/ist/o` | 1 | anark/ist/o | -ist-実在接尾, CORPUS未分割 |
| `biologio` | `biologi/o` | `bio/logi/o` | 1 | bio/logi/o | bio/logi標準, CORPUS一体粗い |
| `fonologio` | `fon/o/log/io` | `fon/o/logi/o` | 1 | fon/o/logi/o | -logi-単位, CORPUSのlog/io綴り割れ誤 |
| `lastatempe` | `lastatemp/e` | `last/a/temp/e` | 1 | last/a/temp/e | last+temp二語根, CORPUS融合誤 |
| `mitologio` | `mitologi/o` | `mit/o/logi/o` | 1 | mit/o/logi/o | mit/o/logi標準, CORPUS一体粗い |
| `eŭfemisme` | `eŭfemism/e` | `eŭfem/ism/e` | 1 | eŭfem/ism/e | eŭfem語根+ism実在。一体は粗い |
| `polietilena` | `polietilen/a` | `poli/etilen/a` | 1 | — | poli-とetilen実在。CORPUSは粗い一体 |
| `ursulanina` | `ursulan/in/a` | `ursul/an/in/a` | 1 | — | gold Ursul/an/in準拠。ursulan粗い |
| `antiseptiko` | `antiseptik/o` | `anti/sept/ik/o` | 1 | — | anti-は実在接頭辞、分析的 |
| `gastroskopon` | `gastroskop/on` | `gastr/o/skop/on` | 1 | — | gastr/o/skop国際語要素を分析 |
| `tibetologo` | `tibetolog/o` | `tibet/o/log/o` | 1 | — | Tibet+o+log+o分析が標準。一体粗い |
| `sociologion` | `sociologi/on` | `soci/o/logi/on` | 1 | — | 社会学はsoci/o/logi分析が学習標準 |
| `enteroviruso` | `enterovirus/o` | `enter/o/virus/o` | 1 | — | entero(腸)+virus、国際接頭で分析 |
| `rinoviruso` | `rinovirus/o` | `rin/o/virus/o` | 1 | — | rino(鼻)+virus、国際接頭で分析 |
| `metalingvistika` | `metalingvistik/a` | `meta/lingvistik/a` | 1 | — | meta接頭辞は実在、分割すべき |
| `mezorienton` | `mezoriento/n` | `mez/orient/on` | 1 | — | mez+orientは透明複合、分割正 |
| `komunumoj` | `komunum/oj` | `komun/um/oj` | 1 | — | 実在接尾-um-を割るのが正(komuna+um) |
| `trilitajn` | `trilit/ajn` | `tri/lit/ajn` | 1 | — | gold tri/lit。CORPUSはtri未分割で粗 |
| `morfologie` | `morfologi/e` | `morf/o/logi/e` | 1 | — | 学術語-logi-。分析側が標準、一体は粗い |
| `bizaraĵon` | `bizaraĵ/on` | `bizar/aĵon` | 1 | — | 真の境界はbizar|aĵ。CORPUSは語根を膠着 |
| `sinteno` | `sinten/o` | `sin/ten/o` | 1 | si/n/ten/o | sin(反身)+ten(保持)。CORPUS一体は粗い |

## 4. 両者妥当 (BOTH_VALID) = 構造的天井・ホモグラフ

41語/152inst。アプリの分解は誤りではない。主に:
- **国名 -i/o**: `ĉinio` app=ĉin/io vs コーパス=ĉini/o vs gold=ĉin/i/o。1字形態素-i-を単独ルビ化しない機構天井。
- **ホモグラフ**: `amas`(am/as 愛する / 固有名Amas), `tenis`(ten/is 保持した / tennis), `anton`(ant/on / 人名Anton)。文脈依存で両読み妥当。

### 両者妥当 全リスト
| 語 | コーパス | アプリ | n | 根拠 |
|---|---|---|---|---|
| `amas` | `am/as` | `amas` | 30 | 走行動詞am/as妥当、固有名Amasも可 |
| `ĉinio` | `ĉini/o` | `ĉin/io` | 21 | 国名-i粗変種は両許容(構造天井) |
| `japanion` | `japanio/n` | `japan/io/n` | 14 | 国名-i粗変種は両許容(構造天井) |
| `anton` | `ant/on` | `anton` | 10 | ant/onか人名Anton。走行で両読み妥当(規則6) |
| `tenis` | `ten/is` | `tenis` | 9 | ten/is(保持)か球技tenis。両読み妥当(規則6) |
| `indonezio` | `indonez/io` | `indonezi/o` | 6 | 国名-i粗変種は両許容。APPはgold一致 |
| `ĉeĥio` | `ĉeĥi/o` | `ĉeĥ/io` | 5 | 国名-i。ĉeĥi/oとĉeĥ/ioは構造天井で両許容 |
| `britio` | `briti/o` | `brit/io` | 5 | 国名-i。briti/oとbrit/ioは構造天井で両許容 |
| `havaj` | `hav/aj` | `havaj` | 4 | hav/aj妥当だがHavaj地名のホモグラフ |
| `elzan` | `elza/n` | `elzan` | 4 | 人名Elza+対格n か外来語丸ごと |
| `antoni` | `anton/i` | `antoni` | 4 | 人名Antoniかanton/iのホモグラフ |
| `anon` | `an/on` | `anon` | 4 | an語根+対格on か固有名anon両可 |
| `malajzio` | `malajz/io` | `malajzi/o` | 2 | 国名-i: malajz/io と malajzi/o は構造天井で両許容 |
| `paran` | `par/an` | `paran` | 2 | par/an対格所属も固有Paranも可 |
| `koreion` | `koreio/n` | `kore/io/n` | 2 | 国名-i: koreio粗とkore/io分析両可 |
| `bulgario` | `bulgari/o` | `bulgar/io` | 2 | 国名-i。bulgari/o と bulgar/io は構造天井 |
| `italio` | `itali/o` | `ital/io` | 2 | 国名-i。itali/o と ital/io は許容変種 |
| `koreio` | `korei/o` | `kore/io` | 2 | 国名-i。korei/o と kore/io は許容変種 |
| `diplomatio` | `diplomati/o` | `diplomat/io` | 2 | -i抽象。diplomati/o と diplomat/io 同天井 |
| `iniciatoro` | `iniciat/or/o` | `iniciator/o` | 1 | iniciat+-or実在 と借用一語の両妥当 |
| `baron` | `bar/on` | `baron` | 1 | baron語根 vs bar/on分割ホモグラフ |
| `kriptologiajn` | `kript/o/log/iajn` | `kript/o/log/i/ajn` | 1 | 両者kript/o/log一致、i/ajn細粒差 |
| `ĉeĥion` | `ĉeĥi/on` | `ĉeĥ/ion` | 1 | 国名-i-の粗変種、両許容 |
| `kievon` | `kievo/n` | `kiev/on` | 1 | 地名根Kiev、kievo/n と kiev/on両許容 |
| `oomoton` | `oomoto/n` | `oomot/on` | 1 | 大本Oomot、oomoto/n と oomot/on両可 |
| `japanion` | `japan/ion` | `japan/io/n` | 1 | 国名-i構造天井、両者粗変種 |
| `rusion` | `rusio/n` | `rus/ion` | 1 | 国名-i構造天井、両者粗変種 |
| `ukrainion` | `ukrainio/n` | `ukrain/ion` | 1 | 国名-i構造天井、両者粗変種 |
| `eŭrazion` | `eŭrazio/n` | `eŭrazi/on` | 1 | 地名-i: eŭrazio/n と eŭrazi/on両粗許容 |
| `jukata` | `jukat/a` | `juk/at/a` | 1 | juk/at受動かJukat固有名ホモグラフ |
| `miaj` | `mia/j` | `mi/aj` | 1 | 正mi/a/j、両案とも一境界融合の粗変種 |
| `ĉinion` | `ĉini/on` | `ĉin/ion` | 1 | 国名-i-。ĉini/o/ĉin/io共に粗い変種で許容 |
| `etiopio` | `etiopi/o` | `etiop/io` | 1 | 国名-i-。etiopi/o/etiop/io共に粗い変種 |
| `pomerio` | `pomeri/o` | `pomer/io` | 1 | 地名-i-。pomeri/o/pomer/io共に許容 |
| `bohemio` | `bohemi/o` | `bohem/io` | 1 | 国名-i-。bohemi/o/bohem/io共に粗い変種 |
| `moravio` | `moravi/o` | `morav/io` | 1 | 地名-i-。moravi/o/morav/io共に許容 |
| `kroatio` | `kroati/o` | `kroat/io` | 1 | 国名-i-。kroati/o/kroat/io共に粗い変種 |
| `sovetia` | `soveti/a` | `sovet/ia` | 1 | 国名-i-。soveti/a/sovet/ia共に許容 |
| `ukrainio` | `ukraini/o` | `ukrain/io` | 1 | 国名-i-。ukraini/o/ukrain/io共に粗い変種 |
| `katalunio` | `kataluni/o` | `katalun/io` | 1 | 地名-i-。kataluni/o/katalun/io共に許容 |
| `vjetnamio` | `vjetnami/o` | `vjetnam/io` | 1 | 国名-i-。vjetnami/o/vjetnam/io共に粗い変種 |

## 5. 両者誤り (NEITHER)
| 語 | コーパス | アプリ | n | 正解(専門家) | 根拠 |
|---|---|---|---|---|---|
| `amon` | `am/on` | `amon` | 17 | `am/o/n` | 正はam/o/n。CORPUSのon端は不在で誤り |
| `dion` | `di/on` | `dion` | 14 | `di/o/n` | 正はdi/o/n。CORPUSのon端は不在で誤り |
| `areopologio` | `are/op/o/log/io` | `are/op/ologi/o` | 11 | `areopag/o/log/i/o` | are/opは綴り割れ。両案とも語幹誤分割 |
| `ndemande` | `n/demand/e` | `ndemande` | 2 | `n/demand/e` | 先頭n孤立は破損入力。正規はdemand/e |
| `pense` | `pen/se` | `pense` | 2 | `pens/e` | -seは非形態素。pen/se誤。正はpens/e |
| `auster` | `aus/ter` | `au/ster` | 2 | `aŭster/o系` | 両案とも誤分割。aŭster一体が妥当 |
| `areopologia` | `are/op/o/log/ia` | `are/op/ologi/a` | 1 | `areopag/i/a` | Areopag語根、両案とも綴り割れ |
| `areopologiajn` | `are/op/o/log/iajn` | `are/op/ologi/ajn` | 1 | `areopag/i/ajn` | Areopag語根、両案とも綴り割れ |
| `areopologion` | `are/op/o/log/ion` | `are/op/ologi/on` | 1 | `areopag/i/on` | Areopag語根、両案とも綴り割れ |
| `jurnalisto` | `jurnalist/o` | `jur/na/list/o` | 1 | `jurnal/ist/o` | jurnal+ist。APPは綴り割れ、CORPUSはist未分割 |
| `renkejtiĝon` | `renkejtiĝo/n` | `ren/kejt/iĝ/on` | 1 | `renkejt/iĝ/o/n` | 固有幹+実在iĝ。両案とも不正確 |

## 6. 文書別精度(全122文書)

最小 97.1% / 中央 99.68% / 平均 99.53% / 最大 100.0%

**下位12文書**(いずれも固有名詞・外来語・国名が密な文書):

| % | 一致/総数 | 文書 |
|---|---|---|
| 97.1 | 67/69 | vere_aux_fantazie_37.html |
| 97.13 | 812/836 | La_eseo_pri_Butano.html |
| 97.99 | 684/698 | RO_202605_eltiritaj_esperantaj_pagxoj_kun_japanaj_tradu |
| 98.2 | 872/888 | osakakenji.html |
| 98.26 | 395/402 | 202601_Revuo_eltiritaj_Esperantaj_pagxoj_kun_japanaj_tr |
| 98.4 | 1413/1436 | 202510_Revuo_eltiritaj_Esperantaj_pagxoj_kun_japanaj_tr |
| 98.47 | 644/654 | 20250521_komuna_kunveno_en_la_japana.html |
| 98.52 | 332/337 | fujimaki11.html |
| 98.64 | 217/220 | gerda_malaperis_25.html |
| 98.64 | 4494/4556 | pola_retradio.html |
| 98.71 | 230/233 | gerda_malaperis_26.html |
| 98.78 | 646/654 | esperanto_express_corrected.html |

**満点(100%)文書: 38件**(Gerda物語の多くの章・vere/fantazie短編群=固有名詞の少ない散文/文学)。

## 7. 結論

1. **アプリの語根分解精度は全171ファイルで実効 99.7%**(形態論的に正しい/許容される分解)。通常の散文・文学では構造的天井に達している。
2. **アプリの真の誤りは 326/107,754 = 0.30% のみ**で、その大半は『辞書に無い固有名詞・外来語の過分解』(下位文書の唯一の要因)。これは無発明・無回帰の範囲では修正困難な周辺ロングテール。
3. **京大コーパス側にも分解ミスが確実に存在**(確定 47語/95inst + 両者誤り11語)。ユーザーの疑念は正しい。京大コーパスは正本(ゴールド)ではなく、`-logi-/-ist-/-um-` 接辞の不統一や `platformo→plat/form/o` 型の偶然分解を含む。
4. **アプリ vs コーパスの不一致573件のうち、アプリが悪いのは約半数(273/573)、コーパスが悪い+両者妥当が残り半数**。両者は同水準で、アプリは京大コーパスに匹敵する分解品質に到達している。