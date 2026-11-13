"""Announced resets of the public test networks.

A reset deletes every account and transaction on a test network. A proof pack
made before one still has its hash, but its transactions are on no ledger.

`proof verify --online` already reports such a miss as "history gone" when the
endpoint does not hold the ledger the pack recorded. But that ledger index is
the pack's own word: anyone can write it. This list is the one signal that
does not come from the pack. When an announced reset covers the time a lesson
was completed, the miss is reported as history gone with the reset named.
Without one, the same miss is UNCONFIRMED: the pack claims a ledger the
endpoint does not hold, and nothing else confirms why.

The announcement gives a day and no hour or timezone. So a reset covers a
lesson completed before the day has ended everywhere (UTC-12), and counts as
having happened only once the day has begun everywhere (UTC+14).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta


@dataclass(frozen=True)
class KnownReset:
    """An announced reset of one network, on one day."""

    network: str
    day: date
    source: str

    @property
    def starts(self) -> datetime:
        """The earliest instant the reset day exists anywhere (UTC+14)."""
        return datetime.combine(self.day, time.min, tzinfo=UTC) - timedelta(hours=14)

    @property
    def ends(self) -> datetime:
        """The last instant the reset day exists anywhere (UTC-12)."""
        return datetime.combine(
            self.day + timedelta(days=1), time.min, tzinfo=UTC,
        ) + timedelta(hours=12)

    def label(self) -> str:
        return f"{self.network.capitalize()} was reset on {self.day.isoformat()} ({self.source})"


_RESET_2026_11_25 = "https://xrpl.org/blog/2026/testnet-devnet-reset"

KNOWN_RESETS: tuple[KnownReset, ...] = (
    KnownReset("testnet", date(2026, 11, 25), _RESET_2026_11_25),
    KnownReset("devnet", date(2026, 11, 25), _RESET_2026_11_25),
)


def _now() -> datetime:
    """The current time. A seam: the test suite pins it, so results don't
    change on the day a listed reset happens."""
    return datetime.now(tz=UTC)


def parse_time(value: object) -> datetime | None:
    """An ISO 8601 time from a pack, as an aware datetime, or None."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def announced_reset_after(
    network: str,
    recorded_at: datetime | None,
    *,
    now: datetime | None = None,
    resets: tuple[KnownReset, ...] = KNOWN_RESETS,
) -> str:
    """The label of the first announced reset of ``network`` after
    ``recorded_at``, or "".

    Only a reset that has (possibly) already happened counts. A lesson with
    no recorded time is covered by any reset that has happened, since nothing
    says it came later.
    """
    now = now or _now()
    for reset in sorted(resets, key=lambda r: r.day):
        if reset.network != network or now < reset.starts:
            continue
        if recorded_at is None or recorded_at < reset.ends:
            return reset.label()
    return ""
