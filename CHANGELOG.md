# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.3.0] - 2026-04-15

### Added

- `status --detail` — expanded view with wallet state, session timing, last activity, txids, and next-step hint
- Lesson 6 completion bundle — certificate, proof pack, explorer link, and verify hint in one coherent panel
- 4 new tests for `status --detail` behavior

### Changed

- README: updated commands table (proof verify, status --detail), dry-run section (non-mutating semantics), proof pack section (verify command)
- Handbook: getting-started (dry-run semantics), reference (proof verify, status --detail), proof-pack (verification command)
- Lesson 6 output restructured from log lines to a green completion panel

## [1.2.1] - 2026-04-15

### Changed

- Lesson 4: memo triple-view shows plain text, hex encoding, and amount/fee explanation
- Lesson 5: explorer URL elevated as independent witness ("You don't have to trust this tool")
- Lesson 5: memo field labeled "Memo (readback)" to complete the encoding round trip

## [1.2.0] - 2026-04-15

### Added

- `DryRunSession` — dry-run is now a non-mutating execution mode with zero disk writes
- `ExecutionMode` enum — centralized mode gating instead of scattered conditionals
- `xrpl-camp proof verify <file>` — local proof pack integrity verification (pass/fail, hash, schema, address, lesson count)
- `--json` flag on `proof verify` for machine-readable output
- 5 typed transport exceptions: `XRPLConnectionError`, `XRPLAccountNotFound`, `XRPLUnfundedAccount`, `XRPLTransactionFailed`, `XRPLMalformedResponse`
- Wallet in-memory cache for dry-run mode (no `.xrpl-camp/` writes)
- Reset command guard — refuses to run in dry-run mode
- 27 new tests covering dry-run semantics, proof verification CLI, and transport exceptions

### Changed

- Dry-run no longer creates wallet files, session files, certificates, or proof packs
- Dry-run guided flow uses `DryRunSession` (ephemeral) instead of `Session` (persisted)
- Lesson 6 in dry-run explicitly refuses artifacts with `⚠ SIMULATION` message
- Completion banner in dry-run shows yellow "Simulation" panel instead of green "Complete"
- `get_balance()` raises typed exceptions instead of silently returning 0
- `fund_wallet()`, `send_memo_payment()`, `lookup_tx()` distinguish connection errors from transaction failures
- Lessons 3–5 map typed transport exceptions to specific `CampError` messages (connection vs faucet vs lookup vs balance)
- Standalone `--dry-run` commands (`fund`, `send`, `verify`) use `DryRunSession.from_existing()` to read but never write

### Fixed

- Dry-run `start` no longer creates `.xrpl-camp/wallet.json` during lesson 2
- Dry-run `start` no longer persists session progress or completion state
- Dry-run `start` no longer writes certificate or proof pack files in lesson 6
- `get_balance()` no longer hides connection failures, unfunded accounts, or malformed responses behind a zero balance

## [1.1.1] - 2026-03-25

### Added

- 3 version consistency tests (semver, >= 1.0.0, CHANGELOG)
- SHA-pinned GitHub Actions in all 4 workflows

## [1.1.0] - 2026-03-19

### Added

- Auto-resume: `start` skips completed lessons and picks up where you left off
- Interactive memo prompt: guided flow asks what you want to write on the ledger
- Lesson timing: each lesson tracks start time and duration
- `status` command: rich visual checklist with completion times and next-up marker
- Total training duration shown in certificate, proof pack, and completion banner
- `Session.total_duration()` and `Session.get_progress()` helpers
- 19 new tests covering timing, status, auto-resume, and backward compat

### Changed

- Certificate includes `duration_seconds` when timing data is available
- Guided flow shows "Welcome back" when resuming, early-exits when all 6 done
- Bumped to v1.1.0 (new features, fully backward-compatible session format)

## [1.0.0] - 2026-03-02

### Added

- Shipcheck compliance (SHIP_GATE.md, SCORECARD.md, verify script)
- Landing page via @mcptoolshop/site-theme
- README translations (8 languages)

### Changed

- Promoted to v1.0.0 (production-stable)
- Development Status classifier: Alpha → Production/Stable

## [0.2.0] - 2026-03-02

### Added

- Dry-run mode (`--dry-run`) for `start`, `fund`, `send`, and `verify` commands
- Proof pack generation (`xrpl_camp_proof_pack.json`) with SHA-256 integrity hash
- `reset` command with typed "RESET" confirmation
- Endpoint override via `XRPL_CAMP_RPC_URL` environment variable
- Structured error handling (`CampError` with code, message, hint, retryable)
- Brand logo in README

## [0.1.0] - 2026-03-02

### Added

- 6-lesson guided flow: mental model, create wallet, fund, send payment, verify, certificate
- CLI via Typer + Rich console output
- Testnet wallet creation and funding
- Self-payment with custom memo
- Transaction verification and lookup
- Certificate generation (no private keys exposed)
- Session persistence and state management
- SECURITY.md with threat model
- CI workflow (Python 3.11 + 3.12, ruff, pytest)
- 47 offline tests
