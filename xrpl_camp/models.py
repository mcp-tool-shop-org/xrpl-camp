"""Data models for XRPL Camp sessions and progress."""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

from xrpl_camp.errors import CampError, CampFailure

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


def refresh_state_paths() -> Path:
    """Recompute the state paths from the environment. Returns the state dir.

    Module import happens once; this exists so a caller (or a test) that
    changes `XRPL_CAMP_HOME` afterwards can re-resolve deterministically.
    """
    global STATE_DIR, SESSION_FILE, WALLET_FILE, MAILBOX_FILE
    STATE_DIR = _resolve_state_dir()
    SESSION_FILE = STATE_DIR / "session.json"
    WALLET_FILE = STATE_DIR / "wallet.json"
    MAILBOX_FILE = STATE_DIR / "mailbox.json"
    return STATE_DIR


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


# ---------------------------------------------------------------------------
# Atomic, permission-aware writes
# ---------------------------------------------------------------------------


def ensure_state_dir(path: Path | None = None) -> Path:
    """Create the state directory with owner-only permissions on POSIX."""
    target = path if path is not None else STATE_DIR
    target.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name == "posix":
        # Best effort: a directory that already existed keeps its own mode
        # unless we can tighten it.
        with contextlib.suppress(OSError):
            os.chmod(target, 0o700)
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


@dataclass
class LessonProgress:
    """Record of a completed lesson."""

    lesson: int
    name: str
    completed_at: str
    txid: str = ""
    started_at: str = ""
    duration_seconds: float = 0.0


@dataclass
class Session:
    """Tracks progress through XRPL Camp lessons."""

    started_at: str = ""
    wallet_address: str = ""
    completed_lessons: list[int] = field(default_factory=list)
    txids: dict[str, str] = field(default_factory=dict)
    progress: list[LessonProgress] = field(default_factory=list)

    def mark_complete(
        self,
        lesson: int,
        name: str,
        txid: str = "",
        started_at: str = "",
        duration_seconds: float = 0.0,
    ) -> None:
        """Mark a lesson as completed. Re-running a lesson UPDATES the record.

        Both stores — the `progress` list and the `txids` map — are written
        together so they can never diverge. Re-running `xrpl-camp send` used to
        leave `progress[].txid` on the first hash while `txids["lesson_4"]`
        moved to the second, which made the sealed proof pack attest two
        different transactions for the same lesson. Last write wins, in both
        places, or in neither.
        """
        if lesson not in self.completed_lessons:
            self.completed_lessons.append(lesson)

        now = datetime.now(UTC).isoformat()
        existing = self.get_progress(lesson)
        if existing is None:
            self.progress.append(LessonProgress(
                lesson=lesson,
                name=name,
                completed_at=now,
                txid=txid,
                started_at=started_at,
                duration_seconds=duration_seconds,
            ))
        else:
            existing.completed_at = now
            if name:
                existing.name = name
            if started_at:
                existing.started_at = started_at
            if duration_seconds:
                existing.duration_seconds = duration_seconds
            # Only overwrite the hash when a new one was actually produced,
            # so a txid-less re-run cannot blank an earlier real transaction.
            if txid:
                existing.txid = txid

        if txid:
            self.txids[f"lesson_{lesson}"] = txid

    def is_complete(self, lesson: int) -> bool:
        """Check if a lesson has been completed."""
        return lesson in self.completed_lessons

    def total_duration(self) -> float:
        """Total training time in seconds across all completed lessons."""
        return sum(p.duration_seconds for p in self.progress)

    def get_progress(self, lesson: int) -> LessonProgress | None:
        """Get progress record for a specific lesson."""
        for p in self.progress:
            if p.lesson == lesson:
                return p
        return None

    def save(self) -> None:
        """Persist session to disk atomically."""
        data = {
            "started_at": self.started_at,
            "wallet_address": self.wallet_address,
            "completed_lessons": self.completed_lessons,
            "txids": self.txids,
            "progress": [
                {
                    "lesson": p.lesson,
                    "name": p.name,
                    "completed_at": p.completed_at,
                    "txid": p.txid,
                    "started_at": p.started_at,
                    "duration_seconds": p.duration_seconds,
                }
                for p in self.progress
            ],
        }
        atomic_write_text(SESSION_FILE, json.dumps(data, indent=2))

    @classmethod
    def load(cls) -> Session | None:
        """Load session from disk. Returns None if no session exists.

        Raises :class:`StateFileError` (structured, no traceback) when the file
        exists but cannot be read or parsed. Unusable progress entries are
        skipped rather than crashing the whole load.
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
        )

        entries = data.get("progress", [])
        if not isinstance(entries, list):
            entries = []
        for p in entries:
            if not isinstance(p, dict):
                continue
            lesson = p.get("lesson")
            if not isinstance(lesson, int):
                continue
            try:
                session.progress.append(LessonProgress(
                    lesson=lesson,
                    name=str(p.get("name", "") or ""),
                    completed_at=str(p.get("completed_at", "") or ""),
                    txid=str(p.get("txid", "") or ""),
                    started_at=str(p.get("started_at", "") or ""),
                    duration_seconds=float(p.get("duration_seconds", 0.0) or 0.0),
                ))
            except (TypeError, ValueError):
                # One malformed entry must not cost the learner the session.
                continue
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
        )
