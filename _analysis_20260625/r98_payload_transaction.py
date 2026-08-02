"""Crash-recoverable three-language payload transaction for the R98 fixup.

This module deliberately knows nothing about Esperanto decomposition.  The
caller builds and validates JA/ZH/KO candidate bytes from the immutable
snapshots supplied to ``apply_payload_transaction``.  This module then makes
sure that the three files move from those snapshots to those candidates as a
single recoverable operation.

There is no filesystem primitive that atomically replaces three independent
files.  The durable journal and mandatory rollback copies therefore form part
of the correctness contract, even when the caller does not request permanent
backups.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import socket
import stat
import time
import uuid
from typing import Any, Callable, Mapping

if os.name == "nt":
    import msvcrt
else:
    import fcntl


LANGUAGES = ("JA", "ZH", "KO")
JOURNAL_SCHEMA = 1


class PayloadTransactionError(RuntimeError):
    """Base class for an R98 payload transaction failure."""


class LockHeldError(PayloadTransactionError):
    """Another process owns the single-writer lock."""


class ConcurrentModificationError(PayloadTransactionError):
    """A payload changed after the transaction snapshot was captured."""


class RecoveryRequiredError(PayloadTransactionError):
    """Automatic recovery refused to overwrite an unrecognised file state."""


class ReportPathError(PayloadTransactionError):
    """The requested report path is not a fresh, dedicated output path."""


@dataclass(frozen=True)
class TransactionResult:
    transaction_id: str
    before_sha256: dict[str, str]
    after_sha256: dict[str, str]
    changed_languages: tuple[str, ...]
    report_path: str | None


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _file_bytes(path: Path) -> bytes:
    with path.open("rb") as stream:
        return stream.read()


def _file_sha256(path: Path) -> str:
    return _sha256(_file_bytes(path))


def _fsync_directory(directory: Path) -> None:
    """Best-effort directory fsync (unsupported by normal Windows handles)."""

    if os.name == "nt":
        return
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_bytes_exclusive(path: Path, data: bytes) -> None:
    """Create a durable file without ever overwriting an existing path."""

    descriptor = None
    created = False
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        created = True
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = None
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        _fsync_directory(path.parent)
    except BaseException:
        if descriptor is not None:
            os.close(descriptor)
        if created:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        raise


def _write_json_replace(path: Path, value: Mapping[str, Any]) -> None:
    """Durably publish JSON through a unique same-directory temporary."""

    raw = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    _write_bytes_exclusive(temporary, raw)
    try:
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _normal(path: Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def _resolved(path: Path) -> str:
    return os.path.normcase(os.fspath(path.resolve(strict=False)))


def _paths_alias(left: Path, right: Path) -> bool:
    if _normal(left) == _normal(right) or _resolved(left) == _resolved(right):
        return True
    try:
        return os.path.samefile(left, right)
    except (FileNotFoundError, OSError):
        return False


def _assert_paths_distinct(paths: Mapping[str, Path]) -> None:
    items = list(paths.items())
    for index, (left_name, left) in enumerate(items):
        for right_name, right in items[index + 1 :]:
            if _paths_alias(left, right):
                raise PayloadTransactionError(
                    f"transaction paths alias: {left_name}={left} and "
                    f"{right_name}={right}"
                )


def _is_within(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
    except ValueError:
        return False
    return True


def _has_symlink_component(path: Path, stop: Path) -> bool:
    current = path
    while True:
        if current.exists() and current.is_symlink():
            return True
        if _normal(current) == _normal(stop):
            return False
        if current.parent == current:
            return False
        current = current.parent


def validate_report_path(
    report_path: os.PathLike[str] | str,
    *,
    report_directory: os.PathLike[str] | str,
    protected_paths: Mapping[str, os.PathLike[str] | str] | None = None,
) -> Path:
    """Validate a new report under the dedicated output directory.

    Existing files, symlinks, hardlinks, lexical/realpath escapes, and aliases
    of payload/ledger/width/journal/lock/stage/rollback paths are rejected.
    """

    report = Path(report_path).absolute()
    directory_lexical = Path(report_directory).absolute()
    if not directory_lexical.is_dir() or directory_lexical.is_symlink():
        raise ReportPathError(
            f"report directory must be an existing real directory: {directory_lexical}"
        )
    directory = directory_lexical.resolve(strict=True)
    if not report.parent.exists() or not report.parent.is_dir():
        raise ReportPathError(f"report parent does not exist: {report.parent}")
    if _has_symlink_component(report.parent, directory_lexical):
        raise ReportPathError(f"report path contains a symlink component: {report}")
    report_resolved = report.resolve(strict=False)
    if not _is_within(report_resolved, directory):
        raise ReportPathError(f"report must stay under {directory}: {report}")
    if report.exists() or report.is_symlink():
        raise ReportPathError(f"report path must be new: {report}")
    for name, protected in (protected_paths or {}).items():
        if _paths_alias(report, Path(protected).absolute()):
            raise ReportPathError(
                f"report path aliases protected path {name}: {report}"
            )
    return report


def _acquire_advisory_lock(descriptor: int, path: Path) -> None:
    """Acquire an OS-enforced, non-blocking exclusive lock."""

    try:
        if os.name == "nt":
            os.lseek(descriptor, 0, os.SEEK_SET)
            msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
        else:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        raise LockHeldError(f"transaction lock is held: {path}") from exc


def _release_advisory_lock(descriptor: int) -> None:
    if os.name == "nt":
        os.lseek(descriptor, 0, os.SEEK_SET)
        msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
    else:
        fcntl.flock(descriptor, fcntl.LOCK_UN)


def _write_all(descriptor: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        written = os.write(descriptor, view)
        if written <= 0:
            raise OSError("short write while publishing lock metadata")
        view = view[written:]


class _SingleWriterLock:
    def __init__(
        self,
        path: Path,
        protected_paths: Mapping[str, os.PathLike[str] | str] | None = None,
    ):
        self.path = path
        self.token = uuid.uuid4().hex
        self.owned = False
        self._descriptor: int | None = None
        self._protected_paths = {
            name: Path(value).absolute()
            for name, value in (protected_paths or {}).items()
        }

    def _validate_open_identity(self, descriptor: int) -> None:
        try:
            opened = os.fstat(descriptor)
            path_stat = os.stat(self.path)
            path_lstat = os.lstat(self.path)
        except (FileNotFoundError, OSError) as exc:
            raise LockHeldError(f"cannot verify transaction lock: {self.path}") from exc
        if (
            not os.path.samestat(opened, path_stat)
            or not os.path.samestat(path_lstat, path_stat)
            or not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink != 1
        ):
            raise LockHeldError(
                f"transaction lock path changed, is linked, or is not a real file: "
                f"{self.path}"
            )
        for name, protected in self._protected_paths.items():
            try:
                protected_stat = os.stat(protected)
            except FileNotFoundError:
                continue
            except OSError as exc:
                raise LockHeldError(
                    f"cannot verify protected path {name}: {protected}"
                ) from exc
            if os.path.samestat(opened, protected_stat):
                raise LockHeldError(
                    f"transaction lock aliases protected path {name}: {protected}"
                )

    def acquire(self) -> None:
        if self.owned or self._descriptor is not None:
            raise LockHeldError(f"lock object already owns {self.path}")
        value = {
            "schema_version": 1,
            "token": self.token,
            "pid": os.getpid(),
            "host": socket.gethostname(),
            "created_unix": time.time(),
        }
        raw = (json.dumps(value, sort_keys=True) + "\n").encode("utf-8")
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_BINARY", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        descriptor: int | None = None
        locked = False
        try:
            descriptor = os.open(self.path, flags, 0o600)
            self._validate_open_identity(descriptor)

            # Windows byte-range locking needs the byte to exist.  Competing
            # first-openers may both write the same sentinel, but neither may
            # publish owner metadata until it holds the advisory lock.
            if os.name == "nt" and os.fstat(descriptor).st_size < 1:
                os.lseek(descriptor, 0, os.SEEK_SET)
                _write_all(descriptor, b"\0")
                os.fsync(descriptor)

            _acquire_advisory_lock(descriptor, self.path)
            locked = True

            # Refuse a symlink/reparse point or a path swapped between open
            # and lock acquisition.  The lock file is intentionally never
            # unlinked, closing the stale-unlink race entirely.
            self._validate_open_identity(descriptor)

            os.lseek(descriptor, 0, os.SEEK_SET)
            _write_all(descriptor, raw)
            os.ftruncate(descriptor, len(raw))
            os.fsync(descriptor)
            self._validate_open_identity(descriptor)
            _fsync_directory(self.path.parent)
            self._descriptor = descriptor
            descriptor = None
            self.owned = True
        finally:
            if descriptor is not None:
                try:
                    if locked:
                        _release_advisory_lock(descriptor)
                finally:
                    os.close(descriptor)

    def release(self) -> None:
        if not self.owned:
            return
        descriptor = self._descriptor
        self._descriptor = None
        self.owned = False
        if descriptor is None:
            raise LockHeldError(f"owned lock has no descriptor: {self.path}")
        try:
            _release_advisory_lock(descriptor)
        finally:
            os.close(descriptor)


def _unlink_if_present(path: Path) -> None:
    try:
        path.unlink()
        _fsync_directory(path.parent)
    except FileNotFoundError:
        pass


def _journal_entries(journal: Mapping[str, Any]) -> list[dict[str, Any]]:
    entries = journal.get("payloads")
    if not isinstance(entries, list) or len(entries) != len(LANGUAGES):
        raise RecoveryRequiredError("transaction journal payload list is invalid")
    if any(not isinstance(entry, dict) for entry in entries):
        raise RecoveryRequiredError("transaction journal payload entry is invalid")
    return entries


def _journal_path(value: Any, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise RecoveryRequiredError(f"journal {field} path is invalid")
    try:
        path = Path(value)
    except (OSError, TypeError, ValueError) as exc:
        raise RecoveryRequiredError(f"journal {field} path is invalid") from exc
    if not path.is_absolute():
        raise RecoveryRequiredError(f"journal {field} path is not absolute")
    return path


def _validate_journal_sha256(value: Any, field: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.upper()
        or any(character not in "0123456789ABCDEF" for character in value)
    ):
        raise RecoveryRequiredError(f"journal {field} is invalid")


def _assert_recovery_paths_distinct(paths: Mapping[str, Path]) -> None:
    try:
        _assert_paths_distinct(paths)
    except PayloadTransactionError as exc:
        raise RecoveryRequiredError(str(exc)) from exc


def _validate_single_link_file(
    path: Path,
    field: str,
    *,
    allow_missing: bool = False,
) -> None:
    if path.is_symlink():
        raise RecoveryRequiredError(f"{field} is a symlink")
    try:
        value = path.stat()
    except FileNotFoundError:
        if allow_missing:
            return
        raise RecoveryRequiredError(f"{field} is missing: {path}")
    except OSError as exc:
        raise RecoveryRequiredError(f"cannot inspect {field}: {path}") from exc
    if not stat.S_ISREG(value.st_mode) or value.st_nlink != 1:
        raise RecoveryRequiredError(f"{field} is linked or is not a real file: {path}")


def _validate_recovery_journal(
    journal: Mapping[str, Any],
    payload_paths: Mapping[str, Path],
    report_directory: Path,
    journal_path: Path,
    lock_path: Path,
    protected_paths: Mapping[str, Path],
) -> None:
    if journal.get("schema_version") != JOURNAL_SCHEMA:
        raise RecoveryRequiredError("unknown transaction journal schema")
    if journal.get("state") not in {"PREPARED", "COMMITTING", "COMMITTED"}:
        raise RecoveryRequiredError("unknown transaction journal state")
    transaction_id = journal.get("transaction_id")
    if (
        not isinstance(transaction_id, str)
        or len(transaction_id) != 32
        or any(character not in "0123456789abcdef" for character in transaction_id)
    ):
        raise RecoveryRequiredError("transaction journal id is not canonical")
    entries = _journal_entries(journal)
    if tuple(entry.get("language") for entry in entries) != LANGUAGES:
        raise RecoveryRequiredError("transaction journal language set is invalid")
    artifact_paths: dict[str, Path] = {
        **payload_paths,
        "journal": journal_path,
        "lock": lock_path,
        **{
            f"caller:{name}": Path(path).absolute()
            for name, path in protected_paths.items()
        },
    }
    for entry in entries:
        language = entry["language"]
        destination = _journal_path(entry.get("destination"), f"{language} destination")
        expected_destination = payload_paths[language]
        if (
            _normal(destination) != _normal(expected_destination)
            or _resolved(destination) != _resolved(expected_destination)
        ):
            raise RecoveryRequiredError(
                f"journal destination is not the expected {language} payload"
            )
        expected_names = {
            "stage": f".{destination.name}.r98-{transaction_id}.stage",
            "rollback": f".{destination.name}.r98-{transaction_id}.rollback",
        }
        for field in ("stage", "rollback"):
            artifact = _journal_path(entry.get(field), f"{language} {field}")
            if artifact.parent.resolve(strict=False) != destination.parent.resolve(strict=False):
                raise RecoveryRequiredError(f"journal {field} is not beside its payload")
            if artifact.name != expected_names[field]:
                raise RecoveryRequiredError(f"journal {field} name is not canonical")
            _validate_single_link_file(
                artifact,
                f"journal {language} {field}",
                allow_missing=True,
            )
            artifact_paths[f"{language}:{field}"] = artifact
        for field in ("before_sha256", "after_sha256"):
            _validate_journal_sha256(entry.get(field), f"{language} {field}")
    _assert_recovery_paths_distinct(artifact_paths)

    report = journal.get("report")
    if report is not None:
        if not isinstance(report, dict):
            raise RecoveryRequiredError("transaction journal report entry is invalid")
        path = _journal_path(report.get("destination"), "report destination")
        resolved = path.resolve(strict=False)
        if not _is_within(resolved, report_directory.resolve(strict=True)):
            raise RecoveryRequiredError("journal report escaped its output directory")
        stage = _journal_path(report.get("stage"), "report stage")
        if stage.parent.resolve(strict=False) != path.parent.resolve(strict=False):
            raise RecoveryRequiredError("journal report stage is not beside report")
        expected_stage_name = f".{path.name}.r98-{transaction_id}.stage"
        if stage.name != expected_stage_name:
            raise RecoveryRequiredError("journal report stage name is not canonical")
        _validate_journal_sha256(report.get("after_sha256"), "report after_sha256")

        # Report publication intentionally hard-links its canonical stage to
        # the destination.  Check each against every other transaction path,
        # while allowing only that designed pair to share an inode.
        _assert_recovery_paths_distinct({**artifact_paths, "report": path})
        _assert_recovery_paths_distinct({**artifact_paths, "report-stage": stage})

        if path.is_symlink() or stage.is_symlink():
            raise RecoveryRequiredError("journal report path is a symlink")
        path_exists = path.exists()
        stage_exists = stage.exists()
        if path_exists and not path.is_file():
            raise RecoveryRequiredError("journal report destination is not a real file")
        if stage_exists and not stage.is_file():
            raise RecoveryRequiredError("journal report stage is not a real file")
        if path_exists and stage_exists:
            if not os.path.samefile(path, stage):
                raise RecoveryRequiredError(
                    "journal report destination is not its canonical stage link"
                )
            if path.stat().st_nlink != 2 or stage.stat().st_nlink != 2:
                raise RecoveryRequiredError("journal report has an unknown hardlink")
        else:
            for existing, field in (
                (path if path_exists else None, "report destination"),
                (stage if stage_exists else None, "report stage"),
            ):
                if existing is not None and existing.stat().st_nlink != 1:
                    raise RecoveryRequiredError(f"journal {field} has an unknown hardlink")


def _classify_payloads(entries: list[dict[str, Any]]) -> dict[str, str]:
    states: dict[str, str] = {}
    for entry in entries:
        destination = Path(entry["destination"])
        current = _real_single_link_sha256(destination)
        if current is None:
            states[entry["language"]] = "unknown"
            continue
        before = entry["before_sha256"]
        after = entry["after_sha256"]
        if current == before:
            states[entry["language"]] = "before"
        elif current == after:
            states[entry["language"]] = "after"
        else:
            states[entry["language"]] = "unknown"
    return states


def _real_single_link_sha256(path: Path) -> str | None:
    if path.is_symlink():
        return None
    try:
        value = path.stat()
    except (FileNotFoundError, OSError):
        return None
    if not stat.S_ISREG(value.st_mode) or value.st_nlink != 1:
        return None
    try:
        return _file_sha256(path)
    except (FileNotFoundError, OSError):
        return None


def _cleanup_journal_artifacts(journal: Mapping[str, Any], journal_path: Path) -> None:
    for entry in _journal_entries(journal):
        _unlink_if_present(Path(entry["stage"]))
        _unlink_if_present(Path(entry["rollback"]))
    report = journal.get("report")
    if report is not None:
        _unlink_if_present(Path(report["stage"]))
    _unlink_if_present(journal_path)


def _recover_locked(
    journal_path: Path,
    payload_paths: Mapping[str, Path],
    report_directory: Path,
    lock_path: Path,
    protected_paths: Mapping[str, Path],
) -> str:
    """Recover an existing journal while the caller holds the writer lock."""

    if not journal_path.exists():
        return "none"
    _validate_single_link_file(journal_path, "transaction journal")
    try:
        journal = json.loads(_file_bytes(journal_path).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RecoveryRequiredError(f"cannot read transaction journal: {journal_path}") from exc
    if not isinstance(journal, dict):
        raise RecoveryRequiredError("transaction journal root is not an object")
    _validate_recovery_journal(
        journal,
        payload_paths,
        report_directory,
        journal_path,
        lock_path,
        protected_paths,
    )
    entries = _journal_entries(journal)
    states = _classify_payloads(entries)
    report = journal.get("report")
    report_state = "absent"
    if report is not None:
        report_path = Path(report["destination"])
        if report_path.exists():
            if not report_path.is_file() or _file_sha256(report_path) != report["after_sha256"]:
                report_state = "unknown"
            else:
                report_state = "after"

    unknown = [language for language, state in states.items() if state == "unknown"]
    if unknown:
        raise RecoveryRequiredError(
            "refusing recovery because files have unknown content: " + ", ".join(unknown)
        )
    if report_state == "unknown":
        raise RecoveryRequiredError("refusing recovery because report has unknown content")

    def verify_payload_classification() -> None:
        changed = []
        for entry in entries:
            language = entry["language"]
            expected = entry[f"{states[language]}_sha256"]
            if _real_single_link_sha256(Path(entry["destination"])) != expected:
                changed.append(language)
        if changed:
            raise RecoveryRequiredError(
                "payload changed after recovery classification: " + ", ".join(changed)
            )

    def verify_report_classification() -> None:
        if report is None:
            return
        destination = Path(report["destination"])
        if report_state == "absent":
            if destination.exists() or destination.is_symlink():
                raise RecoveryRequiredError("report appeared during recovery")
            return
        if not destination.is_file() or _file_sha256(destination) != report["after_sha256"]:
            raise RecoveryRequiredError("report changed during recovery")
        if journal["state"] != "COMMITTED":
            stage = Path(report["stage"])
            if (
                not stage.is_file()
                or not os.path.samefile(destination, stage)
                or _file_sha256(stage) != report["after_sha256"]
            ):
                raise RecoveryRequiredError(
                    "published report is not owned by its canonical stage"
                )

    if journal["state"] == "COMMITTED":
        all_after = all(
            states[entry["language"]] == "after"
            or entry["before_sha256"] == entry["after_sha256"]
            for entry in entries
        )
        report_ok = report is None or report_state == "after"
        if all_after and report_ok:
            verify_payload_classification()
            verify_report_classification()
            _cleanup_journal_artifacts(journal, journal_path)
            return "committed"

    # Anything not durably marked and verified COMMITTED is rolled back.
    # Validate every rollback and every current destination before the first
    # unlink/replace.  Per-file checks are repeated immediately before each
    # operation.  This transaction assumes all cooperating writers honor the
    # advisory lock; a non-cooperating external writer is detected whenever a
    # hash/identity check observes it, and the journal remains recoverable.
    rollback_entries = [
        entry
        for entry in reversed(entries)
        if states[entry["language"]] == "after"
        and entry["before_sha256"] != entry["after_sha256"]
    ]
    for entry in rollback_entries:
        rollback = Path(entry["rollback"])
        _validate_single_link_file(
            rollback,
            f"{entry['language']} rollback copy",
        )
        if _file_sha256(rollback) != entry["before_sha256"]:
            raise RecoveryRequiredError(
                f"valid rollback copy is unavailable for {entry['language']}"
            )
    verify_payload_classification()
    verify_report_classification()

    if report is not None and report_state == "after":
        verify_report_classification()
        _unlink_if_present(Path(report["destination"]))
    for entry in rollback_entries:
        language = entry["language"]
        rollback = Path(entry["rollback"])
        _validate_single_link_file(rollback, f"{language} rollback copy")
        if _file_sha256(rollback) != entry["before_sha256"]:
            raise RecoveryRequiredError(f"valid rollback copy is unavailable for {language}")
        if _real_single_link_sha256(Path(entry["destination"])) != entry["after_sha256"]:
            raise RecoveryRequiredError(
                f"{language} payload changed immediately before rollback"
            )
        os.replace(rollback, entry["destination"])
        _fsync_directory(Path(entry["destination"]).parent)
    failed = [
        entry["language"]
        for entry in entries
        if _real_single_link_sha256(Path(entry["destination"]))
        != entry["before_sha256"]
    ]
    if failed:
        raise RecoveryRequiredError(
            "rollback did not restore original payloads: " + ", ".join(failed)
        )
    _cleanup_journal_artifacts(journal, journal_path)
    return "rolled_back"


def recover_payload_transaction(
    payload_paths: Mapping[str, os.PathLike[str] | str],
    *,
    journal_path: os.PathLike[str] | str,
    lock_path: os.PathLike[str] | str,
    report_directory: os.PathLike[str] | str,
    protected_paths: Mapping[str, os.PathLike[str] | str] | None = None,
) -> str:
    """Recover a stale transaction and return none/rolled_back/committed."""

    payloads = _normalise_payload_paths(payload_paths)
    journal = Path(journal_path).absolute()
    lock_path_obj = Path(lock_path).absolute()
    report_dir = Path(report_directory).absolute()
    if not report_dir.is_dir() or report_dir.is_symlink():
        raise PayloadTransactionError(f"invalid transaction output directory: {report_dir}")
    if journal.parent.resolve(strict=True) != report_dir.resolve(strict=True):
        raise PayloadTransactionError("journal must be directly inside report_directory")
    if lock_path_obj.parent.resolve(strict=True) != report_dir.resolve(strict=True):
        raise PayloadTransactionError("lock must be directly inside report_directory")
    if journal.is_symlink() or lock_path_obj.is_symlink():
        raise PayloadTransactionError("journal and lock paths must not be symlinks")
    recovery_protected = {
        f"caller:{name}": Path(value).absolute()
        for name, value in (protected_paths or {}).items()
    }
    all_protected = {
        **payloads,
        "journal": journal,
        "lock": lock_path_obj,
        **recovery_protected,
    }
    _assert_paths_distinct(all_protected)
    lock = _SingleWriterLock(
        lock_path_obj,
        {name: path for name, path in all_protected.items() if name != "lock"},
    )
    lock.acquire()
    try:
        return _recover_locked(
            journal,
            payloads,
            report_dir,
            lock_path_obj,
            recovery_protected,
        )
    finally:
        lock.release()


def _normalise_payload_paths(
    payload_paths: Mapping[str, os.PathLike[str] | str],
) -> dict[str, Path]:
    if set(payload_paths) != set(LANGUAGES):
        raise PayloadTransactionError(
            f"payload languages must be exactly {LANGUAGES}: {sorted(payload_paths)}"
        )
    payloads = {language: Path(payload_paths[language]).absolute() for language in LANGUAGES}
    for language, path in payloads.items():
        if (
            not path.is_file()
            or path.is_symlink()
            or path.stat().st_nlink != 1
        ):
            raise PayloadTransactionError(f"{language} payload must be a real file: {path}")
    _assert_paths_distinct(payloads)
    return payloads


def _remove_own_artifacts(paths: list[Path]) -> None:
    for path in paths:
        _unlink_if_present(path)


def apply_payload_transaction(
    payload_paths: Mapping[str, os.PathLike[str] | str],
    candidate_builder: Callable[[Mapping[str, bytes]], Mapping[str, bytes]],
    *,
    journal_path: os.PathLike[str] | str,
    lock_path: os.PathLike[str] | str,
    report_directory: os.PathLike[str] | str,
    report_path: os.PathLike[str] | str | None = None,
    report_value: Mapping[str, Any] | None = None,
    protected_paths: Mapping[str, os.PathLike[str] | str] | None = None,
    keep_permanent_backups: bool = False,
    candidate_validator: Callable[[Mapping[str, bytes], Mapping[str, bytes]], None] | None = None,
    before_commit: Callable[[], None] | None = None,
    payload_replace: Callable[[os.PathLike[str] | str, os.PathLike[str] | str], None] = os.replace,
    stage_writer: Callable[[Path, bytes], None] = _write_bytes_exclusive,
) -> TransactionResult:
    """Apply JA/ZH/KO candidate bytes with rollback and crash recovery.

    ``candidate_builder`` receives the exact immutable bytes captured by this
    function.  This prevents a caller from planning from one read and applying
    against a later read.  ``candidate_validator`` is the hook for the R98
    pinned-target and trilingual-boundary checks; it runs before any write.

    ``before_commit``, ``payload_replace``, and ``stage_writer`` exist so the
    failure paths can be tested deterministically.  Production callers should
    leave them at their defaults.
    """

    payloads = _normalise_payload_paths(payload_paths)
    journal = Path(journal_path).absolute()
    lock_path_obj = Path(lock_path).absolute()
    report_dir = Path(report_directory).absolute()
    if not report_dir.is_dir() or report_dir.is_symlink():
        raise PayloadTransactionError(f"invalid transaction output directory: {report_dir}")
    if journal.parent.resolve(strict=True) != report_dir.resolve(strict=True):
        raise PayloadTransactionError("journal must be directly inside report_directory")
    if lock_path_obj.parent.resolve(strict=True) != report_dir.resolve(strict=True):
        raise PayloadTransactionError("lock must be directly inside report_directory")
    if journal.is_symlink() or lock_path_obj.is_symlink():
        raise PayloadTransactionError("journal and lock paths must not be symlinks")

    base_protected: dict[str, Path] = {
        **payloads,
        "journal": journal,
        "lock": lock_path_obj,
    }
    for name, value in (protected_paths or {}).items():
        base_protected[f"caller:{name}"] = Path(value).absolute()
    _assert_paths_distinct(base_protected)

    recovery_protected = {
        name: path
        for name, path in base_protected.items()
        if name.startswith("caller:")
    }
    writer_lock = _SingleWriterLock(
        lock_path_obj,
        {name: path for name, path in base_protected.items() if name != "lock"},
    )
    writer_lock.acquire()
    transaction_id = uuid.uuid4().hex
    created: list[Path] = []
    journal_published = False
    try:
        _recover_locked(
            journal,
            payloads,
            report_dir,
            lock_path_obj,
            recovery_protected,
        )

        orphaned: list[Path] = []
        for payload in payloads.values():
            orphaned.extend(payload.parent.glob(f".{payload.name}.r98-*.stage"))
            orphaned.extend(payload.parent.glob(f".{payload.name}.r98-*.rollback"))
        if orphaned:
            raise RecoveryRequiredError(
                "orphan transaction artifacts exist without an active journal: "
                + ", ".join(os.fspath(path) for path in sorted(orphaned))
            )

        # Capture all three sources, then re-read all three before using the
        # snapshot.  A concurrent writer during capture therefore aborts.
        snapshots = {language: _file_bytes(payloads[language]) for language in LANGUAGES}
        before_sha = {language: _sha256(snapshots[language]) for language in LANGUAGES}
        for language in LANGUAGES:
            if _file_sha256(payloads[language]) != before_sha[language]:
                raise ConcurrentModificationError(
                    f"{language} payload changed while the common snapshot was captured"
                )

        built = candidate_builder(dict(snapshots))
        if set(built) != set(LANGUAGES):
            raise PayloadTransactionError("candidate builder must return exactly JA/ZH/KO")
        candidates: dict[str, bytes] = {}
        for language in LANGUAGES:
            value = built[language]
            if not isinstance(value, bytes) or not value:
                raise PayloadTransactionError(f"{language} candidate must be nonempty bytes")
            candidates[language] = value
        if candidate_validator is not None:
            candidate_validator(dict(snapshots), dict(candidates))
        after_sha = {language: _sha256(candidates[language]) for language in LANGUAGES}

        stages = {
            language: payloads[language].with_name(
                f".{payloads[language].name}.r98-{transaction_id}.stage"
            )
            for language in LANGUAGES
        }
        rollbacks = {
            language: payloads[language].with_name(
                f".{payloads[language].name}.r98-{transaction_id}.rollback"
            )
            for language in LANGUAGES
        }
        all_protected = {
            **base_protected,
            **{f"stage:{k}": v for k, v in stages.items()},
            **{f"rollback:{k}": v for k, v in rollbacks.items()},
        }
        _assert_paths_distinct(all_protected)

        validated_report: Path | None = None
        report_stage: Path | None = None
        report_raw: bytes | None = None
        if report_path is not None:
            validated_report = validate_report_path(
                report_path,
                report_directory=report_dir,
                protected_paths=all_protected,
            )
            report_stage = validated_report.with_name(
                f".{validated_report.name}.r98-{transaction_id}.stage"
            )
            report_protected = {**all_protected, "report": validated_report}
            if any(_paths_alias(report_stage, path) for path in report_protected.values()):
                raise ReportPathError("report stage aliases a protected path")
            payload = dict(report_value or {})
            payload.update(
                {
                    "transaction_id": transaction_id,
                    "before_sha256": before_sha,
                    "after_sha256": after_sha,
                    "changed_languages": [
                        language
                        for language in LANGUAGES
                        if before_sha[language] != after_sha[language]
                    ],
                }
            )
            report_raw = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode(
                "utf-8"
            )

        # All stages and all mandatory rollback copies exist and are verified
        # before the first destination is replaced.
        for language in LANGUAGES:
            try:
                stage_writer(stages[language], candidates[language])
            except BaseException:
                _unlink_if_present(stages[language])
                raise
            created.append(stages[language])
            _validate_single_link_file(stages[language], f"{language} candidate stage")
            if _file_sha256(stages[language]) != after_sha[language]:
                raise PayloadTransactionError(f"{language} stage verification failed")
            try:
                stage_writer(rollbacks[language], snapshots[language])
            except BaseException:
                _unlink_if_present(rollbacks[language])
                raise
            created.append(rollbacks[language])
            _validate_single_link_file(rollbacks[language], f"{language} rollback copy")
            if _file_sha256(rollbacks[language]) != before_sha[language]:
                raise PayloadTransactionError(f"{language} rollback verification failed")
        if report_stage is not None and report_raw is not None:
            try:
                stage_writer(report_stage, report_raw)
            except BaseException:
                _unlink_if_present(report_stage)
                raise
            created.append(report_stage)
            _validate_single_link_file(report_stage, "report stage")
            if _file_sha256(report_stage) != _sha256(report_raw):
                raise PayloadTransactionError("report stage verification failed")

        entries = [
            {
                "language": language,
                "destination": os.fspath(payloads[language]),
                "stage": os.fspath(stages[language]),
                "rollback": os.fspath(rollbacks[language]),
                "before_sha256": before_sha[language],
                "after_sha256": after_sha[language],
            }
            for language in LANGUAGES
        ]
        journal_value: dict[str, Any] = {
            "schema_version": JOURNAL_SCHEMA,
            "transaction_id": transaction_id,
            "state": "PREPARED",
            "payloads": entries,
            "report": None,
        }
        if validated_report is not None and report_stage is not None and report_raw is not None:
            journal_value["report"] = {
                "destination": os.fspath(validated_report),
                "stage": os.fspath(report_stage),
                "after_sha256": _sha256(report_raw),
            }
        if journal.exists():
            raise RecoveryRequiredError(f"journal unexpectedly exists: {journal}")
        _write_json_replace(journal, journal_value)
        journal_published = True

        if before_commit is not None:
            before_commit()
        changed_during_precommit = [
            language
            for language in LANGUAGES
            if _file_sha256(payloads[language]) != before_sha[language]
        ]
        if changed_during_precommit:
            # No replace has happened yet.  Preserve the external writer's
            # bytes, remove only our own artifacts, and abort cleanly.
            _cleanup_journal_artifacts(journal_value, journal)
            journal_published = False
            raise ConcurrentModificationError(
                "payload changed before first replace: " + ", ".join(changed_during_precommit)
            )

        journal_value["state"] = "COMMITTING"
        _write_json_replace(journal, journal_value)

        try:
            for language in LANGUAGES:
                if _file_sha256(payloads[language]) != before_sha[language]:
                    raise ConcurrentModificationError(
                        f"{language} payload changed immediately before replace"
                    )
                if before_sha[language] == after_sha[language]:
                    continue
                payload_replace(stages[language], payloads[language])
                _fsync_directory(payloads[language].parent)
                if _file_sha256(payloads[language]) != after_sha[language]:
                    raise PayloadTransactionError(f"{language} post-replace verification failed")

            for language in LANGUAGES:
                if _file_sha256(payloads[language]) != after_sha[language]:
                    raise PayloadTransactionError(f"{language} final verification failed")

            if validated_report is not None and report_stage is not None:
                if validated_report.exists() or validated_report.is_symlink():
                    raise ReportPathError("report path appeared during transaction")
                # Hard-link publication is atomic and, unlike os.replace,
                # cannot overwrite a report created by a racing process.
                os.link(report_stage, validated_report)
                _fsync_directory(validated_report.parent)
                if _file_sha256(validated_report) != journal_value["report"]["after_sha256"]:
                    raise PayloadTransactionError("published report verification failed")

            journal_value["state"] = "COMMITTED"
            _write_json_replace(journal, journal_value)
        except BaseException as original:
            try:
                _recover_locked(
                    journal,
                    payloads,
                    report_dir,
                    lock_path_obj,
                    recovery_protected,
                )
                journal_published = False
            except BaseException as recovery_error:
                raise RecoveryRequiredError(
                    f"transaction failed and automatic rollback failed: {recovery_error}"
                ) from original
            raise

        # Optional permanent backups use an immutable transaction/SHA name;
        # no fixed .bak path is ever opened or overwritten.
        if keep_permanent_backups:
            for language in LANGUAGES:
                backup = payloads[language].with_name(
                    f"{payloads[language].name}.bak_r98_"
                    f"{before_sha[language][:16]}_{transaction_id}"
                )
                _write_bytes_exclusive(backup, snapshots[language])

        _cleanup_journal_artifacts(journal_value, journal)
        journal_published = False
        return TransactionResult(
            transaction_id=transaction_id,
            before_sha256=before_sha,
            after_sha256=after_sha,
            changed_languages=tuple(
                language for language in LANGUAGES if before_sha[language] != after_sha[language]
            ),
            report_path=os.fspath(validated_report) if validated_report is not None else None,
        )
    except BaseException:
        if not journal_published:
            _remove_own_artifacts(created)
        raise
    finally:
        writer_lock.release()


__all__ = [
    "ConcurrentModificationError",
    "LockHeldError",
    "PayloadTransactionError",
    "RecoveryRequiredError",
    "ReportPathError",
    "TransactionResult",
    "apply_payload_transaction",
    "recover_payload_transaction",
    "validate_report_path",
]
