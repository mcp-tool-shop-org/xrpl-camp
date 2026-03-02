"""Tests for XRPL Camp proof pack generation and verification."""

from __future__ import annotations

import json

from xrpl_camp.models import Session
from xrpl_camp.proof_pack import (
    PROOF_PACK_FILE,
    canonical_json,
    generate_proof_pack,
    proof_pack_has_seed,
    save_proof_pack,
    verify_proof_pack,
)


def _make_session() -> Session:
    """Build a session with completed lessons."""
    s = Session(started_at="2026-01-01T00:00:00Z", wallet_address="rCampAddress")
    s.mark_complete(1, "Mental Model")
    s.mark_complete(2, "Create Wallet")
    s.mark_complete(4, "Send Payment", txid="DEADBEEF1234")
    return s


# ---------------------------------------------------------------------------
# canonical_json
# ---------------------------------------------------------------------------


def test_canonical_json_sorted_keys():
    data = {"z": 1, "a": 2, "m": 3}
    result = canonical_json(data)
    # Verify keys appear in sorted order by checking "a" comes before "m" before "z"
    pos_a = result.index('"a"')
    pos_m = result.index('"m"')
    pos_z = result.index('"z"')
    assert pos_a < pos_m < pos_z


def test_canonical_json_trailing_newline():
    result = canonical_json({"key": "value"})
    assert result.endswith("\n")


def test_canonical_json_no_crlf():
    result = canonical_json({"nested": {"a": 1, "b": 2}})
    assert "\r\n" not in result


def test_canonical_json_deterministic():
    data = {"b": [1, 2, 3], "a": {"x": "y"}}
    assert canonical_json(data) == canonical_json(data)


# ---------------------------------------------------------------------------
# generate_proof_pack
# ---------------------------------------------------------------------------


def test_proof_pack_schema():
    pack = generate_proof_pack(_make_session())
    assert pack["schema"] == "xrpl-camp-proof-pack-v1"


def test_proof_pack_address():
    pack = generate_proof_pack(_make_session())
    assert pack["address"] == "rCampAddress"


def test_proof_pack_network():
    pack = generate_proof_pack(_make_session())
    assert pack["network"] == "testnet"


def test_proof_pack_tool_version():
    from xrpl_camp import __version__

    pack = generate_proof_pack(_make_session())
    assert pack["tool_version"] == __version__


def test_proof_pack_lessons_count():
    pack = generate_proof_pack(_make_session())
    assert len(pack["lessons"]) == 3


def test_proof_pack_lesson_explorer_url():
    pack = generate_proof_pack(_make_session())
    lesson_4 = [entry for entry in pack["lessons"] if entry["lesson"] == 4][0]
    assert "explorer_url" in lesson_4
    assert "DEADBEEF1234" in lesson_4["explorer_url"]


def test_proof_pack_lesson_no_explorer_without_txid():
    pack = generate_proof_pack(_make_session())
    lesson_1 = [entry for entry in pack["lessons"] if entry["lesson"] == 1][0]
    assert "explorer_url" not in lesson_1
    assert "txid" not in lesson_1


def test_proof_pack_sha256_present():
    pack = generate_proof_pack(_make_session())
    assert "sha256" in pack


def test_proof_pack_sha256_format():
    pack = generate_proof_pack(_make_session())
    assert pack["sha256"].startswith("sha256:")
    hex_part = pack["sha256"].split(":")[1]
    assert len(hex_part) == 64  # SHA-256 hex length


# ---------------------------------------------------------------------------
# verify_proof_pack
# ---------------------------------------------------------------------------


def test_verify_valid_pack():
    pack = generate_proof_pack(_make_session())
    valid, msg = verify_proof_pack(pack)
    assert valid is True
    assert "verified" in msg.lower()


def test_verify_tampered_pack():
    pack = generate_proof_pack(_make_session())
    pack["address"] = "rTampered"
    valid, msg = verify_proof_pack(pack)
    assert valid is False
    assert "mismatch" in msg.lower()


def test_verify_missing_hash():
    pack = generate_proof_pack(_make_session())
    del pack["sha256"]
    valid, msg = verify_proof_pack(pack)
    assert valid is False
    assert "no sha256" in msg.lower()


# ---------------------------------------------------------------------------
# save_proof_pack
# ---------------------------------------------------------------------------


def test_save_proof_pack_file(tmp_path):
    pack = generate_proof_pack(_make_session())
    filepath = save_proof_pack(pack, str(tmp_path / "proof.json"))
    assert filepath.exists()

    loaded = json.loads(filepath.read_text(encoding="utf-8"))
    assert loaded["schema"] == "xrpl-camp-proof-pack-v1"

    # Verify the saved file passes integrity check
    valid, _ = verify_proof_pack(loaded)
    assert valid


def test_save_proof_pack_default_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    pack = generate_proof_pack(_make_session())
    filepath = save_proof_pack(pack)
    assert filepath.name == PROOF_PACK_FILE


# ---------------------------------------------------------------------------
# Safety
# ---------------------------------------------------------------------------


def test_proof_pack_no_seed():
    pack = generate_proof_pack(_make_session())
    assert not proof_pack_has_seed(pack)


def test_proof_pack_seed_detection():
    fake = {"seed": "sEdXXXXXX", "data": "other"}
    assert proof_pack_has_seed(fake)
