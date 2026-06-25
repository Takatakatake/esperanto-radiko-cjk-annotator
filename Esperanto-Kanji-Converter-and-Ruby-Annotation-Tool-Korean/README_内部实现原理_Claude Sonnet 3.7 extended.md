# 에스페란토 한자 변환 및 루비 주석 도구 - 기술 설명서

## 목차
1. 애플리케이션 개요
2. 아키텍처 및 모듈 구성
3. 핵심 모듈 상세 분석
4. 데이터 흐름 및 처리 과정
5. 알고리즘 및 구현 기법
6. 성능 최적화 전략
7. 확장 및 사용자 정의 방법

---

## 1. 애플리케이션 개요

이 애플리케이션은 에스페란토 문장을 한자로 변환하거나 HTML 루비 주석을 추가하는 웹 기반 도구입니다. Streamlit 프레임워크를 사용하여 구현되었으며, 에스페란토 텍스트 처리를 위한 여러 전문 모듈로 구성되어 있습니다.

### 주요 기능:
- 에스페란토 문장의 어근 및 접사 분석
- 한자 치환 및 HTML 루비 주석 생성
- 다양한 출력 형식 지원
- 사용자 정의 치환 규칙 생성 및 관리
- 대용량 텍스트 처리를 위한 병렬 처리

---

## 2. 아키텍처 및 모듈 구성

애플리케이션은 다음 4개의 주요 모듈로 구성되어 있습니다:

### 2.1 main.py
- **역할**: 메인 애플리케이션 진입점 및 사용자 인터페이스
- **기술**: Streamlit 웹 프레임워크
- **주요 기능**: 사용자 입력 처리, 치환 프로세스 조정, 결과 표시

### 2.2 에스페란토 문장의 (한자) 치환에 사용할 JSON 파일을 생성합니다.py
- **역할**: 치환 규칙 JSON 파일 생성 도구
- **기술**: Streamlit 페이지 컴포넌트
- **주요 기능**: CSV 파일에서 치환 규칙 생성, 사용자 정의 규칙 처리, JSON 병합

### 2.3 esp_text_replacement_module.py
- **역할**: 에스페란토 텍스트 처리 핵심 모듈
- **기술**: 문자열 처리, 정규식, 병렬 처리
- **주요 기능**: 문자 변환, 치환 로직, 루비 처리, 병렬 텍스트 처리

### 2.4 esp_replacement_json_make_module.py
- **역할**: JSON 파일 생성 보조 모듈
- **기술**: 문자열 처리, 멀티프로세싱
- **주요 기능**: 문자 폭 측정, 출력 형식 지원, 병렬 치환 처리

### 모듈 간 의존성:
```
main.py
  ├─ esp_text_replacement_module.py
  └─ [JSON 파일, 플레이스홀더 파일]

에스페란토 문장의 (한자) 치환에 사용할 JSON 파일을 생성합니다.py
  ├─ esp_text_replacement_module.py
  ├─ esp_replacement_json_make_module.py
  └─ [CSV 파일, 사용자 정의 설정 파일]
```

---

## 3. 핵심 모듈 상세 분석

### 3.1 main.py 분석

#### 3.1.1 핵심 구성 요소
```python
# 주요 모듈 임포트
import streamlit as st
import multiprocessing
from esp_text_replacement_module import (
    x_to_circumflex, x_to_hat, hat_to_circumflex, circumflex_to_hat,
    replace_esperanto_chars, import_placeholders,
    orchestrate_comprehensive_esperanto_text_replacement,
    parallel_process, apply_ruby_html_header_and_footer
)

# 캐시된 JSON 로딩 함수
@st.cache_data
def load_replacements_lists(json_path: str) -> Tuple[List, List, List]:
    # JSON 파일 로드 및 세 가지 치환 리스트 반환
    ...

# Streamlit UI 구성
# 사용자 입력 처리
# 치환 처리 호출
# 결과 표시 및 다운로드 옵션
```

#### 3.1.2 주요 기능 흐름
1. **설정 및 초기화**:
   - Streamlit 페이지 구성
   - multiprocessing 설정 (Windows 호환성 보장)
   - 치환 리스트 초기화

2. **JSON 파일 로딩**:
   - 사용자가 선택한 JSON 파일 또는 기본 JSON 파일 로드
   - `load_replacements_lists()` 함수를 통해 세 가지 치환 리스트 추출
   - `@st.cache_data` 데코레이터로 성능 최적화

3. **플레이스홀더 임포트**:
   - 문자열 치환 중 충돌 방지를 위한 플레이스홀더 목록 로드

4. **사용자 입력 처리**:
   - 출력 형식 선택 (HTML, 괄호 형식 등)
   - 텍스트 입력 방식 선택 (직접 입력 또는 파일 업로드)
   - 출력 문자 형식 선택 (상단 첨자, x 형식, ^ 형식)

5. **치환 처리 실행**:
   - 병렬 처리 옵션에 따라 `parallel_process()` 또는 `orchestrate_comprehensive_esperanto_text_replacement()` 호출
   - 선택된 문자 형식으로 변환
   - HTML 헤더/푸터 적용

6. **결과 표시 및 다운로드**:
   - 텍스트 길이에 따라 미리보기 생성
   - HTML 또는 텍스트 형식으로 결과 표시
   - 다운로드 버튼 생성

### 3.2 에스페란토 문장의 (한자) 치환에 사용할 JSON 파일을 생성합니다.py 분석

#### 3.2.1 핵심 구성 요소
```python
# 외부 모듈 임포트
from esp_text_replacement_module import (
    convert_to_circumflex, safe_replace, import_placeholders,
    apply_ruby_html_header_and_footer
)
from esp_replacement_json_make_module import (
    convert_to_circumflex, output_format, import_placeholders,
    capitalize_ruby_and_rt, process_chunk_for_pre_replacements,
    parallel_build_pre_replacements_dict, remove_redundant_ruby_if_identical
)

# 에스페란토 어미 및 접사 처리를 위한 데이터 구조
verb_suffix_2l = {...}  # 동사 활용 어미
AN = [...]  # 'an' 접미사 처리를 위한 단어 목록
ON = [...]  # 'on' 접미사 처리를 위한 단어 목록
suffix_2char_roots = [...]  # 2글자 접미사 목록
prefix_2char_roots = [...]  # 2글자 접두사 목록
standalone_2char_roots = [...]  # 독립형 2글자 어근 목록

# 플레이스홀더 파일 로드
# 사용자 입력 처리
# JSON 생성 및 병합
# 다운로드 옵션 제공
```

#### 3.2.2 주요 기능 흐름
1. **초기화 및 데이터 준비**:
   - 동사 어미, 접사 등의 데이터 구조 정의
   - 플레이스홀더 파일 로드
   - 문자 폭 측정을 위한 JSON 로드

2. **사용자 입력 처리**:
   - CSV 파일 (에스페란토 어근-한자/한국어 대응표) 로드
   - 어근 분해법 및 치환 후 문자열 설정 JSON 로드
   - 출력 형식 및 병렬 처리 옵션 설정

3. **치환 규칙 생성 프로세스**:
   - CSV 데이터에서 임시 치환 사전 생성
   - 품사 정보에 따른 처리 (접미사 추가 등)
   - 접미사(an, on) 및 2글자 어근 특별 처리
   - 사용자 정의 설정 적용

4. **최종 JSON 파일 구성**:
   - 전역 치환용 리스트 생성
   - 2글자 어근 치환용 리스트 생성
   - 국소 문자 치환용 리스트 생성
   - 세 리스트를 하나의 JSON으로 병합

5. **다운로드 옵션 제공**:
   - 생성된 JSON 파일 다운로드 버튼 생성

### 3.3 esp_text_replacement_module.py 분석

#### 3.3.1 핵심 구성 요소
```python
# 문자 변환 사전 정의
x_to_circumflex = {...}
circumflex_to_x = {...}
x_to_hat = {...}
hat_to_x = {...}
hat_to_circumflex = {...}
circumflex_to_hat = {...}

# 문자 변환 함수
def replace_esperanto_chars(text, char_dict: Dict[str, str]) -> str: ...
def convert_to_circumflex(text: str) -> str: ...
def unify_halfwidth_spaces(text: str) -> str: ...

# 안전한 치환 및 플레이스홀더 관련 함수
def safe_replace(text: str, replacements: List[Tuple[str, str, str]]) -> str: ...
def import_placeholders(filename: str) -> List[str]: ...

# 특수 마크업 처리 함수
def find_percent_enclosed_strings_for_skipping_replacement(text: str) -> List[str]: ...
def create_replacements_list_for_intact_parts(text: str, placeholders: List[str]) -> List[Tuple[str, str]]: ...
def find_at_enclosed_strings_for_localized_replacement(text: str) -> List[str]: ...
def create_replacements_list_for_localized_replacement(...): ...

# 종합 치환 및 병렬 처리 함수
def orchestrate_comprehensive_esperanto_text_replacement(...): ...
def process_segment(...): ...
def parallel_process(...): ...
def apply_ruby_html_header_and_footer(processed_text: str, format_type: str) -> str: ...
```

#### 3.3.2 주요 알고리즘 및 기능
1. **문자 변환**:
   - 에스페란토 특수 문자를 다양한 형식(상단 첨자, x 형식, ^ 형식)으로 상호 변환

2. **안전한 문자열 치환 (safe_replace)**:
   - 문자열 치환 시 중간 충돌을 방지하는 2단계 치환 방식
   - 원본 → 플레이스홀더 → 결과의 단계적 치환

3. **특수 마크업 처리**:
   - % 마크업: 치환에서 제외될 부분 처리
   - @ 마크업: 국소적으로만 치환할 부분 처리

4. **종합 치환 프로세스**:
   - 문자 정규화 및 변환
   - 마크업 처리
   - 전역 치환
   - 2글자 어근 치환
   - 플레이스홀더 복원
   - HTML 형식 처리

5. **병렬 처리**:
   - 텍스트를 여러 청크로 분할
   - 멀티프로세싱을 통한 병렬 처리
   - 결과 병합

### 3.4 esp_replacement_json_make_module.py 분석

#### 3.4.1 핵심 구성 요소
```python
# 문자 변환 관련 함수 및 사전
x_to_circumflex = {...}
def replace_esperanto_chars(text, char_dict: Dict[str, str]) -> str: ...
def convert_to_circumflex(text: str) -> str: ...

# 문자 폭 측정 및 관련 함수
def measure_text_width_Arial16(text, char_widths_dict: Dict[str, int]) -> int: ...
def insert_br_at_half_width(text, char_widths_dict: Dict[str, int]) -> str: ...
def insert_br_at_third_width(text, char_widths_dict: Dict[str, int]) -> str: ...

# 출력 형식 함수
def output_format(main_text, ruby_content, format_type, char_widths_dict): ...

# 보조 함수
def contains_digit(s: str) -> bool: ...
def import_placeholders(filename: str) -> List[str]: ...
def capitalize_ruby_and_rt(text: str) -> str: ...

# 병렬 처리 관련 함수
def safe_replace(text: str, replacements: List[Tuple[str, str, str]]) -> str: ...
def process_chunk_for_pre_replacements(...): ...
def parallel_build_pre_replacements_dict(...): ...

# 루비 관련 특수 함수
def remove_redundant_ruby_if_identical(text: str) -> str: ...
```

#### 3.4.2 주요 알고리즘 및 기능
1. **문자 폭 측정**:
   - Arial 16pt 기준 문자 폭 사전 사용
   - 텍스트 전체 폭 계산

2. **자동 줄바꿈 삽입**:
   - 텍스트 폭의 절반 또는 1/3 지점에 `<br>` 삽입
   - 루비 텍스트가 긴 경우 가독성 향상

3. **출력 형식 생성**:
   - HTML 루비 형식 (크기 조정 포함/미포함)
   - 괄호 형식
   - 단순 치환 형식

4. **병렬 치환 처리**:
   - 데이터를 여러 청크로 분할
   - 각 청크를 별도 프로세스에서 처리
   - 결과 병합

5. **루비 태그 최적화**:
   - 중복 루비 제거
   - 루비 태그 내 대문자화 처리

---

## 4. 데이터 흐름 및 처리 과정

이 애플리케이션의 데이터 흐름은 두 가지 주요 경로로 나뉩니다:

### 4.1 텍스트 치환 경로 (main.py)

```
사용자 입력 (에스페란토 텍스트)
↓
JSON 파일 로드 (치환 규칙)
↓
플레이스홀더 로드
↓
텍스트 전처리 (문자 정규화, % 및 @ 마크업 처리)
↓
치환 처리 (전역 치환, 2글자 어근 치환)
↓
문자 형식 변환 (상단 첨자, x 형식, ^ 형식)
↓
HTML 헤더/푸터 적용
↓
결과 표시 및 다운로드
```

### 4.2 JSON 생성 경로 (에스페란토 문장의 (한자) 치환에 사용할 JSON 파일을 생성합니다.py)

```
CSV 파일 및 사용자 설정 로드
↓
임시 치환 사전 생성
↓
품사별 처리 및 확장
↓
접미사 및 2글자 어근 처리
↓
사용자 정의 설정 적용
↓
세 가지 치환 리스트 생성:
- 전역 치환용 리스트
- 2글자 어근 치환용 리스트
- 국소 문자 치환용 리스트
↓
JSON 병합 및 다운로드
```

### 4.3 핵심 데이터 구조

1. **치환 리스트 구조**:
   ```
   (old, new, placeholder)의 튜플 리스트
   ```
   - `old`: 원본 에스페란토 단어/어근
   - `new`: 치환된 결과(HTML 루비 등)
   - `placeholder`: 중간 치환에 사용되는 고유 문자열

2. **치환 우선순위 체계**:
   - 기본 우선순위 = 문자 길이 × 10000
   - 품사별 우선순위 조정
   - 2글자 어근 특별 우선순위

3. **JSON 파일 구조**:
   ```json
   {
     "全域替换用のリスト(列表)型配列(replacements_final_list)": [...],
     "二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)": [...],
     "局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)": [...]
   }
   ```

---

## 5. 알고리즘 및 구현 기법

### 5.1 안전한 문자열 치환 알고리즘 (safe_replace)

이 애플리케이션의 핵심 알고리즘 중 하나는 `safe_replace` 함수입니다. 이 함수는 중간 충돌 없이 다중 문자열 치환을 안전하게 수행합니다:

```python
def safe_replace(text: str, replacements: List[Tuple[str, str, str]]) -> str:
    """
    (old, new, placeholder) 리스트를 받아
    text에서 old → placeholder → new의 단계적 치환을 수행
    """
    valid_replacements = {}
    # 먼저 old→placeholder
    for old, new, placeholder in replacements:
        if old in text:
            text = text.replace(old, placeholder)
            valid_replacements[placeholder] = new
    # 다음에 placeholder→new
    for placeholder, new in valid_replacements.items():
        text = text.replace(placeholder, new)
    return text
```

#### 5.1.1 작동 원리
1. 먼저 모든 원본 문자열을 고유한 플레이스홀더로 치환
2. 그 다음 플레이스홀더를 최종 결과로 치환

#### 5.1.2 이점
- 부분 문자열 치환 충돌 방지
- 긴 문자열을 먼저 치환해도 안전함
- 치환 과정의 완전한 제어 가능

### 5.2 어근 분석 및 치환 우선순위 시스템

JSON 생성 도구에서 사용되는 어근 분석 시스템은 에스페란토의 어형론적 특성을 반영합니다:

#### 5.2.1 품사별 처리
```python
if "名词" in j[1]:  # 명사
    for k in ["o", "on", 'oj']:
        if not i+k in pre_replacements_dict_2:
            pre_replacements_dict_3[i+k] = [j[0]+k, j[2]+len(k)*10000-3000]
elif "形容词" in j[1]:  # 형용사
    for k in ["a", "aj", 'an']:
        # 처리 로직
elif "副词" in j[1]:  # 부사
    for k in ["e"]:
        # 처리 로직
elif "动词" in j[1]:  # 동사
    for k1, k2 in verb_suffix_2l_2.items():
        # 동사 활용 어미 처리
    for k in ["u ", "i ", "u", "i"]:
        # 명령형, 부정형 등 처리
```

#### 5.2.2 우선순위 시스템
어근 길이, 품사, 접사 여부 등에 따라 다양한 우선순위 조정이 이루어집니다:
- 기본 우선순위: 문자 길이 × 10000
- 동사 활용 어미: +len(k1)*10000-3000
- 품사 접미사: +len(k)*10000-3000 ~ -5000
- 특별 처리(an, on 등): 별도 계산

이 우선순위 시스템을 통해 가장 적합한 치환 결과가 선택됩니다.

### 5.3 병렬 처리 구현

대용량 텍스트 처리를 위한 병렬 처리 구현:

#### 5.3.1 텍스트 치환 병렬화 (parallel_process)
```python
def parallel_process(text, num_processes, ...):
    # 텍스트를 줄 단위로 분할
    lines = re.findall(r'.*?\n|.+$', text)
    
    # 프로세스당 라인 수 계산
    lines_per_process = max(num_lines // num_processes, 1)
    
    # 각 프로세스의 처리 범위 설정
    ranges = [(i * lines_per_process, (i + 1) * lines_per_process) 
             for i in range(num_processes)]
    ranges[-1] = (ranges[-1][0], num_lines)  # 마지막 범위 조정
    
    # 멀티프로세싱 풀 생성 및 실행
    with multiprocessing.Pool(processes=num_processes) as pool:
        results = pool.starmap(process_segment, [...])
    
    # 결과 병합
    return ''.join(results)
```

#### 5.3.2 JSON 생성 병렬화 (parallel_build_pre_replacements_dict)
```python
def parallel_build_pre_replacements_dict(
    E_stem_with_Part_Of_Speech_list, replacements, num_processes=4):
    
    # 데이터를 청크로 분할
    chunk_size = -(-total_len // num_processes)
    chunks = [...]
    
    # 병렬 처리 실행
    with multiprocessing.Pool(num_processes) as pool:
        partial_dicts = pool.starmap(
            process_chunk_for_pre_replacements,
            [(chunk, replacements) for chunk in chunks]
        )
    
    # 부분 결과 병합
    merged_dict = {}
    for partial_d in partial_dicts:
        # 병합 로직
    
    return merged_dict
```

### 5.4 HTML 루비 처리 및 크기 조정

루비 태그의 크기 조정은 문자 폭 계산을 기반으로 합니다:

```python
def output_format(main_text, ruby_content, format_type, char_widths_dict):
    if format_type == 'HTML格式_Ruby文字_大小调整':
        width_ruby = measure_text_width_Arial16(ruby_content, char_widths_dict)
        width_main = measure_text_width_Arial16(main_text, char_widths_dict)
        ratio_1 = width_ruby / width_main
        
        if ratio_1 > 6:
            return f'<ruby>{main_text}<rt class="XXXS_S">{insert_br_at_third_width(ruby_content, char_widths_dict)}</rt></ruby>'
        elif ratio_1 > (9/3):
            return f'<ruby>{main_text}<rt class="XXS_S">{insert_br_at_half_width(ruby_content, char_widths_dict)}</rt></ruby>'
        # 기타 비율에 따른 처리
```

이 알고리즘은 루비 텍스트와 주 텍스트의 폭 비율에 따라 적절한 CSS 클래스를 적용하고, 필요한 경우 루비 텍스트에 자동 줄바꿈을 삽입합니다.

---

## 6. 성능 최적화 전략

이 애플리케이션은 다양한 성능 최적화 전략을 사용합니다:

### 6.1 Streamlit 캐싱

`@st.cache_data` 데코레이터를 사용하여 JSON 파일 로딩 결과를 캐싱합니다:

```python
@st.cache_data
def load_replacements_lists(json_path: str) -> Tuple[List, List, List]:
    """
    JSON 파일을 로드하고 세 가지 리스트를 튜플로 반환
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # ...
    return (
        replacements_final_list,
        replacements_list_for_localized_string,
        replacements_list_for_2char,
    )
```

이 캐싱은 사용자가 같은 JSON 파일을 반복적으로 사용할 때 성능을 크게 향상시킵니다.

### 6.2 멀티프로세싱

병렬 처리를 위한 멀티프로세싱 구현:

```python
# 윈도우 호환성을 위한 처리
try:
    multiprocessing.set_start_method("spawn")
except RuntimeError:
    pass  # 이미 설정된 경우 무시

# 사용자 선택에 따른 병렬 처리 활성화
if use_parallel:
    processed_text = parallel_process(
        text=text0,
        num_processes=num_processes,
        # ...
    )
else:
    processed_text = orchestrate_comprehensive_esperanto_text_replacement(
        # ...
    )
```

병렬 처리는 특히 대용량 텍스트 처리 시 성능을 크게 향상시킵니다.

### 6.3 최적화된 치환 알고리즘

`safe_replace` 함수는 효율적인 2단계 치환을 구현합니다:

1. 사용된 패턴만 필터링하여 처리
2. 딕셔너리를 사용한 빠른 룩업

```python
def safe_replace(text: str, replacements: List[Tuple[str, str, str]]) -> str:
    valid_replacements = {}
    # 사용된 패턴만 필터링
    for old, new, placeholder in replacements:
        if old in text:  # 존재하는 패턴만 처리
            text = text.replace(old, placeholder)
            valid_replacements[placeholder] = new
    # 필터링된 패턴만 치환
    for placeholder, new in valid_replacements.items():
        text = text.replace(placeholder, new)
    return text
```

### 6.4 문자열 처리 최적화

긴 치환 리스트에서의 성능 최적화:

1. **길이 기반 정렬**: 긴 문자열을 먼저 처리하여 부분 문자열 문제 방지
```python
sorted_replacements_list = sorted(replacements_list, key=lambda x: len(x[0]), reverse=True)
```

2. **우선순위 시스템**: 복잡한 치환 규칙의 효율적 적용
```python
pre_replacements_list_2 = sorted(pre_replacements_list_1, key=lambda x: x[2], reverse=True)
```

3. **중복 최소화**: 불필요한 중복 루비 제거
```python
def remove_redundant_ruby_if_identical(text: str) -> str:
    # 중복 루비 제거 로직
```

---

## 7. 확장 및 사용자 정의 방법

이 애플리케이션은 다양한 방식으로 확장하고 사용자 정의할 수 있습니다:

### 7.1 사용자 정의 CSV 파일

에스페란토 어근과 한국어/한자 대응 관계를 정의하는 CSV 파일은 다음 형식을 따릅니다:

```csv
어근,번역
am,사랑
lingv,언어
pac,평화
```

사용자는 이 CSV 파일을 수정하여 자신만의 번역/한자 대응 목록을 만들 수 있습니다.

### 7.2 어근 분해법 사용자 정의

어근 분해법은 JSON 형식으로 정의됩니다:

```json
[
  ["어근", "우선순위", ["옵션1", "옵션2", ...]],
  ["am", "dflt", ["verbo_s1"]],
  ["re", "dflt", ["ne"]]
]
```

- `"어근"`: 에스페란토 어근
- `"우선순위"`: "dflt"(기본) 또는 숫자 값
- `"옵션"`: 
  - `"verbo_s1"`: 동사 활용 어미 추가
  - `"verbo_s2"`: 명령형, 부정형 추가
  - `"ne"`: 기본 형태만 사용

### 7.3 출력 형식 사용자 정의

HTML 루비 형식의 CSS는 `apply_ruby_html_header_and_footer` 함수에서 정의됩니다:

```python
def apply_ruby_html_header_and_footer(processed_text: str, format_type: str) -> str:
    if format_type in ('HTML格式_Ruby文字_大小调整','HTML格式_Ruby文字_大小调整_汉字替换'):
        ruby_style_head = """<!DOCTYPE html>
<html lang="ja">
  <head>
    <style>
    /* CSS 스타일 정의 */
    </style>
  </head>
  <body>
  <p class="text-M_M">
"""
        # ...
```

이 함수를 수정하여 루비 스타일을 사용자 정의할 수 있습니다.

### 7.4 새로운 치환 규칙 추가

`user_replacement_item_setting_list`를 통해 특별한 치환 규칙을 추가할 수 있습니다:

```json
[
  ["어근", "우선순위", ["옵션"], "치환결과"],
  ["esperant", "dflt", ["ne"], "세계어/희망"],
  ["amik", "dflt", ["ne"], "친구/우정"]
]
```

이 형식을 사용하여 특정 단어에 대해 복잡한 치환 결과를 정의할 수 있습니다.

### 7.5 확장 방향

애플리케이션을 확장하는 몇 가지 가능한 방향:

1. **새로운 출력 형식 추가**:
   - 새로운 형식을 지원하려면 `output_format` 함수를 수정

2. **다른 언어 지원**:
   - 한자 대신 다른 언어 표기를 사용하려면 CSV 파일만 변경

3. **추가 특수 마크업**:
   - 현재 `%`와 `@` 외에 다른 특수 마크업을 추가하려면 관련 함수 확장

4. **성능 최적화**:
   - 더 빠른 알고리즘 또는 캐싱 전략 구현

5. **UI 향상**:
   - Streamlit 컴포넌트를 추가하여 사용자 경험 개선

---

이 기술 설명서는 에스페란토 한자 변환 및 루비 주석 도구의 내부 작동 방식을 포괄적으로 설명합니다. 추가 질문이나 피드백이 있으시면 GitHub 리포지토리를 통해 문의해 주세요.