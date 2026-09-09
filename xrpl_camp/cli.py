"""XRPL Camp CLI - the teaching console.

Exit codes follow the documented contract:
0 ok | 1 user error | 2 runtime error | 3 partial success.

Every failure here is a :class:`CampError`, so the learner always gets a code
they can quote in a bug report, a plain message, and something to try next.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markup import escape
from rich.table import Table

import xrpl_camp
from xrpl_camp import lessons, wallet
from xrpl_camp.errors import (
    EXIT_OK,
    EXIT_USER,
    CampError,
    CampFailure,
    delete_error,
    format_error,
    pack_invalid_error,
    set_verbose,
    state_corrupt_error,
    wallet_corrupt_error,
    wallet_missing_error,
    write_error,
)
from xrpl_camp.lessons import LESSON_NAMES, format_duration
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
    # Typer's Rich traceback would print a full stack over the top of a
    # perfectly good structured error. Gate B forbids raw stacks; `run()`
    # below is the single place a CampFailure becomes user-facing output.
    pretty_exceptions_enable=False,
)
console = Console()

PROOF_PACK_SCHEMA = "xrpl-camp-proof-pack-v1"


# ---------------------------------------------------------------------------
# Shared plumbing
# ---------------------------------------------------------------------------


def _fail(err: CampError) -> typer.Exit:
    """Print a structured error and build the matching Exit to raise."""
    console.print(format_error(err))
    return typer.Exit(err.exit_code)


def _simulating(flag: bool) -> bool:
    """Resolve dry-run from the command flag or the app-level flag."""
    if flag:
        set_execution_mode(ExecutionMode.DRY_RUN)
    return flag or is_dry_run()


def _read_session(*, dry_run: bool = False) -> Session | None:
    """Read existing session state. Creates nothing. None when there is none."""
    try:
        return DryRunSession.from_existing() if dry_run else Session.load()
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise _fail(state_corrupt_error(f"{type(exc).__name__}: {exc}")) from None


def _get_session(*, dry_run: bool = False) -> Session:
    """Get a session for a command that records progress."""
    try:
        return DryRunSession.from_existing() if dry_run else Session.get_or_create()
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise _fail(state_corrupt_error(f"{type(exc).__name__}: {exc}")) from None


def _read_wallet() -> dict | None:
    """Load the wallet, turning an unreadable file into a clean error."""
    try:
        return wallet.load_wallet()
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise _fail(wallet_corrupt_error(f"{type(exc).__name__}: {exc}")) from None


def _has_progress(session: Session | None) -> bool:
    """True when a session records anything at all."""
    return bool(session and (session.progress or session.completed_lessons))


def _redact(text: str) -> str:
    """Strip the home directory and account name out of diagnostic text."""
    out = text
    names: list[str] = []
    try:
        home = str(Path.home())
    except (RuntimeError, OSError):
        home = ""
    if home:
        out = out.replace(home, "~")
        names.append(Path(home).name)
    names.extend(os.environ.get(var, "") for var in ("USERNAME", "USER", "LOGNAME"))
    for name in names:
        if len(name) >= 3:
            out = re.sub(re.escape(name), "<user>", out, flags=re.IGNORECASE)
    return out


def _version_callback(value: bool) -> None:
    """Print the version and exit. Eager, so it works without a subcommand."""
    if value:
        console.print(f"xrpl-camp {xrpl_camp.__version__}")
        raise typer.Exit(EXIT_OK)


@app.callback()
def main(
    version: Annotated[
        bool, typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Show the installed version and exit",
        )
    ] = False,
    dry_run: Annotated[
        bool, typer.Option(
            "--dry-run",
            help="Simulate every command in this run: no network calls, no disk writes",
        )
    ] = False,
    yes: Annotated[
        bool, typer.Option(
            "--yes", "-y",
            help="Non-interactive: never wait for a keypress (RESET still asks)",
        )
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", help="Include technical detail with errors"),
    ] = False,
) -> None:
    """XRPL Camp — learn the XRPL diary in one sitting."""
    # Set explicitly both ways: these are process globals, and a command must
    # never inherit a mode from an earlier invocation in the same process.
    set_execution_mode(ExecutionMode.DRY_RUN if dry_run else ExecutionMode.REAL)
    lessons.set_non_interactive(yes)
    set_verbose(verbose)


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
    code = lessons.run_guided_flow(dry_run=_simulating(dry_run))
    if code != EXIT_OK:
        raise typer.Exit(code)


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
    session = _read_session()
    if not _has_progress(session):
        console.print("\n  [dim]No training started yet. Run: xrpl-camp start[/dim]\n")
        return

    # One source of truth for "where am I", so the list and the hint below it
    # cannot contradict each other when lessons complete out of order.
    next_lesson = next((n for n in range(1, 7) if not session.is_complete(n)), None)

    console.print()
    for num in range(1, 7):
        name = LESSON_NAMES[num]
        if session.is_complete(num):
            prog = session.get_progress(num)
            duration = ""
            txid = ""
            if prog:
                if prog.duration_seconds > 0:
                    duration = f"  [dim]({format_duration(prog.duration_seconds)})[/dim]"
                if prog.txid:
                    txid = f"\n       [dim]tx: {escape(prog.txid[:16])}…[/dim]"
            console.print(f"  [green]✓[/green] [bold]{name}[/bold]{duration}{txid}")
        elif num == next_lesson:
            console.print(f"  [cyan]▸[/cyan] {name}  [cyan]← next[/cyan]")
        else:
            console.print(f"  [dim]◌ {name}[/dim]")

    # Counted over the six real lessons, so a drifted state file cannot
    # produce "8/6 lessons complete".
    done = sum(1 for n in range(1, 7) if session.is_complete(n))
    total = session.total_duration()
    console.print()
    if done == 6:
        duration_str = f" in {format_duration(total)}" if total > 0 else ""
        console.print(f"  [bold green]All 6 lessons complete{duration_str}.[/bold green]")
    else:
        console.print(f"  [dim]{done}/6 lessons complete[/dim]")

    # --detail: facilitator triage view
    if detail:
        _print_status_detail(session, next_lesson)

    console.print()


def _print_status_detail(session: Session, next_lesson: int | None) -> None:
    """Print expanded status detail for facilitator triage."""
    console.print()
    console.print("  [bold]─── Detail ───[/bold]")

    # Wallet state
    w = _read_wallet()
    if w:
        console.print(f"  [bold]Wallet:[/bold]    {escape(str(w.get('address', '?')))}")
        console.print(f"  [dim]Created:   {escape(str(w.get('created_at', '?')))}[/dim]")
    else:
        console.print("  [bold]Wallet:[/bold]    [yellow]not created[/yellow]")

    # Session timing
    if session.started_at:
        console.print(f"  [bold]Started:[/bold]   {escape(session.started_at)}")

    # Last activity
    if session.progress:
        last = session.progress[-1]
        console.print(
            f"  [bold]Last:[/bold]      Lesson {last.lesson} ({escape(last.name)})"
            f" at {escape(last.completed_at)}",
        )

    # Transaction IDs
    if session.txids:
        for key, txid in session.txids.items():
            console.print(f"  [bold]{escape(str(key))}:[/bold]  {escape(str(txid))}")

    # Stuck hint - the same next lesson the list above marked
    if next_lesson is not None:
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
    dry_run: Annotated[
        bool, typer.Option(
            "--dry-run",
            help="Simulate without writing a seed to disk",
        )
    ] = False,
) -> None:
    """Create or display your Testnet wallet. 'create' writes a seed to disk."""
    simulate = _simulating(dry_run)

    if action == "create":
        if not simulate and wallet.wallet_exists():
            w = _read_wallet()
            if w:
                console.print(f"  Wallet already exists: {escape(str(w['address']))}")
                console.print(
                    "  [dim]Delete .xrpl-camp/wallet.json to create a new one.[/dim]",
                )
                return

        session = _get_session(dry_run=simulate)
        result = lessons.lesson_2_create_wallet(session, dry_run=simulate)
        if not result:
            raise typer.Exit(result.exit_code)

    elif action == "show":
        w = _read_wallet()
        if not w:
            raise _fail(wallet_missing_error())

        console.print(f"\n  [bold]Address:[/bold]  {escape(str(w['address']))}")
        console.print(f"  [dim]Network:  {escape(str(w.get('network', 'testnet')))}[/dim]")
        console.print(f"  [dim]Created:  {escape(str(w.get('created_at', '?')))}[/dim]")
        console.print("\n  [dim]Seed is stored locally. Not shown here.[/dim]")

    else:
        raise _fail(CampError(
            code="BAD_ACTION",
            message=f"Unknown action '{action}'.",
            hint="Try: xrpl-camp wallet create — or xrpl-camp wallet show",
            exit_code=EXIT_USER,
        ))


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
    simulate = _simulating(dry_run)
    session = _get_session(dry_run=simulate)
    result = lessons.lesson_3_fund_wallet(session, dry_run=simulate)
    if not result:
        raise typer.Exit(result.exit_code)


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
    """Send a memo payment to your mailbox wallet on the XRPL Testnet."""
    simulate = _simulating(dry_run)
    session = _get_session(dry_run=simulate)
    result = lessons.lesson_4_send_payment(session, memo=memo, dry_run=simulate)
    if not result:
        raise typer.Exit(result.exit_code)


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
    simulate = _simulating(dry_run)
    session = _get_session(dry_run=simulate)
    result = lessons.lesson_5_verify_tx(session, txid=tx, dry_run=simulate)
    if not result:
        raise typer.Exit(result.exit_code)


# ---------------------------------------------------------------------------
# Certificate command
# ---------------------------------------------------------------------------


@app.command()
def certificate(
    dry_run: Annotated[
        bool, typer.Option(
            "--dry-run",
            help="Show what would be sealed without writing any files",
        )
    ] = False,
) -> None:
    """Generate a completion certificate and proof pack. Writes two files."""
    simulate = _simulating(dry_run)

    # Read-only: a command that is about to refuse should not leave state
    # behind for having been run.
    session = _read_session(dry_run=simulate)
    if not _has_progress(session):
        raise _fail(CampError(
            code="NO_PROGRESS",
            message="No lessons completed yet, so there is nothing to certify.",
            hint="Run: xrpl-camp start",
            exit_code=EXIT_USER,
        ))

    result = lessons.lesson_6_certificate(session, dry_run=simulate)
    if not result:
        raise typer.Exit(result.exit_code)


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

    def reject(err: CampError) -> typer.Exit:
        if json_output:
            print(json_mod.dumps({
                "valid": False,
                "hash_match": False,
                "file": str(file),
                "code": err.code,
                "message": err.message,
            }, indent=2))
            return typer.Exit(err.exit_code)
        return _fail(err)

    if not file.exists():
        raise reject(CampError(
            code="FILE_NOT_FOUND",
            message=f"File not found: {file}",
            hint="Check the path. The proof pack is usually xrpl_camp_proof_pack.json.",
            exit_code=EXIT_USER,
        ))

    try:
        pack = json_mod.loads(file.read_text(encoding="utf-8"))
    except (json_mod.JSONDecodeError, ValueError, OSError) as e:
        raise reject(pack_invalid_error(
            "invalid JSON", f"{type(e).__name__}: {e}",
        )) from None

    # Valid JSON is not the same as a proof pack. A list, a number or the
    # certificate file sitting next to it must not reach the verifier.
    if not isinstance(pack, dict):
        raise reject(pack_invalid_error(
            f"the file contains a JSON {type(pack).__name__}, not an object",
        ))

    schema = str(pack.get("schema", ""))
    if schema != PROOF_PACK_SCHEMA:
        raise reject(pack_invalid_error(
            f"schema is {schema or 'missing'}, expected {PROOF_PACK_SCHEMA}",
        ))

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
            console.print(f"\n  [red]❌ FAIL[/red] — {escape(message)}\n")

        console.print(f"  [bold]File:[/bold]     {escape(str(file))}")
        console.print(f"  [bold]Schema:[/bold]   {escape(str(pack.get('schema', 'unknown')))}")
        console.print(f"  [bold]Address:[/bold]  {escape(str(pack.get('address', 'unknown')))}")
        console.print(f"  [bold]Network:[/bold]  {escape(str(pack.get('network', 'unknown')))}")
        console.print(f"  [bold]Lessons:[/bold]  {len(pack.get('lessons', []))}")
        console.print(f"  [bold]SHA-256:[/bold]  {escape(str(pack.get('sha256', 'none')))}")
        console.print()

    if not valid:
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# Reset command
# ---------------------------------------------------------------------------


@app.command()
def reset(
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="List what would be deleted, delete nothing"),
    ] = False,
) -> None:
    """Wipe all XRPL Camp state (.xrpl-camp/ directory).

    Requires you to type RESET to confirm. This cannot be undone.
    """
    simulate = _simulating(dry_run)

    if not STATE_DIR.exists():
        console.print("  [dim]Nothing to reset. No .xrpl-camp/ directory found.[/dim]")
        return

    # Show what will be deleted
    try:
        items = sorted(STATE_DIR.iterdir())
    except OSError as exc:
        raise _fail(delete_error(str(STATE_DIR), f"{type(exc).__name__}: {exc}")) from None

    console.print("\n  [bold yellow]This will delete:[/bold yellow]")
    for item in items:
        console.print(f"    {escape(item.name)}")
    console.print(
        "  [dim]This is Testnet data — you can recreate it by running start again.[/dim]",
    )
    console.print()

    if simulate:
        console.print("  [yellow][DRY RUN][/yellow] Nothing was deleted.")
        return

    confirmation = console.input(
        "  Type [bold red]RESET[/bold red] to confirm (anything else cancels): ",
    )
    if confirmation.strip() != "RESET":
        console.print("  [dim]Cancelled. Nothing was deleted.[/dim]")
        return

    try:
        shutil.rmtree(STATE_DIR)
    except OSError as exc:
        survivors = []
        try:
            survivors = sorted(p.name for p in STATE_DIR.iterdir())
        except OSError:
            survivors = []
        if survivors:
            console.print(
                "  [yellow]Still there:[/yellow] " + escape(", ".join(survivors)),
            )
        raise _fail(delete_error(str(STATE_DIR), f"{type(exc).__name__}: {exc}")) from None

    console.print("  [green]Clean slate.[/green] All XRPL Camp state has been removed.")
    console.print("  [dim]Run 'xrpl-camp start' whenever you're ready to go again.[/dim]")


# ---------------------------------------------------------------------------
# Diagnostics (self-check + support-bundle)
# ---------------------------------------------------------------------------


#: Import name -> distribution name, for importlib.metadata.
_DIST_NAMES = {"xrpl": "xrpl-py", "typer": "typer", "rich": "rich"}


def _dependency_version(mod_name: str) -> str:
    """Installed version of a dependency, or '' if it cannot be determined.

    Module __version__ attributes are unreliable (xrpl-py and rich do not
    define one), so ask the installed distribution metadata instead.
    """
    from importlib.metadata import version

    try:
        return version(_DIST_NAMES.get(mod_name, mod_name))
    except Exception:
        return ""


def _collect_checks() -> list[tuple[str, str, str]]:
    """Collect diagnostic checks. Returns list of (status, label, detail)."""
    checks: list[tuple[str, str, str]] = []

    # 1. App version
    checks.append(("ok", "Version", xrpl_camp.__version__))

    # 2. Platform
    py = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    checks.append(("ok", "Platform", f"{platform.system()} {platform.machine()} · Python {py}"))

    # 3. Console encoding - the thing that breaks output on Windows
    encoding = getattr(sys.stdout, "encoding", "") or "unknown"
    checks.append(("ok", "Console encoding", encoding))

    # 4. Rich rendering
    try:
        t = Table(title="Rich")
        t.add_column("A")
        t.add_row("ok")
        with console.capture() as _:
            console.print(t)
        checks.append(("ok", "Rich rendering", "Table renders correctly"))
    except Exception as exc:
        checks.append(("fail", "Rich rendering", str(exc)))

    # 5. Workspace write test
    try:
        probe = Path(tempfile.mkdtemp(prefix="xrpl-camp-"))
        (probe / "probe.txt").write_text("ok", encoding="utf-8")
        shutil.rmtree(probe)
        checks.append(("ok", "Filesystem write", "Temp write succeeded"))
    except Exception as exc:
        checks.append(("fail", "Filesystem write", str(exc)))

    # 6. State directory
    if STATE_DIR.exists():
        try:
            items = list(STATE_DIR.iterdir())
            checks.append(("ok", "State directory", f"{len(items)} file(s) in {STATE_DIR}"))
        except OSError as exc:
            checks.append(("fail", "State directory", f"{STATE_DIR} unreadable: {exc}"))
    else:
        checks.append(("info", "State directory", "Not yet created (run: xrpl-camp start)"))

    # 7. Dependencies (catch all exceptions - PyInstaller may partially bundle)
    for mod_name in ("xrpl", "typer", "rich"):
        try:
            __import__(mod_name)
        except Exception as exc:
            checks.append(("fail", mod_name, type(exc).__name__ + ": " + str(exc)[:80]))
            continue
        ver = _dependency_version(mod_name)
        if ver:
            checks.append(("ok", mod_name, ver))
        else:
            checks.append(("info", mod_name, "-- (imported; version not reported)"))

    return checks


def _print_checks(checks: list[tuple[str, str, str]]) -> None:
    """Pretty-print diagnostic checks to console."""
    icons = {"ok": "[green]OK[/green]", "fail": "[red]FAIL[/red]", "info": "[dim]--[/dim]"}
    console.print()
    for status, label, detail in checks:
        icon = icons.get(status, "[dim]--[/dim]")
        console.print(f"  {icon}  [bold]{escape(label)}[/bold]  {escape(detail)}")
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
    checks = _collect_checks()
    _print_checks(checks)

    failed = [label for status, label, _ in checks if status == "fail"]
    if failed:
        raise _fail(CampError(
            code="SELF_CHECK_FAILED",
            message="These checks failed: " + ", ".join(failed) + ".",
            hint="Reinstall with 'pipx install --force xrpl-camp', then run self-check again.",
            exit_code=EXIT_USER,
        ))


@app.command("support-bundle")
def support_bundle(
    out: Annotated[
        str, typer.Option("--out", help="Where to write the zip (a file or a folder)"),
    ] = "",
) -> None:
    """Write a diagnostic zip for bug reports. Attach it to your issue."""
    import datetime
    import json
    import zipfile

    checks = _collect_checks()
    _print_checks(checks)

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bundle_name = f"xrpl-camp-support-{ts}.zip"
    if not out:
        bundle_path = Path.cwd() / bundle_name
    elif Path(out).is_dir():
        bundle_path = Path(out) / bundle_name
    else:
        bundle_path = Path(out)

    # Say what is going in before it goes in. This file is destined for a
    # public issue tracker.
    console.print("  [bold]This bundle will contain:[/bold]")
    console.print("    self-check.txt      the diagnostics printed above")
    console.print("    session.json        your lesson progress (no seed)")
    console.print("    state-listing.txt   the names of files in .xrpl-camp/ (no contents)")
    console.print("    environment.json    tool version, OS, Python version")
    console.print(
        "  [dim]No seed, no wallet file, and no user names or home paths.[/dim]\n",
    )

    env_info = {
        "tool": "xrpl-camp",
        "version": xrpl_camp.__version__,
        "platform": _redact(platform.platform()),
        "arch": platform.machine(),
        "python": _redact(sys.version),
        "cwd_writable": os.access(Path.cwd(), os.W_OK),
        "state_dir": str(STATE_DIR),
        "state_dir_present": STATE_DIR.exists(),
        "timestamp": ts,
    }

    try:
        with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # 1. Self-check output
            zf.writestr("self-check.txt", _redact(_checks_to_text(checks)))

            # 2. Sanitized config (session state, no secrets)
            if STATE_DIR.exists():
                session_file = STATE_DIR / "session.json"
                if session_file.exists():
                    try:
                        data = json.loads(session_file.read_text(encoding="utf-8"))
                        # Strip wallet secrets if present
                        if isinstance(data, dict):
                            for key in ("seed", "secret", "private_key"):
                                data.pop(key, None)
                        zf.writestr("session.json", _redact(json.dumps(data, indent=2)))
                    except (OSError, ValueError) as exc:
                        zf.writestr("session.json", f"(could not read: {type(exc).__name__})")

                # 3. State file listing (names only, no content)
                try:
                    listing = "\n".join(f.name for f in sorted(STATE_DIR.iterdir()))
                except OSError as exc:
                    listing = f"(could not list: {type(exc).__name__})"
                zf.writestr("state-listing.txt", listing)

            # 4. Environment summary
            zf.writestr("environment.json", json.dumps(env_info, indent=2))
    except OSError as exc:
        raise _fail(write_error(str(bundle_path), f"{type(exc).__name__}: {exc}")) from None

    console.print(f"  [green]Bundle written:[/green] {escape(str(bundle_path))}")
    console.print("  [dim]Attach this file to your GitHub issue.[/dim]")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run() -> None:
    """Console-script entry point.

    The ONE place a :class:`CampFailure` becomes user-facing output. Three
    modules raise them (corrupt state, seed-leak refusal, artifact write), and
    they reach here from anywhere in the call tree — including code paths a
    command never wrapped, which is exactly where the raw tracebacks were
    coming from. Catching the shared base once means a module added later is
    covered before it is written.
    """
    try:
        app()
    except CampFailure as exc:
        console.print(format_error(exc.error))
        raise SystemExit(exc.exit_code) from None
