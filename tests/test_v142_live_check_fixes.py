"""1.4.2: defects from Book Keeper's live check of v1.4.1 on testnet.

D5 was a real double-send: a Ctrl-C half a second after the submit lost a
payment that then validated (18B8294A…), and the next `start` wrote the same
memo to the ledger again (7AA45A5D…).
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.helpers import load_fixture, make_response, strip_ansi, stub_client
from xrpl_camp import cli, lessons, models, transport
from xrpl_camp.cli import app
from xrpl_camp.models import Session

runner = CliRunner()
MAILBOX = "rUUGAx14J9EwWbWLjQgVFfXA2zV5hfKqDP"
TXID = "1E721764B35CAFD9AB24CFA15D8DC5097E9B9CDFE967B3E2A99FC701A3E53E1D"


# ── D5: a payment in flight when the run stopped ──────────────────────


def _stub_signed_send(monkeypatch, result):
    """Pre-signing works (offline), submit returns `result`."""
    import xrpl.transaction
    from xrpl.models import Payment

    stub_client(monkeypatch, make_response({"state": {}}, successful=False))

    def fake_autofill(payment, client, wallet, **k):
        filled = Payment.from_dict({
            **payment.to_dict(), "fee": "10", "sequence": 5, "last_ledger_sequence": 900,
        })
        return xrpl.transaction.sign(filled, wallet)

    order = []
    monkeypatch.setattr(xrpl.transaction, "autofill_and_sign", fake_autofill)
    monkeypatch.setattr(
        xrpl.transaction, "submit_and_wait",
        lambda tx, client, wallet, **k: order.append("submit") or make_response(result),
    )
    return order


def test_on_signed_runs_before_the_submit(monkeypatch):
    from xrpl.wallet import Wallet

    order = _stub_signed_send(monkeypatch, load_fixture("submit_created_account_v2.json"))
    seen = []
    transport.send_memo_payment(
        Wallet.create().seed, "note", MAILBOX, amount_drops=1,
        on_signed=lambda txid, last: (seen.append((txid, last)), order.append("signed")),
    )
    assert order == ["signed", "submit"]
    assert len(seen[0][0]) == 64 and seen[0][1] == 900


def test_a_failing_on_signed_submits_nothing(monkeypatch):
    from xrpl.wallet import Wallet

    order = _stub_signed_send(monkeypatch, load_fixture("submit_created_account_v2.json"))

    def refuse(txid, last):
        raise OSError("disk full")

    with pytest.raises(OSError):
        transport.send_memo_payment(
            Wallet.create().seed, "note", MAILBOX, amount_drops=1, on_signed=refuse,
        )
    assert order == []


def _sent(txid=TXID):
    return transport.SendResult(
        txid=txid, destination=MAILBOX, amount_drops=1, fee_drops=10,
        created_account=False, ledger_index=21727568,
    )


def test_resolve_in_flight_returns_a_landed_payment(monkeypatch):
    monkeypatch.setattr(transport, "_resolve_after_lapse", lambda *a, **k: _sent())
    assert transport.resolve_in_flight(TXID, 900, MAILBOX, 1).txid == TXID


def _unresolved(detail="hash=x last_ledger=900"):
    def raise_it(*a, **k):
        raise transport.XRPLSubmissionUnresolved(
            "not on the ledger", txid=TXID, last_ledger=900, detail=detail,
        )
    return raise_it


def test_resolve_in_flight_is_none_once_the_window_has_passed(monkeypatch):
    monkeypatch.setattr(transport, "_resolve_after_lapse", _unresolved())
    monkeypatch.setattr(transport, "_server_state", lambda url: {"validated_ledger": {"seq": 901}})
    assert transport.resolve_in_flight(TXID, 900, MAILBOX, 1) is None


@pytest.mark.parametrize(("seq", "detail"), [
    (899, "hash=x"),                 # the window is still open
    (901, "hash=x lookup=timeout"),  # the lookup itself failed
    (0, "hash=x"),                   # the ledger couldn't be read
])
def test_resolve_in_flight_refuses_while_it_could_land(monkeypatch, seq, detail):
    monkeypatch.setattr(transport, "_resolve_after_lapse", _unresolved(detail))
    monkeypatch.setattr(
        transport, "_server_state",
        lambda url: {"validated_ledger": {"seq": seq}} if seq else None,
    )
    with pytest.raises(transport.XRPLSubmissionUnresolved, match="may still land"):
        transport.resolve_in_flight(TXID, 900, MAILBOX, 1)


@pytest.fixture
def camp(monkeypatch):
    """A funded learner with a mailbox, and a send that must not happen."""
    from xrpl_camp import wallet

    wallet.save_wallet("rCampLearner", "sEdTM1uX8pu2do5XvTnutH6HsouMaM2")
    wallet.save_mailbox(MAILBOX, "sEd7T2TvAQ6iTni8BPvkJYit21gvcqm")
    monkeypatch.setattr(lessons, "check_endpoint", lambda: None)
    monkeypatch.setattr(
        transport, "send_memo_payment",
        lambda *a, **k: pytest.fail("sent a second payment"),
    )
    s = Session(started_at="2026-01-01T00:00:00Z", wallet_address="rCampLearner")
    s.extra[lessons.IN_FLIGHT_KEY] = {
        "txid": TXID, "last_ledger": 900, "memo": "resume check after submit",
        "destination": MAILBOX, "amount_drops": 1,
    }
    s.save()
    return Session.load()


def test_a_payment_that_landed_is_recorded_not_resent(camp, monkeypatch):
    monkeypatch.setattr(transport, "resolve_in_flight", lambda *a, **k: _sent())
    result = lessons.lesson_4_send_payment(camp, "a new memo")
    assert result.ok and result.txid == TXID
    saved = Session.load()
    assert saved.txids["lesson_4"] == TXID
    assert saved.get_progress(4).memo == "resume check after submit"
    assert not saved.extra.get(lessons.IN_FLIGHT_KEY)


def test_a_payment_that_may_still_land_blocks_a_new_send(camp, monkeypatch):
    monkeypatch.setattr(
        transport, "resolve_in_flight", _unresolved("hash=x"),
    )
    result = lessons.lesson_4_send_payment(camp, "a new memo")
    assert not result.ok
    assert Session.load().extra[lessons.IN_FLIGHT_KEY]["txid"] == TXID


def test_a_payment_that_can_never_land_clears_and_sends(camp, monkeypatch):
    monkeypatch.setattr(transport, "resolve_in_flight", lambda *a, **k: None)
    monkeypatch.setattr(transport, "get_balance", lambda *a, **k: 50_000_000)
    sent = []

    def send(*a, on_signed=None, **k):
        on_signed("C" * 64, 950)
        assert Session.load().extra[lessons.IN_FLIGHT_KEY]["txid"] == "C" * 64
        sent.append(a[1])
        return _sent("C" * 64)

    monkeypatch.setattr(transport, "send_memo_payment", send)
    result = lessons.lesson_4_send_payment(camp, "a new memo")
    assert result.ok and sent == ["a new memo"]
    assert not Session.load().extra.get(lessons.IN_FLIGHT_KEY)


def test_a_payment_that_failed_on_the_ledger_clears_and_sends(camp, monkeypatch):
    def failed(*a, **k):
        raise transport.XRPLTransactionFailed("tecPATH_DRY")

    monkeypatch.setattr(transport, "resolve_in_flight", failed)
    monkeypatch.setattr(transport, "get_balance", lambda *a, **k: 50_000_000)
    monkeypatch.setattr(transport, "send_memo_payment", lambda *a, **k: _sent("D" * 64))
    assert lessons.lesson_4_send_payment(camp, "again").ok


def test_a_send_that_fails_on_the_ledger_clears_the_record(camp, monkeypatch):
    monkeypatch.setattr(transport, "resolve_in_flight", lambda *a, **k: None)
    monkeypatch.setattr(transport, "get_balance", lambda *a, **k: 50_000_000)

    def send(*a, on_signed=None, **k):
        on_signed("E" * 64, 950)
        raise transport.XRPLTransactionFailed("tecPATH_DRY")

    monkeypatch.setattr(transport, "send_memo_payment", send)
    assert not lessons.lesson_4_send_payment(camp, "again").ok
    assert not Session.load().extra.get(lessons.IN_FLIGHT_KEY)


def test_an_unreadable_ledger_while_settling_is_a_clean_failure(camp, monkeypatch):
    def broken(*a, **k):
        raise transport.XRPLConnectionError("down")

    monkeypatch.setattr(transport, "resolve_in_flight", broken)
    assert not lessons.lesson_4_send_payment(camp, "again").ok


# ── D4 and D1: paths ──────────────────────────────────────────────────


def test_the_bundle_redacts_an_absolute_state_dir(tmp_path, monkeypatch):
    home = tmp_path / "home" / "learnername"
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    state = home / "camp-state"
    monkeypatch.setenv("XRPL_CAMP_HOME", str(state))
    models.refresh_state_paths()
    try:
        out = tmp_path / "bundle.zip"
        result = runner.invoke(app, ["support-bundle", "--offline", "--out", str(out)])
        assert result.exit_code == 0, result.output
        env = json.loads(zipfile.ZipFile(out).read("environment.json"))
        assert str(home) not in env["state_dir"]
        assert env["state_dir"].startswith("~")
    finally:
        monkeypatch.delenv("XRPL_CAMP_HOME")
        models.refresh_state_paths()


def test_lesson_2_names_the_real_wallet_path(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("XRPL_CAMP_HOME", str(tmp_path / "elsewhere"))
    models.refresh_state_paths()
    try:
        lessons.lesson_2_create_wallet(Session(started_at="2026-01-01T00:00:00Z"))
        out = strip_ansi(capsys.readouterr().out).replace("\n", "")
        assert (tmp_path / "elsewhere" / "wallet.json").as_posix() in out
    finally:
        monkeypatch.delenv("XRPL_CAMP_HOME")
        models.refresh_state_paths()


# ── D2, D3, D7: what the lessons say ──────────────────────────────────


def test_fund_says_when_the_faucet_was_not_asked(monkeypatch, capsys):
    from xrpl_camp import wallet

    wallet.save_wallet("rCampLearner", "sEdTM1uX8pu2do5XvTnutH6HsouMaM2")
    monkeypatch.setattr(lessons, "check_endpoint", lambda: None)
    monkeypatch.setattr(
        transport, "fund_wallet_detail",
        lambda *a, **k: transport.FundResult("rCampLearner", 10_000_000, already_funded=True),
    )
    monkeypatch.setattr(transport, "get_balance", lambda *a, **k: 10_000_000)
    monkeypatch.setattr(lessons, "_show_reserve", lambda *a: None)
    lessons.lesson_3_fund_wallet(Session(started_at="2026-01-01T00:00:00Z"))
    out = strip_ansi(capsys.readouterr().out)
    assert "faucet was not asked again" in out.replace("\n", " ")
    assert "Requesting funds" not in out


def test_the_replay_case_explains_its_preview_code(monkeypatch):
    class Outcome:
        engine_result = "telCAN_NOT_QUEUE"
        prefix = "tel"

    monkeypatch.setattr(transport, "simulate_tx", lambda tx: Outcome(), raising=False)
    out = lessons._try_past_sequence("rCampLearner", MAILBOX)
    assert out.code == "telCAN_NOT_QUEUE"
    assert "telCAN_NOT_QUEUE" in out.lesson and "tefPAST_SEQ" in out.lesson


def test_a_dry_run_does_not_claim_funds_or_a_ledger_write(dry_run_mode, capsys):
    s = Session(started_at="2026-01-01T00:00:00Z")
    lessons.lesson_2_create_wallet(s, dry_run=True)
    lessons.lesson_3_fund_wallet(s, dry_run=True)
    lessons.lesson_4_send_payment(s, "dry note", dry_run=True)
    out = strip_ansi(capsys.readouterr().out)
    assert "Account funded" not in out
    assert "Written to the ledger" not in out
    assert out.count("Simulated.") == 2


# ── D6: Ctrl-C shows the Paused panel ─────────────────────────────────


def test_ctrl_c_inside_typer_shows_the_paused_panel(monkeypatch, capsys):
    import typer

    interrupted = typer.Typer()

    @interrupted.command()
    def boom():
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "app", interrupted)
    monkeypatch.setattr("sys.argv", ["xrpl-camp"])
    with pytest.raises(SystemExit) as exc:
        cli.run()
    assert exc.value.code == 130
    assert "Paused" in strip_ansi(capsys.readouterr().out)


def test_a_plain_exit_130_shows_no_panel(monkeypatch, capsys):
    import typer

    quits = typer.Typer()

    @quits.command()
    def boom():
        raise typer.Exit(130)

    monkeypatch.setattr(cli, "app", quits)
    monkeypatch.setattr("sys.argv", ["xrpl-camp"])
    with pytest.raises(SystemExit):
        cli.run()
    assert "Paused" not in strip_ansi(capsys.readouterr().out)
