# -*- coding: utf-8 -*-
"""
esp_overlay_module.py  --- 語根分解の「手動補正」軽量オーバーレイ・エンジン

GUI(ページ「語根分解の手動補正」)でユーザが「この単語はこう分解せよ」と指定した補正を、
50MBの置換用JSONを再生成せずに main.py の実行時へ最優先で適用する仕組み。

設計のポイント:
  - 補正の保存時のみ、1語分のルビ/漢字エントリ(<ruby>…</ruby>)を生成する(CSV+char_widthsの
    軽量ロードのみ。50MB再生成は不要)。結果は app_data/user_corrections.json に蓄積。
  - 実行時(main.py)は load_overlay_entries() で事前生成済みエントリを読み、merge_overlay() で
    GG(replacements_final_list)へ安全に挿入するだけ(ほぼ瞬時)。
  - 安全性: GGは概ね old(置換対象文字列)の長さ降順で、orchestrateは先頭から str.replace する。
    補正語 W を「W より長い old を持つGGエントリの後ろ」に挿入することで、W を部分文字列として
    含む長い語(例: sporti ⊂ sportisto)が先に置換され、壊れない。
"""
import os, json
from typing import List

OVERLAY_FILE = "user_corrections.json"        # app_data 直下に置く
KANJI_CSV = "世界语词根-汉字对应列表_参照2新割当_7791.csv"   # 3アプリ共通(参照2新割当)
RUBY_CSV_CANDIDATES = [                         # 言語別ルビCSV(存在するものを採用)
    "エスペラント語根-日本語訳ルビ対応リスト.csv",
    "世界语词根-中文注释对应列表.csv",
    "에스페란토 어근-한국어 번역 루비 대응 목록.csv",
]
RUBY_FMT = "HTML格式_Ruby文字_大小调整"
KANJI_FMT = "HTML格式_Ruby文字_大小调整_汉字替换"

_ROOT_DICT_CACHE = {}   # (data_dir, csv, fmt) -> {root: <ruby>…</ruby>}


def _ruby_csv(data_dir: str) -> str:
    for c in RUBY_CSV_CANDIDATES:
        if os.path.exists(os.path.join(data_dir, c)):
            return c
    raise FileNotFoundError("ルビ用CSVが app_data に見つかりません")


def _build_root_dict(data_dir: str, csv_name: str, fmt: str):
    """CSV(語根→訳/漢字)から {語根: '<ruby>語根<rt…>訳</rt></ruby>'} の辞書を作る。
       50MB JSONは読まない。プロセス内キャッシュ。"""
    key = (data_dir, csv_name, fmt)
    if key in _ROOT_DICT_CACHE:
        return _ROOT_DICT_CACHE[key]
    import pandas as pd
    from io import StringIO
    from esp_replacement_json_make_module import convert_to_circumflex, output_format
    with open(os.path.join(data_dir, "char_widths.json"), encoding="utf-8") as fp:
        cw = json.load(fp)
    txt = convert_to_circumflex(open(os.path.join(data_dir, csv_name), encoding="utf-8").read())
    df = pd.read_csv(StringIO(txt), encoding="utf-8", usecols=[0, 1])
    rd = {}
    for _, (r, mean) in df.iterrows():
        if pd.notna(r) and pd.notna(mean) and "#" not in str(r) and r != "" and mean != "":
            rd[str(r)] = output_format(str(r), str(mean), fmt, cw)
    _ROOT_DICT_CACHE[key] = rd
    return rd


def _build_new(decomp: str, root_dict) -> str:
    """分解形 'sport/i' → ルビ/漢字HTML new。**ユーザの区切りを尊重**し、各セグメントを
       語根辞書で完全一致検索する(safe_replaceのような再分割をしないので bulgar→bul/ar 等の
       崩れが起きない)。辞書に無いセグメント(文法語尾 i/o/a/e/n 等)は裸のまま。"""
    out = []
    for seg in decomp.split("/"):
        if not seg:
            continue
        out.append(root_dict.get(seg, seg))
    return "".join(out)


def _variants(old: str, new: str):
    """小文字・大文字・先頭大文字の3変種 [(old,new), ...] を返す(重複は除外)。"""
    from esp_replacement_json_make_module import capitalize_ruby_and_rt
    out = [(old, new)]
    up = (old.upper(), new.upper())
    cap = (old.capitalize(), capitalize_ruby_and_rt(new))
    for pair in (up, cap):
        if pair[0] != old and pair not in out:
            out.append(pair)
    return out


def build_correction(decomp: str, data_dir: str) -> dict:
    """分解形(スラッシュ区切り, 例 'sport/i')から、ルビ・漢字両モードの補正エントリを生成。
       戻り値: {word, decomp, ruby:[[old,new],...], kanji:[[old,new],...]}"""
    decomp = decomp.strip().strip("/")
    word = decomp.replace("/", "")
    ruby_dict = _build_root_dict(data_dir, _ruby_csv(data_dir), RUBY_FMT)
    kanji_dict = _build_root_dict(data_dir, KANJI_CSV, KANJI_FMT)
    ruby_new = _build_new(decomp, ruby_dict)
    kanji_new = _build_new(decomp, kanji_dict)
    return {
        "word": word,
        "decomp": decomp,
        "ruby": [list(p) for p in _variants(word, ruby_new)],
        "kanji": [list(p) for p in _variants(word, kanji_new)],
    }


def segment_glosses(decomp: str, data_dir: str):
    """各セグメントに ルビ訳/漢字 が登録済みかを返す。
       戻り値: [(seg, ruby_html or None, kanji_html or None), ...]。
       Noneの語根は訳/漢字が無く、補正しても裸で表示される(文法語尾 i/o/a 等は通常None)。"""
    rd = _build_root_dict(data_dir, _ruby_csv(data_dir), RUBY_FMT)
    kd = _build_root_dict(data_dir, KANJI_CSV, KANJI_FMT)
    out = []
    for seg in decomp.strip().strip("/").split("/"):
        if seg:
            out.append((seg, rd.get(seg), kd.get(seg)))
    return out


def load_corrections(data_dir: str) -> List[dict]:
    path = os.path.join(data_dir, OVERLAY_FILE)
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_corrections(data_dir: str, corrections: List[dict]) -> None:
    path = os.path.join(data_dir, OVERLAY_FILE)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(corrections, f, ensure_ascii=False, indent=1)


def add_correction(data_dir: str, decomp: str) -> dict:
    """補正を生成し、既存の同一語を置き換えて保存。生成した補正dictを返す。"""
    entry = build_correction(decomp, data_dir)
    cors = [c for c in load_corrections(data_dir) if c.get("word") != entry["word"]]
    cors.append(entry)
    save_corrections(data_dir, cors)
    return entry


def remove_correction(data_dir: str, word: str) -> None:
    cors = [c for c in load_corrections(data_dir) if c.get("word") != word]
    save_corrections(data_dir, cors)


def load_overlay_entries(data_dir: str, mode: str) -> List[list]:
    """mode='ruby' or 'kanji'。保存済み補正から [old,new,placeholder] の平坦リストを構築。
       placeholderは毎回ここで一意に再採番する(削除・並べ替えに頑健)。
       placeholderは**純数字**($9NNNNNN$)にする。文字を含む形($OV…)は2文字語根置換系
       (suffix '$ov' 等)と衝突して復元が壊れるため(既存placeholderも全て数字)。"""
    cors = load_corrections(data_dir)
    out = []
    for i, c in enumerate(cors):
        for j, pair in enumerate(c.get(mode, [])):
            if len(pair) >= 2 and pair[0] and pair[1]:
                out.append([pair[0], pair[1], f"${9000000 + i * 10 + j}$"])
    return out


def merge_overlay(GG: List[list], overlay: List[list]) -> List[list]:
    """overlay の各エントリを、それより長い old を持つGGエントリの直後に挿入する。
       これにより 補正語W を部分文字列に含む長い語が先に置換され壊れない。GGが長さ降順で
       並んでいる前提(実データで成立)。GGを変更せず新リストを返す。"""
    if not overlay:
        return GG
    ov = sorted(overlay, key=lambda e: len(e[0].strip()), reverse=True)
    out = []
    i = 0
    n = len(ov)
    for e in GG:
        L = len(e[0].strip())
        while i < n and len(ov[i][0].strip()) > L:
            out.append(ov[i]); i += 1
        out.append(e)
    while i < n:
        out.append(ov[i]); i += 1
    return out
