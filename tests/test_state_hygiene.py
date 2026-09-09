"""On-disk state: permissions, atomicity, and where the seed actually lives.

The permission tests are gated on POSIX because the code they cover is
(`os.name == "posix"`). They therefore cannot execute on a Windows developer
box — which is precisely why they are written with an explicit skip rather than
a silent `if`: a no-op assertion that always passes is worse than no test, and
CI runs on ubuntu-latest, where these are real.
"""

from __future__ import annotations

import json
import os
import stat

import pytest

from xrpl_camp import wallet
from xrpl_camp.models import Session, atomic_write_text, ensure_state_dir

posix_only = pytest.mark.skipif(
    os.name != "posix",
    reason="POSIX file modes; the code under test is gated on os.name == 'posix'",
)


def mode_of(path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


# ---------------------------------------------------------------------------
# Permissions (POSIX)
# ---------------------------------------------------------------------------


@posix_only
def test_the_seed_file_is_owner_only(tmp_path):
    """A seed is a private key. On a shared lab machine 0644 meant readable."""
    wallet.save_wallet("rOwner", "sEdTestSeedValue")

    path = tmp_path / ".xrpl-camp" / "wallet.json"
    assert path.exists()
    assert mode_of(path) == 0o600, oct(mode_of(path))
    assert mode_of(path) & 0o077 == 0, "group or other can read the seed"


@posix_only
def test_the_mailbox_seed_file_is_owner_only(tmp_path):
    """The mailbox seed is the learner's too; it gets the same protection."""
    wallet.save_mailbox("rBox", "sEdMailboxSeedValue")

    path = tmp_path / ".xrpl-camp" / "mailbox.json"
    assert mode_of(path) == 0o600, oct(mode_of(path))


@posix_only
def test_the_state_directory_is_owner_only(tmp_path):
    """0700 on the directory, so the file mode cannot be worked around."""
    wallet.save_wallet("rOwner", "sEdTestSeedValue")

    state = tmp_path / ".xrpl-camp"
    assert mode_of(state) == 0o700, oct(mode_of(state))


@posix_only
def test_a_pre_existing_loose_state_directory_is_tightened(tmp_path):
    """An upgrade from an older version must not leave 0755 behind."""
    state = tmp_path / ".xrpl-camp"
    state.mkdir(mode=0o755)
    assert mode_of(state) == 0o755

    ensure_state_dir(state)

    assert mode_of(state) == 0o700


@posix_only
def test_the_seed_is_never_world_readable_even_under_a_loose_umask(tmp_path):
    """`mkstemp` is 0600 already; the chmod must not widen it."""
    old = os.umask(0o000)
    try:
        wallet.save_wallet("rOwner", "sEdTestSeedValue")
    finally:
        os.umask(old)

    path = tmp_path / ".xrpl-camp" / "wallet.json"
    assert mode_of(path) & 0o077 == 0, oct(mode_of(path))


# ---------------------------------------------------------------------------
# The 0600 wiring, provable on every platform
#
# The four tests above are the real thing but only execute on POSIX. This one
# proves the same wiring anywhere, by standing in for `os` with a proxy that
# reports POSIX and records the chmod calls — so a Windows developer who
# deletes the chmod still gets a red build locally, not only in CI.
# ---------------------------------------------------------------------------


class _PosixishOS:
    """Proxy for the `os` module that claims POSIX and records chmod calls."""

    name = "posix"

    def __init__(self) -> None:
        self.chmods: list[tuple[str, int]] = []

    def chmod(self, path, mode, *a, **k):
        self.chmods.append((str(path), mode))

    def __getattr__(self, item):
        return getattr(os, item)


def test_the_seed_write_requests_owner_only_mode(tmp_path, monkeypatch):
    from xrpl_camp import models

    fake = _PosixishOS()
    monkeypatch.setattr(models, "os", fake)

    wallet.save_wallet("rOwner", "sEdTestSeedValue")

    modes = [mode for _, mode in fake.chmods]
    assert wallet.SEED_FILE_MODE == 0o600
    assert 0o600 in modes, f"no 0600 chmod was requested; saw {[oct(m) for m in modes]}"
    assert 0o700 in modes, "the state directory was not tightened to 0700"


def test_the_mode_is_applied_before_the_file_is_visible(tmp_path, monkeypatch):
    """Chmod the temp file, THEN rename.

    Doing it the other way round leaves a window in which the seed is on disk
    under its real name with the default mode.
    """
    from xrpl_camp import models

    order: list[str] = []
    fake = _PosixishOS()

    def record_chmod(path, mode, *a, **k):
        order.append(f"chmod:{oct(mode)}")

    real_replace = os.replace

    def record_replace(src, dst, *a, **k):
        order.append("replace")
        return real_replace(src, dst)

    fake.chmod = record_chmod
    monkeypatch.setattr(models, "os", fake)
    monkeypatch.setattr(os, "replace", record_replace)

    atomic_write_text(tmp_path / "state" / "seed.json", "{}", mode=0o600)

    assert "chmod:0o600" in order
    assert order.index("chmod:0o600") < order.index("replace")


# ---------------------------------------------------------------------------
# Atomicity (every platform)
# ---------------------------------------------------------------------------


def test_an_atomic_write_leaves_no_temp_file_behind(tmp_path):
    target = tmp_path / "state" / "thing.json"

    atomic_write_text(target, '{"ok": true}')

    assert [p.name for p in target.parent.iterdir()] == ["thing.json"]
    assert json.loads(target.read_text("utf-8")) == {"ok": True}


def test_a_failed_write_leaves_the_previous_file_intact(tmp_path, monkeypatch):
    """An interrupted save must not truncate a learner's progress to nothing."""
    target = tmp_path / "state" / "thing.json"
    atomic_write_text(target, '{"generation": 1}')

    def boom(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", boom)

    with pytest.raises(OSError):
        atomic_write_text(target, '{"generation": 2}')

    assert json.loads(target.read_text("utf-8")) == {"generation": 1}
    assert [p.name for p in target.parent.iterdir()] == ["thing.json"], (
        "the temp file was left behind after a failed write"
    )


def test_a_session_round_trips_through_disk(tmp_path):
    s = Session(started_at="2026-01-01T00:00:00Z", wallet_address="rCamp")
    s.mark_complete(4, "Send Payment", txid="ABC", duration_seconds=2.5)
    s.save()

    loaded = Session.load()

    assert loaded is not None
    assert loaded.wallet_address == "rCamp"
    assert loaded.txids["lesson_4"] == "ABC"
    assert loaded.get_progress(4).duration_seconds == 2.5


# ---------------------------------------------------------------------------
# Where state lives
# ---------------------------------------------------------------------------


def test_state_is_directory_local_by_default(tmp_path):
    """A sitting belongs to the folder you ran it in. That is the product model."""
    from xrpl_camp import models

    assert models.state_is_directory_local() is True
    wallet.save_wallet("rHere", "sEdHere")
    assert (tmp_path / ".xrpl-camp" / "wallet.json").exists()


def test_xrpl_camp_home_overrides_the_location(tmp_path, monkeypatch):
    """A learner who `cd`s mid-sitting can point at the original folder."""
    from xrpl_camp import models

    elsewhere = tmp_path / "elsewhere"
    monkeypatch.setenv("XRPL_CAMP_HOME", str(elsewhere))
    try:
        resolved = models.refresh_state_paths()
        assert resolved == elsewhere
        assert models.state_is_directory_local() is False

        Session(started_at="2026-01-01T00:00:00Z").save()
        assert (elsewhere / "session.json").exists()
        assert not (tmp_path / ".xrpl-camp").exists()
    finally:
        monkeypatch.delenv("XRPL_CAMP_HOME", raising=False)
        models.refresh_state_paths()


def test_get_state_dir_answers_where_did_my_seed_go(tmp_path):
    """Relative by default, so only the ABSOLUTE path is an honest answer."""
    from xrpl_camp import models

    resolved = models.get_state_dir()

    assert resolved.is_absolute()
    assert resolved == (tmp_path / ".xrpl-camp").resolve()
