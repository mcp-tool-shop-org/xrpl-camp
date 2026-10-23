# 1.5.0 live testnet check on `ae22f3b`

This is the check the Editor asked for on **`ae22f3b`** (PR #19, `feat/1.5.0-wire-features`, issue #14). 1.5.0 wires
in three features: `xrpl-camp reserve`, `certificate --format text` with a share block, and
`proof verify --online --record`.

- **The code:** a clone checked out at `ae22f3b`, with a non-editable install that reports `xrpl-camp 1.5.0`
  (`code.txt`). Each command ran with `XRPL_CAMP_HOME` set to a fresh folder and stdin from `/dev/null`
  (`harness/camp_run.sh`).
- **Network:** XRPL Testnet, the default endpoint. The CLI's own `check_endpoint()` passed first
  (`course/preflight.txt`).
- **Checked against the ledger itself:** `harness/ledger_probe.py.txt` reads `account_info`, `server_state` and `tx`
  directly with xrpl-py, not through xrpl-camp.
- **Redaction:** no seeds or wallet files are here. Paths read `<scratch>` or `<home>`. The seven txids (five on
  `ae22f3b`, two on `3b80987`) are in `hashes.txt`.

## Verdict

**PASS on all four items.** One step was blocked as expected: the 1.5.0 npm wrapper cannot fetch its binary until a
v1.5.0 release exists. The 1.4.2 wrapper with launcher 1.2.0 shows the pass-through instead.

Three minor defects, none blocking: two cosmetic, one in the JSON contract. See **Defects** at the end. **All three
are fixed on the fixup-3 head `3b80987`**, as the re-check below shows.

**The blocked step is now closed:** the released npm package passes on Windows and Linux. See the next section.

## The released npm package, `@mcptoolshop/xrpl-camp@1.5.0` (`npm-release/`): PASS

This ran after the release: tag `v1.5.0` on `363a2ef`, npm `@mcptoolshop/xrpl-camp@1.5.0` with
`@mcptoolshop/npm-launcher ^1.2.0`.
- **The command:** `npx --yes @mcptoolshop/xrpl-camp@1.5.0 <args>`, from an empty folder.
- **Fresh state:** a fresh npm cache (`npm_config_cache`), a fresh npm prefix (`npm_config_prefix`), and a fresh
  launcher binary cache: `LOCALAPPDATA` on Windows, `XDG_CACHE_HOME` on Linux. So each platform downloaded and
  verified its binary from the GitHub release on the first call.
- **Node:** Node 22.22.3 and npm 10.9.8 on both.
  - **Windows:** run natively.
  - **Linux:** WSL Ubuntu, with the official Node tarball checked against nodejs.org's `SHASUMS256.txt`
    (`harness/wsl_node.sh`). WSL's own PATH only reaches the Windows npm, which would have run the Windows binary.

| Command | Windows | Linux |
|---|---|---|
| `--version` (first call: downloads) | exit 0, `xrpl-camp 1.5.0` | exit 0, `xrpl-camp 1.5.0` |
| `--help` | exit 0; `Usage: xrpl-camp [OPTIONS] COMMAND [ARGS]...`; lists `reserve`, `certificate` and `proof` | the same |
| `reserve --help` | exit 0, `Usage: xrpl-camp reserve [OPTIONS]` | the same |
| `certificate --help` | exit 0, `Usage: xrpl-camp certificate [OPTIONS]`; `--format`: "json (default) or text" | the same |
| `proof verify --help` | exit 0, `Usage: xrpl-camp proof verify [OPTIONS] {file}`; `--online`; `--record` "(requires --online)" | the same |

- **The first call's stderr** is the launcher's own lines: `Fetching checksums from mcp-tool-shop-org/xrpl-camp@v1.5.0...`,
  `Downloading xrpl-camp-1.5.0-<os>-x64...`, `Verifying SHA256...`, `Ready.` After them come npm's update notice
  and nothing else.
- **The cached binary matches the release checksums:**
  - win-x64 `92fc064c3bea4b980642d0007f7efd175e52b9d5b0b34816e45314b83bc0c221`;
  - linux-x64 `12259e59ad9d3fe86b4201ce65bc9df18016fda99aa11c9a5379b664badd424b`;
  - `win/06-*`, `linux/06-*`.
- **argv[0]: the launcher's name, not the file's.** Run directly, the same cached binary prints
  `Usage: xrpl-camp-1.5.0-win-x64.exe [OPTIONS] COMMAND [ARGS]...` on Windows and
  `Usage: xrpl-camp-1.5.0-linux-x64 [OPTIONS] COMMAND [ARGS]...` on Linux (`07-direct-help.*`). Through the
  launcher, every help page says `xrpl-camp`. So the tool name comes from npm-launcher 1.2.0's `argv0`.
- **Not covered:** macOS (`darwin-arm64`) wasn't run.

## Re-check on the fixup-3 head `3b80987` (`recheck-3b80987/`): E1–E3 fixed

Fixup 3 (`3b80987`) addresses E1–E3. This re-check ran from the receipts branch with `3b80987` merged in. Its
`xrpl_camp/`, `pyproject.toml`, `package.json` and `bin/` are identical to `3b80987` (`recheck-3b80987/code.txt`). The
rest of this README describes `ae22f3b`.

**One live `reserve` on the release head (`reserve/`):** exit 0, on the same wallet. The ledger agrees (`54-txs.json`):
both transactions are `tesSUCCESS`, with a fee of 10 drops each.

| Step | txid | OwnerCount | Balance (drops) | Spendable (drops) |
|---|---|---|---|---|
| NFTokenMint | `D7F6E4E4…65BFED19` | 0 → 1 | 98,999,950 → 98,999,940 | 97,999,950 → 97,799,940 (−200,010) |
| NFTokenBurn | `29F14935…3875A9B5` | 1 → 0 | 98,999,940 → 98,999,930 | 97,799,940 → 97,999,930 (+199,990) |

- **E1, fixed:** the mint's reserve cell reads `+200,000 drops (+0.200000 XRP) locked`, signed in both units, the same
  as the burn's `-200,000 drops (-0.200000 XRP) released`.
- **E2, fixed:** `reserve --dry-run` contains no `DEFAULT_RESERVE` text. Its panel reads "Simulated numbers: an owner
  reserve of 200,000 drops (0.2 XRP) and a 10-drop fee per transaction."

**E3, fixed (`e3/summary.txt`):** every call used `--json`, and every stdout parsed as one JSON document. `e3/00-setup.txt`
describes the packs.

| Case | Exit | `hash_match` | Code |
|---|---|---|---|
| `--record` without `--online` | 1 | **null** | `RECORD_REQUIRES_ONLINE` |
| `--record` on a folder | 1 | **null** | `RECORD_FOLDER_UNSUPPORTED` |
| `--dry-run … --online --record` | 1 | **null** | `RECORD_DRY_RUN` |
| a missing file | 1 | **null** | `FILE_NOT_FOUND` |
| a file that is not JSON | 1 | **null** | `PACK_INVALID` |
| the JSON object `{}` | 1 | **null** | `PACK_INVALID` |
| a tampered pack (memo edited, hash left alone) | 1 | **false** | — |
| the same with `--online --record` | 1 | **false** | — (no receipt) |
| `--record` whose write fails (the pack file is read-only) | 2 | **true** | `ARTIFACT_WRITE_FAILED` |
| the forged, re-sealed pack, `--online --record` | 1 | true | — (`contradicted`, no receipt) |
| the valid pack, `--online --record` | 0 | true | — (`recorded: true`) |

- **The write failure:** the read-only pack's bytes are unchanged, it still holds 3 receipts, and no temporary file was
  left behind (`e3/12-files-after.txt`).
- **Noted, not a defect:** the write-failure hint ("Check that the path's parent directory is writable…") does not
  mention that the file itself may be read-only.

## Item 1: `xrpl-camp reserve` (`reserve/`, `reserve-nowallet/`)

The wallet is the one funded by the course in item 2 (`rGWW1JWMihT9PaEntHFVaxY5oaacMa38RY`).

**`reserve` (run 1, exit 0, 21 s):**

| Step | txid | OwnerCount | Balance (drops) | Spendable (drops) | Reserve |
|---|---|---|---|---|---|
| before | | 0 | 98,999,990 | 97,999,990 | |
| NFTokenMint | `159D77ED…5639DDE4` | 0 → **1** | **−10** → 98,999,980 | **−200,010** → 97,799,980 | +200,000 **locked** |
| NFTokenBurn | `CECEF861…8CF3D6A4` | 1 → **0** | **−10** → 98,999,970 | **+199,990** → 97,999,970 | −200,000 **released** |

- **The ledger agrees** (`13-txs.json`): both transactions are `tesSUCCESS` and validated, with a fee of 10 drops each.
  - The metadata shows OwnerCount 0→1 on the mint (an `NFTokenPage` is created) and 1→0 on the burn (the page is
    deleted).
  - The balances in the metadata are the ones in the table.
- **`account_info`** before and after (`10-`, `12-account-*.json`): balance 98,999,990 → 98,999,970 and OwnerCount
  0 → 0. `server_state` gives a 1,000,000-drop base reserve and a 200,000-drop increment.
- **The text:** "Reserve: 200,000 drops (0.200000 XRP) locked" on the mint and "released" on the burn, then "✓ Reserve
  returned. Total cost: 20 drops in fees."

**`reserve --json` (run 2, exit 0):**
- stdout parses as one JSON document (`20-parse-check.txt`). Progress goes to stderr.
- The document has `ok: true` and `simulated: false`.
  - Mint `7CD7F341…75CE9295`: OwnerCount 0→1, `balance_delta` −10, `spendable_delta` −200,010, `reserve_status`
    "locked".
  - Burn `92547258…F591C042`: 1→0, −10, +199,990, "released".
  - Net: −20 / −20 / 0, with `leftover_burned: []`.
- The ledger agrees (`22-txs-json-run.json`).

**`reserve --dry-run`, `reserve --dry-run --json` and `--dry-run reserve`:** all three exit 0. They were traced with
audit hooks (`harness/trace_camp.py.txt`, `3x-*.trace`):
- **No network:** 0 DNS lookups in each. The positive control, `read`, makes 1 lookup of `s.altnet.rippletest.net`.
- **No writes:** 0 file writes, and no file in the home or the workspace changed (`30-files-diff.txt`).
- The `--json` form is one document with `ok: true` and `simulated: true`, and its txids read `DRY_RUN_TX_…`.

**No wallet (an empty state dir, `reserve-nowallet/`):**
- `reserve` exits **1** with `[WALLET_MISSING] No wallet found.`
- `reserve --json` exits **1**. Its stdout is one document with `ok: false` and `code: "WALLET_MISSING"`, plus the
  message and the hint.
- No state dir was created, and the workspace stayed empty (`state-dir.txt`).

## Item 2: the full course, then `certificate --format text` (`course/`)

- **`--yes start --memo "book keeper v1.5.0 live check"`:** exit 0, 30 s, all six lessons.
  - The lesson 4 payment is `0953A221…AA5334454`.
  - It closes with "A next step after camp: xrpl-camp reserve — watch the owner reserve lock and come back."
- **`certificate --format text`:** exit 0.
  - `xrpl_camp_certificate.txt` was written beside the JSON, in the same folder (`02-files-after.txt`).
  - The panel lists it as "Keepsake".
  - It is **not JSON**: `json.load` fails at line 1 column 1 (`05-txt-json-parse.txt`).
  - Its content is in `files/xrpl_camp_certificate.txt`.
- **The share block:** "Copy to share:" is followed by three plain lines (the address, the explorer link and the
  `proof verify … --online` line), with no panel or box around them.
- **`certificate --format bogus`:** exits **1** with `[BAD_FORMAT] Unknown certificate format 'bogus'.` A second run
  with hashes taken before and after shows no file in the workspace or home changed (`04-bogus-diff.txt`).
- **`--format TEXT`** is accepted too (exit 0). The format is matched without regard to case.
- **Noted, not a defect:** each `certificate` run re-seals the certificate and proof pack and keeps the old ones as
  timestamped `.bak` files.

## Item 3: `proof verify <pack> --online --record` (`record/`)

The packs are a copy of the course's proof pack (`valid.json`) and a forgery of it (`forged.json`).
`harness/forge_pack.py.txt` swapped lesson 4's txid for the reserve mint's and re-sealed the hash with the tool's own
code. `states.txt` gives the file's SHA-256, the pack's `sha256` field and the receipt count after every call.

| Call | Exit | Receipts | Pack `sha256` | File bytes |
|---|---|---|---|---|
| `valid.json --online --record` | 0 | 0 → **1** | unchanged (`32b165a1…`) | changed (receipt appended) |
| the same again | 0 | 1 → **2** | unchanged | changed |
| `valid.json` (offline, after) | 0 | 2 | PASS, same hash | unchanged |
| `valid.json --online --record --json` | 0 | 2 → 3 | unchanged | changed |
| `forged.json --online --record` | **1** | **0** | unchanged | **unchanged** |
| `forged.json --online --record --json` | **1** | 0 | unchanged | unchanged |

- **On the valid pack:** "Verification receipt added to valid.json (pack now holds 2 receipts; unsealed, self-reported
  log)." The JSON shows `valid: true` and `recorded: true`, with an online status of `confirmed`.
- **What a receipt holds:** `verified_at`, `tool_version: "1.5.0"`, `endpoint_used`, `status: "confirmed"`,
  per-lesson statuses with `ledger_index_seen`, and `self_reported: true`, with a note that it proves nothing on its
  own.
- **On the forged pack:** "1 of 1 transactions do not match what the ledger says", then "No verification receipt added
  … status is 'contradicted'". The JSON shows `valid: false`, `hash_match: true`, `recorded: false` and
  `record_skipped: "contradicted"`.

**The refusals.** All of them exit **1**, change no file, and print the code below. In `--json` they print one
document with `recorded: false`.

| Call | Code |
|---|---|
| `valid.json --record` (no `--online`) | `RECORD_REQUIRES_ONLINE` |
| `folder --online --record` | `RECORD_FOLDER_UNSUPPORTED` |
| `--dry-run proof verify valid.json --online --record` | `RECORD_DRY_RUN` |

**Off the brief:** `--record` against an unreachable endpoint (`--rpc-url https://s.altnet.rippletest.net:1/`) exits 3.
It reports "status is 'unknown'", adds no receipt, and leaves the file's bytes unchanged.

## Item 4: the npm wrapper (`npm/`)

- **`npm pack` at `ae22f3b`:** gives `mcptoolshop-xrpl-camp-1.5.0.tgz`, with 11 files: `bin/`, `package.json`,
  `LICENSE` and the READMEs (`01-*`).
- **Installed into an empty project:** `@mcptoolshop/xrpl-camp 1.5.0` with `@mcptoolshop/npm-launcher` **1.2.0**
  (`03-installed-versions.txt`).
- **The 1.5.0 wrapper:**
  - `--launcher-version` prints `mcptoolshop-launch 1.2.0` (exit 0).
  - `--print-cache-path` prints `<home>/AppData\Local\mcptoolshop\xrpl-camp\1.5.0`.
- **Blocked, as expected:** `--version` and `--help` both pass through to the tool. The launcher does not answer
  them itself, and goes to fetch the binary. They exit 1 with `Failed to fetch checksums (HTTP 404)` for
  `releases/download/v1.5.0/checksums-1.5.0.txt`, because no v1.5.0 release exists yet. This needs re-checking once
  the release is cut.
- **Pass-through, shown on 1.4.2:** the published `@mcptoolshop/xrpl-camp@1.4.2` pins launcher `1.1.1`, so it was
  installed with an npm `overrides` entry forcing **1.2.0** (`20-proj142-package.json`, `22-installed-versions-142.txt`).
  The binary came from the v1.4.2 release.
  - `--launcher-version` prints `mcptoolshop-launch 1.2.0`.
  - `--version` prints **`xrpl-camp 1.4.2`**, the tool's version and not the launcher's (the 1.4.1 D8 is gone).
  - `--help` prints the tool's own typer help, and `self-check` reports `Version 1.4.2`.
  - All of them exit 0, and none left a file in the working folder.

## Defects

Found on `ae22f3b`. All three are fixed on `3b80987` (see the re-check above).

| # | Class | Where | What |
|---|---|---|---|
| E1 | **cosmetic** | `reserve` mint table, `lessons.py` `_reserve_move_table` (`r_cell = f"+{_drops_line(r_delta)} locked"`) | The "Owner reserve" cell reads `+200,000 drops (0.200000 XRP) locked`. The XRP figure has no `+`, while every other delta is signed in both units, including the burn's `-200,000 drops (-0.200000 XRP) released`. |
| E2 | **cosmetic (copy)** | `reserve --dry-run` panel | A learner sees the internal constant's name: "Simulated numbers: DEFAULT_RESERVE_INC_DROPS (200,000 drops)". "the default owner reserve increment" would say the same. |
| E3 | **minor (JSON contract)** | `proof verify --record --json` refusals (`_reject_proof_verify`, `hash_match=False` by default) | `RECORD_REQUIRES_ONLINE`, `RECORD_FOLDER_UNSUPPORTED` and `RECORD_DRY_RUN` report `"hash_match": false` on a pack whose hash matches. The hash was never checked, so a script reading `hash_match` is told the pack is tampered. Older refusals (for example `FILE_NOT_FOUND`) already used this shape, but there the file was never readable. `null` or omitting the key would be accurate. |

**Not a defect, but worth knowing:** an offline `proof verify` of a pack that holds receipts does not mention them
(`12-valid-offline-after.out`). That is consistent with receipts being self-reported and unsealed.

## Files

- `code.txt`: the commit and version tested.
- `hashes.txt`: the seven Testnet txids.
- `recheck-3b80987/`: the fixup-3 re-check (`code.txt`, `reserve/` and `e3/`, with the extra packs in `e3/packs/`).
- `course/`: `start`, the certificate runs and their file listings, plus `files/` (the `.txt` keepsake, the
  certificate JSON and the proof pack).
- `reserve/`: the live runs and the dry runs with their traces and ledger probes. `reserve-nowallet/`: the empty state
  dir.
- `record/`: every `--record` case, `states.txt`, and `packs/` (the valid pack with its three receipts, the forgery and
  the folder copy).
- `npm/`: the pack, the installs and the wrapper runs.
- `npm-release/`: the released package through `npx`, in `win/` and `linux/`: each command as `.cmd`, `.out`,
  `.err` and `.exit`; the cached binary's hash (and the release checksums, in `win/`); the direct-run control; and
  `harness/` (`wsl_node.sh`, `npm_release_check.sh`).
- `harness/`: `camp_run.sh`, plus `ledger_probe.py.txt`, `trace_camp.py.txt` and `forge_pack.py.txt`. The `.txt` keeps
  the scripts out of the repo's lint.
