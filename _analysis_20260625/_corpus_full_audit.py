# -*- coding: utf-8 -*-
"""京大エス研HTMLコーパス全文書の語根分解精度を【デプロイ実機=autofix込み】で総点検。
   - baseline(GG貪欲) と autofix(先頭1字孤立 自動補正=実機の挙動) の両方を測る
   - 全文書の境界一致率を表に(下位/分布/中央値)、out/_audit_perdoc.json に全件
   - 不一致を gold(参照1学習者版)・##偽分解マーカー・文書単位の人手レビューで裁定し、
       (1) コーパス自身の分解誤り(app正・gold一致)  -> out/_audit_corpus_errors.json
       (2) 真のapp欠陥(gold=コーパス, app誤り)        -> out/_audit_app_errors.json
       (3) 構造的天井(国名-i/o 等) / 同綴りホモグラフ / 裁定不能 -> out/_audit_ceiling.json
   を人間可読のカタログとして出力する。
   python _corpus_full_audit.py
"""
import re, sys, json, os, collections, statistics
sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
from extract_lib import hat_to_circumflex, replace_esperanto_chars
import no_worsening_audit as runtime_audit

ESP_LETTERS = "a-zĉĝĥĵŝŭ"

def norm(p):
    return replace_esperanto_chars(p, hat_to_circumflex).lower().replace("’", "'").strip()

def is_evaluable_surface(word):
    """Esperanto letters plus internal/terminal ASCII apostrophe and hyphen."""
    return runtime_audit.evaluable(word)

CORP = os.environ.get(
    "ESP_CORPUS_PATH",
    os.path.join(BASE, "_project_root_misc", "京大エス研html文書＿Github"),
)
CORPUS_CONTENT_DIRS = ("lernolibroj", "legajxoj", "revuoj", "rondolegado")
EXPECTED_CONTENT_FILES = 169
EXPECTED_ANNOTATED_DOCUMENTS = 123
EXPECTED_ZERO_RUBY_DOCUMENTS = 46
EXPECTED_ZERO_RUBY_TALLY = {
    "navigation/index": 17,
    "plain-source/Gerda": 28,
    "plain-source/bilingual": 1,
}

# HTMLで今回確定した地名分節。goldの収録有無や偽分解マーカーに
# 左右されず、JA実機がこの境界を再現することを必須gateにする。
# countは修正HTML上の実出現数で、合計74件。ハイフンは文字として
# 保持し、o+n / i+o / i+aなど連続するbare語尾はHTML観測上1片に畳み込む。
HTML_PLACE_ALIGNMENT_MANIFEST = {
    "Svislando": ("Svis/land/o", 16),
    "Katmando": ("Katmand/o", 5),
    "Nurnbergo": ("Nurnberg/o", 4),
    "Nov-Zelando": ("Nov/Zeland/o", 4),
    "Burno": ("Burn/o", 4),
    "Italujo": ("Ital/uj/o", 1),
    "Sud-Sudano": ("Sud/Sudan/o", 2),
    "sud-sudana": ("sud/sudan/a", 1),
    "Kievon": ("Kiev/o/n", 1),
    "Mukdeno": ("Mukden/o", 1),
    "Mezorienton": ("Mez/orient/o/n", 1),
    "Sovetunio": ("Sovet/uni/o", 6),
    "Sovetunia": ("Sovet/uni/a", 1),
    "Kamakuron": ("Kamakur/o/n", 1),
    "Enoŝimon": ("Enoŝim/o/n", 1),
    "Tuskolo": ("Tuskol/o", 1),
    "Taragono": ("Taragon/o", 1),
    "Ĝirono": ("Ĝiron/o", 1),
    "Smolenko": ("Smolenk/o", 1),
    "Kaŭno": ("Kaŭn/o", 1),
    "kalifornia": ("kaliforni/a", 2),
    "Hokkajda": ("Hokkajd/a", 1),
    "Ŝanhajon": ("Ŝanhaj/o/n", 1),
    "Pekinon": ("Pekin/o/n", 1),
    "Ĵurason": ("Ĵuras/o/n", 2),
    "Bikini-Atolo": ("Bikini/Atol/o", 1),
    "Papuo-Nov-Gvineo": ("Papu/o/Nov/Gvine/o", 1),
    "Pu-lando": ("Pu/land/o", 2),
    "BUENOS-AIRESO": ("BUENOS-AIRES/O", 2),
    "Ukrainio": ("Ukrain/i/o", 1),
    "Sovetia": ("Sovet/i/a", 1),
    "Bohemio": ("Bohem/i/o", 1),
    "Etiopio": ("Etiop/i/o", 1),
    "Kroatio": ("Kroat/i/o", 1),
    "Pomerio": ("Pomer/i/o", 1),
    "Ĉeĥion": ("Ĉeĥ/i/o/n", 1),
}

# 同じ汎用国名機構の屈折派生と、今回明示裁定した長語根も、
# 現在のHTML修正件数とは切り離して回帰検査する。
PLACE_DERIVATIVE_PROBES = {
    "Ukrainia": "Ukrain/i/a",
    "Sovetio": "Sovet/i/o",
    "Moravio": "Moravi/o",
    "Iberio": "Iber/io",
}
if not os.path.isdir(CORP):
    raise FileNotFoundError(
        f"京大エス研HTMLコーパスが見つかりません: {CORP}\n"
        "別の場所にある場合は ESP_CORPUS_PATH を指定してください。"
    )
APP = BASE + r"\Esperanto-Kanji-Ruby-JA"; sys.path.insert(0, APP)
import esp_text_replacement_module as m
import esp_overlay_module as ov
DATA = APP + r"\app_data"
dd = json.load(open(lp(DATA + r"\置換リスト_ルビ.json"), encoding="utf-8"))
GL = dd["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]
G2 = dd["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]
GG = dd["全域替换用のリスト(列表)型配列(replacements_final_list)"]
ps = m.import_placeholders(lp(DATA + r"\placeholders_skip.txt"))
pl = m.import_placeholders(lp(DATA + r"\placeholders_localcapture.txt"))
FMT = "HTML格式_Ruby文字_大小调整"
USER_CORRECTIONS = json.load(
    open(lp(DATA + r"\user_corrections.json"), encoding="utf-8")
)
EFFECTIVE_GG = ov.merge_overlay(
    GG,
    runtime_audit.overlay_entries_from_corrections(USER_CORRECTIONS, "ruby"),
)

RUBY_RE = runtime_audit.RUBY_RE
RAW_RUBY_OPEN_RE = runtime_audit.RAW_RUBY_OPEN_RE

# ---- gold(学習者版) word -> decomposition ----
GOLD = os.environ.get(
    "ESP_GOLD_PATH",
    os.path.join(
        os.path.dirname(BASE),
        "エスペラント辞書徹底語根分解_20260630",
        "世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416.txt",
    ),
)
if not os.path.isfile(GOLD):
    raise FileNotFoundError(
        f"gold語根分解辞書が見つかりません: {GOLD}\n"
        "別の場所にある場合は ESP_GOLD_PATH を指定してください。"
    )
FAKE_MARKER_RE = re.compile(r"##偽分解(?:\([^)]*\))?")
gold_records = {}
with open(lp(GOLD), encoding="utf-8") as f:
    for line_no, line in enumerate(f, 1):
        if ":" not in line: continue
        d, gloss = line.split(":", 1)
        d = d.strip()
        if " " in d or d.startswith("-") or d.endswith("-") or not d: continue
        w = norm("".join(p for p in d.split("/") if p))
        if is_evaluable_surface(w):
            decomp = "/".join(p for p in norm(d).split("/") if p)
            marker_match = FAKE_MARKER_RE.search(gloss)
            # The marker belongs to this exact selected row/decomposition.
            # Never propagate a marker merely because another row has the same headword.
            gold_records.setdefault(w, {
                "decomp": decomp,
                "marker": marker_match.group(0) if marker_match else None,
                "line": line_no,
            })
gold_decomp = {w: r["decomp"] for w, r in gold_records.items()}
print(f"gold(学習者版) 収録 {len(gold_decomp)} 語")

# ---- 文脈を人手確認済みの保持対象（文書単位でのみ抑制） ----
REVIEWED_CONTEXT = os.path.join(BASE, "_analysis_20260625", "_audit_reviewed_context.json")
reviewed_data = json.load(open(lp(REVIEWED_CONTEXT), encoding="utf-8"))
reviewed_index = {}
reviewed_expected_counts = {}
for entry in reviewed_data.get("entries", []):
    word = norm(entry["word"])
    corpus = "/".join(norm(p) for p in entry["corpus"].split("/") if norm(p))
    entry_key = (word, corpus)
    reviewed_expected_counts[entry_key] = entry.get("reviewed_count", 0)
    for path in entry.get("documents", []):
        key = (word, corpus, path.replace("\\", "/"))
        if key in reviewed_index:
            raise ValueError(f"reviewed-context key が重複しています: {key}")
        reviewed_index[key] = entry
print(f"人手レビュー済み {len(reviewed_data.get('entries', []))} 語 / {len(reviewed_index)} 文書キー")


def normalized_decomp(decomposition):
    return "/".join(
        norm(piece) for piece in decomposition.split("/") if norm(piece)
    )

def cuts(s):
    pp = [p for p in s.split("/") if p]; b = set(); c = 0
    for p in pp[:-1]: c += len(p); b.add(c)
    return b

PLACE_BARE_PIECES = {
    "o", "a", "e", "i", "n", "j", "jn",
    "oj", "on", "ojn", "aj", "an", "ajn", "en",
}


def place_expected_observable(decomp):
    """Collapse adjacent bare endings exactly as rendered HTML exposes them."""
    observable = []
    for raw_piece in decomp.split("/"):
        piece = norm(raw_piece)
        if not piece:
            continue
        is_bare = piece in PLACE_BARE_PIECES
        if is_bare and observable and observable[-1][1]:
            observable[-1] = (observable[-1][0] + piece, True)
        else:
            observable.append((piece, is_bare))
    return "/".join(piece for piece, _is_bare in observable)


def place_canonical_decomp(decomp):
    """Ignore literal hyphens while retaining every morphological boundary."""
    pieces = []
    for raw_piece in decomp.split("/"):
        piece = norm(raw_piece).replace("-", "")
        if piece:
            pieces.append(piece)
    return "/".join(pieces)


def build_place_html_pattern(surface, decomp):
    """Build the exact ruby/literal shape asserted by one HTML manifest row."""
    pieces = [piece for piece in decomp.split("/") if piece]
    position = 0
    fragments = []
    for piece in pieces:
        # The path manifest records compound punctuation as an explicit
        # literal part (e.g. ``Nov/-/Zeland/o``).  It is visible text, never a
        # ruby root.  Treating it as ruby made every hyphenated place look
        # absent even though the HTML itself was correct.
        if piece and all(ch in "-'’" for ch in piece):
            token = surface[position:position + len(piece)]
            if token != piece:
                raise ValueError(
                    f"地名manifest句読点再構成不能: {surface!r} / {decomp!r} "
                    f"at {position}: {token!r} != {piece!r}"
                )
            fragments.append(re.escape(token))
            position += len(piece)
            continue
        # Expected decompositions omit compound separators; preserve each
        # literal hyphen from the full surface between the surrounding pieces.
        while position < len(surface) and surface[position] == "-" and not piece.startswith("-"):
            fragments.append(re.escape(surface[position]))
            position += 1
        token = surface[position:position + len(piece)]
        if token.casefold() != piece.casefold():
            raise ValueError(
                f"地名manifest再構成不能: {surface!r} / {decomp!r} "
                f"at {position}: {token!r} != {piece!r}"
            )
        if norm(piece) in PLACE_BARE_PIECES:
            fragments.append(re.escape(token))
        else:
            fragments.append(
                r"<ruby\b[^>]*>\s*" + re.escape(token)
                + r"\s*<rt\b[^>]*>(?:(?:[^<]|<br\s*/?>)*?)"
                + r"</rt\s*>\s*</ruby\s*>"
            )
        position += len(piece)
    while position < len(surface) and surface[position] == "-":
        fragments.append(re.escape(surface[position]))
        position += 1
    if position != len(surface):
        raise ValueError(
            f"地名manifest表層未消費: {surface!r} / {decomp!r} at {position}"
        )
    return re.compile(
        "".join(fragments) + rf"(?![{ESP_LETTERS}])",
        re.IGNORECASE | re.DOTALL,
    )


PLACE_MANIFEST_PATH = os.path.join(
    BASE, "_analysis_20260625", "_place_alignment_manifest.json"
)
place_manifest_payload = json.load(open(lp(PLACE_MANIFEST_PATH), encoding="utf-8"))
place_path_manifest = place_manifest_payload.get("rows", [])
if len(place_path_manifest) != place_manifest_payload.get("expected_rows"):
    raise ValueError(
        "地名path manifest行数破損: "
        f"{len(place_path_manifest)} != {place_manifest_payload.get('expected_rows')}"
    )
if sum(row.get("count", 0) for row in place_path_manifest) \
        != place_manifest_payload.get("expected_instances"):
    raise ValueError("地名path manifest出現数破損")

place_surface_by_norm = {
    norm(surface): surface for surface in HTML_PLACE_ALIGNMENT_MANIFEST
}
place_path_aggregate = collections.Counter()
place_path_expected = {}
place_path_rows_by_path = collections.defaultdict(list)
for row_id, source_row in enumerate(place_path_manifest):
    row = dict(source_row)
    row["id"] = row_id
    row["path"] = row["path"].replace("\\", "/")
    if row["count"] != len(row.get("lines", [])):
        raise ValueError(
            f"地名path manifest count/lines不一致: {row['path']} {row['surface']}"
        )
    surface_key = norm(row["surface"])
    expected_key = place_canonical_decomp(row["expected"])
    previous_expected = place_path_expected.setdefault(surface_key, expected_key)
    if previous_expected != expected_key:
        raise ValueError(
            f"地名path manifest表層分解競合: {row['surface']} "
            f"{previous_expected} != {expected_key}"
        )
    row["pattern"] = build_place_html_pattern(row["surface"], row["expected"])
    place_path_aggregate[surface_key] += row["count"]
    place_path_rows_by_path[row["path"]].append(row)

expected_place_surface_keys = set(place_surface_by_norm)
if set(place_path_aggregate) != expected_place_surface_keys:
    raise ValueError(
        "地名path/surface manifest表層集合不一致: "
        f"path-only={sorted(set(place_path_aggregate)-expected_place_surface_keys)}, "
        f"surface-only={sorted(expected_place_surface_keys-set(place_path_aggregate))}"
    )
for surface_key, display_surface in place_surface_by_norm.items():
    expected_decomp, expected_count = HTML_PLACE_ALIGNMENT_MANIFEST[display_surface]
    if place_path_expected[surface_key] != place_canonical_decomp(expected_decomp):
        raise ValueError(f"地名path/surface manifest分解不一致: {display_surface}")
    if place_path_aggregate[surface_key] != expected_count:
        raise ValueError(
            f"地名path/surface manifest件数不一致: {display_surface} "
            f"{place_path_aggregate[surface_key]} != {expected_count}"
        )

def _roots(rendered):
    """Read the exact case-preserving typed output produced by the app."""
    signature = runtime_audit.signature_from_typed_parts(
        runtime_audit.rendered_typed_parts(rendered)
    )
    return [piece for piece, _is_ruby in signature[1]]


def app_batch(words, use_autofix, chunk=2500):
    """Render through the deployed overlay, optionally including autofix."""
    out = {}
    for s in range(0, len(words), chunk):
        b = words[s:s+chunk]
        source = "\n".join(" " + w + " " for w in b)
        if use_autofix:
            h = ov.autofix_render(
                source, ps, GL, pl, EFFECTIVE_GG, G2, FMT, DATA, "ruby",
                m.orchestrate_comprehensive_esperanto_text_replacement,
            )
        else:
            h = m.orchestrate_comprehensive_esperanto_text_replacement(
                source, ps, GL, pl, EFFECTIVE_GG, G2, FMT
            )
        ls = h.split("\n")
        if len(ls) != len(b):
            for w in b: out[w] = None
            continue
        for w, ln in zip(b, ls): out[w] = _roots(ln)
    return out

def parse_words(t):
    """Use the same case-preserving, DOTALL parser as the strict gate."""
    return runtime_audit.parse_corpus_words(t)

# ---- 全文書を走査 ----
docs = {}   # docname -> Counter((word, ref))
nfiles = 0
raw_ruby_total = parsed_ruby_total = 0
unparsed_ruby_docs = []
zero_ruby_documents = []
extracted_ruby_word_tokens = 0
eligible_token_total = 0
eligible_word_counts = collections.Counter()
excluded_surface_counts = collections.Counter()
corpus_reconstruction_failures = collections.Counter()
reviewed_observed_keys = set()
reviewed_observed_counts = collections.Counter()
place_path_observed_counts = collections.Counter()
place_html_observed_counts = collections.Counter()
place_manifest_scanned_paths = set()
for content_dir in CORPUS_CONTENT_DIRS:
    content_root = os.path.join(CORP, content_dir)
    if not os.path.isdir(content_root):
        continue
    for root, _dirs, files in os.walk(lp(content_root)):
        for f in files:
            if not f.lower().endswith((".html", ".htm")): continue
            nfiles += 1
            path = os.path.join(root, f)
            try: t = open(path, encoding="utf-8", errors="ignore").read()
            except Exception: continue
            rel_path = os.path.relpath(path, lp(CORP))
            rel_norm_path = rel_path.replace("\\", "/")
            for row in place_path_rows_by_path.get(rel_norm_path, []):
                observed = len(row["pattern"].findall(t))
                place_path_observed_counts[row["id"]] = observed
                display_surface = place_surface_by_norm[norm(row["surface"])]
                place_html_observed_counts[display_surface] += observed
                place_manifest_scanned_paths.add(rel_norm_path)
            raw_count = len(RAW_RUBY_OPEN_RE.findall(t))
            parsed_count = len(RUBY_RE.findall(t))
            raw_ruby_total += raw_count
            parsed_ruby_total += parsed_count
            if raw_count == 0:
                base_name = os.path.basename(path).lower()
                rel_norm = rel_path.replace("\\", "/").lower()
                if base_name.startswith("index"):
                    exclusion = "navigation/index"
                elif "gerda_malaperis_txt" in rel_norm or base_name.endswith("_txt.html"):
                    exclusion = "plain-source/Gerda"
                elif base_name == "vere_aux_fantazie_du-lingva.html":
                    exclusion = "plain-source/bilingual"
                else:
                    exclusion = "UNEXPECTED_zero_ruby"
                zero_ruby_documents.append({"path": rel_path, "exclusion": exclusion})
            if raw_count != parsed_count:
                unparsed_ruby_docs.append({
                    "path": rel_path,
                    "raw": raw_count,
                    "parsed": parsed_count,
                    "gap": raw_count - parsed_count,
                })
            pc = collections.Counter()
            for word, typed_parts in parse_words(t):
                extracted_ruby_word_tokens += 1
                nz = runtime_audit.canonical(word)
                signature = runtime_audit.signature_from_typed_parts(typed_parts)
                rp = [piece for piece, _is_ruby in signature[1]]
                if not rp:
                    excluded_surface_counts[(nz or word, "no_decomposition_parts")] += 1
                    continue
                if not is_evaluable_surface(nz):
                    excluded_surface_counts[(nz or word, "outside_esperanto_letters_hyphen_apostrophe")] += 1
                    continue
                refd = "/".join(rp)
                if signature[0] != nz:
                    corpus_reconstruction_failures[(nz, refd)] += 1
                    continue
                eligible_token_total += 1
                eligible_word_counts[nz] += 1
                pc[(nz, refd)] += 1
                review_key = (
                    norm(nz), normalized_decomp(refd), rel_norm_path,
                )
                if review_key in reviewed_index:
                    reviewed_observed_keys.add(review_key)
                    reviewed_observed_counts[(review_key[0], review_key[1])] += 1
            if pc:
                docs[os.path.relpath(path, lp(CORP))] = pc
print(f"走査ファイル {nfiles} / ルビ付き文書 {len(docs)}")
zero_ruby_tally = collections.Counter(e["exclusion"] for e in zero_ruby_documents)
print(
    "ruby 0 構造的除外 " + str(len(zero_ruby_documents)) + "文書: "
    + ", ".join(f"{k}={v}" for k, v in sorted(zero_ruby_tally.items()))
)
print(f"rubyパース {parsed_ruby_total}/{raw_ruby_total} / 未解析 {raw_ruby_total-parsed_ruby_total}")
print(
    f"ruby付き語抽出 {extracted_ruby_word_tokens} / 評価対象 {eligible_token_total} / "
    f"対象外 {sum(excluded_surface_counts.values())} / corpus再構成失敗 {sum(corpus_reconstruction_failures.values())}"
)
place_html_count_errors = []
place_path_results = []
for row in place_path_manifest:
    row_id = len(place_path_results)
    observed_count = place_path_observed_counts[row_id]
    result = {
        "path": row["path"].replace("\\", "/"),
        "lines": row.get("lines", []),
        "surface": row["surface"],
        "expected": row["expected"],
        "expected_count": row["count"],
        "observed_count": observed_count,
    }
    place_path_results.append(result)
    if observed_count != row["count"]:
        place_html_count_errors.append(result)
place_manifest_missing_paths = sorted(
    set(place_path_rows_by_path) - place_manifest_scanned_paths
)
print(
    f"地名HTML path manifest: exact-pattern観測 "
    f"{sum(place_path_observed_counts.values())}/"
    f"{sum(count for _expected, count in HTML_PLACE_ALIGNMENT_MANIFEST.values())}件 / "
    f"48 rows / 件数差 {len(place_html_count_errors)}rows / "
    f"未走査path {len(place_manifest_missing_paths)}"
)
for error in place_html_count_errors:
    print(
        f"  地名HTML件数NG {error['path']}:{error['lines']} {error['surface']}: "
        f"expected={error['expected_count']} observed={error['observed_count']}"
    )
if unparsed_ruby_docs:
    raise RuntimeError(
        "ruby構造に未解析タグがあるため、語根監査を中止します: "
        + json.dumps(unparsed_ruby_docs, ensure_ascii=False)
    )

uniq = sorted({nz for pc in docs.values() for (nz, _) in pc})
print(f"ユニーク注釈語 {len(uniq)} を baseline 分解中...")
base = app_batch(uniq, False)

# ---- autofix(実機挙動): user corrections + 自動第二パス ----
def is_strand(ap): return ap is not None and len(ap) >= 2 and len(ap[0]) == 1 and ap[0].lower() not in "aeiou"
stranded = [w for w in uniq if is_strand(base.get(w))]
effective = app_batch(uniq, True)
autofix_changed = [w for w in uniq if effective.get(w) != base.get(w)]
print(
    f"先頭子音1字孤立 {len(stranded)} 種 / "
    f"実機第二パスで変化 {len(autofix_changed)} 種"
)

# ---- 今回修正した地名74件: gold非依存のJA実機専用gate ----
place_manifest_instances = sum(
    count for _expected, count in HTML_PLACE_ALIGNMENT_MANIFEST.values()
)
if place_manifest_instances != 74:
    raise RuntimeError(
        f"地名manifest件数破損: {place_manifest_instances} (expected 74)"
    )
place_probe_specs = {
    surface: {
        "expected": expected,
        "html_count": count,
        "source": "html_manifest",
    }
    for surface, (expected, count) in HTML_PLACE_ALIGNMENT_MANIFEST.items()
}
place_probe_specs.update({
    surface: {
        "expected": expected,
        "html_count": 0,
        "source": "derivative_probe",
    }
    for surface, expected in PLACE_DERIVATIVE_PROBES.items()
})
place_rendered_parts = app_batch(list(place_probe_specs), True)
place_alignment_results = []
for surface, spec in place_probe_specs.items():
    parts = place_rendered_parts.get(surface)
    actual = "/".join(parts) if parts is not None else None
    expected_observable = place_expected_observable(spec["expected"])
    expected_canonical = place_canonical_decomp(expected_observable)
    actual_canonical = (
        place_canonical_decomp(actual) if actual is not None else None
    )
    place_alignment_results.append({
        "surface": surface,
        "expected": spec["expected"],
        "expected_observable": expected_observable,
        "app": actual,
        "html_count": spec["html_count"],
        "html_observed": (
            place_html_observed_counts[surface]
            if spec["source"] == "html_manifest" else None
        ),
        "source": spec["source"],
        "match": actual_canonical == expected_canonical,
    })
place_alignment_errors = [
    result for result in place_alignment_results if not result["match"]
]
print(
    f"地名JA実機gate: manifest {len(HTML_PLACE_ALIGNMENT_MANIFEST)}語形/"
    f"{place_manifest_instances}件 + 派生{len(PLACE_DERIVATIVE_PROBES)}語形 / "
    f"不一致 {len(place_alignment_errors)}語形・"
    f"{sum(result['html_count'] for result in place_alignment_errors)}件"
)
for result in place_alignment_errors:
    print(
        f"  地名NG {result['surface']}: expected={result['expected_observable']} "
        f"app={result['app']} count={result['html_count']}"
    )

def app_parts(nz, use_fix):
    return effective.get(nz) if use_fix else base.get(nz)

def app_decomp(nz, use_fix):
    """実機の最終分解(autofix適用後)。完全再構成できなければ None。"""
    ap = app_parts(nz, use_fix)
    if ap is None or "".join(ap) != nz: return None
    return "/".join(ap)

app_failure_words = {}
for w in uniq:
    ap = app_parts(w, True)
    if ap is None:
        app_failure_words[w] = {"reason": "app_returned_none", "parts": None}
    elif "".join(ap) != w:
        app_failure_words[w] = {
            "reason": "app_reconstruction_mismatch",
            "parts": ap,
            "reconstructed": "".join(ap),
        }
app_failure_token_total = sum(eligible_word_counts[w] for w in app_failure_words)
print(
    f"app評価不能 {len(app_failure_words)} 語 / {app_failure_token_total} tokens "
    "(必須gate=0)"
)

# ---- 文書別精度(baseline & autofix) ----
def perdoc(use_fix):
    rows = []; gt = gm = 0; agg = collections.Counter()
    agg_docs = collections.defaultdict(collections.Counter)
    for name, pc in docs.items():
        total = match = 0
        for (nz, refd), c in pc.items():
            ad = app_decomp(nz, use_fix)
            if ad is None: continue
            total += c
            if cuts(refd) == cuts(ad): match += c
            else:
                key = (nz, refd, ad)
                agg[key] += c
                agg_docs[key][name] += c
        if total:
            rows.append((name, total, match, round(match*100/total, 2)))
            gt += total; gm += match
    rows.sort(key=lambda r: r[3])
    return rows, gt, gm, agg, agg_docs

rows_b, gt_b, gm_b, _, _ = perdoc(False)
rows, gt, gm, agg_mis, agg_docs = perdoc(True)
denominator_gate = (
    extracted_ruby_word_tokens
    == eligible_token_total + sum(excluded_surface_counts.values()) + sum(corpus_reconstruction_failures.values())
    and app_failure_token_total == 0
    and gt == eligible_token_total
)

print(f"\n=== コーパス全体 境界一致 ===")
print(f"  baseline : {gm_b}/{gt_b}  ({round(gm_b*100/gt_b,3)}%)  不一致 {gt_b-gm_b}")
print(f"  autofix  : {gm}/{gt}  ({round(gm*100/gt,3)}%)  不一致 {gt-gm}   (実機=デプロイ状態)")
print(
    f"  分母gate : extracted={extracted_ruby_word_tokens}, eligible={eligible_token_total}, "
    f"app-evaluated={gt}, excluded={sum(excluded_surface_counts.values())}, "
    f"corpus-reconstruct-fail={sum(corpus_reconstruction_failures.values())}, "
    f"app-fail={app_failure_token_total} -> {'PASS' if denominator_gate else 'FAIL'}"
)
pcts = sorted(r[3] for r in rows)
print(f"\n=== 文書別(全{len(rows)}文書, autofix) ===")
print(f"  最小 {pcts[0]}% / 中央 {statistics.median(pcts)}% / 平均 {round(statistics.mean(pcts),2)}% / 最大 {pcts[-1]}%")
buckets_pct = collections.Counter()
for p in pcts:
    if p == 100: buckets_pct["100%"] += 1
    elif p >= 99.5: buckets_pct["99.5-99.99%"] += 1
    elif p >= 99: buckets_pct["99.0-99.49%"] += 1
    elif p >= 98: buckets_pct["98.0-98.99%"] += 1
    else: buckets_pct["<98%"] += 1
for k in ["100%", "99.5-99.99%", "99.0-99.49%", "98.0-98.99%", "<98%"]:
    if buckets_pct[k]: print(f"    {k:14s}: {buckets_pct[k]} 文書")
print(f"\n  下位12文書:")
for name, total, match, pct in rows[:12]:
    print(f"    {pct:6.2f}%  {match:5d}/{total:<5d}  {name[:58]}")

# ---- 不一致を gold で裁定 ----
def first_char_isolated(app):
    pp = [p for p in app.split("/") if p]
    return len(pp) >= 2 and len(pp[0]) == 1 and pp[0].lower() not in "aeiou"
def country_io(word, refd, appd):
    # 国名 -i/o 構造天井: gold/corpus = ROOT/i/o, app = ROOT/io
    return ("/i/o" in "/"+refd or refd.endswith("/i/o")) and "io" in appd

# 修正ガイドが明示的に許容・推奨する「学習用の粗い一体注釈」。
# goldとの不一致を機械的に欠陥扱いしない（ガイド §3.1, §6.3, 巻末補記）。
GUIDE_CORPUS_COARSE = {
    "sinmortigo", "sindevigo", "singarde",
    "anestezi", "meningito", "nitrato",
}
GUIDE_APP_COARSE = {"firmao"}

buckets = collections.defaultdict(list)
tally = collections.Counter()
reviewed_used_keys = set()
reviewed_mismatch_counts = collections.Counter()

def default_category(word, refd, appd, g, marker):
    ca, cr = cuts(appd), cuts(refd)
    if g is None:
        return "天井_先頭1字孤立(残)" if first_char_isolated(appd) else (
            "裁定不能_NOTINGOLD_app粗" if len(ca) < len(cr) else "裁定不能_NOTINGOLD_app細"
        )
    cg = cuts(g)
    # A ##偽分解 row is an intentional deep split for kanji allocation, not
    # authoritative evidence that the HTML ruby boundary is wrong.
    if marker:
        if cg == ca and cg != cr:
            return "gold偽分解_コーパス注釈一体"
        if cg == cr and cg != ca:
            return "gold偽分解_app注釈一体"
        return "gold偽分解_gold第三分解"
    if cg == ca and cg != cr:
        return (
            "ガイド準拠_コーパス粗分解(app/gold深分解)"
            if word in GUIDE_CORPUS_COARSE else
            "コーパス誤り_app正(gold一致)"
        )
    if cg == cr and cg != ca:
        if country_io(word, refd, appd):
            return "天井_国名-i/o"
        if word in GUIDE_APP_COARSE:
            return "ガイド準拠_app粗分解(corpus/gold深分解)"
        return "app誤り_真欠陥(gold=コーパス)"
    if cg == ca and cg == cr:
        return "謎(gold=両方)"
    return "gold第三分解_app寄り" if (len(cg ^ ca) <= len(cg ^ cr)) else "gold第三分解_コーパス寄り"

for (word, refd, appd), c in agg_mis.items():
    word_key = norm(word)
    corpus_key = normalized_decomp(refd)
    record = gold_records.get(word_key)
    g = record["decomp"] if record else None
    marker = record["marker"] if record else None
    fallback_cat = default_category(
        word_key, corpus_key, normalized_decomp(appd), g, marker
    )
    doc_counts = agg_docs[(word, refd, appd)]
    if sum(doc_counts.values()) != c:
        raise AssertionError(f"文書別不一致数が集計値と一致しません: {(word, refd, appd)}")

    # Split an aggregated word/decomposition by document.  This is essential:
    # a reviewed proper-name use of e.g. Linda must not suppress a future
    # ordinary adjective in a different document.
    by_category = collections.defaultdict(collections.Counter)
    review_reasons = collections.defaultdict(set)
    for path, n in doc_counts.items():
        path_key = path.replace("\\", "/")
        review_key = (word_key, corpus_key, path_key)
        review = reviewed_index.get(review_key)
        cat = review["category"] if review else fallback_cat
        by_category[cat][path] += n
        if review:
            reviewed_used_keys.add(review_key)
            reviewed_mismatch_counts[(word_key, corpus_key)] += n
            review_reasons[cat].add(review.get("reason", ""))

    for cat, cat_docs in by_category.items():
        count = sum(cat_docs.values())
        tally[cat] += count
        buckets[cat].append({
            "word": word,
            "corpus": refd,
            "app": appd,
            "gold": g,
            "gold_marker": marker,
            "count": count,
            "reviewed_context": cat.startswith("文脈準拠_") or cat.startswith("gold偽分解_公式"),
            "review_reasons": sorted(x for x in review_reasons[cat] if x),
            "documents": [
                {"path": path, "count": n}
                for path, n in cat_docs.most_common()
            ],
        })

print(f"\n=== 不一致 {gt-gm} の gold 裁定(インスタンス数 / ユニーク語数) ===")
for cat, n in tally.most_common():
    print(f"  {n:5d} inst / {len(buckets[cat]):4d} 語   {cat}")

reviewed_unobserved_keys = sorted(set(reviewed_index) - reviewed_observed_keys)
reviewed_resolved_keys = sorted(reviewed_observed_keys - reviewed_used_keys)
reviewed_count_mismatches = []
for key, expected in reviewed_expected_counts.items():
    actual = reviewed_observed_counts.get(key, 0)
    if actual != expected:
        reviewed_count_mismatches.append({
            "word": key[0], "corpus": key[1], "expected": expected, "actual": actual,
        })
print(
    f"人手レビュー照合: コーパス観測 {len(reviewed_observed_keys)}/"
    f"{len(reviewed_index)} 文書キー / 不一致裁定に使用 {len(reviewed_used_keys)} / "
    f"実機改善で解消 {len(reviewed_resolved_keys)} / "
    f"未観測 {len(reviewed_unobserved_keys)} / 件数差 {len(reviewed_count_mismatches)}"
)

print("\n--- 主要バケットの例(出現数上位8) ---")
for cat in ["コーパス誤り_app正(gold一致)", "app誤り_真欠陥(gold=コーパス)", "天井_国名-i/o", "天井_先頭1字孤立(残)"]:
    if cat not in buckets: continue
    print(f"\n[{cat}]  計{tally[cat]}inst / {len(buckets[cat])}語")
    for e in sorted(buckets[cat], key=lambda x: -x["count"])[:8]:
        print(f"   x{e['count']:<3d} {e['word']:18s} corpus={e['corpus']:22s} app={e['app']:22s} gold={e['gold']}")

# ---- 出力 ----
OUT = BASE + r"\_analysis_20260625\out"
def dump(name, lst): json.dump(sorted(lst, key=lambda x: -x["count"]), open(lp(OUT+name), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
dump(r"\_audit_corpus_errors.json", buckets.get("コーパス誤り_app正(gold一致)", []))
dump(r"\_audit_app_errors.json", buckets.get("app誤り_真欠陥(gold=コーパス)", []))
context_reviewed = [
    e for cat, entries in buckets.items() if cat.startswith("文脈準拠_")
    for e in entries
]
gold_fake = [
    e for cat, entries in buckets.items() if cat.startswith("gold偽分解_")
    for e in entries
]
dump(r"\_audit_context_reviewed.json", context_reviewed)
dump(r"\_audit_gold_fake.json", gold_fake)
dump(r"\_audit_guide_coarse.json",
     buckets.get("ガイド準拠_コーパス粗分解(app/gold深分解)", [])
     + buckets.get("ガイド準拠_app粗分解(corpus/gold深分解)", []))
ceil = buckets.get("天井_国名-i/o", []) + buckets.get("天井_先頭1字孤立(残)", []) \
     + buckets.get("gold第三分解_コーパス寄り", []) + buckets.get("gold第三分解_app寄り", [])
dump(r"\_audit_ceiling.json", ceil)
dump(r"\_audit_notingold_appfine.json", buckets.get("裁定不能_NOTINGOLD_app細", []))
dump(r"\_audit_notingold_appcoarse.json", buckets.get("裁定不能_NOTINGOLD_app粗", []))
dump(r"\_audit_excluded_surfaces.json", [
    {"surface": surface, "reason": reason, "count": count}
    for (surface, reason), count in excluded_surface_counts.items()
])
dump(r"\_audit_corpus_reconstruction_failures.json", [
    {"word": word, "corpus": corpus, "count": count}
    for (word, corpus), count in corpus_reconstruction_failures.items()
])
dump(r"\_audit_app_failures.json", [
    {"word": word, "count": eligible_word_counts[word], **failure}
    for word, failure in app_failure_words.items()
])
json.dump({
    "scope": "html_confirmed_place_decompositions_by_path_plus_derivatives",
    "html_manifest_rows": len(place_path_manifest),
    "html_manifest_surfaces": len(HTML_PLACE_ALIGNMENT_MANIFEST),
    "html_manifest_instances": place_manifest_instances,
    "html_manifest_scanned_paths": len(place_manifest_scanned_paths),
    "html_manifest_missing_paths": place_manifest_missing_paths,
    "derivative_probe_surfaces": len(PLACE_DERIVATIVE_PROBES),
    "mismatch_surfaces": len(place_alignment_errors),
    "mismatch_instances": sum(
        result["html_count"] for result in place_alignment_errors
    ),
    "html_count_mismatches": place_html_count_errors,
    "path_results": place_path_results,
    "gate": (
        not place_alignment_errors
        and not place_html_count_errors
        and not place_manifest_missing_paths
    ),
    "results": place_alignment_results,
}, open(lp(OUT + r"\_audit_place_alignment.json"), "w", encoding="utf-8"),
   ensure_ascii=False, indent=1)
json.dump({
    "scope": "all_169_content_html_documents",
    "reason": "These files are navigation pages or explicit plain-source variants, not annotation-bearing HTML. They are inventoried rather than silently omitted.",
    "tally": dict(zero_ruby_tally),
    "documents": sorted(zero_ruby_documents, key=lambda x: x["path"]),
}, open(lp(OUT + r"\_audit_zero_ruby_exclusions.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump({
    "configured_entries": len(reviewed_data.get("entries", [])),
    "configured_document_keys": len(reviewed_index),
    "observed_document_keys": len(reviewed_observed_keys),
    "used_document_keys": len(reviewed_used_keys),
    "resolved_by_runtime_document_keys": [
        {"word": w, "corpus": c, "path": p}
        for w, c, p in reviewed_resolved_keys
    ],
    "unobserved_document_keys": [
        {"word": w, "corpus": c, "path": p}
        for w, c, p in reviewed_unobserved_keys
    ],
    "count_mismatches": reviewed_count_mismatches,
}, open(lp(OUT + r"\_audit_review_coverage.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump([{"name": n, "total": t, "match": mt, "pct": p} for n, t, mt, p in rows],
          open(lp(OUT + r"\_audit_perdoc.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
exact_document_scope_gate = (
    nfiles == EXPECTED_CONTENT_FILES
    and len(docs) == EXPECTED_ANNOTATED_DOCUMENTS
    and len(zero_ruby_documents) == EXPECTED_ZERO_RUBY_DOCUMENTS
    and dict(zero_ruby_tally) == EXPECTED_ZERO_RUBY_TALLY
)
true_corpus_errors = buckets.get("コーパス誤り_app正(gold一致)", [])
true_app_errors = buckets.get("app誤り_真欠陥(gold=コーパス)", [])

json.dump({"scope": "all_ruby_bearing_words", "files": nfiles, "docs": len(docs), "tokens": gt, "match_autofix": gm,
           "pct_autofix": round(gm*100/gt, 3), "match_baseline": gm_b, "pct_baseline": round(gm_b*100/gt_b, 3),
           "raw_ruby": raw_ruby_total, "parsed_ruby": parsed_ruby_total,
           "unparsed_ruby": raw_ruby_total-parsed_ruby_total,
           "annotated_documents_coverage_scope": len(docs),
           "zero_ruby_documents_excluded": len(zero_ruby_documents),
           "zero_ruby_exclusion_tally": dict(zero_ruby_tally),
           "zero_ruby_unexpected": zero_ruby_tally.get("UNEXPECTED_zero_ruby", 0),
           "all_html_document_accounting_gate": nfiles == len(docs) + len(zero_ruby_documents),
           "extracted_ruby_word_tokens": extracted_ruby_word_tokens,
           "eligible_tokens": eligible_token_total,
           "excluded_surface_tokens": sum(excluded_surface_counts.values()),
           "excluded_surface_unique": len(excluded_surface_counts),
           "corpus_reconstruction_failure_tokens": sum(corpus_reconstruction_failures.values()),
           "corpus_reconstruction_failure_unique": len(corpus_reconstruction_failures),
           "app_evaluated_tokens": gt,
           "app_failure_tokens": app_failure_token_total,
           "app_failure_unique": len(app_failure_words),
           "denominator_gate": denominator_gate,
           "exact_document_scope_gate": exact_document_scope_gate,
           "place_alignment_manifest_instances": place_manifest_instances,
           "place_alignment_mismatch_instances": sum(
               result["html_count"] for result in place_alignment_errors
           ),
           "place_alignment_mismatch_surfaces": len(place_alignment_errors),
           "place_alignment_html_count_mismatches": len(place_html_count_errors),
           "place_alignment_missing_paths": len(place_manifest_missing_paths),
           "place_alignment_gate": (
               not place_alignment_errors
               and not place_html_count_errors
               and not place_manifest_missing_paths
           ),
           "reviewed_context_instances": sum(e["count"] for e in context_reviewed),
           "reviewed_context_unique_entries": len(context_reviewed),
           "gold_fake_instances": sum(e["count"] for e in gold_fake),
           "gold_fake_unique_entries": len(gold_fake),
           "true_corpus_error_instances": tally.get("コーパス誤り_app正(gold一致)", 0),
           "true_corpus_error_unique_entries": len(buckets.get("コーパス誤り_app正(gold一致)", [])),
           "true_app_error_instances": tally.get("app誤り_真欠陥(gold=コーパス)", 0),
           "true_app_error_unique_entries": len(buckets.get("app誤り_真欠陥(gold=コーパス)", [])),
           "review_observed_document_keys": len(reviewed_observed_keys),
           "review_used_document_keys": len(reviewed_used_keys),
           "review_resolved_document_keys": len(reviewed_resolved_keys),
           "review_unobserved_document_keys": len(reviewed_unobserved_keys),
           "review_count_mismatches": len(reviewed_count_mismatches),
           "tally": dict(tally)}, open(lp(OUT + r"\_audit_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(
    "\n保存: out/_audit_{summary,perdoc,corpus_errors,app_errors,"
    "context_reviewed,gold_fake,ceiling,place_alignment}.json"
)

gate_failures = []
if corpus_reconstruction_failures:
    gate_failures.append(f"corpus再構成失敗={sum(corpus_reconstruction_failures.values())}")
if app_failure_words:
    gate_failures.append(f"app評価不能={len(app_failure_words)}語/{app_failure_token_total}tokens")
if gt != eligible_token_total:
    gate_failures.append(f"評価分母不一致 eligible={eligible_token_total}, evaluated={gt}")
if not denominator_gate:
    gate_failures.append("抽出token会計不一致")
if nfiles != len(docs) + len(zero_ruby_documents):
    gate_failures.append(
        f"HTML文書会計不一致 files={nfiles}, annotated={len(docs)}, zero-ruby={len(zero_ruby_documents)}"
    )
if zero_ruby_tally.get("UNEXPECTED_zero_ruby", 0):
    gate_failures.append(f"未説明のruby 0文書={zero_ruby_tally['UNEXPECTED_zero_ruby']}")
if true_corpus_errors:
    gate_failures.append(
        "真のコーパス誤り="
        f"{sum(entry['count'] for entry in true_corpus_errors)}instances/"
        f"{len(true_corpus_errors)}entries"
    )
if true_app_errors:
    gate_failures.append(
        "真のapp誤り="
        f"{sum(entry['count'] for entry in true_app_errors)}instances/"
        f"{len(true_app_errors)}entries"
    )
if reviewed_unobserved_keys:
    gate_failures.append(
        f"人手レビュー対象がコーパスに未観測={len(reviewed_unobserved_keys)}文書キー"
    )
if reviewed_count_mismatches:
    gate_failures.append(f"人手レビュー件数差={len(reviewed_count_mismatches)}")
if place_alignment_errors:
    gate_failures.append(
        "地名JA実機不一致="
        f"{len(place_alignment_errors)}語形/"
        f"{sum(result['html_count'] for result in place_alignment_errors)}instances"
    )
if place_html_count_errors:
    gate_failures.append(f"地名HTML path manifest件数差={len(place_html_count_errors)}rows")
if place_manifest_missing_paths:
    gate_failures.append(f"地名HTML manifest未走査path={len(place_manifest_missing_paths)}")
if not exact_document_scope_gate:
    gate_failures.append(
        "HTML文書期待スコープ不一致 "
        f"files={nfiles}/{EXPECTED_CONTENT_FILES}, "
        f"annotated={len(docs)}/{EXPECTED_ANNOTATED_DOCUMENTS}, "
        f"zero-ruby={len(zero_ruby_documents)}/{EXPECTED_ZERO_RUBY_DOCUMENTS}, "
        f"zero-tally={dict(zero_ruby_tally)!r}/{EXPECTED_ZERO_RUBY_TALLY!r}"
    )
if gate_failures:
    raise RuntimeError("全数監査gate失敗: " + "; ".join(gate_failures))
