# 1.5.1 Linux build check on `854c31f`, the G1 re-check on `44dc45a`, and the released npm package

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

**G1 was open at `854c31f`.** The unpacked Linux check found the build machine's (on CI, the runner's) Python
install prefix in `_sysconfigdata`, and the PASS above doesn't cover it. The Publisher ruled to fix it, with no
exception.

**G1 is fixed at `44dc45a`** (the "G1 re-check" section below). A Linux build that follows `publish.yml`, with its new
`UV_PYTHON_INSTALL_DIR=/opt/uv-python` step, bundles a `_sysconfigdata` with no home path.
- The unpacked identity scan is the 8 third-party hits alone, with no `_sysconfigdata` hit and no build record.
- `check_bundle.py` passes it, and fails both the 1.5.0 release asset (naming `direct_url.json` and
  `_sysconfigdata`) and the `854c31f` binary.

The scan still reports 9 hits. 8 are third party. **1 is not: the build machine's home path inside `_sysconfigdata`
(G1 below).** The released 1.5.0 Linux asset carries the same `_sysconfigdata` path, as
`/home/runner/work/_temp/uv-python-dir/…`, alongside its `direct_url.json`. So a CI build of 1.5.1 will carry it too
until G1 is fixed.

**The released package, `@mcptoolshop/xrpl-camp@1.5.1`, passes on Windows and on Linux** (the
"released npm package" section below).
- `npx --yes` from fresh caches prints `xrpl-camp 1.5.1`, and the help reads `Usage: xrpl-camp …`.
- The downloaded binaries match `checksums-1.5.1.txt`.
- `check_bundle.py` passes the CI-built linux asset (exit 0). That is the CI counterpart to the local G1 check.

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

**G1 (open, being fixed before release): `_sysconfigdata` carries the builder's home path.** When uv installs Python, it writes the interpreter's
install prefix into `_sysconfigdata__linux_x86_64-linux-gnu.py`, and PyInstaller bundles that module. It shows up as
20 strings (`BINDIR`, `prefix`, `INCLUDEPY`, `DESTDIRS` …):
- on this build, under `<home>/.local/share/uv/python/cpython-3.12.13-linux-x86_64-gnu`, the WSL account on this
  rig;
- on the 1.5.0 release asset, built on CI, under `/home/runner/work/_temp/uv-python-dir/cpython-3.12.15-linux-x86_64-gnu`
  (`sysconfigdata-home-paths.txt`).

The scanner's bundle-only `/home/<account>` check reports it as `home-path`. The `direct_url.json` removal doesn't
touch it, so the CI-built 1.5.1 binary will carry `/home/runner/…` there. The escape-the-valley 1.3.1 final
candidate has the same hit (its PR #29, item 9). I haven't tested a fix.

## G1 re-check on `44dc45a` — PASS, G1 closed (`g1-44dc45a/`)

The Editor asked for this on **`44dc45a`**: `db6d63e` (the G1 fix) plus its atlas map, on top of the merged
`854c31f` receipts (`e968ddf`). The fix has two parts:
- a `publish.yml` step that sets `UV_PYTHON_INSTALL_DIR` to `/opt/uv-python` (or `C:\uv-python` on Windows)
  before `uv python install 3.12`;
- a `check_bundle.py` that also fails on a home path in the bundled `_sysconfigdata`.

It ran in WSL in a fresh clone at `44dc45a`, CPU only, with uv's concurrency capped at 12.
`harness/linux_build_151_g1.sh` is the `854c31f` script with one line added,
`export UV_PYTHON_INSTALL_DIR=/opt/uv-python`.
- **The `sudo` lines were skipped.** The workflow's step runs `sudo mkdir -p /opt/uv-python` and `sudo chown`
  unconditionally, and `sudo` here needs a password. The folder already existed and was writable
  (`00-uv-python-dir-before.txt`).
- **Python:** `uv python install 3.12` found the 3.12.13 install already in `/opt/uv-python` and used it. The venv
  reads `Using CPython 3.12.13`, and the install log has the same harmless `~/.local/bin/python3.12` warning as the
  ETV run.

`xrpl-camp-1.5.1-linux-x64` is an ELF x86-64, **19,273,240 bytes**, sha256
`979bd82108c6c24a046ef54c43df18c8051650290cfc4f1dff0e5d4b0896f9b3`. Python 3.12.13, PyInstaller 6.22.3.

| Check | Result |
|---|---|
| `scripts/check_bundle.py dist/xrpl-camp-1.5.1-linux-x64` | **exit 0**: `[bundle-check] Verified 97 archive entries in dist/xrpl-camp-1.5.1-linux-x64: no direct_url.json or _sysconfigdata home path present` |
| `scripts/check_bundle.py --list …` | **exit 0**, the 97 entries, then the same line (`08-check-bundle-list.log`) |
| `--version` | exit 0: `xrpl-camp 1.5.1` |
| `self-check` | exit 0 |
| The bundled `_sysconfigdata` (unpacked) | **0 `/home/` strings**, 20 under `/opt/uv-python/cpython-3.12.13-linux-x86_64-gnu`. The `854c31f` binary has 20 under `<home>/…`, and the 1.5.0 asset 20 under `/home/runner/…` (`sysconfigdata-prefix.txt`) |
| `identity-scan.py` on the binary | `RESULT HIT 8`, exit 1: the 8 third-party hits from `854c31f`, at the same offsets, with **no `_sysconfigdata` hit and no `build-record`** |
| **Negative control:** `check_bundle.py` on the v1.5.0 linux release asset (sha256 `12259e59…`) | **exit 1**, naming both: `BUNDLE CHECK FAILED: Bundled PEP 610 direct_url.json build record found in …: xrpl_camp-1.5.0.dist-info/direct_url.json; Home path found in bundled _sysconfigdata module in …: PYZ.pyz:_sysconfigdata__linux_x86_64-linux-gnu (20 hits, e.g. /home/runner/)` |
| **Negative control:** `check_bundle.py` on the `854c31f` binary built here (sha256 `f0efbc2a…`) | **exit 1**: `Home path found in bundled _sysconfigdata module in …: PYZ.pyz:_sysconfigdata__linux_x86_64-linux-gnu (20 hits, e.g. <home>/)` |

**The identity scan, verbatim** (`g1-44dc45a/identity-scan-151-g1-linux.txt`; paths read `<scratch>`):

```
HIT gmail <scratch>/1.5.1-g1-44dc45a/linux/xrpl-camp-1.5.1-linux-x64!carchive/base_library.zip/io.pyc:@0x847
HIT home-path <scratch>/1.5.1-g1-44dc45a/linux/xrpl-camp-1.5.1-linux-x64!carchive/base_library.zip/ntpath.pyc:@0x1976
HIT home-path <scratch>/1.5.1-g1-44dc45a/linux/xrpl-camp-1.5.1-linux-x64!carchive/libpython3.12.so.1.0:@0xe73c8c
HIT gmail <scratch>/1.5.1-g1-44dc45a/linux/xrpl-camp-1.5.1-linux-x64!carchive/libpython3.12.so.1.0:@0xe63b77
HIT gmail <scratch>/1.5.1-g1-44dc45a/linux/xrpl-camp-1.5.1-linux-x64!pyz/PYZ.pyz/bz2.pyc-body:@0x1b9
HIT gmail <scratch>/1.5.1-g1-44dc45a/linux/xrpl-camp-1.5.1-linux-x64!pyz/PYZ.pyz/httpx/_urls.pyc-body:@0x320a
HIT gmail <scratch>/1.5.1-g1-44dc45a/linux/xrpl-camp-1.5.1-linux-x64!pyz/PYZ.pyz/pygments/lexers/gdscript.pyc-body:@0x111
HIT gmail <scratch>/1.5.1-g1-44dc45a/linux/xrpl-camp-1.5.1-linux-x64!pyz/PYZ.pyz/rich/_spinners.pyc-body:@0x448
RESULT HIT 8
```

They are the third-party lines in the table above: CPython's `io` and `bz2` author lines and `splitroot()`
docstring, plus the httpx, pygments and rich lines. Under the Director's ruling, a release with third-party hits
still needs his written exception naming them.

**What the re-check doesn't cover:** the macOS and Windows legs, and the workflow's `sudo mkdir` / `chown` lines.

## The released npm package, `@mcptoolshop/xrpl-camp@1.5.1` — PASS (`npm-release/`)

1.5.1 is released: tag `v1.5.1` on `07ffbb6`, the npm package, and the GitHub release assets. This repeats the
1.5.0 npm check from fresh state, in an empty working folder:
- `npm_config_cache` and `npm_config_prefix` are new folders;
- the launcher's binary cache is new too: `LOCALAPPDATA` on Windows, `XDG_CACHE_HOME` on Linux.

So the first `npx` call downloads the binary from the v1.5.1 release and checks it against `checksums-1.5.1.txt`.
- **Windows:** native, Node 22.22.3, npm 10.9.8 (`harness/npm_release_check_win.sh`).
- **Linux:** WSL Ubuntu 26.04, with the official Node 22.22.3 in `~/opt` (`harness/wsl_node.sh`,
  `harness/npm_release_check.sh`).

| Check | Windows | Linux |
|---|---|---|
| `npx --yes @mcptoolshop/xrpl-camp@1.5.1 --version` | exit 0, `xrpl-camp 1.5.1` | exit 0, `xrpl-camp 1.5.1` |
| `--help` | exit 0, `Usage: xrpl-camp [OPTIONS] COMMAND [ARGS]...`, listing `reserve`, `certificate` and `proof` | the same |
| `reserve --help`, `certificate --help`, `proof verify --help` | exit 0. `certificate` has `--format` (json, or text); `proof verify` has `--online`, and `--record` "(requires --online)" | the same |
| The cached binary | `xrpl-camp-1.5.1-win-x64.exe`, sha256 `049cbf73…`, **equal to `checksums-1.5.1.txt`** | `xrpl-camp-1.5.1-linux-x64`, sha256 `038fbecb…`, **equal to `checksums-1.5.1.txt`** |
| **argv[0] control:** the cached binary run directly | `Usage: xrpl-camp-1.5.1-win-x64.exe …` | `Usage: xrpl-camp-1.5.1-linux-x64 …` |

The direct runs show the file name, so the `xrpl-camp` in every launcher run comes from the launcher setting argv[0].
The launcher's stderr reads `Fetching checksums …`, `Downloading …`, `Verifying SHA256...`, `Ready.` on the first
call. Windows also has npm's "new major version" notice.

**`check_bundle.py` on the CI-built Linux asset.** I ran it from the `v1.5.1` tag (`07ffbb6`), in a venv with
PyInstaller.
- On `xrpl-camp-1.5.1-linux-x64` downloaded straight from the release (sha256 `038fbecb…`, the checksum line):
  **exit 0**, `[bundle-check] Verified 97 archive entries in …: no direct_url.json or _sysconfigdata home path present`.
- On the launcher's cached copy: the same, exit 0.

The asset's unpacked identity scan (`identity-scan-release-linux.txt`) is `RESULT HIT 8`, with no `_sysconfigdata`
hit and no build record. These are the same 8 third-party members as the local G1 build. The two libpython offsets
differ (`0x58857c`, `0x578467`), as they did on the 1.5.0 asset, which CI built on a newer 3.12.

**What it doesn't cover:** macOS (darwin-arm64) didn't run, so the darwin asset and its checksum line weren't
exercised. No lesson ran from the npm channel; the 1.5.0 live check covers those on the Python install.

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
- `npm-release/`:
  - `win/` and `linux/`: each `npx` call as `.cmd`, `.out`, `.err` and `.exit`; the cached file list and sha256;
    the direct-binary control; and `node-version.txt`;
  - `linux/` also has the tag head, the release asset's sha256, and the two `check_bundle.py` runs (`09-`, `10-`);
  - `checksums-1.5.1.txt` (from the release), `identity-scan-release-linux.txt`, and `harness/`.
- `g1-44dc45a/`: `linux-build/` (each step's `.log` and `.exit` 01–12, the two negative controls and their hashes,
  `00-uv-python-dir-before.txt`, the binary's hash, `file` type and versions), `identity-scan-151-g1-linux.txt` and
  `sysconfigdata-prefix.txt`.
- `harness/`: `linux_build_151_g1.sh` and `_run_151_g1.sh` (the G1 re-check), `linux_build_151.sh` and `_run_151.sh` (the build and the 1.5.0 download), plus
  `unpack_pyinstaller` and `hit_context_scan` as `.py.txt`, which keeps them out of `ruff check .`.
