---
title: Beginners
description: New to blockchain? This page explains what XRPL Camp does and why, with no assumed knowledge.
sidebar:
  order: 99
---

New to blockchain? This page explains the concepts behind XRPL Camp before you type a single command.

## What is a blockchain?

A blockchain is a shared record book that nobody owns and everybody can read. When someone writes an entry, it stays there permanently. No single person can erase or change past entries because thousands of computers around the world each keep their own copy.

Traditional databases have an owner who can edit or delete records. A blockchain has no single owner -- the network enforces the rules instead.

## What is the XRP Ledger?

The XRP Ledger (XRPL) is one specific blockchain. It was designed for fast, low-cost payments. A transaction typically settles in 3-5 seconds and costs a fraction of a cent.

XRPL Camp uses the **Testnet** -- a practice version of the real ledger. Test XRP has no monetary value. You cannot accidentally spend real money.

## Key concepts

These are the four ideas you need before starting:

- **Account** -- Your identity on the ledger. A public address that anyone can look up, like a mailbox number.
- **Balance** -- How much XRP your account holds, measured in "drops" (1 XRP = 1,000,000 drops).
- **Transaction** -- An entry written to the ledger. Once confirmed, it cannot be erased.
- **Memo** -- A text note attached to a transaction. Memos are public and permanent.

## What XRPL Camp teaches

XRPL Camp walks you through 6 lessons in about 10 minutes:

1. **Mental Model** -- Understand accounts, balances, transactions, and memos.
2. **Create Wallet** -- Generate a cryptographic keypair (public address + private seed).
3. **Fund Wallet** -- Get free test XRP from the Testnet faucet.
4. **Send Payment** -- Write a custom memo to the ledger via a 1-drop self-payment.
5. **Verify Transaction** -- Query the ledger to confirm what you wrote.
6. **Certificate** -- Receive a portable, tamper-evident record of your learning.

Each lesson builds on the previous one. The guided flow (`xrpl-camp start`) handles the order automatically and resumes where you left off if you stop partway through.

## Safety and privacy

XRPL Camp is designed to be safe for absolute beginners:

- **Testnet only** -- No real money is ever involved. Test XRP has zero value.
- **Local storage** -- Your private key (seed) is saved in `.xrpl-camp/wallet.json` on your machine and never leaves it.
- **No telemetry** -- The tool makes no analytics calls. The only network traffic goes to the XRPL Testnet.
- **Certificate safety** -- The certificate and proof pack never include your seed. A built-in safety check (`certificate_has_seed()`) enforces this.
- **Dry-run mode** -- Every networked command supports `--dry-run` so you can see what would happen before committing.

## How to start

Install with a single command (no Python required):

```bash
npx @mcptoolshop/xrpl-camp start
```

Or with Python:

```bash
pipx install xrpl-camp
xrpl-camp start
```

The guided flow will walk you through each lesson with explanations, pauses between steps, and a summary of what you proved at each stage.

## Glossary

| Term | Definition |
|------|-----------|
| **Address** | Your public identity on the XRPL, safe to share with anyone |
| **Seed** | Your private key -- never share it, never commit it to git |
| **Drop** | The smallest unit of XRP (1 XRP = 1,000,000 drops) |
| **Faucet** | A Testnet service that gives free test XRP for development |
| **Memo** | A text note attached to a transaction, public and permanent |
| **Proof pack** | A tamper-evident JSON file with a SHA-256 integrity hash |
| **Certificate** | A portable record of completed lessons, safe to share |
| **Testnet** | A practice network that mirrors the real XRPL but uses valueless test XRP |
| **Dry run** | A simulation mode that shows what would happen without network calls |
| **Transaction hash** | A unique identifier for a specific transaction on the ledger |
