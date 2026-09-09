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
    PackGenerationError,
    SeedLeakDetected,
    _attested_network,
    _contains_xrpl_seed,
    _write_artifact,
)
from xrpl_camp.errors import EXIT_OK, EXIT_PARTIAL, EXIT_USER
from xrpl_camp.models import Session
from xrpl_camp.transport import (
    EXPLORER_URL,
    REASON_HISTORY_GONE,
    REASON_UNVALIDATED,
    TESTNET_URL,
)

__all__ = [
    "ArtifactWriteError",
    "ONLINE_MISMATCH",
    "ONLINE_MISS_HISTORY_GONE",
    "ONLINE_MISS_NOT_FOUND",
    "ONLINE_NOT_CHECKABLE",
    "ONLINE_OK",
    "ONLINE_UNREACHABLE",
    "PROOF_PACK_FILE",
    "PROOF_PACK_SCHEMA",
    "PackGenerationError",
    "SUPPORTED_PROOF_PACK_SCHEMAS",
    "SeedLeakDetected",
    "UNSEALED_FIELDS",
    "apply_attestation_warnings",
    "batch_summary",
    "build_verification_receipt",
    "canonical_json",
    "classify_lesson_online",
    "endpoint_claim",
    "generate_proof_pack",
    "online_exit_code",
    "online_lookup_plan",
    "proof_pack_has_seed",
    "record_verification",
    "resolve_verification_endpoint",
    "save_proof_pack",
    "summarize_online",
    "verify_proof_pack",
]

PROOF_PACK_FILE = "xrpl_camp_proof_pack.json"

#: The proof-pack schema this version of xrpl-camp WRITES. This is the one
#: place that literal is allowed to live -- callers elsewhere (e.g. the CLI's
#: own schema gate) should import this constant rather than hand-duplicating
#: the string, which is exactly how a second copy silently drifted out of
#: sync with this one before.
PROOF_PACK_SCHEMA = "xrpl-camp-proof-pack-v1"

#: Every schema value verify_proof_pack recognizes. A SET, not a single
#: exact-match constant: the day PROOF_PACK_SCHEMA is bumped to a v2, every
#: older, perfectly valid v1 pack a past learner is holding must stay
#: verifiable -- so a future version bump should ADD to this set rather than
#: replace it.
SUPPORTED_PROOF_PACK_SCHEMAS = frozenset({PROOF_PACK_SCHEMA})

# A real XRPL transaction hash is EXACTLY 64 hex characters -- never 12, never
# 1. This regex previously accepted 1-64, which meant a hand-edited session.json
# holding "DEADBEEF" got a confident-looking explorer_url built for it that can
# only ever 404, and (once --online exists) would have earned a pointless
# network round-trip on a string that cannot be a transaction hash. Requiring
# the full length is both the honest local check and the cheapest possible
# filter in front of the network.
_TXID_RE = re.compile(r"^[0-9A-Fa-f]{64}$")

#: Fields deliberately left OUTSIDE the SHA-256 seal.
#:
#: - ``sha256`` is the hash itself and obviously cannot cover itself.
#: - ``verifications`` is an append-only log of "somebody's tool checked this
#:   pack against the ledger on this date." The whole point of a receipt is
#:   that it can be appended YEARS after the original seal, by a learner or a
#:   facilitator who does not have (and should not need) whatever produced the
#:   original pack. Covering it with the hash would make every append
#:   invalidate the seal, which is exactly backwards. The cost of leaving it
#:   outside is that it is unsealed and therefore worthless as evidence -- so
#:   nothing in this module ever treats it as evidence, and both
#:   verify_proof_pack's message and every receipt's own ``self_reported``
#:   field say so out loud.
#:
#: Packs written before ``verifications`` existed have no such key, so
#: excluding it changes nothing about their hash: every older pack still
#: verifies byte-for-byte against this code.
UNSEALED_FIELDS = frozenset({"sha256", "verifications"})


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
    explorer_url) without trusting this tool, or this hash, at all. When
    the lesson that recorded a txid also captured the ledger's own
    `ledger_index`/`close_time_iso` (see models.LessonProgress), those ride
    along per-lesson too -- so a reader can later tell "this txid stopped
    resolving because the Testnet was reset after ledger index N" apart
    from "this txid never existed."

    Each lesson that recorded a txid also carries the `memo` the learner
    wrote onto the ledger, when the lesson captured one. That sentence is
    the only part of this record the learner actually authored, and it is
    also the ground truth `classify_lesson_online`'s memo-binding check
    compares against -- without it in the pack, that check has nothing to
    compare to and can only ever report "not checkable."

    Trusts session.progress as-is: it does not independently re-verify
    against the live ledger that each lesson's transaction actually
    succeeded -- that validation belongs upstream, at the point lessons are
    marked complete, and a real re-check belongs in an online verify mode
    (see `classify_lesson_online` and `proof verify --online`), not here.
    What this function DOES assert locally, honestly, without a network
    call: a txid that does not even have the shape of a real XRPL
    transaction hash (exactly 64 hex characters) is flagged via
    `txid_format_warning` instead of being silently included as if it were
    legitimate -- catching the cheapest hand-edited-session.json case for
    free.

    Raises PackGenerationError (never a raw UnicodeEncodeError/TypeError/
    ValueError) if some stored field -- most concretely a lone Unicode
    surrogate smuggled into a txid or name -- cannot be canonically hashed.
    """
    network, rpc_url = _attested_network()

    lessons = []
    for p in session.progress:
        entry: dict[str, str | int | bool] = {
            "lesson": p.lesson,
            "name": p.name,
            "completed_at": p.completed_at,
        }
        if p.txid:
            entry["txid"] = p.txid
            if _TXID_RE.match(p.txid):
                entry["explorer_url"] = f"{EXPLORER_URL}{p.txid}"
            else:
                # A txid this shape can never be a real XRPL transaction
                # hash. Flagging it -- rather than silently dropping it (an
                # entry that would then look identical to a clean offline
                # lesson) or silently including it as if legitimate -- is
                # the honest move for an artifact whose whole purpose is
                # transparency.
                entry["txid_format_warning"] = (
                    "does not match the expected XRPL transaction hash "
                    "format (exactly 64 hex characters) -- likely hand-edited"
                )
            # Optional ledger provenance, when the lesson that recorded
            # this txid also captured it (see models.LessonProgress).
            # Getattr-guarded: additive/backward-compatible whether or not
            # the running models.py version has these fields yet.
            ledger_index = getattr(p, "ledger_index", 0) or 0
            if ledger_index:
                entry["ledger_index"] = ledger_index
            close_time_iso = getattr(p, "close_time_iso", "") or ""
            if close_time_iso:
                entry["close_time_iso"] = close_time_iso
            # The sentence the learner wrote onto the ledger. Same
            # getattr-guard convention as above, for sessions saved before
            # the field existed. Free text, so it is exactly the field a
            # credential could be pasted into by accident -- save_proof_pack's
            # existing proof_pack_has_seed() gate already covers it, and that
            # is why this is safe to include verbatim.
            memo = getattr(p, "memo", "") or ""
            if memo:
                entry["memo"] = memo
        lessons.append(entry)

    content: dict = {
        "schema": PROOF_PACK_SCHEMA,
        "address": session.wallet_address,
        "network": network,
        "rpc_url": rpc_url,
        "tool_version": _tool_version(),
        "issued_at": datetime.now(UTC).isoformat(),
        "lessons": lessons,
        "txids": dict(session.txids),
    }

    # Hash the content WITHOUT the unsealed fields (see UNSEALED_FIELDS).
    # A freshly generated pack has none of them yet, so _sealed_content is a
    # no-op here -- it is called anyway so this and verify_proof_pack compute
    # over provably identical input rather than two expressions that have to
    # be kept in sync by hand.
    #
    # Mirrors verify_proof_pack's identical guard below: a lone Unicode
    # surrogate (or any other value canonical_json's allow_nan=False/NFC pass
    # cannot serialize) must raise a structured, typed error here too, not a
    # bare UnicodeEncodeError.
    try:
        content_hash = hashlib.sha256(
            canonical_json(_sealed_content(content)).encode("utf-8"),
        ).hexdigest()
    except (TypeError, ValueError, UnicodeError) as e:
        raise PackGenerationError(str(e)) from e
    content["sha256"] = f"sha256:{content_hash}"

    return content


def _sealed_content(pack: dict) -> dict:
    """`pack` minus every field the SHA-256 deliberately does not cover."""
    return {k: v for k, v in pack.items() if k not in UNSEALED_FIELDS}


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
    only proves internal self-consistency: it confirms the file has not
    been edited since it was written. It does NOT independently confirm
    each transaction against the XRPL ledger -- to check that, look up
    each lesson's txid yourself against the network named by the pack's
    `network`/`rpc_url` fields. The returned message says this explicitly
    rather than leaving "verified" to be read as "this really happened."

    Hash verification is intentionally SCHEMA-AGNOSTIC: a pack's content
    can be perfectly self-consistent under a schema this version of
    xrpl-camp has never seen (e.g. a future v2 written by a newer tool).
    Rather than reject that outright -- which would make an old tool
    unable to even confirm a newer, honest pack has not been tampered
    with -- a True result always names the schema it verified against, and
    clearly flags when that schema is not one of SUPPORTED_PROOF_PACK_SCHEMAS
    instead of silently claiming full understanding of it.
    """
    if not isinstance(pack, dict):
        return False, "Proof pack must be a JSON object."

    stored_hash = pack.get("sha256", "")
    if not stored_hash:
        return False, "No sha256 field in proof pack."

    # Recompute: drop the unsealed fields, canonical-serialize, hash
    try:
        computed = hashlib.sha256(
            canonical_json(_sealed_content(pack)).encode("utf-8"),
        ).hexdigest()
    except (TypeError, ValueError, UnicodeError) as e:
        return False, f"Could not canonicalize proof pack content: {e}"

    expected = f"sha256:{computed}"
    if stored_hash != expected:
        return False, f"Hash mismatch: stored {stored_hash}, computed {expected}"

    receipts = _verification_receipts(pack)
    receipt_note = ""
    if receipts:
        n = len(receipts)
        receipt_note = (
            f" This pack also carries {n} attached verification "
            f"{'receipt' if n == 1 else 'receipts'}, which sit OUTSIDE the "
            "hash and are self-reported log lines -- 'someone's tool said "
            "this passed on this date' -- not evidence, and they raise this "
            "result's confidence by exactly nothing."
        )

    schema = pack.get("schema", "")
    if schema not in SUPPORTED_PROOF_PACK_SCHEMAS:
        return True, (
            f"Proof pack integrity verified against schema "
            f"{schema or '(missing)'}, which this version of xrpl-camp does "
            "not recognize: contents match their own recorded hash, but "
            "this tool cannot confirm it understood every field in a "
            "schema newer than it knows. Either way, this confirms only "
            "that the file has not been edited since it was written -- it "
            "does not independently confirm each transaction against the "
            "XRPL ledger. Verifying with a newer xrpl-camp release may "
            f"say more.{receipt_note}"
        )

    return True, (
        f"Proof pack integrity verified against schema {schema}: contents "
        "match their own recorded hash. This confirms the file has not "
        "been edited since it was written -- it does not independently "
        "confirm each transaction against the XRPL ledger. Run this same "
        "command with --online to check every transaction against the "
        "network, or look each txid up yourself in a block explorer."
        f"{receipt_note}"
    )


def proof_pack_has_seed(pack: dict) -> bool:
    """Safety check: ensure no real XRPL seed leaked into proof pack."""
    return _contains_xrpl_seed(pack)


# ===========================================================================
# Online verification
#
# The honest claim this product can make about a proof pack is two-layered:
# the SHA-256 above catches accidental edits, and the LEDGER is the part
# nobody can fake. Until now the tool only did the first half, which meant the
# strongest true thing about the artifact was the one thing the tool would not
# check for you.
#
# ARCHITECTURE. Everything in this section is PURE: it takes lookup results
# that somebody else already fetched and returns a verdict. proof_pack.py
# makes no network calls, imports no client, and opens no socket -- that
# invariant is what makes every branch below unit-testable offline, and it is
# also why the classifier cannot be tricked into calling an endpoint of the
# pack's choosing. Network orchestration (retry, timeout, progress) lives in
# cli.py, which reuses lessons.try_network rather than growing a second retry
# loop.
# ===========================================================================

#: Per-lesson verdicts from `classify_lesson_online`.
#:
#: These names are load-bearing in the output and in the docs: a MISS is not a
#: MISMATCH, and `miss_ledger_history_gone` in particular is not fraud -- it
#: is the Testnet having been reset out from under an honest learner.
ONLINE_OK = "ok"
ONLINE_MISMATCH = "mismatch"
ONLINE_MISS_HISTORY_GONE = "miss_ledger_history_gone"
ONLINE_MISS_NOT_FOUND = "miss_not_found"
ONLINE_UNREACHABLE = "unreachable"
ONLINE_NOT_CHECKABLE = "not_checkable"

#: Top-level rollups from `summarize_online`.
SUMMARY_CONFIRMED = "confirmed"
SUMMARY_CONTRADICTED = "contradicted"
SUMMARY_HISTORY_GONE = "ledger_history_gone"
SUMMARY_UNKNOWN = "unknown"
SUMMARY_NOTHING_TO_CHECK = "nothing_to_check"

_ONLINE_MEANING = {
    ONLINE_OK: (
        "A transaction with this exact hash is on the ledger, was sent by "
        "this pack's address, and closed successfully.",
        "That xrpl-camp produced it, or that only this learner ever held "
        "the key -- nothing here is signed, so possession of the seed is "
        "not proven.",
    ),
    ONLINE_MISMATCH: (
        "The ledger was reachable and answered about this hash. What it said "
        "contradicts what this pack claims.",
        "Which side is wrong. The ledger is the authority on what happened; "
        "the pack is the thing being checked.",
    ),
    ONLINE_MISS_HISTORY_GONE: (
        "The endpoint no longer holds history reaching back to the ledger "
        "this transaction closed in. XRPL Testnet is periodically wiped; "
        "this is that, not a forgery.",
        "That the transaction was real. It cannot be re-checked here at "
        "all -- an endpoint with deeper history, or an archival explorer, "
        "is the only way to settle it now.",
    ),
    ONLINE_MISS_NOT_FOUND: (
        "The endpoint has history covering the period this pack claims and "
        "reports no transaction with this hash.",
        "Intent. A hand-edited session file and a genuine mistake look "
        "identical from here.",
    ),
    ONLINE_UNREACHABLE: (
        "Nothing. The endpoint could not be reached, so no claim about this "
        "transaction was checked either way.",
        "Anything at all. This is an unknown, not a pass and not a failure.",
    ),
    ONLINE_NOT_CHECKABLE: (
        "Nothing about the ledger. This lesson records no usable transaction "
        "hash, so there was nothing to look up.",
        "That the lesson was not completed -- several lessons are offline by "
        "design and legitimately have no transaction.",
    ),
}


def resolve_verification_endpoint(rpc_url_override: str = "") -> str:
    """The endpoint `--online` verification queries. NEVER the pack's own.

    NOTE THE SIGNATURE: this function does not accept the pack, and must not
    be changed to. That is not stylistic -- it is the entire security
    property, expressed in a way a later "simplification" cannot quietly
    undo.

    WHY, measured. During the wave-5 audit a fake rippled server was stood up
    and a forged pack was written naming it in `rpc_url`. A verifier that
    resolved "every txid in the pack against the XRPL" by reading the pack's
    own `rpc_url` reported the forgery as fully verified -- including a
    transaction that had never existed on any ledger. The identical pack
    checked against a fixed endpoint was caught immediately. Asking a
    document to nominate its own auditor is not verification; it is a
    formality with a network round-trip in it.

    So the oracle is one of exactly two things, both chosen OUTSIDE the file
    under test:

    1. `transport.TESTNET_URL` -- this tool's own fixed default.
    2. An `--rpc-url` the operator typed, for the deliberate case of checking
       a devnet or private-endpoint pack.

    A pack's `network`/`rpc_url` may still be shown to the reader as a
    labelled CLAIM (see `endpoint_claim`) -- "this pack says X, we checked
    against Y". Displaying is not trusting.

    Deliberately does NOT read the XRPL_CAMP_RPC_URL environment variable
    either: `get_rpc_url()` is the right resolution for a learner running
    lessons, but the whole job here is auditing someone else's file, and an
    ambient env var is a less visible way to arrive at the same trap. An
    operator who wants a different endpoint says so on the command line,
    where it appears in the output.
    """
    override = (rpc_url_override or "").strip()
    return override or TESTNET_URL


def endpoint_claim(pack: object, endpoint_used: str) -> dict:
    """What the pack CLAIMS about its network vs. what was actually queried.

    Purely for display. The `matches` flag is information for the reader, not
    a gate: a pack recorded against a private endpoint and audited against
    the public Testnet SHOULD say so loudly, and should not be failed for it,
    because "the pack names a different endpoint" is precisely what a forgery
    and an honest devnet run have in common.
    """
    claimed_network = ""
    claimed_url = ""
    if isinstance(pack, dict):
        claimed_network = str(pack.get("network", "") or "")
        claimed_url = str(pack.get("rpc_url", "") or "")

    matches = bool(claimed_url) and claimed_url == endpoint_used
    if not claimed_url:
        note = (
            f"This pack names no endpoint. Checked against {endpoint_used}."
        )
    elif matches:
        note = (
            f"This pack claims {claimed_network or 'an unnamed network'} at "
            f"{claimed_url}, which is what was checked."
        )
    else:
        note = (
            f"This pack claims {claimed_network or 'an unnamed network'} at "
            f"{claimed_url}, but it was checked against {endpoint_used} -- "
            "the pack does not get to choose where it is verified. If this "
            "pack really was made against another endpoint, re-run with "
            "--rpc-url to check it there deliberately."
        )
    return {
        "pack_claims_network": claimed_network,
        "pack_claims_rpc_url": claimed_url,
        "verified_against": endpoint_used,
        "matches_claim": matches,
        "note": note,
    }


def online_lookup_plan(pack: object) -> list[dict]:
    """What cli.py must fetch, and what it must NOT bother fetching.

    One item per lesson in the pack, in pack order. For each:

        {"lesson": int, "txid": str, "recorded_ledger_index": int,
         "checkable": bool, "skip_reason": str}

    Callers look up ONLY the items with ``checkable`` True, and MUST pass
    ``recorded_ledger_index`` straight through to ``transport.lookup_tx``:
    that argument is the only thing that lets a miss be reported as
    ``ledger_history_gone`` instead of as a forgery, and dropping it turns
    every post-Testnet-reset pack into an accusation.

    A txid that is not exactly 64 hex characters is never worth a network
    round-trip -- it cannot be a transaction hash, so `not_checkable` is a
    complete answer that costs nothing.
    """
    plan: list[dict] = []
    lessons = pack.get("lessons", []) if isinstance(pack, dict) else []
    if not isinstance(lessons, list):
        return plan
    for entry in lessons:
        if not isinstance(entry, dict):
            continue
        txid = str(entry.get("txid", "") or "")
        recorded = entry.get("ledger_index", 0)
        try:
            recorded_index = int(recorded or 0)
        except (TypeError, ValueError):
            recorded_index = 0
        if not txid:
            checkable, reason = False, "this lesson records no transaction"
        elif not _TXID_RE.match(txid):
            checkable, reason = False, (
                "the recorded txid is not a 64-character hex transaction "
                "hash, so it cannot name anything on the ledger"
            )
        else:
            checkable, reason = True, ""
        plan.append({
            "lesson": entry.get("lesson", 0),
            "txid": txid,
            "recorded_ledger_index": recorded_index,
            "checkable": checkable,
            "skip_reason": reason,
        })
    return plan


def _verification_receipts(pack: object) -> list:
    """The pack's attached (unsealed, self-reported) verification log."""
    if not isinstance(pack, dict):
        return []
    receipts = pack.get("verifications", [])
    return receipts if isinstance(receipts, list) else []


def _same_text(a: object, b: object) -> bool:
    """NFC-insensitive string comparison.

    `canonical_json` NFC-normalizes everything it writes, so a pack's memo is
    always NFC. What the ledger hands back is whatever bytes were submitted.
    Comparing those two directly would report a mismatch for two byte
    sequences a human would call the same sentence -- an accusation of
    forgery caused by a Unicode encoding choice.
    """
    return _normalize(str(a)) == _normalize(str(b))


def classify_lesson_online(
    entry: object,
    pack_address: str,
    live: object,
    *,
    unreachable_reason: str = "",
) -> dict:
    """Classify ONE lesson entry against ONE already-fetched lookup result.

    Pure. No network, no clock, no disk. `live` is a
    ``transport.lookup_tx``-shaped dict; pass ``None`` (with
    ``unreachable_reason``) when the endpoint could not be reached at all,
    which is a genuinely different answer from any result the ledger gave.

    The five checks, and what each one does and does not establish:

    1. EXISTENCE -- a transaction with this exact hash was accepted by
       consensus on the network that was queried. It does NOT establish that
       xrpl-camp produced it, nor that whoever holds this file is the address
       owner: nothing here is signed.
    2. ACCOUNT BINDING -- ``live["account"] == pack_address``. This closes the
       cheapest real forgery: lift any genuine txid off an explorer, paste it
       into a session file, claim it under a different address. It does NOT
       establish that the seed was never shared.
    3. SUCCESS -- ``validated`` is true AND the result is ``tesSUCCESS``. A
       transaction can be on the ledger and have reverted; without this, a
       ``tec``-class failure could be attested as an accomplishment.
    4. MEMO BINDING -- the sentence in the pack is the sentence on the ledger.
       Only checkable when the pack carries a memo for that lesson; when it
       does not, this reports "not checked" rather than passing by default.
    5. LEDGER PROVENANCE -- the recorded ``ledger_index``/``close_time_iso``
       match what the ledger reports. This is what makes a later MISS legible:
       the recorded index is what tells a Testnet reset apart from a hash that
       was never real.

    A check that cannot be performed is ``None``, never ``True``. "We did not
    look" and "we looked and it was fine" are different facts, and collapsing
    them is how a verifier starts lying politely.
    """
    entry = entry if isinstance(entry, dict) else {}
    txid = str(entry.get("txid", "") or "")
    checks: dict[str, bool | None] = {
        "exists": None,
        "account_binding": None,
        "validated_success": None,
        "memo_binding": None,
        "ledger_provenance": None,
    }
    result: dict = {
        "lesson": entry.get("lesson", 0),
        "name": entry.get("name", ""),
        "txid": txid,
        "checks": checks,
        "problems": [],
        "ledger_index_seen": 0,
        "ledger_reason": "",
    }

    def finish(status: str, problems: list[str] | None = None) -> dict:
        result["status"] = status
        result["problems"] = problems or []
        proves, does_not = _ONLINE_MEANING[status]
        result["proves"] = proves
        result["does_not_prove"] = does_not
        return result

    # --- nothing to look up -------------------------------------------------
    if not txid:
        return finish(ONLINE_NOT_CHECKABLE, ["this lesson records no transaction"])
    if not _TXID_RE.match(txid):
        return finish(ONLINE_NOT_CHECKABLE, [
            "the recorded txid is not a 64-character hex transaction hash, "
            "so it cannot name anything on the ledger",
        ])

    # --- endpoint never answered -------------------------------------------
    if live is None or not isinstance(live, dict):
        return finish(ONLINE_UNREACHABLE, [
            unreachable_reason
            or "the endpoint could not be reached, so nothing was checked",
        ])

    result["ledger_reason"] = str(live.get("reason", "") or "")

    # --- (1) existence ------------------------------------------------------
    if not live.get("found", False):
        checks["exists"] = False
        if result["ledger_reason"] == REASON_HISTORY_GONE:
            # NOT fraud. The recorded ledger_index predates the earliest
            # ledger this endpoint still holds, which is what a Testnet reset
            # looks like from here. Reporting this as a forgery is the exact
            # failure --online exists to prevent, and it is why
            # online_lookup_plan insists the recorded index be passed through.
            return finish(ONLINE_MISS_HISTORY_GONE, [
                "this endpoint's history no longer reaches back to ledger "
                f"{entry.get('ledger_index', 'unknown')}, where this "
                "transaction was recorded as closing",
            ])
        problems = ["no transaction with this hash is on the ledger"]
        if not entry.get("ledger_index"):
            # Honest about the limit of our own answer: with no recorded
            # index there is no way to ask "was history discarded?", so a
            # reset and a fabrication are indistinguishable from here.
            problems.append(
                "this pack recorded no ledger index for the transaction, so "
                "a wiped Testnet and a hash that was never real cannot be "
                "told apart",
            )
        return finish(ONLINE_MISS_NOT_FOUND, problems)

    checks["exists"] = True
    try:
        result["ledger_index_seen"] = int(live.get("ledger_index", 0) or 0)
    except (TypeError, ValueError):
        result["ledger_index_seen"] = 0

    problems: list[str] = []

    # --- (2) account binding ------------------------------------------------
    live_account = str(live.get("account", "") or "")
    checks["account_binding"] = bool(live_account) and live_account == pack_address
    if not checks["account_binding"]:
        problems.append(
            f"the ledger says this transaction was sent by "
            f"{live_account or '(no account)'}, but this pack claims "
            f"{pack_address or '(no address)'}",
        )

    # --- (3) validated success ---------------------------------------------
    live_result = str(live.get("result", "") or "")
    validated = bool(live.get("validated", False))
    checks["validated_success"] = validated and live_result == "tesSUCCESS"
    if not validated:
        problems.append(
            "the ledger has this transaction but has not validated it in a "
            "closed ledger"
            + (
                " (the endpoint reported it as still unvalidated)"
                if result["ledger_reason"] == REASON_UNVALIDATED
                else ""
            ),
        )
    elif live_result != "tesSUCCESS":
        problems.append(
            f"the transaction closed with {live_result or 'no result code'}, "
            "not tesSUCCESS -- it is on the ledger, but it did not do what "
            "this pack presents it as having done",
        )

    # --- (4) memo binding ---------------------------------------------------
    claimed_memo = str(entry.get("memo", "") or "")
    if claimed_memo:
        checks["memo_binding"] = _same_text(live.get("memo", ""), claimed_memo)
        if not checks["memo_binding"]:
            problems.append(
                "the memo on the ledger is not the sentence this pack "
                "attributes to the learner",
            )
    # else: stays None -- no ground truth to compare against, so no claim.

    # --- (5) ledger provenance ---------------------------------------------
    claimed_index = entry.get("ledger_index", 0)
    claimed_close = str(entry.get("close_time_iso", "") or "")
    if claimed_index or claimed_close:
        provenance_ok = True
        if claimed_index:
            try:
                provenance_ok = int(claimed_index) == result["ledger_index_seen"]
            except (TypeError, ValueError):
                provenance_ok = False
            if not provenance_ok:
                problems.append(
                    f"this pack records ledger {claimed_index}, but the "
                    f"ledger reports {result['ledger_index_seen']}",
                )
        live_close = str(live.get("close_time_iso", "") or "")
        if claimed_close and live_close and not _same_text(live_close, claimed_close):
            provenance_ok = False
            problems.append(
                f"this pack records a close time of {claimed_close}, but the "
                f"ledger reports {live_close}",
            )
        checks["ledger_provenance"] = provenance_ok

    if problems:
        return finish(ONLINE_MISMATCH, problems)
    return finish(ONLINE_OK, [])


def summarize_online(results: list) -> dict:
    """Roll per-lesson verdicts up into one honest top-level answer.

    Precedence is deliberate and is NOT "most common wins":

    - any MISMATCH        -> contradicted. One transaction the ledger
                             disagrees about poisons the pack; the rest
                             passing does not dilute it.
    - any UNREACHABLE     -> unknown. A pack cannot be called confirmed when
                             part of it was never actually checked.
    - any HISTORY GONE    -> ledger_history_gone. Not a failure. The network
                             was reset; there is nothing left here to check
                             and nobody did anything wrong.
    - any MISS NOT FOUND  -> contradicted. History is present and the
                             transaction is not in it.
    - nothing checkable   -> nothing_to_check.
    - otherwise           -> confirmed.
    """
    results = [r for r in (results or []) if isinstance(r, dict)]
    counts: dict[str, int] = {}
    for r in results:
        status = str(r.get("status", ""))
        counts[status] = counts.get(status, 0) + 1

    checked = counts.get(ONLINE_OK, 0)
    total_lookups = sum(
        counts.get(s, 0)
        for s in (
            ONLINE_OK, ONLINE_MISMATCH, ONLINE_MISS_HISTORY_GONE,
            ONLINE_MISS_NOT_FOUND, ONLINE_UNREACHABLE,
        )
    )

    if counts.get(ONLINE_MISMATCH):
        status = SUMMARY_CONTRADICTED
        message = (
            f"{counts[ONLINE_MISMATCH]} of {total_lookups} transactions do "
            "not match what the ledger says. The ledger is the authority "
            "here, not this file."
        )
    elif counts.get(ONLINE_UNREACHABLE):
        status = SUMMARY_UNKNOWN
        message = (
            f"{counts[ONLINE_UNREACHABLE]} of {total_lookups} transactions "
            "could not be checked because the endpoint was unreachable. "
            "Nothing was disproved and nothing was confirmed."
        )
    elif counts.get(ONLINE_MISS_NOT_FOUND):
        status = SUMMARY_CONTRADICTED
        message = (
            f"{counts[ONLINE_MISS_NOT_FOUND]} of {total_lookups} "
            "transactions are absent from a ledger whose history covers the "
            "period this pack claims."
        )
    elif counts.get(ONLINE_MISS_HISTORY_GONE):
        status = SUMMARY_HISTORY_GONE
        message = (
            f"{counts[ONLINE_MISS_HISTORY_GONE]} of {total_lookups} "
            "transactions predate this endpoint's earliest retained ledger. "
            "XRPL Testnet is periodically wiped -- this is that, not a "
            "forgery, and it cannot be re-checked here."
        )
    elif total_lookups == 0:
        status = SUMMARY_NOTHING_TO_CHECK
        message = (
            "This pack records no transaction that could be looked up, so "
            "online verification had nothing to check. The hash result above "
            "is the whole answer."
        )
    else:
        status = SUMMARY_CONFIRMED
        message = (
            f"All {checked} recorded transactions are on the ledger, were "
            "sent by this pack's address, and closed successfully."
        )

    return {
        "status": status,
        "message": message,
        "counts": counts,
        "checked": checked,
        "total_lookups": total_lookups,
    }


def apply_attestation_warnings(pack: dict, results: list) -> dict:
    """Stamp online verdicts onto a pack's lessons and RE-SEAL it.

    Defence in depth for the vector this module cannot otherwise see.
    `generate_proof_pack` is a pure pass-through of `session.progress`, and
    `Session.load()` applies no existence check to a txid -- so a hand-edited
    `.xrpl-camp/session.json` reaches the attestation layer with nothing
    standing in its way. For a product whose entire premise is "you do not
    have to trust this tool," the one place that still blindly trusts its
    only input should not be the part that issues the attestation.

    This is the marking half of the answer, not the refusing half: a lesson
    the ledger disagrees about gets `attestation_warning` /
    `attestation_status` -- exactly parallel to the existing
    `txid_format_warning` -- rather than being silently sealed as if fine, or
    dropped in a way that would make it indistinguishable from an honest
    offline lesson.

    The pack is re-sealed afterwards, so the warning is INSIDE the hash and
    cannot be quietly deleted by whoever holds the file. Stale warnings from
    an earlier run are cleared for every lesson present in `results`, so a
    re-check that now passes does not leave an accusation behind.

    Pure: it takes verdicts somebody else fetched. The network orchestration
    belongs in cli.py's `certificate --verify-online` path, and this stays
    opt-in there -- `xrpl-camp certificate` must remain fast and offline by
    default, or this fix would contradict the offline-first design it exists
    to protect.
    """
    by_lesson = {}
    for entry in pack.get("lessons", []):
        if isinstance(entry, dict):
            by_lesson[entry.get("lesson")] = entry

    for r in results or []:
        if not isinstance(r, dict):
            continue
        entry = by_lesson.get(r.get("lesson"))
        if entry is None:
            continue
        entry.pop("attestation_warning", None)
        entry.pop("attestation_status", None)
        status = str(r.get("status", ""))
        if status in (ONLINE_OK, ONLINE_NOT_CHECKABLE):
            continue
        problems = [str(p) for p in r.get("problems", []) if p]
        entry["attestation_status"] = status
        entry["attestation_warning"] = (
            "; ".join(problems)
            or _ONLINE_MEANING.get(status, ("", ""))[0]
        )

    try:
        content_hash = hashlib.sha256(
            canonical_json(_sealed_content(pack)).encode("utf-8"),
        ).hexdigest()
    except (TypeError, ValueError, UnicodeError) as e:
        raise PackGenerationError(str(e)) from e
    pack["sha256"] = f"sha256:{content_hash}"
    return pack


def online_exit_code(summary: object) -> int:
    """Process exit code for an online verification summary.

    ``contradicted`` is a hard failure (1). ``unknown`` and
    ``ledger_history_gone`` are the CLI's documented-but-until-now-unused
    exit code 3, partial success: the hash result stands, the ledger result
    does not exist, and conflating "could not check" with "checked and it
    failed" would make an unreachable endpoint look like an accusation.
    """
    status = ""
    if isinstance(summary, dict):
        status = str(summary.get("status", ""))
    if status == SUMMARY_CONTRADICTED:
        return EXIT_USER
    if status in (SUMMARY_UNKNOWN, SUMMARY_HISTORY_GONE):
        return EXIT_PARTIAL
    return EXIT_OK


# ---------------------------------------------------------------------------
# Verification receipts -- unsealed, self-reported, appendable
# ---------------------------------------------------------------------------

#: Rides on every receipt so the caveat cannot be lost by someone reading the
#: JSON without the docs. Short on purpose: it has to survive being pasted.
RECEIPT_DISCLAIMER = (
    "Self-reported log line: someone's copy of a tool said this passed on "
    "this date. It sits outside the sha256 seal, nothing signs it, and it "
    "proves nothing on its own."
)


def build_verification_receipt(
    endpoint_used: str, results: list, summary: object,
) -> dict:
    """A receipt recording that an online check was run, and what it said.

    Two-year framing: a Testnet reset destroys the ability to re-check a txid
    directly, and a pack that outlives its network degrades to a hash and a
    dead link. A pack that accumulates a few dated receipts over its life --
    run at completion, run again a year later by a facilitator -- is
    meaningfully better secondary evidence than a bare hash.

    It is still not evidence in the cryptographic sense and this module never
    lets it read as such: no count is surfaced as a score, nothing "levels
    up" with more receipts, and RECEIPT_DISCLAIMER travels inside every entry.
    A verification log that started implying reputation would be exactly the
    unfounded-authority claim this product spent its health pass removing.
    """
    summary = summary if isinstance(summary, dict) else {}
    lessons = []
    for r in results or []:
        if not isinstance(r, dict):
            continue
        lessons.append({
            "lesson": r.get("lesson", 0),
            "status": r.get("status", ""),
            "ledger_index_seen": r.get("ledger_index_seen", 0),
        })
    return {
        "verified_at": datetime.now(UTC).isoformat(),
        "tool_version": _tool_version(),
        "endpoint_used": endpoint_used,
        "status": summary.get("status", ""),
        "lessons": lessons,
        "self_reported": True,
        "note": RECEIPT_DISCLAIMER,
    }


def record_verification(pack: dict, receipt: dict) -> dict:
    """Append `receipt` to `pack["verifications"]`. Returns the same pack.

    Mutates and returns `pack` so a caller can save it straight back. The
    existing `sha256` stays VALID and is not recomputed: `verifications` is in
    UNSEALED_FIELDS precisely so a receipt can be added years later without
    the original generator, and without breaking the seal that protects
    everything else.

    A pack whose hash does not verify should never be given a receipt --
    appending "someone checked this" to a tampered file is the one way this
    feature could actively mislead. Callers must gate on verify_proof_pack
    first; cli.py's --online path does.
    """
    receipts = pack.get("verifications")
    if not isinstance(receipts, list):
        receipts = []
    receipts.append(receipt)
    pack["verifications"] = receipts
    return pack


# ---------------------------------------------------------------------------
# Batch composition -- a facilitator with 30 packs on a lab machine
# ---------------------------------------------------------------------------


def batch_summary(rows: list) -> dict:
    """Roll up many packs into one answer for someone marking a workshop.

    Each row is what cli.py already computed for one file:

        {"file": str, "address": str, "hash_ok": bool,
         "online": <summarize_online() dict> | None}

    The point of a batch is a facilitator who needs to know WHICH of thirty
    files need a human, not a wall of thirty verdicts. So the rollup leads
    with the exceptions: `needs_attention` holds every file that is not a
    clean pass, in file order, each with the one-line reason it is there.

    "Everything else passed" is a fine thing to print in one line. "Two of
    these thirty disagree with the ledger and here they are" is the thing
    nobody should have to grep for.
    """
    rows = [r for r in (rows or []) if isinstance(r, dict)]
    needs_attention: list[dict] = []
    passed = 0
    for row in rows:
        online = row.get("online")
        online_status = (
            str(online.get("status", "")) if isinstance(online, dict) else ""
        )
        if not row.get("hash_ok", False):
            reason = "hash does not match its own contents"
        elif online_status == SUMMARY_CONTRADICTED:
            reason = "the ledger contradicts this pack"
        elif online_status == SUMMARY_UNKNOWN:
            reason = "could not be checked against the ledger"
        elif online_status == SUMMARY_HISTORY_GONE:
            reason = "the network was reset; the ledger no longer holds this"
        else:
            passed += 1
            continue
        needs_attention.append({
            "file": row.get("file", ""),
            "address": row.get("address", ""),
            "reason": reason,
            "online_status": online_status,
            "hash_ok": bool(row.get("hash_ok", False)),
        })

    total = len(rows)
    if not total:
        message = "No proof packs were given to check."
    elif not needs_attention:
        message = f"All {total} proof packs passed every check that was run."
    else:
        message = (
            f"{len(needs_attention)} of {total} proof packs need a look; "
            f"{passed} passed."
        )
    return {
        "total": total,
        "passed": passed,
        "needs_attention": needs_attention,
        "message": message,
    }
