"""What a "history gone" verdict rests on.

`proof verify --online` calls a miss "history gone" when the endpoint does not
hold the ledger the pack recorded. That ledger number is the pack's own word.

* an announced reset covers the lesson's time: independent -> NO HISTORY
* only the pack's ledger number says so:       a claim     -> UNCONFIRMED

Both are exit 3 (unverifiable). Neither is ever a pass.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from urllib.parse import urlparse

import pytest
from typer.testing import CliRunner

from tests.helpers import strip_ansi
from xrpl_camp import proof_pack, resets, transport
from xrpl_camp.cli import app
from xrpl_camp.models import Session

runner = CliRunner()
TESTNET = "https://s.altnet.rippletest.net:51234"
RESET_SOURCE = "https://xrpl.org/blog/2026/testnet-devnet-reset"
RESET_LABEL = f"Testnet was reset on 2026-11-25 ({RESET_SOURCE})"
BEFORE = datetime(2026, 11, 20, tzinfo=UTC)
AFTER = datetime(2026, 12, 1, tzinfo=UTC)
GONE = {"found": False, "reason": transport.REASON_HISTORY_GONE}


@pytest.fixture(autouse=True)
def pinned_clock(monkeypatch):
    """Before any listed reset, unless a test says otherwise."""
    monkeypatch.setattr("xrpl_camp.resets._now", lambda: BEFORE)


def _entry(**extra) -> dict:
    return {"lesson": 4, "txid": "A" * 64, "ledger_index": 4_200_000,
            "completed_at": "2026-11-06T00:00:00Z", **extra}


# ── the announced-reset list ──────────────────────────────────────────


def test_the_2026_11_25_reset_is_listed_for_both_test_networks():
    assert {(r.network, r.day) for r in resets.KNOWN_RESETS} == {
        ("testnet", date(2026, 11, 25)), ("devnet", date(2026, 11, 25)),
    }


def test_every_listed_reset_cites_the_xrpl_org_notice():
    for reset in resets.KNOWN_RESETS:
        source = urlparse(reset.source)
        assert (source.scheme, source.hostname) == ("https", "xrpl.org")
        assert reset.source == RESET_SOURCE


def test_a_reset_day_spans_every_timezone():
    r = resets.KnownReset("testnet", date(2026, 11, 25), "src")
    assert r.starts == datetime(2026, 11, 24, 10, 0, tzinfo=UTC)
    assert r.ends == datetime(2026, 11, 26, 12, 0, tzinfo=UTC)
    assert r.label() == "Testnet was reset on 2026-11-25 (src)"


@pytest.mark.parametrize(
    ("network", "recorded", "now", "covered"),
    [
        ("testnet", datetime(2026, 11, 6, tzinfo=UTC), AFTER, True),
        ("devnet", datetime(2026, 11, 25, 18, tzinfo=UTC), AFTER, True),
        ("testnet", None, AFTER, True),                                       # no time recorded
        ("testnet", datetime(2026, 11, 26, 12, tzinfo=UTC), AFTER, False),    # after the reset
        ("testnet", datetime(2026, 11, 6, tzinfo=UTC), BEFORE, False),        # not happened yet
        ("testnet", datetime(2026, 11, 6, tzinfo=UTC),
         datetime(2026, 11, 24, 9, 59, tzinfo=UTC), False),
        ("mainnet", None, AFTER, False),
        ("custom:example.org", None, AFTER, False),
    ],
)
def test_which_lessons_an_announced_reset_covers(network, recorded, now, covered):
    label = resets.announced_reset_after(network, recorded, now=now)
    expected = f"{network.capitalize()} was reset on 2026-11-25 ({RESET_SOURCE})" if covered else ""
    assert label == expected


@pytest.mark.parametrize(
    ("raw", "parsed"),
    [
        ("2026-11-06T00:00:00Z", datetime(2026, 11, 6, tzinfo=UTC)),
        ("2026-11-06T00:00:00+00:00", datetime(2026, 11, 6, tzinfo=UTC)),
        ("2026-11-06T00:00:00", datetime(2026, 11, 6, tzinfo=UTC)),   # naive reads as UTC
        ("", None), ("   ", None), ("not a time", None), (None, None), (12345, None),
    ],
)
def test_parse_time(raw, parsed):
    assert resets.parse_time(raw) == parsed


def test_the_unpinned_clock_reads_the_real_time(monkeypatch):
    monkeypatch.undo()
    assert abs((datetime.now(tz=UTC) - resets._now()).total_seconds()) < 5


# ── one lesson ────────────────────────────────────────────────────────


def test_an_announced_reset_is_an_independent_signal():
    r = proof_pack.classify_lesson_online(_entry(), "rCamp", GONE, announced_reset=RESET_LABEL)
    assert r["status"] == proof_pack.ONLINE_MISS_HISTORY_GONE
    assert r["history_signal"] == "announced"
    text = " ".join(r["problems"])
    assert "does not hold ledger 4200000" in text
    assert "Testnet was reset on 2026-11-25" in text
    assert "after this lesson was completed" in text
    assert "a made-up hash dated before the reset reads the same way" in r["does_not_prove"]


def test_only_the_packs_ledger_number_is_unconfirmed():
    r = proof_pack.classify_lesson_online(_entry(), "rCamp", GONE)
    assert r["status"] == proof_pack.ONLINE_MISS_HISTORY_UNCONFIRMED == "miss_history_unconfirmed"
    assert r["history_signal"] == "pack_claim"
    text = " ".join(r["problems"])
    assert text.startswith(
        "UNCONFIRMED: the pack claims a ledger this endpoint does not hold, "
        "and nothing else confirms a reset."
    )
    assert "This endpoint does not hold ledger 4200000" in text
    assert "anyone can write that number" in text
    assert "Anyone can write a ledger number into a pack" in r["does_not_prove"]


def test_a_found_transaction_and_a_plain_miss_carry_no_signal():
    found = {"found": True, "account": "rCamp", "result": "tesSUCCESS",
             "validated": True, "ledger_index": 4_200_000}
    ok = proof_pack.classify_lesson_online(_entry(), "rCamp", found, announced_reset=RESET_LABEL)
    assert (ok["status"], ok["history_signal"]) == (proof_pack.ONLINE_OK, "")
    miss = {"found": False, "reason": transport.REASON_NOT_FOUND}
    plain = proof_pack.classify_lesson_online(_entry(), "rCamp", miss, announced_reset=RESET_LABEL)
    assert (plain["status"], plain["history_signal"]) == (proof_pack.ONLINE_MISS_NOT_FOUND, "")


# ── the whole pack ────────────────────────────────────────────────────


def _res(status: str) -> dict:
    return {"status": status}


def test_an_announced_reset_summary_is_history_gone_and_not_a_pass():
    s = proof_pack.summarize_online([_res(proof_pack.ONLINE_MISS_HISTORY_GONE)])
    assert s["status"] == proof_pack.SUMMARY_HISTORY_GONE
    assert s["history_signal"] == "announced"
    assert "Not a failure, and not a pass" in s["message"]
    assert proof_pack.online_exit_code(s) == 3


def test_a_pack_claim_summary_is_unconfirmed_and_not_a_pass():
    s = proof_pack.summarize_online([_res(proof_pack.ONLINE_MISS_HISTORY_UNCONFIRMED)])
    assert s["status"] == proof_pack.SUMMARY_HISTORY_UNCONFIRMED == "history_unconfirmed"
    assert s["history_signal"] == "pack_claim"
    assert s["message"].startswith("UNCONFIRMED: 1 of 1 transactions are missing")
    assert "a claim, not evidence" in s["message"]
    assert proof_pack.online_exit_code(s) == 3


def test_the_weaker_signal_names_the_result():
    s = proof_pack.summarize_online([
        _res(proof_pack.ONLINE_OK),
        _res(proof_pack.ONLINE_MISS_HISTORY_GONE),
        _res(proof_pack.ONLINE_MISS_HISTORY_UNCONFIRMED),
    ])
    assert (s["status"], s["history_signal"]) == ("history_unconfirmed", "pack_claim")
    assert (s["checked"], s["total_lookups"]) == (3, 3)


@pytest.mark.parametrize(
    ("beside", "status", "code"),
    [
        (proof_pack.ONLINE_MISMATCH, proof_pack.SUMMARY_CONTRADICTED, 1),
        (proof_pack.ONLINE_MISS_NOT_FOUND, proof_pack.SUMMARY_CONTRADICTED, 1),
        (proof_pack.ONLINE_UNREACHABLE, proof_pack.SUMMARY_UNKNOWN, 3),
    ],
)
def test_a_contradiction_or_an_unknown_still_outranks_it(beside, status, code):
    s = proof_pack.summarize_online([
        _res(proof_pack.ONLINE_MISS_HISTORY_UNCONFIRMED), _res(beside),
    ])
    assert s["status"] == status
    assert proof_pack.online_exit_code(s) == code
    assert s["history_signal"] == "pack_claim"  # still named


def test_a_confirmed_pack_has_no_history_signal():
    s = proof_pack.summarize_online([_res(proof_pack.ONLINE_OK)])
    assert (s["status"], s["history_signal"]) == (proof_pack.SUMMARY_CONFIRMED, "")
    assert proof_pack.online_exit_code(s) == 0


@pytest.mark.parametrize("status", ["ledger_history_gone", "history_unconfirmed"])
def test_neither_is_ever_counted_as_passed_in_a_batch(status):
    rows = [{"file": "p.json", "address": "rCamp", "hash_ok": True,
             "online": {"status": status}}]
    summary = proof_pack.batch_summary(rows)
    assert summary["passed"] == 0
    reason = summary["needs_attention"][0]["reason"]
    assert ("unconfirmed" in reason) is (status == "history_unconfirmed")


# ── the CLI, through the real lookup path ─────────────────────────────


def _pack_file(tmp_path, completed_at: str = "2026-11-06T00:00:00Z"):
    s = Session(started_at="2026-11-06T00:00:00Z", wallet_address="rCamp")
    s.mark_complete(4, "Send", txid="A" * 64, ledger_index=4_200_000)
    s.progress[-1].completed_at = completed_at
    pack = proof_pack.generate_proof_pack(s)
    path = tmp_path / "xrpl_camp_proof_pack.json"
    proof_pack.save_proof_pack(pack, str(path))
    return path


def _history_gone(monkeypatch):
    monkeypatch.setattr(transport, "lookup_tx", lambda *a, **k: dict(GONE))


def _verify(path, *extra):
    return runner.invoke(
        app, ["proof", "verify", str(path), "--online", "--rpc-url", TESTNET, *extra],
    )


def test_cli_before_any_announced_reset_a_history_miss_is_unconfirmed(tmp_path, monkeypatch):
    _history_gone(monkeypatch)
    path = _pack_file(tmp_path)
    out = _verify(path)
    text = " ".join(strip_ansi(out.output).split())
    assert out.exit_code == 3, out.output
    assert "UNCONFIRMED" in text
    assert "the pack claims a ledger this endpoint does not hold" in text
    assert "NO HISTORY" not in text
    data = json.loads(_verify(path, "--json").stdout)
    assert data["online"]["status"] == "history_unconfirmed"
    assert data["online"]["history_signal"] == "pack_claim"
    assert data["lessons"][-1]["history_signal"] == "pack_claim"


def test_cli_after_the_announced_reset_it_is_history_gone_with_the_signal(tmp_path, monkeypatch):
    monkeypatch.setattr("xrpl_camp.resets._now", lambda: AFTER)
    _history_gone(monkeypatch)
    path = _pack_file(tmp_path)
    out = _verify(path)
    text = " ".join(strip_ansi(out.output).split())
    assert out.exit_code == 3, out.output
    assert "NO HISTORY" in text and "Testnet was reset on 2026-11-25" in text
    assert "UNCONFIRMED" not in text
    data = json.loads(_verify(path, "--json").stdout)
    assert data["online"]["status"] == "ledger_history_gone"
    assert data["online"]["history_signal"] == "announced"


def test_cli_a_lesson_completed_after_the_reset_is_not_covered_by_it(tmp_path, monkeypatch):
    monkeypatch.setattr("xrpl_camp.resets._now", lambda: AFTER)
    _history_gone(monkeypatch)
    path = _pack_file(tmp_path, completed_at="2026-11-28T00:00:00Z")
    data = json.loads(_verify(path, "--json").stdout)
    assert data["online"]["history_signal"] == "pack_claim"


def test_cli_the_network_is_the_endpoints_not_the_packs(tmp_path, monkeypatch):
    """A Testnet reset says nothing about a custom endpoint, whatever the pack says."""
    monkeypatch.setattr("xrpl_camp.resets._now", lambda: AFTER)
    monkeypatch.setattr(transport, "lookup_tx", lambda *a, **k: dict(GONE))
    path = _pack_file(tmp_path)
    out = runner.invoke(app, [
        "proof", "verify", str(path), "--online", "--json",
        "--rpc-url", "https://ledger.example.org:51234",
    ])
    data = json.loads(out.stdout)
    assert data["online"]["history_signal"] == "pack_claim"
