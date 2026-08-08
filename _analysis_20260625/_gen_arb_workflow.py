# -*- coding: utf-8 -*-
"""係争語データセット(_disputed_all.json)を読み、Esペラント形態論 敵対裁定ワークフローの
   JSファイル(_arb_workflow.js)を DATA 埋め込みで生成する。"""
import json, os, sys
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
OUT = BASE + r"\_analysis_20260625\out"
ds = json.load(open(os.path.join(OUT, "_disputed_all.json"), encoding="utf-8"))
for i, d in enumerate(ds):
    d["id"] = i
DATA_JS = json.dumps(ds, ensure_ascii=False)

js = r'''export const meta = {
  name: 'corpus-decomp-arbitration-v2',
  description: '京大エス研コーパス係争語198件をEsペラント形態論専門家で敵対裁定(コーパス誤り/app誤り/両者妥当を確証)',
  phases: [
    { title: '裁定', detail: '専門家2名が独立に全係争語を裁定' },
    { title: '調停', detail: '2名が割れた語を調停' },
  ],
}

const DATA = __DATA__;

function chunk(a, n) { const o = []; for (let i = 0; i < a.length; i += n) o.push(a.slice(i, i + n)); return o; }

const MORPH = `あなたはエスペラント形態論(PMEG/PIV準拠)の専門家です。各単語について「学習者にとって有用な語根分解」=各片が実在のエスペラント形態素(語根・接辞・文法語尾)で、それ自身の意味を持つ分解、の観点で、提示された2案 CORPUS と APP のどちらが形態論的に正しいかを中立に判定してください。どちらかに肩入れせず、純粋に形態論で判断すること。

判定の原則:
1. 実在語根のみ。単一形態素の語根を偶然の部分文字列に割ってはならない。例: platformo=platform/o(正), plat/form/o は誤り。ocelo=ocel/o(正), o/cel/o は誤り。meritokratio の正は merit/o/krat/i/o 系であり merit/ok/rati/o(APP)は綴り割れの誤り。
2. 接辞は実在なら割る。-ad-,-ism-,-ist-,-it-,-at-,-ig-,-ec-,-ul-,-in-,-an-,-iĉ-,-um- 等。例: far/ad/o(正) ≠ farad/o, faŝ/ism/o(正) ≠ faŝism/o, lingv/ist/o(正) ≠ lingvist/o, komun/um/o(正) ≠ komunum/o, jun/ul/iĉ/oj(正)。
3. 国際語接尾辞 -log-(学), -graf-(記述), -logi-/-grafi- 等を含む学術語: 例 biologio は bio/logi/o あるいは bi/o/log/i/o の分析が学習者標準で、biologi/o(一体)はやや粗い。zoologia=zo/o/logi/a, geologio=geo/logi/o の類は分析側が正しい。
4. 国名・地名の -i-: ROOT/i/o (例 ĉin/i/o, ital/i/o) が最も分析的な標準。ROOT/io や ROOTi/o は粗い変種。これらは形態論的にどちらも許容されるので BOTH_VALID とせよ(構造的天井)。
5. 固有名詞・外来語(地名/人名/商標/借用語)は丸ごと語根+文法語尾に留めるのが正しい。エスペラント語根に砕くのは誤り。例: Vroclavo=vroclav/o(正), vroc/lav/o は誤り。Tokio=tokio/+...(地名), Jutubo=jutub/o(YouTube借用,正), ju/tub/o は誤り。Tokipono=tokipon/...(Toki Pona,正), toki/po/n... は誤り。Kievo, Oomoto, Kamakuro, Enoŝima, Jokohama 等も同様。
6. ホモグラフ(同綴り異義): 表層が動詞分解とも固有名詞丸ごととも読める場合は BOTH_VALID。例: amas=am/as(愛する) か 固有名 Amas か; tenis=ten/is(保持した) か tennis(球技) か; anton=ant/on か 人名 Anton か。走行文中で両読み妥当なら BOTH_VALID。
7. レキシカル化国際語: esperanto=esperant/o(慣用一語), esper/ant/o は語源的だが現代では一体が標準。同様に語彙化した語は一体側を正とすることがある。

各案の表記は スラッシュ区切り。CORPUS と APP のどちらの「切れ目(境界)」が正しいかを見る(文法語尾 o/a/e/n/j/as/is 等の扱いも含む)。

出力(各 # に対し1件, JSON):
  id    : 提示された番号(整数)
  side  : "CORPUS_RIGHT"(CORPUS案が正・APPが誤り) | "APP_RIGHT"(APP案が正・CORPUSが誤り=コーパス側の分解ミス) | "BOTH_VALID"(両案とも形態論的に許容=ホモグラフ/国名-i/構造天井) | "NEITHER"(両案とも誤りで正解は第三の分解)
  correct : あなたが考える正しい分解(スラッシュ区切り)
  conf  : 確信度 0.0-1.0
  reason: 30字以内の根拠(日本語可)`;

function fmt(batch) {
  return batch.map(d => `#${d.id} "${d.w}"  CORPUS=${d.c}  APP=${d.a}` + (d.g ? `  (gold=${d.g})` : '')).join('\n');
}
function judgePrompt(batch) {
  return `${MORPH}\n\n=== 判定対象 ${batch.length}件 ===\n${fmt(batch)}\n\n全 ${batch.length} 件について verdicts 配列で返すこと。`;
}
function arbiterPrompt(rows) {
  const body = rows.map(m => `#${m.id} "${m.w}"  CORPUS=${m.corpus}  APP=${m.app}` + (m.gold ? `  (gold=${m.gold})` : '') +
    `\n    判定A=${m.sideA}(${m.correctA||''}; ${m.reasonA||''})  判定B=${m.sideB}(${m.correctB||''}; ${m.reasonB||''})`).join('\n');
  return `${MORPH}\n\n以下は2名の専門家の判定が割れた語です。各語を再検討し、最終判定を下してください。AかBのどちらかに合わせる必要はなく、形態論的に正しい結論を出すこと。\n\n${body}\n\n全 ${rows.length} 件について verdicts 配列で最終判定を返すこと。`;
}

const JUDGE_SCHEMA = {
  type: 'object',
  properties: {
    verdicts: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'integer' },
          side: { type: 'string', enum: ['CORPUS_RIGHT', 'APP_RIGHT', 'BOTH_VALID', 'NEITHER'] },
          correct: { type: 'string' },
          conf: { type: 'number' },
          reason: { type: 'string' },
        },
        required: ['id', 'side', 'correct', 'conf', 'reason'],
      },
    },
  },
  required: ['verdicts'],
};

phase('裁定');
const BATCHES = chunk(DATA, 18);
log(`係争語 ${DATA.length} 件を ${BATCHES.length} バッチ × 専門家2名で裁定`);
const judged = await pipeline(
  BATCHES,
  batch => parallel([
    () => agent(judgePrompt(batch), { label: `judgeA#${batch[0].id}-${batch[batch.length-1].id}`, phase: '裁定', schema: JUDGE_SCHEMA }),
    () => agent(judgePrompt(batch), { label: `judgeB#${batch[0].id}-${batch[batch.length-1].id}`, phase: '裁定', schema: JUDGE_SCHEMA }),
  ]).then(([a, b]) => ({ batch, a, b }))
);

const merged = [];
for (const r of judged.filter(Boolean)) {
  const ma = new Map((r.a && r.a.verdicts || []).map(v => [v.id, v]));
  const mb = new Map((r.b && r.b.verdicts || []).map(v => [v.id, v]));
  for (const d of r.batch) {
    const va = ma.get(d.id), vb = mb.get(d.id);
    merged.push({
      id: d.id, w: d.w, corpus: d.c, app: d.a, gold: d.g, n: d.n, bucket: d.b,
      sideA: va ? va.side : '?', sideB: vb ? vb.side : '?',
      correctA: va ? va.correct : '', correctB: vb ? vb.correct : '',
      reasonA: va ? va.reason : '', reasonB: vb ? vb.reason : '',
      agree: !!(va && vb && va.side === vb.side),
    });
  }
}
const disagree = merged.filter(m => !m.agree);
log(`一致 ${merged.length - disagree.length}/${merged.length} 語、不一致 ${disagree.length} 語を調停へ`);

phase('調停');
let arbMap = new Map();
if (disagree.length) {
  const arb = await agent(arbiterPrompt(disagree), { label: 'arbiter', phase: '調停', schema: JUDGE_SCHEMA });
  arbMap = new Map((arb.verdicts || []).map(v => [v.id, v]));
}

const final = merged.map(m => {
  const av = arbMap.get(m.id);
  const side = m.agree ? m.sideA : (av ? av.side : m.sideA);
  const correct = m.agree ? (m.correctA || m.correctB) : (av ? av.correct : m.correctA);
  const reason = m.agree ? (m.reasonA || m.reasonB) : (av ? av.reason : m.reasonA);
  return { id: m.id, w: m.w, corpus: m.corpus, app: m.app, gold: m.gold, n: m.n, bucket: m.bucket,
           side, correct, reason, agreed: m.agree, sideA: m.sideA, sideB: m.sideB };
});

const tallyInst = {}, tallyWord = {};
for (const f of final) { tallyInst[f.side] = (tallyInst[f.side] || 0) + f.n; tallyWord[f.side] = (tallyWord[f.side] || 0) + 1; }
const corpusErrors = final.filter(f => f.side === 'APP_RIGHT').sort((a, b) => b.n - a.n);
const appErrors = final.filter(f => f.side === 'CORPUS_RIGHT').sort((a, b) => b.n - a.n);
const bothValid = final.filter(f => f.side === 'BOTH_VALID').sort((a, b) => b.n - a.n);
const neither = final.filter(f => f.side === 'NEITHER').sort((a, b) => b.n - a.n);

return {
  total_words: final.length,
  total_inst: final.reduce((s, f) => s + f.n, 0),
  agreement: `${merged.length - disagree.length}/${merged.length}`,
  tallyInst, tallyWord,
  corpusErrors, appErrors, bothValid, neither,
};
'''

js = js.replace("__DATA__", DATA_JS)
path = BASE + r"\_analysis_20260625\_arb_workflow.js"
open(path, "w", encoding="utf-8").write(js)
print(f"生成: {path}  ({len(js)} bytes, DATA {len(ds)} 件)")
