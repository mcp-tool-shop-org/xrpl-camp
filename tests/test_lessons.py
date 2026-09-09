"""Direct coverage of `lessons.py` — every user-visible behaviour in the product.

Before this file, grepping tests/ for `lesson_1_mental_model|lesson_2_create_wallet|
lesson_3_fund_wallet|lesson_4_send_payment|lesson_5_verify_tx|lesson_6_certificate`
returned zero call sites. Both escaped CRITICALs lived here: the blank lesson-5
details table and the lesson-4 self-payment.

The lesson-5 tests below drive the REAL `transport.lookup_tx` over a REAL
recorded response, so the table assertions are downstream of the parser rather
than of a hand-written dict.
"""

from __future__ import annotations

import json

import pytest

from tests.helpers import (
    load_fixture,
    make_response,
    squash,
    strip_ansi,
    stub_client,
)
from xrpl_camp import lessons, transport, wallet
from xrpl_camp.models import DryRunSession, ExecutionMode, Session, set_execution_mode

TXID = "1E721764B35CAFD9AB24CFA15D8DC5097E9B9CDFE967B3E2A99FC701A3E53E1D"
SENDER = "r3B7h4qQERrzogwxrCqFMJBewNBzutXVn1"
MAILBOX = "rUUGAx14J9EwWbWLjQgVFfXA2zV5hfKqDP"
MEMO_TEXT = "XRPLCAMP|FIXTURE|recorded response"


@pytest.fixture()
def capture():
    """Capture everything a lesson prints, with ANSI stripped."""

    class Capture:
        def __init__(self) -> None:
            self.text = ""

        def __enter__(self):
            self._cap = lessons.console.capture()
            self._cap.__enter__()
            return self

        def __exit__(self, *exc):
            self._cap.__exit__(*exc)
            self.text = strip_ansi(self._cap.get())
            return False

        @property
        def squashed(self) -> str:
            return squash(self.text)

    return Capture


@pytest.fixture()
def session() -> Session:
    # `wallet_address` is SENDER because lesson 5 now credits only a
    # transaction the learner actually sent, so a session that verifies the
    # recorded fixture has to be the session that owns it.
    return Session(started_at="2026-01-01T00:00:00Z", wallet_address=SENDER)


@pytest.fixture()
def real_wallet(monkeypatch):
    """A wallet and mailbox on disk in the test's isolated cwd."""
    from xrpl.wallet import Wallet

    main = Wallet.create()
    box = Wallet.create()
    wallet.save_wallet(main.address, main.seed)
    wallet.save_mailbox(box.address, box.seed)
    return main, box


# ---------------------------------------------------------------------------
# Lesson 1
# ---------------------------------------------------------------------------


def test_lesson_1_marks_complete_and_teaches_the_units(session, capture):
    with capture() as cap:
        result = lessons.lesson_1_mental_model(session)

    assert result.ok is True
    assert result.exit_code == 0
    assert session.is_complete(1)
    assert "1 XRP = 1,000,000 drops" in cap.squashed
    assert "Foundation set" in cap.squashed


# ---------------------------------------------------------------------------
# Lesson 2
# ---------------------------------------------------------------------------


def test_lesson_2_writes_a_wallet_and_never_prints_the_seed(session, capture, tmp_path):
    with capture() as cap:
        result = lessons.lesson_2_create_wallet(session)

    assert result.ok is True
    saved = json.loads((tmp_path / ".xrpl-camp" / "wallet.json").read_text("utf-8"))
    assert saved["address"] == session.wallet_address
    assert saved["seed"] not in cap.text, "the seed reached the console"
    assert saved["address"] in cap.text


def test_lesson_2_dry_run_writes_nothing(session, capture, tmp_path):
    set_execution_mode(ExecutionMode.DRY_RUN)

    with capture() as cap:
        result = lessons.lesson_2_create_wallet(session, dry_run=True)

    assert result.ok is True
    assert list(tmp_path.iterdir()) == [], "a dry run touched the filesystem"
    assert "nothing written" in cap.squashed
    assert not session.is_complete(2), "a dry run must not record progress"


def test_lesson_2_reports_a_structured_failure_for_a_corrupt_wallet(
    session, capture, tmp_path,
):
    """A broken wallet.json produces a code + hint, never a raw traceback.

    `wallet.load_wallet()` raises `StateFileError`, which is a `CampFailure`.
    `lessons._load_wallet` catches it and returns the carried `CampError`, so
    the lesson fails gracefully — the guided flow can print its halt panel and
    tell the learner how to resume, rather than unwinding the whole run to the
    `cli.run()` boundary.

    An earlier revision of this test asserted the opposite (that the failure
    propagates), because that was the measured behaviour at the time: the
    handler's `except (OSError, ValueError, TypeError, KeyError)` could not
    catch a `CampFailure`, so the clause could never fire for the case its own
    docstring described. The user-facing contract was intact either way, which
    is exactly why the dead clause survived. `test_cli_behaviour.py` still pins
    the exit code and the absence of a traceback end to end.
    """
    state = tmp_path / ".xrpl-camp"
    state.mkdir()
    (state / "wallet.json").write_text("{not json", encoding="utf-8")

    with capture() as cap:
        result = lessons.lesson_2_create_wallet(session)

    assert result.ok is False
    assert result.error is not None
    assert result.error.code == "WALLET_CORRUPT"
    assert result.error.hint
    assert result.exit_code != 0
    assert "Traceback" not in cap.squashed
    assert not session.is_complete(2)


# ---------------------------------------------------------------------------
# Lesson 3
# ---------------------------------------------------------------------------


def test_lesson_3_without_a_wallet_fails_with_a_hint(session, capture):
    with capture() as cap:
        result = lessons.lesson_3_fund_wallet(session)

    assert result.ok is False
    assert not session.is_complete(3)
    assert "wallet" in cap.squashed.lower()
    assert "Traceback" not in cap.text


def test_lesson_3_faucet_failure_fails_the_lesson(
    session, capture, real_wallet, monkeypatch,
):
    """The error branch that a live run hit and no test covered."""
    def boom(*args, **kwargs):
        raise transport.XRPLConnectionError("Could not connect to the faucet")

    monkeypatch.setattr(transport, "fund_wallet", boom)

    with capture() as cap:
        result = lessons.lesson_3_fund_wallet(session)

    assert result.ok is False
    assert result.exit_code != 0
    assert not session.is_complete(3)
    assert "Traceback" not in cap.text


def test_lesson_3_dry_run_makes_no_call_and_records_nothing(
    session, capture, real_wallet, monkeypatch,
):
    calls: list = []
    real = transport.fund_wallet
    monkeypatch.setattr(
        transport, "fund_wallet",
        lambda *a, **k: (calls.append((a, k)), real(*a, **k))[1],
    )

    with capture() as cap:
        result = lessons.lesson_3_fund_wallet(session, dry_run=True)

    assert result.ok is True
    assert calls and calls[0][1]["dry_run"] is True
    assert not session.is_complete(3)
    assert "skipped — dry run" in cap.squashed


# ---------------------------------------------------------------------------
# Lesson 4
# ---------------------------------------------------------------------------


def test_lesson_4_pays_the_mailbox_not_the_sender(
    session, capture, real_wallet, monkeypatch,
):
    """The shipped bug, stated as a lesson-level assertion.

    Lesson 4 must hand `send_memo_payment` a destination that is NOT the
    sender. It used to pass the learner's own address, which xrpl-py refuses to
    construct and the ledger rejects as temREDUNDANT.
    """
    main, box = real_wallet
    seen: dict = {}

    def fake_send(seed, memo, destination, url=None, **kwargs):
        seen.update(seed=seed, memo=memo, destination=destination, **kwargs)
        return transport.SendResult(
            txid=TXID, destination=destination,
            amount_drops=kwargs.get("amount_drops") or 1,
            fee_drops=10, created_account=True,
        )

    monkeypatch.setattr(transport, "send_memo_payment", fake_send)
    monkeypatch.setattr(transport, "get_balance", lambda *a, **k: 100_000_000)

    with capture() as cap:
        result = lessons.lesson_4_send_payment(session, memo="hello ledger")

    assert result.ok is True
    assert seen["destination"] == box.address
    assert seen["destination"] != main.address
    assert seen["seed"] == main.seed
    assert session.txids["lesson_4"] == TXID
    assert "created an account on a public ledger" in cap.squashed


def test_lesson_4_sends_the_reserve_when_the_mailbox_does_not_exist(
    session, capture, real_wallet, monkeypatch,
):
    """A 1-drop payment to a non-existent account is rejected AND burns the fee."""
    seen: dict = {}

    def fake_send(seed, memo, destination, url=None, **kwargs):
        seen.update(kwargs)
        return transport.SendResult(
            txid=TXID, destination=destination,
            amount_drops=kwargs["amount_drops"], fee_drops=10, created_account=True,
        )

    def missing(*a, **k):
        raise transport.XRPLAccountNotFound("rMailbox")

    monkeypatch.setattr(transport, "get_balance", missing)
    monkeypatch.setattr(transport, "get_reserve_base", lambda *a, **k: 1_000_000)
    monkeypatch.setattr(transport, "send_memo_payment", fake_send)

    with capture():
        result = lessons.lesson_4_send_payment(session, memo="first")

    assert result.ok is True
    assert seen["amount_drops"] == 1_000_000


def test_lesson_4_sends_one_drop_when_the_mailbox_already_exists(
    session, capture, real_wallet, monkeypatch,
):
    seen: dict = {}

    def fake_send(seed, memo, destination, url=None, **kwargs):
        seen.update(kwargs)
        return transport.SendResult(
            txid=TXID, destination=destination,
            amount_drops=kwargs["amount_drops"], fee_drops=10, created_account=False,
        )

    monkeypatch.setattr(transport, "get_balance", lambda *a, **k: 100_000_000)
    monkeypatch.setattr(transport, "send_memo_payment", fake_send)

    with capture() as cap:
        result = lessons.lesson_4_send_payment(session, memo="again")

    assert result.ok is True
    assert seen["amount_drops"] == lessons.REPEAT_SEND_DROPS == 1
    assert "created an account" not in cap.squashed


def test_lesson_4_refuses_a_memo_containing_the_seed(
    session, capture, real_wallet, monkeypatch,
):
    """Lesson 2 says guard the seed; lesson 4 invites free text into a public record."""
    main, _ = real_wallet
    monkeypatch.setattr(transport, "get_balance", lambda *a, **k: 100_000_000)
    called: list = []
    monkeypatch.setattr(
        transport, "send_memo_payment",
        lambda *a, **k: called.append(a),
    )

    with capture() as cap:
        result = lessons.lesson_4_send_payment(session, memo=f"my seed is {main.seed}")

    assert result.ok is False
    assert called == [], "a memo carrying the seed was submitted anyway"
    assert not session.is_complete(4)
    assert "Traceback" not in cap.text


def test_lesson_4_send_failure_does_not_mark_the_lesson_complete(
    session, capture, real_wallet, monkeypatch,
):
    def boom(*a, **k):
        raise transport.XRPLTransactionFailed("Transaction failed (temREDUNDANT)")

    monkeypatch.setattr(transport, "get_balance", lambda *a, **k: 100_000_000)
    monkeypatch.setattr(transport, "send_memo_payment", boom)

    with capture() as cap:
        result = lessons.lesson_4_send_payment(session, memo="note")

    assert result.ok is False
    assert result.exit_code != 0
    assert not session.is_complete(4)
    assert "lesson_4" not in session.txids
    assert "Traceback" not in cap.text


def test_lesson_4_escapes_a_memo_that_looks_like_rich_markup(
    session, capture, real_wallet, monkeypatch,
):
    """`--memo "note [v1]"` must display what it writes to the ledger."""
    monkeypatch.setattr(transport, "get_balance", lambda *a, **k: 100_000_000)
    monkeypatch.setattr(
        transport, "send_memo_payment",
        lambda seed, memo, dest, url=None, **k: transport.SendResult(
            txid=TXID, destination=dest, amount_drops=1,
            fee_drops=10, created_account=False,
        ),
    )

    with capture() as cap:
        result = lessons.lesson_4_send_payment(session, memo="note [v1]")

    assert result.ok is True
    assert "note [v1]" in cap.squashed


# ---------------------------------------------------------------------------
# Lesson 5 — the blank details table
# ---------------------------------------------------------------------------


def test_lesson_5_renders_the_parsed_fields_from_a_real_response(
    session, capture, monkeypatch,
):
    """THE lesson-level regression test for the tx_json break.

    The table is rendered from whatever the real parser returns. With the
    pre-fix parser every one of these rows was empty and the lesson still
    printed "Independently verified" underneath.
    """
    stub_client(monkeypatch, make_response(load_fixture("tx_v2_payment.json")))

    with capture() as cap:
        result = lessons.lesson_5_verify_tx(session, TXID, expected_memo=MEMO_TEXT)

    body = cap.squashed
    assert result.ok is True
    assert SENDER in body
    assert MAILBOX in body
    assert "1000000 drops" in body
    assert "10 drops" in body
    assert MEMO_TEXT in body
    assert "20604320" in body
    assert "tesSUCCESS" in body
    assert "Independently verified" in body
    assert session.is_complete(5)


def test_lesson_5_refuses_a_transaction_that_is_not_on_the_ledger(
    session, capture, monkeypatch,
):
    """`verify --tx <any 64 hex chars>` used to print a table and a green tick."""
    stub_client(
        monkeypatch,
        make_response(load_fixture("tx_not_found_v2.json"), successful=False),
    )

    with capture() as cap:
        result = lessons.lesson_5_verify_tx(session, "A" * 64)

    body = cap.squashed
    assert result.ok is False
    assert result.exit_code != 0
    assert not session.is_complete(5)
    assert "Independently verified" not in body
    assert "Transaction Details" not in body
    assert "Traceback" not in cap.text


def test_lesson_5_refuses_a_failed_transaction(session, capture, monkeypatch):
    fixture = load_fixture("tx_v2_payment.json")
    fixture["meta"]["TransactionResult"] = "tecUNFUNDED_PAYMENT"
    stub_client(monkeypatch, make_response(fixture))

    with capture() as cap:
        result = lessons.lesson_5_verify_tx(session, TXID)

    assert result.ok is False
    assert not session.is_complete(5)
    assert "Independently verified" not in cap.squashed


def test_lesson_5_refuses_when_the_ledger_memo_differs_from_what_was_sent(
    session, capture, monkeypatch,
):
    """The readback is a comparison, not a display."""
    stub_client(monkeypatch, make_response(load_fixture("tx_v2_payment.json")))

    with capture() as cap:
        result = lessons.lesson_5_verify_tx(
            session, TXID, expected_memo="something else entirely",
        )

    assert result.ok is False
    assert "Independently verified" not in cap.squashed


def test_lesson_5_refuses_a_response_with_blank_fields(session, capture, monkeypatch):
    """The exact symptom of the shipped bug, caught at the lesson boundary.

    Even if a future parser regression blanks the fields again, the lesson must
    refuse rather than certify the blanks.
    """
    fixture = load_fixture("tx_v2_payment.json")
    fixture["tx_json"]["Destination"] = ""
    stub_client(monkeypatch, make_response(fixture))

    with capture() as cap:
        result = lessons.lesson_5_verify_tx(session, TXID)

    assert result.ok is False
    assert "recipient" in cap.squashed
    assert "Independently verified" not in cap.squashed


def test_lesson_5_without_a_transaction_explains_what_to_run(session, capture):
    with capture() as cap:
        result = lessons.lesson_5_verify_tx(session)

    assert result.ok is False
    assert "NO_TRANSACTION" in cap.text
    assert "xrpl-camp send" in cap.squashed


def test_lesson_5_lookup_failure_is_a_structured_error(session, capture, monkeypatch):
    def boom(*a, **k):
        raise transport.XRPLConnectionError("Could not connect")

    monkeypatch.setattr(transport, "lookup_tx", boom)

    with capture() as cap:
        result = lessons.lesson_5_verify_tx(session, TXID)

    assert result.ok is False
    assert "Traceback" not in cap.text
    assert not session.is_complete(5)


# ---------------------------------------------------------------------------
# Lesson 6
# ---------------------------------------------------------------------------


def _completed_through_five() -> Session:
    s = Session(started_at="2026-01-01T00:00:00Z", wallet_address=SENDER)
    for n in range(1, 6):
        s.mark_complete(n, lessons.LESSON_NAMES[n], duration_seconds=1.0)
    s.txids["lesson_4"] = TXID
    return s


def test_lesson_6_writes_both_artifacts(capture, tmp_path):
    s = _completed_through_five()

    with capture() as cap:
        result = lessons.lesson_6_certificate(s)

    assert result.ok is True
    cert = tmp_path / "xrpl_camp_certificate.json"
    pack = tmp_path / "xrpl_camp_proof_pack.json"
    assert cert.exists() and pack.exists()
    assert "Record sealed" in cap.squashed
    # No seed anywhere in either artifact.
    assert "seed" not in cert.read_text("utf-8").lower()
    assert "seed" not in pack.read_text("utf-8").lower()


def test_lesson_6_refuses_to_seal_incomplete_work(capture, tmp_path):
    """A certificate is a claim about what you did.

    With lessons 3-5 unfinished, the flow used to walk on and write a
    SHA-256-sealed pack claiming the learner funded an account, wrote to the
    ledger and verified it.
    """
    s = Session(started_at="2026-01-01T00:00:00Z", wallet_address=SENDER)
    s.mark_complete(1, lessons.LESSON_NAMES[1])
    s.mark_complete(2, lessons.LESSON_NAMES[2])

    with capture() as cap:
        result = lessons.lesson_6_certificate(s)

    assert result.ok is False
    assert result.exit_code != 0
    assert list(tmp_path.iterdir()) == [], "an artifact was written anyway"
    assert "Fund Wallet" in cap.squashed
    assert "Record sealed" not in cap.squashed


def test_lesson_6_dry_run_writes_nothing(capture, tmp_path):
    """The documented promise: 'No artifacts generated in dry-run mode'."""
    s = _completed_through_five()

    with capture() as cap:
        result = lessons.lesson_6_certificate(s, dry_run=True)

    assert result.ok is True
    assert list(tmp_path.iterdir()) == []
    assert "No artifacts generated in dry-run mode" in cap.squashed


def test_lesson_6_accepts_lessons_proven_in_this_process(capture, tmp_path):
    """`assume_complete` is the dry-run flow's only record; it must be honoured."""
    s = DryRunSession(started_at="2026-01-01T00:00:00Z", wallet_address=SENDER)

    with capture():
        result = lessons.lesson_6_certificate(
            s, dry_run=True, assume_complete={1, 2, 3, 4, 5},
        )

    assert result.ok is True
    assert list(tmp_path.iterdir()) == []


# ---------------------------------------------------------------------------
# Interactivity
# ---------------------------------------------------------------------------


def test_pause_is_a_no_op_when_stdin_is_not_a_tty(monkeypatch, capture):
    """Every CI run, every pipe, every `< /dev/null`.

    `_pause()` used to call `console.input()` unconditionally, so the guided
    flow raised EOFError before lesson 1 rendered whenever stdin was not a
    terminal — and nothing in the suite reached it.
    """
    class NotATty:
        def isatty(self):
            return False

    monkeypatch.setattr("sys.stdin", NotATty())

    def explode(*a, **k):
        raise AssertionError("_pause() prompted with no terminal attached")

    monkeypatch.setattr(lessons.console, "input", explode)

    assert lessons.is_interactive() is False
    with capture():
        lessons._pause()  # must not raise


def test_pause_is_a_no_op_under_non_interactive_mode(monkeypatch, capture):
    class IsATty:
        def isatty(self):
            return True

    monkeypatch.setattr("sys.stdin", IsATty())
    monkeypatch.setattr(
        lessons.console, "input",
        lambda *a, **k: pytest.fail("_pause() prompted under --yes"),
    )
    lessons.set_non_interactive(True)

    assert lessons.is_interactive() is False
    with capture():
        lessons._pause()


def test_pause_survives_a_tty_that_reaches_eof(monkeypatch, capture):
    class IsATty:
        def isatty(self):
            return True

    monkeypatch.setattr("sys.stdin", IsATty())

    def eof(*a, **k):
        raise EOFError("EOF when reading a line")

    monkeypatch.setattr(lessons.console, "input", eof)

    with capture():
        lessons._pause()  # must swallow the EOFError


def test_is_interactive_is_false_when_stdin_is_gone(monkeypatch):
    """A frozen binary launched without a console has sys.stdin = None."""
    monkeypatch.setattr("sys.stdin", None)
    assert lessons.is_interactive() is False


# ---------------------------------------------------------------------------
# Endpoint guard
# ---------------------------------------------------------------------------


def test_check_endpoint_accepts_the_public_testnet():
    assert lessons.check_endpoint() is None


def test_check_endpoint_refuses_an_unknown_host(monkeypatch):
    monkeypatch.setenv("XRPL_CAMP_RPC_URL", "https://s1.ripple.com:51234/")
    assert lessons.check_endpoint() is not None


def test_check_endpoint_warns_loudly_when_overridden(monkeypatch, capture):
    monkeypatch.setenv("XRPL_CAMP_RPC_URL", "https://s1.ripple.com:51234/")
    monkeypatch.setenv(lessons.ALLOW_ANY_ENDPOINT_ENV, "1")

    with capture() as cap:
        assert lessons.check_endpoint() is None

    assert "not a known test network" in cap.squashed.lower()
    assert "real" in cap.squashed.lower()


# ---------------------------------------------------------------------------
# Duration formatting — exact strings, not substrings
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(0, "0s"), (45, "45s"), (59, "59s"), (60, "1m"), (120, "2m"),
     (125, "2m 5s"), (3600, "60m"), (671, "11m 11s")],
)
def test_format_duration_exact(seconds, expected):
    assert lessons.format_duration(seconds) == expected
