"""XRPL Testnet transport — fund, send, verify, balance.

Response-shape contract
-----------------------
Every request model that accepts one is pinned to ``api_version=2``
(:data:`XRPL_API_VERSION`). The parser then knows the layout it is reading
instead of inheriting whatever the client and server happen to negotiate —
which is how the ``tx_json`` nesting break happened in the first place. The
parsers keep a top-level fallback so an older API-v1 endpoint still works.

Failure contract
----------------
``except (ConnectionError, OSError, TimeoutError)`` catches nothing that
xrpl-py 5.x actually raises: it runs on httpx, and no httpx exception derives
from those builtins. Network guards therefore classify with
:func:`_is_connection_failure`, which walks the ``__cause__`` chain and
recognises httpx/httpcore transport errors — so :class:`XRPLConnectionError`
is a live code path rather than decoration.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlsplit

TESTNET_URL = "https://s.altnet.rippletest.net:51234/"
EXPLORER_URL = "https://testnet.xrpl.org/transactions/"

DRY_RUN_TXID = "DRY_RUN_TX_0000000000000000"
DRY_RUN_BALANCE_DROPS = 100_000_000  # 100 XRP — what the Testnet faucet grants

#: rippled API version this module parses. One place to change it.
XRPL_API_VERSION = 2

#: Seconds between the Unix epoch (1970-01-01) and the Ripple epoch (2000-01-01).
RIPPLE_EPOCH_OFFSET = 946_684_800

#: Fallback only. The live value is read from ``server_state``; the XRPL has
#: lowered the base reserve by amendment before and will again.
DEFAULT_RESERVE_BASE_DROPS = 1_000_000

#: Measured live on Testnet: a 900-byte memo is accepted, 1000 bytes is
#: rejected with "The memo exceeds the maximum allowed size". The cap is on
#: BYTES, not characters — ~250 emoji already exceed it.
MAX_MEMO_BYTES = 900

#: Networks this tool is allowed to sign transactions against. 1 = Testnet,
#: 2 = Devnet. Mainnet is 0.
TESTNET_NETWORK_IDS = (1, 2)

#: Engine results that mean "not enough XRP", not "the network is broken".
_UNFUNDED_RESULTS = frozenset({
    "tecUNFUNDED_PAYMENT",
    "tecINSUFFICIENT_RESERVE",
    "tecNO_DST_INSUF_XRP",
    "terINSUF_FEE_B",
    "tecINSUF_RESERVE_LINE",
})

# Top-level module names whose exceptions mean "the wire failed", not "the
# ledger said no". httpx/httpcore are what xrpl-py 5.x raises through.
_CONNECTION_MODULES = frozenset({
    "httpx", "httpcore", "h11", "anyio", "aiohttp", "urllib3", "socket", "ssl",
})


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


class XRPLInvalidSeed(Exception):
    """The stored seed could not be decoded into a wallet."""


class XRPLMemoTooLarge(Exception):
    """The memo exceeds the ledger's maximum memo size."""


class XRPLWrongNetwork(Exception):
    """The configured endpoint is not a Testnet/Devnet node."""


# ---------------------------------------------------------------------------
# Endpoint resolution
# ---------------------------------------------------------------------------


def get_rpc_url() -> str:
    """Resolve RPC endpoint. Env var XRPL_CAMP_RPC_URL overrides default."""
    return os.environ.get("XRPL_CAMP_RPC_URL") or TESTNET_URL


def get_faucet_url() -> str | None:
    """Resolve the faucet endpoint, if the user pinned one.

    xrpl-py derives the faucet from the server's ``network_id`` and only knows
    the public altnet/devnet faucets, so a custom endpoint needs this.
    """
    return os.environ.get("XRPL_CAMP_FAUCET_URL") or None


def network_label_for_url(url: str | None = None) -> str:
    """Label the endpoint WITHOUT a network call, for wallet records/display."""
    raw = (url or get_rpc_url()).strip()
    low = raw.lower()
    if "altnet.rippletest.net" in low:
        return "testnet"
    if "devnet.rippletest.net" in low:
        return "devnet"
    if "sidechain-net" in low:
        return "sidechain"
    if any(h in low for h in ("s1.ripple.com", "s2.ripple.com", "xrplcluster.com")):
        return "mainnet"
    host = urlsplit(raw).hostname or raw
    return f"custom:{host}"


# ---------------------------------------------------------------------------
# Failure classification
# ---------------------------------------------------------------------------


def _is_connection_failure(exc: BaseException) -> bool:
    """True when `exc` (or anything it was raised from) is a transport failure.

    httpx exceptions do NOT subclass ConnectionError / OSError / TimeoutError,
    so the builtin tuple that used to guard these calls could never fire.
    """
    seen: set[int] = set()
    cur: BaseException | None = exc
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        if isinstance(cur, (ConnectionError, TimeoutError, OSError)):
            return True
        root = type(cur).__module__.split(".")[0]
        if root in _CONNECTION_MODULES:
            return True
        cur = cur.__cause__ or cur.__context__
    return False


def _network_failure(exc: Exception, url: str, prefix: str) -> Exception:
    """Map a raw client exception to the right typed transport exception."""
    if _is_connection_failure(exc):
        return XRPLConnectionError(f"Could not connect to {url}: {exc}")
    return XRPLTransactionFailed(f"{prefix}: {exc}" if prefix else str(exc))


def _engine_failure(engine_result: str, detail: str = "") -> Exception:
    """Map an XRPL engine result code to a typed exception."""
    suffix = f": {detail}" if detail else ""
    if engine_result == "tecNO_DST_INSUF_XRP":
        return XRPLUnfundedAccount(
            "The destination account does not exist yet, and the amount sent "
            "is below the base reserve needed to bring it into existence "
            "(tecNO_DST_INSUF_XRP).",
        )
    if engine_result in _UNFUNDED_RESULTS:
        return XRPLUnfundedAccount(
            "Not enough XRP in the sending account for this transaction "
            f"({engine_result}).",
        )
    if engine_result == "temREDUNDANT":
        return XRPLTransactionFailed(
            "The ledger rejected this payment as redundant (temREDUNDANT): "
            "sender and destination are the same account.",
        )
    return XRPLTransactionFailed(f"Transaction failed ({engine_result}){suffix}")


# ---------------------------------------------------------------------------
# Hex helpers
# ---------------------------------------------------------------------------


def _to_hex(text: str) -> str:
    """Encode text to hex for XRPL memo fields."""
    return text.encode("utf-8").hex()


def _from_hex(hex_str: str) -> str:
    """Decode hex to text from XRPL memo fields. NEVER raises.

    Memos on a public ledger are stranger-controlled: `xrpl-camp verify --tx`
    accepts any hash, and binary (non-UTF-8) memos are common. A decoder that
    raises would turn "found the transaction, memo is binary" into "lookup
    failed", which is a wrong diagnosis for a transaction that was found
    perfectly well.
    """
    if not hex_str:
        return ""
    cleaned = "".join(hex_str.split())
    if len(cleaned) % 2:
        cleaned = cleaned[:-1]
    try:
        raw = bytes.fromhex(cleaned)
    except (ValueError, TypeError):
        return "(unreadable memo)"
    if not raw:
        return ""
    return raw.decode("utf-8", errors="replace")


def _decode_memos(memos: object) -> str:
    """First decodable memo from an XRPL Memos array. Never raises."""
    if not isinstance(memos, list):
        return ""
    for entry in memos:
        if not isinstance(entry, dict):
            continue
        memo_obj = entry.get("Memo")
        if not isinstance(memo_obj, dict):
            continue
        data = _from_hex(str(memo_obj.get("MemoData", "") or ""))
        if data:
            return data
    return ""


def _tx_fields(result: dict) -> dict:
    """Transaction fields for the pinned API version, with a v1 fallback.

    Under rippled API v2 they live under ``tx_json``; under v1 they sit at the
    top level of ``result``.
    """
    nested = result.get("tx_json")
    if isinstance(nested, dict):
        return nested
    return result


def _meta(result: dict) -> dict:
    meta = result.get("meta")
    if not isinstance(meta, dict):
        meta = result.get("metaData")
    return meta if isinstance(meta, dict) else {}


def _wallet_from_seed(seed: str):
    """Decode a seed into a Wallet, or raise a typed, actionable error."""
    from xrpl.wallet import Wallet

    try:
        return Wallet.from_seed(seed)
    except Exception as e:
        raise XRPLInvalidSeed(
            "The stored seed in .xrpl-camp/wallet.json could not be read "
            f"({e}). Run `xrpl-camp reset` to start with a fresh wallet.",
        ) from e


# ---------------------------------------------------------------------------
# Ledger facts
# ---------------------------------------------------------------------------


def get_reserve_base(url: str | None = None) -> int:
    """Live base reserve in drops, from ``server_state``. NEVER hardcode this.

    Falls back to :data:`DEFAULT_RESERVE_BASE_DROPS` only when the request
    fails — the value has been lowered by amendment before and will be again.
    """
    from xrpl.clients import JsonRpcClient
    from xrpl.models import ServerState

    url = url or get_rpc_url()
    try:
        client = JsonRpcClient(url)
        response = client.request(ServerState(api_version=XRPL_API_VERSION))
    except Exception:
        return DEFAULT_RESERVE_BASE_DROPS

    if not response.is_successful():
        return DEFAULT_RESERVE_BASE_DROPS

    state = (response.result or {}).get("state")
    ledger = state.get("validated_ledger") if isinstance(state, dict) else None
    if not isinstance(ledger, dict):
        return DEFAULT_RESERVE_BASE_DROPS

    drops = ledger.get("reserve_base")
    if drops is None:
        xrp = ledger.get("reserve_base_xrp")
        if xrp is None:
            return DEFAULT_RESERVE_BASE_DROPS
        try:
            return int(float(xrp) * 1_000_000)
        except (TypeError, ValueError):
            return DEFAULT_RESERVE_BASE_DROPS
    try:
        return int(drops)
    except (TypeError, ValueError):
        return DEFAULT_RESERVE_BASE_DROPS


def get_network_id(url: str | None = None) -> int | None:
    """Network id of the configured endpoint, or None if it could not be read.

    rippled omits ``network_id`` when it is 0 (Mainnet), so a successful
    response with no id is reported as 0 — not as "unknown". Only a failed
    request returns None.
    """
    from xrpl.clients import JsonRpcClient
    from xrpl.models import ServerState

    url = url or get_rpc_url()
    try:
        client = JsonRpcClient(url)
        response = client.request(ServerState(api_version=XRPL_API_VERSION))
    except Exception:
        return None
    if not response.is_successful():
        return None
    state = (response.result or {}).get("state")
    if not isinstance(state, dict):
        return None
    try:
        return int(state.get("network_id", 0))
    except (TypeError, ValueError):
        return None


def assert_safe_network(url: str | None = None) -> None:
    """Refuse to SIGN against a non-Testnet endpoint.

    The default endpoint is the public Testnet, so this costs nothing on the
    normal path — the check runs only when the learner pointed
    ``XRPL_CAMP_RPC_URL`` somewhere else. Set ``XRPL_CAMP_ALLOW_ANY_NETWORK=1``
    to opt out.
    """
    if os.environ.get("XRPL_CAMP_ALLOW_ANY_NETWORK", "").strip():
        return
    if not os.environ.get("XRPL_CAMP_RPC_URL", "").strip():
        return
    url = url or get_rpc_url()
    network_id = get_network_id(url)
    if network_id is None:
        return  # endpoint unreachable; the call itself will report that
    if network_id not in TESTNET_NETWORK_IDS:
        raise XRPLWrongNetwork(
            f"{url} reports network_id {network_id}, which is not the XRPL "
            "Testnet (1) or Devnet (2). XRPL Camp refuses to sign "
            "transactions there. Unset XRPL_CAMP_RPC_URL, or set "
            "XRPL_CAMP_ALLOW_ANY_NETWORK=1 if you really mean it.",
        )


# ---------------------------------------------------------------------------
# Funding
# ---------------------------------------------------------------------------


def fund_wallet(seed: str, url: str | None = None, *, dry_run: bool = False) -> str:
    """Fund an existing wallet via testnet faucet. Returns funded address."""
    wallet = _wallet_from_seed(seed)

    if dry_run:
        return wallet.address

    from xrpl.clients import JsonRpcClient
    from xrpl.wallet import generate_faucet_wallet

    url = url or get_rpc_url()
    faucet_host = get_faucet_url()
    try:
        client = JsonRpcClient(url)
        if faucet_host:
            funded = generate_faucet_wallet(
                client, wallet=wallet, faucet_host=faucet_host,
            )
        else:
            funded = generate_faucet_wallet(client, wallet=wallet)
    except Exception as e:
        if _is_connection_failure(e):
            raise XRPLConnectionError(f"Could not connect to {url}: {e}") from e
        if type(e).__name__ == "XRPLFaucetException":
            raise XRPLTransactionFailed(
                f"{url} has no known faucet ({e}). Set XRPL_CAMP_FAUCET_URL to "
                "your network's faucet, or unset XRPL_CAMP_RPC_URL to use the "
                "public Testnet.",
            ) from e
        raise XRPLTransactionFailed(f"Faucet request failed: {e}") from e
    return funded.address


# ---------------------------------------------------------------------------
# Balance
# ---------------------------------------------------------------------------


def get_balance_detail(
    address: str, url: str | None = None, *, dry_run: bool = False,
) -> tuple[int, int]:
    """Validated balance in drops, plus the ledger index it was read from.

    Reads ``ledger_index="validated"``: the figure a learner sees is then the
    figure the explorer will confirm, which is the whole point of the lesson.
    """
    if dry_run:
        return DRY_RUN_BALANCE_DROPS, 0

    from xrpl.clients import JsonRpcClient
    from xrpl.models import AccountInfo

    url = url or get_rpc_url()
    try:
        client = JsonRpcClient(url)
        response = client.request(AccountInfo(
            account=address,
            api_version=XRPL_API_VERSION,
            ledger_index="validated",
        ))
    except Exception as e:
        raise _network_failure(e, url, "Balance check failed") from e

    result = response.result or {}

    # client.request() does NOT raise for ledger-level errors — it returns a
    # Response with status ERROR. Sniffing the exception text could never work.
    if not response.is_successful():
        error = str(result.get("error", ""))
        if error == "actNotFound":
            raise XRPLAccountNotFound(address)
        raise XRPLTransactionFailed(
            result.get("error_message") or error or "Unknown balance error",
        )

    try:
        drops = int(result["account_data"]["Balance"])
    except (KeyError, ValueError, TypeError) as e:
        raise XRPLMalformedResponse(f"Unexpected balance response: {e}") from e

    try:
        ledger_index = int(result.get("ledger_index", 0) or 0)
    except (TypeError, ValueError):
        ledger_index = 0
    return drops, ledger_index


def get_balance(
    address: str, url: str | None = None, *, dry_run: bool = False,
) -> int:
    """Get account balance in drops. Raises typed exceptions on failure."""
    drops, _ = get_balance_detail(address, url, dry_run=dry_run)
    return drops


def account_exists(
    address: str, url: str | None = None, *, dry_run: bool = False,
) -> bool:
    """True if `address` is funded into existence on the validated ledger."""
    if dry_run:
        return True
    try:
        get_balance(address, url)
    except XRPLAccountNotFound:
        return False
    return True


# ---------------------------------------------------------------------------
# Sending
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SendResult:
    """Outcome of a memo payment."""

    txid: str
    destination: str
    amount_drops: int
    fee_drops: int
    created_account: bool


def _created_account(meta: dict, destination: str) -> bool:
    """True iff this transaction brought `destination` into existence."""
    nodes = meta.get("AffectedNodes")
    if not isinstance(nodes, list):
        return False
    for node in nodes:
        if not isinstance(node, dict):
            continue
        created = node.get("CreatedNode")
        if not isinstance(created, dict):
            continue
        if created.get("LedgerEntryType") != "AccountRoot":
            continue
        new_fields = created.get("NewFields")
        if isinstance(new_fields, dict) and new_fields.get("Account") == destination:
            return True
    return False


def send_memo_payment(
    seed: str,
    memo: str,
    destination: str,
    url: str | None = None,
    *,
    amount_drops: int | None = None,
    dry_run: bool = False,
) -> SendResult:
    """Send a real payment carrying a memo. Returns a :class:`SendResult`.

    `destination` is REQUIRED and must not be the sender. The old code built
    ``Payment(account=X, destination=X)``, which xrpl-py refuses to construct
    (``XRPLModelException``) and the ledger rejects as ``temREDUNDANT`` — so
    lesson 4 could never run, and lessons 5 and 6 sat unreachable behind it.
    The ValueError below makes that impossible to reintroduce silently.

    `amount_drops` defaults to whatever the destination needs: the base
    reserve when the account does not exist yet (the payment then *creates* it,
    which is the strongest beat in the product), otherwise 1 drop.
    """
    wallet = _wallet_from_seed(seed)
    sender = wallet.address

    if not destination or not str(destination).strip():
        raise ValueError(
            "send_memo_payment() requires a destination address. A payment "
            "needs somewhere to go.",
        )
    destination = str(destination).strip()
    if destination == sender:
        raise ValueError(
            "A payment cannot be sent to its own sender "
            f"({sender}). The XRPL rejects that as temREDUNDANT. Send to the "
            "learner's mailbox account instead.",
        )

    memo_bytes = len(memo.encode("utf-8"))
    if memo_bytes > MAX_MEMO_BYTES:
        raise XRPLMemoTooLarge(
            f"Memo is {memo_bytes} bytes; the maximum is {MAX_MEMO_BYTES}. "
            "Note the limit is on bytes, not characters — accented letters "
            "and emoji cost several bytes each.",
        )

    if dry_run:
        return SendResult(
            txid=DRY_RUN_TXID,
            destination=destination,
            amount_drops=amount_drops if amount_drops is not None else 1,
            fee_drops=10,
            created_account=False,
        )

    from xrpl.clients import JsonRpcClient
    from xrpl.models import Memo, Payment
    from xrpl.transaction import submit_and_wait

    url = url or get_rpc_url()
    assert_safe_network(url)

    if amount_drops is None:
        # A 1-drop payment to a non-existent account is rejected with
        # tecNO_DST_INSUF_XRP *and burns the fee*. Pay the reserve instead and
        # the payment creates the account.
        amount_drops = (
            1 if account_exists(destination, url) else get_reserve_base(url)
        )
    if amount_drops < 1:
        raise ValueError(f"amount_drops must be at least 1 drop, got {amount_drops}")

    try:
        client = JsonRpcClient(url)
        tx_memo = Memo(
            memo_data=_to_hex(memo),
            memo_type=_to_hex("text/plain"),
            memo_format=_to_hex("text/plain"),
        )
        payment = Payment(
            account=sender,
            destination=destination,
            amount=str(amount_drops),
            memos=[tx_memo],
        )
        response = submit_and_wait(payment, client, wallet)
    except Exception as e:
        if _is_connection_failure(e):
            raise XRPLConnectionError(f"Could not connect to {url}: {e}") from e
        text = str(e)
        for code in _UNFUNDED_RESULTS:
            if code in text:
                raise _engine_failure(code, text) from e
        if "memo exceeds the maximum" in text.lower():
            raise XRPLMemoTooLarge(
                f"The ledger rejected the memo as too large ({memo_bytes} bytes).",
            ) from e
        raise XRPLTransactionFailed(f"Transaction failed: {e}") from e

    result = response.result or {}
    meta = _meta(result)
    engine_result = str(meta.get("TransactionResult", "") or "")
    if engine_result and engine_result != "tesSUCCESS":
        raise _engine_failure(engine_result)

    try:
        tx_hash = str(result["hash"])
    except (KeyError, TypeError) as e:
        raise XRPLMalformedResponse(f"Missing hash in response: {e}") from e

    fields = _tx_fields(result)
    try:
        fee_drops = int(fields.get("Fee", 0) or 0)
    except (TypeError, ValueError):
        fee_drops = 0

    return SendResult(
        txid=tx_hash,
        destination=destination,
        amount_drops=amount_drops,
        fee_drops=fee_drops,
        created_account=_created_account(meta, destination),
    )


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


def _empty_lookup(txid: str) -> dict:
    """The not-found shape. Same keys as a hit, so callers never KeyError."""
    return {
        "found": False,
        "hash": txid,
        "account": "",
        "destination": "",
        "amount": "0",
        "delivered": "",
        "fee": "0",
        "memo": "",
        "ledger_index": 0,
        "result": "",
        "validated": False,
        "close_time_iso": "",
        "date": 0,
    }


def lookup_tx(txid: str, url: str | None = None, *, dry_run: bool = False) -> dict:
    """Look up a transaction and return parsed fields.

    Callers MUST branch on ``["found"]``. ``client.request()`` does not raise
    for a missing transaction — it returns a Response whose ``result`` is
    ``{"error": "txnNotFound", ...}``. Parsing that as a hit is what made
    ``xrpl-camp verify --tx <any 64 hex chars>`` print "Independently
    verified" for a hash that is not on the ledger.
    """
    if dry_run:
        return {
            "found": True,
            "hash": txid,
            "account": "(dry run)",
            "destination": "(dry run)",
            "amount": "1",
            "delivered": "1",
            "fee": "10",
            "memo": "(dry run — no lookup performed)",
            "ledger_index": 0,
            "result": "tesSUCCESS",
            "validated": True,
            "close_time_iso": "(dry run)",
            "date": 0,
        }

    from xrpl.clients import JsonRpcClient
    from xrpl.models import Tx

    url = url or get_rpc_url()
    try:
        client = JsonRpcClient(url)
        response = client.request(Tx(transaction=txid, api_version=XRPL_API_VERSION))
    except Exception as e:
        raise _network_failure(e, url, "Lookup failed") from e

    result = response.result or {}

    if not response.is_successful():
        error = str(result.get("error", ""))
        if error in ("txnNotFound", "notFound"):
            return _empty_lookup(txid)
        raise XRPLTransactionFailed(
            result.get("error_message") or error or "Unknown lookup error",
        )

    try:
        fields = _tx_fields(result)
        meta = _meta(result)

        amount = fields.get("DeliverMax", fields.get("Amount", "0"))
        delivered = meta.get("delivered_amount", "")

        raw_date = fields.get("date", result.get("date", 0))
        try:
            unix_date = int(raw_date) + RIPPLE_EPOCH_OFFSET if raw_date else 0
        except (TypeError, ValueError):
            unix_date = 0

        return {
            "found": True,
            "hash": str(result.get("hash", txid)),
            "account": str(fields.get("Account", "") or ""),
            "destination": str(fields.get("Destination", "") or ""),
            "amount": str(amount if amount is not None else "0"),
            "delivered": str(delivered if delivered is not None else ""),
            "fee": str(fields.get("Fee", "0") or "0"),
            # Memo decoding lives INSIDE the guard and cannot raise: a binary
            # memo on a stranger's transaction must not read as "lookup failed".
            "memo": _decode_memos(fields.get("Memos", result.get("Memos", []))),
            "ledger_index": int(result.get("ledger_index", 0) or 0),
            "result": str(meta.get("TransactionResult", "") or ""),
            "validated": bool(result.get("validated", False)),
            "close_time_iso": str(result.get("close_time_iso", "") or ""),
            "date": unix_date,
        }
    except (AttributeError, TypeError, ValueError) as e:
        raise XRPLMalformedResponse(f"Unexpected transaction response: {e}") from e
