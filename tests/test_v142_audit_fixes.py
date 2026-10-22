"""1.4.2: the eight bugs from the v1.4.1 deep audit, each pinned by a test.

Every test here failed on v1.4.1.
"""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from tests.helpers import strip_ansi
from xrpl_camp import cli, lessons, models, proof_pack, transport, wallet
from xrpl_camp.cli import app
from xrpl_camp.models import ExecutionMode, Session, get_execution_mode

runner = CliRunner()


def _pack(tmp_path, name="xrpl_camp_proof_pack.json", address="rCamp"):
    s = Session(started_at="2026-01-01T00:00:00Z", wallet_address=address)
    s.mark_complete(1, "Mental Model")
    pack = proof_pack.generate_proof_pack(s)
    path = tmp_path / name
    proof_pack.save_proof_pack(pack, str(path))
    return path


def _summary(status):
    return [], {"status": status, "message": status}


# ── Bug 1: proof verify <folder> --online ─────────────────────────────


@pytest.fixture
def folder(tmp_path):
    d = tmp_path / "packs"
    d.mkdir()
    _pack(d, "a_xrpl_camp_proof_pack.json", "rAlice")
    _pack(d, "b_xrpl_camp_proof_pack.json", "rBob")
    return d


def test_a_folder_with_online_asks_the_ledger(folder, monkeypatch):
    seen = []

    def fake(pack, endpoint):
        seen.append((pack["address"], endpoint))
        return _summary("confirmed")

    monkeypatch.setattr(cli, "_online_check", fake)
    result = runner.invoke(app, ["proof", "verify", str(folder), "--online"])
    assert result.exit_code == 0, result.output
    assert sorted(a for a, _ in seen) == ["rAlice", "rBob"]
    assert all(e == proof_pack.resolve_verification_endpoint("") for _, e in seen)
    assert "VERIFIED" in strip_ansi(result.output)


@pytest.mark.parametrize(("status", "code", "word"), [
    ("contradicted", 1, "FAILED"),
    ("unknown", 3, "UNVERIFIABLE"),
    ("ledger_history_gone", 3, "UNVERIFIABLE"),
])
def test_a_folder_exit_code_follows_the_ledger(folder, monkeypatch, status, code, word):
    """The forged-and-rehashed pack: its hash passes, the ledger refutes it."""
    answers = iter([_summary("confirmed"), _summary(status)])
    monkeypatch.setattr(cli, "_online_check", lambda pack, endpoint: next(answers))
    result = runner.invoke(app, ["proof", "verify", str(folder), "--online"])
    assert result.exit_code == code
    out = strip_ansi(result.output)
    assert word in out and "need a look" in out


def test_a_folder_json_carries_each_ledger_verdict(folder, monkeypatch):
    monkeypatch.setattr(cli, "_online_check", lambda pack, endpoint: _summary("confirmed"))
    result = runner.invoke(app, ["proof", "verify", str(folder), "--online", "--json"])
    data = json.loads(result.output)
    assert [p["online"]["status"] for p in data["packs"]] == ["confirmed", "confirmed"]
    assert data["summary"]["passed"] == 2


def test_a_tampered_pack_is_never_sent_to_the_ledger(folder, monkeypatch):
    bad = folder / "a_xrpl_camp_proof_pack.json"
    pack = json.loads(bad.read_text("utf-8"))
    pack["address"] = "rForged"
    bad.write_text(json.dumps(pack), encoding="utf-8")
    seen = []
    monkeypatch.setattr(
        cli, "_online_check",
        lambda pack, endpoint: seen.append(pack["address"]) or _summary("confirmed"),
    )
    result = runner.invoke(app, ["proof", "verify", str(folder), "--online"])
    assert result.exit_code == 1
    assert seen == ["rBob"]


def test_a_folder_without_online_stays_offline(folder, monkeypatch):
    monkeypatch.setattr(cli, "_online_check", lambda *a: pytest.fail("went online"))
    assert runner.invoke(app, ["proof", "verify", str(folder)]).exit_code == 0


@pytest.mark.parametrize("target", ["folder", "file"])
def test_online_is_skipped_under_dry_run(folder, monkeypatch, target):
    monkeypatch.setattr(cli, "_online_check", lambda *a: pytest.fail("went online"))
    path = folder if target == "folder" else folder / "a_xrpl_camp_proof_pack.json"
    result = runner.invoke(app, ["--dry-run", "proof", "verify", str(path), "--online"])
    assert result.exit_code == 0
    assert "--online was skipped" in strip_ansi(result.output)
    as_json = runner.invoke(
        app, ["--dry-run", "proof", "verify", str(path), "--online", "--json"],
    )
    assert "skipped" in as_json.output


# ── Bug 2: reset with no answer ───────────────────────────────────────


def test_reset_with_closed_stdin_cancels(tmp_path):
    (tmp_path / ".xrpl-camp").mkdir()
    (tmp_path / ".xrpl-camp" / "session.json").write_text("{}", encoding="utf-8")
    result = runner.invoke(app, ["reset"], input=None)
    assert result.exit_code == 0
    assert result.exception is None
    assert "Cancelled" in strip_ansi(result.output)
    assert (tmp_path / ".xrpl-camp" / "session.json").exists()


# ── Bugs 3 and 4: the explorer link and the network label ─────────────


@pytest.mark.parametrize(("url", "label"), [
    ("https://s.altnet.rippletest.net:51234", "testnet"),
    ("https://clio.altnet.rippletest.net:51234/", "testnet"),
    ("https://s.devnet.rippletest.net:51234/", "devnet"),
])
def test_the_attested_network_uses_the_host_rules(monkeypatch, url, label):
    from xrpl_camp.certificate import _attested_network

    monkeypatch.setenv("XRPL_CAMP_RPC_URL", url)
    assert _attested_network()[0] == label


def _pack_with_txid(monkeypatch, url):
    if url:
        monkeypatch.setenv("XRPL_CAMP_RPC_URL", url)
    s = Session(started_at="2026-01-01T00:00:00Z", wallet_address="rCamp")
    s.mark_complete(4, "Send", txid="A" * 64)
    return proof_pack.generate_proof_pack(s)["lessons"][0]


def test_a_pack_links_to_the_endpoints_explorer(monkeypatch):
    devnet = _pack_with_txid(monkeypatch, "https://s.devnet.rippletest.net:51234/")
    assert "devnet" in devnet["explorer_url"]


def test_a_custom_endpoint_gets_no_dead_testnet_link(monkeypatch):
    entry = _pack_with_txid(monkeypatch, "http://localhost:5005/")
    assert "explorer_url" not in entry and entry["txid"] == "A" * 64


def test_explorer_url_for_network():
    assert transport.explorer_url_for_network("A" * 64, "testnet").endswith("A" * 64)
    assert transport.explorer_url_for_network("A" * 64, "custom:x") == ""
    assert transport.explorer_url_for_network("", "testnet") == ""


def test_the_certificate_text_follows_its_network():
    from xrpl_camp.certificate import render_certificate_text, share_text

    cert = {
        "address": "rCamp", "network": "devnet",
        "completed": [{"lesson": 4, "name": "Send", "txid": "B" * 64}],
    }
    assert "devnet" in render_certificate_text(cert)
    custom = dict(cert, network="custom:x")
    assert "testnet.xrpl.org" not in render_certificate_text(custom)
    assert "testnet.xrpl.org" not in share_text(custom)


# ── Bug 5: a newer pack schema ────────────────────────────────────────


def test_a_newer_schema_is_hash_checked_not_turned_away(tmp_path):
    import hashlib

    path = _pack(tmp_path)
    pack = json.loads(path.read_text("utf-8"))
    pack["schema"] = "xrpl-camp-proof-pack-v2"
    digest = hashlib.sha256(
        proof_pack.canonical_json(proof_pack._sealed_content(pack)).encode("utf-8"),
    ).hexdigest()
    pack["sha256"] = f"sha256:{digest}"
    path.write_text(json.dumps(pack), encoding="utf-8")
    result = runner.invoke(app, ["proof", "verify", str(path)])
    assert result.exit_code == 0, result.output
    assert "does not recognize" in strip_ansi(result.output).replace("\n", " ")
    other = tmp_path / "other.json"
    other.write_text(json.dumps(dict(pack, schema="something-else")), encoding="utf-8")
    assert runner.invoke(app, ["proof", "verify", str(other)]).exit_code != 0


# ── Bug 6: session state ──────────────────────────────────────────────


def test_a_repeat_send_does_not_inherit_created_account():
    s = Session(started_at="2026-01-01T00:00:00Z", wallet_address="rCamp")
    s.mark_complete(4, "Send", txid="A" * 64, created_account=True)
    s.mark_complete(4, "Send", txid="B" * 64, created_account=False)
    assert s.get_progress(4).created_account is False
    s.mark_complete(4, "Send")  # a txid-less re-run keeps what is on record
    assert s.get_progress(4).created_account is False


def test_a_merge_keeps_another_processs_wallet_address():
    Session(started_at="2026-01-01T00:00:00Z", wallet_address="rFromDisk").save()
    mine = Session(started_at="2026-01-01T00:00:00Z", wallet_address="")
    mine.save()
    assert Session.load().wallet_address == "rFromDisk"


def test_the_lock_file_goes_even_if_the_stamp_write_raises(tmp_path, monkeypatch):
    target = tmp_path / ".xrpl-camp"

    def boom(*a, **k):
        raise RuntimeError("interrupted while stamping")

    monkeypatch.setattr(models, "_write_lock_stamp", boom)
    with pytest.raises(RuntimeError), models.state_lock(target):
        pass
    assert not models._lock_file(target).exists()


def test_a_wallet_save_holds_the_state_lock(monkeypatch):
    held = []
    real = wallet._save_record

    def spy(path, data):
        held.append(models._lock_file(path.parent).exists())
        return real(path, data)

    monkeypatch.setattr(wallet, "_save_record", spy)
    wallet.save_wallet("rCamp", "sEdTM1uX8pu2do5XvTnutH6HsouMaM2")
    wallet.save_mailbox("rMail", "sEd7T2TvAQ6iTni8BPvkJYit21gvcqm")
    assert held == [True, True]


# ── Bug 7: a CampFailure from the state files ─────────────────────────


def test_a_corrupt_session_is_a_clean_exit_and_logged(tmp_path):
    state = tmp_path / ".xrpl-camp"
    state.mkdir()
    (state / "session.json").write_text("{not json", encoding="utf-8")
    result = runner.invoke(app, ["status"])
    assert result.exit_code != 0
    assert not isinstance(result.exception, models.StateFileError)
    assert (state / "errors.log").exists()


def test_run_logs_a_campfailure(tmp_path, monkeypatch):
    (tmp_path / ".xrpl-camp").mkdir()
    from xrpl_camp.errors import state_corrupt_error

    err = models.StateFileError(state_corrupt_error("boom"))

    def raise_it():
        raise err

    monkeypatch.setattr(cli, "app", raise_it)
    with pytest.raises(SystemExit):
        cli.run()
    assert "STATE_CORRUPT" in (tmp_path / ".xrpl-camp" / "errors.log").read_text("utf-8")


# ── Bug 8: dry_run=True from Python ───────────────────────────────────


def test_lesson_2_with_dry_run_writes_no_wallet(tmp_path):
    s = Session(started_at="2026-01-01T00:00:00Z")
    lessons.lesson_2_create_wallet(s, dry_run=True)
    assert not (tmp_path / ".xrpl-camp" / "wallet.json").exists()
    assert get_execution_mode() == ExecutionMode.REAL
    assert wallet._dry_run_wallet is None


def test_dry_run_inside_dry_run_leaves_the_mode_alone(dry_run_mode):
    s = Session(started_at="2026-01-01T00:00:00Z")
    lessons.lesson_2_create_wallet(s, dry_run=True)
    assert get_execution_mode() == ExecutionMode.DRY_RUN


# ── Coverage for the paths the fixes moved or added ───────────────────


def _txid_pack(tmp_path):
    s = Session(started_at="2026-01-01T00:00:00Z", wallet_address="rCamp")
    s.mark_complete(4, "Send", txid="A" * 64, ledger_index=100)
    pack = proof_pack.generate_proof_pack(s)
    path = tmp_path / "xrpl_camp_proof_pack.json"
    proof_pack.save_proof_pack(pack, str(path))
    return pack, path


def test_online_check_looks_up_each_checkable_lesson(tmp_path, monkeypatch):
    pack, _ = _txid_pack(tmp_path)
    asked = []

    def lookup(txid, url=None, recorded_ledger_index=None, **k):
        asked.append((txid, url, recorded_ledger_index))
        return {"found": False, "reason": "not found"}

    monkeypatch.setattr(transport, "lookup_tx", lookup)
    results, summary = cli._online_check(pack, "https://example.invalid:51234/")
    assert asked == [("A" * 64, "https://example.invalid:51234/", 100)]
    assert len(results) == len(pack["lessons"]) and "status" in summary


def test_a_single_file_online_check_uses_the_shared_lookup(tmp_path, monkeypatch):
    _, path = _txid_pack(tmp_path)
    monkeypatch.setattr(cli, "_online_check", lambda pack, endpoint: _summary("confirmed"))
    result = runner.invoke(app, ["proof", "verify", str(path), "--online"])
    assert result.exit_code == 0 and "Ledger check" in strip_ansi(result.output)


def test_a_folder_reports_files_that_are_not_packs(tmp_path):
    d = tmp_path / "mixed"
    d.mkdir()
    (d / "a.json").write_text("{broken", encoding="utf-8")
    (d / "b.json").write_text("[1, 2]", encoding="utf-8")
    (d / "c.json").write_text(json.dumps({"schema": "other"}), encoding="utf-8")
    result = runner.invoke(app, ["proof", "verify", str(d)])
    out = strip_ansi(result.output)
    assert result.exit_code == 1
    assert "unreadable" in out and "not a JSON object" in out
    assert "not an xrpl-camp proof pack" in out


def test_a_corrupt_wallet_is_a_clean_exit(tmp_path):
    state = tmp_path / ".xrpl-camp"
    state.mkdir()
    (state / "wallet.json").write_text("{not json", encoding="utf-8")
    result = runner.invoke(app, ["wallet", "show"])
    assert result.exit_code != 0
    assert not isinstance(result.exception, models.StateFileError)


def test_send_with_a_corrupt_session_is_a_clean_exit(tmp_path):
    state = tmp_path / ".xrpl-camp"
    state.mkdir()
    (state / "session.json").write_text("{not json", encoding="utf-8")
    result = runner.invoke(app, ["send", "--memo", "hi"])
    assert result.exit_code != 0
    assert not isinstance(result.exception, models.StateFileError)


def test_a_direct_keyboard_interrupt_shows_the_panel(monkeypatch, capsys):
    def interrupt():
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "app", interrupt)
    with pytest.raises(SystemExit) as exc:
        cli.run()
    assert exc.value.code == 130 and "Paused" in strip_ansi(capsys.readouterr().out)


def test_a_wallet_write_failure_names_the_real_path(monkeypatch, capsys):
    def no_disk(*a, **k):
        raise OSError("read-only")

    monkeypatch.setattr(wallet, "save_wallet", no_disk)
    result = lessons.lesson_2_create_wallet(Session(started_at="2026-01-01T00:00:00Z"))
    assert not result.ok
    assert "wallet.json" in strip_ansi(capsys.readouterr().out)


@pytest.mark.parametrize(("url", "shows_link"), [
    ("", True), ("http://localhost:5005/", False),
])
def test_read_by_hash_links_only_to_a_known_explorer(monkeypatch, capsys, url, shows_link):
    if url:
        monkeypatch.setenv("XRPL_CAMP_RPC_URL", url)
    monkeypatch.setattr(lessons, "check_endpoint", lambda: None, raising=False)
    monkeypatch.setattr(transport, "lookup_tx", lambda *a, **k: {
        "found": True, "hash": "A" * 64, "validated": True, "result": "tesSUCCESS",
        "account": "rCamp", "destination": "rMail", "amount_drops": 1, "fee_drops": 10,
        "ledger_index": 5, "memos": [], "tx_type": "Payment",
    })
    lessons.read_transaction("A" * 64)
    out = strip_ansi(capsys.readouterr().out)
    assert ("where anyone can check it" in out) is shows_link
