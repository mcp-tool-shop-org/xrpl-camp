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

Most blockchain tutorials teach concepts. XRPL Camp makes you _do_ them — create a wallet, fund it, write a permanent memo to a public ledger, verify it independently, and walk away with a portable, tamper-evident certificate. The whole arc takes about 10 minutes.

Built for workshops, classrooms, and self-study. The guided flow resumes where you left off, every lesson gives clear feedback, and the completion certificate is SHA-256 verifiable so it can't be faked.

## Why this instead of a generic tutorial

- **Real transactions, not slides.** You write to an actual ledger. When lesson 5 says "verify it yourself," it gives you an explorer link anyone can check.
- **10 minutes, not 10 weeks.** Six lessons, each about 90 seconds. No prerequisites beyond a terminal.
- **Portable proof.** The certificate and proof pack are JSON files with a SHA-256 integrity hash. Anyone can verify they haven't been edited.
- **Safe by design.** Testnet only — test XRP has no value. Your seed never leaves your machine. No telemetry, no analytics, no accounts.
- **Workshop-ready.** `status --detail` gives facilitators a triage view. Dry-run mode lets learners preview the flow without network access.

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

This runs the guided flow through all 6 lessons. If you restart, it picks up where you left off.

**The 6 lessons:**

1. **Mental Model** — What the XRPL is (accounts, balances, transactions, memos)
2. **Create Wallet** — Generate a Testnet keypair (your seed stays on your machine)
3. **Fund Wallet** — Get free test XRP from the faucet (nothing at risk)
4. **Send Payment** — Write a memo to the ledger (the moment people remember)
5. **Verify Transaction** — Look up what you wrote (you don't have to trust this tool)
6. **Certificate** — Get a portable, verifiable record of everything you did

## Commands

| Command | What it does |
|---------|-------------|
| `xrpl-camp start` | Guided flow through all 6 lessons (auto-resumes if you restart) |
| `xrpl-camp start --dry-run` | Non-mutating simulation: no network calls, no disk writes |
| `xrpl-camp status` | Show your progress — visual checklist with timing |
| `xrpl-camp status --detail` | Expanded view with wallet state, timing, and next-step hint |
| `xrpl-camp wallet create` | Create a Testnet wallet |
| `xrpl-camp wallet show` | Display your wallet address |
| `xrpl-camp fund` | Fund your wallet via the Testnet faucet |
| `xrpl-camp fund --dry-run` | See what funding would do, no network |
| `xrpl-camp send --memo "hello"` | Send a self-payment with a custom memo |
| `xrpl-camp send --dry-run` | Simulate the payment |
| `xrpl-camp verify --tx <hash>` | Verify a transaction on the ledger |
| `xrpl-camp certificate` | Generate certificate + proof pack |
| `xrpl-camp proof verify <file>` | Verify a proof pack's integrity locally |
| `xrpl-camp proof verify <file> --json` | Machine-readable verification output |
| `xrpl-camp reset` | Wipe all state (requires typed confirmation) |
| `xrpl-camp self-check` | Diagnose your environment (paste output into bug reports) |
| `xrpl-camp support-bundle` | Write a diagnostic zip for bug reports |

## What You End Up With

- A funded Testnet wallet (local, gitignored — never leaves your machine)
- A confirmed payment on a real public ledger
- A memo you chose, permanently recorded and independently verifiable
- A certificate (`xrpl_camp_certificate.json`) — safe to share, no private keys
- A proof pack (`xrpl_camp_proof_pack.json`) — tamper-evident, SHA-256 hashed

## Dry-Run Mode

Every networked command supports `--dry-run`. In dry-run mode:

- **No network calls** — transactions, faucet requests, and lookups are simulated
- **No disk writes** — no wallet file, no session persistence, no artifacts
- **No misleading output** — lesson 6 explicitly refuses to generate certificates or proof packs

Dry-run may read existing wallet/session state from disk (e.g. `fund --dry-run` uses your existing wallet address), but it never mutates anything.

```bash
xrpl-camp start --dry-run
```

## Proof Pack

The proof pack is a tamper-evident record of everything you did:

- Wallet address and network
- Lesson completion timestamps
- Transaction IDs with explorer URLs
- Tool version
- SHA-256 hash of the entire content

Anyone can verify the hash to confirm the file hasn't been edited:

```bash
xrpl-camp proof verify xrpl_camp_proof_pack.json
```

Add `--json` for machine-readable output. Verification is fully local — no network calls.

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

## For Workshops and Classrooms

XRPL Camp is designed to run in facilitated settings:

- **Guided flow** — `xrpl-camp start` handles the order, resumes on restart, and asks the learner what they want to write on the ledger
- **Dry-run preview** — `xrpl-camp start --dry-run` lets learners see the full flow before committing (good for environments without network access)
- **Facilitator triage** — `xrpl-camp status --detail` shows wallet state, timing, and next-step hints so you can see who is stuck and where
- **Proof of completion** — the SHA-256-verified proof pack means you can confirm completion without trusting screenshots

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
