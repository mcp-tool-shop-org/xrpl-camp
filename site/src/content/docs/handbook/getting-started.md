---
title: Getting Started
description: Install XRPL Camp and start the guided flow.
sidebar:
  order: 1
---

XRPL Camp teaches the XRP Ledger through hands-on lessons. No accounts, no real money, just you and the ledger.

## Installation

No Python required — downloads a prebuilt binary:

```bash
npx @mcptoolshop/xrpl-camp start
```

Or install with Python:

```bash
pipx install xrpl-camp
```

## Start the guided flow

```bash
xrpl-camp start
```

This walks you through all 6 lessons in order. Each lesson builds on the previous one and takes about 1–2 minutes.

## Dry-run mode

Every networked command supports `--dry-run`. This prints what would happen without making any network calls or changing state:

```bash
xrpl-camp start --dry-run
```

Useful for confidence-building before your first real run, or for environments without network access.

## What you end up with

After completing all 6 lessons:

- A funded Testnet wallet (`.xrpl-camp/wallet.json` — local, gitignored)
- A confirmed payment on the XRPL Testnet
- A verification report showing what the ledger recorded
- A certificate (`xrpl_camp_certificate.json`) — safe to share, no private keys
- A proof pack (`xrpl_camp_proof_pack.json`) — tamper-evident, SHA-256 hashed

## Next steps

- Read about each [lesson](/xrpl-camp/handbook/lessons/) in detail
- Learn about the [proof pack](/xrpl-camp/handbook/proof-pack/) and certificates
