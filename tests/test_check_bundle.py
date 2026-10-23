"""Tests for scripts/check_bundle.py (PEP 610 direct_url.json bundle guard)."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = ROOT / "scripts" / "check_bundle.py"


def _load_check_bundle_module():
    spec = importlib.util.spec_from_file_location("check_bundle", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_check_bundle_passes_when_no_direct_url_present(tmp_path: Path) -> None:
    mod = _load_check_bundle_module()
    fake_bin = tmp_path / "xrpl-camp-1.5.1-linux-x64"
    fake_bin.write_bytes(b"fake")

    clean_toc = [
        "PYZ-00.pyz",
        "base_library.zip",
        "xrpl_camp-1.5.1.dist-info/METADATA",
        "xrpl_camp-1.5.1.dist-info/WHEEL",
    ]
    entries = mod.check_bundle_no_direct_url(fake_bin, archive_entries=clean_toc)
    assert entries == sorted(clean_toc)


def test_check_bundle_fails_when_direct_url_present(tmp_path: Path) -> None:
    mod = _load_check_bundle_module()
    fake_bin = tmp_path / "xrpl-camp-1.5.1-linux-x64"
    fake_bin.write_bytes(b"fake")

    leaked_toc = [
        "PYZ-00.pyz",
        "xrpl_camp-1.5.1.dist-info/METADATA",
        "xrpl_camp-1.5.1.dist-info/direct_url.json",
    ]
    with pytest.raises(RuntimeError, match="direct_url.json"):
        mod.check_bundle_no_direct_url(fake_bin, archive_entries=leaked_toc)


def test_check_bundle_cli_with_mocked_carchivereader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    mod = _load_check_bundle_module()
    fake_bin = tmp_path / "xrpl-camp-1.5.1-linux-x64"
    fake_bin.write_bytes(b"fake")

    toc_entries: dict[str, tuple[int, int, int, int, str]] = {
        "PYZ-00.pyz": (0, 0, 0, 0, "z"),
        "xrpl_camp-1.5.1.dist-info/METADATA": (0, 0, 0, 0, "x"),
    }

    class _FakeCArchiveReader:
        def __init__(self, path: str) -> None:
            self.path = path
            self.toc = dict(toc_entries)

    fake_pyi = types.ModuleType("PyInstaller")
    fake_archive = types.ModuleType("PyInstaller.archive")
    fake_readers = types.ModuleType("PyInstaller.archive.readers")
    fake_readers.CArchiveReader = _FakeCArchiveReader  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "PyInstaller", fake_pyi)
    monkeypatch.setitem(sys.modules, "PyInstaller.archive", fake_archive)
    monkeypatch.setitem(sys.modules, "PyInstaller.archive.readers", fake_readers)

    rc_ok = mod.main(["--list", str(fake_bin)])
    captured_ok = capsys.readouterr()
    assert rc_ok == 0
    assert "no direct_url.json present" in captured_ok.out
    assert "xrpl_camp-1.5.1.dist-info/METADATA" in captured_ok.out

    toc_entries["xrpl_camp-1.5.1.dist-info/direct_url.json"] = (0, 0, 0, 0, "x")
    rc_bad = mod.main([str(fake_bin)])
    captured_bad = capsys.readouterr()
    assert rc_bad == 1
    assert "direct_url.json" in captured_bad.err
