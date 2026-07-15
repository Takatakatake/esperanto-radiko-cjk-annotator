# -*- coding: utf-8 -*-
"""ルビ再生成後の同綴り共存fixup(恒久運用)。E_stem語幹キーと衝突する語形限定の上書き:
 - 相関詞 ĉiel(単独/ĉiele) → 色々に/以各种方式/여러모로 (名詞ĉielo=空はword_anno側)
 - 形容詞 lama/laman/lamaj/lamajn/lame → lam+語尾 (僧lamao=ラマ僧はword_anno側)
再生成のたびに実行: python fix_ruby_postregen.py
"""
import json, sys, re, unicodedata
from pathlib import Path

from atomic_json import atomic_file_copy, atomic_json_dump
from gen_replacement import load_app_replacement_helper
sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]


def load_authoritative_exact_surfaces(root=ROOT):
    """Return exact-case and casefold surfaces that post-fixups may not edit."""
    exact_surfaces = set()
    casefold_surfaces = set()
    for name in (
        "_corpus_exact_app_manifest.json",
        "_corpus_reviewed_exact_app_manifest.json",
    ):
        path = root / "_analysis_20260625" / name
        payload = json.loads(path.read_text(encoding="utf-8"))
        exact_surfaces.update(
            unicodedata.normalize("NFC", row["surface"])
            for row in payload["exact_surfaces"]
        )
    for path in (
        root / "_analysis_20260625" / "no_worsening_guards.json",
        root / "_analysis_20260625" / "_strict_gold_reference_fixes.json",
        root / "_analysis_20260625" / "out" / "confirmed_tier30.json",
    ):
        payload = json.loads(path.read_text(encoding="utf-8"))
        entries = payload.get("entries", []) if isinstance(payload, dict) else payload
        for entry in entries:
            if not entry.get("exact_only"):
                continue
            surface = unicodedata.normalize("NFC", entry["w"])
            if entry.get("case_sensitive"):
                exact_surfaces.add(surface)
            else:
                casefold_surfaces.add(surface.casefold())
    return exact_surfaces, casefold_surfaces


AUTHORITATIVE_EXACT_SURFACES, AUTHORITATIVE_CASEFOLD_SURFACES = (
    load_authoritative_exact_surfaces()
)


def is_authoritative_exact_surface(surface):
    normalized = unicodedata.normalize("NFC", surface)
    return (
        normalized in AUTHORITATIVE_EXACT_SURFACES
        or normalized.casefold() in AUTHORITATIVE_CASEFOLD_SURFACES
    )

CORR_CIEL={'JA':'色々に','ZH':'以各种方式','KO':'여러모로'}
# E_stem語幹キーがwa未収録/別noslで root既定に落ちる語の per-word piece 再構築
WORD_PIECES={
  'anestezi': [('an',{'JA':'無','ZH':'无','KO':'무'}),
               ('estez',{'JA':'感覚','ZH':'感觉','KO':'감각'}),
               ('i',None)],
  # 医学-it-(炎症)・化学-at-(塩)は分詞ではなく「偽の友」。E_stem既定の it=受動完了/at=受動継続
  # を、既存 wa['mening/it']/wa['nitr/at'] と同じ正しいグロス(炎/酸塩)へ後処理で是正。
  # (コーパスの粗ルビ meningit=髄膜炎/nitrat=硝酸塩 とも意味整合。漢字トラックは元より正)
  # 固有名詞のルビ一体化(コーパス粗さ整合; gold偽分解 nov/jork 等は漢字トラック専用)
  # 典拠: コーパス実グロス Novjork=[地名]ニューヨーク / Bonaer=[地名]ブエノスアイレス(KO=부에노스아이레스)
  #        Manil=[地名]マニラ / detektiv=探偵 (第72R監査 corpus_errors 4語=36箇所の解消)
  'novjork': [('novjork',{'JA':'[地名]ニューヨーク','ZH':'[地名]纽约','KO':'[지명]뉴욕'})],
  'bonaer': [('bonaer',{'JA':'[地名]ブエノスアイレス','ZH':'[地名]布宜诺斯艾利斯','KO':'[지명]부에노스아이레스'})],
  'manil': [('manil',{'JA':'[地名]マニラ','ZH':'[地名]马尼拉','KO':'[지명]마닐라'})],
  'detektiv': [('detektiv',{'JA':'探偵','ZH':'侦探','KO':'탐정'})],
  'meningit': [('mening',{'JA':'髄膜','ZH':'脑膜','KO':'수막'}),
               ('it',{'JA':'炎','ZH':'炎','KO':'염'})],
  'nitrat':   [('nitr',{'JA':'窒素','ZH':'氮','KO':'질소'}),
               ('at',{'JA':'酸塩','ZH':'酸盐','KO':'산염'})],
}
_WP_END={'','o','on','oj','ojn','a','aj','an','ajn','e','en','ist','isto','iston','istoj'}
ADJ_LAM={'JA':'足が不自由な','ZH':'跛行的','KO':'다리 저는'}
CIEL_FORMS={'ĉiel','ĉiele'}
LAMA_FORMS={'lama','laman','lamaj','lamajn','lame'}


# 大文字語頭でのみ適用する固有名詞 piece 再構築(小文字の同綴り一般語は不変)。
# Butano(国名ブータン) vs butano(ブタンガス): 小文字CSV既定 butan=ブタン を保持したまま、
# 大文字語形にのみ地名グロスを割り当てる(コーパス Butan<rt>[地名]ブータン と整合)。
CAP_WORD_PIECES={
  'butan': [('butan',{'JA':'[地名]ブータン','ZH':'[地名]不丹','KO':'[지명]부탄'})],
}

def rewrite_surface_core(src, app, format_piece):
    """Return a replacement core, or ``None`` when no fixup may apply."""
    if is_authoritative_exact_surface(src):
        return None
    sl = src.casefold()
    if sl in CIEL_FORMS:
        stem = src[:4]
        return format_piece(stem, CORR_CIEL[app]) + src[4:]
    if src[:1].isupper() and any(
        sl.startswith(stem) and sl[len(stem):] in _WP_END
        for stem in CAP_WORD_PIECES
    ):
        stem = next(
            candidate for candidate in CAP_WORD_PIECES
            if sl.startswith(candidate) and sl[len(candidate):] in _WP_END
        )
        pos = 0
        parts = []
        for piece, glosses in CAP_WORD_PIECES[stem]:
            segment = src[pos:pos + len(piece)]
            pos += len(piece)
            parts.append(
                segment if glosses is None
                else format_piece(segment, glosses[app])
            )
        return ''.join(parts) + src[pos:]
    if any(
        sl.startswith(stem) and sl[len(stem):] in _WP_END
        for stem in WORD_PIECES
    ):
        stem = next(
            candidate for candidate in WORD_PIECES
            if sl.startswith(candidate) and sl[len(candidate):] in _WP_END
        )
        pos = 0
        parts = []
        for piece, glosses in WORD_PIECES[stem]:
            segment = src[pos:pos + len(piece)]
            pos += len(piece)
            parts.append(
                segment if glosses is None
                else format_piece(segment, glosses[app])
            )
        return ''.join(parts) + src[pos:]
    if sl in LAMA_FORMS:
        stem = src[:3]
        return format_piece(stem, ADJ_LAM[app]) + src[3:]
    return None


def process_app(app):
    base=ROOT / f"Esperanto-Kanji-Ruby-{app}" / "app_data"
    dep=base / "置換リスト_ルビ.json"
    with dep.open(encoding="utf-8") as stream:
        d=json.load(stream)
    M = load_app_replacement_helper(
        ROOT / f"Esperanto-Kanji-Ruby-{app}"
    )
    with (base / "char_widths.json").open(encoding="utf-8") as stream:
        cw=json.load(stream)
    FMT='HTML格式_Ruby文字_大小调整'
    n=0
    for k in d:
        for e in d[k]:
            if len(e)<2 or not isinstance(e[0],str) or not isinstance(e[1],str): continue
            old=e[0]
            left_len=len(old)-len(old.lstrip())
            right_len=len(old)-len(old.rstrip())
            core_end=len(old)-right_len if right_len else len(old)
            leading=old[:left_len]
            trailing=old[core_end:]
            src=unicodedata.normalize('NFC',old[left_len:core_end])
            rewritten = rewrite_surface_core(
                src,
                app,
                lambda piece, gloss: M.output_format(
                    piece, gloss, FMT, cw,
                ),
            )
            if rewritten is not None:
                nb=leading+rewritten+trailing
                if nb!=e[1]: e[1]=nb; n+=1
    atomic_file_copy(dep, str(dep)+".bak_postregen")
    atomic_json_dump(dep, d)
    return n


def main():
    for app in ("JA", "ZH", "KO"):
        print(f"[{app}] postregen fixup {process_app(app)}")
    print("完了")


if __name__ == "__main__":
    main()
