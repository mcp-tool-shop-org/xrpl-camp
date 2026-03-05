---
title: Lessons
description: All 6 lessons — from mental model to certificate.
sidebar:
  order: 2
---

XRPL Camp has 6 lessons that build on each other. Complete them in order for the best experience.

## Lesson 1 — Mental Model

Learn what the XRPL is: accounts, balances, transactions, and memos. No code, no commands — just the concepts you need before touching the ledger.

## Lesson 2 — Create Wallet

Generate a Testnet keypair:

```bash
xrpl-camp wallet create
```

Your seed (private key) is stored locally in `.xrpl-camp/wallet.json` and never leaves your machine. The directory is gitignored by default.

## Lesson 3 — Fund Wallet

Get free test XRP from the Testnet faucet:

```bash
xrpl-camp fund
```

Test XRP has no real value — it exists purely for learning and experimentation.

## Lesson 4 — Send Payment

Write a memo to the ledger via a self-payment (1 drop):

```bash
xrpl-camp send --memo "hello from camp"
```

This creates a real transaction on the XRPL Testnet with your custom memo permanently recorded.

## Lesson 5 — Verify Transaction

Look up what you wrote:

```bash
xrpl-camp verify --tx <hash>
```

This queries the ledger and confirms the transaction details, including your memo.

## Lesson 6 — Certificate

Get a portable, verifiable record of what you did:

```bash
xrpl-camp certificate
```

This generates a certificate and a tamper-evident proof pack. The certificate is safe to share — it contains no private keys.

## Endpoint override

By default, XRPL Camp uses the public XRPL Testnet node. To use a different endpoint:

```bash
export XRPL_CAMP_RPC_URL="https://your-node:51234/"
xrpl-camp fund
```
