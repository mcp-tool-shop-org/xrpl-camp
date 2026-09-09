"""Data models for XRPL Camp sessions and progress."""

from __future__ import annotations

import contextlib
import json
import logging
import os
import sys
import tempfile
import time
import warnings
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

from xrpl_camp.errors import EXIT_USER, CampError, CampFailure

logger = logging.getLogger("xrpl_camp.models")

# ---------------------------------------------------------------------------
# State location
# ---------------------------------------------------------------------------
#
# XRPL Camp keeps state PER DIRECTORY by design: a "sitting" belongs to the
# folder you ran it in, so two workshops in two folders do not collide. That is
# the product's model and it stays the default.
#
# It is, however, no longer implicit: `XRPL_CAMP_HOME` overrides the location,
# and `get_state_dir()` returns the resolved ABSOLUTE path so the CLI can show
# the learner exactly where their seed and progress live. A learner who `cd`s
# mid-sitting can point `XRPL_CAMP_HOME` at the original folder instead of
# silently starting over.

DEFAULT_STATE_DIRNAME = ".xrpl-camp"

#: Schema version written into session.json. Bump when the shape changes in a
#: way an older reader cannot handle; an older tool refuses a NEWER file
#: rather than rewriting it (see `Session.load`).
SESSION_SCHEMA_VERSION = 1

#: Name of the whole-state-directory lock (see `state_lock`).
LOCK_FILENAME = ".lock"

#: A lock older than this is assumed to belong to a process that died.
STALE_LOCK_SECONDS = 15 * 60


def _resolve_state_dir() -> Path:
    """Resolve the state directory from the environment.

    `XRPL_CAMP_HOME` wins when set and non-empty; otherwise state is
    directory-local (`./.xrpl-camp`).
    """
    override = os.environ.get("XRPL_CAMP_HOME", "").strip()
    if override:
        return Path(override).expanduser()
    return Path(DEFAULT_STATE_DIRNAME)


STATE_DIR = _resolve_state_dir()
SESSION_FILE = STATE_DIR / "session.json"
WALLET_FILE = STATE_DIR / "wallet.json"
MAILBOX_FILE = STATE_DIR / "mailbox.json"

#: Modules that import the path constants BY VALUE at import time. Rebinding
#: only this module's globals is what split a learner's state across two
#: directories: `wallet.py` kept writing wallet.json to the old location while
#: `models.py` wrote session.json to the new one, and `cli.reset` then deleted
#: one half and left the other. Any module listed here is written through.
_PATH_MIRRORS = ("xrpl_camp.wallet", "xrpl_camp.cli")
_PATH_NAMES = ("STATE_DIR", "SESSION_FILE", "WALLET_FILE", "MAILBOX_FILE")


def _sync_path_mirrors() -> None:
    """Push the resolved paths into every module that bound them by value.

    Only names the mirror already defines are written, so this cannot invent
    attributes on a module that never wanted them.
    """
    values = {
        "STATE_DIR": STATE_DIR,
        "SESSION_FILE": SESSION_FILE,
        "WALLET_FILE": WALLET_FILE,
        "MAILBOX_FILE": MAILBOX_FILE,
    }
    for name in _PATH_MIRRORS:
        module = sys.modules.get(name)
        if module is None:
            continue  # not imported yet; it will bind the fresh value itself
        for attr in _PATH_NAMES:
            if hasattr(module, attr):
                setattr(module, attr, values[attr])


def refresh_state_paths() -> Path:
    """Recompute the state paths from the environment. Returns the state dir.

    Module import happens once; this exists so a caller (or a test) that
    changes `XRPL_CAMP_HOME` afterwards can re-resolve deterministically —
    and "deterministically" has to mean *everywhere*, not just here. It now
    writes through to the modules that copied these constants at import time,
    so a post-refresh `save_wallet()` and `Session.save()` land in the SAME
    directory.
    """
    global STATE_DIR, SESSION_FILE, WALLET_FILE, MAILBOX_FILE
    STATE_DIR = _resolve_state_dir()
    SESSION_FILE = STATE_DIR / "session.json"
    WALLET_FILE = STATE_DIR / "wallet.json"
    MAILBOX_FILE = STATE_DIR / "mailbox.json"
    _sync_path_mirrors()
    return STATE_DIR


def state_dir() -> Path:
    """The state directory, resolved now. Prefer this over the constant."""
    return STATE_DIR


def session_file() -> Path:
    """Path of session.json, resolved now."""
    return SESSION_FILE


def wallet_file() -> Path:
    """Path of wallet.json, resolved now."""
    return WALLET_FILE


def mailbox_file() -> Path:
    """Path of mailbox.json, resolved now."""
    return MAILBOX_FILE


def get_state_dir() -> Path:
    """Absolute, resolved path of the state directory (for display).

    State is directory-local by default, so the *absolute* path is the only
    honest thing to show a learner: it is the answer to "where did my seed go?"
    """
    try:
        return STATE_DIR.resolve()
    except OSError:  # pragma: no cover - resolve() is effectively total
        return STATE_DIR.absolute()


def state_is_directory_local() -> bool:
    """True when state follows the working directory (no XRPL_CAMP_HOME set)."""
    return not os.environ.get("XRPL_CAMP_HOME", "").strip()


# ---------------------------------------------------------------------------
# Structured state errors (shipcheck Gate B: no raw stacks)
# ---------------------------------------------------------------------------


class StateFileError(CampFailure):
    """A state file on disk could not be read or parsed.

    Carries a structured :class:`~xrpl_camp.errors.CampError` so the CLI can
    render code + message + hint instead of a traceback. ``str(exc)`` is the
    full user-facing message, so even an unhandled instance ends in something
    actionable rather than a JSONDecodeError column number.
    """


class StateLockError(CampFailure):
    """Another xrpl-camp is working in this folder. Same structured shape."""


def _corrupt_state_error(path: Path, detail: str) -> StateFileError:
    return StateFileError(CampError(
        code="STATE_CORRUPT",
        message=f"Could not read {path}: {detail}",
        hint=(
            "The file is unreadable or malformed. Run `xrpl-camp reset` to "
            "start a fresh session (this deletes the local wallet and "
            "progress), or repair the file by hand."
        ),
        retryable=False,
    ))


def _future_state_error(path: Path, found: int) -> StateFileError:
    return StateFileError(CampError(
        code="STATE_TOO_NEW",
        message=(
            f"{path} was written by a newer version of xrpl-camp "
            f"(schema {found}; this build understands "
            f"{SESSION_SCHEMA_VERSION}). Nothing was changed."
        ),
        hint=(
            "Upgrade with `pipx upgrade xrpl-camp` (or `pip install -U "
            "xrpl-camp`) and run this again. Writing it with this build "
            "would discard the newer fields permanently."
        ),
        retryable=False,
        exit_code=EXIT_USER,
    ))


# ---------------------------------------------------------------------------
# Atomic, permission-aware writes
# ---------------------------------------------------------------------------

#: Directories we have already warned about, so the notice is once per run.
_warned_open_dirs: set[str] = set()


def _user_chose_this_path(target: Path) -> bool:
    """True when `target` is the path XRPL_CAMP_HOME points at, not our default."""
    override = os.environ.get("XRPL_CAMP_HOME", "").strip()
    if not override:
        return False
    try:
        return Path(override).expanduser().resolve() == target.resolve()
    except OSError:  # pragma: no cover - resolve() is effectively total
        return False


def _tighten_our_own_dir(target: Path) -> None:
    """Make our own state directory owner-only, and say that we did.

    Reached only for the default `./.xrpl-camp`, which xrpl-camp created. A
    loose mode here is an older version's mistake sitting on top of a wallet
    seed. Fixing it silently would be the "behind your back" change the warning
    path exists to avoid, so this says it out loud instead of staying quiet.
    """
    key = str(target)
    try:
        mode = target.stat().st_mode & 0o777
    except OSError:  # pragma: no cover
        return
    if not mode & 0o077:
        return
    try:
        os.chmod(target, 0o700)
    except OSError:  # pragma: no cover - fall back to telling them
        _warn_if_world_readable(target)
        return
    if key not in _warned_open_dirs:
        _warned_open_dirs.add(key)
        warnings.warn(
            f"{target} was readable by other users (mode {mode:04o}) and "
            "xrpl-camp keeps a wallet seed there, so it has been tightened to "
            "owner-only. An older version of this tool created it that way.",
            stacklevel=3,
        )


def _warn_if_world_readable(target: Path) -> None:
    """Tell the learner their seed is somewhere others can read it.

    We do NOT tighten a directory we did not create. `XRPL_CAMP_HOME` is a
    path the *user* chose — plausibly a shared workshop folder — and silently
    rewriting its permissions can lock other people out of a directory that
    was never ours. Saying so is the honest half of that trade.
    """
    key = str(target)
    if key in _warned_open_dirs:
        return
    try:
        mode = target.stat().st_mode & 0o777
    except OSError:  # pragma: no cover - stat on a directory we just wrote to
        return
    if not mode & 0o077:
        return
    _warned_open_dirs.add(key)
    warnings.warn(
        f"{target} is readable by other users on this machine (mode "
        f"{mode:04o}) and xrpl-camp keeps a wallet seed there. It was left "
        "as you set it rather than tightened behind your back; run "
        f"`chmod 700 {target}` if that is not what you want.",
        stacklevel=3,
    )


def ensure_state_dir(path: Path | None = None) -> Path:
    """Create the state directory with owner-only permissions on POSIX.

    A directory this call created is always tightened to 0700. A pre-existing
    one depends on **who chose the path**, and the two cases are genuinely
    different:

    * The default ``./.xrpl-camp`` is ours. If it is loose, an older xrpl-camp
      made it that way — that is our own past bug sitting on top of a wallet
      seed, and leaving it there out of politeness helps nobody. Tighten it,
      and say so out loud, which is the honest answer to "don't change things
      behind my back."
    * A path the user pointed ``XRPL_CAMP_HOME`` at is theirs — plausibly a
      shared workshop folder — and silently rewriting its permissions could
      lock other people out of a directory that was never ours. Warn instead.

    An earlier revision warned in both cases and a test asserted the upgrade
    path was tightened; CI caught the disagreement on POSIX, where it is the
    only place it can show.
    """
    target = path if path is not None else STATE_DIR
    created = True
    try:
        target.mkdir(parents=True, exist_ok=False, mode=0o700)
    except FileExistsError:
        created = False
    if os.name != "posix":
        return target
    if created:
        # mkdir's mode is masked by umask, so tighten explicitly.
        with contextlib.suppress(OSError):
            os.chmod(target, 0o700)
    elif _user_chose_this_path(target):
        _warn_if_world_readable(target)
    else:
        _tighten_our_own_dir(target)
    return target


def atomic_write_text(path: Path, text: str, *, mode: int | None = None) -> Path:
    """Write `text` to `path` atomically.

    Writes a sibling temp file in the same directory, fsyncs it, applies
    `mode` (POSIX only) BEFORE it is visible under the real name, then
    `os.replace()`s it into place — atomic on POSIX and on Windows. An
    interrupted write therefore leaves the previous good file intact instead
    of a half-truncated one.
    """
    parent = path.parent
    ensure_state_dir(parent)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(parent),
    )
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        if mode is not None and os.name == "posix":
            os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):  # cleanup is best effort
            tmp.unlink(missing_ok=True)
        raise
    return path


# ---------------------------------------------------------------------------
# The state-directory lock
# ---------------------------------------------------------------------------
#
# `atomic_write_text` makes each individual file write atomic, but there are
# three state files and there was no lock, lease or read-modify-write guard
# anywhere. Two processes in one folder therefore destroyed each other's
# state: session.json ended up attesting a wallet whose seed was no longer on
# disk, and the losing process's seed — possibly already funded — was gone.
#
# This is a single-machine advisory lock over one directory. It is
# deliberately not a distributed protocol.

_lock_depth = 0
_lock_path: Path | None = None


def _lock_file(target: Path | None = None) -> Path:
    return (target if target is not None else STATE_DIR) / LOCK_FILENAME


def _lock_is_stale(path: Path) -> bool:
    try:
        age = time.time() - path.stat().st_mtime
    except OSError:
        return True
    return age > STALE_LOCK_SECONDS


def _busy_error(path: Path) -> StateLockError:
    holder = ""
    with contextlib.suppress(OSError, ValueError):
        holder = path.read_text(encoding="utf-8").strip()
    return StateLockError(CampError(
        code="STATE_BUSY",
        message=(
            f"Another xrpl-camp is already working in {path.parent}. "
            "Nothing was changed."
        ),
        hint=(
            "Finish or close the other run, then try again. Two runs in one "
            "folder overwrite each other's wallet and progress. If nothing "
            f"else is running, delete {path}."
        ),
        retryable=True,
        detail=holder,
        exit_code=EXIT_USER,
    ))


@contextlib.contextmanager
def state_lock(target: Path | None = None, *, required: bool = True):
    """Hold an exclusive lock on the state directory for a whole command.

    Re-entrant within one process (nested `with` blocks share the outermost
    lock) so a command may take it once and the model layer can take it again
    without deadlocking. Set ``XRPL_CAMP_NO_LOCK=1`` to disable — intended for
    read-only tooling, not for concurrent writers.

    ``required=False`` degrades to a no-op when the lock is held by someone
    else, which is what the individual `save()` calls use: they still get
    mutual exclusion whenever they can, but a stuck lock must never make a
    learner's progress unsaveable.
    """
    global _lock_depth, _lock_path

    if _lock_depth > 0 or os.environ.get("XRPL_CAMP_NO_LOCK", "").strip():
        _lock_depth += 1
        try:
            yield False
        finally:
            _lock_depth -= 1
        return

    directory = target if target is not None else STATE_DIR
    ensure_state_dir(directory)
    path = _lock_file(directory)

    fd = None
    for _ in range(2):
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            break
        except FileExistsError:
            if not _lock_is_stale(path):
                break
            logger.debug("breaking a stale lock at %s", path)
            with contextlib.suppress(OSError):
                path.unlink()
        except OSError as exc:  # pragma: no cover - unwritable state dir
            logger.debug("could not create %s: %s", path, exc)
            break

    if fd is None:
        if required:
            raise _busy_error(path)
        yield False
        return

    stamp = f"pid={os.getpid()} at={datetime.now(UTC).isoformat()}"
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(stamp)
    except OSError:  # pragma: no cover - the lock exists either way
        with contextlib.suppress(OSError):
            os.close(fd)

    _lock_depth += 1
    _lock_path = path
    try:
        yield True
    finally:
        _lock_depth -= 1
        _lock_path = None
        with contextlib.suppress(OSError):
            path.unlink()


# ---------------------------------------------------------------------------
# Execution mode
# ---------------------------------------------------------------------------


class ExecutionMode(Enum):
    """Execution mode for the current session."""

    REAL = "real"
    DRY_RUN = "dry_run"


_execution_mode = ExecutionMode.REAL


def set_execution_mode(mode: ExecutionMode) -> None:
    """Set the global execution mode."""
    global _execution_mode
    _execution_mode = mode


def get_execution_mode() -> ExecutionMode:
    """Get the current execution mode."""
    return _execution_mode


def is_dry_run() -> bool:
    """Check if running in dry-run mode."""
    return _execution_mode == ExecutionMode.DRY_RUN


# ---------------------------------------------------------------------------
# Progress records
# ---------------------------------------------------------------------------
#
# The lessons produce far more than these records used to hold. lesson_4
# produces a memo, a destination, an amount, a fee and `created_account`;
# lesson_5 reads back the memo, ledger_index, close_time_iso, delivered and
# result. None of it was stored, and the concrete cost was that `xrpl-camp
# verify` had no memo to pass as `expected_memo` — so the "You wrote / Ledger
# returned / Identical" panel, the one assertion lesson 5 exists to
# demonstrate, was skipped on every standalone run.
#
# `LedgerEntry` is the append-only half: one row per ledger write, N per
# lesson. `txids` kept exactly one hash per lesson, so five real memo sends
# collapsed to one record and four permanent, fee-paid writes vanished.

#: Keys the dataclasses below own. Anything else in a persisted record is
#: round-tripped through `extra` rather than destroyed.
_ENTRY_KEYS = frozenset({
    "lesson", "txid", "memo", "destination", "amount_drops", "fee_drops",
    "created_account", "ledger_index", "close_time_iso", "recorded_at",
    "memo_type", "destination_tag", "submitted_at_ledger_index",
})
_PROGRESS_KEYS = frozenset({
    "lesson", "name", "completed_at", "txid", "started_at", "duration_seconds",
    "total_seconds", "attempts", "memo", "destination", "amount_drops",
    "fee_drops", "created_account", "ledger_index", "close_time_iso",
    "memo_type", "destination_tag",
})
_SESSION_KEYS = frozenset({
    "schema_version", "started_at", "wallet_address", "completed_lessons",
    "txids", "progress", "entries",
})


def _as_int(value: object, default: int = 0) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _as_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _leftovers(raw: dict, known: frozenset[str]) -> dict:
    """Keys a newer writer put here that this build does not understand."""
    return {k: v for k, v in raw.items() if k not in known}


@dataclass
class LedgerEntry:
    """One ledger write, recorded permanently. Many per lesson.

    Written append-only: a repeat send adds a row, it does not replace one.
    ``ledger_index`` and ``close_time_iso`` come from the ledger itself, so a
    machine with a wrong clock produces a record that can still be checked
    against the chain — and a Testnet reset becomes distinguishable from a
    forged pack, because the recorded ledger index either predates the
    endpoint's history or it does not.
    """

    lesson: int
    txid: str = ""
    memo: str = ""
    destination: str = ""
    amount_drops: int = 0
    fee_drops: int = 0
    created_account: bool = False
    ledger_index: int = 0
    close_time_iso: str = ""
    recorded_at: str = ""
    #: MemoType the payment carried. Recorded because it is what makes a set
    #: of entries filterable back OFF the ledger — `xrpl-camp/diary` picks the
    #: learner's writing out of a history that also holds the faucet grant.
    memo_type: str = ""
    #: DestinationTag, when one was sent. ``None`` means "no tag"; ``0`` is a
    #: real tag, which is why this is not an int with a 0 default.
    destination_tag: int | None = None
    #: Validated ledger index at the moment of sending. With `ledger_index`
    #: (where it landed) this is how many ledgers closed while the learner
    #: waited — a real number for the sentence lesson 4 hand-waves.
    submitted_at_ledger_index: int = 0
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        data = {
            "lesson": self.lesson,
            "txid": self.txid,
            "memo": self.memo,
            "destination": self.destination,
            "amount_drops": self.amount_drops,
            "fee_drops": self.fee_drops,
            "created_account": self.created_account,
            "ledger_index": self.ledger_index,
            "close_time_iso": self.close_time_iso,
            "recorded_at": self.recorded_at,
            "memo_type": self.memo_type,
            "destination_tag": self.destination_tag,
            "submitted_at_ledger_index": self.submitted_at_ledger_index,
        }
        data.update(self.extra)
        return data

    @classmethod
    def from_dict(cls, raw: dict) -> LedgerEntry | None:
        lesson = raw.get("lesson")
        if not isinstance(lesson, int):
            return None
        return cls(
            lesson=lesson,
            txid=str(raw.get("txid", "") or ""),
            memo=str(raw.get("memo", "") or ""),
            destination=str(raw.get("destination", "") or ""),
            amount_drops=_as_int(raw.get("amount_drops")),
            fee_drops=_as_int(raw.get("fee_drops")),
            created_account=bool(raw.get("created_account", False)),
            ledger_index=_as_int(raw.get("ledger_index")),
            close_time_iso=str(raw.get("close_time_iso", "") or ""),
            recorded_at=str(raw.get("recorded_at", "") or ""),
            memo_type=str(raw.get("memo_type", "") or ""),
            destination_tag=(
                None if raw.get("destination_tag") is None
                else _as_int(raw.get("destination_tag"))
            ),
            submitted_at_ledger_index=_as_int(
                raw.get("submitted_at_ledger_index"),
            ),
            extra=_leftovers(raw, _ENTRY_KEYS),
        )


@dataclass
class LessonProgress:
    """Record of a completed lesson.

    ``duration_seconds`` stays the LAST attempt (the field callers and the
    certificate already read). ``total_seconds`` accumulates every attempt, so
    a learner who retried lesson 4 four times gets a training time that
    reflects what they actually spent.
    """

    lesson: int
    name: str
    completed_at: str
    txid: str = ""
    started_at: str = ""
    duration_seconds: float = 0.0
    total_seconds: float = 0.0
    attempts: int = 1
    memo: str = ""
    destination: str = ""
    amount_drops: int = 0
    fee_drops: int = 0
    created_account: bool = False
    ledger_index: int = 0
    close_time_iso: str = ""
    memo_type: str = ""
    destination_tag: int | None = None
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        data = {
            "lesson": self.lesson,
            "name": self.name,
            "completed_at": self.completed_at,
            "txid": self.txid,
            "started_at": self.started_at,
            "duration_seconds": self.duration_seconds,
            "total_seconds": self.total_seconds,
            "attempts": self.attempts,
            "memo": self.memo,
            "destination": self.destination,
            "amount_drops": self.amount_drops,
            "fee_drops": self.fee_drops,
            "created_account": self.created_account,
            "ledger_index": self.ledger_index,
            "close_time_iso": self.close_time_iso,
            "memo_type": self.memo_type,
            "destination_tag": self.destination_tag,
        }
        data.update(self.extra)
        return data

    @classmethod
    def from_dict(cls, raw: dict) -> LessonProgress | None:
        lesson = raw.get("lesson")
        if not isinstance(lesson, int):
            return None
        duration = _as_float(raw.get("duration_seconds"))
        return cls(
            lesson=lesson,
            name=str(raw.get("name", "") or ""),
            completed_at=str(raw.get("completed_at", "") or ""),
            txid=str(raw.get("txid", "") or ""),
            started_at=str(raw.get("started_at", "") or ""),
            duration_seconds=duration,
            total_seconds=_as_float(raw.get("total_seconds"), duration),
            attempts=max(1, _as_int(raw.get("attempts"), 1)),
            memo=str(raw.get("memo", "") or ""),
            destination=str(raw.get("destination", "") or ""),
            amount_drops=_as_int(raw.get("amount_drops")),
            fee_drops=_as_int(raw.get("fee_drops")),
            created_account=bool(raw.get("created_account", False)),
            ledger_index=_as_int(raw.get("ledger_index")),
            close_time_iso=str(raw.get("close_time_iso", "") or ""),
            memo_type=str(raw.get("memo_type", "") or ""),
            destination_tag=(
                None if raw.get("destination_tag") is None
                else _as_int(raw.get("destination_tag"))
            ),
            extra=_leftovers(raw, _PROGRESS_KEYS),
        )


@dataclass
class Session:
    """Tracks progress through XRPL Camp lessons."""

    started_at: str = ""
    wallet_address: str = ""
    completed_lessons: list[int] = field(default_factory=list)
    txids: dict[str, str] = field(default_factory=dict)
    progress: list[LessonProgress] = field(default_factory=list)
    entries: list[LedgerEntry] = field(default_factory=list)
    extra: dict = field(default_factory=dict)

    def mark_complete(
        self,
        lesson: int,
        name: str,
        txid: str = "",
        started_at: str = "",
        duration_seconds: float = 0.0,
        *,
        memo: str = "",
        destination: str = "",
        amount_drops: int = 0,
        fee_drops: int = 0,
        created_account: bool = False,
        ledger_index: int = 0,
        close_time_iso: str = "",
        memo_type: str = "",
        destination_tag: int | None = None,
        submitted_at_ledger_index: int = 0,
    ) -> None:
        """Mark a lesson as completed. Re-running a lesson UPDATES the record.

        Both summary stores — the `progress` list and the `txids` map — are
        written together so they can never diverge. Re-running `xrpl-camp
        send` used to leave `progress[].txid` on the first hash while
        `txids["lesson_4"]` moved to the second, which made the sealed proof
        pack attest two different transactions for the same lesson. Last write
        wins, in both places, or in neither.

        A new hash ALSO appends to `entries`, which is append-only. Five real
        memo sends are five permanent, fee-paid ledger writes; collapsing them
        to one summary row is fine, throwing four of them away is not.
        """
        if lesson not in self.completed_lessons:
            self.completed_lessons.append(lesson)

        now = datetime.now(UTC).isoformat()
        existing = self.get_progress(lesson)
        if existing is None:
            existing = LessonProgress(
                lesson=lesson,
                name=name,
                completed_at=now,
                txid=txid,
                started_at=started_at,
                duration_seconds=duration_seconds,
                total_seconds=duration_seconds,
                attempts=1,
                memo=memo,
                destination=destination,
                amount_drops=amount_drops,
                fee_drops=fee_drops,
                created_account=created_account,
                ledger_index=ledger_index,
                close_time_iso=close_time_iso,
                memo_type=memo_type,
                destination_tag=destination_tag,
            )
            self.progress.append(existing)
        else:
            existing.completed_at = now
            existing.attempts = max(1, existing.attempts) + 1
            if name:
                existing.name = name
            if started_at:
                existing.started_at = started_at
            if duration_seconds:
                existing.duration_seconds = duration_seconds
                existing.total_seconds += duration_seconds
            # Only overwrite the hash when a new one was actually produced,
            # so a txid-less re-run cannot blank an earlier real transaction.
            if txid:
                existing.txid = txid
            if memo:
                existing.memo = memo
            if destination:
                existing.destination = destination
            if amount_drops:
                existing.amount_drops = amount_drops
            if fee_drops:
                existing.fee_drops = fee_drops
            if created_account:
                existing.created_account = True
            if ledger_index:
                existing.ledger_index = ledger_index
            if close_time_iso:
                existing.close_time_iso = close_time_iso
            if memo_type:
                existing.memo_type = memo_type
            if destination_tag is not None:
                existing.destination_tag = destination_tag

        if txid:
            self.txids[f"lesson_{lesson}"] = txid
            self.record_entry(
                lesson,
                txid=txid,
                memo=memo,
                destination=destination,
                amount_drops=amount_drops,
                fee_drops=fee_drops,
                created_account=created_account,
                ledger_index=ledger_index,
                close_time_iso=close_time_iso,
                memo_type=memo_type,
                destination_tag=destination_tag,
                submitted_at_ledger_index=submitted_at_ledger_index,
                recorded_at=now,
            )

    def record_entry(self, lesson: int, *, txid: str = "", **fields) -> LedgerEntry:
        """Append one ledger write to the permanent record (idempotent by hash).

        Fields this build does not know are DROPPED, not stored — so a caller
        that invents a name gets a silently empty record, which is the exact
        failure mode this record was written to end (a real, live-funded run
        producing ``ledger_index=0`` and ``close_time_iso=""`` throughout while
        every value sat in local scope at the call site). Unknown keys are
        therefore logged rather than swallowed in silence.
        """
        unknown = sorted(set(fields) - _ENTRY_KEYS - {"recorded_at"})
        if unknown:
            logger.debug(
                "record_entry(lesson=%s) dropped unknown field(s): %s",
                lesson, ", ".join(unknown),
            )
        for existing in self.entries:
            if txid and existing.txid == txid:
                for key, value in fields.items():
                    if not hasattr(existing, key):
                        continue
                    # `destination_tag` may legitimately be 0, so it cannot
                    # share the truthiness test that protects the others from
                    # being blanked by a re-run that produced no new value.
                    if key == "destination_tag":
                        if value is not None:
                            setattr(existing, key, value)
                    elif value:
                        setattr(existing, key, value)
                return existing
        recorded_at = fields.pop("recorded_at", "") or datetime.now(UTC).isoformat()
        entry = LedgerEntry(
            lesson=lesson,
            txid=txid,
            recorded_at=recorded_at,
            **{
                k: v for k, v in fields.items()
                if k in _ENTRY_KEYS and k not in ("lesson", "txid", "recorded_at")
            },
        )
        self.entries.append(entry)
        return entry

    def entries_for(self, lesson: int) -> list[LedgerEntry]:
        """Every ledger write recorded for `lesson`, oldest first."""
        return [e for e in self.entries if e.lesson == lesson]

    def is_complete(self, lesson: int) -> bool:
        """Check if a lesson has been completed."""
        return lesson in self.completed_lessons

    def total_duration(self) -> float:
        """Total training time in seconds, summed across every attempt."""
        return sum(p.total_seconds or p.duration_seconds for p in self.progress)

    def get_progress(self, lesson: int) -> LessonProgress | None:
        """Get progress record for a specific lesson."""
        for p in self.progress:
            if p.lesson == lesson:
                return p
        return None

    def memo_for(self, lesson: int = 4) -> str:
        """The memo this session actually sent, or "".

        `xrpl-camp verify` had nothing to pass as `expected_memo` because the
        session never stored one, so the readback comparison lesson 5 exists
        for was skipped on the standalone path.
        """
        for entry in reversed(self.entries):
            if entry.lesson == lesson and entry.memo:
                return entry.memo
        record = self.get_progress(lesson)
        return record.memo if record is not None else ""

    def to_dict(self) -> dict:
        """The persisted shape, including anything a newer build wrote."""
        data = {
            "schema_version": SESSION_SCHEMA_VERSION,
            "started_at": self.started_at,
            "wallet_address": self.wallet_address,
            "completed_lessons": self.completed_lessons,
            "txids": self.txids,
            "progress": [p.to_dict() for p in self.progress],
            "entries": [e.to_dict() for e in self.entries],
        }
        data.update(self.extra)
        return data

    def _merge_from_disk(self) -> None:
        """Fold anything another process wrote back in before overwriting it.

        Measured, with two real subprocesses sharing one XRPL_CAMP_HOME: the
        one that saved last wrote the state it had loaded minutes earlier, and
        the other's completed lesson simply disappeared. `save()` rebuilt the
        file from in-memory fields, so whoever wrote last won everything.
        Re-reading under the lock and merging makes the loser's work survive.
        """
        try:
            other = Session.load()
        except StateFileError:
            return  # a corrupt or newer file is not something to merge blindly
        if other is None:
            return

        gained = False
        for lesson in other.completed_lessons:
            if lesson not in self.completed_lessons:
                self.completed_lessons.append(lesson)
                gained = True
        if gained:
            self.completed_lessons.sort()

        for key, value in other.txids.items():
            self.txids.setdefault(key, value)

        added_progress = False
        for record in other.progress:
            if self.get_progress(record.lesson) is None:
                self.progress.append(record)
                added_progress = True
        if added_progress:
            # Only reorder when a foreign row was folded in — otherwise the
            # caller's own ordering is left exactly as it was.
            self.progress.sort(key=lambda p: p.lesson)

        known = {e.txid for e in self.entries if e.txid}
        for entry in other.entries:
            if entry.txid and entry.txid in known:
                continue
            self.entries.append(entry)

        for key, value in other.extra.items():
            self.extra.setdefault(key, value)

        if not self.started_at:
            self.started_at = other.started_at

    def save(self) -> None:
        """Persist session to disk atomically, under the state-directory lock.

        The lock is taken with ``required=False``: mutual exclusion whenever
        it is available, but a stale or unobtainable lock must never make a
        learner's progress unsaveable. The merge below is what actually stops
        the data loss; the lock stops the merge from racing.
        """
        with state_lock(SESSION_FILE.parent, required=False):
            self._merge_from_disk()
            atomic_write_text(SESSION_FILE, json.dumps(self.to_dict(), indent=2))

    def wallet_disagreement(self) -> tuple[str, str] | None:
        """``(session_address, wallet_file_address)`` when they differ.

        Nothing used to detect this. After two concurrent runs, session.json
        attested one wallet while wallet.json held another — the session
        vouching for a seed that was no longer on disk.
        """
        if not self.wallet_address or not WALLET_FILE.exists():
            return None
        try:
            raw = json.loads(WALLET_FILE.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None
        on_disk = str(raw.get("address", "") or "") if isinstance(raw, dict) else ""
        if on_disk and on_disk != self.wallet_address:
            return self.wallet_address, on_disk
        return None

    @classmethod
    def load(cls) -> Session | None:
        """Load session from disk. Returns None if no session exists.

        Raises :class:`StateFileError` (structured, no traceback) when the file
        exists but cannot be read or parsed, or when it was written by a
        NEWER schema than this build understands — refusing beats silently
        rewriting a file whose extra fields we would then destroy. Unusable
        progress entries are skipped rather than crashing the whole load.
        """
        if not SESSION_FILE.exists():
            return None
        try:
            raw = SESSION_FILE.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            raise _corrupt_state_error(SESSION_FILE, str(e)) from e
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise _corrupt_state_error(SESSION_FILE, f"invalid JSON ({e.msg})") from e

        if not isinstance(data, dict):
            raise _corrupt_state_error(
                SESSION_FILE,
                f"expected a JSON object, found {type(data).__name__}",
            )

        version = _as_int(data.get("schema_version", SESSION_SCHEMA_VERSION),
                          SESSION_SCHEMA_VERSION)
        if version > SESSION_SCHEMA_VERSION:
            raise _future_state_error(SESSION_FILE, version)

        completed = data.get("completed_lessons", [])
        if not isinstance(completed, list):
            completed = []
        txids = data.get("txids", {})
        if not isinstance(txids, dict):
            txids = {}

        session = cls(
            started_at=str(data.get("started_at", "") or ""),
            wallet_address=str(data.get("wallet_address", "") or ""),
            completed_lessons=[n for n in completed if isinstance(n, int)],
            txids={str(k): str(v) for k, v in txids.items()},
            # Unknown top-level keys are carried, not destroyed: an older
            # build writing over a newer file used to discard them silently.
            extra=_leftovers(data, _SESSION_KEYS),
        )

        entries = data.get("progress", [])
        if not isinstance(entries, list):
            entries = []
        for p in entries:
            if not isinstance(p, dict):
                continue
            try:
                record = LessonProgress.from_dict(p)
            except (TypeError, ValueError):
                # One malformed entry must not cost the learner the session.
                continue
            if record is not None:
                session.progress.append(record)

        ledger_rows = data.get("entries", [])
        if isinstance(ledger_rows, list):
            for row in ledger_rows:
                if not isinstance(row, dict):
                    continue
                try:
                    entry = LedgerEntry.from_dict(row)
                except (TypeError, ValueError):
                    continue
                if entry is not None:
                    session.entries.append(entry)

        mismatch = session.wallet_disagreement()
        if mismatch is not None:
            # A Python warning rather than a print: it reaches stderr on a
            # real run without inserting itself into the lesson's rendered
            # output, and a caller that wants to show it properly can ask
            # `wallet_disagreement()` directly.
            warnings.warn(
                f"session.json attests wallet {mismatch[0]} but wallet.json "
                f"holds {mismatch[1]}. Two xrpl-camp runs probably shared "
                "this folder; the seed for the attested wallet may be gone.",
                stacklevel=2,
            )
        return session

    @classmethod
    def get_or_create(cls) -> Session:
        """Load existing session or create a new one."""
        session = cls.load()
        if session is None:
            session = cls(
                started_at=datetime.now(UTC).isoformat(),
            )
            session.save()
        return session


@dataclass
class DryRunSession(Session):
    """Session that never persists to disk. Used in dry-run mode."""

    def save(self) -> None:
        """No-op: dry-run sessions are ephemeral."""

    @classmethod
    def get_or_create(cls) -> DryRunSession:
        """Create a fresh ephemeral session (no disk reads or writes)."""
        return cls(started_at=datetime.now(UTC).isoformat())

    @classmethod
    def from_existing(cls) -> DryRunSession:
        """Load existing session state into a non-persisting session.

        Used by standalone commands (fund, send, verify) in dry-run mode
        where a real session already exists from a previous run.
        """
        real = Session.load()
        if real is None:
            return cls(started_at=datetime.now(UTC).isoformat())
        return cls(
            started_at=real.started_at,
            wallet_address=real.wallet_address,
            completed_lessons=list(real.completed_lessons),
            txids=dict(real.txids),
            progress=list(real.progress),
            entries=list(real.entries),
            extra=dict(real.extra),
        )
