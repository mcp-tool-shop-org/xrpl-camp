"""Structured error handling for XRPL Camp.

Every user-facing failure in this package is a :class:`CampError`. The shape is
always the same - a stable ``code`` a bug report can quote, a plain-language
``message`` with no Python or XRPL jargon in it, and an actionable ``hint``.

Raw exception text never goes in ``message``. It goes in ``detail``, which is
shown only when the learner asks for it with ``--verbose`` (or when it is
captured into a support bundle).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

#: The endpoint override. Named here so hints can quote it and say whether it
#: is the cause of the failure being reported.
RPC_URL_ENV = "XRPL_CAMP_RPC_URL"

#: The single opt-out for both safety gates (hostname allowlist and the
#: server's ``network_id``). ``XRPL_CAMP_ALLOW_ANY_ENDPOINT`` is kept as an
#: alias for compatibility, but no message advertises it any more: two
#: near-identical names meant two rounds of trial and error for one decision.
ALLOW_ANY_NETWORK_ENV = "XRPL_CAMP_ALLOW_ANY_NETWORK"

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

#: Shown whenever an error carries technical ``detail`` the learner cannot see.
#: The escape hatch existed from the start and no user-facing string ever named
#: it, so the one sentence that would have solved the problem ("run
#: `xrpl-camp reset`") sat behind a flag nobody knew was there.
VERBOSE_POINTER = "  Run the same command with --verbose for the technical detail."


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
        if self.detail:
            if is_verbose():
                parts.append(f"  Detail: {self.detail}")
            else:
                parts.append(VERBOSE_POINTER)
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
    if err.detail:
        if is_verbose():
            lines.append(f"  [dim]Detail: {escape(err.detail)}[/dim]")
        else:
            lines.append(f"  [dim]{escape(VERBOSE_POINTER.strip())}[/dim]")
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


def balance_error(detail: str = "", account: str = "") -> CampError:
    """Balance check failed.

    ``account`` names WHICH account could not be read. Lesson 4 probes two of
    them - the learner's wallet and the mailbox it is about to pay - and an
    unqualified "the account may not exist yet, fund it first" sent learners
    back to lesson 3 to re-fund a wallet that was already funded.
    """
    whose = f" for {account}" if account else ""
    return CampError(
        code="NET_BALANCE",
        message=f"Balance check failed{whose}{': ' + detail if detail else '.'}",
        hint=(
            f"That account ({account}) may not exist on the ledger yet."
            if account
            else "The account may not exist yet. Fund it first."
        ),
        retryable=True,
        exit_code=EXIT_RUNTIME,
    )


def connection_error(url: str) -> CampError:
    """Could not connect to the RPC endpoint.

    The hint branches on whether the learner pinned the endpoint themselves.
    Telling somebody to "set XRPL_CAMP_RPC_URL" when that variable is already
    set, and is the reason the call failed, is advice pointing at the cause.
    """
    pinned = os.environ.get(RPC_URL_ENV, "").strip()
    if pinned:
        hint = (
            f"{RPC_URL_ENV} is set to {pinned}, and that is the endpoint that "
            f"did not answer. Unset {RPC_URL_ENV} to go back to the public Testnet."
        )
    else:
        hint = (
            "Check your internet connection. If you are on conference, hotel or "
            "campus wifi, open a browser first - a sign-in page will block this. "
            f"You can also set {RPC_URL_ENV} to a different Testnet endpoint."
        )
    return CampError(
        code="NET_CONNECT",
        message=f"Could not connect to {url}",
        hint=hint,
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
    """The configured endpoint is not a known test network.

    The hint names ONE variable and says up front that it clears both gates.
    There were two - a hostname allowlist here and a ``network_id`` check in
    the signing path - and each error named only its own, so a workshop host
    running their own rippled got past lesson 3 and then hit a second,
    differently-named variable at lesson 4.
    """
    return CampError(
        code="NET_ENDPOINT",
        message="That endpoint is not a known XRPL test network, so nothing was sent.",
        hint=(
            f"XRPL Camp spends real transactions. Unset {RPC_URL_ENV} to use the "
            f"Testnet, or set {ALLOW_ANY_NETWORK_ENV}=1 if you truly mean to use "
            "another network - that one opt-in clears both this check and the "
            "network-id check lesson 4 makes before it signs anything."
        ),
        detail=url,
        exit_code=EXIT_USER,
    )


def wrong_network_error(message: str = "", detail: str = "") -> CampError:
    """The endpoint answered, and it is not a Testnet/Devnet node.

    Deterministic: the same endpoint will report the same network id next
    time, so this is never "safe to run again".
    """
    return CampError(
        code="NET_WRONG_NETWORK",
        message=message or "That endpoint is not the XRPL Testnet or Devnet, so nothing was sent.",
        hint=(
            f"Unset {RPC_URL_ENV} to use the public Testnet, or set "
            f"{ALLOW_ANY_NETWORK_ENV}=1 if you really mean to use that network. "
            "If it is Mainnet, the XRP you spend is real."
        ),
        retryable=False,
        detail=detail,
        exit_code=EXIT_USER,
    )


def malformed_response_error(url: str, detail: str = "") -> CampError:
    """Something answered, but not with a rippled response.

    The signature of a captive portal: HTTP 200 with a sign-in page in the
    body. Retrying cannot help, and the old behaviour ("the transaction may
    not be validated yet, wait and retry") sent people to wait for something
    that had already happened.
    """
    return CampError(
        code="NET_BAD_RESPONSE",
        message=f"{url} answered, but not with something the XRP Ledger speaks.",
        hint=(
            "That is usually a wifi sign-in page or a proxy answering instead of "
            "the ledger. Open a browser and finish signing in to the network, then "
            "run this again. On a corporate proxy, ask for the endpoint to be allowed."
        ),
        retryable=False,
        detail=detail,
        exit_code=EXIT_RUNTIME,
    )


def wallet_seed_invalid_error(detail: str = "") -> CampError:
    """The stored seed could not be decoded into a wallet.

    Deterministic and locally fixable in one command. This used to be reported
    as "the Testnet faucet may be temporarily down", which sent learners to
    retry a healthy faucet forever.
    """
    return CampError(
        code="WALLET_SEED_INVALID",
        message="The wallet saved on this machine could not be read as a key.",
        hint=(
            "The seed in .xrpl-camp/wallet.json is damaged. Run 'xrpl-camp reset' "
            "to start with a fresh wallet - nothing on the ledger is affected."
        ),
        retryable=False,
        detail=detail,
        exit_code=EXIT_USER,
    )


def unfunded_error(detail: str = "") -> CampError:
    """The account exists but cannot cover this transaction."""
    return CampError(
        code="NET_UNFUNDED",
        message="There is not enough XRP in your account for that transaction.",
        hint="Run 'xrpl-camp fund' to top up from the Testnet faucet, then try again.",
        retryable=False,
        detail=detail,
        exit_code=EXIT_USER,
    )


def transaction_failed_error(
    message: str = "", detail: str = "", *, retryable: bool = False,
) -> CampError:
    """The request round-tripped and something came back wrong.

    ``message`` is the transport's own text when it is already plain language;
    transport writes these for humans, and burying them in ``detail`` behind
    --verbose replaced a specific answer with a generic one.

    ``retryable`` separates the two things this covers, because they need
    opposite advice: a ledger that rejected a transaction outright will reject
    it again, while a server answering 5xx usually will not.
    """
    return CampError(
        code="NET_TX_FAILED",
        message=message or "The ledger did not accept that transaction.",
        hint=(
            "The endpoint is answering with errors — usually a busy or unhealthy "
            "server. Run 'xrpl-camp self-check' to see whether it is reachable."
            if retryable else
            "The ledger rejected this outright, so running it again will not "
            "change the answer. Run 'xrpl-camp status' to see where you are."
        ),
        retryable=retryable,
        detail=detail,
        exit_code=EXIT_RUNTIME,
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


# ---------------------------------------------------------------------------
# Error history - the thing a support bundle exists to carry
# ---------------------------------------------------------------------------

#: File in the state directory holding the recent-error ring buffer.
ERROR_LOG_NAME = "errors.log"

#: How many entries the ring buffer keeps. Small on purpose: this is a
#: breadcrumb trail for a facilitator, not a log file.
ERROR_LOG_LIMIT = 20


def _error_log_path():
    """Path of the error log, or None when there is no state directory.

    Resolved at call time: ``models.STATE_DIR`` is a module global that
    ``XRPL_CAMP_HOME`` and the test suite both rebind.
    """
    try:
        from xrpl_camp import models

        return models.STATE_DIR / ERROR_LOG_NAME
    except Exception:
        return None


def record_error(err: CampError, *, command: str = "") -> None:
    """Append `err` to the local error history. Never raises.

    Deliberately does NOT create the state directory. A read-only command that
    refuses must not leave state behind for having been run, and a machine with
    no state directory has nothing for a support bundle to explain anyway.
    """
    import json
    from datetime import UTC, datetime

    path = _error_log_path()
    if path is None or not path.parent.is_dir():
        return

    entry = {
        "at": datetime.now(UTC).isoformat(timespec="seconds"),
        "command": command,
        "code": err.code,
        "message": err.message,
        "detail": err.detail,
        "retryable": err.retryable,
    }
    try:
        existing = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    except OSError:
        existing = []
    lines = [*existing, json.dumps(entry, ensure_ascii=False)][-ERROR_LOG_LIMIT:]
    try:
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError:
        return


def read_error_history() -> str:
    """The recent-error log as text, or '' when there is none. Never raises."""
    path = _error_log_path()
    if path is None:
        return ""
    try:
        return path.read_text(encoding="utf-8") if path.exists() else ""
    except OSError:
        return ""
