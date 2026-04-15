"""Tests for dry-run mode: execution mode, DryRunSession, wallet gating."""

from __future__ import annotations

import json

import pytest

from xrpl_camp.models import (
    DryRunSession,
    ExecutionMode,
    Session,
    get_execution_mode,
    is_dry_run,
    set_execution_mode,
)


# ---------------------------------------------------------------------------
# Execution mode
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_execution_mode():
    """Reset execution mode to REAL after each test."""
    yield
    set_execution_mode(ExecutionMode.REAL)


def test_execution_mode_default_is_real():
    assert get_execution_mode() == ExecutionMode.REAL
    assert not is_dry_run()


def test_set_execution_mode_dry_run():
    set_execution_mode(ExecutionMode.DRY_RUN)
    assert get_execution_mode() == ExecutionMode.DRY_RUN
    assert is_dry_run()


def test_set_execution_mode_back_to_real():
    set_execution_mode(ExecutionMode.DRY_RUN)
    set_execution_mode(ExecutionMode.REAL)
    assert not is_dry_run()


# ---------------------------------------------------------------------------
# DryRunSession
# ---------------------------------------------------------------------------


def test_dry_run_session_save_is_noop(tmp_path, monkeypatch):
    """DryRunSession.save() never writes to disk."""
    monkeypatch.setattr("xrpl_camp.models.STATE_DIR", tmp_path)
    monkeypatch.setattr("xrpl_camp.models.SESSION_FILE", tmp_path / "session.json")

    session = DryRunSession(started_at="2026-01-01T00:00:00Z")
    session.mark_complete(1, "Mental Model")
    session.save()

    assert not (tmp_path / "session.json").exists()


def test_dry_run_session_get_or_create_ephemeral(tmp_path, monkeypatch):
    """get_or_create returns a fresh session without disk IO."""
    monkeypatch.setattr("xrpl_camp.models.STATE_DIR", tmp_path)
    monkeypatch.setattr("xrpl_camp.models.SESSION_FILE", tmp_path / "session.json")

    session = DryRunSession.get_or_create()

    assert isinstance(session, DryRunSession)
    assert session.started_at  # non-empty
    assert not (tmp_path / "session.json").exists()


def test_dry_run_session_from_existing_loads_state(tmp_path, monkeypatch):
    """from_existing loads real session data into a non-persisting session."""
    monkeypatch.setattr("xrpl_camp.models.STATE_DIR", tmp_path)
    monkeypatch.setattr("xrpl_camp.models.SESSION_FILE", tmp_path / "session.json")

    # Create and persist a real session
    real = Session(started_at="2026-01-01T00:00:00Z", wallet_address="rReal")
    real.mark_complete(1, "Mental Model")
    real.save()

    # Load into DryRunSession
    dry = DryRunSession.from_existing()

    assert isinstance(dry, DryRunSession)
    assert dry.wallet_address == "rReal"
    assert dry.is_complete(1)

    # Mutate and save — should not touch disk
    dry.mark_complete(2, "Create Wallet")
    dry.save()

    # Verify original file unchanged
    data = json.loads((tmp_path / "session.json").read_text(encoding="utf-8"))
    assert 2 not in data["completed_lessons"]


def test_dry_run_session_from_existing_no_file(tmp_path, monkeypatch):
    """from_existing creates fresh session when no session file exists."""
    monkeypatch.setattr("xrpl_camp.models.STATE_DIR", tmp_path)
    monkeypatch.setattr("xrpl_camp.models.SESSION_FILE", tmp_path / "no.json")

    dry = DryRunSession.from_existing()
    assert isinstance(dry, DryRunSession)
    assert dry.started_at


def test_dry_run_session_mark_complete_works_in_memory():
    """Lessons can be marked complete in memory."""
    session = DryRunSession.get_or_create()
    session.mark_complete(1, "Mental Model", duration_seconds=5.0)
    session.mark_complete(2, "Create Wallet", duration_seconds=3.0)

    assert session.is_complete(1)
    assert session.is_complete(2)
    assert session.total_duration() == 8.0


# ---------------------------------------------------------------------------
# Wallet dry-run gating
# ---------------------------------------------------------------------------


@pytest.fixture()
def _dry_run_wallet_env(tmp_path, monkeypatch):
    """Set up dry-run mode for wallet tests."""
    import xrpl_camp.wallet as wallet_mod

    set_execution_mode(ExecutionMode.DRY_RUN)
    monkeypatch.setattr("xrpl_camp.wallet.STATE_DIR", tmp_path)
    monkeypatch.setattr("xrpl_camp.wallet.WALLET_FILE", tmp_path / "wallet.json")
    monkeypatch.setattr("xrpl_camp.models.STATE_DIR", tmp_path)
    monkeypatch.setattr("xrpl_camp.models.WALLET_FILE", tmp_path / "wallet.json")

    # Reset in-memory cache
    wallet_mod._dry_run_wallet = None

    yield tmp_path

    wallet_mod._dry_run_wallet = None


def test_wallet_save_dry_run_caches_in_memory(_dry_run_wallet_env):
    """save_wallet in dry-run mode caches in memory, not on disk."""
    from xrpl_camp.wallet import save_wallet

    tmp_path = _dry_run_wallet_env
    save_wallet("rDryRun", "sEdDryRun")

    # No file on disk
    assert not (tmp_path / "wallet.json").exists()


def test_wallet_load_dry_run_returns_cache(_dry_run_wallet_env):
    """load_wallet in dry-run returns the in-memory cached wallet."""
    from xrpl_camp.wallet import load_wallet, save_wallet

    save_wallet("rDryRun", "sEdDryRun")
    w = load_wallet()

    assert w is not None
    assert w["address"] == "rDryRun"
    assert w["seed"] == "sEdDryRun"


def test_wallet_exists_dry_run(_dry_run_wallet_env):
    """wallet_exists returns True after in-memory save in dry-run."""
    from xrpl_camp.wallet import save_wallet, wallet_exists

    assert not wallet_exists()  # No cache yet
    save_wallet("rDryRun", "sEdDryRun")
    assert wallet_exists()


def test_wallet_no_disk_write_in_dry_run(_dry_run_wallet_env):
    """Full wallet lifecycle in dry-run writes nothing to disk."""
    from xrpl_camp.wallet import load_wallet, save_wallet, wallet_exists

    tmp_path = _dry_run_wallet_env

    save_wallet("rAddr", "sSeed")
    assert wallet_exists()
    w = load_wallet()
    assert w is not None

    # Absolutely no files created
    assert list(tmp_path.iterdir()) == []
