# -*- coding: utf-8 -*-
"""Lightweight tests for the fail-closed Phase 597 successor gate."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import shutil
from types import SimpleNamespace
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import phase597_full_master_successor_sidecar_gate as gate
import run_phase597_full_master_successor as runner


SOURCE_DIR = Path(
    os.environ.get(
        runner.SOURCE_ENVIRONMENT,
        r"D:\tmp\esperanto_stage_20260726_phase597_audit",
    )
)
FRESH_REPORT = HERE / "out" / "_audit_master_3lang_phase597_successor.json"
HISTORICAL_REPORT = Path(
    r"D:\tmp\phase597_r72_di_full_3lang_audit_20260726.json"
)


def candidate_failure_report(**changes) -> dict:
    report = {
        "complete": True,
        "gate": False,
        "candidate_audit": {"runtime_gate": True},
    }
    report.update(changes)
    return report


class Phase597FullMasterSuccessorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.review = gate.load_review()

    def test_review_is_fixed_and_runtime_measurement_is_fresh_sealed(self):
        self.assertEqual(self.review["phase"], 597)
        self.assertEqual(set(self.review["sources"]), gate.SOURCE_NAMES)
        measurement = self.review["runtime_measurement"]
        self.assertIs(measurement["sealed"], True)
        self.assertEqual(
            measurement["raw_audit_script_sha256"],
            "F3AF9A7084807ED6B5FD34C8970375E7820C74AF4179EFB95E3808847B76370E",
        )
        self.assertEqual(
            measurement["raw_semantic_projection_sha256"],
            "B574021AF5DC842494C177FA81979D6D16626B2D6C318B55A9CF121873BC7FC2",
        )
        self.assertEqual(
            measurement["comment_line_numbers_sha256"],
            "9979008ACE1B9F72B61345BB7FF825AC2EA3AF96AC5F8E76414901C3B334CED4",
        )
        self.assertEqual(
            measurement["fake_mismatch_count_per_language"], 2561,
        )
        self.assertEqual(
            measurement["fake_mismatch_projection_sha256"],
            "BD4F9A1CC41086FB8C93FE24B3F2EAAA129D3FE71B8303086341F40A25110C2B",
        )
        self.assertEqual(
            tuple(measurement["current_app_fingerprints"]),
            gate.LANGUAGES,
        )
        self.assertTrue(
            all(
                len(measurement["current_app_fingerprints"][language]) == 11
                for language in gate.LANGUAGES
            )
        )
        gate.require_sealed_runtime_measurement(self.review)

    def test_atletiko_two_track_adjudication_is_exact(self):
        row = self.review["atletiko_two_track_adjudication"]
        self.assertEqual(row["surface"], "atletiko")
        self.assertEqual(row["learner_line"], 2704)
        self.assertEqual(row["ruby_track"]["decomposition"], "atletik/o")
        self.assertEqual(
            row["ruby_track"]["typed_signature"], "R:atletik|L:o",
        )
        self.assertEqual(
            row["kanji_master_track"]["learner_decomposition"],
            "atlet/ik/o",
        )
        self.assertEqual(
            {
                language: row["ruby_track"]["languages"][language]["rt"]
                for language in gate.LANGUAGES
            },
            {"JA": "陸上競技", "ZH": "田径", "KO": "육상경기"},
        )
        self.assertIs(row["master_candidate_promotion_authorized"], False)
        self.assertIs(row["full_fake_coarse_semantic_gate"], False)

    def test_fixed_six_file_source_and_atletiko_line_validate(self):
        if not SOURCE_DIR.is_dir():
            self.skipTest(f"fixed Phase 597 source is absent: {SOURCE_DIR}")
        result = gate.validate_phase597_source_directory(
            SOURCE_DIR, self.review,
        )
        self.assertTrue(result["gate"])
        self.assertTrue(result["atletiko_two_track_source_gate"])
        self.assertEqual(len(result["files"]), 6)

    def test_transition_disposition_tamper_fails(self):
        if not SOURCE_DIR.is_dir():
            self.skipTest(f"fixed Phase 597 source is absent: {SOURCE_DIR}")
        with tempfile.TemporaryDirectory() as raw_temp:
            copied = Path(raw_temp) / "phase597"
            shutil.copytree(SOURCE_DIR, copied)
            path = copied / "candidate_transition_dispositions.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["entries"][0]["decision"] = "silently_promoted"
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                ValueError, "fixed source drift|disposition semantic drift",
            ):
                gate.validate_phase597_source_directory(
                    copied, self.review,
                )

    def test_unsealed_review_blocks_before_every_expensive_callback(self):
        calls = []
        unsealed = copy.deepcopy(self.review)
        measurement = unsealed["runtime_measurement"]
        measurement["sealed"] = False
        for key in (
            "raw_audit_script_sha256",
            "raw_semantic_projection_sha256",
            "comment_line_numbers_sha256",
            "fake_mismatch_count_per_language",
            "fake_mismatch_projection_sha256",
        ):
            measurement[key] = None
        measurement["current_app_fingerprints"] = {
            language: None for language in gate.LANGUAGES
        }
        measurement["language_semantic_projection_sha256"] = {
            language: None for language in gate.LANGUAGES
        }

        def predecessors(**_kwargs):
            calls.append("predecessors")
            return {}

        def focused(**_kwargs):
            calls.append("focused")
            return {}

        with self.assertRaisesRegex(
            ValueError, "unsealed Phase 597 successor measurement",
        ):
            gate.validate_successor_gate(
                {},
                Path("not-consulted-while-unsealed"),
                review=unsealed,
                predecessor_runner=predecessors,
                focused_renderer=focused,
            )
        self.assertEqual(calls, [])
        with self.assertRaisesRegex(
            ValueError, "unsealed Phase 597 successor measurement",
        ):
            gate.validate_raw_report(
                {},
                Path("not-consulted-while-unsealed"),
                review=unsealed,
            )

    def test_fresh_report_matches_every_sealed_raw_projection(self):
        if not SOURCE_DIR.is_dir():
            self.skipTest(f"fixed Phase 597 source is absent: {SOURCE_DIR}")
        if not FRESH_REPORT.is_file():
            self.skipTest(f"fresh Phase 597 report is absent: {FRESH_REPORT}")
        report = json.loads(FRESH_REPORT.read_text(encoding="utf-8"))
        result = gate.validate_raw_report(
            report,
            SOURCE_DIR,
            review=self.review,
            expected_head=report["app"]["head_oid"],
        )
        self.assertTrue(result["gate"])
        self.assertEqual(result["fake_mismatch_count_per_language"], 2561)
        self.assertEqual(
            result["fake_mismatch_projection_sha256"],
            self.review["runtime_measurement"][
                "fake_mismatch_projection_sha256"
            ],
        )
        self.assertIs(
            result["fake_mismatch_queue_semantic_approval"], False,
        )
        self.assertIs(result["atletiko_only_sidecar_admission"], True)
        self.assertIs(result["master_promotion_gate"], False)
        self.assertIs(result["full_fake_coarse_semantic_gate"], False)

    def test_fake_queue_full_projection_is_identical_in_three_languages(self):
        if not FRESH_REPORT.is_file():
            self.skipTest(f"fresh Phase 597 report is absent: {FRESH_REPORT}")
        report = json.loads(FRESH_REPORT.read_text(encoding="utf-8"))
        rows = report["coarse_authority"]["languages"]
        queues = [row["mismatches"] for row in rows]
        self.assertEqual(queues[0], queues[1])
        self.assertEqual(queues[1], queues[2])
        self.assertEqual(len(queues[0]), 2561)
        self.assertEqual(
            gate.stable_json_sha256(queues[0]),
            self.review["runtime_measurement"][
                "fake_mismatch_projection_sha256"
            ],
        )
        self.assertNotIn(
            "atletiko",
            {row["surface"] for row in queues[0]},
        )
        self.assertEqual(
            report["candidate_audit"]["retired_transition_pending_review"],
            1,
        )
        self.assertIs(
            report["candidate_audit"][
                "master_candidate_promotion_authorized"
            ],
            False,
        )

    def test_historical_report_cannot_supply_current_runtime_pins(self):
        if not SOURCE_DIR.is_dir() or not HISTORICAL_REPORT.is_file():
            self.skipTest("historical comparison evidence is unavailable")
        old = json.loads(HISTORICAL_REPORT.read_text(encoding="utf-8"))
        old_queues = old["coarse_authority"]["languages"]
        self.assertEqual(
            [len(row["mismatches"]) for row in old_queues],
            [2569, 2569, 2569],
        )
        self.assertNotEqual(
            gate.stable_json_sha256(old_queues[0]["mismatches"]),
            self.review["runtime_measurement"][
                "fake_mismatch_projection_sha256"
            ],
        )
        with self.assertRaises(ValueError):
            gate.validate_raw_report(
                old,
                SOURCE_DIR,
                review=self.review,
                expected_head=old["app"]["head_oid"],
            )

    def test_raw_semantic_projection_ignores_only_nested_render_seconds(self):
        if not FRESH_REPORT.is_file():
            self.skipTest(f"fresh Phase 597 report is absent: {FRESH_REPORT}")
        report = json.loads(FRESH_REPORT.read_text(encoding="utf-8"))
        expected = gate.stable_json_sha256(
            gate.raw_report_semantic_projection(report)
        )
        timing_only = copy.deepcopy(report)
        for index, row in enumerate(timing_only["languages"], 1):
            row["render_seconds"] += index * 123.456
        self.assertEqual(
            gate.stable_json_sha256(
                gate.raw_report_semantic_projection(timing_only)
            ),
            expected,
        )
        semantic_change = copy.deepcopy(report)
        semantic_change["languages"][0]["global_rules"] += 1
        self.assertNotEqual(
            gate.stable_json_sha256(
                gate.raw_report_semantic_projection(semantic_change)
            ),
            expected,
        )
        with self.assertRaisesRegex(
            ValueError, "render accounting drift|semantic projection drift",
        ):
            gate.validate_raw_report(
                semantic_change,
                SOURCE_DIR,
                review=self.review,
                expected_head=report["app"]["head_oid"],
            )

    def test_predecessor_semantic_hash_algorithms_are_not_cross_compared(self):
        import phase532_runtime_signature_gate as phase532
        import phase558_ruby_overlay_runtime_gate as phase558
        import phase598_technical_on_runtime_gate as phase598

        ordered_value = {"z": 1, "a": 2}
        self.assertEqual(
            phase532.compact_sha256(ordered_value),
            phase558.compact_sha256(ordered_value),
        )
        self.assertNotEqual(
            phase558.compact_sha256(ordered_value),
            phase598.compact_sha256(ordered_value),
        )

    def test_raw_command_is_generic_and_uses_only_fixed_candidate_inputs(self):
        command = runner.build_raw_command(
            SOURCE_DIR,
            "f" * 40,
            report_path=Path("fresh-report.json"),
        )
        joined = "\n".join(command)
        for required in (
            "--gold",
            "--academic",
            "--candidate-fake-coarse-manifest",
            "--candidate-transition-dispositions",
            "--allow-stable-tracked-changes",
            "--expected-head",
            "--report",
        ):
            self.assertIn(required, command)
        for forbidden in (
            "--phase532-baseline-dir",
            "--phase532-candidate-dir",
            "--phase532-runtime-mode",
            "--phase558-candidate-dir",
            "--phase558-ruby-disposition-ledger",
            "--phase558-runtime-mode",
            "--enforce-all-fake-coarse",
        ):
            self.assertNotIn(forbidden, command)
        self.assertIn(
            self.review["sources"]["learner"]["sha256"], joined,
        )
        self.assertIn(
            self.review["sources"]["academic"]["sha256"], joined,
        )

    def test_sidecar_command_is_deployed_and_report_explicit(self):
        command = runner.build_sidecar_command(
            SOURCE_DIR,
            report_path=Path("fresh-report.json"),
            batch_size=20,
        )
        self.assertIn("--deployed", command)
        self.assertEqual(command[command.index("--batch-size") + 1], "20")
        self.assertEqual(
            command[command.index("--audit") + 1], "fresh-report.json",
        )

    def test_stale_regular_report_is_removed(self):
        with tempfile.TemporaryDirectory() as raw_temp:
            report = Path(raw_temp) / "report.json"
            report.write_text("stale", encoding="utf-8")
            runner._remove_report(report)
            self.assertFalse(report.exists())

    def test_report_symlink_is_refused(self):
        with tempfile.TemporaryDirectory() as raw_temp:
            directory = Path(raw_temp)
            target = directory / "target.json"
            target.write_text("do not remove", encoding="utf-8")
            link = directory / "report.json"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError) as error:
                self.skipTest(f"symlink creation unavailable: {error}")
            with self.assertRaisesRegex(
                RuntimeError, "refusing to remove report symlink",
            ):
                runner._remove_report(link)
            self.assertTrue(target.exists())

    def _raw_callback(self, report_path, returncode, payload):
        def callback(_command, **_kwargs):
            if payload is not None:
                report_path.write_text(
                    json.dumps(payload), encoding="utf-8",
                )
            return SimpleNamespace(returncode=returncode)
        return callback

    def test_only_raw_return_code_one_can_be_reviewed(self):
        with tempfile.TemporaryDirectory() as raw_temp:
            for returncode in (0, 2):
                with self.subTest(returncode=returncode):
                    report = Path(raw_temp) / f"report-{returncode}.json"
                    with self.assertRaisesRegex(
                        RuntimeError, "expected exactly 1",
                    ):
                        runner._run_expected_raw_failure(
                            ["raw"],
                            report,
                            environment={},
                            run_process=self._raw_callback(
                                report,
                                returncode,
                                candidate_failure_report(),
                            ),
                        )

    def test_raw_return_code_one_still_requires_fresh_complete_state(self):
        with tempfile.TemporaryDirectory() as raw_temp:
            directory = Path(raw_temp)
            missing = directory / "missing.json"
            with self.assertRaisesRegex(
                RuntimeError, "did not create a regular report",
            ):
                runner._run_expected_raw_failure(
                    ["raw"],
                    missing,
                    environment={},
                    run_process=self._raw_callback(missing, 1, None),
                )
            mutations = (
                {"complete": False},
                {"gate": True},
                {"candidate_audit": {"runtime_gate": False}},
            )
            for index, changes in enumerate(mutations):
                with self.subTest(changes=changes):
                    path = directory / f"wrong-{index}.json"
                    payload = candidate_failure_report(**changes)
                    with self.assertRaisesRegex(
                        RuntimeError, "runtime_gate=true and top gate=false",
                    ):
                        runner._run_expected_raw_failure(
                            ["raw"],
                            path,
                            environment={},
                            run_process=self._raw_callback(path, 1, payload),
                        )

    def test_raw_return_code_one_with_exact_high_level_state_is_accepted(self):
        with tempfile.TemporaryDirectory() as raw_temp:
            report = Path(raw_temp) / "fresh.json"
            payload = candidate_failure_report()
            result = runner._run_expected_raw_failure(
                ["raw"],
                report,
                environment={},
                run_process=self._raw_callback(report, 1, payload),
            )
            self.assertEqual(result, payload)

    def test_toctou_drift_after_raw_prevents_sidecar(self):
        if not SOURCE_DIR.is_dir():
            self.skipTest(f"fixed Phase 597 source is absent: {SOURCE_DIR}")
        with tempfile.TemporaryDirectory() as raw_temp:
            report_path = Path(raw_temp) / "fresh.json"
            state = {"version": 0}
            calls = []

            def fake_process(command, **_kwargs):
                calls.append(command)
                if Path(command[1]).resolve() == runner.RAW_AUDITOR.resolve():
                    report_path.write_text(
                        json.dumps(candidate_failure_report()),
                        encoding="utf-8",
                    )
                    state["version"] = 1
                    return SimpleNamespace(returncode=1)
                return SimpleNamespace(returncode=0)

            with self.assertRaisesRegex(
                RuntimeError, "inputs changed.*after-raw",
            ):
                runner.run_formal_successor(
                    SOURCE_DIR,
                    report_path=report_path,
                    environ={},
                    run_process=fake_process,
                    head_reader=lambda: "f" * 40,
                    state_reader=lambda: copy.deepcopy(state),
                )
            self.assertEqual(len(calls), 1)
            self.assertEqual(
                Path(calls[0][1]).resolve(), runner.RAW_AUDITOR.resolve(),
            )
            self.assertTrue(report_path.is_file())


if __name__ == "__main__":
    unittest.main()
