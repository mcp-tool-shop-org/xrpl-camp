"""Tests for xrpl-camp 1.5.2 fixes:
- #20.1: `_submit_signed` resolves an empty `TransactionResult` by hash lookup
- #20.2: `reserve --json` includes `reserve_measured` and clear human note on `not_yet_visible`
- #17: `proof verify --online --json` mode-matched `message`, `online.checked` count,
  and POSIX `file` path
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.helpers import make_response, strip_ansi
from xrpl_camp import lessons, transport, wallet
from xrpl_camp.cli import app
from xrpl_camp.models import Session
from xrpl_camp.proof_pack import (
    PROOF_PACK_FILE,
    generate_proof_pack,
    save_proof_pack,
)

runner = CliRunner()

SENDER = "rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh"
TXID = "E" * 64
MINT_TXID = "A" * 64
BURN_TXID = "B" * 64
NFTOKEN_ID = "00080000" + "1" * 56


def _stub_submit_without_tx_result(monkeypatch, *, presign_ok: bool = True):
    """Stub `autofill_and_sign` and `submit_and_wait` so `submit_and_wait` returns
    a response whose `meta` has NO `TransactionResult`."""
    import xrpl.clients
    import xrpl.transaction
    from xrpl.models import NFTokenMint

    class DummyClient:
        def __init__(self, url: str) -> None:
            self.url = url

    monkeypatch.setattr(xrpl.clients, "JsonRpcClient", DummyClient)
    monkeypatch.setattr(transport, "assert_safe_network", lambda url=None: None)

    signed_state: dict[str, object] = {"txid": "", "last_ledger": 0}

    if presign_ok:

        def fake_autofill(tx, client, w, **kwargs):
            filled = NFTokenMint.from_dict(
                {
                    **tx.to_dict(),
                    "fee": "10",
                    "sequence": 7,
                    "last_ledger_sequence": 910,
                }
            )
            signed = xrpl.transaction.sign(filled, w)
            signed_state["txid"] = str(signed.get_hash())
            signed_state["last_ledger"] = 910
            return signed

    else:

        def fake_autofill(tx, client, w, **kwargs):
            raise RuntimeError("pre-sign autofill failed")

    monkeypatch.setattr(xrpl.transaction, "autofill_and_sign", fake_autofill)
    monkeypatch.setattr(
        xrpl.transaction,
        "submit_and_wait",
        lambda tx, client, w, **kwargs: make_response({"meta": {}}),
    )
    return signed_state


# ---------------------------------------------------------------------------
# 1. #20.1: `_submit_signed` must never treat an empty TransactionResult as success
# ---------------------------------------------------------------------------


def test_submit_signed_empty_result_resolves_validated_tes_success_via_lookup(
    monkeypatch,
):
    from xrpl.models import NFTokenMint
    from xrpl.wallet import Wallet

    w = Wallet.create()
    signed_state = _stub_submit_without_tx_result(monkeypatch, presign_ok=True)
    looked_up_hashes: list[str] = []

    def fake_fetch_tx(txid: str, url: str):
        looked_up_hashes.append(txid)
        payload = {
            "hash": txid,
            "validated": True,
            "ledger_index": 50001,
            "close_time_iso": "2026-10-23T00:00:00Z",
            "meta": {
                "TransactionResult": "tesSUCCESS",
                "nftoken_id": NFTOKEN_ID,
            },
        }
        return make_response(payload, successful=True), payload

    monkeypatch.setattr(transport, "_fetch_tx", fake_fetch_tx)

    tx = NFTokenMint(account=w.address, nftoken_taxon=0, uri=transport._to_hex("xrpl-camp"))
    result = transport._submit_signed(tx, w, transport.TESTNET_URL)

    assert looked_up_hashes == [signed_state["txid"]]
    assert result["validated"] is True
    assert result["hash"] == signed_state["txid"]
    assert transport._meta(result)["TransactionResult"] == "tesSUCCESS"
    assert transport._minted_nftoken_id(result) == NFTOKEN_ID


@pytest.mark.parametrize(
    ("code", "expected_exc"),
    [
        ("tecFAILED_PROCESSING", transport.XRPLTransactionFailed),
        ("tecNO_PERMISSION", transport.XRPLTransactionFailed),
        ("tecINSUFFICIENT_RESERVE", transport.XRPLUnfundedAccount),
    ],
)
def test_submit_signed_empty_result_raises_engine_failure_on_non_success_lookup(
    monkeypatch, code, expected_exc
):
    from xrpl.models import NFTokenMint
    from xrpl.wallet import Wallet

    w = Wallet.create()
    signed_state = _stub_submit_without_tx_result(monkeypatch, presign_ok=True)

    def fake_fetch_tx(txid: str, url: str):
        payload = {
            "hash": txid,
            "validated": True,
            "ledger_index": 50002,
            "meta": {"TransactionResult": code},
        }
        return make_response(payload, successful=True), payload

    monkeypatch.setattr(transport, "_fetch_tx", fake_fetch_tx)

    tx = NFTokenMint(account=w.address, nftoken_taxon=0, uri=transport._to_hex("xrpl-camp"))
    with pytest.raises(expected_exc) as exc_info:
        transport._submit_signed(tx, w, transport.TESTNET_URL)

    assert code in str(exc_info.value)
    assert str(signed_state["txid"]) in (exc_info.value.error.detail or "")


@pytest.mark.parametrize("lookup_kind", ["not_found", "unvalidated", "lookup_error"])
def test_submit_signed_empty_result_raises_unresolved_when_lookup_not_found_or_unvalidated(
    monkeypatch, lookup_kind
):
    from xrpl.models import NFTokenMint
    from xrpl.wallet import Wallet

    w = Wallet.create()
    signed_state = _stub_submit_without_tx_result(monkeypatch, presign_ok=True)

    def fake_fetch_tx(txid: str, url: str):
        if lookup_kind == "lookup_error":
            raise transport.XRPLConnectionError("connection dropped during lookup")
        if lookup_kind == "not_found":
            payload = {"error": "txnNotFound", "error_message": "Transaction not found."}
            return make_response(payload, successful=False), payload
        payload = {
            "hash": txid,
            "validated": False,
            "meta": {},
        }
        return make_response(payload, successful=True), payload

    monkeypatch.setattr(transport, "_fetch_tx", fake_fetch_tx)

    tx = NFTokenMint(account=w.address, nftoken_taxon=0, uri=transport._to_hex("xrpl-camp"))
    with pytest.raises(transport.XRPLSubmissionUnresolved) as exc_info:
        transport._submit_signed(tx, w, transport.TESTNET_URL)

    assert exc_info.value.txid == signed_state["txid"]
    assert exc_info.value.last_ledger == 910
    assert exc_info.value.error.retryable is False


def test_submit_signed_empty_result_with_no_hash_raises_unresolved(monkeypatch):
    from xrpl.models import NFTokenMint
    from xrpl.wallet import Wallet

    w = Wallet.create()
    _stub_submit_without_tx_result(monkeypatch, presign_ok=False)
    monkeypatch.setattr(
        transport,
        "_fetch_tx",
        lambda *a, **k: pytest.fail("_fetch_tx must not run when there is no hash"),
    )

    tx = NFTokenMint(account=w.address, nftoken_taxon=0, uri=transport._to_hex("xrpl-camp"))
    with pytest.raises(transport.XRPLSubmissionUnresolved) as exc_info:
        transport._submit_signed(tx, w, transport.TESTNET_URL)

    assert exc_info.value.txid == ""
    assert exc_info.value.error.retryable is False


def test_nft_submit_empty_result_lookup_not_found_with_hash_hint_names_nft_and_real_txid(
    monkeypatch,
):
    from xrpl.models import NFTokenMint
    from xrpl.wallet import Wallet

    w = Wallet.create()
    signed_state = _stub_submit_without_tx_result(monkeypatch, presign_ok=True)
    payload = {"error": "txnNotFound", "error_message": "Transaction not found."}
    monkeypatch.setattr(
        transport,
        "_fetch_tx",
        lambda txid, url: (make_response(payload, successful=False), payload),
    )

    tx = NFTokenMint(account=w.address, nftoken_taxon=0, uri=transport._to_hex("xrpl-camp"))
    with pytest.raises(transport.XRPLSubmissionUnresolved) as exc_info:
        transport._submit_signed(tx, w, transport.TESTNET_URL)

    hint = exc_info.value.error.hint
    real_txid = str(signed_state["txid"])
    assert real_txid
    assert "NFT" in hint
    assert "payment" not in hint.lower()
    assert "<hash>" not in hint
    assert f"xrpl-camp verify --tx {real_txid}" in hint


def test_nft_submit_empty_result_no_hash_hint_omits_verify_tx_and_mentions_explorer_or_account(
    monkeypatch,
):
    from xrpl.models import NFTokenMint
    from xrpl.wallet import Wallet

    w = Wallet.create()
    _stub_submit_without_tx_result(monkeypatch, presign_ok=False)
    monkeypatch.setattr(
        transport,
        "_fetch_tx",
        lambda *a, **k: pytest.fail("_fetch_tx must not run when there is no hash"),
    )

    tx = NFTokenMint(account=w.address, nftoken_taxon=0, uri=transport._to_hex("xrpl-camp"))
    with pytest.raises(transport.XRPLSubmissionUnresolved) as exc_info:
        transport._submit_signed(tx, w, transport.TESTNET_URL)

    hint = exc_info.value.error.hint
    assert "verify --tx" not in hint
    assert "<hash>" not in hint
    assert "payment" not in hint.lower()
    assert "NFT" in hint
    assert "explorer" in hint.lower()
    assert w.address in hint


def test_nft_submit_lapsed_window_during_reserve_mint_uses_nft_hint_with_txid(
    monkeypatch,
):
    import xrpl.clients
    import xrpl.transaction
    from xrpl.models import NFTokenMint
    from xrpl.wallet import Wallet

    w = Wallet.create()

    class DummyClient:
        def __init__(self, url: str) -> None:
            self.url = url

    monkeypatch.setattr(xrpl.clients, "JsonRpcClient", DummyClient)
    monkeypatch.setattr(transport, "assert_safe_network", lambda url=None: None)
    monkeypatch.setattr(
        transport,
        "_spendable_detail",
        lambda address, url=None, *, fee_drops=0: (
            99_000_000,
            True,
            transport.AccountSummary(100_000_000, 50000, 0, 7),
            1_000_000,
            200_000,
        ),
    )

    signed_txid: list[str] = []

    def fake_autofill(tx, client, wallet_arg, **kwargs):
        filled = NFTokenMint.from_dict(
            {
                **tx.to_dict(),
                "fee": "10",
                "sequence": 7,
                "last_ledger_sequence": 910,
            }
        )
        signed = xrpl.transaction.sign(filled, wallet_arg)
        signed_txid.append(str(signed.get_hash()))
        return signed

    def lapsed_submit(tx, client, wallet_arg, **kwargs):
        raise RuntimeError(
            "The latest validated ledger sequence 912 is greater than LastLedgerSequence 910."
        )

    payload = {"error": "txnNotFound", "error_message": "Transaction not found."}
    monkeypatch.setattr(xrpl.transaction, "autofill_and_sign", fake_autofill)
    monkeypatch.setattr(xrpl.transaction, "submit_and_wait", lapsed_submit)
    monkeypatch.setattr(
        transport,
        "_fetch_tx",
        lambda txid, url: (make_response(payload, successful=False), payload),
    )

    with pytest.raises(transport.XRPLSubmissionUnresolved) as exc_info:
        transport.mint_nft(w.seed, url=transport.TESTNET_URL)

    real_txid = signed_txid[0]
    hint = exc_info.value.error.hint
    assert "NFT" in hint
    assert "payment" not in hint.lower()
    assert "<hash>" not in hint
    assert f"xrpl-camp verify --tx {real_txid}" in hint
    assert exc_info.value.txid == real_txid
    assert exc_info.value.last_ledger == 910


def test_payment_lesson_unresolved_path_keeps_payment_wording(monkeypatch):
    import xrpl.clients
    import xrpl.transaction
    from xrpl.models import Payment
    from xrpl.wallet import Wallet

    sender = Wallet.create()
    dest = Wallet.create()

    class DummyClient:
        def __init__(self, url: str) -> None:
            self.url = url

    monkeypatch.setattr(xrpl.clients, "JsonRpcClient", DummyClient)
    monkeypatch.setattr(transport, "assert_safe_network", lambda url=None: None)
    monkeypatch.setattr(
        transport,
        "_spendable_detail",
        lambda address, url=None, *, fee_drops=0: (
            99_000_000,
            True,
            transport.AccountSummary(100_000_000, 50000, 0, 7),
            1_000_000,
            200_000,
        ),
    )

    def fake_autofill(tx, client, wallet_arg, **kwargs):
        filled = Payment.from_dict(
            {
                **tx.to_dict(),
                "fee": "10",
                "sequence": 7,
                "last_ledger_sequence": 910,
            }
        )
        return xrpl.transaction.sign(filled, wallet_arg)

    def lapsed_submit(tx, client, wallet_arg, **kwargs):
        raise RuntimeError(
            "The latest validated ledger sequence 912 is greater than LastLedgerSequence 910."
        )

    payload = {"error": "txnNotFound", "error_message": "Transaction not found."}
    monkeypatch.setattr(xrpl.transaction, "autofill_and_sign", fake_autofill)
    monkeypatch.setattr(xrpl.transaction, "submit_and_wait", lapsed_submit)
    monkeypatch.setattr(
        transport,
        "_fetch_tx",
        lambda txid, url: (make_response(payload, successful=False), payload),
    )

    with pytest.raises(transport.XRPLSubmissionUnresolved) as exc_info:
        transport.send_memo_payment(
            sender.seed,
            "hello",
            dest.address,
            url=transport.TESTNET_URL,
            amount_drops=1_000_000,
        )

    hint = exc_info.value.error.hint
    assert hint == transport.XRPLSubmissionUnresolved.default_hint
    assert "Do NOT send again — that would write a second payment." in hint
    # Also assert that NFT submission does NOT share the payment wording:
    assert "payment" in hint.lower()
    # And compare with _resolve_submitted_tx on an NFT submission to ensure they differ:
    with pytest.raises(transport.XRPLSubmissionUnresolved) as nft_exc:
        transport._resolve_submitted_tx(
            exc_info.value.txid, 910, transport.TESTNET_URL
        )
    assert "NFT" in nft_exc.value.error.hint
    assert "payment" not in nft_exc.value.error.hint.lower()


# ---------------------------------------------------------------------------
# 2. #20.2: `reserve --json` `reserve_measured` and human-readable note
# ---------------------------------------------------------------------------


def test_reserve_json_reports_reserve_measured_true_on_measured_path(
    monkeypatch, capsys
):
    wallet.save_wallet(SENDER, "sEdV150ReserveTestSeed123456789")
    mint_move = transport.ReserveMove(
        txid=MINT_TXID,
        engine_result="tesSUCCESS",
        owner_count_before=0,
        owner_count_after=1,
        balance_before=100_000_000,
        balance_after=99_999_990,
        spendable_before=99_000_000,
        spendable_after=98_799_990,
        ledger_index=50001,
        close_time_iso="2026-10-23T00:00:00Z",
        nftoken_id=NFTOKEN_ID,
    )
    burn_move = transport.ReserveMove(
        txid=BURN_TXID,
        engine_result="tesSUCCESS",
        owner_count_before=1,
        owner_count_after=0,
        balance_before=99_999_990,
        balance_after=99_999_980,
        spendable_before=98_799_990,
        spendable_after=98_999_980,
        ledger_index=50002,
        close_time_iso="2026-10-23T00:00:04Z",
        nftoken_id=NFTOKEN_ID,
    )

    monkeypatch.setattr(transport, "assert_safe_network", lambda url=None: 1)
    monkeypatch.setattr(transport, "account_nfts", lambda address, url=None: [])
    monkeypatch.setattr(
        transport, "mint_nft", lambda seed, uri="xrpl-camp", url=None, *, taxon=0: mint_move
    )
    monkeypatch.setattr(
        transport, "burn_nft", lambda seed, nftoken_id, url=None: burn_move
    )

    code = lessons.run_reserve(json_output=True)
    captured = capsys.readouterr()

    assert code == 0
    doc = json.loads(captured.out)
    assert doc["ok"] is True
    assert doc["reserve_measured"] is True
    assert "reserve_note" not in doc


def test_reserve_not_yet_visible_sets_reserve_measured_false_and_explains_plainly(
    monkeypatch, capsys
):
    wallet.save_wallet(SENDER, "sEdV150ReserveTestSeed123456789")
    stale_mint = transport.ReserveMove(
        txid=MINT_TXID,
        engine_result="tesSUCCESS",
        owner_count_before=0,
        owner_count_after=0,
        balance_before=100_000_000,
        balance_after=100_000_000,
        spendable_before=99_000_000,
        spendable_after=99_000_000,
        ledger_index=50001,
        close_time_iso="2026-10-23T00:00:00Z",
        nftoken_id=NFTOKEN_ID,
    )
    stale_burn = transport.ReserveMove(
        txid=BURN_TXID,
        engine_result="tesSUCCESS",
        owner_count_before=0,
        owner_count_after=0,
        balance_before=100_000_000,
        balance_after=100_000_000,
        spendable_before=99_000_000,
        spendable_after=99_000_000,
        ledger_index=50002,
        close_time_iso="2026-10-23T00:00:04Z",
        nftoken_id=NFTOKEN_ID,
    )

    monkeypatch.setattr(transport, "assert_safe_network", lambda url=None: 1)
    monkeypatch.setattr(transport, "account_nfts", lambda address, url=None: [])
    monkeypatch.setattr(
        transport, "mint_nft", lambda seed, uri="xrpl-camp", url=None, *, taxon=0: stale_mint
    )
    monkeypatch.setattr(
        transport, "burn_nft", lambda seed, nftoken_id, url=None: stale_burn
    )

    res = runner.invoke(app, ["reserve"])
    human = " ".join(strip_ansi(res.output).split())
    assert res.exit_code == 0, human
    assert "could not be measured this time" in human

    capsys.readouterr()
    code = lessons.run_reserve(json_output=True)
    captured = capsys.readouterr()

    assert code == 0
    doc = json.loads(captured.out)
    assert doc["ok"] is True
    assert doc["reserve_measured"] is False
    assert doc["reserve_note"] == "not_yet_visible"


# ---------------------------------------------------------------------------
# 3. #17: `proof verify --online --json` message, checked count, POSIX file path
# ---------------------------------------------------------------------------


def _write_pack_with_tx(tmp_path: Path, name: str = PROOF_PACK_FILE) -> Path:
    s = Session(started_at="2026-10-23T00:00:00+00:00", wallet_address=SENDER)
    s.mark_complete(1, lessons.LESSON_NAMES[1])
    s.mark_complete(
        4,
        lessons.LESSON_NAMES[4],
        txid=TXID,
        memo="XRPLCAMP|L4|hello",
        ledger_index=12345,
        close_time_iso="2026-10-23T00:01:00Z",
    )
    pack = generate_proof_pack(s)
    target = tmp_path / name
    save_proof_pack(pack, str(target))
    return target


def test_proof_verify_online_json_message_matches_mode_and_omits_offline_prompt(
    tmp_path, monkeypatch
):
    folder = tmp_path / "packs"
    folder.mkdir()
    pack_path = _write_pack_with_tx(folder, "learner_xrpl_camp_proof_pack.json")

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
            "close_time_iso": "2026-10-23T00:01:00Z",
            "result": "tesSUCCESS",
            "validated": True,
        },
    )

    # Single file --online --json
    r_file = runner.invoke(
        app, ["proof", "verify", str(pack_path), "--online", "--json"]
    )
    assert r_file.exit_code == 0, r_file.output
    file_doc = json.loads(r_file.stdout)
    assert "Run this same command with --online" not in file_doc["message"]
    assert "does not independently confirm" not in file_doc["message"]
    assert file_doc["online"]["message"] in file_doc["message"]

    # Folder --online --json
    r_folder = runner.invoke(
        app, ["proof", "verify", str(folder), "--online", "--json"]
    )
    assert r_folder.exit_code == 0, r_folder.output
    folder_doc = json.loads(r_folder.stdout)
    for entry in folder_doc["packs"]:
        assert "Run this same command with --online" not in entry["message"]
        assert "does not independently confirm" not in entry["message"]
        assert entry["online"]["message"] in entry["message"]


def test_proof_verify_online_json_contradicted_pack_counts_checked_lookups(
    tmp_path, monkeypatch
):
    folder = tmp_path / "packs"
    folder.mkdir()
    pack_path = _write_pack_with_tx(folder, "forged_xrpl_camp_proof_pack.json")

    # Contradicted via account mismatch (1 lookup actually made).
    monkeypatch.setattr(
        transport,
        "lookup_tx",
        lambda txid, url=None, dry_run=False, *, recorded_ledger_index=0: {
            "found": True,
            "hash": txid,
            "account": "rSomeoneElseCompletely",
            "destination": "rMailbox",
            "amount": "1000000",
            "delivered": "1000000",
            "fee": "10",
            "memo": "XRPLCAMP|L4|hello",
            "ledger_index": 12345,
            "close_time_iso": "2026-10-23T00:01:00Z",
            "result": "tesSUCCESS",
            "validated": True,
        },
    )

    r_file = runner.invoke(
        app, ["proof", "verify", str(pack_path), "--online", "--json"]
    )
    assert r_file.exit_code == 1, r_file.output
    file_doc = json.loads(r_file.stdout)
    assert file_doc["online"]["status"] == "contradicted"
    assert file_doc["online"]["total_lookups"] == 1
    assert file_doc["online"]["checked"] == 1

    r_folder = runner.invoke(
        app, ["proof", "verify", str(folder), "--online", "--json"]
    )
    assert r_folder.exit_code == 1, r_folder.output
    folder_doc = json.loads(r_folder.stdout)
    pack_entry = folder_doc["packs"][0]
    assert pack_entry["online"]["status"] == "contradicted"
    assert pack_entry["online"]["total_lookups"] == 1
    assert pack_entry["online"]["checked"] == 1


def test_proof_verify_json_prints_posix_file_separators_on_every_os(
    tmp_path, monkeypatch
):
    folder = tmp_path / "packs"
    folder.mkdir()
    pack_path = _write_pack_with_tx(folder, "forged.json")

    monkeypatch.setattr(
        transport,
        "lookup_tx",
        lambda txid, url=None, dry_run=False, *, recorded_ledger_index=0: {
            "found": False,
            "reason": transport.REASON_NOT_FOUND,
        },
    )

    monkeypatch.chdir(tmp_path)
    win_style_rel = "packs\\forged.json"
    # When run on POSIX where backslashes are not directory separators, pass the
    # nested relative path for filesystem resolution and also verify _posix_path
    # converts Windows backslashes.
    from xrpl_camp.cli import _posix_path

    assert _posix_path(Path(win_style_rel)) == "packs/forged.json"

    r_file = runner.invoke(
        app, ["proof", "verify", str(pack_path), "--online", "--json"]
    )
    file_doc = json.loads(r_file.stdout)
    assert "\\" not in file_doc["file"]
    assert file_doc["file"].endswith("packs/forged.json")

    r_folder = runner.invoke(
        app, ["proof", "verify", str(folder), "--online", "--json"]
    )
    folder_doc = json.loads(r_folder.stdout)
    assert "\\" not in folder_doc["folder"]
    for entry in folder_doc["packs"]:
        assert "\\" not in entry["file"]
        assert entry["file"].endswith("packs/forged.json")
    for item in folder_doc["summary"]["needs_attention"]:
        assert "\\" not in item["file"]
        assert item["file"].endswith("packs/forged.json")
