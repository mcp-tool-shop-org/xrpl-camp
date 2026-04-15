"""Wallet creation, storage, and display."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from xrpl_camp.models import STATE_DIR, WALLET_FILE, is_dry_run

_dry_run_wallet: dict[str, str] | None = None


def create_wallet() -> tuple[str, str]:
    """Generate a new XRPL Testnet wallet. Returns (address, seed)."""
    from xrpl.wallet import Wallet

    wallet = Wallet.create()
    return wallet.address, wallet.seed


def save_wallet(address: str, seed: str) -> Path:
    """Save wallet credentials to disk. In dry-run, caches in memory only."""
    global _dry_run_wallet
    data = {
        "address": address,
        "seed": seed,
        "network": "testnet",
        "created_at": datetime.now(UTC).isoformat(),
    }
    if is_dry_run():
        _dry_run_wallet = data
        return WALLET_FILE
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    WALLET_FILE.write_text(
        json.dumps(data, indent=2), encoding="utf-8", newline="\n",
    )
    return WALLET_FILE


def load_wallet() -> dict[str, str] | None:
    """Load wallet. Returns in-memory cache in dry-run, else reads disk."""
    if is_dry_run() and _dry_run_wallet is not None:
        return _dry_run_wallet
    if not WALLET_FILE.exists():
        return None
    return json.loads(WALLET_FILE.read_text(encoding="utf-8"))


def wallet_exists() -> bool:
    """Check if a wallet exists (on disk or in dry-run cache)."""
    if is_dry_run() and _dry_run_wallet is not None:
        return True
    return WALLET_FILE.exists()
