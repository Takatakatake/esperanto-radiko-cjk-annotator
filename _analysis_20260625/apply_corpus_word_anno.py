# -*- coding: utf-8 -*-
"""Mirror corpus-confirmed atomic annotations and exact rules into app data.

These are proper names or language names whose internal spelling resembles
ordinary Esperanto roots.  Keeping them in word_anno lets explicit curated
settings render one atomic ruby without teaching a broad morphological rule.

Usage: python apply_corpus_word_anno.py [--write]
"""
import hashlib
import json
from pathlib import Path
import sys

from atomic_json import atomic_json_dump
from build_fake_coarse_transition_app_review import (
    validate as validate_fake_coarse_transition_app_review,
)
from build_fake_coarse_ff33_transition_review import (
    validate as validate_fake_coarse_ff33_transition_review,
)
from build_fake_coarse_5e_transition_review import (
    validate as validate_fake_coarse_5e_transition_review,
)
from build_fake_coarse_phase511_transition_review import (
    validate as validate_fake_coarse_phase511_transition_review,
)


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_analysis_20260625" / "out"
WRITE = "--write" in sys.argv
FAKE_COARSE_APP_REVIEW_PATH = (
    ROOT / "_analysis_20260625" / "_fake_coarse_transition_app_review.json"
)
FAKE_COARSE_APP_REVIEW = json.loads(
    FAKE_COARSE_APP_REVIEW_PATH.read_text(encoding="utf-8")
)
validate_fake_coarse_transition_app_review(FAKE_COARSE_APP_REVIEW)
FAKE_COARSE_APP_ENTRIES = FAKE_COARSE_APP_REVIEW["entries"]
FAKE_COARSE_FF33_REVIEW_PATH = (
    ROOT / "_analysis_20260625" / "_fake_coarse_ff33_transition_review.json"
)
FAKE_COARSE_FF33_REVIEW = json.loads(
    FAKE_COARSE_FF33_REVIEW_PATH.read_text(encoding="utf-8")
)
validate_fake_coarse_ff33_transition_review(FAKE_COARSE_FF33_REVIEW)
FAKE_COARSE_FF33_ENTRIES = FAKE_COARSE_FF33_REVIEW["entries"]
FAKE_COARSE_5E_REVIEW_PATH = (
    ROOT / "_analysis_20260625" / "_fake_coarse_5e_transition_review.json"
)
FAKE_COARSE_5E_REVIEW = json.loads(
    FAKE_COARSE_5E_REVIEW_PATH.read_text(encoding="utf-8")
)
validate_fake_coarse_5e_transition_review(FAKE_COARSE_5E_REVIEW)
FAKE_COARSE_5E_ENTRIES = FAKE_COARSE_5E_REVIEW["entries"]
if len(FAKE_COARSE_5E_ENTRIES) != 1:
    raise SystemExit("final 5E transition must contain exactly one entry")
_final_5e_entry = FAKE_COARSE_5E_ENTRIES[0]
if (
    _final_5e_entry.get("surface") != "promilo"
    or _final_5e_entry.get("learner_decomposition") != "pro/mil/o"
    or _final_5e_entry.get("target") != "promil/o"
    or _final_5e_entry.get("typed_roles") != "RL"
):
    raise SystemExit("final 5E promilo transition identity drift")
FAKE_COARSE_PHASE511_REVIEW_PATH = (
    ROOT / "_analysis_20260625"
    / "_fake_coarse_phase511_transition_review.json"
)
FAKE_COARSE_PHASE511_REVIEW = json.loads(
    FAKE_COARSE_PHASE511_REVIEW_PATH.read_text(encoding="utf-8")
)
validate_fake_coarse_phase511_transition_review(
    FAKE_COARSE_PHASE511_REVIEW
)
FAKE_COARSE_PHASE511_ENTRIES = FAKE_COARSE_PHASE511_REVIEW["entries"]
if {
    entry.get("surface") for entry in FAKE_COARSE_PHASE511_ENTRIES
} != {
    "arabinozo", "bifenilo", "celulozo", "laktozo",
    "deoksiozo", "deoksiribozo",
    "maltozo", "sakarozo", "grenmaltozaĵo", "amelozo",
    "fruktozo", "kalozo", "ksilozo", "rafinozo", "ribozo",
    "aldozo", "furanozo", "ketozo", "piranozo", "deoksi",
    "stakiozo",
}:
    raise SystemExit("Phase 511 reviewed Ruby surface scope drift")
KANJI_TRACK_PRODUCTIVE_TARGETS = {
    _final_5e_entry["surface"]: {
        "target": _final_5e_entry["learner_decomposition"],
        "kanji_track_only": True,
        "fake_coarse_5e_transition_managed": True,
    },
}
ATOMIC_ROOT_FAMILY_PATH = (
    ROOT / "_analysis_20260625" / "localized_atomic_root_families.json"
)
ATOMIC_ROOT_FAMILY_REVIEW = json.loads(
    ATOMIC_ROOT_FAMILY_PATH.read_text(encoding="utf-8")
)
_fake_reference = json.loads(
    (ROOT / "_analysis_20260625" / "_fake_coarse_reference_manifest.json")
    .read_text(encoding="utf-8")
)
if (
    ATOMIC_ROOT_FAMILY_REVIEW.get("schema_version") != 1
    or ATOMIC_ROOT_FAMILY_REVIEW.get("learner_sha256")
    != _fake_reference.get("sources", {}).get("learner", {}).get("sha256")
    or ATOMIC_ROOT_FAMILY_REVIEW.get("academic_sha256")
    != _fake_reference.get("sources", {}).get("academic", {}).get("sha256")
):
    raise SystemExit("localized atomic-root family source identity mismatch")
_atomic_families = ATOMIC_ROOT_FAMILY_REVIEW.get("families", [])
_atomic_families_compact = json.dumps(
    _atomic_families, ensure_ascii=False, separators=(",", ":"),
).encode("utf-8")
if (
    len(_atomic_families)
    != ATOMIC_ROOT_FAMILY_REVIEW.get("expected_families")
    or sum(len(row.get("morph_targets", [])) for row in _atomic_families)
    != ATOMIC_ROOT_FAMILY_REVIEW.get("expected_morph_targets")
    or sum(len(row.get("authority", [])) for row in _atomic_families)
    != ATOMIC_ROOT_FAMILY_REVIEW.get("expected_authority_rows")
    or hashlib.sha256(_atomic_families_compact).hexdigest().upper()
    != ATOMIC_ROOT_FAMILY_REVIEW.get("families_sha256")
    or ATOMIC_ROOT_FAMILY_REVIEW.get("families_sha256")
    != "B047D6177321BC1E3B0C73D57B57A8B20EA79679E309AC8E3BCFBAABCF57BB61"
    or ATOMIC_ROOT_FAMILY_REVIEW.get("case_policy")
    != ["lower", "initial", "upper"]
):
    raise SystemExit("localized atomic-root family fingerprint/count drift")
_fake_reference_by_line = {
    entry["learner_line"]: entry for entry in _fake_reference["entries"]
}
_atomic_family_roots = set()
PRODUCTIVE_RUBY_LEFT_TARGETS = {}
COMPOSITIONAL_FAMILY_TARGETS = {}
ATOMIC_FAMILY_CONTEXT_KEYS = {}
LEGACY_ATOMIC_FAMILY_WORD_ANNO_KEYS = set()
for _family in _atomic_families:
    _root = _family.get("root")
    _legacy = _family.get("legacy_pieces", [])
    if (
        not _root or _root in _atomic_family_roots
        or "".join(_legacy) != _root
        or _family.get("productive_boundary") != "ruby_token_left"
        or _family.get("productive_left_cases") not in (
            ["initial", "upper"], ["lower", "initial", "upper"],
        )
        or _family.get("lowercase_left_fallback") is not None
        or _family.get("compositional_target") not in (None, "bon/aer")
        or _family.get("atomic_context_key_prefix") not in (
            None, "@atomic-family:",
        )
        or not _family.get("morph_targets")
        or not _family.get("authority")
    ):
        raise SystemExit(f"invalid localized atomic-root family: {_family!r}")
    _atomic_family_roots.add(_root)
    _case_surfaces = {
        "lower": _root,
        "initial": _root.capitalize(),
        "upper": _root.upper(),
    }
    # One lowercase generator row already expands to initial/upper. When the
    # lowercase spelling is not authorized (Bonaer), retain the two explicit
    # case-sensitive rows instead.
    _emitted_cases = (
        ["lower"]
        if "lower" in _family["productive_left_cases"]
        else _family["productive_left_cases"]
    )
    _compositional_target = _family.get("compositional_target")
    _context_prefix = _family.get("atomic_context_key_prefix")
    if (_compositional_target is None) != (_context_prefix is None):
        raise SystemExit(f"atomic-family context/composition drift: {_family!r}")
    if _compositional_target is not None:
        if _compositional_target.replace("/", "") != _root:
            raise SystemExit(f"atomic-family composition reconstruction drift: {_family!r}")
        COMPOSITIONAL_FAMILY_TARGETS[_root] = {
            "target": _compositional_target,
            "allow_substring": True,
        }
        for _surface in _case_surfaces.values():
            ATOMIC_FAMILY_CONTEXT_KEYS[_surface] = _context_prefix + _surface
    for _case_name in _emitted_cases:
        _surface = _case_surfaces[_case_name]
        if _surface in PRODUCTIVE_RUBY_LEFT_TARGETS:
            raise SystemExit(f"duplicate productive Ruby-left surface: {_surface!r}")
        PRODUCTIVE_RUBY_LEFT_TARGETS[_surface] = {
            "target": _surface,
            "mode": "atomic",
            # A lowercase rule receives automatic initial/upper variants from
            # the generator. Explicit Bonaer/BONAER rows must stay exact-case.
            "case_sensitive": _case_name != "lower",
            "family_root": _root,
        }
        if _surface in ATOMIC_FAMILY_CONTEXT_KEYS:
            PRODUCTIVE_RUBY_LEFT_TARGETS[_surface][
                "ruby_context_annotation"
            ] = ATOMIC_FAMILY_CONTEXT_KEYS[_surface]
    LEGACY_ATOMIC_FAMILY_WORD_ANNO_KEYS.update(
        _family.get("legacy_word_anno_keys", [])
    )
    _morph_pairs = {
        (row.get("surface", "").casefold(), row.get("target", "").casefold())
        for row in _family["morph_targets"]
    }
    _authority_pairs = {
        (row.get("surface", "").casefold(), row.get("target", "").casefold())
        for row in _family["authority"]
    }
    if _morph_pairs != _authority_pairs:
        raise SystemExit(
            f"atomic-root morph/authority coverage drift: {_family!r}"
        )
    for _row in _family["authority"]:
        _reference = _fake_reference_by_line.get(_row.get("learner_line"))
        if (
            _reference is None
            or _reference.get("surface") != _row.get("surface")
            or _reference.get("coarse_decomposition") != _row.get("target")
        ):
            raise SystemExit(f"atomic-root authority drift: {_row!r}")
if _atomic_family_roots != {"bonaer", "novjork"}:
    raise SystemExit("localized atomic-root family set drift")
if set(PRODUCTIVE_RUBY_LEFT_TARGETS) != {
    "Bonaer", "BONAER", "novjork",
}:
    raise SystemExit("productive Ruby-left case policy drift")
if COMPOSITIONAL_FAMILY_TARGETS != {
    "bonaer": {"target": "bon/aer", "allow_substring": True},
} or set(ATOMIC_FAMILY_CONTEXT_KEYS) != {"bonaer", "Bonaer", "BONAER"}:
    raise SystemExit("localized compositional/context policy drift")
EXACT_MANIFEST_PATH = ROOT / "_analysis_20260625" / "_corpus_exact_app_manifest.json"
EXACT_MANIFEST = json.loads(EXACT_MANIFEST_PATH.read_text(encoding="utf-8"))
if EXACT_MANIFEST.get("schema_version") != 1:
    raise SystemExit("unsupported corpus exact manifest schema")
REVIEWED_EXACT_MANIFEST_PATH = (
    ROOT / "_analysis_20260625" / "_corpus_reviewed_exact_app_manifest.json"
)
if REVIEWED_EXACT_MANIFEST_PATH.exists():
    REVIEWED_EXACT_MANIFEST = json.loads(
        REVIEWED_EXACT_MANIFEST_PATH.read_text(encoding="utf-8")
    )
    if REVIEWED_EXACT_MANIFEST.get("schema_version") != 1:
        raise SystemExit("unsupported reviewed corpus exact manifest schema")
else:
    # Development bootstrap only.  The formal regeneration pipeline runs the
    # reviewed-manifest --check step before any write and therefore cannot
    # silently ship without this artifact.
    REVIEWED_EXACT_MANIFEST = {"exact_surfaces": [], "annotations": {}}
STRICT_FIX_MANIFEST_PATH = (
    ROOT / "_analysis_20260625" / "_strict_gold_reference_fixes.json"
)
STRICT_FIX_MANIFEST = json.loads(
    STRICT_FIX_MANIFEST_PATH.read_text(encoding="utf-8")
)
STRICT_FIX_ENTRIES = STRICT_FIX_MANIFEST.get("entries", [])
_strict_compact = json.dumps(
    STRICT_FIX_ENTRIES, ensure_ascii=False, separators=(",", ":"),
).encode("utf-8")
if (
    STRICT_FIX_MANIFEST.get("schema_version") != 1
    or len(STRICT_FIX_ENTRIES) != STRICT_FIX_MANIFEST.get("expected_entries")
    or hashlib.sha256(_strict_compact).hexdigest().upper()
    != STRICT_FIX_MANIFEST.get("entries_sha256")
):
    raise SystemExit("strict gold-reference fix manifest identity mismatch")
_strict_fix_by_surface = {
    entry["w"]: entry for entry in STRICT_FIX_ENTRIES
}
for _phase_entry in FAKE_COARSE_PHASE511_ENTRIES:
    _strict_entry = _strict_fix_by_surface.get(_phase_entry["surface"])
    if (
        _strict_entry is None
        or _strict_entry.get("target") != _phase_entry.get("target")
        or _strict_entry.get("typed_roles")
        != _phase_entry.get("typed_roles")
        or _strict_entry.get("exact_only") is not True
        or _strict_entry.get("boundary_only") is not True
        or _strict_entry.get("case_sensitive") is not True
        or _strict_entry.get("ruby_track_only") is not True
        or _phase_entry.get("ruby_track_only") is not True
    ):
        raise SystemExit(
            "Phase 511 strict Ruby-only rule drift: "
            f"{_phase_entry.get('surface')!r}"
        )


def curly_apostrophe_variant(value):
    """Return the visible U+2019 spelling of an ASCII-apostrophe surface."""
    return value.replace("'", "’") if "'" in value else None

# Case-sensitive whole forms are declared once with all three localized
# glosses.  This table drives both word_anno and confirmed exact rules, so a
# newly adjudicated acronym/brand/phrase cannot be added to only one side.
CASE_SENSITIVE_EXACT_GLOSSES = {
    "UK": {"ja": "[略]世界大会", "zh": "[简称]世界大会", "ko": "[약]세계대회"},
    "SAT": {"ja": "[略]世界無民族性協会", "zh": "[简称]世界无民族性协会", "ko": "[약]세계 무민족성 협회"},
    "UEA": {"ja": "[略]世エス協", "zh": "[简称]国际世界语协会", "ko": "[약]세계 에스페란토 협회"},
    "JEI": {"ja": "[略]日エス協", "zh": "[简称]日本世界语协会", "ko": "[약]일본 에스페란토 협회"},
    "IJK": {"ja": "[略]国際青年大会", "zh": "[简称]国际青年大会", "ko": "[약]국제 청년 대회"},
    "TEJO": {"ja": "[略]青年組織", "zh": "[简称]青年组织", "ko": "[약]청년 조직"},
    "UN": {"ja": "[略]国連", "zh": "[简称]联合国", "ko": "[약]유엔"},
    "KLEG": {"ja": "[略]関西エス連盟", "zh": "[简称]关西世界语联盟", "ko": "[약]간사이 에스페란토 연맹"},
    "KS": {"ja": "[略]共同セミ", "zh": "[简称]共同研讨会", "ko": "[약]공동 세미나"},
    "EPA": {"ja": "[略]エスペラント普及会", "zh": "[简称]世界语普及会", "ko": "[약]에스페란토 보급회"},
    "ILEI": {"ja": "[略]国際エス教員連盟", "zh": "[简称]国际世界语教师联盟", "ko": "[약]국제 에스페란토 교사 연맹"},
    "LKK": {"ja": "[略]現地委", "zh": "[简称]当地委员会", "ko": "[약]현지 위원회"},
    "PS": {"ja": "[略]パスポートサービス", "zh": "[简称]护照服务", "ko": "[약]여권 서비스"},
    "PS2.0": {"ja": "[略]パスポートサービス2.0", "zh": "[简称]护照服务2.0", "ko": "[약]여권 서비스2.0"},
    "Google": {"ja": "[団体]グーグル", "zh": "[团体]谷歌", "ko": "[단체]구글"},
    "DeepL": {"ja": "[AI]ディープエル", "zh": "[AI]深度翻译", "ko": "[AI]딥엘"},
    "s-ro": {"ja": "[敬称]氏", "zh": "[敬称]先生", "ko": "[경칭]씨"},
    "S-ro": {"ja": "[敬称]氏", "zh": "[敬称]先生", "ko": "[경칭]씨"},
    "d-ro": {"ja": "[略]博士", "zh": "[简称]博士", "ko": "[약]박사"},
    "D-ro": {"ja": "[略]博士", "zh": "[简称]博士", "ko": "[약]박사"},
    "prof": {"ja": "[略]教授", "zh": "[简称]教授", "ko": "[약]교수"},
    "Prof": {"ja": "[略]教授", "zh": "[简称]教授", "ko": "[약]교수"},
    "Pop Mart": {"ja": "[団体]ポップマート", "zh": "[企业]泡泡玛特", "ko": "[단체]팝마트"},
    "Labubu": {"ja": "[商品名]ラブブ", "zh": "[商品名]拉布布", "ko": "[상품명]라부부"},
    "Global Voices": {"ja": "[団体]グローバル・ボイス", "zh": "[团体]全球之声", "ko": "[단체]글로벌 보이스"},
    "SADD": {"ja": "[略]全障連", "zh": "[简称]SADD", "ko": "[약]전장연"},
    "Suvam Pal": {"ja": "[人名]スバム・パル", "zh": "[人名]苏瓦姆·帕尔", "ko": "[인명]수밤 팔"},
    "Sonja Lang": {"ja": "[人名]ソニア・ラング", "zh": "[人名]索尼娅·朗", "ko": "[인명]소냐 랑"},
    "Alberto Crescenti": {"ja": "[人名]アルベルト・クレシェンティ", "zh": "[人名]阿尔贝托·克雷森蒂", "ko": "[인명]알베르토 크레센티"},
    "Hangeul": {"ja": "[語]ハングル", "zh": "[文字]韩文", "ko": "[언어명]한글"},
    "EU": {"ja": "[略]欧州連合", "zh": "[简称]欧盟", "ko": "[약]유럽연합"},
    "AFP": {"ja": "[略]フランス通信社", "zh": "[简称]法新社", "ko": "[약]AFP"},
    "TaiwanPlus": {"ja": "[団体]台湾プラス", "zh": "[团体]TaiwanPlus", "ko": "[단체]타이완플러스"},
    "ChatGPT": {"ja": "[AI]チャットGPT", "zh": "[AI]ChatGPT", "ko": "[AI]챗GPT"},
    "Juan Pablo Schiavi": {"ja": "[人名]フアン・パブロ・スキアビ", "zh": "[人名]胡安·巴勃罗·斯基亚维", "ko": "[인명]후안 파블로 스키아비"},
    "Hankook Research": {"ja": "[団体]ハンコックリサーチ", "zh": "[机构]韩国研究", "ko": "[단체]한국리서치"},
    "SKY": {"ja": "[略]SKY大学", "zh": "[简称]SKY大学", "ko": "[약]SKY대"},
    "PDF": {"ja": "[略]PDF", "zh": "[简称]PDF", "ko": "[약]PDF"},
    "JPEU": {"ja": "[略]JPEU", "zh": "[简称]JPEU", "ko": "[약]JPEU"},
    "JJJ": {"ja": "[略]JJJ", "zh": "[简称]JJJ", "ko": "[약]JJJ"},
    "AK": {"ja": "[略]AK", "zh": "[简称]AK", "ko": "[약]AK"},
    "JEK": {"ja": "[略]JEK", "zh": "[简称]JEK", "ko": "[약]JEK"},
    "TTT": {"ja": "[略]TTT", "zh": "[简称]TTT", "ko": "[약]TTT"},
    "AEKO": {"ja": "[略]AEKO", "zh": "[简称]AEKO", "ko": "[약]AEKO"},
    "UNESKO": {"ja": "[団体]ユネスコ", "zh": "[团体]联合国教科文组织", "ko": "[단체]유네스코"},
    "GPS": {"ja": "[略]GPS", "zh": "[简称]全球定位系统", "ko": "[약]GPS"},
    "HK": {"ja": "[略]HK", "zh": "[简称]HK", "ko": "[약]HK"},
    "PEA": {"ja": "[略]PEA", "zh": "[简称]PEA", "ko": "[약]PEA"},
    "KAEM": {"ja": "[略]KAEM", "zh": "[简称]KAEM", "ko": "[약]KAEM"},
    "IKU": {"ja": "[略]国際大会大学", "zh": "[简称]国际大会大学", "ko": "[약]국제 대회 대학"},
    "ERAJ": {"ja": "[略]ERAJ", "zh": "[简称]ERAJ", "ko": "[약]ERAJ"},
    "N-ro": {"ja": "[略]番号", "zh": "[简称]号码", "ko": "[약]번호"},
    "GV": {"ja": "[略]グローバル・ボイス", "zh": "[简称]全球之声", "ko": "[약]GV"},
    "SP": {"ja": "[略]スバム・パル", "zh": "[简称]苏瓦姆·帕尔", "ko": "[약]SP"},
    "Johano Paŭlo Schiavi": {"ja": "[人名]フアン・パブロ・スキアビ", "zh": "[人名]胡安·巴勃罗·斯基亚维", "ko": "[인명]후안 파블로 스키아비"},
    "Feminism With Him": {"ja": "[団体]彼と一緒にフェミニズム", "zh": "[团体]与他同行的女性主义", "ko": "[단체]그와 함께하는 페미니즘"},
    "Feminism with Him": {"ja": "[団体]彼と一緒にフェミニズム", "zh": "[团体]与他同行的女性主义", "ko": "[단체]그와 함께하는 페미니즘"},
    "John Kuk": {"ja": "[人名]ジョン・グク", "zh": "[人名]约翰·库克", "ko": "[인명]존 쿡"},
    "Lee Han": {"ja": "[人名]リー・ハン", "zh": "[人名]李·韩", "ko": "[인명]리 핸"},
    "FM Korea": {"ja": "[団体]FMコリア", "zh": "[团体]FM韩国", "ko": "[단체]FM 코리아"},
    "The Meritocracy Trap": {"ja": "[書]メリトクラシーの罠", "zh": "[书]精英陷阱", "ko": "[책]능력주의의 함정"},
    "Korea meritokratio": {"ja": "[書]韓国のメリトクラシー", "zh": "[书]韩国的精英主义", "ko": "[책]한국의 능력주의"},
    "Korean Meritocracy": {"ja": "[書]韓国のメリトクラシー", "zh": "[书]韩国的精英主义", "ko": "[책]한국의 능력주의"},
    "ISO": {"ja": "[略]国際標準化機構", "zh": "[简称]国际标准化组织", "ko": "[약]국제표준화기구"},
    "Discord": {"ja": "[サービス]ディスコード", "zh": "[服务]Discord", "ko": "[서비스]디스코드"},
    "SC": {"ja": "[略]SC", "zh": "[简称]SC", "ko": "[약]SC"},
    "RO": {"ja": "[略]RO", "zh": "[简称]RO", "ko": "[약]RO"},
    "UAE": {"ja": "[略]アラブ首長国連邦", "zh": "[简称]阿联酋", "ko": "[약]아랍에미리트"},
    "CEO": {"ja": "[略]最高経営責任者", "zh": "[简称]首席执行官", "ko": "[약]최고경영자"},
    "CGTN": {"ja": "[略]中国国際テレビ", "zh": "[简称]中国国际电视台", "ko": "[약]중국국제텔레비전"},
    "DLT": {"ja": "[略]DLT", "zh": "[简称]DLT", "ko": "[약]DLT"},
    "NBA": {"ja": "[略]米プロバスケ", "zh": "[简称]美国职业篮球联赛", "ko": "[약]미국프로농구"},
    "LLM": {"ja": "[AI]大規模言語モデル", "zh": "[AI]大型语言模型", "ko": "[AI]대규모 언어 모델"},
    "NHK": {"ja": "[団体]日本放送協会", "zh": "[机构]日本广播协会", "ko": "[단체]일본방송협회"},
    "SOJO": {"ja": "[略]SOJO", "zh": "[简称]SOJO", "ko": "[약]SOJO"},
    "PEJ": {"ja": "[略]PEJ", "zh": "[简称]PEJ", "ko": "[약]PEJ"},
    "NEspA": {"ja": "[略]NEspA", "zh": "[简称]NEspA", "ko": "[약]NEspA"},
    "MAML": {"ja": "[略]MAML", "zh": "[简称]MAML", "ko": "[약]MAML"},
    "QR": {"ja": "[略]QRコード", "zh": "[简称]二维码", "ko": "[약]QR코드"},
    "LRO": {"ja": "[略]LRO", "zh": "[简称]LRO", "ko": "[약]LRO"},
    "NaCl": {"ja": "[化学式]塩化ナトリウム", "zh": "[化学式]氯化钠", "ko": "[화학식]염화나트륨"},
    "Facebook": {"ja": "[サービス]フェイスブック", "zh": "[平台]脸书", "ko": "[서비스]페이스북"},
    "TikTok": {"ja": "[サービス]ティックトック", "zh": "[平台]抖音", "ko": "[서비스]틱톡"},
    "WhatsApp": {"ja": "[サービス]ワッツアップ", "zh": "[服务]WhatsApp", "ko": "[서비스]왓츠앱"},
    "YouTube": {"ja": "[サービス]ユーチューブ", "zh": "[平台]YouTube", "ko": "[서비스]유튜브"},
    "eBay": {"ja": "[企業]イーベイ", "zh": "[企业]易贝", "ko": "[기업]이베이"},
    "Zoom": {"ja": "[サービス]ズーム", "zh": "[服务]Zoom", "ko": "[서비스]줌"},
    "Ipernity": {"ja": "[サービス]イペルニティ", "zh": "[服务]Ipernity", "ko": "[서비스]이퍼니티"},
    "PET": {"ja": "[略]PET", "zh": "[简称]PET", "ko": "[약]PET"},
    "Maria": {"ja": "[人名]マリア", "zh": "[人名]玛丽亚", "ko": "[인명]마리아"},
    "Tokipono": {"ja": "[言語名]トキポナ", "zh": "[语言名]道本语", "ko": "[언어명]토키포나"},
    "Unesko": {"ja": "[団体]ユネスコ", "zh": "[团体]联合国教科文组织", "ko": "[단체]유네스코"},
    "TV": {"ja": "[略]テレビ", "zh": "[简称]电视", "ko": "[약]TV"},
    "aKE": {"ja": "[略]紀元前", "zh": "[简称]公元前", "ko": "[약]aKE"},
    "RĈ": {"ja": "[略]RĈ", "zh": "[简称]RĈ", "ko": "[약]RĈ"},
    "EsFes": {"ja": "[略]エスフェス", "zh": "[简称]EsFes", "ko": "[약]EsFes"},
    "Disney": {"ja": "[団体]ディズニー", "zh": "[企业]迪士尼", "ko": "[단체]디즈니"},
    "HarperCollins": {"ja": "[団体]HarperCollins", "zh": "[出版社]哈珀柯林斯", "ko": "[출판사]하퍼콜린스"},
    "Routledge": {"ja": "[団体]Routledge", "zh": "[出版社]劳特利奇", "ko": "[출판사]라우틀리지"},
    "The Financial Times": {"ja": "[雑誌]フィナンシャル・タイムズ", "zh": "[报刊]金融时报", "ko": "[잡지]파이낸셜 타임스"},
    "The Conversation": {"ja": "[雑誌]ザ・カンバセーション", "zh": "[杂志]对话", "ko": "[잡지]더 컨버세이션"},
    "Harry Potter": {"ja": "[書]ハリー・ポッター", "zh": "[书]哈利·波特", "ko": "[책]해리 포터"},
    "Gen-Z": {"ja": "[時代]Z世代", "zh": "[世代]Z世代", "ko": "[시대]Z세대"},
    "L'Espérantiste": {"ja": "[雑誌]レスペランティスト", "zh": "[杂志]世界语者", "ko": "[잡지]레스페란티스트"},
    "Esp": {"ja": "[略]エスペラント", "zh": "[简称]世界语", "ko": "[약]에스페란토"},
    "jan.": {"ja": "[略]1月", "zh": "[简称]1月", "ko": "[약]1월"},
    "Vd": {"ja": "[略]参照", "zh": "[简称]参见", "ko": "[약]참조"},
    "Univ": {"ja": "[略]大学", "zh": "[简称]大学", "ko": "[약]대학"},
}

# Typed whole-ruby rules with a case homograph are kept out of the ordinary
# exact table so they produce one confirmed entry, not a duplicate untyped row.
MANAGED_TYPED_EXACT_GLOSSES = {
    "Aŭdu": {"ja": "[人名]アウドゥ", "zh": "[人名]Aŭdu", "ko": "[인명]Aŭdu"},
}

ANNOTATIONS = {
    "ja": {
        "kanto": "[地名]関東",
        "paiŭan": "パイワン",
        "ŝona": "ショナ",
        "ursul": "ウルスラ",
        "renkejtiĝo": "[団体]集い(造語)",
        "RenKEJtiĝo": "[団体]集い(造語)",
        "jutub": "ユーチューブ",
        "taranaki": "[地名]タラナキ",
        "Taranaki": "[地名]タラナキ",
        "s-ino": "[敬称]女史",
        "urewera": "[地名]ウレウェラ",
        "Urewera": "[地名]ウレウェラ",
        "whanganui": "[地名]ワンガヌイ",
        "Whanganui": "[地名]ワンガヌイ",
        "egmont": "[地名]エグモント",
        "Egmont": "[地名]エグモント",
        "davao": "[地名]ダバオ",
        "golfo": "湾",
        "hiv": "[略]HIV",
        "khz": "[単位]キロヘルツ",
        "mhz": "[単位]メガヘルツ",
        "ddt": "[略]DDT",
        "tejo": "青年組織",
        "kaŭn": "[地名]カウナス",
        "bikini": "[地名]ビキニ",
        "buenos-aires": "[地名]ブエノスアイレス",
        "bonaer": "[地名]ブエノスアイレス",
        "novjork": "[地名]ニューヨーク",
        "kriptografi": "暗号学",
        "anestez": "麻酔する",
        "davaan": "[人]ダバオ住民",
        "Sejong": "[地名]世宗",
        "kampus": "キャンパス",
        "Ivo": "[人名]イヴォ",
        "f-ino": "[敬称]令嬢",
        "ioj": "何か(複数)",
        "iojn": "何か(複数・対格)",
        "Tang": "[時代]唐",
        "meme": "ミーム",
        "Brazili": "[地名]ブラジリア",
        "jurnal": "新聞",
    },
    "zh": {
        "kanto": "[地名]关东",
        "paiŭan": "排湾",
        "ŝona": "绍纳",
        "ursul": "乌尔苏拉",
        "renkejtiĝo": "[团体]聚会(造词)",
        "RenKEJtiĝo": "[团体]聚会(造词)",
        "jutub": "YouTube",
        "taranaki": "[地名]塔拉纳基",
        "Taranaki": "[地名]塔拉纳基",
        "s-ino": "[敬称]女士",
        "urewera": "[地名]乌雷韦拉",
        "Urewera": "[地名]乌雷韦拉",
        "whanganui": "[地名]旺阿努伊",
        "Whanganui": "[地名]旺阿努伊",
        "egmont": "[地名]埃格蒙特",
        "Egmont": "[地名]埃格蒙特",
        "davao": "[地名]达沃",
        "golfo": "海湾",
        "hiv": "艾滋病毒",
        "khz": "千赫",
        "mhz": "兆赫",
        "ddt": "滴滴涕",
        "tejo": "青年组织",
        "kaŭn": "[地名]考纳斯",
        "bikini": "[地名]比基尼",
        "buenos-aires": "[地名]布宜诺斯艾利斯",
        "bonaer": "[地名]布宜诺斯艾利斯",
        "novjork": "[地名]纽约",
        "kriptografi": "密码学",
        "anestez": "麻醉",
        "davaan": "[人]达沃居民",
        "Sejong": "[地名]世宗",
        "kampus": "校园",
        "Ivo": "[人名]伊沃",
        "f-ino": "[敬称]小姐",
        "ioj": "某些事物",
        "iojn": "某些事物(宾格)",
        "Tang": "[时代]唐",
        "meme": "迷因",
        "Brazili": "[地名]巴西利亚",
        "jurnal": "报纸",
    },
    "ko": {
        "kanto": "[지명]간토",
        "paiŭan": "파이완",
        "ŝona": "쇼나",
        "ursul": "우르술라",
        "renkejtiĝo": "[단체]모임(조어)",
        "RenKEJtiĝo": "[단체]모임(조어)",
        "jutub": "유튜브",
        "taranaki": "[지명]타라나키",
        "Taranaki": "[지명]타라나키",
        "s-ino": "[경칭]여사",
        "urewera": "[지명]우레웨라",
        "Urewera": "[지명]우레웨라",
        "whanganui": "[지명]웡가누이",
        "Whanganui": "[지명]웡가누이",
        "egmont": "[지명]에그몬트",
        "Egmont": "[지명]에그몬트",
        "davao": "[지명]다바오",
        "golfo": "만",
        "hiv": "[약]HIV",
        "khz": "[단위]킬로헤르츠",
        "mhz": "[단위]메가헤르츠",
        "ddt": "[약]DDT",
        "tejo": "청년조직",
        "kaŭn": "[지명]카우나스",
        "bikini": "[지명]비키니",
        "buenos-aires": "[지명]부에노스아이레스",
        "bonaer": "[지명]부에노스아이레스",
        "novjork": "[지명]뉴욕",
        "kriptografi": "암호학",
        "anestez": "마취하다",
        "davaan": "[사람]다바오 주민",
        "Sejong": "[지명]세종",
        "kampus": "캠퍼스",
        "Ivo": "[인명]이보",
        "f-ino": "[경칭]양",
        "ioj": "어떤 것들",
        "iojn": "어떤 것들을",
        "Tang": "[시대]당",
        "meme": "밈",
        "Brazili": "[지명]브라질리아",
        "jurnal": "신문",
    },
}

# Explicit case-sensitive Ruby-left rules cannot borrow the lowercase key at
# generation time. Mirror only their reviewed localized gloss, retaining the
# written rb spelling; this does not create a lowercase productive fallback.
for _surface, _spec in PRODUCTIVE_RUBY_LEFT_TARGETS.items():
    if not _spec["case_sensitive"] or _spec["mode"] != "atomic":
        continue
    for _language in ANNOTATIONS:
        _source_gloss = ANNOTATIONS[_language].get(_spec["family_root"])
        if not _source_gloss:
            raise SystemExit(
                f"{_language}: missing atomic-family gloss for {_surface!r}"
            )
        ANNOTATIONS[_language][_surface] = _source_gloss

# Ordinary slashless word_anno keys would overwrite E_stem ``bon/aer`` with
# one atomic ``bonaer`` span. Keep the gloss behind reserved, case-exact keys
# which only reviewed atomic settings can request.
ATOMIC_FAMILY_CONTEXT_ANNOTATIONS = {language: {} for language in ANNOTATIONS}
for _surface, _key in ATOMIC_FAMILY_CONTEXT_KEYS.items():
    for _language in ANNOTATIONS:
        _gloss = ANNOTATIONS[_language].get(_surface)
        if not _gloss:
            raise SystemExit(
                f"{_language}: missing atomic-family context gloss for {_surface!r}"
            )
        ATOMIC_FAMILY_CONTEXT_ANNOTATIONS[_language][_key] = [[_surface, _gloss]]

# Contextual homographs use a reserved key which is never a normal Esperanto
# surface.  A typed exact rule can therefore annotate kaj="wharf" or al="wing"
# without changing standalone kaj="and", al="toward", or sin=si/n.
TYPED_CONTEXT_GLOSSES = {
    ("alo", 0, "al"): {
        "ja": "翼", "zh": "翅膀", "ko": "날개",
    },
    ("kajo", 0, "kaj"): {
        "ja": "波止場", "zh": "码头", "ko": "부두",
    },
    ("videaĵo", 0, "vide"): {
        "ja": "映像", "zh": "视频", "ko": "영상",
    },
    ("diplomatio", 0, "diplomati"): {
        "ja": "外交", "zh": "外交", "ko": "외교",
    },
    ("Sejong-kampuso", 0, "Sejong"): {
        "ja": "[地名]世宗", "zh": "[地名]世宗", "ko": "[지명]세종",
    },
    ("Sejong-kampuso", 2, "kampus"): {
        "ja": "キャンパス", "zh": "校园", "ko": "캠퍼스",
    },
    ("Ivo", 0, "Ivo"): {
        "ja": "[人名]イヴォ", "zh": "[人名]伊沃", "ko": "[인명]이보",
    },
    ("f-ino", 0, "f-ino"): {
        "ja": "[敬称]令嬢", "zh": "[敬称]小姐", "ko": "[경칭]양",
    },
    # Hokkaido is a borrowed place-name root, not hokkajd+o.  Lower/upper
    # exact forms are declared here; the reviewed Initial-cap annotation is
    # normalized below from the same three-language gloss authority.
    ("hokkajdon", 0, "hokkajdo"): {
        "ja": "[地名]北海道", "zh": "[地名]北海道", "ko": "[지명]홋카이도",
    },
    ("HOKKAJDON", 0, "HOKKAJDO"): {
        "ja": "[地名]北海道", "zh": "[地名]北海道", "ko": "[지명]홋카이도",
    },
}

# The staged manifests supply only explicitly reviewed localized fallbacks.
# Historical manifests used one ``exact_annotation`` object; the Phase 511
# semantic review can carry several indexed ``exact_annotations`` for a single
# word.  Normalize both forms fail-closed, and never turn these contextual
# glosses into productive root annotations.
def _iter_reviewed_exact_annotations(entry):
    singular = entry.get("exact_annotation")
    plural = entry.get("exact_annotations")
    if singular is not None and plural is not None:
        raise SystemExit(
            f"mixed exact annotation schemas: {entry.get('surface')!r}"
        )
    pieces = [piece for piece in entry["target"].split("/") if piece]
    roles = entry.get("typed_roles", "")
    if len(roles) != len(pieces):
        raise SystemExit(
            f"invalid typed exact target: {entry.get('surface')!r}"
        )
    if singular is not None:
        matches = [
            index for index, piece in enumerate(pieces)
            if piece == singular.get("piece")
        ]
        if len(matches) != 1:
            raise SystemExit(
                f"ambiguous legacy exact annotation: {entry.get('surface')!r}"
            )
        plural = [{**singular, "index": matches[0]}]
    elif plural is None:
        return ()
    if not isinstance(plural, list) or not plural:
        raise SystemExit(
            f"invalid exact annotation list: {entry.get('surface')!r}"
        )
    normalized = []
    seen = set()
    for annotation in plural:
        index = annotation.get("index")
        glosses = annotation.get("glosses")
        if (
            not isinstance(index, int)
            or index < 0
            or index >= len(pieces)
            or pieces[index] != annotation.get("piece")
            or roles[index] != "R"
            or index in seen
            or not isinstance(glosses, dict)
            or set(glosses) != {"ja", "zh", "ko"}
            or any(not isinstance(value, str) or not value for value in glosses.values())
        ):
            raise SystemExit(
                f"invalid indexed exact annotation: {entry.get('surface')!r}"
            )
        seen.add(index)
        normalized.append((index, pieces[index], glosses))
    return tuple(normalized)


for _fake_entry in (
    FAKE_COARSE_APP_ENTRIES + FAKE_COARSE_PHASE511_ENTRIES
):
    for _fake_index, _fake_piece, _fake_glosses in (
        _iter_reviewed_exact_annotations(_fake_entry)
    ):
        _fake_key = (_fake_entry["surface"], _fake_index, _fake_piece)
        if _fake_key in TYPED_CONTEXT_GLOSSES:
            raise SystemExit(
                f"duplicate fake-coarse typed annotation: {_fake_key!r}"
            )
        TYPED_CONTEXT_GLOSSES[_fake_key] = dict(_fake_glosses)

# The last strict-gate residuals are mostly technical abbreviations, anatomy,
# and hyphenated proper-name components absent from all three ordinary CSVs.
# Keep their localized glosses contextual: Andora in Andora-la-Velo is useful,
# but it must not silently redefine a same-spelled standalone dictionary key.
STRICT_TYPED_PIECE_GLOSSES = {
    "ADP": {"ja": "[略]アデノシン二リン酸", "zh": "[简称]腺苷二磷酸", "ko": "[약]아데노신 이인산"},
    "AMP": {"ja": "[略]アデノシン一リン酸", "zh": "[简称]腺苷一磷酸", "ko": "[약]아데노신 일인산"},
    "ATP": {"ja": "[略]アデノシン三リン酸", "zh": "[简称]腺苷三磷酸", "ko": "[약]아데노신 삼인산"},
    "AZT": {"ja": "[略]アジドチミジン", "zh": "[简称]叠氮胸苷", "ko": "[약]아지도티미딘"},
    "MHz": {"ja": "[略]メガヘルツ", "zh": "[简称]兆赫", "ko": "[약]메가헤르츠"},
    "Andora": {"ja": "[地名]アンドラ", "zh": "[地名]安道尔", "ko": "[지명]안도라"},
    # These capitalized roots occur in newly reviewed, case-sensitive
    # geographic exact rules.  Contextual glosses prevent lowercase
    # homographs such as arg (Argo ship), ret (net), and umbr from leaking
    # into the place-name readings.
    "Arg": {"ja": "[地名]アルゴス", "zh": "[地名]阿尔戈斯", "ko": "[지명]아르고스"},
    "Eol": {"ja": "[地名]アイオリス", "zh": "[地名]埃奥利斯", "ko": "[지명]아이올리스"},
    "Frig": {"ja": "[地名]フリギア", "zh": "[地名]弗里吉亚", "ko": "[지명]프리기아"},
    "Ligur": {"ja": "[地名]リグーリア", "zh": "[地名]利古里亚", "ko": "[지명]리구리아"},
    "Ohi": {"ja": "[地名]オハイオ", "zh": "[地名]俄亥俄", "ko": "[지명]오하이오"},
    "Ret": {"ja": "[地名]レーティア", "zh": "[地名]雷蒂亚", "ko": "[지명]레티아"},
    "Umbr": {"ja": "[地名]ウンブリア", "zh": "[地名]翁布里亚", "ko": "[지명]움브리아"},
    "la": {"ja": "定冠詞", "zh": "定冠词", "ko": "정관사"},
    "Buenos": {"ja": "[地名]ブエノス", "zh": "[地名]布宜诺斯", "ko": "[지명]부에노스"},
    "Ajres": {"ja": "[地名]アイレス", "zh": "[地名]艾利斯", "ko": "[지명]아이레스"},
    "Cseh": {"ja": "[人名]チェ", "zh": "[人名]切赫", "ko": "[인명]체"},
    "DNA": {"ja": "[略]デオキシリボ核酸", "zh": "[简称]脱氧核糖核酸", "ko": "[약]디옥시리보핵산"},
    "Dalai": {"ja": "[称号]ダライ", "zh": "[称号]达赖", "ko": "[칭호]달라이"},
    "E-o": {"ja": "[略]エスペラント", "zh": "[简称]世界语", "ko": "[약]에스페란토"},
    "FTP": {"ja": "[略]ファイル転送プロトコル", "zh": "[简称]文件传输协议", "ko": "[약]파일 전송 프로토콜"},
    "Fuĵi": {"ja": "[地名]富士", "zh": "[地名]富士", "ko": "[지명]후지"},
    "H": {"ja": "水素", "zh": "氢", "ko": "수소"},
    "Harun": {"ja": "[人名]ハールーン", "zh": "[人名]哈伦", "ko": "[인명]하룬"},
    "Raŝid": {"ja": "[人名]ラシード", "zh": "[人名]拉希德", "ko": "[인명]라시드"},
    "al": {"ja": "[冠詞]アル", "zh": "[冠词]阿尔", "ko": "[관사]알"},
    "Kapet": {"ja": "[人名]カペー", "zh": "[人名]卡佩", "ko": "[인명]카페"},
    "Kolonja": {"ja": "[地名]コロニア", "zh": "[地名]科洛尼亚", "ko": "[지명]콜로니아"},
    "Ponape": {"ja": "[地名]ポナペ", "zh": "[地名]波纳佩", "ko": "[지명]포나페"},
    "LSD": {"ja": "[略]リゼルグ酸ジエチルアミド", "zh": "[简称]麦角酸二乙酰胺", "ko": "[약]리세르그산 디에틸아미드"},
    "Levi": {"ja": "[人名]レビ", "zh": "[人名]利未", "ko": "[인명]레위"},
    "Me": {"ja": "[化学記号]金属・メチル", "zh": "[化学符号]金属或甲基", "ko": "[화학 기호]금속·메틸"},
    "Hampŝir": {"ja": "[地名]ハンプシャー", "zh": "[地名]汉普郡", "ko": "[지명]햄프셔"},
    "Jorki": {"ja": "[地名]ヨーク", "zh": "[地名]约克", "ko": "[지명]요크"},
    "Skoti": {"ja": "[地名]スコットランド", "zh": "[地名]苏格兰", "ko": "[지명]스코틀랜드"},
    "Karolin": {"ja": "[地名]カロライナ", "zh": "[地名]卡罗来纳", "ko": "[지명]캐롤라이나"},
    "Plata": {"ja": "[地名]ラプラタ", "zh": "[地名]拉普拉塔", "ko": "[지명]라플라타"},
    "Moresb": {"ja": "[地名]モレスビー", "zh": "[地名]莫尔兹比", "ko": "[지명]모르즈비"},
    "Said": {"ja": "[地名]サイド", "zh": "[地名]塞得", "ko": "[지명]사이드"},
    "Port": {"ja": "港", "zh": "港", "ko": "항구"},
    "Porto": {"ja": "[地名]ポルト", "zh": "[地名]波尔图", "ko": "[지명]포르토"},
    "Algr": {"ja": "[地名]アレグレ", "zh": "[地名]阿莱格里", "ko": "[지명]알레그리"},
    "Rik": {"ja": "[地名]リコ", "zh": "[地名]黎各", "ko": "[지명]리코"},
    "Puerto": {"ja": "[地名]プエルト", "zh": "[地名]波多", "ko": "[지명]푸에르토"},
    "RNA": {"ja": "[略]リボ核酸", "zh": "[简称]核糖核酸", "ko": "[약]리보핵산"},
    "Rio": {"ja": "[地名]リオ", "zh": "[地名]里约", "ko": "[지명]리우"},
    "de": {"ja": "の", "zh": "的", "ko": "의"},
    "Ĵanejr": {"ja": "[地名]デジャネイロ", "zh": "[地名]热内卢", "ko": "[지명]데자네이루"},
    "SOS": {"ja": "[略]遭難信号", "zh": "[简称]求救信号", "ko": "[약]조난 신호"},
    "Santo": {"ja": "[地名]サント", "zh": "[地名]圣多", "ko": "[지명]산토"},
    "Doming": {"ja": "[地名]ドミンゴ", "zh": "[地名]多明各", "ko": "[지명]도밍고"},
    "Saudi": {"ja": "[地名]サウジ", "zh": "[地名]沙特", "ko": "[지명]사우디"},
    "Siera": {"ja": "[地名]シエラ", "zh": "[地名]塞拉", "ko": "[지명]시에라"},
    "Leon": {"ja": "[地名]レオネ", "zh": "[地名]利昂", "ko": "[지명]리온"},
    "Nevad": {"ja": "[地名]ネバダ", "zh": "[地名]内华达", "ko": "[지명]네바다"},
    "Sir": {"ja": "[地名]シル", "zh": "[地名]锡尔", "ko": "[지명]시르"},
    "Darj": {"ja": "[地名]ダリア", "zh": "[地名]达里亚", "ko": "[지명]다리야"},
    "Sri": {"ja": "[地名]スリ", "zh": "[地名]斯里", "ko": "[지명]스리"},
    "Ĵajavardanepur": {"ja": "[地名]ジャヤワルダナプラ", "zh": "[地名]贾亚瓦德纳普拉", "ko": "[지명]자야와르데네푸라"},
    "T": {"ja": "[字母]T", "zh": "[字母]T", "ko": "[글자]T"},
    "TNT": {"ja": "[略]トリニトロトルエン", "zh": "[简称]三硝基甲苯", "ko": "[약]트라이나이트로톨루엔"},
    "X": {"ja": "[字母]X", "zh": "[字母]X", "ko": "[글자]X"},
    "micv": {"ja": "戒律", "zh": "诫命", "ko": "계명"},
    "bar": {"ja": "息子", "zh": "儿子", "ko": "아들"},
    "blefarit": {"ja": "眼瞼炎", "zh": "睑缘炎", "ko": "안검염"},
    "dakrioadenit": {"ja": "涙腺炎", "zh": "泪腺炎", "ko": "누선염"},
    "deferent": {"ja": "輸精管", "zh": "输精管", "ko": "정관"},
    "deism": {"ja": "理神論", "zh": "自然神论", "ko": "이신론"},
    "deist": {"ja": "理神論者", "zh": "自然神论者", "ko": "이신론자"},
    "diskredit": {"ja": "信用を失墜させる", "zh": "使失去信誉", "ko": "신용을 실추시키다"},
    "esp": {"ja": "[略]エスペラント", "zh": "[简称]世界语", "ko": "[약]에스페란토"},
    "gramen": {"ja": "イネ科植物", "zh": "禾本科植物", "ko": "벼과 식물"},
    "anc": {"ja": "性・量", "zh": "性质·量", "ko": "성질·양"},
    # psikokirurgio alone uses the finer PIV root kirurg.  Preserve the
    # established coarse-root meaning of kirurgi instead of borrowing the
    # ordinary kirurg gloss "surgeon" from the language CSVs.
    "kirurg": {"ja": "外科学", "zh": "外科", "ko": "외과"},
    "k": {"ja": "[略]スプーン", "zh": "[简称]汤匙", "ko": "[약]숟가락"},
    "k-o": {"ja": "[略]スプーン", "zh": "[简称]汤匙", "ko": "[약]숟가락"},
    "mejbomit": {"ja": "マイボーム腺炎", "zh": "睑板腺炎", "ko": "마이봄샘염"},
    "pH": {"ja": "水素イオン指数", "zh": "氢离子指数", "ko": "수소 이온 농도 지수"},
    "pK": {"ja": "イオン化定数", "zh": "电离常数", "ko": "이온화 상수"},
    "spondilit": {"ja": "脊椎炎", "zh": "脊椎炎", "ko": "척추염"},
    "strateg": {"ja": "戦略", "zh": "战略", "ko": "전략"},
    "vojaĝ": {"ja": "旅行", "zh": "旅行", "ko": "여행"},
    "Ĉefeĉ": {"ja": "[名称]チェフェチ", "zh": "[名称]切费奇", "ko": "[명칭]체페치"},
    "ĥilopod": {"ja": "唇脚類", "zh": "唇足类", "ko": "순각류"},
    "Vel": {"ja": "[地名]ベリャ", "zh": "[地名]城", "ko": "[지명]라베야"},
    "Sudan": {"ja": "[地名]スーダン", "zh": "[地名]苏丹", "ko": "[지명]수단"},
    "Baal-Zebub": {"ja": "[聖名]バアル・ゼブブ", "zh": "[圣名]巴力·西卜", "ko": "[성서명]바알세붑"},
    "Baal-Zebul": {"ja": "[聖名]バアル・ゼブル", "zh": "[圣名]巴力·西布勒", "ko": "[성서명]바알세불"},
    "En-Dor": {"ja": "[聖地]エン・ドル", "zh": "[圣地]隐多珥", "ko": "[성서 지명]엔돌"},
    "Ho-Ĉi-Min": {"ja": "[人名]ホー・チ・ミン", "zh": "[人名]胡志明", "ko": "[인명]호찌민"},
    "Ut-Napiŝtim": {"ja": "[神話]ウトナピシュティム", "zh": "[神话]乌特纳庇什提姆", "ko": "[신화]우트나피쉬팀"},
    "gik-gak": {"ja": "ガーガー", "zh": "嘎嘎", "ko": "꽥꽥"},
    "k-do": {"ja": "[略]同志", "zh": "[简称]同志", "ko": "[약]동지"},
    "riĉ-raĉ": {"ja": "ビリビリ", "zh": "撕拉", "ko": "쭉쭉"},
    "ace": {"ja": "[化学接頭辞]アセ", "zh": "[化学前缀]乙炔・乙烯关联", "ko": "[화학 접두사]아세"},
}

_strict_ruby_pieces = set()
for _entry in STRICT_FIX_ENTRIES:
    _parts = [part for part in _entry["target"].split("/") if part]
    _roles = _entry.get("typed_roles", "")
    if len(_parts) != len(_roles):
        raise SystemExit(f"invalid strict typed entry: {_entry!r}")
    for _index, (_piece, _role) in enumerate(zip(_parts, _roles)):
        if _role != "R":
            continue
        _strict_ruby_pieces.add(_piece)
        _glosses = STRICT_TYPED_PIECE_GLOSSES.get(_piece)
        if _glosses is None:
            continue
        _key = (_entry["w"], _index, _piece)
        if _key in TYPED_CONTEXT_GLOSSES and TYPED_CONTEXT_GLOSSES[_key] != _glosses:
            raise SystemExit(f"conflicting strict typed gloss: {_key!r}")
        TYPED_CONTEXT_GLOSSES[_key] = _glosses
_unused_strict_glosses = set(STRICT_TYPED_PIECE_GLOSSES) - _strict_ruby_pieces
if _unused_strict_glosses:
    raise SystemExit(
        f"strict typed glosses are unused: {sorted(_unused_strict_glosses)!r}"
    )

# Exact slash-keyed compound annotations disambiguate a root only in that
# composition.  They are never copied onto the standalone homograph.
SPLIT_CONTEXT_ANNOTATIONS = {
    "ja": {
        "pasi/grafi": [["pasi", "全"], ["grafi", "記述"]],
    },
    "zh": {
        "pasi/grafi": [["pasi", "全"], ["grafi", "记述"]],
    },
    "ko": {
        "pasi/grafi": [["pasi", "전체"], ["grafi", "기술"]],
    },
}

# The pinned corpus manifest supplies every multi-word, Latin-Extended and
# punctuated atomic base.  Existing hand-written entries remain authoritative
# because they often provide a better Chinese/Korean translation than the
# safe localized-tag + original-spelling fallback used by the builder.
for root, row in EXACT_MANIFEST["annotations"].items():
    glosses = row.get("glosses", {})
    if set(glosses) != set(ANNOTATIONS):
        raise SystemExit(f"{root}: exact manifest must define ja/zh/ko glosses")
    for annotation_root in filter(None, (root, curly_apostrophe_variant(root))):
        for language, gloss in glosses.items():
            ANNOTATIONS[language].setdefault(annotation_root, gloss)

for surface, glosses in CASE_SENSITIVE_EXACT_GLOSSES.items():
    if set(glosses) != set(ANNOTATIONS):
        raise SystemExit(f"{surface}: exact gloss must define ja/zh/ko")
    for annotation_surface in filter(
        None, (surface, curly_apostrophe_variant(surface)),
    ):
        for language, gloss in glosses.items():
            ANNOTATIONS[language][annotation_surface] = gloss

for surface, glosses in MANAGED_TYPED_EXACT_GLOSSES.items():
    if set(glosses) != set(ANNOTATIONS):
        raise SystemExit(f"{surface}: typed exact gloss must define ja/zh/ko")
    for language, gloss in glosses.items():
        ANNOTATIONS[language][surface] = gloss

APP = {"ja": "JA", "zh": "ZH", "ko": "KO"}

# Historical place-name annotations included the grammatical -o.  Mirror each
# existing localized gloss onto the actual root used by confirmed splits.
MIRRORED_ATOMIC_ROOTS = {
    "katmand": "katmando",
    "nurnberg": "nurnbergo",
    "burn": "burno",
    "mukden": "mukdeno",
    "kamakur": "kamakuro",
    "enoŝim": "enoŝimo",
    "tuskol": "tuskolo",
    "taragon": "taragono",
    "ĝiron": "ĝirono",
    "smolenk": "smolenko",
    "moravi": "morav",
}

# This is the single source of truth for corpus-only whole-form rules.  The
# general morphological corrections already in confirmed_tier30 are retained;
# only entries whose ``w`` is listed here are replaced deterministically.
MANAGED_EXACT_TARGETS = {
    # Earlier corpus adjudications.  Their normal case variants remain useful.
    "RenKEJtiĝon": ("RenKEJtiĝo/n", False),
    "Taranaki": ("Taranaki", False),
    "s-ino": ("s-ino", False),
    "Urewera": ("Urewera", False),
    "Whanganui": ("Whanganui", False),
    "Egmont": ("Egmont", False),
    # Independent correlatives and their inflections are whole rubies; -ioj is
    # bare only when it follows a country/root stem (Japan/ioj).
    "ioj": ("ioj", False),
    "iojn": ("iojn", False),
    # Acronyms, brands and abbreviations must not leak into lowercase roots.
    **{surface: (surface, True) for surface in CASE_SENSITIVE_EXACT_GLOSSES},
    # Hyphenated inflections keep the acronym ruby atomic and the suffix bare.
    "UK-oj": ("UK/-/oj", True),
    "UK-on": ("UK/-/on", True),
    # The atomic key is prof/Prof; these higher-priority punctuation wrappers
    # keep the sentence dot outside ruby despite the legacy prof. CSV entry.
    "prof.": ("prof/.", True),
    "Prof.": ("Prof/.", True),
}

# Do not add a bounded bare ``bonaer`` correction. The generator's reviewed
# E_stem ``bon/aer`` rule is deliberately unbounded, so it preserves the real
# composition in lowercase and token-internal forms (bonaerdevena,
# malbonaero, xBonaer...). A bounded correction for the same slashless stem
# would pop that reusable rule before registering its space-guarded variant.

for _surface, (_target, _case_sensitive) in list(MANAGED_EXACT_TARGETS.items()):
    _curly_surface = curly_apostrophe_variant(_surface)
    if _curly_surface is None:
        continue
    _curly_target = curly_apostrophe_variant(_target)
    if _curly_surface in MANAGED_EXACT_TARGETS:
        raise SystemExit(f"duplicate curly exact surface: {_curly_surface!r}")
    MANAGED_EXACT_TARGETS[_curly_surface] = (
        _curly_target or _target, _case_sensitive,
    )

# Productive morphology remains in the ordinary confirmed tier.  These rows
# repair the reusable root/affix analysis, while the observed surface also gets
# a typed exact row below when a homographic root needs a context-specific rt.
MANAGED_MORPH_TARGETS = {
    "alo": {"target": "al/o", "context_annotation": "@typed:alo:0"},
    "kajo": {"target": "kaj/o", "context_annotation": "@typed:kajo:0"},
    "videaĵo": {"target": "vide/aĵ/o"},
    "diplomatio": {"target": "diplomati/o"},
    "sindevigo": {"target": "sin/dev/ig/o"},
    "singarde": {"target": "sin/gard/e"},
    "sinmortigo": {"target": "sin/mort/ig/o"},
    "Sejong-kampuso": {"target": "Sejong/-/kampus/o", "case_sensitive": True},
    "d-ron": {"target": "d-ro/n"},
    "s-ron": {"target": "s-ro/n"},
    # Productive finite predicates absent from the old POS-derived paradigm.
    "aŭdeblas": {"target": "aŭd/ebl/as"},
    "mankis": {"target": "mank/is"},
    "strangas": {"target": "strang/as"},
    "agrablas": {"target": "agrabl/as"},
    "apudas": {"target": "apud/as"},
    "dojmos": {"target": "dojm/os"},
    "dolĉas": {"target": "dolĉ/as"},
    "facilas": {"target": "facil/as"},
    "feliĉas": {"target": "feliĉ/as"},
    "klaras": {"target": "klar/as"},
    "legeblas": {"target": "leg/ebl/as"},
    "longas": {"target": "long/as"},
    "malsamas": {"target": "mal/sam/as"},
    "poemos": {"target": "poem/os"},
    "ruĝas": {"target": "ruĝ/as"},
    "simplas": {"target": "simpl/as"},
    "solas": {"target": "sol/as"},
    "sportas": {"target": "sport/as"},
    "super-fortis": {"target": "super/-/fort/is"},
    "teatras": {"target": "teatr/as"},
    "varmas": {"target": "varm/as"},
    "vizitindas": {"target": "vizit/ind/as"},
    # Equal-length prefix/suffix candidates can otherwise win in a
    # language-dependent order (akord/ig vs ord/ig/os, memor/ig vs or/ig/ant).
    # Register the reviewed productive stems so every inflected sibling gets
    # one bounded, language-independent decomposition rule.
    "akordigos": {"target": "akord/ig/os"},
    "difinita": {"target": "difin/it/a"},
    "memoriganta": {"target": "memor/ig/ant/a"},
    "rehonorigante": {"target": "re/honor/ig/ant/e"},
    # Country/correlative accusatives whose final n must not atomize -io.
    "japanion": {"target": "japan/io/n"},
    "koreion": {"target": "kore/io/n"},
    "rusion": {"target": "rus/io/n"},
    "ukrainion": {"target": "ukrain/io/n"},
    "vjetnamion": {"target": "vjetnam/io/n"},
    "ĉinion": {"target": "ĉin/io/n"},
    "eŭrazion": {"target": "eŭrazi/o/n"},
    # Same spelling -an: adjective accusative versus inhabitant suffix.
    "hongkongan": {"target": "hongkong/a/n"},
    "butanon": {"target": "butan/o/n"},
    "jokohaman": {"target": "jokoham/a/n"},
    "firmao": {"target": "firma/o"},
    "rumanio": {"target": "ruman/io"},
    "jugoslavio": {"target": "jugoslav/io"},
    "skanu": {"target": "skan/u"},
    "kriptaĵoscienco": {"target": "kript/aĵ/o/scienc/o"},
    "retroen": {"target": "retro/e/n"},
    "ĉinaangla": {"target": "ĉin/a/angl/a"},
    "memeo": {"target": "meme/o"},
    "Tang-imperifamilio": {
        "target": "Tang/-/imperi/famili/o", "case_sensitive": True,
    },
    "bizaraĵon": {"target": "bizar/aĵ/o/n"},
    "jurnalisto": {"target": "jurnal/ist/o"},
    "dudekon": {"target": "du/dek/o/n"},
    "kriptaĵo-scienco": {"target": "kript/aĵ/o/-/scienc/o"},
    "revenĝe": {"target": "re/venĝ/e"},
    "en-landiĝoj": {"target": "en/-/land/iĝ/o/j"},
    "en-ŝipigi": {"target": "en/-/ŝip/ig/i"},
    "sub-premi": {"target": "sub/-/prem/i"},
    "antaŭeniras": {"target": "antaŭ/e/n/ir/as"},
    "antaŭenpuŝas": {"target": "antaŭ/e/n/puŝ/as"},
    "antaŭenpuŝataj": {"target": "antaŭ/e/n/puŝ/at/a/j"},
    "antaŭkonceptitan": {"target": "antaŭ/koncept/it/a/n"},
    "disflorantan": {"target": "dis/flor/ant/a/n"},
    "esperantigitan": {"target": "esperant/ig/it/a/n"},
    "hegemonio-amaj": {"target": "hegemoni/o/-/am/a/j"},
    # Directional adverb -e-n before a lexical verb.
    "subeniri": {"target": "sub/e/n/ir/i"},
    # Dictionary i-stems: keep the lexical final i inside the root and append
    # only the following grammatical ending.
    "kriptologio": {"target": "kript/o/logi/o"},
    "areopologio": {"target": "are/op/o/logi/o"},
    "areopologii": {"target": "are/op/o/logi/i"},
    "areopologia": {"target": "are/op/o/logi/a"},
    "areopologiajn": {"target": "are/op/o/logi/a/j/n"},
    "areopologion": {"target": "are/op/o/logi/o/n"},
    "fotografio": {"target": "fot/o/grafi/o"},
    "pasigrafio": {"target": "pasi/grafi/o"},
    "meritokrati": {"target": "merit/o/krati"},
    "meritokratio": {"target": "merit/o/krati/o"},
    "meritokratia": {"target": "merit/o/krati/a"},
    "meritokratian": {"target": "merit/o/krati/a/n"},
    "hipermeritokratio": {"target": "hiper/merit/o/krati/o"},
    "hiper-meritokratio": {"target": "hiper/-/merit/o/krati/o"},
    "hiper-meritokratia": {"target": "hiper/-/merit/o/krati/a"},
    "hiper-meritokratian": {"target": "hiper/-/merit/o/krati/a/n"},
    "kriptologia": {"target": "kript/o/logi/a"},
    "kriptologiaj": {"target": "kript/o/logi/a/j"},
    "kriptologian": {"target": "kript/o/logi/a/n"},
    "kriptologiajn": {"target": "kript/o/logi/a/j/n"},
    "logio": {"target": "logi/o"},
    "Brazilio": {"target": "Brazili/o", "case_sensitive": True},
    "sirio": {"target": "siri/o"},
    "oceania": {"target": "oceani/a"},
    "radiofonio": {"target": "radiofoni/o"},
    "azia-oceania": {"target": "azi/a/-/oceani/a"},
    "azian-oceanian": {"target": "azi/a/n/-/oceani/a/n"},
}

for _family in ATOMIC_ROOT_FAMILY_REVIEW["families"]:
    for _target in _family["morph_targets"]:
        _surface = _target["surface"]
        if _surface in MANAGED_MORPH_TARGETS:
            raise SystemExit(f"duplicate atomic-family morph target: {_surface!r}")
        _spec = {"target": _target["target"]}
        # The shared ``novjork`` nominal stem is intentionally useful to both
        # tracks: Ruby keeps the reviewed atomic spelling while Kanji can use
        # its deeper nov/jork authority.  Only the derived ``novjork/an`` stem
        # needs Ruby scoping; otherwise its coarse family correction masks the
        # Kanji-track lexical ``an`` piece.  Bonaer already skips the whole row
        # in Kanji through ruby_context_annotation below.
        if _target["target"].casefold().startswith("novjork/an/"):
            _spec["ruby_track_only"] = True
        if _family["root"] in ATOMIC_FAMILY_CONTEXT_KEYS:
            _spec["ruby_context_annotation"] = (
                ATOMIC_FAMILY_CONTEXT_KEYS[_family["root"]]
            )
        MANAGED_MORPH_TARGETS[_surface] = _spec

# Obsolete same-family pins are removed so the productive managed stem above
# remains the sole rule and retains its context-specific annotation.
MANAGED_REMOVED_SURFACES = {
    "pasigrafioj",
    # Replaced by the productive novjork/o nominal paradigm above.  Leaving
    # this legacy nov/jork/on row would create a same-stem casefold collision.
    "novjorkon",
}

# Slash boundaries alone cannot encode whether a piece is ruby or literal.
# These bounded rows pin the reviewed Kyoto typed signature without weakening
# the productive morphology above or leaking into another case variant.
MANAGED_TYPED_EXACT_TARGETS = {
    "Ivo": {"target": "Ivo", "typed_roles": "R", "case_sensitive": True},
    "f-ino": {"target": "f-ino", "typed_roles": "R"},
    # Proper-name Aŭdu must coexist with the lowercase imperative aŭd/u.
    "Aŭdu": {"target": "Aŭdu", "typed_roles": "R", "case_sensitive": True},
    # Foreign entity + Esperanto accusative: keep the hyphen and -on literal.
    "ChatGPT-on": {
        "target": "ChatGPT/-/on", "typed_roles": "RLL",
        "case_sensitive": True,
    },
    # Case-specific reviewed place-name forms.  Keeping the grammatical -n
    # literal prevents the obsolete hokkajd/on split from returning.
    "hokkajdon": {
        "target": "hokkajdo/n", "typed_roles": "RL", "case_sensitive": True,
    },
    "HOKKAJDON": {
        "target": "HOKKAJDO/N", "typed_roles": "RL", "case_sensitive": True,
    },
}

FAKE_COARSE_TYPED_SURFACES = set()
for _fake_entry in FAKE_COARSE_APP_ENTRIES:
    _fake_surface = _fake_entry["surface"]
    if (
        _fake_surface in MANAGED_TYPED_EXACT_TARGETS
        or _fake_surface in FAKE_COARSE_TYPED_SURFACES
    ):
        raise SystemExit(
            f"duplicate staged fake-coarse exact surface: {_fake_surface!r}"
        )
    MANAGED_TYPED_EXACT_TARGETS[_fake_surface] = {
        "target": _fake_entry["target"],
        "typed_roles": _fake_entry["typed_roles"],
        # Limit this first reviewed deployment to the exact written form.  A
        # later productive family expansion requires its own semantic review.
        "case_sensitive": True,
    }
    FAKE_COARSE_TYPED_SURFACES.add(_fake_surface)

FAKE_COARSE_FF33_TYPED_SURFACES = set()
for _fake_entry in FAKE_COARSE_FF33_ENTRIES:
    _fake_surface = _fake_entry["surface"]
    if (
        _fake_surface in MANAGED_TYPED_EXACT_TARGETS
        or _fake_surface in FAKE_COARSE_FF33_TYPED_SURFACES
    ):
        raise SystemExit(
            f"duplicate FF33 fake-coarse exact surface: {_fake_surface!r}"
        )
    MANAGED_TYPED_EXACT_TARGETS[_fake_surface] = {
        "target": _fake_entry["target"],
        "typed_roles": _fake_entry["typed_roles"],
        "case_sensitive": True,
    }
    FAKE_COARSE_FF33_TYPED_SURFACES.add(_fake_surface)

FAKE_COARSE_5E_TYPED_SURFACES = set()
for _fake_entry in FAKE_COARSE_5E_ENTRIES:
    _fake_surface = _fake_entry["surface"]
    if (
        _fake_surface in MANAGED_TYPED_EXACT_TARGETS
        or _fake_surface in FAKE_COARSE_5E_TYPED_SURFACES
    ):
        raise SystemExit(
            f"duplicate 5E fake-coarse exact surface: {_fake_surface!r}"
        )
    MANAGED_TYPED_EXACT_TARGETS[_fake_surface] = {
        "target": _fake_entry["target"],
        "typed_roles": _fake_entry["typed_roles"],
        "case_sensitive": True,
        "ruby_only": True,
    }
    FAKE_COARSE_5E_TYPED_SURFACES.add(_fake_surface)

REVIEWED_TYPED_EXACT_TARGETS = {}
REVIEWED_TYPED_ANNOTATIONS = dict(REVIEWED_EXACT_MANIFEST["annotations"])
_HOKKAJDO_GLOSSES = {
    "ja": "[地名]北海道", "zh": "[地名]北海道", "ko": "[지명]홋카이도",
}
_hokkajdon_annotation = dict(
    REVIEWED_TYPED_ANNOTATIONS.get("@typed:Hokkajdon:0", {})
)
if _hokkajdon_annotation.get("piece") != "Hokkajdo":
    raise SystemExit("reviewed Hokkajdon annotation is missing or malformed")
_hokkajdon_annotation["glosses"] = dict(_HOKKAJDO_GLOSSES)
REVIEWED_TYPED_ANNOTATIONS["@typed:Hokkajdon:0"] = _hokkajdon_annotation

# ``nitrato`` is a reviewed exact coarse surface (nitrat/o), but its corpus
# manifest observed only the Japanese annotation and therefore supplied
# machine fallback tags in Chinese and Korean.  Repair only this typed context:
# a plain ``nitrat`` annotation would also feed productive/deep words such as
# nitrata acido and sennitratigo, changing their intended boundaries.
_NITRATO_GLOSSES = {
    "ja": "硝酸塩", "zh": "硝酸盐", "ko": "질산염",
}
_nitrato_annotation = dict(
    REVIEWED_TYPED_ANNOTATIONS.get("@typed:nitrato:0", {})
)
if _nitrato_annotation.get("piece") != "nitrat":
    raise SystemExit("reviewed nitrato annotation is missing or malformed")
_nitrato_annotation["glosses"] = dict(_NITRATO_GLOSSES)
REVIEWED_TYPED_ANNOTATIONS["@typed:nitrato:0"] = _nitrato_annotation
for row in REVIEWED_EXACT_MANIFEST["exact_surfaces"]:
    surface = row["surface"]
    target = row["target"]
    roles = row["typed_roles"]
    pieces = [piece for piece in target.split("/") if piece]
    if target.replace("/", "") != surface:
        raise SystemExit(f"reviewed exact target reconstruction failed: {surface!r}")
    if len(roles) != len(pieces) or any(role not in "RL" for role in roles):
        raise SystemExit(f"invalid reviewed typed roles: {surface!r}")
    variants = [(surface, target)]
    curly_surface = curly_apostrophe_variant(surface)
    if curly_surface is not None:
        variants.append((curly_surface, curly_apostrophe_variant(target) or target))
        for index, source_key in row.get("annotation_keys", {}).items():
            source_annotation = REVIEWED_EXACT_MANIFEST["annotations"].get(source_key)
            if source_annotation is None:
                raise SystemExit(f"missing reviewed annotation: {source_key!r}")
            curly_key = f"@typed:{curly_surface}:{index}"
            curly_annotation = dict(source_annotation)
            curly_piece = curly_apostrophe_variant(curly_annotation.get("piece", ""))
            if curly_piece is not None:
                curly_annotation["piece"] = curly_piece
            REVIEWED_TYPED_ANNOTATIONS[curly_key] = curly_annotation
    for variant_surface, variant_target in variants:
        if variant_surface in REVIEWED_TYPED_EXACT_TARGETS:
            raise SystemExit(f"duplicate reviewed exact surface: {variant_surface!r}")
        REVIEWED_TYPED_EXACT_TARGETS[variant_surface] = {
            "target": variant_target,
            "typed_roles": roles,
            "case_sensitive": True,
        }

_extended_exact_surfaces = set()
for _row in EXACT_MANIFEST["exact_surfaces"]:
    _extended_exact_surfaces.add(_row["surface"])
    _curly_surface = curly_apostrophe_variant(_row["surface"])
    if _curly_surface is not None:
        _extended_exact_surfaces.add(_curly_surface)
_reviewed_overlap = (
    set(REVIEWED_TYPED_EXACT_TARGETS)
    & (
        set(MANAGED_EXACT_TARGETS)
        | set(MANAGED_MORPH_TARGETS)
        | set(MANAGED_TYPED_EXACT_TARGETS)
        | _extended_exact_surfaces
    )
)
if _reviewed_overlap:
    raise SystemExit(
        "reviewed residual manifest still contains managed generic surfaces: "
        f"{sorted(_reviewed_overlap)}"
    )

# Corpus-observed typed signatures override older hand-maintained punctuation
# guesses (notably prof./Prof., whose abbreviation dot belongs inside rb).
# Every rule is exact, bounded and case-sensitive, so none can leak into a
# lowercase Esperanto root or a longer foreign spelling.
for row in EXACT_MANIFEST["exact_surfaces"]:
    surface = row["surface"]
    target = row["target"]
    if target.replace("/", "") != surface:
        raise SystemExit(f"exact target reconstruction failed: {surface!r}")
    for variant_surface, variant_target in (
        (surface, target),
        (
            curly_apostrophe_variant(surface),
            curly_apostrophe_variant(target),
        ),
    ):
        if variant_surface is None:
            continue
        MANAGED_EXACT_TARGETS[variant_surface] = (
            variant_target or target, True,
        )


def targets(language):
    yield OUT / f"word_anno_{language}.json"
    yield ROOT / f"Esperanto-Kanji-Ruby-{APP[language]}" / "app_data" / "word_anno.json"


def main():
    for language, entries in ANNOTATIONS.items():
        target_paths = list(targets(language))
        # out/word_anno_*.json is the pipeline's canonical annotation master.
        # Derive the deployed app copy from that one in-memory snapshot so a
        # stale interrupted deployment is repaired rather than perpetuated.
        data = json.loads(target_paths[0].read_text(encoding="utf-8"))
        desired_typed_keys = {
            f"@typed:{surface}:{index}"
            for surface, index, _piece in TYPED_CONTEXT_GLOSSES
        } | set(REVIEWED_TYPED_ANNOTATIONS)
        for key in list(data):
            if key.startswith("@typed:") and key not in desired_typed_keys:
                del data[key]
            if (
                key.startswith("@atomic-family:")
                and key not in ATOMIC_FAMILY_CONTEXT_ANNOTATIONS[language]
            ):
                del data[key]
        for key in LEGACY_ATOMIC_FAMILY_WORD_ANNO_KEYS:
            data.pop(key, None)
        for root, gloss in entries.items():
            if root in ATOMIC_FAMILY_CONTEXT_KEYS:
                continue
            data[root] = [[root, gloss]]
        data.update(ATOMIC_FAMILY_CONTEXT_ANNOTATIONS[language])
        for key, pairs in SPLIT_CONTEXT_ANNOTATIONS[language].items():
            data[key] = pairs
        for (surface, index, piece), glosses in TYPED_CONTEXT_GLOSSES.items():
            if set(glosses) != set(ANNOTATIONS):
                raise SystemExit(f"{surface}[{index}]: typed gloss must define ja/zh/ko")
            data[f"@typed:{surface}:{index}"] = [[piece, glosses[language]]]
        for key, row in REVIEWED_TYPED_ANNOTATIONS.items():
            glosses = row.get("glosses", {})
            piece = row.get("piece")
            if set(glosses) != set(ANNOTATIONS) or not piece:
                raise SystemExit(f"{key}: reviewed annotation must define piece and ja/zh/ko")
            data[key] = [[piece, glosses[language]]]
        for root, source in MIRRORED_ATOMIC_ROOTS.items():
            source_units = data.get(source)
            if not source_units or len(source_units) != 1:
                raise SystemExit(f"{language}: cannot mirror {source!r} to {root!r}")
            data[root] = [[root, source_units[0][1]]]
        for path in target_paths:
            if WRITE:
                atomic_json_dump(path, data)
        print(f"[{language}] corpus atomic annotations: {len(entries)} ({'written' if WRITE else 'dry-run'})")

    confirmed_path = OUT / "confirmed_tier30.json"
    confirmed = json.loads(confirmed_path.read_text(encoding="utf-8"))
    managed_surfaces = (
        set(MANAGED_EXACT_TARGETS)
        | set(PRODUCTIVE_RUBY_LEFT_TARGETS)
        | set(COMPOSITIONAL_FAMILY_TARGETS)
        | set(KANJI_TRACK_PRODUCTIVE_TARGETS)
        | set(MANAGED_MORPH_TARGETS)
        | set(MANAGED_TYPED_EXACT_TARGETS)
        | set(REVIEWED_TYPED_EXACT_TARGETS)
        | MANAGED_REMOVED_SURFACES
    )
    confirmed = [
        entry for entry in confirmed
        if not entry.get("corpus_managed") and entry.get("w") not in managed_surfaces
    ]
    for surface, (target, case_sensitive) in MANAGED_EXACT_TARGETS.items():
        entry = {
            "w": surface,
            "target": target,
            "exact_only": True,
            "corpus_managed": True,
        }
        entry["boundary_only"] = True
        if case_sensitive:
            entry["case_sensitive"] = True
        confirmed.append(entry)
    for surface, spec in MANAGED_MORPH_TARGETS.items():
        entry = {
            "w": surface,
            "target": spec["target"],
            "corpus_managed": True,
        }
        if spec.get("case_sensitive"):
            entry["case_sensitive"] = True
        if spec.get("context_annotation"):
            entry["context_annotation"] = spec["context_annotation"]
        if spec.get("ruby_context_annotation"):
            entry["ruby_context_annotation"] = spec["ruby_context_annotation"]
        if spec.get("ruby_track_only"):
            entry["ruby_track_only"] = True
        confirmed.append(entry)
    for surface, spec in MANAGED_TYPED_EXACT_TARGETS.items():
        entry = {
            "w": surface,
            "target": spec["target"],
            "typed_roles": spec["typed_roles"],
            "exact_only": True,
            "boundary_only": True,
            "case_sensitive": bool(spec.get("case_sensitive", True)),
            "corpus_managed": True,
        }
        if surface in FAKE_COARSE_TYPED_SURFACES:
            entry["fake_coarse_transition_managed"] = True
        if surface in FAKE_COARSE_FF33_TYPED_SURFACES:
            entry["fake_coarse_ff33_transition_managed"] = True
        if surface in FAKE_COARSE_5E_TYPED_SURFACES:
            entry["fake_coarse_5e_transition_managed"] = True
        if spec.get("ruby_only"):
            entry["ruby_only"] = True
        confirmed.append(entry)
    for surface, spec in KANJI_TRACK_PRODUCTIVE_TARGETS.items():
        confirmed.append({
            "w": surface,
            "target": spec["target"],
            "kanji_track_only": True,
            "corpus_managed": True,
            "fake_coarse_5e_transition_managed": True,
        })
    for surface, spec in PRODUCTIVE_RUBY_LEFT_TARGETS.items():
        entry = {
            "w": surface,
            "target": spec["target"],
            "exact_only": True,
            "ruby_left_boundary": True,
            "case_sensitive": spec["case_sensitive"],
            "corpus_managed": True,
        }
        if spec.get("ruby_context_annotation"):
            entry["ruby_context_annotation"] = spec["ruby_context_annotation"]
        confirmed.append(entry)
    for surface, spec in COMPOSITIONAL_FAMILY_TARGETS.items():
        confirmed.append({
            "w": surface,
            "target": spec["target"],
            "exact_only": True,
            "allow_substring": True,
            "corpus_managed": True,
            "localized_compositional": True,
        })
    for surface, spec in REVIEWED_TYPED_EXACT_TARGETS.items():
        confirmed.append({
            "w": surface,
            "target": spec["target"],
            "typed_roles": spec["typed_roles"],
            "exact_only": True,
            "boundary_only": True,
            "case_sensitive": True,
            "corpus_managed": True,
            "reviewed_residual": True,
        })
    if WRITE:
        atomic_json_dump(confirmed_path, confirmed, indent=1)
    print(
        "[confirmed] corpus rules: "
        f"exact={len(MANAGED_EXACT_TARGETS)} "
        f"ruby_left={len(PRODUCTIVE_RUBY_LEFT_TARGETS)} "
        f"compositional={len(COMPOSITIONAL_FAMILY_TARGETS)} "
        f"kanji_productive={len(KANJI_TRACK_PRODUCTIVE_TARGETS)} "
        f"morph={len(MANAGED_MORPH_TARGETS)} "
        f"typed={len(MANAGED_TYPED_EXACT_TARGETS)} "
        f"reviewed_typed={len(REVIEWED_TYPED_EXACT_TARGETS)} "
        f"removed={len(MANAGED_REMOVED_SURFACES)} "
        f"({'written' if WRITE else 'dry-run'})"
    )


if __name__ == "__main__":
    main()
