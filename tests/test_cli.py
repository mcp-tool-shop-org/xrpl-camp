"""Tests for XRPL Camp CLI commands (reset, dry-run flags)."""

from __future__ import annotations

from typer.testing import CliRunner

from xrpl_camp.cli import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Reset command
# ---------------------------------------------------------------------------


def test_reset_no_state_dir(tmp_path, monkeypatch):
    """Reset with no .xrpl-camp/ exits cleanly."""
    monkeypatch.setattr("xrpl_camp.cli.STATE_DIR", tmp_path / "nonexistent")
    result = runner.invoke(app, ["reset"])
    assert result.exit_code == 0
    assert "nothing to reset" in result.output.lower()


def test_reset_cancelled(tmp_path, monkeypatch):
    """Reset cancelled when user doesn't type RESET."""
    state = tmp_path / ".xrpl-camp"
    state.mkdir()
    (state / "session.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr("xrpl_camp.cli.STATE_DIR", state)

    result = runner.invoke(app, ["reset"], input="no\n")
    assert result.exit_code == 0
    assert "cancelled" in result.output.lower()
    assert state.exists()  # Not deleted


def test_reset_confirmed(tmp_path, monkeypatch):
    """Reset deletes .xrpl-camp/ when user types RESET."""
    state = tmp_path / ".xrpl-camp"
    state.mkdir()
    (state / "session.json").write_text("{}", encoding="utf-8")
    (state / "wallet.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr("xrpl_camp.cli.STATE_DIR", state)

    result = runner.invoke(app, ["reset"], input="RESET\n")
    assert result.exit_code == 0
    assert "reset complete" in result.output.lower()
    assert not state.exists()  # Deleted


def test_reset_shows_files_before_asking(tmp_path, monkeypatch):
    """Reset lists files before asking for confirmation."""
    state = tmp_path / ".xrpl-camp"
    state.mkdir()
    (state / "session.json").write_text("{}", encoding="utf-8")
    (state / "wallet.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr("xrpl_camp.cli.STATE_DIR", state)

    result = runner.invoke(app, ["reset"], input="no\n")
    assert "session.json" in result.output
    assert "wallet.json" in result.output


# ---------------------------------------------------------------------------
# Dry-run flag acceptance
# ---------------------------------------------------------------------------


def test_start_dry_run_flag_accepted(tmp_path, monkeypatch):
    """--dry-run flag is accepted by start command."""
    # We can't run the full guided flow (needs stdin for _pause()),
    # but we can verify the flag is parsed without error by checking --help
    result = runner.invoke(app, ["start", "--help"])
    assert "--dry-run" in result.output


def test_fund_dry_run_flag_accepted():
    """--dry-run flag is accepted by fund command."""
    result = runner.invoke(app, ["fund", "--help"])
    assert "--dry-run" in result.output


def test_send_dry_run_flag_accepted():
    """--dry-run flag is accepted by send command."""
    result = runner.invoke(app, ["send", "--help"])
    assert "--dry-run" in result.output


def test_verify_dry_run_flag_accepted():
    """--dry-run flag is accepted by verify command."""
    result = runner.invoke(app, ["verify", "--help"])
    assert "--dry-run" in result.output
