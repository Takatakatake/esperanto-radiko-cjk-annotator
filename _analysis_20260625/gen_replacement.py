# -*- coding: utf-8 -*-
"""
置換用JSON生成ロジックを、Streamlit生成ページ
「エスペラント文(漢字)置換用のJSONファイル生成ページ.py」の
ボタンブロック(行38-895)から忠実に移植したスタンドアロン版。
アプリ同梱モジュール(esp_replacement_json_make_module)の関数をそのまま再利用する。

generate(...) を呼ぶと combined_data(dict) を返す(JSONには書かない)。
呼び出し側で必要なら書き出す。
"""
import importlib
import re, json, sys, os, unicodedata
from io import StringIO

def lp(path):
    if path.startswith('\\\\?\\'): return path
    if path.startswith('\\\\'): return '\\\\?\\UNC' + path[1:]
    if len(path) > 2 and path[1] == ':': return '\\\\?\\' + path
    return path

def import_placeholders(filename):
    with open(lp(filename), 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]


def load_app_replacement_helper(app_module_dir):
    """Load the helper belonging to exactly one app, replacing stale cache.

    The three apps deliberately carry language-specific helper files.  A
    sequential JA/ZH/KO regeneration in one Python process must therefore not
    reuse whichever generic module name happened to be imported first.
    Keeping the standard module name preserves Windows multiprocessing support
    while the path check makes every language switch explicit and fail-closed.
    """
    module_name = "esp_replacement_json_make_module"
    module_dir = os.path.abspath(app_module_dir)
    expected_path = os.path.normcase(os.path.abspath(os.path.join(
        module_dir, module_name + ".py",
    )))
    if not os.path.isfile(expected_path):
        raise FileNotFoundError(expected_path)
    sys.path[:] = [
        module_dir,
        *[
            entry for entry in sys.path
            if os.path.normcase(os.path.abspath(entry or os.curdir))
            != os.path.normcase(module_dir)
        ],
    ]
    existing = sys.modules.get(module_name)
    existing_path = os.path.normcase(os.path.abspath(
        getattr(existing, "__file__", "") or os.curdir,
    ))
    if existing is not None and existing_path != expected_path:
        del sys.modules[module_name]
        existing = None
    module = existing or importlib.import_module(module_name)
    actual_path = os.path.normcase(os.path.abspath(module.__file__))
    if actual_path != expected_path:
        raise ImportError(
            f"wrong replacement helper loaded: expected {expected_path!r}, "
            f"got {actual_path!r}"
        )
    return module

# ---- 生成ページ 行38-44 の固定変数 (verbatim) ----
verb_suffix_2l={'as':'as', 'is':'is', 'os':'os', 'us':'us','at':'at','it':'it','ot':'ot', 'ad':'ad','iĝ':'iĝ','ig':'ig','ant':'ant','int':'int','ont':'ont'}
AN=[['dietan', '/diet/an/', '/diet/an'], ['afrikan', '/afrik/an/', '/afrik/an'], ['movadan', '/mov/ad/an/', '/mov/ad/an'], ['akcian', '/akci/an/', '/akci/an'], ['montaran', '/mont/ar/an/', '/mont/ar/an'], ['amerikan', '/amerik/an/', '/amerik/an'], ['regnan', '/regn/an/', '/regn/an'], ['dezertan', '/dezert/an/', '/dezert/an'], ['asocian', '/asoci/an/', '/asoci/an'], ['insulan', '/insul/an/', '/insul/an'], ['azian', '/azi/an/', '/azi/an'], ['ŝtatan', '/ŝtat/an/', '/ŝtat/an'], ['doman', '/dom/an/', '/dom/an'], ['montan', '/mont/an/', '/mont/an'], ['familian', '/famili/an/', '/famili/an'], ['urban', '/urb/an/', '/urb/an'], ['popolan', '/popol/an/', '/popol/an'], ['dekan', '/dekan/', '/dek/an'], ['partian', '/parti/an/', '/parti/an'], ['lokan', '/lok/an/', '/lok/an'], ['ŝipan', '/ŝip/an/', '/ŝip/an'], ['eklezian', '/eklezi/an/', '/eklezi/an'], ['landan', '/land/an/', '/land/an'], ['orientan', '/orient/an/', '/orient/an'], ['lernejan', '/lern/ej/an/', '/lern/ej/an'], ['enlandan', '/en/land/an/', '/en/land/an'], ['kalkan', '/kalkan/', '/kalk/an'], ['estraran', '/estr/ar/an/', '/estr/ar/an'], ['etnan', '/etn/an/', '/etn/an'], ['eŭropan', '/eŭrop/an/', '/eŭrop/an'], ['fazan', '/fazan/', '/faz/an'], ['polican', '/polic/an/', '/polic/an'], ['socian', '/soci/an/', '/soci/an'], ['societan', '/societ/an/', '/societ/an'], ['grupan', '/grup/an/', '/grup/an'], ['ligan', '/lig/an/', '/lig/an'], ['nacian', '/naci/an/', '/naci/an'], ['koran', '/koran/', '/kor/an'], ['religian', '/religi/an/', '/religi/an'], ['kuban', '/kub/an/', '/kub/an'], ['majoran', '/major/an/', '/major/an'], ['nordan', '/nord/an/', '/nord/an'], ['paran', 'paran', '/par/an'], ['parizan', '/pariz/an/', '/pariz/an'], ['parokan', '/parok/an/', '/parok/an'], ['podian', '/podi/an/', '/podi/an'], ['rusian', '/rus/i/an/', '/rus/ian'], ['satan', '/satan/', '/sat/an'], ['sektan', '/sekt/an/', '/sekt/an'], ['senatan', '/senat/an/', '/senat/an'], ['skisman', '/skism/an/', '/skism/an'], ['sudan', 'sudan', '/sud/an'], ['utopian', '/utopi/an/', '/utopi/an'], ['vilaĝan', '/vilaĝ/an/', '/vilaĝ/an'], ['arĝentan', '/arĝent/an/', '/arĝent/an'], ['seulan', '/seul/an/', '/seul/an'], ['bonlingvan', '/bon/lingv/an/', '/bon/lingv/an'], ['pragmatikan', '/pragmatik/an/', '/pragmatik/an'], ['teran', '/ter/an/', '/ter/an'], ['lingvan', '/lingv/an/', '/lingv/an'], ['samcelan', '/sam/cel/an/', '/sam/cel/an'], ['vroclavan', '/vroclav/an/', '/vroclav/an'], ['ursulan', '/ursul/an/', '/ursul/an'], ['mondan', '/mond/an/', '/mond/an'], ['kunhejman', '/kun/hejm/an/', '/kun/hejm/an'], ['vilaĝetan', '/vilaĝ/et/an/', '/vilaĝ/et/an'], ['specialvilaĝetan', '/special/vilaĝ/et/an/', '/special/vilaĝ/et/an'], ['stratan', '/strat/an/', '/strat/an'], ['maran', '/mar/an/', '/mar/an'], ['samstratan', '/sam/strat/an/', '/sam/strat/an']]
ON=[['duon', '/du/on/', '/du/on'], ['okon', '/ok/on/', '/ok/on'], ['nombron', '/nombr/on/', '/nombr/on'], ['patron', '/patron/', '/patr/on'], ['karbon', '/karbon/', '/karb/on'], ['ciklon', '/ciklon/', '/cikl/on'], ['aldon', '/al/don/', '/ald/on'], ['balon', '/balon/', '/bal/on'], ['baron', '/baron/', '/bar/on'], ['baston', '/baston/', '/bast/on'], ['magneton', '/magnet/on/', '/magnet/on'], ['beton', 'beton', '/bet/on'], ['bombon', '/bombon/', '/bomb/on'], ['breton', 'breton', '/bret/on'], ['burĝon', '/burĝon/', '/burĝ/on'], ['centon', '/cent/on/', '/cent/on'], ['milon', '/mil/on/', '/mil/on'], ['kanton', '/kanton/', '/kant/on'], ['citron', '/citron/', '/citr/on'], ['platon', 'platon', '/plat/on'], ['dekon', '/dek/on/', '/dek/on'], ['kvaron', '/kvar/on/', '/kvar/on'], ['kvinon', '/kvin/on/', '/kvin/on'], ['seson', '/ses/on/', '/ses/on'], ['trion', '/tri/on/', '/tri/on'], ['karton', '/karton/', '/kart/on'], ['foton', '/fot/on/', '/fot/on'], ['peron', '/peron/', '/per/on'], ['elektron', '/elektr/on/', '/elektr/on'], ['drakon', 'drakon', '/drak/on'], ['mondon', '/mon/don/', '/mond/on'], ['pension', '/pension/', '/pensi/on'], ['ordon', '/ordon/', '/ord/on'], ['eskadron', 'eskadron', '/eskadr/on'], ['senton', '/sen/ton/', '/sent/on'], ['eston', 'eston', '/est/on'], ['fanfaron', '/fanfaron/', '/fanfar/on'], ['feston', '/feston/', '/fest/on'], ['flegmon', 'flegmon', '/flegm/on'], ['fronton', '/fronton/', '/front/on'], ['galon', '/galon/', '/gal/on'], ['mason', '/mason/', '/mas/on'], ['helikon', 'helikon', '/helik/on'], ['kanon', '/kanon/', '/kan/on'], ['kapon', '/kapon/', '/kap/on'], ['kokon', '/kokon/', '/kok/on'], ['kolon', '/kolon/', '/kol/on'], ['komision', '/komision/', '/komisi/on'], ['salon', '/salon/', '/sal/on'], ['ponton', '/ponton/', '/pont/on'], ['koton', '/koton/', '/kot/on'], ['kripton', 'kripton', '/kript/on'], ['kupon', '/kupon/', '/kup/on'], ['lakon', 'lakon', '/lak/on'], ['ludon', '/lu/don/', '/lud/on'], ['melon', '/melon/', '/mel/on'], ['menton', '/menton/', '/ment/on'], ['milion', '/milion/', '/mili/on'], ['milionon', '/milion/on/', '/milion/on'], ['naŭon', '/naŭ/on/', '/naŭ/on'], ['violon', '/violon/', '/viol/on'], ['trombon', '/trombon/', '/tromb/on'], ['senson', '/sen/son/', '/sens/on'], ['sepon', '/sep/on/', '/sep/on'], ['skadron', 'skadron', '/skadr/on'], ['stadion', '/stadion/', '/stadi/on'], ['tetraon', 'tetraon', '/tetra/on'], ['timon', '/timon/', '/tim/on'], ['valon', 'valon', '/val/on']]
allowed_values = {-1, "-1", "ー１", "ー1", "-１", "－１", "－1"}
# 純粋な文法語尾。custom_stemmingでリテラル付加する。
# ``io/ia`` とその屈折形は、複数片の明示分解に現れた場合だけ
# 国名系の文法語尾として裸に保つ。単独の ``io/ia`` は相関語の
# 全体ルールで処理されるため、この集合では侵食しない。
_SPECIAL_GRAM_ENDINGS = {"io", "ia", "ion", "ian", "ioj", "iojn", "iaj", "iajn"}
_GRAM_ENDINGS = {
    "o", "oj", "on", "ojn", "a", "aj", "an", "ajn",
    "e", "en", "n", "j", "jn",
} | _SPECIAL_GRAM_ENDINGS
_AN_INFLECTION_ENDINGS = ("o", "oj", "on", "ojn", "a", "aj", "an", "ajn", "e", "en")
_ALWAYS_BARE_SETTING_PIECES = {
    "o", "a", "e", "i", "n", "j", "jn",
}
# as/is/os/us はガイドの標準どおり独立rubyにする。裸の終端語尾は
# 不定法/\u547d令法 i/u と名詞・形容詞・副詞系だけである。
_TERMINAL_BARE_SETTING_PIECES = (_GRAM_ENDINGS - _SPECIAL_GRAM_ENDINGS) | {"u", "i"}
_LITERAL_SETTING_PUNCTUATION = frozenset("-'\"’‘“”.,!?;:()[]")
_FINITE_VERB_ENDINGS = frozenset({"as", "is", "os", "us"})
_TYPED_ROLES_PREFIX = "typed_roles:"
_CONTEXT_ANNOTATION_PREFIX = "context_annotation:"
_AUTHORED_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_RT_CONTENT_RE = re.compile(
    r"(<rt\b[^>]*>).*?(</rt>)", re.IGNORECASE | re.DOTALL,
)


class AmbiguousCasefoldError(ValueError):
    """An explicit component has multiple case-insensitive interpretations."""


def restore_authored_rt_breaks(rendered, authored_meaning):
    """Restore trusted ``<br>`` markup after width-class calculation.

    ``output_format`` may insert an automatic break at a character position.
    Feeding it an already marked-up gloss can therefore split the tag itself
    (``<b<br>r>`` or ``<br<br>>``).  Callers measure the tag-free visible text,
    then restore the exact curated rt content once.
    """
    authored_meaning = str(authored_meaning)
    if _AUTHORED_BR_RE.search(authored_meaning) is None:
        return rendered
    replaced, count = _RT_CONTENT_RE.subn(
        lambda match: match.group(1) + authored_meaning + match.group(2),
        str(rendered),
    )
    if count != 1:
        raise ValueError("cannot restore authored <br>: rendered output has no unique rt")
    return replaced


def setting_piece_is_bare(piece, index, total):
    """Whether an explicitly split setting piece stays unannotated.

    One-letter linking/inflection pieces remain bare even inside a word
    (``elektr/o/n``, ``merit/o/krat/i``).  Ambiguous two-letter pieces such as
    ``an`` and ``on`` are bare only word-finally; internally they are lexical
    affixes and must pass through the atomic dictionary renderer.
    """
    piece_lookup = piece.casefold()
    return (
        bool(piece)
        and all(character in _LITERAL_SETTING_PUNCTUATION for character in piece)
    ) or (
        piece_lookup in _ALWAYS_BARE_SETTING_PIECES
        # ``io/ia`` and their inflected country-name endings are grammatical
        # only after an already explicit root (Brazil/io, Azi/ian).  Treating
        # a one-piece ``ion``/``iaj`` setting as a bare ending erases genuine
        # lexical/correlative rubies, so position zero is intentionally not
        # licensed here.
        or (piece_lookup in _SPECIAL_GRAM_ENDINGS and index > 0)
        or (index == total - 1 and piece_lookup in _TERMINAL_BARE_SETTING_PIECES)
    )


def extract_typed_roles(actions, part_count):
    """Remove and validate the optional exact R/L role signature.

    The normal slash notation records boundaries but cannot distinguish an
    annotated ``an/on/en`` root from the same spelling used as a literal
    grammatical ending.  Reviewed corpus-exact settings therefore carry one
    role letter per explicit piece.  ``R`` forces a ruby and ``L`` preserves
    literal text; all ordinary settings continue through the historical
    heuristic path.
    """
    markers = [a for a in actions if isinstance(a, str) and a.startswith(_TYPED_ROLES_PREFIX)]
    if not markers:
        return None
    if len(markers) != 1:
        raise ValueError("setting must contain at most one typed_roles marker")
    marker = markers[0]
    roles = marker[len(_TYPED_ROLES_PREFIX):]
    if len(roles) != part_count or any(role not in "RL" for role in roles):
        raise ValueError(f"invalid typed_roles {roles!r} for {part_count} setting pieces")
    actions.remove(marker)
    return roles


def extract_context_annotation(actions):
    """Remove and return one reserved word_anno key for a setting stem."""
    markers = [
        a for a in actions
        if isinstance(a, str) and a.startswith(_CONTEXT_ANNOTATION_PREFIX)
    ]
    if not markers:
        return None
    if len(markers) != 1:
        raise ValueError("setting must contain at most one context_annotation marker")
    marker = markers[0]
    key = marker[len(_CONTEXT_ANNOTATION_PREFIX):]
    if not key:
        raise ValueError("context_annotation key must not be empty")
    actions.remove(marker)
    return key


def setting_effective_part_total(parts, actions):
    """Include an appended suffix slot when classifying a stem-final piece."""
    return len(parts) + (1 if any(action != "ne" for action in actions) else 0)


def setting_suffix_rules_need_boundary(parts, actions, explicit_boundary=False):
    """Generated endings after ambiguous ``an/on`` stems are whole words.

    Boundarying keeps the corrected internal affix visible in ``kunhejmano``
    without allowing a generated substring such as ``ar/an/a`` to consume the
    middle of the proper name ``Taranaki``.  An explicit ``word_boundary``
    setting applies the same safety policy to every generated sibling form;
    otherwise a confirmed whole-word correction such as ``fer/o`` could still
    leak through its generated ``fer/i`` rule into the unrelated ``ofer/i``.
    """
    return bool(
        explicit_boundary
        or (parts and parts[-1] in {"an", "on"} and any(a != "ne" for a in actions))
    )


def lookup_word_anno_exact_first(word_anno, word_anno_nosl, key):
    """Prefer an exact decomposition key over the lossy slashless index."""
    exact = word_anno.get(key) if word_anno is not None else None
    if exact is not None:
        return exact
    return word_anno_nosl.get(key.replace('/', '')) if word_anno_nosl is not None else None


def lookup_typed_ruby_annotation(word_anno, surface, index, piece):
    """Resolve one forced-ruby piece without guessing across case homographs.

    A reserved per-surface annotation has highest priority (``kaj`` as wharf
    inside ``kajo``).  Otherwise an exact plain annotation for the component
    may be reused (``Aŭdu`` and ``ChatGPT``).  A present but malformed or
    multipart entry is rejected fail-closed; casefold fallback is deliberately
    forbidden because proper names can coexist with lowercase grammar roots.
    """
    if word_anno is None:
        return None
    context_key = f"@typed:{surface}:{index}"
    context_pairs = word_anno.get(context_key)
    if context_pairs is not None:
        if (
            len(context_pairs) != 1
            or context_pairs[0][0].replace('/', '') != piece
        ):
            raise ValueError(
                f"invalid typed context annotation {context_key!r} "
                f"for piece {piece!r}"
            )
        return context_pairs
    plain_pairs = word_anno.get(piece)
    if plain_pairs is not None:
        if (
            len(plain_pairs) != 1
            or plain_pairs[0][0].replace('/', '') != piece
        ):
            raise ValueError(
                f"invalid exact word annotation {piece!r} for typed ruby "
                f"{surface!r}[{index}]"
            )
        return plain_pairs
    return None


def build_unique_casefold_index(mapping, ambiguous_out=None):
    """Index only case-insensitive keys whose payload is unambiguous.

    Exact spelling always has priority.  This fallback is for explicitly
    decomposed, case-sensitive corpus forms whose component is capitalized
    (``Sekretari``) while the shared lexical dictionary stores ``sekretari``.
    Homographs with genuinely different case-specific meanings (``Tang`` vs
    ``tang``) are omitted instead of being guessed.
    """
    index = {}
    ambiguous = set()
    for key, value in mapping.items():
        folded = str(key).casefold()
        if folded in ambiguous:
            continue
        if folded in index and index[folded] != value:
            index.pop(folded, None)
            ambiguous.add(folded)
            if ambiguous_out is not None:
                ambiguous_out.add(folded)
            continue
        index[folded] = value
    return index


def lookup_unique_casefold(index, ambiguous, key, source_label):
    """Return an unambiguous casefold fallback or fail closed on collision."""
    folded = str(key).casefold()
    if folded in ambiguous:
        raise AmbiguousCasefoldError(
            f"ambiguous {source_label} casefold value for explicit piece {key!r}"
        )
    return index.get(folded)


def explicit_piece_allows_casefold_fallback(piece):
    """Limit lexical casefold borrowing to source-cased components.

    This supports ``Sekretari`` -> dictionary ``sekretari`` while preventing
    lowercase roots such as ``uk``/``ttt`` from borrowing the semantics of
    uppercase abbreviations ``UK``/``TTT``.  Lowercase pieces continue through
    their exact CSV/safe-replacement path, preserving established behaviour.
    """
    return any(character.isupper() for character in str(piece))


def resolve_elided_article_meaning(word_anno, word_anno_nosl, csv_root_map):
    """Return the rendering payload for ``l'``/``l’``, when available.

    Ruby annotation dictionaries contain ``la`` and therefore render the
    guide-mandated whole article ruby.  The Kanji-only dictionary deliberately
    omits grammatical function words such as ``la``; in that mode ``None``
    means that no article replacement rule should be emitted, leaving the
    original spelling visible instead of aborting the whole generation.
    """
    la_annotation = lookup_word_anno_exact_first(
        word_anno, word_anno_nosl, "la",
    )
    if la_annotation is not None and len(la_annotation) == 1:
        return la_annotation[0][1]
    return csv_root_map.get("la")


def iter_word_anno_an_inflections(word_anno):
    """Yield safe ``-an-`` inflections derived from curated per-word decompositions.

    ``word_anno`` is the language-specific gloss table, but its keys are the shared
    morphological source of truth.  A key ending in a *separate* ``/an`` segment
    (for example ``bon/lingv/an``) licenses the full nominal/adjectival/adverbial
    paradigm.  A generated surface form is skipped when word_anno already records
    a different decomposition for that spelling.  If the *stem spelling itself*
    is ambiguous (for example ``sud/an`` versus the country root ``sudan``), the
    entire automatic paradigm is skipped because generated capitalized variants
    would otherwise corrupt ``Sudano``, ``Sudana`` and related country forms.

    Yields ``(surface, stem_key, ending)`` in deterministic order.  The helper is
    intentionally independent of HTML rendering so it can be regression-tested.
    """
    if not isinstance(word_anno, dict):
        return

    decomps_by_surface = {}
    an_stems = set()
    for raw_key in word_anno:
        if not isinstance(raw_key, str):
            continue
        pieces = tuple(p for p in raw_key.strip("/").split("/") if p)
        if not pieces:
            continue
        canonical = "/".join(pieces)
        surface = "".join(pieces)
        decomps_by_surface.setdefault(surface, set()).add(canonical)
        if len(pieces) >= 2 and pieces[-1] == "an":
            an_stems.add(pieces)

    for pieces in sorted(an_stems, key=lambda p: ("".join(p), p)):
        stem_key = "/".join(pieces)
        stem_surface = "".join(pieces)
        stem_decomps = decomps_by_surface.get(stem_surface, set())
        if stem_decomps != {stem_key}:
            continue
        # A hyphenated stem can hide the same ambiguity in its final component:
        # ``sud-sud/an`` has no atomic *whole-word* rival, but its last component
        # spells the atomic country root ``sudan``.  Expanding it would overwrite
        # the established ``sud/sudan/a`` analysis with ``sud-sud/an/a``.
        final_hyphen_component = stem_surface.rsplit("-", 1)[-1]
        component_decomps = decomps_by_surface.get(final_hyphen_component, set())
        pre_an_surface = "".join(pieces[:-1])
        pre_an_decomps = decomps_by_surface.get(pre_an_surface, set())
        pre_an_is_atomic = pre_an_surface in pre_an_decomps
        if (
            final_hyphen_component != stem_surface
            and final_hyphen_component in component_decomps
            and not pre_an_is_atomic
        ):
            continue
        for ending in _AN_INFLECTION_ENDINGS:
            surface = stem_surface + ending
            desired = stem_key + "/" + ending
            existing = decomps_by_surface.get(surface)
            if existing and existing != {desired}:
                continue
            yield surface, stem_key, ending


def enforce_boundary_only_surfaces(replacements, surfaces):
    """Keep complete generated word forms from becoming substring rules.

    A curated custom/user rule is processed after the data-driven ``-an``
    expansion and may therefore re-register the same surface as an unbounded
    exact rule.  Move that later, higher-authority rendering onto the already
    bounded key instead of discarding it.  This makes the boundary policy
    independent of source ordering while preserving the curated decomposition.
    """
    for surface in surfaces:
        naked = replacements.pop(surface, None)
        if naked is not None:
            replacements[' ' + surface + ' '] = [
                ' ' + naked[0] + ' ', naked[1],
            ]


def split_trailing_sentence_punctuation(root, meaning):
    """Separate sentence marks and Esperanto final elision from a ruby.

    The HTML guide requires sentence punctuation outside ``rb``/``rt``.  Dots
    are deliberately excluded because dictionary abbreviations such as
    ``k.t.p.`` and ``ekz.`` keep their dots inside the atomic ruby.  A final
    apostrophe replaces a grammatical vowel (``dank'``, ``l'``) and is likewise
    visible literal notation, never part of the annotated lexical base.
    """
    # The elided definite article is conventionally one grammatical ruby
    # (l'); its apostrophe is not a dropped ending of the annotated stem.
    if str(root).casefold() in {"l'", "l’"}:
        return root, meaning, ""
    match = re.search(r"[!?\u0027\u2019]+$", root)
    if match is None:
        return root, meaning, ""
    suffix = match.group(0)
    bare_root = root[:-len(suffix)]
    bare_meaning = str(meaning)
    for mark in reversed(suffix):
        if bare_meaning.endswith(mark):
            bare_meaning = bare_meaning[:-1]
    return bare_root, bare_meaning, suffix


def split_annotated_piece_punctuation(root, meaning):
    """Apply punctuation policy without breaking a quoted multiword entity.

    A final apostrophe on an ordinary Esperanto word is poetic vowel elision
    and stays outside its lexical ruby.  A whitespace-containing piece in the
    explicit annotation dictionary is instead an authoritative entity label;
    the Kyoto corpus has ``La Ŝodfon'``/``La Ŝodfon’`` as complete rb
    text, so its closing mark belongs to that one annotated unit.
    """
    root = str(root)
    if any(character.isspace() for character in root) and root.endswith(("'", "’")):
        return root, str(meaning), ""
    return split_trailing_sentence_punctuation(root, meaning)


def split_typed_ruby_piece_punctuation(root, meaning):
    """Keep every authored character inside an explicitly typed ``R`` span.

    The ordinary punctuation policy correctly renders poetic elision as
    ``<ruby>dank</ruby>'``.  A reviewed typed signature is stronger evidence:
    when it marks the complete piece ``klak'`` as ``R``, the apostrophe is part
    of that exact ruby span and must not be inferred back into a literal suffix.
    """
    return str(root), str(meaning), ""


def stable_replacement_sort_key(rule, is_important):
    """Language-independent ordering for global rules, including exact ties."""
    return (rule[2], len(rule[0]), is_important(rule[0]), rule[0])


def guarded_boundary_priorities(base_priority):
    """Order bounded split > naked guard > equal-length lexical rules."""
    return base_priority + 2, base_priority + 1


def confirmed_priority_for_stem(stem_nosl):
    """Put a confirmed rule above +5000 peers but below the next length tier."""
    return len(stem_nosl) * 10000 + 9000


def suffix_priority_length(suffix):
    """Count morphological letters, excluding boundary-padding spaces."""
    return len(str(suffix).strip())


def stable_dedupe_first_wins(rules):
    """Remove duplicate old keys without changing the winning rule order."""
    deduped = []
    seen = set()
    for rule in rules:
        old = rule[0]
        if old in seen:
            continue
        seen.add(old)
        deduped.append(rule)
    return deduped


def normalize_esperanto_surface_notation(value):
    """Normalize case plus Esperanto Hat/X notation for identity checks."""
    normalized = str(value).casefold()
    for source, target in (
        ("c^", "ĉ"), ("g^", "ĝ"), ("h^", "ĥ"),
        ("j^", "ĵ"), ("s^", "ŝ"), ("u^", "ŭ"),
        ("cx", "ĉ"), ("gx", "ĝ"), ("hx", "ĥ"),
        ("jx", "ĵ"), ("sx", "ŝ"), ("ux", "ŭ"),
    ):
        normalized = normalized.replace(source, target)
    return normalized


def normalize_esperanto_surface_notation_case_preserving(value):
    """Normalize NFC and Esperanto Hat/X notation without folding case."""
    normalized = unicodedata.normalize("NFC", str(value))
    lower_map = {
        "c": "ĉ", "g": "ĝ", "h": "ĥ", "j": "ĵ", "s": "ŝ", "u": "ŭ",
    }

    def replace_notation(match):
        source = match.group(1)
        converted = lower_map[source.lower()]
        return converted.upper() if source.isupper() else converted

    return re.sub(
        r"([cghjsuCGHJSU])(?:\^|[xX])",
        replace_notation,
        normalized,
    )


def correction_removal_identity(value, case_sensitive):
    """Normalize an old setting at the correction's intended case scope.

    A case-sensitive proper-name correction such as ``Sin`` must replace a
    stale ``Sin`` row without deleting the distinct grammatical ``si/n`` row.
    Ordinary corrections retain the historical case-insensitive identity.
    """
    slashless = normalize_esperanto_surface_notation_case_preserving(
        str(value).replace('/', '').strip(),
    )
    if case_sensitive:
        return slashless
    return normalize_esperanto_surface_notation(slashless)


def filter_settings_for_correction_removals(
    settings, exact_case_removals, casefold_removals,
    exact_only_exact_case_removals=None,
    exact_only_casefold_removals=None,
):
    """Remove stale settings without erasing unrelated productive paradigms.

    A productive correction replaces every old row with the same stem.  An
    ``exact_only`` correction is narrower: it owns only the bare surface.  If
    an old same-spelling row generates suffixed siblings but not the bare stem
    (for example ``teren`` + ``o/oj/on/...``), preserve that row.  If it also
    contains ``ne``, remove only that bare-stem action and retain its siblings.
    """
    exact_only_exact_case_removals = set(
        exact_only_exact_case_removals or (),
    )
    exact_only_casefold_removals = set(
        exact_only_casefold_removals or (),
    )
    kept = []
    removed = 0
    for entry in settings:
        if (
            isinstance(entry, list)
            and len(entry) == 3
            and isinstance(entry[0], str)
        ):
            exact_identity = correction_removal_identity(entry[0], True)
            folded_identity = correction_removal_identity(entry[0], False)
            broad_match = (
                exact_identity in exact_case_removals
                or folded_identity in casefold_removals
            )
            exact_only_match = (
                exact_identity in exact_only_exact_case_removals
                or folded_identity in exact_only_casefold_removals
            )
            if broad_match:
                removed += 1
                continue
            if exact_only_match and "ne" in entry[2]:
                # ``atomic_no_split`` and ``boundary_noop_guard`` describe the
                # removed bare-stem action.  Other metadata continues to scope
                # the surviving productive suffix rules.
                actions = [
                    action for action in entry[2]
                    if action not in {
                        "ne", "atomic_no_split", "boundary_noop_guard",
                    }
                ]
                semantic_actions = [
                    action for action in actions
                    if action not in {"word_boundary", "case_sensitive"}
                    and not str(action).startswith(_TYPED_ROLES_PREFIX)
                    and not str(action).startswith(_CONTEXT_ANNOTATION_PREFIX)
                ]
                removed += 1
                if semantic_actions:
                    kept.append([entry[0], entry[1], actions])
                continue
        kept.append(entry)
    return kept, removed


# ハイフン直後のエスペラント文字を大文字化(固有名詞 Abu-Dabi 等。実テキストは各部大文字)
def _cap_after_hyphen(s, source_in_rt=False):
    # Rendered replacements may put the next component inside a ruby tag.  In
    # that case capitalize only rb's first visible letter; rt/gloss text must
    # retain its original language-specific casing.
    letters = r'a-zĉĝĥĵŝŭ'
    if source_in_rt:
        s = re.sub(
            r'-(<ruby>.*?<rt[^>]*>)([' + letters + r'])',
            lambda m: '-' + m.group(1) + m.group(2).upper(),
            s,
        )
        return re.sub(r'-([' + letters + r'])', lambda m: '-' + m.group(1).upper(), s)
    s = re.sub(
        r'-(<ruby>)([' + letters + r'])',
        lambda m: '-' + m.group(1) + m.group(2).upper(),
        s,
    )
    return re.sub(r'-([' + letters + r'])', lambda m: '-' + m.group(1).upper(), s)
suffix_2char_roots=['ad', 'ag', 'am', 'ar', 'as', 'at', 'av', 'di', 'ec', 'eg', 'ej', 'em', 'er', 'et', 'id', 'ig', 'il', 'in', 'ir', 'is', 'it', 'lu', 'nj', 'op', 'or', 'os', 'ot', 'ov', 'pi', 'te', 'uj', 'ul', 'um', 'us', 'uz','ĝu','aĵ','iĝ','aĉ','aĝ','ŝu','eĥ']
prefix_2char_roots=['al', 'am', 'av', 'bo', 'di', 'du', 'ek', 'el', 'en', 'fi', 'ge', 'ir', 'lu', 'ne', 'ok', 'or', 'ov', 'pi', 're', 'te', 'uz','ĝu','aĉ','aĝ','ŝu','eĥ']
standalone_2char_roots=['al', 'ci', 'da', 'de', 'di', 'do', 'du', 'el', 'en', 'fi', 'ha', 'he', 'ho', 'ia', 'ie', 'io', 'iu', 'ja', 'je', 'ju','ke', 'la', 'li', 'mi', 'ne', 'ni', 'nu', 'ok', 'ol', 'po', 'se', 'si', 've', 'vi','ŭa','aŭ','ĉe','ĝi','ŝi','ĉu','eĉ','ĉi']

# An explicit hyphen is a morphological boundary.  Register reusable component
# rules instead of pinning every observed compound (re-agi, ek-malsan-iĝis,
# don-it-aĵo, unu-op-ulo) as a whole word.  The small lexical supplement covers
# productive/technical prefixes and short roots attested with that notation;
# longer proper-name compounds remain case-sensitive exact data.
_HYPHEN_PREFIX_COMPONENT_ROOTS = frozenset(prefix_2char_roots) | {
    "ag", "anti", "ar", "go", "mikro", "narko", "no",
}
_HYPHEN_INFIX_COMPONENT_ROOTS = frozenset(suffix_2char_roots) | {
    "ant", "int", "ont",
}
_HYPHEN_COMPOSITE_PREFIXES = {
    "duon-": ("du", "on"),
    "kvaron-": ("kvar", "on"),
    "unu-op-": ("unu", "op"),
}


def generate(app_module_dir, data_dir, csv_path, stemming_json_path,
             user_repl_json_path, estem_path, rootlist_path,
    format_type='HTML格式_Ruby文字_大小调整', word_anno=None,
             use_parallel=False, num_processes=4, important_stems=None):
    import pandas as pd
    helper = load_app_replacement_helper(app_module_dir)
    convert_to_circumflex = helper.convert_to_circumflex
    output_format = helper.output_format
    capitalize_ruby_and_rt = helper.capitalize_ruby_and_rt
    remove_redundant_ruby_if_identical = helper.remove_redundant_ruby_if_identical
    mod_safe_replace = helper.safe_replace
    parallel_build_pre_replacements_dict = helper.parallel_build_pre_replacements_dict
    # safe_replace は (old,new,placeholder) を使う版が必要。モジュールの safe_replace は3要素対応。
    safe_replace = mod_safe_replace
    _LATIN = re.compile(r'^[a-zĉĝĥĵŝŭ!\-]+$')

    imported_placeholders_for_global_replacement = import_placeholders(os.path.join(data_dir, 'placeholders_global.txt'))
    imported_placeholders_for_2char_replacement = import_placeholders(os.path.join(data_dir, 'placeholders_2char.txt'))
    imported_placeholders_for_local_replacement = import_placeholders(os.path.join(data_dir, 'placeholders_local.txt'))

    with open(lp(os.path.join(data_dir, 'char_widths.json')), 'r', encoding='utf-8') as fp:
        char_widths_dict = json.load(fp)

    def dictionary_output(
        root, meaning, *, authoritative_annotation=False,
        typed_atomic_piece=False,
    ):
        splitter = (
            split_typed_ruby_piece_punctuation
            if typed_atomic_piece
            else split_annotated_piece_punctuation
            if authoritative_annotation
            else split_trailing_sentence_punctuation
        )
        bare_root, bare_meaning, punctuation = splitter(str(root), str(meaning))
        has_authored_break = _AUTHORED_BR_RE.search(str(bare_meaning)) is not None
        is_kanji_format = "汉字替换" in str(format_type)
        width_meaning = (
            _AUTHORED_BR_RE.sub("", str(bare_meaning))
            if has_authored_break and not is_kanji_format
            else bare_meaning
        )
        rendered = output_format(
            bare_root, width_meaning, format_type, char_widths_dict,
        )
        if has_authored_break and not is_kanji_format:
            rendered = restore_authored_rt_breaks(rendered, bare_meaning)
        return rendered + punctuation

    # CSV 読み込み (デフォルト使用パス相当)
    with open(lp(csv_path), 'r', encoding='utf-8') as file:
        text = file.read()
    converted_text = convert_to_circumflex(text)
    csv_buffer = StringIO(converted_text)
    CSV_data_imported = pd.read_csv(csv_buffer, encoding='utf-8', usecols=[0, 1])
    # piece-atomic用: 語根→訳の直引き辞書(2字語根も含む。設定分解片の解決に使用)
    _csv_root_map = {}
    for _rr, _gg in zip(CSV_data_imported.iloc[:,0], CSV_data_imported.iloc[:,1]):
        _rrs = str(_rr).strip(); _ggs = str(_gg).strip()
        if _rrs and _ggs and not _rrs.startswith('#'):
            _csv_root_map.setdefault(_rrs, _ggs)
    _csv_root_map_casefold_ambiguous = set()
    _csv_root_map_casefold = build_unique_casefold_index(
        _csv_root_map, _csv_root_map_casefold_ambiguous,
    )

    # 語根分解法JSON / 置換後文字列JSON
    with open(lp(stemming_json_path), 'r', encoding='utf-8') as g:
        custom_stemming_setting_list = json.load(g)
    with open(lp(user_repl_json_path), 'r', encoding='utf-8') as g:
        user_replacement_item_setting_list = json.load(g)

    # ===== ボタンブロック (行360〜) =====
    with open(lp(estem_path), 'r', encoding='utf-8') as g:
        E_stem_with_Part_Of_Speech_list = json.load(g)

    temporary_replacements_dict = {}
    with open(lp(rootlist_path), 'r', encoding='utf-8') as file:
        for E_root in file.readlines():
            E_root = E_root.strip()
            # Sentence-punctuation forms must fall through to their bare root
            # when a language CSV lacks the duplicated punctuated entry (pat!
            # was absent only in JA).  CSV entries below re-add them uniformly.
            if not E_root.isdigit() and not E_root.endswith(("!", "?")):
                temporary_replacements_dict[E_root] = [E_root, len(E_root)]

    for _, (E_root, hanzi_or_meaning) in CSV_data_imported.iterrows():
        if pd.notna(E_root) and pd.notna(hanzi_or_meaning) and '#' not in E_root and (E_root != '') and (hanzi_or_meaning != ''):
            temporary_replacements_dict[E_root] = [dictionary_output(E_root, hanzi_or_meaning), len(E_root)]

    temporary_replacements_list_1 = []
    for old, new in temporary_replacements_dict.items():
        temporary_replacements_list_1.append((old, new[0], new[1]))
    temporary_replacements_list_2 = sorted(temporary_replacements_list_1, key=lambda x: x[2], reverse=True)

    temporary_replacements_list_final = []
    for kk in range(len(temporary_replacements_list_2)):
        temporary_replacements_list_final.append([temporary_replacements_list_2[kk][0], temporary_replacements_list_2[kk][1], imported_placeholders_for_global_replacement[kk]])

    # word_anno はスラッシュ除去形でも引けるようにする(E_stemと注釈版でスラッシュ位置が
    # 食い違う語のため。出力は後段でどのみち'/'除去されるので、注釈版の分解を採用して安全)。
    word_anno_nosl = None
    word_anno_casefold = None
    word_anno_casefold_ambiguous = set()
    if word_anno is not None:
        word_anno_nosl = {}
        for _k, _v in word_anno.items():
            word_anno_nosl.setdefault(_k.replace('/', ''), _v)
        word_anno_casefold = build_unique_casefold_index(
            word_anno, word_anno_casefold_ambiguous,
        )

    # per-word注釈からルビを構築(文脈依存訳; 無い語はper-root safe_replaceにフォールバック)
    def build_ruby_from_anno(
        pairs, *, force_ruby=False, typed_atomic_punctuation=False,
    ):
        segs = []
        for piece, trans in pairs:
            if (
                trans
                and trans != piece
                and (force_ruby or not _LATIN.match(trans))
            ):
                segs.append(dictionary_output(
                    piece, trans, authoritative_annotation=True,
                    typed_atomic_piece=typed_atomic_punctuation,
                ))
            else:
                segs.append(piece)
        return '/'.join(segs)

    def word_ruby_with_ending(i_x):
        """AN/ON等のスラッシュ分解(語尾付き)について、語幹がword_annoにあればper-word訳を採用。"""
        pieces = [p for p in i_x.split('/') if p]
        if len(pieces) >= 2 and word_anno_nosl is not None:
            stem_nosl = ''.join(pieces[:-1]); ending = pieces[-1]
            if stem_nosl in word_anno_nosl:
                return build_ruby_from_anno(word_anno_nosl[stem_nosl]) + '/' + ending
        return safe_replace(i_x, temporary_replacements_list_final)

    # pre_replacements_dict_1: E_stem を per-root置換。use_parallelで並列(Streamlit Cloud用)。
    if use_parallel:
        pre_replacements_dict_1 = parallel_build_pre_replacements_dict(
            E_stem_with_Part_Of_Speech_list, temporary_replacements_list_final, num_processes)
    else:
        pre_replacements_dict_1 = {}
        for i, j in enumerate(E_stem_with_Part_Of_Speech_list):
            if len(j) == 2 and len(j[0]) >= 2:
                if j[0] in pre_replacements_dict_1:
                    if j[1] not in pre_replacements_dict_1[j[0]][1]:
                        pre_replacements_dict_1[j[0]] = [pre_replacements_dict_1[j[0]][0], pre_replacements_dict_1[j[0]][1] + ',' + j[1]]
                else:
                    pre_replacements_dict_1[j[0]] = [safe_replace(j[0], temporary_replacements_list_final), j[1]]
    # word_anno(per-word文脈グロス)を後処理で上書き(serial/parallel共通。固有名詞の偽友グロス回避)。
    if word_anno_nosl is not None:
        for _k in pre_replacements_dict_1:
            _ns = _k.replace('/', '')
            if _ns in word_anno_nosl:
                pre_replacements_dict_1[_k][0] = build_ruby_from_anno(word_anno_nosl[_ns])

    for key in ['domen', 'teren', 'posten']:
        pre_replacements_dict_1.pop(key, None)

    pre_replacements_dict_2 = {}
    for i, j in pre_replacements_dict_1.items():
        if i == j[0]:
            pre_replacements_dict_2[i.replace('/', '')] = [j[0].replace("</rt></ruby>", "%%%").replace('/', '').replace("%%%", "</rt></ruby>"), j[1], len(i.replace('/', '')) * 10000 - 3000]
        else:
            pre_replacements_dict_2[i.replace('/', '')] = [j[0].replace("</rt></ruby>", "%%%").replace('/', '').replace("%%%", "</rt></ruby>"), j[1], len(i.replace('/', '')) * 10000]

    verb_suffix_2l_2 = {}
    for original_verb_suffix, replaced_verb_suffix in verb_suffix_2l.items():
        if (
            original_verb_suffix in _FINITE_VERB_ENDINGS
            and original_verb_suffix in _csv_root_map
            and "Ruby文字" in format_type
        ):
            # Two-letter roots are deliberately shielded in safe_replace, but
            # finite verb endings are independent annotations in the Kyoto
            # guide.  Direct CSV lookup keeps as/is/os/us ruby-bearing in every
            # generated verb paradigm while retaining localized JA/ZH/KO rt.
            verb_suffix_2l_2[original_verb_suffix] = dictionary_output(
                original_verb_suffix, _csv_root_map[original_verb_suffix],
            )
        else:
            verb_suffix_2l_2[original_verb_suffix] = safe_replace(replaced_verb_suffix, temporary_replacements_list_final)

    unchangeable_after_creation_list = []
    AN_replacement = safe_replace('an', temporary_replacements_list_final)
    AN_treatment = []

    pre_replacements_dict_3 = {}
    pre_replacements_dict_2_copy = pre_replacements_dict_2.copy()
    for i, j in pre_replacements_dict_2_copy.items():
        if i.endswith('an') and (AN_replacement in j[0]) and ("名词" in j[1]) and (i[:-2] in pre_replacements_dict_2_copy):
            AN_treatment.append([i, j[0]])
            pre_replacements_dict_2.pop(i, None)
            for k in ["o", "a", "e"]:
                if not i + k in pre_replacements_dict_2_copy:
                    pre_replacements_dict_3[i + k] = [j[0] + k, j[2] + len(k) * 10000 - 2000]
        elif (j[1] == "名词") and (len(i) <= 6) and not (j[2] == 60000 or j[2] == 50000 or j[2] == 40000 or j[2] == 30000 or j[2] == 20000):
            for k in ["o"]:
                if not i + k in pre_replacements_dict_2_copy:
                    pre_replacements_dict_3[i + k] = [j[0] + k, j[2] + len(k) * 10000 - 2000]
                else:
                    pass
            pre_replacements_dict_2.pop(i, None)

    for i, j in pre_replacements_dict_2.items():
        if j[2] == 20000:
            if "名词" in j[1]:
                for k in ["o", "on", 'oj', 'ojn']:
                    if not i + k in pre_replacements_dict_2:
                        pre_replacements_dict_3[' ' + i + k] = [' ' + j[0] + k, j[2] + (len(k) + 1) * 10000 - 5000]
                    else:
                        pass
            if "形容词" in j[1]:
                for k in ["a", "aj", 'an', 'ajn']:
                    if not i + k in pre_replacements_dict_2:
                        pre_replacements_dict_3[' ' + i + k] = [' ' + j[0] + k, j[2] + (len(k) + 1) * 10000 - 5000]
                    else:
                        pre_replacements_dict_3[i + k] = [j[0] + k, j[2] + len(k) * 10000 - 5000]
                        unchangeable_after_creation_list.append(i + k)
            if "副词" in j[1]:
                for k in ["e"]:
                    if not i + k in pre_replacements_dict_2:
                        pre_replacements_dict_3[' ' + i + k] = [' ' + j[0] + k, j[2] + (len(k) + 1) * 10000 - 5000]
                    else:
                        pre_replacements_dict_3[' ' + i + k] = [' ' + j[0] + k, j[2] + (len(k) + 1) * 10000 - 5000]
            if "动词" in j[1]:
                for k1, k2 in verb_suffix_2l_2.items():
                    if not i + k1 in pre_replacements_dict_2:
                        pre_replacements_dict_3[i + k1] = [j[0] + k2, j[2] + len(k1) * 10000 - 3000]
                    elif j[0] + k2 != pre_replacements_dict_2[i + k1][0]:
                        pre_replacements_dict_3[i + k1] = [j[0] + k2, j[2] + len(k1) * 10000 - 3000]
                        unchangeable_after_creation_list.append(i + k1)
                for k in ["u ", "i ", "u", "i"]:
                    if not i + k in pre_replacements_dict_2:
                        pre_replacements_dict_3[i + k] = [j[0] + k, j[2] + suffix_priority_length(k) * 10000 - 3000]
                    elif j[0] + k != pre_replacements_dict_2[i + k][0]:
                        pass
            continue
        else:
            if not i in unchangeable_after_creation_list:
                pre_replacements_dict_3[i] = [j[0], j[2]]
            if j[2] == 60000 or j[2] == 50000 or j[2] == 40000 or j[2] == 30000:
                if "名词" in j[1]:
                    for k in ["o", "on", 'oj', 'ojn']:
                        if not i + k in pre_replacements_dict_2:
                            pre_replacements_dict_3[i + k] = [j[0] + k, j[2] + suffix_priority_length(k) * 10000 - 3000]
                        elif j[0] + k != pre_replacements_dict_2[i + k][0]:
                            pre_replacements_dict_3[i + k] = [j[0] + k, j[2] + suffix_priority_length(k) * 10000 - 3000]
                            unchangeable_after_creation_list.append(i + k)
                if "形容词" in j[1]:
                    for k in ["a", "aj", 'an', 'ajn']:
                        if not i + k in pre_replacements_dict_2:
                            pre_replacements_dict_3[i + k] = [j[0] + k, j[2] + len(k) * 10000 - 3000]
                        elif j[0] + k != pre_replacements_dict_2[i + k][0]:
                            pre_replacements_dict_3[i + k] = [j[0] + k, j[2] + len(k) * 10000 - 3000]
                            unchangeable_after_creation_list.append(i + k)
                if "副词" in j[1]:
                    for k in ["e"]:
                        if not i + k in pre_replacements_dict_2:
                            pre_replacements_dict_3[i + k] = [j[0] + k, j[2] + len(k) * 10000 - 3000]
                        elif j[0] + k != pre_replacements_dict_2[i + k][0]:
                            pre_replacements_dict_3[i + k] = [j[0] + k, j[2] + len(k) * 10000 - 3000]
                            unchangeable_after_creation_list.append(i + k)
                if "动词" in j[1]:
                    for k1, k2 in verb_suffix_2l_2.items():
                        if not i + k1 in pre_replacements_dict_2:
                            pre_replacements_dict_3[i + k1] = [j[0] + k2, j[2] + len(k1) * 10000 - 3000]
                        elif j[0] + k2 != pre_replacements_dict_2[i + k1][0]:
                            pre_replacements_dict_3[i + k1] = [j[0] + k2, j[2] + len(k1) * 10000 - 3000]
                            unchangeable_after_creation_list.append(i + k1)
                    for k in ["u ", "i ", "u", "i"]:
                        if not i + k in pre_replacements_dict_2:
                            pre_replacements_dict_3[i + k] = [j[0] + k, j[2] + len(k) * 10000 - 3000]
                        elif j[0] + k != pre_replacements_dict_2[i + k][0]:
                            pre_replacements_dict_3[i + k] = [j[0] + k, j[2] + len(k) * 10000 - 3000]
                            unchangeable_after_creation_list.append(i + k)
            elif len(i) >= 3 and len(i) <= 6:
                if "名词" in j[1]:
                    for k in ["o"]:
                        if not i + k in pre_replacements_dict_2:
                            pre_replacements_dict_3[i + k] = [j[0] + k, j[2] + len(k) * 10000 - 5000]
                        elif j[0] + k != pre_replacements_dict_2[i + k][0]:
                            pass
                if "形容词" in j[1]:
                    for k in ["a"]:
                        if not i + k in pre_replacements_dict_2:
                            pre_replacements_dict_3[i + k] = [j[0] + k, j[2] + len(k) * 10000 - 5000]
                        elif j[0] + k != pre_replacements_dict_2[i + k][0]:
                            pass
                if "副词" in j[1]:
                    for k in ["e"]:
                        if not i + k in pre_replacements_dict_2:
                            pre_replacements_dict_3[i + k] = [j[0] + k, j[2] + len(k) * 10000 - 5000]
                        elif j[0] + k != pre_replacements_dict_2[i + k][0]:
                            pass

    for an in AN:
        if an[1].endswith("/an/"):
            i2 = an[1]; i3 = re.sub(r"/an/$", "", i2)
            for suf in ["/an/o", "/an/oj", "/an/on", "/an/ojn", "/an/a", "/an/aj", "/an/an", "/an/ajn", "/an/e", "/an/en", None]:
                i_x = (i3 + suf) if suf else (i3 + "/a/n/")
                pre_replacements_dict_3[i_x.replace('/', '')] = [word_ruby_with_ending(i_x).replace("</rt></ruby>", "%%%").replace('/', '').replace("%%%", "</rt></ruby>"), len(i_x.replace('/', '')) * 10000 + 5000]
        else:
            i2 = an[1]; i2_2 = re.sub(r"an$", "", i2); i3 = re.sub(r"an/$", "", i2_2)
            for suf in ["an/o", "an/oj", "an/on", "an/ojn", "an/a", "an/aj", "an/an", "an/ajn", "an/e", "an/en", None]:
                i_x = (i3 + suf) if suf else (i3 + "/a/n/")
                pre_replacements_dict_3[i_x.replace('/', '')] = [word_ruby_with_ending(i_x).replace("</rt></ruby>", "%%%").replace('/', '').replace("%%%", "</rt></ruby>"), len(i_x.replace('/', '')) * 10000 + 5000]

    # word_anno の確定分節 ``.../an`` を正本とし、-an-幹の文法語尾を
    # データ駆動で全展開する。従来の AN 表は同綴異義語の特別扱いと
    # 形容詞対格 ``.../a/n`` の生成に引き続き使い、ここで収録語幹を
    # 汎用的に補完する。既存 word_anno に別分解がある語形は helper 側で除外。
    _word_anno_boundary_surfaces = set()
    if word_anno is not None:
        for surface, stem_key, ending in iter_word_anno_an_inflections(word_anno):
            _word_anno_boundary_surfaces.add(surface)
            pairs = word_anno.get(stem_key)
            if pairs:
                replaced = build_ruby_from_anno(pairs) + '/' + ending
            else:
                replaced = safe_replace(stem_key + '/' + ending, temporary_replacements_list_final)
            replaced = replaced.replace("</rt></ruby>", "%%%").replace('/', '').replace("%%%", "</rt></ruby>")
            # These are complete inflected word forms, not productive substrings.
            # Remove a lower-priority naked rule and let punctuation/line padding
            # activate the bounded variant, protecting proper names such as Taranaki.
            pre_replacements_dict_3.pop(surface, None)
            pre_replacements_dict_3[' ' + surface + ' '] = [
                ' ' + replaced + ' ', len(surface) * 10000 + 5000,
            ]

    for on in ON:
        if on[1].endswith("/on/"):
            i2 = on[1]; i3 = re.sub(r"/on/$", "", i2)
            for suf in ["/on/o", "/on/oj", "/on/on", "/on/ojn", "/on/a", "/on/aj", "/on/e", None]:
                i_x = (i3 + suf) if suf else (i3 + "/o/n/")
                pre_replacements_dict_3[i_x.replace('/', '')] = [word_ruby_with_ending(i_x).replace("</rt></ruby>", "%%%").replace('/', '').replace("%%%", "</rt></ruby>"), len(i_x.replace('/', '')) * 10000 + 5000]
        else:
            i2 = on[1]; i2_2 = re.sub(r"on$", "", i2); i3 = re.sub(r"on/$", "", i2_2)
            for suf in ["on/o", "on/oj", "on/on", "on/ojn", "on/a", "on/aj", "on/e", None]:
                i_x = (i3 + suf) if suf else (i3 + "/o/n/")
                pre_replacements_dict_3[i_x.replace('/', '')] = [word_ruby_with_ending(i_x).replace("</rt></ruby>", "%%%").replace('/', '').replace("%%%", "</rt></ruby>"), len(i_x.replace('/', '')) * 10000 + 5000]

    # Explicit hyphen components are intentionally unbounded: they operate
    # inside a longer hyphenated token.  A longer case-sensitive exact surface
    # still wins by length/priority for foreign names and publication titles.
    for _root in sorted(_HYPHEN_PREFIX_COMPONENT_ROOTS):
        if _root not in _csv_root_map:
            continue
        _surface = _root + "-"
        pre_replacements_dict_3[_surface] = [
            dictionary_output(_root, _csv_root_map[_root]) + "-",
            len(_surface) * 10000 + 8000,
        ]
    for _root in sorted(_HYPHEN_INFIX_COMPONENT_ROOTS):
        if _root not in _csv_root_map:
            continue
        _surface = "-" + _root + "-"
        pre_replacements_dict_3[_surface] = [
            "-" + dictionary_output(_root, _csv_root_map[_root]) + "-",
            len(_surface) * 10000 + 8000,
        ]
    for _surface, _roots in sorted(_HYPHEN_COMPOSITE_PREFIXES.items()):
        if any(_root not in _csv_root_map for _root in _roots):
            continue
        # Most composite prefixes have an internal morphological boundary but
        # no written separator (du/on-, kvar/on-).  Preserve a separator when
        # it is actually present in the source spelling (unu-op-); otherwise a
        # generic component rule silently changes the visible text.
        _written_joiner = "-" if "-" in _surface[:-1] else ""
        pre_replacements_dict_3[_surface] = [
            _written_joiner.join(
                dictionary_output(_root, _csv_root_map[_root])
                for _root in _roots
            ) + "-",
            len(_surface) * 10000 + 8500,
        ]

    # Ordinary roots already match immediately before a poetic final
    # apostrophe (dank' -> dank + literal ').  Two-letter roots are deliberately
    # boundary-shielded elsewhere, so give the same treatment explicitly at a
    # left word boundary (Di', ni', ...).  Prefer word_anno over the CSV because
    # short homographs such as di have context-correct lexical annotations.
    _two_char_elision_roots = (
        set(suffix_2char_roots)
        | set(prefix_2char_roots)
        | set(standalone_2char_roots)
    )
    for _root in sorted(_two_char_elision_roots):
        if len(_root) != 2:
            continue
        _pa = lookup_word_anno_exact_first(word_anno, word_anno_nosl, _root)
        if (
            _pa is not None
            and len(_pa) == 1
            and _pa[0][0].replace('/', '') == _root
        ):
            _rendered_root = build_ruby_from_anno(_pa)
        elif _root in _csv_root_map:
            _rendered_root = dictionary_output(_root, _csv_root_map[_root])
        else:
            continue
        for _apostrophe in ("'", "’"):
            _surface = _root + _apostrophe
            pre_replacements_dict_3[" " + _surface] = [
                " " + _rendered_root + _apostrophe,
                len(_surface) * 10000 + 8700,
            ]

    # The elided definite article is exceptional: the guide treats l' as one
    # complete ruby, and it can be written directly before the next word
    # (l'Dio).  Keep only the left boundary: this protects foreign substrings,
    # still permits the following word to be adjacent, and also carries the
    # two-character article through the global rule layer's length >= 3 gate.
    _la_meaning = resolve_elided_article_meaning(
        word_anno, word_anno_nosl, _csv_root_map,
    )
    if _la_meaning is not None:
        for _article in ("l'", "l’"):
            pre_replacements_dict_3[" " + _article] = [
                " " + dictionary_output(_article, _la_meaning),
                len(_article) * 10000 + 8800,
            ]

    # custom_stemming_setting_list
    _case_sensitive_rule_keys = set()
    if len(custom_stemming_setting_list) > 0:
        if len(custom_stemming_setting_list[0]) != 3:
            custom_stemming_setting_list.pop(0)
    for i in custom_stemming_setting_list:
        if len(i) == 3:
            try:
                _explicit_word_boundary = "word_boundary" in i[2]
                _boundary_noop_guard = "boundary_noop_guard" in i[2]
                _case_sensitive = "case_sensitive" in i[2]
                _atomic_no_split = "atomic_no_split" in i[2]
                _word_boundary = _explicit_word_boundary
                if _explicit_word_boundary:
                    i[2].remove("word_boundary")
                if _boundary_noop_guard:
                    i[2].remove("boundary_noop_guard")
                if _case_sensitive:
                    i[2].remove("case_sensitive")
                if _atomic_no_split:
                    i[2].remove("atomic_no_split")
                esperanto_Word_before_replacement = i[0].replace('/', '')
                _setting_parts = [q for q in i[0].split('/') if q]
                _typed_roles = extract_typed_roles(i[2], len(_setting_parts))
                _context_annotation_key = extract_context_annotation(i[2])
                if i[1] == "dflt":
                    replacement_priority_by_length = len(esperanto_Word_before_replacement) * 10000
                elif i[1] in allowed_values:
                    pre_replacements_dict_3.pop(esperanto_Word_before_replacement, None)
                    if "ne" in i[2]:
                        pre_replacements_dict_3.pop(esperanto_Word_before_replacement, None)
                        i[2].remove("ne")
                    if "verbo_s1" in i[2]:
                        for k1 in verb_suffix_2l_2.keys():
                            pre_replacements_dict_3.pop(esperanto_Word_before_replacement + k1, None)
                        i[2].remove("verbo_s1")
                    if "verbo_s2" in i[2]:
                        for k in ["u ", "i ", "u", "i"]:
                            pre_replacements_dict_3.pop(esperanto_Word_before_replacement + k, None)
                        i[2].remove("verbo_s2")
                    if len(i[2]) >= 1:
                        for jj in i[2]:
                            j2 = jj.replace('/', '')
                            pre_replacements_dict_3.pop(esperanto_Word_before_replacement + j2, None)
                    continue
                elif isinstance(i[1], int) or (isinstance(i[1], str) and i[1].isdigit()):
                    replacement_priority_by_length = int(i[1])
                # 設定JSONの語幹: 注釈版(word_anno)が「語幹全体を1ユニットとして持つ」場合のみ採用
                # (固有名詞の偽友グロス回避。複数片に分節する語はsafe_replaceの語根単位グロスを優先し、
                #  word_annoの旧分節による上書き退行=alten→al/ten 等を防ぐ)
                _stem_ns = i[0].replace('/', '')
                _wa = lookup_word_anno_exact_first(word_anno, word_anno_nosl, i[0])
                # 設定JSONが明示的に複数片分解(スラッシュ)を指定している場合は、
                # word_anno単体グロスで上書きしない(層序列: 設定JSON=最上位の人手キュレーション)。
                _setting_wants_split = '/' in i[0].strip('/')
                _suffix_rules_need_boundary = setting_suffix_rules_need_boundary(
                    _setting_parts, i[2], _explicit_word_boundary,
                )
                # 単体指定でも、word_anno側の片連結が語幹に一致すれば採用(単体=1片/複数片の両対応。
                # 漢字モードのper-word注入(kaj/o=码 等)を単体設定行でも活かす)
                _wa_concat = ''.join(x[0] for x in _wa).replace('/', '') if _wa else None
                _exact_split_wa = word_anno.get(i[0]) if word_anno is not None else None
                if _exact_split_wa is not None and (
                    len(_exact_split_wa) != len(_setting_parts)
                    or any(
                        pair[0].replace('/', '') != piece
                        for pair, piece in zip(_exact_split_wa, _setting_parts)
                    )
                ):
                    _exact_split_wa = None
                # 多片anno採用は漢字モード限定(ルビ=一体保持/漢字=深分解 の二本立て。
                # ルビ側でalten→al/ten型の旧分節退行を防ぐ元ガードの意図を維持)
                _wa_usable = _wa is not None and (
                    (len(_wa) == 1 and _wa[0][0].replace('/', '') == _stem_ns)
                    or ('汉字替换' in format_type and _wa_concat == _stem_ns))
                if _context_annotation_key is not None:
                    _context_pa = word_anno.get(_context_annotation_key) if word_anno is not None else None
                    if (
                        _context_pa is None
                        or len(_context_pa) != 1
                        or _context_pa[0][0].replace('/', '') != _stem_ns
                    ):
                        if '汉字替换' in format_type:
                            # A Ruby homograph annotation (al=wing in alo)
                            # has no authority to borrow the ordinary Kanji
                            # homograph (al=toward).  Without an explicit
                            # context-specific Kanji assignment, retain the
                            # reviewed source stem verbatim.
                            Replaced_String = _stem_ns
                        else:
                            raise ValueError(
                                f"invalid context annotation {_context_annotation_key!r} "
                                f"for setting stem {_stem_ns!r}"
                            )
                    else:
                        Replaced_String = build_ruby_from_anno(_context_pa).replace(
                            "</rt></ruby>", "%%%"
                        ).replace('/', '').replace("%%%", "</rt></ruby>")
                elif _typed_roles is not None:
                    # A reviewed exact signature has stronger information than
                    # the grammatical bare-piece heuristic.  Context annotation
                    # keys are deliberately outside the Esperanto alphabet so
                    # they cannot change the ordinary standalone analysis of a
                    # homograph (notably sin = si/n).
                    _parts = []
                    for _part_index, (_pc, _role) in enumerate(zip(_setting_parts, _typed_roles)):
                        if _role == "L":
                            _parts.append(_pc)
                            continue
                        _pa = lookup_typed_ruby_annotation(
                            word_anno,
                            esperanto_Word_before_replacement,
                            _part_index,
                            _pc,
                        )
                        if _pa is not None:
                            _parts.append(build_ruby_from_anno(
                                _pa, force_ruby=True,
                                typed_atomic_punctuation=True,
                            ))
                        else:
                            # A case-sensitive reviewed surface can capitalize
                            # an otherwise ordinary lexical component.  Reuse
                            # only a unique casefold value, with the same
                            # fail-closed collision policy as the non-typed
                            # explicit-piece branch below.  Lowercase pieces
                            # never borrow uppercase abbreviation semantics.
                            _pa_casefold = (
                                lookup_unique_casefold(
                                    word_anno_casefold,
                                    word_anno_casefold_ambiguous,
                                    _pc,
                                    "word annotation",
                                )
                                if (
                                    word_anno_casefold is not None
                                    and explicit_piece_allows_casefold_fallback(_pc)
                                ) else None
                            )
                            if (
                                _pa_casefold is not None
                                and len(_pa_casefold) == 1
                                and _pa_casefold[0][0].replace('/', '').casefold()
                                == _pc.casefold()
                            ):
                                _annotation_piece, _annotation_gloss = _pa_casefold[0]
                                _parts.append(dictionary_output(
                                    _pc, _annotation_gloss,
                                    authoritative_annotation=True,
                                    typed_atomic_piece=True,
                                ))
                                continue
                            _csv_casefold_meaning = (
                                _csv_root_map[_pc]
                                if _pc in _csv_root_map else
                                lookup_unique_casefold(
                                    _csv_root_map_casefold,
                                    _csv_root_map_casefold_ambiguous,
                                    _pc,
                                    "CSV root",
                                )
                                if explicit_piece_allows_casefold_fallback(_pc)
                                else None
                            )
                            if _csv_casefold_meaning is not None:
                                _parts.append(dictionary_output(
                                    _pc, _csv_casefold_meaning,
                                    typed_atomic_piece=True,
                                ))
                            elif '汉字替换' in format_type:
                                # Typed roles describe the reviewed Ruby span
                                # structure.  The Kanji track may deliberately
                                # have no character assignment for a proper or
                                # technical root; preserve that exact source
                                # piece instead of dropping the whole bounded
                                # morphology rule.  Ruby generation remains
                                # fail-closed because it must supply an rt.
                                _parts.append(_pc)
                            else:
                                raise ValueError(
                                    f"typed ruby piece lacks contextual annotation: "
                                    f"{esperanto_Word_before_replacement!r}"
                                    f"[{_part_index}]={_pc!r}"
                                )
                    Replaced_String = ''.join(_parts)
                elif _atomic_no_split:
                    # A reviewed exact unsplit form is one morphological unit.
                    # Prefer its exact per-word gloss, then an exact CSV root;
                    # otherwise keep it literal.  Never feed it to safe_replace,
                    # which would reintroduce the very internal split this guard
                    # is meant to suppress (Ralf -> ral/f, Labubu -> lab/ubu).
                    if _wa_usable:
                        Replaced_String = build_ruby_from_anno(_wa).replace("</rt></ruby>", "%%%").replace('/', '').replace("%%%", "</rt></ruby>")
                    elif i[0] in _csv_root_map:
                        Replaced_String = dictionary_output(i[0], _csv_root_map[i[0]])
                    else:
                        Replaced_String = i[0]
                elif (not _setting_wants_split) and _wa_usable:
                    Replaced_String = build_ruby_from_anno(_wa).replace("</rt></ruby>", "%%%").replace('/', '').replace("%%%", "</rt></ruby>")
                elif _setting_wants_split:
                    # 分解指定時は各片を原子的に構築(片の内部を再分解しない)。
                    # 片が既知語根なら単独safe_replaceでルビ化、未知(固有名詞等)なら裸のまま。
                    _parts=[]
                    # 語幹の後ろにsuffix actionが付く場合、語幹末のan/onは最終語尾では
                    # なく内部接辞。kun/hejm/an + o を kun/hejm/ano に潰さない。
                    _effective_part_total = setting_effective_part_total(_setting_parts, i[2])
                    for _part_index, _pc in enumerate(_setting_parts):
                        # 裸で保つのは【語末】の屈折語尾だけ。
                        # ter/an/oj の中間 an まで裸にすると an+oj が連結し、
                        # 明示分解が ter/anoj へ退行する。中間片は接辞を含め
                        # 必ず以下の原子的辞書引きに渡す。
                        if setting_piece_is_bare(_pc, _part_index, _effective_part_total):
                            _parts.append(_pc); continue
                        # An exact slash-keyed annotation may disambiguate one
                        # root only inside this reviewed compound (pasi="all"
                        # in pasi/grafi, not the ordinary pasi="passion").
                        if _exact_split_wa is not None:
                            _parts.append(build_ruby_from_anno([_exact_split_wa[_part_index]]))
                            continue
                        # 片がword_annoに単体1ユニットで存在 → その注釈でルビ化(固有名詞・借用語根)
                        _pa = lookup_word_anno_exact_first(word_anno, word_anno_nosl, _pc)
                        if _pa is not None and len(_pa) == 1 and _pa[0][0].replace('/', '') == _pc:
                            _parts.append(build_ruby_from_anno(_pa)); continue
                        # A case-sensitive exact surface retains its written
                        # capitalization, but its reusable lexical component
                        # may exist only in lowercase.  Use a casefold fallback
                        # only when that key has one unambiguous payload, and
                        # render the source-cased component rather than the
                        # dictionary's lowercase spelling.
                        _pa_casefold = (
                            lookup_unique_casefold(
                                word_anno_casefold,
                                word_anno_casefold_ambiguous,
                                _pc,
                                "word annotation",
                            )
                            if (
                                word_anno_casefold is not None
                                and explicit_piece_allows_casefold_fallback(_pc)
                            ) else None
                        )
                        if (
                            _pa_casefold is not None
                            and len(_pa_casefold) == 1
                            and _pa_casefold[0][0].replace('/', '').casefold() == _pc.casefold()
                        ):
                            _annotation_piece, _annotation_gloss = _pa_casefold[0]
                            if (
                                _annotation_gloss
                                and _annotation_gloss != _annotation_piece
                                and not _LATIN.match(_annotation_gloss)
                            ):
                                _parts.append(dictionary_output(
                                    _pc, _annotation_gloss,
                                    authoritative_annotation=True,
                                ))
                            else:
                                _parts.append(_pc)
                            continue
                        _r = safe_replace(_pc, temporary_replacements_list_final)
                        # 完全一致1ルビ(片全体を覆う)以外=内部分解 → CSV直引き→裸(片を壊さない)
                        _m = re.fullmatch(r'<ruby>' + re.escape(_pc) + r'<rt[^>]*>.*?</rt></ruby>', _r, re.DOTALL)
                        if _m:
                            _parts.append(_r)
                        else:
                            _csv_casefold_meaning = (
                                None
                                if _pc in _csv_root_map
                                else lookup_unique_casefold(
                                    _csv_root_map_casefold,
                                    _csv_root_map_casefold_ambiguous,
                                    _pc,
                                    "CSV root",
                                )
                                if explicit_piece_allows_casefold_fallback(_pc)
                                else None
                            )
                            if (
                                _pc in _csv_root_map
                                or _csv_casefold_meaning is not None
                            ):
                                _csv_meaning = (
                                    _csv_root_map[_pc]
                                    if _pc in _csv_root_map
                                    else _csv_casefold_meaning
                                )
                                _parts.append(dictionary_output(
                                    _pc, _csv_meaning,
                                ))
                            else:
                                _parts.append(_pc)
                    Replaced_String = ''.join(_parts)
                else:
                    Replaced_String = safe_replace(i[0], temporary_replacements_list_final).replace("</rt></ruby>", "%%%").replace('/', '').replace("%%%", "</rt></ruby>")
                def _register_custom_suffix(old_suffix, new_suffix, priority):
                    if _suffix_rules_need_boundary:
                        # verbo_s2 historically supplies both ``i`` and
                        # ``i `` (likewise ``u``).  A boundary wrapper already
                        # contributes exactly one outer space; retaining the
                        # suffix's own space produced `` old  ``/`` new  ``
                        # while the placeholder carried only one, leaking raw
                        # $...$ markers after a padded hyphen (el-meti).
                        old_suffix = str(old_suffix).strip()
                        new_suffix = str(new_suffix).strip()
                    old_key = esperanto_Word_before_replacement + old_suffix
                    new_value = Replaced_String + new_suffix
                    if _suffix_rules_need_boundary:
                        pre_replacements_dict_3.pop(old_key, None)
                        registered_key = ' ' + old_key + ' '
                        pre_replacements_dict_3[registered_key] = [' ' + new_value + ' ', priority]
                    else:
                        registered_key = old_key
                        pre_replacements_dict_3[registered_key] = [new_value, priority]
                    if _case_sensitive:
                        _case_sensitive_rule_keys.add(registered_key)
                if "ne" in i[2]:
                    if _word_boundary:
                        # 通常の boundary_only は裸キーを除去する。確定データが明示した
                        # boundary_noop_guard だけは裸の no-op を併置し、非Esperanto語
                        # anona 内の anon をplaceholderで無変更保護する。
                        if _boundary_noop_guard:
                            _bounded_guard_priority, _naked_guard_priority = (
                                guarded_boundary_priorities(replacement_priority_by_length)
                            )
                            pre_replacements_dict_3[esperanto_Word_before_replacement] = [
                                esperanto_Word_before_replacement,
                                # The naked no-op must win against an equal-length
                                # lexical rule inside a longer foreign word (anon+a
                                # versus nona), while remaining below any genuinely
                                # longer exact rule such as anono.
                                _naked_guard_priority,
                            ]
                        else:
                            pre_replacements_dict_3.pop(esperanto_Word_before_replacement, None)
                        _bounded_old = ' ' + esperanto_Word_before_replacement + ' '
                        _bounded_new = ' ' + Replaced_String + ' '
                        # For a guarded homograph, the standalone bounded split
                        # must run before its unbounded no-op; inside a longer
                        # token only the latter is eligible.
                        _bounded_priority = (
                            _bounded_guard_priority
                            if _boundary_noop_guard else replacement_priority_by_length
                        )
                        pre_replacements_dict_3[_bounded_old] = [_bounded_new, _bounded_priority]
                        if _case_sensitive:
                            _case_sensitive_rule_keys.add(_bounded_old)
                    else:
                        pre_replacements_dict_3[esperanto_Word_before_replacement] = [Replaced_String, replacement_priority_by_length]
                        if _case_sensitive:
                            _case_sensitive_rule_keys.add(esperanto_Word_before_replacement)
                    i[2].remove("ne")
                if "verbo_s1" in i[2]:
                    for k1, k2 in verb_suffix_2l_2.items():
                        _register_custom_suffix(k1, k2, replacement_priority_by_length + len(k1) * 10000)
                    i[2].remove("verbo_s1")
                if "verbo_s2" in i[2]:
                    for k in ["u ", "i ", "u", "i"]:
                        _register_custom_suffix(k, k, replacement_priority_by_length + suffix_priority_length(k) * 10000)
                    i[2].remove("verbo_s2")
                if len(i[2]) >= 1:
                    for jj in i[2]:
                        j2 = jj.replace('/', '')
                        # 純粋な文法語尾(o/oj/on/ojn/a/aj/an/ajn/e/en/n/j等)はリテラル付加
                        # (通常名詞処理と整合。対格onが分数接尾辞-on-に誤マッチするのを防ぐ)
                        if j2 in _GRAM_ENDINGS:
                            j3 = j2
                        else:
                            j3 = safe_replace(jj, temporary_replacements_list_final).replace("</rt></ruby>", "%%%").replace('/', '').replace("%%%", "</rt></ruby>")
                        _register_custom_suffix(j2, j3, replacement_priority_by_length + len(j2) * 10000)
                elif not _word_boundary:
                    # boundary-only 固定語は上で登録した空白付きキーだけを保つ。
                    # ``ne`` を除いた後の共通 fallback で裸キーを復活させない。
                    pre_replacements_dict_3[esperanto_Word_before_replacement] = [Replaced_String, replacement_priority_by_length]
                    if _case_sensitive:
                        _case_sensitive_rule_keys.add(esperanto_Word_before_replacement)
            except (AmbiguousCasefoldError, ValueError):
                # Typed-role and contextual-annotation rows are reviewed
                # authority.  A missing/malformed localized annotation must
                # fail the build instead of silently dropping the exact rule.
                raise
            except Exception:
                continue

    # user_replacement_item_setting_list
    if len(user_replacement_item_setting_list) > 0:
        if len(user_replacement_item_setting_list[0]) != 4:
            user_replacement_item_setting_list.pop(0)
    for i in user_replacement_item_setting_list:
        if len(i) == 4:
            try:
                esperanto_Roots_before_replacement = i[0].strip('/').split('/')
                replaced_roots = i[3].strip('/').split('/')
                if len(esperanto_Roots_before_replacement) == len(replaced_roots):
                    Replaced_String = ""
                    for kk in range(len(esperanto_Roots_before_replacement)):
                        Replaced_String += output_format(esperanto_Roots_before_replacement[kk], replaced_roots[kk], format_type, char_widths_dict)
                    esperanto_Word_before_replacement = i[0].replace('/', '')
                    if i[1] == "dflt":
                        replacement_priority_by_length = len(esperanto_Word_before_replacement) * 10000
                    elif isinstance(i[1], int) or (isinstance(i[1], str) and i[1].isdigit()):
                        replacement_priority_by_length = int(i[1])
                    if "ne" in i[2]:
                        pre_replacements_dict_3[esperanto_Word_before_replacement] = [Replaced_String, replacement_priority_by_length]
                        i[2].remove("ne")
                    if "verbo_s1" in i[2]:
                        for k1, k2 in verb_suffix_2l_2.items():
                            pre_replacements_dict_3[esperanto_Word_before_replacement + k1] = [Replaced_String + k2, replacement_priority_by_length + len(k1) * 10000]
                        i[2].remove("verbo_s1")
                    if "verbo_s2" in i[2]:
                        for k in ["u ", "i ", "u", "i"]:
                            pre_replacements_dict_3[esperanto_Word_before_replacement + k] = [Replaced_String + k, replacement_priority_by_length + suffix_priority_length(k) * 10000]
                        i[2].remove("verbo_s2")
                    if len(i[2]) >= 1:
                        for jj in i[2]:
                            j2 = jj.replace('/', '')
                            j3 = safe_replace(jj, temporary_replacements_list_final).replace("</rt></ruby>", "%%%").replace('/', '').replace("%%%", "</rt></ruby>")
                            pre_replacements_dict_3[esperanto_Word_before_replacement + j2] = [Replaced_String + j3, replacement_priority_by_length + len(j2) * 10000]
                    else:
                        pre_replacements_dict_3[esperanto_Word_before_replacement] = [Replaced_String, replacement_priority_by_length]
            except ValueError:
                # Invalid typed roles, contextual annotations, and ambiguous
                # exact lookups are authority errors.  Silently skipping the
                # row would remove a reviewed rule from the deployed payload.
                raise
            except Exception:
                continue

    # Custom and user settings are intentionally processed after word_anno, but
    # a legacy exact entry (for example ter/an/oj + ``ne``) must not silently
    # undo the whole-word boundary established by the data-driven paradigm.
    enforce_boundary_only_surfaces(pre_replacements_dict_3, _word_anno_boundary_surfaces)

    # A lowercase general rule can create an uppercase/capitalized variant only
    # after this dictionary stage (sat -> SAT).  Reserve every explicitly
    # case-sensitive bounded spelling now, remove any naked duplicate, and use
    # the set again while creating automatic case variants below.
    _reserved_case_bounded_surfaces = {
        key[1:-1] for key in _case_sensitive_rule_keys
        if key.startswith(' ') and key.endswith(' ')
    }
    for surface in _reserved_case_bounded_surfaces:
        pre_replacements_dict_3.pop(surface, None)

    pre_replacements_list_1 = []
    for old, new in pre_replacements_dict_3.items():
        if isinstance(new[1], int):
            pre_replacements_list_1.append((old, new[0], new[1]))
    # 重要語彙(2890+派生)の同長タイ優先: 優先度(=文字数ベース)を一切跨がず、完全同値の
    # タイの時だけ重要語を勝たせる(タプルキー)。greedy最長一致・POS補正は不変。
    _imp = important_stems or set()
    _GSUF = ("ojn", "oj", "on", "o", "ajn", "aj", "an", "a", "en", "e", "jn", "j", "n",
             "as", "is", "os", "us", "u", "i")
    def _destem(w):
        w = w.strip()
        for s in _GSUF:
            if w.endswith(s) and len(w) - len(s) >= 2:
                return w[:-len(s)]
        return w
    def _is_important(old):
        if not _imp:
            return False
        o = old.strip()
        return o in _imp or _destem(o) in _imp
    # 同一優先度内は「長いold優先」(貪欲最長一致の徹底)。従来は挿入順で不定のため、
    # 短語エントリ(ama=am+a等)が同帯の長語(lama等)を先食いする不具合があった。
    # 重要語タイブレークは同長の完全タイ時のみ(従来意図を保持)。
    pre_replacements_list_2 = sorted(pre_replacements_list_1,
                                     key=lambda x: stable_replacement_sort_key(x, _is_important), reverse=True)

    pre_replacements_list_3 = []
    for kk in range(len(pre_replacements_list_2)):
        if len(pre_replacements_list_2[kk][0]) >= 3:
            pre_replacements_list_3.append([pre_replacements_list_2[kk][0], remove_redundant_ruby_if_identical(pre_replacements_list_2[kk][1]), imported_placeholders_for_global_replacement[kk]])

    # 大文字化で rb(語根)の幅が変わる(例 v=8→V=10.7, ĉ=8→Ĉ=11.6)ため、大文字/先頭大文字
    # 変種はルビサイズ(rtのCSSクラス)を「実際のcased rb」で output_format により再計算する。
    # これをしないと、小文字語根の幅で決めたサイズを流用し、短語根で最大3段ずれる(要件7.4)。
    _RUBYFIX = re.compile(r'<ruby>([^<]+)<rt class="[^"]+">((?:[^<]|<br>)*)</rt></ruby>', re.IGNORECASE)
    # new.upper() が '<br>'→'<BR>' 化するため、除去は大文字小文字を問わず行う。
    # ('<BR>' が残ると幅計測に文字として混入し、<br>挿入で '<B<br>R>' に破損する)
    _BR_ANY = re.compile(r'<br\s*/?>', re.IGNORECASE)
    # 漢字置換フォーマットでは output_format(エス語根, 漢字) が出力時に役割スワップして
    # <ruby>漢字<rt>語根</rt></ruby> を生む。出力済みHTMLから再計算する際は
    # group(1)=漢字(本文), group(2)=語根(rt) なので、引数順を戻して渡す(二重スワップ防止)。
    _IS_KANJI_FMT = ('汉字替换' in format_type)
    def _resize_caps(h):
        def _rf(mo):
            g1 = mo.group(1); g2 = _BR_ANY.sub('', mo.group(2))
            if _IS_KANJI_FMT:
                return output_format(g2, _BR_ANY.sub('', g1), format_type, char_widths_dict)
            return output_format(g1, g2, format_type, char_widths_dict)
        return _RUBYFIX.sub(_rf, h)

    pre_replacements_list_4 = []
    def _case_variant_is_reserved(old):
        return old.strip() in _reserved_case_bounded_surfaces

    def _capitalized_rule_key(old):
        if old[0] == ' ':
            return old[0] + old[1:].capitalize()
        return old.capitalize()

    if format_type in ('HTML格式_Ruby文字_大小调整', 'HTML格式_Ruby文字_大小调整_汉字替换', 'HTML格式', 'HTML格式_汉字替换'):
        for old, new, place_holder in pre_replacements_list_3:
            pre_replacements_list_4.append((old, new, place_holder))
            if old in _case_sensitive_rule_keys:
                continue
            upper_old = old.upper()
            cap_old = _capitalized_rule_key(old)
            # A one-letter surface plus punctuation (l') has identical upper
            # and title-case keys.  Keep the title-case rendering so its rt is
            # capitalized normally instead of being forced to full uppercase.
            if upper_old != cap_old and not _case_variant_is_reserved(upper_old):
                pre_replacements_list_4.append((upper_old, _resize_caps(new.upper()), place_holder[:-1] + 'up$'))
            if old[0] == ' ':
                cap_new = new[0] + capitalize_ruby_and_rt(new[1:])
            else:
                cap_new = capitalize_ruby_and_rt(new)
            cap_new = _resize_caps(cap_new)
            if not _case_variant_is_reserved(cap_old):
                pre_replacements_list_4.append((cap_old, cap_new, place_holder[:-1] + 'cap$'))
            # ハイフン複合の各部大文字変種(固有名詞 Abu-Dabi 等。実テキストはこの形)
            if '-' in old.strip().strip('-'):
                pc_old = _cap_after_hyphen(cap_old)
                if pc_old != cap_old and not _case_variant_is_reserved(pc_old):
                    pre_replacements_list_4.append((
                        pc_old,
                        _resize_caps(_cap_after_hyphen(cap_new, _IS_KANJI_FMT)),
                        place_holder[:-1] + 'pc$',
                    ))
    elif format_type in ('括弧(号)格式', '括弧(号)格式_汉字替换'):
        for old, new, place_holder in pre_replacements_list_3:
            pre_replacements_list_4.append((old, new, place_holder))
            if old in _case_sensitive_rule_keys:
                continue
            upper_old = old.upper()
            cap_old = _capitalized_rule_key(old)
            if upper_old != cap_old and not _case_variant_is_reserved(upper_old):
                pre_replacements_list_4.append((upper_old, new.upper(), place_holder[:-1] + 'up$'))
            if old[0] == ' ':
                if not _case_variant_is_reserved(cap_old):
                    pre_replacements_list_4.append((cap_old, new[0] + new[1:].capitalize(), place_holder[:-1] + 'cap$'))
            else:
                if not _case_variant_is_reserved(cap_old):
                    pre_replacements_list_4.append((cap_old, new.capitalize(), place_holder[:-1] + 'cap$'))
    elif format_type in ('替换后文字列のみ(仅)保留(简单替换)'):
        for old, new, place_holder in pre_replacements_list_3:
            pre_replacements_list_4.append((old, new, place_holder))
            if old in _case_sensitive_rule_keys:
                continue
            upper_old = old.upper()
            cap_old = _capitalized_rule_key(old)
            if upper_old != cap_old and not _case_variant_is_reserved(upper_old):
                pre_replacements_list_4.append((upper_old, new.upper(), place_holder[:-1] + 'up$'))
            if old[0] == ' ':
                if not _case_variant_is_reserved(cap_old):
                    pre_replacements_list_4.append((cap_old, new[0] + new[1:].capitalize(), place_holder[:-1] + 'cap$'))
            else:
                if not _case_variant_is_reserved(cap_old):
                    pre_replacements_list_4.append((cap_old, new.capitalize(), place_holder[:-1] + 'cap$'))

    replacements_final_list = []
    for old, new, place_holder in pre_replacements_list_4:
        modified_placeholder = place_holder
        if old.startswith(' '):
            modified_placeholder = ' ' + modified_placeholder
            if not new.startswith(' '):
                new = ' ' + new
        if old.endswith(' '):
            modified_placeholder = modified_placeholder + ' '
            if not new.endswith(' '):
                new = new + ' '
        replacements_final_list.append((old, new, modified_placeholder))

    def _edge_spaces(value):
        return (
            len(value) - len(value.lstrip(' ')),
            len(value) - len(value.rstrip(' ')),
        )

    placeholder_cores = set()
    for old, new, placeholder in replacements_final_list:
        edge_counts = {
            _edge_spaces(old),
            _edge_spaces(new),
            _edge_spaces(placeholder),
        }
        if len(edge_counts) != 1:
            raise ValueError(
                "global replacement edge-space invariant failed: "
                f"old={old!r}, new={new!r}, placeholder={placeholder!r}"
            )
        placeholder_core = placeholder.strip(' ')
        if not placeholder_core or placeholder_core in placeholder_cores:
            raise ValueError(
                "global replacement placeholder core is empty or duplicated: "
                f"{placeholder!r}"
            )
        placeholder_cores.add(placeholder_core)

    replacements_list_for_suffix_2char_roots = []
    for i in range(len(suffix_2char_roots)):
        replaced_suffix = remove_redundant_ruby_if_identical(safe_replace(suffix_2char_roots[i], temporary_replacements_list_final))
        replacements_list_for_suffix_2char_roots.append(["$" + suffix_2char_roots[i], "$" + replaced_suffix, "$" + imported_placeholders_for_2char_replacement[i]])
        replacements_list_for_suffix_2char_roots.append(["$" + suffix_2char_roots[i].upper(), "$" + _resize_caps(replaced_suffix.upper()), "$" + imported_placeholders_for_2char_replacement[i][:-1] + 'up$'])
        replacements_list_for_suffix_2char_roots.append(["$" + suffix_2char_roots[i].capitalize(), "$" + _resize_caps(capitalize_ruby_and_rt(replaced_suffix)), "$" + imported_placeholders_for_2char_replacement[i][:-1] + 'cap$'])

    replacements_list_for_prefix_2char_roots = []
    for i in range(len(prefix_2char_roots)):
        replaced_prefix = remove_redundant_ruby_if_identical(safe_replace(prefix_2char_roots[i], temporary_replacements_list_final))
        replacements_list_for_prefix_2char_roots.append([prefix_2char_roots[i] + "$", replaced_prefix + "$", imported_placeholders_for_2char_replacement[i + 1000] + "$"])
        replacements_list_for_prefix_2char_roots.append([prefix_2char_roots[i].upper() + "$", _resize_caps(replaced_prefix.upper()) + "$", imported_placeholders_for_2char_replacement[i + 1000][:-1] + 'up$' + "$"])
        replacements_list_for_prefix_2char_roots.append([prefix_2char_roots[i].capitalize() + "$", _resize_caps(capitalize_ruby_and_rt(replaced_prefix)) + "$", imported_placeholders_for_2char_replacement[i + 4000][:-1] + 'cap$' + "$"])
        replacements_list_for_prefix_2char_roots.append([prefix_2char_roots[i].capitalize() + "$", _resize_caps(capitalize_ruby_and_rt(replaced_prefix)) + "$", imported_placeholders_for_2char_replacement[i + 1000][:-1] + 'cap$' + "$"])

    replacements_list_for_standalone_2char_roots = []
    for i in range(len(standalone_2char_roots)):
        replaced_standalone = remove_redundant_ruby_if_identical(safe_replace(standalone_2char_roots[i], temporary_replacements_list_final))
        replacements_list_for_standalone_2char_roots.append([" " + standalone_2char_roots[i] + " ", " " + replaced_standalone + " ", " " + imported_placeholders_for_2char_replacement[i + 2000] + " "])
        replacements_list_for_standalone_2char_roots.append([" " + standalone_2char_roots[i].upper() + " ", " " + _resize_caps(replaced_standalone.upper()) + " ", " " + imported_placeholders_for_2char_replacement[i + 2000][:-1] + 'up$' + " "])
        # 行頭の文頭大文字(Mi/La/Ĉu等)対応: Capitalized変種(番兵仮想スペースと組で機能)
        _cap_sa = standalone_2char_roots[i].capitalize()
        replacements_list_for_standalone_2char_roots.append([" " + _cap_sa + " ", " " + _resize_caps(capitalize_ruby_and_rt(replaced_standalone)) + " ", " " + imported_placeholders_for_2char_replacement[i + 3000][:-1] + 'cap$' + " "])
        replacements_list_for_standalone_2char_roots.append([" " + standalone_2char_roots[i].capitalize() + " ", " " + _resize_caps(capitalize_ruby_and_rt(replaced_standalone)) + " ", " " + imported_placeholders_for_2char_replacement[i + 2000][:-1] + 'cap$' + " "])

    replacements_list_for_2char = replacements_list_for_standalone_2char_roots + replacements_list_for_suffix_2char_roots + replacements_list_for_prefix_2char_roots

    pre_replacements_list_for_localized_string_1 = []
    for _, (E_root, hanzi_or_meaning) in CSV_data_imported.iterrows():
        if pd.notna(E_root) and pd.notna(hanzi_or_meaning) and '#' not in E_root and (E_root != '') and (hanzi_or_meaning != ''):
            if E_root == hanzi_or_meaning:
                pre_replacements_list_for_localized_string_1.append([E_root, hanzi_or_meaning, len(E_root)])
                pre_replacements_list_for_localized_string_1.append([E_root.upper(), hanzi_or_meaning.upper(), len(E_root)])
                pre_replacements_list_for_localized_string_1.append([E_root.capitalize(), hanzi_or_meaning.capitalize(), len(E_root)])
            else:
                pre_replacements_list_for_localized_string_1.append([E_root, dictionary_output(E_root, hanzi_or_meaning), len(E_root)])
                pre_replacements_list_for_localized_string_1.append([E_root.upper(), dictionary_output(E_root.upper(), hanzi_or_meaning.upper()), len(E_root)])
                pre_replacements_list_for_localized_string_1.append([E_root.capitalize(), dictionary_output(E_root.capitalize(), hanzi_or_meaning.capitalize()), len(E_root)])
    pre_replacements_list_for_localized_string_2 = sorted(pre_replacements_list_for_localized_string_1, key=lambda x: x[2], reverse=True)
    replacements_list_for_localized_string = []
    for kk in range(len(pre_replacements_list_for_localized_string_2)):
        replacements_list_for_localized_string.append([pre_replacements_list_for_localized_string_2[kk][0], pre_replacements_list_for_localized_string_2[kk][1], imported_placeholders_for_local_replacement[kk]])

    # Case expansion can reproduce an existing spelling (notably digit-leading
    # roots), and overlapping curated/CSV sources can do the same.  Runtime
    # replacement is first-wins, so make that policy explicit and remove dead
    # or conflicting duplicates from every deployed list.
    replacements_final_list = stable_dedupe_first_wins(replacements_final_list)
    replacements_list_for_2char = stable_dedupe_first_wins(replacements_list_for_2char)
    replacements_list_for_localized_string = stable_dedupe_first_wins(
        replacements_list_for_localized_string
    )

    combined_data = {}
    combined_data["全域替换用のリスト(列表)型配列(replacements_final_list)"] = replacements_final_list
    combined_data["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"] = replacements_list_for_2char
    combined_data["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"] = replacements_list_for_localized_string
    return combined_data
