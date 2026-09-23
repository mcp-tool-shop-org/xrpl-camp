# xrpl-camp: how it works

Mapped at 2026-09-23 from commit d3e4b7d.

## What this is

7 parts, mostly Python (31 files). Work enters through 7 doors; the busiest is Freshness Check, which reaches 1 part and commits into the repository (CI reaches 5 but commits nothing). It publishes to npm and PyPI, and a container image. People run xrpl-camp.

## What changed since the last map

This is the first map.

## What comes in

1. **CI.** On a pull request touching 10 paths; on a push touching 10 paths; or by hand. Runs bin/xrpl-camp.js, scripts/check-versions.sh, scripts/verify.sh and 1 more; checks xrpl_camp/.
2. **Deploy site to GitHub Pages.** On a push to main touching 2 paths; or by hand. Runs site/astro.config.mjs and site/src/.
3. **Publish.** When a tag matching `v*` is pushed; or by hand. Runs scripts/verify-pypi-publish.sh.
4. **Release (npm).** When a tag matching `v*` is pushed; or by hand. Runs scripts/check-versions.sh.
5. **Freshness Check.** On a schedule (`0 8 * * 1`), Monday at 08:00 UTC; or by hand. Runs scripts/check-freshness.sh.
6. **xrpl-camp** (a command people run, from package.json). Runs bin/xrpl-camp.js.
7. **xrpl-camp** (a command people run, from pyproject.toml). Runs xrpl_camp/cli.py.

## What happens through Freshness Check

1. The workflow runs scripts/check-freshness.sh in scripts.
2. It writes to .github/freshness-report.md.
3. It commits .github/freshness-report.md and pushes.
4. It opens a pull request.

## Who reads the results

Only Freshness Check itself reads what it writes.

## The other doors

**CI** runs bin/xrpl-camp.js, scripts/check-versions.sh, scripts/verify.sh and 1 more, checks xrpl_camp/, and reaches the repository root.

**Deploy site to GitHub Pages** runs site/astro.config.mjs and site/src/, and deploys the site.

**Publish** runs scripts/verify-pypi-publish.sh, publishes to PyPI and a container image on a tag push, and creates a GitHub release on a tag push.

**Release (npm)** runs scripts/check-versions.sh and publishes to npm.

**xrpl-camp** (a command people run, from package.json) runs bin/xrpl-camp.js and reaches the repository root.

**xrpl-camp** (a command people run, from pyproject.toml) runs xrpl_camp/cli.py.

## What breaks what

- **the repository root** is imported by 1 part (bin) and sits on the path of 2 doors.
- **scripts** is imported by no other part and sits on the path of 4 doors.
- **xrpl_camp** is imported only from tests, by 1 part (tests), and sits on the path of 2 doors.
- **bin** is imported by no other part and sits on the path of 2 doors.

## What tends to change together

- **xrpl_camp/cli.py** and **xrpl_camp/lessons.py** changed together in 6 of 9 commits, inside the xrpl_camp part.
- **xrpl_camp/__init__.py** and **xrpl_camp/lessons.py** changed together in 5 of 10 commits, inside the xrpl_camp part.
- **xrpl_camp/lessons.py** and **xrpl_camp/models.py** changed together in 4 of 8 commits, inside the xrpl_camp part.

Confidence is low: fewer than 30 qualifying commits in the window, and fewer than 20 source files reach 10 revisions.

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

People write the repository root, scripts/ and site/; 4 writes with paths built at run time may land here.

## Where to start

.github/workflows/ci.yml → tests/__init__.py

Read those in order to follow one pull request end to end.

## What this map cannot see

- 1 import site could not be resolved.
- 4 writes and 11 reads use paths built at run time and are not named here.
- Statistics confidence is low: fewer than 30 qualifying commits in the window, and fewer than 20 source files reach 10 revisions.

Regenerate with `npx --yes @dogfood-lab/atlas map`.
