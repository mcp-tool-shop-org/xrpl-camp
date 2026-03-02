"""Tests for XRPL Camp structured error handling."""

from __future__ import annotations

from xrpl_camp.errors import (
    CampError,
    connection_error,
    faucet_error,
    lookup_error,
    send_error,
)


def test_camp_error_user_message():
    err = CampError(code="TEST", message="Something broke", hint="Try again")
    msg = err.user_message()
    assert "[TEST]" in msg
    assert "Something broke" in msg
    assert "Try again" in msg


def test_camp_error_user_message_no_hint():
    err = CampError(code="TEST", message="Something broke", hint="")
    msg = err.user_message()
    assert "[TEST]" in msg
    assert "Hint" not in msg


def test_faucet_error_defaults():
    err = faucet_error()
    assert err.code == "NET_FAUCET"
    assert "faucet" in err.hint.lower()
    assert err.retryable is True


def test_faucet_error_with_detail():
    err = faucet_error("timeout after 30s")
    assert "timeout after 30s" in err.message


def test_send_error_code():
    err = send_error()
    assert err.code == "NET_SEND"
    assert err.retryable is True


def test_lookup_error_retryable():
    err = lookup_error("not found")
    assert err.retryable is True
    assert "not found" in err.message


def test_connection_error_includes_url():
    err = connection_error("https://example.com:51234/")
    assert "example.com" in err.message
    assert "XRPL_CAMP_RPC_URL" in err.hint
