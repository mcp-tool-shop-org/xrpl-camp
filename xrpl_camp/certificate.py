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


class PackGenerationError(CampFailure):
    """Raised when a proof pack's content cannot be canonically hashed.

    generate_proof_pack() computes a SHA-256 over the pack's canonical JSON
    before anything is written to disk. If session.progress holds a value
    canonical_json cannot serialize -- most concretely, a lone Unicode
    surrogate code point smuggled into a txid via a hand-edited
    session.json (json.loads() decodes a bare ``\\ud800`` escape into an
    unpaired surrogate with zero complaint; UTF-8 encoding then refuses it)
    -- that used to surface as a raw, unguarded UnicodeEncodeError with no
    .code/.message/.hint. This gives it the same structured shape as every
    other failure in this package, mirroring how verify_proof_pack already
    turns the identical encoding failure into a clean (False, reason)
    instead of a crash.
    """

    def __init__(self, reason: str) -> None:
        self.code = "PACK_GENERATION_FAILED"
        self.message = f"Could not generate proof pack: {reason}"
        self.hint = (
            "A stored txid or lesson name contains characters that cannot "
            "be safely encoded -- most likely a hand-edited session.json. "
            "Run `xrpl-camp reset` if this session was hand-edited, or fix "
            "the offending field in .xrpl-camp/session.json by hand."
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


def _unique_backup_path(filepath: Path) -> Path:
    """A `<name>.<UTC-timestamp>.bak` path for `filepath` that does not exist.

    Stamped (microsecond resolution) so successive backups sort
    chronologically and, under normal use, never collide -- a learner who
    completes the same lesson a third, fourth, or Nth time in one directory
    gets a NEW backup file each time rather than overwriting the one
    protecting an earlier completion's record. A numeric suffix is appended
    only in the pathological case of two backups landing in the same clock
    tick (a tight loop, or a coarse OS clock), so a generation can never be
    silently overwritten regardless of clock resolution.
    """
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    candidate = filepath.with_name(f"{filepath.name}.{stamp}.bak")
    n = 1
    while candidate.exists():
        candidate = filepath.with_name(f"{filepath.name}.{stamp}-{n}.bak")
        n += 1
    return candidate


def _write_through_tempfile(filepath: Path, content: str) -> None:
    """Write `content` into `filepath` via a same-directory temp file + os.replace().

    Isolated from `_write_artifact` so EVERY failure point of this step --
    including `tempfile.mkstemp` itself, which is the call most likely to be
    the one that actually hits "No space left on device," not just the
    write/replace after it -- is caught by one `except BaseException` in the
    caller and can trigger the backup rollback below. An earlier version of
    this fix wrapped only the fdopen/write/replace portion, which missed
    exactly that case.
    """
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


def _write_artifact(filepath: Path, content: str) -> None:
    """Write `content` to `filepath` atomically, backing up any pre-existing file.

    - Creates parent directories as needed, instead of raising
      FileNotFoundError.
    - Refuses cleanly if `filepath` is itself a directory, rather than
      raising a confusing PermissionError and leaving the directory
      untouched.
    - If a file already exists at `filepath`, it is moved to a uniquely
      timestamped `<name>.<UTC-timestamp>.bak` (see _unique_backup_path)
      instead of being silently destroyed or overwriting an earlier
      backup -- completing a lesson a third, fourth, or Nth time in the
      same directory no longer destroys any earlier completion's record.
      Every prior generation stays recoverable under its own name.
    - Writes through a temp file in the same directory (see
      _write_through_tempfile) and os.replace()s it into place, so a
      process kill mid-write (Ctrl+C, power loss) cannot leave a
      truncated/corrupt file on disk.
    - The backup-then-write sequence is two steps, not one atomic
      operation: if ANY part of the write step fails AFTER the backup
      rename has already happened -- including mkstemp itself failing to
      even create the temp file, e.g. because the disk that "No space
      left on device" refers to is this one -- the prior file is moved
      back into place before raising, so `filepath` is never left with
      nothing at it because of a failure on our side. If that restoration
      itself also fails (the disk is truly gone), the raised error still
      names the exact backup path the old content survives at, instead of
      going silent about it.
    - Wraps any OSError in ArtifactWriteError with a clearer message.
    """
    backup_path: Path | None = None
    restored = False
    try:
        if filepath.is_dir():
            raise OSError(f"{filepath} is a directory, not a file")
        filepath.parent.mkdir(parents=True, exist_ok=True)
        if filepath.exists():
            backup_path = _unique_backup_path(filepath)
            os.replace(filepath, backup_path)
        try:
            _write_through_tempfile(filepath, content)
        except BaseException:
            if backup_path is not None:
                # The failure happened AFTER we already moved the old file
                # out of the way -- anywhere inside _write_through_tempfile,
                # not just its write/replace tail. Put the old file back
                # before propagating, so a write failure on our side never
                # leaves the target path empty when the old content is
                # right there to restore.
                try:
                    os.replace(backup_path, filepath)
                    restored = True
                except OSError:
                    restored = False
            raise
    except OSError as e:
        reason = str(e).rstrip(".") + "."
        if backup_path is not None:
            if restored:
                reason += (
                    f" Your previous version was restored to {filepath} "
                    "and is unchanged."
                )
            else:
                reason += f" Your previous version was preserved at {backup_path}."
        raise ArtifactWriteError(str(filepath), reason) from e


# ---------------------------------------------------------------------------
# Certificate
# ---------------------------------------------------------------------------


def generate_certificate(session: Session) -> dict:
    """Generate a certificate dict from session state. No seed included.

    Trusts session.progress as-is: it does not independently re-verify
    that each lesson's transaction actually succeeded on the ledger. That
    validation belongs upstream, at the point lessons are marked complete.

    The certificate carries no integrity hash by design -- it is a
    human-readable summary, not the artifact meant to be independently
    checked. xrpl_camp.proof_pack.generate_proof_pack/verify_proof_pack is
    that artifact: it is the one that computes and stores a SHA-256 over
    its own content and that a learner (or anyone else) can verify without
    trusting this tool. There is deliberately no verify-certificate
    counterpart to this function.
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
