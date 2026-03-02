# Security

## Seed Handling

XRPL Camp creates a **Testnet wallet** with a cryptographic seed (private key).

- The seed is stored locally in `.xrpl-camp/wallet.json`
- The `.xrpl-camp/` directory is gitignored by default
- The certificate (`xrpl_camp_certificate.json`) **never** contains your seed
- `xrpl-camp wallet show` displays your address but **never** your seed

## Testnet Only

This tool only connects to the XRPL **Testnet**. Test XRP has no real value.

**Never use a Testnet seed on Mainnet.** If you do, anyone who had access to your
Testnet seed could spend your real funds.

## What Gets Shared

| Data | Where | Public? |
|------|-------|---------|
| Address | Certificate, ledger | Yes — safe to share |
| Seed | `.xrpl-camp/wallet.json` only | **No — never share** |
| Transactions | XRPL Testnet | Yes — permanent and public |
| Memos | XRPL Testnet | Yes — permanent and public |
| Certificate | `xrpl_camp_certificate.json` | Yes — safe to share |

## Reporting

If you find a security issue, please open a GitHub issue or email
64996768+mcp-tool-shop@users.noreply.github.com.
