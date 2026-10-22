# xrpl-camp 1.4.1 live check

This is the live testnet check the Editor asked for on **xrpl-camp v1.4.1** (tag `v1.4.1` = `fa1c077`). It is
measurement only: no code was changed. The last live check on record was the v1.4.0 release on 2026-09-09.

- **Code under test:** a fresh clone at tag `v1.4.1`, installed into its own venv (`uv pip install .`, Python 3.13.13,
  xrpl-py 5.2.0, typer 0.27.3, rich 15.0.0). `main` (`af2d49d`) differs from the tag only in CI, Atlas, the site and a
  dev dependency; `xrpl_camp/` is identical, so these results hold for `main` too.
- **Homes:** each item ran in a fresh home in the session scratchpad. Items 1–2 used `XRPL_CAMP_HOME`, and items 3–5
  the default `./.xrpl-camp` in an empty folder, so both state modes are covered.
- **Preflight:** no `XRPL_CAMP_*` override set, RPC = the default `https://s.altnet.rippletest.net:51234/`, the CLI's
  own `check_endpoint()` PASS (`flow/preflight.txt`).
- **Input:** every call ran with `--yes` and stdin from `/dev/null`, so nothing could wait on a keypress.
- **Faucet:** 5 grants in all, one per fresh wallet, about 60 s apart. No 429s.
- **Redaction:** no seeds, wallet files or mailbox files are in this directory. Local paths read `<scratch>`, `<home>`
  and `<worktree>`. Both proof packs still verify after redaction.

## Verdict

The guided flow, every command and both install channels work: every one exits as designed and the ledger agrees
with every claim checked. There are **8 defects**. Two I read as blocking: the support bundle leaks the account name
when `XRPL_CAMP_HOME` is set (D4), and a Ctrl-C after lesson 4 submits leads `start` to send a second permanent
payment (D5). See [Defects](#defects).

## Item 1: the guided flow

`xrpl-camp --yes start --memo "book keeper v1.4.1 live check"` in a fresh home (`flow/01-start.*`).

| Lesson | Outcome | Time |
|---|---|---|
| 1 Mental Model | ✓ | 6.7 s |
| 2 Create Wallet | ✓ wallet `rp6xWefa…` | 0.0 s |
| 3 Fund Wallet | ✓ 100 XRP from the faucet (ledger 21,727,377) | 10.2 s |
| 4 Send Payment | ✓ `2B7CF0F5…`, 1 XRP, which created the mailbox `rao31kqK…` | 12.1 s |
| 5 Verify Transaction | ✓ memo read back identical, `tesSUCCESS`, validated | 0.4 s |
| 6 Certificate | ✓ certificate and proof pack written (`flow/artifacts/from-start/`) | 0.0 s |

- **Exit 0**, 6 of 6 lessons, 29 s in all. `session.json` has `completed_lessons: [1..6]`.
- **`certificate`** (`02`): exit 0. It re-seals both files with a new SHA-256 and keeps the previous pair as
  timestamped `.bak` files.
- **`proof verify xrpl_camp_proof_pack.json --online`** (`03`): exit 0. PASS on integrity; lesson 4 is OK on the
  ledger and the other 5 lessons are SKIPPED ("records no transaction"). The ledger checked was the default testnet
  endpoint.

## Item 2: every command, in the flow home

| # | Command | Exit | Result |
|---|---|---|---|
| 10 | `status` | 0 | 6 of 6 ✓ with timings, lesson 4 hash |
| 11 | `status --detail` | 0 | version, endpoint, wallet, balance 99.00 XRP, mailbox, timings, artifact and state paths |
| 12 | `wallet show` | 0 | address, network, created; "Seed is stored locally. Not shown here." |
| 13 | `fund` (already funded) | 0 | **D2:** prints "Requesting funds… funded." and "✓ Account funded", but the faucet was never asked: no new payment on the ledger, balance unchanged |
| 14 | `send --memo "book keeper send check"` | 0 | `A3418C43…`, 1 drop to the mailbox, validated |
| 15 | `read` | 0 | 3 transactions, 2 with memos, read off the ledger |
| 16 | `read <my address>` | 0 | the same 3 |
| 17 | `read <hash>` | 0 | the full transaction table for `2B7CF0F5…` |
| 18 | `verify --tx <hash>` | 0 | lesson 5's check, memo identical, validated |
| 19 | `try` | 0 | 7 failures, 0 drops spent. **D3:** the replay case shows `telCAN_NOT_QUEUE` but teaches `tefPAST_SEQ` |
| 20 | `self-check` | 0 | 12 OK, including Ledger round-trip network_id 1 (Testnet) |
| 21 | `support-bundle --out bundle` | 0 | a zip of 4 files. **D4:** `environment.json` `state_dir` holds the full home path with the account name |
| 22 | `proof verify .` | 0 | "1 of 1 packs verified". It does not recurse and skips `.bak` files |
| 23 | `--verbose try replay` | 0 | the same `telCAN_NOT_QUEUE`, with no extra detail |

## Item 3: resume, auto-resume and Ctrl-C

**Method for Ctrl-C:** `harness/interrupt_cli.py` runs the CLI in-process and calls `_thread.interrupt_main()`, which
is what a console Ctrl-C does at the Python level: a `KeyboardInterrupt` in the main thread. The trigger is either a
line of output or the moment xrpl-py's `submit` RPC returns. Runs `f1`, `s1` and `i1` used an earlier version that
tee'd stdout. Its own flush failed at exit, so the process exit is 120, while the CLI's own exit, recorded in the
`.out` file, is 130. `j1` used the final version, with process exit 130.

| Run | Interrupted at | After the interrupt | `start` again | Ledger |
|---|---|---|---|---|
| `30` (flow home, all done) | not interrupted | — | exit 0: "All 6 lessons are done. Nothing here needs doing again" | nothing sent (`account_checks.txt`) |
| `f` | 1 s into lesson 3's faucet wait | CLI exit 130, no "Paused" panel (**D6**); `status` 2 of 6, "Fund Wallet ← next" | exit 0; lessons 1–2 "already completed", resumes at lesson 3, 6 of 6 | one faucet grant, one memo payment |
| `s` | 0.3 s after "Submitting transaction" | 130; `status` 3 of 6, "Send Payment ← next" | exit 0, resumes at lesson 4, 6 of 6 | one memo payment (`1416EDB0…`); nothing had been sent before the interrupt |
| `i` | 2.5 s after "Submitting transaction" | 130; 3 of 6 | exit 0, 6 of 6 | one memo payment (`8C350B86…`); still before the submit, since autofill and signing come first |
| `j` | 0.5 s after the submit RPC returned `tesSUCCESS` | 130; `status` 3 of 6, "Send Payment ← next"; `read` already shows `18B8294A…` validated | exit 0, resumes at lesson 4 and **sends again** (`7AA45A5D…`, same memo) | **two** permanent memo payments (**D5**) |

## Item 4: offline dry run

`harness/trace_camp.py` installs Python audit hooks and logs every DNS lookup, every connect, every write-mode `open`
and every mkdir, rename, remove and chmod. File listings are taken before and after each run.

| Run | Exit | Lessons | Lookups | Writes (not `__pycache__`) | New files |
|---|---|---|---|---|---|
| control: `self-check --offline` | 0 | — | 0 | 7 (its temp-dir probe) | 0 |
| control: `read <address>` | 0 | — | 1 (`s.altnet.rippletest.net`) | 0 | 0 |
| `--yes start --dry-run --memo …` | 0 | all 6 shown; lesson 6 "SIMULATION — No artifacts" | **0** | **0** | **0** |
| `--yes --dry-run start --memo …` (global flag) | 0 | all 6 | **0** | **0** | **0** |
| `--yes start --dry-run` (no memo) | 0 | all 6; memo `XRPLCAMP\|L4\|<time>` announced | **0** | **0** | **0** |
| the same, with `XRPL_CAMP_HOME` set | 0 | all 6 | **0** | **0** | **0** |

- **The controls show the tracer sees writes and lookups.** On Windows, asyncio connects through the proactor's
  `ConnectEx`, which raises no audit event. So a lookup is the network signal here, and connects log only asyncio's
  loopback socketpair.
- **D7 (minor):** the dry run still prints "✓ Written to the ledger. Your memo is permanent and public" and "✓ Account
  funded" under its DRY RUN banners.

## Item 5: the install channels

| Channel | `--version` | `--yes start --dry-run` | Files left in the empty folder |
|---|---|---|---|
| PyPI: `uvx --from xrpl-camp==1.4.1 xrpl-camp` | `xrpl-camp 1.4.1` | exit 0, all 6, "Dry Run Complete" | none |
| npm: `npx --yes @mcptoolshop/xrpl-camp@1.4.1` | **`mcptoolshop-launch 1.1.1`** (**D8**) | exit 0, all 6, "Dry Run Complete" | none |
| Docker | skipped: Docker Desktop is not running on this rig | | |

- **`npx … --help`** prints the launcher's help, not xrpl-camp's.
- **The npm binary itself is 1.4.1:** `npx … self-check --offline` reports `Version 1.4.1`, a frozen build on Python
  3.12.14.

## Defects

| # | Blocking? | Defect | My read of the cause |
|---|---|---|---|
| D4 | **blocking** | `support-bundle` puts the full home path and account name (`C:\Users\<account>\…`) in `environment.json` `state_dir` when `XRPL_CAMP_HOME` is an absolute path. The same run says "No seed, no wallet file, and no user names or home paths", and the README threat model says the bundle "redacts home directory and account name". The default `./.xrpl-camp` mode is clean (`resume/support-bundle-default/`). | `cli.py:1494`: `"state_dir": str(STATE_DIR)` is the one path field not passed through `_redact()`. `XRPL_CAMP_HOME` itself and `self-check.txt` are redacted. |
| D5 | **blocking** | A Ctrl-C after lesson 4's payment is submitted, before it validates, leaves no record of it. `status` says "Send Payment ← next" and `start` sends a second permanent payment with the same memo (`18B8294A…`, then `7AA45A5D…`). | Nothing saves the signed hash before waiting. `transport.py:1500–1570` already refuses to call a lapsed or broken submission "safe to run again", for exactly this double-send, but a `KeyboardInterrupt` goes around it. The (unseen, D6) Paused panel's "Nothing was left half-written" is false in this case. |
| D6 | not blocking | Ctrl-C ends the run with exit 130 and no "Paused — your progress is saved; run start" panel. | typer 0.27.3 (`typer/core.py:201`) turns `KeyboardInterrupt` into `Exit(130)` inside `app()`, so `cli.run()`'s `except KeyboardInterrupt` (`cli.py:1575`) never runs. Reproduced offline by raising `KeyboardInterrupt` in lesson 3. The tests drive `app` through `CliRunner`, which never reaches `cli.run()`. |
| D2 | not blocking | `fund` on a funded wallet prints "Requesting funds from the Testnet faucet… funded." and "✓ Account funded", though the faucet is never asked. The same text shows when `start` reruns lesson 3 after an interrupt. | `transport.fund_wallet_detail` skips the faucet and returns `already_funded=True` (`transport.py:1149`), which is right, since it saves a shared grant. But lesson 3 calls `fund_wallet()`, which drops the flag (`transport.py:1187`). The comment at `lessons.py:1156` ("asking the faucet twice tops the same account up") contradicts the transport. |
| D3 | not blocking | `try`'s "Send the same transaction a second time" shows `telCAN_NOT_QUEUE`, while its lesson text explains sequence replay (`tefPAST_SEQ`). | Testnet's `simulate` answers `telCAN_NOT_QUEUE` for any past sequence: seq=1 and seq=current−1 both, with or without a fee. The current sequence answers `tesSUCCESS`. The fee case carries a "preview answers X; a real submission answers Y" note (`transport.py:2494`); the replay case (`lessons.py:2087`) has none and no test. |
| D1 | not blocking | With `XRPL_CAMP_HOME` set, lesson 2 says "Seed saved to .xrpl-camp/wallet.json", lesson 4 says the mailbox keys are in ".xrpl-camp/mailbox.json", and `support-bundle` lists "the names of files in .xrpl-camp/". All three point a learner to the wrong folder for their seed. | Hard-coded strings: `lessons.py:1106`, `lessons.py:1414`, and the support-bundle list in `cli.py`. `status --detail` shows the real state path. |
| D7 | not blocking | The dry run prints success claims ("Written to the ledger… permanent and public", "Account funded") under its DRY RUN banners. | Lessons 3–5 print the same closing line in both modes. |
| D8 | not blocking (another repo) | `npx @mcptoolshop/xrpl-camp@1.4.1 --version` / `--help` print the launcher's version and help. | `@mcptoolshop/npm-launcher` 1.1.1 intercepts `--version`, `-V`, `--help` and `-h` as `argv[2]` before it reads `MCPTOOLSHOP_LAUNCH_CONFIG`. Every tool on that launcher is affected; the fix belongs there. |

**Not defects:**
- `support-bundle --out bundle` writes the zip under exactly that name, with no `.zip` added.
- `proof verify <folder>` does not recurse.
- `certificate` re-seals with a new SHA and keeps the previous pair as `.bak`.

## Hashes to check on testnet

All six were looked up with `tx` after the runs (`hashes.txt`). Each is a validated `Payment`, `tesSUCCESS`.

| Hash | What | Expected |
|---|---|---|
| `2B7CF0F5679F06DF3BE55313E932AC415AB59FBC6484B447A3B1B0922EC8D2F4` | Item 1, lesson 4 | `rp6xWefa…` → `rao31kqK…`, 1,000,000 drops, memo "book keeper v1.4.1 live check", ledger 21,727,381 |
| `A3418C433A0A1D65CDD2B3A121D5571BB61A4A5D9DBD6AA310184025D26F147C` | Item 2, `send --memo` | the same pair, 1 drop, memo "book keeper send check" |
| `18B8294A3DC78953558FFACBB02B2ACD98E2554145C69B95C7AA37DEAC1378EC` | D5: the payment the Ctrl-C cut off | `rEzKTTzX…` → `rJFJLg4f…`, 1,000,000 drops, memo "resume check after submit", ledger 21,727,568 |
| `7AA45A5D01A1EF7DB7E2F4917115228C9A54838E9261B6B9B622A940FDF48851` | D5: the second payment `start` sent | the same pair, 1 drop, the same memo, ledger 21,727,575 |
| `1416EDB0748C20020813E53D19C458D58B2470BD6BF7656BC7D63F6B2C19941C` | Item 3 `s`: resume after an early Ctrl-C | `r9GFm3mu…` → `rDmiKaSC…`, memo "resume check submit" (the only one) |
| `8C350B86070D341D908FDF7A47876D171D3C96AD597A59A2869A62BA735A49B5` | Item 3 `i`: resume after a 2.5 s Ctrl-C | `rfPZMN7b…` → `rEk8XVc1…`, memo "resume check in flight" (the only one) |

## Files

- `flow/`: items 1 and 2. `<n>-<command>.{cmd,out,err}`, `preflight.txt`, `session.json` (no seed), `artifacts/`
  (the current certificate and proof pack, plus `from-start/` from lesson 6), `support-bundle/` (the bundle's 4
  files, extracted and redacted).
- `resume/`: item 3 runs `f`, `s`, `i` and `j`, plus `support-bundle-default/` from the default-mode home.
- `dry-run/`: item 4. Per run `.cmd`, `.out`, `.err`, `.trace`, and `.before` / `.after` file listings.
- `channels/`: item 5.
- `hashes.txt` and `account_checks.txt`: the ledger lookups.
- `harness/`: `camp_run.sh`, `interrupt_cli.py` and `trace_camp.py`, as used.
