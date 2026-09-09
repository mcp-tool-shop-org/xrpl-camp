"""The failure gate: what the product does when a lesson fails.

What it used to do was issue a signed certificate for work that never happened.
Measured on the shipped build: with `fund_wallet` and `send_memo_payment`
raising the real live failure (`temREDUNDANT`), `run_guided_flow()` walked all
the way to lesson 6, printed a completion panel claiming the learner "Funded it
on a public network / Wrote permanent words to the ledger / Verified everything
independently", wrote `xrpl_camp_certificate.json` and
`xrpl_camp_proof_pack.json` with a valid SHA-256 recording lessons [1, 2, 6],
and exited 0.

The product's central claim is portable, verifiable proof of what you did. The
suite had no assertion whatsoever about proof integrity under partial failure.
Every assertion below is about an artifact or an exit code, not about stdout
alone.
"""

from __future__ import annotations

import pytest

from tests.helpers import load_fixture, make_response, squash, stub_client
from xrpl_camp import lessons, transport
from xrpl_camp.models import Session

TXID = "1E721764B35CAFD9AB24CFA15D8DC5097E9B9CDFE967B3E2A99FC701A3E53E1D"

ARTIFACTS = ("xrpl_camp_certificate.json", "xrpl_camp_proof_pack.json")

#: The four claims the closing panel makes. None may be printed as achieved
#: for a lesson that did not complete.
CLAIMS = [claim for _, claim in lessons.COMPLETION_CLAIMS]


def _run_captured(**kwargs) -> tuple[int, str]:
    with lessons.console.capture() as cap:
        code = lessons.run_guided_flow(**kwargs)
    return code, squash(cap.get())


@pytest.fixture()
def working_network(monkeypatch):
    """A transport where everything succeeds, so a test can break one thing.

    The lookup is wired to the memo lesson 4 actually sent, so lesson 5's
    readback comparison is a genuine round trip rather than a rubber stamp: the
    ledger's answer is checked against what was written, and a test that breaks
    the send is therefore visible at the verify step too.
    """
    sent: dict = {}

    def fake_send(seed, memo, dest, url=None, **k):
        sent["memo"] = memo
        return transport.SendResult(
            txid=TXID, destination=dest, amount_drops=k.get("amount_drops") or 1,
            fee_drops=10, created_account=False,
        )

    def lookup_response(_req):
        fixture = load_fixture("tx_v2_payment.json")
        fixture["tx_json"]["Memos"][0]["Memo"]["MemoData"] = transport._to_hex(
            sent.get("memo", ""),
        )
        return make_response(fixture)

    monkeypatch.setattr(
        transport, "fund_wallet", lambda seed, url=None, **k: "rFunded",
    )
    monkeypatch.setattr(transport, "get_balance", lambda *a, **k: 100_000_000)
    monkeypatch.setattr(transport, "get_reserve_base", lambda *a, **k: 1_000_000)
    monkeypatch.setattr(transport, "send_memo_payment", fake_send)
    stub_client(monkeypatch, lookup_response)
    return sent


def _break(monkeypatch, name: str, exc: Exception) -> None:
    def boom(*a, **k):
        raise exc

    monkeypatch.setattr(transport, name, boom)


# ---------------------------------------------------------------------------
# One failing lesson stops everything downstream
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("lesson", "attr", "exc"),
    [
        (3, "fund_wallet", transport.XRPLConnectionError("faucet unreachable")),
        (4, "send_memo_payment",
         transport.XRPLTransactionFailed("Transaction failed (temREDUNDANT)")),
        (5, "lookup_tx", transport.XRPLConnectionError("endpoint unreachable")),
    ],
)
def test_a_failed_lesson_halts_the_flow_and_certifies_nothing(
    lesson, attr, exc, working_network, monkeypatch, tmp_path,
):
    """The exact escape: three network lessons failed and a pack was still sealed."""
    _break(monkeypatch, attr, exc)

    code, output = _run_captured()

    assert code != 0, "a failed lesson exited 0"
    for name in ARTIFACTS:
        assert not (tmp_path / name).exists(), f"{name} was written after a failure"
    assert "Paused" in output
    assert f"Stopped at Lesson {lesson}" in output
    assert "Record sealed" not in output
    assert "XRPL Camp — Complete" not in output


@pytest.mark.parametrize(
    ("lesson", "attr", "exc"),
    [
        (3, "fund_wallet", transport.XRPLConnectionError("faucet unreachable")),
        (4, "send_memo_payment",
         transport.XRPLTransactionFailed("Transaction failed (temREDUNDANT)")),
        (5, "lookup_tx", transport.XRPLConnectionError("endpoint unreachable")),
    ],
)
def test_no_success_language_survives_a_failure(
    lesson, attr, exc, working_network, monkeypatch,
):
    """Not one of the four completion claims may be printed as achieved."""
    _break(monkeypatch, attr, exc)

    _, output = _run_captured()

    for claim in CLAIMS:
        assert claim not in output, f"claimed {claim!r} after lesson {lesson} failed"


@pytest.mark.parametrize(
    ("lesson", "attr", "exc"),
    [
        (3, "fund_wallet", transport.XRPLConnectionError("faucet unreachable")),
        (4, "send_memo_payment",
         transport.XRPLTransactionFailed("Transaction failed (temREDUNDANT)")),
        (5, "lookup_tx", transport.XRPLConnectionError("endpoint unreachable")),
    ],
)
def test_the_session_records_only_what_actually_happened(
    lesson, attr, exc, working_network, monkeypatch,
):
    """Progress up to the failure is kept; the failed lesson and beyond are not."""
    _break(monkeypatch, attr, exc)

    _run_captured()

    saved = Session.load()
    assert saved is not None
    for done in range(1, lesson):
        assert saved.is_complete(done), f"lesson {done} succeeded but was not recorded"
    for undone in range(lesson, 7):
        assert not saved.is_complete(undone), f"lesson {undone} recorded but never ran"


def test_a_transaction_that_is_not_on_the_ledger_halts_the_flow(
    working_network, monkeypatch, tmp_path,
):
    """The lookup succeeds as a request and finds nothing. That is still a failure.

    Previously `lookup_tx` parsed a `txnNotFound` body as a hit, so this path
    rendered a details table, printed "Independently verified", and sealed a
    certificate for a transaction that does not exist.
    """
    stub_client(
        monkeypatch,
        make_response(load_fixture("tx_not_found_v2.json"), successful=False),
    )

    code, output = _run_captured()

    assert code != 0
    assert "Stopped at Lesson 5" in output
    assert "Independently verified" not in output
    for name in ARTIFACTS:
        assert not (tmp_path / name).exists()


def test_a_ledger_readback_that_does_not_match_halts_the_flow(
    working_network, monkeypatch, tmp_path,
):
    """The memo comparison is the verification. A mismatch must not certify."""
    fixture = load_fixture("tx_v2_payment.json")
    fixture["tx_json"]["Memos"][0]["Memo"]["MemoData"] = "6e6f7420776861742077652073656e74"
    stub_client(monkeypatch, make_response(fixture))

    code, output = _run_captured()

    assert code != 0
    assert "Stopped at Lesson 5" in output
    for name in ARTIFACTS:
        assert not (tmp_path / name).exists()


# ---------------------------------------------------------------------------
# The happy path still produces a sealed record — so the gate is a gate,
# not a wall.
# ---------------------------------------------------------------------------


def test_a_clean_run_seals_a_record_and_exits_zero(working_network, tmp_path):
    code, output = _run_captured()

    assert code == 0
    for name in ARTIFACTS:
        assert (tmp_path / name).exists(), f"{name} was not written on a clean run"
    for claim in CLAIMS:
        assert claim in output
    assert "Record sealed" in output

    saved = Session.load()
    assert saved is not None
    assert all(saved.is_complete(n) for n in range(1, 7))
    assert saved.txids["lesson_4"] == TXID


def test_the_sealed_pack_never_contains_a_seed(working_network, tmp_path):
    """The certificate is meant to be shareable. That is only true if it is clean."""
    import json

    _run_captured()

    wallet_seed = json.loads(
        (tmp_path / ".xrpl-camp" / "wallet.json").read_text("utf-8"),
    )["seed"]
    mailbox_seed = json.loads(
        (tmp_path / ".xrpl-camp" / "mailbox.json").read_text("utf-8"),
    )["seed"]

    for name in ARTIFACTS:
        text = (tmp_path / name).read_text("utf-8")
        assert wallet_seed not in text
        assert mailbox_seed not in text


# ---------------------------------------------------------------------------
# Resume
# ---------------------------------------------------------------------------


def test_the_flow_resumes_from_where_a_failure_stopped_it(
    working_network, monkeypatch, tmp_path,
):
    """"Run start again and it picks up exactly where you stopped" — asserted."""
    _break(
        monkeypatch, "fund_wallet",
        transport.XRPLConnectionError("faucet unreachable"),
    )
    first_code, _ = _run_captured()
    assert first_code != 0

    monkeypatch.setattr(
        transport, "fund_wallet", lambda seed, url=None, **k: "rFunded",
    )
    second_code, output = _run_captured()

    assert second_code == 0
    assert "already completed 2 of 6 lessons" in output
    assert (tmp_path / "xrpl_camp_certificate.json").exists()


def test_a_finished_run_does_not_redo_itself(working_network, tmp_path):
    assert _run_captured()[0] == 0
    cert_before = (tmp_path / "xrpl_camp_certificate.json").read_bytes()

    code, output = _run_captured()

    assert code == 0
    assert "already completed all 6 lessons" in output.lower()
    assert (tmp_path / "xrpl_camp_certificate.json").read_bytes() == cert_before


# ---------------------------------------------------------------------------
# Dry run
# ---------------------------------------------------------------------------


def test_a_full_dry_run_writes_nothing_at_all(tmp_path, dry_run_mode):
    """The whole flow, end to end, with the network guard armed.

    `no_network` (conftest) fails this test if any code path opens a socket, so
    "no network calls, no disk writes" is checked in both halves rather than
    asserted in a docstring.

    `dry_run_mode` is required, not incidental: the wallet layer consults the
    PROCESS-GLOBAL execution mode, not `run_guided_flow`'s `dry_run` argument.
    Calling `run_guided_flow(dry_run=True)` on its own therefore still writes
    a seed to disk. The CLI sets the global first (`cli._simulating`), so the
    shipped path is sound; this test mirrors the shipped path, and
    `test_cli_behaviour.py` pins it end to end through the console script.
    """
    code, output = _run_captured(dry_run=True)

    assert code == 0
    assert list(tmp_path.iterdir()) == [], "a dry run wrote to disk"
    assert "Dry Run Complete" in output
    assert Session.load() is None


def test_a_dry_run_does_not_disturb_a_real_session(tmp_path, working_network):
    """A learner mid-course must be able to preview without losing their place."""
    from xrpl_camp.models import ExecutionMode, set_execution_mode

    assert _run_captured()[0] == 0
    before = sorted(p.name for p in tmp_path.iterdir())
    session_before = (tmp_path / ".xrpl-camp" / "session.json").read_bytes()
    cert_before = (tmp_path / "xrpl_camp_certificate.json").read_bytes()

    set_execution_mode(ExecutionMode.DRY_RUN)
    code, _ = _run_captured(dry_run=True)

    assert code == 0
    assert sorted(p.name for p in tmp_path.iterdir()) == before
    assert (tmp_path / ".xrpl-camp" / "session.json").read_bytes() == session_before
    assert (tmp_path / "xrpl_camp_certificate.json").read_bytes() == cert_before
