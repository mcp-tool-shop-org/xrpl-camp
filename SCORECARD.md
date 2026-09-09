# Scorecard

> Score a repo before remediation. Fill this out first, then use SHIP_GATE.md to fix.

**Repo:** xrpl-camp
**Date:** 2026-09-09 (dogfood swarm, v1.3.1 → v1.4.0)
**Type tags:** `[all]` `[pypi]` `[npm]` `[container]` `[cli]`

## About the previous scorecard

The prior revision was dated **2026-03-02** and reported **50/50 post-remediation**. It
predated v1.1.0 through v1.3.1 entirely, and it predated every defect this swarm
measured. Its scores are not corrected below — they are *replaced*, because they were
estimates of a product that no longer resembles the one that was shipping.

Worth stating plainly, because it is the lesson: at 50/50 this repo's last three
lessons could not execute, PyPI had been serving a version two minors old for five
months, and a workflow was pinned to an action commit that did not exist. A perfect
self-score that nobody re-measures is worse than no score, because it is cited as
evidence.

## Pre-Remediation Assessment (measured 2026-09-08, at commit da117b7)

| Category | Score | Notes |
|----------|-------|-------|
| A. Security | 5/10 | SECURITY.md claimed Testnet-only connectivity that `XRPL_CAMP_RPC_URL` overrode. Threat model credited two seed guards that were never called outside tests. Seed written world-readable on POSIX. |
| B. Error Handling | 3/10 | `CampError` existed and `cli.py` never imported it. Four raw-traceback paths. `fund`/`send`/`verify`/`start` all exited 0 on hard failure. Six errors declared `retryable` and nothing acted on it. |
| C. Operator Docs | 4/10 | README, landing page and handbook all documented lesson 4 as a "self-payment" — a transaction the ledger rejects. All 7 translations a full feature generation stale. Package summary on PyPI read "Learn the XRPL diary". |
| D. Shipping Hygiene | 2/10 | PyPI five months stale and nothing noticed. `publish.yml` pinned to a nonexistent action SHA. npm serving a version absent from git. Dependency scanning credited to a linter. |
| E. Identity (soft) | 6/10 | Logo, landing page and metadata present; translations stale. |
| **Overall** | **20/50** | |

## Key Gaps

1. The product's last three lessons could not run (A, B)
2. 139 passing tests could not detect that, because none imported `xrpl` (D)
3. Release automation had not published since 2026-03-19 and nothing went red (D)
4. Public surfaces asserted mitigations that did not exist (A, C)

## Post-Remediation (measured 2026-09-09, at v1.4.0)

| Category | Before | After | Evidence |
|----------|--------|-------|----------|
| A. Security | 5/10 | 10/10 | Endpoint verified before signing; seed guards wired fail-closed on xrpl-py's `decode_seed`; 0600/0700; memo scanned for secrets; identity scan `RESULT CLEAN` |
| B. Error Handling | 3/10 | 10/10 | All 12 transport exceptions carry a `CampError`; one handler at the command boundary; 13/13 corrupt-state paths clean; all four exit codes in use; retry bounded and never applied to a payment |
| C. Operator Docs | 4/10 | 10/10 | README/landing/handbook rewritten against measured behaviour; 7 translations regenerated before the tag; claims match mechanisms |
| D. Shipping Hygiene | 2/10 | 10/10 | Two tag-triggered publish workflows, each with a post-publish registry check; `check-versions.sh` in CI; `pip-audit`; weekly freshness PR; container published and version-verified |
| E. Identity (soft) | 6/10 | 10/10 | Logo, translations, landing page, handbook, metadata |
| **Overall** | **20/50** | **50/50** | |

A 50/50 here means the same thing the last one should have meant and didn't: every line
in SHIP_GATE.md was re-measured on the date it carries. The scores above are only worth
the freshness of those dates — re-measure them at the next release rather than quoting
this table.

## What the swarm cost and produced

| | |
|---|---|
| Waves | 6 (audit + amend × health A, health B/C, feature) |
| Findings | 166 audited, 150 fixed |
| Tests | 139 → 318 |
| Python versions tested | 2 → 3 |
| Registries with a publish verifier | 0 → 2 |
| Six-lesson flow | unreachable past lesson 3 → completes live in ~20s |
