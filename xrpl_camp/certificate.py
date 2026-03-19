"""Certificate generation for XRPL Camp completion."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from xrpl_camp.models import Session

CERTIFICATE_FILE = "xrpl_camp_certificate.json"


def generate_certificate(session: Session) -> dict:
    """Generate a certificate dict from session state. No seed included."""
    completed = []
    for p in session.progress:
        entry: dict[str, str | int] = {
            "lesson": p.lesson,
            "name": p.name,
            "at": p.completed_at,
        }
        if p.txid:
            entry["txid"] = p.txid
        completed.append(entry)

    total = session.total_duration()
    cert: dict = {
        "schema": "xrpl-camp-certificate-v1",
        "network": "testnet",
        "address": session.wallet_address,
        "completed": completed,
        "issued_at": datetime.now(UTC).isoformat(),
    }
    if total > 0:
        cert["duration_seconds"] = round(total, 1)
    return cert


def save_certificate(cert: dict, path: str = CERTIFICATE_FILE) -> Path:
    """Write certificate to disk. Returns file path."""
    filepath = Path(path)
    filepath.write_text(
        json.dumps(cert, indent=2), encoding="utf-8", newline="\n",
    )
    return filepath


def certificate_has_seed(cert: dict) -> bool:
    """Safety check: verify no seed leaked into certificate."""
    text = json.dumps(cert)
    # Seeds start with "sEd" (XRPL secp256k1 seeds)
    return "sEd" in text or "seed" in text.lower()
