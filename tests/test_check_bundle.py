"""Tests for scripts/check_bundle.py (direct_url.json and _sysconfigdata home-path guard)."""

from __future__ import annotations

import importlib.util
import marshal
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


def _marshal_sysconfigdata(
    prefix: str, *, mod_name: str = "_sysconfigdata__linux_x86_64-linux-gnu.py"
) -> bytes:
    """Compile and marshal a realistic _sysconfigdata module for a given install prefix."""
    sep = "\\" if "\\" in prefix else "/"
    destdirs = (
        f"{prefix} {prefix}{sep}lib {prefix}{sep}lib{sep}python3.12 "
        f"{prefix}{sep}lib{sep}python3.12{sep}lib-dynload"
    )
    src = (
        "# system configuration generated and used by the sysconfig module\n"
        "build_time_vars = {\n"
        f" 'BINDIR': {f'{prefix}{sep}bin'!r},\n"
        f" 'CONFINCLUDEDIR': {f'{prefix}{sep}include'!r},\n"
        f" 'CONFINCLUDEPY': {f'{prefix}{sep}include{sep}python3.12'!r},\n"
        f" 'DESTDIRS': {destdirs!r},\n"
        f" 'DESTLIB': {f'{prefix}{sep}lib{sep}python3.12'!r},\n"
        f" 'INCLDIRSTOMAKE': {f'{prefix}{sep}include {prefix}{sep}include{sep}python3.12'!r},\n"
        f" 'INCLUDEDIR': {f'{prefix}{sep}include'!r},\n"
        f" 'INCLUDEPY': {f'{prefix}{sep}include{sep}python3.12'!r},\n"
        f" 'LIBDEST': {f'{prefix}{sep}lib{sep}python3.12'!r},\n"
        f" 'LIBDIR': {f'{prefix}{sep}lib'!r},\n"
        f" 'LIBPC': {f'{prefix}{sep}lib{sep}pkgconfig'!r},\n"
        f" 'LIBPL': {f'{prefix}{sep}lib{sep}python3.12{sep}config-3.12-x86_64-linux-gnu'!r},\n"
        f" 'MANDIR': {f'{prefix}{sep}share{sep}man'!r},\n"
        f" 'SCRIPTDIR': {f'{prefix}{sep}lib'!r},\n"
        f" 'datarootdir': {f'{prefix}{sep}share'!r},\n"
        f" 'exec_prefix': {prefix!r},\n"
        f" 'prefix': {prefix!r},\n"
        "}\n"
    )
    code = compile(src, mod_name, "exec")
    return marshal.dumps(code)


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
    clean_sysconfig = {
        "PYZ.pyz:_sysconfigdata__linux_x86_64-linux-gnu": _marshal_sysconfigdata(
            "/opt/uv-python/cpython-3.12.15-linux-x86_64-gnu"
        )
    }
    entries = mod.check_bundle_no_direct_url(
        fake_bin, archive_entries=clean_toc, sysconfigdata_blobs=clean_sysconfig
    )
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


@pytest.mark.parametrize(
    ("mod_name", "prefix", "expected_fragment"),
    [
        (
            "_sysconfigdata__linux_x86_64-linux-gnu",
            "/"
            + "/".join(
                ("home", "runner", "work/_temp/uv-python-dir/cpython-3.12.15-linux-x86_64-gnu")
            ),
            "/" + "/".join(("home", "runner", "")),
        ),
        (
            "_sysconfigdata__linux_x86_64-linux-gnu",
            "/"
            + "/".join(
                ("HOME", "Builder", ".local/share/uv/python/cpython-3.12.13-linux-x86_64-gnu")
            ),
            "/" + "/".join(("HOME", "Builder", "")),
        ),
        (
            "_sysconfigdata__darwin_darwin",
            "/"
            + "/".join(
                ("Users", "runner", ".local/share/uv/python/cpython-3.12.15-macos-aarch64-none")
            ),
            "/" + "/".join(("Users", "runner", "")),
        ),
        (
            "_sysconfigdata__darwin_darwin",
            "/" + "/".join(("users", "macbuilder", "uv/python/cpython-3.12.15")),
            "/" + "/".join(("users", "macbuilder", "")),
        ),
        (
            "_sysconfigdata__win32_",
            "\\".join(
                (
                    "C:",
                    "Users",
                    "runneradmin",
                    r"AppData\Roaming\uv\python\cpython-3.12.15-windows-x86_64-none",
                )
            ),
            "\\".join(("C:", "Users", "runneradmin", "")),
        ),
        (
            "_sysconfigdata__win32_",
            "/".join(("c:", "users", "dev_user", "appdata/roaming/uv/python/cpython-3.12.15")),
            "/".join(("c:", "users", "dev_user", "")),
        ),
    ],
)
def test_check_bundle_fails_when_sysconfigdata_contains_home_path(
    tmp_path: Path, mod_name: str, prefix: str, expected_fragment: str
) -> None:
    mod = _load_check_bundle_module()
    fake_bin = tmp_path / "xrpl-camp-1.5.1-linux-x64"
    fake_bin.write_bytes(b"fake")

    clean_toc = ["PYZ.pyz", "xrpl_camp-1.5.1.dist-info/METADATA"]
    leaked_blob = _marshal_sysconfigdata(prefix, mod_name=f"{mod_name}.py")

    with pytest.raises(RuntimeError, match="_sysconfigdata") as exc_info:
        mod.check_bundle_no_direct_url(
            fake_bin,
            archive_entries=clean_toc,
            sysconfigdata_blobs={f"PYZ.pyz:{mod_name}": leaked_blob},
        )
    assert expected_fragment in str(exc_info.value)


@pytest.mark.parametrize(
    ("mod_name", "prefix"),
    [
        (
            "_sysconfigdata__linux_x86_64-linux-gnu",
            "/opt/uv-python/cpython-3.12.15-linux-x86_64-gnu",
        ),
        (
            "_sysconfigdata__darwin_darwin",
            "/opt/uv-python/cpython-3.12.15-macos-aarch64-none",
        ),
        (
            "_sysconfigdata__win32_",
            r"C:\uv-python\cpython-3.12.15-windows-x86_64-none",
        ),
        (
            "_sysconfigdata__linux_x86_64-linux-gnu",
            "/install",
        ),
    ],
)
def test_check_bundle_passes_when_sysconfigdata_has_neutral_prefix(
    tmp_path: Path, mod_name: str, prefix: str
) -> None:
    mod = _load_check_bundle_module()
    fake_bin = tmp_path / "xrpl-camp-1.5.1-linux-x64"
    fake_bin.write_bytes(b"fake")

    clean_toc = ["PYZ.pyz", "xrpl_camp-1.5.1.dist-info/METADATA"]
    clean_blob = _marshal_sysconfigdata(prefix, mod_name=f"{mod_name}.py")

    entries = mod.check_bundle_no_direct_url(
        fake_bin,
        archive_entries=clean_toc,
        sysconfigdata_blobs={f"PYZ.pyz:{mod_name}": clean_blob},
    )
    assert entries == sorted(clean_toc)


def test_check_bundle_cli_with_mocked_carchivereader_and_pyz(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    mod = _load_check_bundle_module()
    fake_bin = tmp_path / "xrpl-camp-1.5.1-linux-x64"
    fake_bin.write_bytes(b"fake")

    toc_entries: dict[str, tuple[int, int, int, int, str]] = {
        "PYZ.pyz": (0, 0, 0, 0, "z"),
        "xrpl_camp-1.5.1.dist-info/METADATA": (0, 0, 0, 0, "x"),
    }
    pyz_modules: dict[str, bytes] = {
        "_sysconfigdata__linux_x86_64-linux-gnu": _marshal_sysconfigdata(
            "/opt/uv-python/cpython-3.12.15-linux-x86_64-gnu"
        ),
        "xrpl_camp.__main__": marshal.dumps(compile("x = 1\n", "__main__.py", "exec")),
    }

    class _FakePYZReader:
        def __init__(self, modules: dict[str, bytes]) -> None:
            self.toc = {k: (0, 0, len(v)) for k, v in modules.items()}
            self._modules = modules

        def extract(self, name: str, raw: bool = False) -> bytes | None:
            assert raw is True
            return self._modules.get(name)

    class _FakeCArchiveReader:
        def __init__(self, path: str) -> None:
            self.path = path
            self.toc = dict(toc_entries)

        def open_embedded_archive(self, name: str) -> _FakePYZReader:
            assert name == "PYZ.pyz"
            return _FakePYZReader(pyz_modules)

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
    assert "no direct_url.json or _sysconfigdata home path present" in captured_ok.out
    assert "xrpl_camp-1.5.1.dist-info/METADATA" in captured_ok.out

    # Fail when PYZ _sysconfigdata has a home path
    pyz_modules["_sysconfigdata__linux_x86_64-linux-gnu"] = _marshal_sysconfigdata(
        "/home/runner/work/_temp/uv-python-dir/cpython-3.12.15-linux-x86_64-gnu"
    )
    rc_bad_sysconfig = mod.main([str(fake_bin)])
    captured_bad_sysconfig = capsys.readouterr()
    assert rc_bad_sysconfig == 1
    assert "_sysconfigdata" in captured_bad_sysconfig.err
    assert "/home/runner/" in captured_bad_sysconfig.err

    # Fail with both when direct_url.json is also present
    toc_entries["xrpl_camp-1.5.1.dist-info/direct_url.json"] = (0, 0, 0, 0, "x")
    rc_bad_both = mod.main([str(fake_bin)])
    captured_bad_both = capsys.readouterr()
    assert rc_bad_both == 1
    assert "direct_url.json" in captured_bad_both.err
    assert "_sysconfigdata" in captured_bad_both.err
