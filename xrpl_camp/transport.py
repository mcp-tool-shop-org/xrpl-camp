"""XRPL Testnet transport — fund, send, verify, balance."""

from __future__ import annotations

import os

TESTNET_URL = "https://s.altnet.rippletest.net:51234/"
EXPLORER_URL = "https://testnet.xrpl.org/transactions/"

DRY_RUN_TXID = "DRY_RUN_TX_0000000000000000"


# ---------------------------------------------------------------------------
# Typed transport exceptions
# ---------------------------------------------------------------------------


class XRPLConnectionError(Exception):
    """Could not connect to the RPC endpoint."""


class XRPLAccountNotFound(Exception):
    """Account does not exist on the ledger."""


class XRPLUnfundedAccount(Exception):
    """Account exists but is below the reserve requirement."""


class XRPLTransactionFailed(Exception):
    """Transaction submission or query failed."""


class XRPLMalformedResponse(Exception):
    """RPC response could not be parsed."""


def get_rpc_url() -> str:
    """Resolve RPC endpoint. Env var XRPL_CAMP_RPC_URL overrides default."""
    return os.environ.get("XRPL_CAMP_RPC_URL") or TESTNET_URL


def _to_hex(text: str) -> str:
    """Encode text to hex for XRPL memo fields."""
    return text.encode("utf-8").hex()


def _from_hex(hex_str: str) -> str:
    """Decode hex to text from XRPL memo fields."""
    return bytes.fromhex(hex_str).decode("utf-8") if hex_str else ""


def fund_wallet(seed: str, url: str | None = None, *, dry_run: bool = False) -> str:
    """Fund an existing wallet via testnet faucet. Returns funded address."""
    from xrpl.wallet import Wallet

    wallet = Wallet.from_seed(seed)

    if dry_run:
        return wallet.address

    from xrpl.clients import JsonRpcClient
    from xrpl.wallet import generate_faucet_wallet

    url = url or get_rpc_url()
    try:
        client = JsonRpcClient(url)
        funded = generate_faucet_wallet(client, wallet=wallet)
    except (ConnectionError, OSError, TimeoutError) as e:
        raise XRPLConnectionError(f"Could not connect to {url}: {e}") from e
    except Exception as e:
        raise XRPLTransactionFailed(f"Faucet request failed: {e}") from e
    return funded.address


def get_balance(address: str, url: str | None = None) -> int:
    """Get account balance in drops. Raises typed exceptions on failure."""
    from xrpl.clients import JsonRpcClient
    from xrpl.models import AccountInfo

    url = url or get_rpc_url()
    try:
        client = JsonRpcClient(url)
        response = client.request(AccountInfo(account=address))
    except (ConnectionError, OSError, TimeoutError) as e:
        raise XRPLConnectionError(f"Could not connect to {url}: {e}") from e
    except Exception as e:
        msg = str(e)
        if "actNotFound" in msg:
            raise XRPLAccountNotFound(address) from e
        raise XRPLTransactionFailed(msg) from e

    try:
        return int(response.result["account_data"]["Balance"])
    except (KeyError, ValueError, TypeError) as e:
        raise XRPLMalformedResponse(f"Unexpected balance response: {e}") from e


def send_memo_payment(
    seed: str, memo: str, url: str | None = None, *, dry_run: bool = False,
) -> str:
    """Self-payment (1 drop) with a memo. Returns transaction hash."""
    if dry_run:
        return DRY_RUN_TXID

    from xrpl.clients import JsonRpcClient
    from xrpl.models import Memo, Payment
    from xrpl.transaction import submit_and_wait
    from xrpl.wallet import Wallet

    url = url or get_rpc_url()
    try:
        client = JsonRpcClient(url)
        wallet = Wallet.from_seed(seed)

        tx_memo = Memo(
            memo_data=_to_hex(memo),
            memo_type=_to_hex("text/plain"),
            memo_format=_to_hex("text/plain"),
        )

        payment = Payment(
            account=wallet.address,
            destination=wallet.address,
            amount="1",  # 1 drop (smallest unit)
            memos=[tx_memo],
        )

        response = submit_and_wait(payment, client, wallet)
    except (ConnectionError, OSError, TimeoutError) as e:
        raise XRPLConnectionError(f"Could not connect to {url}: {e}") from e
    except Exception as e:
        raise XRPLTransactionFailed(f"Transaction failed: {e}") from e

    try:
        tx_hash: str = response.result["hash"]
    except (KeyError, TypeError) as e:
        raise XRPLMalformedResponse(f"Missing hash in response: {e}") from e
    return tx_hash


def lookup_tx(txid: str, url: str | None = None, *, dry_run: bool = False) -> dict:
    """Look up a transaction and return parsed fields."""
    if dry_run:
        return {
            "hash": txid,
            "amount": "1",
            "destination": "(dry run)",
            "account": "(dry run)",
            "fee": "12",
            "memo": "(dry run — no lookup performed)",
            "ledger_index": 0,
            "result": "tesSUCCESS",
            "date": 0,
        }

    from xrpl.clients import JsonRpcClient
    from xrpl.models import Tx

    url = url or get_rpc_url()
    try:
        client = JsonRpcClient(url)
        response = client.request(Tx(transaction=txid))
    except (ConnectionError, OSError, TimeoutError) as e:
        raise XRPLConnectionError(f"Could not connect to {url}: {e}") from e
    except Exception as e:
        raise XRPLTransactionFailed(f"Lookup failed: {e}") from e

    result = response.result

    # Decode memo
    memo_text = ""
    memos = result.get("Memos", [])
    for m in memos:
        memo_obj = m.get("Memo", {})
        data = _from_hex(memo_obj.get("MemoData", ""))
        if data:
            memo_text = data
            break

    return {
        "hash": result.get("hash", txid),
        "amount": result.get("Amount", "0"),
        "destination": result.get("Destination", ""),
        "account": result.get("Account", ""),
        "fee": result.get("Fee", "0"),
        "memo": memo_text,
        "ledger_index": result.get("ledger_index", 0),
        "result": result.get("meta", {}).get("TransactionResult", ""),
        "date": result.get("date", 0),
    }
