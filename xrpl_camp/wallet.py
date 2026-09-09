"""Wallet creation, storage, and display.

Two wallets live here:

* the **main wallet** — the learner's account, funded by the Testnet faucet;
* the **mailbox** — a second account the learner also owns, so lesson 4 can
  send a *real* payment to a *real* destination. The old lesson tried to pay
  its own address, which xrpl-py refuses to even CONSTRUCT
  (`XRPLModelException`: "An XRP payment transaction cannot have the same
  sender and destination"). Nothing was signed and nothing was submitted, so
  the ledger never saw it — measured, the protocol's `temREDUNDANT` is
  unreachable through xrpl-py's model layer and must not be described as what
  happens when you pay yourself.

The mailbox seed is the learner's and is saved alongside the main wallet.
Nothing is thrown away: they hold the keys to both ends of the payment.

Spending FROM the mailbox
-------------------------
The mailbox is funded with EXACTLY the base reserve, so its SPENDABLE balance
is zero — measured, 1,000,000 drops held and 0 drops spendable. Anything that
spends from it, or gives it an owned object, must call
`transport.get_spendable_drops` first and top it up: a TrustSet from that
account returned `tesSUCCESS` and left it at MINUS 200,010 drops spendable.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from xrpl_camp.errors import EXIT_USER, CampError
from xrpl_camp.models import (
    MAILBOX_FILE,
    STATE_DIR,
    WALLET_FILE,
    StateFileError,
    atomic_write_text,
    is_dry_run,
)

# These three are bound BY VALUE at import, which is why `models.
# refresh_state_paths()` writes through to this module (see
# `models._PATH_MIRRORS`). Without that write-through, re-pointing
# XRPL_CAMP_HOME moved session.json and left wallet.json behind, splitting a
# learner's state across two directories — and `xrpl-camp reset` then deleted
# one half. Keep them module-level: callers and tests override them here.

# Owner-only. The seed is a private key; on a shared lab machine the default
# 0644 meant any other local account could read it.
SEED_FILE_MODE = 0o600

#: Key type every seed this product issues. Pinned rather than inherited:
#: `Wallet.create()`'s default is a dependency decision, and if it ever moves
#: a newer install would silently start writing `ss`-prefixed secp256k1 seeds
#: into wallet.json — a different shape for the one secret this tool stores,
#: and the shape certificate.py's `sEd` prefix heuristic is written around.
WALLET_ALGORITHM = "ed25519"

#: Schema version stamped into wallet.json and mailbox.json, so a future
#: format change is detectable rather than inferred from a seed prefix.
WALLET_SCHEMA_VERSION = 1

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


def _occupied_by_error(path: Path, existing: str, incoming: str) -> StateFileError:
    return StateFileError(CampError(
        code="WALLET_OCCUPIED",
        message=(
            f"{path} already holds wallet {existing}, and this would replace "
            f"it with {incoming}. Nothing was written."
        ),
        hint=(
            "Overwriting it destroys the seed for the first wallet — and any "
            "test XRP it holds — with no way to recover it. Run "
            "`xrpl-camp reset` if you really want a fresh wallet, or close "
            "the other xrpl-camp run that is using this folder."
        ),
        retryable=False,
        exit_code=EXIT_USER,
    ))


def _refuse_clobber(path: Path, address: str, *, force: bool) -> None:
    """Refuse to replace a stored wallet with a DIFFERENT one.

    Two runs in one folder used to overwrite each other silently: the loser's
    seed was destroyed, and if the faucet had already funded it (the guided
    flow funds in lesson 3, before lesson 4 saves) that XRP was unrecoverable.
    A same-address rewrite is a harmless refresh and is allowed.
    """
    if force or not path.exists():
        return
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return  # a broken file is the corrupt-read path's problem, not ours
    if not isinstance(raw, dict):
        return
    existing = str(raw.get("address", "") or "")
    if existing and existing != address:
        raise _occupied_by_error(path, existing, address)


def _save_record(path: Path, data: dict[str, str]) -> Path:
    """Atomically write a wallet-shaped record with owner-only permissions."""
    return atomic_write_text(
        path, json.dumps(data, indent=2), mode=SEED_FILE_MODE,
    )


# ---------------------------------------------------------------------------
# Main wallet
# ---------------------------------------------------------------------------


def create_wallet() -> tuple[str, str]:
    """Generate a new XRPL Testnet wallet. Returns (address, seed).

    The algorithm is passed explicitly. ``Wallet.create()``'s default is
    ed25519 *today*, but that is xrpl-py's decision, not this product's, and
    the key type of every seed we have ever issued should not move because a
    dependency changed its mind.
    """
    from xrpl.constants import CryptoAlgorithm
    from xrpl.wallet import Wallet

    wallet = Wallet.create(algorithm=CryptoAlgorithm.ED25519)
    return wallet.address, wallet.seed


def save_wallet(
    address: str, seed: str, *, network: str | None = None, force: bool = False,
) -> Path | None:
    """Save wallet credentials to disk. In dry-run, caches in memory only.

    Returns the path actually written, or **None** in dry-run — where nothing
    was written, so returning the real wallet path would be a claim about the
    filesystem that is not true.

    Refuses to replace a stored wallet with a different address unless
    ``force=True``; see :func:`_refuse_clobber`.
    """
    global _dry_run_wallet
    data = {
        "schema_version": WALLET_SCHEMA_VERSION,
        "address": address,
        "seed": seed,
        "algorithm": WALLET_ALGORITHM,
        "network": network or _network_label(),
        "created_at": datetime.now(UTC).isoformat(),
    }
    if is_dry_run():
        _dry_run_wallet = data
        return None
    _refuse_clobber(WALLET_FILE, address, force=force)
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
    address: str, seed: str, *, network: str | None = None, force: bool = False,
) -> Path | None:
    """Save the mailbox credentials. Same dry-run semantics as `save_wallet`."""
    global _dry_run_mailbox
    data = {
        "schema_version": WALLET_SCHEMA_VERSION,
        "address": address,
        "seed": seed,
        "algorithm": WALLET_ALGORITHM,
        "network": network or _network_label(),
        "role": "mailbox",
        "created_at": datetime.now(UTC).isoformat(),
    }
    if is_dry_run():
        _dry_run_mailbox = data
        return None
    _refuse_clobber(MAILBOX_FILE, address, force=force)
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
    "WALLET_ALGORITHM",
    "WALLET_FILE",
    "WALLET_SCHEMA_VERSION",
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
