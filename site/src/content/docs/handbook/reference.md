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
| `xrpl-camp status` | Show training progress checklist |
| `xrpl-camp self-check` | Diagnose your environment |
| `xrpl-camp support-bundle` | Write a diagnostic zip for bug reports |

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
| `.xrpl-camp/session.json` | Session progress (lesson completions, timing) |

## Error codes

| Code | Meaning |
|------|---------|
| `NET_FAUCET` | Testnet faucet request failed |
| `NET_SEND` | Transaction submission failed |
| `NET_LOOKUP` | Transaction lookup failed |
| `NET_BALANCE` | Balance check failed |
| `NET_CONNECT` | Could not connect to the RPC endpoint |

## Links

- [GitHub Repository](https://github.com/mcp-tool-shop-org/xrpl-camp)
- [XRPL Testnet Explorer](https://testnet.xrpl.org/)
