# -*- coding: utf-8 -*-
"""Closed semantic authority for the Esperanto homograph ``di``.

The ordinary root ``di`` means God.  A scientific combining form with the
same spelling means two/di-.  This module deliberately exposes exact reviewed
compound keys and exact generated surface families instead of a productive
global replacement.
"""

REVIEWED_THEOLOGICAL_DI_KEYS = (
    "di/aĵ",
    "di/ar",
    "di/ec",
    "di/favor",
    "di/ig",
    "di/in",
    "di/ism",
    "di/ist",
    "di/kred/ant",
    "di/o/plaĉ",
    "di/o/tim",
    "di/patr/in",
    "di/serv",
    "di/serv/ant",
    "di/skarab",
    "du/on/di",
    "kontraŭ/di",
    "plur/di/ism",
    "sen/di",
    "sen/di/ec",
    "sen/di/ism",
    "sen/di/ist",
    "sen/di/ul",
    "unu/di/ism",
    "unu/di/ist",
)

REVIEWED_SCIENTIFIC_DI_NEGATIVE_KEYS = (
    "di/al",
    "di/azot",
    "di/gram",
    "di/klor/id",
    "di/kotiledon",
    "di/kromiat",
    "di/mer",
    "di/metoksi/fenol",
    "di/morf",
    "di/morf/ec",
    "di/morf/ism",
    "di/oksid",
    "di/ol",
    "di/ploid",
    "di/pod",
    "di/pter",
    "di/sakarid",
    "di/sulf/id",
    "di/tionat",
    "di/valent",
    "karbon/di/oksid",
    "sulfur/di/oksid",
)

REVIEWED_DI_GLOSSES = {
    "ja": {"scientific": "二", "theological": "神"},
    "zh": {"scientific": "二", "theological": "神"},
    "ko": {"scientific": "이", "theological": "신"},
}
REVIEWED_SEND_GLOSSES = {
    "ja": "送る",
    "zh": "送",
    "ko": "보내다",
}

# Each tuple is (generated endings, default exact coarse-Ruby piece signature).
# The ordinary verb send/i is intentionally absent: sen/di begins at sendia.
THEOLOGICAL_DI_RUNTIME_FAMILIES = {
    "diaĵ": (("", "o", "oj", "ojn", "on"), ("di", "aĵ")),
    "diar": (("", "o", "oj", "ojn", "on"), ("di", "ar")),
    "diec": (("", "o", "oj", "ojn", "on"), ("di", "ec")),
    "difavor": (("",), ("di", "favor")),
    "diig": (
        (
            "", "ad", "ant", "as", "at", "i", "ig", "iĝ", "int", "is",
            "it", "ont", "os", "ot", "u", "us",
        ),
        ("di", "ig"),
    ),
    "diin": (
        ("", "a", "aj", "ajn", "an", "o", "oj", "ojn", "on"),
        ("di", "in"),
    ),
    "diism": (("", "o", "oj", "ojn", "on"), ("di", "ism")),
    "diist": (("", "o", "oj", "ojn", "on"), ("di", "ist")),
    "dikredant": (("",), ("di", "kred", "ant")),
    # The internal grammatical -o is deliberately bare in coarse Ruby.
    "dioplaĉ": (("",), ("di", "plaĉ")),
    "diotim": (
        ("", "a", "aj", "ajn", "an", "o", "oj", "ojn", "on"),
        ("di", "tim"),
    ),
    "dipatrin": (("",), ("di", "patr", "in")),
    "diserv": (("", "o", "oj", "ojn", "on"), ("di", "serv")),
    "diservant": (("",), ("di", "serv", "ant")),
    "diskarab": (("",), ("di", "skarab")),
    "duondi": (("", "o", "oj", "ojn", "on"), ("du", "on", "di")),
    "kontraŭdi": (("",), ("kontraŭ", "di")),
    "plurdiism": (("",), ("plur", "di", "ism")),
    "sendi": (("a", "aj", "ajn", "an", "e", "o"), ("sen", "di")),
    "sendiec": (("",), ("sen", "di", "ec")),
    "sendiism": (("",), ("sen", "di", "ism")),
    "sendiist": (("",), ("sen", "di", "ist")),
    "sendiul": (("",), ("sen", "di", "ul")),
    "unudiism": (("",), ("unu", "di", "ism")),
    "unudiist": (("",), ("unu", "di", "ist")),
}

# These derivational/tense pieces are ruby-bearing in the current canonical
# generator.  The remaining diig endings (i/u) are deliberately bare.  Store
# the exact per-surface signature so a new trailing piece cannot be accepted
# merely because the reviewed prefix still happens to match.
_THEOLOGICAL_DI_RUNTIME_SIGNATURE_OVERRIDES = {
    "diigad": ("di", "ig", "ad"),
    "diigant": ("di", "ig", "ant"),
    "diigas": ("di", "ig", "as"),
    "diigat": ("di", "ig", "at"),
    "diigig": ("di", "ig", "ig"),
    "diigiĝ": ("di", "ig", "iĝ"),
    "diigint": ("di", "ig", "int"),
    "diigis": ("di", "ig", "is"),
    "diigit": ("di", "ig", "it"),
    "diigont": ("di", "ig", "ont"),
    "diigos": ("di", "ig", "os"),
    "diigot": ("di", "ig", "ot"),
    "diigus": ("di", "ig", "us"),
}

THEOLOGICAL_DI_RUNTIME_AUTHORITY = {}
for _stem, (_endings, _signature) in THEOLOGICAL_DI_RUNTIME_FAMILIES.items():
    for _ending in _endings:
        _surface = _stem + _ending
        if _surface in THEOLOGICAL_DI_RUNTIME_AUTHORITY:
            raise ValueError(
                f"duplicate theological di runtime surface: {_surface!r}"
            )
        THEOLOGICAL_DI_RUNTIME_AUTHORITY[_surface] = (
            _THEOLOGICAL_DI_RUNTIME_SIGNATURE_OVERRIDES.get(
                _surface, _signature,
            )
        )

THEOLOGICAL_DI_GLOSSES = {
    language.upper(): (
        glosses["scientific"],
        glosses["theological"],
    )
    for language, glosses in REVIEWED_DI_GLOSSES.items()
}
EXPECTED_THEOLOGICAL_DI_GLOBAL_RULES = 273
# Most surfaces have lower/title/upper rules.  diigi and diigu each have a
# second reviewed boundary series, so their per-surface multiplicity is six.
THEOLOGICAL_DI_RUNTIME_RULE_MULTIPLICITY = {
    surface: 6 if surface in {"diigi", "diigu"} else 3
    for surface in THEOLOGICAL_DI_RUNTIME_AUTHORITY
}

if (
    len(REVIEWED_THEOLOGICAL_DI_KEYS) != 25
    or len(set(REVIEWED_THEOLOGICAL_DI_KEYS)) != 25
    or len(REVIEWED_SCIENTIFIC_DI_NEGATIVE_KEYS) != 22
    or len(set(REVIEWED_SCIENTIFIC_DI_NEGATIVE_KEYS)) != 22
    or set(REVIEWED_THEOLOGICAL_DI_KEYS)
    & set(REVIEWED_SCIENTIFIC_DI_NEGATIVE_KEYS)
    or len(THEOLOGICAL_DI_RUNTIME_AUTHORITY) != 89
    or "sendi" in THEOLOGICAL_DI_RUNTIME_AUTHORITY
    or len(_THEOLOGICAL_DI_RUNTIME_SIGNATURE_OVERRIDES) != 13
    or not set(_THEOLOGICAL_DI_RUNTIME_SIGNATURE_OVERRIDES).issubset(
        THEOLOGICAL_DI_RUNTIME_AUTHORITY
    )
    or set(REVIEWED_SEND_GLOSSES) != set(REVIEWED_DI_GLOSSES)
    or set(THEOLOGICAL_DI_RUNTIME_RULE_MULTIPLICITY)
    != set(THEOLOGICAL_DI_RUNTIME_AUTHORITY)
    or sum(THEOLOGICAL_DI_RUNTIME_RULE_MULTIPLICITY.values())
    != EXPECTED_THEOLOGICAL_DI_GLOBAL_RULES
    or {
        surface
        for surface, multiplicity
        in THEOLOGICAL_DI_RUNTIME_RULE_MULTIPLICITY.items()
        if multiplicity == 6
    } != {"diigi", "diigu"}
    or any(
        multiplicity not in {3, 6}
        for multiplicity in THEOLOGICAL_DI_RUNTIME_RULE_MULTIPLICITY.values()
    )
):
    raise ValueError("reviewed di semantic authority scope drift")
