# -*- coding: utf-8 -*-
"""第117R: ユーザー裁定「国名 -ujo 型は漢字トラックで 器 を用いる」(2026-08-08) の実装。
   DRY既定 / --apply。

■ 裁定(esperanto=望在o と同じ「ユーザー裁定 > マスター」方式)
  マスターexportは国名 -ujo 型をラテン維持と定める(Afgan/uj/o → Afganujo)が、
  ユーザーは 2026-08-08 に「漢字化エスペラントとしては Afgan/器/o が適切」と裁定した。
  対象は第116Rでラテン化した -ujo 国名型 **107語とその語尾変化形のみ**。
  他の固有名詞ラテン維持(Usono/Sara/Agripino等)は変更しない。
  裁定台帳: _ujo_country_adjudication_20260808.json(本スクリプトが生成)。
  ★fix_kanji_latin_maintained_r116.py はこの台帳を EXCLUDE として参照するよう改修済み
    (再実行しても裁定が巻き戻らない)。

■ 実装
  対象107語族の全キー(第116Rの $R116L 挿入行 + 値置換済みの既存全語キー)の**値だけ**を
  「語幹ラテン + <ruby>器<rt>uj</rt></ruby> + 語尾」のクリーン合成に差し替える。
  キー・位置・IDは一切動かさない。
  - 104語は第116R前の合成描画(X器o)と同じ見た目に戻る
  - ★3語(Lakonujo→简ᴸ器o / Lombardujo→当ᴸ器o / Trakujo→轨ᵀ器o)は第116R前が
    小文字語根(简ᴸ=簡潔/当ᴸ=質屋/轨ᵀ=軌道)に語幹を食われた欠陥形だったので、
    巻き戻しではなく Lakon器o 型のクリーン形にする(裁定の設計=語幹ラテン+器)
  - 器のマークアップは第116R原状台帳(out/r116_valuefix_ledger.json)の旧値から抽出し、
    全エントリで同一であることを検証(fail-closed・発明ゼロ)

■ 検証
  適用後に107語族×(基本形+on/oj/ojn)を3言語で再描画し、全て「語幹+器+語尾」で
  一致することを fail-closed で確認。ゲート側の期待値: エクスポート不一致 655→762
  (+107は本裁定の文書化された差分)・注入不変・3言語同一性PASS。
"""
import json, os, re, sys, argparse
sys.stdout.reconfigure(encoding='utf-8')
BS = chr(92); PFX = BS * 2 + chr(63) + BS
def LP(p): return PFX + os.path.abspath(p)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AN = os.path.join(ROOT, '_analysis_20260625')
sys.path.insert(0, AN)
from atomic_json import atomic_file_copy, atomic_json_dump

ap = argparse.ArgumentParser()
ap.add_argument('--apply', action='store_true')
A = ap.parse_args()
DRY = not A.apply
KEY = '全域替换用のリスト(列表)型配列(replacements_final_list)'

# ── 対象107語(第116Rでラテン化した -ujo 国名型の全数) ───────────────────────
UJO = ['Abisenujo','Afganujo','Akadujo','Akvitanujo','Albanujo','Arabujo','Armenujo',
'Baltujo','Bavarujo','Belgujo','Belorusujo','Beotujo','Bohemujo','Bretonujo','Britujo',
'Bulgarujo','Burgundujo','Dalmatujo','Danujo','Egiptujo','Englujo','Estonujo','Etiopujo',
'Etruskujo','Fenicujo','Finnujo','Flandrujo','Francujo','Frisujo','Galatujo','Galegujo',
'Gallujo','Gaskonujo','Grekujo','Helvetujo','Hesujo','Hindujo','Hispanujo','Hungarujo',
'Iberujo','Italujo','Japanujo','Jordanujo','Jorubujo','Judujo','Jugoslavujo','Kabilujo',
'Kafrujo','Kartvelujo','Katalunujo','Keltujo','Kimrujo','Kirgizujo','Koreujo','Kroatujo',
'Kurdujo','Lakonujo','Laponujo','Latvujo','Letonujo','Ligurujo','Litovujo','Livonujo',
'Lombardujo','Longobardujo','Luksemburgujo','Makedonujo','Malagasujo','Mariujo',
'Meksikujo','Moldavujo','Mongolujo','Normandujo','Norvegujo','Numidujo','Okcitanujo',
'Patagonujo','Persujo','Pikardujo','Polujo','Portugalujo','Prusujo','Rumanujo','Rutenujo',
'Sabenujo','Saksujo','Sardujo','Sarmatujo','Senegalujo','Serbujo','Skandinavujo','Skitujo',
'Slovakujo','Slovenujo','Somalujo','Sovetujo','Svedujo','Svisujo','Tatarujo','Toskanujo',
'Trakujo','Turkmenujo','Turkujo','Ukrainujo','Uzbekujo','Valonujo','Vjetnamujo']
assert len(UJO) == 107, len(UJO)
ENDS = {'': 'o', 'n': 'on', 'j': 'oj', 'jn': 'ojn'}
def family(w):
    return {w + suf: end for suf, end in ENDS.items()}  # 表層 -> 語尾(o/on/oj/ojn)
FAM = {}
for w in UJO:
    for s, end in family(w).items():
        FAM[s] = (w, end)

# ── 器マークアップの抽出(第116R原状台帳から・発明ゼロ) ─────────────────────
led = json.load(open(os.path.join(AN, 'out', 'r116_valuefix_ledger.json'), encoding='utf-8'))
marks = set()
for e in led['valuefix']:
    k = e['key'].strip()
    if k.endswith('ujo') and k in FAM:
        stem = k[:-3]
        old = e['old']
        if old.startswith(stem) and old.endswith('o'):
            marks.add(old[len(stem):-1])
if len(marks) != 1:
    raise SystemExit(f'fail-closed: 器マークアップが一意でない: {sorted(marks)[:3]} ({len(marks)}種)')
UJ = marks.pop()
print(f'器マークアップ(台帳から抽出): {UJ!r}')

def comp_value(surface):
    """表層(基本形or変化形)に対するクリーン合成値(語幹+器markup+語尾)。"""
    w, end = FAM[surface]
    return w[:-3] + UJ + end

# ── 3言語へ適用 ─────────────────────────────────────────────────────────
DATA = {}
for lang in ('JA', 'ZH', 'KO'):
    p = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}', 'app_data', '置換リスト_漢字.json')
    DATA[lang] = (p, json.load(open(LP(p), encoding='utf-8')))

plans = None
for lang in ('JA', 'ZH', 'KO'):
    path, dd = DATA[lang]
    gg = dd[KEY]
    plan = []
    for i, e in enumerate(gg):
        k = e[0]
        if not isinstance(k, str): continue
        s = k.strip()
        if s not in FAM: continue
        newv = k.replace(s, comp_value(s))  # キーの空白体裁を値に鏡映
        if e[1] != newv:
            plan.append((i, k, e[1], newv))
    if plans is None:
        plans = [(i, k) for i, k, _o, _n in plan]
        print(f'[JA] 値差替の対象キー: {len(plan)}')
        heads = [p_ for p_ in plan if p_[1].strip().endswith("ujo")]
        print(f'  内訳: 基本形 {len(heads)} / 変化形 {len(plan)-len(heads)}')
    else:
        if [(i, k) for i, k, _o, _n in plan] != plans:
            raise SystemExit(f'{lang}: 対象キー集合がJAと不一致(3言語同一性が壊れている)')
    if not DRY:
        for i, k, _old, newv in plan:
            gg[i] = [gg[i][0], newv, gg[i][2] if len(gg[i]) > 2 else '']
        atomic_file_copy(LP(path), LP(path + '.bak_preR117'))
        atomic_json_dump(LP(path), dd)
        print(f'[{lang}] 値差替 {len(plan)} キー(位置・キー・ID不変)')

# ── 検証: 107語族×4形を3言語で再描画 ─────────────────────────────────────
RT = re.compile(r'<rt[^>]*>(?:[^<]|<br\s*/?>)*?</rt>'); TAG = re.compile(r'<[^>]+>')
def disp(seg): return TAG.sub('', RT.sub('', seg)).strip()
def disp_expect(surface):
    return disp(' ' + comp_value(surface) + ' ')
surfaces = sorted(FAM)
sys.path.insert(0, os.path.join(ROOT, 'Esperanto-Kanji-Ruby-JA'))
import esp_text_replacement_module as M
bad_total = 0
for lang in ('JA', 'ZH', 'KO'):
    path, _ = DATA[lang]
    dd = json.load(open(LP(path), encoding='utf-8')) if not DRY else DATA[lang][1]
    gg = dd[KEY]
    app = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}')
    GL = dd['局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)']
    G2 = dd['二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)']
    ps_ = M.import_placeholders(os.path.join(app, 'app_data', 'placeholders_skip.txt'))
    pl_ = M.import_placeholders(os.path.join(app, 'app_data', 'placeholders_localcapture.txt'))
    if DRY:
        # DRYでは差替をメモリ上でだけ先行適用して見込みを検証
        gg = [list(e) for e in gg]
        for i, e in enumerate(gg):
            k = e[0]
            if isinstance(k, str) and k.strip() in FAM:
                gg[i][1] = k.replace(k.strip(), comp_value(k.strip()))
    B = 400; SEP = '◆'; out = {}
    for i in range(0, len(surfaces), B):
        ch = surfaces[i:i+B]
        o = M.orchestrate_comprehensive_esperanto_text_replacement(
            ' ' + (' ' + SEP + ' ').join(ch) + ' ', ps_, GL, pl_, gg, G2, '汉字替换_大小调整')
        parts = o.split(SEP)
        if len(parts) != len(ch):
            for w_ in ch:
                o1 = M.orchestrate_comprehensive_esperanto_text_replacement(
                    ' ' + w_ + ' ', ps_, GL, pl_, gg, G2, '汉字替换_大小调整')
                out[w_] = disp(o1)
        else:
            for w_, seg in zip(ch, parts): out[w_] = disp(seg)
    bad = [(s, out[s], disp_expect(s)) for s in surfaces if out[s] != disp_expect(s)]
    print(f'[{lang}] 描画検証: {len(surfaces)}表層中 不一致 {len(bad)}')
    for s, got, exp in bad[:10]: print(f'    ★ {s}: got={got} expect={exp}')
    bad_total += len(bad)
if bad_total:
    raise SystemExit('fail-closed: 描画検証で不一致あり')
print('検証OK: 107語族×4形×3言語 全て「語幹+器+語尾」')

if DRY:
    print('(DRY-RUN: --apply で書込)'); sys.exit(0)

adj = {
    'generated': '2026-08-08 第117R',
    'adjudication': 'ユーザー裁定: 国名 -ujo 型は漢字トラックで 器 を用いる(Afgan器o)。'
                    'マスターexportのラテン維持より本裁定が優先(esperanto=望在o と同方式)。'
                    '対象はこの107語族のみ。他の固有名詞ラテン維持は変更しない。'
                    'マスター側への変更提案(107行: Afgan/uj/o の描画列→Afgan/器/o)は照会中。',
    'words': UJO,
}
json.dump(adj, open(LP(os.path.join(AN, '_ujo_country_adjudication_20260808.json')), 'w',
                    encoding='utf-8'), ensure_ascii=False, indent=1)
print('裁定台帳を保存: _ujo_country_adjudication_20260808.json')
print('適用完了。ゲート(export/injection/3言語同一性)を必ず回すこと。')
