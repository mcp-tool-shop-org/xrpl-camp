# The released npm package, `@mcptoolshop/xrpl-camp@1.6.0`

The Publisher asked for this after the release: tag `v1.6.0` on `3c4ad65`, and npm `@mcptoolshop/xrpl-camp` 1.6.0.
It is the same check as 1.5.1's and 1.5.2's, run on 2026-11-13.

**macOS was not run.** There is no Mac on this rig, so the `darwin-arm64` asset is unchecked: its line in
`checksums-1.6.0.txt` is recorded here, and nothing else about it is claimed.

## Verdict

**PASS on Windows and on Linux (WSL).**
- `npx --yes @mcptoolshop/xrpl-camp@1.6.0` from fresh caches prints `xrpl-camp 1.6.0`, and the help reads
  `Usage: xrpl-camp …`.
- The binaries the launcher downloaded match `checksums-1.6.0.txt` from the v1.6.0 release.
- `check_bundle.py` from the v1.6.0 tag passes the linux asset (exit 0).
- The 1.6.0 behaviour comes through the npm binary, live against Testnet: a history miss only the pack claims reads
  `history_unconfirmed` with `history_signal` `pack_claim`, exit 3.

## How

Fresh state on each platform:
- **npm cache and prefix:** fresh, set with `npm_config_cache` and `npm_config_prefix`.
- **Launcher cache:** `LOCALAPPDATA` on Windows, `XDG_CACHE_HOME` on Linux.
- **Node:** v26.13.1 with npm 11.20.0 on Windows; v22.22.3 with npm 10.9.8 in WSL, which uses its own Node
  (`win/node-version.txt`, `linux/node-version.txt`).

The scripts are in `harness/`: `npm_release_check_win.sh` (Git Bash), `npm_release_check.sh` and
`_run_npm160_linux.sh` (WSL).

## Results

| Check | Windows (`win/`) | Linux (`linux/`) |
|---|---|---|
| `--version` | exit 0: `xrpl-camp 1.6.0` | exit 0: `xrpl-camp 1.6.0` |
| `--help`, `reserve --help`, `certificate --help`, `proof verify --help` | all exit 0; help reads `Usage: xrpl-camp …` | the same |
| Cached binary sha256 vs `checksums-1.6.0.txt` | `b35c9e05…cf61195` for `xrpl-camp-1.6.0-win-x64.exe`: **matches** | `80ce71a0…c5afc7` for `xrpl-camp-1.6.0-linux-x64`: **matches** |
| **argv[0] control:** the cached binary run directly | help reads `Usage: xrpl-camp-1.6.0-win-x64.exe …`, so `xrpl-camp` comes from the launcher | `Usage: xrpl-camp-1.6.0-linux-x64 …` |
| `check_bundle.py --list` from the v1.6.0 tag (`08-tag-head.txt` = `3c4ad65…`) | not run on Windows | **exit 0** on the asset downloaded from the release and on the launcher's cached copy: 107 archive entries, no `direct_url.json` and no `_sysconfigdata` home path |

The Publisher scanned the published wheel, sdist and npm tarball before announcing the release; that scan is not
repeated here.

## The 1.6.0 verdicts through the npm binary (`verify/`)

Run with the Windows check's caches, so it is the binary checked above, against the public Testnet. The packs are
the ones from the release's own live check (`../README.md`): the honest pack from a real course run, and forgeries of
it re-sealed with the tool's own code. They are in the session scratchpad and are not here.

| Command | File | Exit | `online.status` | `history_signal` |
|---|---|---|---|---|
| `self-check` | `verify/08-self-check.*` | 0 | reports `Version 1.6.0` | |
| `proof verify packs/honest.json --online --json` | `verify/09-verify-honest.*` | **0** | `confirmed` | "" |
| `proof verify packs/fake_txid_future_ledger.json --online --json` | `verify/10-verify-unconfirmed.*` | **3** | `history_unconfirmed` | `pack_claim` |
| `proof verify packs/fake_txid.json --online --json` | `verify/11-verify-fake.*` | **1** | `contradicted` | "" |

These are the same results as the source check on `c10abfb`. As recorded there, the unconfirmed pack's JSON still
reads `"valid": true`: `valid` means "not contradicted", not "verified" (see the handbook's proof-pack page).

## Redaction

- Paths read `<scratch>` or `<home>`.
- The npm and launcher caches and the binaries aren't committed.
- A check of every file here for any seed-shaped string found none.
- The identity scan of this folder is `RESULT CLEAN`.
