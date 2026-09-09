"""Wallet creation, storage, and display.

Two wallets live here:

* the **main wallet** — the learner's account, funded by the Testnet faucet;
* the **mailbox** — a second account the learner also owns, so lesson 4 can
  send a *real* payment to a *real* destination. The old lesson tried to pay
  its own address, which xrpl-py refuses to even construct and which the
  ledger rejects as `temREDUNDANT`.

The mailbox seed is the learner's and is saved alongside the main wallet.
Nothing is thrown away: they hold the keys to both ends of the payment.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from xrpl_camp.errors import CampError
from xrpl_camp.models import (
    MAILBOX_FILE,
    STATE_DIR,
    WALLET_FILE,
    StateFileError,
    atomic_write_text,
    is_dry_run,
)

# Owner-only. The seed is a private key; on a shared lab machine the default
# 0644 meant any other local account could read it.
SEED_FILE_MODE = 0o600

_dry_run_wallet: dict[str, str] | None = None
_dry_run_mailbox: dict[str, str] | None = None


def reset_dry_run_cache() -> None:
    """Clear the in-memory dry-run wallet and mailbox.

    Exposed so tests (and any future mode switch) can reset this without
    poking private module names.
    """
    global _dry_run_wallet, _dry_run_mailbox
    _dry_run_wallet = None
    _dry_run_mailbox = None


def _network_label() -> str:
    """Best-effort label for the endpoint in use, with no network call.

    The old code stamped a literal ``"testnet"`` into wallet.json regardless of
    which endpoint ``XRPL_CAMP_RPC_URL`` pointed at, so a wallet created
    against some other network was indistinguishable from a Testnet one — the
    exact confusion SECURITY.md's "never use a Testnet seed on Mainnet"
    warning depends on the user not making.
    """
    try:
        from xrpl_camp.transport import get_rpc_url, network_label_for_url

        return network_label_for_url(get_rpc_url())
    except Exception:  # pragma: no cover - labelling must never break a save
        return "unknown"


def _corrupt_wallet_error(path: Path, detail: str) -> StateFileError:
    return StateFileError(CampError(
        code="WALLET_CORRUPT",
        message=f"Could not read {path}: {detail}",
        hint=(
            "The wallet file is unreadable or malformed. Run `xrpl-camp reset` "
            "to start fresh (this discards the local seed and progress)."
        ),
        retryable=False,
    ))


def _read_json_record(path: Path, required: tuple[str, ...]) -> dict[str, str]:
    """Read a wallet-shaped JSON record, or raise a structured error."""
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise _corrupt_wallet_error(path, str(e)) from e
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise _corrupt_wallet_error(path, f"invalid JSON ({e.msg})") from e
    if not isinstance(data, dict):
        raise _corrupt_wallet_error(
            path, f"expected a JSON object, found {type(data).__name__}",
        )
    missing = [k for k in required if not data.get(k)]
    if missing:
        raise _corrupt_wallet_error(
            path, f"missing required field(s): {', '.join(missing)}",
        )
    return data


def _save_record(path: Path, data: dict[str, str]) -> Path:
    """Atomically write a wallet-shaped record with owner-only permissions."""
    return atomic_write_text(
        path, json.dumps(data, indent=2), mode=SEED_FILE_MODE,
    )


# ---------------------------------------------------------------------------
# Main wallet
# ---------------------------------------------------------------------------


def create_wallet() -> tuple[str, str]:
    """Generate a new XRPL Testnet wallet. Returns (address, seed)."""
    from xrpl.wallet import Wallet

    wallet = Wallet.create()
    return wallet.address, wallet.seed


def save_wallet(
    address: str, seed: str, *, network: str | None = None,
) -> Path | None:
    """Save wallet credentials to disk. In dry-run, caches in memory only.

    Returns the path actually written, or **None** in dry-run — where nothing
    was written, so returning the real wallet path would be a claim about the
    filesystem that is not true.
    """
    global _dry_run_wallet
    data = {
        "address": address,
        "seed": seed,
        "network": network or _network_label(),
        "created_at": datetime.now(UTC).isoformat(),
    }
    if is_dry_run():
        _dry_run_wallet = data
        return None
    return _save_record(WALLET_FILE, data)


def load_wallet() -> dict[str, str] | None:
    """Load wallet. Returns in-memory cache in dry-run, else reads disk.

    Raises :class:`~xrpl_camp.models.StateFileError` (structured, no traceback)
    when the file exists but is unreadable, malformed, or missing the
    `address` / `seed` fields every caller indexes directly.
    """
    if is_dry_run() and _dry_run_wallet is not None:
        return _dry_run_wallet
    if not WALLET_FILE.exists():
        return None
    return _read_json_record(WALLET_FILE, ("address", "seed"))


def wallet_exists() -> bool:
    """Check if a wallet exists (on disk or in dry-run cache)."""
    if is_dry_run() and _dry_run_wallet is not None:
        return True
    return WALLET_FILE.exists()


# ---------------------------------------------------------------------------
# Mailbox — the lesson-4 destination the learner also owns
# ---------------------------------------------------------------------------


def create_mailbox() -> tuple[str, str]:
    """Generate the learner's second ("mailbox") wallet. Returns (address, seed)."""
    return create_wallet()


def save_mailbox(
    address: str, seed: str, *, network: str | None = None,
) -> Path | None:
    """Save the mailbox credentials. Same dry-run semantics as `save_wallet`."""
    global _dry_run_mailbox
    data = {
        "address": address,
        "seed": seed,
        "network": network or _network_label(),
        "role": "mailbox",
        "created_at": datetime.now(UTC).isoformat(),
    }
    if is_dry_run():
        _dry_run_mailbox = data
        return None
    return _save_record(MAILBOX_FILE, data)


def load_mailbox() -> dict[str, str] | None:
    """Load the mailbox record, or None if the learner has no mailbox yet."""
    if is_dry_run() and _dry_run_mailbox is not None:
        return _dry_run_mailbox
    if not MAILBOX_FILE.exists():
        return None
    return _read_json_record(MAILBOX_FILE, ("address", "seed"))


def mailbox_exists() -> bool:
    """Check if a mailbox exists (on disk or in dry-run cache)."""
    if is_dry_run() and _dry_run_mailbox is not None:
        return True
    return MAILBOX_FILE.exists()


def get_or_create_mailbox() -> tuple[str, str]:
    """Return the learner's mailbox (address, seed), creating it if needed.

    Convenience for lesson 4 so the flow is one call instead of four.
    """
    existing = load_mailbox()
    if existing:
        return existing["address"], existing["seed"]
    address, seed = create_mailbox()
    save_mailbox(address, seed)
    return address, seed


__all__ = [
    "MAILBOX_FILE",
    "SEED_FILE_MODE",
    "STATE_DIR",
    "WALLET_FILE",
    "create_mailbox",
    "create_wallet",
    "get_or_create_mailbox",
    "load_mailbox",
    "load_wallet",
    "mailbox_exists",
    "reset_dry_run_cache",
    "save_mailbox",
    "save_wallet",
    "wallet_exists",
]
