# Building Standalone Binaries

This project uses [PyInstaller](https://pyinstaller.org/) to create standalone
binaries for distribution via `npx @mcptoolshop/xrpl-camp`.

## Quick Build (local)

```bash
uv venv && uv pip install . "pyinstaller>=6.9.0"
uv run pyinstaller --onefile --name xrpl-camp --console \
  --collect-submodules rich \
  xrpl_camp/__main__.py
```

The binary lands in `dist/xrpl-camp` (or `dist/xrpl-camp.exe` on Windows).

## CI Build

The GitHub Actions workflow `.github/workflows/release-binaries.yml` runs
automatically when a version tag (`v*`) is pushed. It builds for three
platforms and uploads binaries + checksums to the GitHub Release.

## Why `--collect-submodules rich`?

Rich loads Unicode cell-width tables dynamically via
`importlib.import_module()` at runtime:

```python
# rich/_unicode_data/__init__.py
module = import_module(f".unicode{version}", "rich._unicode_data")
```

PyInstaller's static analysis cannot detect dynamic imports, so the
`rich/_unicode_data/unicode17-0-0.py` (and friends) are excluded from the
bundle. The `--collect-submodules rich` flag forces PyInstaller to include
all Rich submodules.

## Why `pyinstaller>=6.9.0`?

PyInstaller 6.8.0 has a bug where `collect_submodules()` rejects module names
containing hyphens (like `unicode17-0-0`). This was fixed in
[PyInstaller 6.9.0](https://github.com/pyinstaller/pyinstaller/issues/8591).

**Do not downgrade below 6.9.0** or the binaries will crash with:

```
ModuleNotFoundError: No module named 'rich._unicode_data.unicode17-0-0'
```
