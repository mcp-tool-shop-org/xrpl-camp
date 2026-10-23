# The released npm package, `@mcptoolshop/xrpl-camp@1.5.2`

The Editor asked for this after the release: tag `v1.5.2` on `5999be0`, and npm `@mcptoolshop/xrpl-camp` 1.5.2.
It is the same check as 1.5.1's. macOS was not run.

## Verdict

**PASS on Windows and on Linux (WSL).**
- `npx --yes @mcptoolshop/xrpl-camp@1.5.2` from fresh caches prints `xrpl-camp 1.5.2`, and the help reads
  `Usage: xrpl-camp …`.
- The binaries the launcher downloaded match `checksums-1.5.2.txt` from the v1.5.2 release.
- `check_bundle.py` from the v1.5.2 tag passes the linux asset (exit 0).
- The optional check: `reserve --json` through the npm binary on Testnet carries `"reserve_measured": true`.

## How

Fresh state on each platform:
- **npm cache and prefix:** fresh, set with `npm_config_cache` and `npm_config_prefix`.
- **Launcher cache:** `LOCALAPPDATA` on Windows, `XDG_CACHE_HOME` on Linux.
- **Node:** v22.22.3 with npm 10.9.8 on both. WSL uses its own Node, from `~/opt` (`node-version.txt`).

The scripts are in `harness/`: `npm_release_check_win.sh` (Git Bash), `npm_release_check.sh` and
`_run_npm152_linux.sh` (WSL).

## Results

| Check | Windows (`win/`) | Linux (`linux/`) |
|---|---|---|
| `--version` | exit 0: `xrpl-camp 1.5.2` | exit 0: `xrpl-camp 1.5.2` |
| `--help`, `reserve --help`, `certificate --help`, `proof verify --help` | all exit 0; help reads `Usage: xrpl-camp …` | the same |
| Cached binary sha256 vs `checksums-1.5.2.txt` | `91539ce7…a99076` for `xrpl-camp-1.5.2-win-x64.exe`: **matches** | `26d77a83…f727c` for `xrpl-camp-1.5.2-linux-x64`: **matches** |
| **argv[0] control:** the cached binary run directly | help reads `Usage: xrpl-camp-1.5.2-win-x64.exe …`, so `xrpl-camp` comes from the launcher | `Usage: xrpl-camp-1.5.2-linux-x64 …` |
| `check_bundle.py --list` from the v1.5.2 tag (`08-tag-head.txt` = `5999be0…`) | — | **exit 0** on the asset downloaded from the release (sha256 equal to the checksum line), and **exit 0** on the launcher's cached copy: `Verified 97 archive entries …: no direct_url.json or _sysconfigdata home path present` |

**The unpacked identity scan of the released linux asset** (`identity-scan-release-linux.txt`) is `RESULT HIT 8`.
These are the 8 third-party lines alone, with the same members and offsets as the local `4a7ff84` build. The Publisher
has already cleared the asset scan; this result is here for the record.

## Optional: `reserve --json` through the npm binary (`reserve/`)

`harness/npx_camp_win.sh` runs `npx --yes @mcptoolshop/xrpl-camp@1.5.2` with the Windows check's caches, so it runs
the binary that was checked above. It used the funded Testnet wallet from the `4a7ff84` check. Its home is in the
session scratchpad and isn't here.

- `self-check` exits 0, reports version 1.5.2, and the endpoint is Testnet.
- `--yes reserve --json` exits 0 with one JSON document (`03-parse-check.txt`):
  - `"reserve_measured": true`, `"ok": true`, `"simulated": false`, `"network": "testnet"`;
  - the mint `84AA3361…` is `tesSUCCESS`, owner count 0 → 1, reserve +200000, status `locked`;
  - the burn `D6D6952B…` is `tesSUCCESS`, owner count 1 → 0, reserve −200000, status `released`;
  - `net_reserve_delta` is 0.

## Redaction

- Paths read `<scratch>` or `<home>`.
- The npm and launcher caches and the binaries aren't committed.
- A check of every file here for the wallet's seed value, and for any seed-shaped string, found none.
- The identity scan of this folder is `RESULT CLEAN`.
