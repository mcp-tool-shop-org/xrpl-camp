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
Every exception this module raises derives from :class:`XRPLTransportError`,
which is a :class:`~xrpl_camp.errors.CampFailure` and therefore carries a
structured :class:`~xrpl_camp.errors.CampError` on ``.error`` — a stable
``code``, a beginner-facing ``message``, an actionable ``hint``, and a
``retryable`` flag that is *true only when running the command again can
actually succeed*.

That last part is load-bearing. These exceptions used to be bare
``Exception`` subclasses carrying prose, so the layer above could only
type-switch, branched on two of them, and rendered the other six as
"Transaction submission failed … This one is safe to run again." The tool's
most safety-critical refusal (wrong network) and its most dangerous ambiguity
(a lapsed ``LastLedgerSequence``, where the payment may already be on the
ledger) both rendered as "safe to retry". Re-running the second one sends a
SECOND real payment. Nothing in this module may claim ``retryable=True``
unless a repeat is genuinely free.

``except (ConnectionError, OSError, TimeoutError)`` catches nothing that
xrpl-py 5.x actually raises: it runs on httpx, and no httpx exception derives
from those builtins. Network guards therefore classify with
:func:`_is_connection_failure`, which walks the ``__cause__`` chain and
recognises httpx/httpcore transport errors — but explicitly EXCLUDES
``httpx.HTTPStatusError``, because a 429 from the faucet means the server
answered, not that the wire failed.
"""

from __future__ import annotations

import logging
import os
import random
import re
import time
from dataclasses import dataclass
from urllib.parse import urlsplit

from xrpl_camp.errors import EXIT_RUNTIME, EXIT_USER, CampError, CampFailure

TESTNET_URL = "https://s.altnet.rippletest.net:51234/"
EXPLORER_URL = "https://testnet.xrpl.org/transactions/"

#: Explorer bases per network label. ``network_label_for_url`` picks the key;
#: an endpoint we cannot map gets NO link rather than a wrong one, because the
#: link exists to back the claim "you don't have to trust this tool".
_EXPLORER_BASES = {
    "testnet": "https://testnet.xrpl.org/transactions/",
    "devnet": "https://devnet.xrpl.org/transactions/",
    "mainnet": "https://livenet.xrpl.org/transactions/",
}

DRY_RUN_TXID = "DRY_RUN_TX_0000000000000000"
DRY_RUN_BALANCE_DROPS = 100_000_000  # 100 XRP — what the Testnet faucet grants

#: rippled API version this module parses. One place to change it.
XRPL_API_VERSION = 2

#: Seconds between the Unix epoch (1970-01-01) and the Ripple epoch (2000-01-01).
RIPPLE_EPOCH_OFFSET = 946_684_800

#: Fallback only. The live value is read from ``server_state``; the XRPL has
#: lowered the base reserve by amendment before and will again.
DEFAULT_RESERVE_BASE_DROPS = 1_000_000

#: Fallback only, same reasoning as the base reserve above.
DEFAULT_RESERVE_INC_DROPS = 200_000

#: Measured live on Testnet: a 900-byte memo is accepted, 1000 bytes is
#: rejected with "The memo exceeds the maximum allowed size". The cap is on
#: BYTES, not characters — ~250 emoji already exceed it.
MAX_MEMO_BYTES = 900

#: Networks this tool is allowed to sign transactions against. 1 = Testnet,
#: 2 = Devnet. Mainnet is 0.
TESTNET_NETWORK_IDS = (1, 2)

#: xrpl-py's own inherited request timeout. It has no timeout parameter on
#: ``SyncClient.request``, so every call against a dead host takes exactly
#: this long. Documented so "it hung for ten seconds" is an expected number.
REQUEST_TIMEOUT_SECONDS = 10

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

#: Public mainnet endpoints that do not live under ``ripple.com``. Matched
#: against the parsed HOST, never against the URL string — the old substring
#: match labelled ``https://evil.example.com/?u=s1.ripple.com`` as "mainnet".
_MAINNET_HOSTS = frozenset({"xrplcluster.com", "xrpl.ws", "xrpl.link"})

#: An XRPL engine result code, extracted from a message. Pulling the code out
#: once beats scanning the same string for five literals: it recognises every
#: ``tec``/``tef``/``tel``/``tem``/``ter`` result, not the handful we listed.
_ENGINE_CODE_RE = re.compile(r"\b(t(?:ec|ef|el|em|er|es)[A-Z][A-Za-z_]*)\b")

#: The two numbers in xrpl-py's LastLedgerSequence-lapse message.
_LAPSE_RE = re.compile(
    r"ledger sequence\s+(\d+)\s+is greater than LastLedgerSequence\s+(\d+)",
    re.IGNORECASE,
)

#: HTTP statuses where waiting and trying again is the right advice.
_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})

#: Total seconds a retry policy may add to one call. A faucet that asks for
#: 45 seconds is better answered with the clear "wait about a minute" message
#: than with 90 seconds of silence: the healthy fund already costs 8-10s with
#: no output, so silence is the one thing a learner cannot tell from a hang.
MAX_RETRY_WAIT_SECONDS = 20.0

#: Headroom left for the network fee in the pre-send affordability check.
#: The fee is set during autofill, after this check runs, so the check keeps
#: a small allowance rather than approving a send that the ledger will then
#: reject for want of ten drops — burning the fee to say so.
FEE_HEADROOM_DROPS = 100

logger = logging.getLogger("xrpl_camp.transport")

#: Indirected so a test can make backoff instantaneous without monkeypatching
#: ``time`` globally.
_sleep = time.sleep


# ---------------------------------------------------------------------------
# Optional dependency symbols
# ---------------------------------------------------------------------------
#
# These are imported by SYMBOL, not matched by name, so a dependency that
# renames a class turns into a loud ImportError at module load instead of a
# silently dead branch. The guards keep the module importable if a future
# xrpl-py drops one — the classification degrades, it does not crash.

try:  # pragma: no cover - exercised by the contract test, not by branching
    from httpx import HTTPStatusError as _HTTPStatusError
except ImportError:  # pragma: no cover
    _HTTPStatusError = ()  # type: ignore[assignment]

try:  # pragma: no cover
    from xrpl.asyncio.wallet.wallet_generation import (
        XRPLFaucetException as _XRPLFaucetException,
    )
except ImportError:  # pragma: no cover
    _XRPLFaucetException = ()  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Typed transport exceptions
# ---------------------------------------------------------------------------


class XRPLTransportError(CampFailure):
    """Base for every transport failure. Always carries a ``CampError``.

    The contract the rendering layer depends on:

    * ``exc.error`` is a :class:`~xrpl_camp.errors.CampError` with
      ``code`` / ``message`` / ``hint`` / ``retryable`` / ``detail``;
    * ``exc.error.retryable`` is TRUE only when re-running the command is
      free — never for a signed submission whose outcome is unknown;
    * ``str(exc)`` remains the rendered user-facing message, so an instance
      that escapes every handler still ends in something actionable.

    Constructing with a plain string keeps the old call shape working; the
    class attributes below supply the structure.
    """

    #: Stable code a bug report can quote.
    error_code = "NET_UNKNOWN"
    #: What to try next. Never mentions Python or XRPL internals.
    default_hint = "Run 'xrpl-camp self-check' to see what the tool can reach."
    #: Whether running the same command again can succeed.
    default_retryable = False
    default_exit_code = EXIT_RUNTIME

    def __init__(
        self,
        message: object,
        *,
        code: str | None = None,
        hint: str | None = None,
        retryable: bool | None = None,
        detail: str = "",
        exit_code: int | None = None,
    ) -> None:
        if isinstance(message, CampError):
            error = message
        else:
            cls = type(self)
            error = CampError(
                code=code or cls.error_code,
                message=str(message),
                hint=cls.default_hint if hint is None else hint,
                retryable=cls.default_retryable if retryable is None else retryable,
                detail=detail,
                exit_code=cls.default_exit_code if exit_code is None else exit_code,
            )
        super().__init__(error)


class XRPLConnectionError(XRPLTransportError):
    """Could not connect to the RPC endpoint. The request never landed."""

    error_code = "NET_CONNECT"
    default_hint = (
        "Check your internet connection, or set XRPL_CAMP_RPC_URL to a "
        "different endpoint."
    )
    default_retryable = True


class XRPLAccountNotFound(XRPLTransportError):
    """Account does not exist on the ledger."""

    error_code = "NET_ACCOUNT_NOT_FOUND"
    default_hint = (
        "Run 'xrpl-camp fund' first — an account has to be funded to exist. "
        "If it worked before, the Testnet may have been reset: "
        "'xrpl-camp reset' starts a fresh wallet."
    )
    default_retryable = False


class XRPLUnfundedAccount(XRPLTransportError):
    """Account exists but is below the reserve requirement."""

    error_code = "NET_UNFUNDED"
    default_hint = (
        "Run 'xrpl-camp fund' to top the account up, then try again. "
        "Sending less than you hold in reserve is not possible."
    )
    default_retryable = False


class XRPLTransactionFailed(XRPLTransportError):
    """Transaction submission or query failed, and the ledger said why.

    Not retryable by default: a ledger that rejected a transaction will
    reject the identical transaction again, and a caller that wants to offer
    a retry must say so explicitly.
    """

    error_code = "NET_SEND"
    default_hint = (
        "The ledger rejected this one. Nothing further was written; read the "
        "reason above before trying a different value."
    )
    default_retryable = False


class XRPLMalformedResponse(XRPLTransportError):
    """RPC response could not be parsed."""

    error_code = "NET_MALFORMED"
    default_hint = (
        "The endpoint answered in a shape this version does not understand. "
        "Unset XRPL_CAMP_RPC_URL to use the public Testnet, or upgrade "
        "xrpl-camp."
    )
    default_retryable = False


class XRPLInvalidSeed(XRPLTransportError):
    """The stored seed could not be decoded into a wallet."""

    error_code = "NET_SEED"
    default_hint = (
        "Run 'xrpl-camp reset' to start with a fresh wallet. Nothing on the "
        "ledger is affected."
    )
    default_retryable = False
    default_exit_code = EXIT_USER


class XRPLMemoTooLarge(XRPLTransportError):
    """The memo exceeds the ledger's maximum memo size."""

    error_code = "NET_MEMO_TOO_LARGE"
    default_hint = "Shorten the message and send again. Nothing was written."
    default_retryable = False
    default_exit_code = EXIT_USER


class XRPLWrongNetwork(XRPLTransportError):
    """The configured endpoint is not a Testnet/Devnet node.

    Never retryable: the same command against the same endpoint will refuse
    identically, and the only thing that unblocks the learner is changing an
    environment variable, which the message names.
    """

    error_code = "NET_WRONG_NETWORK"
    default_hint = (
        "Unset XRPL_CAMP_RPC_URL to use the public Testnet, or set "
        "XRPL_CAMP_ALLOW_ANY_ENDPOINT=1 if you truly mean to spend against "
        "that network."
    )
    default_retryable = False
    default_exit_code = EXIT_USER


class XRPLFaucetBusy(XRPLTransportError):
    """The faucet answered, but could not fund right now (rate limit / delay).

    The one genuinely retryable failure in this module. A 30-person workshop
    sharing one Testnet faucet meets this constantly, and it used to arrive
    as "could not connect", naming the RPC URL that had connected fine.
    """

    error_code = "NET_FAUCET_BUSY"
    default_hint = (
        "The shared Testnet faucet is rate limited or still working. Wait "
        "about a minute, then run 'xrpl-camp fund' again — your internet is "
        "fine and changing endpoints will not help."
    )
    default_retryable = True

    def __init__(self, message: object, *, retry_after: float = 0.0, **kw) -> None:
        super().__init__(message, **kw)
        #: Seconds the faucet asked us to wait, 0 when it did not say.
        self.retry_after = retry_after


class XRPLFaucetError(XRPLTransportError):
    """The faucet answered with an error that waiting will not fix."""

    error_code = "NET_FAUCET"
    default_hint = (
        "Set XRPL_CAMP_FAUCET_URL to your network's faucet, or unset "
        "XRPL_CAMP_RPC_URL to use the public Testnet."
    )
    default_retryable = False


class XRPLSubmissionUnresolved(XRPLTransportError):
    """A transaction was signed and submitted, and its outcome is UNKNOWN.

    The dangerous case, and the reason this class exists separately from
    :class:`XRPLTransactionFailed`. When the ``LastLedgerSequence`` window
    lapses, xrpl-py stops waiting — but the transaction may still have been
    included in the final ledger. It carries the hash so the outcome can be
    looked up instead of guessed, and it is NEVER retryable: re-running would
    send a second real payment in the lesson whose whole point is that ledger
    writes are permanent.
    """

    error_code = "NET_SUBMIT_UNRESOLVED"
    default_hint = (
        "Do NOT send again — that would write a second payment. Look the "
        "hash up first with 'xrpl-camp verify --tx <hash>'."
    )
    default_retryable = False

    def __init__(
        self,
        message: object,
        *,
        txid: str = "",
        last_ledger: int = 0,
        **kw,
    ) -> None:
        super().__init__(message, **kw)
        #: Hash of the signed transaction. Empty only when signing itself failed.
        self.txid = txid
        #: The LastLedgerSequence the transaction was signed with.
        self.last_ledger = last_ledger


# ---------------------------------------------------------------------------
# Endpoint resolution
# ---------------------------------------------------------------------------


def _flag(name: str) -> bool:
    """True when env var `name` is set to something that means "yes"."""
    return os.environ.get(name, "").strip().lower() not in ("", "0", "false", "no")


def get_rpc_url() -> str:
    """Resolve RPC endpoint. Env var XRPL_CAMP_RPC_URL overrides default."""
    return os.environ.get("XRPL_CAMP_RPC_URL") or TESTNET_URL


def get_faucet_url() -> str | None:
    """Resolve the faucet endpoint, if the user pinned one.

    xrpl-py derives the faucet from the server's ``network_id`` and only knows
    the public altnet/devnet faucets, so a custom endpoint needs this.
    """
    return os.environ.get("XRPL_CAMP_FAUCET_URL") or None


def faucet_label(url: str | None = None) -> str:
    """The faucet a fund request will actually hit, for error messages.

    A faucet failure must never name the RPC url. They are different servers,
    and telling a learner whose faucet is rate limited to check their
    connection to the RPC endpoint is advice that cannot help.
    """
    pinned = get_faucet_url()
    if pinned:
        return pinned
    label = network_label_for_url(url)
    if label == "devnet":
        return "https://faucet.devnet.rippletest.net/accounts"
    if label == "testnet":
        return "https://faucet.altnet.rippletest.net/accounts"
    return "the network's faucet"


def network_label_for_url(url: str | None = None) -> str:
    """Label the endpoint WITHOUT a network call, for wallet records/display.

    Matches on the parsed HOST with suffix rules. The old version matched
    substrings anywhere in the URL string, so ``https://evil.example.com/
    ?u=s1.ripple.com`` was labelled "mainnet" (the match was inside the query
    string) while ``https://xrpl.ws/`` — a real public mainnet endpoint — was
    labelled "custom". This is the field wallet.json records as the network a
    seed belongs to, and SECURITY.md's "never use a Testnet seed on Mainnet"
    guidance depends on that record being right.
    """
    raw = (url or get_rpc_url()).strip()
    host = (urlsplit(raw).hostname or "").lower().rstrip(".")
    if not host:
        # No scheme means urlsplit finds no host; fall back to the raw text so
        # the label is still traceable rather than silently empty.
        return f"custom:{raw}" if raw else "unknown"

    if host == "altnet.rippletest.net" or host.endswith(".altnet.rippletest.net"):
        return "testnet"
    if host == "devnet.rippletest.net" or host.endswith(".devnet.rippletest.net"):
        return "devnet"
    if "sidechain-net" in host:
        return "sidechain"
    if host == "rippletest.net" or host.endswith(".rippletest.net"):
        return "testnet"
    if host in _MAINNET_HOSTS or host.endswith(".ripple.com") or host == "ripple.com":
        return "mainnet"
    return f"custom:{host}"


def explorer_url_for(txid: str, url: str | None = None) -> str:
    """Explorer link for `txid` on the endpoint's network, or "".

    Returns an EMPTY STRING for an endpoint we cannot map, so the caller
    prints nothing rather than a link that resolves to "transaction does not
    exist". The link is there to back the claim "you don't have to trust this
    tool — verify it yourself"; a dead link undermines exactly that claim, and
    the proof pack then seals it.
    """
    if not txid:
        return ""
    base = _EXPLORER_BASES.get(network_label_for_url(url), "")
    return f"{base}{txid}" if base else ""


# ---------------------------------------------------------------------------
# Failure classification
# ---------------------------------------------------------------------------


def _causes(exc: BaseException):
    """Walk `exc` and everything it was raised from, once each."""
    seen: set[int] = set()
    cur: BaseException | None = exc
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        yield cur
        cur = cur.__cause__ or cur.__context__


def http_status_error(exc: BaseException):
    """The HTTP *status* error in `exc`'s cause chain, or None.

    A status error means the server ANSWERED — with 429, 500, whatever. That
    is categorically not "could not connect", and conflating the two is what
    told a rate-limited workshop to check their internet.
    """
    for cur in _causes(exc):
        if _HTTPStatusError and isinstance(cur, _HTTPStatusError):
            return cur
        response = getattr(cur, "response", None)
        if response is not None and getattr(response, "status_code", None) is not None:
            return cur
    return None


def _status_code(exc: BaseException) -> int:
    """HTTP status carried by `exc`, or 0."""
    found = http_status_error(exc)
    if found is None:
        return 0
    try:
        return int(found.response.status_code)
    except (AttributeError, TypeError, ValueError):
        return 0


def _retry_after(exc: BaseException) -> float:
    """``Retry-After`` seconds from the response on `exc`, or 0.0."""
    found = http_status_error(exc)
    if found is None:
        return 0.0
    try:
        raw = found.response.headers.get("Retry-After", "")
    except (AttributeError, TypeError):
        return 0.0
    try:
        return max(0.0, float(str(raw).strip()))
    except (TypeError, ValueError):
        return 0.0


def _is_connection_failure(exc: BaseException) -> bool:
    """True when `exc` (or anything it was raised from) is a transport failure.

    httpx exceptions do NOT subclass ConnectionError / OSError / TimeoutError,
    so the builtin tuple that used to guard these calls could never fire.

    An HTTP *status* error is excluded even though it comes from httpx: the
    connection succeeded and the server replied. Classifying a 429 as "could
    not connect" is how a rate-limited faucet was reported as an outage, with
    the wrong URL named.
    """
    if http_status_error(exc) is not None:
        return False
    for cur in _causes(exc):
        if isinstance(cur, (ConnectionError, TimeoutError, OSError)):
            return True
        root = type(cur).__module__.split(".")[0]
        if root in _CONNECTION_MODULES:
            return True
    return False


def _network_failure(exc: Exception, url: str, prefix: str) -> Exception:
    """Map a raw client exception to the right typed transport exception."""
    detail = f"{type(exc).__name__}: {exc}"
    status = _status_code(exc)
    if status:
        return XRPLTransactionFailed(
            f"{url} answered with HTTP {status}."
            + (f" {prefix}." if prefix else ""),
            retryable=status in _RETRYABLE_STATUS,
            detail=detail,
        )
    if _is_connection_failure(exc):
        return XRPLConnectionError(f"Could not connect to {url}: {exc}", detail=detail)
    return XRPLTransactionFailed(
        f"{prefix}: {exc}" if prefix else str(exc), detail=detail,
    )


def _engine_code(text: str) -> str:
    """Extract an XRPL engine result code from `text`, or "".

    One structured extraction beats scanning for five literals: it recognises
    every ``tec``/``tef``/``tel``/``tem``/``ter`` result the ledger can
    return, so a code we never listed still classifies as a ledger rejection
    rather than falling through to a generic failure.
    """
    match = _ENGINE_CODE_RE.search(text or "")
    return match.group(1) if match else ""


def _engine_failure(engine_result: str, detail: str = "") -> Exception:
    """Map an XRPL engine result code to a typed exception."""
    suffix = f": {detail}" if detail else ""
    if engine_result == "tecNO_DST_INSUF_XRP":
        return XRPLUnfundedAccount(
            "The destination account does not exist yet, and the amount sent "
            "is below the base reserve needed to bring it into existence "
            "(tecNO_DST_INSUF_XRP).",
            detail=detail,
        )
    if engine_result in _UNFUNDED_RESULTS:
        return XRPLUnfundedAccount(
            "Not enough XRP in the sending account for this transaction "
            f"({engine_result}).",
            detail=detail,
        )
    if engine_result == "temREDUNDANT":
        return XRPLTransactionFailed(
            "The ledger rejected this payment as redundant (temREDUNDANT): "
            "sender and destination are the same account.",
            detail=detail,
        )
    return XRPLTransactionFailed(
        f"Transaction failed ({engine_result}){suffix}", detail=detail,
    )


# ---------------------------------------------------------------------------
# Retry
# ---------------------------------------------------------------------------


def _retry_delay(attempt: int, retry_after: float) -> float:
    """Backoff for `attempt` (1-based), honouring a server ``Retry-After``."""
    if retry_after > 0:
        return retry_after
    return (2.0 ** (attempt - 1)) + random.uniform(0.0, 0.5)


def _with_retries(
    call,
    *,
    attempts: int = 3,
    on_retry=None,
    what: str = "request",
    budget: float = MAX_RETRY_WAIT_SECONDS,
):
    """Run `call`, retrying ONLY failures where waiting can actually help.

    Retryable: :class:`XRPLFaucetBusy` and HTTP 429/5xx — the server answered
    and asked us to come back. NOT retryable: connection failures (the caller
    decides), engine results, and anything at all touching a signed
    submission.

    The total wait is bounded by `budget`. A faucet asking for 45 seconds is
    told to the learner ("wait about a minute") rather than absorbed in
    silence: a healthy fund already takes 8-10s with no output, so a long
    silent retry is indistinguishable from a hang. Set ``XRPL_CAMP_NO_RETRY=1``
    to disable retries entirely.
    """
    if _flag("XRPL_CAMP_NO_RETRY"):
        attempts = 1
    last: Exception | None = None
    spent = 0.0
    for attempt in range(1, max(1, attempts) + 1):
        try:
            return call()
        except XRPLFaucetBusy as exc:
            last = exc
            wait = _retry_delay(attempt, getattr(exc, "retry_after", 0.0))
        except XRPLTransactionFailed as exc:
            if not exc.error.retryable:
                raise
            last = exc
            wait = _retry_delay(attempt, 0.0)
        if attempt >= attempts or spent + wait > budget:
            break
        logger.debug(
            "%s failed (%s); retrying in %.1fs (%d of %d)",
            what, last, wait, attempt + 1, attempts,
        )
        if on_retry is not None:
            try:
                on_retry(attempt, attempts, wait, last)
            except Exception:
                # Progress reporting must never be the thing that fails a call.
                logger.debug("retry callback raised", exc_info=True)
        _sleep(wait)
        spent += wait
    raise last  # type: ignore[misc]


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
            detail=f"{type(e).__name__}: {e}",
        ) from e


# ---------------------------------------------------------------------------
# Ledger facts
# ---------------------------------------------------------------------------


def _server_state(url: str) -> dict | None:
    """``server_state``'s ``state`` object, or None when it could not be read.

    Returning None rather than a default is the point: two readers used to
    swallow every exception and hand back a guess that was indistinguishable
    from a live read, and a safety gate built on one of them failed OPEN.
    """
    from xrpl.clients import JsonRpcClient
    from xrpl.models import ServerState

    started = time.monotonic()
    try:
        client = JsonRpcClient(url)
        response = client.request(ServerState(api_version=XRPL_API_VERSION))
    except Exception as e:
        # Callers decide what a failed read means; this one only reports it.
        logger.debug(
            "server_state %s failed after %.2fs: %s: %s",
            url, time.monotonic() - started, type(e).__name__, e,
        )
        return None
    logger.debug("server_state %s in %.2fs", url, time.monotonic() - started)
    if not response.is_successful():
        return None
    state = (response.result or {}).get("state")
    return state if isinstance(state, dict) else None


def _int_or_none(value: object) -> int | None:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def get_reserve_detail(url: str | None = None) -> tuple[int, int, bool]:
    """``(base_drops, increment_drops, is_live)`` from ``server_state``.

    ``is_live`` is False when the endpoint could not be read and the constants
    were used instead. The caller can then say "could not read the live
    reserve, using 1 XRP" rather than silently paying a guess — the base
    reserve has been lowered by amendment before and will be again.
    """
    state = _server_state(url or get_rpc_url())
    ledger = state.get("validated_ledger") if isinstance(state, dict) else None
    if not isinstance(ledger, dict):
        return DEFAULT_RESERVE_BASE_DROPS, DEFAULT_RESERVE_INC_DROPS, False

    base = _int_or_none(ledger.get("reserve_base"))
    if base is None:
        xrp = ledger.get("reserve_base_xrp")
        try:
            base = int(float(xrp) * 1_000_000) if xrp is not None else None
        except (TypeError, ValueError):
            base = None
    if base is None:
        return DEFAULT_RESERVE_BASE_DROPS, DEFAULT_RESERVE_INC_DROPS, False

    inc = _int_or_none(ledger.get("reserve_inc"))
    if inc is None:
        xrp = ledger.get("reserve_inc_xrp")
        try:
            inc = int(float(xrp) * 1_000_000) if xrp is not None else None
        except (TypeError, ValueError):
            inc = None
    return base, (DEFAULT_RESERVE_INC_DROPS if inc is None else inc), True


def get_reserve_base(url: str | None = None) -> int:
    """Live base reserve in drops, from ``server_state``. NEVER hardcode this.

    Falls back to :data:`DEFAULT_RESERVE_BASE_DROPS` only when the request
    fails. Use :func:`get_reserve_detail` when you need to know WHICH of those
    happened — a silent fallback that happens to equal the live value today is
    latent, not fixed.
    """
    base, _, _ = get_reserve_detail(url)
    return base


def get_network_id(url: str | None = None) -> int | None:
    """Network id of the configured endpoint, or None if it could not be read.

    rippled omits ``network_id`` when it is 0 (Mainnet), so a successful
    response with no id is reported as 0 — not as "unknown". Only a failed
    request returns None.
    """
    state = _server_state(url or get_rpc_url())
    if state is None:
        return None
    return _int_or_none(state.get("network_id", 0))


def earliest_complete_ledger(url: str | None = None) -> int | None:
    """Lowest ledger index the endpoint still has, from ``complete_ledgers``.

    This is how "the Testnet was reset and your history is gone" becomes a
    sentence the tool can say instead of a silent empty result.
    """
    state = _server_state(url or get_rpc_url())
    if state is None:
        return None
    raw = str(state.get("complete_ledgers", "") or "").strip()
    if not raw or raw.lower() in ("empty", "none"):
        return None
    lowest: int | None = None
    for span in raw.split(","):
        head = span.strip().split("-")[0].strip()
        value = _int_or_none(head)
        if value is not None and (lowest is None or value < lowest):
            lowest = value
    return lowest


def assert_safe_network(url: str | None = None) -> None:
    """Refuse to SIGN against an endpoint that is not a known test network.

    The default endpoint is the public Testnet, so this costs nothing on the
    normal path — the check runs only when the learner pointed
    ``XRPL_CAMP_RPC_URL`` somewhere else.

    It fails CLOSED. An endpoint whose ``network_id`` cannot be read used to
    pass this gate, so a flaky custom RPC got the learner *past* the check
    that exists precisely because the endpoint is not the default one.

    Either escape hatch opens it: ``XRPL_CAMP_ALLOW_ANY_ENDPOINT`` (the one
    the other gate names, and the one the docs carry) or the older
    ``XRPL_CAMP_ALLOW_ANY_NETWORK``. Two similarly named variables for two
    gates meant a workshop host who did exactly what the first gate told them
    hit a second gate whose name they could not discover.
    """
    if _flag("XRPL_CAMP_ALLOW_ANY_NETWORK") or _flag("XRPL_CAMP_ALLOW_ANY_ENDPOINT"):
        return
    if not os.environ.get("XRPL_CAMP_RPC_URL", "").strip():
        return
    url = url or get_rpc_url()
    network_id = get_network_id(url)
    if network_id is None:
        raise XRPLWrongNetwork(
            f"Could not confirm which network {url} is, so nothing was "
            "signed. XRPL Camp only signs against the XRPL Testnet (1) or "
            "Devnet (2), and an endpoint it cannot read could be anything.",
            detail=f"server_state unreadable at {url}",
        )
    if network_id not in TESTNET_NETWORK_IDS:
        raise XRPLWrongNetwork(
            f"{url} reports network_id {network_id}, which is not the XRPL "
            "Testnet (1) or Devnet (2). XRPL Camp refuses to sign "
            "transactions there. Unset XRPL_CAMP_RPC_URL, or set "
            "XRPL_CAMP_ALLOW_ANY_ENDPOINT=1 if you really mean it.",
            detail=f"network_id={network_id} at {url}",
        )


# ---------------------------------------------------------------------------
# Funding
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FundResult:
    """Outcome of a funding request."""

    address: str
    balance_drops: int
    already_funded: bool


def _faucet_failure(exc: Exception, url: str) -> Exception:
    """Classify a faucet failure. NEVER names the RPC url."""
    faucet = faucet_label(url)
    detail = f"{type(exc).__name__}: {exc}"
    status = _status_code(exc)

    if status:
        if status in _RETRYABLE_STATUS:
            after = _retry_after(exc)
            waited = (
                f" It asked us to wait {after:.0f}s."
                if after
                else " Wait about a minute and try again."
            )
            return XRPLFaucetBusy(
                f"The Testnet faucet at {faucet} is busy (HTTP {status})."
                + waited,
                retry_after=after,
                detail=detail,
            )
        return XRPLFaucetError(
            f"The Testnet faucet at {faucet} refused the request "
            f"(HTTP {status}).",
            detail=detail,
        )

    if _XRPLFaucetException and isinstance(exc, _XRPLFaucetException):
        text = str(exc)
        if "after waiting" in text.lower():
            # xrpl-py polled for 40 seconds and gave up. The faucet TOOK the
            # request; the account may well appear a moment later. The old
            # message claimed the network "has no known faucet" and told the
            # learner to unset a variable they had never set.
            return XRPLFaucetBusy(
                f"The faucet at {faucet} accepted the request but has not "
                "funded the account yet. It often lands a few seconds later "
                "— run 'xrpl-camp status' in a minute before asking again.",
                detail=detail,
            )
        return XRPLFaucetError(
            f"{url} has no faucet this tool knows how to reach ({exc}).",
            detail=detail,
        )

    if _is_connection_failure(exc):
        return XRPLConnectionError(
            f"Could not reach the Testnet faucet at {faucet}: {exc}",
            detail=detail,
        )
    return XRPLFaucetError(f"Faucet request failed: {exc}", detail=detail)


def fund_wallet_detail(
    seed: str,
    url: str | None = None,
    *,
    dry_run: bool = False,
    force: bool = False,
    on_retry=None,
) -> FundResult:
    """Fund a wallet via the Testnet faucet, reporting what actually happened.

    An account that is already funded short-circuits: the grant is a shared,
    rate-limited resource, and after a misdiagnosed 429 or a 40-second silence
    re-running `xrpl-camp fund` is the obvious thing to do — which quietly
    takes a second grant another learner in the room is waiting on. Pass
    ``force=True`` to top up deliberately.
    """
    wallet = _wallet_from_seed(seed)

    if dry_run:
        return FundResult(wallet.address, DRY_RUN_BALANCE_DROPS, already_funded=False)

    url = url or get_rpc_url()

    if not force:
        try:
            existing = get_balance(wallet.address, url)
        except XRPLAccountNotFound:
            existing = 0
        except XRPLTransportError as exc:
            logger.debug("pre-fund balance check failed: %s", exc)
            existing = 0
        if existing > 0:
            logger.debug("%s already holds %d drops; skipping faucet",
                         wallet.address, existing)
            return FundResult(wallet.address, existing, already_funded=True)

    from xrpl.clients import JsonRpcClient
    from xrpl.wallet import generate_faucet_wallet

    faucet_host = get_faucet_url()

    def attempt() -> str:
        started = time.monotonic()
        try:
            client = JsonRpcClient(url)
            if faucet_host:
                funded = generate_faucet_wallet(
                    client, wallet=wallet, faucet_host=faucet_host,
                )
            else:
                funded = generate_faucet_wallet(client, wallet=wallet)
        except Exception as e:
            logger.debug(
                "faucet %s failed after %.2fs: %s: %s",
                faucet_label(url), time.monotonic() - started, type(e).__name__, e,
            )
            raise _faucet_failure(e, url) from e
        logger.debug("faucet %s funded in %.2fs", faucet_label(url),
                     time.monotonic() - started)
        return funded.address

    address = _with_retries(attempt, on_retry=on_retry, what="faucet request")

    try:
        balance = get_balance(address, url)
    except XRPLTransportError:
        balance = 0
    return FundResult(address, balance, already_funded=False)


def fund_wallet(seed: str, url: str | None = None, *, dry_run: bool = False) -> str:
    """Fund an existing wallet via testnet faucet. Returns funded address."""
    return fund_wallet_detail(seed, url, dry_run=dry_run).address


# ---------------------------------------------------------------------------
# Balance
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AccountSummary:
    """What ``account_info`` tells us about an account, parsed."""

    drops: int
    ledger_index: int
    owner_count: int


def get_account_summary(
    address: str, url: str | None = None, *, dry_run: bool = False,
) -> AccountSummary:
    """Validated balance, ledger index and owner count for `address`."""
    if dry_run:
        return AccountSummary(DRY_RUN_BALANCE_DROPS, 0, 0)

    from xrpl.clients import JsonRpcClient
    from xrpl.models import AccountInfo

    url = url or get_rpc_url()
    started = time.monotonic()
    try:
        client = JsonRpcClient(url)
        response = client.request(AccountInfo(
            account=address,
            api_version=XRPL_API_VERSION,
            ledger_index="validated",
        ))
    except Exception as e:
        logger.debug(
            "account_info %s failed after %.2fs: %s: %s",
            url, time.monotonic() - started, type(e).__name__, e,
        )
        raise _network_failure(e, url, "Balance check failed") from e
    logger.debug("account_info %s in %.2fs", url, time.monotonic() - started)

    result = response.result or {}

    # client.request() does NOT raise for ledger-level errors — it returns a
    # Response with status ERROR. Sniffing the exception text could never work.
    if not response.is_successful():
        error = str(result.get("error", ""))
        if error == "actNotFound":
            raise XRPLAccountNotFound(
                f"{address} does not exist on the ledger at {url}. Either it "
                "has never been funded, or the Testnet was reset since you "
                "last used it — a reset wipes every account and transaction.",
                detail=f"actNotFound for {address} at {url}",
            )
        raise XRPLTransactionFailed(
            result.get("error_message") or error or "Unknown balance error",
            detail=f"account_info error {error} at {url}",
        )

    try:
        account_data = result["account_data"]
        drops = int(account_data["Balance"])
    except (KeyError, ValueError, TypeError) as e:
        raise XRPLMalformedResponse(
            f"Unexpected balance response: {e}", detail=f"{type(e).__name__}: {e}",
        ) from e

    owner_count = _int_or_none(account_data.get("OwnerCount", 0)) or 0
    ledger_index = _int_or_none(result.get("ledger_index", 0)) or 0
    return AccountSummary(drops, ledger_index, owner_count)


def get_balance_detail(
    address: str, url: str | None = None, *, dry_run: bool = False,
) -> tuple[int, int]:
    """Validated balance in drops, plus the ledger index it was read from.

    Reads ``ledger_index="validated"``: the figure a learner sees is then the
    figure the explorer will confirm, which is the whole point of the lesson.
    """
    summary = get_account_summary(address, url, dry_run=dry_run)
    return summary.drops, summary.ledger_index


def get_balance(
    address: str, url: str | None = None, *, dry_run: bool = False,
) -> int:
    """Get account balance in drops. Raises typed exceptions on failure."""
    drops, _ = get_balance_detail(address, url, dry_run=dry_run)
    return drops


def get_spendable_drops(
    address: str, url: str | None = None, *, fee_drops: int = 0,
) -> tuple[int, bool]:
    """``(spendable_drops, reserves_are_live)`` — what `address` can actually send.

    ``account_data.Balance`` includes the locked reserve, so reporting it as
    "your balance" and then submitting an unaffordable payment costs a real
    transaction and a burned fee before the learner is told anything — and the
    ledger's own message gives no number, which is the only fact that unblocks
    them.
    """
    url = url or get_rpc_url()
    summary = get_account_summary(address, url)
    base, inc, live = get_reserve_detail(url)
    locked = base + (summary.owner_count * inc)
    return max(0, summary.drops - locked - max(0, fee_drops)), live


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
    ledger_index: int = 0
    close_time_iso: str = ""


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


def _send_result_from_result(
    result: dict, destination: str, amount_drops: int, txid: str = "",
) -> SendResult:
    """Build a :class:`SendResult` from a validated ``tx``/submit result."""
    meta = _meta(result)
    fields = _tx_fields(result)
    fee_drops = _int_or_none(fields.get("Fee", 0)) or 0
    amount = _int_or_none(fields.get("DeliverMax", fields.get("Amount")))
    return SendResult(
        txid=str(result.get("hash", txid) or txid),
        destination=destination,
        amount_drops=amount if amount is not None else amount_drops,
        fee_drops=fee_drops,
        created_account=_created_account(meta, destination),
        ledger_index=_int_or_none(result.get("ledger_index", 0)) or 0,
        close_time_iso=str(result.get("close_time_iso", "") or ""),
    )


def _resolve_after_lapse(
    txid: str, last_ledger: int, destination: str, amount_drops: int, url: str,
) -> SendResult:
    """Look the transaction up instead of guessing, after a lapsed window.

    xrpl-py's ``_wait_for_final_transaction_outcome`` checks the ledger
    sequence BEFORE it queries the transaction by hash, so a payment that was
    validated in the final ledger still raises the lapse error. The old code
    could not tell that apart from a genuine rejection — same exception class,
    no attribute distinguishing them, and no hash anywhere in the message,
    because the one-shot ``submit_and_wait`` never handed back the signed
    transaction. It then rendered as "This one is safe to run again", and
    running again sends a SECOND real payment in the lesson whose whole point
    is that ledger writes cannot be undone.

    So: ask the ledger. A found, validated ``tesSUCCESS`` is a success.
    """
    detail = f"hash={txid} last_ledger={last_ledger}"
    try:
        response, result = _fetch_tx(txid, url)
    except XRPLTransportError as exc:
        raise XRPLSubmissionUnresolved(
            "Your transaction was signed and sent, but its window closed "
            "before the ledger confirmed it, and the follow-up lookup failed "
            f"too. It may or may not be on the ledger. Hash: {txid}",
            txid=txid,
            last_ledger=last_ledger,
            detail=f"{detail} lookup={exc}",
        ) from exc

    if response is not None and response.is_successful() and result.get("validated"):
        engine_result = str(_meta(result).get("TransactionResult", "") or "")
        if engine_result == "tesSUCCESS":
            logger.debug("lapsed window, but %s validated successfully", txid)
            return _send_result_from_result(result, destination, amount_drops, txid)
        raise _engine_failure(engine_result or "unknown", detail)

    raise XRPLSubmissionUnresolved(
        "Your transaction was signed and sent, but the ledger did not "
        "confirm it inside its validity window, and it is not on the ledger "
        f"now. Hash: {txid}",
        txid=txid,
        last_ledger=last_ledger,
        detail=detail,
    )


def _submission_failure(
    exc: Exception, url: str, txid: str, last_ledger: int, memo_bytes: int,
) -> Exception:
    """Classify a failure raised at (or after) the moment of submission."""
    text = str(exc)
    detail = f"{type(exc).__name__}: {exc}"

    if _is_connection_failure(exc) or _status_code(exc):
        if txid:
            # The bytes may have reached a validator. Never call this safe to
            # repeat just because the socket broke.
            return XRPLSubmissionUnresolved(
                f"The connection to {url} failed while your transaction was "
                f"in flight, so its outcome is unknown. Hash: {txid}",
                txid=txid,
                last_ledger=last_ledger,
                detail=detail,
            )
        return _network_failure(exc, url, "Transaction submission failed")

    if _LAPSE_RE.search(text):
        # No hash to look up (pre-signing did not happen), but the safety
        # property is the same: the payment MAY be on the ledger, so this is
        # never "safe to run again".
        return XRPLSubmissionUnresolved(
            "Your transaction was sent, but its validity window closed "
            "before the ledger confirmed it. It may or may not have been "
            "recorded.",
            last_ledger=int(_LAPSE_RE.search(text).group(2)),  # type: ignore[union-attr]
            detail=detail,
        )

    if "memo exceeds the maximum" in text.lower():
        return XRPLMemoTooLarge(
            f"The ledger rejected the memo as too large ({memo_bytes} bytes).",
            detail=detail,
        )

    code = _engine_code(text)
    if code and code != "tesSUCCESS":
        return _engine_failure(code, "")

    # Strip xrpl-py's own "Transaction failed: " prefix so the rendered
    # message does not read "Transaction failed: Transaction failed: tecX".
    cleaned = re.sub(r"^(Transaction failed:\s*)+", "", text).strip() or text
    return XRPLTransactionFailed(
        f"The ledger did not accept the transaction: {cleaned}", detail=detail,
    )


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

    The transaction is autofilled and signed FIRST, so its hash exists here
    before anything is submitted. That hash is what makes a lapsed validity
    window recoverable instead of ambiguous — see :func:`_resolve_after_lapse`.
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
    from xrpl.transaction import autofill_and_sign, submit_and_wait

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

    # Affordability, BEFORE anything is signed. An unaffordable send used to
    # cost a real submitted transaction and a burned fee, and the ledger's
    # reply carried no number — "you can send at most N" is the only fact that
    # unblocks the learner. Best effort: a read that fails must not block a
    # send that would have worked.
    try:
        spendable, _live = get_spendable_drops(
            sender, url, fee_drops=FEE_HEADROOM_DROPS,
        )
    except XRPLTransportError as exc:
        logger.debug("spendable check skipped: %s", exc)
    else:
        if amount_drops > spendable:
            raise XRPLUnfundedAccount(
                f"That would send {amount_drops:,} drops, but only "
                f"{spendable:,} drops are spendable right now — the rest is "
                "locked as the account's reserve, plus a little for the "
                "network fee. Nothing was sent.",
                detail=f"spendable={spendable} requested={amount_drops}",
            )

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

    # Autofill + sign BEFORE submitting, so the hash exists on this side of
    # the wire. Autofill and signing are entirely pre-submission — nothing has
    # been sent when they fail — so this stays best effort: if it cannot be
    # done, submit the unsigned payment exactly as before and carry no hash.
    # A tool that could not pre-sign must still be able to send; what it must
    # NOT do is call an unresolved submission retryable, and that holds either
    # way (see `_submission_failure`).
    to_submit = payment
    txid = ""
    last_ledger = 0
    try:
        signed = autofill_and_sign(payment, client, wallet)
        txid = str(signed.get_hash())
        last_ledger = _int_or_none(signed.last_ledger_sequence) or 0
        to_submit = signed
    except Exception:
        logger.debug("could not pre-sign; submitting unsigned", exc_info=True)

    started = time.monotonic()
    try:
        # The wallet is passed even when `to_submit` is already signed:
        # xrpl-py returns a signed transaction untouched, and keeping the
        # argument means one call shape for both paths.
        response = submit_and_wait(to_submit, client, wallet)
    except Exception as e:
        elapsed = time.monotonic() - started
        logger.debug("submit %s failed after %.2fs: %s: %s",
                     url, elapsed, type(e).__name__, e)
        if txid and _LAPSE_RE.search(str(e)):
            match = _LAPSE_RE.search(str(e))
            if match and not last_ledger:
                last_ledger = int(match.group(2))
            return _resolve_after_lapse(
                txid, last_ledger, destination, amount_drops, url,
            )
        raise _submission_failure(e, url, txid, last_ledger, memo_bytes) from e
    logger.debug("submit %s in %.2fs", url, time.monotonic() - started)

    result = response.result or {}
    meta = _meta(result)
    engine_result = str(meta.get("TransactionResult", "") or "")
    if engine_result and engine_result != "tesSUCCESS":
        raise _engine_failure(engine_result)

    if "hash" not in result and not txid:
        raise XRPLMalformedResponse(
            "Missing hash in response: the endpoint confirmed a transaction "
            "without saying which one.",
            detail=str(sorted(result))[:400],
        )

    return _send_result_from_result(result, destination, amount_drops, txid)


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

#: ``lookup_tx`` reasons. Callers branch on ``found`` first; ``reason``
#: explains a miss so "the Testnet was reset" is a thing the tool can say.
REASON_FOUND = "found"
REASON_NOT_FOUND = "not_found"
REASON_UNVALIDATED = "unvalidated"
REASON_HISTORY_GONE = "ledger_history_gone"


def _empty_lookup(txid: str, reason: str = REASON_NOT_FOUND) -> dict:
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
        "reason": reason,
    }


def _fetch_tx(txid: str, url: str):
    """Raw ``tx`` response for `txid`. Returns ``(response, result)``."""
    from xrpl.clients import JsonRpcClient
    from xrpl.models import Tx

    started = time.monotonic()
    try:
        client = JsonRpcClient(url)
        response = client.request(Tx(transaction=txid, api_version=XRPL_API_VERSION))
    except Exception as e:
        logger.debug("tx %s failed after %.2fs: %s: %s",
                     url, time.monotonic() - started, type(e).__name__, e)
        raise _network_failure(e, url, "Lookup failed") from e
    logger.debug("tx %s in %.2fs", url, time.monotonic() - started)
    return response, (response.result or {})


def _miss_reason(url: str, recorded_ledger_index: int) -> str:
    """Why a transaction is missing: never recorded, or history discarded.

    A workshop host needs "the Testnet was reset, run `xrpl-camp reset`" to be
    a sentence the tool can say. It can: ``server_state`` carries
    ``complete_ledgers``, and the ledger index recorded when the transaction
    was made is on the caller's side of the call.
    """
    if recorded_ledger_index <= 0:
        return REASON_NOT_FOUND
    earliest = earliest_complete_ledger(url)
    if earliest is not None and earliest > recorded_ledger_index:
        return REASON_HISTORY_GONE
    return REASON_NOT_FOUND


def lookup_tx(
    txid: str,
    url: str | None = None,
    *,
    dry_run: bool = False,
    recorded_ledger_index: int = 0,
) -> dict:
    """Look up a transaction and return parsed fields.

    Callers MUST branch on ``["found"]``. ``client.request()`` does not raise
    for a missing transaction — it returns a Response whose ``result`` is
    ``{"error": "txnNotFound", ...}``. Parsing that as a hit is what made
    ``xrpl-camp verify --tx <any 64 hex chars>`` print "Independently
    verified" for a hash that is not on the ledger.

    ``["reason"]`` says WHY a miss is a miss. Pass ``recorded_ledger_index``
    (the ledger the tool recorded for this transaction) and a miss whose
    ledger predates the endpoint's earliest complete ledger is reported as
    ``ledger_history_gone`` — the Testnet was reset — rather than as a silent
    empty result indistinguishable from a typo.
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
            "reason": REASON_FOUND,
        }

    url = url or get_rpc_url()
    response, result = _fetch_tx(txid, url)

    if not response.is_successful():
        error = str(result.get("error", ""))
        if error in ("txnNotFound", "notFound"):
            return _empty_lookup(txid, _miss_reason(url, recorded_ledger_index))
        raise XRPLTransactionFailed(
            result.get("error_message") or error or "Unknown lookup error",
            detail=f"tx error {error} at {url}",
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

        validated = bool(result.get("validated", False))
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
            "validated": validated,
            "close_time_iso": str(result.get("close_time_iso", "") or ""),
            "date": unix_date,
            "reason": REASON_FOUND if validated else REASON_UNVALIDATED,
        }
    except (AttributeError, TypeError, ValueError) as e:
        raise XRPLMalformedResponse(
            f"Unexpected transaction response: {e}",
            detail=f"{type(e).__name__}: {e}",
        ) from e
