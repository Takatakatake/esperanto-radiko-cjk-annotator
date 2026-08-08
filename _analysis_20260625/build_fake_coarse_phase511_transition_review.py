# -*- coding: utf-8 -*-
"""Build/check the explicit Phase 511 fake-to-coarse review scope.

Phase 511 changed the paired academic (annotation-Ruby) authority for three
already-deployed strict surfaces and for one row in the provenance-frozen
C679/B090 transition.  A later closed-set semantic review admitted the two
deoksi sugar rows plus fifteen related sugar-name surfaces whose deployed deep
pieces produced false or needlessly fine Ruby glosses.  Keep the historical
manifest byte-for-byte intact and record these twenty-one bounded decisions in
this separate fail-closed supersession ledger.

The learner decompositions remain the Kanji/deep track.  Every rule in this
ledger is therefore exact, case-sensitive and Ruby-track-only; the remaining
Phase 511 fake rows stay in the unreviewed queue.
"""
import argparse
import hashlib
import json
from pathlib import Path

from atomic_json import atomic_json_dump


HERE = Path(__file__).resolve().parent
REFERENCE = HERE / "_phase513_fake_coarse_reference_manifest.json"
HISTORICAL = HERE / "_fake_coarse_transition_review.json"
OUTPUT = HERE / "_fake_coarse_phase511_transition_review.json"

EXPECTED_REFERENCE_SHA256 = (
    "8C507321A27ACD3FE9F919E82C1C380833D6D51760C122467D49757511004504"
)
EXPECTED_REFERENCE_ENTRIES_SHA256 = (
    "A542BC4464CDA30FBE39C28F0EFBEE51EECE83EEABBEA5D3A201388DA3AA7DEB"
)
EXPECTED_LEARNER_SHA256 = (
    "1435F5B1CD1B0BB8224521A8262E3CA740B07B7523E805545A4E3CA7447A286C"
)
EXPECTED_ACADEMIC_SHA256 = (
    "4C813C48B3C4919601FA51E25B6AA3628A0A6793A39C49F1DDFB22A9112E1A0A"
)
EXPECTED_HISTORICAL_SHA256 = (
    "D20633B41904776B5A6954F6EAC8F72335DCE3FEE51213AA9245A360E3027E34"
)
EXPECTED_HISTORICAL_ENTRIES_SHA256 = (
    "B8B1036BF0164960429B2FD079EBF62A71FA02425FC0A4D8EB7B84F127BCCF01"
)
EXPECTED_HISTORICAL_ARABINOZO_ENTRY_SHA256 = (
    "93611A1DB885BD4AF3951C847185F109C7D7A4412B1606EBD3590E0BA7B35C08"
)

REFERENCE_ENTRY_SHA256 = {
    4785: "3F326F1E1834A67F65F112C53BBB29E4725A1B8A58713F1A081A4211B0259E5B",
    21361: "ED2CBB5B1C621F61897926CF05D4805FB77F73C0536067C08F05EE72AAE926E9",
    45205: "88606BCF6186735D613CCB779F822DD38550737E48554799F2679F68227BE291",
    45818: "A583D7A3D0B4824DE38B5045878C5AE0AD1621BD4B96D2368C4844BD90D78F97",
    60166: "DEEBC14E5F55D7E5CA73DD2CB81F94DD35AFACB7C7F7007983576460FDBDCC65",
    60735: "B01CA33F631D95C7596E70A11B881AB536B47751F0A29A48D1ACADC8F1BA6766",
    # Phase 511 sugar/deoksi closed set.  These compact entry fingerprints
    # bind each exact decision to the pinned Phase 513 paired authority.
    24033: "C7C852DFD7BF643F655894DB2E810C19FB4530FA021CD18AAE4F2BE676F9D306",
    34886: "601FD08A7A144FA53771F10538FEDEE69DCDFAF90D78F409A6ED572371D7ADE3",
    44893: "37CD6B15D73AEFFB000990BAFBB5BB7614430127F2465A9A4E8C2CB4A512E90D",
    46627: "2303E4EE28F9A1F8C56F2CA532BA549BDB947F36EAFEEEB40A1A9AFE670A128A",
    48081: "8A869E29DF744CAE28DFE90FCC85AA4B7A6AF6412DAB7839D3166E31841117A4",
    49821: "3BEC84AB366A52E3F99F2F5DED064C9EE7FE059E455486B72A8F741390D6C0C8",
    51048: "14CD6E0762D87F48408E85E58096B46ED401BE7604023A3A96CA5D4FB973357A",
    54151: "725CEE6219018B65C1E5F6A7D9C5E6819CA8B4FCE77B13620848AACB4CD57E69",
    54383: "2427A076E891441255F789BD584606FD6B411939E31AF5EDA30F72C1E39EE4E5",
    55369: "36BEF3E198835D599DCA8FC90771BD5F7A37F78530021C30864019B129FEEA08",
    59757: "C68803D17FE4A89B642EAC0478C6C73AE952838147DF5934FE87C2A1A01C5FF2",
    60165: "5C9EC18EBE402F7B3BFA97689DF205517D56DECD61000250BD5CCD565ABA749E",
    60167: "3AADEFCB9EFE7E2463B617F8A7301453FD70682F64AAF0F00C03072B4EC3F74F",
    60168: "DB1866DC96A4318CF7A5BEFE9E8D14343F93709F5F4BCC7EF02331A1911330CA",
    60169: "A417430EEB9C0512617D6E889715055A8A7CD1425DF11D874E1A0AE0CDD56955",
}

PREVIOUS_STRICT_ENTRY_SHA256 = {
    45818: "D34E079717436B166B9305D7F1A32C6A366654E100F903873DB79003AB409997",
    4785: "41F3FCFF4911615606DAC601641786B1334C9724A6CDE835D6AF86C1004E4EC0",
    21361: "70BE599AC4B88BE6A9248A771E0D415B90B81586F50B7000361A1918A7C1D5F3",
}

REVIEW = {
    45205: {
        "surface": "arabinozo",
        "target": "arabinoz/o",
        "typed_roles": "RL",
        "category": "phase511_historical_authority_supersession",
        "previous_target": "arabin/oz/o",
        "exact_annotations": [{
            "index": 0,
            "piece": "arabinoz",
            "glosses": {
                "ja": "アラビノース",
                "zh": "阿拉伯糖",
                "ko": "아라비노스",
            },
        }],
        "reason": (
            "Phase 511 distinguishes PIV sugar -oz/④ from the homographic "
            "PEJVO disease/abundance suffix. Annotation Ruby follows the "
            "paired academic arabinoz/o root; Kanji keeps arab/in/oz/o."
        ),
    },
    45818: {
        "surface": "bifenilo",
        "target": "bi/fenil/o",
        "typed_roles": "RRL",
        "category": "phase511_strict_authority_carry_forward",
        "previous_target": "bi/fenil/o",
        "reason": (
            "Phase 511 newly marks the learner bi/fen/il/o as deep/Kanji "
            "decomposition. The paired academic bi/fenil/o exactly preserves "
            "the already-reviewed Ruby boundary."
        ),
    },
    4785: {
        "surface": "celulozo",
        "target": "celuloz/o",
        "typed_roles": "RL",
        "category": "phase511_strict_authority_supersession",
        "previous_target": "celul/oz/o",
        "reason": (
            "Phase 511 assigns sugar -oz/④ only to the deep/Kanji track. "
            "Annotation Ruby follows the PEJVO and paired-academic celuloz/o "
            "lexical root."
        ),
    },
    21361: {
        "surface": "laktozo",
        "target": "laktoz/o",
        "typed_roles": "RL",
        "category": "phase511_strict_authority_supersession",
        "previous_target": "lakt/oz/o",
        "reason": (
            "Phase 511 assigns sugar -oz/④ only to the deep/Kanji track. "
            "Annotation Ruby follows the PEJVO and paired-academic laktoz/o "
            "lexical root."
        ),
    },
    60166: {
        "surface": "deoksiozo",
        "target": "deoksioz/o",
        "typed_roles": "RL",
        "category": "phase511_semantic_authority_addition",
        "previous_target": "de/oksi/oz/o",
        "exact_annotations": [{
            "index": 0,
            "piece": "deoksioz",
            "glosses": {
                "ja": "デオキシ糖",
                "zh": "脱氧糖",
                "ko": "디옥시당",
            },
        }],
        "reason": (
            "The paired academic deoksioz/o is the reviewed coarse sugar root. "
            "The deployed learner/deep pieces expose oxygen and the homographic "
            "disease -oz gloss, so Ruby uses one exact localized root while "
            "Kanji keeps de/oksi/oz/o."
        ),
    },
    60735: {
        "surface": "deoksiribozo",
        "target": "deoksi/riboz/o",
        "typed_roles": "RRL",
        "category": "phase511_semantic_authority_addition",
        "previous_target": "de/oksi/rib/oz/o",
        "exact_annotations": [
            {
                "index": 0,
                "piece": "deoksi",
                "glosses": {
                    "ja": "デオキシ",
                    "zh": "脱氧",
                    "ko": "디옥시",
                },
            },
            {
                "index": 1,
                "piece": "riboz",
                "glosses": {
                    "ja": "リボース",
                    "zh": "核糖",
                    "ko": "리보스",
                },
            },
        ],
        "reason": (
            "The paired academic deoksi/riboz/o preserves the coarse PIV "
            "chemical prefix and ribose root. The learner/deep rib piece is "
            "the currant homograph in the Ruby dictionaries, so the two exact "
            "localized pieces prevent a semantic false annotation without "
            "creating productive root rules."
        ),
    },
    24033: {
        "surface": "maltozo",
        "target": "maltoz/o",
        "typed_roles": "RL",
        "category": "phase511_semantic_authority_addition",
        "previous_target": "malt/oz/o",
        "exact_annotations": [{
            "index": 0, "piece": "maltoz",
            "glosses": {"ja": "麦芽糖", "zh": "麦芽糖", "ko": "맥아당"},
        }],
        "reason": (
            "The paired academic maltoz/o is the reviewed coarse sugar name. "
            "The learner/deep malt/oz/o remains the Kanji analysis, while this "
            "exact Ruby-only annotation prevents the disease -oz homograph."
        ),
    },
    34886: {
        "surface": "sakarozo",
        "target": "sakaroz/o",
        "typed_roles": "RL",
        "category": "phase511_semantic_authority_addition",
        "previous_target": "sakar/oz/o",
        "exact_annotations": [{
            "index": 0, "piece": "sakaroz",
            "glosses": {"ja": "ショ糖", "zh": "蔗糖", "ko": "자당"},
        }],
        "reason": (
            "The paired academic sakaroz/o is the reviewed coarse sugar name. "
            "The learner/deep sakar/oz/o remains the Kanji analysis, while this "
            "exact Ruby-only annotation prevents the disease -oz homograph."
        ),
    },
    44893: {
        "surface": "amelozo",
        "target": "ameloz/o",
        "typed_roles": "RL",
        "category": "phase511_semantic_authority_addition",
        "previous_target": "amel/oz/o",
        "exact_annotations": [{
            "index": 0, "piece": "ameloz",
            "glosses": {"ja": "アミロース", "zh": "直链淀粉", "ko": "아밀로스"},
        }],
        "reason": (
            "The paired academic ameloz/o is the reviewed coarse sugar name. "
            "The learner/deep amel/oz/o remains the Kanji analysis; the exact "
            "Ruby-only gloss avoids composing the starch and disease senses."
        ),
    },
    46627: {
        "surface": "deoksi",
        "target": "deoksi",
        "typed_roles": "R",
        "category": "phase511_semantic_authority_addition",
        "previous_target": "de/oksi",
        "exact_annotations": [{
            "index": 0, "piece": "deoksi",
            "glosses": {"ja": "デオキシ", "zh": "脱氧", "ko": "디옥시"},
        }],
        "reason": (
            "The paired academic deoksi is the reviewed coarse chemical root. "
            "The learner/deep de/oksi remains available to the Kanji track; "
            "this exact annotation prevents a misleading oxygen-only Ruby."
        ),
    },
    48081: {
        "surface": "fruktozo",
        "target": "fruktoz/o",
        "typed_roles": "RL",
        "category": "phase511_semantic_authority_addition",
        "previous_target": "frukt/oz/o",
        "exact_annotations": [{
            "index": 0, "piece": "fruktoz",
            "glosses": {"ja": "果糖", "zh": "果糖", "ko": "과당"},
        }],
        "reason": (
            "The paired academic fruktoz/o is the reviewed coarse sugar name. "
            "The learner/deep frukt/oz/o remains the Kanji analysis; the exact "
            "Ruby-only gloss avoids composing fruit with disease -oz."
        ),
    },
    49821: {
        "surface": "kalozo",
        "target": "kaloz/o",
        "typed_roles": "RL",
        "category": "phase511_semantic_authority_addition",
        "previous_target": "kal/oz/o",
        "exact_annotations": [{
            "index": 0, "piece": "kaloz",
            "glosses": {
                "ja": "カロース;脳梁", "zh": "胼胝质;胼胝体", "ko": "칼로스;뇌량",
            },
        }],
        "reason": (
            "Both pinned kalozo senses share the paired academic kaloz/o "
            "boundary.  The exact localized Ruby records the plant and anatomy "
            "senses together without turning kaloz into a productive rule; "
            "Kanji keeps kal/oz/o."
        ),
    },
    51048: {
        "surface": "ksilozo",
        "target": "ksiloz/o",
        "typed_roles": "RL",
        "category": "phase511_semantic_authority_addition",
        "previous_target": "ksil/oz/o",
        "exact_annotations": [{
            "index": 0, "piece": "ksiloz",
            "glosses": {"ja": "キシロース", "zh": "木糖", "ko": "자일로스"},
        }],
        "reason": (
            "The paired academic ksiloz/o is the reviewed coarse sugar name. "
            "The learner/deep ksil/oz/o remains the Kanji analysis; the exact "
            "Ruby-only annotation prevents the disease -oz homograph."
        ),
    },
    54151: {
        "surface": "rafinozo",
        "target": "rafinoz/o",
        "typed_roles": "RL",
        "category": "phase511_semantic_authority_addition",
        "previous_target": "rafin/oz/o",
        "exact_annotations": [{
            "index": 0, "piece": "rafinoz",
            "glosses": {"ja": "ラフィノース", "zh": "棉子糖", "ko": "라피노스"},
        }],
        "reason": (
            "The paired academic rafinoz/o is the reviewed coarse sugar name. "
            "The learner/deep rafin/oz/o remains the Kanji analysis; the exact "
            "Ruby-only annotation prevents the disease -oz homograph."
        ),
    },
    54383: {
        "surface": "ribozo",
        "target": "riboz/o",
        "typed_roles": "RL",
        "category": "phase511_semantic_authority_addition",
        "previous_target": "rib/oz/o",
        "exact_annotations": [{
            "index": 0, "piece": "riboz",
            "glosses": {"ja": "リボース", "zh": "核糖", "ko": "리보스"},
        }],
        "reason": (
            "The paired academic riboz/o is the reviewed coarse sugar name. "
            "The learner/deep rib/oz/o remains the Kanji analysis; the exact "
            "Ruby-only annotation avoids the currant and disease homographs."
        ),
    },
    55369: {
        "surface": "stakiozo",
        "target": "stakioz/o",
        "typed_roles": "RL",
        "category": "phase511_coarse_authority_addition",
        "previous_target": "staki/oz/o",
        "exact_annotations": [{
            "index": 0, "piece": "stakioz",
            "glosses": {"ja": "スタキオース", "zh": "水苏糖", "ko": "스타키오스"},
        }],
        "reason": (
            "The paired academic stakioz/o supplies the Kyoto-level coarse Ruby "
            "boundary.  The semantically usable learner/deep staki/oz/o remains "
            "for Kanji, and the exact rule does not generalize either piece."
        ),
    },
    59757: {
        "surface": "grenmaltozaĵo",
        "target": "gren/maltoz/aĵ/o",
        "typed_roles": "RRRL",
        "category": "phase511_semantic_authority_addition",
        "previous_target": "gren/malt/oz/aĵ/o",
        "exact_annotations": [{
            "index": 1, "piece": "maltoz",
            "glosses": {"ja": "麦芽糖", "zh": "麦芽糖", "ko": "맥아당"},
        }],
        "reason": (
            "The paired academic compound keeps maltoz as one sugar root.  "
            "Only that indexed piece receives a context-local gloss; gren and "
            "aĵ retain their existing annotations and Kanji keeps the deep "
            "gren/malt/oz/aĵ/o analysis."
        ),
    },
    60165: {
        "surface": "aldozo",
        "target": "aldoz/o",
        "typed_roles": "RL",
        "category": "phase511_semantic_authority_addition",
        "previous_target": "ald/oz/o",
        "exact_annotations": [{
            "index": 0, "piece": "aldoz",
            "glosses": {"ja": "アルドース", "zh": "醛糖", "ko": "알도스"},
        }],
        "reason": (
            "The paired academic aldoz/o is the reviewed coarse sugar name. "
            "The learner/deep ald/oz/o remains the Kanji analysis; the exact "
            "Ruby-only annotation avoids alto and disease homographs."
        ),
    },
    60167: {
        "surface": "furanozo",
        "target": "furanoz/o",
        "typed_roles": "RL",
        "category": "phase511_semantic_authority_addition",
        "previous_target": "furan/oz/o",
        "exact_annotations": [{
            "index": 0, "piece": "furanoz",
            "glosses": {"ja": "フラノース", "zh": "呋喃糖", "ko": "푸라노스"},
        }],
        "reason": (
            "The paired academic furanoz/o is the reviewed coarse sugar name. "
            "The learner/deep furan/oz/o remains the Kanji analysis; the exact "
            "Ruby-only annotation prevents the disease -oz homograph."
        ),
    },
    60168: {
        "surface": "ketozo",
        "target": "ketoz/o",
        "typed_roles": "RL",
        "category": "phase511_semantic_authority_addition",
        "previous_target": "ket/oz/o",
        "exact_annotations": [{
            "index": 0, "piece": "ketoz",
            "glosses": {"ja": "ケトース", "zh": "酮糖", "ko": "케토스"},
        }],
        "reason": (
            "The paired academic ketoz/o is the reviewed coarse sugar name. "
            "The learner/deep ket/oz/o remains the Kanji analysis; the exact "
            "Ruby-only annotation prevents the disease -oz homograph."
        ),
    },
    60169: {
        "surface": "piranozo",
        "target": "piranoz/o",
        "typed_roles": "RL",
        "category": "phase511_semantic_authority_addition",
        "previous_target": "piran/oz/o",
        "exact_annotations": [{
            "index": 0, "piece": "piranoz",
            "glosses": {"ja": "ピラノース", "zh": "吡喃糖", "ko": "피라노스"},
        }],
        "reason": (
            "The paired academic piranoz/o is the reviewed coarse sugar name. "
            "The learner/deep piran/oz/o remains the Kanji analysis; the exact "
            "Ruby-only annotation prevents the disease -oz homograph."
        ),
    },
}

# Filled after the reviewed payload is constructed.  Any later field or order
# drift must be an explicit new review, not a silent manifest regeneration.
EXPECTED_ENTRIES_SHA256 = (
    "3F7DBBB34ECE9D3657444818F753755176C89E66307E4AE0E0297A59B8919BFF"
)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest().upper()


def compact_sha256(value):
    raw = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    return sha256(raw)


def load_json(path):
    raw = path.read_bytes()
    return raw, json.loads(raw.decode("utf-8"))


def build_payload():
    reference_raw, reference = load_json(REFERENCE)
    if (
        sha256(reference_raw) != EXPECTED_REFERENCE_SHA256
        or reference.get("entries_sha256")
        != EXPECTED_REFERENCE_ENTRIES_SHA256
        or reference.get("sources", {}).get("learner", {}).get("sha256")
        != EXPECTED_LEARNER_SHA256
        or reference.get("sources", {}).get("academic", {}).get("sha256")
        != EXPECTED_ACADEMIC_SHA256
    ):
        raise ValueError("Phase 511 fake-coarse reference identity changed")

    historical_raw, historical = load_json(HISTORICAL)
    if (
        sha256(historical_raw) != EXPECTED_HISTORICAL_SHA256
        or historical.get("entries_sha256")
        != EXPECTED_HISTORICAL_ENTRIES_SHA256
    ):
        raise ValueError("historical transition manifest changed")
    historical_arabinozo = [
        entry for entry in historical.get("entries", [])
        if entry.get("learner_line") == 45205
    ]
    if (
        len(historical_arabinozo) != 1
        or compact_sha256(historical_arabinozo[0])
        != EXPECTED_HISTORICAL_ARABINOZO_ENTRY_SHA256
    ):
        raise ValueError("historical arabinozo review identity changed")

    reference_by_line = {
        entry["learner_line"]: entry for entry in reference.get("entries", [])
    }
    entries = []
    for learner_line in (
        45205, 45818, 4785, 21361, 60166, 60735,
        24033, 34886, 44893, 46627, 48081, 49821, 51048, 54151,
        54383, 55369, 59757, 60165, 60167, 60168, 60169,
    ):
        source = reference_by_line.get(learner_line)
        review = REVIEW[learner_line]
        if (
            source is None
            or compact_sha256(source) != REFERENCE_ENTRY_SHA256[learner_line]
            or source.get("surface") != review["surface"]
            or source.get("coarse_decomposition") != review["target"]
            or source.get("academic_decomposition") != review["target"]
        ):
            raise ValueError(
                f"Phase 511 reviewed authority drift at line {learner_line}"
            )
        pieces = [piece for piece in review["target"].split("/") if piece]
        roles = review["typed_roles"]
        if (
            "".join(pieces) != review["surface"]
            or len(pieces) != len(roles)
            or any(role not in "RL" for role in roles)
        ):
            raise ValueError(f"invalid reviewed target at line {learner_line}")
        entry = {
            "learner_line": learner_line,
            "surface": review["surface"],
            "learner_decomposition": source["learner_decomposition"],
            "coarse_decomposition": source["coarse_decomposition"],
            "academic_decomposition": source["academic_decomposition"],
            "target": review["target"],
            "typed_roles": roles,
            "case_sensitive": True,
            "ruby_track_only": True,
            "category": review["category"],
            "previous_target": review["previous_target"],
            "reference_entry_sha256": REFERENCE_ENTRY_SHA256[learner_line],
            "reason": review["reason"],
        }
        if learner_line == 45205:
            entry["supersedes_historical_entry_sha256"] = (
                EXPECTED_HISTORICAL_ARABINOZO_ENTRY_SHA256
            )
        elif learner_line in PREVIOUS_STRICT_ENTRY_SHA256:
            entry["supersedes_strict_entry_sha256"] = (
                PREVIOUS_STRICT_ENTRY_SHA256[learner_line]
            )
        else:
            entry["adds_strict_entry"] = True
        if review.get("exact_annotations"):
            annotations = review["exact_annotations"]
            if not isinstance(annotations, list) or not annotations:
                raise ValueError(
                    f"invalid exact annotations at line {learner_line}"
                )
            seen_indices = set()
            for annotation in annotations:
                index = annotation.get("index")
                glosses = annotation.get("glosses")
                if (
                    not isinstance(index, int)
                    or index < 0
                    or index >= len(pieces)
                    or index in seen_indices
                    or pieces[index] != annotation.get("piece")
                    or roles[index] != "R"
                    or not isinstance(glosses, dict)
                    or set(glosses) != {"ja", "zh", "ko"}
                    or any(
                        not isinstance(value, str) or not value
                        for value in glosses.values()
                    )
                ):
                    raise ValueError(
                        f"invalid exact annotations at line {learner_line}"
                    )
                seen_indices.add(index)
            entry["exact_annotations"] = annotations
        entries.append(entry)

    entries_sha256 = compact_sha256(entries)
    if (
        EXPECTED_ENTRIES_SHA256 != "TO_BE_PINNED"
        and entries_sha256 != EXPECTED_ENTRIES_SHA256
    ):
        raise ValueError("Phase 511 transition entry fingerprint changed")
    return {
        "schema_version": 2,
        "phase": 511,
        "source_fake_coarse_manifest": {
            "sha256": EXPECTED_REFERENCE_SHA256,
            "entries_sha256": EXPECTED_REFERENCE_ENTRIES_SHA256,
        },
        "sources": {
            "learner": reference["sources"]["learner"],
            "academic": reference["sources"]["academic"],
        },
        "supersedes": {
            "historical_manifest": {
                "sha256": EXPECTED_HISTORICAL_SHA256,
                "entries_sha256": EXPECTED_HISTORICAL_ENTRIES_SHA256,
                "learner_lines": [45205],
            },
            "strict_ledger_entries": {
                "learner_lines": [45818, 4785, 21361],
                "entry_sha256": {
                    str(line): PREVIOUS_STRICT_ENTRY_SHA256[line]
                    for line in (45818, 4785, 21361)
                },
            },
        },
        "counts": {
            "entries": 21,
            "historical_authority_supersessions": 1,
            "strict_authority_carry_forwards": 1,
            "strict_authority_supersessions": 2,
            "strict_authority_additions": 17,
            "reviewed_exact_localized_annotations": 19,
        },
        "entries_sha256": entries_sha256,
        "entries": entries,
    }


def validate(payload):
    rebuilt = build_payload()
    if payload != rebuilt:
        raise ValueError("Phase 511 transition review is stale")
    return rebuilt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    payload = build_payload()
    if args.write:
        atomic_json_dump(OUTPUT, payload, indent=1)
    else:
        validate(json.loads(OUTPUT.read_text(encoding="utf-8")))
    print(json.dumps({
        "manifest": str(OUTPUT),
        "mode": "write" if args.write else "check",
        "counts": payload["counts"],
        "entries_sha256": payload["entries_sha256"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
