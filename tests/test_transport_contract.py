"""Recorded-response contract tests: the REAL parsers over REAL wire captures.

Provenance
----------
Every file in `tests/fixtures/` is a verbatim capture of a live XRPL Testnet
response, taken on 2026-09-09 with xrpl-py 5.1.0 against
`https://s.altnet.rippletest.net:51234/`. The payment they record
(`1E721764B35CAFD9AB24CFA15D8DC5097E9B9CDFE967B3E2A99FC701A3E53E1D`) funded a
brand-new account into existence, so the same capture carries the
`CreatedNode` metadata lesson 4's strongest beat depends on.

  tx_v2_payment.json                 `tx`, api_version=2  — fields under tx_json
  tx_v1_payment.json                 `tx`, api_version=1  — fields at top level
  tx_not_found_v2.json               `tx` for a hash that is not on the ledger
  submit_created_account_v2.json     submit_and_wait result, account created
  submit_existing_account_v2.json    submit_and_wait result, 1-drop repeat
  account_info_v2.json               `account_info` for a funded account
  account_info_not_found_v2.json     `account_info`, actNotFound
  server_state_v2.json               `server_state`, carries reserve_base

Why this file exists
--------------------
The tests it replaces hand-copied `lookup_tx`'s body into the test and asserted
against their own copy, so deleting `lookup_tx` left them green. Worse, the
shape they declared as truth was the API-v1 layout — Account/Destination/Fee at
the top level and `Amount` rather than `DeliverMax` — which is exactly the
layout that does NOT come back under API v2. Feeding a real v2 response through
the shipped parser returned `amount='0', destination='', account=''`: lesson
5's blank details table, reproduced from the wire.

Nothing here re-implements parsing. Each test stubs only the client and calls
the real function.
"""

from __future__ import annotations

import pytest

from tests.helpers import LOOKUP_KEYS, load_fixture, make_response, stub_client
from xrpl_camp import transport

TXID = "1E721764B35CAFD9AB24CFA15D8DC5097E9B9CDFE967B3E2A99FC701A3E53E1D"
SENDER = "r3B7h4qQERrzogwxrCqFMJBewNBzutXVn1"
MAILBOX = "rUUGAx14J9EwWbWLjQgVFfXA2zV5hfKqDP"
MEMO_TEXT = "XRPLCAMP|FIXTURE|recorded response"


@pytest.fixture()
def tx_v2() -> dict:
    return load_fixture("tx_v2_payment.json")


@pytest.fixture()
def tx_v1() -> dict:
    return load_fixture("tx_v1_payment.json")


# ---------------------------------------------------------------------------
# The captured shape is the shape the contract claims
# ---------------------------------------------------------------------------


def test_recorded_v2_response_nests_fields_under_tx_json(tx_v2):
    """Guards the fixture itself. If this drifts, every assertion below is moot."""
    assert set(tx_v2) == {
        "close_time_iso", "ctid", "hash", "ledger_hash", "ledger_index",
        "meta", "tx_json", "validated",
    }
    for key in ("Account", "Destination", "DeliverMax", "Fee", "Memos"):
        assert key in tx_v2["tx_json"], f"{key} moved out of tx_json"
    # The old parser looked for these at the top level and found nothing.
    for key in ("Account", "Destination", "Amount", "Fee", "Memos"):
        assert key not in tx_v2


def test_recorded_v1_response_is_flat(tx_v1):
    """The fallback path is a real API shape, not a hypothetical one."""
    assert "tx_json" not in tx_v1
    for key in ("Account", "Destination", "Amount", "Fee", "Memos"):
        assert key in tx_v1


# ---------------------------------------------------------------------------
# lookup_tx over the real v2 response
# ---------------------------------------------------------------------------


def test_lookup_tx_parses_every_field_from_a_real_v2_response(monkeypatch, tx_v2):
    """The single test that would have caught the blank details table."""
    stub_client(monkeypatch, make_response(tx_v2))

    tx = transport.lookup_tx(TXID)

    assert tx["found"] is True
    assert tx["hash"] == TXID
    assert tx["account"] == SENDER
    assert tx["destination"] == MAILBOX
    assert tx["amount"] == "1000000"
    assert tx["delivered"] == "1000000"
    assert tx["fee"] == "10"
    assert tx["memo"] == MEMO_TEXT
    assert tx["ledger_index"] == 20604320
    assert tx["result"] == "tesSUCCESS"
    assert tx["validated"] is True
    assert tx["close_time_iso"] == "2026-09-09T03:28:21Z"
    # Ripple epoch (2000-01-01) converted to Unix epoch.
    assert tx["date"] == 842239701 + transport.RIPPLE_EPOCH_OFFSET


def test_lookup_tx_leaves_no_field_blank_on_a_real_response(monkeypatch, tx_v2):
    """The failure mode was blanks, not wrong values. Assert against blanks.

    With the pre-fix parser this returned account='', destination='',
    amount='0', fee='0', memo='' — a rendered table of nothing, over the top of
    "Independently verified".
    """
    stub_client(monkeypatch, make_response(tx_v2))

    tx = transport.lookup_tx(TXID)

    for key in ("hash", "account", "destination", "memo", "close_time_iso"):
        assert str(tx[key]).strip(), f"{key} came back blank"
    assert int(tx["amount"]) > 0
    assert int(tx["fee"]) > 0
    assert int(tx["ledger_index"]) > 0


def test_lookup_tx_return_matches_the_shared_key_contract(monkeypatch, tx_v2):
    """The real path is pinned to the SAME key set as the dry-run path.

    Asserted in one place against both returns, so the simulated walkthrough and
    the real run cannot render different tables again.
    """
    stub_client(monkeypatch, make_response(tx_v2))

    real = transport.lookup_tx(TXID)
    simulated = transport.lookup_tx(TXID, dry_run=True)

    assert set(real) == set(LOOKUP_KEYS)
    assert set(simulated) == set(real)


def test_lookup_tx_pins_the_api_version(monkeypatch, tx_v2):
    """`api_version=2` is what makes the parsed shape predictable.

    Without the pin the layout is whatever the client and server negotiate,
    which is how the tx_json break landed in the first place.
    """
    recorder = stub_client(monkeypatch, make_response(tx_v2))

    transport.lookup_tx(TXID)

    req = recorder.request_of("Tx")
    assert req.api_version == transport.XRPL_API_VERSION == 2
    assert req.transaction == TXID


def test_every_request_model_pins_the_version_explicitly():
    """The pin must be spelled out, not inherited from xrpl-py's default.

    xrpl-py 5.1.0 happens to default `api_version` to 2, so deleting the
    explicit argument is INVISIBLE at the request level today — and the day the
    library's default moves to 3 is exactly the day the `tx_json` break repeats,
    silently, in the field. This walks the transport's AST so a dropped pin is
    red immediately rather than on someone else's machine a major version later.
    """
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(transport))
    models = {"Tx", "AccountInfo", "ServerState"}
    found: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = getattr(node.func, "id", None)
        if name not in models:
            continue
        found.append(name)
        pinned = [
            kw for kw in node.keywords
            if kw.arg == "api_version"
            and isinstance(kw.value, ast.Name)
            and kw.value.id == "XRPL_API_VERSION"
        ]
        assert pinned, (
            f"{name}(...) at transport.py line {node.lineno} does not pass "
            f"api_version=XRPL_API_VERSION"
        )

    assert models.issubset(found), (
        f"expected every request model to be constructed in transport.py; "
        f"missing {sorted(models - set(found))}"
    )


# ---------------------------------------------------------------------------
# The v1 fallback
# ---------------------------------------------------------------------------


def test_lookup_tx_parses_a_real_v1_response_via_the_fallback(monkeypatch, tx_v1):
    """An older endpoint that only speaks API v1 still parses correctly."""
    stub_client(monkeypatch, make_response(tx_v1))

    tx = transport.lookup_tx(TXID)

    assert tx["found"] is True
    assert tx["account"] == SENDER
    assert tx["destination"] == MAILBOX
    assert tx["amount"] == "1000000"
    assert tx["fee"] == "10"
    assert tx["memo"] == MEMO_TEXT
    assert tx["result"] == "tesSUCCESS"
    # v1 has no close_time_iso; the parser must not invent one.
    assert tx["close_time_iso"] == ""
    assert set(tx) == set(LOOKUP_KEYS)


def test_both_api_versions_agree_on_every_shared_field(monkeypatch, tx_v1, tx_v2):
    """One transaction, two wire layouts, one parsed answer."""
    stub_client(monkeypatch, make_response(tx_v2))
    from_v2 = transport.lookup_tx(TXID)

    monkeypatch.undo()
    stub_client(monkeypatch, make_response(tx_v1))
    from_v1 = transport.lookup_tx(TXID)

    shared = set(LOOKUP_KEYS) - {"close_time_iso"}
    for key in sorted(shared):
        assert from_v1[key] == from_v2[key], f"{key} differs between API versions"


# ---------------------------------------------------------------------------
# found = False
# ---------------------------------------------------------------------------


def test_lookup_tx_reports_not_found_for_a_txn_not_found_response(monkeypatch):
    """`client.request()` does not raise for a missing transaction.

    It returns a Response whose result is `{"error": "txnNotFound"}`. Parsing
    that as a hit is what made `xrpl-camp verify --tx <any 64 hex chars>` print
    a details table and "Independently verified" for a hash that is not on any
    ledger.
    """
    missing = load_fixture("tx_not_found_v2.json")
    assert missing["error"] == "txnNotFound"
    stub_client(monkeypatch, make_response(missing, successful=False))

    tx = transport.lookup_tx("A" * 64)

    assert tx["found"] is False
    assert tx["validated"] is False
    assert tx["result"] == ""
    assert tx["account"] == ""
    assert tx["destination"] == ""
    assert tx["memo"] == ""
    assert tx["hash"] == "A" * 64


def test_not_found_return_carries_the_full_key_contract(monkeypatch):
    """Callers branch on `found` and index the rest. They must never KeyError."""
    stub_client(
        monkeypatch,
        make_response(load_fixture("tx_not_found_v2.json"), successful=False),
    )

    assert set(transport.lookup_tx("A" * 64)) == set(LOOKUP_KEYS)


def test_lookup_tx_raises_for_a_non_not_found_error(monkeypatch):
    """A malformed-request error is a failure, not an empty result."""
    stub_client(
        monkeypatch,
        make_response(
            {"error": "invalidParams", "error_message": "Invalid field 'transaction'."},
            successful=False,
        ),
    )

    with pytest.raises(transport.XRPLTransactionFailed) as exc:
        transport.lookup_tx("nonsense")

    assert "Invalid field" in str(exc.value)


# ---------------------------------------------------------------------------
# Memo decoding must never turn a found transaction into a failed lookup
# ---------------------------------------------------------------------------


def test_binary_memo_does_not_break_a_real_lookup(monkeypatch, tx_v2):
    """Derived from the real capture: same response, non-UTF-8 memo bytes.

    Memos on a public ledger are stranger-controlled and `verify --tx` accepts
    any hash, so a decoder that raised would report "lookup failed" for a
    transaction that was found perfectly well.
    """
    tx_v2["tx_json"]["Memos"][0]["Memo"]["MemoData"] = "FFFE"
    stub_client(monkeypatch, make_response(tx_v2))

    tx = transport.lookup_tx(TXID)

    assert tx["found"] is True
    assert tx["destination"] == MAILBOX  # everything else still parses
    assert tx["memo"]  # something readable-ish came back, and nothing raised


def test_malformed_memo_hex_does_not_break_a_real_lookup(monkeypatch, tx_v2):
    tx_v2["tx_json"]["Memos"][0]["Memo"]["MemoData"] = "zzzz"
    stub_client(monkeypatch, make_response(tx_v2))

    tx = transport.lookup_tx(TXID)

    assert tx["found"] is True
    assert tx["memo"] == "(unreadable memo)"


def test_missing_memos_leaves_every_other_field_populated(monkeypatch, tx_v2):
    """The no-memo case, asserted on the whole dict rather than one blank field."""
    del tx_v2["tx_json"]["Memos"]
    stub_client(monkeypatch, make_response(tx_v2))

    tx = transport.lookup_tx(TXID)

    assert tx["memo"] == ""
    assert tx["found"] is True
    assert tx["account"] == SENDER
    assert tx["destination"] == MAILBOX
    assert tx["amount"] == "1000000"
    assert tx["fee"] == "10"
    assert tx["result"] == "tesSUCCESS"


# ---------------------------------------------------------------------------
# Account creation metadata
# ---------------------------------------------------------------------------


def test_created_account_detected_from_real_submit_metadata():
    """The beat lesson 4 sells: this payment brought an account into existence."""
    meta = load_fixture("submit_created_account_v2.json")["meta"]
    assert transport._created_account(meta, MAILBOX) is True


def test_created_account_is_false_for_a_repeat_payment():
    meta = load_fixture("submit_existing_account_v2.json")["meta"]
    assert transport._created_account(meta, MAILBOX) is False


def test_created_account_is_false_for_a_different_destination():
    """The CreatedNode must be the destination's, not just any created node."""
    meta = load_fixture("submit_created_account_v2.json")["meta"]
    assert transport._created_account(meta, SENDER) is False


# ---------------------------------------------------------------------------
# The real send path — Payment construction and result extraction
# ---------------------------------------------------------------------------


def _stub_send(monkeypatch, result: dict) -> dict:
    """Stub the client and submit_and_wait; return a dict capturing the tx built."""
    import xrpl.transaction

    captured: dict = {}
    stub_client(monkeypatch, make_response({"state": {}}, successful=False))

    def fake_submit(transaction, client, wallet, **kwargs):
        captured["transaction"] = transaction
        captured["wallet"] = wallet
        return make_response(result)

    monkeypatch.setattr(xrpl.transaction, "submit_and_wait", fake_submit)
    return captured


def test_send_memo_payment_builds_a_valid_payment(monkeypatch):
    """Executes the Payment/Memo construction the dry-run tests skipped entirely.

    transport.py lines from the client construction through the hash extraction
    had literally zero execution coverage: every send test returned 18 lines
    earlier at the dry-run guard.
    """
    from xrpl.wallet import Wallet

    sender = Wallet.from_seed(Wallet.create().seed)
    captured = _stub_send(
        monkeypatch, load_fixture("submit_created_account_v2.json"),
    )

    result = transport.send_memo_payment(
        sender.seed, "hello ledger", MAILBOX, amount_drops=1_000_000,
    )

    payment = captured["transaction"]
    assert type(payment).__name__ == "Payment"
    assert payment.is_valid()
    assert payment._get_errors() == {}
    assert payment.account == sender.address
    assert payment.destination == MAILBOX
    assert payment.amount == "1000000"
    assert transport._from_hex(payment.memos[0].memo_data) == "hello ledger"

    assert result.txid == TXID
    assert result.destination == MAILBOX
    assert result.amount_drops == 1_000_000
    assert result.fee_drops == 10
    assert result.created_account is True


def test_send_memo_payment_reports_no_creation_on_a_repeat(monkeypatch):
    from xrpl.wallet import Wallet

    sender = Wallet.create()
    _stub_send(monkeypatch, load_fixture("submit_existing_account_v2.json"))

    result = transport.send_memo_payment(
        sender.seed, "again", MAILBOX, amount_drops=1,
    )

    assert result.created_account is False
    assert result.amount_drops == 1


def test_send_memo_payment_raises_on_a_failed_engine_result(monkeypatch):
    """A tec* result is a failure even though the request itself succeeded."""
    from xrpl.wallet import Wallet

    sender = Wallet.create()
    failed = load_fixture("submit_created_account_v2.json")
    failed["meta"]["TransactionResult"] = "tecUNFUNDED_PAYMENT"
    _stub_send(monkeypatch, failed)

    with pytest.raises(transport.XRPLUnfundedAccount):
        transport.send_memo_payment(
            sender.seed, "note", MAILBOX, amount_drops=1,
        )


def test_send_memo_payment_maps_temredundant_to_a_readable_failure():
    """The live failure code, mapped to something a learner can act on."""
    err = transport._engine_failure("temREDUNDANT")

    assert isinstance(err, transport.XRPLTransactionFailed)
    assert "sender and destination are the same" in str(err)


# ---------------------------------------------------------------------------
# Balance / account_info
# ---------------------------------------------------------------------------


def test_get_balance_detail_parses_a_real_account_info_response(monkeypatch):
    fixture = load_fixture("account_info_v2.json")
    recorder = stub_client(monkeypatch, make_response(fixture))

    drops, ledger_index = transport.get_balance_detail(SENDER)

    assert drops == int(fixture["account_data"]["Balance"])
    assert ledger_index == fixture["ledger_index"]
    req = recorder.request_of("AccountInfo")
    assert req.api_version == 2
    assert req.ledger_index == "validated"


def test_get_balance_raises_account_not_found_on_a_real_error_response(monkeypatch):
    """`request()` returns status ERROR; it does not raise. Sniffing text cannot work."""
    fixture = load_fixture("account_info_not_found_v2.json")
    assert fixture["error"] == "actNotFound"
    stub_client(monkeypatch, make_response(fixture, successful=False))

    with pytest.raises(transport.XRPLAccountNotFound):
        transport.get_balance(fixture["account"])


def test_account_exists_is_false_for_a_real_act_not_found(monkeypatch):
    stub_client(
        monkeypatch,
        make_response(load_fixture("account_info_not_found_v2.json"), successful=False),
    )

    assert transport.account_exists("rGhost") is False


def test_account_exists_is_true_for_a_funded_account(monkeypatch):
    stub_client(monkeypatch, make_response(load_fixture("account_info_v2.json")))

    assert transport.account_exists(SENDER) is True


# ---------------------------------------------------------------------------
# Reserve base — read live, never hardcoded
# ---------------------------------------------------------------------------


def test_get_reserve_base_reads_the_live_value(monkeypatch):
    fixture = load_fixture("server_state_v2.json")
    recorder = stub_client(monkeypatch, make_response(fixture))

    assert transport.get_reserve_base() == (
        fixture["state"]["validated_ledger"]["reserve_base"]
    )
    assert recorder.request_of("ServerState").api_version == 2


def test_get_reserve_base_falls_back_when_the_request_fails(monkeypatch):
    stub_client(monkeypatch, make_response({"error": "noNetwork"}, successful=False))

    assert transport.get_reserve_base() == transport.DEFAULT_RESERVE_BASE_DROPS


def test_get_reserve_base_survives_a_response_without_the_field(monkeypatch):
    """Amendments move this value; a missing field must degrade, not crash."""
    fixture = load_fixture("server_state_v2.json")
    del fixture["state"]["validated_ledger"]["reserve_base"]
    fixture["state"]["validated_ledger"].pop("reserve_base_xrp", None)
    stub_client(monkeypatch, make_response(fixture))

    assert transport.get_reserve_base() == transport.DEFAULT_RESERVE_BASE_DROPS


# ---------------------------------------------------------------------------
# Failure classification — httpx does not subclass the builtins
# ---------------------------------------------------------------------------


def test_httpx_errors_are_classified_as_connection_failures():
    """`except (ConnectionError, OSError, TimeoutError)` catches none of these.

    xrpl-py 5.x runs on httpx and no httpx exception derives from those
    builtins, so the guard they used to be spelled with was dead code and
    XRPLConnectionError was unreachable.
    """
    httpx = pytest.importorskip("httpx")

    exc = httpx.ConnectError("nodename nor servname provided")
    assert not isinstance(exc, (ConnectionError, OSError, TimeoutError))
    assert transport._is_connection_failure(exc) is True


def test_a_wrapped_httpx_error_is_still_a_connection_failure():
    """xrpl-py re-raises through its own exception types; the cause chain matters."""
    httpx = pytest.importorskip("httpx")

    try:
        try:
            raise httpx.ConnectTimeout("timed out")
        except httpx.ConnectTimeout as inner:
            raise RuntimeError("request failed") from inner
    except RuntimeError as outer:
        assert transport._is_connection_failure(outer) is True


def test_a_ledger_rejection_is_not_a_connection_failure():
    assert transport._is_connection_failure(ValueError("temREDUNDANT")) is False


def test_lookup_tx_wraps_a_transport_error_as_connection_error(monkeypatch):
    httpx = pytest.importorskip("httpx")
    import xrpl.clients

    def exploding(url, *args, **kwargs):
        class Boom:
            def request(self, _req):
                raise httpx.ConnectError("no route to host")

        return Boom()

    monkeypatch.setattr(xrpl.clients, "JsonRpcClient", exploding)

    with pytest.raises(transport.XRPLConnectionError):
        transport.lookup_tx(TXID)
