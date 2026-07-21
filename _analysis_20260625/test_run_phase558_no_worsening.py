# -*- coding: utf-8 -*-
"""Lightweight orchestration tests for the Phase 558 formal audit runner."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import sys
import unittest
from unittest import mock

import run_phase558_no_worsening as runner


class Phase558FormalRunnerTests(unittest.TestCase):
    def environment(self):
        return {
            "ESP_GOLD_PATH": "phase532-gold.txt",
            "ESP_CORPUS_PATH": "parent-b769",
            "ESP_PHASE558_CURRENT_CORPUS_PATH": "current-e373",
        }

    def test_audit_arguments_pin_baseline_gold_scope_and_languages(self):
        full = runner._raw_common_arguments()
        current = runner._current_e373_audit_arguments()
        self.assertEqual(full[full.index("--baseline-revision") + 1], runner.BASELINE_REVISION)
        self.assertEqual(full[full.index("--expected-gold-sha256") + 1], runner.PHASE532_GOLD_SHA256)
        self.assertEqual(full[full.index("--languages") + 1:], [
            "JA", "ZH", "KO", "--expected-gold-sha256",
            runner.PHASE532_GOLD_SHA256, "--baseline-revision",
            runner.BASELINE_REVISION,
        ])
        self.assertEqual(
            current[current.index("--scope-manifest") + 1],
            str(runner.CURRENT_E373_SCOPE),
        )
        self.assertIn("--current-only-diagnostic", current)

    def test_three_fresh_raw_failures_then_three_sidecars(self):
        calls = []
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            full_report = output / "full.json"
            current_report = output / "current-e373.json"
            parent_report = output / "parent-current.json"
            parent_report.write_text("stale parent authority", encoding="utf-8")
            stale_checkpoint = (
                output / "_no_worsening_checkpoint_JA_stale.json"
            )
            stale_checkpoint.write_text("stale", encoding="utf-8")
            raw_number = 0

            def fake_process(command, *, cwd, env, check):
                nonlocal raw_number
                calls.append((list(command), dict(env)))
                if str(runner.RAW_AUDITOR) in command:
                    self.assertEqual(list(output.glob(runner.CHECKPOINT_GLOB)), [])
                    raw_number += 1
                    target = (
                        parent_report
                        if "--current-only-diagnostic" in command
                        else full_report
                    )
                    target.write_text(
                        json.dumps({"complete": True, "gate": False}),
                        encoding="utf-8",
                    )
                    (output / (
                        f"_no_worsening_checkpoint_JA_raw{raw_number}.json"
                    )).write_text("fresh evidence", encoding="utf-8")
                    return SimpleNamespace(returncode=1)
                if "--_current-e373-child" in command:
                    self.assertEqual(list(output.glob(runner.CHECKPOINT_GLOB)), [])
                    raw_number += 1
                    current_report.write_text(
                        json.dumps({"complete": True, "gate": False}),
                        encoding="utf-8",
                    )
                    (output / (
                        f"_no_worsening_checkpoint_JA_raw{raw_number}.json"
                    )).write_text("fresh evidence", encoding="utf-8")
                    return SimpleNamespace(returncode=1)
                return SimpleNamespace(returncode=0)

            with (
                mock.patch.object(runner, "FULL_REPORT", full_report),
                mock.patch.object(runner, "CURRENT_E373_REPORT", current_report),
                mock.patch.object(runner, "PARENT_CURRENT_REPORT", parent_report),
                mock.patch.object(runner, "CHECKPOINT_DIR", output),
            ):
                runner.run_formal_audits(
                    environ=self.environment(),
                    run_process=fake_process,
                    head_reader=lambda: "f" * 40,
                )
                self.assertEqual(list(output.glob(runner.CHECKPOINT_GLOB)), [])
                self.assertEqual(
                    json.loads(parent_report.read_text(encoding="utf-8")),
                    {"complete": True, "gate": False},
                )
        self.assertEqual(len(calls), 6)
        self.assertEqual(calls[0][1]["ESP_CORPUS_PATH"], "parent-b769")
        self.assertEqual(calls[2][1]["ESP_CORPUS_PATH"], "parent-b769")
        self.assertEqual(calls[4][1]["ESP_CORPUS_PATH"], "current-e373")
        self.assertTrue(all(call[1]["PYTHONUTF8"] == "1" for call in calls))
        self.assertIn("parent-current", calls[1][0])
        self.assertIn("full-old-to-new", calls[3][0])
        self.assertIn("current-e373", calls[5][0])
        self.assertIn("33", calls[1][0])
        self.assertIn("33", calls[3][0])
        self.assertIn("33", calls[5][0])

    def test_raw_zero_is_never_accepted_even_with_complete_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            parent_report = output / "parent.json"

            def fake_process(command, *, cwd, env, check):
                parent_report.write_text(
                    json.dumps({"complete": True, "gate": False}),
                    encoding="utf-8",
                )
                return SimpleNamespace(returncode=0)

            with (
                mock.patch.object(runner, "PARENT_CURRENT_REPORT", parent_report),
                mock.patch.object(runner, "CHECKPOINT_DIR", output),
            ):
                with self.assertRaisesRegex(RuntimeError, "expected 1"):
                    runner.run_formal_audits(
                        environ=self.environment(),
                        run_process=fake_process,
                        head_reader=lambda: "f" * 40,
                    )

    def test_sidecar_failure_preserves_fresh_forensic_checkpoint(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            report = output / "report.json"
            stale = output / "_no_worsening_checkpoint_JA_stale.json"
            fresh = output / "_no_worsening_checkpoint_JA_fresh.json"
            stale.write_text("old", encoding="utf-8")

            def fake_process(command, *, cwd, env, check):
                if command == ["raw"]:
                    self.assertFalse(stale.exists())
                    report.write_text(
                        json.dumps({"complete": True, "gate": False}),
                        encoding="utf-8",
                    )
                    fresh.write_text("new evidence", encoding="utf-8")
                    return SimpleNamespace(returncode=1)
                return SimpleNamespace(returncode=7)

            with mock.patch.object(runner, "CHECKPOINT_DIR", output):
                with self.assertRaisesRegex(RuntimeError, "sidecar returned 7"):
                    runner._run_fresh_closed_audit(
                        ["raw"], report, "synthetic", "parent-current",
                        environment={}, run_process=fake_process,
                    )
            self.assertTrue(fresh.is_file())
            self.assertEqual(fresh.read_text(encoding="utf-8"), "new evidence")

    def test_dirty_worktree_audit_dependency_drift_fails_before_sidecar(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            parent_report = output / "parent.json"
            fresh = output / "_no_worsening_checkpoint_JA_fresh.json"
            calls = []

            def fake_process(command, *, cwd, env, check):
                calls.append(list(command))
                parent_report.write_text(
                    json.dumps({"complete": True, "gate": False}),
                    encoding="utf-8",
                )
                fresh.write_text("fresh evidence", encoding="utf-8")
                return SimpleNamespace(returncode=1)

            states = iter((
                {"audit": "sealed"},
                {"audit": "sealed"},
                {"audit": "mutated"},
            ))
            with (
                mock.patch.object(runner, "PARENT_CURRENT_REPORT", parent_report),
                mock.patch.object(runner, "CHECKPOINT_DIR", output),
            ):
                with self.assertRaisesRegex(
                    RuntimeError, "formal audit inputs changed",
                ):
                    runner.run_formal_audits(
                        environ=self.environment(),
                        run_process=fake_process,
                        head_reader=lambda: "f" * 40,
                        state_reader=lambda: next(states),
                    )
            self.assertEqual(len(calls), 1)
            self.assertTrue(fresh.is_file())
            self.assertEqual(fresh.read_text(encoding="utf-8"), "fresh evidence")

    def test_checkpoint_symlink_is_refused_before_any_unlink(self):
        ordinary = mock.Mock()
        ordinary.is_symlink.return_value = False
        ordinary.is_file.return_value = True
        ordinary.__str__ = lambda _self: "ordinary"
        symlink = mock.Mock()
        symlink.is_symlink.return_value = True
        symlink.__str__ = lambda _self: "symlink"
        with mock.patch.object(
            runner, "_checkpoint_paths", return_value=[ordinary, symlink],
        ):
            with self.assertRaisesRegex(RuntimeError, "checkpoint symlink"):
                runner._remove_checkpoints()
        ordinary.unlink.assert_not_called()
        symlink.unlink.assert_not_called()

    def test_current_child_redirects_only_parent_report_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            analysis = Path(temporary)
            out = analysis / "out"
            out.mkdir()
            source = out / "_audit_no_worsening_current_only.json"
            destination = out / "_audit_no_worsening_current_e373.json"
            source.write_text("parent-current", encoding="utf-8")

            def atomic_dump(path, value, *args, **kwargs):
                Path(path).write_text(json.dumps(value), encoding="utf-8")

            fake_audit = SimpleNamespace(
                HERE=analysis,
                atomic_json_dump=atomic_dump,
            )

            def fake_main(arguments):
                self.assertEqual(arguments, runner._current_e373_audit_arguments())
                fake_audit.atomic_json_dump(
                    source, {"complete": True, "gate": False}, indent=1,
                )
                raise SystemExit(1)

            fake_audit.main = fake_main
            with (
                mock.patch.dict(sys.modules, {"no_worsening_audit": fake_audit}),
                mock.patch.object(runner, "CURRENT_E373_REPORT", destination),
            ):
                with self.assertRaises(SystemExit) as caught:
                    runner._run_current_e373_child()
            self.assertEqual(caught.exception.code, 1)
            self.assertEqual(source.read_text(encoding="utf-8"), "parent-current")
            self.assertEqual(
                json.loads(destination.read_text(encoding="utf-8")),
                {"complete": True, "gate": False},
            )
            self.assertIs(fake_audit.atomic_json_dump, atomic_dump)

    def test_missing_fresh_report_and_head_drift_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            report = Path(temporary) / "missing.json"
            with self.assertRaisesRegex(RuntimeError, "expected 1"):
                runner._run_expected_raw_failure(
                    ["raw"],
                    report,
                    "synthetic",
                    environment={},
                    run_process=lambda *args, **kwargs: SimpleNamespace(returncode=0),
                )
            with self.assertRaisesRegex(RuntimeError, "did not create"):
                runner._run_expected_raw_failure(
                    ["raw"],
                    report,
                    "synthetic",
                    environment={},
                    run_process=lambda *args, **kwargs: SimpleNamespace(returncode=1),
                )

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            full_report = output / "full.json"
            current_report = output / "current.json"
            parent_report = output / "parent.json"
            heads = iter(("a" * 40, "b" * 40))

            def fake_process(command, *, cwd, env, check):
                if str(runner.RAW_AUDITOR) in command:
                    target = (
                        parent_report
                        if "--current-only-diagnostic" in command
                        else full_report
                    )
                    target.write_text(
                        json.dumps({"complete": True, "gate": False}),
                        encoding="utf-8",
                    )
                    return SimpleNamespace(returncode=1)
                if "--_current-e373-child" in command:
                    current_report.write_text(
                        json.dumps({"complete": True, "gate": False}),
                        encoding="utf-8",
                    )
                    return SimpleNamespace(returncode=1)
                return SimpleNamespace(returncode=0)

            with (
                mock.patch.object(runner, "FULL_REPORT", full_report),
                mock.patch.object(runner, "CURRENT_E373_REPORT", current_report),
                mock.patch.object(runner, "PARENT_CURRENT_REPORT", parent_report),
                mock.patch.object(runner, "CHECKPOINT_DIR", output),
            ):
                with self.assertRaisesRegex(RuntimeError, "HEAD changed"):
                    runner.run_formal_audits(
                        environ=self.environment(),
                        run_process=fake_process,
                        head_reader=lambda: next(heads),
                    )


if __name__ == "__main__":
    unittest.main()
