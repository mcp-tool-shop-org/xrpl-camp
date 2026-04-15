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
from xrpl_camp.lessons import LESSON_NAMES, _format_duration
from xrpl_camp.models import (
    STATE_DIR,
    DryRunSession,
    ExecutionMode,
    Session,
    is_dry_run,
    set_execution_mode,
)

app = typer.Typer(
    name="xrpl-camp",
    help="XRPL Camp — learn the XRPL diary in one sitting.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def start(
    dry_run: Annotated[
        bool, typer.Option(
            "--dry-run",
            help="Non-mutating simulation: no network calls, no disk writes",
        )
    ] = False,
) -> None:
    """Guided flow through all 6 lessons."""
    if dry_run:
        set_execution_mode(ExecutionMode.DRY_RUN)
    lessons.run_guided_flow(dry_run=dry_run)


# ---------------------------------------------------------------------------
# Status command
# ---------------------------------------------------------------------------


@app.command()
def status(
    detail: Annotated[
        bool, typer.Option(
            "--detail", help="Expanded view with wallet state and timing",
        )
    ] = False,
) -> None:
    """Show your training progress."""
    session = Session.load()
    if session is None or not session.progress:
        console.print("\n  [dim]No training started yet. Run: xrpl-camp start[/dim]\n")
        return

    console.print()
    for num in range(1, 7):
        name = LESSON_NAMES[num]
        prog = session.get_progress(num)
        if prog:
            # Completed
            duration = ""
            if prog.duration_seconds > 0:
                duration = f"  [dim]({_format_duration(prog.duration_seconds)})[/dim]"
            txid = ""
            if prog.txid:
                txid = f"\n       [dim]tx: {prog.txid[:16]}…[/dim]"
            console.print(f"  [green]✓[/green] [bold]{name}[/bold]{duration}{txid}")
        else:
            # Next up or pending
            is_next = all(
                session.is_complete(i) for i in range(1, num)
            )
            if is_next:
                console.print(f"  [cyan]▸[/cyan] {name}  [cyan]← next[/cyan]")
            else:
                console.print(f"  [dim]◌ {name}[/dim]")

    # Summary line
    done = len(session.completed_lessons)
    total = session.total_duration()
    console.print()
    if done == 6:
        duration_str = f" in {_format_duration(total)}" if total > 0 else ""
        console.print(f"  [bold green]All 6 lessons complete{duration_str}.[/bold green]")
    else:
        console.print(f"  [dim]{done}/6 lessons complete[/dim]")

    # --detail: facilitator triage view
    if detail:
        _print_status_detail(session, done)

    console.print()


def _print_status_detail(session: Session, done: int) -> None:
    """Print expanded status detail for facilitator triage."""
    console.print()
    console.print("  [bold]─── Detail ───[/bold]")

    # Wallet state
    w = wallet.load_wallet()
    if w:
        console.print(f"  [bold]Wallet:[/bold]    {w['address']}")
        console.print(f"  [dim]Created:   {w.get('created_at', '?')}[/dim]")
    else:
        console.print("  [bold]Wallet:[/bold]    [yellow]not created[/yellow]")

    # Session timing
    if session.started_at:
        console.print(f"  [bold]Started:[/bold]   {session.started_at}")

    # Last activity
    if session.progress:
        last = session.progress[-1]
        console.print(
            f"  [bold]Last:[/bold]      Lesson {last.lesson} ({last.name})"
            f" at {last.completed_at}",
        )

    # Transaction IDs
    if session.txids:
        for key, txid in session.txids.items():
            console.print(f"  [bold]{key}:[/bold]  {txid}")

    # Stuck hint — if not all done, show what to run next
    if done < 6:
        next_lesson = done + 1
        next_name = LESSON_NAMES.get(next_lesson, "?")
        hints = {
            1: "xrpl-camp start",
            2: "xrpl-camp wallet create",
            3: "xrpl-camp fund",
            4: 'xrpl-camp send --memo "your message"',
            5: "xrpl-camp verify --tx <hash>",
            6: "xrpl-camp certificate",
        }
        hint = hints.get(next_lesson, "xrpl-camp start")
        console.print(
            f"\n  [cyan]Next:[/cyan] Lesson {next_lesson} — {next_name}",
        )
        console.print(f"  [dim]Run: {hint}[/dim]")


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
        bool, typer.Option(
            "--dry-run",
            help="Simulate without network calls or state changes",
        )
    ] = False,
) -> None:
    """Fund your wallet via the Testnet faucet."""
    if dry_run:
        set_execution_mode(ExecutionMode.DRY_RUN)
    session = DryRunSession.from_existing() if dry_run else Session.get_or_create()
    lessons.lesson_3_fund_wallet(session, dry_run=dry_run)


# ---------------------------------------------------------------------------
# Send command
# ---------------------------------------------------------------------------


@app.command()
def send(
    memo: Annotated[str, typer.Option("--memo", "-m", help="Memo text")] = "",
    dry_run: Annotated[
        bool, typer.Option(
            "--dry-run",
            help="Simulate without network calls or state changes",
        )
    ] = False,
) -> None:
    """Send a self-payment with a memo to the XRPL Testnet."""
    if dry_run:
        set_execution_mode(ExecutionMode.DRY_RUN)
    session = DryRunSession.from_existing() if dry_run else Session.get_or_create()
    lessons.lesson_4_send_payment(session, memo=memo, dry_run=dry_run)


# ---------------------------------------------------------------------------
# Verify command
# ---------------------------------------------------------------------------


@app.command()
def verify(
    tx: Annotated[str, typer.Option("--tx", help="Transaction hash to verify")] = "",
    dry_run: Annotated[
        bool, typer.Option(
            "--dry-run",
            help="Simulate without network calls or state changes",
        )
    ] = False,
) -> None:
    """Verify a transaction on the XRPL Testnet."""
    if dry_run:
        set_execution_mode(ExecutionMode.DRY_RUN)
    session = DryRunSession.from_existing() if dry_run else Session.get_or_create()
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
# Proof pack commands
# ---------------------------------------------------------------------------


proof_app = typer.Typer(
    name="proof",
    help="Proof pack commands.",
    no_args_is_help=True,
)
app.add_typer(proof_app, name="proof")


@proof_app.command("verify")
def proof_verify(
    file: Annotated[Path, typer.Argument(help="Path to proof pack JSON file")],
    json_output: Annotated[
        bool, typer.Option("--json", help="Machine-readable JSON output")
    ] = False,
) -> None:
    """Verify a proof pack's integrity."""
    import json as json_mod

    from xrpl_camp.proof_pack import verify_proof_pack

    if not file.exists():
        console.print(f"[red]File not found: {file}[/red]")
        raise typer.Exit(1)

    try:
        pack = json_mod.loads(file.read_text(encoding="utf-8"))
    except (json_mod.JSONDecodeError, ValueError) as e:
        console.print(f"[red]Invalid JSON: {e}[/red]")
        raise typer.Exit(1) from None

    valid, message = verify_proof_pack(pack)

    if json_output:
        result = {
            "valid": valid,
            "hash_match": valid,
            "file": str(file),
            "schema": pack.get("schema", ""),
            "address": pack.get("address", ""),
            "network": pack.get("network", ""),
            "lessons_completed": len(pack.get("lessons", [])),
            "tool_version": pack.get("tool_version", ""),
            "sha256": pack.get("sha256", ""),
            "message": message,
        }
        print(json_mod.dumps(result, indent=2))
    else:
        if valid:
            console.print("\n  [green]✅ PASS[/green] — Proof pack integrity verified.\n")
        else:
            console.print(f"\n  [red]❌ FAIL[/red] — {message}\n")

        console.print(f"  [bold]File:[/bold]     {file}")
        console.print(f"  [bold]Schema:[/bold]   {pack.get('schema', 'unknown')}")
        console.print(f"  [bold]Address:[/bold]  {pack.get('address', 'unknown')}")
        console.print(f"  [bold]Network:[/bold]  {pack.get('network', 'unknown')}")
        console.print(f"  [bold]Lessons:[/bold]  {len(pack.get('lessons', []))}")
        console.print(f"  [bold]SHA-256:[/bold]  {pack.get('sha256', 'none')}")
        console.print()

    if not valid:
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# Reset command
# ---------------------------------------------------------------------------


@app.command()
def reset() -> None:
    """Wipe all XRPL Camp state (.xrpl-camp/ directory).

    Requires you to type RESET to confirm. This cannot be undone.
    """
    if is_dry_run():
        console.print("  [yellow]Reset is not available in dry-run mode.[/yellow]")
        return

    if not STATE_DIR.exists():
        console.print("  [dim]Nothing to reset. No .xrpl-camp/ directory found.[/dim]")
        return

    # Show what will be deleted
    console.print("\n  [bold yellow]This will delete:[/bold yellow]")
    for item in sorted(STATE_DIR.iterdir()):
        console.print(f"    {item.name}")
    console.print(
        "  [dim]This is Testnet data \u2014 you can recreate it by running start again.[/dim]",
    )
    console.print()

    confirmation = console.input(
        "  Type [bold red]RESET[/bold red] to confirm (anything else cancels): ",
    )
    if confirmation.strip() != "RESET":
        console.print("  [dim]Cancelled. Nothing was deleted.[/dim]")
        return

    shutil.rmtree(STATE_DIR)
    console.print("  [green]Clean slate.[/green] All XRPL Camp state has been removed.")
    console.print("  [dim]Run 'xrpl-camp start' whenever you're ready to go again.[/dim]")


# ---------------------------------------------------------------------------
# Diagnostics (self-check + support-bundle)
# ---------------------------------------------------------------------------


def _collect_checks() -> list[tuple[str, str, str]]:
    """Collect diagnostic checks. Returns list of (status, label, detail)."""
    checks: list[tuple[str, str, str]] = []

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

    return checks


def _print_checks(checks: list[tuple[str, str, str]]) -> None:
    """Pretty-print diagnostic checks to console."""
    icons = {"ok": "[green]OK[/green]", "fail": "[red]FAIL[/red]", "info": "[dim]--[/dim]"}
    console.print()
    for status, label, detail in checks:
        icon = icons.get(status, "[dim]--[/dim]")
        console.print(f"  {icon}  [bold]{label}[/bold]  {detail}")
    console.print()


def _checks_to_text(checks: list[tuple[str, str, str]]) -> str:
    """Render checks as plain text for support bundles."""
    lines = []
    icons = {"ok": "OK", "fail": "FAIL", "info": "--"}
    for status, label, detail in checks:
        icon = icons.get(status, "--")
        lines.append(f"  {icon}  {label}  {detail}")
    return "\n".join(lines)


@app.command("self-check")
def self_check() -> None:
    """Diagnose your environment. Paste output into a bug report."""
    _print_checks(_collect_checks())


@app.command("support-bundle")
def support_bundle() -> None:
    """Write a diagnostic zip for bug reports. Attach it to your issue."""
    import datetime
    import json
    import zipfile

    checks = _collect_checks()
    _print_checks(checks)

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bundle_name = f"xrpl-camp-support-{ts}.zip"
    bundle_path = Path.cwd() / bundle_name

    with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Self-check output
        zf.writestr("self-check.txt", _checks_to_text(checks))

        # 2. Sanitized config (session state, no secrets)
        if STATE_DIR.exists():
            session_file = STATE_DIR / "session.json"
            if session_file.exists():
                try:
                    data = json.loads(session_file.read_text(encoding="utf-8"))
                    # Strip wallet secrets if present
                    for key in ("seed", "secret", "private_key"):
                        data.pop(key, None)
                    zf.writestr("session.json", json.dumps(data, indent=2))
                except Exception:
                    zf.writestr("session.json", "(could not read)")

            # 3. State file listing (names only, no content)
            listing = "\n".join(f.name for f in sorted(STATE_DIR.iterdir()))
            zf.writestr("state-listing.txt", listing)

        # 4. Environment summary
        env_info = {
            "tool": "xrpl-camp",
            "version": xrpl_camp.__version__,
            "platform": platform.platform(),
            "arch": platform.machine(),
            "python": sys.version,
            "cwd": str(Path.cwd()),
            "state_dir": str(STATE_DIR),
            "timestamp": ts,
        }
        zf.writestr("environment.json", json.dumps(env_info, indent=2))

    console.print(f"  [green]Bundle written:[/green] {bundle_path}")
    console.print("  [dim]Attach this file to your GitHub issue.[/dim]")
