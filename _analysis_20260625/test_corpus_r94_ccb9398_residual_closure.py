# -*- coding: utf-8 -*-
"""Fail-closed checks for the pinned ccb9398 pre-fix residual ledger."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess
import unittest


HERE = Path(__file__).resolve().parent
LEDGER_PATH = HERE / "_corpus_r94_ccb9398_residual_closure.json"


HEAD_OID = "ccb9398eef2a81eaf7e038e67848f89ad3997029"
TREE_OID = "250af9cf8dd9011cd296604787584c516ed2fb79"
CONTENT_SHA256 = "05C4A95250515BF3CBCBE382843DC2A48BC255B4A34FDF6F96771237F7D8B79B"
EMPTY_SHA256 = "E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855"
APP_BASELINE = "6a707dd8da4be04da8dba0968b8de9255411af76"

EXPECTED_SURFACES = {
    "Asahi", "Fukuwarai'", "HKDSE", "Hannja-ĝi", "Mondial",
    "Primico", "Sinzyuku-ku", "TK", "Waseda-mati", "Watanabe", "Yae",
    "apudon", "dekokjarulojn", "hongkongano", "hongkongano-japanaj",
    "koreo-hongkongano", "miksdevena", "multdevenuloj",
    "nederlandano-hongkongano", "premi-ceremonio", "radioprogramo",
    "reprezentis", "samas", "ĉino-japanaj", "radio-elsendoj",
    "radioelsendoj",
}

CLASS_A = {
    "apudon", "dekokjarulojn", "premi-ceremonio", "reprezentis",
    "samas", "ĉino-japanaj",
}
CLASS_B = {
    "miksdevena", "multdevenuloj", "radioprogramo", "radio-elsendoj",
    "radioelsendoj",
}
PROPER_EXACT = {
    "Asahi", "Fukuwarai'", "HKDSE", "Hannja-ĝi", "Mondial", "Primico",
    "Sinzyuku-ku", "TK", "Waseda-mati", "Watanabe", "Yae",
}
HONGKONG_CLOSED = {
    "hongkongano", "hongkongano-japanaj", "koreo-hongkongano",
    "nederlandano-hongkongano",
}
CLASS_C = PROPER_EXACT | HONGKONG_CLOSED
RADIO_BROADCAST = {"radioprogramo", "radio-elsendoj", "radioelsendoj"}


def canonical_sha256(value) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def parse_typed(value: str):
    roles = []
    pieces = []
    for field in value.split("|"):
        role, piece = field.split(":", 1)
        if role not in {"R", "L"}:
            raise ValueError(f"invalid typed role: {role!r}")
        roles.append(role)
        pieces.append(piece)
    return "".join(roles), pieces


class CorpusR94ResidualClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        cls.rows = cls.ledger["residuals"]
        cls.by_surface = {row["surface"]: row for row in cls.rows}

    def test_schema_and_pinned_counts_are_exact(self):
        self.assertEqual(self.ledger["schema_version"], 1)
        self.assertEqual(
            set(self.ledger),
            {
                "schema_version", "ledger_id", "description", "authority",
                "counts", "policy", "residuals", "residuals_sha256",
            },
        )
        self.assertEqual(
            self.ledger["ledger_id"],
            "corpus-r94-ccb9398-ruby-residual-closure-v1",
        )
        counts = self.ledger["counts"]
        self.assertEqual(counts["residual_surfaces"], 26)
        self.assertEqual(counts["residual_instances"], 32)
        self.assertEqual(counts["language_surfaces"], 78)
        self.assertEqual(counts["language_instances"], 96)
        self.assertEqual(counts["visible_failures"], 0)
        self.assertEqual(counts["placeholder_failures"], 0)
        self.assertEqual(
            counts["classifications"],
            {
                "A_productive_family": 6,
                "B_kyoto_coarse_context": 5,
                "C_bounded_proper_foreign": 15,
            },
        )

    def test_pinned_authority_constants_and_scope_are_exact(self):
        authority = self.ledger["authority"]
        corpus = authority["corpus"]
        self.assertEqual(corpus["head_oid"], HEAD_OID)
        self.assertEqual(corpus["tree_oid"], TREE_OID)
        self.assertEqual(corpus["branch"], "agent/r94-kyoto-ruby-audit")
        self.assertEqual(corpus["status_entries"], 0)
        self.assertEqual(corpus["status_sha256"], EMPTY_SHA256)
        self.assertEqual(corpus["content_sha256"], CONTENT_SHA256)
        self.assertEqual(
            corpus["scope"],
            {
                "content_files": 170,
                "raw_ruby": 350519,
                "parsed_ruby": 350519,
                "parsed_units": 272297,
                "evaluable_instances": 271079,
                "canonical_surfaces": 21572,
            },
        )
        self.assertEqual(
            authority["app_baseline"]["source_head_oid"], APP_BASELINE,
        )
        self.assertEqual(
            authority["app_baseline"]["global_rules_per_language"], 572771,
        )
        self.assertEqual(
            set(authority["app_baseline"]["payloads"]), {"JA", "ZH", "KO"},
        )

    def test_pre_fix_full_runtime_report_matches_every_ledger_row(self):
        baseline = self.ledger["authority"]["app_baseline"]
        evidence = baseline["pre_fix_report"]
        report_path = HERE.parent / evidence["path"]
        raw = report_path.read_bytes()
        self.assertEqual(
            hashlib.sha256(raw).hexdigest().upper(), evidence["file_sha256"],
        )
        report = json.loads(raw)
        self.assertEqual(
            report["algorithm_sha256"], evidence["algorithm_sha256"],
        )
        self.assertEqual(report["script_sha256"], evidence["script_sha256"])
        self.assertFalse(report["pass"])
        self.assertEqual(report["residual_language_surfaces"], 78)
        self.assertEqual(report["visible_failures"], 0)
        self.assertEqual(report["placeholder_residual_surfaces"], 0)
        self.assertEqual(
            report["scope"],
            {
                **self.ledger["authority"]["corpus"]["scope"],
                "reviewed_overrides": 625,
            },
        )
        for language_report in report["languages"]:
            language = language_report["language"]
            expected_payload = baseline["payloads"][language]
            self.assertEqual(
                language_report["payload_sha256"],
                expected_payload["sha256"],
            )
            self.assertEqual(
                language_report["runtime_sha256"],
                expected_payload["runtime_sha256"],
            )
            self.assertEqual(language_report["global_rules"], 572771)
            self.assertEqual(language_report["residual_surfaces"], 26)
            self.assertEqual(language_report["residual_instances"], 32)
            observed = {row["surface"]: row for row in language_report["residuals"]}
            self.assertEqual(set(observed), EXPECTED_SURFACES)
            for ledger_row in self.rows:
                residual = observed[ledger_row["surface"]]
                expected = ledger_row["languages"][language]
                self.assertEqual(residual["instances"], ledger_row["instances"])
                self.assertEqual(residual["actual"], expected["actual_typed"])
                self.assertEqual(
                    residual["expected"], [expected["expected_typed"]],
                )

    def test_historical_corpus_commit_and_tree_remain_available(self):
        raw_path = os.environ.get("ESP_CORPUS_PATH")
        self.assertTrue(
            raw_path,
            "ESP_CORPUS_PATH is mandatory for the historical ccb9398 check",
        )
        corpus_root = Path(raw_path).resolve()
        self.assertTrue(corpus_root.is_dir(), corpus_root)

        def git(*args, binary=False):
            completed = subprocess.run(
                ["git", *args], cwd=corpus_root, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, check=False,
            )
            self.assertEqual(
                completed.returncode, 0,
                completed.stderr.decode("utf-8", errors="replace"),
            )
            if binary:
                return completed.stdout
            return completed.stdout.decode("utf-8", errors="strict").strip()

        # ccb9398 is immutable historical evidence.  The live checkout may be
        # its reviewed successor; the successor gate separately archives and
        # recomputes this old content fingerprint without checking it out.
        self.assertEqual(git("rev-parse", f"{HEAD_OID}^{{commit}}"), HEAD_OID)
        self.assertEqual(git("rev-parse", f"{HEAD_OID}^{{tree}}"), TREE_OID)
        self.assertEqual(
            subprocess.run(
                ["git", "merge-base", "--is-ancestor", HEAD_OID, "HEAD"],
                cwd=corpus_root, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, check=False,
            ).returncode,
            0,
            "live corpus must descend from the sealed ccb9398 authority",
        )

    def test_surface_and_instance_closure_is_exact(self):
        surfaces = [row["surface"] for row in self.rows]
        self.assertEqual(len(surfaces), 26)
        self.assertEqual(len(set(surfaces)), 26)
        self.assertEqual(set(surfaces), EXPECTED_SURFACES)
        self.assertEqual(sum(row["instances"] for row in self.rows), 32)
        for row in self.rows:
            self.assertEqual(
                sum(context["count"] for context in row["contexts"]),
                row["instances"],
                row["surface"],
            )
            for context in row["contexts"]:
                self.assertEqual(set(context), {"path", "line", "count"})
                self.assertFalse(Path(context["path"]).is_absolute())
                self.assertEqual(Path(context["path"]).suffix, ".html")
                self.assertGreater(context["line"], 0)
                self.assertGreater(context["count"], 0)

    def test_all_three_languages_have_identical_actual_and_expected_boundaries(self):
        for row in self.rows:
            languages = row["languages"]
            self.assertEqual(set(languages), {"JA", "ZH", "KO"}, row["surface"])
            self.assertEqual(languages["JA"], languages["ZH"], row["surface"])
            self.assertEqual(languages["JA"], languages["KO"], row["surface"])
            self.assertEqual(
                set(languages["JA"]), {"actual_typed", "expected_typed"},
            )
            self.assertNotEqual(
                languages["JA"]["actual_typed"],
                languages["JA"]["expected_typed"],
                row["surface"],
            )

    def test_actual_expected_and_target_reconstruct_each_surface(self):
        for row in self.rows:
            actual = row["languages"]["JA"]["actual_typed"]
            expected = row["languages"]["JA"]["expected_typed"]
            _, actual_pieces = parse_typed(actual)
            expected_roles, expected_pieces = parse_typed(expected)
            target_pieces = row["planned"]["target"].split("/")
            self.assertEqual("".join(actual_pieces), row["surface"])
            self.assertEqual("".join(expected_pieces), row["surface"])
            self.assertEqual("".join(target_pieces), row["surface"])
            self.assertEqual(expected_pieces, target_pieces, row["surface"])
            self.assertEqual(expected_roles, row["planned"]["roles"])

    def test_classification_sets_and_row_modes_are_closed(self):
        classified = {
            label: {row["surface"] for row in self.rows
                    if row["classification"] == label}
            for label in self.ledger["counts"]["classifications"]
        }
        self.assertEqual(classified["A_productive_family"], CLASS_A)
        self.assertEqual(classified["B_kyoto_coarse_context"], CLASS_B)
        self.assertEqual(classified["C_bounded_proper_foreign"], CLASS_C)
        self.assertEqual(
            Counter(row["classification"] for row in self.rows),
            Counter({
                "A_productive_family": 6,
                "B_kyoto_coarse_context": 5,
                "C_bounded_proper_foreign": 15,
            }),
        )
        for surface in CLASS_A:
            self.assertEqual(
                self.by_surface[surface]["match_mode"],
                "bounded_productive_family",
            )
        for surface in {"miksdevena", "multdevenuloj"}:
            self.assertEqual(
                self.by_surface[surface]["match_mode"], "kyoto_coarse_exact",
            )

    def test_proper_names_are_exact_and_case_sensitive(self):
        policy = self.ledger["policy"]["proper_foreign"]
        self.assertEqual(set(policy["surfaces"]), PROPER_EXACT)
        self.assertEqual(policy["match_mode"], "case_sensitive_exact")
        self.assertTrue(policy["case_sensitive"])
        self.assertTrue(policy["exact_only"])
        for surface in PROPER_EXACT:
            row = self.by_surface[surface]
            self.assertEqual(row["subgroup"], "proper_foreign_exact")
            self.assertEqual(row["match_mode"], "case_sensitive_exact")

    def test_hongkong_family_is_a_closed_bounded_set(self):
        policy = self.ledger["policy"]["hongkong_derivatives"]
        self.assertEqual(set(policy["surfaces"]), HONGKONG_CLOSED)
        self.assertEqual(policy["match_mode"], "closed_bounded_family")
        self.assertFalse(policy["substring_matching_allowed"])
        self.assertFalse(policy["global_family_expansion_allowed"])
        for surface in HONGKONG_CLOSED:
            row = self.by_surface[surface]
            self.assertEqual(row["subgroup"], "hongkong_closed_bounded")
            self.assertEqual(row["match_mode"], "closed_bounded_family")

    def test_radio_rules_are_broadcast_context_only(self):
        policy = self.ledger["policy"]["radio_broadcast_context"]
        self.assertEqual(set(policy["residual_surfaces"]), RADIO_BROADCAST)
        self.assertEqual(
            policy["existing_semantic_companion_surfaces"], ["radioprogramoj"],
        )
        self.assertEqual(policy["match_mode"], "broadcast_context_bounded")
        self.assertEqual(policy["required_root"], "radio")
        self.assertFalse(policy["global_radi_o_rewrite_allowed"])
        self.assertTrue(policy["physics_radi_root_must_remain_unchanged"])
        self.assertNotIn("radioprogramoj", self.by_surface)
        for surface in RADIO_BROADCAST:
            row = self.by_surface[surface]
            self.assertEqual(row["subgroup"], "radio_broadcast_context")
            self.assertEqual(row["match_mode"], "broadcast_context_bounded")
            expected = row["languages"]["JA"]["expected_typed"]
            self.assertTrue(expected.startswith("R:radio"), surface)

    def test_every_planned_change_is_ruby_only_and_kanji_invariant(self):
        policy = self.ledger["policy"]
        self.assertTrue(policy["ruby_track_only"])
        self.assertEqual(policy["kanji_planned_changes"], 0)
        self.assertTrue(policy["kanji_artifacts_must_remain_byte_identical"])
        self.assertTrue(policy["trilingual_boundary_identity_required"])
        self.assertFalse(policy["corpus_mutation_authorized_by_ledger"])
        for row in self.rows:
            self.assertEqual(row["planned"]["track"], "ruby", row["surface"])
            self.assertFalse(row["planned"]["kanji_change"], row["surface"])

    def test_miksdevena_strict_rule_is_partitioned_without_kanji_change(self):
        policy = self.ledger["policy"]
        partitions = policy["strict_track_partitions"]
        self.assertEqual(set(partitions), {"miksdevena"})
        partition = partitions["miksdevena"]
        source = partition["source_entry"]
        effective = partition["effective_entry"]
        self.assertEqual(
            partition["operation"],
            "retag_existing_strict_as_kanji_track_only",
        )
        self.assertFalse(partition["kanji_output_change"])
        self.assertEqual(
            effective, {**source, "kanji_track_only": True},
        )
        self.assertEqual(source["target"], "miks/de/ven/a")
        self.assertEqual(partition["ruby_target"], "miks/deven/a")
        self.assertEqual(
            policy["managed_morph_targets"]["miksdevena"]["target"],
            partition["ruby_target"],
        )
        self.assertEqual(
            source["target"].replace("/", ""),
            partition["ruby_target"].replace("/", ""),
        )
        strict_manifest = json.loads(
            (HERE / "_strict_gold_reference_fixes.json").read_text(
                encoding="utf-8"
            )
        )
        matches = [
            entry for entry in strict_manifest["entries"]
            if entry.get("w") == "miksdevena"
        ]
        self.assertEqual(matches, [source])

    def test_residual_payload_hash_is_canonical_and_pinned(self):
        self.assertEqual(
            canonical_sha256(self.rows),
            "25C1CA86E17A3B65817C4747B79900933807C794062EC51FA8239CBA221FDDE4",
        )
        self.assertEqual(
            self.ledger["residuals_sha256"], canonical_sha256(self.rows),
        )


if __name__ == "__main__":
    unittest.main()
