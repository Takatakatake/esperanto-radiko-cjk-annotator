# 全数意味監査＋修正ログ 2026-07-01（フェーズA〜D）

サンプル78件でパイプラインを固めた後、全17,785タプルへ拡大。

## フェーズA: 全数監査（残15,651タプル・32バッチ・発見→敵対的検証）
確定 **214件**（誤訳97/JCK不整合68/崩れ24/学習品質17/語根忠実8｜高36・中110・低68）。
※fb27バッチの検証がAPI過負荷で失敗→当該6件は精査WFで再判定。
サンプル78と合わせ全17,785で確定 約292件（監査対象の約1.6%）。

## フェーズB: 発生源特定（220語根）
CSV既定/マスター注釈/実コンテキストを突合。マスター自体の誤りが多く、CSV既定＋文脈で是正。

## フェーズC: 規則精査WF（9判定＋4検証・2×字数＋両義頻出のみ併記）
209語根 apply可 / 11語根 却下（危険・不確実）。
主是正（同綴り異義の取り違えが中心）:
- ser 連続→血清・乳清（seri=系列と別）/ maŝ 機械→網目（maŝin=機械と別）/ kran 頭蓋→蛇口（krani=頭蓋と別）
- gazet 雑誌→新聞（revuo）/ rabi ×→狂犬病（rab=略奪）/ sod ×→ソーダ（natrio）/ koleg ×→同僚（kolegio=学院）
- vetur 行く→乗り物で行く / flar 感じる→嗅ぐ / envi 欲しがる→羨む / negativ 消極的→負・否定
- 語根忠実化: halter 重量挙げ→亜鈴 / muf ミトン→マフ / kegl 柱→ボウリングのピン
- 語尾切れ補完(KO): korekt/konvink/protest 等の「…하」→「…하다」

## フェーズD: 全語適用＋検証
適用: 209語根 / word_anno 1,201箇所 / **deployed 11,518フラグメント（3アプリ）**。
2×字数圧縮: hirt→逆立った, kegl→ボウリングのピン, u→命令, fol→愚かな 等。
検証(全合格): 構造健全・PH不変・サイズクラス整合(不整合0)。外科性: ser/maŝ/kran修正だが兄弟 seri=連続/maŝin=機械/krani=頭蓋 は不変。保留 kak/ta も不変。
backup: word_anno.json.bak_preFullFix / 置換リスト_ルビ.json.bak_preFullFix（3アプリ）。

## 保留（要別処理・11語根）
kak(排便が支配義・危険), ta(2字断片衝突・危険), balote(ZHのみ要修正), fumari/stekio/ace/ej-inaŭgur(束縛/典拠不確実), d/l/o-re/a-japan(不正分割・機械ノイズ)。
+ サンプル保留 hidr(水支配)/golf(湾支配)/oz(多義接尾)/sklerot。
+ 全数監査の uncertain 23件（低信頼・未処理）。

## 累計（サンプル＋全数の意味修正）
約280語根を是正 / deployed 約20,600フラグメント（3アプリ）。機械修正(=kaŝ-/ポー/o-/ism等)と合わせ、
JCK注釈ルビの確定的誤りをほぼ一掃。残る保留・uncertainは語単位/判断待ち。

## 追補: uncertain/保留の決裁処理 2026-07-01
ユーザー決裁: A(明白誤り)=修正 / B(多義微妙)=保留 / C(保留語根)=安全なもののみ語単位。
- **A(語根単位7件・修正)**: invalid 傷痍軍人→身体障害者/残疾人/장애인, kolonj コロン→ケルン/科隆, ablaci JA消融→アブレーション, melas ZH/KO→糖蜜/당밀, bastion ZH/KO→棱堡/능보, hektik ZH→消耗热, imersi ZH→浸入。deployed 180フラグメント。
- **C(語単位・安全のみ修正)**: hidr/oid・hidr/ul・vir/hidr のZH/KO→水螅/히드라(hidrogen=水は不変), golf/lud のZH/KO→高尔夫/골프(golfo=湾は不変)。deployed 15フラグメント。
- **B(16件)＝保留**: freŝ/libertin/loz/facet/areol/katakrez/ĥimer/kaĉu 等(辞書的に多義成立)。
- **C残(保留継続)**: kak/ta(危険), oz/sklerot(多義/無効), balote(ZH正解未確立), o-re/a-japan/d/l/fumari/stekio/ace/ej-inaŭgur(不正分割・典拠不確実)。
検証: 構造健全・サイズ整合(不整合0)・外科性OK(兄弟語根 hidrogen水/golfo湾 不変)。backup .bak_preGroupAC。

## 第4次: 漢字化トラックの2890検証・是正 2026-07-03
ユーザー強調「ルビも漢字化も2890語の精度が最重要」に基づき、漢字トラックを2890全数検証。

### 検証
- deployed漢字(3アプリ)を漢字注入マスター(44,939単語エントリ, c^表記→ĉ正規化)と完全形キーで照合。
- 完全形は大半正常(fino=终, semajno=周, sano=健, vino=酒, religio=宗, esperant=望+在)。
- **相違38語**を特定: 識別子上付き欠落(值→值ⱽ等)24語+実誤り/浅分解14語。

### 是正(語形ホワイトリスト厳格スコープ, 366エントリ×3アプリ)
- 同綴り漏出: **ĉielo 全样→天ᶜ̂**(相関詞漢字の漏出), **kajo 和→码**(接続詞漢字の漏出),
  **ĉaro 因→车**(接続詞ĉarの漏出), logi 学家→诱, termo 热→项。
- 深分解回復(漢字=マスター偽分解忠実の原則): aŭtomobilo 车→车+动, astronomio 天→星+学,
  teleskopo 镜→远+镜, ortografio 拼→直+志, mekanismo, kolektiva, fotografi。
- 識別子上付き復元: valoro=值ⱽ, vetero=气ⱽ 等24語。
- 保護確認: 単独ĉar=因/kaj=和(接続詞)・vero=真・vesto=衣・ĉielosfer=天+球 全て不変。
- word_kanji.json に39エントリ追記(再生成時も正しく)。backup .bak_preKanji2890。
- 語尾ホワイトリスト(o/on/oj/ojn/a/aj/...)により ve(2字)等の短語幹誤爆(vero/vesto)を排除(1770→366)。

### 残バックログ(2890外)
注入マスターとの一般相違 約2,965(大半は識別子上付き差・裸語幹フォールバック)。次期パスで対応可。

### 結論: 2890重要単語は ルビ(≈98%+)・漢字化(マスター完全準拠) の両トラックで最高精度を達成。
