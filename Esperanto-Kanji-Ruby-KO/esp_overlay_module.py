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
import os, json, re
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


# ============================================================================
# 先頭1字孤立(first-char isolation) の自動補正
#   placeholder貪欲置換が語頭1文字を遊離させる過分解(例 fero->f/er/o, sporti->s/port/i)を、
#   orchestrate出力から検出し、語頭から再分解して機構レベルで一掃する。
#   - 検出: 裸の1文字が <ruby> の直前に残る = エスペラントに語頭1字の形態素は存在しない
#           (接頭辞も語根も最短2字、1字は末尾の文法語尾のみ)ので、100%確実な誤りシグナル。
#   - 再分解: 大文字始まり(固有名詞)=幹を丸ごと / 小文字で「≤3個・各≥3字の訳付き語根」に
#           綺麗に割れる=その分解 / それ以外=幹を丸ごと(誤った訳を付けない)。
#   - 適用: 自動算出した分解を build_correction → merge_overlay に流す(手動補正と同一機構)。
# ============================================================================

_SEG_END = ["ojn", "oj", "on", "o", "ajn", "aj", "an", "a", "en", "e", "jn", "j", "n",
            "as", "is", "os", "us", "u", "i"]
_SEG_ENDSET = set(_SEG_END)
_LATIN_CLASS = "a-zĉĝĥĵŝŭA-ZĈĜĤĴŜŬ"
_RUBY_BLOCK = re.compile(r"<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>", re.S)
_LATIN_RE = re.compile(r"[" + _LATIN_CLASS + "]")


def _glossed_rootset(data_dir):
    """訳/漢字が付いた語根(=表示可能)の集合。ルビCSV基準(言語非依存の語根集合)。"""
    rd = _build_root_dict(data_dir, _ruby_csv(data_dir), RUBY_FMT)
    return frozenset(r for r in rd if len(r) >= 2)


def _clean_split(word, rootset):
    """word を『訳付き語根(>=2字) + 文法語尾』で全被覆する最少片の分解。先頭は語根。
       採用条件: 語根片が 1〜3 個 かつ 各語根片が >=3字(偶然の短語根合体=固有名詞の粉砕を排除)。
       条件を満たさなければ None。"""
    n = len(word)
    ends = sorted(_SEG_ENDSET, key=len, reverse=True)
    memo = {}

    def soln(i):
        if i == n:
            return []
        if i in memo:
            return memo[i]
        cands = []
        for L in range(min(18, n - i), 1, -1):
            if word[i:i + L] in rootset:
                r = soln(i + L)
                if r is not None:
                    cands.append([word[i:i + L]] + r)
        if i > 0:
            for e in ends:
                if word.startswith(e, i):
                    r = soln(i + len(e))
                    if r is not None:
                        cands.append([e] + r)
        memo[i] = min(cands, key=len) if cands else None
        return memo[i]

    s = soln(0)
    if not s or s[0] in _SEG_ENDSET or len(s[0]) < 2:
        return None
    roots = [p for p in s if p not in _SEG_ENDSET]
    if 1 <= len(roots) <= 3 and all(len(r) >= 3 for r in roots):
        return "/".join(s)
    return None


def autofix_decomp(word, data_dir):
    """先頭1字孤立した word の『正しい分解』を返す。改善できなければ None。
       戻り値はスラッシュ区切り(例 'fer/o', 'kor/lig', 'kvedlinburg/o')。"""
    low = word.lower()
    if len(low) < 3 or not re.fullmatch(r"[a-zĉĝĥĵŝŭ]+", low):
        return None
    if not word[:1].isupper():  # 小文字: 訳付き語根で綺麗に割れるなら分解
        cs = _clean_split(low, _glossed_rootset(data_dir))
        if cs and cs.replace("/", "") == low:
            return cs
    for e in ("jn", "j", "n"):  # フォールバック(固有名詞・外来語): 屈折語尾を剥がし幹を丸ごと
        if low.endswith(e) and len(low) - len(e) >= 3:
            return low[:-len(e)] + "/" + "/".join(list(e))
    return low  # 幹を丸ごと(剥がせる語尾なし)


def _latin_of(base, rt):
    """ruby/漢字 どちらのモードでも、その語根のラテン綴りを返す(baseがラテンならbase, 否ならrt)。"""
    return base if _LATIN_RE.search(base) else rt


def find_stranded_words(html):
    """orchestrate出力から『裸1文字 + <ruby>』で始まる語を検出し、その表層(ラテン綴り)集合を返す。
       ruby/漢字 両モード対応(漢字モードでは語根が<rt>側にあるため _latin_of で吸収)。"""
    def repl(m):
        return "\x02" + _latin_of(m.group(1), m.group(2)) + "\x03"
    s = _RUBY_BLOCK.sub(repl, html)
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("&nbsp;", " ")
    out = set()
    for run in re.findall(r"(?:[" + _LATIN_CLASS + r"]|\x02[^\x03]*\x03)+", s):
        pieces = re.findall(r"\x02([^\x03]*)\x03|([" + _LATIN_CLASS + r"]+)", run)
        seq = [("R", a) if a != "" else ("B", b) for a, b in pieces if (a != "" or b)]
        # 真の欠陥 = 先頭が「子音1文字」の遊離のみ。先頭が母音(a/e/i/o/u)1字は
        # 正当な文法語尾(名詞-o/形容詞-a/副詞-e等)で、前語尾が連結したトークンに頻出する
        # (例 o/pren, a/opini/e)ため除外しないと正しい分解を壊して回帰する。
        if len(seq) >= 2 and seq[0][0] == "B" and len(seq[0][1]) == 1 \
                and seq[0][1].lower() not in "aeiou" and seq[1][0] == "R":
            surface = "".join(p[1] for p in seq)
            if 3 <= len(surface) <= 30:
                out.add(surface)
    return out


def auto_overlay_entries(html_pass1, data_dir, mode):
    """pass1のhtmlから孤立語を検出 → 各語の正しい分解を自動算出 → build_correctionでmode別
       エントリ化。返り値は merge_overlay 用 [old, new, placeholder] のリスト($911NNNN$帯)。"""
    entries = []
    for w in sorted(find_stranded_words(html_pass1)):
        try:
            d = autofix_decomp(w, data_dir)
            if not d or d.replace("/", "").lower() != w.lower():
                continue
            corr = build_correction(d, data_dir)
            for pair in corr.get(mode, []):
                if len(pair) >= 2 and pair[0] and pair[1]:
                    entries.append(pair)
        except Exception:
            continue
    return [[old, new, f"${9110000 + i}$"] for i, (old, new) in enumerate(entries)]


def autofix_render(text, ps, GL, pl, GG, G2, fmt, data_dir, mode, orchestrate_fn):
    """1パス目を描画し、先頭1字孤立語があれば自動補正をmerge_overlayして2パス目を描画して返す。
       孤立語が無ければ1パスのみ(通常テキストは大半がこれ=高速)。"""
    html = orchestrate_fn(text, ps, GL, pl, GG, G2, fmt)
    if "<ruby>" not in html:
        return html
    auto = auto_overlay_entries(html, data_dir, mode)
    if not auto:
        return html
    return orchestrate_fn(text, ps, GL, pl, merge_overlay(GG, auto), G2, fmt)
