"""Unit tests for the transport layer's pure helpers and short-circuits.

Scope note: everything here is offline and covers ONLY the hex helpers, the
constants, endpoint resolution, and the dry-run short-circuits. The real
network paths — the parsers, the Payment construction, the failure
classification — are pinned in `test_transport_contract.py` against recorded
wire responses, and the xrpl-py model contract in `test_xrpl_models.py`.

The split matters. Every send/fund/lookup test in this file used to pass
`dry_run=True`, which returns before any of the code the product depends on,
and there were no tests anywhere else. The suite was measuring its own early
returns.
"""

from __future__ import annotations

from tests.helpers import LOOKUP_KEYS
from xrpl_camp.transport import _from_hex, _to_hex

# ---------------------------------------------------------------------------
# Hex encoding / decoding
# ---------------------------------------------------------------------------


def test_to_hex_ascii():
    assert _to_hex("hello") == "68656c6c6f"


def test_to_hex_empty():
    assert _to_hex("") == ""


def test_to_hex_unicode():
    result = _to_hex("café")
    assert isinstance(result, str)
    # Verify roundtrip
    assert _from_hex(result) == "café"


def test_from_hex_ascii():
    assert _from_hex("68656c6c6f") == "hello"


def test_from_hex_empty():
    assert _from_hex("") == ""


def test_roundtrip_memo():
    """Memo encoding roundtrips correctly."""
    memo = "XRPLCAMP|L4|1709337600"
    assert _from_hex(_to_hex(memo)) == memo


def test_roundtrip_text_plain():
    assert _from_hex(_to_hex("text/plain")) == "text/plain"


def test_to_hex_special_chars():
    text = "Hello, World! 🌍"
    assert _from_hex(_to_hex(text)) == text


def test_from_hex_invalid_does_not_raise():
    """Bad hex degrades to a label. It must NOT raise.

    Memos are stranger-controlled: `xrpl-camp verify --tx <hash>` accepts any
    transaction on a public ledger, and binary memos are common. A decoder that
    raised turned "found it, the memo is not text" into "lookup failed", which
    is a wrong diagnosis for a transaction that was found perfectly well.
    """
    assert _from_hex("not_hex!") == "(unreadable memo)"


def test_from_hex_non_utf8_bytes_are_replaced():
    """0xFF is valid hex and invalid UTF-8. It decodes to the replacement char."""
    assert _from_hex("FF") == "�"


def test_from_hex_odd_length_is_tolerated():
    """A truncated memo loses its last nibble rather than the whole lookup."""
    assert _from_hex("68656c6c6") == "hell"


def test_from_hex_whitespace_is_ignored():
    assert _from_hex("68 65 6c 6c 6f") == "hello"


# ---------------------------------------------------------------------------
# NOTE: the two fixture-based "parsing" tests that used to live here were
# deleted, not moved. They hand-copied lookup_tx's body into the test and
# asserted against their own copy, so deleting lookup_tx entirely left them
# green — and the shape they declared as truth (Account/Destination/Fee/Memos
# at the top level, Amount not DeliverMax) was the API-v1 layout, which is
# precisely the bug that blanked lesson 5's details table under API v2.
# Their replacements drive the REAL parser over a REAL recorded response:
# see tests/test_transport_contract.py.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


def test_testnet_url():
    from xrpl_camp.transport import TESTNET_URL
    assert "testnet" in TESTNET_URL or "altnet" in TESTNET_URL


def test_explorer_url():
    from xrpl_camp.transport import EXPLORER_URL
    assert "testnet" in EXPLORER_URL
    assert EXPLORER_URL.endswith("/")


# ---------------------------------------------------------------------------
# get_rpc_url + env var override
# ---------------------------------------------------------------------------


def test_get_rpc_url_default():
    from xrpl_camp.transport import TESTNET_URL, get_rpc_url
    assert get_rpc_url() == TESTNET_URL


def test_get_rpc_url_env_override(monkeypatch):
    from xrpl_camp.transport import get_rpc_url
    monkeypatch.setenv("XRPL_CAMP_RPC_URL", "https://custom.endpoint:51234/")
    assert get_rpc_url() == "https://custom.endpoint:51234/"


def test_get_rpc_url_env_empty_falls_back(monkeypatch):
    from xrpl_camp.transport import TESTNET_URL, get_rpc_url
    monkeypatch.setenv("XRPL_CAMP_RPC_URL", "")
    assert get_rpc_url() == TESTNET_URL


# ---------------------------------------------------------------------------
# Dry-run short-circuits
#
# These are named for what they actually prove: that the early return fires
# before any client is constructed. They are NOT evidence that the real send,
# fund or lookup paths work — those live in test_transport_contract.py.
# ---------------------------------------------------------------------------


def test_fund_wallet_dry_run_short_circuits():
    """Dry-run fund echoes the wallet's own address and touches no faucet."""
    from xrpl_camp.transport import fund_wallet
    from xrpl_camp.wallet import create_wallet

    address, seed = create_wallet()
    result = fund_wallet(seed, dry_run=True)
    assert result == address  # Returns the wallet's own address


def test_send_memo_payment_dry_run_short_circuits():
    """Dry-run send returns a complete SendResult without a network call."""
    from xrpl_camp.transport import DRY_RUN_TXID, SendResult, send_memo_payment
    from xrpl_camp.wallet import create_wallet

    _, seed = create_wallet()
    destination, _ = create_wallet()

    result = send_memo_payment(seed, "test memo", destination, dry_run=True)

    assert isinstance(result, SendResult)
    assert result.txid == DRY_RUN_TXID
    assert result.destination == destination
    assert result.amount_drops >= 1
    assert result.fee_drops >= 0
    assert result.created_account is False


def test_send_memo_payment_dry_run_honours_amount():
    """The simulated result reports the amount the caller asked for."""
    from xrpl_camp.transport import send_memo_payment
    from xrpl_camp.wallet import create_wallet

    _, seed = create_wallet()
    destination, _ = create_wallet()

    result = send_memo_payment(
        seed, "any memo works here", destination,
        amount_drops=1_000_000, dry_run=True,
    )
    assert result.amount_drops == 1_000_000


# ---------------------------------------------------------------------------
# Typed transport exceptions
# ---------------------------------------------------------------------------


def test_typed_exceptions_exist():
    """All typed transport exceptions are importable."""
    from xrpl_camp.transport import (
        XRPLAccountNotFound,
        XRPLConnectionError,
        XRPLMalformedResponse,
        XRPLTransactionFailed,
        XRPLUnfundedAccount,
    )

    assert issubclass(XRPLConnectionError, Exception)
    assert issubclass(XRPLAccountNotFound, Exception)
    assert issubclass(XRPLUnfundedAccount, Exception)
    assert issubclass(XRPLTransactionFailed, Exception)
    assert issubclass(XRPLMalformedResponse, Exception)


def test_exceptions_are_distinct():
    """Each exception type is a distinct class."""
    from xrpl_camp.transport import (
        XRPLAccountNotFound,
        XRPLConnectionError,
        XRPLMalformedResponse,
        XRPLTransactionFailed,
        XRPLUnfundedAccount,
    )

    classes = {
        XRPLConnectionError, XRPLAccountNotFound, XRPLUnfundedAccount,
        XRPLTransactionFailed, XRPLMalformedResponse,
    }
    assert len(classes) == 5


def test_connection_error_message():
    """XRPLConnectionError preserves message."""
    from xrpl_camp.transport import XRPLConnectionError

    err = XRPLConnectionError("timeout")
    assert "timeout" in str(err)


def test_account_not_found_message():
    """XRPLAccountNotFound preserves address."""
    from xrpl_camp.transport import XRPLAccountNotFound

    err = XRPLAccountNotFound("rTestAddr")
    assert "rTestAddr" in str(err)


def test_lookup_tx_dry_run():
    from xrpl_camp.transport import lookup_tx

    result = lookup_tx("SOME_TXID", dry_run=True)
    assert result["found"] is True
    assert result["hash"] == "SOME_TXID"
    assert result["result"] == "tesSUCCESS"
    assert result["validated"] is True
    assert "dry run" in result["memo"].lower()


def test_lookup_tx_dry_run_has_expected_keys():
    """The simulated return carries the SHARED key contract.

    `LOOKUP_KEYS` is asserted against the real parser's output over a recorded
    response too (test_transport_contract.py). Pinning the key set in only one
    of the two places is how the simulated and real paths were free to drift —
    and they had: the simulation showed a populated details table while the
    real run showed blanks.
    """
    from xrpl_camp.transport import lookup_tx

    result = lookup_tx("SOME_TXID", dry_run=True)
    assert set(result.keys()) == set(LOOKUP_KEYS)


def test_dry_run_txid_constant():
    from xrpl_camp.transport import DRY_RUN_TXID
    assert isinstance(DRY_RUN_TXID, str)
    assert "DRY_RUN" in DRY_RUN_TXID
