"""Tests for XRPL Camp certificate generation."""

from __future__ import annotations

import json

from xrpl_camp.certificate import (
    CERTIFICATE_FILE,
    certificate_has_seed,
    generate_certificate,
    save_certificate,
)
from xrpl_camp.models import Session


def _make_session() -> Session:
    """Build a session with some completed lessons."""
    s = Session(started_at="2026-01-01T00:00:00Z", wallet_address="rCampAddress")
    s.mark_complete(1, "Mental Model")
    s.mark_complete(2, "Create Wallet")
    s.mark_complete(4, "Send Payment", txid="DEADBEEF1234")
    return s


# ---------------------------------------------------------------------------
# generate_certificate
# ---------------------------------------------------------------------------


def test_certificate_schema():
    cert = generate_certificate(_make_session())
    assert cert["schema"] == "xrpl-camp-certificate-v1"


def test_certificate_network():
    cert = generate_certificate(_make_session())
    assert cert["network"] == "testnet"


def test_certificate_address():
    cert = generate_certificate(_make_session())
    assert cert["address"] == "rCampAddress"


def test_certificate_completed_count():
    cert = generate_certificate(_make_session())
    assert len(cert["completed"]) == 3


def test_certificate_includes_txid():
    cert = generate_certificate(_make_session())
    lesson_4 = [c for c in cert["completed"] if c["lesson"] == 4][0]
    assert lesson_4["txid"] == "DEADBEEF1234"


def test_certificate_no_txid_for_offline_lesson():
    cert = generate_certificate(_make_session())
    lesson_1 = [c for c in cert["completed"] if c["lesson"] == 1][0]
    assert "txid" not in lesson_1


def test_certificate_issued_at():
    cert = generate_certificate(_make_session())
    assert "issued_at" in cert
    assert cert["issued_at"]  # non-empty


def test_certificate_required_fields():
    cert = generate_certificate(_make_session())
    assert set(cert.keys()) == {
        "schema", "network", "address", "completed", "issued_at",
    }


# ---------------------------------------------------------------------------
# No seed leakage
# ---------------------------------------------------------------------------


def test_no_seed_in_certificate():
    cert = generate_certificate(_make_session())
    assert not certificate_has_seed(cert)


def test_seed_detection_catches_seed():
    fake = {"seed": "sEdXXXXXX", "data": "other"}
    assert certificate_has_seed(fake)


def test_seed_detection_catches_sEd_in_values():
    fake = {"note": "my sEd12345 is here"}
    assert certificate_has_seed(fake)


# ---------------------------------------------------------------------------
# save_certificate
# ---------------------------------------------------------------------------


def test_save_certificate_creates_file(tmp_path):
    cert = generate_certificate(_make_session())
    filepath = save_certificate(cert, str(tmp_path / "cert.json"))
    assert filepath.exists()

    loaded = json.loads(filepath.read_text(encoding="utf-8"))
    assert loaded["schema"] == "xrpl-camp-certificate-v1"
    assert loaded["address"] == "rCampAddress"


def test_save_certificate_default_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cert = generate_certificate(_make_session())
    filepath = save_certificate(cert)
    assert filepath.name == CERTIFICATE_FILE


# ---------------------------------------------------------------------------
# Empty session
# ---------------------------------------------------------------------------


def test_certificate_empty_session():
    s = Session()
    cert = generate_certificate(s)
    assert cert["completed"] == []
    assert cert["address"] == ""
    assert not certificate_has_seed(cert)
