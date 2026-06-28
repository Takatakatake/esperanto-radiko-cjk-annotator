# -*- coding: utf-8 -*-
"""コーパス過分解(app片数>ref片数)のうち、gold(正本)が「より粗い(丸ごと)」分解を支持する語=
   アプリが真に誤っている語を tier19候補に。gold分解をtarget。
   tier18の教訓: 短い単一語根stemは部分文字列衝突→複合/長語幹のみ(保守的)。固有名詞も除外(gold不在)。"""
import re, sys, json, os, glob
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from extract_lib import hat_to_circumflex, replace_esperanto_chars
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()
OUT = BASE + r"\_analysis_20260625\out"
GOLD = r"\\wsl.localhost\Ubuntu\home\y\エスペラント辞書徹底語根分解_20260619\世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416.txt"
if not os.path.exists(GOLD):
    for b in reversed(sorted(glob.glob(os.path.join(os.environ['USERPROFILE'],'Downloads','エスペラント_backup_*')))):
        g=os.path.join(b,'語根分解辞書_WSL','世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416.txt')
        if os.path.exists(g): GOLD=g; break
gold_map={}
with open(GOLD,encoding='utf-8') as f:
    for line in f:
        line=line.rstrip('\n')
        if not line or line.startswith('##') or ':' not in line: continue
        for w in line.split(':')[0].split(' '):
            wc=norm(w)
            if '#' in wc or not wc: continue
            ps=[p for p in wc.split('/') if p]
            if ps: gold_map.setdefault(''.join(ps), ps)
cm = json.load(open(OUT + r"\corpus_mismatch.json", encoding="utf-8"))
def is_conservative(target):
    pieces=[p for p in target.split('/') if p]
    if len(pieces)<2: return False
    # stem = 末尾語尾を除いた部分
    end=pieces[-1]
    stem_pieces = pieces[:-1] if (end in ('o','a','e','i','n','j','oj','on','ojn','aj','an','ajn') ) else pieces
    if len(stem_pieces)>=2: return True            # 複合語幹(mal/fiks 等)=安全
    return len(stem_pieces[0])>=7                  # 長い単一語幹(akredit等)=安全
cands=[]; seen=set()
for entry in cm:
    ref, app = entry[0], entry[1]
    rp=[p for p in ref.split('/') if p]; ap=[p for p in app.split('/') if p]
    if len(ap)<=len(rp): continue                  # 過分解のみ
    w=''.join(rp)
    g=gold_map.get(w)
    if g is None: continue                          # goldに無い(固有名詞等)=除外
    # goldがappより粗い(=appが過分解)場合のみ。target=gold
    if len(g)>=len(ap): continue                     # goldもapp同等以上に分割=appが正しいかも→除外
    target='/'.join(g)
    if not is_conservative(target): continue
    if w in seen: continue
    seen.add(w); cands.append({"w":w,"target":target,"app":app})
json.dump([{"w":c["w"],"target":c["target"]} for c in cands],
          open(OUT + r"\confirmed_tier19.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"コーパス過分解 × gold支持丸ごと × 保守的 = {len(cands)}件")
for c in cands: print(f"  {c['w']:24s} gold={c['target']:22s} (app誤={c['app']})")
