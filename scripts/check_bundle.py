#!/usr/bin/env python3
"""Verify that a PyInstaller bundle archive does not contain any PEP 610 direct_url.json.

Usage:
    python scripts/check_bundle.py [--list] <binary_path>
"""

from __future__ import annotations

import sys
from collections.abc import Iterable
from pathlib import Path


def check_bundle_no_direct_url(
    binary_path: str | Path,
    *,
    archive_entries: Iterable[str] | None = None,
) -> list[str]:
    """List the PyInstaller archive and raise RuntimeError if any entry ends in direct_url.json."""
    if archive_entries is None:
        from PyInstaller.archive.readers import CArchiveReader

        reader = CArchiveReader(str(Path(binary_path)))
        entries = sorted(str(k) for k in reader.toc)
    else:
        entries = sorted(str(k) for k in archive_entries)

    leaked = [
        entry
        for entry in entries
        if entry.replace("\\", "/").lower() == "direct_url.json"
        or entry.replace("\\", "/").lower().endswith("/direct_url.json")
    ]
    if leaked:
        raise RuntimeError(
            f"Bundled PEP 610 direct_url.json build record found in {binary_path}: "
            f"{', '.join(leaked)}"
        )
    return entries


def main(argv: list[str] | None = None) -> int:
    raw_args = list(sys.argv[1:] if argv is None else argv)
    show_list = False
    args: list[str] = []
    for arg in raw_args:
        if arg == "--list":
            show_list = True
        else:
            args.append(arg)

    if len(args) != 1:
        print(
            "usage: check_bundle.py [--list] <binary_path>",
            file=sys.stderr,
        )
        return 2

    binary_path = args[0]
    try:
        entries = check_bundle_no_direct_url(binary_path)
    except Exception as exc:
        print(f"BUNDLE CHECK FAILED: {exc}", file=sys.stderr)
        return 1

    if show_list:
        for entry in entries:
            print(entry)
    print(
        f"[bundle-check] Verified {len(entries)} archive entries in "
        f"{binary_path}: no direct_url.json present"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
