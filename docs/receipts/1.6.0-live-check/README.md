# 1.6.0 live check on XRPL Testnet, on `c10abfb`

1.6.0 is the release for the **2026-11-25** Testnet and Devnet wipe. It changes one command, `proof verify --online`:
a pack from before a full reset reads as history gone and not as a forgery (#38), and a history verdict names what it
rests on, with a claim only the pack makes shown as UNCONFIRMED (#39). This check ran the release commit against the
real Testnet on 2026-11-13.

- **Code:** `mcp-tool-shop-org/xrpl-camp` at `c10abfb`, in the test clone's editable install, reinstalled after the
  switch. `xrpl-camp --version` prints `xrpl-camp 1.6.0` (`testnet/code.txt`).
- **Network:** the public Testnet, default endpoint, no `XRPL_CAMP_*` overrides; the CLI's own endpoint check passes
  (`testnet/preflight.txt`). One faucet grant.
- **Course:** `xrpl-camp --yes start --memo "book keeper v1.6.0 live check"`, all six lessons, exit 0
  (`testnet/01-start.*`). The honest pack is that run's own proof pack.
- **Redaction:** no seeds or wallet files are here. Paths read `<scratch>`.

## Verdict

**PASS.** Every outcome the release adds came out as designed against the real ledger. Neither history outcome was
counted as passed, alone or in a folder.

## The endpoint's ledger range on the day

`testnet/03-endpoint-range.txt`: the public Testnet endpoint held ledgers **13073099 to 22293206**. Its history
already starts well after ledger 1, so both shapes of "the endpoint does not hold this ledger" exist on the real
network today: a ledger older than its earliest one, and a ledger newer than its newest one.

## One pack at a time

Each forged pack is the honest pack with lesson 4 changed and the hash recomputed with the tool's own code, so its
integrity check passes (`testnet/02-forge.txt`). The fake transaction hash is `F00DFACE…`, which is on no ledger.

| Pack | What was forged | Exit | Result status | `history_signal` | Lesson 4 |
|---|---|---|---|---|---|
| `honest` | nothing | **0** | `confirmed` | "" | `ok` |
| `fake_txid` | the transaction hash | **1** | `contradicted` | "" | `miss_not_found` |
| `fake_txid_future_ledger` | the hash, and ledger index 99000000 | **3** | `history_unconfirmed` | `pack_claim` | `miss_history_unconfirmed` |
| `fake_txid_pruned_ledger` | the hash, and ledger index 5000000 | **3** | `history_unconfirmed` | `pack_claim` | `miss_history_unconfirmed` |
| `real_txid_future_ledger` | only the ledger index, to 99000000 | **1** | `contradicted` | "" | `mismatch` |

Files: `testnet/10-verify-<pack>-json.*` and `testnet/11-verify-<pack>.*`.

- **`fake_txid`** is the baseline. The endpoint holds the ledger the pack records, and the transaction is not in it:
  contradicted, as before.
- **`fake_txid_future_ledger`** is the shape a full reset leaves: a recorded ledger far past the endpoint's newest
  one. Before #38 this read "no transaction with this hash is on the ledger" (exit 1).
- **`fake_txid_pruned_ledger`** is the shape discarded history leaves: a recorded ledger before the endpoint's
  earliest one.
- Both of those are **exit 3, UNCONFIRMED**, because the announced reset has not happened yet and the ledger number is
  the pack's own word. The text reads: "UNCONFIRMED: the pack claims a ledger this endpoint does not hold, and nothing
  else confirms a reset … anyone can write that number" (`testnet/11-verify-fake_txid_pruned_ledger.out`).
- **`real_txid_future_ledger`** shows that a false ledger number does not help a real transaction: the ledger answers
  with the real index, and the pack is contradicted.

## A folder

| Folder | File | Exit | `passed` | `failed` | `unverifiable` |
|---|---|---|---|---|---|
| honest + `fake_txid_future_ledger` | `testnet/20-folder-unconfirmed-json.out` | **3** | 1 | 0 | 1 |
| all five | `testnet/22-folder-all-json.out` | **1** | 1 | 2 | 2 |

The unconfirmed packs are counted as `unverifiable`, never as `passed`.

## What could not be run live

The **announced** signal depends on the date: it applies from 2026-11-24 10:00 UTC, when the 25th begins anywhere.
Until then every history miss is `pack_claim`, which is what this run shows. The announced path is covered by the
test suite with a pinned clock (`tests/test_history_signal.py`).

## One fact about `--json` this run makes visible

An unconfirmed pack's JSON reads `"valid": true` (`testnet/10-verify-fake_txid_future_ledger-json.out`). That is the
field's meaning since 1.4.2, not a change in 1.6.0: `valid` is false only when the hash fails or the ledger
contradicts the pack, and it was already `true` for `unknown` and `ledger_history_gone`. A consumer that reads only
`valid` would not see that the pack was unverifiable. The exit code (3), `online.status`, `online.history_signal`
and a folder's `unverifiable` count all say so.

## Offline

`testnet/30-verify-honest-offline.*`: the honest pack verifies offline, exit 0, with no network call.

## Layout

`testnet/NN-name.cmd` is the command and its exit code and duration; `.out` and `.err` are its stdout and stderr.
