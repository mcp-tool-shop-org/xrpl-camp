---
title: Getting Started
description: Install XRPL Camp and start the guided flow.
sidebar:
  order: 1
---

XRPL Camp teaches the XRP Ledger through hands-on lessons. No sign-ups, no real money — just you and the ledger.

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

Every networked command supports `--dry-run`. In dry-run mode:

- **No network calls** — transactions, faucet requests, and lookups are simulated
- **No disk writes** — no wallet file, no session persistence, no artifacts
- **No misleading output** — lesson 6 refuses to generate certificates from simulated runs

Dry-run may read existing state (e.g. your wallet address) but never mutates anything.

```bash
xrpl-camp start --dry-run
```

Useful for confidence-building before your first real run, or for environments without network access.

## What you end up with

After completing all 6 lessons:

- A funded Testnet wallet (local, gitignored — never leaves your machine)
- A confirmed payment on a real public ledger
- A memo you chose, permanently recorded and independently verifiable
- A certificate (`xrpl_camp_certificate.json`) — safe to share, no private keys
- A proof pack (`xrpl_camp_proof_pack.json`) — tamper-evident, SHA-256 hashed

## Next steps

- Read about each [lesson](/xrpl-camp/handbook/lessons/) in detail
- Learn about the [proof pack](/xrpl-camp/handbook/proof-pack/) and certificates
