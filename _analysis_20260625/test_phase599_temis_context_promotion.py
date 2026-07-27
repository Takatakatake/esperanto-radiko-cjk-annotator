# -*- coding: utf-8 -*-
"""Regression tests for the explicit Phase 599 promotion transaction."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import phase599_temis_context_policy as candidate_policy
import phase599_temis_context_promotion as promotion
import phase600_master_ruby_policy as later_policy


ROOT = HERE.parent


def _small_payload(global_rows=None, local_rows=None, two_char_rows=None):
    return {
        "localized_string": list(local_rows or []),
        "replacements_final_list": list(global_rows or []),
        "replacements_list_for_2char": list(two_char_rows or []),
    }


def _deployed_payload(language):
    return json.loads(
        promotion.candidate_gate.deployed_payload_path(language).read_text(
            encoding="utf-8"
        )
    )


class Phase599PromotionTests(unittest.TestCase):
    def test_ledger_is_explicit_and_separate_from_candidate_authority(self):
        ledger = promotion.load_promotion_ledger()
        identity = promotion.promotion_identity()
        self.assertEqual(ledger["status"], "promotion_authorized")
        self.assertEqual(
            ledger["authorization"]["from_status"], "candidate_only"
        )
        self.assertEqual(
            ledger["authorization"]["to_status"], "deployed_ruby_overlay"
        )
        self.assertEqual(
            ledger["candidate_authority"]["review_sha256"],
            candidate_policy.EXPECTED_REVIEW_SHA256,
        )
        self.assertEqual(
            candidate_policy.review_identity()["status"], "candidate_only"
        )
        self.assertEqual(identity["managed_rows_total"], 15)
        self.assertEqual(identity["kanji_paths_written"], [])

    def test_trilingual_rows_match_the_sealed_manifests(self):
        report = promotion.validate_trilingual_row_manifests()
        self.assertTrue(report["gate"])
        self.assertTrue(report["trilingual_source_order_identical"])
        self.assertTrue(report["trilingual_placeholders_unique"])
        for language in promotion.LANGUAGES:
            rows = report["rows"][language]
            self.assertEqual(len(rows), 5)
            self.assertEqual(
                promotion.row_manifest(rows),
                promotion.load_promotion_ledger()["row_manifests"][language],
            )
            self.assertEqual(
                [row[0] for row in rows],
                [
                    f" {phrase} "
                    for phrase in candidate_policy.positive_phrases()
                ],
            )

    def test_corpus_context_inventory_covers_all_six_instances(self):
        report = promotion.validate_corpus_context_inventory()
        contexts = promotion.CORPUS_CONTEXTS
        self.assertTrue(report["gate"])
        self.assertEqual(
            report["contexts_sha256"],
            promotion.EXPECTED_CORPUS_CONTEXTS_SHA256,
        )
        self.assertEqual(report["unique_contexts"], 5)
        self.assertEqual(report["corpus_instances"], 6)
        self.assertEqual(
            [phrase for phrase, _surface, _count in contexts],
            list(candidate_policy.positive_phrases()),
        )
        self.assertEqual(
            {
                phrase: count
                for phrase, _surface, count in contexts
            },
            candidate_policy.EXPECTED_POSITIVE_INSTANCES,
        )
        self.assertEqual(sum(count for _phrase, _surface, count in contexts), 6)
        self.assertEqual(
            len({surface for _phrase, surface, _count in contexts}), 5
        )
        for phrase, surface, _count in contexts:
            self.assertTrue(surface.startswith(phrase + " "))

    def test_normalize_then_add_is_exact_and_idempotent(self):
        rows = promotion.expected_rows("JA")
        base_row = [" unrelated ", " unchanged ", " $42$ "]
        original = _small_payload(global_rows=[base_row])
        normalized, candidate, state = (
            promotion.normalize_and_build_payload(
                original, "JA", rows, expected_normalized_rows=1,
            )
        )
        self.assertEqual(original["replacements_final_list"], [base_row])
        self.assertEqual(normalized["replacements_final_list"], [base_row])
        self.assertEqual(
            candidate["replacements_final_list"], [*rows, base_row]
        )
        self.assertEqual(state["state"], "unpromoted")
        self.assertTrue(state["needs_write"])

        normalized_again, candidate_again, second = (
            promotion.normalize_and_build_payload(
                candidate, "JA", rows, expected_normalized_rows=1,
            )
        )
        self.assertEqual(normalized_again, normalized)
        self.assertEqual(candidate_again, candidate)
        self.assertEqual(second["state"], "promoted_canonical")
        self.assertFalse(second["needs_write"])
        self.assertEqual(second["rows_removed_during_normalization"], 5)
        self.assertEqual(second["rows_added_to_candidate"], 5)

    def test_managed_collision_or_non_global_leak_fails_closed(self):
        rows = promotion.expected_rows("JA")
        collision = copy.deepcopy(rows)
        collision[0][1] += "corrupt"
        payload = _small_payload(
            global_rows=[*collision, [" x ", " y ", " $1$ "]],
        )
        with self.assertRaises(ValueError):
            promotion.normalize_and_build_payload(
                payload, "JA", rows, expected_normalized_rows=1,
            )

        payload = _small_payload(
            global_rows=[[" x ", " y ", " $1$ "]],
            local_rows=[copy.deepcopy(rows[0])],
        )
        with self.assertRaises(ValueError):
            promotion.normalize_and_build_payload(
                payload, "JA", rows, expected_normalized_rows=1,
            )

    def test_phase600_successor_is_preserved_after_phase599_reaudit(self):
        rows_by_language = promotion.validate_trilingual_row_manifests()[
            "rows"
        ]
        for language in promotion.LANGUAGES:
            with self.subTest(language=language):
                payload = _deployed_payload(language)
                normalized, candidate, state = (
                    promotion.normalize_and_build_payload(
                        payload, language, rows_by_language[language],
                    )
                )
                local_key, global_key, two_char_key = later_policy.rule_keys(
                    payload
                )
                managed = later_policy.validate_optional_layer(
                    payload,
                    language,
                    require_present=True,
                )
                self.assertEqual(len(managed), later_policy.MANAGED_ROWS)
                self.assertEqual(
                    payload[global_key][
                        later_policy.PHASE599_ROWS:
                        later_policy.PHASE599_ROWS
                        + later_policy.MANAGED_ROWS
                    ],
                    managed,
                )
                self.assertEqual(
                    len(normalized[global_key]),
                    promotion.NORMALIZED_GLOBAL_ROWS,
                )
                self.assertEqual(
                    len(candidate[global_key]),
                    promotion.POST_PHASE600_GLOBAL_ROWS,
                )
                self.assertIs(normalized[local_key], payload[local_key])
                self.assertIs(normalized[two_char_key], payload[two_char_key])
                self.assertEqual(
                    state["later_phase600_rows_preserved"],
                    later_policy.MANAGED_ROWS,
                )
                self.assertEqual(
                    state["phase599_global_rows"],
                    promotion.PROMOTED_GLOBAL_ROWS,
                )
                self.assertEqual(
                    state["deployed_global_rows"],
                    promotion.POST_PHASE600_GLOBAL_ROWS,
                )
                self.assertEqual(state["state"], "promoted_canonical")
                self.assertFalse(state["needs_write"])
                self.assertEqual(candidate, payload)

    def test_phase600_mutation_partial_or_position_drift_fails_closed(self):
        language = "JA"
        payload = _deployed_payload(language)
        rows = promotion.expected_rows(language)
        _local_key, global_key, _two_char_key = later_policy.rule_keys(
            payload
        )
        start = later_policy.PHASE599_ROWS
        stop = start + later_policy.MANAGED_ROWS

        mutation = copy.deepcopy(payload)
        mutation[global_key][start][2] += "corrupt"

        partial = copy.deepcopy(payload)
        del partial[global_key][start + 7]

        displaced = copy.deepcopy(payload)
        managed = displaced[global_key][start:stop]
        remainder = displaced[global_key][stop:]
        displaced[global_key] = [
            *displaced[global_key][:start],
            remainder[0],
            *managed,
            *remainder[1:],
        ]

        for label, candidate in (
            ("placeholder_mutation", mutation),
            ("partial_layer", partial),
            ("position_drift", displaced),
        ):
            with self.subTest(label=label):
                with self.assertRaisesRegex(
                    ValueError, "managed rows drift|position drift"
                ):
                    promotion.normalize_and_build_payload(
                        candidate, language, rows,
                    )

    def test_one_language_missing_phase600_fails_trilingual_prepare(self):
        counts = {
            "JA": later_policy.MANAGED_ROWS,
            "ZH": 0,
            "KO": later_policy.MANAGED_ROWS,
        }

        def fake_normalize(payload, language, rows):
            return payload, payload, {
                "later_phase600_rows_preserved": counts[language],
                "state": "promoted_canonical",
            }

        with tempfile.TemporaryDirectory(
            prefix="phase599_mixed_phase600_"
        ) as temporary:
            paths = {}
            for language in promotion.LANGUAGES:
                path = Path(temporary) / f"{language}.json"
                path.write_text("{}", encoding="utf-8")
                paths[language] = path

            with (
                mock.patch.object(
                    promotion,
                    "normalize_and_build_payload",
                    side_effect=fake_normalize,
                ),
                mock.patch.object(
                    promotion,
                    "validate_trilingual_row_manifests",
                    return_value={
                        "rows": {
                            language: []
                            for language in promotion.LANGUAGES
                        }
                    },
                ),
                mock.patch.object(
                    promotion.candidate_gate,
                    "deployed_payload_path",
                    side_effect=lambda language: paths[language],
                ),
                mock.patch.object(
                    promotion.candidate_gate,
                    "runtime_input_fingerprint",
                    return_value={},
                ),
                mock.patch.object(
                    promotion.candidate_gate,
                    "kanji_track_fingerprint",
                    return_value={},
                ),
                mock.patch.object(
                    promotion.phase598_parent,
                    "_parent_identity",
                    return_value={},
                ),
                mock.patch.object(
                    promotion,
                    "_r67_r68_language_summary",
                    return_value={"overlays": {}, "global_rows": 0},
                ),
                mock.patch.object(
                    promotion,
                    "_validate_parent_delta",
                    return_value={},
                ),
                mock.patch.object(
                    promotion,
                    "_render_pair",
                    return_value=(None, None, None, None, None),
                ),
            ):
                with self.assertRaisesRegex(
                    ValueError, "mixed Phase-600 deployment state"
                ):
                    promotion.prepare_promotion(batch_size=20)

    def test_transaction_success_and_replace_failure_rollback(self):
        with tempfile.TemporaryDirectory(prefix="phase599_tx_") as temporary:
            root = Path(temporary)
            destinations = {}
            stages = {}
            originals = {}
            for index, language in enumerate(promotion.LANGUAGES):
                destination = root / f"{language}.json"
                stage = root / f"{language}.stage"
                original = json.dumps({"old": index}).encode("utf-8")
                replacement = json.dumps({"new": index}).encode("utf-8")
                destination.write_bytes(original)
                stage.write_bytes(replacement)
                destinations[language] = destination
                stages[language] = stage
                originals[language] = original

            report = promotion.transactional_replace(
                stages,
                destinations,
                lambda: {"post": True},
            )
            self.assertTrue(report["transaction_gate"])
            self.assertEqual(report["postcondition"], {"post": True})
            for index, language in enumerate(promotion.LANGUAGES):
                self.assertEqual(
                    json.loads(destinations[language].read_text()),
                    {"new": index},
                )

            stages = {}
            for index, language in enumerate(promotion.LANGUAGES):
                destinations[language].write_bytes(originals[language])
                stage = root / f"{language}.stage2"
                stage.write_text(json.dumps({"newer": index}))
                stages[language] = stage

            calls = 0

            def fail_second(source, destination):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("injected second replace failure")
                os.replace(source, destination)

            with self.assertRaisesRegex(
                OSError, "injected second replace failure"
            ):
                promotion.transactional_replace(
                    stages,
                    destinations,
                    lambda: {"unexpected": True},
                    replace=fail_second,
                )
            for language in promotion.LANGUAGES:
                self.assertEqual(
                    destinations[language].read_bytes(),
                    originals[language],
                )
                self.assertFalse(
                    promotion._rollback_path(
                        destinations[language]
                    ).exists()
                )

    def test_postcondition_failure_rolls_back_all_languages(self):
        with tempfile.TemporaryDirectory(prefix="phase599_post_") as temporary:
            root = Path(temporary)
            destinations = {}
            stages = {}
            for index, language in enumerate(promotion.LANGUAGES):
                destination = root / f"{language}.json"
                stage = root / f"{language}.stage"
                destination.write_text(json.dumps({"old": index}))
                stage.write_text(json.dumps({"new": index}))
                destinations[language] = destination
                stages[language] = stage

            def fail_postcondition():
                raise ValueError("injected postcondition failure")

            with self.assertRaisesRegex(
                ValueError, "injected postcondition failure"
            ):
                promotion.transactional_replace(
                    stages, destinations, fail_postcondition,
                )
            for index, language in enumerate(promotion.LANGUAGES):
                self.assertEqual(
                    json.loads(destinations[language].read_text()),
                    {"old": index},
                )

    def test_incomplete_rollback_preserves_recovery_copy(self):
        with tempfile.TemporaryDirectory(prefix="phase599_recovery_") as temporary:
            root = Path(temporary)
            destinations = {}
            stages = {}
            originals = {}
            for index, language in enumerate(promotion.LANGUAGES):
                destination = root / f"{language}.json"
                stage = root / f"{language}.stage"
                original = json.dumps({"old": index}).encode("utf-8")
                destination.write_bytes(original)
                stage.write_text(json.dumps({"new": index}))
                destinations[language] = destination
                stages[language] = stage
                originals[language] = original

            calls = 0

            def fail_second_replace(source, destination):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError(f"injected replace failure {calls}")
                destination.write_bytes(source.read_bytes())
                source.unlink()

            real_os_replace = os.replace

            def fail_only_rollback(source, destination):
                if str(source).endswith(".phase599_rollback"):
                    raise OSError("injected rollback failure")
                real_os_replace(source, destination)

            with mock.patch.object(
                promotion.os,
                "replace",
                side_effect=fail_only_rollback,
            ):
                with self.assertRaisesRegex(
                    RuntimeError, "recovery copies preserved"
                ):
                    promotion.transactional_replace(
                        stages,
                        destinations,
                        lambda: {"unexpected": True},
                        replace=fail_second_replace,
                    )
            recovery = promotion._rollback_path(destinations["JA"])
            self.assertTrue(recovery.is_file())
            self.assertEqual(recovery.read_bytes(), originals["JA"])
            self.assertNotEqual(
                destinations["JA"].read_bytes(), originals["JA"]
            )
            for language in ("ZH", "KO"):
                self.assertFalse(
                    promotion._rollback_path(destinations[language]).exists()
                )

    def test_apply_requires_explicit_promotion_flag(self):
        with self.assertRaisesRegex(ValueError, "explicit promotion"):
            promotion.apply_promotion(
                explicit_promotion=False, batch_size=20,
            )

    def test_deployed_promotion_audit_and_generator_order(self):
        report = promotion.audit_deployed_promotion(batch_size=20)
        self.assertTrue(report["promotion_audit_gate"])
        self.assertTrue(report["already_promoted"])
        self.assertEqual(
            set(report["managed_rows_per_language"].values()), {5}
        )
        self.assertEqual(
            report["post_promotion_global_rows_per_language"], 572506
        )
        self.assertEqual(
            set(report["deployed_global_rows_per_language"].values()),
            {572558},
        )
        self.assertEqual(
            set(report["phase600_rows_preserved_per_language"].values()),
            {52},
        )
        self.assertEqual(
            set(
                report["later_phase600"][
                    "rows_preserved_per_language"
                ].values()
            ),
            {52},
        )
        self.assertTrue(
            report["normalized_candidate_precondition"]["precondition_gate"]
        )
        self.assertTrue(
            report["promoted_candidate_runtime"]["candidate_runtime_gate"]
        )
        context = report["promoted_corpus_context_runtime"]
        self.assertTrue(context["gate"])
        self.assertEqual(context["unique_contexts"], 5)
        self.assertEqual(context["corpus_instances"], 6)
        self.assertEqual(context["language_cases_activated"], 15)
        self.assertEqual(
            context["suffix_boundary_annotation_cases_preserved"], 15
        )
        self.assertTrue(context["trilingual_boundaries_identical"])
        self.assertTrue(context["trilingual_rb_sequences_identical"])
        self.assertTrue(report["kanji_nonintervention"])

        source = (
            ROOT / "_analysis_20260625" / "regenerate_all.py"
        ).read_text(encoding="utf-8")
        r67_audit = source.index(
            "'preserve_r67_r68_ruby_overlays.py'),\n"
            "        'audit'"
        )
        parent_delta = source.index(
            "'phase598_parent_payload_delta_gate.py'"
        )
        promotion_apply = source.index(
            "'phase599_temis_context_promotion.py'),\n"
            "        'apply', '--promote'"
        )
        promotion_audit = source.index(
            "'phase599_temis_context_promotion.py'),\n"
            "        'audit', '--deployed'"
        )
        phase600_apply = source.index(
            "'phase600_master_ruby_repair.py'),\n"
            "        'apply'"
        )
        phase600_audit = source.index(
            "'phase600_master_ruby_repair.py'),\n"
            "        'audit'"
        )
        final_phase599_audit = source.index(
            "'phase599_temis_context_promotion.py'),\n"
            "        'audit', '--deployed'",
            phase600_audit,
        )
        self.assertLess(r67_audit, parent_delta)
        self.assertLess(parent_delta, promotion_apply)
        self.assertLess(promotion_apply, promotion_audit)
        self.assertLess(promotion_audit, phase600_apply)
        self.assertLess(phase600_apply, phase600_audit)
        self.assertLess(phase600_audit, final_phase599_audit)


if __name__ == "__main__":
    unittest.main()
