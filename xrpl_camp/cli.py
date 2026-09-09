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
from rich.panel import Panel
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
    record_error,
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
    help="XRPL Camp — learn the XRP Ledger in one sitting.",
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
    record_error(err, command=" ".join(sys.argv[1:3]))
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


def _read_mailbox_address() -> str:
    """The lesson-4 mailbox address, or '' if there is not one yet."""
    try:
        record = wallet.load_mailbox()
    except Exception:
        return ""
    return str(record.get("address", "")) if record else ""


#: Words that are part of a platform or Python string, never a person. An
#: unanchored case-insensitive substitution over the account name mangled the
#: exact data a support bundle exists to preserve: USERNAME='win' turned
#: 'Windows-11-10.0.26340-SP0' into '<user>dows-11-...', 'python' ate the word
#: Python, and 'arm' would eat ARM64 on Apple Silicon. Redacting a path is the
#: goal; mangling the OS build string is collateral.
_PLATFORM_TOKENS = frozenset({
    "windows", "python", "amd", "arm", "x86", "x64", "msc", "darwin", "linux",
    "win", "mac", "cpython", "intel", "gcc", "clang", "sp0", "bit",
})


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
        if len(name) < 3 or name.lower() in _PLATFORM_TOKENS:
            continue
        # Word-bounded: 'dev' should not eat the 'dev' in 'devnet'.
        out = re.sub(
            r"\b" + re.escape(name) + r"\b", "<user>", out, flags=re.IGNORECASE,
        )
    return out


def _tool_version() -> str:
    """Installed version, preferring the distribution metadata.

    Three surfaces reported the version and two of them read a hand-maintained
    literal while the proof pack read the installed distribution - so a release
    that bumped pyproject.toml and missed __init__.py, or a stale editable
    shadowing a pipx install, would have the version a user quotes disagree
    with the version the proof pack cryptographically attests to. Same order
    proof_pack already uses.
    """
    from importlib.metadata import version

    try:
        return version("xrpl-camp")
    except Exception:
        return xrpl_camp.__version__


def _version_callback(value: bool) -> None:
    """Print the version and exit. Eager, so it works without a subcommand."""
    if value:
        console.print(f"xrpl-camp {_tool_version()}")
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
    """XRPL Camp — learn the XRP Ledger in one sitting."""
    # Set explicitly both ways: these are process globals, and a command must
    # never inherit a mode from an earlier invocation in the same process.
    set_execution_mode(ExecutionMode.DRY_RUN if dry_run else ExecutionMode.REAL)
    lessons.set_non_interactive(yes)
    set_verbose(verbose)


@app.command()
def start(
    memo: Annotated[
        str, typer.Option(
            "--memo", "-m",
            help="Lesson 4's message. Needed to script the guided flow, since a "
                 "piped or --yes run cannot be asked for one",
        )
    ] = "",
    dry_run: Annotated[
        bool, typer.Option(
            "--dry-run",
            help="Non-mutating simulation: no network calls, no disk writes",
        )
    ] = False,
) -> None:
    """Guided flow through all 6 lessons."""
    code = lessons.run_guided_flow(dry_run=_simulating(dry_run), memo=memo)
    if code != EXIT_OK:
        raise typer.Exit(code)


# ---------------------------------------------------------------------------
# Status command
# ---------------------------------------------------------------------------


@app.command()
def status(
    detail: Annotated[
        bool, typer.Option(
            "--detail", help="Expanded view with wallet state, endpoint and timing",
        )
    ] = False,
    json_output: Annotated[
        bool, typer.Option(
            "--json", help="Machine-readable output, for scripting a room of learners",
        )
    ] = False,
) -> None:
    """Show your training progress."""
    session = _read_session()

    if json_output:
        _print_status_json(session)
        return

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


def _print_status_json(session: Session | None) -> None:
    """Emit the whole triage view as one JSON object.

    `proof verify` grew --json and `status` did not, so a workshop script had
    no way to read thirty learners' progress except by parsing panels.
    """
    import json as json_mod

    from xrpl_camp import transport

    wallet_record = None
    try:
        wallet_record = wallet.load_wallet()
    except Exception:
        wallet_record = None

    address = str(wallet_record.get("address", "")) if wallet_record else ""
    drops, why = _live_balance(address) if address else (None, "no wallet")

    payload = {
        "tool_version": _tool_version(),
        "endpoint": transport.get_rpc_url(),
        "network": transport.network_label_for_url(),
        "endpoint_pinned": bool(os.environ.get("XRPL_CAMP_RPC_URL", "").strip()),
        "wallet_address": address,
        "mailbox_address": _read_mailbox_address(),
        "balance_drops": drops,
        "balance_error": why,
        "started_at": (session.started_at if session else "") or "",
        "completed_lessons": sorted(
            n for n in range(1, 7) if session and session.is_complete(n)
        ),
        "lessons_complete": sum(
            1 for n in range(1, 7) if session and session.is_complete(n)
        ),
        "next_lesson": next(
            (n for n in range(1, 7) if not (session and session.is_complete(n))), None,
        ),
        "txids": dict(session.txids) if session else {},
        "total_duration_seconds": session.total_duration() if session else 0,
        "artifacts": [str(p) for p in _artifact_paths()],
        "state_dir": str(STATE_DIR),
    }
    print(json_mod.dumps(payload, indent=2, default=str))


def _ago(iso: str) -> str:
    """'3 minutes ago', or '' when the timestamp cannot be read.

    Raw ISO-8601 with microseconds is noise for a beginner and harder to scan
    for a facilitator than a relative time. The exact value stays alongside.
    """
    import datetime as dt

    try:
        when = dt.datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return ""
    if when.tzinfo is None:
        when = when.replace(tzinfo=dt.UTC)
    seconds = (dt.datetime.now(dt.UTC) - when).total_seconds()
    if seconds < 0:
        return ""
    if seconds < 90:
        return f"{int(seconds)} seconds ago"
    if seconds < 5400:
        return f"{int(seconds // 60)} minutes ago"
    if seconds < 172800:
        return f"{int(seconds // 3600)} hours ago"
    return f"{int(seconds // 86400)} days ago"


def _stamp(iso: str) -> str:
    """'3 minutes ago (2026-09-09T04:05:37+00:00)' - relative first."""
    relative = _ago(iso)
    return f"{relative}  [dim]({escape(iso)})[/dim]" if relative else escape(iso)


def _artifact_paths() -> list[Path]:
    """Certificate and proof pack, if they have been written here."""
    from xrpl_camp.certificate import CERTIFICATE_FILE
    from xrpl_camp.proof_pack import PROOF_PACK_FILE

    found = []
    for name in (CERTIFICATE_FILE, PROOF_PACK_FILE):
        path = Path.cwd() / name
        if path.exists():
            found.append(path.resolve())
    return found


def _live_balance(address: str) -> tuple[int | None, str]:
    """Balance in drops, or (None, why-not). Never raises.

    The one question a facilitator has at lessons 3 and 4 is "did the faucet
    actually land". A failed read must degrade to a sentence, never take the
    triage command down with it - and never make somebody who is already stuck
    wait out a ten-second client timeout to be told the endpoint is not there,
    which is why the cheap reachability probe runs first.
    """
    from xrpl_camp import transport

    url = transport.get_rpc_url()
    reachable, _, why = _tcp_probe(url)
    if not reachable:
        return None, why.split(":")[0] or "endpoint unreachable"
    try:
        return int(transport.get_balance(address)), ""
    except Exception as exc:
        return None, f"{type(exc).__name__}"


def _print_status_detail(session: Session, next_lesson: int | None) -> None:
    """Print expanded status detail for facilitator triage.

    Everything here answers a question somebody actually asks across a room:
    which server is this learner talking to, did their funding land, which
    version are they on, and where did the certificate go.
    """
    from xrpl_camp import transport

    console.print()
    console.print("  [bold]─── Detail ───[/bold]")

    console.print(f"  [bold]Version:[/bold]   {escape(_tool_version())}")

    # Endpoint. A stale XRPL_CAMP_RPC_URL exported in a shell is otherwise
    # completely invisible, and it is the single likeliest cause of "it works
    # for everyone but me".
    url = transport.get_rpc_url()
    label = transport.network_label_for_url(url)
    pinned = os.environ.get("XRPL_CAMP_RPC_URL", "").strip()
    console.print(f"  [bold]Endpoint:[/bold]  {escape(url)}  [dim]({escape(label)})[/dim]")
    if pinned:
        console.print(
            "  [yellow]XRPL_CAMP_RPC_URL is set in this shell — that is where "
            "the above comes from.[/yellow]",
        )

    # Wallet state
    w = _read_wallet()
    if w:
        address = str(w.get("address", "?"))
        console.print(f"  [bold]Wallet:[/bold]    {escape(address)}")
        console.print(f"  [dim]Created:   {_stamp(str(w.get('created_at', '')))}[/dim]")
        drops, why = _live_balance(address)
        if drops is None:
            console.print(f"  [bold]Balance:[/bold]   [yellow]could not read — {why}[/yellow]")
        else:
            console.print(
                f"  [bold]Balance:[/bold]   {drops / 1_000_000:.2f} XRP ({drops:,} drops)",
            )
    else:
        console.print("  [bold]Wallet:[/bold]    [yellow]not created[/yellow]")

    mailbox = _read_mailbox_address()
    if mailbox:
        console.print(f"  [bold]Mailbox:[/bold]   {escape(mailbox)}")

    # Session timing
    if session.started_at:
        console.print(f"  [bold]Started:[/bold]   {_stamp(session.started_at)}")

    # Last activity
    if session.progress:
        last = session.progress[-1]
        console.print(
            f"  [bold]Last:[/bold]      Lesson {last.lesson} ({escape(last.name)})"
            f" — {_stamp(last.completed_at)}",
        )

    # Transaction IDs
    if session.txids:
        for key, txid in session.txids.items():
            console.print(f"  [bold]{escape(str(key))}:[/bold]  {escape(str(txid))}")

    # Where the deliverables went. Nothing in the CLI could answer this.
    for path in _artifact_paths():
        console.print(f"  [bold]Artifact:[/bold]  {escape(str(path))}")

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
    out: Annotated[
        str, typer.Option(
            "--out",
            help="Folder to write the two files into (default: this directory)",
        ),
    ] = "",
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

    result = lessons.lesson_6_certificate(session, dry_run=simulate, out_dir=out)
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


#: Environment variables xrpl-camp reads. None of them hold key material, and
#: between them they explain most of "it works for everyone but me".
_CAMP_ENV_VARS = (
    "XRPL_CAMP_RPC_URL",
    "XRPL_CAMP_FAUCET_URL",
    "XRPL_CAMP_HOME",
    "XRPL_CAMP_ALLOW_ANY_NETWORK",
    "XRPL_CAMP_ALLOW_ANY_ENDPOINT",
    "XRPL_CAMP_NO_UTF8",
    "XRPL_CAMP_RETRIES",
)

#: How long a diagnostic probe may block. Bounded on purpose: this command is
#: run by somebody who is already stuck.
_PROBE_TIMEOUT_SECONDS = 4.0


def _camp_environment() -> dict[str, str]:
    """The XRPL_CAMP_* variables that are actually set, redacted."""
    return {
        name: _redact(os.environ[name])
        for name in _CAMP_ENV_VARS
        if os.environ.get(name, "").strip()
    }


def _tcp_probe(url: str) -> tuple[bool, float, str]:
    """Open and close a TCP connection to `url`. Returns (reachable, ms, why)."""
    import socket
    import time
    from urllib.parse import urlsplit

    parts = urlsplit(url)
    host = parts.hostname or ""
    port = parts.port or (443 if parts.scheme == "https" else 80)
    if not host:
        return False, 0.0, f"no host in {url}"
    started = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=_PROBE_TIMEOUT_SECONDS):
            pass
    except Exception as exc:
        return False, (time.monotonic() - started) * 1000, f"{type(exc).__name__}: {exc}"
    return True, (time.monotonic() - started) * 1000, ""


def _collect_network_checks() -> list[tuple[str, str, str]]:
    """Ask the network the questions a stuck learner is actually stuck on.

    Kept separate from the local checks because they answer different questions
    and carry different consequences: a broken install is fixed by reinstalling,
    and a dead endpoint is not. Nothing here can raise - a diagnostic that
    crashes is worse than one that says nothing.
    """
    from xrpl_camp import transport

    checks: list[tuple[str, str, str]] = []
    url = transport.get_rpc_url()
    pinned = os.environ.get("XRPL_CAMP_RPC_URL", "").strip()

    checks.append((
        "ok" if not pinned else "info",
        "Endpoint",
        f"{url}  ({transport.network_label_for_url(url)})"
        + ("  [set by XRPL_CAMP_RPC_URL]" if pinned else ""),
    ))

    reachable, ms, why = _tcp_probe(url)
    if not reachable:
        checks.append(("warn", "Endpoint reachable", f"no — {why}"))
        return checks
    checks.append(("ok", "Endpoint reachable", f"yes, {ms:.0f} ms to open a connection"))

    # The round trip. A host that accepts TCP and then answers 500 to every
    # RPC call, or answers with a wifi sign-in page, is the failure this whole
    # command existed to catch and could not see.
    try:
        network_id = transport.get_network_id(url)
    except Exception as exc:
        network_id = None
        why = f"{type(exc).__name__}: {exc}"
    else:
        why = "the endpoint answered, but not with a server_state a rippled would send"

    if network_id is None:
        checks.append(("warn", "Ledger round-trip", f"failed — {why}"))
    else:
        known = {0: "Mainnet", 1: "Testnet", 2: "Devnet"}.get(network_id, "unknown network")
        status = "ok" if network_id in transport.TESTNET_NETWORK_IDS else "warn"
        checks.append((status, "Ledger round-trip", f"network_id {network_id} ({known})"))

    faucet = transport.get_faucet_url()
    if faucet:
        ok, fms, fwhy = _tcp_probe(faucet)
        checks.append((
            "ok" if ok else "warn",
            "Faucet reachable",
            f"{faucet} — {f'yes, {fms:.0f} ms' if ok else 'no — ' + fwhy}",
        ))
    return checks


def _collect_checks() -> list[tuple[str, str, str]]:
    """Collect diagnostic checks. Returns list of (status, label, detail)."""
    checks: list[tuple[str, str, str]] = []

    # 1. App version
    checks.append(("ok", "Version", _tool_version()))

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
    icons = {
        "ok": "[green]OK[/green]",
        "fail": "[red]FAIL[/red]",
        "warn": "[yellow]WARN[/yellow]",
        "info": "[dim]--[/dim]",
    }
    console.print()
    for status, label, detail in checks:
        icon = icons.get(status, "[dim]--[/dim]")
        console.print(f"  {icon}  [bold]{escape(label)}[/bold]  {escape(detail)}")
    console.print()


def _checks_to_text(checks: list[tuple[str, str, str]]) -> str:
    """Render checks as plain text for support bundles."""
    lines = []
    icons = {"ok": "OK", "fail": "FAIL", "warn": "WARN", "info": "--"}
    for status, label, detail in checks:
        icon = icons.get(status, "--")
        lines.append(f"  {icon}  {label}  {detail}")
    return "\n".join(lines)


def _diagnostics(*, offline: bool) -> list[tuple[str, str, str]]:
    """Local checks, plus the network ones unless they were declined."""
    checks = _collect_checks()
    if offline:
        checks.append(("info", "Network checks", "skipped (--offline)"))
        return checks
    try:
        return [*checks, *_collect_network_checks()]
    except Exception as exc:  # a diagnostic must never be the thing that breaks
        return [*checks, ("warn", "Network checks", f"could not run: {type(exc).__name__}")]


@app.command("self-check")
def self_check(
    offline: Annotated[
        bool, typer.Option("--offline", help="Skip the network probes"),
    ] = False,
) -> None:
    """Diagnose your environment and your connection to the ledger.

    Paste the output into a bug report. The network section is the half that
    answers "why is nothing happening": which endpoint you are actually
    talking to, whether it answers, and whether it is the Testnet.
    """
    checks = _diagnostics(offline=offline)
    _print_checks(checks)

    failed = [label for status, label, _ in checks if status == "fail"]
    if failed:
        raise _fail(CampError(
            code="SELF_CHECK_FAILED",
            message="These checks failed: " + ", ".join(failed) + ".",
            hint="Reinstall with 'pipx install --force xrpl-camp', then run self-check again.",
            exit_code=EXIT_USER,
        ))

    warned = [label for status, label, _ in checks if status == "warn"]
    if not warned:
        return

    console.print(
        "  [yellow]Network checks did not come back clean:[/yellow] "
        + escape(", ".join(warned)),
    )
    # A pinned endpoint that does not answer is the learner's own
    # configuration, and it is fixable in one command - so it earns a non-zero
    # exit. A flaky public Testnet is neither, and reinstalling will not help.
    if os.environ.get("XRPL_CAMP_RPC_URL", "").strip():
        raise _fail(CampError(
            code="SELF_CHECK_ENDPOINT",
            message="The endpoint you pinned with XRPL_CAMP_RPC_URL is not answering.",
            hint="Unset XRPL_CAMP_RPC_URL to use the public Testnet, then run this again.",
            exit_code=EXIT_USER,
        ))
    console.print(
        "  [dim]Nothing is wrong with your install. Check your connection, and "
        "if you are on conference or hotel wifi, open a browser and sign in "
        "first.[/dim]\n",
    )


@app.command("support-bundle")
def support_bundle(
    out: Annotated[
        str, typer.Option("--out", help="Where to write the zip (a file or a folder)"),
    ] = "",
    offline: Annotated[
        bool, typer.Option("--offline", help="Skip the network probes"),
    ] = False,
) -> None:
    """Write a diagnostic zip for bug reports. Attach it to your issue."""
    import datetime
    import json
    import zipfile

    from xrpl_camp import transport
    from xrpl_camp.errors import read_error_history

    checks = _diagnostics(offline=offline)
    _print_checks(checks)

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bundle_name = f"xrpl-camp-support-{ts}.zip"
    if not out:
        bundle_path = Path.cwd() / bundle_name
    elif Path(out).is_dir():
        bundle_path = Path(out) / bundle_name
    else:
        bundle_path = Path(out)

    history = _redact(read_error_history())

    # Say what is going in before it goes in. This file is destined for a
    # public issue tracker.
    console.print("  [bold]This bundle will contain:[/bold]")
    console.print("    self-check.txt      the diagnostics printed above")
    console.print("    session.json        your lesson progress (no seed)")
    console.print("    state-listing.txt   the names of files in .xrpl-camp/ (no contents)")
    console.print("    environment.json    tool version, OS, endpoint, XRPL_CAMP_* settings")
    if history:
        console.print("    errors.log          the last few errors this tool reported")
    console.print(
        "  [dim]No seed, no wallet file, and no user names or home paths.[/dim]\n",
    )

    # The endpoint and the XRPL_CAMP_* settings are the two things a maintainer
    # reading this on a GitHub issue most needs and could not previously get.
    # None of these variables hold key material.
    env_info = {
        "tool": "xrpl-camp",
        "version": _tool_version(),
        "platform": _redact(platform.platform()),
        "arch": platform.machine(),
        "python": _redact(sys.version),
        "cwd_writable": os.access(Path.cwd(), os.W_OK),
        "state_dir": str(STATE_DIR),
        "state_dir_present": STATE_DIR.exists(),
        "rpc_url": transport.get_rpc_url(),
        "network_label": transport.network_label_for_url(),
        "endpoint_pinned": bool(os.environ.get("XRPL_CAMP_RPC_URL", "").strip()),
        "camp_environment": _camp_environment(),
        "network_checks_run": not offline,
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

            # 5. Recent error history. Only when there is some - a bundle from
            # a machine that has never failed should not carry an empty file
            # implying it has.
            if history:
                zf.writestr("errors.log", history)
    except OSError as exc:
        raise _fail(write_error(str(bundle_path), f"{type(exc).__name__}: {exc}")) from None

    console.print(f"  [green]Bundle written:[/green] {escape(str(bundle_path))}")
    console.print("  [dim]Attach this file to your GitHub issue.[/dim]")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


#: POSIX convention for "terminated by SIGINT" (128 + 2).
EXIT_INTERRUPTED = 130


def run() -> None:
    """Console-script entry point.

    The ONE place a :class:`CampFailure` becomes user-facing output. Three
    modules raise them (corrupt state, seed-leak refusal, artifact write), and
    they reach here from anywhere in the call tree — including code paths a
    command never wrapped, which is exactly where the raw tracebacks were
    coming from. Catching the shared base once means a module added later is
    covered before it is written.

    Ctrl-C lands here too. It is the most common way a run ends in a room of
    thirty beginners, and it was the one exit path that said nothing at all —
    the learner walked away not knowing their progress was saved, or that
    `start` picks up exactly where they stopped. The recovery is genuinely
    good; nobody was told it existed.
    """
    try:
        app()
    except CampFailure as exc:
        console.print(format_error(exc.error))
        raise SystemExit(exc.exit_code) from None
    except KeyboardInterrupt:
        console.print()
        console.print(Panel(
            "[bold]Stopped.[/bold]\n\n"
            "Your progress is saved. Nothing was left half-written.\n\n"
            "Run [bold]xrpl-camp start[/bold] to pick up where you left off, or\n"
            "[bold]xrpl-camp status[/bold] to see where that is.",
            title="XRPL Camp — Paused",
            border_style="yellow",
        ))
        raise SystemExit(EXIT_INTERRUPTED) from None
