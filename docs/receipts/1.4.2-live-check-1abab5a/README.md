# xrpl-camp 1.4.2 live check on `1abab5a`

This is the live testnet check the Editor asked for on **`1abab5a`** (PR #13, `chore/1.4.2-pins-coverage`), after
Argon's conditional pass. It reruns items 2 and 3 of the 1.4.1 check (`docs/receipts/1.4.1-live-check/`, PR #15),
then checks D4 with an absolute `XRPL_CAMP_HOME`, and a folder of one honest and one forged proof pack.

- **Code under test:** the test clone at `1abab5a`, installed into its own venv. It reports `xrpl-camp 1.4.2`, with
  xrpl-py 5.2.0, typer 0.27.3, rich 15.0.0 and Python 3.13.13 (`code.txt`).
- **Preflight:** no `XRPL_CAMP_*` override set, RPC = the default testnet endpoint, `check_endpoint()` PASS
  (`flow/preflight.txt`).
- **Input:** every call ran with `--yes` and stdin from `/dev/null`.
- **Faucet:** 6 grants, one per fresh wallet, about 60 s apart. No 429s.
- **Redaction:** no seeds, wallet files or mailbox files are here. Paths read `<scratch>`, `<home>`, `<worktree>` and
  `<runs>`. Every proof pack still passes its hash check after redaction.

## Verdict

**All three items pass.** D5 is fixed on the ledger: a Ctrl-C 0.5 s after lesson 4 submits, then `start`, records the
payment and sends nothing new. D4 is fixed. The forged pack is FAILED and the folder check exits 1. The 1.4.1 fixes
for D1, D2, D3 and D6 also show live. I found no new defects, only two cosmetic notes at the end.

## Item 1: items 2 and 3 of the 1.4.1 run, again

### The flow home and every command (`flow/`)

`XRPL_CAMP_HOME` is an absolute path under the home folder (`<scratch>/…/flow/home`).

| # | Command | Exit | Result | Against 1.4.1 |
|---|---|---|---|---|
| 01 | `--yes start --memo …` | 0 | 6 of 6 lessons in 29 s; lesson 4 `C298D52D…` | lesson 2 and 4 now print the real state path (**D1 fixed**) |
| 02 | `certificate` | 0 | re-sealed, previous pair kept as `.bak` | same |
| 03 | `proof verify xrpl_camp_proof_pack.json --online` | 0 | PASS; lesson 4 OK on the ledger, 5 SKIPPED | same |
| 10 | `status` | 0 | 6 of 6 with timings | same |
| 11 | `status --detail` | 0 | version, endpoint, wallet, balance, mailbox, state path | same |
| 12 | `wallet show` | 0 | "Seed is stored locally. Not shown here." | same |
| 13 | `fund` (already funded) | 0 | "Your wallet already holds test XRP, so the faucet was not asked again" | **D2 fixed** |
| 14 | `send --memo` | 0 | `0D06FAFC…`, 1 drop, validated; no "Account created" panel this time | the session-state fix shows |
| 15 | `read` | 0 | 3 transactions, 2 with memos | same |
| 16 | `read <my address>` | 0 | the same 3 | same |
| 17 | `read <hash>` | 0 | the transaction table for `C298D52D…` | same |
| 18 | `verify --tx <hash>` | 0 | memo identical, validated | same |
| 19 | `try` | 0 | 7 failures, 0 drops. The replay case now adds "This preview answers telCAN_NOT_QUEUE… Submitted for real… tefPAST_SEQ" | **D3 fixed** |
| 20 | `self-check` | 0 | 12 OK, network_id 1 (Testnet) | same |
| 21 | `support-bundle --out bundle.zip` | 0 | 4 files; "the names of files in the state folder" | **D4 fixed**, see item 2 |
| 22 | `proof verify .` | 0 | "1 of 1 packs pass the hash check" | wording changed |
| 23 | `--verbose try replay` | 0 | the same note as 19 | **D3 fixed** |
| 30 | `start` again (all done) | 0 | "All 6 lessons are done. Nothing here needs doing again"; nothing sent | same |

### Resume and Ctrl-C (`resume/`)

Each case ran in a fresh default-mode home (`./.xrpl-camp`). `harness/interrupt_cli.py.txt` is the in-process
Ctrl-C (`_thread.interrupt_main()`), fired on a line of output, or `@submit` when xrpl-py's `submit` RPC returns.

| Run | Ctrl-C at | Exit, panel | `status` after | `start` again (same memo) | On the ledger |
|---|---|---|---|---|---|
| `j` | **0.5 s after the submit RPC returned `tesSUCCESS`** (`7AB38D6E…`) | 130; "XRPL Camp — Paused … Your progress is saved" (**D6 fixed**) | 3 of 6, "Send Payment ← next" | exit 0: "Your last run sent a payment and stopped before it was recorded. Checking the ledger for it first: 7AB38D6E… **It landed. Recording it instead of sending again.**" Then lessons 5–6, 6 of 6 | **one** memo payment, `7AB38D6E…` (ledger 21,728,436). The account's whole history is the faucet grant and that payment (`hashes.txt`) |
| `s` | 0.3 s after "Submitting transaction" | 130, Paused panel | 3 of 6 | exit 0; a fresh send, `0D01ECC9…`, 6 of 6 | one memo payment. The interrupt came before signing, so there was nothing to look up |
| `i` | 2.5 s after "Submitting transaction" | 130, Paused panel | 3 of 6 | exit 0; a fresh send, `39004F26…`, 6 of 6 | one memo payment, as for `s` |
| `g` | 1 s into lesson 3's faucet wait | 130, Paused panel | 2 of 6, "Fund Wallet ← next" | exit 0; lesson 3 funds (balance 100.00), 6 of 6, `04C4A5CE…` | one faucet grant, one memo payment |

`f1` was meant to be the faucet case, but it never fired: 1.4.2 changed the line to "Funding your wallet from the
Testnet faucet…", so its trigger never appeared, and that run is simply an uninterrupted 6 of 6. `g` is the
same case with the new trigger (`resume/README-f-vs-g.txt`).

## Item 2: D4, `support-bundle` with an absolute `XRPL_CAMP_HOME`

`flow/21-support-bundle.*`; the bundle's 4 files, extracted, are in `flow/support-bundle/`. `flow/d4_grep.txt`
greps every file in the zip, before any redaction of mine. It searches for the home path (backslash, forward-slash
and JSON-escaped forms), the account name and `C:\Users`.

| File | Hits |
|---|---|
| `self-check.txt` | none |
| `session.json` | none |
| `state-listing.txt` | none |
| `environment.json` | none; `state_dir` = `~\AppData\…\flow\home`, `XRPL_CAMP_HOME` = `~\AppData\…\flow\home` |

**RESULT: CLEAN.** In 1.4.1 the same setup put `C:\Users\<account>\…` in `state_dir`.

## Item 3: `proof verify <folder> --online`, honest and forged (`forgery/`)

- **`honest.json`** is the flow home's own pack.
- **`forged.json`** is that pack with lesson 4's txid swapped in all three places for `1416EDB0…`. That is a real,
  validated payment from a different account (1.4.1 run). The sha256 is then recomputed with the tool's own
  `canonical_json` (`harness/forge_pack.py.txt`, `forgery/forge.txt`).
- **`packs-nonexistent/`** holds a second forgery, with a random 64-hex txid that is on no ledger.

Run from `forgery/` with relative paths, human mode only (not `--json`, Argon's F1):

| # | Command | Exit | Output |
|---|---|---|---|
| 1 | `proof verify packs/forged.json` (offline) | 0 | "✅ PASS — Proof pack integrity verified": the forged hash holds, so only the ledger can tell |
| 2 | **`proof verify packs --online`** | **1** | `PASS forged.json … ledger: FAILED`, `PASS honest.json … ledger: VERIFIED`; "1 of 2 proof packs need a look; 1 passed. • forged.json: the ledger contradicts this pack" |
| 3 | `proof verify packs` (offline) | 0 | both PASS the hash check |
| 4 | `proof verify packs-nonexistent --online` | 1 | `forged-nonexistent.json … ledger: FAILED`, `honest.json … ledger: VERIFIED` |

As expected: honest VERIFIED, forged FAILED, exit 1. In 1.4.1 a folder check ignored `--online`.

## Notes (cosmetic, not defects)

1. **Online-check progress lines read oddly.** They say "Checking lesson 4 against the ledger checked." In folder
   mode that line prints once per pack, without the pack's name.
2. **`fund` on a funded wallet still says it is working first.** It prints "Funding your wallet from the Testnet
   faucet… done." before the new "the faucet was not asked again" line.

## Hashes to check on testnet

All are a validated `Payment`, `tesSUCCESS` (`hashes.txt`).

| Hash | What |
|---|---|
| `7AB38D6E9FBB8545D53B91AE1787DF40F4F5051CD2A86291005D91D8B921BF74` | **D5:** the payment the Ctrl-C cut off. Recorded on resume, not re-sent. `rBPAEubp…` → `rnY3giNX…`, memo "recheck 142-1abab5a j", ledger 21,728,436; the sender's only payment |
| `C298D52D6D61B957B69767712B342B05B4A977656DB2C616F1A9AECEA4A85741` | the flow's lesson 4, memo "book keeper 142-1abab5a live check" |
| `0D06FAFCD8084B1B88720113B0585F0BABD90ABA2F815B9C12037FC5BAE90C19` | `send --memo`, 1 drop |
| `0D01ECC9319394AF0602D5BDA83E69379744125284CE00F2D6D654BE799EED24` | `s`: the one payment after an early Ctrl-C |
| `39004F2695909AE8C956FCD55E754B958F1A777FC6D04D141648370FDB9ED00B` | `i`: the one payment after a 2.5 s Ctrl-C |
| `04C4A5CEC85EE13C1608D0C5463EDACF7BE42D48C7CFEC85EA150DE7D12FD547` | `g`: the one payment after a Ctrl-C in the faucet wait |

## Files

- `code.txt`: the commit and version run.
- `flow/`: the flow home. `<n>-<command>.{cmd,out,err}`, `preflight.txt`, `ids.txt`, `d4_grep.txt`,
  `support-bundle/` (extracted), and `artifacts/` (the current certificate and pack, plus `from-start/`).
- `resume/`: runs `f` (did not fire), `g`, `s`, `i` and `j`.
- `forgery/`: the packs, `forge.txt` and the four verify calls.
- `hashes.txt`: the `tx` lookups, and the D5 account's full history.
- `harness/`: `recheck_items23.sh`, `interrupt_cli.py.txt` and `forge_pack.py.txt`. The `.txt` keeps them out of the
  repo's `ruff check`.
