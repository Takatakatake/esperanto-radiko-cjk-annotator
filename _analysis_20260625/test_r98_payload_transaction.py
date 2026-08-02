"""Failure-injection tests for the R98 three-payload transaction."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, os.fspath(HERE))

import r98_payload_transaction
from r98_payload_transaction import (
    ConcurrentModificationError,
    LockHeldError,
    PayloadTransactionError,
    RecoveryRequiredError,
    ReportPathError,
    _SingleWriterLock,
    apply_payload_transaction,
    recover_payload_transaction,
    validate_report_path,
)


LANGUAGES = ("JA", "ZH", "KO")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


class PayloadTransactionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.out = self.root / "_analysis_20260625" / "out"
        self.out.mkdir(parents=True)
        self.payloads: dict[str, Path] = {}
        self.before: dict[str, bytes] = {}
        for language in LANGUAGES:
            directory = self.root / f"Esperanto-Kanji-Ruby-{language}" / "app_data"
            directory.mkdir(parents=True)
            path = directory / "replacement.json"
            raw = (json.dumps({"language": language, "value": "before"}) + "\n").encode()
            path.write_bytes(raw)
            self.payloads[language] = path
            self.before[language] = raw
        self.journal = self.out / ".r98_payload_transaction.active.json"
        self.lock = self.out / ".r98_payload_transaction.lock"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def candidates(self, snapshots):
        return {
            language: snapshots[language].replace(b"before", b"after")
            for language in LANGUAGES
        }

    def apply(self, **kwargs):
        return apply_payload_transaction(
            self.payloads,
            self.candidates,
            journal_path=self.journal,
            lock_path=self.lock,
            report_directory=self.out,
            **kwargs,
        )

    def assert_original_payloads(self) -> None:
        self.assertEqual(
            {language: path.read_bytes() for language, path in self.payloads.items()},
            self.before,
        )

    def assert_no_transaction_artifacts(self) -> None:
        self.assertFalse(self.journal.exists())
        self.assertTrue(self.lock.is_file())
        self.assertFalse(self.lock.is_symlink())
        artifacts = [
            path
            for payload in self.payloads.values()
            for pattern in (
                f".{payload.name}.r98-*.stage",
                f".{payload.name}.r98-*.rollback",
            )
            for path in payload.parent.glob(pattern)
        ]
        self.assertEqual(artifacts, [])
        self.assertEqual(list(self.out.glob("*.r98-*.stage")), [])

    def test_success_uses_one_snapshot_and_publishes_report_last(self) -> None:
        report = self.out / "r98-transaction-report.json"
        sentinel_backups = {}
        for language, payload in self.payloads.items():
            sentinel = payload.with_name(payload.name + ".bak_preR95G")
            sentinel.write_bytes(f"sentinel-{language}".encode())
            sentinel_backups[language] = sentinel

        seen = []

        def validate(before, after):
            seen.append((dict(before), dict(after)))
            self.assertEqual(before, self.before)
            self.assertTrue(all(b"after" in after[language] for language in LANGUAGES))

        result = self.apply(
            report_path=report,
            report_value={"gate": True},
            candidate_validator=validate,
        )

        self.assertEqual(len(seen), 1)
        self.assertEqual(result.changed_languages, LANGUAGES)
        self.assertEqual(
            {language: sha(self.before[language]) for language in LANGUAGES},
            result.before_sha256,
        )
        for language, payload in self.payloads.items():
            self.assertIn(b"after", payload.read_bytes())
            self.assertEqual(
                sentinel_backups[language].read_bytes(), f"sentinel-{language}".encode()
            )
        report_value = json.loads(report.read_text(encoding="utf-8"))
        self.assertTrue(report_value["gate"])
        self.assertEqual(report_value["changed_languages"], list(LANGUAGES))
        self.assert_no_transaction_artifacts()

    def test_idempotent_candidates_do_not_replace_payloads(self) -> None:
        calls = []

        def replace(source, destination):
            calls.append((source, destination))
            os.replace(source, destination)

        result = apply_payload_transaction(
            self.payloads,
            lambda snapshots: snapshots,
            journal_path=self.journal,
            lock_path=self.lock,
            report_directory=self.out,
            payload_replace=replace,
        )
        self.assertEqual(calls, [])
        self.assertEqual(result.changed_languages, ())
        self.assert_original_payloads()
        self.assert_no_transaction_artifacts()

    def test_failure_on_second_replace_restores_all_before_bytes(self) -> None:
        calls = 0

        def fail_second(source, destination):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("injected second replace failure")
            os.replace(source, destination)

        with self.assertRaisesRegex(OSError, "second replace"):
            self.apply(payload_replace=fail_second)
        self.assertEqual(calls, 2)
        self.assert_original_payloads()
        self.assert_no_transaction_artifacts()

    def test_exception_after_second_replace_still_restores_all_before_bytes(self) -> None:
        calls = 0

        def fail_after_second(source, destination):
            nonlocal calls
            calls += 1
            os.replace(source, destination)
            if calls == 2:
                raise OSError("injected exception after replace")

        with self.assertRaisesRegex(OSError, "after replace"):
            self.apply(payload_replace=fail_after_second)
        self.assertEqual(calls, 2)
        self.assert_original_payloads()
        self.assert_no_transaction_artifacts()

    def test_toctou_before_first_replace_never_overwrites_external_change(self) -> None:
        external = b'{"language":"ZH","value":"external"}\n'

        def mutate_source():
            self.payloads["ZH"].write_bytes(external)

        calls = []
        with self.assertRaisesRegex(ConcurrentModificationError, "before first replace"):
            self.apply(before_commit=mutate_source, payload_replace=lambda *args: calls.append(args))
        self.assertEqual(calls, [])
        self.assertEqual(self.payloads["JA"].read_bytes(), self.before["JA"])
        self.assertEqual(self.payloads["ZH"].read_bytes(), external)
        self.assertEqual(self.payloads["KO"].read_bytes(), self.before["KO"])
        self.assert_no_transaction_artifacts()

    def test_partial_stage_write_is_removed_and_destinations_are_unchanged(self) -> None:
        calls = 0

        def partial_writer(path, data):
            nonlocal calls
            calls += 1
            if calls == 3:
                path.write_bytes(data[:3])
                raise OSError("injected ENOSPC")
            # This is a test-only exclusive writer.
            with path.open("xb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())

        with self.assertRaisesRegex(OSError, "ENOSPC"):
            self.apply(stage_writer=partial_writer)
        self.assert_original_payloads()
        self.assert_no_transaction_artifacts()

    def test_candidate_validator_fails_before_any_transaction_file_is_written(self) -> None:
        def reject_wrong_class(_before, _after):
            raise PayloadTransactionError("pinned target row mismatch")

        with self.assertRaisesRegex(PayloadTransactionError, "pinned target"):
            self.apply(candidate_validator=reject_wrong_class)
        self.assert_original_payloads()
        self.assert_no_transaction_artifacts()

    def test_live_lock_is_fail_closed_and_is_not_deleted(self) -> None:
        holder = _SingleWriterLock(self.lock)
        holder.acquire()
        try:
            with self.assertRaises(LockHeldError):
                self.apply()
        finally:
            holder.release()
        lock_value = json.loads(self.lock.read_text(encoding="utf-8"))
        self.assertEqual(lock_value["token"], holder.token)
        self.assert_original_payloads()
        self.assert_no_transaction_artifacts()

    def _write_mixed_journal(self, *, unknown_ko: bool = False) -> None:
        transaction_id = "deadbeefcafebabedeadbeefcafebabe"
        entries = []
        for language in LANGUAGES:
            destination = self.payloads[language]
            after = self.before[language].replace(b"before", b"after")
            stage = destination.with_name(
                f".{destination.name}.r98-{transaction_id}.stage"
            )
            rollback = destination.with_name(
                f".{destination.name}.r98-{transaction_id}.rollback"
            )
            stage.write_bytes(after)
            rollback.write_bytes(self.before[language])
            entries.append(
                {
                    "language": language,
                    "destination": os.fspath(destination.absolute()),
                    "stage": os.fspath(stage.absolute()),
                    "rollback": os.fspath(rollback.absolute()),
                    "before_sha256": sha(self.before[language]),
                    "after_sha256": sha(after),
                }
            )
        # Simulate a crash after JA was replaced (its stage is consumed).
        os.replace(entries[0]["stage"], entries[0]["destination"])
        if unknown_ko:
            self.payloads["KO"].write_bytes(b"unknown external bytes")
        self.journal.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "transaction_id": transaction_id,
                    "state": "COMMITTING",
                    "payloads": entries,
                    "report": None,
                }
            ),
            encoding="utf-8",
        )
        self.lock.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "token": "stale-owner",
                    "pid": 999999,
                    "host": socket.gethostname(),
                    "created_unix": 0,
                }
            ),
            encoding="utf-8",
        )

    def test_stale_lock_and_mixed_journal_restore_all_before_bytes(self) -> None:
        self._write_mixed_journal()
        outcome = recover_payload_transaction(
            self.payloads,
            journal_path=self.journal,
            lock_path=self.lock,
            report_directory=self.out,
        )
        self.assertEqual(outcome, "rolled_back")
        self.assert_original_payloads()
        self.assert_no_transaction_artifacts()

    def test_unknown_payload_hash_stops_recovery_without_overwrite(self) -> None:
        self._write_mixed_journal(unknown_ko=True)
        ja_after = self.payloads["JA"].read_bytes()
        ko_unknown = self.payloads["KO"].read_bytes()
        with self.assertRaisesRegex(RecoveryRequiredError, "unknown content"):
            recover_payload_transaction(
                self.payloads,
                journal_path=self.journal,
                lock_path=self.lock,
                report_directory=self.out,
            )
        self.assertEqual(self.payloads["JA"].read_bytes(), ja_after)
        self.assertEqual(self.payloads["KO"].read_bytes(), ko_unknown)
        self.assertTrue(self.journal.exists())
        self.assertTrue(self.lock.is_file())

    def test_report_must_be_new_inside_out_and_not_an_alias(self) -> None:
        outside = self.root / "outside.json"
        with self.assertRaises(ReportPathError):
            validate_report_path(outside, report_directory=self.out)

        protected = self.out / "ledger.json"
        protected.write_bytes(b"ledger")
        hardlink = self.out / "hardlink-report.json"
        os.link(protected, hardlink)
        with self.assertRaises(ReportPathError):
            validate_report_path(
                hardlink,
                report_directory=self.out,
                protected_paths={"ledger": protected},
            )

        fresh = self.out / "fresh.json"
        self.assertEqual(validate_report_path(fresh, report_directory=self.out), fresh.absolute())

    def test_report_alias_of_payload_is_rejected_before_replace(self) -> None:
        calls = []
        with self.assertRaises(ReportPathError):
            self.apply(
                report_path=self.payloads["JA"],
                payload_replace=lambda *args: calls.append(args),
            )
        self.assertEqual(calls, [])
        self.assert_original_payloads()
        self.assert_no_transaction_artifacts()

    def test_orphan_stage_without_journal_refuses_new_transaction(self) -> None:
        payload = self.payloads["JA"]
        orphan = payload.with_name(f".{payload.name}.r98-orphan.stage")
        orphan.write_bytes(b"orphan")
        with self.assertRaisesRegex(RecoveryRequiredError, "orphan transaction artifacts"):
            self.apply()
        self.assert_original_payloads()
        self.assertTrue(orphan.exists())
        self.assertTrue(self.lock.is_file())

    def test_recovery_rejects_noncanonical_report_stage_name(self) -> None:
        self._write_mixed_journal()
        journal = json.loads(self.journal.read_text(encoding="utf-8"))
        destination = self.out / "report.json"
        stage = self.out / f"report-{journal['transaction_id']}-almost.stage"
        report_raw = b'{"gate":true}\n'
        stage.write_bytes(report_raw)
        journal["report"] = {
            "destination": os.fspath(destination.absolute()),
            "stage": os.fspath(stage.absolute()),
            "after_sha256": sha(report_raw),
        }
        self.journal.write_text(json.dumps(journal), encoding="utf-8")

        with self.assertRaisesRegex(RecoveryRequiredError, "not canonical"):
            recover_payload_transaction(
                self.payloads,
                journal_path=self.journal,
                lock_path=self.lock,
                report_directory=self.out,
            )
        self.assertTrue(self.journal.exists())
        self.assertTrue(self.lock.is_file())

    def test_recovery_rejects_hardlinked_transaction_artifacts(self) -> None:
        self._write_mixed_journal()
        journal = json.loads(self.journal.read_text(encoding="utf-8"))
        ja_rollback = Path(journal["payloads"][0]["rollback"])
        ko_rollback = Path(journal["payloads"][2]["rollback"])
        ko_rollback.unlink()
        os.link(ja_rollback, ko_rollback)

        with self.assertRaisesRegex(RecoveryRequiredError, "linked|paths alias"):
            recover_payload_transaction(
                self.payloads,
                journal_path=self.journal,
                lock_path=self.lock,
                report_directory=self.out,
            )
        self.assertTrue(self.journal.exists())
        self.assertTrue(self.lock.is_file())

    def test_zero_byte_hardlinked_lock_is_rejected_before_any_write(self) -> None:
        external = self.root / "external-zero-byte"
        external.write_bytes(b"")
        os.link(external, self.lock)

        with self.assertRaisesRegex(LockHeldError, "linked"):
            _SingleWriterLock(self.lock).acquire()
        self.assertEqual(external.read_bytes(), b"")
        self.assertEqual(self.lock.read_bytes(), b"")

    def test_recovery_preflights_all_rollbacks_before_unlink_or_replace(self) -> None:
        self._write_mixed_journal()
        journal = json.loads(self.journal.read_text(encoding="utf-8"))

        # Crash after JA and ZH payload replacement and report publication.
        os.replace(journal["payloads"][1]["stage"], journal["payloads"][1]["destination"])
        report_raw = b'{"gate":true}\n'
        report_path = self.out / "published-report.json"
        report_stage = self.out / (
            f".{report_path.name}.r98-{journal['transaction_id']}.stage"
        )
        report_stage.write_bytes(report_raw)
        os.link(report_stage, report_path)
        journal["report"] = {
            "destination": os.fspath(report_path.absolute()),
            "stage": os.fspath(report_stage.absolute()),
            "after_sha256": sha(report_raw),
        }
        self.journal.write_text(json.dumps(journal), encoding="utf-8")

        # A later required rollback is corrupt.  Nothing may be changed before
        # the complete rollback set has passed preflight.
        Path(journal["payloads"][1]["rollback"]).write_bytes(b"corrupt")
        payload_snapshot = {
            language: path.read_bytes() for language, path in self.payloads.items()
        }
        report_snapshot = report_path.read_bytes()

        with self.assertRaisesRegex(RecoveryRequiredError, "rollback copy"):
            recover_payload_transaction(
                self.payloads,
                journal_path=self.journal,
                lock_path=self.lock,
                report_directory=self.out,
            )
        self.assertEqual(
            {language: path.read_bytes() for language, path in self.payloads.items()},
            payload_snapshot,
        )
        self.assertEqual(report_path.read_bytes(), report_snapshot)
        self.assertTrue(os.path.samefile(report_path, report_stage))

    def test_recovery_rejects_report_alias_of_caller_protected_path(self) -> None:
        self._write_mixed_journal()
        journal = json.loads(self.journal.read_text(encoding="utf-8"))
        protected = self.out / "sealed-ledger.json"
        report_path = self.out / "report-hardlink.json"
        report_raw = b'{"gate":true}\n'
        protected.write_bytes(report_raw)
        os.link(protected, report_path)
        report_stage = self.out / (
            f".{report_path.name}.r98-{journal['transaction_id']}.stage"
        )
        journal["report"] = {
            "destination": os.fspath(report_path.absolute()),
            "stage": os.fspath(report_stage.absolute()),
            "after_sha256": sha(report_raw),
        }
        self.journal.write_text(json.dumps(journal), encoding="utf-8")

        with self.assertRaisesRegex(RecoveryRequiredError, "paths alias"):
            recover_payload_transaction(
                self.payloads,
                journal_path=self.journal,
                lock_path=self.lock,
                report_directory=self.out,
                protected_paths={"ledger": protected},
            )
        self.assertEqual(protected.read_bytes(), report_raw)
        self.assertTrue(self.journal.exists())

    def test_noncommitted_report_must_be_canonical_stage_hardlink(self) -> None:
        self._write_mixed_journal()
        journal = json.loads(self.journal.read_text(encoding="utf-8"))
        report_path = self.out / "separate-report.json"
        report_stage = self.out / (
            f".{report_path.name}.r98-{journal['transaction_id']}.stage"
        )
        report_raw = b'{"gate":true}\n'
        report_path.write_bytes(report_raw)
        report_stage.write_bytes(report_raw)
        journal["report"] = {
            "destination": os.fspath(report_path.absolute()),
            "stage": os.fspath(report_stage.absolute()),
            "after_sha256": sha(report_raw),
        }
        self.journal.write_text(json.dumps(journal), encoding="utf-8")

        with self.assertRaisesRegex(RecoveryRequiredError, "canonical stage link"):
            recover_payload_transaction(
                self.payloads,
                journal_path=self.journal,
                lock_path=self.lock,
                report_directory=self.out,
            )
        self.assertEqual(report_path.read_bytes(), report_raw)

    def test_committed_report_stage_hardlink_is_accepted_and_cleaned(self) -> None:
        self._write_mixed_journal()
        journal = json.loads(self.journal.read_text(encoding="utf-8"))
        for entry in journal["payloads"][1:]:
            os.replace(entry["stage"], entry["destination"])
        report_path = self.out / "committed-report.json"
        report_stage = self.out / (
            f".{report_path.name}.r98-{journal['transaction_id']}.stage"
        )
        report_raw = b'{"gate":true}\n'
        report_stage.write_bytes(report_raw)
        os.link(report_stage, report_path)
        journal["state"] = "COMMITTED"
        journal["report"] = {
            "destination": os.fspath(report_path.absolute()),
            "stage": os.fspath(report_stage.absolute()),
            "after_sha256": sha(report_raw),
        }
        self.journal.write_text(json.dumps(journal), encoding="utf-8")

        outcome = recover_payload_transaction(
            self.payloads,
            journal_path=self.journal,
            lock_path=self.lock,
            report_directory=self.out,
        )
        self.assertEqual(outcome, "committed")
        self.assertEqual(report_path.read_bytes(), report_raw)
        self.assertFalse(report_stage.exists())
        self.assert_no_transaction_artifacts()

    def test_recovery_rejects_nonobject_journal_root(self) -> None:
        self.journal.write_text("[]", encoding="utf-8")
        with self.assertRaisesRegex(RecoveryRequiredError, "root is not an object"):
            recover_payload_transaction(
                self.payloads,
                journal_path=self.journal,
                lock_path=self.lock,
                report_directory=self.out,
            )

    def test_recovery_requires_canonical_id_and_absolute_paths(self) -> None:
        self._write_mixed_journal()
        journal = json.loads(self.journal.read_text(encoding="utf-8"))
        journal["transaction_id"] = "deadbeefcafebabe"
        self.journal.write_text(json.dumps(journal), encoding="utf-8")
        with self.assertRaisesRegex(RecoveryRequiredError, "id is not canonical"):
            recover_payload_transaction(
                self.payloads,
                journal_path=self.journal,
                lock_path=self.lock,
                report_directory=self.out,
            )

        journal["transaction_id"] = "deadbeefcafebabedeadbeefcafebabe"
        journal["payloads"][0]["destination"] = "relative-payload.json"
        self.journal.write_text(json.dumps(journal), encoding="utf-8")
        with self.assertRaisesRegex(RecoveryRequiredError, "not absolute"):
            recover_payload_transaction(
                self.payloads,
                journal_path=self.journal,
                lock_path=self.lock,
                report_directory=self.out,
            )

    def test_lock_implementation_never_uses_process_signals(self) -> None:
        source = Path(r98_payload_transaction.__file__).read_text(encoding="utf-8")
        self.assertNotIn("os.kill", source)


if __name__ == "__main__":
    unittest.main()
