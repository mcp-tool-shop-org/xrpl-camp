# 1.5.2 live check on `4a7ff84`

The Editor asked for this on **`4a7ff84`** (PR #31, `fix/1.5.2` → `main`, base `1cab0cb`). CPU only; uv's
concurrency was capped at 12 of 24 cores. macOS was not run, and neither was a Windows binary build.

## Verdict

**PASS on all three items.**

1. **The Linux build.** It follows the updated `publish.yml`, and it passes:
   - `check_bundle.py` exits 0;
   - `--version` prints `xrpl-camp 1.5.2`;
   - the unpacked identity scan has the 8 third-party hits alone, with no `_sysconfigdata` hit and no build record.
2. **#20.1:** `xrpl-camp reserve --json` against Testnet now carries `"reserve_measured": true`.
3. **#17:** `proof verify … --online --json` behaves as asked:
   - the top-level `message` drops the "Run this same command with --online" sentence and carries the ledger's
     verdict instead;
   - `online.checked` counts the lookups (1 on a contradicted pack; the changelog says 1.5.1 gave 0, which this check did not re-run);
   - `file` and `folder` use `/` on Windows.

## 1. Linux build (`linux-build/`, `identity-scan-152-linux.txt`)

**Where:** WSL (Ubuntu 26.04), in a fresh clone of `4a7ff84`, with uv 0.11.18, CPython 3.12.13 and PyInstaller
6.22.3 (`versions.txt`).

**What:** `harness/linux_build_152.sh` runs the linux-x64 leg of `publish.yml`'s `build-binaries` job, step by step:
1. `UV_PYTHON_INSTALL_DIR=/opt/uv-python`;
2. `uv python install 3.12.13`, then `uv venv --python 3.12.13 --managed-python`;
3. `uv pip install . "pyinstaller>=6.9.0,<7.0"`;
4. the `direct_url.json` removal;
5. `uv run --no-sync pyinstaller --onefile --name xrpl-camp --console --collect-submodules rich --collect-data xrpl xrpl_camp/__main__.py`;
6. the rename, then `check_bundle.py`.

Each step writes a `.log` and an `.exit`.

**Differences from CI:**
- The workflow's `sudo mkdir -p /opt/uv-python` and `chown` were skipped, because `sudo` needs a password here. The
  folder already exists and is writable (`00-uv-python-dir-before.txt`).
- `/opt/uv-python` already held a 3.12.13 install with a neutral prefix, so `uv python install 3.12.13` reused it.
- That step also printed one warning: uv couldn't link `~/.local/bin/python3.12`, because a file it doesn't manage is
  already there. That comes from this machine, not the build, and the step exits 0.

**The binary:** `xrpl-camp-1.5.2-linux-x64` is an ELF x86-64, **19,275,760 bytes**, sha256
`35c205f008aba79b5e75d6e159a362a5f572881425def503fc3ce9c53b9741d8`. Every step exits 0 except the negative control,
which is meant to fail.

| Check | Result |
|---|---|
| `scripts/check_bundle.py dist/xrpl-camp-1.5.2-linux-x64` | **exit 0**: `Verified 97 archive entries …: no direct_url.json or _sysconfigdata home path present` |
| **Negative control:** `check_bundle.py` on the v1.5.0 release asset | **exit 1**. It names both the `direct_url.json` and the `_sysconfigdata` home path (`/home/runner/`, 20 hits). sha256 in `neg-control-sha256.txt` |
| `--version` | exit 0: `xrpl-camp 1.5.2` |
| `self-check` | exit 0. The endpoint is Testnet (network_id 1) |
| Unpacked identity scan (the Publisher's `identity-scan.py`, sha256 `4d9a3c90…`) | `RESULT HIT 8`: the same eight members, kinds and offsets as the `44dc45a` G1 build |

The 8 hits are the third-party set that already goes to the Director in one exception question:

| Member | Offset | Library |
|---|---|---|
| `base_library.zip/io.pyc` | 0x847 | CPython |
| `base_library.zip/ntpath.pyc` | 0x1976 | CPython |
| `libpython3.12.so.1.0` | 0xe73c8c, 0xe63b77 | CPython |
| `PYZ.pyz/bz2.pyc` | 0x1b9 | CPython |
| `PYZ.pyz/httpx/_urls.pyc` | 0x320a | httpx |
| `PYZ.pyz/pygments/lexers/gdscript.pyc` | 0x111 | pygments |
| `PYZ.pyz/rich/_spinners.pyc` | 0x448 | rich |

## 2. #20.1 on Testnet (`testnet/course/`, `testnet/reserve/`)

The CLI is a non-editable install of a clean `4a7ff84` worktree on Windows (Python 3.12, `testnet/code.txt`). The
endpoint is the default Testnet URL, and the CLI's own `check_endpoint()` passes (`preflight.txt`).

1. `xrpl-camp --yes start` ran the course with a fresh faucet wallet. It exits 0 in 30 s and writes the proof pack
   used in item 3.
2. `xrpl-camp --yes reserve --json` ran **once**. It exits 0 with one JSON document (`10-parse-check.txt`):
   - `"reserve_measured": true`, `"ok": true`, `"simulated": false`, `"network": "testnet"`;
   - the mint `1A08DAFB…` is `tesSUCCESS`, owner count 0 → 1, `reserve_delta` 200000, status `locked`;
   - the burn `6878D4F8…` is `tesSUCCESS`, owner count 1 → 0, `reserve_delta` −200000, status `released`;
   - `net_reserve_delta` is 0.

The `false` branch (the ledger read after the mint doesn't show it yet) and an empty `TransactionResult` from
`submit_and_wait` can't be forced against a live server. The unit tests in `tests/test_v152_fixes.py` cover them.

## 3. #17: `proof verify --online --json` (`testnet/verify/`)

`packs/` holds two packs:
- `honest.json`, the pack from item 2's course run;
- `forged.json`, a copy whose lesson 4 txid is swapped for the reserve mint's txid. `harness/forge_pack.py.txt`
  then re-seals the hash with the tool's own code, so the offline hash check passes and only the ledger can tell.

Every command runs from `testnet/verify/` with a relative path. `harness/parse_verify_152.py.txt` reads each output
into `30-parse-check.txt`.

| Command | Exit | `file` | `online.status` / `checked` / `total_lookups` | `message` |
|---|---|---|---|---|
| `proof verify packs --online --json` (folder) | 1 | `packs/forged.json`, `packs/honest.json`; `folder` is `packs` | forged: `contradicted` / **1** / 1; honest: `confirmed` / 1 / 1 | the hash result plus the ledger's verdict, with no `--online` sentence |
| `proof verify packs\honest.json --online --json` | 0 | `packs/honest.json` | `confirmed` / 1 / 1 | "… match their own recorded hash. All 1 recorded transactions are on the ledger, were sent by this pack's address, and closed successfully." |
| `proof verify packs\forged.json --online --json` | 1 | `packs/forged.json` | `contradicted` / **1** / 1 | "… match their own recorded hash. 1 of 1 transactions do not match what the ledger says. The ledger is the authority here, not this file." |
| **Control:** `proof verify packs\honest.json --json` (offline) | 0 | `packs/honest.json` | none | keeps "Run this same command with --online …", which is right without `--online` |

- The single-file runs pass the path with a backslash (`packs\honest.json`), and `file` still comes back with `/`.
- No output has a backslash in `file`.
- `24-folder-online-human.out` is the same folder check without `--json`, for reference.

## Redaction

- **Wallet:** the course wallet's home was in the session scratchpad and isn't here.
  - The only wallet trace is the line `Seed saved to <scratch>/home152/wallet.json`.
  - A check of every file here for the wallet's seed value, and for any seed-shaped string, found none.
- **Paths:** they read `<scratch>`, `<home>` or `<worktree>`, and the `ls` owner columns read `<user>`.
- **Scans:** the identity scan of this folder is `RESULT CLEAN`. The binary itself isn't committed.
