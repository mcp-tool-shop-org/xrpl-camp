"""A missing transaction after a full network reset.

Testnet and Devnet are wiped on 2026-11-25. A reset deletes every ledger and
counts again from the start, so a ledger index recorded before it is far past
anything on the new chain. That must read as "history gone" (can't be
checked), not as "no transaction with this hash" (which reads as a forgery).
"""

from __future__ import annotations

import pytest

from xrpl_camp import proof_pack, transport

URL = "https://s.altnet.rippletest.net:51234"
RECORDED = 4_200_000  # a ledger index recorded before the reset


def _server(monkeypatch, complete: str | None) -> None:
    state = None if complete is None else {"complete_ledgers": complete}
    monkeypatch.setattr(transport, "_server_state", lambda url: state)


# ── the endpoint's ledger range ───────────────────────────────────────


@pytest.mark.parametrize(
    ("complete", "bounds"),
    [
        ("800-1000", (800, 1000)),
        ("800-890,905-1000", (800, 1000)),
        (" 32570 - 4200000 ", (32570, 4200000)),
        ("77", (77, 77)),
        ("905-1000,800-890", (800, 1000)),
    ],
)
def test_bounds_read_the_lowest_and_highest_ledger(monkeypatch, complete, bounds):
    _server(monkeypatch, complete)
    assert transport.complete_ledger_bounds(URL) == bounds
    assert transport.earliest_complete_ledger(URL) == bounds[0]


@pytest.mark.parametrize("complete", [None, "", "empty", "none", "junk", "a-b"])
def test_bounds_are_none_when_the_range_cannot_be_read(monkeypatch, complete):
    _server(monkeypatch, complete)
    assert transport.complete_ledger_bounds(URL) is None
    assert transport.earliest_complete_ledger(URL) is None


def test_bounds_default_to_the_configured_endpoint(monkeypatch):
    seen = []
    monkeypatch.setattr(transport, "get_rpc_url", lambda: "https://configured.example")
    monkeypatch.setattr(
        transport, "_server_state",
        lambda url: seen.append(url) or {"complete_ledgers": "5-9"},
    )
    assert transport.complete_ledger_bounds() == (5, 9)
    assert seen == ["https://configured.example"]


# ── why a transaction is missing ──────────────────────────────────────


def test_after_a_full_reset_the_recorded_ledger_is_past_the_new_chain(monkeypatch):
    """The chain restarted: its newest ledger is far below the recorded one."""
    _server(monkeypatch, "2-640")
    assert transport._miss_reason(URL, RECORDED) == transport.REASON_HISTORY_GONE


def test_discarded_old_history_is_still_history_gone(monkeypatch):
    _server(monkeypatch, "5000000-5200000")
    assert transport._miss_reason(URL, RECORDED) == transport.REASON_HISTORY_GONE


def test_a_ledger_the_endpoint_holds_is_a_real_miss(monkeypatch):
    _server(monkeypatch, "32570-4300000")
    assert transport._miss_reason(URL, RECORDED) == transport.REASON_NOT_FOUND


@pytest.mark.parametrize(
    ("latest", "reason"),
    [
        (RECORDED - 10, transport.REASON_NOT_FOUND),       # a server a few ledgers behind
        (RECORDED - 1_000, transport.REASON_NOT_FOUND),    # at the tolerance
        (RECORDED - 1_001, transport.REASON_HISTORY_GONE),  # past it: a restart
    ],
)
def test_server_lag_is_not_a_reset(monkeypatch, latest, reason):
    _server(monkeypatch, f"32570-{latest}")
    assert transport._miss_reason(URL, RECORDED) == reason


@pytest.mark.parametrize("recorded", [0, -5])
def test_no_recorded_index_means_nothing_can_be_said(monkeypatch, recorded):
    _server(monkeypatch, "2-640")
    assert transport._miss_reason(URL, recorded) == transport.REASON_NOT_FOUND


@pytest.mark.parametrize("complete", [None, "empty"])
def test_an_unreadable_range_is_a_plain_miss(monkeypatch, complete):
    _server(monkeypatch, complete)
    assert transport._miss_reason(URL, RECORDED) == transport.REASON_NOT_FOUND


# ── what the learner is told ──────────────────────────────────────────


def _entry() -> dict:
    return {"lesson": 2, "txid": "A" * 64, "ledger_index": RECORDED}


def test_a_reset_miss_is_reported_as_uncheckable_not_as_a_forgery():
    live = {"found": False, "reason": transport.REASON_HISTORY_GONE}
    result = proof_pack.classify_lesson_online(_entry(), "rLEARNER", live)
    assert result["status"] == proof_pack.ONLINE_MISS_HISTORY_GONE
    text = " ".join(result["problems"])
    assert f"does not hold ledger {RECORDED}" in text
    assert "the network was reset or its old history was discarded" in text
    assert "no transaction with this hash" not in text


def test_a_plain_miss_still_reads_as_not_found():
    live = {"found": False, "reason": transport.REASON_NOT_FOUND}
    result = proof_pack.classify_lesson_online(_entry(), "rLEARNER", live)
    assert result["status"] == proof_pack.ONLINE_MISS_NOT_FOUND
    assert "no transaction with this hash is on the ledger" in " ".join(result["problems"])
