##  main.py(1つ目)
# main.py (メインの Streamlit アプリ/機能拡充版202502)

import streamlit as st
import re
import io
import json
import pandas as pd  # 必要なら使う
from typing import List, Dict, Tuple, Optional
import streamlit.components.v1 as components
import multiprocessing

#=================================================================
# Streamlit で multiprocessing を使う際、PicklingError 回避のため
# 明示的に 'spawn' モードを設定する必要がある。
#=================================================================
try:
    multiprocessing.set_start_method("spawn")
except RuntimeError:
    pass  # すでに start method が設定済みの場合はここで無視する

#=================================================================
# エスペラント文の(漢字)置換・ルビ振りなどを行う独自モジュールから
# 関数をインポートする。
# esp_text_replacement_module.py内に定義されているツールをまとめて呼び出す
#=================================================================
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

#=================================================================
# Streamlit の @st.cache_data デコレータを使い、読み込み結果をキャッシュして
# JSONファイルのロード高速化を図る。大きなJSON(50MB程度)を都度読むと遅いので、
# ここで呼び出す関数をキャッシュする作り。
#=================================================================
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

#=================================================================
# Streamlit ページの見た目設定
# page_title: ブラウザタブに表示されるタイトル
# layout="wide" で横幅を広く使えるUIにする
#=================================================================
st.set_page_config(page_title="에스페란토 문서의 문자열(한자) 치환 도구", layout="wide")

# タイトル部分
st.title("에스페란토 문장을 한자로 치환하거나, HTML 형식의 번역 루비를 적용하기 (확장판)")
st.write("---")

#=================================================================
# 1) JSONファイル (置換ルール) をロード
#   (デフォルトを使うか、ユーザーがアップロードするかの選択)
#=================================================================
selected_option = st.radio(
    "JSON 파일을 어떻게 하시겠습니까? (치환용 JSON 파일 불러오기)",
    ("기본값 사용", "업로드하기")
)

# Streamlit の折りたたみ (expander) でサンプルJSONのダウンロードを案内
with st.expander("샘플 JSON(치환용 JSON 파일)"):
    # サンプルファイルのパス
    json_file_path = './Appの运行に使用する各类文件/最终的な替换用リスト(列表)(合并3个JSON文件).json'
    # JSONファイルを読み込んでダウンロードボタンを生成
    with open(json_file_path, "rb") as file_json:
        btn_json = st.download_button(
            label="샘플 JSON(치환용 JSON 파일) 다운로드",
            data=file_json,
            file_name="치환용JSON파일.json",
            mime="application/json"
        )

#=================================================================
# 置換ルールとして使うリスト3種を初期化しておく。
# (JSONファイル読み込み後に代入される)
#=================================================================
replacements_final_list: List[Tuple[str, str, str]] = []
replacements_list_for_localized_string: List[Tuple[str, str, str]] = []
replacements_list_for_2char: List[Tuple[str, str, str]] = []

# JSONファイルの読み込み方を分岐
if selected_option == "기본값 사용":
    default_json_path = "./Appの运行に使用する各类文件/最终的な替换用リスト(列表)(合并3个JSON文件).json"
    try:
        (replacements_final_list,
         replacements_list_for_localized_string,
         replacements_list_for_2char) = load_replacements_lists(default_json_path)
        st.success("기본 JSON을 성공적으로 불러왔습니다.")
    except Exception as e:
        st.error(f"JSON 파일 불러오기에 실패했습니다: {e}")
        st.stop()
else:
    uploaded_file = st.file_uploader("JSON 파일을 업로드하십시오 (합병된 3개 JSON 파일).json 형식", type="json")
    if uploaded_file is not None:
        try:
            combined_data = json.load(uploaded_file)
            replacements_final_list = combined_data.get(
                "全域替换用のリスト(列表)型配列(replacements_final_list)", [])
            replacements_list_for_localized_string = combined_data.get(
                "局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)", [])
            replacements_list_for_2char = combined_data.get(
                "二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)", [])
            st.success("업로드한 JSON을 성공적으로 불러왔습니다.")
        except Exception as e:
            st.error(f"업로드한 JSON 파일 불러오기에 실패했습니다: {e}")
            st.stop()
    else:
        st.warning("JSON 파일이 업로드되지 않았습니다. 처리를 중단합니다.")
        st.stop()

#=================================================================
# 2) placeholders (占位符) の読み込み
#    %...% や @...@ で囲った文字列を守るために使用する文字列群を読み込む
#=================================================================
placeholders_for_skipping_replacements: List[str] = import_placeholders(
    './Appの运行に使用する各类文件/占位符(placeholders)_%1854%-%4934%_文字列替换skip用.txt'
)
placeholders_for_localized_replacement: List[str] = import_placeholders(
    './Appの运行に使用する各类文件/占位符(placeholders)_@5134@-@9728@_局部文字列替换结果捕捉用.txt'
)

st.write("---")

#=================================================================
# 設定パラメータ (UI) - 高度な設定
# 並列処理 (multiprocessing) を利用できるかどうかのスイッチと、
# 同時プロセス数の選択
#=================================================================
st.header("고급 설정 (병렬 처리)")
with st.expander("병렬 처리 설정을 열기"):
    st.write("""
    여기에서는 문자열(한자) 치환 시에 사용할 병렬 처리 프로세스 개수를 결정합니다. 
    """)
    use_parallel = st.checkbox("병렬 처리를 사용하기", value=False)
    num_processes = st.number_input("동시 프로세스 수", min_value=2, max_value=4, value=4, step=1)

st.write("---")

#=================================================================
# 例: 出力形式の選択
# (HTMLルビ形式・括弧形式・文字列のみ など)
#=================================================================

# ユーザー向け選択肢（キー側を韓国語に変更 / 値側は機能維持のためそのまま）
options = {
    'HTML형식_Ruby문자_크기조정': 'HTML格式_Ruby文字_大小调整',
    'HTML형식_Ruby문자_크기조정_한자치환': 'HTML格式_Ruby文字_大小调整_汉字替换',
    'HTML형식': 'HTML格式',
    'HTML형식_한자치환': 'HTML格式_汉字替换',
    '괄호 형식': '括弧(号)格式',
    '괄호 형식_한자치환': '括弧(号)格式_汉字替换',
    '치환 후 문자열만(간단 치환) 유지': '替换后文字列のみ(仅)保留(简单替换)'
}

# 사용자에게 보여줄 옵션 목록 (라벨)은 위의 dict 키들을 사용
display_options = list(options.keys())
selected_display = st.selectbox("출력 형식을 선택하십시오 (치환용 JSON 파일을 작성했을 때와 동일한 형식을 선택):", display_options)
format_type = options[selected_display]


# フォーム外で、変数 processed_text を初期化しておく
processed_text = ""

#=================================================================
# 4) 入力テキストのソースを選択 (手動入力 or ファイルアップロード)
#=================================================================
st.subheader("입력 텍스트의 소스")
source_option = st.radio("입력 텍스트를 어떻게 하시겠습니까?", ("직접 입력", "파일 업로드"))
uploaded_text = ""

# ファイルアップロードが選択された場合
if source_option == "파일 업로드":
    text_file = st.file_uploader("텍스트 파일을 업로드하십시오 (UTF-8)", type=["txt", "csv", "md"])
    if text_file is not None:
        uploaded_text = text_file.read().decode("utf-8", errors="replace")
        st.info("파일을 불러왔습니다.")
    else:
        st.warning("텍스트 파일이 업로드되지 않았습니다. 직접 입력으로 전환하거나 파일을 업로드해 주십시오.")

#=================================================================
# フォーム: 実行ボタン(送信/キャンセル)を配置
#  - テキストエリアにエスペラント文を入力してもらう
#=================================================================
with st.form(key='profile_form'):

    if uploaded_text:
        initial_text = uploaded_text
    else:
        initial_text = st.session_state.get("text0_value", "")

    text0 = st.text_area(
        "에스페란토 문장을 입력해 주십시오",
        height=150,
        value=initial_text
    )

    st.markdown("""「%」로 앞뒤를 감싸는(「%<50자 이내의 문자열>%」 형식) 경우,  
    「%」로 감싸진 부분은 문자열(한자) 치환 대상에서 제외되어 원문 그대로 유지됩니다.""")

    st.markdown("""또한, 「@」로 앞뒤를 감싸는(「@<18자 이내의 문자열>@」 형식) 경우,  
    「@」로 감싸진 부분은 국소적으로 문자열(한자) 치환 대상이 됩니다.""")

    # 출力文字形式 (エスペラント特有文字の表記形式)
    letter_type = st.radio('출력 문자 형식', ('상단 첨자', 'x 形式', '^ 형식'))

    submit_btn = st.form_submit_button('전송')
    cancel_btn = st.form_submit_button("취소")

    if cancel_btn:
        st.warning("취소되었습니다.")
        st.stop()

    if submit_btn:
        st.session_state["text0_value"] = text0

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

        # letter_type에 따라 최종 에스페란토 문자 표기를 변환
        if letter_type == '상단 첨자':
            processed_text = replace_esperanto_chars(processed_text, x_to_circumflex)
            processed_text = replace_esperanto_chars(processed_text, hat_to_circumflex)
        elif letter_type == '^ 형식':
            processed_text = replace_esperanto_chars(processed_text, x_to_hat)
            processed_text = replace_esperanto_chars(processed_text, circumflex_to_hat)

        processed_text = apply_ruby_html_header_and_footer(processed_text, format_type)

#=================================================================
# =========================================
# フォーム外の処理: 結果表示・ダウンロード
# =========================================
#=================================================================
if processed_text:
    MAX_PREVIEW_LINES = 250
    lines = processed_text.splitlines()

    if len(lines) > MAX_PREVIEW_LINES:
        first_part = lines[:247]
        last_part = lines[-3:]
        preview_text = "\n".join(first_part) + "\n...\n" + "\n".join(last_part)
        st.warning(
            f"텍스트가 길기 때문에(총 {len(lines)}줄), 본문 전체 프리뷰를 일부만 표시합니다. 마지막 3줄도 함께 표시합니다."
        )
    else:
        preview_text = processed_text

    if "HTML" in format_type:
        tab1, tab2 = st.tabs(["HTML 미리보기", "치환 결과(HTML 소스 코드)"])
        with tab1:
            components.html(preview_text, height=500, scrolling=True)
        with tab2:
            st.text_area("", preview_text, height=300)
    else:
        tab3_list = st.tabs(["치환 결과 텍스트"])
        with tab3_list[0]:
            st.text_area("", preview_text, height=300)

    download_data = processed_text.encode('utf-8')
    st.download_button(
        label="치환 결과 다운로드",
        data=download_data,
        file_name="치환결과.html",
        mime="text/html"
    )


#=================================================================
# ページ下部に、アプリのGitHubリポジトリのリンクを表示
#=================================================================

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
中文版  
https://esperanto-hanzi-converter-and-ruby-annotation-tool-chinese-dgw.streamlit.app/  
**한국어 버전**    
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
中文版  
https://github.com/Takatakatake/Esperanto-Hanzi-Converter-and-Ruby-Annotation-Tool-Chinese  
**한국어 버전**    
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

