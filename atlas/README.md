# xrpl-camp: how it works

Mapped at 2026-10-23 from commit 208cbc6 by Atlas 1.24.0.

## What this is

7 parts, mostly Python (36 files), shell (11), CSS (2), JavaScript (2), TypeScript (2) and Astro (1). Work enters through 7 doors; the busiest is CI, which reaches 4 parts. It publishes to npm and PyPI, and a container image. It deploys a site to GitHub Pages. People run xrpl-camp.

## What changed since 2026-10-23 (b74ffff)

- tests now imports scripts.
- CI now also checks scripts/.
- Publish now also runs scripts/check_bundle.py.
- scripts/check_bundle.py is now read by tests/test_check_bundle.py.
- 2 files added and 5 changed content, across 5 parts.

## What comes in

1. **CI.** On a pull request; on a push touching 12 paths; or by hand. Runs scripts/check-versions.sh and scripts/verify.sh; checks bin/xrpl-camp.js, xrpl_camp/, scripts/ and 25 more.
2. **Publish.** When a tag matching `v*` is pushed; or by hand. On a tag push, it runs docker-entrypoint.sh, scripts/check_bundle.py, scripts/verify-pypi-publish.sh and 1 more; builds xrpl_camp/__main__.py; checks xrpl_camp/; packs LICENSE, README.md and pyproject.toml into an image.
3. **Deploy site to GitHub Pages.** On a push to main touching 2 paths; or by hand. Runs site/astro.config.mjs and site/src/.
4. **Release (npm).** When a tag matching `v*` is pushed; or by hand. Runs scripts/check-versions.sh.
5. **Freshness Check.** On a schedule (`0 8 * * 1`), Monday at 08:00 UTC; or by hand. Runs scripts/check-freshness.sh.
6. **xrpl-camp** (a command people run, from package.json). Runs bin/xrpl-camp.js.
7. **xrpl-camp** (a command people run, from pyproject.toml). Runs xrpl_camp/cli.py.

## What happens through CI

1. The workflow runs scripts/check-versions.sh and scripts/verify.sh in scripts; it checks bin/xrpl-camp.js in bin, scripts/ in scripts, tests/ in tests and xrpl_camp/ in xrpl_camp.
2. It uploads coverage to Codecov.

## Who reads the results

CI writes nothing this map can see.

## The other doors

**Publish** runs docker-entrypoint.sh, scripts/check_bundle.py, scripts/verify-pypi-publish.sh and 1 more and checks xrpl_camp/ and packs LICENSE, README.md and pyproject.toml into an image on a tag push, and publishes to PyPI and a container image, creates a GitHub release, and builds xrpl_camp/__main__.py into binaries for darwin-arm64, linux-x64 and win-x64 and uploads them to the release, on a tag push.

**Deploy site to GitHub Pages** runs site/astro.config.mjs and site/src/, and deploys the site.

**Release (npm)** runs scripts/check-versions.sh and publishes to npm.

**Freshness Check** runs scripts/check-freshness.sh, writes to .github/freshness-report.md, commits .github/freshness-report.md and pushes to a branch for review, never to main, and opens an issue.

**xrpl-camp** (a command people run, from package.json) runs bin/xrpl-camp.js.

**xrpl-camp** (a command people run, from pyproject.toml) runs xrpl_camp/cli.py.

## What breaks what

- **scripts** is imported only from tests, by 1 part (tests), and sits on the path of 4 doors.
- **xrpl_camp** is imported only from tests, by 1 part (tests), and sits on the path of 3 doors.
- **bin** is imported by no other part and sits on the path of 2 doors.

## What tends to change together

No two source files changed together often enough to name.

Window: 180 days; a pair counts from 3 shared commits, since the window holds fewer than 30 qualifying commits.

## What no test touches

- **bin** is imported by no test.

## Written but never read

- **.github/freshness-report.md** is written by .github/workflows/freshness-check.yml and read by nothing else in this repository.

## Helpers that look duplicated

No two parts export a helper that looks alike.

## Generated, never hand-edited

- **.github/freshness-report.md** is written by .github/workflows/freshness-check.yml.

## Hand-authored

People write the repository root, scripts/ and site/. Nothing in this repository writes to them.

## Where to start

xrpl_camp/cli.py → xrpl_camp/errors.py

Read those in order to follow one run of xrpl-camp end to end. This path follows xrpl-camp (a command people run, from pyproject.toml) from its entry, since CI only checks code.

## What this map cannot see

- 1 import could not be resolved: `xrpl_camp/cli.py` imports a path built at run time.
- 6 reads use paths built at run time and are not named here.
- 4 writes and 10 reads go to a path their caller passes, not to this repository.
- 1 write goes to a temporary directory, not to this repository.
- 637 files belong to no part: docs/receipts/1.4.1-live-check/README.md, docs/receipts/1.4.1-live-check/account_checks.txt, docs/receipts/1.4.1-live-check/channels/npm-dryrun.cmd and 634 more.
- Statistics confidence is low: fewer than 30 qualifying commits in the window, and fewer than 25 source files reach 10 revisions.

Regenerate with `npx --yes @dogfood-lab/atlas map`.
