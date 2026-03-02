<p align="center">
  <strong>XRPL Camp</strong>
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/xrpl-camp/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/xrpl-camp/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
</p>

Learn the XRP Ledger in one sitting. No accounts. No real money. Just you and the ledger.

XRPL Camp walks you through 6 lessons — from "what is a ledger?" to a funded wallet, a confirmed payment, and a portable certificate — in about 10 minutes.

## Install

```bash
pipx install xrpl-camp
```

Or with pip:

```bash
pip install xrpl-camp
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
| `xrpl-camp wallet create` | Create a Testnet wallet |
| `xrpl-camp wallet show` | Display your wallet address |
| `xrpl-camp fund` | Fund your wallet via the Testnet faucet |
| `xrpl-camp send --memo "hello"` | Send a self-payment with a custom memo |
| `xrpl-camp verify --tx <hash>` | Verify a transaction on the ledger |
| `xrpl-camp certificate` | Generate your completion certificate |

## What You End Up With

- A funded Testnet wallet (`.xrpl-camp/wallet.json` — local, gitignored)
- A confirmed payment on the XRPL Testnet
- A verification report showing exactly what the ledger recorded
- A certificate (`xrpl_camp_certificate.json`) — safe to share, no private keys

## Security

Your seed (private key) is stored locally and never included in the certificate.
This tool only uses the XRPL **Testnet** — test XRP has no real value.

See [SECURITY.md](SECURITY.md) for details.

## Threat Model

| Threat | Mitigation |
|--------|-----------|
| Seed leakage via certificate | Certificate generation explicitly excludes seed; `certificate_has_seed()` safety check |
| Seed in git | `.xrpl-camp/` is gitignored; `wallet show` never displays seed |
| Testnet seed reuse on Mainnet | Warning displayed during wallet creation |
| Memo content exposure | All memos are public by design; users are warned before sending |

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
