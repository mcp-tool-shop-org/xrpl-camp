# Ship Gate

> No repo is "done" until every applicable line is checked.
> Copy this into your repo root. Check items off per-release.

**Tags:** `[all]` every repo · `[npm]` `[pypi]` `[vsix]` `[desktop]` `[container]` published artifacts · `[mcp]` MCP servers · `[cli]` CLI tools

**Measured 2026-09-09 for v1.4.0.** v1.4.1 is a patch that moves a container warning from stdout to stderr and pins LF on shell scripts; it changes nothing any line below measures, so the dates stand rather than being re-stamped to look fresher than the measurement is. Every date below is when the line was last
actually verified, not when it was first written. The previous revision carried
`2026-03-02` on every row and had gone unre-measured across four releases — including
a row that skipped the entire npm section as "not an npm package" while four npm
versions were live. A gate that is not re-measured is decoration.

---

## A. Security Baseline

- [x] `[all]` SECURITY.md exists (report email, supported versions, response timeline) (2026-09-09)
- [x] `[all]` README includes threat model paragraph (data touched, data NOT touched, permissions required) (2026-09-09) — 8 rows, each naming the mechanism that enforces it
- [x] `[all]` No secrets, tokens, or credentials in source or diagnostics output (2026-09-09) — no NPM_TOKEN anywhere; both registries publish via OIDC. `support-bundle` byte-checked: no seed, home path redacted
- [x] `[all]` No telemetry by default — state it explicitly even if obvious (2026-09-09) — README + SECURITY.md
- [x] `[all]` Operator identity scan clean (2026-09-09) — `identity-scan.py` → `RESULT CLEAN` on the git-tracked tree

### Default safety posture

- [x] `[cli|mcp|desktop]` Dangerous actions (kill, delete, restart) require explicit confirmation (2026-09-09) — `reset` requires typing `RESET`; `--yes` deliberately does not bypass it
- [x] `[cli|mcp|desktop]` File operations constrained to known directories (2026-09-09) — all state under `.xrpl-camp/`, path resolved and displayable via `status --detail`
- [x] `[cli]` Network destination is constrained and verified (2026-09-09) — endpoint `network_id` checked before signing; non-Testnet refused unless `XRPL_CAMP_ALLOW_ANY_NETWORK=1`
- [ ] `[mcp]` SKIP: not an MCP server
- [ ] `[mcp]` SKIP: not an MCP server

## B. Error Handling

- [x] `[all]` Errors follow the Structured Error Shape: `code`, `message`, `hint`, `cause?`, `retryable?` (2026-09-09) — `CampError`; all 12 transport exception classes carry one
- [x] `[cli]` Exit codes: 0 ok · 1 user error · 2 runtime error · 3 partial success (2026-09-09) — all four in use; 3 is `proof verify --online` when the ledger cannot confirm either way
- [x] `[cli]` No raw stack traces without `--verbose` (2026-09-09) — one `CampFailure` handler at the command boundary; 13/13 corrupt-state paths verified clean
- [x] `[cli]` Retry is bounded and never applied to an irreversible action (2026-09-09) — only the faucet and reads retry; payments never do
- [ ] `[mcp]` SKIP: not an MCP server
- [ ] `[mcp]` SKIP: not an MCP server
- [ ] `[desktop]` SKIP: not a desktop app
- [ ] `[vscode]` SKIP: not a VS Code extension

## C. Operator Docs

- [x] `[all]` README is current: what it does, install, usage, supported platforms + runtime versions (2026-09-09)
- [x] `[all]` CHANGELOG.md (Keep a Changelog format) (2026-09-09) — 1.4.0 states plainly what shipped to which registry and what did not
- [x] `[all]` LICENSE file present and repo states support status (2026-09-09)
- [x] `[cli]` `--help` output accurate for all commands and flags (2026-09-09) — command table in README generated from actual `--help`
- [x] `[cli|mcp|desktop]` Logging levels defined: silent / normal / verbose / debug — secrets redacted at all levels (2026-09-09) — `--verbose` gates technical detail; `support-bundle` redacts
- [ ] `[mcp]` SKIP: not an MCP server
- [ ] `[complex]` SKIP: simple CLI tool, not complex ops software

## D. Shipping Hygiene

- [x] `[all]` `verify` script exists (test + build + smoke in one command) (2026-09-09) — `scripts/verify.sh`; `ci.yml` calls it directly so the two cannot drift
- [x] `[all]` Version in manifest matches git tag (2026-09-09) — `scripts/check-versions.sh` gates `pyproject.toml` / `__init__.py` / `package.json` in CI; both publish workflows re-verify against the tag
- [x] `[all]` Dependency scanning runs in CI (ecosystem-appropriate) (2026-09-09) — `pip-audit`. The previous revision credited "ruff in CI", which is a linter and scans nothing
- [x] `[all]` Automated dependency update mechanism exists (2026-09-09) — weekly `freshness-check.yml` opens a PR on stale action pins and dependency ceilings. The previous revision credited "uv.lock, manual updates", which is both self-contradicting and cites a gitignored file
- [x] `[npm]` Package published from CI with no long-lived token (2026-09-09) — `release.yml`, OIDC trusted publishing, `--provenance`
- [x] `[npm]` `files` allowlist set and packed artifact inspected (2026-09-09) — `npm pack --dry-run`: 11 files, bin + README(s) + LICENSE + package.json
- [x] `[npm]` Registry serves what the tag claims, verified in CI (2026-09-09) — bounded post-publish poll in `release.yml`
- [x] `[pypi]` `python_requires` set (2026-09-09) — `>=3.11,<3.14`, matching the CI matrix and the classifiers
- [x] `[pypi]` Clean wheel + sdist build (2026-09-09) — hatchling, exercised by `verify.sh`
- [x] `[pypi]` Registry serves what the tag claims, verified in CI (2026-09-09) — `scripts/verify-pypi-publish.sh`, run after publish
- [x] `[container]` Image builds and runs, published from CI (2026-09-09) — `ghcr.io`, built and version-checked in `publish.yml`; local run verified end to end with a mounted volume
- [ ] `[vsix]` SKIP: not a VS Code extension
- [ ] `[desktop]` SKIP: not a desktop app

## E. Identity (soft gate — does not block ship)

- [x] `[all]` Logo in README header (2026-09-09)
- [x] `[all]` Translations (polyglot-mcp, 7 languages) (2026-09-09) — regenerated for 1.4.0 before the tag
- [x] `[org]` Landing page (@mcptoolshop/site-theme) (2026-09-09)
- [x] `[all]` GitHub repo metadata: description, homepage, topics (2026-09-09)

---

## Gate Rules

**Hard gate (A–D):** Must pass before any version is tagged or published.
If a section doesn't apply, mark `SKIP:` with justification — don't leave it unchecked.

**A SKIP is a claim, and claims go stale.** `[npm] SKIP: not an npm package` sat in
this file while `@mcptoolshop/xrpl-camp` had four published versions, so shipcheck
reported 100% while no npm packaging item had ever been checked. Re-read every SKIP
at every release and ask whether it is still true.

**Soft gate (E):** Should be done. Product ships without it, but isn't "whole."

**Checking off:**
```
- [x] `[all]` SECURITY.md exists (2026-02-27)
```

**Skipping:**
```
- [ ] `[pypi]` SKIP: not a Python project
```
