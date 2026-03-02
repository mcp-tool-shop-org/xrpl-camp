"""Structured error handling for XRPL Camp."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CampError:
    """Structured error shape for user-facing messages.

    Follows the pattern: code + message + actionable hint.
    No stack traces. No jargon. Just what happened and what to try next.
    """

    code: str
    message: str
    hint: str
    retryable: bool = False

    def user_message(self) -> str:
        """Format for console output."""
        parts = [f"[{self.code}] {self.message}"]
        if self.hint:
            parts.append(f"  Hint: {self.hint}")
        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Factory functions — one per failure mode
# ---------------------------------------------------------------------------


def faucet_error(detail: str = "") -> CampError:
    """Testnet faucet request failed."""
    return CampError(
        code="NET_FAUCET",
        message=f"Faucet request failed{': ' + detail if detail else '.'}",
        hint="The Testnet faucet may be temporarily down. Try again in a minute.",
        retryable=True,
    )


def send_error(detail: str = "") -> CampError:
    """Transaction submission failed."""
    return CampError(
        code="NET_SEND",
        message=f"Transaction submission failed{': ' + detail if detail else '.'}",
        hint="Check your wallet is funded. The Testnet may be congested.",
        retryable=True,
    )


def lookup_error(detail: str = "") -> CampError:
    """Transaction lookup failed."""
    return CampError(
        code="NET_LOOKUP",
        message=f"Transaction lookup failed{': ' + detail if detail else '.'}",
        hint="The transaction may not be validated yet. Wait a moment and retry.",
        retryable=True,
    )


def balance_error(detail: str = "") -> CampError:
    """Balance check failed."""
    return CampError(
        code="NET_BALANCE",
        message=f"Balance check failed{': ' + detail if detail else '.'}",
        hint="The account may not exist yet. Fund it first.",
        retryable=True,
    )


def connection_error(url: str) -> CampError:
    """Could not connect to the RPC endpoint."""
    return CampError(
        code="NET_CONNECT",
        message=f"Could not connect to {url}",
        hint="Check your internet connection, or set XRPL_CAMP_RPC_URL to a different endpoint.",
        retryable=True,
    )
