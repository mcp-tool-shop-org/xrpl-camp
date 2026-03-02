"""Proof Pack — tamper-evident completion record for XRPL Camp."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from xrpl_camp import __version__
from xrpl_camp.models import Session
from xrpl_camp.transport import EXPLORER_URL

PROOF_PACK_FILE = "xrpl_camp_proof_pack.json"


def canonical_json(data: dict) -> str:
    """Canonical JSON: sorted keys, 2-space indent, LF line endings, trailing newline.

    Identical output on every platform. Used for hash computation.
    """
    return (
        json.dumps(
            data,
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
            separators=(",", ": "),
        ).replace("\r\n", "\n")
        + "\n"
    )


def generate_proof_pack(session: Session) -> dict:
    """Build a proof pack dict with SHA-256 integrity hash.

    The hash is computed over the canonical JSON of all fields
    except the hash itself. Anyone can verify by stripping the
    sha256 field and recomputing.
    """
    lessons = []
    for p in session.progress:
        entry: dict[str, str | int] = {
            "lesson": p.lesson,
            "name": p.name,
            "completed_at": p.completed_at,
        }
        if p.txid:
            entry["txid"] = p.txid
            entry["explorer_url"] = f"{EXPLORER_URL}{p.txid}"
        lessons.append(entry)

    content: dict = {
        "schema": "xrpl-camp-proof-pack-v1",
        "address": session.wallet_address,
        "network": "testnet",
        "tool_version": __version__,
        "issued_at": datetime.now(UTC).isoformat(),
        "lessons": lessons,
        "txids": dict(session.txids),
    }

    # Hash the content WITHOUT the hash field
    content_hash = hashlib.sha256(canonical_json(content).encode("utf-8")).hexdigest()
    content["sha256"] = f"sha256:{content_hash}"

    return content


def save_proof_pack(pack: dict, path: str = PROOF_PACK_FILE) -> Path:
    """Write proof pack to disk using canonical JSON. Returns file path."""
    filepath = Path(path)
    filepath.write_text(canonical_json(pack), encoding="utf-8", newline="\n")
    return filepath


def verify_proof_pack(pack: dict) -> tuple[bool, str]:
    """Verify a proof pack's integrity. Returns (valid, message).

    Strips the sha256 field, recomputes the hash over the remaining
    content, and compares. Never raises — returns (False, reason) on
    any problem.
    """
    stored_hash = pack.get("sha256", "")
    if not stored_hash:
        return False, "No sha256 field in proof pack."

    # Recompute: remove hash, canonical-serialize, hash
    content = {k: v for k, v in pack.items() if k != "sha256"}
    computed = hashlib.sha256(canonical_json(content).encode("utf-8")).hexdigest()

    expected = f"sha256:{computed}"
    if stored_hash != expected:
        return False, f"Hash mismatch: stored {stored_hash}, computed {expected}"

    return True, "Proof pack integrity verified."


def proof_pack_has_seed(pack: dict) -> bool:
    """Safety check: ensure no seed leaked into proof pack."""
    text = json.dumps(pack)
    return "sEd" in text or "seed" in text.lower()
