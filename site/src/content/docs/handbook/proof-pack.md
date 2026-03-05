---
title: Proof Pack
description: Certificates, proof packs, and tamper-evident verification.
sidebar:
  order: 3
---

XRPL Camp generates two artifacts that record your learning journey: a certificate and a proof pack.

## Certificate

The certificate (`xrpl_camp_certificate.json`) is a portable record of what you did. It includes your wallet address, network, and lesson completions — but never your seed (private key).

Generate it after completing all lessons:

```bash
xrpl-camp certificate
```

Safe to share publicly. The generation process has a `certificate_has_seed()` safety check that prevents accidental seed inclusion.

## Proof pack

The proof pack (`xrpl_camp_proof_pack.json`) is a tamper-evident record of everything you did:

- Wallet address and network
- Lesson completion timestamps
- Transaction IDs with explorer URLs
- Tool version
- SHA-256 hash of the entire content

Anyone can verify the hash to confirm the file hasn't been edited.

## Verification

The proof pack includes a `verify_proof_pack()` function that detects modification. If someone edits the file, the SHA-256 hash won't match.

## Security

| Aspect | Protection |
|--------|-----------|
| Seed in certificate | Explicitly excluded; safety check enforced |
| Seed in proof pack | Explicitly excluded; safety check enforced |
| Seed in git | `.xrpl-camp/` gitignored; `wallet show` never displays seed |
| Testnet reuse | Warning displayed during wallet creation |
| Memo privacy | All memos are public by design; warning before sending |
| Proof tampering | SHA-256 integrity hash; mismatch detection |
