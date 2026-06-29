# メインの Streamlit アプリ (機能拡充版202502)

import streamlit as st
import re
import io
import json
import pandas as pd  # 必要なら使う
from typing import List, Dict, Tuple, Optional
import streamlit.components.v1 as components

import multiprocessing
# multiprocessing時のPicklingError回避のため 'spawn' を明示: streamlitでは必ず必要。
try:
    multiprocessing.set_start_method("spawn")
except RuntimeError:
    pass  # すでに start method が設定済みの場合はここで無視する


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

## 関数のキャッシュを活用することで、デフォルトの置換用JSONファイル(50MB程度)の読み込みを早くする。(約1.0秒→0.5秒 の短縮)
@st.cache_data
def load_replacements_lists(json_path: str) -> Tuple[List, List, List]:
    """
    JSONファイルをロードし、以下の3つのリストをタプルとして返す:
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

# ページ設定
st.set_page_config(page_title="Esperanto文の文字列(漢字)置換ツール", layout="wide")

st.title("エスペラント文を漢字置換したり、HTML形式の訳ルビを振ったりする (拡張版)")

st.write("---")

# 1) JSONファイル (置換ルール) をロードする (デフォルト or アップロード)
selected_option = st.radio(
    "JSONファイルをどうしますか？ (置換用JSONファイルの読み込み)",
    ("デフォルトを使用する", "漢字化版(新漢字割り当て)を使用する", "アップロードする")
)



with st.expander("**サンプルJSON(置換用JSONファイル)**"):
    # サンプルファイルのパス
    json_file_path = './app_data/置換リスト_ルビ.json'
    # JSONファイルを読み込んでダウンロードボタンを生成
    with open(json_file_path, "rb") as file_json:
        btn_json = st.download_button(
            label="サンプルJSON(置換用JSONファイル)ダウンロード",
            data=file_json,
            file_name="置換用JSONファイル.json",
            mime="application/json"
        )

replacements_final_list: List[Tuple[str, str, str]] = []
replacements_list_for_localized_string: List[Tuple[str, str, str]] = []
replacements_list_for_2char: List[Tuple[str, str, str]] = []

if selected_option == "デフォルトを使用する":
    default_json_path = "./app_data/置換リスト_ルビ.json"
    try:
        replacements_final_list, replacements_list_for_localized_string, replacements_list_for_2char = load_replacements_lists(default_json_path)
        st.success("デフォルトJSONの読み込みに成功しました。")
    except Exception as e:
        st.error(f"JSONファイルの読み込みに失敗: {e}")
        st.stop()
elif selected_option == "漢字化版(新漢字割り当て)を使用する":
    kanji_json_path = "./app_data/置換リスト_漢字.json"
    try:
        replacements_final_list, replacements_list_for_localized_string, replacements_list_for_2char = load_replacements_lists(kanji_json_path)
        st.success("漢字化版JSON(新漢字割り当て)の読み込みに成功しました。エスペラント文が漢字(ルビ=語根)に変換されます。")
    except Exception as e:
        st.error(f"漢字化版JSONの読み込みに失敗: {e}")
        st.stop()
else:
    uploaded_file = st.file_uploader("JSONファイルをアップロード (合并3个JSON文件).json 形式)", type="json")
    if uploaded_file is not None:
        try:
            combined_data = json.load(uploaded_file)
            replacements_final_list = combined_data.get(
                "全域替换用のリスト(列表)型配列(replacements_final_list)", [])
            replacements_list_for_localized_string = combined_data.get(
                "局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)", [])
            replacements_list_for_2char = combined_data.get(
                "二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)", [])
            st.success("アップロードしたJSONの読み込みに成功しました。")
        except Exception as e:
            st.error(f"アップロードJSONファイルの読み込みに失敗: {e}")
            st.stop()
    else:
        st.warning("JSONファイルがアップロードされていません。処理を停止します。")
        st.stop()

# 1.5) 手動補正(軽量オーバーレイ)を最優先で適用
#   「語根分解の手動補正」ページで保存した補正(app_data/user_corrections.json)を、
#   置換用JSONを再生成せずに実行時へ反映する。補正語より長い語を先に置換するよう安全挿入。
try:
    import esp_overlay_module as _ov
    _ov_mode = "kanji" if selected_option == "漢字化版(新漢字割り当て)を使用する" else "ruby"
    _ov_entries = _ov.load_overlay_entries("./app_data", _ov_mode)
    if _ov_entries:
        replacements_final_list = _ov.merge_overlay(replacements_final_list, _ov_entries)
        st.info(f"手動補正 {len(_ov.load_corrections('./app_data'))} 件を適用中(「語根分解の手動補正」ページで編集できます)。")
except Exception:
    pass  # オーバーレイは任意機能。失敗しても通常の置換は継続する。

# 2) placeholders (占位符) の読み込み
placeholders_for_skipping_replacements: List[str] = import_placeholders(
    './app_data/placeholders_skip.txt'
)
placeholders_for_localized_replacement: List[str] = import_placeholders(
    './app_data/placeholders_localcapture.txt'
)

st.write("---")


# 設定パラメータ (UI) - 高度な設定
st.header("高度な設定 (並列処理)")
with st.expander("並列処理についての設定を開く"):
    st.write("""
            ここでは、文字列(漢字)置換時に使用する並列処理のプロセス数を決めます。  
            """)
    use_parallel = st.checkbox("並列処理を使う", value=False)
    num_processes = st.number_input("同時プロセス数", min_value=2, max_value=4, value=4, step=1)


st.write("---")

# 例: 出力形式など。必要に応じて追加カスタマイズ
format_type = st.selectbox(
    "出力形式を選択(置換用JSONファイルを作成したときと同じ形式を選択):",
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

# フォーム外で、変数 processed_text を初期化
processed_text = ""

# 4) 入力テキストのソースを選択 (アップロード or テキストエリア)
st.subheader("入力テキストのソース")
source_option = st.radio("入力テキストをどうしますか？", ("手動入力", "ファイルアップロード"))

uploaded_text = ""
if source_option == "ファイルアップロード":
    text_file = st.file_uploader("テキストファイルをアップロード (UTF-8)", type=["txt", "csv", "md"])
    if text_file is not None:
        uploaded_text = text_file.read().decode("utf-8", errors="replace")
        st.info("ファイルを読み込みました。")
    else:
        st.warning("テキストファイルがアップロードされていません。手動入力に切り替えるかファイルをアップロードしてください。")


# アップロードがあれば、フォーム生成前に session_state へ反映(key バインドの初期値として)
if uploaded_text:
    st.session_state["text0_value"] = uploaded_text

with st.form(key='profile_form'):
    # text_area を key="text0_value" で session_state と双方向バインドする。
    # 旧方式(value=initial_text で session_state を初期値にする)は、送信時にウィジェットが
    # value= で前回値に戻され「1つ前の入力で変換される(1ステップ遅延)」バグの原因だった。
    # key= 方式では送信時に現在の入力がそのまま反映される。
    text0 = st.text_area(
        "エスペラントの文章を入力してください",
        height=150,
        key="text0_value"
    )

    st.markdown("""「%」で前後を囲む(「%<50文字以内の文字列>%」形式)と、
    「%」で囲まれた部分は文字列(漢字)置換せず、元のまま保持することができます。""")
    st.markdown("""また、「@」で前後を囲む(「@<18文字以内の文字列>@」形式)と、
    「@」で囲まれた部分を局所的に文字列(漢字)置換します。""")

    letter_type = st.radio('出力文字形式', ('上付き文字', 'x 形式', '^形式'))

    submit_btn = st.form_submit_button('送信')
    cancel_btn = st.form_submit_button("キャンセル")

    # キャンセルが押されたら、ここで処理を打ち切る
    if cancel_btn:
        st.warning("キャンセルされました。")
        st.stop()  # ここで処理が終了するので、下の行は実行されない

    if submit_btn:
        # text0 は key="text0_value" で session_state と双方向バインド済み。
        # ここで手動代入するとウィジェット生成後の session_state 変更となりエラーになるため行わない。

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

        # 1パス目に「先頭1字孤立」過分解(子音1字の遊離: fero->f/er/o 等)があれば、
        # 自動補正を最優先でmergeして2パス目を描画(機構レベルで欠陥クラスを一掃)。
        # 孤立が無ければ何もしない(通常テキストは大半がこれ)。
        try:
            import esp_overlay_module as _ovx
            _afmode = "kanji" if selected_option == "漢字化版(新漢字割り当て)を使用する" else "ruby"
            _auto = _ovx.auto_overlay_entries(processed_text, "./app_data", _afmode)
            if _auto:
                _GGx = _ovx.merge_overlay(replacements_final_list, _auto)
                if use_parallel:
                    processed_text = parallel_process(
                        text=text0, num_processes=num_processes,
                        placeholders_for_skipping_replacements=placeholders_for_skipping_replacements,
                        replacements_list_for_localized_string=replacements_list_for_localized_string,
                        placeholders_for_localized_replacement=placeholders_for_localized_replacement,
                        replacements_final_list=_GGx,
                        replacements_list_for_2char=replacements_list_for_2char,
                        format_type=format_type)
                else:
                    processed_text = orchestrate_comprehensive_esperanto_text_replacement(
                        text=text0,
                        placeholders_for_skipping_replacements=placeholders_for_skipping_replacements,
                        replacements_list_for_localized_string=replacements_list_for_localized_string,
                        placeholders_for_localized_replacement=placeholders_for_localized_replacement,
                        replacements_final_list=_GGx,
                        replacements_list_for_2char=replacements_list_for_2char,
                        format_type=format_type)
        except Exception:
            pass  # 自動補正は任意。失敗しても1パス目の結果をそのまま使う。

        # letter_typeに応じて再変換
        if letter_type == '上付き文字':
            processed_text = replace_esperanto_chars(processed_text, x_to_circumflex)
            processed_text = replace_esperanto_chars(processed_text, hat_to_circumflex)
        elif letter_type == '^形式':
            processed_text = replace_esperanto_chars(processed_text, x_to_hat)
            processed_text = replace_esperanto_chars(processed_text, circumflex_to_hat)

        processed_text = apply_ruby_html_header_and_footer(processed_text, format_type)

        # 結果を session_state に保存（再実行で消えない＋結果を編集可能にするため）
        st.session_state["result_html"] = processed_text
        st.session_state["edited_html"] = processed_text          # 編集用の初期値＝生成結果
        st.session_state["result_is_html"] = ("HTML" in format_type)

# =========================================
# フォーム外の処理: 結果のプレビュー・編集・ダウンロード
# =========================================
def _reset_edited_html():
    # 「編集を破棄」用コールバック（ウィジェット生成後に session_state を変更すると
    #  エラーになるため、コールバック内で生成結果へ戻す）
    st.session_state["edited_html"] = st.session_state.get("result_html", "")

if st.session_state.get("result_html"):
    st.caption("「HTMLソース（編集可）」タブで出力を直接修正できます。"
               "修正はプレビューとダウンロードに反映されます（再変換すると生成結果に戻ります）。")

    # 編集後の内容（なければ生成結果）。プレビュー・ダウンロードとも、この内容を使う。
    current_html = st.session_state.get("edited_html", st.session_state["result_html"])

    # 長文時はプレビューのみ一部省略（編集とダウンロードは常に全文が対象）
    MAX_PREVIEW_LINES = 250
    lines = current_html.splitlines()
    if len(lines) > MAX_PREVIEW_LINES:
        preview_text = "\n".join(lines[:247]) + "\n...\n" + "\n".join(lines[-3:])
        st.warning(
            f"テキストが長いため（総行数 {len(lines)} 行）、プレビューは一部省略しています"
            "（編集・ダウンロードは全文が対象です）。"
        )
    else:
        preview_text = current_html

    if st.session_state.get("result_is_html"):
        tab1, tab2 = st.tabs(["HTMLプレビュー", "HTMLソース（編集可）"])
        with tab1:
            components.html(preview_text, height=500, scrolling=True)
        with tab2:
            st.text_area(
                "出力HTMLを直接編集できます（編集後、プレビューとダウンロードに反映されます）",
                key="edited_html",
                height=300
            )
            st.button("編集を破棄して生成結果に戻す", on_click=_reset_edited_html)
        download_name = "置換結果.html"
    else:
        tab3_list = st.tabs(["置換結果テキスト（編集可）"])
        with tab3_list[0]:
            st.text_area("出力を直接編集できます", key="edited_html", height=300)
            st.button("編集を破棄して生成結果に戻す", on_click=_reset_edited_html)
        download_name = "置換結果.txt"

    download_data = current_html.encode('utf-8')
    st.download_button(
        label="置換結果のダウンロード（編集を反映）",
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
**日本語版**    
https://esperanto-kanji-converter-and-ruby-annotation-tool.streamlit.app/  
中文版  
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
**日本語版**    
https://github.com/Takatakatake/Esperanto-Kanji-Converter-and-Ruby-Annotation-Tool-  
中文版  
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
