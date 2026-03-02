<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/xrpl-camp/readme.png" width="400" alt="XRPL Camp">
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/xrpl-camp/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/xrpl-camp/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/xrpl-camp/"><img src="https://img.shields.io/badge/Landing_Page-live-blue" alt="Landing Page"></a>
</p>

Learn the XRP Ledger in one sitting. No accounts. No real money. Just you and the ledger.

XRPL Camp walks you through 6 lessons — from "what is a ledger?" to a funded wallet, a confirmed payment, and a portable certificate — in about 10 minutes.

## Install

**No Python required** (downloads a prebuilt binary):

```bash
npx @mcptoolshop/xrpl-camp start
```

Or with Python:

```bash
pipx install xrpl-camp
```

## Quick Start

```bash
xrpl-camp start
```

This runs the guided flow through all 6 lessons:

1. **Mental Model** — What the XRPL is (accounts, balances, transactions, memos)
2. **Create Wallet** — Generate a Testnet keypair
3. **Fund Wallet** — Get free test XRP from the faucet
4. **Send Payment** — Write a memo to the ledger (self-payment, 1 drop)
5. **Verify Transaction** — Look up what you wrote
6. **Certificate** — Get a portable, verifiable record of what you did

## Commands

| Command | What it does |
|---------|-------------|
| `xrpl-camp start` | Guided flow through all 6 lessons |
| `xrpl-camp start --dry-run` | Walk the full flow without network calls |
| `xrpl-camp wallet create` | Create a Testnet wallet |
| `xrpl-camp wallet show` | Display your wallet address |
| `xrpl-camp fund` | Fund your wallet via the Testnet faucet |
| `xrpl-camp fund --dry-run` | See what funding would do, no network |
| `xrpl-camp send --memo "hello"` | Send a self-payment with a custom memo |
| `xrpl-camp send --dry-run` | Simulate the payment |
| `xrpl-camp verify --tx <hash>` | Verify a transaction on the ledger |
| `xrpl-camp certificate` | Generate certificate + proof pack |
| `xrpl-camp reset` | Wipe all state (requires typed confirmation) |

## What You End Up With

- A funded Testnet wallet (`.xrpl-camp/wallet.json` — local, gitignored)
- A confirmed payment on the XRPL Testnet
- A verification report showing exactly what the ledger recorded
- A certificate (`xrpl_camp_certificate.json`) — safe to share, no private keys
- A proof pack (`xrpl_camp_proof_pack.json`) — tamper-evident, SHA-256 hashed

## Dry-Run Mode

Every networked command supports `--dry-run`. It prints what would happen without making any network calls or changing state. Useful for confidence-building and debugging.

## Proof Pack

The proof pack is a tamper-evident record of everything you did:

- Wallet address and network
- Lesson completion timestamps
- Transaction IDs with explorer URLs
- Tool version
- SHA-256 hash of the entire content

Anyone can verify the hash to confirm the file hasn't been edited.

## Endpoint Override

By default, XRPL Camp uses the public XRPL Testnet node. To use a different endpoint:

```bash
export XRPL_CAMP_RPC_URL="https://your-node:51234/"
xrpl-camp fund
```

## Security

Your seed (private key) is stored locally and never included in the certificate or proof pack.
This tool only uses the XRPL **Testnet** — test XRP has no real value.
No telemetry, no analytics, no phone-home — the only network calls go to the XRPL Testnet.

See [SECURITY.md](SECURITY.md) for details.

## Threat Model

| Threat | Mitigation |
|--------|-----------|
| Seed leakage via certificate | Certificate generation explicitly excludes seed; `certificate_has_seed()` safety check |
| Seed leakage via proof pack | Proof pack generation excludes seed; `proof_pack_has_seed()` safety check |
| Seed in git | `.xrpl-camp/` is gitignored; `wallet show` never displays seed |
| Testnet seed reuse on Mainnet | Warning displayed during wallet creation |
| Memo content exposure | All memos are public by design; users are warned before sending |
| Proof pack tampering | SHA-256 integrity hash; `verify_proof_pack()` detects modification |

## Development

```bash
git clone https://github.com/mcp-tool-shop-org/xrpl-camp.git
cd xrpl-camp
uv sync --dev
uv run ruff check .
uv run pytest tests/ -v
```

## License

MIT

---

Built by [MCP Tool Shop](https://mcp-tool-shop.github.io/)
