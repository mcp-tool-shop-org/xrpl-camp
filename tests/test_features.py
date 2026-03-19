"""Tests for new features: timing, auto-resume, status, interactive memo."""

from __future__ import annotations

import re

from typer.testing import CliRunner

from xrpl_camp.certificate import generate_certificate
from xrpl_camp.cli import app
from xrpl_camp.lessons import LESSON_NAMES, _format_duration
from xrpl_camp.models import LessonProgress, Session

runner = CliRunner()


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


# ---------------------------------------------------------------------------
# Lesson timing in models
# ---------------------------------------------------------------------------


def test_lesson_progress_timing_fields():
    lp = LessonProgress(
        lesson=1, name="Mental Model", completed_at="2026-01-01T00:00:00Z",
        started_at="2026-01-01T00:00:00Z", duration_seconds=12.5,
    )
    assert lp.started_at == "2026-01-01T00:00:00Z"
    assert lp.duration_seconds == 12.5


def test_lesson_progress_timing_defaults():
    lp = LessonProgress(lesson=1, name="Mental Model", completed_at="2026-01-01T00:00:00Z")
    assert lp.started_at == ""
    assert lp.duration_seconds == 0.0


def test_mark_complete_with_timing():
    s = Session()
    s.mark_complete(1, "Mental Model", started_at="2026-01-01T00:00:00Z", duration_seconds=5.3)
    assert s.progress[0].started_at == "2026-01-01T00:00:00Z"
    assert s.progress[0].duration_seconds == 5.3


def test_total_duration():
    s = Session()
    s.mark_complete(1, "Mental Model", duration_seconds=3.0)
    s.mark_complete(2, "Create Wallet", duration_seconds=7.0)
    s.mark_complete(3, "Fund Wallet", duration_seconds=10.0)
    assert s.total_duration() == 20.0


def test_total_duration_empty():
    s = Session()
    assert s.total_duration() == 0.0


def test_get_progress():
    s = Session()
    s.mark_complete(1, "Mental Model", duration_seconds=3.0)
    s.mark_complete(2, "Create Wallet", duration_seconds=7.0)

    p = s.get_progress(1)
    assert p is not None
    assert p.name == "Mental Model"

    assert s.get_progress(3) is None


# ---------------------------------------------------------------------------
# Timing persistence (save/load roundtrip)
# ---------------------------------------------------------------------------


def test_timing_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr("xrpl_camp.models.STATE_DIR", tmp_path)
    monkeypatch.setattr("xrpl_camp.models.SESSION_FILE", tmp_path / "session.json")

    s = Session(started_at="2026-01-01T00:00:00Z")
    s.mark_complete(1, "Mental Model", started_at="2026-01-01T00:00:01Z", duration_seconds=5.3)
    s.mark_complete(
        4, "Send Payment", txid="ABC",
        started_at="2026-01-01T00:01:00Z", duration_seconds=30.0,
    )
    s.save()

    loaded = Session.load()
    assert loaded is not None
    assert loaded.progress[0].started_at == "2026-01-01T00:00:01Z"
    assert loaded.progress[0].duration_seconds == 5.3
    assert loaded.progress[1].duration_seconds == 30.0
    assert loaded.total_duration() == 35.3


def test_timing_backward_compat(tmp_path, monkeypatch):
    """Loading old session files without timing fields works fine."""
    import json

    monkeypatch.setattr("xrpl_camp.models.STATE_DIR", tmp_path)
    monkeypatch.setattr("xrpl_camp.models.SESSION_FILE", tmp_path / "session.json")

    # Simulate an old session file without timing fields
    old_data = {
        "started_at": "2026-01-01T00:00:00Z",
        "wallet_address": "rOld",
        "completed_lessons": [1],
        "txids": {},
        "progress": [
            {"lesson": 1, "name": "Mental Model", "completed_at": "2026-01-01T00:00:00Z"},
        ],
    }
    (tmp_path / "session.json").write_text(json.dumps(old_data), encoding="utf-8")

    loaded = Session.load()
    assert loaded is not None
    assert loaded.progress[0].started_at == ""
    assert loaded.progress[0].duration_seconds == 0.0
    assert loaded.total_duration() == 0.0


# ---------------------------------------------------------------------------
# Certificate includes duration
# ---------------------------------------------------------------------------


def test_certificate_includes_duration():
    s = Session(started_at="2026-01-01T00:00:00Z", wallet_address="rCamp")
    s.mark_complete(1, "Mental Model", duration_seconds=5.0)
    s.mark_complete(2, "Create Wallet", duration_seconds=10.0)
    cert = generate_certificate(s)
    assert cert["duration_seconds"] == 15.0


def test_certificate_no_duration_when_zero():
    s = Session(started_at="2026-01-01T00:00:00Z", wallet_address="rCamp")
    s.mark_complete(1, "Mental Model")
    cert = generate_certificate(s)
    assert "duration_seconds" not in cert


# ---------------------------------------------------------------------------
# Format duration
# ---------------------------------------------------------------------------


def test_format_duration_seconds():
    assert _format_duration(45) == "45s"


def test_format_duration_minutes():
    assert _format_duration(120) == "2m"


def test_format_duration_minutes_and_seconds():
    assert _format_duration(125) == "2m 5s"


def test_format_duration_zero():
    assert _format_duration(0) == "0s"


# ---------------------------------------------------------------------------
# Status command
# ---------------------------------------------------------------------------


def test_status_no_session(tmp_path, monkeypatch):
    monkeypatch.setattr("xrpl_camp.cli.STATE_DIR", tmp_path / "nonexistent")
    monkeypatch.setattr("xrpl_camp.models.STATE_DIR", tmp_path / "nonexistent")
    monkeypatch.setattr("xrpl_camp.models.SESSION_FILE", tmp_path / "nonexistent" / "session.json")

    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "no training started" in _strip_ansi(result.output).lower()


def test_status_partial_progress(tmp_path, monkeypatch):
    monkeypatch.setattr("xrpl_camp.models.STATE_DIR", tmp_path)
    monkeypatch.setattr("xrpl_camp.models.SESSION_FILE", tmp_path / "session.json")

    s = Session(started_at="2026-01-01T00:00:00Z")
    s.mark_complete(1, "Mental Model", duration_seconds=5.0)
    s.mark_complete(2, "Create Wallet", duration_seconds=3.0)
    s.save()

    result = runner.invoke(app, ["status"])
    output = _strip_ansi(result.output)
    assert result.exit_code == 0
    assert "Mental Model" in output
    assert "Create Wallet" in output
    assert "next" in output.lower()  # Should show "next" marker for lesson 3
    assert "2/6" in output


def test_status_all_complete(tmp_path, monkeypatch):
    monkeypatch.setattr("xrpl_camp.models.STATE_DIR", tmp_path)
    monkeypatch.setattr("xrpl_camp.models.SESSION_FILE", tmp_path / "session.json")

    s = Session(started_at="2026-01-01T00:00:00Z")
    for i in range(1, 7):
        s.mark_complete(i, LESSON_NAMES[i], duration_seconds=10.0)
    s.save()

    result = runner.invoke(app, ["status"])
    output = _strip_ansi(result.output)
    assert result.exit_code == 0
    assert "6 lessons complete" in output.lower()
    assert "1m" in output  # 60 seconds total = 1m


# ---------------------------------------------------------------------------
# Auto-resume (guided flow skips completed lessons)
# ---------------------------------------------------------------------------


def test_guided_flow_all_complete_exits(tmp_path, monkeypatch):
    """If all 6 lessons are done, guided flow says so and exits."""
    monkeypatch.setattr("xrpl_camp.models.STATE_DIR", tmp_path)
    monkeypatch.setattr("xrpl_camp.models.SESSION_FILE", tmp_path / "session.json")

    s = Session(started_at="2026-01-01T00:00:00Z")
    for i in range(1, 7):
        s.mark_complete(i, LESSON_NAMES[i])
    s.save()

    from xrpl_camp import lessons

    with lessons.console.capture() as capture:
        lessons.run_guided_flow()

    output = capture.get().lower()
    assert "already completed all 6 lessons" in output


# ---------------------------------------------------------------------------
# Interactive memo (lesson_4_send_payment with interactive=True)
# ---------------------------------------------------------------------------


def test_lesson_names_complete():
    """All 6 lessons are named."""
    assert len(LESSON_NAMES) == 6
    for i in range(1, 7):
        assert i in LESSON_NAMES
        assert LESSON_NAMES[i]
