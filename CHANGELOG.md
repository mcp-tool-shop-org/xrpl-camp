# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

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
