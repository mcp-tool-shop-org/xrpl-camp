"""Lesson content and guided flow for XRPL Camp."""

from __future__ import annotations

import time
from datetime import UTC, datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from xrpl_camp import transport, wallet
from xrpl_camp.certificate import generate_certificate, save_certificate
from xrpl_camp.errors import (
    balance_error,
    connection_error,
    faucet_error,
    lookup_error,
    send_error,
)
from xrpl_camp.models import DryRunSession, Session
from xrpl_camp.proof_pack import generate_proof_pack, save_proof_pack

console = Console()


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


def _format_duration(seconds: float) -> str:
    """Human-friendly duration string."""
    if seconds < 60:
        return f"{int(seconds)}s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if secs == 0:
        return f"{minutes}m"
    return f"{minutes}m {secs}s"


def _pause() -> None:
    """Pause between lessons in guided mode."""
    console.input("\n  [dim]Press Enter to continue...[/dim]")
    console.print()


def _skip_banner(lesson: int, name: str) -> None:
    """Show a skip message for already-completed lessons."""
    console.print(f"  [dim]✓ Lesson {lesson}: {name} — already completed[/dim]")


def _dry_run_banner() -> None:
    """Print a dry-run indicator."""
    console.print("  [bold yellow][DRY RUN][/bold yellow] No network calls will be made.\n")


def _show_endpoint() -> None:
    """Print which RPC endpoint will be used."""
    console.print(f"  [dim]Endpoint: {transport.get_rpc_url()}[/dim]")


def lesson_1_mental_model(session: Session) -> None:
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


def lesson_2_create_wallet(session: Session) -> None:
    """Lesson 2: Create a Testnet wallet."""
    ts, t0 = _start_timer()

    if wallet.wallet_exists():
        w = wallet.load_wallet()
        if w:
            console.print(
                f"  [dim]Wallet already exists: {w['address']}[/dim]",
            )
            session.wallet_address = w["address"]
            session.mark_complete(2, LESSON_NAMES[2], started_at=ts, duration_seconds=_elapsed(t0))
            session.save()
            return

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

    console.print("\n  Creating wallet...", end="")
    address, seed = wallet.create_wallet()
    wallet.save_wallet(address, seed)
    console.print(" [green]done.[/green]")

    console.print(f"\n  [bold]Address:[/bold] {address}")
    console.print("  [dim]Seed saved to .xrpl-camp/wallet.json[/dim]")
    console.print(
        "\n  [yellow]This is a Testnet wallet. "
        "Never use Testnet seeds on Mainnet.[/yellow]",
    )

    session.wallet_address = address
    session.mark_complete(2, LESSON_NAMES[2], started_at=ts, duration_seconds=_elapsed(t0))
    session.save()

    console.print(
        "\n  [green]✓ Identity created.[/green] "
        "Nobody issued it to you — you generated it yourself.",
    )


def lesson_3_fund_wallet(session: Session, *, dry_run: bool = False) -> None:
    """Lesson 3: Fund the wallet via Testnet faucet."""
    ts, t0 = _start_timer()

    w = wallet.load_wallet()
    if not w:
        console.print("[red]No wallet found. Run lesson 2 first.[/red]")
        return

    console.print(Panel(
        "[bold]Lesson 3: Fund Your Wallet[/bold]\n\n"
        "The XRPL Testnet has a faucet that gives free test XRP.\n"
        "This is play money \u2014 no real value, nothing at risk.\n"
        "But it behaves exactly like real XRP on the ledger.\n\n"
        "We'll request funds from the faucet and check your balance.",
        title="XRPL Camp",
        border_style="blue",
    ))

    if dry_run:
        _dry_run_banner()
    _show_endpoint()

    console.print("\n  Requesting funds from Testnet faucet...", end="")
    try:
        transport.fund_wallet(w["seed"], dry_run=dry_run)
        console.print(" [green]funded.[/green]")
    except transport.XRPLConnectionError:
        err = connection_error(transport.get_rpc_url())
        console.print(f" [red]{err.message}[/red]")
        console.print(f"  [dim]{err.hint}[/dim]")
        return
    except Exception as e:
        err = faucet_error(str(e))
        console.print(f" [red]{err.message}[/red]")
        console.print(f"  [dim]{err.hint}[/dim]")
        return

    if dry_run:
        console.print("\n  [bold]Balance:[/bold] (skipped — dry run)")
    else:
        try:
            balance = transport.get_balance(w["address"])
            xrp = balance / 1_000_000
            console.print(f"\n  [bold]Balance:[/bold] {xrp:.2f} XRP ({balance:,} drops)")
        except transport.XRPLAccountNotFound:
            console.print(
                "\n  [bold]Balance:[/bold] [yellow]Account not yet activated[/yellow]",
            )
        except transport.XRPLConnectionError:
            err = connection_error(transport.get_rpc_url())
            console.print(f"\n  [yellow]{err.message}[/yellow]")
        except (transport.XRPLTransactionFailed, transport.XRPLMalformedResponse) as e:
            err = balance_error(str(e))
            console.print(f"\n  [yellow]{err.message}[/yellow]")

    if not dry_run:
        session.mark_complete(3, LESSON_NAMES[3], started_at=ts, duration_seconds=_elapsed(t0))
        session.save()

    console.print(
        "\n  [green]✓ Account funded.[/green] "
        "The network knows you exist now.",
    )


def lesson_4_send_payment(
    session: Session,
    memo: str = "",
    *,
    dry_run: bool = False,
    interactive: bool = False,
) -> str:
    """Lesson 4: Send a self-payment with a memo. Returns txid."""
    ts, t0 = _start_timer()

    w = wallet.load_wallet()
    if not w:
        console.print("[red]No wallet found. Run lesson 2 first.[/red]")
        return ""

    # In guided mode, ask what the user wants to write on the ledger
    if interactive and not memo:
        console.print(Panel(
            "[bold]Lesson 4: Send a Payment[/bold]\n\n"
            "You're about to write something permanent on a public ledger.\n"
            "The amount is just 1 drop (a fraction of a fraction of a penny).\n"
            "What matters is the [cyan]memo[/cyan] — your message on the blockchain.\n\n"
            "It can be anything: your name, a date, a thought, a joke.\n"
            "Once submitted, anyone can read it and nobody can erase it.",
            title="XRPL Camp",
            border_style="blue",
        ))
        user_memo = console.input(
            "\n  [bold]What do you want to write on the ledger?[/bold] ",
        ).strip()
        if user_memo:
            memo = user_memo
            console.print()

    if not memo:
        memo = f"XRPLCAMP|L4|{int(time.time())}"

    console.print(Panel(
        "[bold]Lesson 4: Send a Payment[/bold]\n\n"
        "You're about to send a transaction to yourself.\n\n"
        f"  [cyan]Memo:[/cyan]    {memo}\n"
        f"  [cyan]Encoded:[/cyan] {transport._to_hex(memo)}\n\n"
        "  [dim]Your memo is converted to hex bytes for the ledger.[/dim]\n\n"
        "  [cyan]Amount:[/cyan]  1 drop (0.000001 XRP — the smallest unit)\n"
        "  [cyan]Fee:[/cyan]     ~12 drops (paid to validators, not an app charge)\n\n"
        "The amount is tiny because the point is the memo, not the value.\n"
        "The fee is how the network processes your transaction.",
        title="XRPL Camp",
        border_style="blue",
    ))

    if dry_run:
        _dry_run_banner()
    _show_endpoint()

    console.print("\n  Submitting transaction...", end="")
    try:
        txid = transport.send_memo_payment(w["seed"], memo, dry_run=dry_run)
    except transport.XRPLConnectionError:
        err = connection_error(transport.get_rpc_url())
        console.print(f" [red]{err.message}[/red]")
        console.print(f"  [dim]{err.hint}[/dim]")
        return ""
    except Exception as e:
        err = send_error(str(e))
        console.print(f" [red]{err.message}[/red]")
        console.print(f"  [dim]{err.hint}[/dim]")
        return ""
    console.print(" [green]confirmed.[/green]")

    explorer = f"{transport.EXPLORER_URL}{txid}"
    console.print(f"\n  [bold]Transaction:[/bold] {txid}")
    console.print(f"  [dim]Explorer: {explorer}[/dim]")

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
    return txid


def lesson_5_verify_tx(
    session: Session, txid: str = "", *, dry_run: bool = False,
) -> None:
    """Lesson 5: Verify a transaction."""
    ts, t0 = _start_timer()

    if not txid:
        txid = session.txids.get("lesson_4", "")
    if not txid:
        console.print("[red]No transaction to verify. Run lesson 4 first.[/red]")
        return

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
    except transport.XRPLConnectionError:
        err = connection_error(transport.get_rpc_url())
        console.print(f" [red]{err.message}[/red]")
        console.print(f"  [dim]{err.hint}[/dim]")
        return
    except Exception as e:
        err = lookup_error(str(e))
        console.print(f" [red]{err.message}[/red]")
        console.print(f"  [dim]{err.hint}[/dim]")
        return
    console.print(" [green]found.[/green]")

    table = Table(title="Transaction Details")
    table.add_column("Field", style="bold")
    table.add_column("Value")

    table.add_row("Hash", tx["hash"])
    table.add_row("From", tx["account"])
    table.add_row("To", tx["destination"])
    table.add_row("Amount", f"{tx['amount']} drops")
    table.add_row("Fee", f"{tx['fee']} drops")
    table.add_row("Memo (readback)", tx["memo"])
    table.add_row("Ledger", str(tx["ledger_index"]))
    table.add_row("Result", tx["result"])

    console.print()
    console.print(table)

    # Independent witness — the strongest anti-handwaving beat
    explorer = f"{transport.EXPLORER_URL}{txid}"
    console.print(
        "\n  [bold]You don't have to trust this tool.[/bold]"
        "\n  Verify it yourself:",
    )
    console.print(f"  [cyan]{explorer}[/cyan]")

    if not dry_run:
        session.mark_complete(5, LESSON_NAMES[5], started_at=ts, duration_seconds=_elapsed(t0))
        session.save()

    console.print(
        "\n  [green]✓ Independently verified.[/green] "
        "No login, no API key — just the hash and the open ledger.",
    )


def lesson_6_certificate(session: Session, *, dry_run: bool = False) -> None:
    """Lesson 6: Generate a completion certificate and proof pack."""
    ts, t0 = _start_timer()

    console.print(Panel(
        "[bold]Lesson 6: Your Certificate[/bold]\n\n"
        "Your certificate records what you did — which lessons you\n"
        "completed, which transactions you sent, and your public\n"
        "address. No seed. No private data. Safe to share.\n\n"
        "The proof pack adds a SHA-256 hash so anyone can verify\n"
        "the file hasn't been edited.",
        title="XRPL Camp",
        border_style="blue",
    ))

    session.mark_complete(6, LESSON_NAMES[6], started_at=ts, duration_seconds=_elapsed(t0))

    if dry_run:
        console.print(
            "\n  [bold yellow]⚠ SIMULATION[/bold yellow] — "
            "No artifacts generated in dry-run mode.",
        )
        console.print(
            "  [dim]Run without --dry-run to generate your certificate "
            "and proof pack.[/dim]",
        )
        return

    session.save()

    cert = generate_certificate(session)
    cert_path = save_certificate(cert)

    pack = generate_proof_pack(session)
    pack_path = save_proof_pack(pack)

    total = session.total_duration()
    duration_str = _format_duration(total) if total > 0 else "n/a"

    # Completion bundle — one coherent handoff block
    txid = session.txids.get("lesson_4", "")
    explorer = f"{transport.EXPLORER_URL}{txid}" if txid else ""

    lines = [
        "[bold]Your completion bundle:[/bold]\n",
        f"  Certificate:  {cert_path}",
        f"  Proof pack:   {pack_path}",
    ]
    if explorer:
        lines.append(f"  Explorer:     {explorer}")
    lines.append(f"\n  Address:      {cert['address']}")
    lines.append(f"  Lessons:      {len(cert['completed'])}")
    lines.append(f"  Duration:     {duration_str}")
    lines.append(f"  SHA-256:      {pack['sha256']}")
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
        "This is yours — portable, verifiable, and no one can edit it.",
    )


# ---------------------------------------------------------------------------
# Guided flow
# ---------------------------------------------------------------------------


def run_guided_flow(*, dry_run: bool = False) -> None:
    """Walk through all 6 lessons in sequence, auto-skipping completed ones."""
    session = DryRunSession.get_or_create() if dry_run else Session.get_or_create()
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
        return
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

    # Lesson 1
    if session.is_complete(1):
        _skip_banner(1, LESSON_NAMES[1])
    else:
        _pause()
        lesson_1_mental_model(session)

    # Lesson 2
    if session.is_complete(2):
        _skip_banner(2, LESSON_NAMES[2])
    else:
        _pause()
        lesson_2_create_wallet(session)

    # Lesson 3
    if session.is_complete(3):
        _skip_banner(3, LESSON_NAMES[3])
    else:
        _pause()
        lesson_3_fund_wallet(session, dry_run=dry_run)

    # Lesson 4 — interactive memo in guided mode
    if session.is_complete(4):
        _skip_banner(4, LESSON_NAMES[4])
        txid = session.txids.get("lesson_4", "")
    else:
        _pause()
        txid = lesson_4_send_payment(session, dry_run=dry_run, interactive=True)

    if dry_run and not txid:
        txid = transport.DRY_RUN_TXID

    # Lesson 5
    if session.is_complete(5):
        _skip_banner(5, LESSON_NAMES[5])
    else:
        _pause()
        lesson_5_verify_tx(session, txid, dry_run=dry_run)

    # Lesson 6
    if session.is_complete(6):
        _skip_banner(6, LESSON_NAMES[6])
    else:
        _pause()
        lesson_6_certificate(session, dry_run=dry_run)

    total = session.total_duration()
    duration_line = f"  Total time: {_format_duration(total)}\n" if total > 0 else ""

    if dry_run:
        console.print(Panel(
            "[bold yellow]XRPL Camp — Dry Run Complete[/bold yellow]\n\n"
            "You've seen the whole flow in simulation mode.\n"
            "Nothing was saved and no transactions were sent.\n\n"
            "When you're ready, run [bold]xrpl-camp start[/bold] to do it for real.",
            title="Simulation",
            border_style="yellow",
        ))
    else:
        console.print(Panel(
            "[bold green]XRPL Camp \u2014 Complete[/bold green]\n\n"
            "You did it. In a few minutes you:\n"
            "  \u2713 Created a cryptographic identity\n"
            "  \u2713 Funded it on a public network\n"
            "  \u2713 Wrote permanent words to the ledger\n"
            "  \u2713 Verified everything independently\n"
            f"{duration_line}\n"
            "Your certificate and proof pack are yours to keep.\n\n"
            "Next step: try Sovereignty.\n"
            "  [dim]pipx install sovereignty-game[/dim]\n"
            "  [dim]sov tutorial[/dim]",
            title="Complete",
            border_style="green",
        ))
