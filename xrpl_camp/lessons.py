"""Lesson content and guided flow for XRPL Camp."""

from __future__ import annotations

import time

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from xrpl_camp import transport, wallet
from xrpl_camp.certificate import generate_certificate, save_certificate
from xrpl_camp.errors import faucet_error, lookup_error, send_error
from xrpl_camp.models import Session
from xrpl_camp.proof_pack import generate_proof_pack, save_proof_pack

console = Console()

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


def _pause() -> None:
    """Pause between lessons in guided mode."""
    console.input("\n  [dim]Press Enter to continue...[/dim]")
    console.print()


def _dry_run_banner() -> None:
    """Print a dry-run indicator."""
    console.print("  [bold yellow][DRY RUN][/bold yellow] No network calls will be made.\n")


def _show_endpoint() -> None:
    """Print which RPC endpoint will be used."""
    console.print(f"  [dim]Endpoint: {transport.get_rpc_url()}[/dim]")


def lesson_1_mental_model(session: Session) -> None:
    """Lesson 1: Explain the XRPL mental model."""
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

    session.mark_complete(1, LESSON_NAMES[1])
    session.save()

    console.print(
        "\n  [green]What you just learned:[/green] the XRPL is a shared "
        "ledger where every entry is permanent and verifiable.",
    )


def lesson_2_create_wallet(session: Session) -> None:
    """Lesson 2: Create a Testnet wallet."""
    if wallet.wallet_exists():
        w = wallet.load_wallet()
        if w:
            console.print(
                f"  [dim]Wallet already exists: {w['address']}[/dim]",
            )
            session.wallet_address = w["address"]
            session.mark_complete(2, LESSON_NAMES[2])
            session.save()
            return

    console.print(Panel(
        "[bold]Lesson 2: Create a Wallet[/bold]\n\n"
        "A wallet is a pair of keys:\n"
        "  [cyan]Address[/cyan] — your public identity (safe to share)\n"
        "  [cyan]Seed[/cyan]    — your private key (never share this)\n\n"
        "The seed proves you own the address. Anyone with your seed\n"
        "can spend your funds. Guard it like a password.",
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
    session.mark_complete(2, LESSON_NAMES[2])
    session.save()

    console.print(
        "\n  [green]What you just proved:[/green] "
        "you can create a cryptographic identity.",
    )


def lesson_3_fund_wallet(session: Session, *, dry_run: bool = False) -> None:
    """Lesson 3: Fund the wallet via Testnet faucet."""
    w = wallet.load_wallet()
    if not w:
        console.print("[red]No wallet found. Run lesson 2 first.[/red]")
        return

    console.print(Panel(
        "[bold]Lesson 3: Fund Your Wallet[/bold]\n\n"
        "The XRPL Testnet has a faucet that gives free test XRP.\n"
        "This is play money — no real value. But it behaves exactly\n"
        "like real XRP on the ledger.\n\n"
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
    except Exception as e:
        err = faucet_error(str(e))
        console.print(f" [red]{err.message}[/red]")
        console.print(f"  [dim]{err.hint}[/dim]")
        return

    if dry_run:
        console.print("\n  [bold]Balance:[/bold] (skipped — dry run)")
    else:
        balance = transport.get_balance(w["address"])
        xrp = balance / 1_000_000
        console.print(f"\n  [bold]Balance:[/bold] {xrp:.2f} XRP ({balance:,} drops)")

    if not dry_run:
        session.mark_complete(3, LESSON_NAMES[3])
        session.save()

    console.print(
        "\n  [green]What you just proved:[/green] "
        "you can receive funds on a public network.",
    )


def lesson_4_send_payment(
    session: Session, memo: str = "", *, dry_run: bool = False,
) -> str:
    """Lesson 4: Send a self-payment with a memo. Returns txid."""
    w = wallet.load_wallet()
    if not w:
        console.print("[red]No wallet found. Run lesson 2 first.[/red]")
        return ""

    if not memo:
        memo = f"XRPLCAMP|L4|{int(time.time())}"

    console.print(Panel(
        "[bold]Lesson 4: Send a Payment[/bold]\n\n"
        "You're about to send a transaction to yourself (1 drop).\n"
        "The amount doesn't matter — what matters is the memo.\n\n"
        f"  [cyan]Memo:[/cyan] {memo}\n\n"
        "This memo is now permanently written to the XRPL Testnet.\n"
        "Anyone can read it. Nobody can erase it.",
        title="XRPL Camp",
        border_style="blue",
    ))

    if dry_run:
        _dry_run_banner()
    _show_endpoint()

    console.print("\n  Submitting transaction...", end="")
    try:
        txid = transport.send_memo_payment(w["seed"], memo, dry_run=dry_run)
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
        session.mark_complete(4, LESSON_NAMES[4], txid=txid)
        session.save()

    console.print(
        "\n  [green]What you just proved:[/green] "
        "you can write to a public ledger.",
    )
    return txid


def lesson_5_verify_tx(
    session: Session, txid: str = "", *, dry_run: bool = False,
) -> None:
    """Lesson 5: Verify a transaction."""
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
    table.add_row("Memo", tx["memo"])
    table.add_row("Ledger", str(tx["ledger_index"]))
    table.add_row("Result", tx["result"])

    console.print()
    console.print(table)

    if not dry_run:
        session.mark_complete(5, LESSON_NAMES[5])
        session.save()

    console.print(
        "\n  [green]What you just proved:[/green] "
        "anyone can independently verify what happened.",
    )


def lesson_6_certificate(session: Session) -> None:
    """Lesson 6: Generate a completion certificate and proof pack."""
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

    session.mark_complete(6, LESSON_NAMES[6])
    session.save()

    cert = generate_certificate(session)
    cert_path = save_certificate(cert)

    pack = generate_proof_pack(session)
    pack_path = save_proof_pack(pack)

    console.print(f"\n  [bold]Certificate saved:[/bold] {cert_path}")
    console.print(f"  [bold]Proof pack saved:[/bold]  {pack_path}")
    console.print(f"  [dim]Address: {cert['address']}[/dim]")
    console.print(f"  [dim]Lessons: {len(cert['completed'])}[/dim]")
    console.print(f"  [dim]SHA-256: {pack['sha256']}[/dim]")

    console.print(
        "\n  [green]What you just proved:[/green] "
        "you have a portable, verifiable record of learning.",
    )


# ---------------------------------------------------------------------------
# Guided flow
# ---------------------------------------------------------------------------


def run_guided_flow(*, dry_run: bool = False) -> None:
    """Walk through all 6 lessons in sequence."""
    console.print(Panel(
        "[bold]Welcome to XRPL Camp[/bold]\n\n"
        "In the next few minutes, you'll:\n"
        "  1. Learn what the XRPL is\n"
        "  2. Create a Testnet wallet\n"
        "  3. Fund it with test XRP\n"
        "  4. Send your first payment\n"
        "  5. Verify it on the ledger\n"
        "  6. Get a completion certificate\n\n"
        "No real money. No accounts. Just you and the ledger.",
        title="XRPL Camp",
        border_style="green",
    ))

    if dry_run:
        _dry_run_banner()

    session = Session.get_or_create()

    _pause()
    lesson_1_mental_model(session)

    _pause()
    lesson_2_create_wallet(session)

    _pause()
    lesson_3_fund_wallet(session, dry_run=dry_run)

    _pause()
    txid = lesson_4_send_payment(session, dry_run=dry_run)

    if dry_run and not txid:
        # Dry-run send returns a placeholder — use it for verify
        txid = transport.DRY_RUN_TXID

    _pause()
    lesson_5_verify_tx(session, txid, dry_run=dry_run)

    _pause()
    lesson_6_certificate(session)

    console.print(Panel(
        "[bold green]XRPL Camp Complete[/bold green]\n\n"
        "You now have:\n"
        "  - A funded Testnet wallet\n"
        "  - A confirmed payment on the ledger\n"
        "  - A verification report\n"
        "  - A certificate and proof pack\n\n"
        "Next step: try Sovereignty.\n"
        "  [dim]pipx install sovereignty-game[/dim]\n"
        "  [dim]sov tutorial[/dim]",
        title="Done",
        border_style="green",
    ))
