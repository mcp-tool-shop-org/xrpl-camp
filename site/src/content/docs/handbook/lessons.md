---
title: Lessons
description: All 6 lessons — from mental model to a record you can prove.
sidebar:
  order: 2
---

XRPL Camp has 6 lessons that build on each other. Complete them in order for the best experience — and if one fails, the run stops there rather than walking on and pretending.

```bash
xrpl-camp start
```

## Lesson 1 — Mental Model

What the XRPL is: accounts, balances, transactions, and memos. Rather than asserting that the ledger is live and public, this lesson asks it — the ledger index it prints is the real one, and it moves while you read.

The unit that matters: **1 XRP = 1,000,000 drops**. Everything the ledger does is denominated in drops.

## Lesson 2 — Create Wallet

Generate a Testnet keypair:

```bash
xrpl-camp wallet create
```

Your seed is stored locally in `.xrpl-camp/wallet.json` — owner-only on POSIX — and never leaves your machine. Nobody issued this identity to you; you generated it.

## Lesson 3 — Fund Wallet

Get free test XRP from the Testnet faucet:

```bash
xrpl-camp fund
```

You will be funded 100 XRP and be able to spend about 99. That gap is the **base reserve**: a balance the ledger locks for as long as the account exists. It is not a fee and nobody took it — it is the cost of occupying space in a shared ledger, and you get it back if the account is ever deleted.

Test XRP has no real value. Nothing here is at risk.

## Lesson 4 — Send Payment

Write a memo to the ledger:

```bash
xrpl-camp send --memo "hello from camp"
```

The payment goes to a **mailbox** — a second wallet the tool creates for you, whose seed is saved next to your own. Both ends belong to you.

The first payment is the interesting one. The mailbox account does not exist yet, so the payment carries the base reserve and **brings the account into being**. The transaction metadata contains a `CreatedNode` naming an address that did not exist a moment earlier. Nobody approved it; nobody could have stopped it.

Later sends to the same mailbox cost 1 drop, because the account already exists.

The fee — around 10 drops — is **destroyed**. It is not our charge, and it does not go to a miner or a validator. That XRP simply stops existing, which is why spamming the ledger costs something real and why nobody profits from your transaction.

## Lesson 5 — Verify Transaction

Look up what you wrote:

```bash
xrpl-camp verify --tx <hash>
```

This queries the ledger and shows exactly what it recorded — sender, destination, amount actually delivered, fee, ledger index, and your memo read back out of the transaction.

The memo comparison is the point. The tool shows what you typed next to what the ledger returned, and they are compared rather than merely displayed. The second one is not our copy of your message; it came back from the network.

Lesson 5 credits only a transaction **you** sent. You can look up anybody's transaction — that is what a public ledger means — but reading someone else's is not the same as having written one.

## Lesson 6 — Certificate

```bash
xrpl-camp certificate
```

This writes two files you keep: a certificate, and a proof pack. See [Proof Pack](/xrpl-camp/handbook/proof-pack/) for what they prove and, just as importantly, what they do not.

The certificate refuses to seal a record whose prerequisite lessons did not complete. A partial run is recorded honestly as a partial run.

## After the six

The lessons end; the ledger does not.

```bash
xrpl-camp read                  # your entries, read back off the ledger
xrpl-camp read <address>        # what somebody else wrote — no key needed
xrpl-camp try                   # break it on purpose. Costs nothing.
```

`xrpl-camp try` is worth the two minutes. It runs seven deliberate failures against the live network using the ledger's `simulate` facility — nothing is signed and nothing is submitted, so it costs zero drops — and then shows you the receipt: which of those failures would have reached the ledger and charged you, and which were refused before the ledger ever saw them.

The three-letter prefix on an XRPL result code tells you which, before you press send:

| Prefix | Meaning | Cost |
|--------|---------|------|
| `tes` | success | the fee |
| `tec` | the ledger accepted the transaction and recorded that it failed | the fee — you pay |
| `tem` | malformed | nothing — never applied |
| `tel` | rejected locally by the server | nothing |
| `tef` | already stale (e.g. a replayed sequence number) | nothing |

## Endpoint and state

```bash
export XRPL_CAMP_RPC_URL="https://your-node:51234/"
```

The tool checks the endpoint's network before signing anything and refuses one it cannot confirm is a test network.

State lives in `./.xrpl-camp` — the folder you ran the tool in. `xrpl-camp status --detail` prints the resolved absolute path, and `XRPL_CAMP_HOME` overrides it.
