# Building Standalone Binaries

This project uses [PyInstaller](https://pyinstaller.org/) to create standalone
binaries for distribution via `npx @mcptoolshop/xrpl-camp`.

## Quick Build (local)

```bash
uv venv && uv pip install . "pyinstaller>=6.9.0"
uv run pyinstaller --onefile --name xrpl-camp --console \
  --collect-submodules rich \
  --collect-data xrpl \
  xrpl_camp/__main__.py
```

The binary lands in `dist/xrpl-camp` (or `dist/xrpl-camp.exe` on Windows).

## CI Build

The GitHub Actions workflow `.github/workflows/publish.yml` runs automatically
when a version tag (`v*`) is pushed. It builds for three platforms, uploads
binaries + checksums to the GitHub Release, publishes to PyPI, and then
verifies that PyPI actually serves the version the tag claims.

Those steps used to live in two files, and the split is why PyPI served 1.1.0
for five months while the repo moved on. `release-binaries.yml` created the
GitHub Release authenticated as `GITHUB_TOKEN`, and GitHub does not cascade
workflow triggers from `GITHUB_TOKEN`-raised events — so `publish.yml`'s
`on: release: published` trigger never fired, silently, with nothing going red.
Merging them removed the cross-workflow event dependency instead of working
around it.

**The filename `publish.yml` is load-bearing.** PyPI Trusted Publishing
authenticates against the exact workflow filename plus the `pypi` environment
name, so renaming the file breaks publishing in a way that does not surface
until the next release is cut.

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

## Why `--collect-data xrpl`?

The `xrpl-py` library ships JSON data files (e.g. `definitions.json` for the
binary codec). PyInstaller doesn't include data files by default, so without
`--collect-data xrpl` the binary will crash with `FileNotFoundError` when
accessing XRPL binary codec functions or the `self-check` command.

## Why `pyinstaller>=6.9.0`?

PyInstaller 6.8.0 has a bug where `collect_submodules()` rejects module names
containing hyphens (like `unicode17-0-0`). This was fixed in
[PyInstaller 6.9.0](https://github.com/pyinstaller/pyinstaller/issues/8591).

**Do not downgrade below 6.9.0** or the binaries will crash with:

```
ModuleNotFoundError: No module named 'rich._unicode_data.unicode17-0-0'
```
