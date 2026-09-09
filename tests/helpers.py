"""Shared test helpers.

Three things live here rather than being copy-pasted into modules:

* :func:`strip_ansi` — one hardened implementation. The two private copies it
  replaces stripped only SGR sequences (``\\x1b[...m``), so an OSC-8 hyperlink
  or a cursor-movement sequence from a future Rich release would have silently
  corrupted every substring assertion in two modules at once.
* :data:`LOOKUP_KEYS` — the return contract of
  :func:`xrpl_camp.transport.lookup_tx`, asserted against BOTH the dry-run
  return and the real parser's return over a recorded response. Pinning only
  the simulated path is how the two were free to drift.
* the stub-client plumbing — so a test can drive the REAL transport functions
  over a recorded wire response instead of re-implementing the parser in the
  test body.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

FIXTURES = Path(__file__).parent / "fixtures"

#: Exact key set every ``lookup_tx`` return must carry — simulated or real.
#: A caller that branches on ``found`` and renders the rest must never meet a
#: dict with a key missing, so the not-found shape carries these too.
LOOKUP_KEYS = frozenset({
    "found",
    "hash",
    "account",
    "destination",
    "amount",
    "delivered",
    "fee",
    "memo",
    "ledger_index",
    "result",
    "validated",
    "close_time_iso",
    "date",
})


# ---------------------------------------------------------------------------
# Terminal output
# ---------------------------------------------------------------------------

# CSI (\x1b[ ... final-byte) plus OSC (\x1b] ... BEL or ST) plus the short
# two-character escapes. Rich emits OSC 8 for hyperlinks when it thinks the
# terminal supports them.
_ANSI = re.compile(
    r"""
    \x1b\[ [0-?]* [ -/]* [@-~]        # CSI: colours, cursor moves, erases
    | \x1b\] .*? (?: \x07 | \x1b\\ )  # OSC: hyperlinks, titles
    | \x1b [@-Z\\-_]                  # two-character escapes
    """,
    re.VERBOSE | re.DOTALL,
)


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences (CSI, OSC and two-byte) from `text`."""
    return _ANSI.sub("", text)


def squash(text: str) -> str:
    """Collapse whitespace so an assertion survives Rich's line wrapping.

    Rich breaks a panel body wherever the terminal width lands. Asserting on a
    sentence therefore has to compare against a width-independent form, or the
    test is really an assertion about `COLUMNS`.
    """
    return re.sub(r"\s+", " ", strip_ansi(text)).strip()


# ---------------------------------------------------------------------------
# Recorded responses
# ---------------------------------------------------------------------------


def load_fixture(name: str) -> dict:
    """Load a recorded rippled response body from ``tests/fixtures``."""
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def make_response(result: dict, *, successful: bool = True):
    """Wrap a recorded result in a REAL :class:`xrpl.models.response.Response`.

    Using the library's own Response (rather than a hand-rolled stand-in) means
    ``is_successful()`` is the library's implementation, so a change to what
    "successful" means upstream turns these tests red instead of sliding past.
    """
    from xrpl.models.response import Response, ResponseStatus, ResponseType

    return Response(
        status=ResponseStatus.SUCCESS if successful else ResponseStatus.ERROR,
        result=result,
        type=ResponseType.RESPONSE,
    )


class RecordingClient:
    """Stand-in for ``JsonRpcClient`` that replays canned responses.

    Records every request model it was handed, so a test can assert on what the
    transport actually asked for — ``api_version=2`` in particular, which is the
    pin that stops the ``tx_json`` nesting break from recurring under API v3.
    """

    def __init__(self, url: str, log: list[Any], responder: Callable[[Any], Any]):
        self.url = url
        self._log = log
        self._responder = responder
        log.append(("client", url))

    def request(self, req: Any):
        self._log.append(("request", req))
        return self._responder(req)


class ClientRecorder:
    """Handle returned by :func:`stub_client`."""

    def __init__(self) -> None:
        self.log: list[Any] = []

    @property
    def urls(self) -> list[str]:
        return [entry[1] for entry in self.log if entry[0] == "client"]

    @property
    def requests(self) -> list[Any]:
        return [entry[1] for entry in self.log if entry[0] == "request"]

    def request_of(self, model_name: str) -> Any:
        """The first recorded request whose model class is `model_name`."""
        for req in self.requests:
            if type(req).__name__ == model_name:
                return req
        raise AssertionError(
            f"no {model_name} request was made; saw "
            f"{[type(r).__name__ for r in self.requests]}",
        )


def stub_client(
    monkeypatch,
    responses: Any | Iterable[Any] | Callable[[Any], Any],
) -> ClientRecorder:
    """Replace ``xrpl.clients.JsonRpcClient`` with a recording stub.

    `responses` is one response, an iterable consumed in request order, or a
    callable taking the request model. The transport imports ``JsonRpcClient``
    inside each function, so patching the attribute on ``xrpl.clients`` reaches
    every call site without the transport needing a seam of its own.
    """
    import xrpl.clients

    recorder = ClientRecorder()

    if callable(responses):
        responder = responses
    elif isinstance(responses, (list, tuple)):
        queue = list(responses)

        def responder(_req: Any):
            if not queue:
                raise AssertionError("stub client ran out of canned responses")
            return queue.pop(0)
    else:
        def responder(_req: Any):
            return responses

    def factory(url: str, *args: Any, **kwargs: Any) -> RecordingClient:
        return RecordingClient(url, recorder.log, responder)

    monkeypatch.setattr(xrpl.clients, "JsonRpcClient", factory)
    return recorder


__all__ = [
    "FIXTURES",
    "LOOKUP_KEYS",
    "ClientRecorder",
    "RecordingClient",
    "load_fixture",
    "make_response",
    "squash",
    "strip_ansi",
    "stub_client",
]
