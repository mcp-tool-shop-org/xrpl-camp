---
title: Reference
description: Full command reference for XRPL Camp.
sidebar:
  order: 4
---

## Commands

| Command | Description |
|---------|-------------|
| `xrpl-camp start` | Guided flow through all 6 lessons |
| `xrpl-camp start --dry-run` | Full flow without network calls |
| `xrpl-camp wallet create` | Create a Testnet wallet |
| `xrpl-camp wallet show` | Display your wallet address |
| `xrpl-camp fund` | Fund via the Testnet faucet |
| `xrpl-camp fund --dry-run` | See what funding would do |
| `xrpl-camp send --memo "text"` | Self-payment with custom memo |
| `xrpl-camp send --dry-run` | Simulate the payment |
| `xrpl-camp verify --tx <hash>` | Verify a transaction on-ledger |
| `xrpl-camp certificate` | Generate certificate + proof pack |
| `xrpl-camp reset` | Wipe all state (typed confirmation) |

## Environment variables

| Variable | Description |
|----------|-------------|
| `XRPL_CAMP_RPC_URL` | Custom XRPL Testnet endpoint |

## Generated files

| File | Description |
|------|-------------|
| `.xrpl-camp/wallet.json` | Local wallet (gitignored, never shared) |
| `xrpl_camp_certificate.json` | Portable certificate (safe to share) |
| `xrpl_camp_proof_pack.json` | Tamper-evident proof pack |

## Links

- [GitHub Repository](https://github.com/mcp-tool-shop-org/xrpl-camp)
- [XRPL Testnet Explorer](https://testnet.xrpl.org/)
