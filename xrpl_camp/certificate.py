"""Certificate generation for XRPL Camp completion."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from xrpl_camp.errors import EXIT_RUNTIME, CampError, CampFailure
from xrpl_camp.models import Session
from xrpl_camp.transport import TESTNET_URL, get_rpc_url

CERTIFICATE_FILE = "xrpl_camp_certificate.json"


# ---------------------------------------------------------------------------
# Typed exceptions
# ---------------------------------------------------------------------------


class SeedLeakDetected(CampFailure):
    """Raised when generated content appears to contain a real XRPL seed.

    save_certificate() and save_proof_pack() raise this instead of writing
    to disk when the seed guard trips, so a credential can never actually
    reach a certificate or proof-pack file -- fail closed rather than
    silently write it. Carries the same code/message/hint shape as
    errors.CampError so a caller can convert it 1:1 if it wants to.
    """

    def __init__(self, artifact: str) -> None:
        self.code = "SEED_LEAK_DETECTED"
        self.message = (
            f"Refusing to write {artifact}: its content appears to "
            f"contain a real XRPL seed."
        )
        self.hint = (
            "This should not happen during normal use and likely means a "
            "bug in xrpl-camp itself. Do not share this file or its "
            "contents -- please report the issue."
        )
        super().__init__(CampError(
            code=self.code, message=self.message, hint=self.hint,
            retryable=False, exit_code=EXIT_RUNTIME,
        ))


class ArtifactWriteError(CampFailure):
    """Raised when writing a certificate or proof pack to disk fails.

    Wraps the underlying OSError with a clearer, typed message -- e.g. the
    OS raises a confusing PermissionError when the real problem is "path
    is a directory," not a permissions issue. Carries the same
    code/message/hint shape as errors.CampError so a caller can convert it
    1:1 if it wants to.
    """

    def __init__(self, path: str, reason: str) -> None:
        self.code = "ARTIFACT_WRITE_FAILED"
        self.message = f"Could not write {path}: {reason}"
        self.hint = (
            "Check that the path's parent directory is writable and that "
            "the path itself does not point at a directory."
        )
        super().__init__(CampError(
            code=self.code, message=self.message, hint=self.hint,
            retryable=False, exit_code=EXIT_RUNTIME,
        ))


# ---------------------------------------------------------------------------
# Seed-leak guard (shared by certificate.py and proof_pack.py)
# ---------------------------------------------------------------------------

_STRIP_CHARS = ",;:\"'()[]{}<>"


def _looks_like_xrpl_seed(token: str) -> bool:
    """True if `token` is (or safely might be) a real XRPL seed.

    Two independent checks; either is enough to flag:

    1. Starts with "sEd" (case-sensitive) -- the fixed, version-byte-derived
       prefix of every ed25519 seed. Cheap, and deliberately conservative:
       a truncated or otherwise-malformed string that merely starts this
       way is still refused, since a near-miss is exactly the kind of
       thing a fail-closed guard should not wave through.
    2. Decodes as a real, checksummed XRPL seed via xrpl-py's own base58
       codec -- covers secp256k1 seeds, which have no fixed short prefix
       (unlike ed25519, they cannot be recognised from the first few
       characters alone; "sEd" is the ed25519 marker, not a secp256k1 one).

    Neither check is "contains the word seed" -- ordinary prose (a lesson
    name, a learner's memo) cannot trip this: plain English essentially
    never contains the literal substring "sEd" case-sensitively, and it
    will not pass a base58 checksum.
    """
    if not token:
        return False
    if token.startswith("sEd"):
        return True
    from xrpl.core.addresscodec import decode_seed  # lazy: keeps CLI startup fast

    try:
        decode_seed(token)
    except Exception:
        # Any failure here means "not a valid seed" -- decode_seed raises a
        # mix of ValueError (bad checksum/charset) and
        # XRPLAddressCodecException (wrong encoding family), and probing
        # arbitrary untrusted text for credential shape is exactly the
        # case a broad except is for: every outcome maps to the same
        # "not a seed" answer.
        return False
    return True


def _contains_xrpl_seed(value: object) -> bool:
    """Recursively scan a JSON-shaped value for anything that looks like a real XRPL seed."""
    if isinstance(value, str):
        if _looks_like_xrpl_seed(value):
            return True
        return any(
            _looks_like_xrpl_seed(token.strip(_STRIP_CHARS))
            for token in value.split()
        )
    if isinstance(value, dict):
        return any(_contains_xrpl_seed(k) for k in value) or any(
            _contains_xrpl_seed(v) for v in value.values()
        )
    if isinstance(value, (list, tuple)):
        return any(_contains_xrpl_seed(v) for v in value)
    return False


# ---------------------------------------------------------------------------
# Attested network (shared by certificate.py and proof_pack.py)
# ---------------------------------------------------------------------------


def _attested_network() -> tuple[str, str]:
    """Return (network_label, rpc_url) for the endpoint actually in effect.

    Reads the same resolution transport.get_rpc_url() uses (the
    XRPL_CAMP_RPC_URL override, falling back to the public Testnet), so the
    attested network always matches what the session's transactions
    actually ran against instead of a hardcoded literal.
    """
    url = get_rpc_url()
    label = "testnet" if url == TESTNET_URL else "custom"
    return label, url


# ---------------------------------------------------------------------------
# Atomic, backed-up disk write (shared by certificate.py and proof_pack.py)
# ---------------------------------------------------------------------------


def _write_artifact(filepath: Path, content: str) -> None:
    """Write `content` to `filepath` atomically, backing up any pre-existing file.

    - Creates parent directories as needed, instead of raising
      FileNotFoundError.
    - Refuses cleanly if `filepath` is itself a directory, rather than
      raising a confusing PermissionError and leaving the directory
      untouched.
    - If a file already exists at `filepath`, it is moved to `<name>.bak`
      (overwriting any previous .bak) instead of being silently destroyed
      -- completing a lesson twice in the same directory no longer
      destroys the first completion's record with zero indication.
    - Writes through a temp file in the same directory and os.replace()s
      it into place, so a process kill mid-write (Ctrl+C, power loss)
      cannot leave a truncated/corrupt file on disk.
    - Wraps any OSError in ArtifactWriteError with a clearer message.
    """
    try:
        if filepath.is_dir():
            raise OSError(f"{filepath} is a directory, not a file")
        filepath.parent.mkdir(parents=True, exist_ok=True)
        if filepath.exists():
            backup_path = filepath.with_name(filepath.name + ".bak")
            os.replace(filepath, backup_path)
        fd, tmp_name = tempfile.mkstemp(
            dir=str(filepath.parent), prefix=filepath.name, suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            os.replace(tmp_name, filepath)
        except BaseException:
            Path(tmp_name).unlink(missing_ok=True)
            raise
    except OSError as e:
        raise ArtifactWriteError(str(filepath), str(e)) from e


# ---------------------------------------------------------------------------
# Certificate
# ---------------------------------------------------------------------------


def generate_certificate(session: Session) -> dict:
    """Generate a certificate dict from session state. No seed included.

    Trusts session.progress as-is: it does not independently re-verify
    that each lesson's transaction actually succeeded on the ledger. That
    validation belongs upstream, at the point lessons are marked complete.
    """
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

    network, _rpc_url = _attested_network()
    total = session.total_duration()
    cert: dict = {
        "schema": "xrpl-camp-certificate-v1",
        "network": network,
        "address": session.wallet_address,
        "completed": completed,
        "issued_at": datetime.now(UTC).isoformat(),
    }
    if total > 0:
        cert["duration_seconds"] = round(total, 1)
    return cert


def save_certificate(cert: dict, path: str = CERTIFICATE_FILE) -> Path:
    """Write certificate to disk. Returns file path.

    Raises SeedLeakDetected instead of writing if the certificate appears
    to contain a real XRPL seed (see certificate_has_seed), and
    ArtifactWriteError if the write itself fails.
    """
    if certificate_has_seed(cert):
        raise SeedLeakDetected(str(path))
    filepath = Path(path)
    _write_artifact(filepath, json.dumps(cert, indent=2))
    return filepath


def certificate_has_seed(cert: dict) -> bool:
    """Safety check: verify no real XRPL seed leaked into certificate."""
    return _contains_xrpl_seed(cert)
