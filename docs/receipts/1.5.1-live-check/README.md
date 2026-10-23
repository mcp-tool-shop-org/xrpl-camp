# 1.5.1 Linux build check on `854c31f`

This is the check the Editor asked for on **`854c31f`** (PR #25, `fix/1.5.1-build-record` → `main`). 1.5.1 removes
the PEP 610 `direct_url.json` build record from the build venv before PyInstaller runs, and adds
`scripts/check_bundle.py` to fail a build whose bundle still carries one.

- **Where:** WSL (Ubuntu 26.04), in a fresh clone at `854c31f`, CPU only, with uv's concurrency capped at 12 of 24
  cores. uv 0.11.18, Python 3.12.13, PyInstaller 6.22.3.
- **What:** `harness/linux_build_151.sh` runs the linux-x64 leg of `publish.yml`'s `build-binaries` job step by
  step:
  1. `uv python install 3.12`, the venv, and `uv pip install . "pyinstaller>=6.9.0,<7.0"`;
  2. the `direct_url.json` removal step;
  3. `uv run --no-sync pyinstaller --onefile --name xrpl-camp --console --collect-submodules rich --collect-data xrpl xrpl_camp/__main__.py`;
  4. the rename, then `check_bundle.py`.

  Each step writes a `.log` and an `.exit` (`linux-build/`).
- **Two differences from CI:**
  - `uv venv -p 3.12` where the workflow has a bare `uv venv`, because this machine has newer managed Pythons.
  - The workflow doesn't pin uv or the Python patch level. This rig's uv gave 3.12.13; the 1.5.0 release was built
    on 3.12.15.
- **Redaction:** no seeds or wallet files are here (this check makes none). Paths read `<scratch>` or `<home>`.

## Verdict

**PASS on the brief.**
- `check_bundle.py` finds no `direct_url.json` in the 1.5.1 binary, and it fails the 1.5.0 release asset, which has
  one.
- `--version` prints `xrpl-camp 1.5.1`.
- The identity scan on the unpacked binary has **no `build-record`**, and the same scan of the 1.5.0 asset has one.

The scan still reports 9 hits. 8 are third party. **1 is not: the build machine's home path inside `_sysconfigdata`
(G1 below).** The released 1.5.0 asset carries it as `/home/runner/…`, so a CI build of 1.5.1 will too.

## The build

`xrpl-camp-1.5.1-linux-x64` is an ELF x86-64, **19,272,832 bytes**, sha256
`f0efbc2a1b88be7d5d5d3739311f230af1f806b97fde3f02c66261acb748fda5` (`linux-build/dist-sha256.txt`). Every step
exits 0 except the negative control, which is meant to fail.

| Check | Result |
|---|---|
| `direct_url.json` removal | exit 0: `Removed direct_url.json from build venv.` |
| `scripts/check_bundle.py dist/xrpl-camp-1.5.1-linux-x64` | **exit 0**: `[bundle-check] Verified 97 archive entries in dist/xrpl-camp-1.5.1-linux-x64: no direct_url.json present` |
| `scripts/check_bundle.py --list …` | **exit 0**, the 97 entries, then the same line (`08-check-bundle-list.log`) |
| **Negative control:** `check_bundle.py` on the v1.5.0 release asset `xrpl-camp-1.5.0-linux-x64` | **exit 1**: `BUNDLE CHECK FAILED: Bundled PEP 610 direct_url.json build record found in …/xrpl-camp-1.5.0-linux-x64: xrpl_camp-1.5.0.dist-info/direct_url.json` |
| The 1.5.0 asset is the released one | sha256 `12259e59…`, equal to the `checksums-1.5.0.txt` line on the v1.5.0 release (`neg-control-150-sha256.txt`) |
| `--version` | exit 0: `xrpl-camp 1.5.1` |
| `self-check` | exit 0: `Version 1.5.1`, `Python 3.12.13`, Testnet endpoint reachable, `network_id 1` |

- **The removal has a positive control.** The 1.5.0 asset's `direct_url.json` reads
  `{"url":"file:///home/runner/work/xrpl-camp/xrpl-camp","dir_info":{"editable":true}}`.
- **What stays in the 1.5.1 dist-info:** `uv_build.json` and `uv_cache.json` are still bundled
  (`dist-info-uv-files.txt`). Neither holds a path. `uv_build.json` is `{}`, and `uv_cache.json` holds the build's
  timestamp, with `commit`, `tags`, `env` and `src` all empty.

## The identity scan

The scan is `identity-scan.py` on the binary itself, which unpacks it. Verbatim (`identity-scan-151-linux.txt`):

```
HIT gmail <scratch>/1.5.1-854c31f/linux/xrpl-camp-1.5.1-linux-x64!carchive/base_library.zip/io.pyc:@0x847
HIT home-path <scratch>/1.5.1-854c31f/linux/xrpl-camp-1.5.1-linux-x64!carchive/base_library.zip/ntpath.pyc:@0x1976
HIT home-path <scratch>/1.5.1-854c31f/linux/xrpl-camp-1.5.1-linux-x64!carchive/libpython3.12.so.1.0:@0xe73c8c
HIT gmail <scratch>/1.5.1-854c31f/linux/xrpl-camp-1.5.1-linux-x64!carchive/libpython3.12.so.1.0:@0xe63b77
HIT gmail <scratch>/1.5.1-854c31f/linux/xrpl-camp-1.5.1-linux-x64!pyz/PYZ.pyz/bz2.pyc-body:@0x1b9
HIT home-path <scratch>/1.5.1-854c31f/linux/xrpl-camp-1.5.1-linux-x64!pyz/PYZ.pyz/_sysconfigdata__linux_x86_64-linux-gnu.pyc-body:@0x2c42
HIT gmail <scratch>/1.5.1-854c31f/linux/xrpl-camp-1.5.1-linux-x64!pyz/PYZ.pyz/httpx/_urls.pyc-body:@0x320a
HIT gmail <scratch>/1.5.1-854c31f/linux/xrpl-camp-1.5.1-linux-x64!pyz/PYZ.pyz/pygments/lexers/gdscript.pyc-body:@0x111
HIT gmail <scratch>/1.5.1-854c31f/linux/xrpl-camp-1.5.1-linux-x64!pyz/PYZ.pyz/rich/_spinners.pyc-body:@0x448
RESULT HIT 9
```

The 1.5.0 release asset gives `RESULT HIT 10`. It has the same 9 hits plus
`HIT build-record …!carchive/xrpl_camp-1.5.0.dist-info/direct_url.json` (`identity-scan-150-linux-control.txt`).
So the build-record line is gone in 1.5.1, and nothing else changed.

I read the bytes around each hit in the unpacked bundle (`harness/unpack_pyinstaller.py.txt`,
`harness/hit_context_scan.py.txt`). Third-party addresses aren't repeated here.

| Member | What is there | Whose |
|---|---|---|
| `carchive/base_library.zip/io.pyc`, and again in `libpython3.12.so.1.0` | the `io` module's author line | third party: CPython |
| `carchive/base_library.zip/ntpath.pyc`, and again in `libpython3.12.so.1.0` | the `splitroot()` docstring example of a Windows profile path | third party: CPython |
| `pyz/PYZ.pyz/bz2.pyc-body` | the `bz2` module's author line | third party: CPython |
| `pyz/PYZ.pyz/httpx/_urls.pyc-body` | a docstring example address | third party: httpx |
| `pyz/PYZ.pyz/pygments/lexers/gdscript.pyc-body` | the GDScript lexer's author line | third party: pygments |
| `pyz/PYZ.pyz/rich/_spinners.pyc-body` | the MIT licence line of the spinners data | third party: rich |
| **`pyz/PYZ.pyz/_sysconfigdata__linux_x86_64-linux-gnu.pyc-body`** | **the build machine's home path** (G1) | **the builder** |

**G1: `_sysconfigdata` carries the builder's home path.** When uv installs Python, it writes the interpreter's
install prefix into `_sysconfigdata__linux_x86_64-linux-gnu.py`, and PyInstaller bundles that module. It shows up as
20 strings (`BINDIR`, `prefix`, `INCLUDEPY`, `DESTDIRS` …):
- on this build, under `<home>/.local/share/uv/python/cpython-3.12.13-linux-x86_64-gnu`, the WSL account on this
  rig;
- on the 1.5.0 release asset, built on CI, under `/home/runner/work/_temp/uv-python-dir/cpython-3.12.15-linux-x86_64-gnu`
  (`sysconfigdata-home-paths.txt`).

The scanner's bundle-only `/home/<account>` check reports it as `home-path`. The `direct_url.json` removal doesn't
touch it, so the CI-built 1.5.1 binary will carry `/home/runner/…` there. The escape-the-valley 1.3.1 final
candidate has the same hit (its PR #29, item 9). I haven't tested a fix.

## What this doesn't cover

- macOS (darwin-arm64) didn't run. Its `_sysconfigdata` would hold the macOS runner's home path, but that is
  untested.
- The Windows leg didn't run.
- The binaries aren't committed.

## Files

- `linux-build/`: each step's `.log` and `.exit` (01–11), `head.txt`, `uv-version.txt`, `versions.txt`,
  `dist-sha256.txt`, `file.txt` and `neg-control-150-sha256.txt`.
- `identity-scan-151-linux.txt`, `identity-scan-150-linux-control.txt`, `sysconfigdata-home-paths.txt`,
  `dist-info-uv-files.txt`.
- `harness/`: `linux_build_151.sh` and `_run_151.sh` (the build and the 1.5.0 download), plus
  `unpack_pyinstaller` and `hit_context_scan` as `.py.txt`, which keeps them out of `ruff check .`.
