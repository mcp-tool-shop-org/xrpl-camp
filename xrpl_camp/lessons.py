"""Lesson content and guided flow for XRPL Camp.

Every lesson returns a :class:`LessonResult`. That is the whole integrity
story of this file: a lesson that fails says so, the guided flow stops there,
and the certificate refuses to attest to anything that did not actually
happen. A run that only got as far as lesson 3 says exactly that.
"""

from __future__ import annotations

import os
import re
import sys
import time
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlparse

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from xrpl_camp import transport, wallet
from xrpl_camp.certificate import generate_certificate, save_certificate
from xrpl_camp.errors import (
    EXIT_OK,
    CampError,
    CampFailure,
    balance_error,
    connection_error,
    endpoint_error,
    faucet_error,
    format_error,
    lookup_error,
    memo_secret_error,
    memo_too_long_error,
    not_found_error,
    prerequisites_error,
    send_error,
    state_corrupt_error,
    unexpected_error,
    verification_error,
    wallet_corrupt_error,
    wallet_missing_error,
    write_error,
)
from xrpl_camp.models import (
    DryRunSession,
    ExecutionMode,
    Session,
    get_execution_mode,
    set_execution_mode,
)
from xrpl_camp.proof_pack import generate_proof_pack, save_proof_pack

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

#: XRPL family seed: 's' followed by base58 (no 0, O, I, l).
SEED_PATTERN = re.compile(r"^s[1-9A-HJ-NP-Za-km-z]{25,}$")

ALLOW_ANY_ENDPOINT_ENV = "XRPL_CAMP_ALLOW_ANY_ENDPOINT"


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
    """
    if _non_interactive:
        return False
    stdin = getattr(sys, "stdin", None)
    if stdin is None:
        return False
    try:
        return bool(stdin.isatty())
    except Exception:
        return False


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


def _report(err: CampError) -> None:
    """Print a structured error. Never raises on odd content."""
    console.print(format_error(err))


def _fail(lesson: int, err: CampError) -> LessonResult:
    """Print the error and return a failing result."""
    _report(err)
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
    """'1,000,000 drops (1.000000 XRP)' - the unit lesson, every time."""
    return f"{drops:,} drops ({drops / 1_000_000:.6f} XRP)"


# ---------------------------------------------------------------------------
# Failure classification
# ---------------------------------------------------------------------------


def _classify(exc: Exception, fallback) -> CampError:
    """Map a transport exception to a CampError.

    The raw exception text is attached as `detail` (shown only under
    --verbose) and never interpolated into the beginner-facing message.
    """
    if isinstance(exc, transport.XRPLConnectionError):
        err = connection_error(transport.get_rpc_url())
    elif isinstance(exc, transport.XRPLAccountNotFound):
        err = balance_error()
        err.message = "That account does not exist on the ledger yet."
        err.hint = "Run 'xrpl-camp fund' first - an account has to be funded to exist."
    elif isinstance(exc, ValueError | TypeError | KeyError):
        err = unexpected_error()
    else:
        err = fallback()
    err.detail = f"{type(exc).__name__}: {exc}"
    return err


# ---------------------------------------------------------------------------
# Endpoint and wallet guards
# ---------------------------------------------------------------------------


def _endpoint_override_allowed() -> bool:
    """True when the learner has explicitly opted out of the host allowlist."""
    return os.environ.get(ALLOW_ANY_ENDPOINT_ENV, "").strip() not in ("", "0", "false")


def check_endpoint() -> CampError | None:
    """Refuse to spend against an endpoint that may not be a test network.

    Returns None when the endpoint is fine (printing a loud banner if the
    learner overrode the allowlist), or a CampError to fail the lesson with.
    """
    url = transport.get_rpc_url()
    host = (urlparse(url).hostname or "").lower()
    if host in TESTNET_HOSTS or host.endswith(".rippletest.net"):
        return None
    if _endpoint_override_allowed():
        console.print(Panel(
            "[bold]This is not a known test network.[/bold]\n\n"
            f"Endpoint: {escape(url)}\n\n"
            "You set " + ALLOW_ANY_ENDPOINT_ENV + ", so XRPL Camp will go ahead.\n"
            "If this is Mainnet, the XRP you spend is real and the memo you write\n"
            "is public and permanent. Nothing here can be undone.",
            title="Not a test network",
            border_style="red",
        ))
        return None
    return endpoint_error(url)


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


# ---------------------------------------------------------------------------
# Memo handling
# ---------------------------------------------------------------------------


def _memo_hex(memo: str) -> str:
    """Hex bytes for the memo, exactly as the transport writes them."""
    encoder = getattr(transport, "to_hex", None) or getattr(transport, "_to_hex", None)
    if callable(encoder):
        return str(encoder(memo))
    return memo.encode("utf-8").hex()


def validate_memo(memo: str, secrets: Iterable[str] = ()) -> CampError | None:
    """Refuse memos that are too long, or that look like key material.

    Lesson 2 tells the learner to guard their seed like a password. Lesson 4
    then invites them to type anything at all into a permanent public record.
    This is the guard between those two sentences.
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
            return "", None
        if not answer:
            return "", None
        last_error = validate_memo(answer, secrets)
        if last_error is None:
            console.print()
            return answer, None
        _report(last_error)
    return "", last_error


# ---------------------------------------------------------------------------
# Lessons
# ---------------------------------------------------------------------------


def lesson_1_mental_model(session: Session) -> LessonResult:
    """Lesson 1: Explain the XRPL mental model."""
    ts, t0 = _start_timer()

    console.print(Panel(
        "[bold]Lesson 1: The Mental Model[/bold]\n\n"
        "The XRP Ledger (XRPL) is a shared notebook.\n\n"
        "  [cyan]Account[/cyan]   — Your identity on the ledger. "
        "A public address that anyone can look up.\n"
        "  [cyan]Balance[/cyan]   — How much XRP your account holds. "
        "Measured in 'drops' (1 XRP = 1,000,000 drops).\n"
        "  [cyan]Transaction[/cyan] — An entry in the notebook. "
        "Once written, it can never be erased.\n"
        "  [cyan]Memo[/cyan]      — A note attached to a transaction. "
        "You can write anything here.\n\n"
        "Every transaction is public. Every memo is permanent.\n"
        "That's what makes it useful as a diary.",
        title="XRPL Camp",
        border_style="blue",
    ))

    session.mark_complete(1, LESSON_NAMES[1], started_at=ts, duration_seconds=_elapsed(t0))
    session.save()

    console.print(
        "\n  [green]✓ Foundation set.[/green] The ledger is shared, "
        "permanent, and verifiable. Everything builds on that.",
    )
    return LessonResult(lesson=1, ok=True)


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
        "The seed proves you own the address. Anyone with your seed\n"
        "can spend your funds. Guard it like a password.\n\n"
        "Your seed stays on this machine. XRPL Camp never sends it anywhere.",
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
        return _fail(2, write_error(".xrpl-camp/wallet.json", f"{type(exc).__name__}: {exc}"))
    except Exception as exc:
        console.print()
        return _fail(2, _classify(exc, unexpected_error))
    console.print(" [green]done.[/green]")

    console.print(f"\n  [bold]Address:[/bold] {escape(address)}")
    if dry_run:
        console.print(
            "  [dim]Seed would be saved to .xrpl-camp/wallet.json "
            "(nothing written — dry run)[/dim]",
        )
    else:
        console.print("  [dim]Seed saved to .xrpl-camp/wallet.json[/dim]")
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

    console.print(Panel(
        "[bold]Lesson 3: Fund Your Wallet[/bold]\n\n"
        "The XRPL Testnet has a faucet that gives free test XRP.\n"
        "This is play money — no real value, nothing at risk.\n"
        "But it behaves exactly like real XRP on the ledger.\n\n"
        "We'll request funds from the faucet and check your balance.",
        title="XRPL Camp",
        border_style="blue",
    ))

    if dry_run:
        _dry_run_banner()
    _show_endpoint()

    if not dry_run:
        endpoint_problem = check_endpoint()
        if endpoint_problem is not None:
            return _fail(3, endpoint_problem)

    console.print("\n  Requesting funds from Testnet faucet...", end="")
    try:
        transport.fund_wallet(w["seed"], dry_run=dry_run)
    except Exception as exc:
        console.print()
        return _fail(3, _classify(exc, faucet_error))
    console.print(" [green]funded.[/green]")

    if dry_run:
        console.print("\n  [bold]Balance:[/bold] (skipped — dry run)")
    else:
        # A balance read that fails does not undo the funding, so it warns
        # rather than failing the lesson.
        try:
            balance = transport.get_balance(w["address"])
            xrp = balance / 1_000_000
            console.print(f"\n  [bold]Balance:[/bold] {xrp:.2f} XRP ({balance:,} drops)")
        except transport.XRPLAccountNotFound:
            console.print(
                "\n  [bold]Balance:[/bold] [yellow]Account not yet activated[/yellow]",
            )
        except Exception as exc:
            warning = _classify(exc, balance_error)
            console.print()
            _report(warning)

    if not dry_run:
        session.mark_complete(3, LESSON_NAMES[3], started_at=ts, duration_seconds=_elapsed(t0))
        session.save()

    console.print(
        "\n  [green]✓ Account funded.[/green] "
        "The network knows you exist now.",
    )
    return LessonResult(lesson=3, ok=True)


def lesson_4_send_payment(
    session: Session,
    memo: str = "",
    *,
    dry_run: bool = False,
    interactive: bool = False,
) -> LessonResult:
    """Lesson 4: Send a memo payment to a second wallet the learner owns."""
    ts, t0 = _start_timer()

    w, err = _require_wallet()
    if err is not None:
        return _fail(4, err)

    # Refuse a non-test endpoint before anything is created or spent.
    if not dry_run:
        endpoint_problem = check_endpoint()
        if endpoint_problem is not None:
            return _fail(4, endpoint_problem)

    mailbox, err = _resolve_mailbox()
    if err is not None:
        return _fail(4, err)

    secrets = [w.get("seed", ""), mailbox.get("seed", "")]

    if interactive and not memo:
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
        if is_interactive():
            memo, memo_error = _ask_memo(secrets)
            if memo_error is not None:
                return _fail(4, memo_error)

    if not memo:
        memo = f"XRPLCAMP|L4|{int(time.time())}"

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
        try:
            transport.get_balance(mailbox["address"])
            creates_account = False
        except transport.XRPLAccountNotFound:
            creates_account = True
        except Exception as exc:
            return _fail(4, _classify(exc, balance_error))

        if creates_account:
            try:
                amount_drops = int(transport.get_reserve_base())
            except Exception:
                amount_drops = FALLBACK_RESERVE_DROPS
        else:
            amount_drops = REPEAT_SEND_DROPS

    creation_note = (
        "\n  [dim]This one brings the mailbox account into existence, so it has to\n"
        "  carry at least the network's base reserve.[/dim]\n"
        if creates_account else ""
    )

    console.print(Panel(
        "[bold]Lesson 4: Send a Payment[/bold]\n\n"
        "You're sending a real transaction to your mailbox — a second wallet\n"
        "whose keys are also yours.\n\n"
        f"  [cyan]Memo:[/cyan]    {escape(memo)}\n"
        f"  [cyan]Encoded:[/cyan] {escape(_memo_hex(memo))}\n\n"
        "  [dim]Your memo is converted to hex bytes for the ledger.[/dim]\n\n"
        f"  [cyan]To:[/cyan]      {escape(mailbox['address'])}\n"
        f"  [cyan]Amount:[/cyan]  {_drops_line(amount_drops)}\n"
        "  [cyan]Fee:[/cyan]     a few drops, set by the network "
        "(paid to validators, not an app charge)\n"
        f"{creation_note}\n"
        "The amount is small because the point is the memo, not the value.\n"
        "The fee is how the network processes your transaction.",
        title="XRPL Camp",
        border_style="blue",
    ))

    if dry_run:
        _dry_run_banner()
    _show_endpoint()

    console.print("\n  Submitting transaction...", end="")
    try:
        result = transport.send_memo_payment(
            w["seed"],
            memo,
            mailbox["address"],
            amount_drops=amount_drops,
            dry_run=dry_run,
        )
    except Exception as exc:
        console.print()
        return _fail(4, _classify(exc, send_error))
    console.print(" [green]confirmed.[/green]")

    txid = result.txid
    explorer = f"{transport.EXPLORER_URL}{txid}"
    console.print(f"\n  [bold]Transaction:[/bold] {escape(txid)}")
    console.print(f"  [bold]Delivered:[/bold]   {_drops_line(int(result.amount_drops))}")
    console.print(f"  [bold]Fee paid:[/bold]    {int(result.fee_drops):,} drops")
    console.print(f"  [dim]Explorer: {escape(explorer)}[/dim]")

    if result.created_account:
        console.print(Panel(
            "[bold]You just created an account on a public ledger.[/bold]\n\n"
            f"{escape(result.destination)}\n\n"
            "That address did not exist a moment ago. Your payment brought it\n"
            "into being, and you hold its keys — they are in\n"
            ".xrpl-camp/mailbox.json, next to your own.\n\n"
            "Nobody approved this. Nobody could have stopped it.",
            title="Account created",
            border_style="green",
        ))

    if not dry_run:
        session.mark_complete(
            4, LESSON_NAMES[4], txid=txid,
            started_at=ts, duration_seconds=_elapsed(t0),
        )
        session.save()

    console.print(
        "\n  [green]✓ Written to the ledger.[/green] "
        "Your memo is permanent and public — no one can erase it.",
    )
    return LessonResult(lesson=4, ok=True, txid=txid, memo=memo)


def lesson_5_verify_tx(
    session: Session,
    txid: str = "",
    *,
    dry_run: bool = False,
    expected_memo: str = "",
) -> LessonResult:
    """Lesson 5: Verify a transaction, and check the readback against what was sent."""
    ts, t0 = _start_timer()

    if not txid:
        txid = session.txids.get("lesson_4", "")
    if not txid:
        return _fail(5, CampError(
            code="NO_TRANSACTION",
            message="There is no transaction to verify yet.",
            hint="Run 'xrpl-camp send --memo \"your message\"' first, or 'xrpl-camp start'.",
            exit_code=1,
        ))

    console.print(Panel(
        "[bold]Lesson 5: Verify a Transaction[/bold]\n\n"
        "Anyone can look up any transaction on the XRPL.\n"
        "No login needed. No API key. Just the transaction hash.\n\n"
        "We'll query the ledger and show you exactly what it recorded.",
        title="XRPL Camp",
        border_style="blue",
    ))

    if dry_run:
        _dry_run_banner()
    _show_endpoint()

    console.print("\n  Looking up transaction...", end="")
    try:
        tx = transport.lookup_tx(txid, dry_run=dry_run)
    except Exception as exc:
        console.print()
        return _fail(5, _classify(exc, lookup_error))

    # The lookup can succeed as a request and still not find the transaction.
    if not tx.get("found", True):
        console.print()
        return _fail(5, not_found_error(txid))
    console.print(" [green]found.[/green]")

    table = Table(title="Transaction Details")
    table.add_column("Field", style="bold")
    table.add_column("Value")

    def cell(value: object) -> str:
        return escape(str(value))

    table.add_row("Hash", cell(tx.get("hash", txid)))
    table.add_row("From", cell(tx.get("account", "")))
    table.add_row("To", cell(tx.get("destination", "")))
    table.add_row("Amount", cell(f"{tx.get('amount', '')} drops"))
    if tx.get("delivered"):
        table.add_row("Delivered", cell(f"{tx['delivered']} drops"))
    table.add_row("Fee", cell(f"{tx.get('fee', '')} drops"))
    table.add_row("Memo (readback)", cell(tx.get("memo", "")))
    table.add_row("Ledger", cell(tx.get("ledger_index", "")))
    if tx.get("close_time_iso"):
        table.add_row("Time", cell(tx["close_time_iso"]))
    table.add_row("Result", cell(tx.get("result", "")))
    if "validated" in tx:
        table.add_row("Validated", cell(tx["validated"]))

    console.print()
    console.print(table)

    # Everything below is the actual verification. Without it, this lesson
    # prints a table of whatever came back and then congratulates the learner.
    problem = _verification_problem(tx, expected_memo)
    if problem is not None:
        console.print()
        return _fail(5, problem)

    if expected_memo:
        console.print(
            f"\n  [bold]You wrote:[/bold]        {escape(expected_memo)}"
            f"\n  [bold]Ledger returned:[/bold]  {escape(str(tx.get('memo', '')))}"
            "\n  [green]Identical.[/green] Not our copy of it — the ledger's.",
        )

    # Independent witness - the strongest anti-handwaving beat
    explorer = f"{transport.EXPLORER_URL}{txid}"
    console.print(
        "\n  [bold]You don't have to trust this tool.[/bold]"
        "\n  Verify it yourself:",
    )
    console.print(f"  [cyan]{escape(explorer)}[/cyan]")

    if not dry_run:
        session.mark_complete(5, LESSON_NAMES[5], started_at=ts, duration_seconds=_elapsed(t0))
        session.save()

    console.print(
        "\n  [green]✓ Independently verified.[/green] "
        "No login, no API key — just the hash and the open ledger.",
    )
    return LessonResult(lesson=5, ok=True, txid=txid, memo=str(tx.get("memo", "")))


def _verification_problem(tx: dict, expected_memo: str) -> CampError | None:
    """Return a CampError if the looked-up transaction fails verification."""
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
) -> LessonResult:
    """Lesson 6: Generate a completion certificate and proof pack.

    Refuses to seal a record whose lessons did not happen. `assume_complete`
    carries lessons that succeeded in this process but were not persisted -
    that is only ever the dry-run flow, where nothing is written anyway.
    """
    ts, t0 = _start_timer()

    proven = set(assume_complete)
    missing = [n for n in range(1, 6) if not session.is_complete(n) and n not in proven]
    if missing:
        err = prerequisites_error(missing, LESSON_NAMES)
        _report(err)
        console.print(
            "\n  [dim]A certificate is a claim about what you did. "
            "It only covers lessons you finished.[/dim]",
        )
        return LessonResult(lesson=6, ok=False, error=err)

    console.print(Panel(
        "[bold]Lesson 6: Your Certificate[/bold]\n\n"
        "Your certificate records what you did — which lessons you\n"
        "completed, which transactions you sent, and your public\n"
        "address. No seed. No private data. Safe to share.\n\n"
        "The proof pack adds a SHA-256 hash, so an accidental edit\n"
        "shows up immediately. But the hash is not what makes it\n"
        "trustworthy — anyone could recompute it. What nobody can\n"
        "fake is the transaction: the pack names a hash on a public\n"
        "ledger, and that either exists or it doesn't.",
        title="XRPL Camp",
        border_style="blue",
    ))

    if dry_run:
        console.print(
            "\n  [bold yellow]⚠ SIMULATION[/bold yellow] — "
            "No artifacts generated in dry-run mode.",
        )
        console.print(
            "  [dim]Run without --dry-run to generate your certificate "
            "and proof pack.[/dim]",
        )
        return LessonResult(lesson=6, ok=True)

    # Marked in memory so the certificate can include lesson 6, but persisted
    # only once the files it describes actually exist on disk.
    session.mark_complete(6, LESSON_NAMES[6], started_at=ts, duration_seconds=_elapsed(t0))

    try:
        cert = generate_certificate(session)
        cert_path = save_certificate(cert)
        pack = generate_proof_pack(session)
        pack_path = save_proof_pack(pack)
    except OSError as exc:
        return _fail(6, write_error(
            "your certificate and proof pack", f"{type(exc).__name__}: {exc}",
        ))

    session.save()

    total = session.total_duration()
    duration_str = format_duration(total) if total > 0 else "n/a"

    # Completion bundle - one coherent handoff block
    txid = session.txids.get("lesson_4", "")
    explorer = f"{transport.EXPLORER_URL}{txid}" if txid else ""

    lines = [
        "[bold]Your completion bundle:[/bold]\n",
        f"  Certificate:  {escape(str(cert_path))}",
        f"  Proof pack:   {escape(str(pack_path))}",
    ]
    if explorer:
        lines.append(f"  Explorer:     {escape(explorer)}")
    lines.append(f"\n  Address:      {escape(str(cert['address']))}")
    lines.append(f"  Lessons:      {len(cert['completed'])}")
    lines.append(f"  Duration:     {duration_str}")
    lines.append(f"  SHA-256:      {escape(str(pack['sha256']))}")
    lines.append(
        "\n  [dim]Verify your proof pack anytime:[/dim]"
        "\n  [dim]xrpl-camp proof verify xrpl_camp_proof_pack.json[/dim]"
    )

    console.print(Panel(
        "\n".join(lines),
        title="XRPL Camp — Complete",
        border_style="green",
    ))

    console.print(
        "\n  [green]✓ Record sealed.[/green] "
        "This is yours to keep — and anyone can check it against the ledger.",
    )
    return LessonResult(lesson=6, ok=True)


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
    """Stop the guided flow on a failed lesson. Returns the exit code."""
    name = LESSON_NAMES.get(result.lesson, "?")
    err = result.error
    body = [
        f"[bold]Stopped at Lesson {result.lesson} — {name}.[/bold]\n",
    ]
    if err is not None:
        body.append(f"{escape(err.message)}")
        if err.hint:
            body.append(f"[dim]{escape(err.hint)}[/dim]")
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


def run_guided_flow(*, dry_run: bool = False) -> int:
    """Walk through all 6 lessons in sequence, auto-skipping completed ones.

    Returns a process exit code: 0 when every lesson in the run completed,
    non-zero when one failed. A failed lesson halts the flow - the run never
    walks past a failure into a certificate.
    """
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
            "You've already completed all 6 lessons.\n"
            "Run [bold]xrpl-camp status[/bold] to see your progress, or\n"
            "[bold]xrpl-camp reset[/bold] to start fresh.",
            title="XRPL Camp",
            border_style="green",
        ))
        return EXIT_OK
    else:
        console.print(Panel(
            "[bold]Welcome to XRPL Camp[/bold]\n\n"
            "In the next few minutes, you'll:\n"
            "  1. Learn what the XRPL is\n"
            "  2. Create a Testnet wallet\n"
            "  3. Fund it with test XRP\n"
            "  4. Send your first payment\n"
            "  5. Verify it on the ledger\n"
            "  6. Get a completion certificate\n\n"
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
        result = lesson_1_mental_model(session)
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
        result = lesson_4_send_payment(session, dry_run=dry_run, interactive=True)
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
    claim_lines = []
    for num, claim in COMPLETION_CLAIMS:
        if session.is_complete(num) or num in proven:
            claim_lines.append(f"  [green]✓[/green] {claim}")
        else:
            claim_lines.append(f"  [yellow]✗ {claim} — not completed[/yellow]")

    console.print(Panel(
        "[bold green]XRPL Camp — Complete[/bold green]\n\n"
        "You did it. In a few minutes you:\n"
        + "\n".join(claim_lines)
        + f"\n{duration_line}\n"
        "Your certificate and proof pack are yours to keep.\n\n"
        "Next step: try Sovereignty.\n"
        "  [dim]pipx install sovereignty-game[/dim]\n"
        "  [dim]sov tutorial[/dim]",
        title="Complete",
        border_style="green",
    ))
    return EXIT_OK
