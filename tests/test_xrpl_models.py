"""The xrpl-py model contract — the class of test this suite did not have.

Before this file, `grep -rn "from xrpl" tests/` returned nothing. 139 tests
passed while the product's central transaction was structurally invalid, and a
green build across a three-major-version drift of xrpl-py (2.x to 5.1.0) proved
only that the resolver succeeded.

Everything here is pure CPU — no client, no network, no mock. The check that
would have caught the shipped defect on the day it was written is three lines:
constructing `Payment(account=X, destination=X)` raises at CONSTRUCTION time.
"""

from __future__ import annotations

import dataclasses
import re
from importlib.metadata import version
from pathlib import Path

import pytest
from xrpl.models import AccountInfo, Memo, Payment, ServerState, Tx
from xrpl.models.exceptions import XRPLModelException
from xrpl.wallet import Wallet

from xrpl_camp import transport

ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# The bug, pinned at the model layer
# ---------------------------------------------------------------------------


def test_payment_to_self_is_rejected_at_construction():
    """THE regression test.

    Lesson 4 built `Payment(account=w.address, destination=w.address)`. xrpl-py
    refuses to construct it and the protocol rejects it as temREDUNDANT, so
    lessons 4, 5 and 6 were unreachable for every user. No mock, no client, no
    network: the library says no before anything is sent.
    """
    w = Wallet.create()

    with pytest.raises(XRPLModelException) as exc:
        Payment(account=w.address, destination=w.address, amount="1")

    assert "same sender and destination" in str(exc.value)


def test_payment_to_self_with_memo_is_also_rejected():
    """A memo does not make a self-payment legal — that was the shipped call."""
    w = Wallet.create()
    memo = Memo(
        memo_data=transport._to_hex("hello ledger"),
        memo_type=transport._to_hex("text/plain"),
        memo_format=transport._to_hex("text/plain"),
    )

    with pytest.raises(XRPLModelException):
        Payment(
            account=w.address, destination=w.address, amount="1", memos=[memo],
        )


def test_shipping_payment_shape_is_valid():
    """The exact object transport.send_memo_payment builds, validated for real."""
    sender = Wallet.create()
    mailbox = Wallet.create()
    memo_text = "XRPLCAMP|L4|1709337600"

    memo = Memo(
        memo_data=transport._to_hex(memo_text),
        memo_type=transport._to_hex("text/plain"),
        memo_format=transport._to_hex("text/plain"),
    )
    payment = Payment(
        account=sender.address,
        destination=mailbox.address,
        amount=str(transport.DEFAULT_RESERVE_BASE_DROPS),
        memos=[memo],
    )

    assert payment.is_valid()
    assert payment._get_errors() == {}
    assert payment.destination != payment.account


def test_memo_survives_the_ledger_round_trip():
    """What `_to_hex` writes into a Memo is what `_from_hex` reads back out."""
    memo_text = "café — permanent 🌍"
    memo = Memo(
        memo_data=transport._to_hex(memo_text),
        memo_type=transport._to_hex("text/plain"),
        memo_format=transport._to_hex("text/plain"),
    )

    assert memo.is_valid()
    # Hex the ledger accepts: uppercase or lowercase, but always even-length.
    assert len(memo.memo_data) % 2 == 0
    assert transport._from_hex(memo.memo_data) == memo_text


# ---------------------------------------------------------------------------
# send_memo_payment refuses the invalid destination itself
# ---------------------------------------------------------------------------


def test_send_memo_payment_refuses_self_destination():
    """The guard fires before any client exists, in real mode."""
    address, seed = None, None
    w = Wallet.create()
    address, seed = w.address, w.seed

    with pytest.raises(ValueError) as exc:
        transport.send_memo_payment(seed, "note", address)

    assert address in str(exc.value)
    assert "temREDUNDANT" in str(exc.value)


def test_send_memo_payment_refuses_self_destination_in_dry_run():
    """Dry-run must not be a hole in the guard.

    If the check sat below the dry-run early return, the simulation would show
    a learner a successful self-payment that the real run cannot perform — the
    exact divergence that made a green suite compatible with a broken product.
    """
    w = Wallet.create()

    with pytest.raises(ValueError):
        transport.send_memo_payment(w.seed, "note", w.address, dry_run=True)


@pytest.mark.parametrize("destination", ["", "   ", None])
def test_send_memo_payment_requires_a_destination(destination):
    """A payment needs somewhere to go; `destination` is not optional."""
    w = Wallet.create()

    with pytest.raises(ValueError) as exc:
        transport.send_memo_payment(w.seed, "note", destination, dry_run=True)

    assert "destination" in str(exc.value).lower()


def test_send_memo_payment_rejects_oversized_memo():
    """The cap is on BYTES. 900 is accepted, 901 is not."""
    w = Wallet.create()
    dest = Wallet.create().address

    ok = transport.send_memo_payment(
        w.seed, "a" * transport.MAX_MEMO_BYTES, dest, dry_run=True,
    )
    assert ok.txid == transport.DRY_RUN_TXID

    with pytest.raises(transport.XRPLMemoTooLarge):
        transport.send_memo_payment(
            w.seed, "a" * (transport.MAX_MEMO_BYTES + 1), dest, dry_run=True,
        )


def test_memo_byte_cap_counts_bytes_not_characters():
    """A multi-byte memo shorter than the cap in characters can still exceed it."""
    w = Wallet.create()
    dest = Wallet.create().address
    # 250 four-byte emoji = 1000 bytes but only 250 characters.
    memo = "🌍" * 250
    assert len(memo) < transport.MAX_MEMO_BYTES
    assert len(memo.encode("utf-8")) > transport.MAX_MEMO_BYTES

    with pytest.raises(transport.XRPLMemoTooLarge):
        transport.send_memo_payment(w.seed, memo, dest, dry_run=True)


def test_invalid_seed_raises_typed_error_not_a_traceback():
    with pytest.raises(transport.XRPLInvalidSeed) as exc:
        transport.send_memo_payment("not-a-seed", "note", "rSomewhere", dry_run=True)

    assert "reset" in str(exc.value).lower()


# ---------------------------------------------------------------------------
# The API-version pin
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("model", [Tx, AccountInfo, ServerState])
def test_request_models_still_accept_api_version(model):
    """The pin only works if the field exists.

    `transport` passes `api_version=XRPL_API_VERSION` to all three of these.
    An upstream release that removed the field would make every request raise
    TypeError — and until this file existed, nothing in the suite imported
    these models, so that failure could only ever be found by a user.
    """
    names = [f.name for f in dataclasses.fields(model)]
    assert "api_version" in names


def test_tx_request_carries_the_pinned_version():
    req = Tx(transaction="A" * 64, api_version=transport.XRPL_API_VERSION)
    assert req.api_version == 2
    assert req.is_valid()


def test_account_info_request_carries_the_pinned_version():
    req = AccountInfo(
        account=Wallet.create().address,
        api_version=transport.XRPL_API_VERSION,
        ledger_index="validated",
    )
    assert req.api_version == 2
    assert req.ledger_index == "validated"
    assert req.is_valid()


# ---------------------------------------------------------------------------
# The dependency range
# ---------------------------------------------------------------------------


def _declared_range(dist: str) -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(rf'"{re.escape(dist)}([^"]*)"', text)
    assert match, f"{dist} is not pinned in pyproject.toml dependencies"
    return match.group(1)


def test_installed_xrpl_py_is_inside_the_declared_range():
    """Fail loudly on an untested major of the library the product IS.

    `xrpl-py>=2.0` with no ceiling resolved silently to 5.1.0 in CI, and because
    nothing imported xrpl, the resolver drift could not turn the build red no
    matter what it broke.
    """
    from packaging.requirements import Requirement
    from packaging.version import Version

    spec = Requirement("xrpl-py" + _declared_range("xrpl-py"))
    installed = Version(version("xrpl-py"))

    assert installed in spec.specifier, (
        f"installed xrpl-py {installed} is outside the declared range "
        f"{spec.specifier} — the transport has not been proven against it"
    )


def test_xrpl_py_pin_has_an_upper_bound():
    """An unbounded pin on the core dependency is the defect, not the symptom."""
    assert "<" in _declared_range("xrpl-py"), (
        "xrpl-py must carry an upper bound; an unbounded pin is what let a "
        "three-major-version drift reach production unnoticed"
    )
