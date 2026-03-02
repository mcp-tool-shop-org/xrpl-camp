"""XRPL Camp CLI — the teaching console."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console

from xrpl_camp import lessons, wallet
from xrpl_camp.models import Session

app = typer.Typer(
    name="xrpl-camp",
    help="XRPL Camp — learn the XRPL diary in one sitting.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def start() -> None:
    """Guided flow through all 6 lessons."""
    lessons.run_guided_flow()


# ---------------------------------------------------------------------------
# Wallet commands
# ---------------------------------------------------------------------------


@app.command("wallet")
def wallet_cmd(
    action: Annotated[str, typer.Argument(help="Action: create or show")],
) -> None:
    """Create or display your Testnet wallet."""
    if action == "create":
        if wallet.wallet_exists():
            w = wallet.load_wallet()
            if w:
                console.print(f"  Wallet already exists: {w['address']}")
                console.print(
                    "  [dim]Delete .xrpl-camp/wallet.json to create a new one.[/dim]",
                )
                return

        session = Session.get_or_create()
        lessons.lesson_2_create_wallet(session)

    elif action == "show":
        w = wallet.load_wallet()
        if not w:
            console.print("[red]No wallet found. Run: xrpl-camp wallet create[/red]")
            raise typer.Exit(1)

        console.print(f"\n  [bold]Address:[/bold]  {w['address']}")
        console.print(f"  [dim]Network:  {w.get('network', 'testnet')}[/dim]")
        console.print(f"  [dim]Created:  {w.get('created_at', '?')}[/dim]")
        console.print("\n  [dim]Seed is stored locally. Not shown here.[/dim]")

    else:
        console.print(f"[yellow]Unknown action '{action}'. Try: create or show[/yellow]")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# Fund command
# ---------------------------------------------------------------------------


@app.command()
def fund() -> None:
    """Fund your wallet via the Testnet faucet."""
    session = Session.get_or_create()
    lessons.lesson_3_fund_wallet(session)


# ---------------------------------------------------------------------------
# Send command
# ---------------------------------------------------------------------------


@app.command()
def send(
    memo: Annotated[str, typer.Option("--memo", "-m", help="Memo text")] = "",
) -> None:
    """Send a self-payment with a memo to the XRPL Testnet."""
    session = Session.get_or_create()
    lessons.lesson_4_send_payment(session, memo=memo)


# ---------------------------------------------------------------------------
# Verify command
# ---------------------------------------------------------------------------


@app.command()
def verify(
    tx: Annotated[str, typer.Option("--tx", help="Transaction hash to verify")] = "",
) -> None:
    """Verify a transaction on the XRPL Testnet."""
    session = Session.get_or_create()
    lessons.lesson_5_verify_tx(session, txid=tx)


# ---------------------------------------------------------------------------
# Certificate command
# ---------------------------------------------------------------------------


@app.command()
def certificate() -> None:
    """Generate a completion certificate."""
    session = Session.get_or_create()

    if not session.progress:
        console.print("[yellow]No lessons completed yet. Run: xrpl-camp start[/yellow]")
        raise typer.Exit(1)

    lessons.lesson_6_certificate(session)
