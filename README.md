<p align="center">
  <a href="README.md">English</a> | <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/xrpl-camp/readme.png" width="400" alt="XRPL Camp">
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/xrpl-camp/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/xrpl-camp/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/xrpl-camp/"><img src="https://img.shields.io/pypi/v/xrpl-camp?label=PyPI" alt="PyPI version"></a>
  <a href="https://www.npmjs.com/package/@mcptoolshop/xrpl-camp"><img src="https://img.shields.io/npm/v/@mcptoolshop/xrpl-camp?label=npm" alt="npm version"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/xrpl-camp/"><img src="https://img.shields.io/badge/Landing_Page-live-blue" alt="Landing Page"></a>
</p>

Learn the XRP Ledger in one sitting. No accounts. No real money. Just you and the ledger.

Most blockchain tutorials teach concepts. XRPL Camp makes you _do_ them — create a wallet, fund it, write a permanent memo to a public ledger, verify it independently, and walk away with a record anyone can check against the ledger itself. The whole arc takes about ten minutes.

Built for workshops, classrooms, and self-study. The guided flow resumes where you left off, a failed lesson stops the run instead of pretending, and nothing claims to have happened that didn't.

## Why this instead of a generic tutorial

- **Real transactions, not slides.** You write to an actual ledger. When lesson 5 says "verify it yourself," it hands you a hash and an explorer link that anyone can check.
- **Your payment brings an account into existence.** Lesson 4 isn't a toy transfer — it funds a second account that did not exist a moment earlier, and whose keys are also yours.
- **Failure is part of the curriculum.** `xrpl-camp try` breaks things on purpose against the live network, then shows you which failures would have cost money and which are free — *before* you ever press send.
- **Proof you can actually check.** The proof pack names real transactions, and `proof verify --online` asks the ledger whether they happened. That part nobody can fake.
- **Safe by design.** Testnet only. Test XRP has no value. Your seed never leaves your machine. No telemetry, no analytics, no accounts.

## Install

**No Python required** (downloads a prebuilt binary):

```bash
npx @mcptoolshop/xrpl-camp start
```

With Python:

```bash
pipx install xrpl-camp
```

In Docker — for workshops where installing things is the hard part:

```bash
docker run --rm -it -v "$PWD:/work" ghcr.io/mcp-tool-shop-org/xrpl-camp start
```

> Mount a volume. Everything you make — wallet, certificate, proof pack — is written to `/work`, and an unmounted container throws it away on exit. The image tells you if you forgot.

## Quick Start

```bash
xrpl-camp start
```

Six lessons, in order, resuming if you restart:

1. **Mental Model** — what the XRPL is, asked of the live network rather than asserted
2. **Create Wallet** — generate a Testnet keypair; the seed stays on your machine
3. **Fund Wallet** — free test XRP from the faucet, and why some of it is not spendable
4. **Send Payment** — write your memo to the ledger, in a payment that creates an account
5. **Verify Transaction** — look up what you wrote and compare it to what you typed
6. **Certificate** — a record you keep, and can prove

## Commands

| Command | What it does |
|---------|-------------|
| `xrpl-camp start` | Guided flow through all 6 lessons (auto-resumes) |
| `xrpl-camp start --memo "..."` | Supply lesson 4's message up front, for scripted or non-interactive runs |
| `xrpl-camp read` | Your entries, read back **off the ledger** — not off this machine |
| `xrpl-camp read <address>` | What somebody else wrote. No key, no login, no permission |
| `xrpl-camp read <hash>` | One transaction, in full |
| `xrpl-camp try` | Break it on purpose against the live network. Signs nothing, costs nothing |
| `xrpl-camp status` | Progress checklist, with timings |
| `xrpl-camp status --detail` | Facilitator view: wallet, endpoint, state directory, next step |
| `xrpl-camp wallet create` / `show` | Create or display your Testnet wallet |
| `xrpl-camp fund` | Fund your wallet via the Testnet faucet |
| `xrpl-camp send --memo "hello"` | Send a memo payment to your mailbox |
| `xrpl-camp verify --tx <hash>` | Verify a transaction **you** sent |
| `xrpl-camp certificate` | Generate the certificate + proof pack |
| `xrpl-camp proof verify <file>` | Check a proof pack's hash. Fully offline |
| `xrpl-camp proof verify <file> --online` | Also ask the ledger whether the transactions really happened |
| `xrpl-camp proof verify <folder>` | Verify every pack in a folder — for facilitators |
| `xrpl-camp reset` | Wipe all state (requires typing `RESET`) |
| `xrpl-camp self-check` | Diagnose your environment **and** your connection to the ledger |
| `xrpl-camp support-bundle` | Write a diagnostic zip for bug reports |

Global flags: `--version`, `--dry-run`, `--yes` (non-interactive), `--verbose` (technical detail on errors).

## What You End Up With

- A funded Testnet wallet, local and gitignored
- A **second account that did not exist until your payment created it** — and whose keys are also yours
- A memo you chose, permanently recorded and independently readable
- A certificate (`xrpl_camp_certificate.json`) — safe to share, no private keys
- A proof pack (`xrpl_camp_proof_pack.json`) — naming real transactions anyone can resolve

## About that proof

The proof pack carries a SHA-256 hash. That hash detects an accidental edit. It is **not** a signature, and on its own it does not prove the pack is genuine — anyone can change a field and recompute the hash with the same public function this tool uses.

What cannot be faked is the ledger:

```bash
xrpl-camp proof verify xrpl_camp_proof_pack.json --online
```

This resolves every transaction the pack names and checks that it exists, was sent by the pack's address, carries the memo the pack claims, and closed successfully. A pack with a rewritten address passes the offline hash check and fails this one.

Two details worth knowing, because both are easy to get wrong:

- Verification always queries the public Testnet (or `--rpc-url`), **never** the endpoint named inside the pack. A forged pack can name a server its author controls.
- The XRPL Testnet is periodically reset. When that happens, honest transactions stop resolving. The pack records each transaction's ledger index, so a reset reports as *unverifiable* (exit 3) rather than as fraud (exit 1).

Offline verification remains the default and makes no network calls, so it still works on a plane or a locked-down classroom machine.

## Dry-Run Mode

```bash
xrpl-camp start --dry-run
```

No network calls, no disk writes, and no misleading output — lesson 6 explicitly refuses to generate artifacts. Dry-run may *read* existing state, but never mutates anything.

## Endpoint and State

```bash
export XRPL_CAMP_RPC_URL="https://your-node:51234/"
```

The tool refuses endpoints it cannot confirm are Testnet, before signing anything. Set `XRPL_CAMP_ALLOW_ANY_NETWORK=1` only if you understand what you are pointing it at.

State lives in `./.xrpl-camp` by default — a sitting belongs to the folder you ran it in. `XRPL_CAMP_HOME` overrides that, and `xrpl-camp status --detail` prints the resolved absolute path.

## Security

Your seed is stored locally in `.xrpl-camp/wallet.json` (owner-only on POSIX) and is never included in the certificate or proof pack — generation refuses to write an artifact containing one.

This tool **defaults to** the XRPL Testnet, where test XRP has no real value, and refuses non-Testnet endpoints unless you explicitly opt out. No telemetry, no analytics, no phone-home.

See [SECURITY.md](SECURITY.md).

## Threat Model

| Threat | Mitigation |
|--------|-----------|
| Seed leaked into an artifact | Generation runs a seed check built on xrpl-py's own `decode_seed` and **refuses to write the file** if it trips |
| Seed committed to git | `.xrpl-camp/` is gitignored *in this repo*; state is written to your working directory, so add it to your own `.gitignore` |
| Seed readable by other users | Wallet file 0600, state directory 0700 on POSIX |
| Learner pastes a secret into a public memo | Memo text is scanned for seed-shaped strings and refused before submission |
| Testnet seed reused on Mainnet | Warned at wallet creation; the tool refuses non-Testnet endpoints by default |
| Proof pack tampering | SHA-256 detects casual edits; `--online` detects a re-sealed forgery by asking the ledger |
| Verifying against an attacker's endpoint | `--online` never uses the endpoint named in the pack under test |
| Diagnostics leaking your identity | `support-bundle` redacts home directory and account name |

## For Workshops and Classrooms

- **One command per learner.** `npx`, `pipx`, or the container — no shared setup.
- **Failure is free.** `xrpl-camp try` teaches the failure modes without spending anything, so a learner who breaks something on purpose learns more than one who doesn't.
- **Facilitator triage.** `status --detail` shows wallet, endpoint and state directory. `self-check` probes the actual connection instead of reporting a hopeful OK.
- **Verify the whole room at once.** `proof verify <folder> --online` checks every learner's pack against the ledger.
- **Rate limits are real.** Thirty people hitting one faucet will meet it; the tool retries with backoff and says so rather than blaming your wifi.

## Development

```bash
git clone https://github.com/mcp-tool-shop-org/xrpl-camp.git
cd xrpl-camp
uv sync --dev
bash scripts/verify.sh     # lint + tests + build + smoke
```

## License

MIT

---

Built by [MCP Tool Shop](https://mcp-tool-shop.github.io/)
