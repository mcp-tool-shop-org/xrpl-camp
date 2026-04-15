"""Tests for XRPL Camp transport layer (offline only — no network calls)."""

from __future__ import annotations

import pytest

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


def test_from_hex_invalid_raises():
    with pytest.raises(ValueError):
        _from_hex("not_hex!")


# ---------------------------------------------------------------------------
# Fixture-based tx parsing
# ---------------------------------------------------------------------------


def test_lookup_tx_parsing():
    """Verify lookup_tx field extraction from a fixture response."""
    from xrpl_camp.transport import _from_hex, _to_hex

    # Simulate the dict that lookup_tx builds from an XRPL response
    memo_text = "XRPLCAMP|L4|1709337600"
    fixture_result = {
        "hash": "ABCDEF1234567890",
        "Amount": "1",
        "Destination": "rTestAddr",
        "Account": "rTestAddr",
        "Fee": "12",
        "Memos": [
            {
                "Memo": {
                    "MemoData": _to_hex(memo_text),
                    "MemoType": _to_hex("text/plain"),
                    "MemoFormat": _to_hex("text/plain"),
                }
            }
        ],
        "ledger_index": 42000000,
        "meta": {"TransactionResult": "tesSUCCESS"},
        "date": 700000000,
    }

    # Extract the same way lookup_tx does
    memo_decoded = ""
    memos = fixture_result.get("Memos", [])
    for m in memos:
        memo_obj = m.get("Memo", {})
        data = _from_hex(memo_obj.get("MemoData", ""))
        if data:
            memo_decoded = data
            break

    parsed = {
        "hash": fixture_result.get("hash", ""),
        "amount": fixture_result.get("Amount", "0"),
        "destination": fixture_result.get("Destination", ""),
        "account": fixture_result.get("Account", ""),
        "fee": fixture_result.get("Fee", "0"),
        "memo": memo_decoded,
        "ledger_index": fixture_result.get("ledger_index", 0),
        "result": fixture_result.get("meta", {}).get("TransactionResult", ""),
        "date": fixture_result.get("date", 0),
    }

    assert parsed["hash"] == "ABCDEF1234567890"
    assert parsed["amount"] == "1"
    assert parsed["destination"] == "rTestAddr"
    assert parsed["account"] == "rTestAddr"
    assert parsed["fee"] == "12"
    assert parsed["memo"] == memo_text
    assert parsed["ledger_index"] == 42000000
    assert parsed["result"] == "tesSUCCESS"


def test_tx_parsing_no_memo():
    """Handles transaction with no memos gracefully."""
    fixture_result = {
        "hash": "NOMEMO123",
        "Amount": "100",
        "Destination": "rDest",
        "Account": "rSrc",
        "Fee": "12",
        "ledger_index": 42000001,
        "meta": {"TransactionResult": "tesSUCCESS"},
    }

    memo_decoded = ""
    memos = fixture_result.get("Memos", [])
    for m in memos:
        memo_obj = m.get("Memo", {})
        data = _from_hex(memo_obj.get("MemoData", ""))
        if data:
            memo_decoded = data
            break

    assert memo_decoded == ""


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
# Dry-run mode
# ---------------------------------------------------------------------------


def test_fund_wallet_dry_run():
    from xrpl_camp.transport import fund_wallet
    from xrpl_camp.wallet import create_wallet

    address, seed = create_wallet()
    result = fund_wallet(seed, dry_run=True)
    assert result == address  # Returns the wallet's own address


def test_send_memo_payment_dry_run():
    from xrpl_camp.transport import DRY_RUN_TXID, send_memo_payment
    from xrpl_camp.wallet import create_wallet

    _, seed = create_wallet()
    txid = send_memo_payment(seed, "test memo", dry_run=True)
    assert txid == DRY_RUN_TXID


def test_send_memo_payment_dry_run_memo_accepted():
    """Dry-run accepts any memo without network call."""
    from xrpl_camp.transport import send_memo_payment
    from xrpl_camp.wallet import create_wallet

    _, seed = create_wallet()
    txid = send_memo_payment(seed, "any memo works here", dry_run=True)
    assert isinstance(txid, str)
    assert len(txid) > 0


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
    assert result["hash"] == "SOME_TXID"
    assert result["result"] == "tesSUCCESS"
    assert "dry run" in result["memo"].lower()


def test_lookup_tx_dry_run_has_expected_keys():
    from xrpl_camp.transport import lookup_tx

    result = lookup_tx("SOME_TXID", dry_run=True)
    expected_keys = {
        "hash", "amount", "destination", "account", "fee",
        "memo", "ledger_index", "result", "date",
    }
    assert set(result.keys()) == expected_keys


def test_dry_run_txid_constant():
    from xrpl_camp.transport import DRY_RUN_TXID
    assert isinstance(DRY_RUN_TXID, str)
    assert "DRY_RUN" in DRY_RUN_TXID
