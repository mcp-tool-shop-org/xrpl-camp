# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.4.0] - 2026-09-09

A dogfood swarm took this repo from "green CI, dead product" to something that
works. 166 findings audited, 150 fixed, across six waves.

### The three defects that made every shipped channel broken

- **Lesson 4 could not execute.** `send_memo_payment` built a Payment whose
  sender and destination were the same account. xrpl-py 5.x refuses to
  construct it and the ledger would reject it, so lessons 4, 5 and 6 were
  unreachable. Lesson 4 now pays a second "mailbox" wallet the learner also
  owns, funded at the live base reserve — so the payment *creates an account*,
  which the transaction metadata proves.
- **Lesson 5 rendered blank.** `lookup_tx` read `Amount`/`Destination`/
  `Account`/`Fee`/`Memos` from the top level of the `tx` response; under
  rippled API v2 they live in `tx_json`, and `Amount` is `DeliverMax`. The
  parser now reads the right level, keeps a v1 fallback, checks
  `is_successful()`, and pins `api_version` so the shape cannot drift silently
  again.
- **The guided flow had no failure gate.** Against a dead endpoint, all three
  network lessons failed and the tool still wrote a SHA-256-sealed proof pack
  and printed "you funded it, wrote to the ledger, and verified it" — exit 0.
  Lessons now return an explicit result, a failure halts the run, and the
  certificate refuses to seal a record whose prerequisites did not complete.

None of this was visible to CI, because no test in the suite imported `xrpl`
at all.

### Added

- `xrpl-camp read` — your entries read back **off the ledger**; an address
  reads anyone else's; a hash reads one transaction
- `xrpl-camp try` — seven deliberate failures against the live network via the
  `simulate` RPC: no signature, no submission, zero drops. The receipt is the
  lesson — which failures would have reached the ledger and cost you, and how
  the three-letter result prefix tells you which *before* you press send
- `xrpl-camp proof verify --online` — resolves every transaction the pack names
  and checks it exists, was sent by the pack's address, carries the claimed
  memo, and succeeded. Verification never queries the endpoint named inside the
  pack under test
- `proof verify <folder>` — verify a whole workshop at once
- Docker image at `ghcr.io/mcp-tool-shop-org/xrpl-camp`, which warns when
  `/work` is unmounted rather than silently discarding the learner's record
- `--version`, `--yes` (non-interactive), `--verbose`, `--memo` on `start`
- Python 3.13 support, tested in CI

### Changed

- Every transport exception carries a structured `CampError`. The layer above
  could previously distinguish two of eight and collapsed the rest into
  "the network is flaky, retry" — so a corrupt seed was reported as a faucet
  outage, and a wrong-network refusal as congestion
- Retry exists and is bounded, and only the faucet and reads go through it. A
  payment is never retried: a submission whose ledger window lapsed may already
  be on the ledger, and re-sending would write the learner's memo twice
- Lesson 5 credits only a transaction the learner actually sent. Previously a
  hash copied off the explorer completed the lesson
- The reserve is visible; the fee is described honestly as **destroyed**, not
  "paid to validators"
- `verify_proof_pack` no longer claims the pack "can't be faked" — the hash
  detects accidental edits, the ledger is the thing nobody can forge

### Fixed

- Corrupt state produced raw tracebacks from most commands; all 13 such paths
  now exit cleanly with a code and a hint
- `--memo "note [v1]"` displayed something different from what it wrote to the
  ledger
- Unicode output crashed on cp1252 consoles, including the shipped Windows
  binary
- Seed-leak guards were defined and never called; they now run fail-closed
- State writes are atomic; the seed file is 0600 on POSIX

### Release plumbing

`publish.yml` had not run since 2026-03-19. It was not failing — it was not
firing. `release-binaries.yml` created the GitHub Release as `GITHUB_TOKEN`,
and GitHub does not cascade workflow triggers from `GITHUB_TOKEN`-raised
events, so `on: release: published` never fired. Confirmed by authorship:
v1.3.1 and v1.0.6 were released by `github-actions[bot]` and neither published;
v1.1.0 was released by a human and did. Compounding it, the pinned SHA for
`pypa/gh-action-pypi-publish` did not exist in that repository at all (HTTP
422) — a fabricated 40-character value built from a correct 16-character
prefix, introduced after the last successful publish, so it had never run.

**What that meant for anyone installing this tool:**

- PyPI served **1.1.0** from 2026-03-19 until this release
- npm served **1.3.2**, a version that exists nowhere in git and has no tag,
  no release, and no changelog entry. Its launcher pinned the v1.3.1 binaries,
  so `npx` ran 1.3.1 while reporting 1.3.2
- Every channel shipped the broken lesson flow described above

Now: one tag push runs `publish.yml` (binaries → GitHub Release → PyPI →
**verify the registry actually serves it**) and `release.yml` (npm via OIDC
trusted publishing). Both filenames are load-bearing for their registry's
trusted publisher and are commented as such. A publish that silently no-ops
fails loudly instead.

## [1.3.1] - 2026-04-15

### Changed

- Lesson closers: replaced 6 identical "What you just proved:" lines with distinct progression markers (✓ Foundation set → ✓ Identity created → ✓ Account funded → ✓ Written to the ledger → ✓ Independently verified → ✓ Record sealed)
- Lesson 2 panel: added "Your seed stays on this machine" reassurance
- Lesson 3 panel: added "nothing at risk" to Testnet money description
- Guided flow welcome: "No sign-ups" replaces "No accounts"
- Completion banner: reworked as retrospective checklist with celebratory tone
- Dry-run completion: shortened and softened
- Reset: added Testnet-data reassurance, "Clean slate" replaces "Reset complete"
- README: added positioning section ("Why this instead of a generic tutorial") and workshop/classroom section
- Landing page: sharper hero copy, workshop-ready features, npx install, status/proof commands in table
- Handbook: updated voice across getting-started, lessons, and index pages
- GitHub repo metadata: updated description and topics

### Added

- `npm/` directory: @mcptoolshop/xrpl-camp npm wrapper for `npx` distribution
- Published @mcptoolshop/xrpl-camp v1.3.1 to npm

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
