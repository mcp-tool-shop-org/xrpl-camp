"""Structured error handling for XRPL Camp.

Every user-facing failure in this package is a :class:`CampError`. The shape is
always the same - a stable ``code`` a bug report can quote, a plain-language
``message`` with no Python or XRPL jargon in it, and an actionable ``hint``.

Raw exception text never goes in ``message``. It goes in ``detail``, which is
shown only when the learner asks for it with ``--verbose`` (or when it is
captured into a support bundle).
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Exit codes - the documented CLI contract
#   0 ok | 1 user error | 2 runtime error | 3 partial success
# ---------------------------------------------------------------------------

EXIT_OK = 0
EXIT_USER = 1
EXIT_RUNTIME = 2
EXIT_PARTIAL = 3


# ---------------------------------------------------------------------------
# Verbosity - controls whether technical detail is rendered
# ---------------------------------------------------------------------------

_verbose = False


def set_verbose(value: bool) -> None:
    """Enable or disable technical detail in rendered errors."""
    global _verbose
    _verbose = bool(value)


def is_verbose() -> bool:
    """True when technical detail should be shown to the user."""
    return _verbose


@dataclass
class CampError:
    """Structured error shape for user-facing messages.

    Follows the pattern: code + message + actionable hint.
    No stack traces. No jargon. Just what happened and what to try next.

    ``detail`` carries the raw technical text (an exception string, a path)
    for ``--verbose`` and support bundles. It is never part of the message a
    beginner sees by default.
    """

    code: str
    message: str
    hint: str
    retryable: bool = False
    detail: str = ""
    exit_code: int = EXIT_RUNTIME

    def user_message(self) -> str:
        """Format for console output."""
        parts = [f"[{self.code}] {self.message}"]
        if self.hint:
            parts.append(f"  Hint: {self.hint}")
        if self.retryable:
            parts.append("  This one is safe to run again.")
        if self.detail and is_verbose():
            parts.append(f"  Detail: {self.detail}")
        return "\n".join(parts)


class CampFailure(Exception):
    """Base for every exception in this package that carries a CampError.

    There is exactly one of these so there needs to be exactly one handler.
    Three modules independently grew a structured exception during the same
    amend wave (state files, seed-leak refusal, artifact writes); all three
    inherited from bare ``Exception``, none of them was caught, and Typer
    rendered a Rich traceback over the top of a perfectly good error message.
    Gate B forbids that.

    Catching a shared base at the command boundary means the next module to
    add one is covered before it is written, rather than adding a fourth
    ``except`` clause to a growing tuple.

    ``str(exc)`` stays the full user-facing message, so even an instance that
    somehow escapes the handler ends in something actionable.
    """

    def __init__(self, error: CampError) -> None:
        super().__init__(error.user_message())
        self.error = error

    @property
    def exit_code(self) -> int:
        """Exit code this failure should produce."""
        return self.error.exit_code


def format_error(err: CampError) -> str:
    """Render a CampError as Rich markup that its own content cannot break.

    Every interpolated value is escaped, so an error whose text happens to
    contain square brackets prints literally instead of raising MarkupError.
    """
    from rich.markup import escape

    lines = [f"  [red]\\[{escape(err.code)}][/red] {escape(err.message)}"]
    if err.hint:
        lines.append(f"  [dim]{escape(err.hint)}[/dim]")
    if err.retryable:
        lines.append("  [dim]This one is safe to run again.[/dim]")
    if err.detail and is_verbose():
        lines.append(f"  [dim]Detail: {escape(err.detail)}[/dim]")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Network failures
# ---------------------------------------------------------------------------


def faucet_error(detail: str = "") -> CampError:
    """Testnet faucet request failed."""
    return CampError(
        code="NET_FAUCET",
        message=f"Faucet request failed{': ' + detail if detail else '.'}",
        hint="The Testnet faucet may be temporarily down. Try again in a minute.",
        retryable=True,
        exit_code=EXIT_RUNTIME,
    )


def send_error(detail: str = "") -> CampError:
    """Transaction submission failed."""
    return CampError(
        code="NET_SEND",
        message=f"Transaction submission failed{': ' + detail if detail else '.'}",
        hint="Check your wallet is funded. The Testnet may be congested.",
        retryable=True,
        exit_code=EXIT_RUNTIME,
    )


def lookup_error(detail: str = "") -> CampError:
    """Transaction lookup failed."""
    return CampError(
        code="NET_LOOKUP",
        message=f"Transaction lookup failed{': ' + detail if detail else '.'}",
        hint="The transaction may not be validated yet. Wait a moment and retry.",
        retryable=True,
        exit_code=EXIT_RUNTIME,
    )


def balance_error(detail: str = "") -> CampError:
    """Balance check failed."""
    return CampError(
        code="NET_BALANCE",
        message=f"Balance check failed{': ' + detail if detail else '.'}",
        hint="The account may not exist yet. Fund it first.",
        retryable=True,
        exit_code=EXIT_RUNTIME,
    )


def connection_error(url: str) -> CampError:
    """Could not connect to the RPC endpoint."""
    return CampError(
        code="NET_CONNECT",
        message=f"Could not connect to {url}",
        hint="Check your internet connection, or set XRPL_CAMP_RPC_URL to a different endpoint.",
        retryable=True,
        exit_code=EXIT_RUNTIME,
    )


def not_found_error(txid: str = "") -> CampError:
    """The ledger has no record of this transaction."""
    return CampError(
        code="NET_TX_NOT_FOUND",
        message="The ledger has no record of that transaction yet.",
        hint="A brand-new transaction can take a few seconds to validate. Try again shortly.",
        retryable=True,
        detail=txid,
        exit_code=EXIT_RUNTIME,
    )


def endpoint_error(url: str) -> CampError:
    """The configured endpoint is not a known test network."""
    return CampError(
        code="NET_ENDPOINT",
        message="That endpoint is not a known XRPL test network, so nothing was sent.",
        hint=(
            "XRPL Camp spends real transactions. Unset XRPL_CAMP_RPC_URL to use the "
            "Testnet, or set XRPL_CAMP_ALLOW_ANY_ENDPOINT=1 if you truly mean to use "
            "another network."
        ),
        detail=url,
        exit_code=EXIT_USER,
    )


# ---------------------------------------------------------------------------
# Verification failures - the ledger answered, but not with what we sent
# ---------------------------------------------------------------------------


def verification_error(message: str, detail: str = "") -> CampError:
    """The readback did not match what was sent."""
    return CampError(
        code="VERIFY_MISMATCH",
        message=message,
        hint="Nothing was recorded as verified. Look the hash up in the explorer yourself.",
        detail=detail,
        exit_code=EXIT_RUNTIME,
    )


# ---------------------------------------------------------------------------
# Local state and user input
# ---------------------------------------------------------------------------


def state_corrupt_error(detail: str = "") -> CampError:
    """The saved progress file could not be read."""
    return CampError(
        code="STATE_CORRUPT",
        message="Your progress file could not be read.",
        hint="Run 'xrpl-camp reset' to start fresh. Nothing on the ledger is affected.",
        detail=detail,
        exit_code=EXIT_USER,
    )


def wallet_missing_error() -> CampError:
    """No wallet has been created yet."""
    return CampError(
        code="WALLET_MISSING",
        message="No wallet found.",
        hint="Run 'xrpl-camp wallet create' (or 'xrpl-camp start') to make one.",
        exit_code=EXIT_USER,
    )


def wallet_corrupt_error(detail: str = "") -> CampError:
    """The wallet file exists but could not be read."""
    return CampError(
        code="WALLET_CORRUPT",
        message="Your wallet file could not be read.",
        hint="Move .xrpl-camp/wallet.json aside and run 'xrpl-camp wallet create' again.",
        detail=detail,
        exit_code=EXIT_USER,
    )


def memo_secret_error() -> CampError:
    """The memo looks like it contains a secret."""
    return CampError(
        code="MEMO_SECRET",
        message="That message looks like a wallet seed, so nothing was sent.",
        hint=(
            "Whatever you write goes on a public ledger forever. Write something you "
            "are happy for anyone to read."
        ),
        exit_code=EXIT_USER,
    )


def memo_too_long_error(length: int, limit: int) -> CampError:
    """The memo exceeds the documented limit."""
    return CampError(
        code="MEMO_TOO_LONG",
        message=f"That message is {length} bytes long. The limit is {limit}.",
        hint="Shorten it and try again.",
        exit_code=EXIT_USER,
    )


def prerequisites_error(missing: list[int], names: dict[int, str]) -> CampError:
    """Certificate requested before the lessons it would attest to are done."""
    listed = ", ".join(f"{n} ({names.get(n, '?')})" for n in missing)
    return CampError(
        code="CERT_INCOMPLETE",
        message=f"Not yet - these lessons are still outstanding: {listed}.",
        hint="Run 'xrpl-camp start' to pick up where you left off. Nothing was written.",
        exit_code=EXIT_USER,
    )


def pack_invalid_error(reason: str, detail: str = "") -> CampError:
    """The file handed to 'proof verify' is not a proof pack."""
    return CampError(
        code="PACK_INVALID",
        message=f"That file is not an XRPL Camp proof pack: {reason}",
        hint="Point this at xrpl_camp_proof_pack.json - not the certificate file.",
        detail=detail,
        exit_code=EXIT_USER,
    )


def write_error(path: str, detail: str = "") -> CampError:
    """A file could not be written."""
    return CampError(
        code="IO_WRITE",
        message=f"Could not write {path}.",
        hint="Check the folder exists, is writable, and has free space, then try again.",
        detail=detail,
        exit_code=EXIT_RUNTIME,
    )


def delete_error(path: str, detail: str = "") -> CampError:
    """State could not be removed."""
    return CampError(
        code="IO_DELETE",
        message=f"Could not fully remove {path}.",
        hint="Close any program using those files (or another xrpl-camp run) and try again.",
        detail=detail,
        exit_code=EXIT_RUNTIME,
    )


def unexpected_error(detail: str = "") -> CampError:
    """Anything we did not anticipate."""
    return CampError(
        code="INTERNAL",
        message="Something unexpected went wrong.",
        hint="Run 'xrpl-camp self-check', then 'xrpl-camp support-bundle' for a bug report.",
        detail=detail,
        exit_code=EXIT_RUNTIME,
    )
