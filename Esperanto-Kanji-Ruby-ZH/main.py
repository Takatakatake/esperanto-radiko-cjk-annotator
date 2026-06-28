# main.py
# --------------------------------------------------------------------
# 这里是 Streamlit 应用程序的主文件 (扩展功能版 202502)
# --------------------------------------------------------------------

import streamlit as st
import re
import io
import json
import pandas as pd  # 如果需要的话使用
from typing import List, Dict, Tuple, Optional
import streamlit.components.v1 as components

import multiprocessing
# 在使用 multiprocessing 时，为避免 PicklingError，必须在 streamlit 中显式指定 "spawn"：
# 如果已经设置过 start method，则会抛出 RuntimeError，这里直接忽略
try:
    multiprocessing.set_start_method("spawn")
except RuntimeError:
    pass

# 从 esp_text_replacement_module.py 中导入必要函数
from esp_text_replacement_module import (
    x_to_circumflex,
    x_to_hat,
    hat_to_circumflex,
    circumflex_to_hat,

    replace_esperanto_chars,
    import_placeholders,

    orchestrate_comprehensive_esperanto_text_replacement,
    parallel_process,
    apply_ruby_html_header_and_footer
)

# --------------------------------------------------------------------
# 通过对函数的结果进行 cache_data，可以加快读取默认的替换用 JSON 文件(可能有 50MB左右)
# (约 1.0 秒 -> 0.5 秒 的加速)
# --------------------------------------------------------------------
@st.cache_data
def load_replacements_lists(json_path: str) -> Tuple[List, List, List]:
    """
    从 JSON 文件中读取以下三种列表并以元组形式返回:
      1) replacements_final_list
      2) replacements_list_for_localized_string
      3) replacements_list_for_2char
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    replacements_final_list = data.get(
        "全域替换用のリスト(列表)型配列(replacements_final_list)", []
    )
    replacements_list_for_localized_string = data.get(
        "局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)", []
    )
    replacements_list_for_2char = data.get(
        "二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)", []
    )

    return (
        replacements_final_list,
        replacements_list_for_localized_string,
        replacements_list_for_2char,
    )

# 设置页面基本信息
st.set_page_config(page_title="（汉字替换）世界语文本转换工具", layout="wide")

# 页面主标题
st.title("将世界语文本转换为汉字形式，或生成带有汉字注释的 HTML (扩展版)")

st.write("---")

# --------------------------------------------------------------------
# 第1步：读取 JSON 文件（替换规则）。
#   用户可选择“使用默认”或“上传自定义 JSON”
# --------------------------------------------------------------------
selected_option = st.radio(
    "请选择替换规则 JSON 文件的读取方式：",
    ("使用默认 JSON", "使用汉字化版(新汉字分配)", "上传 JSON 文件")
)

# 在折叠框中提供一个示例 JSON 文件可下载
with st.expander("【示例 JSON 文件（替换用）】"):
    json_file_path = './app_data/置換リスト_ルビ.json'
    with open(json_file_path, "rb") as file_json:
        btn_json = st.download_button(
            label="下载示例 JSON（替换用）",
            data=file_json,
            file_name="示例_替换用JSON文件.json",
            mime="application/json"
        )

# 准备好这三个列表，以便之后进行替换
replacements_final_list: List[Tuple[str, str, str]] = []
replacements_list_for_localized_string: List[Tuple[str, str, str]] = []
replacements_list_for_2char: List[Tuple[str, str, str]] = []

if selected_option == "使用默认 JSON":
    default_json_path = "./app_data/置換リスト_ルビ.json"
    try:
        replacements_final_list, replacements_list_for_localized_string, replacements_list_for_2char = load_replacements_lists(default_json_path)
        st.success("成功读取默认 JSON 文件。")
    except Exception as e:
        st.error(f"读取默认 JSON 文件时出错: {e}")
        st.stop()
elif selected_option == "使用汉字化版(新汉字分配)":
    kanji_json_path = "./app_data/置換リスト_漢字.json"
    try:
        replacements_final_list, replacements_list_for_localized_string, replacements_list_for_2char = load_replacements_lists(kanji_json_path)
        st.success("成功读取汉字化版 JSON(新汉字分配)。世界语将转换为汉字(注音=词根)。")
    except Exception as e:
        st.error(f"读取汉字化版 JSON 时出错: {e}")
        st.stop()
else:
    uploaded_file = st.file_uploader("请上传 JSON 文件 (合并3个JSON文件).json 格式", type="json")
    if uploaded_file is not None:
        try:
            combined_data = json.load(uploaded_file)
            replacements_final_list = combined_data.get(
                "全域替换用のリスト(列表)型配列(replacements_final_list)", [])
            replacements_list_for_localized_string = combined_data.get(
                "局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)", [])
            replacements_list_for_2char = combined_data.get(
                "二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)", [])
            st.success("已成功读取上传的 JSON 文件。")
        except Exception as e:
            st.error(f"读取上传 JSON 文件时出错: {e}")
            st.stop()
    else:
        st.warning("尚未上传 JSON 文件，无法继续执行。")
        st.stop()

# 1.5) 手动校正(轻量 overlay)以最高优先级应用
#   在「语根分解手动校正」页面保存的校正(app_data/user_corrections.json),
#   无需重新生成替换用JSON即可在运行时反映。
try:
    import esp_overlay_module as _ov
    _ov_mode = "kanji" if selected_option == "使用汉字化版(新汉字分配)" else "ruby"
    _ov_entries = _ov.load_overlay_entries("./app_data", _ov_mode)
    if _ov_entries:
        replacements_final_list = _ov.merge_overlay(replacements_final_list, _ov_entries)
        st.info(f"正在应用 {len(_ov.load_corrections('./app_data'))} 条手动校正(可在「语根分解手动校正」页面编辑)。")
except Exception:
    pass

# --------------------------------------------------------------------
# 2) 读取一些与替换相关的 placeholder(占位符) 文件
# --------------------------------------------------------------------
placeholders_for_skipping_replacements: List[str] = import_placeholders(
    './app_data/placeholders_skip.txt'
)
placeholders_for_localized_replacement: List[str] = import_placeholders(
    './app_data/placeholders_localcapture.txt'
)

st.write("---")

# --------------------------------------------------------------------
# 给用户提供一个并行处理（multiprocessing）的配置选项
# --------------------------------------------------------------------
st.header("高级设置：并行处理选项")
with st.expander("点击此处配置并行处理"):
    st.write("""
        如果文本很大，可以通过多进程并行处理加快转换速度。
        请在此处勾选“使用并行处理”，并指定进程数。
    """)
    use_parallel = st.checkbox("使用并行处理", value=False)
    num_processes = st.number_input("并行进程数量", min_value=2, max_value=4, value=4, step=1)


st.write("---")

# --------------------------------------------------------------------
# 选择“输出形式”（HTML 或者带括号等等）
# --------------------------------------------------------------------
format_type = st.selectbox(
    "请选择输出格式（请与生成替换用JSON时的设定保持一致）：",
    [
        "HTML格式_Ruby文字_大小调整",
        "HTML格式_Ruby文字_大小调整_汉字替换",
        "HTML格式",
        "HTML格式_汉字替换",
        "括弧(号)格式",
        "括弧(号)格式_汉字替换",
        "替换后文字列のみ(仅)保留(简单替换)"
    ]
)

# 准备一个全局字符串 processed_text 来保存处理后的文本
processed_text = ""

# --------------------------------------------------------------------
# 4) 选择如何输入待转换的文本（手动输入或上传文件）
# --------------------------------------------------------------------
st.subheader("输入文本来源")
source_option = st.radio("请选择输入文本的方式：", ("手动输入", "上传文件"))

uploaded_text = ""
if source_option == "上传文件":
    text_file = st.file_uploader("上传文本文件 (UTF-8 编码)", type=["txt", "csv", "md"])
    if text_file is not None:
        uploaded_text = text_file.read().decode("utf-8", errors="replace")
        st.info("文件已读取。")
    else:
        st.warning("尚未上传文本文件，请重新上传或切换为手动输入。")

# --------------------------------------------------------------------
# 使用表单的方式，让用户输入文本并提交
# --------------------------------------------------------------------
# 如果上传了文本，则在生成表单前写入 session_state（作为 key 绑定的初始值）
if uploaded_text:
    st.session_state["text0_value"] = uploaded_text

with st.form(key='profile_form'):
    # 用 key="text0_value" 将 text_area 与 session_state 双向绑定。
    # 旧方式(value=initial_text)会在提交时把控件重置为上一次的值，导致
    # “提交后使用的是上一次输入(滞后一步)”的 bug；key= 方式可让提交时立即反映当前输入。
    text0 = st.text_area(
        "请输入世界语文章",
        height=150,
        key="text0_value"
    )

    st.markdown("""如果您使用“%”包裹文本（例如“%这段文本%”），则这部分内容将**跳过替换**。""")
    st.markdown("""另外，如果您用“@”包裹文本（例如“@这段文本@”），则这部分内容将**只做局部替换**（即使用特定的局部替换列表）。""")

    # 让用户选择“输出字符形式”（上标形式、x 形式、^ 形式）
    letter_type = st.radio('选择世界语字母形式', ('上标形式', 'x 形式', '^形式'))

    # 提交、取消按钮
    submit_btn = st.form_submit_button('提交')
    cancel_btn = st.form_submit_button("取消")

    # 如果用户点击“取消”，则停止执行
    if cancel_btn:
        st.warning("操作已取消。")
        st.stop()

    # 如果点击了“提交”
    if submit_btn:
        # text0 已通过 key="text0_value" 与 session_state 双向绑定，
        # 此处手动赋值会在控件实例化后修改 session_state 而报错，故不再赋值。

        # 根据是否勾选并行处理，调用不同函数
        if use_parallel:
            processed_text = parallel_process(
                text=text0,
                num_processes=num_processes,
                placeholders_for_skipping_replacements=placeholders_for_skipping_replacements,
                replacements_list_for_localized_string=replacements_list_for_localized_string,
                placeholders_for_localized_replacement=placeholders_for_localized_replacement,
                replacements_final_list=replacements_final_list,
                replacements_list_for_2char=replacements_list_for_2char,
                format_type=format_type
            )
        else:
            processed_text = orchestrate_comprehensive_esperanto_text_replacement(
                text=text0,
                placeholders_for_skipping_replacements=placeholders_for_skipping_replacements,
                replacements_list_for_localized_string=replacements_list_for_localized_string,
                placeholders_for_localized_replacement=placeholders_for_localized_replacement,
                replacements_final_list=replacements_final_list,
                replacements_list_for_2char=replacements_list_for_2char,
                format_type=format_type
            )

        # 将上标形式等应用到结果中
        if letter_type == '上标形式':
            processed_text = replace_esperanto_chars(processed_text, x_to_circumflex)
            processed_text = replace_esperanto_chars(processed_text, hat_to_circumflex)
        elif letter_type == '^形式':
            processed_text = replace_esperanto_chars(processed_text, x_to_hat)
            processed_text = replace_esperanto_chars(processed_text, circumflex_to_hat)

        processed_text = apply_ruby_html_header_and_footer(processed_text, format_type)

        # 将结果保存到 session_state（避免重跑时丢失，并使结果可编辑）
        st.session_state["result_html"] = processed_text
        st.session_state["edited_html"] = processed_text          # 编辑用初始值＝生成结果
        st.session_state["result_is_html"] = ("HTML" in format_type)

# --------------------------------------------------------------------
# 表单外：结果预览 / 编辑 / 下载
# --------------------------------------------------------------------
def _reset_edited_html():
    # “放弃编辑”回调（控件实例化后修改 session_state 会报错，故在回调里恢复为生成结果）
    st.session_state["edited_html"] = st.session_state.get("result_html", "")

if st.session_state.get("result_html"):
    st.caption("可在「HTML 源码（可编辑）」标签页直接修改输出，修改会反映到预览与下载（重新转换则恢复生成结果）。")

    # 编辑后的内容（没有则为生成结果）。预览与下载都使用该内容。
    current_html = st.session_state.get("edited_html", st.session_state["result_html"])

    # 文本过长时仅预览省略（编辑与下载始终针对全文）
    MAX_PREVIEW_LINES = 250
    lines = current_html.splitlines()
    if len(lines) > MAX_PREVIEW_LINES:
        preview_text = "\n".join(lines[:247]) + "\n...\n" + "\n".join(lines[-3:])
        st.warning(
            f"文本行数较多（共 {len(lines)} 行），预览仅显示部分内容（编辑与下载为全文）。"
        )
    else:
        preview_text = current_html

    if st.session_state.get("result_is_html"):
        tab1, tab2 = st.tabs(["HTML 预览", "HTML 源码（可编辑）"])
        with tab1:
            components.html(preview_text, height=500, scrolling=True)
        with tab2:
            st.text_area(
                "可直接编辑输出的 HTML（编辑后会反映到预览与下载）",
                key="edited_html",
                height=300
            )
            st.button("放弃编辑，恢复生成结果", on_click=_reset_edited_html)
        download_name = "转换结果.html"
    else:
        tab3_list = st.tabs(["转换结果（可编辑）"])
        with tab3_list[0]:
            st.text_area("可直接编辑输出", key="edited_html", height=300)
            st.button("放弃编辑，恢复生成结果", on_click=_reset_edited_html)
        download_name = "转换结果.txt"

    download_data = current_html.encode('utf-8')
    st.download_button(
        label="下载转换结果（已反映编辑）",
        data=download_data,
        file_name=download_name,
        mime="text/html"
    )

st.write("---")
st.title("Ligilo-oj(URL-oj)")
st.markdown("""
#### Ligilo-oj de la aplikaĵo en aliaj lingvaj versioj (Esperanto, English, 日本語, 中文, 한국어, Русский, español, italiano, français, Deutsch, العربية, हिन्दी, polski, Tiếng Việt, Bahasa Indonesia; entute 14 lingvoj) ⇓  
              
Esperanta versio    
https://esperanto-kanji-converter-and-ruby-annotation-tool-esperanto.streamlit.app/  
English version  
https://esperanto-kanji-converter-and-ruby-annotation-tool-english.streamlit.app/  
日本語版  
https://esperanto-kanji-converter-and-ruby-annotation-tool.streamlit.app/  
**中文版**    
https://esperanto-hanzi-converter-and-ruby-annotation-tool-chinese-dgw.streamlit.app/  
한국어 버전  
https://esperanto-kanji-converter-and-ruby-annotation-tool-korean-yrrx.streamlit.app/    
Русская версия  
https://esperanto-kanji-converter-and-ruby-annotation-tool-russian.streamlit.app/  
Versión en español  
https://esperanto-kanji-converter-and-ruby-annotation-tool-spanish.streamlit.app/  
Versione italiana  
https://esperanto-kanji-converter-and-ruby-annotation-tool-italian.streamlit.app/  
Version française  
https://esperanto-kanji-converter-and-ruby-annotation-tool-french.streamlit.app/  
Deutsche Version  
https://esperanto-kanji-converter-and-ruby-annotation-tool-german.streamlit.app/  
إصدار عربي  
https://esperanto-kanji-converter-and-ruby-annotation-tool-arabic.streamlit.app/  
हिन्दी संस्करण  
https://esperanto-kanji-converter-and-ruby-annotation-tool-hindi.streamlit.app/  
Polska wersja  
https://esperanto-kanji-converter-and-ruby-annotation-tool-polish.streamlit.app/  
Phiên bản tiếng Việt  
https://esperanto-kanji-converter-and-ruby-annotation-tool-vietnamese.streamlit.app/  
Versi Bahasa Indonesia  
https://esperanto-kanji-converter-and-ruby-annotation-tool-indonesian.streamlit.app/  

#### Uzadaj instrukcioj de la aplikaĵo (README.md en la GitHub-deponejo) ⇓    
  
Esperanta versio  
https://github.com/TakafumiYamauchi/Esperanto-Kanji-Converter-and-Ruby-Annotation-Tool-Esperanto  
English version  
https://github.com/TakafumiYamauchi/Esperanto-Kanji-Converter-and-Ruby-Annotation-Tool-English  
日本語版  
https://github.com/Takatakatake/Esperanto-Kanji-Converter-and-Ruby-Annotation-Tool-  
**中文版**    
https://github.com/Takatakatake/Esperanto-Hanzi-Converter-and-Ruby-Annotation-Tool-Chinese  
한국어 버전  
https://github.com/Takatakatake/Esperanto-Kanji-Converter-and-Ruby-Annotation-Tool-Korean  
Русская версия  
https://github.com/TakafumiYamauchi/Esperanto-Kanji-Converter-and-Ruby-Annotation-Tool-Russian  
Versión en español  
https://github.com/TakafumiYamauchi/Esperanto-Kanji-Converter-and-Ruby-Annotation-Tool-Spanish  
Versione italiana  
https://github.com/TakafumiYamauchi/Esperanto-Kanji-Converter-and-Ruby-Annotation-Tool-Italian  
Version française  
https://github.com/TakafumiYamauchi/Esperanto-Kanji-Converter-and-Ruby-Annotation-Tool-French  
Deutsche Version  
https://github.com/TakafumiYamauchi/Esperanto-Kanji-Converter-and-Ruby-Annotation-Tool-German  
إصدار عربي  
https://github.com/TakafumiYamauchi/Esperanto-Kanji-Converter-and-Ruby-Annotation-Tool-Arabic  
हिन्दी संस्करण  
https://github.com/TakafumiYamauchi/Esperanto-Kanji-Converter-and-Ruby-Annotation-Tool-Hindi  
Polska wersja  
https://github.com/TakafumiYamauchi/Esperanto-Kanji-Converter-and-Ruby-Annotation-Tool-Polish  
Phiên bản tiếng Việt  
https://github.com/TakafumiYamauchi/Esperanto-Kanji-Converter-and-Ruby-Annotation-Tool-Vietnamese  
Versi Bahasa Indonesia  
https://github.com/TakafumiYamauchi/Esperanto-Kanji-Converter-and-Ruby-Annotation-Tool-Indonesian  
""")
