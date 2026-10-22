"""Lesson content and guided flow for XRPL Camp.

Every lesson returns a :class:`LessonResult`. That is the whole integrity
story of this file: a lesson that fails says so, the guided flow stops there,
and the certificate refuses to attest to anything that did not actually
happen. A run that only got as far as lesson 3 says exactly that.
"""

from __future__ import annotations

import functools
import os
import re
import sys
import time
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from xrpl_camp import transport, wallet
from xrpl_camp.certificate import (
    CERTIFICATE_FILE,
    CERTIFICATE_FORMATS,
    CERTIFICATE_TEXT_FILE,
    generate_certificate,
    save_certificate,
    save_certificate_text,
    share_text,
)
from xrpl_camp.errors import (
    ALLOW_ANY_NETWORK_ENV,
    EXIT_OK,
    EXIT_RUNTIME,
    EXIT_USER,
    VERBOSE_POINTER,
    CampError,
    CampFailure,
    bad_address_error,
    bad_hash_error,
    balance_error,
    connection_error,
    endpoint_error,
    faucet_error,
    format_error,
    is_verbose,
    lookup_error,
    malformed_response_error,
    memo_secret_error,
    memo_too_long_error,
    no_account_yet_error,
    not_found_error,
    not_your_transaction_error,
    prerequisites_error,
    record_error,
    send_error,
    simulate_error,
    state_corrupt_error,
    transaction_failed_error,
    tx_unknown_error,
    unexpected_error,
    unfunded_error,
    unknown_target_error,
    unsupported_feature_error,
    verification_error,
    wallet_corrupt_error,
    wallet_missing_error,
    wallet_seed_invalid_error,
    write_error,
    wrong_network_error,
)
from xrpl_camp.models import (
    DryRunSession,
    ExecutionMode,
    Session,
    clear_in_flight,
    get_execution_mode,
    in_flight_file,
    is_dry_run,
    load_in_flight,
    save_in_flight,
    set_execution_mode,
)
from xrpl_camp.proof_pack import (
    PROOF_PACK_FILE,
    generate_proof_pack,
    save_proof_pack,
)

console = Console()

# ---------------------------------------------------------------------------
# Limits and guards
# ---------------------------------------------------------------------------

#: Largest memo we will put on the ledger, in UTF-8 bytes.
MEMO_MAX_BYTES = 512

#: Used only when the live base reserve cannot be read. Never a display value
#: for a real send - lesson 4 reads the reserve from the network.
FALLBACK_RESERVE_DROPS = 1_000_000

#: What a repeat send costs once the mailbox account already exists.
REPEAT_SEND_DROPS = 1

#: Hosts we accept without an explicit opt-in. Anything else could be Mainnet,
#: and lesson 3 tells the learner "nothing at risk" as a statement of fact.
TESTNET_HOSTS = frozenset({
    "s.altnet.rippletest.net",
    "s.devnet.rippletest.net",
    "clio.altnet.rippletest.net",
    "clio.devnet.rippletest.net",
    "testnet.xrpl-labs.com",
    "localhost",
    "127.0.0.1",
    "::1",
})

#: XRPL family seed: 's' followed by base58 (no 0, O, I, l). Anchored, so it
#: only ever saw whole whitespace-delimited tokens.
SEED_PATTERN = re.compile(r"^s[1-9A-HJ-NP-Za-km-z]{25,}$")

#: Splits text on everything base58 is NOT, so a seed pasted with punctuation
#: around it still ends up as its own run: `seed:sEd...`, `{"seed": "sEd..."}`,
#: `seed=sEd...`, `backup-sEd...`. The anchored pattern above could only ever
#: see `memo.split()` tokens, which is not how anyone pastes a line out of a
#: .env or a JSON file.
BASE58_SPLIT_PATTERN = re.compile(r"[^1-9A-HJ-NP-Za-km-z]+")

#: Shortest run worth putting to a seed test.
SEED_MIN_LENGTH = 26

#: Deprecated alias, still honoured so existing instructions keep working. Only
#: ALLOW_ANY_NETWORK_ENV is advertised - see errors.endpoint_error.
ALLOW_ANY_ENDPOINT_ENV = "XRPL_CAMP_ALLOW_ANY_ENDPOINT"

#: How many times a genuinely transient network call is attempted in total, and
#: how long to wait between attempts. Applied ONLY to idempotent reads and to
#: the faucet - never to a signed payment, which may already be on the ledger.
NETWORK_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = (2.0, 5.0)


def _start_timer() -> tuple[str, float]:
    """Start a lesson timer. Returns (iso_timestamp, monotonic_time)."""
    return datetime.now(UTC).isoformat(), time.monotonic()


def _elapsed(start_mono: float) -> float:
    """Seconds elapsed since start_mono."""
    return round(time.monotonic() - start_mono, 1)

# ---------------------------------------------------------------------------
# Lesson definitions
# ---------------------------------------------------------------------------

LESSON_NAMES = {
    1: "Mental Model",
    2: "Create Wallet",
    3: "Fund Wallet",
    4: "Send Payment",
    5: "Verify Transaction",
    6: "Certificate",
}


@dataclass(frozen=True)
class LessonResult:
    """What a lesson did. Truthy when the lesson actually succeeded.

    `txid` and `memo` are how lesson 4 hands lesson 5 the two things it needs
    to check the ledger against: the hash to look up, and the exact text that
    was sent, so the readback can be compared rather than just displayed.
    """

    lesson: int
    ok: bool
    error: CampError | None = None
    txid: str = ""
    memo: str = ""

    def __bool__(self) -> bool:
        return self.ok

    @property
    def exit_code(self) -> int:
        """Process exit code this outcome should produce."""
        if self.ok:
            return EXIT_OK
        return self.error.exit_code if self.error else 2


def format_duration(seconds: float) -> str:
    """Human-friendly duration string."""
    if seconds < 60:
        return f"{int(seconds)}s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if secs == 0:
        return f"{minutes}m"
    return f"{minutes}m {secs}s"


#: Back-compat alias. Prefer `format_duration`.
_format_duration = format_duration


# ---------------------------------------------------------------------------
# Interactivity
# ---------------------------------------------------------------------------

_non_interactive = False


def set_non_interactive(value: bool) -> None:
    """Force non-interactive mode (the --yes flag)."""
    global _non_interactive
    _non_interactive = bool(value)


def is_interactive() -> bool:
    """True when we may stop and wait for a human.

    False under --yes, and false whenever stdin is not a terminal - a pipe, a
    CI runner, a Docker build, `< /dev/null`. In those cases the flow runs
    straight through instead of aborting on the first prompt.

    ``isatty()`` alone is not enough on Windows: ``xrpl-camp start < NUL``
    reports True for the NUL device, so the memo prompt was printed, the read
    raised EOFError, and the learner's one permanent ledger entry silently
    became a machine token. Anything that is not readable, or that is already
    at end of input, is treated as non-interactive.
    """
    if _non_interactive:
        return False
    stdin = getattr(sys, "stdin", None)
    if stdin is None:
        return False
    try:
        if not stdin.isatty():
            return False
    except Exception:
        return False
    readable = getattr(stdin, "readable", None)
    if callable(readable):
        try:
            if not readable():
                return False
        except Exception:
            return False
    closed = getattr(stdin, "closed", False)
    if closed:
        return False
    if os.name == "nt":
        return _windows_has_console(stdin)
    return True


def _windows_has_console(stdin: object) -> bool:
    """True when Windows stdin is a real console, not the NUL device.

    ``NUL`` is a character device, so ``isatty()`` says True for it and the
    guided flow printed 'What do you want to write on the ledger?' into a log
    nobody could answer from. Only a genuine console handle has a console
    mode, so ``GetConsoleMode`` is the question that distinguishes them.

    Anything unexpected answers True: failing open keeps a real terminal
    interactive, and the memo path announces its default either way.
    """
    try:
        import ctypes
        import msvcrt

        handle = msvcrt.get_osfhandle(stdin.fileno())  # type: ignore[attr-defined]
        mode = ctypes.c_ulong()
        ok = ctypes.windll.kernel32.GetConsoleMode(  # type: ignore[attr-defined]
            ctypes.c_void_p(handle), ctypes.byref(mode),
        )
        return bool(ok)
    except Exception:
        return True


def _pause() -> None:
    """Pause between lessons in guided mode. A no-op when nobody can answer."""
    if not is_interactive():
        return
    try:
        console.input("\n  [dim]Press Enter to continue...[/dim]")
    except EOFError:
        console.print()
        return
    console.print()


# ---------------------------------------------------------------------------
# Small console helpers
# ---------------------------------------------------------------------------


def _report(err: CampError, *, command: str = "") -> None:
    """Print a structured error. Never raises on odd content."""
    record_error(err, command=command)
    console.print(format_error(err))


#: True while run_guided_flow is walking the lessons. The guided flow renders
#: every failure a second time inside its 'Paused' panel, so a lesson that also
#: prints on the way out gives the beginner the same two sentences twice in a
#: row, with a stray 'This one is safe to run again.' floating between the
#: copies. The panel is the better presentation, so the loose copy is
#: suppressed there; a standalone command has no panel and keeps printing the
#: structured block.
_in_guided_flow = False


def _fail(lesson: int, err: CampError) -> LessonResult:
    """Record the error, print it (unless the Paused panel will), and fail."""
    record_error(err, command=f"lesson {lesson}")
    if not _in_guided_flow:
        console.print(format_error(err))
    return LessonResult(lesson=lesson, ok=False, error=err)


def _skip_banner(lesson: int, name: str) -> None:
    """Show a skip message for already-completed lessons."""
    console.print(f"  [dim]✓ Lesson {lesson}: {name} — already completed[/dim]")


def _dry_run_banner() -> None:
    """Print a dry-run indicator."""
    console.print("  [bold yellow][DRY RUN][/bold yellow] No network calls will be made.\n")


def _show_endpoint() -> None:
    """Print which RPC endpoint will be used."""
    console.print(f"  [dim]Endpoint: {escape(transport.get_rpc_url())}[/dim]")


def _drops_line(drops: int) -> str:
    """'1,000,000 drops (1.000000 XRP)' - the unit lesson, every time.

    A repeat send costs exactly one drop, and the lesson whose whole teaching
    job is the drops unit was printing '1 drops'.
    """
    unit = "drop" if drops == 1 else "drops"
    return f"{drops:,} {unit} ({drops / 1_000_000:.6f} XRP)"


def _copyable(text: str, *, style: str = "cyan") -> None:
    """Print `text` as one unbroken, selectable line.

    Rich wraps at the terminal width, which split the explorer URL mid-hash at
    80 and 100 columns - so the payoff of lesson 5 ("go and check it yourself")
    was a link that 404s when you copy the visible line. `soft_wrap` emits the
    string as-is and lets the terminal own the overflow; the OSC-8 markup makes
    it clickable where the terminal supports it, and is ignored where it does
    not.
    """
    console.print(
        f"  [{style}][link={text}]{escape(text)}[/link][/{style}]",
        soft_wrap=True,
        highlight=False,
    )


def _reserve_facts(address: str) -> dict | None:
    """The reserve breakdown for `address`, or None if it cannot be read.

    Prefers ``transport.reserve_breakdown`` (one call). Falls back to the two
    functions that were already there and were called from nowhere in this
    file, so the lesson works on an install that predates it.
    """
    one_call = getattr(transport, "reserve_breakdown", None)
    if callable(one_call):
        try:
            facts = one_call(address)
        except Exception:
            return None
        return facts if isinstance(facts, dict) else None
    try:
        balance = int(transport.get_balance(address))
        spendable, _live = transport.get_spendable_drops(address)
        base, inc, _live2 = transport.get_reserve_detail()
    except Exception:
        return None
    return {
        "balance_drops": balance,
        "base_reserve_drops": int(base),
        "owner_reserve_drops": max(0, balance - int(spendable) - int(base)),
        "spendable_drops": int(spendable),
        "owner_count": 0,
    }


def _show_reserve(address: str) -> None:
    """Say what the learner can actually spend, and why it is not all of it.

    The faucet grants exactly 100.00 XRP, lesson 3 celebrates it, and roughly
    1 XRP of it can never be spent. The reserve is the most XRPL-specific idea
    in the whole product and it was invisible - computed twice inside a run
    and shown to the learner in neither. One line, or nothing at all.
    """
    facts = _reserve_facts(address)
    if not facts:
        return
    spendable = int(facts.get("spendable_drops", 0) or 0)
    reserve = int(facts.get("base_reserve_drops", 0) or 0)
    if spendable <= 0 or reserve <= 0:
        return
    console.print(
        f"  [bold]Spendable:[/bold] {spendable / 1_000_000:.2f} XRP — the other "
        f"{reserve / 1_000_000:.2f} is the [cyan]reserve[/cyan], locked for as long as the "
        "account exists. The ledger charges rent for the space you take up.",
    )


# ---------------------------------------------------------------------------
# Waiting, and trying again
# ---------------------------------------------------------------------------

#: Failures that are marked retryable but for which a second identical attempt
#: is not worth the learner's time. A refused connection fails instantly and
#: will fail instantly again; the hint is what they need, now. The transient
#: this product actually meets is thirty people sharing one Testnet faucet.
NO_RETRY_CODES = frozenset({"NET_CONNECT", "NET_ENDPOINT", "NET_WRONG_NETWORK"})


class _CheckFailed(Exception):
    """The call worked and the answer was not the one we are waiting for."""

    def __init__(self, error: CampError) -> None:
        super().__init__(error.message)
        self.error = error


def _retry_attempts() -> int:
    """Total attempts for an idempotent network call. 1 disables retrying."""
    raw = os.environ.get("XRPL_CAMP_RETRIES", "").strip()
    if raw:
        try:
            return max(1, min(5, int(raw)))
        except ValueError:
            pass
    return NETWORK_ATTEMPTS


def _worth_retrying(err: CampError) -> bool:
    """True when running the SAME idempotent call again could plausibly work."""
    return bool(err.retryable) and err.code not in NO_RETRY_CODES


def _backoff(attempt: int) -> None:
    """Wait before the next attempt: 2s, then 5s, with jitter."""
    import random

    index = min(attempt, len(RETRY_BACKOFF_SECONDS)) - 1
    base = RETRY_BACKOFF_SECONDS[index]
    time.sleep(base * random.uniform(0.8, 1.2))


def _live_console() -> bool:
    """True when a spinner would be seen by a human rather than logged."""
    return bool(console.is_terminal) and not _non_interactive


class _working:
    """Context manager that shows what is happening while a call runs.

    Both long waits used to be a static partial line: 'Requesting funds from
    Testnet faucet...' sat unchanged for 8 seconds on the happy path and 40+ on
    a rate-limited faucet, with nothing distinguishing 'working' from 'hung'.
    A spinner where a human is watching, the same static line where the output
    is a log, and the partial line always terminated so a failure never lands
    on the end of it.
    """

    def __init__(self, label: str, *, waiting: str = "", done: str = "done.") -> None:
        self.label = label
        self.waiting = waiting
        self.done = done
        self._status = None

    def __enter__(self):
        text = f"{self.label}{' ' + self.waiting if self.waiting else ''}"
        if _live_console():
            self._status = console.status(f"[bold]{escape(text)}[/bold]", spinner="dots")
            self._status.__enter__()
        else:
            console.print(f"  {escape(text)}", end="")
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if self._status is not None:
            self._status.__exit__(exc_type, exc, tb)
            self._status = None
            if exc_type is None:
                console.print(f"  {escape(self.label)} [green]{self.done}[/green]")
        elif exc_type is None:
            console.print(f" [green]{self.done}[/green]")
        else:
            console.print()
        return False


def try_network(
    label: str,
    call,
    fallback,
    *,
    waiting: str = "",
    done: str = "done.",
    check=None,
    attempts: int | None = None,
):
    """Run an IDEMPOTENT network call with a live status and bounded retry.

    Returns ``(value, None)`` on success or ``(None, CampError)`` on failure.

    ``retryable=True`` was declared on six errors, rendered to the learner as
    "This one is safe to run again", and acted on by nothing: the product knew
    which failures were transient and still made thirty people individually
    notice, read and re-run. This is the one place that knowledge is used.

    NEVER wrap a signed payment in this. A submission that timed out may
    already be on the ledger, and re-sending it would write the learner's memo
    twice. Only reads and the faucet come through here.

    ``check`` turns a *successful* return value into a CampError - the ledger
    answering "no such transaction yet" is a request that worked and a result
    worth waiting for.
    """
    total = attempts if attempts is not None else _retry_attempts()
    err: CampError | None = None

    for attempt in range(1, total + 1):
        if attempt > 1:
            console.print(
                f"  [dim]{escape(err.message.rstrip('.'))} — "
                f"trying again ({attempt} of {total})...[/dim]",
            )
            _backoff(attempt - 1)
        try:
            with _working(label, waiting=waiting, done=done):
                value = call()
                # Checked INSIDE the wait, so a request that worked and
                # answered "not yet" never gets to print "found." first.
                problem = check(value) if check is not None else None
                if problem is not None:
                    raise _CheckFailed(problem)
        except _CheckFailed as failed:
            err = failed.error
        except Exception as exc:  # noqa: BLE001 - classified, never re-raised
            err = _classify(exc, fallback)
        else:
            return value, None
        if not _worth_retrying(err):
            break

    return None, err


# ---------------------------------------------------------------------------
# Failure classification
# ---------------------------------------------------------------------------


def _classify(exc: Exception, fallback, *, account: str = "") -> CampError:
    """Map a transport exception to the CampError it deserves.

    Two rules, in order.

    **The exception's own error wins.** Transport exceptions carry a structured
    ``.error`` - the contract ``models.StateFileError`` already follows - and a
    layer that knows exactly what went wrong should not have its answer thrown
    away by a layer that is guessing.

    **Everything else is mapped by class.** Only a genuinely unrecognised
    exception reaches ``fallback``. It used to recognise two of transport's
    eight classes and collapse the other six into three generic "the network is
    briefly flaky, retry" messages, which produced advice that was not just
    unhelpful but wrong: a corrupt seed was reported as a faucet outage, a wifi
    sign-in page as a transaction still validating, and an RPC 5xx as an
    unfunded account - sending the learner back to lesson 3 to re-fund an
    account that was already funded. All three also promised "This one is safe
    to run again", which is false for every one of them.

    The raw exception text is attached as ``detail`` and never interpolated
    into the beginner-facing message.
    """
    raw = f"{type(exc).__name__}: {exc}"

    carried = getattr(exc, "error", None)
    if isinstance(carried, CampError):
        if not carried.detail:
            carried.detail = raw
        return carried

    url = transport.get_rpc_url()

    if isinstance(exc, transport.XRPLConnectionError):
        err = connection_error(url)
    elif isinstance(exc, transport.XRPLInvalidSeed):
        err = wallet_seed_invalid_error()
    elif isinstance(exc, transport.XRPLMalformedResponse):
        err = malformed_response_error(url)
    elif isinstance(exc, transport.XRPLWrongNetwork):
        err = wrong_network_error(_wrong_network_message(str(exc)))
    elif isinstance(exc, transport.XRPLUnfundedAccount):
        # transport writes these for humans ("the destination account does not
        # exist yet, and the amount sent is below the base reserve"). Keeping
        # its sentence is strictly better than replacing it with a guess.
        err = unfunded_error()
        err.message = str(exc) or err.message
    elif isinstance(exc, transport.XRPLMemoTooLarge):
        err = CampError(
            code="MEMO_TOO_LONG",
            message=str(exc) or "That message is too long for the ledger.",
            hint="Shorten it and send it again.",
            exit_code=EXIT_USER,
        )
    elif isinstance(exc, transport.XRPLAccountNotFound):
        err = balance_error(account=account)
        who = f"That account ({account})" if account else "That account"
        err.message = f"{who} does not exist on the ledger yet."
        err.hint = "Run 'xrpl-camp fund' first - an account has to be funded to exist."
        err.retryable = False
    elif isinstance(exc, transport.XRPLTransactionFailed):
        # This one class covers both halves of "the request round-tripped and
        # the answer was wrong", and they need opposite advice - see
        # _engine_rejection.
        text = str(exc)
        err = transaction_failed_error(text, retryable=not _engine_rejection(text))
    elif isinstance(exc, ValueError | TypeError | KeyError):
        err = unexpected_error()
    else:
        err = fallback()
    err.detail = raw
    return err


#: An XRPL engine result code - temREDUNDANT, tecUNFUNDED_PAYMENT, tefPAST_SEQ.
ENGINE_RESULT_PATTERN = re.compile(r"\b(?:tec|tef|tel|tem|ter|tes)[A-Z][A-Z_]{2,}")


def _engine_rejection(text: str) -> bool:
    """True when the ledger itself said no, rather than a server misbehaving.

    ``XRPLTransactionFailed`` is transport's catch-all for "the request
    round-tripped and the answer was wrong", and it carries two very different
    situations. A ledger that answered ``temREDUNDANT`` will answer it again
    forever, so promising "this one is safe to run again" is a lie and retrying
    wastes the learner's time. A faucet answering HTTP 500 because a room of
    thirty people just asked at once is precisely the case worth waiting out.
    The result code is what tells them apart.

    A heuristic, and deliberately the second question asked. Since the Stage
    B/C merge every transport exception carries a structured ``.error``, so
    ``_classify`` returns from structure before reaching here and this only
    sees an ``XRPLTransactionFailed`` built by hand — which the test suite
    does, and which a future caller might. It is a fallback, not the mechanism;
    if you find yourself extending it, attach a ``.error`` in transport instead.
    """
    return bool(ENGINE_RESULT_PATTERN.search(text))


def _wrong_network_message(text: str) -> str:
    """One sentence naming the network id, out of transport's longer text."""
    match = re.search(r"network_id\s+(\d+)", text)
    if not match:
        return ""
    return (
        f"That endpoint reports network id {match.group(1)}, which is not the "
        "XRPL Testnet (1) or Devnet (2), so nothing was sent."
    )


# ---------------------------------------------------------------------------
# Endpoint and wallet guards
# ---------------------------------------------------------------------------


def _endpoint_override_allowed() -> bool:
    """True when the learner has explicitly opted out of the safety gates.

    Either variable clears this gate. There were two names for what a user
    experiences as one decision, and each error named only its own, so a
    workshop host running their own rippled followed the instruction, got past
    lesson 3, and met a second, differently-named variable at lesson 4. Only
    ``XRPL_CAMP_ALLOW_ANY_NETWORK`` is advertised now, because that is the one
    the signing gate in transport reads.
    """
    return any(
        os.environ.get(name, "").strip() not in ("", "0", "false")
        for name in (ALLOW_ANY_NETWORK_ENV, ALLOW_ANY_ENDPOINT_ENV)
    )


def check_endpoint() -> CampError | None:
    """Refuse to spend against an endpoint that may not be a test network.

    Two gates, because a hostname is not evidence. ``localhost`` is on the
    allowlist - it has to be, for anyone running their own rippled - and a
    local node connected to Mainnet is an entirely ordinary thing for this
    tool's audience to have running. Lesson 3 tells the learner "nothing at
    risk" as a statement of fact, and a hostname string cannot support that
    claim, so the server's own ``network_id`` is asked as well.

    Returns None when the endpoint is fine (printing a loud banner if the
    learner overrode the gates), or a CampError to fail the lesson with.
    """
    url = transport.get_rpc_url()
    host = (urlparse(url).hostname or "").lower()
    known_test_host = host in TESTNET_HOSTS or host.endswith(".rippletest.net")
    overridden = _endpoint_override_allowed()

    if not known_test_host and not overridden:
        return endpoint_error(url)

    if not overridden:
        # The stronger guard: what the server says it is, not what it is
        # called. A no-op on the default endpoint - see
        # transport.assert_safe_network.
        try:
            transport.assert_safe_network(url)
        except transport.XRPLWrongNetwork as exc:
            return _classify(exc, wrong_network_error)
        except Exception:
            # An unreachable endpoint is reported by the call that needs it,
            # with a hint this function has no context to write.
            pass

    if not known_test_host:
        console.print(Panel(
            "[bold]This is not a known test network.[/bold]\n\n"
            f"Endpoint: {escape(url)}\n\n"
            f"You set {ALLOW_ANY_NETWORK_ENV}, so XRPL Camp will go ahead.\n"
            "If this is Mainnet, the XRP you spend is real and the memo you write\n"
            "is public and permanent. Nothing here can be undone.",
            title="Not a test network",
            border_style="red",
        ))
    return None


def _load_wallet() -> tuple[dict | None, CampError | None]:
    """Load the wallet, converting a broken file into a CampError."""
    try:
        return wallet.load_wallet(), None
    except CampFailure as exc:
        # wallet.load_wallet raises StateFileError, which is a CampFailure and
        # therefore inherits from Exception - not from any of the four types
        # below. Without this clause the handler could never fire for the case
        # it was written for, and the error only rendered because cli.run()
        # catches CampFailure at the boundary.
        return None, exc.error
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return None, wallet_corrupt_error(f"{type(exc).__name__}: {exc}")


def _require_wallet() -> tuple[dict | None, CampError | None]:
    """Load the wallet, or explain that there isn't one."""
    w, err = _load_wallet()
    if err is not None:
        return None, err
    if not w:
        return None, wallet_missing_error()
    return w, None


def _resolve_mailbox() -> tuple[dict | None, CampError | None]:
    """Load the lesson-4 mailbox wallet, creating and saving one if needed.

    The mailbox is a second wallet the learner also owns. Its seed is saved
    next to the main wallet - both ends of the payment belong to them.
    """
    try:
        mailbox = wallet.load_mailbox()
        if mailbox:
            return mailbox, None
        address, seed = wallet.create_mailbox()
        wallet.save_mailbox(address, seed)
        return {"address": address, "seed": seed}, None
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return None, wallet_corrupt_error(f"{type(exc).__name__}: {exc}")


def _existing_mailbox_seed() -> str:
    """The mailbox seed if there already is one. Never creates one.

    `send --to` has no use for a mailbox, but the memo guard still has to know
    that seed so it can refuse a learner who pastes it.
    """
    try:
        record = wallet.load_mailbox()
    except Exception:
        return ""
    return str(record.get("seed", "")) if record else ""


def is_valid_address(address: str) -> bool:
    """True when `address` passes the XRPL checksum, offline. No network call.

    An XRPL address carries its own checksum, so a typo is catchable on the
    learner's own machine in microseconds. Before this, a mistyped address
    cost a network round-trip and came back as "Account malformed".
    """
    checker = getattr(transport, "is_valid_address", None)
    if not callable(checker):
        try:
            from xrpl.core.addresscodec import is_valid_classic_address as checker
        except Exception:
            return True  # cannot answer: do not invent a refusal
    try:
        return bool(checker(str(address)))
    except Exception:
        return False


#: A transaction hash: exactly 64 hex characters, either case.
TX_HASH_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


def is_tx_hash(value: str) -> bool:
    """True when `value` has the shape of an XRPL transaction hash."""
    return bool(TX_HASH_PATTERN.match(str(value).strip()))


# ---------------------------------------------------------------------------
# Memo handling
# ---------------------------------------------------------------------------


def _memo_hex(memo: str) -> str:
    """Hex bytes for the memo, exactly as the transport writes them."""
    encoder = getattr(transport, "to_hex", None) or getattr(transport, "_to_hex", None)
    if callable(encoder):
        return str(encoder(memo))
    return memo.encode("utf-8").hex()


def _looks_like_a_seed(candidate: str) -> bool:
    """True when `candidate` is, or plausibly is, a real XRPL seed.

    Delegates to the certificate module's guard, which is the stronger of the
    two the package had: it accepts the fixed ed25519 ``sEd`` prefix (so a
    truncated near-miss is still refused) and asks xrpl-py's own base58 codec
    about everything else, which is the only way to recognise a secp256k1 seed.
    """
    from xrpl_camp.certificate import _looks_like_xrpl_seed

    try:
        return bool(_looks_like_xrpl_seed(candidate))
    except Exception:
        return False


def validate_memo(memo: str, secrets: Iterable[str] = ()) -> CampError | None:
    """Refuse memos that are too long, or that look like key material.

    Lesson 2 tells the learner to guard their seed like a password. Lesson 4
    then invites them to type anything at all into a permanent public record.
    This is the guard between those two sentences, and the thing it is guarding
    against is irreversible: a private key written onto a public ledger cannot
    be taken back.

    It used to see only whitespace-delimited tokens against an anchored
    pattern, so it caught `sEd...` and `my seed is sEd...` and missed every
    shape people actually paste - `seed:sEd...`, `{"seed": "sEd..."}`,
    `seed=sEd...`, `backup-sEd...` - because any adjacent punctuation defeated
    both halves at once. It also only ever recognised the two seeds the current
    run happens to hold; an older wallet's seed, or a Mainnet one, went
    straight through. Now the text is scanned for base58 runs wherever they sit
    and each one is put to a real seed test.
    """
    encoded = memo.encode("utf-8")
    if len(encoded) > MEMO_MAX_BYTES:
        return memo_too_long_error(len(encoded), MEMO_MAX_BYTES)
    for secret in secrets:
        if secret and secret in memo:
            return memo_secret_error()
    for token in memo.split():
        if SEED_PATTERN.match(token):
            return memo_secret_error()
    for run in BASE58_SPLIT_PATTERN.split(memo):
        if len(run) < SEED_MIN_LENGTH:
            continue
        if _looks_like_a_seed(run):
            return memo_secret_error()
        # A seed can sit inside a longer base58 run ("passEdTi..."), where
        # testing only the whole run would miss it. "sEd" is a fixed prefix,
        # so every offset that starts one is cheap to check.
        for index in range(1, len(run) - SEED_MIN_LENGTH + 1):
            if run.startswith("sEd", index) and _looks_like_a_seed(run[index:]):
                return memo_secret_error()
    return None


def _ask_memo(secrets: Iterable[str]) -> tuple[str, CampError | None]:
    """Prompt for the memo, re-asking on a rejected one. ('', None) = use default."""
    secrets = list(secrets)
    last_error: CampError | None = None
    for _ in range(3):
        try:
            answer = console.input(
                "\n  [bold]What do you want to write on the ledger?[/bold] ",
            ).strip()
        except EOFError:
            # The prompt is already on screen and there is nobody to answer it.
            # Saying so is the whole point: the caller announces the default it
            # is about to write instead of letting it appear unexplained.
            console.print("\n  [dim](no answer - nothing is reading this input)[/dim]")
            return "", None
        if not answer:
            return "", None
        last_error = validate_memo(answer, secrets)
        if last_error is None:
            console.print()
            return answer, None
        _report(last_error, command="memo")
    return "", last_error


def _announce_default_memo(memo: str) -> None:
    """Say what is about to go on the ledger when the learner gave no message.

    The memo is the emotional centre of the product and the one permanent thing
    the learner writes. Under `--yes`, a pipe, or `| tee workshop.log`, the
    prompt was skipped and a machine token went onto a public ledger with
    nothing on screen to say a default had been substituted.
    """
    console.print(
        f"\n  [yellow]No message was given, so this run will write "
        f"{escape(memo)} to the ledger.[/yellow]",
    )
    console.print(
        "  [dim]Use --memo \"your message\" to write your own. "
        "Whatever goes on is permanent and public.[/dim]",
    )


# ---------------------------------------------------------------------------
# Lessons
# ---------------------------------------------------------------------------


#: How long lesson 1 waits between its two readings of the ledger. Long enough
#: that the number has to move (a Testnet ledger closes about every 3-4s),
#: short enough that nobody in a room of thirty feels it.
LEDGER_WATCH_SECONDS = 5.0


def _validated_ledger() -> tuple[int, int] | None:
    """``(ledger_index, seconds_since_it_closed)`` from the live network.

    None on anything at all going wrong. Lesson 1 is the first screen a
    beginner ever sees, and thirty people on conference wifi is the normal
    case, so this must never be able to fail a lesson.
    """
    read = getattr(transport, "_server_state", None)
    if not callable(read):
        return None
    try:
        state = read(transport.get_rpc_url())
        ledger = (state or {}).get("validated_ledger")
        index = int((ledger or {}).get("seq", 0) or 0)
        age = int((ledger or {}).get("age", 0) or 0)
    except Exception:
        return None
    return (index, age) if index > 0 else None


def _ask_prediction(question: str) -> None:
    """Ask for a one-word guess, print nothing back, gate nothing on it.

    Recall beats reading, and this is the only way to get it without the tool
    becoming the arbiter of a right answer - which would be the one beat in
    the product whose answer key is a hardcoded string rather than the ledger.
    The ledger answers a moment later; the learner does the comparing.
    """
    if not is_interactive():
        return
    try:
        console.input(f"\n  [bold]{escape(question)}[/bold] [dim](or Enter)[/dim] ")
    except EOFError:
        console.print()


def lesson_1_mental_model(session: Session, *, dry_run: bool = False) -> LessonResult:
    """Lesson 1: the mental model, demonstrated against the live network.

    This used to be 103 words of assertion and a green tick for having read
    them: no network call, no input, nothing produced, and no way to fail. It
    now asks the live ledger the same question twice and lets the answer move.
    Everything about it degrades to the static panel, because the FIRST screen
    a beginner sees must not be the one that can break.
    """
    ts, t0 = _start_timer()

    console.print(Panel(
        "[bold]Lesson 1: The Mental Model[/bold]\n\n"
        "The XRP Ledger is a public notebook. Every few seconds the whole\n"
        "network agrees on the next page and closes it, forever.\n\n"
        "  [cyan]Account[/cyan]     — your identity on it: an address anyone can look up\n"
        "  [cyan]Balance[/cyan]     — what it holds, in drops (1 XRP = 1,000,000 drops)\n"
        "  [cyan]Transaction[/cyan] — one line in the notebook, which cannot be erased\n"
        "  [cyan]Memo[/cyan]        — a note you attach to a transaction. Anything you like.",
        title="XRPL Camp",
        border_style="blue",
    ))

    # A dry run promises no network calls and is asserted on. Checked both
    # ways: the argument for a direct caller, the process mode for the CLI.
    first = None if (dry_run or is_dry_run()) else _validated_ledger()
    if first is not None:
        index, age = first
        closed = (
            "a moment ago" if age <= 0
            else f"{age} second{'' if age == 1 else 's'} ago"
        )
        console.print(
            f"\n  [bold]Right now it is on page {index:,}[/bold], closed {closed}.",
        )
        _ask_prediction(
            f"How many more pages in the next {int(LEDGER_WATCH_SECONDS)} seconds?",
        )
        with _working("Watching...", done="asked again."):
            time.sleep(LEDGER_WATCH_SECONDS)
        second = _validated_ledger()
        if second is not None and second[0] > index:
            closed = second[0] - index
            console.print(
                f"\n  [bold]Page {second[0]:,}.[/bold] "
                f"{closed} more closed while you watched — with or without you.",
            )

    session.mark_complete(1, LESSON_NAMES[1], started_at=ts, duration_seconds=_elapsed(t0))
    session.save()

    console.print(
        "\n  [green]✓ Foundation set.[/green] "
        "It is already running. You are about to join it.",
    )
    return LessonResult(lesson=1, ok=True)


def _honours_dry_run(fn):
    """Make a lesson's own ``dry_run=True`` mean dry-run all the way down.

    1.4.2: the wallet layer reads only the process-wide execution mode, so
    calling ``run_guided_flow(dry_run=True)`` (or lesson 2 or 4) in-process,
    without the CLI having set that mode first, still wrote a seed to disk.
    This enters DRY_RUN for the call and restores the earlier mode after it;
    leaving dry-run also drops the in-memory dry-run wallet, so nothing from
    the simulated run leaks into a later real one.
    """

    @functools.wraps(fn)
    def wrapper(*args, dry_run: bool = False, **kwargs):
        previous = get_execution_mode()
        if not dry_run or previous == ExecutionMode.DRY_RUN:
            return fn(*args, dry_run=dry_run, **kwargs)
        set_execution_mode(ExecutionMode.DRY_RUN)
        try:
            return fn(*args, dry_run=dry_run, **kwargs)
        finally:
            set_execution_mode(previous)
            wallet.reset_dry_run_cache()

    return wrapper


@_honours_dry_run
def lesson_2_create_wallet(session: Session, *, dry_run: bool = False) -> LessonResult:
    """Lesson 2: Create a Testnet wallet."""
    ts, t0 = _start_timer()

    # A dry run never touches the real wallet, in either direction: it does
    # not read one and it does not write one.
    if not dry_run and wallet.wallet_exists():
        w, err = _load_wallet()
        if err is not None:
            return _fail(2, err)
        if w:
            console.print(f"  [dim]Wallet already exists: {escape(w['address'])}[/dim]")
            session.wallet_address = w["address"]
            session.mark_complete(
                2, LESSON_NAMES[2], started_at=ts, duration_seconds=_elapsed(t0),
            )
            session.save()
            return LessonResult(lesson=2, ok=True)

    console.print(Panel(
        "[bold]Lesson 2: Create a Wallet[/bold]\n\n"
        "A wallet is a pair of keys:\n"
        "  [cyan]Address[/cyan] — your public identity (safe to share)\n"
        "  [cyan]Seed[/cyan]    — your private key (never share this)\n\n"
        "The seed proves you own the address, so anyone holding it can\n"
        "spend your funds. It stays on this machine; XRPL Camp never\n"
        "sends it anywhere.",
        title="XRPL Camp",
        border_style="blue",
    ))

    if dry_run:
        _dry_run_banner()

    console.print("\n  Creating wallet...", end="")
    try:
        address, seed = wallet.create_wallet()
        wallet.save_wallet(address, seed)
    except OSError as exc:
        console.print()
        return _fail(2, write_error(wallet.WALLET_FILE.as_posix(), f"{type(exc).__name__}: {exc}"))
    except Exception as exc:
        console.print()
        return _fail(2, _classify(exc, unexpected_error))
    console.print(" [green]done.[/green]")

    console.print(f"\n  [bold]Address:[/bold] {escape(address)}")
    # 1.4.2: the real path. With XRPL_CAMP_HOME set it isn't ./.xrpl-camp.
    where = escape(wallet.WALLET_FILE.as_posix())
    if dry_run:
        console.print(
            f"  [dim]Seed would be saved to {where} "
            "(nothing written — dry run)[/dim]",
        )
    else:
        console.print(f"  [dim]Seed saved to {where}[/dim]")
    console.print(
        "\n  [yellow]This is a Testnet wallet. "
        "Never use Testnet seeds on Mainnet.[/yellow]",
    )

    session.wallet_address = address
    if not dry_run:
        session.mark_complete(2, LESSON_NAMES[2], started_at=ts, duration_seconds=_elapsed(t0))
        session.save()

    console.print(
        "\n  [green]✓ Identity created.[/green] "
        "Nobody issued it to you — you generated it yourself.",
    )
    return LessonResult(lesson=2, ok=True)


def lesson_3_fund_wallet(session: Session, *, dry_run: bool = False) -> LessonResult:
    """Lesson 3: Fund the wallet via Testnet faucet."""
    ts, t0 = _start_timer()

    w, err = _require_wallet()
    if err is not None:
        return _fail(3, err)

    if dry_run:
        _dry_run_banner()
    _show_endpoint()

    # Before the panel, not after it. "This is play money - nothing at risk" is
    # a safety assertion, and it was printed fifteen lines before the guard
    # that establishes it.
    if not dry_run:
        endpoint_problem = check_endpoint()
        if endpoint_problem is not None:
            return _fail(3, endpoint_problem)

    console.print(Panel(
        "[bold]Lesson 3: Fund Your Wallet[/bold]\n\n"
        "The XRPL Testnet has a faucet that gives free test XRP.\n"
        "This is play money — no real value, nothing at risk.\n"
        "But it behaves exactly like real XRP on the ledger.\n\n"
        "[dim]Usually about ten seconds, and up to a minute when the faucet is\n"
        "busy — a whole room asking it at once will do that.[/dim]",
        title="XRPL Camp",
        border_style="blue",
    ))
    console.print()

    # A busy faucet is worth waiting out rather than handing back to thirty
    # people to re-run one at a time. An account that already holds test XRP
    # is not funded again (fund_wallet_detail): the grant is shared, and a
    # second one takes it from somebody else in the room. 1.4.2: say so,
    # instead of "Requesting funds... funded." for a request never made.
    funded, err = try_network(
        # Worded for both outcomes: the balance is read first, and the faucet
        # is asked only when it is empty (Book Keeper, 1.4.2 live check).
        "Checking your balance, and asking the Testnet faucet if it's empty...",
        lambda: transport.fund_wallet_detail(w["seed"], dry_run=dry_run),
        faucet_error,
        waiting="(usually about ten seconds)",
        done="done.",
    )
    if err is not None:
        return _fail(3, err)
    if funded is not None and funded.already_funded:
        console.print(
            "  [dim]Your wallet already holds test XRP, so the faucet was not "
            "asked again: its grants are shared with everyone using it.[/dim]",
        )

    if dry_run:
        console.print("\n  [bold]Balance:[/bold] (skipped — dry run)")
    else:
        # A balance read that fails does not undo the funding, so it warns
        # rather than failing the lesson.
        try:
            balance = transport.get_balance(w["address"])
            xrp = balance / 1_000_000
            console.print(f"\n  [bold]Balance:[/bold]   {xrp:.2f} XRP ({balance:,} drops)")
        except transport.XRPLAccountNotFound:
            console.print(
                "\n  [bold]Balance:[/bold]   [yellow]Account not yet activated[/yellow]",
            )
        except Exception as exc:
            warning = _classify(exc, balance_error, account=w["address"])
            console.print()
            _report(warning, command="lesson 3 balance")
        else:
            _show_reserve(w["address"])

    if not dry_run:
        session.mark_complete(3, LESSON_NAMES[3], started_at=ts, duration_seconds=_elapsed(t0))
        session.save()

    # 1.4.2: under a DRY RUN banner, nothing was funded; don't say it was.
    console.print(
        "\n  [green]✓ Simulated.[/green] Nothing was funded — dry run."
        if dry_run else
        "\n  [green]✓ Account funded.[/green] "
        "The network knows you exist now.",
    )
    return LessonResult(lesson=3, ok=True)


def _settle_in_flight(session: Session):
    """Find out what happened to a payment a cut-off run sent (1.4.2).

    Book Keeper's live check: a Ctrl-C half a second after the submit lost a
    payment that then validated, and the next `start` wrote the same memo to
    the ledger a second time. Returns ``(result, memo, None)`` when the
    earlier payment landed, ``(None, "", None)`` when it is safe to send, and
    ``(None, "", error)`` while it could still land or can't be checked.
    """
    record = load_in_flight()
    if record is None:
        return None, "", None
    txid = str(record.get("txid", "") or "")
    if not txid:
        # Fails closed: a payment may be in flight and its record is damaged.
        return None, "", CampError(
            code="SEND_IN_FLIGHT_UNREADABLE",
            message=(
                "Your last run may have sent a payment, and its record can't "
                "be read, so nothing new was sent."
            ),
            hint=(
                f"Check your recent transactions in the explorer, then delete "
                f"{in_flight_file().as_posix()} and run this again."
            ),
            detail=str(record.get("unreadable", "")),
            exit_code=EXIT_USER,
        )
    recorded = {p.txid for p in session.progress if p.lesson == 4}
    recorded |= {e.txid for e in session.entries}
    if txid in recorded:
        # Recorded already; only the clear was cut off. Not a reason to stop
        # a deliberate new send.
        clear_in_flight()
        return None, "", None
    console.print(
        f"\n  [dim]Your last run sent a payment and stopped before it was "
        f"recorded. Checking the ledger for it first: {escape(txid)}[/dim]",
    )
    try:
        result = transport.resolve_in_flight(
            txid,
            int(record.get("last_ledger") or 0),
            str(record.get("destination", "")),
            int(record.get("amount_drops") or 0),
        )
    except transport.XRPLSubmissionUnresolved as exc:
        return None, "", _classify(exc, send_error)
    except (transport.XRPLTransactionFailed, transport.XRPLUnfundedAccount):
        # It reached the ledger and failed there (a tec claims the fee and
        # delivers nothing): no memo was written, so a new send is right.
        console.print(
            "  [dim]It did not succeed on the ledger, so it is safe to send "
            "again.[/dim]",
        )
        clear_in_flight()
        return None, "", None
    except Exception as exc:
        return None, "", _classify(exc, send_error)
    if result is None:
        console.print(
            "  [dim]It never made it onto the ledger, so it is safe to send "
            "again.[/dim]",
        )
        clear_in_flight()
        return None, "", None
    console.print("  [green]It landed.[/green] Recording it instead of sending again.")
    return result, str(record.get("memo", "")), None


def _report_send(
    session: Session, result, *, memo: str, to_address: str, mailbox,
    ts: str, t0: float, dry_run: bool,
) -> LessonResult:
    """Show a sent payment and record it. Shared by a fresh send and by a
    payment an earlier, cut-off run sent (1.4.2)."""
    txid = result.txid
    landed = int(getattr(result, "ledger_index", 0) or 0)
    # Which page the notebook was on a moment before this went in: soft (0
    # means the line is simply not printed), and it turns "waiting for
    # validators to agree" from a spinner into a number the learner can watch
    # move. 1.4.2: send_memo_payment measures it at submission, so the extra
    # server_state read this used to make is gone.
    before_ledger = int(getattr(result, "submitted_at_ledger_index", 0) or 0)
    # 1.4.2: the link follows the endpoint in use ("" off Testnet/Devnet).
    explorer = transport.explorer_url_for(txid)
    console.print(f"\n  [bold]Transaction:[/bold] {escape(txid)}")
    console.print(f"  [bold]Delivered:[/bold]   {_drops_line(int(result.amount_drops))}")
    console.print(f"  [bold]Fee paid:[/bold]    {int(result.fee_drops):,} drops")
    if landed:
        console.print(f"  [bold]Ledger:[/bold]      {landed:,}")
        # Both indices were already in hand: the destination probe read one,
        # the validated result carries the other. No extra network call, and
        # it is the only place the learner gets to SEE consensus happening.
        closed = landed - before_ledger if before_ledger else 0
        if 0 < closed < 1000:
            console.print(
                f"  [dim]{closed} ledger{'' if closed == 1 else 's'} closed while you "
                "waited. The network does that every few seconds, "
                "with or without you.[/dim]",
            )
    if explorer:
        console.print("  [dim]Explorer:[/dim]")
        _copyable(explorer, style="dim")

    if result.created_account:
        keys_note = (
            "into being, and you hold its keys — they are in\n"
            f"{escape(wallet.MAILBOX_FILE.as_posix())}, next to your own."
            if mailbox else
            "into being. You do not hold its keys; whoever gave you that\n"
            "address does."
        )
        console.print(Panel(
            "[bold]You just created an account on a public ledger.[/bold]\n\n"
            f"{escape(result.destination)}\n\n"
            f"That address did not exist a moment ago. Your payment brought it\n"
            f"{keys_note}\n\n"
            "Nobody approved this. Nobody could have stopped it.",
            title="Account created",
            border_style="green",
        ))

    if not dry_run:
        # Everything the send produced, into the permanent record. Every one of
        # these values was in scope here and none of them was passed, so a
        # real, validated run sealed a certificate with no memo on it and a
        # proof pack carrying ledger_index=0 and close_time_iso="" - which is
        # also what makes a Testnet reset indistinguishable from a forgery.
        # `memo` is already length-capped and seed-screened by validate_memo.
        session.mark_complete(
            4, LESSON_NAMES[4], txid=txid,
            started_at=ts, duration_seconds=_elapsed(t0),
            memo=memo,
            destination=str(result.destination or to_address),
            amount_drops=int(result.amount_drops or 0),
            fee_drops=int(result.fee_drops or 0),
            created_account=bool(result.created_account),
            ledger_index=landed,
            close_time_iso=str(getattr(result, "close_time_iso", "") or ""),
        )
        session.save()
        # Recorded, and saved first: nothing is in flight any more.
        clear_in_flight()

    console.print(
        "\n  [green]✓ Simulated.[/green] Nothing was written to the ledger — dry run."
        if dry_run else
        "\n  [green]✓ Written to the ledger.[/green] "
        "Your memo is permanent and public — no one can erase it.",
    )
    return LessonResult(lesson=4, ok=True, txid=txid, memo=memo)


@_honours_dry_run
def lesson_4_send_payment(
    session: Session,
    memo: str = "",
    *,
    dry_run: bool = False,
    interactive: bool = False,
    destination: str = "",
) -> LessonResult:
    """Lesson 4: send a memo payment. To the learner's own mailbox by default.

    ``destination`` is the opt-in ``send --to`` path and is never used by the
    guided flow: putting an address exchange on the critical path of a room of
    thirty turns a twenty-second lesson into a coordination problem. Offered
    after the arc, where the payoff - writing into somebody else's permanent
    record - is the whole point.
    """
    ts, t0 = _start_timer()

    w, err = _require_wallet()
    if err is not None:
        return _fail(4, err)

    # The endpoint goes up FIRST, before any of the three network round-trips
    # below. It used to be printed after all of them, so a failure in any one
    # produced three lines of output that never said which server had been
    # asked - and 1.14 seconds of blank screen even when everything worked.
    if dry_run:
        _dry_run_banner()
    _show_endpoint()

    # Refuse a non-test endpoint before anything is created or spent.
    if not dry_run:
        endpoint_problem = check_endpoint()
        if endpoint_problem is not None:
            return _fail(4, endpoint_problem)

    # The address's own checksum, checked offline, before a round-trip is
    # spent on it. A mistyped address used to cost a network call and come
    # back as "Account malformed"; caught here it costs nothing and is one of
    # the best free teaching beats in the product.
    to_address = str(destination or "").strip()
    if to_address:
        if not is_valid_address(to_address):
            return _fail(4, bad_address_error(to_address))
        if to_address == w.get("address", ""):
            return _fail(4, CampError(
                code="SEND_TO_SELF",
                message="That is your own address, and the XRPL rejects a payment to itself.",
                hint=(
                    "Leave --to off to write to your own mailbox, or give "
                    "somebody else's address."
                ),
                exit_code=EXIT_USER,
            ))
        mailbox = None
        secrets = [w.get("seed", ""), _existing_mailbox_seed()]
    else:
        mailbox, err = _resolve_mailbox()
        if err is not None:
            return _fail(4, err)
        to_address = mailbox["address"]
        secrets = [w.get("seed", ""), mailbox.get("seed", "")]

    if not dry_run:
        earlier, earlier_memo, problem = _settle_in_flight(session)
        if problem is not None:
            return _fail(4, problem)
        if earlier is not None:
            return _report_send(
                session, earlier, memo=earlier_memo, to_address=to_address,
                mailbox=mailbox, ts=ts, t0=t0, dry_run=dry_run,
            )

    if interactive:
        console.print(Panel(
            "[bold]Lesson 4: Send a Payment[/bold]\n\n"
            "You're about to write something permanent on a public ledger.\n"
            "The payment goes to a second wallet you also own — your mailbox —\n"
            "so both ends of it are yours.\n\n"
            "What matters is the [cyan]memo[/cyan]: your message on the blockchain.\n"
            "It can be anything: your name, a date, a thought, a joke.\n"
            "Once submitted, anyone can read it and nobody can erase it.\n\n"
            "[dim]Don't paste anything secret. This is public, forever.[/dim]",
            title="XRPL Camp",
            border_style="blue",
        ))
        # Only ask when there is somebody to answer AND no message was supplied.
        # The prompt used to be printed regardless on Windows redirects, read
        # EOF, and be silently overwritten by the next panel.
        if not memo and is_interactive():
            memo, memo_error = _ask_memo(secrets)
            if memo_error is not None:
                return _fail(4, memo_error)

    if not memo:
        memo = f"XRPLCAMP|L4|{int(time.time())}"
        _announce_default_memo(memo)

    memo_problem = validate_memo(memo, secrets)
    if memo_problem is not None:
        return _fail(4, memo_problem)

    # How much to send depends on whether the mailbox account exists yet: a
    # brand-new account has to be funded to at least the base reserve, and
    # that reserve is read live because it changes by amendment.
    if dry_run:
        creates_account = True
        amount_drops = FALLBACK_RESERVE_DROPS
    else:
        whose = "your mailbox account" if mailbox else "that account"
        console.print(
            f"\n  [dim]Checking {whose} {escape(to_address)} "
            "— does it exist on the ledger yet?[/dim]",
        )
        try:
            transport.get_balance(to_address)
            creates_account = False
        except transport.XRPLAccountNotFound:
            creates_account = True
        except Exception as exc:
            # Name the account. The failing probe here is the DESTINATION's,
            # and an unqualified "the account may not exist yet, fund it first"
            # sent learners back to lesson 3 to re-fund a wallet that was fine.
            return _fail(4, _classify(exc, balance_error, account=to_address))

        if creates_account:
            console.print(
                "  [dim]It doesn't. Asking the network what the base reserve is, "
                "so we send enough to bring it into existence...[/dim]",
            )
            try:
                amount_drops = int(transport.get_reserve_base())
            except Exception:
                amount_drops = FALLBACK_RESERVE_DROPS
        else:
            amount_drops = REPEAT_SEND_DROPS

    creation_note = (
        "\n  [dim]This one brings that account into existence, so it has to\n"
        "  carry at least the network's base reserve.[/dim]\n"
        if creates_account else ""
    )

    # The default destination is a wallet the learner also owns. `--to` is not,
    # and the existing warning is phrased entirely about their own record.
    intro = (
        "You're sending a real transaction to your mailbox — a second wallet\n"
        "whose keys are also yours."
        if mailbox else
        "You're sending this to somebody else's account. Your memo goes into\n"
        "[bold]their[/bold] permanent public history, and nobody can take it out again."
    )

    console.print(Panel(
        "[bold]Lesson 4: Send a Payment[/bold]\n\n"
        f"{intro}\n\n"
        f"  [cyan]Memo:[/cyan]    {escape(memo)}\n"
        f"  [cyan]Encoded:[/cyan] {escape(_memo_hex(memo))}\n\n"
        "  [dim]Your memo is converted to hex bytes for the ledger.[/dim]\n\n"
        f"  [cyan]To:[/cyan]      {escape(to_address)}\n"
        f"  [cyan]Amount:[/cyan]  {_drops_line(amount_drops)}\n"
        "  [cyan]Fee:[/cyan]     a few drops, set by the network — "
        "and destroyed, not paid to anyone\n"
        f"{creation_note}\n"
        "The amount is small on purpose: the point is the memo, not the value.\n"
        "The fee is not our charge, and it does not go to a miner or a validator\n"
        "either — that XRP simply stops existing. Nobody profits from your\n"
        "transaction; it just makes XRP very slightly scarcer.",
        title="XRPL Camp",
        border_style="blue",
    ))

    console.print()

    # NOT retried, deliberately. A submission that timed out may already be on
    # the ledger; sending it again would write the learner's one permanent
    # message twice. Everything else in this file that touches the network is
    # a read or the faucet, and those go through try_network.
    def _remember(txid: str, last_ledger: int) -> None:
        save_in_flight({
            "txid": txid, "last_ledger": last_ledger, "memo": memo,
            "destination": to_address, "amount_drops": amount_drops,
        })

    try:
        with _working(
            "Submitting transaction...",
            waiting="(waiting for validators to agree — usually a few seconds)",
            done="confirmed.",
        ):
            result = transport.send_memo_payment(
                w["seed"],
                memo,
                to_address,
                amount_drops=amount_drops,
                dry_run=dry_run,
                on_signed=_remember,
            )
    except Exception as exc:
        if isinstance(exc, (transport.XRPLTransactionFailed, transport.XRPLUnfundedAccount)):
            # Settled on the ledger as a failure: nothing is in flight.
            clear_in_flight()
        return _fail(4, _classify(exc, send_error, account=w["address"]))

    return _report_send(
        session, result, memo=memo, to_address=to_address, mailbox=mailbox,
        ts=ts, t0=t0, dry_run=dry_run,
    )


def lesson_5_verify_tx(
    session: Session,
    txid: str = "",
    *,
    dry_run: bool = False,
    expected_memo: str = "",
) -> LessonResult:
    """Lesson 5: verify a transaction the learner sent, and compare the readback.

    Two things this lesson has to get right and used to get wrong. It must
    refuse a hash that is not on the ledger (fixed earlier), and it must refuse
    a hash that IS on the ledger and belongs to somebody else - which anyone
    could copy off the explorer to complete the lesson from a directory with no
    wallet in it.
    """
    ts, t0 = _start_timer()

    own_hash = session.txids.get("lesson_4", "")
    typed = bool(txid)
    if not txid:
        txid = own_hash
    if not txid:
        return _fail(5, CampError(
            code="NO_TRANSACTION",
            message="There is no transaction to verify yet.",
            hint="Run 'xrpl-camp send --memo \"your message\"' first, or 'xrpl-camp start'.",
            exit_code=1,
        ))

    # "Ours" means this run produced the hash. It decides two behaviours: a
    # hash the flow just submitted is worth waiting out (it may still be
    # settling), and a hash somebody typed is worth checking for shape before
    # any network call. Keyed off provenance, never off a heuristic - getting
    # it backwards would make a fresh transaction look permanently missing.
    ours = dry_run or not typed or txid == own_hash
    if not ours and not is_tx_hash(txid):
        return _fail(5, bad_hash_error(txid))

    console.print(Panel(
        "[bold]Lesson 5: Verify a Transaction[/bold]\n\n"
        "Anyone can look up any transaction on the XRPL.\n"
        "No login needed. No API key. Just the transaction hash.",
        title="XRPL Camp",
        border_style="blue",
    ))

    if dry_run:
        _dry_run_banner()
    _show_endpoint()

    console.print()

    # A lookup is a read: running it again cannot change the ledger, so a
    # transaction that has been submitted but not yet validated is worth
    # waiting for rather than reporting as a failure. A hash somebody TYPED is
    # a different question - "not yet" is the wrong answer for a typo, and
    # seven seconds of backoff is a bad way to say it.
    recorded_ledger = 0
    if txid == own_hash:
        record = session.get_progress(4)
        recorded_ledger = int(getattr(record, "ledger_index", 0) or 0)

    def still_settling(result: dict) -> CampError | None:
        if result.get("found", True):
            return None
        return not_found_error(txid) if ours else tx_unknown_error(txid)

    tx, err = try_network(
        "Looking up transaction...",
        lambda: transport.lookup_tx(
            txid, dry_run=dry_run, recorded_ledger_index=recorded_ledger,
        ),
        lookup_error,
        waiting="(asking the ledger what it recorded)",
        done="found.",
        check=still_settling,
    )
    if err is not None:
        return _fail(5, err)

    console.print()
    console.print(transaction_table(tx, txid))

    # Everything below is the actual verification. Without it, this lesson
    # prints a table of whatever came back and then congratulates the learner.
    problem = _verification_problem(
        tx, expected_memo, own_address=_own_address(session), dry_run=dry_run,
    )
    if problem is not None:
        if problem.code in ("VERIFY_NOT_YOURS", "VERIFY_NO_ACCOUNT"):
            # Looking it up was the right thing to have done - it is just not
            # this lesson. Keep the payoff, lose the credit.
            console.print(
                "\n  [dim]It is still a real entry on a public ledger, "
                "readable by anyone:[/dim]",
            )
            link = transport.explorer_url_for(txid)
            if link:
                _copyable(link, style="dim")
        console.print()
        return _fail(5, problem)

    if expected_memo:
        console.print(
            f"\n  [bold]You wrote:[/bold]        {escape(expected_memo)}"
            f"\n  [bold]Ledger returned:[/bold]  {escape(str(tx.get('memo', '')))}"
            "\n  [green]Identical.[/green] Not our copy of it — the ledger's.",
        )

    # Independent witness - the strongest anti-handwaving beat, and the one
    # place in the product where the learner is asked to leave and check. Both
    # the hash and the URL are printed unbroken: a link that wraps mid-hash is
    # a link that 404s when you copy the line you can see.
    explorer = transport.explorer_url_for(txid)
    console.print(
        "\n  [bold]You don't have to trust this tool.[/bold]"
        "\n  Verify it yourself — this is the full hash:",
    )
    console.print(f"  [bold]{escape(str(tx.get('hash', txid)))}[/bold]",
                  soft_wrap=True, highlight=False)
    if explorer:
        console.print("  [dim]and this is where to look it up:[/dim]")
        _copyable(explorer)

    if not dry_run:
        ledger_index = int(tx.get("ledger_index") or 0)
        close_time = str(tx.get("close_time_iso") or "")
        session.mark_complete(
            5, LESSON_NAMES[5], started_at=ts, duration_seconds=_elapsed(t0),
            ledger_index=ledger_index, close_time_iso=close_time,
        )
        # The ledger's own answer for the lesson-4 write, back into the
        # lesson-4 record. This is what lets a sealed pack tell a Testnet reset
        # (the recorded ledger predates the endpoint's history) from a forgery.
        if ledger_index and txid and txid == own_hash:
            session.record_entry(
                4, txid=txid, ledger_index=ledger_index, close_time_iso=close_time,
            )
        session.save()

    console.print(
        "\n  [green]✓ Independently verified.[/green] "
        "No login, no API key — just the hash and the open ledger.",
    )
    return LessonResult(lesson=5, ok=True, txid=txid, memo=str(tx.get("memo", "")))


def transaction_table(tx: dict, txid: str = "") -> Table:
    """The details table for one transaction. Shared by `verify` and `read`."""
    table = Table(title="Transaction Details")
    table.add_column("Field", style="bold")
    # `fold` rather than the default ellipsis: at 80 columns the Hash cell was
    # truncated to '04183C...3637...', so the complete hash appeared nowhere on
    # screen in a form the learner could copy. Folding wraps it; nothing is
    # thrown away.
    table.add_column("Value", overflow="fold")

    def cell(value: object) -> str:
        return escape(str(value))

    def drops(value: object) -> str:
        """'1 drop' / '10 drops' - the same unit lesson the panel gives."""
        text = str(value)
        return escape(f"{text} drop{'' if text.strip() == '1' else 's'}")

    table.add_row("Hash", cell(tx.get("hash", txid)))
    table.add_row("From", cell(tx.get("account", "")))
    table.add_row("To", cell(tx.get("destination", "")))
    table.add_row("Amount", drops(tx.get("amount", "")))
    if tx.get("delivered"):
        table.add_row("Delivered", drops(tx["delivered"]))
    table.add_row("Fee", drops(tx.get("fee", "")))
    table.add_row("Memo (readback)", cell(tx.get("memo", "")))
    table.add_row("Ledger", cell(tx.get("ledger_index", "")))
    if tx.get("close_time_iso"):
        table.add_row("Time", cell(tx["close_time_iso"]))
    table.add_row("Result", cell(tx.get("result", "")))
    if "validated" in tx:
        table.add_row("Validated", cell(tx["validated"]))
    return table


def _own_address(session: Session) -> str:
    """The learner's own address: the session's, else the wallet on disk."""
    address = str(getattr(session, "wallet_address", "") or "").strip()
    if address:
        return address
    try:
        record = wallet.load_wallet()
    except Exception:
        return ""
    return str(record.get("address", "")).strip() if record else ""


def _verification_problem(
    tx: dict,
    expected_memo: str,
    *,
    own_address: str = "",
    dry_run: bool = False,
) -> CampError | None:
    """Return a CampError if the looked-up transaction fails verification.

    The ownership check is the one that turns this from a display into a
    proof. Without it, ``verify --tx <a hash off the explorer>`` printed the
    details table, printed "Independently verified", exited 0 and marked
    lesson 5 complete — in a directory with no wallet, no funding and no
    payment. The lesson whose entire purpose is proving the record is the
    learner's own could not tell their record from a stranger's.

    Ordered so the more specific answer wins: a failed transaction is reported
    as failed, and a malformed response as malformed, before anything is said
    about whose it is.
    """
    result_code = str(tx.get("result", ""))
    if result_code and result_code != "tesSUCCESS":
        return verification_error(
            f"The ledger recorded that transaction as {result_code}, not a success.",
            detail=result_code,
        )

    missing = [
        label for label, key in (("sender", "account"), ("recipient", "destination"),
                                 ("amount", "amount"))
        if not str(tx.get(key, "")).strip()
    ]
    if missing:
        return verification_error(
            "The ledger's answer came back missing its " + ", ".join(missing) + ".",
            detail=f"keys present: {sorted(tx)}",
        )

    # A dry run's lookup returns "(dry run)" for every field, so there is
    # nothing here to own.
    if not dry_run:
        sender = str(tx.get("account", "")).strip()
        if not own_address:
            return no_account_yet_error()
        if sender != own_address:
            return not_your_transaction_error(sender, own_address)

    if expected_memo and str(tx.get("memo", "")) != expected_memo:
        return verification_error(
            "The memo on the ledger is not the memo that was sent.",
            detail=f"sent={expected_memo!r} readback={tx.get('memo', '')!r}",
        )
    return None


def lesson_6_certificate(
    session: Session,
    *,
    dry_run: bool = False,
    assume_complete: Iterable[int] = (),
    out_dir: str = "",
    fmt: str = "json",
) -> LessonResult:
    """Lesson 6: Generate a completion certificate and proof pack.

    Refuses to seal a record whose lessons did not happen. `assume_complete`
    carries lessons that succeeded in this process but were not persisted -
    that is only ever the dry-run flow, where nothing is written anyway.
    """
    ts, t0 = _start_timer()

    fmt_norm = str(fmt or "json").strip().lower()
    if fmt_norm not in CERTIFICATE_FORMATS:
        return _fail(6, CampError(
            code="BAD_FORMAT",
            message=f"Unknown certificate format '{fmt}'.",
            hint="Use --format json (default) or --format text.",
            exit_code=EXIT_USER,
        ))

    proven = set(assume_complete)
    missing = [n for n in range(1, 6) if not session.is_complete(n) and n not in proven]
    if missing:
        result = _fail(6, prerequisites_error(missing, LESSON_NAMES))
        console.print(
            "\n  [dim]A certificate is a claim about what you did. "
            "It only covers lessons you finished.[/dim]",
        )
        return result

    console.print(Panel(
        "[bold]Lesson 6: Your Certificate[/bold]\n\n"
        "It records what you did: the lessons you finished, what you\n"
        "sent, your public address, and the words you wrote. No seed,\n"
        "nothing private. Safe to share.\n\n"
        "The proof pack adds a SHA-256 hash, so an edit shows up. But\n"
        "the hash is not what makes it trustworthy — anyone can\n"
        "recompute one. What nobody can fake is the transaction: the\n"
        "pack names a hash on a public ledger, and that either exists\n"
        "or it doesn't.\n\n"
        "[dim]Testnet is reset from time to time and this copy goes with it.\n"
        "The mechanism is real; this particular record is not forever.[/dim]",
        title="XRPL Camp",
        border_style="blue",
    ))

    if dry_run:
        console.print(
            "\n  [bold yellow]⚠ SIMULATION[/bold yellow] — "
            "No artifacts generated in dry-run mode. Nothing was written.",
        )
        console.print(
            "  [dim]Run without --dry-run to generate your certificate "
            "and proof pack.[/dim]",
        )
        return LessonResult(lesson=6, ok=True)

    # Marked in memory so the certificate can include lesson 6, but persisted
    # only once the files it describes actually exist on disk.
    session.mark_complete(6, LESSON_NAMES[6], started_at=ts, duration_seconds=_elapsed(t0))

    folder = Path(out_dir).expanduser() if out_dir else None
    text_path: Path | None = None
    try:
        if folder is not None:
            folder.mkdir(parents=True, exist_ok=True)
        cert = generate_certificate(session)
        cert_path = save_certificate(
            cert, str(folder / CERTIFICATE_FILE) if folder else CERTIFICATE_FILE,
        )
        pack = generate_proof_pack(session)
        pack_path = save_proof_pack(
            pack, str(folder / PROOF_PACK_FILE) if folder else PROOF_PACK_FILE,
        )
        if fmt_norm == "text":
            text_path = save_certificate_text(
                cert,
                str(folder / CERTIFICATE_TEXT_FILE) if folder else CERTIFICATE_TEXT_FILE,
                pack_file=Path(pack_path).name,
            )
    except OSError as exc:
        return _fail(6, write_error(
            str(folder) if folder else "your certificate and proof pack",
            f"{type(exc).__name__}: {exc}",
        ))

    session.save()

    total = session.total_duration()
    duration_str = format_duration(total) if total > 0 else "n/a"

    # Completion bundle - one coherent handoff block
    txid = session.txids.get("lesson_4", "")
    explorer = transport.explorer_url_for(txid)

    # Absolute paths. These were bare relative names, resolved against
    # whatever directory the terminal happened to open in - so a learner told
    # "this is yours to keep" had no way to find it once they closed the
    # window, and nothing else in the CLI could answer "where did it go".
    cert_path = Path(cert_path).resolve()
    pack_path = Path(pack_path).resolve()
    if text_path is not None:
        text_path = Path(text_path).resolve()

    lines = [
        "[bold]Your completion bundle:[/bold]\n",
        f"  Certificate:  {escape(str(cert_path))}",
        f"  Proof pack:   {escape(str(pack_path))}",
    ]
    if text_path is not None:
        lines.append(f"  Keepsake:     {escape(str(text_path))}")
    lines.extend([
        f"\n  Address:      {escape(str(cert['address']))}",
        f"  Lessons:      {len(cert['completed'])}",
        f"  Duration:     {duration_str}",
        f"  SHA-256:      {escape(str(pack['sha256']))}",
        "\n  [dim]Verify your proof pack anytime:[/dim]"
        f"\n  [dim]xrpl-camp proof verify {escape(pack_path.name)}[/dim]",
    ])

    console.print(Panel(
        "\n".join(lines),
        title="XRPL Camp — Complete",
        border_style="green",
    ))

    # Outside the panel on purpose: a panel border forces the URL to wrap, and
    # a wrapped explorer link is one the learner cannot copy.
    if explorer:
        console.print("\n  [dim]Your transaction on the public ledger:[/dim]")
        _copyable(explorer)

    console.print("\n  [dim]Copy to share:[/dim]")
    console.print(
        share_text(cert, pack_file=pack_path.name),
        markup=False,
        highlight=False,
        soft_wrap=True,
    )

    console.print(
        "\n  [green]✓ Record sealed.[/green] "
        "This is yours to keep — and anyone can check it against the ledger.",
    )
    console.print(
        "  [dim]A next step after camp: xrpl-camp reserve — "
        "watch the owner reserve lock and come back.[/dim]",
    )
    return LessonResult(lesson=6, ok=True)


# ---------------------------------------------------------------------------
# read - the diary, and everybody else's
# ---------------------------------------------------------------------------

#: Rows `read` will render at most. AccountTx is a heavier call than Tx, and a
#: stranger's account can carry an arbitrary amount of history.
READ_LIMIT_DEFAULT = 20
READ_LIMIT_MAX = 100


def _need(name: str):
    """A transport function, or a structured error instead of an AttributeError."""
    fn = getattr(transport, name, None)
    if not callable(fn):
        raise CampFailure(unsupported_feature_error(f"transport.{name}"))
    return fn


def _entry_row(entry: object, *, viewing: str) -> tuple[str, str]:
    """One ledger write, as (headline, memo). Everything escaped."""
    ledger = int(getattr(entry, "ledger_index", 0) or 0)
    when = str(getattr(entry, "close_time_iso", "") or "")
    outgoing = bool(getattr(entry, "outgoing", True))
    other = str(
        (getattr(entry, "destination", "") if outgoing else getattr(entry, "account", ""))
        or "",
    )
    amount = int(getattr(entry, "amount_drops", 0) or 0)
    arrow = "→" if outgoing else "←"
    head = f"[bold]{ledger:,}[/bold]  [dim]{escape(when)}[/dim]  {arrow} {escape(other or viewing)}"
    if amount:
        head += f"  [dim]{amount:,} drop{'' if amount == 1 else 's'}[/dim]"
    return head, str(getattr(entry, "memo", "") or "")


def read_account(address: str, *, own: bool, limit: int = READ_LIMIT_DEFAULT) -> int:
    """Print what the ledger has recorded for `address`. Exit code."""
    limit = max(1, min(READ_LIMIT_MAX, int(limit)))
    fetch = _need("account_transactions")

    entries, err = try_network(
        "Asking the ledger...",
        lambda: fetch(address, limit=limit),
        lookup_error,
        waiting="(reading a public account — no key, no login)",
        done="read.",
    )
    if err is not None:
        _report(err, command="read")
        return err.exit_code

    rows = sorted(
        list(entries or []),
        key=lambda e: int(getattr(e, "ledger_index", 0) or 0),
    )
    if own:
        console.print(
            f"\n  [bold]{escape(address)}[/bold] — your entries, read back "
            "[bold]off the ledger[/bold], not off this machine.",
        )
    else:
        console.print(
            f"\n  [bold]{escape(address)}[/bold] — somebody else's public history. "
            "You needed no key and nobody's permission to read it.",
        )

    if not rows:
        console.print(
            "\n  [dim]Nothing recorded for that account yet.[/dim]"
            + ("\n  [dim]Write something with: xrpl-camp send --memo \"...\"[/dim]"
               if own else ""),
        )
        return EXIT_OK

    console.print()
    written = 0
    for entry in rows:
        head, memo = _entry_row(entry, viewing=address)
        console.print(f"  {head}")
        if memo:
            written += 1
            console.print(f'      [cyan]"{escape(memo)}"[/cyan]')
    console.print(
        f"\n  [dim]{len(rows)} transaction{'' if len(rows) == 1 else 's'}, "
        f"{written} carrying words. None of this is stored here — it came back "
        "from the network.[/dim]",
    )
    return EXIT_OK


def read_transaction(txid: str) -> int:
    """Print one transaction, whoever sent it. Exit code."""
    def missing(result: dict) -> CampError | None:
        return None if result.get("found", True) else tx_unknown_error(txid)

    tx, err = try_network(
        "Looking it up...",
        lambda: transport.lookup_tx(txid),
        lookup_error,
        waiting="(one hash, no login, no API key)",
        done="found.",
        check=missing,
    )
    if err is not None:
        _report(err, command="read")
        return err.exit_code

    console.print()
    console.print(transaction_table(tx, txid))
    link = transport.explorer_url_for(txid)
    if link:
        console.print("\n  [dim]On the public ledger, where anyone can check it:[/dim]")
        _copyable(link, style="dim")
    return EXIT_OK


def read_ledger(
    target: str = "", *, session: Session | None = None, limit: int = READ_LIMIT_DEFAULT,
) -> int:
    """`xrpl-camp read` — one verb, three questions.

    No argument reads YOUR entries back off the ledger rather than out of
    session.json: reading local state would make this a text file in a
    blockchain costume. An address reads what somebody else wrote — the
    neighbour across the room, or the genesis account. A hash reads one
    transaction. All three need no key, no account and no permission, which is
    the claim lesson 2 makes and nothing in the product demonstrated.
    """
    target = str(target or "").strip()

    if not target:
        address = _own_address(session) if session is not None else ""
        if not address:
            _report(wallet_missing_error(), command="read")
            return EXIT_USER
        return read_account(address, own=True, limit=limit)

    if is_tx_hash(target):
        return read_transaction(target)

    # An address before a near-miss hash: 64 hex characters is unambiguous, and
    # anything else that starts with 'r' is far likelier to be an address typed
    # slightly wrong than a hash.
    if is_valid_address(target):
        own = session is not None and target == _own_address(session)
        return read_account(target, own=own, limit=limit)

    if target[:1] == "r":
        _report(bad_address_error(target), command="read")
        return EXIT_USER
    if len(target) >= 40:
        _report(bad_hash_error(target), command="read")
        return EXIT_USER
    _report(unknown_target_error(target), command="read")
    return EXIT_USER


# ---------------------------------------------------------------------------
# try - failure as curriculum, for nothing
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TryOutcome:
    """What one deliberate failure did, and what it would have cost."""

    key: str
    title: str
    layer: str
    code: str
    lesson: str
    reached_ledger: bool
    cost_drops: int
    ok: bool = True


#: Where a rejection was caught. Four layers stand between a mistyped
#: character and a permanent, fee-paid row, and the learner meets all of them.
LAYER_CODEC = "your machine, before anything is built"
LAYER_LIBRARY = "the library, before anything is signed"
LAYER_SERVER = "the server, before consensus"
LAYER_LEDGER = "the ledger itself"

#: Result prefixes that are applied to a ledger. `tec` is the one that costs:
#: the transaction failed AND it is on the chain forever, fee paid.
COSTLY_PREFIXES = ("tec", "tes")

#: What a Testnet transaction costs when it reaches the ledger.
LEDGER_COST_DROPS = 10


def _prefix(code: str) -> str:
    """The three-letter class of an engine result: tec / tem / tel / tef / tes."""
    return code[:3] if len(code) >= 3 else ""


def _simulated(tx, *, key: str, title: str, lesson: str) -> TryOutcome:
    """Run one transaction through `simulate`: 0 drops, no signature, ~0.5s."""
    simulate = _need("simulate_tx")
    outcome = simulate(tx)
    code = str(getattr(outcome, "engine_result", "") or "")
    prefix = str(getattr(outcome, "prefix", "") or _prefix(code))
    costly = prefix in COSTLY_PREFIXES
    return TryOutcome(
        key=key, title=title, layer=LAYER_LEDGER if costly else LAYER_SERVER,
        code=code, lesson=lesson, reached_ledger=costly,
        cost_drops=LEDGER_COST_DROPS if costly else 0,
    )


def _payment(**fields):
    """A Payment model, built here so `try` never touches the signing path."""
    from xrpl.models import Payment

    return Payment(**fields)


def _try_bad_address(address: str) -> TryOutcome:
    """Change one character of a real address and watch it refuse, offline."""
    broken = address[:-1] + ("A" if address[-1] != "A" else "B")
    valid = is_valid_address(broken)
    console.print(f"  [dim]Sending to:[/dim] {escape(broken)}  [dim](one character off)[/dim]")
    return TryOutcome(
        key="address", title="A mistyped address", layer=LAYER_CODEC,
        code="refused" if not valid else "ACCEPTED",
        lesson=(
            "An XRPL address carries its own checksum, so this never left your "
            "machine. You cannot send to an address that does not exist because "
            "you cannot type one by accident."
        ),
        reached_ledger=False, cost_drops=0, ok=not valid,
    )


def _try_self_payment(address: str) -> TryOutcome:
    """The library refuses to build it. Nothing is signed, nothing is sent."""
    code = "temREDUNDANT"
    try:
        _payment(account=address, destination=address, amount="1")
    except Exception as exc:
        code = type(exc).__name__
    console.print(f"  [dim]Sending to:[/dim] {escape(address)}  [dim](yourself)[/dim]")
    return TryOutcome(
        key="self", title="A payment to yourself", layer=LAYER_LIBRARY,
        code=code,
        lesson=(
            "The ledger would reject this as temREDUNDANT, but it never got the "
            "chance: the library refused to build the transaction at all."
        ),
        reached_ledger=False, cost_drops=0,
    )


def _try_low_fee(address: str, destination: str) -> TryOutcome:
    """A fee below what the server will relay. Rejected locally, costs nothing."""
    return _simulated(
        _payment(account=address, destination=destination, amount="1", fee="1"),
        key="fee", title="A fee that is too small",
        lesson=(
            "The server would not even pass it on. A transaction rejected here "
            "never reaches consensus and never costs anything — which is why "
            "the fee is a queue, not a charge."
        ),
    )


def _try_past_sequence(address: str, destination: str) -> TryOutcome:
    """Replay an old sequence number. This is why you cannot be double-charged."""
    return _simulated(
        _payment(account=address, destination=destination, amount="1", sequence=1),
        key="replay", title="Sending the same transaction twice",
        lesson=(
            "Every transaction carries a sequence number and each one can be "
            "used once. Replay a signed transaction and the ledger has already "
            "moved past it. This is why nobody can charge you twice. "
            # 1.4.2: the preview's code isn't the one a real submission gets,
            # and the lesson used to leave the learner to puzzle that out
            # (Book Keeper, 1.4.1 live check).
            "(This preview answers telCAN_NOT_QUEUE, because the server cannot "
            "queue a transaction whose sequence has passed. Submitted for real, "
            "the same transaction is refused with tefPAST_SEQ. Neither costs "
            "anything.)"
        ),
    )


def _try_no_destination(address: str) -> TryOutcome:
    """One drop to an address nobody has funded: too little to create it."""
    from xrpl.wallet import Wallet

    stranger = Wallet.create().address
    console.print(f"  [dim]Sending 1 drop to:[/dim] {escape(stranger)}  [dim](brand new)[/dim]")
    return _simulated(
        _payment(account=address, destination=stranger, amount="1"),
        key="nodest", title="One drop to an account that does not exist",
        lesson=(
            "An account has to be funded to at least the base reserve before it "
            "exists at all. One drop is not enough to bring it into being — and "
            "this is the first failure so far that would have reached the ledger."
        ),
    )


def _try_unfunded(address: str, destination: str, spendable: int) -> TryOutcome:
    """Spend almost everything. The reserve stops being a number and starts biting."""
    amount = max(1, spendable + 2_000_000)
    console.print(f"  [dim]Sending:[/dim] {_drops_line(amount)}  [dim](more than you have)[/dim]")
    return _simulated(
        _payment(account=address, destination=destination, amount=str(amount)),
        key="broke", title="Spending more than the reserve leaves you",
        lesson=(
            "Your balance is not your spendable balance. The reserve is locked "
            "for as long as the account exists, and a payment that ignores it "
            "lands on the ledger as a failure you paid for."
        ),
    )


def _try_missing_hash() -> TryOutcome:
    """Look up a hash that was never real. A read: it cannot cost anything."""
    import hashlib

    fake = hashlib.sha256(b"xrpl-camp: a transaction nobody ever sent").hexdigest().upper()
    console.print(f"  [dim]Looking up:[/dim] {escape(fake)}")
    found = True
    try:
        found = bool(transport.lookup_tx(fake).get("found", False))
    except Exception:
        found = False
    return TryOutcome(
        key="hash", title="A hash that was never real", layer=LAYER_LEDGER,
        code="txnNotFound" if not found else "FOUND",
        lesson=(
            "That is a perfectly well-formed hash. It is just not a transaction. "
            "The ledger does not guess, and reading is free, so asking cost "
            "nothing at all."
        ),
        reached_ledger=False, cost_drops=0, ok=not found,
    )


#: The cases, in the order they teach best: the two that never touch the wire,
#: then the free network ones, then the two that would have cost real drops.
TRY_CASES = ("address", "self", "fee", "hash", "replay", "nodest", "broke")


def run_try(case: str = "") -> int:
    """`xrpl-camp try` — break it on purpose, on the real network, for nothing.

    Every network case goes through ``simulate``: the real ledger, the real
    engine result, the metadata it WOULD have written, no signature, and zero
    drops. Doing this for real cost 30 drops and left three junk `tec` rows on
    the chain, which is exactly the lesson — three letters tell you which
    failures are free and which are permanent.
    """
    wanted = str(case or "").strip().lower()
    if wanted and wanted not in TRY_CASES:
        _report(CampError(
            code="BAD_CASE",
            message=f"There is no failure called '{wanted}'.",
            hint="Try one of: " + ", ".join(TRY_CASES) + " — or 'xrpl-camp try' for all.",
            exit_code=EXIT_USER,
        ), command="try")
        return EXIT_USER

    w, err = _require_wallet()
    if err is not None:
        _report(err, command="try")
        return err.exit_code
    address = str(w["address"])

    endpoint_problem = check_endpoint()
    if endpoint_problem is not None:
        _report(endpoint_problem, command="try")
        return endpoint_problem.exit_code

    console.print(Panel(
        "[bold]Breaking it on purpose[/bold]\n\n"
        "Every one of these runs against the live network and none of them\n"
        "signs anything, sends anything or costs a drop. The ledger tells us\n"
        "exactly what it [bold]would[/bold] have done.",
        title="XRPL Camp — try",
        border_style="blue",
    ))

    destination = _read_mailbox_or_self(address)
    spendable = 0
    facts = _reserve_facts(address)
    if facts:
        spendable = int(facts.get("spendable_drops", 0) or 0)

    runners = {
        "address": lambda: _try_bad_address(address),
        "self": lambda: _try_self_payment(address),
        "fee": lambda: _try_low_fee(address, destination),
        "hash": _try_missing_hash,
        "replay": lambda: _try_past_sequence(address, destination),
        "nodest": lambda: _try_no_destination(address),
        "broke": lambda: _try_unfunded(address, destination, spendable),
    }

    keys = [wanted] if wanted else list(TRY_CASES)
    outcomes: list[TryOutcome] = []
    for key in keys:
        console.print(f"\n  [bold]{escape(TRY_TITLES[key])}[/bold]")
        try:
            outcome = runners[key]()
        except CampFailure as exc:
            _report(exc.error, command=f"try {key}")
            return exc.exit_code
        except Exception as exc:
            problem = _classify(exc, simulate_error, account=address)
            _report(problem, command=f"try {key}")
            return problem.exit_code
        outcomes.append(outcome)
        _show_outcome(outcome)

    _try_receipt(outcomes)
    return EXIT_OK


#: Headline per case, shown before it runs so the learner knows what is coming.
TRY_TITLES = {
    "address": "Send to an address with one character wrong",
    "self": "Send a payment to yourself",
    "fee": "Offer a fee the network will not relay",
    "hash": "Look up a transaction that never existed",
    "replay": "Send the same transaction a second time",
    "nodest": "Send one drop to an account that does not exist",
    "broke": "Spend more than you have",
}


def _read_mailbox_or_self(address: str) -> str:
    """A destination for the simulations. Never the sender - the XRPL refuses that."""
    from xrpl.wallet import Wallet

    try:
        record = wallet.load_mailbox()
    except Exception:
        record = None
    box = str((record or {}).get("address", "") or "")
    return box if box and box != address else Wallet.create().address


def _show_outcome(outcome: TryOutcome) -> None:
    """One result: the code, where it was caught, and what it teaches."""
    colour = "red" if outcome.reached_ledger else "green"
    console.print(
        f"  [{colour}]{escape(outcome.code or 'no result')}[/{colour}]"
        f"  [dim]caught by {escape(outcome.layer)}[/dim]",
    )
    console.print(f"  {escape(outcome.lesson)}")
    if outcome.reached_ledger:
        console.print(
            f"  [yellow]For real, this one lands on the ledger and costs "
            f"{outcome.cost_drops} drops. It cost 0 here.[/yellow]",
        )


def _try_receipt(outcomes: list[TryOutcome]) -> None:
    """The payoff: which prefixes cost you, and what this all would have cost."""
    if not outcomes:
        return
    landed = [o for o in outcomes if o.reached_ledger]
    free = [o for o in outcomes if not o.reached_ledger]
    spent = sum(o.cost_drops for o in landed)
    lines = [
        f"[bold]{len(outcomes)} deliberate failure"
        f"{'' if len(outcomes) == 1 else 's'}. This run cost 0 drops.[/bold]\n",
        f"  [green]{len(free)} free[/green]   — refused before the ledger ever saw them",
        f"  [red]{len(landed)} costly[/red] — would have landed, "
        f"{spent} drops and a permanent row",
        "\n[bold]The first three letters tell you which, before you press send:[/bold]",
        "  [green]tem tel tef[/green]  malformed, rejected locally, already stale — "
        "never applied, never charged",
        "  [red]tec[/red]          the ledger accepted the transaction and "
        "recorded that it failed. You pay.",
        "  [green]tes[/green]          success",
    ]
    console.print()
    console.print(Panel(
        "\n".join(lines), title="The receipt", border_style="green",
    ))


# ---------------------------------------------------------------------------
# reserve - watch the owner reserve lock and come back
# ---------------------------------------------------------------------------

RESERVE_NFT_URI = "xrpl-camp"
RESERVE_NFT_URI_HEX = RESERVE_NFT_URI.encode("utf-8").hex().upper()
RESERVE_NFT_TAXON = 0
DRY_RUN_NFTOKEN_ID = "00080000" + "0" * 56


def _signed_drops_line(drops: int) -> str:
    """'+200,000 drops (+0.200000 XRP)' / '-10 drops (-0.000010 XRP)'."""
    unit = "drop" if abs(drops) == 1 else "drops"
    sign = "+" if drops > 0 else ""
    return f"{sign}{drops:,} {unit} ({sign}{drops / 1_000_000:.6f} XRP)"


def _camp_nftoken_id(nft: object) -> str:
    """Return the NFTokenID if `nft` is an xrpl-camp reserve token (uri 'xrpl-camp', taxon 0)."""
    if not isinstance(nft, dict):
        return ""
    token_id = str(nft.get("NFTokenID") or nft.get("nftoken_id") or "").strip()
    if not token_id:
        return ""
    raw_taxon = nft.get("NFTokenTaxon", nft.get("nftoken_taxon", nft.get("taxon", 0)))
    try:
        taxon = int(raw_taxon if raw_taxon is not None else 0)
    except (TypeError, ValueError):
        return ""
    if taxon != RESERVE_NFT_TAXON:
        return ""
    raw_uri = str(nft.get("URI") if "URI" in nft else nft.get("uri", "") or "").strip()
    if raw_uri == RESERVE_NFT_URI or raw_uri.upper() == RESERVE_NFT_URI_HEX:
        return token_id
    return ""


def _burn_failed_error(nftoken_id: str, exc: Exception) -> CampError:
    """Structured error when burning an NFT fails."""
    base = _classify(exc, send_error)
    return CampError(
        code="RESERVE_BURN_FAILED",
        message=(
            f"Could not burn NFTokenID {nftoken_id}: {base.message}"
        ),
        hint=(
            f"The token ({nftoken_id}) is still on your account. "
            "Running 'xrpl-camp reserve' again burns it and releases the reserve."
        ),
        retryable=True,
        detail=base.detail,
        exit_code=base.exit_code or EXIT_RUNTIME,
    )


def _simulated_reserve_moves() -> tuple[transport.ReserveMove, transport.ReserveMove]:
    """Simulated mint and burn moves for `reserve --dry-run`. No network calls."""
    inc = int(transport.DEFAULT_RESERVE_INC_DROPS)
    fee = int(LEDGER_COST_DROPS)
    bal0 = int(transport.DRY_RUN_BALANCE_DROPS)
    spend0 = bal0 - int(transport.DEFAULT_RESERVE_BASE_DROPS)

    bal1 = bal0 - fee
    spend1 = spend0 - inc - fee
    mint_move = transport.ReserveMove(
        txid=transport.DRY_RUN_TXID,
        engine_result="tesSUCCESS (simulated)",
        owner_count_before=0,
        owner_count_after=1,
        balance_before=bal0,
        balance_after=bal1,
        spendable_before=spend0,
        spendable_after=spend1,
        ledger_index=0,
        close_time_iso="",
        nftoken_id=DRY_RUN_NFTOKEN_ID,
    )

    bal2 = bal1 - fee
    spend2 = spend1 + inc - fee
    burn_move = transport.ReserveMove(
        txid=transport.DRY_RUN_TXID,
        engine_result="tesSUCCESS (simulated)",
        owner_count_before=1,
        owner_count_after=0,
        balance_before=bal1,
        balance_after=bal2,
        spendable_before=spend1,
        spendable_after=spend2,
        ledger_index=0,
        close_time_iso="",
        nftoken_id=DRY_RUN_NFTOKEN_ID,
    )
    return mint_move, burn_move


def _reserve_move_to_dict(
    move: transport.ReserveMove, *, network: str, simulated: bool = False,
) -> dict:
    """Serialize a ReserveMove (including computed deltas) for `--json`."""
    delta = int(move.reserve_delta)
    status = "locked" if delta > 0 else ("released" if delta < 0 else "unchanged")
    return {
        "txid": move.txid,
        "engine_result": move.engine_result,
        "owner_count_before": move.owner_count_before,
        "owner_count_after": move.owner_count_after,
        "owner_count_delta": move.owner_count_delta,
        "balance_before": move.balance_before,
        "balance_after": move.balance_after,
        "balance_delta": move.balance_delta,
        "spendable_before": move.spendable_before,
        "spendable_after": move.spendable_after,
        "spendable_delta": move.spendable_delta,
        "reserve_delta": delta,
        "reserve_status": status,
        "ledger_index": move.ledger_index,
        "close_time_iso": move.close_time_iso,
        "nftoken_id": move.nftoken_id,
        "explorer_url": (
            "" if simulated
            else transport.explorer_url_for_network(move.txid, network)
        ),
    }


def _reserve_move_table(
    step_title: str, move: transport.ReserveMove, *, simulated: bool = False,
) -> Table:
    """Table showing OwnerCount, balance, and spendable XRP before/after with deltas."""
    tag = " (simulated)" if simulated else ""
    table = Table(title=f"{step_title}{tag}")
    table.add_column("Field", style="bold")
    table.add_column("Before", justify="right")
    table.add_column("After", justify="right")
    table.add_column("Delta", justify="right")

    table.add_row(
        "OwnerCount",
        f"{move.owner_count_before}",
        f"{move.owner_count_after}",
        f"{move.owner_count_delta:+d}",
    )
    table.add_row(
        "Balance",
        escape(_drops_line(move.balance_before)),
        escape(_drops_line(move.balance_after)),
        escape(_signed_drops_line(move.balance_delta)),
    )
    table.add_row(
        "Spendable",
        escape(_drops_line(move.spendable_before)),
        escape(_drops_line(move.spendable_after)),
        escape(_signed_drops_line(move.spendable_delta)),
    )
    r_delta = int(move.reserve_delta)
    if r_delta > 0:
        r_cell = f"+{_drops_line(r_delta)} locked"
    elif r_delta < 0:
        r_cell = f"{_signed_drops_line(r_delta)} released"
    else:
        r_cell = "0 drops (unchanged)"
    table.add_row("Owner reserve", "—", "—", escape(r_cell))
    return table


def _print_reserve_step(
    step_title: str,
    move: transport.ReserveMove,
    *,
    network: str,
    simulated: bool = False,
) -> None:
    """Render one reserve step (mint or burn) with its table, reserve line, and link."""
    console.print()
    console.print(_reserve_move_table(step_title, move, simulated=simulated))
    r_delta = int(move.reserve_delta)
    if r_delta > 0:
        console.print(
            f"  [bold]Reserve:[/bold] {_drops_line(r_delta)} [yellow]locked[/yellow] — "
            "held while you own the object, never spent.",
        )
    elif r_delta < 0:
        console.print(
            f"  [bold]Reserve:[/bold] {_drops_line(abs(r_delta))} [green]released[/green] — "
            "back in your spendable XRP.",
        )
    if not simulated and move.txid:
        console.print(f"  [bold]Transaction:[/bold] {escape(move.txid)}")
        link = transport.explorer_url_for_network(move.txid, network)
        if link:
            console.print("  [dim]Explorer:[/dim]")
            _copyable(link, style="dim")


@_honours_dry_run
def run_reserve(*, dry_run: bool = False, json_output: bool = False) -> int:
    """`xrpl-camp reserve` — mint an NFT, then burn it, and watch the reserve return."""
    global console

    previous_console = console
    if json_output:
        console = Console(stderr=True)
    try:
        return _run_reserve_inner(
            dry_run=bool(dry_run or is_dry_run()),
            json_output=json_output,
        )
    finally:
        if json_output:
            console = previous_console


def _run_reserve_inner(*, dry_run: bool, json_output: bool) -> int:
    import json as json_mod

    url = transport.get_rpc_url()
    network = transport.network_label_for_url(url)

    if dry_run:
        _dry_run_banner()
        console.print(Panel(
            "[bold]Watching the owner reserve lock and return (simulated)[/bold]\n\n"
            "Every object your account owns on the ledger locks an owner\n"
            "reserve increment. When the object is removed, that XRP comes\n"
            "straight back to your spendable balance.\n\n"
            "[dim]Simulated numbers: DEFAULT_RESERVE_INC_DROPS (200,000 drops)\n"
            "and a 10-drop fee per transaction. Nothing is signed or sent.[/dim]",
            title="XRPL Camp — reserve (simulated)",
            border_style="yellow",
        ))
        mint_move, burn_move = _simulated_reserve_moves()
        _print_reserve_step(
            "Step 1: Mint NFT (NFTokenMint)", mint_move, network=network, simulated=True,
        )
        _print_reserve_step(
            "Step 2: Burn NFT (NFTokenBurn)", burn_move, network=network, simulated=True,
        )
        total_fees = abs(mint_move.balance_delta + burn_move.balance_delta)
        console.print(
            f"\n  [bold yellow]Simulated:[/bold yellow] balance moved only by the two "
            f"fees ({total_fees:,} drops), while {mint_move.reserve_delta:,} drops were "
            "locked on the mint and released on the burn. Nothing was sent — dry run.",
        )
        if json_output:
            doc = {
                "simulated": True,
                "address": _own_address(None) or "rSimulatedCampAccount",
                "network": network,
                "endpoint": url,
                "leftover_burned": [],
                "mint": _reserve_move_to_dict(mint_move, network=network, simulated=True),
                "burn": _reserve_move_to_dict(burn_move, network=network, simulated=True),
                "moves": [
                    _reserve_move_to_dict(mint_move, network=network, simulated=True),
                    _reserve_move_to_dict(burn_move, network=network, simulated=True),
                ],
                "net_balance_delta": mint_move.balance_delta + burn_move.balance_delta,
                "net_spendable_delta": mint_move.spendable_delta + burn_move.spendable_delta,
                "net_reserve_delta": mint_move.reserve_delta + burn_move.reserve_delta,
            }
            print(json_mod.dumps(doc, indent=2))
        return EXIT_OK

    w, err = _require_wallet()
    if err is not None:
        _report(err, command="reserve")
        return err.exit_code
    address = str(w["address"])
    seed = str(w["seed"])

    _show_endpoint()
    endpoint_problem = check_endpoint()
    if endpoint_problem is not None:
        _report(endpoint_problem, command="reserve")
        return endpoint_problem.exit_code

    console.print(Panel(
        "[bold]Watching the owner reserve lock and return[/bold]\n\n"
        "Two real Testnet transactions from your wallet: an NFTokenMint,\n"
        "then an NFTokenBurn of that same token.\n\n"
        "Watch the two columns: your [bold]balance[/bold] moves only by the\n"
        "fee (~10 drops each), while your [bold]spendable[/bold] XRP drops by\n"
        "the owner reserve increment on the mint and comes back on the burn.\n"
        "The reserve is held, then released, never spent.",
        title="XRPL Camp — reserve",
        border_style="blue",
    ))

    # Before minting, check for any leftover xrpl-camp token from an interrupted run.
    try:
        owned_nfts = transport.account_nfts(address)
    except (transport.XRPLUnfundedAccount, transport.XRPLAccountNotFound) as exc:
        err = unfunded_error(detail=f"{type(exc).__name__}: {exc}")
        if isinstance(exc, transport.XRPLUnfundedAccount) and str(exc):
            err.message = str(exc)
        _report(err, command="reserve")
        return err.exit_code
    except Exception as exc:
        err = _classify(exc, lookup_error, account=address)
        _report(err, command="reserve")
        return err.exit_code

    leftover_ids = [
        tid for tid in (_camp_nftoken_id(item) for item in (owned_nfts or [])) if tid
    ]
    for leftover_id in leftover_ids:
        console.print(
            f"\n  [yellow]Leftover xrpl-camp token from an earlier reserve run found "
            f"({escape(leftover_id)}); burning it first...[/yellow]",
        )
        try:
            with _working("Burning leftover NFT...", done="burned."):
                transport.burn_nft(seed, leftover_id)
        except Exception as exc:
            err = _burn_failed_error(leftover_id, exc)
            _report(err, command="reserve")
            return err.exit_code

    # Step 1: Mint NFT
    console.print()
    try:
        with _working(
            "Step 1: Minting an xrpl-camp NFT (locking one owner reserve)...",
            done="minted.",
        ):
            mint_move = transport.mint_nft(
                seed, uri=RESERVE_NFT_URI, taxon=RESERVE_NFT_TAXON,
            )
    except (transport.XRPLUnfundedAccount, transport.XRPLAccountNotFound) as exc:
        err = unfunded_error(detail=f"{type(exc).__name__}: {exc}")
        if isinstance(exc, transport.XRPLUnfundedAccount) and str(exc):
            err.message = str(exc)
        _report(err, command="reserve")
        return err.exit_code
    except Exception as exc:
        err = _classify(exc, send_error, account=address)
        _report(err, command="reserve")
        return err.exit_code

    _print_reserve_step(
        "Step 1: Mint NFT (NFTokenMint)", mint_move, network=network, simulated=False,
    )

    # Step 2: Burn that NFT
    token_id = str(mint_move.nftoken_id or "")
    console.print()
    try:
        with _working(
            "Step 2: Burning that NFT (releasing the owner reserve)...",
            done="burned.",
        ):
            burn_move = transport.burn_nft(seed, token_id)
    except Exception as exc:
        err = _burn_failed_error(token_id or "(unknown NFTokenID)", exc)
        _report(err, command="reserve")
        return err.exit_code

    _print_reserve_step(
        "Step 2: Burn NFT (NFTokenBurn)", burn_move, network=network, simulated=False,
    )

    total_fees = abs(mint_move.balance_delta + burn_move.balance_delta)
    console.print(
        f"\n  [green]✓ Reserve returned.[/green] Total cost: {total_fees:,} drops in fees. "
        f"The {mint_move.reserve_delta:,}-drop owner reserve was locked on the mint "
        "and released on the burn — never spent.",
    )

    if json_output:
        doc = {
            "simulated": False,
            "address": address,
            "network": network,
            "endpoint": url,
            "leftover_burned": leftover_ids,
            "mint": _reserve_move_to_dict(mint_move, network=network, simulated=False),
            "burn": _reserve_move_to_dict(burn_move, network=network, simulated=False),
            "moves": [
                _reserve_move_to_dict(mint_move, network=network, simulated=False),
                _reserve_move_to_dict(burn_move, network=network, simulated=False),
            ],
            "net_balance_delta": mint_move.balance_delta + burn_move.balance_delta,
            "net_spendable_delta": mint_move.spendable_delta + burn_move.spendable_delta,
            "net_reserve_delta": mint_move.reserve_delta + burn_move.reserve_delta,
        }
        print(json_mod.dumps(doc, indent=2))
    return EXIT_OK


# ---------------------------------------------------------------------------
# Guided flow
# ---------------------------------------------------------------------------


#: The four claims the closing panel makes, and the lesson each one rests on.
COMPLETION_CLAIMS = (
    (2, "Created a cryptographic identity"),
    (3, "Funded it on a public network"),
    (4, "Wrote permanent words to the ledger"),
    (5, "Verified everything independently"),
)


def _halt(result: LessonResult) -> int:
    """Stop the guided flow on a failed lesson. Returns the exit code.

    This panel is now the ONLY rendering of the failure - `_fail` stays quiet
    while the guided flow is running - so it carries everything the loose block
    used to: the code to quote in a bug report, the retry note, and the pointer
    to --verbose when there is technical detail behind it.
    """
    name = LESSON_NAMES.get(result.lesson, "?")
    err = result.error
    body = [
        f"[bold]Stopped at Lesson {result.lesson} — {name}.[/bold]\n",
    ]
    if err is not None:
        body.append(f"[red]\\[{escape(err.code)}][/red] {escape(err.message)}")
        if err.hint:
            body.append(f"[dim]{escape(err.hint)}[/dim]")
        if err.retryable:
            body.append("[dim]This one is safe to run again.[/dim]")
        if err.detail:
            body.append(
                f"[dim]Detail: {escape(err.detail)}[/dim]" if is_verbose()
                else f"[dim]{escape(VERBOSE_POINTER.strip())}[/dim]"
            )
    body.append(
        "\nNothing was certified. Your progress up to here is saved.\n"
        "Fix the problem above, then run [bold]xrpl-camp start[/bold] — "
        "it picks up\nexactly where you stopped."
    )
    console.print(Panel(
        "\n".join(body),
        title="XRPL Camp — Paused",
        border_style="yellow",
    ))
    return result.exit_code


@_honours_dry_run
def run_guided_flow(*, dry_run: bool = False, memo: str = "") -> int:
    """Walk through all 6 lessons in sequence, auto-skipping completed ones.

    Returns a process exit code: 0 when every lesson in the run completed,
    non-zero when one failed. A failed lesson halts the flow - the run never
    walks past a failure into a certificate.

    ``memo`` is lesson 4's message, for the paths where nobody can be asked for
    one: `--yes`, a pipe, `| tee workshop.log`. Without it the learner's one
    permanent ledger entry was a machine token, chosen silently.
    """
    global _in_guided_flow

    _in_guided_flow = True
    try:
        return _guided_flow(dry_run=dry_run, memo=memo)
    finally:
        _in_guided_flow = False


def _guided_flow(*, dry_run: bool = False, memo: str = "") -> int:
    """The guided flow proper. See run_guided_flow."""
    # The wallet and models layers read the process-global execution mode, not
    # this parameter. cli._simulating() sets it before calling us, so the CLI
    # path was always correct - but a direct call with dry_run=True would still
    # write a real seed to disk, which is the opposite of what the argument
    # name promises. Set it here so the parameter means what it says from any
    # caller, including tests.
    set_execution_mode(ExecutionMode.DRY_RUN if dry_run else get_execution_mode())
    try:
        session = DryRunSession.get_or_create() if dry_run else Session.get_or_create()
    except (CampFailure, OSError, ValueError, TypeError, KeyError) as exc:
        err = exc.error if isinstance(exc, CampFailure) else state_corrupt_error(
            f"{type(exc).__name__}: {exc}",
        )
        _report(err)
        return err.exit_code

    skipped = sum(1 for i in range(1, 7) if session.is_complete(i))

    if skipped > 0 and skipped < 6:
        console.print(Panel(
            "[bold]Welcome back to XRPL Camp[/bold]\n\n"
            f"You've already completed {skipped} of 6 lessons.\n"
            "Picking up where you left off.",
            title="XRPL Camp",
            border_style="green",
        ))
    elif skipped == 6:
        console.print(Panel(
            "[bold]Welcome back to XRPL Camp[/bold]\n\n"
            "All 6 lessons are done. Nothing here needs doing again —\n"
            "but the network you joined has not stopped.",
            title="XRPL Camp",
            border_style="green",
        ))
        _what_now()
        console.print(
            "\n  [dim]xrpl-camp status for the checklist, "
            "xrpl-camp reset to wipe it and start over.[/dim]\n",
        )
        return EXIT_OK
    else:
        console.print(Panel(
            "[bold]Welcome to XRPL Camp[/bold]\n\n"
            "Six steps, about ten minutes. You'll make an account, fund it,\n"
            "write a permanent public sentence, and check that the ledger\n"
            "kept it — then walk out with a certificate anyone can verify.\n\n"
            "No real money. No sign-ups. Just you and the ledger.",
            title="XRPL Camp",
            border_style="green",
        ))

    if dry_run:
        _dry_run_banner()

    # Lessons proven in THIS process. In a real run this mirrors the session;
    # in a dry run it is the only record, because nothing is persisted.
    proven: set[int] = {n for n in range(1, 7) if session.is_complete(n)}
    txid = ""
    sent_memo = ""

    # Lesson 1
    if session.is_complete(1):
        _skip_banner(1, LESSON_NAMES[1])
    else:
        _pause()
        result = lesson_1_mental_model(session, dry_run=dry_run)
        if not result:
            return _halt(result)
        proven.add(1)

    # Lesson 2
    if session.is_complete(2):
        _skip_banner(2, LESSON_NAMES[2])
    else:
        _pause()
        result = lesson_2_create_wallet(session, dry_run=dry_run)
        if not result:
            return _halt(result)
        proven.add(2)

    # Lesson 3
    if session.is_complete(3):
        _skip_banner(3, LESSON_NAMES[3])
    else:
        _pause()
        result = lesson_3_fund_wallet(session, dry_run=dry_run)
        if not result:
            return _halt(result)
        proven.add(3)

    # Lesson 4 - interactive memo in guided mode
    if session.is_complete(4):
        _skip_banner(4, LESSON_NAMES[4])
        txid = session.txids.get("lesson_4", "")
    else:
        _pause()
        result = lesson_4_send_payment(
            session, memo=memo, dry_run=dry_run, interactive=True,
        )
        if not result:
            return _halt(result)
        proven.add(4)
        txid = result.txid
        sent_memo = result.memo

    if dry_run and not txid:
        txid = transport.DRY_RUN_TXID

    # Lesson 5
    if session.is_complete(5):
        _skip_banner(5, LESSON_NAMES[5])
    else:
        _pause()
        result = lesson_5_verify_tx(
            session, txid, dry_run=dry_run,
            expected_memo="" if dry_run else sent_memo,
        )
        if not result:
            return _halt(result)
        proven.add(5)

    # Lesson 6
    if session.is_complete(6):
        _skip_banner(6, LESSON_NAMES[6])
    else:
        _pause()
        result = lesson_6_certificate(session, dry_run=dry_run, assume_complete=proven)
        if not result:
            return _halt(result)
        proven.add(6)

    total = session.total_duration()
    duration_line = f"  Total time: {format_duration(total)}\n" if total > 0 else ""

    if dry_run:
        console.print(Panel(
            "[bold yellow]XRPL Camp — Dry Run Complete[/bold yellow]\n\n"
            "You've seen the whole flow in simulation mode.\n"
            "Nothing was saved and no transactions were sent.\n\n"
            "When you're ready, run [bold]xrpl-camp start[/bold] to do it for real.",
            title="Simulation",
            border_style="yellow",
        ))
        return EXIT_OK

    # Every claim below is read back off the session. The banner can only say
    # you did a thing if the record says you did it.
    #
    # ONE ending. Lesson 6 used to print a green 'XRPL Camp - Complete' panel,
    # then 'Record sealed', and then this printed a second green panel opening
    # with the same title - the ceremony firing twice with different words,
    # which flattens the strongest beat in the product. Lesson 6 owns the
    # artifacts; this owns what the learner actually did.
    claim_lines = []
    for num, claim in COMPLETION_CLAIMS:
        if session.is_complete(num) or num in proven:
            claim_lines.append(f"  [green]✓[/green] {claim}")
        else:
            claim_lines.append(f"  [yellow]✗ {claim} — not completed[/yellow]")

    console.print(
        "\n  [bold green]You did it.[/bold green] In a few minutes you:",
    )
    for line in claim_lines:
        console.print(line)
    if duration_line:
        console.print(f"\n{duration_line.rstrip()}")
    _what_now()
    console.print(
        "\n  [dim]If you liked this, Sovereignty is the same idea at book "
        "length — a\n  text game about running your own keys:[/dim]"
        "\n  [dim]pipx install sovereignty-game && sov tutorial[/dim]\n",
    )
    return EXIT_OK


def _what_now() -> None:
    """The three things the learner can now do on a network they are part of.

    The product used to end on a checklist, a command that destroys everything,
    and then an advert for a different product — after the best moment in it.
    The ledger they just joined is still running, still free, still open. Every
    command named here exists.
    """
    console.print("\n  [bold]The ledger is still running, and you are on it.[/bold]")
    console.print(
        "    [cyan]xrpl-camp read[/cyan]                     "
        "your entries, read back off the ledger",
    )
    console.print(
        "    [cyan]xrpl-camp read <address>[/cyan]           "
        "what somebody else wrote — no key needed",
    )
    console.print(
        "    [cyan]xrpl-camp try[/cyan]                      "
        "make it fail on purpose. Costs nothing.",
    )
    console.print(
        "\n  [dim]Check your proof pack any time: "
        "xrpl-camp proof verify xrpl_camp_proof_pack.json[/dim]",
    )
