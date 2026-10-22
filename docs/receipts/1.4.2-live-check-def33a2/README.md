# xrpl-camp 1.4.2 live check on `def33a2`

This is the short repeat the Editor asked for on **`def33a2`** (`chore/1.4.2-pins-coverage`). That commit is
`64e7781`, Argon's round 2 pass on F1–F5, plus the two wording fixes from the `1abab5a` check
(`../1.4.2-live-check-1abab5a/`). The clone reports `xrpl-camp 1.4.2` (`code.txt`).

The same rules apply: fresh default-mode homes (`./.xrpl-camp`), `--yes`, stdin from `/dev/null`, no
`XRPL_CAMP_*` override. There are no seeds, wallet files or mailbox files here, and paths are redacted. Two faucet
grants were used.

## Verdict

**PASS on all three items.**

## Item 1: Ctrl-C, then `start` with the same memo (`ctrlc/`)

| Run | Ctrl-C at | State folder after the Ctrl-C | `start` again | State folder after | Ledger, the learner's full history |
|---|---|---|---|---|---|
| `j` | **0.5 s after the submit RPC returned `tesSUCCESS`** (`ED191D1A…`) | `in_flight.json` with `txid` = `ED191D1A…`, plus `mailbox.json`, `session.json`, `wallet.json` | exit 0: "Your last run sent a payment and stopped before it was recorded. Checking the ledger for it first: ED191D1A… **It landed. Recording it instead of sending again.**" Then 6 of 6 | **no `in_flight.json`** | the faucet grant plus **one** memo payment, `ED191D1A…` (ledger 21,728,623) |
| `s` | 0.3 s after "Submitting transaction", before signing | no `in_flight.json` | exit 0: one fresh send, `B7ED61C0…`, then 6 of 6 | no `in_flight.json` | the faucet grant plus **one** memo payment, `B7ED61C0…` (ledger 21,728,662) |

- **Both interrupted runs** exit 130 and show the "XRPL Camp — Paused" panel. `status` showed 3 of 6, "Send Payment ←
  next".
- **The state listings** are file names only (`*-state-after-*.txt`). For `in_flight.json`, only its keys and txid are
  recorded: `amount_drops`, `destination`, `last_ledger`, `memo`, `txid`.
- **The ledger histories** are in `hashes.txt`.

## Item 2: `proof verify packs --online --json` (`json-verify/`)

These are the same honest and forged packs as the `1abab5a` check (`json-verify/packs/`). The forgery swaps lesson 4's
txid for another account's real payment and re-seals the hash.

| Check | Result |
|---|---|
| exit | **1** |
| stdout | `json.loads` parses it as **one document** (`1-parse-check.txt`) |
| top level | `passed` **1**, `failed` **1**, `unverifiable` **0**, `checked` 2 |
| `forged.json` | `"valid": false`, `"hash_match": true`, `online.status` `"contradicted"` |
| `honest.json` | `"valid": true`, `"hash_match": true`, `online.status` `"confirmed"` |
| stderr | the two progress lines only, `forged.json: Checking lesson 4 against the ledger... done.` and the same for `honest.json` |

The human-mode run of the same folder (`2-folder-online-human.*`) also exits 1, with forged "ledger: FAILED" and
honest "ledger: VERIFIED".

## Item 3: the two wording fixes, live

- **The folder progress line names the pack:** `forged.json: Checking lesson 4 against the ledger... done.`, in both
  JSON mode (stderr) and human mode.
- **`fund` on a funded wallet** (`ctrlc/j6-fund-funded`, `s6-fund-funded`) prints "Checking your balance, and asking
  the Testnet faucet if it's empty... done." and then "Your wallet already holds test XRP, so the faucet was not asked
  again". Neither wallet's history shows a second grant.

## Notes (cosmetic, not defects)

1. **The online message contradicts itself.** In `--online --json`, each pack's `message` is still the offline
   wording: "...it does not independently confirm each transaction against the XRPL ledger. Run this same command
   with --online...". Its `online` block, right after it, says the ledger was checked.
2. **The forged pack's `online.checked` is 0 while `total_lookups` is 1.** It reads as "nothing checked" for a pack
   whose lookup found a mismatch.
3. **`file` uses the OS's separator** (`packs\\forged.json` on Windows), so the same folder gives different JSON on
   Linux.

## Hashes to check on testnet

| Hash | What |
|---|---|
| `ED191D1A1CC5893691BA2A17B728CD380596D68C51C23684098127BAB61CA444` | `j`: the payment the Ctrl-C cut off. Recorded on resume, not re-sent. `rUPWujDU…` → `rsJqj9JJ…`, memo "ctrlc 142-def33a2 j", the sender's only payment |
| `B7ED61C0F6082D0E2B5F298F4431E02C36E5C238BF265D39DC3CC9F064DD1219` | `s`: the single fresh send after a pre-signing Ctrl-C. `r3KHYF6k…` → `rsU4cc7S…`, memo "ctrlc 142-def33a2 s" |

## Files

- `code.txt`: the commit and version run.
- `hashes.txt`: both learners' full ledger histories.
- `ctrlc/`: runs `j` and `s`, as `<n>-<step>.{cmd,out,err}` plus the state listings.
- `json-verify/`: `packs/`, the JSON and human runs, and `1-parse-check.txt`.
- `harness/recheck_ctrlc.sh`. It uses `interrupt_cli.py.txt` from `../1.4.2-live-check-1abab5a/harness/`.
