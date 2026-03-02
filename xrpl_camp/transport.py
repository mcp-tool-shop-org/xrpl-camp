"""XRPL Testnet transport — fund, send, verify, balance."""

from __future__ import annotations

TESTNET_URL = "https://s.altnet.rippletest.net:51234/"
EXPLORER_URL = "https://testnet.xrpl.org/transactions/"


def _to_hex(text: str) -> str:
    """Encode text to hex for XRPL memo fields."""
    return text.encode("utf-8").hex()


def _from_hex(hex_str: str) -> str:
    """Decode hex to text from XRPL memo fields."""
    return bytes.fromhex(hex_str).decode("utf-8") if hex_str else ""


def fund_wallet(seed: str, url: str = TESTNET_URL) -> str:
    """Fund an existing wallet via testnet faucet. Returns funded address."""
    from xrpl.clients import JsonRpcClient
    from xrpl.wallet import Wallet, generate_faucet_wallet

    client = JsonRpcClient(url)
    wallet = Wallet.from_seed(seed)
    # Use faucet to fund — generate_faucet_wallet creates and funds
    # But we already have a wallet, so we use the faucet endpoint directly
    funded = generate_faucet_wallet(client, wallet=wallet)
    return funded.address


def get_balance(address: str, url: str = TESTNET_URL) -> int:
    """Get account balance in drops. Returns 0 if account not found."""
    from xrpl.clients import JsonRpcClient
    from xrpl.models import AccountInfo

    client = JsonRpcClient(url)
    try:
        response = client.request(AccountInfo(account=address))
        return int(response.result["account_data"]["Balance"])
    except Exception:
        return 0


def send_memo_payment(seed: str, memo: str, url: str = TESTNET_URL) -> str:
    """Self-payment (1 drop) with a memo. Returns transaction hash."""
    from xrpl.clients import JsonRpcClient
    from xrpl.models import Memo, Payment
    from xrpl.transaction import submit_and_wait
    from xrpl.wallet import Wallet

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
    tx_hash: str = response.result["hash"]
    return tx_hash


def lookup_tx(txid: str, url: str = TESTNET_URL) -> dict:
    """Look up a transaction and return parsed fields."""
    from xrpl.clients import JsonRpcClient
    from xrpl.models import Tx

    client = JsonRpcClient(url)
    response = client.request(Tx(transaction=txid))
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
