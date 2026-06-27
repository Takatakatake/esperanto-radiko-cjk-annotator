# -*- coding: utf-8 -*-
"""短語根の語義不一致候補(_xcheck_candidates.json の2-3字)から、グロス監査ワークフローJSを生成。
LLMが各語根を CONSISTENT / HOMOGRAPH / ERROR に分類(ruby ja/zh と 漢字master の意味整合)。"""
import sys, json
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r".")
from gen_replacement import lp
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
cand = json.load(open(lp("out/_xcheck_candidates.json"), encoding="utf-8"))
items = [{"r": d["r"], "ja": d["ja"], "zh": d["zh"], "k": d["k"]} for d in cand if 2 <= len(d["r"]) <= 3]
data_js = json.dumps(items, ensure_ascii=False)
OUTJS = BASE + r"\.claude_wf_gloss_audit.js"  # placeholder; 実際は下でscriptPath用に別所へ
js = '''export const meta = {
  name: 'gloss-faithfulness-audit',
  description: 'Audit short-root ruby glosses vs kanji master for sense faithfulness (CONSISTENT/HOMOGRAPH/ERROR)',
  phases: [ { title: '監査' } ],
}
const ITEMS = %s
if (!Array.isArray(ITEMS) || ITEMS.length===0 || ITEMS.length>400 || !ITEMS[0].r) throw new Error('ITEMS不正')
const SCHEMA = { type:'object', properties:{ items:{ type:'array', items:{ type:'object', properties:{
  r:{type:'string'}, verdict:{type:'string', enum:['CONSISTENT','HOMOGRAPH','ERROR']},
  wrong:{type:'string', description:'ERROR時、誤っているソース: ja|zh|kanji|"" '},
  correct:{type:'string', description:'ERROR時の正しい意味(簡潔)。それ以外は""'},
  note:{type:'string', description:'簡潔な根拠(日本語)'} }, required:['r','verdict','wrong','correct','note'] } } }, required:['items'] }
const COMMON = `あなたはエスペラント語根の専門家です。各エスペラント語根について、ルビ訳(ja=日本語, zh=中国語)と漢字master(k=参照2のキュレーション済み代表漢字)の意味整合を判定します。

# 判定区分
- CONSISTENT: ruby訳と漢字が「同じ概念」。代表字が別字でも意味が一致すれば CONSISTENT。
  例 ad:継続/持续/行(行=継続の意,一致), av:祖父/祖父/爷(爷=祖父,一致), ist:従事者/从事者/家(家=専門家,一致), ul:人/人/者(一致), jun:若い/年轻/幼(一致)。
- HOMOGRAPH: その綴りが複数の独立語根を表し、ソースが別々の正しい語義を採用している(両方正しい)。
  例 di:二(di-接頭=2) vs 神(dio=神), bi:二(bi-=2) vs 生(bio-=生命), fer:休日(ferio) vs 鉄(fero), pir:火(piro-) vs 梨(piro), lin:線(linio) vs 亜麻(lino), fol:葉(folio) vs 愚(fola=狂)。
- ERROR: いずれかのソースがこの語根の意味として明確に誤り(別語根の意味が混入)。
  例 hum:humus(腐植土)なのに zh=人类(人間=hom/humanの意が混入)→ ERROR(wrong=zh, correct=腐植土)。
     kak:排便/糞(kaki)なのに zh=可可(cocoa=kakaoが混入)→ ERROR(wrong=zh, correct=排便)。

# 注意
- 漢字masterは単一の代表字なので、ruby訳より粗いのは当然(それだけでERROR/HOMOGRAPHにしない)。
- 確信が持てない/微妙は CONSISTENT 寄りに(過剰なERROR/HOMOGRAPH判定を避ける)。
- r は入力からそのままコピー。`
function batches(a,s){const o=[];for(let i=0;i<a.length;i+=s)o.push(a.slice(i,i+s));return o}
const CH=batches(ITEMS,28)
const res=await parallel(CH.map((c,ci)=>()=>agent(`${COMMON}\\n\\n候補(JSON配列):\\n${JSON.stringify(c)}`,{label:`audit:${ci}`,phase:'監査',schema:SCHEMA})))
const all=[]; for(const r of res.filter(Boolean)) if(r.items) all.push(...r.items)
const err=all.filter(x=>x.verdict==='ERROR'); const homo=all.filter(x=>x.verdict==='HOMOGRAPH')
log(`CONSISTENT=${all.filter(x=>x.verdict==='CONSISTENT').length} HOMOGRAPH=${homo.length} ERROR=${err.length}`)
return { error: err, homograph: homo, total: all.length }
''' % data_js
import os
dest = r"C:\Users\yt\.claude\projects\D--GoogleDrive202510--------20----------------------------20260624--analysis-20260625\46f52639-acfa-48a8-8c2f-e95e8e59b22d\workflows\scripts\gloss-audit.js"
with open(lp(dest), "w", encoding="utf-8") as f:
    f.write(js)
print("候補件数:", len(items))
print("WF書込:", dest)
