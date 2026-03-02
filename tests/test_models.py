"""Tests for XRPL Camp session models."""

from __future__ import annotations

import json

from xrpl_camp.models import LessonProgress, Session

# ---------------------------------------------------------------------------
# Session basics
# ---------------------------------------------------------------------------


def test_session_defaults():
    s = Session()
    assert s.started_at == ""
    assert s.wallet_address == ""
    assert s.completed_lessons == []
    assert s.txids == {}
    assert s.progress == []


def test_mark_complete_adds_lesson():
    s = Session()
    s.mark_complete(1, "Mental Model")
    assert 1 in s.completed_lessons
    assert len(s.progress) == 1
    assert s.progress[0].lesson == 1
    assert s.progress[0].name == "Mental Model"
    assert s.progress[0].completed_at  # non-empty timestamp


def test_mark_complete_with_txid():
    s = Session()
    s.mark_complete(4, "Send Payment", txid="ABC123")
    assert s.txids["lesson_4"] == "ABC123"
    assert s.progress[0].txid == "ABC123"


def test_mark_complete_is_idempotent():
    s = Session()
    s.mark_complete(1, "Mental Model")
    s.mark_complete(1, "Mental Model")
    assert s.completed_lessons.count(1) == 1
    assert len(s.progress) == 1


def test_is_complete():
    s = Session()
    assert not s.is_complete(1)
    s.mark_complete(1, "Mental Model")
    assert s.is_complete(1)
    assert not s.is_complete(2)


def test_multiple_lessons():
    s = Session()
    s.mark_complete(1, "Mental Model")
    s.mark_complete(2, "Create Wallet")
    s.mark_complete(3, "Fund Wallet")
    assert s.completed_lessons == [1, 2, 3]
    assert len(s.progress) == 3


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def test_save_and_load(tmp_path, monkeypatch):
    monkeypatch.setattr("xrpl_camp.models.STATE_DIR", tmp_path)
    monkeypatch.setattr("xrpl_camp.models.SESSION_FILE", tmp_path / "session.json")

    s = Session(started_at="2026-01-01T00:00:00Z", wallet_address="rTestAddr")
    s.mark_complete(1, "Mental Model")
    s.mark_complete(4, "Send Payment", txid="DEADBEEF")
    s.save()

    loaded = Session.load()
    assert loaded is not None
    assert loaded.started_at == "2026-01-01T00:00:00Z"
    assert loaded.wallet_address == "rTestAddr"
    assert loaded.completed_lessons == [1, 4]
    assert loaded.txids["lesson_4"] == "DEADBEEF"
    assert len(loaded.progress) == 2


def test_load_returns_none_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("xrpl_camp.models.SESSION_FILE", tmp_path / "nope.json")
    assert Session.load() is None


def test_get_or_create_new(tmp_path, monkeypatch):
    monkeypatch.setattr("xrpl_camp.models.STATE_DIR", tmp_path)
    monkeypatch.setattr("xrpl_camp.models.SESSION_FILE", tmp_path / "session.json")

    s = Session.get_or_create()
    assert s.started_at  # non-empty
    assert (tmp_path / "session.json").exists()


def test_get_or_create_existing(tmp_path, monkeypatch):
    monkeypatch.setattr("xrpl_camp.models.STATE_DIR", tmp_path)
    monkeypatch.setattr("xrpl_camp.models.SESSION_FILE", tmp_path / "session.json")

    s1 = Session.get_or_create()
    s1.wallet_address = "rKeep"
    s1.save()

    s2 = Session.get_or_create()
    assert s2.wallet_address == "rKeep"


def test_session_json_schema(tmp_path, monkeypatch):
    """Session JSON has expected top-level keys."""
    monkeypatch.setattr("xrpl_camp.models.STATE_DIR", tmp_path)
    monkeypatch.setattr("xrpl_camp.models.SESSION_FILE", tmp_path / "session.json")

    s = Session(started_at="2026-01-01T00:00:00Z")
    s.mark_complete(1, "Mental Model")
    s.save()

    data = json.loads((tmp_path / "session.json").read_text(encoding="utf-8"))
    assert set(data.keys()) == {
        "started_at", "wallet_address", "completed_lessons", "txids", "progress",
    }


# ---------------------------------------------------------------------------
# LessonProgress
# ---------------------------------------------------------------------------


def test_lesson_progress_defaults():
    lp = LessonProgress(lesson=1, name="Mental Model", completed_at="2026-01-01T00:00:00Z")
    assert lp.txid == ""
