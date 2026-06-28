# -*- coding: utf-8 -*-
"""
页面「词根分解的手动校正」

当某个世界语单词的词根分解有误时(例: sporti → s/port/i),可在 GUI 上输入正确的分解
(例: sport/i)即可即时修正。无需重新生成 50MB 的替换用 JSON 文件。

机制(轻量 overlay):
  - 此处保存的校正会累积到 app_data/user_corrections.json。
  - main 页面启动时读取该文件,并在注音(ruby)与汉字两种模式下以最高优先级应用。
  - 校正只对「该单词本身」生效(固定形),不会破坏共享子字符串的其他单词(如 sportisto)。
"""
import streamlit as st
import json, re, os

from esp_text_replacement_module import (
    import_placeholders,
    orchestrate_comprehensive_esperanto_text_replacement,
)
from esp_replacement_json_make_module import convert_to_circumflex
import esp_overlay_module as ov

DATA = "./app_data"
RUBY_JSON = DATA + "/置換リスト_ルビ.json"
KANJI_JSON = DATA + "/置換リスト_漢字.json"
RUBY_FMT = "HTML格式_Ruby文字_大小调整"
KANJI_FMT = "HTML格式_Ruby文字_大小调整_汉字替换"

st.set_page_config(page_title="词根分解的手动校正", layout="wide")
st.title("词根分解的手动校正 (在 GUI 上轻松修正)")

with st.expander("使用方法", expanded=True):
    st.markdown(
        """
        1. 输入**单词**并点击「查看当前分解」,可确认应用当前如何分解它。
        2. 若分解有误,请以 `词根/词根/词尾` 的形式(斜杠分隔)输入**正确的分解**。
           - 例: `sporti` 被误分解为 `s/port/i` → 正确为 `sport/i`
           - 去掉斜杠后的字符串必须与原单词一致。
        3. 点击「**保存此校正**」,即可立即反映到注音(ruby)与汉字两种模式
           (无需重新生成替换用 JSON)。
        4. 已保存的校正可随时在下方列表中删除。

        ※ 各词根的译文/汉字使用应用内置词根词典(CSV)中登记的内容。
        词典中没有的词根或语法词尾(i, o, a, e, n …)会以无译文的裸形显示。
        """
    )


@st.cache_data(show_spinner="正在读取替换列表…")
def _load_lists(path):
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    return (
        d.get("局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)", []),
        d.get("二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)", []),
        d.get("全域替换用のリスト(列表)型配列(replacements_final_list)", []),
    )


_PS = import_placeholders(DATA + "/placeholders_skip.txt")
_PL = import_placeholders(DATA + "/placeholders_localcapture.txt")


def _decompose(word, json_path, fmt, mode):
    GL, G2, GG = _load_lists(json_path)
    GG = ov.merge_overlay(GG, ov.load_overlay_entries(DATA, mode))
    h = orchestrate_comprehensive_esperanto_text_replacement(" " + word + " ", _PS, GL, _PL, GG, G2, fmt)
    toks, pos = [], 0
    for mm in re.finditer(r"<ruby>(.*?)<rt[^>]*>.*?</rt></ruby>", h):
        for ch in re.findall(r"[a-zĉĝĥĵŝŭ]+", re.sub(r"<[^>]+>", "", h[pos:mm.start()]), re.I):
            toks.append(ch)
        toks.append(mm.group(1)); pos = mm.end()
    for ch in re.findall(r"[a-zĉĝĥĵŝŭ]+", re.sub(r"<[^>]+>", "", h[pos:]), re.I):
        toks.append(ch)
    return "/".join(toks)


# ============ 1) 确认当前分解 ============
st.header("1. 确认当前分解")
word_in = st.text_input("输入单词 (例: sporti)", key="word_probe").strip()
if st.button("查看当前分解") and word_in:
    w = convert_to_circumflex(word_in).lower()
    try:
        rb = _decompose(w, RUBY_JSON, RUBY_FMT, "ruby")
        kj = _decompose(w, KANJI_JSON, KANJI_FMT, "kanji")
        st.write(f"**注音(ruby)模式的分解**: `{rb}`")
        st.write(f"**汉字模式的分解**: `{kj}`")
        st.session_state["probe_word"] = w
        st.session_state["probe_ruby"] = rb
    except Exception as e:
        st.error(f"确认分解失败: {e}")

# ============ 2) 输入正确分解并保存 ============
st.header("2. 输入正确分解并保存校正")
default_decomp = st.session_state.get("probe_ruby", "")
decomp_in = st.text_input(
    "正确的分解 (斜杠分隔, 例: sport/i)", value=default_decomp, key="decomp_in"
).strip()

if decomp_in:
    norm_decomp = convert_to_circumflex(decomp_in).lower()
    word_of_decomp = norm_decomp.replace("/", "").replace(" ", "")
    try:
        segs = ov.segment_glosses(norm_decomp, DATA)
        rows = []
        for seg, rhtml, khtml in segs:
            rgloss = re.sub(r"<[^>]+>", "", rhtml).replace(seg, "", 1) if rhtml else "—(无译文)"
            kgloss = re.sub(r"<[^>]+>", "", khtml).replace(seg, "", 1) if khtml else "—(无汉字)"
            rows.append({"词根": seg, "译文": rgloss, "汉字": kgloss})
        st.table(rows)
    except Exception as e:
        st.warning(f"预览生成失败: {e}")

    col1, col2 = st.columns(2)
    with col1:
        st.caption(f"去掉斜杠后的单词: `{word_of_decomp}`")
    with col2:
        if st.button("✅ 保存此校正", type="primary"):
            try:
                entry = ov.add_correction(DATA, norm_decomp)
                _load_lists.clear()
                st.success(
                    f"已保存校正: `{entry['word']}` → `{entry['decomp']}`  "
                    "(已即时反映到注音与汉字两种模式,可在 main 页面确认)"
                )
            except Exception as e:
                st.error(f"保存失败: {e}")

# ============ 3) 已保存的校正列表 ============
st.header("3. 已保存的校正列表")
cors = ov.load_corrections(DATA)
if not cors:
    st.info("目前还没有校正。")
else:
    st.caption(f"共有 {len(cors)} 条校正生效中(自动应用于 main 页面)。")
    for c in cors:
        c1, c2, c3 = st.columns([3, 5, 2])
        c1.write(f"**{c.get('word','')}**")
        c2.write(f"→ `{c.get('decomp','')}`")
        if c3.button("删除", key="del_" + c.get("word", "")):
            ov.remove_correction(DATA, c.get("word", ""))
            st.rerun()

    st.download_button(
        "下载校正列表(user_corrections.json)",
        data=json.dumps(cors, ensure_ascii=False, indent=1).encode("utf-8"),
        file_name="user_corrections.json",
        mime="application/json",
    )
