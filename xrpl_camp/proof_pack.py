"""Proof Pack — a self-consistency-checked completion record for XRPL Camp,
anchored to independently-verifiable XRPL ledger transactions."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from pathlib import Path

from xrpl_camp import __version__
from xrpl_camp.certificate import (
    ArtifactWriteError,
    SeedLeakDetected,
    _attested_network,
    _contains_xrpl_seed,
    _write_artifact,
)
from xrpl_camp.models import Session
from xrpl_camp.transport import EXPLORER_URL

__all__ = [
    "ArtifactWriteError",
    "PROOF_PACK_FILE",
    "SeedLeakDetected",
    "canonical_json",
    "generate_proof_pack",
    "proof_pack_has_seed",
    "save_proof_pack",
    "verify_proof_pack",
]

PROOF_PACK_FILE = "xrpl_camp_proof_pack.json"

# Real XRPL transaction hashes are exactly 64 hex characters. Restricting
# explorer_url construction to this charset -- rather than concatenating
# whatever string happens to be sitting in a (trivially hand-editable)
# session.json -- keeps a malformed or tampered txid from ever reaching an
# unescaped, unvalidated URL.
_TXID_RE = re.compile(r"^[0-9A-Fa-f]{1,64}$")


def _tool_version() -> str:
    """Resolve the attested tool version from installed package metadata.

    Falls back to the xrpl_camp.__version__ constant when no installed
    package metadata is found (e.g. running from a source checkout with no
    `pip install`), so the attested value reflects what is actually
    running rather than only a hand-maintained literal that can drift from
    pyproject.toml's version.
    """
    try:
        return _pkg_version("xrpl-camp")
    except PackageNotFoundError:
        return __version__


def _normalize(obj: object) -> object:
    """Recursively NFC-normalize every string in a JSON-shaped value.

    Two different Unicode representations of what a human considers the
    same text (e.g. "e" + combining acute vs. the precomposed "é"
    codepoint) otherwise hash to different SHA-256 values.
    """
    if isinstance(obj, str):
        return unicodedata.normalize("NFC", obj)
    if isinstance(obj, dict):
        return {_normalize(k): _normalize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalize(v) for v in obj]
    return obj


def canonical_json(data: dict) -> str:
    """Canonical JSON: sorted keys, 2-space indent, LF line endings,
    NFC-normalized strings, trailing newline.

    Identical output for any two Unicode representations of the same
    content, on every platform. Used for hash computation. NaN/Infinity
    are rejected (allow_nan=False) so the output is always valid JSON
    rather than silently emitting the non-standard NaN/Infinity tokens.
    """
    return (
        json.dumps(
            _normalize(data),
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    )


def generate_proof_pack(session: Session) -> dict:
    """Build a proof pack dict with a SHA-256 self-consistency hash.

    The hash is computed over the canonical JSON of all fields except the
    hash itself, and anyone can verify it by stripping the sha256 field
    and recomputing. Because the hashing algorithm is public and nothing
    signs it, this only detects accidental edits and corruption -- it is
    NOT a cryptographic signature and does not by itself prove the pack
    was not fabricated by someone running this same code.

    The real, hard-to-fake anchor is the XRPL ledger itself: every
    completed lesson with a txid can be independently looked up against
    the network named by `network`/`rpc_url` (see each lesson's
    explorer_url) without trusting this tool, or this hash, at all.

    Trusts session.progress as-is: it does not independently re-verify
    that each lesson's transaction actually succeeded on the ledger. That
    validation belongs upstream, at the point lessons are marked complete.
    """
    network, rpc_url = _attested_network()

    lessons = []
    for p in session.progress:
        entry: dict[str, str | int] = {
            "lesson": p.lesson,
            "name": p.name,
            "completed_at": p.completed_at,
        }
        if p.txid:
            entry["txid"] = p.txid
            if _TXID_RE.match(p.txid):
                entry["explorer_url"] = f"{EXPLORER_URL}{p.txid}"
        lessons.append(entry)

    content: dict = {
        "schema": "xrpl-camp-proof-pack-v1",
        "address": session.wallet_address,
        "network": network,
        "rpc_url": rpc_url,
        "tool_version": _tool_version(),
        "issued_at": datetime.now(UTC).isoformat(),
        "lessons": lessons,
        "txids": dict(session.txids),
    }

    # Hash the content WITHOUT the hash field
    content_hash = hashlib.sha256(canonical_json(content).encode("utf-8")).hexdigest()
    content["sha256"] = f"sha256:{content_hash}"

    return content


def save_proof_pack(pack: dict, path: str = PROOF_PACK_FILE) -> Path:
    """Write proof pack to disk using canonical JSON. Returns file path.

    Raises SeedLeakDetected instead of writing if the pack appears to
    contain a real XRPL seed (see proof_pack_has_seed), and
    ArtifactWriteError if the write itself fails.
    """
    if proof_pack_has_seed(pack):
        raise SeedLeakDetected(str(path))
    filepath = Path(path)
    _write_artifact(filepath, canonical_json(pack))
    return filepath


def verify_proof_pack(pack: object) -> tuple[bool, str]:
    """Verify a proof pack's self-consistency. Returns (valid, message).

    Strips the sha256 field, recomputes the hash over the remaining
    content, and compares. Never raises -- returns (False, reason) on any
    problem, including malformed input: a non-dict top-level JSON value
    (array/string/number/bool/null), an unpaired Unicode surrogate that
    cannot be UTF-8 encoded, or a value canonical_json cannot serialize.

    A True result means the content matches its own embedded hash -- it
    does NOT mean the content is truthful. The hash is not a signature; it
    only proves internal self-consistency. To check truthfulness,
    independently look up each lesson's txid against the XRPL ledger named
    by the pack's `network`/`rpc_url` fields.
    """
    if not isinstance(pack, dict):
        return False, "Proof pack must be a JSON object."

    stored_hash = pack.get("sha256", "")
    if not stored_hash:
        return False, "No sha256 field in proof pack."

    # Recompute: remove hash, canonical-serialize, hash
    content = {k: v for k, v in pack.items() if k != "sha256"}
    try:
        computed = hashlib.sha256(canonical_json(content).encode("utf-8")).hexdigest()
    except (TypeError, ValueError, UnicodeError) as e:
        return False, f"Could not canonicalize proof pack content: {e}"

    expected = f"sha256:{computed}"
    if stored_hash != expected:
        return False, f"Hash mismatch: stored {stored_hash}, computed {expected}"

    return True, "Proof pack integrity verified."


def proof_pack_has_seed(pack: dict) -> bool:
    """Safety check: ensure no real XRPL seed leaked into proof pack."""
    return _contains_xrpl_seed(pack)
