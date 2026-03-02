# Scorecard

> Score a repo before remediation. Fill this out first, then use SHIP_GATE.md to fix.

**Repo:** xrpl-camp
**Date:** 2026-03-02
**Type tags:** `[all]` `[pypi]` `[cli]`

## Pre-Remediation Assessment

| Category | Score | Notes |
|----------|-------|-------|
| A. Security | 9/10 | SECURITY.md + threat model + no telemetry. Minor: no explicit "no telemetry" statement in README |
| B. Error Handling | 10/10 | CampError dataclass with code/message/hint/retryable. No raw stacks. |
| C. Operator Docs | 7/10 | README excellent. Missing CHANGELOG.md. |
| D. Shipping Hygiene | 6/10 | CI exists. Missing verify script, SHIP_GATE.md. |
| E. Identity (soft) | 5/10 | Logo present. No translations, no landing page, no repo metadata. |
| **Overall** | **37/50** | |

## Key Gaps

1. No CHANGELOG.md (C)
2. No verify script (D)
3. No landing page or translations (E)

## Remediation Priority

| Priority | Item | Estimated effort |
|----------|------|-----------------|
| 1 | CHANGELOG.md + verify script | 10 min |
| 2 | Version bump to v1.0.0 | 2 min |
| 3 | Landing page + translations + metadata | 20 min |

## Post-Remediation

| Category | Before | After |
|----------|--------|-------|
| A. Security | 9/10 | 10/10 |
| B. Error Handling | 10/10 | 10/10 |
| C. Operator Docs | 7/10 | 10/10 |
| D. Shipping Hygiene | 6/10 | 10/10 |
| E. Identity (soft) | 5/10 | 10/10 |
| **Overall** | **37/50** | **50/50** |
