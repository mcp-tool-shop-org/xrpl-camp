"""XRPL Camp CLI — the teaching console."""

from __future__ import annotations

import platform
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

import xrpl_camp
from xrpl_camp import lessons, wallet
from xrpl_camp.models import STATE_DIR, Session

app = typer.Typer(
    name="xrpl-camp",
    help="XRPL Camp — learn the XRPL diary in one sitting.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def start(
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Simulate network steps (no real transactions)")
    ] = False,
) -> None:
    """Guided flow through all 6 lessons."""
    lessons.run_guided_flow(dry_run=dry_run)


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
def fund(
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Simulate the faucet request")
    ] = False,
) -> None:
    """Fund your wallet via the Testnet faucet."""
    session = Session.get_or_create()
    lessons.lesson_3_fund_wallet(session, dry_run=dry_run)


# ---------------------------------------------------------------------------
# Send command
# ---------------------------------------------------------------------------


@app.command()
def send(
    memo: Annotated[str, typer.Option("--memo", "-m", help="Memo text")] = "",
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Simulate the payment")
    ] = False,
) -> None:
    """Send a self-payment with a memo to the XRPL Testnet."""
    session = Session.get_or_create()
    lessons.lesson_4_send_payment(session, memo=memo, dry_run=dry_run)


# ---------------------------------------------------------------------------
# Verify command
# ---------------------------------------------------------------------------


@app.command()
def verify(
    tx: Annotated[str, typer.Option("--tx", help="Transaction hash to verify")] = "",
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Simulate the lookup")
    ] = False,
) -> None:
    """Verify a transaction on the XRPL Testnet."""
    session = Session.get_or_create()
    lessons.lesson_5_verify_tx(session, txid=tx, dry_run=dry_run)


# ---------------------------------------------------------------------------
# Certificate command
# ---------------------------------------------------------------------------


@app.command()
def certificate() -> None:
    """Generate a completion certificate and proof pack."""
    session = Session.get_or_create()

    if not session.progress:
        console.print("[yellow]No lessons completed yet. Run: xrpl-camp start[/yellow]")
        raise typer.Exit(1)

    lessons.lesson_6_certificate(session)


# ---------------------------------------------------------------------------
# Reset command
# ---------------------------------------------------------------------------


@app.command()
def reset() -> None:
    """Wipe all XRPL Camp state (.xrpl-camp/ directory).

    Requires you to type RESET to confirm. This cannot be undone.
    """
    if not STATE_DIR.exists():
        console.print("  [dim]Nothing to reset. No .xrpl-camp/ directory found.[/dim]")
        return

    # Show what will be deleted
    console.print("\n  [bold yellow]This will delete:[/bold yellow]")
    for item in sorted(STATE_DIR.iterdir()):
        console.print(f"    {item.name}")
    console.print()

    confirmation = console.input(
        "  Type [bold red]RESET[/bold red] to confirm (anything else cancels): ",
    )
    if confirmation.strip() != "RESET":
        console.print("  [dim]Cancelled. Nothing was deleted.[/dim]")
        return

    shutil.rmtree(STATE_DIR)
    console.print("  [green]Reset complete. All XRPL Camp state has been deleted.[/green]")
    console.print("  [dim]Run 'xrpl-camp start' to begin again.[/dim]")


# ---------------------------------------------------------------------------
# Self-check command
# ---------------------------------------------------------------------------


@app.command("self-check")
def self_check() -> None:
    """Diagnose your environment. Paste output into a bug report."""
    checks: list[tuple[str, str, str]] = []  # (status, label, detail)

    # 1. App version
    checks.append(("ok", "Version", xrpl_camp.__version__))

    # 2. Platform
    py = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    checks.append(("ok", "Platform", f"{platform.system()} {platform.machine()} · Python {py}"))

    # 3. Rich rendering
    try:
        t = Table(title="Rich")
        t.add_column("A")
        t.add_row("ok")
        with console.capture() as _:
            console.print(t)
        checks.append(("ok", "Rich rendering", "Table renders correctly"))
    except Exception as exc:
        checks.append(("fail", "Rich rendering", str(exc)))

    # 4. Workspace write test
    try:
        probe = Path(tempfile.mkdtemp(prefix="xrpl-camp-"))
        (probe / "probe.txt").write_text("ok", encoding="utf-8")
        shutil.rmtree(probe)
        checks.append(("ok", "Filesystem write", "Temp write succeeded"))
    except Exception as exc:
        checks.append(("fail", "Filesystem write", str(exc)))

    # 5. State directory
    if STATE_DIR.exists():
        items = list(STATE_DIR.iterdir())
        checks.append(("ok", "State directory", f"{len(items)} file(s) in {STATE_DIR}"))
    else:
        checks.append(("info", "State directory", "Not yet created (run: xrpl-camp start)"))

    # 6. Dependencies (catch all exceptions — PyInstaller may partially bundle)
    for mod_name in ("xrpl", "typer", "rich"):
        try:
            mod = __import__(mod_name)
            ver = getattr(mod, "__version__", getattr(mod, "VERSION", "?"))
            checks.append(("ok", mod_name, str(ver)))
        except Exception as exc:
            checks.append(("fail", mod_name, type(exc).__name__ + ": " + str(exc)[:80]))

    # Print
    icons = {"ok": "[green]OK[/green]", "fail": "[red]FAIL[/red]", "info": "[dim]--[/dim]"}
    console.print()
    for status, label, detail in checks:
        icon = icons.get(status, "[dim]--[/dim]")
        console.print(f"  {icon}  [bold]{label}[/bold]  {detail}")
    console.print()
