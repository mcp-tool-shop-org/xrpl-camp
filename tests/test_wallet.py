"""Tests for XRPL Camp wallet module (no network calls)."""

from __future__ import annotations

import json

from xrpl_camp.wallet import create_wallet, load_wallet, save_wallet, wallet_exists


def test_create_wallet_returns_tuple():
    address, seed = create_wallet()
    assert isinstance(address, str)
    assert isinstance(seed, str)
    assert address.startswith("r")  # XRPL addresses start with 'r'
    assert len(address) > 20


def test_create_wallet_unique():
    a1, s1 = create_wallet()
    a2, s2 = create_wallet()
    assert a1 != a2
    assert s1 != s2


def test_save_and_load_wallet(tmp_path, monkeypatch):
    monkeypatch.setattr("xrpl_camp.models.STATE_DIR", tmp_path)
    monkeypatch.setattr("xrpl_camp.models.WALLET_FILE", tmp_path / "wallet.json")
    monkeypatch.setattr("xrpl_camp.wallet.STATE_DIR", tmp_path)
    monkeypatch.setattr("xrpl_camp.wallet.WALLET_FILE", tmp_path / "wallet.json")

    save_wallet("rTestAddress", "sEdTestSeed")
    w = load_wallet()

    assert w is not None
    assert w["address"] == "rTestAddress"
    assert w["seed"] == "sEdTestSeed"
    assert w["network"] == "testnet"
    assert "created_at" in w


def test_load_wallet_returns_none_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("xrpl_camp.wallet.WALLET_FILE", tmp_path / "nope.json")
    assert load_wallet() is None


def test_wallet_exists_false(tmp_path, monkeypatch):
    monkeypatch.setattr("xrpl_camp.wallet.WALLET_FILE", tmp_path / "nope.json")
    assert not wallet_exists()


def test_wallet_exists_true(tmp_path, monkeypatch):
    monkeypatch.setattr("xrpl_camp.models.STATE_DIR", tmp_path)
    monkeypatch.setattr("xrpl_camp.models.WALLET_FILE", tmp_path / "wallet.json")
    monkeypatch.setattr("xrpl_camp.wallet.STATE_DIR", tmp_path)
    monkeypatch.setattr("xrpl_camp.wallet.WALLET_FILE", tmp_path / "wallet.json")

    save_wallet("rAddr", "sSeed")
    assert wallet_exists()


def test_save_wallet_creates_directory(tmp_path, monkeypatch):
    sub = tmp_path / "sub" / "dir"
    monkeypatch.setattr("xrpl_camp.wallet.STATE_DIR", sub)
    monkeypatch.setattr("xrpl_camp.wallet.WALLET_FILE", sub / "wallet.json")

    path = save_wallet("rAddr", "sSeed")
    assert path.exists()
    assert sub.exists()


def test_wallet_json_no_extra_fields(tmp_path, monkeypatch):
    """Wallet JSON should only contain expected fields."""
    monkeypatch.setattr("xrpl_camp.wallet.STATE_DIR", tmp_path)
    monkeypatch.setattr("xrpl_camp.wallet.WALLET_FILE", tmp_path / "wallet.json")

    save_wallet("rAddr", "sSeed")
    data = json.loads((tmp_path / "wallet.json").read_text(encoding="utf-8"))
    assert set(data.keys()) == {"address", "seed", "network", "created_at"}
