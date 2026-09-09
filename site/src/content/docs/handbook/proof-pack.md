---
title: Proof Pack
description: What the certificate and proof pack prove — and what they don't.
sidebar:
  order: 3
---

Finishing XRPL Camp writes two files into your working directory:

- `xrpl_camp_certificate.json` — the human-readable record of what you did
- `xrpl_camp_proof_pack.json` — the same events plus a SHA-256 hash and the ledger references needed to check them

Both are safe to share. Neither contains your seed; generation refuses to write a file that appears to contain one.

## The honest version of what the hash does

The proof pack carries a SHA-256 hash computed over its own contents.

That hash detects an **accidental** edit — a truncated download, a text editor that reformatted the JSON, a field someone changed by hand and forgot to account for.

It is **not a signature**, and on its own it does not prove the pack is genuine. Anyone can change a field and recompute the hash using the same public function this tool uses. That was demonstrated during development: a pack was edited to claim a different address, its hash was re-sealed, and offline verification reported it as valid.

An earlier version of this tool claimed the certificate was "SHA-256 verifiable so it can't be faked." That was false, and it has been removed rather than softened.

## What actually cannot be faked

The transactions.

```bash
xrpl-camp proof verify xrpl_camp_proof_pack.json --online
```

This resolves every transaction the pack names against the XRP Ledger and checks four things per transaction:

1. it exists
2. it was sent by the address the pack claims
3. it carries the memo the pack claims
4. it closed successfully and is validated

The forged pack above — the one that passes the offline hash check — fails this immediately, because the ledger says the transaction was sent by somebody else.

## Two things this check gets right that are easy to get wrong

**It never trusts the endpoint named in the pack.** The pack records which RPC endpoint the run used, and that is displayed as context. It is not used as the oracle. A forged pack can name a server its author controls, and such a server will happily confirm a transaction that never existed — this was tested. Verification queries the public Testnet, or an endpoint you pass with `--rpc-url`.

**A missing transaction is not automatically fraud.** The XRPL Testnet is periodically reset, and when that happens perfectly honest transactions stop resolving. The pack records each transaction's ledger index, so the tool can tell "this ledger range no longer exists" from "this never happened":

| Outcome | Exit code | Meaning |
|---------|-----------|---------|
| confirmed | 0 | the ledger agrees with the pack |
| contradicted | 1 | the ledger disagrees — something in this pack is not true |
| ledger history gone | 3 | the Testnet was reset; unverifiable, not disproven |
| unknown | 3 | the endpoint could not be reached |

Exit 3 means *could not check*, and it is deliberately not the same as *checked and failed*. Conflating them would make a flaky wifi connection look like an accusation.

## Offline stays the default

```bash
xrpl-camp proof verify xrpl_camp_proof_pack.json
```

Plain `proof verify` makes **zero network calls**. It works on a plane, in a locked-down classroom, and in an air-gapped lab. `--online` is strictly opt-in.

Add `--json` to either form for machine-readable output.

## For facilitators

```bash
xrpl-camp proof verify ./submissions --online
```

Point it at a folder and it verifies every pack in it, exiting non-zero if any fails. That is how you confirm a room of thirty people finished without trusting thirty screenshots.

## Longevity

The Testnet is reset from time to time, and the transactions in your pack will eventually stop resolving. That is a property of a test network, not a flaw in the record — the pack keeps the ledger indices and close times, so a reader years from now can tell that these events were real and that the network they lived on has since been rebuilt.

On Mainnet, the same mechanism would be permanent. That is the thing the lessons are actually teaching.
