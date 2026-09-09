"""Behavioural coverage for the CLI — invocations, not help text.

The full invocation inventory of the previous suite was: reset, status,
`status --detail`, `proof verify`, and `--help` for four commands. Four
commands were never invoked in any form, not even `--help`: `wallet`,
`certificate`, `self-check`, `support-bundle`. `self-check` is what CI's canary
runs, so the repo's only end-to-end health probe was itself unprotected; and
`support-bundle` writes a file destined for a public issue tracker with no test
asserting what goes into it.

Two things are checked through a real subprocess rather than `CliRunner`:

* the packaged-artefact path (`python -m xrpl_camp`), which is what the
  PyInstaller binaries shipped to npm users run, and which nothing exercised;
* the `CampFailure` handler, which lives in `cli.run()` — `CliRunner` invokes
  `app` directly and never reaches it.
"""

from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.helpers import load_fixture, make_response, squash, stub_client
from xrpl_camp import transport
from xrpl_camp.cli import app
from xrpl_camp.models import Session

runner = CliRunner()

TXID = "1E721764B35CAFD9AB24CFA15D8DC5097E9B9CDFE967B3E2A99FC701A3E53E1D"
ARTIFACTS = ("xrpl_camp_certificate.json", "xrpl_camp_proof_pack.json")


def out(result) -> str:
    return squash(result.output)


def _run_module(*args: str, cwd: Path, stdin_closed: bool = True):
    """Run `python -m xrpl_camp` for real, with stdin at EOF by default."""
    return subprocess.run(
        [sys.executable, "-m", "xrpl_camp", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdin=subprocess.DEVNULL if stdin_closed else None,
        timeout=120,
        check=False,
    )


# ---------------------------------------------------------------------------
# --dry-run, behaviourally
#
# The tests these replace asserted that `--dry-run` appeared in `--help`
# output. They proved typer declared an option and nothing about what it does.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "argv",
    [
        ["start", "--dry-run"],
        ["wallet", "create", "--dry-run"],
        ["fund", "--dry-run"],
        ["send", "--memo", "hello", "--dry-run"],
        ["verify", "--tx", TXID, "--dry-run"],
        ["certificate", "--dry-run"],
    ],
)
def test_dry_run_commands_write_nothing_to_disk(argv, tmp_path):
    """The advertised contract: "no network calls, no disk writes".

    `no_network` (conftest) enforces the first half by failing the test if a
    socket opens. This assertion enforces the second half at the level the
    learner actually types.
    """
    result = runner.invoke(app, argv)

    assert result.exit_code in (0, 1), out(result)
    assert list(tmp_path.iterdir()) == [], f"{argv} wrote to disk under --dry-run"


def test_start_dry_run_completes_with_stdin_closed(tmp_path):
    """CI's canary depends on this, and every `xrpl-camp start | tee log`.

    `_pause()` used to call `console.input()` unconditionally, so with stdin at
    EOF the guided flow raised EOFError before lesson 1 rendered. The canary
    could not see it: the CI step was `... || true`, inside a job gated on
    `workflow_dispatch`.
    """
    result = runner.invoke(app, ["start", "--dry-run"])

    assert result.exit_code == 0, out(result)
    assert result.exception is None
    assert "Dry Run Complete" in out(result)
    assert list(tmp_path.iterdir()) == []


def test_global_dry_run_flag_also_simulates(tmp_path):
    """`xrpl-camp --dry-run start`, not only `xrpl-camp start --dry-run`."""
    result = runner.invoke(app, ["--dry-run", "start"])

    assert result.exit_code == 0, out(result)
    assert list(tmp_path.iterdir()) == []


def test_start_dry_run_leaves_no_trace_via_the_module_entry_point(tmp_path):
    """The packaged path, in a real process with stdin at EOF.

    This is the shape of the PyInstaller binaries shipped to npm users, and
    nothing exercised `python -m xrpl_camp` at all.
    """
    proc = _run_module("start", "--dry-run", cwd=tmp_path)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "Traceback" not in proc.stderr
    assert "EOFError" not in proc.stderr
    assert list(tmp_path.iterdir()) == []


def test_help_still_documents_the_flag():
    """One help-text assertion is kept deliberately, to guard the wording."""
    result = runner.invoke(app, ["start", "--help"])

    assert result.exit_code == 0
    assert "--dry-run" in out(result)
    assert "simulation" in out(result).lower()


# ---------------------------------------------------------------------------
# --version
# ---------------------------------------------------------------------------


def test_version_flag_prints_the_installed_version_and_exits():
    import xrpl_camp

    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert xrpl_camp.__version__ in out(result)


def test_version_flag_works_through_the_module_entry_point(tmp_path):
    import xrpl_camp

    proc = _run_module("--version", cwd=tmp_path)

    assert proc.returncode == 0
    assert xrpl_camp.__version__ in proc.stdout


def test_the_installed_console_script_starts(tmp_path):
    """`[project.scripts] xrpl-camp = "xrpl_camp.cli:run"` — never exercised.

    A broken entry point is invisible to every in-process test: `CliRunner`
    imports `app` directly, so the declared console script could fail to resolve
    and the suite would stay green. This is the artefact `pipx install
    xrpl-camp` actually puts on a learner's PATH.
    """
    import shutil

    import xrpl_camp

    script = shutil.which("xrpl-camp", path=str(Path(sys.executable).parent))
    if script is None:
        pytest.skip("console script not installed in this environment")

    proc = subprocess.run(
        [script, "--version"],
        cwd=str(tmp_path), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        stdin=subprocess.DEVNULL, timeout=120, check=False,
    )

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert xrpl_camp.__version__ in proc.stdout
    assert "Traceback" not in proc.stderr


# ---------------------------------------------------------------------------
# wallet — never invoked before, not even --help
# ---------------------------------------------------------------------------


def test_wallet_create_writes_a_wallet_and_never_prints_the_seed(tmp_path):
    result = runner.invoke(app, ["wallet", "create"])

    assert result.exit_code == 0, out(result)
    record = json.loads((tmp_path / ".xrpl-camp" / "wallet.json").read_text("utf-8"))
    assert record["address"] in out(result)
    assert record["seed"] not in result.output, "the seed reached stdout"


def test_wallet_create_is_idempotent(tmp_path):
    assert runner.invoke(app, ["wallet", "create"]).exit_code == 0
    first = (tmp_path / ".xrpl-camp" / "wallet.json").read_bytes()

    result = runner.invoke(app, ["wallet", "create"])

    assert result.exit_code == 0
    assert "already exists" in out(result)
    assert (tmp_path / ".xrpl-camp" / "wallet.json").read_bytes() == first


def test_wallet_show_displays_the_address_and_withholds_the_seed(tmp_path):
    runner.invoke(app, ["wallet", "create"])
    record = json.loads((tmp_path / ".xrpl-camp" / "wallet.json").read_text("utf-8"))

    result = runner.invoke(app, ["wallet", "show"])

    assert result.exit_code == 0
    assert record["address"] in out(result)
    assert record["seed"] not in result.output
    assert "Not shown here" in out(result)


def test_wallet_show_without_a_wallet_is_a_user_error():
    result = runner.invoke(app, ["wallet", "show"])

    assert result.exit_code == 1
    assert "Traceback" not in result.output


def test_wallet_rejects_an_unknown_action():
    result = runner.invoke(app, ["wallet", "destroy"])

    assert result.exit_code == 1
    assert "BAD_ACTION" in result.output
    assert "wallet create" in out(result)


# ---------------------------------------------------------------------------
# certificate — never invoked before
# ---------------------------------------------------------------------------


def test_certificate_refuses_with_no_progress(tmp_path):
    result = runner.invoke(app, ["certificate"])

    assert result.exit_code == 1
    assert "NO_PROGRESS" in result.output
    assert list(tmp_path.iterdir()) == [], "a refusal still created state"


def test_certificate_refuses_to_seal_incomplete_work(tmp_path):
    """The integrity claim, at the command boundary."""
    s = Session(started_at="2026-01-01T00:00:00Z", wallet_address="rCamp")
    s.mark_complete(1, "Mental Model")
    s.mark_complete(2, "Create Wallet")
    s.save()

    result = runner.invoke(app, ["certificate"])

    assert result.exit_code != 0
    for name in ARTIFACTS:
        assert not (tmp_path / name).exists()


def test_certificate_writes_both_artifacts_when_the_work_is_done(tmp_path):
    s = Session(started_at="2026-01-01T00:00:00Z", wallet_address="rCamp")
    for n in range(1, 6):
        s.mark_complete(n, f"Lesson {n}", duration_seconds=1.0)
    s.txids["lesson_4"] = TXID
    s.save()

    result = runner.invoke(app, ["certificate"])

    assert result.exit_code == 0, out(result)
    for name in ARTIFACTS:
        assert (tmp_path / name).exists()
    pack = json.loads((tmp_path / "xrpl_camp_proof_pack.json").read_text("utf-8"))
    assert pack["sha256"].startswith("sha256:")
    assert len(pack["sha256"].removeprefix("sha256:")) == 64

    verify = runner.invoke(
        app, ["proof", "verify", str(tmp_path / "xrpl_camp_proof_pack.json")],
    )
    assert verify.exit_code == 0
    assert "PASS" in verify.output


# ---------------------------------------------------------------------------
# self-check — what CI's canary runs
# ---------------------------------------------------------------------------


SELF_CHECK_LABELS = (
    "Version", "Platform", "Console encoding", "Rich rendering",
    "Filesystem write", "State directory", "xrpl", "typer", "rich",
)


def test_self_check_reports_every_declared_check():
    result = runner.invoke(app, ["self-check"])

    assert result.exit_code == 0, out(result)
    body = out(result)
    for label in SELF_CHECK_LABELS:
        assert label in body, f"self-check omitted {label!r}"


def test_self_check_exits_non_zero_when_a_check_fails(monkeypatch):
    """A diagnostic that always exits 0 is not a diagnostic."""
    from xrpl_camp import cli

    real = cli._collect_checks
    monkeypatch.setattr(
        cli, "_collect_checks",
        lambda: [*real(), ("fail", "Filesystem write", "Read-only file system")],
    )

    result = runner.invoke(app, ["self-check"])

    assert result.exit_code != 0
    assert "SELF_CHECK_FAILED" in result.output
    assert "Filesystem write" in out(result)


def test_self_check_runs_through_the_module_entry_point(tmp_path):
    proc = _run_module("self-check", cwd=tmp_path)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "Traceback" not in proc.stderr


# ---------------------------------------------------------------------------
# support-bundle — a file destined for a public issue tracker
# ---------------------------------------------------------------------------


def test_support_bundle_contains_no_seed_material(tmp_path):
    """The security-relevant one: this zip goes to a public issue tracker."""
    runner.invoke(app, ["wallet", "create"])
    record = json.loads((tmp_path / ".xrpl-camp" / "wallet.json").read_text("utf-8"))
    s = Session(started_at="2026-01-01T00:00:00Z", wallet_address=record["address"])
    s.mark_complete(1, "Mental Model")
    s.save()

    result = runner.invoke(app, ["support-bundle", "--out", str(tmp_path)])
    assert result.exit_code == 0, out(result)

    bundles = list(tmp_path.glob("xrpl-camp-support-*.zip"))
    assert len(bundles) == 1

    with zipfile.ZipFile(bundles[0]) as zf:
        names = set(zf.namelist())
        blob = b"".join(zf.read(n) for n in sorted(names))

    assert names == {
        "self-check.txt", "session.json", "state-listing.txt", "environment.json",
    }
    assert record["seed"].encode() not in blob, "the seed is inside the support bundle"
    assert b"wallet.json" in blob, "the state listing should name the file"
    # The listing carries names, never contents.
    assert zipfile.ZipFile(bundles[0]).read("state-listing.txt").decode().split() == [
        "session.json", "wallet.json",
    ]


def test_support_bundle_redacts_the_home_directory(tmp_path):
    result = runner.invoke(app, ["support-bundle", "--out", str(tmp_path)])
    assert result.exit_code == 0

    bundle = next(tmp_path.glob("xrpl-camp-support-*.zip"))
    with zipfile.ZipFile(bundle) as zf:
        env = json.loads(zf.read("environment.json"))
        text = zf.read("self-check.txt").decode()

    home = str(Path.home())
    assert home not in json.dumps(env)
    assert home not in text


def test_support_bundle_defaults_to_the_working_directory(tmp_path):
    result = runner.invoke(app, ["support-bundle"])

    assert result.exit_code == 0
    assert len(list(tmp_path.glob("xrpl-camp-support-*.zip"))) == 1


# ---------------------------------------------------------------------------
# fund / send / verify, behaviourally
# ---------------------------------------------------------------------------


def test_send_records_the_transaction_in_the_session(tmp_path, monkeypatch):
    runner.invoke(app, ["wallet", "create"])
    monkeypatch.setattr(transport, "get_balance", lambda *a, **k: 100_000_000)
    monkeypatch.setattr(
        transport, "send_memo_payment",
        lambda seed, memo, dest, url=None, **k: transport.SendResult(
            txid=TXID, destination=dest, amount_drops=1,
            fee_drops=10, created_account=False,
        ),
    )

    result = runner.invoke(app, ["send", "--memo", "hello ledger"])

    assert result.exit_code == 0, out(result)
    assert Session.load().txids["lesson_4"] == TXID
    mailbox = json.loads((tmp_path / ".xrpl-camp" / "mailbox.json").read_text("utf-8"))
    assert mailbox["address"] != json.loads(
        (tmp_path / ".xrpl-camp" / "wallet.json").read_text("utf-8"),
    )["address"], "the payment destination is the sender again"


def test_verify_refuses_a_transaction_that_is_not_on_the_ledger(monkeypatch):
    """`verify --tx <64 hex chars>` used to print "Independently verified"."""
    stub_client(
        monkeypatch,
        make_response(load_fixture("tx_not_found_v2.json"), successful=False),
    )

    result = runner.invoke(app, ["verify", "--tx", "A" * 64])

    assert result.exit_code != 0
    assert "Independently verified" not in out(result)


def test_verify_shows_the_parsed_fields_for_a_real_transaction(monkeypatch):
    """The table renders from the real parser even when the tx is not ours.

    Reading someone else's transaction is the whole point of a public ledger,
    so the details still print and the explorer link still works. What it is
    NOT is lesson 5: crediting it would let anyone finish the lesson with a
    hash copied off the explorer, which is exactly what this used to do.
    """
    stub_client(monkeypatch, make_response(load_fixture("tx_v2_payment.json")))

    result = runner.invoke(app, ["verify", "--tx", TXID])

    body = out(result)
    assert "r3B7h4qQERrzogwxrCqFMJBewNBzutXVn1" in body
    assert "rUUGAx14J9EwWbWLjQgVFfXA2zV5hfKqDP" in body
    assert result.exit_code != 0, "a stranger's transaction must not pass lesson 5"
    assert "VERIFY_NO_ACCOUNT" in body
    assert "Independently verified" not in body


def test_fund_without_a_wallet_is_a_clean_failure():
    result = runner.invoke(app, ["fund"])

    assert result.exit_code != 0
    assert "Traceback" not in result.output


# ---------------------------------------------------------------------------
# Corrupt state reaches the user as a code and a hint, never a stack
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "argv",
    [["status"], ["status", "--detail"], ["wallet", "show"], ["fund"],
     ["send", "--memo", "x"], ["certificate"], ["start"]],
)
def test_a_corrupt_state_file_never_produces_a_traceback(argv, tmp_path):
    """13 corrupt-state paths, one handler. Exercised through a real process.

    `CliRunner` invokes `app` directly and never reaches `cli.run()`, where the
    single `CampFailure` handler lives — so this has to be a subprocess to mean
    anything.
    """
    state = tmp_path / ".xrpl-camp"
    state.mkdir()
    (state / "session.json").write_text("{ not json", encoding="utf-8")
    (state / "wallet.json").write_text("[]", encoding="utf-8")

    proc = _run_module(*argv, cwd=tmp_path)

    combined = proc.stdout + proc.stderr
    assert proc.returncode != 0, combined
    assert "Traceback" not in combined
    assert "CORRUPT" in combined
    assert "reset" in combined.lower()


def test_status_with_no_state_is_not_an_error(tmp_path):
    proc = _run_module("status", cwd=tmp_path)

    assert proc.returncode == 0
    assert "No training started" in proc.stdout


# ---------------------------------------------------------------------------
# Legacy console encoding
# ---------------------------------------------------------------------------


def test_the_cli_survives_a_cp1252_stdout(tmp_path):
    """Windows binaries ship to npm users; a legacy code page is cp1252.

    Every lesson prints U+2713 / U+2717 / U+25B8 and em dashes, which cp1252
    cannot encode. `CliRunner` captures to a UTF-8 buffer, so no in-process test
    can see this — it has to be a subprocess with PYTHONIOENCODING set.
    """
    import os

    env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
    proc = subprocess.run(
        [sys.executable, "-m", "xrpl_camp", "start", "--dry-run"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        encoding="cp1252",
        errors="replace",
        stdin=subprocess.DEVNULL,
        env=env,
        timeout=120,
        check=False,
    )

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "UnicodeEncodeError" not in proc.stderr
    assert "Traceback" not in proc.stderr
    assert list(tmp_path.iterdir()) == []
