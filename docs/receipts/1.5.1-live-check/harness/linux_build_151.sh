#!/usr/bin/env bash
# publish.yml build-binaries job (854c31f shape), linux-x64 leg, step by step, in WSL.
# Usage (inside WSL): bash linux_build_151.sh <checkout> <out-dir> <neg-control-binary>
set -u
src=$1; out=$2; neg=$3
mkdir -p "$out"
cd "$src" || exit 2
export UV_CONCURRENT_INSTALLS=12 UV_CONCURRENT_BUILDS=12 UV_CONCURRENT_DOWNLOADS=12
VERSION=1.5.1; TARGET=linux-x64; EXT=""
OUTNAME="xrpl-camp-${VERSION}-${TARGET}${EXT}"
step() { local name=$1; shift; { echo "+ $*"; "$@"; } > "$out/$name.log" 2>&1; local rc=$?; echo "$rc" > "$out/$name.exit"; echo "$name: exit $rc"; }
git rev-parse HEAD > "$out/head.txt"; uv --version > "$out/uv-version.txt"
step 01-python-install uv python install 3.12
# The workflow's bare `uv venv` gets 3.12 on a fresh runner; pinned here because this machine has newer managed Pythons.
step 02-venv uv venv -p 3.12
step 03-install uv pip install . "pyinstaller>=6.9.0,<7.0"
step 04-remove-direct-url uv run --no-sync python -c '
import pathlib, sysconfig
purelib = pathlib.Path(sysconfig.get_path("purelib"))
for p in purelib.glob("*.dist-info/direct_url.json"):
    p.unlink()
remaining = list(purelib.glob("*.dist-info/direct_url.json"))
if remaining:
    raise SystemExit(f"direct_url.json still present in venv: {remaining}")
print("Removed direct_url.json from build venv.")
'
step 05-pyinstaller uv run --no-sync pyinstaller --onefile --name "xrpl-camp" --console --collect-submodules rich --collect-data xrpl xrpl_camp/__main__.py
step 06-rename mv "dist/xrpl-camp${EXT}" "dist/${OUTNAME}"
step 07-check-bundle uv run --no-sync python scripts/check_bundle.py "dist/$OUTNAME"
step 08-check-bundle-list uv run --no-sync python scripts/check_bundle.py --list "dist/$OUTNAME"
step 09-neg-control-150 uv run --no-sync python scripts/check_bundle.py "$neg"
step 10-version "dist/$OUTNAME" --version
step 11-self-check "dist/$OUTNAME" self-check
uv run --no-sync python -c "import sys, PyInstaller; print(sys.version); print('PyInstaller', PyInstaller.__version__)" > "$out/versions.txt" 2>&1
(cd dist && sha256sum "$OUTNAME" && stat -c '%n %s bytes' "$OUTNAME") > "$out/dist-sha256.txt" 2>&1
file "dist/$OUTNAME" > "$out/file.txt" 2>&1
cp "dist/$OUTNAME" "$out/"
