# Esperanto-Kanji-Converter-and-Ruby-Annotation-Tool-Korean

아래 설명서는 **에스페란토 문장을 (한자) 치환하기 위한 한국어 버전 Streamlit 앱**의 전체 구조와 동작 방식을,  
**이미 GUI 측 사용법**은 어느 정도 숙지하고 있으나 **코드와 내부 로직을 좀 더 깊이 이해하고 싶은**  
**중급 프로그래머**를 대상으로 **깊이 있고 체계적인 관점**에서 서술한 문서입니다.

> **대상 독자**:  
> - 이미 `main.py` 실행을 통해 GUI 사용 경험이 있고,  
> - Streamlit, Python, JSON, 병렬 처리(multiprocessing) 등 기본을 아는 **중급 개발자**.  
> - 에스페란토 한자화/번역 방식, CSV-JSON 합성 로직을 좀 더 깊이 이해하고 싶음.

---

# 전체 구조 개요

이 앱은 크게 **4개의 Python 파일**로 구성됩니다:

1. **`main.py`**  
   - 스트리밍 클라우드(또는 로컬)에서 실행되는 **메인 Streamlit 앱**  
   - “에스페란토 → (한자/루비) 치환” 기능을 GUI로 제공  
   - (옵션) JSON 파일을 사용자 업로드 / 혹은 기본 JSON 사용  
   - 에스페란토 텍스트 입력 후 치환 결과를 HTML, 괄호 등 원하는 방식으로 미리보기 & 다운로드  

2. **`에스페란토 문장의 (한자) 치환에 사용할 JSON 파일을 생성합니다.py`**  
   - **Streamlit의 `pages/` 폴더** 안에 위치 (별도 페이지)  
   - `main.py`에서 활용할 **치환용 JSON**을 사용자가 직접 대규모로 생성하는 용도  
   - CSV(“에스페란토 어근 - 번역/한자”), 사용자 정의 JSON(어근 분해/치환 규칙)을 합쳐 **최종 JSON**(전역치환리스트 + 국소치환리스트 + 2글자치환리스트)을 만들고 다운로드  

3. **`esp_text_replacement_module.py`**  
   - “메인 치환 로직”과 관련된 핵심 함수들이 들어 있음  
   - `%...%` 구문 스킵, `@...@` 구문 국소 치환, 에스페란토 문자를 `cx`→`ĉ` 등으로 통일,  
     병렬 처리(`parallel_process`) 로직 등  
   - `main.py`에서 import해 사용  

4. **`esp_replacement_json_make_module.py`**  
   - JSON 생성(치환 규칙 합성) 시 필요한 유틸리티 함수 모음  
   - 문자를 HTML 루비로 감싸거나, CSV-JSON 여러 파일을 합쳐 dictionary로 만드는 병렬 처리(`parallel_build_pre_replacements_dict`) 등  
   - `에스페란토 문장의 (한자) 치환에 사용할 JSON 파일을 생성합니다.py` 내부에서 import해 사용  

---

## 1. `main.py` (메인 앱)

### 1.1. Streamlit 설정 및 멀티프로세싱

```python
import streamlit as st
import re, io, json
import pandas as pd
import multiprocessing
...
try:
    multiprocessing.set_start_method("spawn")
except RuntimeError:
    pass
```

- **`set_start_method('spawn')`**:  Streamlit에서 `multiprocessing` 사용 시 PicklingError를 피하기 위한 설정.  
- 이미 다른 곳에서 `start_method`가 설정되어 있으면 `RuntimeError`가 발생할 수 있으므로 `try-except`로 감싸 놓음.

### 1.2. JSON 치환 규칙 로드 (`@st.cache_data`)

```python
@st.cache_data
def load_replacements_lists(json_path: str) -> Tuple[List, List, List]:
    ...
```

- **치환 규칙 JSON**을 읽어서 세 가지 리스트를 반환합니다:
  1. `replacements_final_list` (전역 치환용)  
  2. `replacements_list_for_localized_string` (`@...@` 구문 전용)  
  3. `replacements_list_for_2char` (2글자 어근 치환)  

- `@st.cache_data` 데코레이터 덕에, 한 번 로드하면 **세션 내에서 재사용**하여 속도 향상.

### 1.3. Streamlit GUI: JSON 불러오기

```python
selected_option = st.radio("JSON 파일...", ("기본값", "업로드"))
...
if selected_option == "기본값":
    ...
else:
    uploaded_file = st.file_uploader(...)
```

- 라디오 버튼으로 “기본값 사용” vs “업로드하기” 선택  
- 업로드 시 `json.load` → 내부에서 JSON 키값을 읽어 리스트를 세팅  

### 1.4. placeholder(점유 문자열) 로드

```python
placeholders_for_skipping_replacements = import_placeholders("...")
placeholders_for_localized_replacement = import_placeholders("...")
```

- `%1854%-%4934%` 등의 텍스트 파일에서 placeholder를 한 줄씩 읽어옴.  
- 이를 통해 `%...%` 구문, `@...@` 구문을 임시 치환할 때 conflict 없이 안전하게 처리 가능.

### 1.5. 병렬 처리 옵션

```python
use_parallel = st.checkbox("병렬 처리", value=False)
num_processes = st.number_input("프로세스 수", min_value=2, max_value=4, value=4, step=1)
```

- 만약 체크하면, 뒤에서 `parallel_process(...)` 사용  
- 체크 안 하면 `orchestrate_comprehensive_esperanto_text_replacement(...)` 단일 스레드로 실행

### 1.6. 출력 형식(Selectbox)

```python
format_type = st.selectbox("출력 형식 선택", [
    "HTML형식_Ruby문자_크기조정", ...
])
```
- 나중에 치환 완료 후, **HTML 루비** / **괄호** / **단순 치환** 식으로 변환할 때 어떤 형식을 쓸지 결정  
- 실제 적용은 내부의 `output_format(...)`(esp_replacement_json_make_module.py)나 `apply_ruby_html_header_and_footer(...)` 등에 반영.

### 1.7. 텍스트 입력(직접/파일 업로드), Form

- `st.radio("입력 텍스트", ("직접 입력", "파일 업로드"))`  
- 업로드된 txt/csv/md 등을 `text_file.read().decode("utf-8")`로 읽을 수 있음.  
- 최종적으로 `text_area`에 배치 후, "전송" 버튼을 누르면  
  → **실제 치환 함수**(`parallel_process` or `orchestrate_comprehensive_esperanto_text_replacement`) 호출.

### 1.8. 실제 치환 함수 호출

만약 `use_parallel`이 True이면:

```python
processed_text = parallel_process(
    text0, num_processes, placeholders_for_skipping_replacements,
    replacements_list_for_localized_string, placeholders_for_localized_replacement,
    replacements_final_list, replacements_list_for_2char, format_type
)
```

그렇지 않으면:

```python
processed_text = orchestrate_comprehensive_esperanto_text_replacement(
    text0, placeholders_for_skipping_replacements,
    replacements_list_for_localized_string, placeholders_for_localized_replacement,
    replacements_final_list, replacements_list_for_2char, format_type
)
```

이 부분이 **핵심 로직**입니다. 함수 구현은 `esp_text_replacement_module.py`에 있으며:

- `%...%`로 감싸진 부분 → 치환 제외  
- `@...@`로 감싸진 부분 → 국소 치환  
- 전역 치환 → `(old, new, placeholder)` 식으로 1차 old→placeholder, 2차 placeholder→new  
- 2글자 어근은 2번 스캔(추가 치환)  
- placeholder 복원  
- (HTML형식이라면) 줄바꿈 `<br>` 처리, 공백 `&nbsp;` 변환 등.

### 1.9. 에스페란토 특수문자 표기 변환(상단 첨자/x 형식/^ 형식)

```python
if letter_type == '상단 첨자':
    processed_text = replace_esperanto_chars(processed_text, x_to_circumflex)
    processed_text = replace_esperanto_chars(processed_text, hat_to_circumflex)
elif letter_type == '^ 형식':
    processed_text = replace_esperanto_chars(processed_text, x_to_hat)
    processed_text = replace_esperanto_chars(processed_text, circumflex_to_hat)
```

- 결과물에 대해 `cx→ĉ`/`c^→ĉ` 등을 원하는 형식으로 재변환.

### 1.10. 미리보기 및 다운로드

- 미리보기는 너무 긴 경우 앞 247줄 + 뒤 3줄만.  
- HTML 탭 vs 텍스트 탭으로 표시.  
- 다운로드 버튼(“치환 결과 다운로드”) → `.html` 파일로 내려받음.

---

## 2. `에스페란토 문장의 (한자) 치환에 사용할 JSON 파일을 생성합니다.py` (서브 페이지)

- **main.py**가 *“실제 치환”*을 수행하는 반면,  
- 이 페이지는 *“치환 규칙(합병형 JSON)을 대규모로 만들기”*에 초점.

### 2.1. CSV vs JSON 준비

사용자는
- CSV(“에스페란토 어근 - 한자/번역” 매핑)  
- (옵션) **어근 분해법 JSON**(동사/형용사 접미사 우선순위, -1 등 특정 단어 제외 등)  
- (옵션) **치환 후 문자열 JSON**(특수한 특정 한자 할당)  
을 업로드하거나, 기본값들을 사용해 **최종 JSON**을 만든다.

### 2.2. 핵심 처리: CSV→(임시 dictionary)→placeholder 치환

1. **CSV 불러오기**  
   - pandas로 “(에스페란토어근, 한자/번역)” 2개 컬럼만 사용  
   - `convert_to_circumflex(...)`로 `cx`, `c^` 등을 표준 `ĉ` 형태로 통일

2. **PEJVO 전체 단어 리스트 (예: 4만 단어) + 모든 에스페란토 어근(약 1.1만개)**  
   - 여기서 어근별로 “치환 후 문자열” + “치환 우선순위(=길이)”를 임시로 저장.

3. **사용자가 업로드한 CSV에서 (에스페란토→한자) 정보를 덮어쓰기**  
   - 예: “am → [<ruby>am<rt>愛</rt></ruby>, 길이2]” 식으로

4. **그 결과를 (old, new, placeholder) 형태로 묶기 위해 placeholder를 부여**  
   - old문자열을 placeholder로 교체 → 최종치환문자열 식

5. **병렬 처리**로, 4만여 개(또는 1.1만 단어)의 “(에스페란토 단어 + 품사)” 리스트에 대해 “safe_replace” 적용

6. **동사 활용 접미사(as,is,os,us), ‘an’, ‘on’ 등** 접미어/어근 분리 로직을 거치며 우선순위를 다시 재조정

7. **custom_stemming_setting_list(어근 분해 JSON)** 및 **user_replacement_item_setting_list(치환 후 문자열 JSON)**  
   - 특정 어근(혹은 단어)을 제외(-1)  
   - 동사/명사/형용사 형태를 새로 추가(어근+as, 어근+an, 등)  
   - “verbo_s1” / “verbo_s2” / “ne” 등.  

### 2.3. 최종 세 가지 치환 리스트

결국 **3가지** 리스트가 JSON으로 만들어진다:

1. `replacements_final_list`: 전역(全域) 치환용 (most of words)  
2. `replacements_list_for_2char`: 2글자 접두/접미($ar, $am 등)  
3. `replacements_list_for_localized_string`: 국소 치환(@...@)용  

다운로드하면, `main.py`에서 “JSON 업로드” 시에 동일 키를 읽어 세팅.

---

## 3. `esp_text_replacement_module.py`

### 3.1. 주요 함수 구조

- **`orchestrate_comprehensive_esperanto_text_replacement(...)`**  
  이 모듈의 가장 중요한 함수로, “최종 치환 과정”을 **한 번에** 수행:
  1. 공백 정규화(`unify_halfwidth_spaces`)  
  2. 에스페란토 특수문자(`cx`, `c^`) → `ĉ`  
  3. `%...%` 부분 → placeholder (치환 제외)  
  4. `@...@` 부분 → “국소 치환”(`replacements_list_for_localized_string`)  
  5. 전역 치환(`replacements_final_list` 이용)  
  6. 2글자 치환(2회 반복)  
  7. placeholder 복원  
  8. HTML이라면 `<br>`, `&nbsp;`로 처리  

- **`parallel_process(...)`**  
  - 긴 텍스트를 **줄단위**로 쪼개어, `process_segment(...)`를 병렬로 호출.  
  - `process_segment(...)` 내부에서 `orchestrate_comprehensive_esperanto_text_replacement(...)`를 수행.  
  - 마지막에 결과를 다시 이어붙임.

### 3.2. placeholder를 사용하는 safe_replace

```python
def safe_replace(text: str, replacements: List[Tuple[str, str, str]]) -> str:
    # (old, new, placeholder) 각각에 대해
    # 1) old→placeholder
    # 2) placeholder→new
    # 중복 치환이나 교차 치환을 피하기 위한 안전 방식
```

---

## 4. `esp_replacement_json_make_module.py`

### 4.1. JSON 생성 관련 핵심 유틸

- `parallel_build_pre_replacements_dict(...)`:  
  - (에스페란토어근, 품사) 목록을 여러 청크로 나눠서 `process_chunk_for_pre_replacements(...)` 병렬 수행  
  - safe_replace 결과를 합침.

- `output_format(main_text, ruby_content, format_type, char_widths_dict)`:  
  - 메인 텍스트와 번역(또는 한자)에 대해 `<ruby>`를 씌우거나, 괄호 등을 붙이는 함수  
  - HTML 루비의 크기 자동 조정(글자 폭 측정)  
  - ex) 루비가 본문보다 훨씬 길면 `<rt class="XXXS_S">` 처리를 하여 줄바꿈 삽입.

- `remove_redundant_ruby_if_identical(...)`:  
  - `<ruby>xxx<rt>xxx</rt></ruby>` 처럼 parent와 child가 동일하면 중복 제거  

### 4.2. 접미사·접두사·2글자 처리( `suffix_2char_roots`, `prefix_2char_roots`, `standalone_2char_roots` )

서브 페이지에서 2글자 어근을 **2번 치환**에 사용할 수 있도록 미리( `$ar → placeholder`, 등 ) 생성해 둠.  
이를 `main.py`의 “2글자 치환 리스트”로 삽입.

---

## 5. 전체 파이프라인 정리

1. **(선택) JSON 생성 페이지**:  
   1. CSV(어근→번역) 로딩  
   2. (필요 시) “어근 분해 JSON”, “치환 후 문자열 JSON”도 로드  
   3. “치환용 JSON 생성” 버튼 → 내부 로직으로 (에스페란토 전체 단어 목록 + CSV + JSON 설정 + placeholders) 결합 → 3가지 치환 리스트 JSON 다운로드  

2. **메인 페이지**:  
   1. 위에서 만든 JSON(또는 기본 JSON) 로드  
   2. placeholders도 로딩  
   3. 병렬 처리 설정(필요 시)  
   4. 에스페란토 텍스트 입력(직접/파일)  
   5. “전송” → `parallel_process` 또는 `orchestrate_comprehensive_esperanto_text_replacement`  
   6. 치환 결과 미리보기 + HTML 다운로드  

---

## 6. 주목할 구현 포인트

1. **Placeholders 기반 치환**  
   - “(old → placeholder → new)” 2단계 치환  
   - 중첩 교체나 교차 치환 오류를 근본적으로 예방.  
   - `%...%`, `@...@` 같은 특정 구간은 placeholder로 완전히 보호, 이후 복원.

2. **병렬 처리**  
   - Streamlit에서 multiprocess를 사용하려면 `spawn` 모드를 지정해야 함.  
   - `parallel_process` 함수로 텍스트를 줄단위로 분할 처리(줄 개수가 적으면 의미가 줄어듦).  
   - 대규모 문서일 때 유효.

3. **HTML 루비 크기 자동 조정**  
   - `measure_text_width_Arial16`으로 각 문자의 픽셀 폭 계산 → 루비와 본문 폭 비율(ratio)에 따라 클래스(`XXXS_S`, `XXS_S`, …) 할당.  
   - 루비가 본문보다 훨씬 길면 `<br>`를 삽입하여 2~3줄로 분리.

4. **‘an’, ‘on’, 접미사(as/is/os/us) 등** 에스페란토 어근 분해  
   - 특정 어근/파생어를 “형용사”, “명사”로 간주할지, “접미사 an(회원)” vs “형용사 an(형용사 어미)” 등 충돌 로직 해결  
   - 필요 시 우선순위를 낮추거나, “(어근+o)”, “(어근+on)” 등을 추가 키로 등록.

5. **어근 분해 JSON / 치환 후 문자열 JSON**  
   - “-1” 표시는 치환 제외  
   - “verbo_s1” → 동사 접미사(as, is, os, us 등) 자동 생성  
   - “verbo_s2” → 동사 “u ”, “i ” 형태(마지막에 공백이 붙는 등)까지 확장

---

## 7. 확장 아이디어 & 참고

- **더 다양한 언어**:  
  - 코드 상 “cx → ĉ”, “sx → ŝ” 로직은 모듈화되어 있어, 다른 식(예: 독자적 기호)으로 변환 가능  
- **루비 대신**:
  - “HTML 루비” 이외에도, 테이블/괄호/원문제거 등 형식을 늘릴 수 있음(`output_format` 함수).  
- **Streamlit Cloud**  
  - CPU 코어 제한(2~4)으로 병렬 효과가 제한될 수 있음  
  - 로컬에서 실행하면 더 폭넓은 스레드 활용 가능  
- **데이터베이스 연동**  
  - CSV 대신 RDB나 NoSQL DB에서 “에스페란토→한자” 매핑을 불러온 뒤 JSON 생성도 가능.  

---

# 결론

이로써,  
1. **`main.py`**는 최종 치환 앱의 **프론트엔드+백엔드** 역할(텍스트 입력 → 치환 결과).  
2. **`에스페란토 문장의 (한자) 치환에 사용할 JSON 파일을 생성합니다.py`**는 치환 규칙(대규모 JSON)을 생성하는 별도 페이지.  
3. **`esp_text_replacement_module.py`**는 치환 로직, 병렬 처리 로직 등.  
4. **`esp_replacement_json_make_module.py`**는 JSON 구성 시 필요한 여러 유틸 함수 모음.

에스페란토-한자 변환을 세밀하게 다루는 점이 특징이며, **“safe_replace, placeholder, 병렬 처리, HTML 루비 자동 크기 조정, 어근 분해”** 등이 핵심 아이디어입니다.  
코드 전반은 Streamlit의 **interactive UI** + Python의 **multiprocessing** + **JSON/CSV** 입출력을 결합해 구성됩니다.

**중급 프로그래머**로서는,  
- 각 모듈 간 **import** 구조와 placeholder를 통한 안전 치환 로직,  
- 병렬화를 위한 **segment 분할**,  
- JSON 생성 시에 동사/형용사 우선순위 재조정  
등을 자세히 파악하시면, 프로젝트를 **기호에 맞게 커스터마이징**하거나, **새로운 언어 변환** 등으로 확장할 수 있을 것입니다.

> **요약**:  
> - 4개 파일이 각각 “(메인앱) / (JSON 생성 서브앱) / (치환 로직) / (JSON 생성 유틸)”을 담당  
> - placeholder 기법과 병렬 프로세스가 치환 효율과 충돌 방지에 기여  
> - 에스페란토 특유의 ‘an/on/as/is...’ 분해 법칙과 “샘플 CSV/JSON” 구조를 읽어보면 심도 있는 이해 가능  

그럼, **에스페란토 한자 치환** 개발에 많은 도움이 되길 바랍니다!  
필요에 따라 코드를 직접 수정/추가하여 여러분만의 확장 기능을 시도해 보세요.  
