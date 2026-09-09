"""Opt-in integration tests against the live XRPL Testnet.

Deselected by default; run with `pytest --run-network`. CI stays green with no
network, and nothing here is a dependency of the default suite.

They exist because a coordinator's FIRST live run found in one attempt what
months of green CI did not: the product could not complete its own lesson flow.
Testnet XRP is free and the faucet is public, so the only cost of this file is
wall-clock time — which is a much smaller price than shipping a tutorial whose
last three lessons cannot run.

If one of these fails while the rest of the suite is green, the recorded
fixtures in `tests/fixtures/` have drifted from the live wire format. Re-record
them; do not relax the assertions.
"""

from __future__ import annotations

import pytest

from tests.helpers import LOOKUP_KEYS, squash
from xrpl_camp import lessons, transport, wallet
from xrpl_camp.models import Session

pytestmark = pytest.mark.network


@pytest.fixture(scope="module")
def funded_wallet():
    """One faucet-funded wallet, reused across this module."""
    from xrpl.clients import JsonRpcClient
    from xrpl.wallet import generate_faucet_wallet

    client = JsonRpcClient(transport.get_rpc_url())
    return generate_faucet_wallet(client)


# ---------------------------------------------------------------------------
# The round trip
# ---------------------------------------------------------------------------


def test_a_real_payment_creates_the_mailbox_account(funded_wallet):
    """The strongest beat in the product, verified against a public ledger.

    This is also the exact call that used to raise `XRPLModelException` at
    construction and `temREDUNDANT` at the protocol: sender and destination
    were the same account.
    """
    mailbox_address, _ = wallet.create_mailbox()
    assert transport.account_exists(mailbox_address) is False

    reserve = transport.get_reserve_base()
    assert reserve > 0

    result = transport.send_memo_payment(
        funded_wallet.seed,
        "XRPLCAMP|LIVE|integration test",
        mailbox_address,
        amount_drops=reserve,
    )

    assert result.destination == mailbox_address
    assert result.created_account is True, "the payment did not create the account"
    assert result.fee_drops > 0
    assert len(result.txid) == 64
    assert transport.account_exists(mailbox_address) is True


def test_a_real_lookup_returns_the_full_contract(funded_wallet):
    """The recorded fixtures claim this shape. This is where the claim is checked."""
    mailbox_address, _ = wallet.create_mailbox()
    memo = "XRPLCAMP|LIVE|lookup contract"

    sent = transport.send_memo_payment(
        funded_wallet.seed, memo, mailbox_address,
        amount_drops=transport.get_reserve_base(),
    )
    tx = transport.lookup_tx(sent.txid)

    assert set(tx) == set(LOOKUP_KEYS)
    assert tx["found"] is True
    assert tx["account"] == funded_wallet.address
    assert tx["destination"] == mailbox_address
    assert tx["memo"] == memo, "the ledger did not read back what was written"
    assert tx["result"] == "tesSUCCESS"
    assert tx["validated"] is True
    assert int(tx["fee"]) > 0
    assert int(tx["ledger_index"]) > 0
    assert tx["close_time_iso"]


def test_a_hash_that_is_not_on_the_ledger_reports_not_found():
    tx = transport.lookup_tx("A" * 64)

    assert tx["found"] is False
    assert set(tx) == set(LOOKUP_KEYS)


def test_the_reserve_base_is_read_from_the_network_not_hardcoded():
    """It has been lowered by amendment before and will be again."""
    assert transport.get_reserve_base() > 0


def test_the_endpoint_reports_a_test_network():
    """The signing guard is only meaningful if network_id is readable."""
    assert transport.get_network_id() in transport.TESTNET_NETWORK_IDS


# ---------------------------------------------------------------------------
# The whole product, once, for real
# ---------------------------------------------------------------------------


def test_the_full_guided_flow_completes_against_the_live_testnet(tmp_path):
    """Six lessons, one process, a real certificate. Exit 0 or the product is broken."""
    with lessons.console.capture() as cap:
        code = lessons.run_guided_flow()
    output = squash(cap.get())

    assert code == 0, output
    assert "Record sealed" in output
    for claim in (claim for _, claim in lessons.COMPLETION_CLAIMS):
        assert claim in output

    cert = tmp_path / "xrpl_camp_certificate.json"
    pack = tmp_path / "xrpl_camp_proof_pack.json"
    assert cert.exists() and pack.exists()

    saved = Session.load()
    assert saved is not None
    assert all(saved.is_complete(n) for n in range(1, 7))

    # The transaction the pack attests is genuinely on the ledger.
    tx = transport.lookup_tx(saved.txids["lesson_4"])
    assert tx["found"] is True
    assert tx["result"] == "tesSUCCESS"
