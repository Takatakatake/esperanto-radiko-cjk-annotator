# -*- coding: utf-8 -*-
"""第67R: ルビの語頭食い込み(head truncation)を語スコープ後処理で是正する。DRY既定/--apply。

■ 症状
  gastronomio → g<ruby>astronomi<rt>天文学</rt></ruby>o
  美食学(胃の学)に「天文学」のルビが振られる。学習者を明確に誤らせる実害。
  同型: kanalizi→分析する / prigardi→眺める / fleganto→読む / klisteri→リステリア など。

■ 原因
  全域置換リストで、同じ長さ帯のキーのうち「語の途中から一致する方」が先に適用される。
    astronomio (10字) idx=33989  ← 先に適用され gastronomio の2文字目以降を消費
    gastronomi (10字) idx=42960  ← 正しいのに出番が来ない
  正しい語幹エントリは3言語×3変種すべてに存在しており、順番だけの問題である。

■ なぜ再生成でなく後処理か
  ルビ軌道は Phase513→532→558 の認証連鎖にピン留めされており、gold がドリフトした現在
  apply_confirmed_now は fail-closed で停止する(academic Ruby authority mismatch →
  参照manifest更新 → incoherent Phase 532 activation state)。
  10語のために認証基盤を作り直すのは本末転倒なので、漢字側 fix_kanji_master_residual.py と
  同じ「生成済みJSONの語スコープ後処理」で閉じる。

■ 安全設計
  1. 既存の正しい語幹エントリの描画を**そのまま再利用**する(訳語を発明しない)。
     各言語の各大小変種から取るので、3言語の分節同一性は構造的に保たれる。
  2. 追加キーは**空白パディング(語境界)**。完全一致でしか発火せず、
     psikanalizo/klisteraĵo/flegantino 等の長語には原理的に波及しない。
  3. リスト**先頭**に挿入して確実に競合より先に適用させる。
  4. プレースホルダは専用名前空間 $R67H…$ で既存と衝突しない。
  5. SATano は除外。語根 SATan の訳語がどの言語のルビCSVにも無く、
     発明になるため。マスター側への照会項目とする。
"""
import json, os, sys, re, argparse
sys.stdout.reconfigure(encoding='utf-8')
BS = chr(92); PFX = BS*2 + chr(63) + BS
def LP(p): return PFX + os.path.abspath(p)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, '_analysis_20260625'))
from atomic_json import atomic_file_copy, atomic_json_dump

ap = argparse.ArgumentParser()
ap.add_argument('--apply', action='store_true')
A = ap.parse_args()
DRY = not A.apply

# 語 -> (正しい語幹, 付く文法語尾)  ※gold分解に完全準拠(マスターは読み取りのみ)
#   gastronomio  gastr/o/nomi/o      gastronomia gastr/o/nomi/a
#   gastronomo   gastr/o/nom/o       kanalizi    kanal/iz/i
#   klisteri     klister/i           anaerobia   a/n/aer/o/bi/a
#   fleganto     fleg/ant/o          spontono    sponton/o
#   prigardi     pri/gard/i
#  ★flegant は除外。既存の語幹エントリの分節が3言語で食い違っている
#    (JA=fleg / ZH=fleg/ant / KO=fleg/ant)。そのまま再利用すると
#    「日中韓で分解は完全一致」というユーザー最重要要件を、この修正自身が壊す。
#    現状は3言語とも同じ誤り(leg/ant)で一致しているため、直すなら3言語の
#    語幹側を揃えてからにする。別ラウンドの課題として送る。
STEMS = ['gastronomi', 'gastronom', 'kanaliz', 'klister', 'anaerobi',
         'sponton', 'prigard']
# 文法語尾のみ(それ自体はルビ非対象なので素のまま連結する)
ENDINGS = ['o', 'on', 'oj', 'ojn', 'a', 'aj', 'an', 'ajn', 'e', 'en',
           'i', 'as', 'is', 'os', 'us', 'u']
KEY = '全域替换用のリスト(列表)型配列(replacements_final_list)'

def variants(s):
    """lower / UPPER / Capitalized の3変種(既存リストの規約と同じ)。"""
    return [(s, str.lower), (s.upper(), str.upper), (s[0].upper() + s[1:], lambda x: x)]

# --- 事前ガード: 使う語幹の分節が3言語で完全一致することを強制検証する ---
# 「ルビは粗くてよいが、日中韓で分解は完全一致していないといけない」という最重要要件を、
# この修正自身が壊さないための自己防衛。実測で flegant が JA=fleg / ZH,KO=fleg/ant と
# 食い違っていたため、この検査を通らない語幹は使わない。
_RUBY = re.compile(r'<ruby>([^<]*)<rt[^>]*>([^<]*)</rt></ruby>')
_idx_all = {}
for _app in ('JA', 'ZH', 'KO'):
    _p = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{_app}', 'app_data', '置換リスト_ルビ.json')
    _d = json.load(open(LP(_p), encoding='utf-8'))
    _m = {}
    for _e in _d[KEY]:
        if len(_e) >= 2 and isinstance(_e[0], str) and _e[0] not in _m:
            _m[_e[0]] = _e[1]
    _idx_all[_app] = _m
_bad = []
for _s in STEMS:
    for _f in (_s, _s.upper(), _s[0].upper() + _s[1:]):
        _segs = {}
        for _app in ('JA', 'ZH', 'KO'):
            _v = _idx_all[_app].get(_f)
            _segs[_app] = '/'.join(p for p, _ in _RUBY.findall(_v)) if _v else None
        if _segs['JA'] is None or not (_segs['JA'] == _segs['ZH'] == _segs['KO']):
            _bad.append((_f, _segs))
if _bad:
    for _f, _segs in _bad:
        print(f'  ★3言語で分節不一致: {_f!r} JA={_segs["JA"]} ZH={_segs["ZH"]} KO={_segs["KO"]}')
    raise SystemExit('3言語の分節が一致しない語幹が含まれる: 修正を中止')
print(f'事前ガード: {len(STEMS)}語幹 ×3変種 すべて3言語で分節一致 ✓')

total_added = 0
for app in ('JA', 'ZH', 'KO'):
    path = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{app}', 'app_data', '置換リスト_ルビ.json')
    d = json.load(open(LP(path), encoding='utf-8'))
    GG = d[KEY]
    idx = {}
    for e in GG:
        if len(e) >= 2 and isinstance(e[0], str) and e[0] not in idx:
            idx[e[0]] = e[1]
    existing_keys = {e[0] for e in GG if len(e) >= 1 and isinstance(e[0], str)}
    used_ph = {e[2] for e in GG if len(e) > 2}

    new_rows = []; n = 0; skipped = 0
    for stem in STEMS:
        for form, casefn in variants(stem):
            render = idx.get(form)
            if render is None:
                print(f'  [{app}] ★語幹エントリ無し: {form!r} → この変種はスキップ')
                continue
            for end in ENDINGS:
                e2 = casefn(end) if form.isupper() else end
                key = ' ' + form + e2 + ' '
                if key in existing_keys:
                    skipped += 1
                    continue          # 既に語境界エントリがあるなら触らない
                ph = f' $R67H{n:04d}{"" if app == "JA" else app}$ '
                if ph in used_ph:
                    raise SystemExit(f'placeholder collision: {ph}')
                new_rows.append([key, ' ' + render + e2 + ' ', ph])
                existing_keys.add(key); n += 1
    print(f'[{app}] 追加 {len(new_rows)} 件 (既存につきスキップ {skipped})')
    for r in new_rows[:4]:
        print(f'     {r[0]!r} -> {r[1][:88]!r}')
    total_added += len(new_rows)
    if not DRY:
        d[KEY] = new_rows + GG          # 先頭に挿入=競合より先に適用
        atomic_file_copy(LP(path), LP(path + '.bak_preHeadTrunc'))
        atomic_json_dump(LP(path), d)
        print(f'     保存({os.path.basename(path)}) 全域 {len(GG)} -> {len(d[KEY])}')

print(f'\n合計 {total_added} 件' + ('  (DRY-RUN: --apply で書込)' if DRY else '  適用完了'))
print('※ SATano は語根 SATan の訳語が全言語のルビCSVに無いため除外(マスター照会項目)')
