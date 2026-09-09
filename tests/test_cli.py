"""Tests for XRPL Camp CLI commands (reset, proof verify).

Behavioural coverage for every command — including the four that had none at
all — lives in `test_cli_behaviour.py`. This module keeps `reset` and
`proof verify`, which were already exercised by invocation rather than by help
text.

`_strip_ansi` used to be copy-pasted verbatim into this file and
`test_features.py`, and both copies stripped only SGR sequences, so an OSC-8
hyperlink from a future Rich release would have corrupted every substring
assertion in both at once. The shared implementation in `tests/helpers.py`
covers the full CSI/OSC grammar.
"""

from __future__ import annotations

from typer.testing import CliRunner

from tests.helpers import strip_ansi as _strip_ansi
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
    assert "nothing to reset" in _strip_ansi(result.output).lower()


def test_reset_cancelled(tmp_path, monkeypatch):
    """Reset cancelled when user doesn't type RESET."""
    state = tmp_path / ".xrpl-camp"
    state.mkdir()
    (state / "session.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr("xrpl_camp.cli.STATE_DIR", state)

    result = runner.invoke(app, ["reset"], input="no\n")
    assert result.exit_code == 0
    assert "cancelled" in _strip_ansi(result.output).lower()
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
    assert "clean slate" in _strip_ansi(result.output).lower()
    assert not state.exists()  # Deleted


def test_reset_shows_files_before_asking(tmp_path, monkeypatch):
    """Reset lists files before asking for confirmation."""
    state = tmp_path / ".xrpl-camp"
    state.mkdir()
    (state / "session.json").write_text("{}", encoding="utf-8")
    (state / "wallet.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr("xrpl_camp.cli.STATE_DIR", state)

    result = runner.invoke(app, ["reset"], input="no\n")
    output = _strip_ansi(result.output)
    assert "session.json" in output
    assert "wallet.json" in output


# ---------------------------------------------------------------------------
# Dry-run
#
# The four tests that were here invoked `<command> --help` and asserted the
# literal string "--dry-run" appeared in the output. No command was ever
# invoked WITH the flag, so they proved typer had declared an option and
# nothing about what it does — while the advertised contract ("no network
# calls, no disk writes") went unverified end to end.
#
# Replaced by `test_cli_behaviour.py::test_dry_run_commands_write_nothing_to_disk`,
# which invokes each command WITH the flag in an isolated cwd and asserts the
# directory is still empty afterwards, with the conftest socket guard covering
# the network half. One help-text assertion is kept there to guard the wording.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Proof verify command
# ---------------------------------------------------------------------------


def test_proof_verify_valid(tmp_path):
    """Verify a valid proof pack passes."""
    from xrpl_camp.models import Session
    from xrpl_camp.proof_pack import generate_proof_pack, save_proof_pack

    s = Session(started_at="2026-01-01T00:00:00Z", wallet_address="rTestAddr")
    s.mark_complete(1, "Mental Model")
    pack = generate_proof_pack(s)
    pack_file = tmp_path / "proof.json"
    save_proof_pack(pack, str(pack_file))

    result = runner.invoke(app, ["proof", "verify", str(pack_file)])
    assert result.exit_code == 0
    output = _strip_ansi(result.output)
    assert "PASS" in output


def test_proof_verify_tampered(tmp_path):
    """Reject a tampered proof pack."""
    import json

    from xrpl_camp.models import Session
    from xrpl_camp.proof_pack import generate_proof_pack

    s = Session(started_at="2026-01-01T00:00:00Z", wallet_address="rTestAddr")
    s.mark_complete(1, "Mental Model")
    pack = generate_proof_pack(s)
    pack["address"] = "rTampered"

    pack_file = tmp_path / "proof.json"
    pack_file.write_text(json.dumps(pack, indent=2), encoding="utf-8")

    result = runner.invoke(app, ["proof", "verify", str(pack_file)])
    assert result.exit_code == 1
    output = _strip_ansi(result.output)
    assert "FAIL" in output


def test_proof_verify_missing_file():
    """Reject missing file."""
    result = runner.invoke(app, ["proof", "verify", "nonexistent.json"])
    assert result.exit_code == 1
    output = _strip_ansi(result.output)
    assert "not found" in output.lower()


def test_proof_verify_json_output(tmp_path):
    """--json flag produces machine-readable output."""
    import json

    from xrpl_camp.models import Session
    from xrpl_camp.proof_pack import generate_proof_pack, save_proof_pack

    s = Session(started_at="2026-01-01T00:00:00Z", wallet_address="rTestAddr")
    s.mark_complete(1, "Mental Model")
    pack = generate_proof_pack(s)
    pack_file = tmp_path / "proof.json"
    save_proof_pack(pack, str(pack_file))

    result = runner.invoke(app, ["proof", "verify", str(pack_file), "--json"])
    assert result.exit_code == 0
    data = json.loads(_strip_ansi(result.output))
    assert data["valid"] is True
    assert data["lessons_completed"] == 1
    assert data["address"] == "rTestAddr"


def test_proof_verify_invalid_json(tmp_path):
    """Reject malformed JSON."""
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("not json{{{", encoding="utf-8")

    result = runner.invoke(app, ["proof", "verify", str(bad_file)])
    assert result.exit_code == 1
    output = _strip_ansi(result.output)
    assert "invalid json" in output.lower()


# ---------------------------------------------------------------------------
# Proof help
# ---------------------------------------------------------------------------


def test_proof_help():
    """proof subcommand shows help."""
    result = runner.invoke(app, ["proof", "--help"])
    assert result.exit_code == 0
    output = _strip_ansi(result.output)
    assert "verify" in output.lower()
