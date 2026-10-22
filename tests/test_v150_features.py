"""Tests for xrpl-camp 1.5.0 features (issue #14):
- `xrpl-camp reserve`
- `xrpl-camp certificate --format json|text` and share block
- `xrpl-camp proof verify <file> --online --record`
"""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from tests.helpers import strip_ansi
from xrpl_camp import lessons, transport, wallet
from xrpl_camp.certificate import (
    CERTIFICATE_FILE,
    CERTIFICATE_TEXT_FILE,
    SeedLeakDetected,
    generate_certificate,
    save_certificate_text,
    share_text,
)
from xrpl_camp.cli import app
from xrpl_camp.models import Session
from xrpl_camp.proof_pack import (
    PROOF_PACK_FILE,
    RECEIPT_DISCLAIMER,
    generate_proof_pack,
    save_proof_pack,
    verify_proof_pack,
)

runner = CliRunner()

SENDER = "rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh"
TXID = "E" * 64
MINT_TXID = "A" * 64
BURN_TXID = "B" * 64
LEFTOVER_TXID = "C" * 64
NFTOKEN_ID = "00080000" + "1" * 56
LEFTOVER_NFTOKEN_ID = "00080000" + "2" * 56


def _completed_session() -> Session:
    s = Session(started_at="2026-10-22T00:00:00+00:00", wallet_address=SENDER)
    for n in range(1, 6):
        s.mark_complete(
            n,
            lessons.LESSON_NAMES[n],
            txid=TXID if n == 4 else "",
            memo="XRPLCAMP|L4|hello" if n == 4 else "",
            ledger_index=12345 if n in (4, 5) else 0,
            close_time_iso="2026-10-22T00:01:00Z" if n in (4, 5) else "",
            duration_seconds=2.0,
        )
    return s


def _sample_moves() -> tuple[transport.ReserveMove, transport.ReserveMove]:
    mint_move = transport.ReserveMove(
        txid=MINT_TXID,
        engine_result="tesSUCCESS",
        owner_count_before=0,
        owner_count_after=1,
        balance_before=100_000_000,
        balance_after=99_999_988,
        spendable_before=99_000_000,
        spendable_after=98_799_988,
        ledger_index=50001,
        close_time_iso="2026-10-22T12:00:00Z",
        nftoken_id=NFTOKEN_ID,
    )
    burn_move = transport.ReserveMove(
        txid=BURN_TXID,
        engine_result="tesSUCCESS",
        owner_count_before=1,
        owner_count_after=0,
        balance_before=99_999_988,
        balance_after=99_999_976,
        spendable_before=98_799_988,
        spendable_after=98_999_976,
        ledger_index=50002,
        close_time_iso="2026-10-22T12:00:04Z",
        nftoken_id=NFTOKEN_ID,
    )
    return mint_move, burn_move


# ---------------------------------------------------------------------------
# 1. `xrpl-camp reserve`
# ---------------------------------------------------------------------------


def test_reserve_mints_then_burns_and_displays_reserve_move_deltas(monkeypatch):
    wallet.save_wallet(SENDER, "sEdV150ReserveTestSeed123456789")
    mint_move, burn_move = _sample_moves()
    calls: list[tuple[str, object]] = []

    monkeypatch.setattr(transport, "assert_safe_network", lambda url=None: 1)
    monkeypatch.setattr(
        transport,
        "account_nfts",
        lambda address, url=None: (calls.append(("account_nfts", address)) or []),
    )

    def fake_mint(seed, uri="xrpl-camp", url=None, *, taxon=0):
        calls.append(("mint_nft", (uri, taxon)))
        return mint_move

    def fake_burn(seed, nftoken_id, url=None):
        calls.append(("burn_nft", nftoken_id))
        return burn_move

    monkeypatch.setattr(transport, "mint_nft", fake_mint)
    monkeypatch.setattr(transport, "burn_nft", fake_burn)

    result = runner.invoke(app, ["reserve"])
    output = strip_ansi(result.output)

    assert result.exit_code == 0, output
    assert [c[0] for c in calls] == ["account_nfts", "mint_nft", "burn_nft"]
    assert calls[1][1] == ("xrpl-camp", 0)
    assert calls[2][1] == NFTOKEN_ID

    # Mint step appears before burn step, and deltas come from ReserveMove values.
    mint_pos = output.index("Step 1: Mint NFT")
    burn_pos = output.index("Step 2: Burn NFT")
    assert mint_pos < burn_pos

    assert "-12 drops" in output
    assert "-200,012 drops" in output
    assert "+199,988 drops" in output
    assert "200,000 drops (0.200000 XRP) locked" in output
    assert "200,000 drops (0.200000 XRP) released" in output
    assert MINT_TXID in output
    assert BURN_TXID in output


def test_reserve_burns_leftover_xrpl_camp_nft_before_new_mint(monkeypatch):
    wallet.save_wallet(SENDER, "sEdV150ReserveTestSeed123456789")
    mint_move, burn_move = _sample_moves()
    leftover_move = transport.ReserveMove(
        txid=LEFTOVER_TXID,
        engine_result="tesSUCCESS",
        owner_count_before=1,
        owner_count_after=0,
        balance_before=100_000_010,
        balance_after=100_000_000,
        spendable_before=98_800_010,
        spendable_after=99_000_000,
        nftoken_id=LEFTOVER_NFTOKEN_ID,
    )
    events: list[tuple[str, str]] = []

    monkeypatch.setattr(transport, "assert_safe_network", lambda url=None: 1)
    monkeypatch.setattr(
        transport,
        "account_nfts",
        lambda address, url=None: [
            # Unrelated NFT (different URI/taxon) must be ignored.
            {"NFTokenID": "00080000" + "9" * 56, "URI": "other", "NFTokenTaxon": 1},
            # Leftover xrpl-camp NFT (hex-encoded 'xrpl-camp', taxon 0).
            {
                "NFTokenID": LEFTOVER_NFTOKEN_ID,
                "URI": "7872706C2D63616D70",
                "NFTokenTaxon": 0,
            },
        ],
    )

    def fake_mint(seed, uri="xrpl-camp", url=None, *, taxon=0):
        events.append(("mint", NFTOKEN_ID))
        return mint_move

    def fake_burn(seed, nftoken_id, url=None):
        events.append(("burn", nftoken_id))
        return leftover_move if nftoken_id == LEFTOVER_NFTOKEN_ID else burn_move

    monkeypatch.setattr(transport, "mint_nft", fake_mint)
    monkeypatch.setattr(transport, "burn_nft", fake_burn)

    result = runner.invoke(app, ["reserve"])
    output = strip_ansi(result.output)

    assert result.exit_code == 0, output
    assert events == [
        ("burn", LEFTOVER_NFTOKEN_ID),
        ("mint", NFTOKEN_ID),
        ("burn", NFTOKEN_ID),
    ]
    assert LEFTOVER_NFTOKEN_ID in output
    assert "earlier reserve run" in output


def test_reserve_burn_failure_exits_nonzero_and_names_nftoken_id(monkeypatch):
    wallet.save_wallet(SENDER, "sEdV150ReserveTestSeed123456789")
    mint_move, _ = _sample_moves()

    monkeypatch.setattr(transport, "assert_safe_network", lambda url=None: 1)
    monkeypatch.setattr(transport, "account_nfts", lambda address, url=None: [])
    monkeypatch.setattr(
        transport, "mint_nft", lambda seed, uri="xrpl-camp", url=None, *, taxon=0: mint_move,
    )

    def failing_burn(seed, nftoken_id, url=None):
        raise transport.XRPLTransactionFailed("tefMAX_LEDGER")

    monkeypatch.setattr(transport, "burn_nft", failing_burn)

    result = runner.invoke(app, ["reserve"])
    output = strip_ansi(result.output)

    assert result.exit_code != 0
    assert NFTOKEN_ID in output
    assert "xrpl-camp reserve" in output


def test_reserve_dry_run_makes_no_network_calls(tmp_path):
    """The conftest `no_network` guard fails this test if any socket opens."""
    result = runner.invoke(app, ["reserve", "--dry-run"])
    output = strip_ansi(result.output)

    assert result.exit_code == 0, output
    assert list(tmp_path.iterdir()) == []
    assert "DRY RUN" in output
    assert "simulated" in output.lower()
    assert "200,000 drops" in output
    assert "-10 drops" in output


def test_reserve_unfunded_wallet_exits_user_error_with_fund_hint(monkeypatch):
    wallet.save_wallet(SENDER, "sEdV150ReserveTestSeed123456789")

    monkeypatch.setattr(transport, "assert_safe_network", lambda url=None: 1)
    monkeypatch.setattr(transport, "account_nfts", lambda address, url=None: [])

    def unfunded_mint(seed, uri="xrpl-camp", url=None, *, taxon=0):
        raise transport.XRPLUnfundedAccount("This account has no spendable XRP.")

    monkeypatch.setattr(transport, "mint_nft", unfunded_mint)

    result = runner.invoke(app, ["reserve"])
    output = strip_ansi(result.output)

    assert result.exit_code == 1, output
    assert "NET_UNFUNDED" in output
    assert "xrpl-camp fund" in output


def test_reserve_without_wallet_fails_with_wallet_missing_error():
    result = runner.invoke(app, ["reserve"])
    output = strip_ansi(result.output)

    assert result.exit_code == 1
    assert "WALLET_MISSING" in output


def test_reserve_json_prints_one_document(monkeypatch, capsys):
    wallet.save_wallet(SENDER, "sEdV150ReserveTestSeed123456789")
    mint_move, burn_move = _sample_moves()

    monkeypatch.setattr(transport, "assert_safe_network", lambda url=None: 1)
    monkeypatch.setattr(transport, "account_nfts", lambda address, url=None: [])
    monkeypatch.setattr(
        transport, "mint_nft", lambda seed, uri="xrpl-camp", url=None, *, taxon=0: mint_move,
    )
    monkeypatch.setattr(
        transport, "burn_nft", lambda seed, nftoken_id, url=None: burn_move,
    )

    code = lessons.run_reserve(json_output=True)
    captured = capsys.readouterr()

    assert code == 0
    doc = json.loads(captured.out)
    assert doc["simulated"] is False
    assert doc["address"] == SENDER
    assert len(doc["moves"]) == 2
    assert doc["mint"]["txid"] == MINT_TXID
    assert doc["mint"]["reserve_delta"] == 200_000
    assert doc["mint"]["reserve_status"] == "locked"
    assert doc["burn"]["txid"] == BURN_TXID
    assert doc["burn"]["reserve_delta"] == -200_000
    assert doc["burn"]["reserve_status"] == "released"
    assert doc["net_reserve_delta"] == 0
    assert doc["net_balance_delta"] == -24
    # Progress went to stderr, not stdout.
    assert "Step 1" in captured.err


# ---------------------------------------------------------------------------
# 2. `certificate --format json|text` and the share line
# ---------------------------------------------------------------------------


def test_certificate_format_text_writes_txt_beside_json_and_is_not_json(tmp_path):
    s = _completed_session()
    s.save()
    out_dir = tmp_path / "out"

    result = runner.invoke(
        app, ["certificate", "--format", "text", "--out", str(out_dir)],
    )
    output = strip_ansi(result.output)

    assert result.exit_code == 0, output
    cert_json = out_dir / CERTIFICATE_FILE
    pack_json = out_dir / PROOF_PACK_FILE
    cert_txt = out_dir / CERTIFICATE_TEXT_FILE

    assert cert_json.exists()
    assert pack_json.exists()
    assert cert_txt.exists()

    # The JSON certificate parses as JSON; the .txt keepsake does NOT.
    parsed_cert = json.loads(cert_json.read_text(encoding="utf-8"))
    assert parsed_cert["address"] == SENDER
    txt_body = cert_txt.read_text(encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        json.loads(txt_body)
    assert "XRPL Camp" in txt_body
    assert SENDER in txt_body
    assert "XRPLCAMP|L4|hello" in txt_body

    # Running a second time creates a unique .bak backup for the .txt file too.
    second = runner.invoke(
        app, ["certificate", "--format", "text", "--out", str(out_dir)],
    )
    assert second.exit_code == 0
    txt_backups = list(out_dir.glob(f"{CERTIFICATE_TEXT_FILE}.*.bak"))
    assert len(txt_backups) == 1


def test_seed_in_memo_blocks_certificate_text_write(tmp_path):
    from xrpl.wallet import Wallet

    real_seed = Wallet.create().seed
    s = _completed_session()
    for p in s.progress:
        if p.lesson == 4:
            p.memo = f"leaked {real_seed}"
    cert = generate_certificate(s)

    target_txt = tmp_path / CERTIFICATE_TEXT_FILE
    with pytest.raises(SeedLeakDetected):
        save_certificate_text(cert, str(target_txt))
    assert not target_txt.exists()

    # Also via the CLI command with --format text.
    s.save()
    result = runner.invoke(app, ["certificate", "--format", "text"])
    assert result.exit_code != 0
    assert not (tmp_path / CERTIFICATE_FILE).exists()
    assert not (tmp_path / CERTIFICATE_TEXT_FILE).exists()


def test_share_line_printed_after_certificate_and_after_lesson_6(tmp_path):
    s = _completed_session()
    s.save()

    result = runner.invoke(app, ["certificate"])
    output = strip_ansi(result.output)
    assert result.exit_code == 0, output

    cert = json.loads((tmp_path / CERTIFICATE_FILE).read_text(encoding="utf-8"))
    expected_share = share_text(cert)
    for line in expected_share.splitlines():
        assert line in output

    # Also check direct lesson_6_certificate call (used by `start`).
    s2 = _completed_session()
    with lessons.console.capture() as cap:
        res = lessons.lesson_6_certificate(s2)
    assert res.ok is True
    captured = strip_ansi(cap.get())
    for line in expected_share.splitlines():
        assert line in captured


def test_certificate_dry_run_writes_nothing_and_prints_no_share_line(tmp_path):
    s = _completed_session()
    with lessons.console.capture() as cap:
        res = lessons.lesson_6_certificate(s, dry_run=True, fmt="text")
    output = strip_ansi(cap.get())

    assert res.ok is True
    assert list(tmp_path.iterdir()) == []
    assert "Nothing was written" in output
    assert "Copy to share" not in output
    assert "Check the record yourself:" not in output


# ---------------------------------------------------------------------------
# 3. `proof verify <file> --online --record`
# ---------------------------------------------------------------------------


def _write_valid_pack(tmp_path) -> tuple[ dict, object ]:
    s = _completed_session()
    pack = generate_proof_pack(s)
    path = save_proof_pack(pack, str(tmp_path / PROOF_PACK_FILE))
    return pack, path


def _mock_online_lookup_ok(monkeypatch):
    monkeypatch.setattr(
        transport,
        "lookup_tx",
        lambda txid, url=None, dry_run=False, *, recorded_ledger_index=0: {
            "found": True,
            "hash": txid,
            "account": SENDER,
            "destination": "rMailbox",
            "amount": "1000000",
            "delivered": "1000000",
            "fee": "10",
            "memo": "XRPLCAMP|L4|hello",
            "ledger_index": 12345,
            "close_time_iso": "2026-10-22T00:01:00Z",
            "result": "tesSUCCESS",
            "validated": True,
        },
    )


def test_tampered_pack_with_record_is_refused_and_bytes_unchanged(
    tmp_path, monkeypatch,
):
    _mock_online_lookup_ok(monkeypatch)
    pack, path = _write_valid_pack(tmp_path)
    pack["address"] = "rTamperedAddress"
    path.write_text(json.dumps(pack, indent=2), encoding="utf-8")
    before = path.read_bytes()

    result = runner.invoke(
        app, ["proof", "verify", str(path), "--online", "--record"],
    )

    assert result.exit_code == 1
    assert path.read_bytes() == before


def test_valid_pack_with_record_gains_one_receipt_and_keeps_sha256(
    tmp_path, monkeypatch,
):
    _mock_online_lookup_ok(monkeypatch)
    pack, path = _write_valid_pack(tmp_path)
    original_sha = pack["sha256"]

    result = runner.invoke(
        app, ["proof", "verify", str(path), "--online", "--record"],
    )
    output = " ".join(strip_ansi(result.output).split())

    assert result.exit_code == 0, output
    assert "Verification receipt added" in output
    assert "1 receipt" in output

    reloaded = json.loads(path.read_text(encoding="utf-8"))
    assert reloaded["sha256"] == original_sha
    assert len(reloaded["verifications"]) == 1
    receipt = reloaded["verifications"][0]
    assert receipt["status"] == "confirmed"
    assert receipt["self_reported"] is True
    assert receipt["note"] == RECEIPT_DISCLAIMER

    ok, _msg = verify_proof_pack(reloaded)
    assert ok is True


def test_second_record_appends_second_receipt(tmp_path, monkeypatch):
    _mock_online_lookup_ok(monkeypatch)
    pack, path = _write_valid_pack(tmp_path)
    original_sha = pack["sha256"]

    first = runner.invoke(
        app, ["proof", "verify", str(path), "--online", "--record"],
    )
    assert first.exit_code == 0

    second = runner.invoke(
        app, ["proof", "verify", str(path), "--online", "--record", "--json"],
    )
    assert second.exit_code == 0, second.output
    doc = json.loads(second.stdout)
    assert doc["recorded"] is True
    assert doc["valid"] is True

    reloaded = json.loads(path.read_text(encoding="utf-8"))
    assert reloaded["sha256"] == original_sha
    assert len(reloaded["verifications"]) == 2
    ok, _msg = verify_proof_pack(reloaded)
    assert ok is True


def test_record_refusals_folder_without_online_and_dry_run(tmp_path, monkeypatch):
    _mock_online_lookup_ok(monkeypatch)
    _pack, path = _write_valid_pack(tmp_path)
    before = path.read_bytes()

    # 1. Folder + --record is refused (exit 1 with hint).
    r_folder = runner.invoke(
        app, ["proof", "verify", str(tmp_path), "--online", "--record"],
    )
    assert r_folder.exit_code == 1
    assert "RECORD_FOLDER_UNSUPPORTED" in strip_ansi(r_folder.output)
    assert "--record" in strip_ansi(r_folder.output)

    # 2. --record without --online is refused (exit 1 with hint).
    r_no_online = runner.invoke(
        app, ["proof", "verify", str(path), "--record"],
    )
    assert r_no_online.exit_code == 1
    assert "RECORD_REQUIRES_ONLINE" in strip_ansi(r_no_online.output)
    assert "--online" in strip_ansi(r_no_online.output)

    # 3. --dry-run + --record is refused (exit 1 with hint).
    r_dry = runner.invoke(
        app, ["--dry-run", "proof", "verify", str(path), "--online", "--record"],
    )
    assert r_dry.exit_code == 1
    assert "RECORD_DRY_RUN" in strip_ansi(r_dry.output)
    assert "--dry-run" in strip_ansi(r_dry.output)

    # None of the three touched the file.
    assert path.read_bytes() == before
