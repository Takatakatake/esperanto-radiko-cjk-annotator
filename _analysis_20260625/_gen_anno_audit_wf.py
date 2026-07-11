# -*- coding: utf-8 -*-
"""日中韓注釈ルビ 敵対監査ワークフローJSを生成(_anno_audit_dataset.json 埋め込み)。"""
import json, os, sys
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
OUT = BASE + r"\_analysis_20260625\out"
ds = json.load(open(os.path.join(OUT, "_anno_audit_dataset.json"), encoding="utf-8"))
DATA_JS = json.dumps(ds, ensure_ascii=False)

js = r'''export const meta = {
  name: 'jck-annotation-audit',
  description: '日中韓注釈ルビ277件(分解不一致108/言語欠落29/グロス標本140)をEsペラント形態論+日中韓ネイティブで敵対監査',
  phases: [ { title: '監査', detail: '専門家2名が独立に全件を監査' }, { title: '調停', detail: '割れた項目を調停' } ],
}

const DATA = __DATA__;
function chunk(a, n) { const o = []; for (let i = 0; i < a.length; i += n) o.push(a.slice(i, i + n)); return o; }

const RULES = `あなたはエスペラント形態論(PMEG/PIV)の専門家であり、日本語・中国語(簡体)・韓国語のネイティブ校正者です。エスペラント学習ツールの「注釈ルビ」を監査します。各語根には日中韓それぞれで、その**語根自身の意味**(語根忠実=全体語義でなく根の意味)の短い訳が付き、3言語は**並行**(同じ意味を各言語で)であるべきです。

項目は3種:
- "GLOSS" {root, ja, zh, ko}: 各言語のグロスが、その語根の正しい・語根忠実な訳か? 3言語が並行(同義)か? 誤訳/非並行/非語根忠実を指摘。
- "GAP" {root, ja, zh, ko の一部がnull}: ある言語の訳が欠落。欠落言語に入れるべき正しい訳(他言語と並行)を示す。不要な語根なら note で説明。
- "DIVERGE" {w, JA/ZH/KO = [[語根,訳],...]}: 3アプリがこの語を別々に分解した。形態論的に正しい分解はどれか(JA/ZH/KO のいずれか, または別)を判断し、各言語の**誤グロス**を指摘(特に分割側で根が誤訳されるもの)。

重要な判断原則:
1. 国際語の分割で生じる典型的誤グロス(必ず誤りとして指摘):
   - antibiotik を anti+bio+**tik** と割り tik を「被套布/티킹(寝具生地)」とするのは誤り(-tik-は科学接尾辞 or 借用語の一部)。
   - ekologi を **ek**+ologi と割り ek を「开始/시작(起動接頭ek-)」とするのは誤り(eco=eko、起動のek-ではない)。
   - dialog を **dia**+log と割り「通过/言」は誤り(dialog=対話で一語; dia-は接頭でない)。
   - hidrogen/oksigen を hidr/oksi+**gen** と割るのは可だが、固有の化学語として一語(水素/酸素)も妥当。
   - radiofoni を radio+foni と割り radio を「光线/광선」とするのは文脈誤り(ここは無線/ラジオ)。
   - 一般に、語源的破片が実在の別語根と偶然一致して無関係な意味を当てる「偽の友」を厳しく見る。
2. 国名・地名語根 + -an-: 例 brazilano = brazil(ブラジル) + an(成員/-ano). **-an-(成員)を別ルビにするのが正**。KOで-anを落として地名だけにするのは欠落(不足)。
3. 語根忠実: 合成語義を一語根に押し込めない。ただし真の一語借用語(esperant, telefon 等)は一体も可。
4. 同綴り異義(homograph)に注意: drag(浚渫する/dredge)≠ drako(竜); ten(保持)≠ 等。

各項目について判定を返す:
  id     : 番号
  status : "OK"(問題なし) | "ISSUE"(誤り/欠落/不一致あり)
  correct_decomp : DIVERGE のみ。正しい語根分解(スラッシュ区切り, 例 "brazil/an/o")。他は ""。
  problems : [{lang:"ja"|"zh"|"ko", current:"現在の訳(無ければ空)", correct:"正しい訳", why:"30字以内理由"}] (無ければ空配列)
  note   : 補足(30字以内, 日本語可)`;

function fmtItem(d) {
  if (d.t === 'GLOSS' || d.t === 'GAP')
    return `#${d.id} [${d.t}] root="${d.root}"  ja=${d.ja || '∅'}  zh=${d.zh || '∅'}  ko=${d.ko || '∅'}`;
  const g = l => (d[l] || []).map(x => `${x[0]}[${x[1]}]`).join('+');
  return `#${d.id} [DIVERGE] "${d.w}"  JA: ${g('JA')}   ZH: ${g('ZH')}   KO: ${g('KO')}`;
}
function judgePrompt(batch) {
  return `${RULES}\n\n=== 監査対象 ${batch.length}件 ===\n${batch.map(fmtItem).join('\n')}\n\n全 ${batch.length} 件について verdicts 配列で返すこと。`;
}
function arbiterPrompt(rows) {
  const body = rows.map(m => `${fmtItem(m.item)}\n   判定A=${m.a && m.a.status}(${JSON.stringify(m.a && m.a.problems || [])}) 判定B=${m.b && m.b.status}(${JSON.stringify(m.b && m.b.problems || [])})`).join('\n');
  return `${RULES}\n\n以下は2名の判定が割れた項目。各々を再検討し最終判定を verdicts 配列で返すこと。\n\n${body}`;
}

const SCHEMA = {
  type: 'object', properties: { verdicts: { type: 'array', items: {
    type: 'object', properties: {
      id: { type: 'integer' },
      status: { type: 'string', enum: ['OK', 'ISSUE'] },
      correct_decomp: { type: 'string' },
      problems: { type: 'array', items: { type: 'object', properties: {
        lang: { type: 'string', enum: ['ja', 'zh', 'ko'] }, current: { type: 'string' }, correct: { type: 'string' }, why: { type: 'string' } },
        required: ['lang', 'current', 'correct', 'why'] } },
      note: { type: 'string' } },
    required: ['id', 'status', 'correct_decomp', 'problems', 'note'] } } },
  required: ['verdicts'],
};

phase('監査');
const BATCHES = chunk(DATA, 16);
log(`注釈監査 ${DATA.length}件 を ${BATCHES.length}バッチ×専門家2名`);
const judged = await pipeline(BATCHES,
  batch => parallel([
    () => agent(judgePrompt(batch), { label: `audA#${batch[0].id}`, phase: '監査', schema: SCHEMA }),
    () => agent(judgePrompt(batch), { label: `audB#${batch[0].id}`, phase: '監査', schema: SCHEMA }),
  ]).then(([a, b]) => ({ batch, a, b }))
);
const byId = new Map(DATA.map(d => [d.id, d]));
const merged = [];
for (const r of judged.filter(Boolean)) {
  const ma = new Map((r.a && r.a.verdicts || []).map(v => [v.id, v]));
  const mb = new Map((r.b && r.b.verdicts || []).map(v => [v.id, v]));
  for (const d of r.batch) {
    const va = ma.get(d.id), vb = mb.get(d.id);
    const sa = va ? va.status : '?', sb = vb ? vb.status : '?';
    merged.push({ id: d.id, item: d, a: va, b: vb, agree: sa === sb, bothIssue: sa === 'ISSUE' && sb === 'ISSUE' });
  }
}
const disagree = merged.filter(m => !m.agree);
log(`一致 ${merged.length - disagree.length}/${merged.length}, 不一致 ${disagree.length} を調停`);

phase('調停');
let arb = new Map();
if (disagree.length) {
  for (const ch of chunk(disagree, 24)) {
    const a = await agent(arbiterPrompt(ch), { label: 'arbiter', phase: '調停', schema: SCHEMA });
    for (const v of (a.verdicts || [])) arb.set(v.id, v);
  }
}

const final = merged.map(m => {
  let v;
  if (m.agree) v = m.bothIssue ? (m.a.problems && m.a.problems.length >= (m.b.problems||[]).length ? m.a : m.b) : m.a;
  else v = arb.get(m.id) || m.a || m.b;
  return { id: m.id, t: m.item.t, key: m.item.w || m.item.root, status: v ? v.status : '?',
           correct_decomp: v ? v.correct_decomp : '', problems: v ? v.problems : [], note: v ? v.note : '', agreed: m.agree };
});
const issues = final.filter(f => f.status === 'ISSUE');
const byType = {};
for (const f of final) { byType[f.t] = byType[f.t] || { total: 0, issue: 0 }; byType[f.t].total++; if (f.status === 'ISSUE') byType[f.t].issue++; }
return {
  total: final.length, issues: issues.length, agreement: `${merged.length - disagree.length}/${merged.length}`,
  byType,
  issueList: issues.sort((a, b) => a.t.localeCompare(b.t)),
};
'''
js = js.replace("__DATA__", DATA_JS)
path = BASE + r"\_analysis_20260625\_anno_audit_wf.js"
open(path, "w", encoding="utf-8").write(js)
print(f"生成: {path} ({len(js)} bytes, DATA {len(ds)}件)")
