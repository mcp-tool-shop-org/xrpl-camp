"""XRPL Camp - learn the XRP Ledger in one sitting.

Importing this package makes stdout and stderr safe for the characters the
lessons print. XRPL Camp draws check marks, arrows, em dashes and box-drawing
borders; on Windows a console, a redirect, a pipe or a frozen binary can hand
Python a cp1252 stream, where the first check mark raises UnicodeEncodeError
and takes the lesson down with it. The guard below runs once, before any
Console object exists, so every command is covered by construction.
"""

from __future__ import annotations

import io
import os
import sys
from typing import Any

__version__ = "1.4.0"

# Streams we wrapped ourselves. Held so the underlying buffer is not closed
# when the wrapper we replaced is garbage collected.
_wrapped_streams: list[Any] = []


def _is_utf8(encoding: str | None) -> bool:
    """True if `encoding` is some spelling of UTF-8."""
    if not encoding:
        return False
    return encoding.lower().replace("_", "-") in ("utf-8", "utf8")


def _reconfigure(stream: Any, **kwargs: Any) -> bool:
    """Try stream.reconfigure(**kwargs). True if it took."""
    reconfigure = getattr(stream, "reconfigure", None)
    if not callable(reconfigure):
        return False
    try:
        reconfigure(**kwargs)
    except Exception:
        return False
    return True


def _rewrap_utf8(name: str, stream: Any) -> bool:
    """Replace sys.<name> with a UTF-8 writer over the same binary buffer."""
    buffer = getattr(stream, "buffer", None)
    if buffer is None:
        return False
    try:
        replacement = io.TextIOWrapper(
            buffer, encoding="utf-8", errors="replace", line_buffering=True,
        )
    except Exception:
        return False
    _wrapped_streams.append(replacement)
    setattr(sys, name, replacement)
    return True


def configure_console_encoding() -> None:
    """Make stdout/stderr tolerate non-ASCII output on every platform.

    Three layers, each a fallback for the one before:

    1. Reconfigure the stream to UTF-8 with ``errors="replace"``.
    2. Wrap the underlying binary buffer in a fresh UTF-8 writer.
    3. Failing both, at least set ``errors="replace"`` on whatever encoding
       the stream already has, so output degrades to '?' instead of crashing.

    Set ``XRPL_CAMP_NO_UTF8=1`` to keep the platform encoding and take only
    layer 3. Nothing here ever raises.
    """
    keep_encoding = os.environ.get("XRPL_CAMP_NO_UTF8", "").strip() not in ("", "0", "false")

    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        if stream is None:  # pythonw / frozen GUI build: no stream at all
            continue
        if _is_utf8(getattr(stream, "encoding", None)):
            continue
        if not keep_encoding and _reconfigure(stream, encoding="utf-8", errors="replace"):
            continue
        if not keep_encoding and _rewrap_utf8(name, stream):
            continue
        _reconfigure(stream, errors="replace")


configure_console_encoding()
