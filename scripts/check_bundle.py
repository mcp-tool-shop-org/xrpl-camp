#!/usr/bin/env python3
"""Verify that a PyInstaller bundle archive does not contain build-machine paths.

Checks both:
1. No PEP 610 direct_url.json in the CArchive TOC.
2. No home path (Linux, macOS, or Windows user profile directory, any case)
   in any bundled _sysconfigdata* module (in the embedded PYZ archive or CArchive).

Usage:
    python scripts/check_bundle.py [--list] <binary_path>
"""

from __future__ import annotations

import re
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path

_SEP = r"(?:[\\/]+)"
_HOME_PATH_RE = re.compile(
    rf"(?:"
    rf"/(?:home|users)/[\w.-]+(?:/|\b)"
    rf"|[a-z]:{_SEP}users{_SEP}[\w.-]+(?:{_SEP}|\b)"
    rf"|{_SEP}[a-z]{_SEP}users{_SEP}[\w.-]+(?:{_SEP}|\b)"
    rf")",
    re.IGNORECASE,
)


def _is_sysconfigdata_name(name: str) -> bool:
    norm = name.replace("\\", "/").split("/")[-1]
    base = norm.split(".")[0]
    return base.startswith("_sysconfigdata")


def find_sysconfigdata_home_paths(data: bytes | str) -> list[str]:
    """Return any home-path substrings found in raw or text _sysconfigdata content."""
    text = data.decode("latin-1") if isinstance(data, bytes) else data
    return [m.group(0) for m in _HOME_PATH_RE.finditer(text)]


def _extract_sysconfigdata_blobs(reader: object) -> dict[str, bytes]:
    """Extract raw bytes of all _sysconfigdata* modules from embedded PYZ and CArchive."""
    blobs: dict[str, bytes] = {}
    toc = getattr(reader, "toc", {})
    items = toc.items() if isinstance(toc, Mapping) else ()
    for name, entry in items:
        typecode = entry[-1] if isinstance(entry, tuple) and entry else None
        if typecode in ("z", "Z", b"z", b"Z") and hasattr(reader, "open_embedded_archive"):
            pyz = reader.open_embedded_archive(name)
            pyz_toc = getattr(pyz, "toc", ())
            for mod in sorted(str(k) for k in pyz_toc):
                if _is_sysconfigdata_name(mod):
                    raw = pyz.extract(mod, raw=True)
                    if isinstance(raw, bytes):
                        blobs[f"{name}:{mod}"] = raw
        elif _is_sysconfigdata_name(str(name)) and hasattr(reader, "extract"):
            raw = reader.extract(name)
            if isinstance(raw, bytes):
                blobs[str(name)] = raw
    return blobs


def check_bundle_no_direct_url(
    binary_path: str | Path,
    *,
    archive_entries: Iterable[str] | None = None,
    sysconfigdata_blobs: Mapping[str, bytes | str] | None = None,
) -> list[str]:
    """Verify the bundle has no direct_url.json and no home paths in _sysconfigdata*."""
    reader = None
    if archive_entries is None:
        from PyInstaller.archive.readers import CArchiveReader

        reader = CArchiveReader(str(Path(binary_path)))
        entries = sorted(str(k) for k in reader.toc)
    else:
        entries = sorted(str(k) for k in archive_entries)

    leaked_direct_url = [
        entry
        for entry in entries
        if entry.replace("\\", "/").lower() == "direct_url.json"
        or entry.replace("\\", "/").lower().endswith("/direct_url.json")
    ]

    if sysconfigdata_blobs is None:
        blobs: Mapping[str, bytes | str] = (
            _extract_sysconfigdata_blobs(reader) if reader is not None else {}
        )
    else:
        blobs = sysconfigdata_blobs

    leaked_sysconfig: list[str] = []
    for mod_key, raw in sorted(blobs.items()):
        hits = find_sysconfigdata_home_paths(raw)
        if hits:
            sample = ", ".join(dict.fromkeys(hits[:3]))
            leaked_sysconfig.append(f"{mod_key} ({len(hits)} hits, e.g. {sample})")

    errors: list[str] = []
    if leaked_direct_url:
        errors.append(
            f"Bundled PEP 610 direct_url.json build record found in {binary_path}: "
            f"{', '.join(leaked_direct_url)}"
        )
    if leaked_sysconfig:
        errors.append(
            f"Home path found in bundled _sysconfigdata module in {binary_path}: "
            f"{'; '.join(leaked_sysconfig)}"
        )
    if errors:
        raise RuntimeError("; ".join(errors))

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
        f"{binary_path}: no direct_url.json or _sysconfigdata home path present"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
