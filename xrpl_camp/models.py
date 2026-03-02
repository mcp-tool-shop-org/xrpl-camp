"""Data models for XRPL Camp sessions and progress."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

STATE_DIR = Path(".xrpl-camp")
SESSION_FILE = STATE_DIR / "session.json"
WALLET_FILE = STATE_DIR / "wallet.json"


@dataclass
class LessonProgress:
    """Record of a completed lesson."""

    lesson: int
    name: str
    completed_at: str
    txid: str = ""


@dataclass
class Session:
    """Tracks progress through XRPL Camp lessons."""

    started_at: str = ""
    wallet_address: str = ""
    completed_lessons: list[int] = field(default_factory=list)
    txids: dict[str, str] = field(default_factory=dict)
    progress: list[LessonProgress] = field(default_factory=list)

    def mark_complete(self, lesson: int, name: str, txid: str = "") -> None:
        """Mark a lesson as completed."""
        if lesson not in self.completed_lessons:
            self.completed_lessons.append(lesson)
            self.progress.append(LessonProgress(
                lesson=lesson,
                name=name,
                completed_at=datetime.now(UTC).isoformat(),
                txid=txid,
            ))
        if txid:
            self.txids[f"lesson_{lesson}"] = txid

    def is_complete(self, lesson: int) -> bool:
        """Check if a lesson has been completed."""
        return lesson in self.completed_lessons

    def save(self) -> None:
        """Persist session to disk."""
        STATE_DIR.mkdir(parents=True, exist_ok=True)
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
                }
                for p in self.progress
            ],
        }
        SESSION_FILE.write_text(
            json.dumps(data, indent=2), encoding="utf-8", newline="\n",
        )

    @classmethod
    def load(cls) -> Session | None:
        """Load session from disk. Returns None if no session exists."""
        if not SESSION_FILE.exists():
            return None
        data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
        session = cls(
            started_at=data.get("started_at", ""),
            wallet_address=data.get("wallet_address", ""),
            completed_lessons=data.get("completed_lessons", []),
            txids=data.get("txids", {}),
        )
        for p in data.get("progress", []):
            session.progress.append(LessonProgress(
                lesson=p["lesson"],
                name=p["name"],
                completed_at=p["completed_at"],
                txid=p.get("txid", ""),
            ))
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
