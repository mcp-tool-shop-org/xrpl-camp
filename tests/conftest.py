"""Session-wide test hygiene.

There was no conftest.py in this repo, so four process globals leaked freely
between test modules:

* ``xrpl_camp.models._execution_mode`` — every ``--dry-run`` CLI invocation
  sets it and none restores it, so one behavioural CLI test used to be enough
  to put the whole rest of the session into DRY_RUN;
* ``xrpl_camp.wallet._dry_run_wallet`` / ``_dry_run_mailbox`` — in-memory seeds
  that survive into the next test;
* ``xrpl_camp.lessons._non_interactive`` — the ``--yes`` flag;
* ``xrpl_camp.errors._verbose`` — the ``--verbose`` flag.

The one guard that existed reset only AFTER its test, so it could never repair
state a different module had already leaked in. Everything here resets BEFORE
as well as after.

Two more invariants are enforced here because a convention nobody checks is not
an invariant:

* every test runs with the working directory inside its own ``tmp_path``, so no
  test can touch the developer's real ``./.xrpl-camp`` (``STATE_DIR`` is a
  RELATIVE path resolved against the cwd);
* no test may open a TCP connection unless it is marked ``network``. "The
  dry-run paths make no network calls" was previously unverified in either
  direction — the dry-run early returns sit immediately above code that
  constructs a client, so a refactor moving a guard one line down was
  undetectable.
"""

from __future__ import annotations

import socket

import pytest

from tests.helpers import strip_ansi as _strip_ansi

# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------
#
# pyproject.toml belongs to another domain in this wave, so the markers are
# registered here instead of in [tool.pytest.ini_options]. Registering them in
# code keeps `-W error::pytest.PytestUnknownMarkWarning` viable and means the
# marker travels with the tests that use it.


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "network: performs REAL calls against the XRPL Testnet. Deselected by "
        "default (see pytest_collection_modifyitems); run with "
        "`-m network --run-network`.",
    )


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-network",
        action="store_true",
        default=False,
        help="Run the tests marked `network` against the live XRPL Testnet.",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item],
) -> None:
    """Skip live-network tests unless explicitly asked for.

    CI must stay green with no network. The live tests exist because an
    end-to-end Testnet run found in one attempt what months of green CI did
    not — but they are opt-in, not a dependency of the default suite.
    """
    if config.getoption("--run-network"):
        return
    skip = pytest.mark.skip(
        reason="needs the live XRPL Testnet; pass --run-network to enable",
    )
    for item in items:
        if "network" in item.keywords:
            item.add_marker(skip)


# ---------------------------------------------------------------------------
# Process-global reset
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_process_globals():
    """Snapshot and restore every process global, before AND after each test."""
    from xrpl_camp import errors, lessons, wallet
    from xrpl_camp.models import ExecutionMode, set_execution_mode

    def to_clean_state() -> None:
        set_execution_mode(ExecutionMode.REAL)
        wallet.reset_dry_run_cache()
        lessons.set_non_interactive(False)
        errors.set_verbose(False)

    to_clean_state()
    try:
        yield
    finally:
        to_clean_state()


# ---------------------------------------------------------------------------
# Filesystem isolation
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolate_cwd(tmp_path, monkeypatch):
    """Run every test from its own tmp_path, with no XRPL_CAMP_HOME set.

    ``models.STATE_DIR`` is ``Path(".xrpl-camp")`` — relative, resolved against
    the working directory. Without this, any test that reaches real state code
    writes a seed into whatever directory pytest was launched from.
    """
    monkeypatch.delenv("XRPL_CAMP_HOME", raising=False)
    monkeypatch.delenv("XRPL_CAMP_RPC_URL", raising=False)
    monkeypatch.delenv("XRPL_CAMP_FAUCET_URL", raising=False)
    monkeypatch.delenv("XRPL_CAMP_ALLOW_ANY_NETWORK", raising=False)
    monkeypatch.delenv("XRPL_CAMP_ALLOW_ANY_ENDPOINT", raising=False)
    # Rich reads COLUMNS at render time, so pinning it here makes wrapped
    # output width-independent instead of terminal-dependent.
    monkeypatch.setenv("COLUMNS", "200")
    monkeypatch.setenv("LINES", "50")
    monkeypatch.chdir(tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# Network guard
# ---------------------------------------------------------------------------


class SocketBlockedError(RuntimeError):
    """A test tried to open a network connection."""


@pytest.fixture(autouse=True)
def no_network(request, monkeypatch):
    """Fail any unmarked test that opens a TCP connection.

    This is the machine-checked half of the ``--dry-run`` promise. The other
    half ("no disk writes") already had a real assertion; this one had none, so
    nothing in the suite would have failed if a dry-run path had opened a
    socket.
    """
    if "network" in request.keywords:
        yield
        return

    def blocked(*args, **kwargs):
        target = args[1] if len(args) > 1 else kwargs.get("address", "?")
        raise SocketBlockedError(
            f"Network access is blocked in this test (tried to connect to "
            f"{target!r}). If the test genuinely needs the live XRPL Testnet, "
            f"mark it with @pytest.mark.network.",
        )

    monkeypatch.setattr(socket.socket, "connect", blocked, raising=False)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked, raising=False)
    monkeypatch.setattr(socket, "create_connection", blocked, raising=False)
    yield


# ---------------------------------------------------------------------------
# Convenience fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def strip_ansi():
    """The hardened ANSI stripper, as a fixture."""
    return _strip_ansi


@pytest.fixture()
def dry_run_mode():
    """Put the process in DRY_RUN for the duration of the test."""
    from xrpl_camp.models import ExecutionMode, set_execution_mode

    set_execution_mode(ExecutionMode.DRY_RUN)
    yield
    set_execution_mode(ExecutionMode.REAL)
