#!/usr/bin/env bash
# Fails loudly if the three hand-maintained version copies in this repo
# disagree with each other:
#   - pyproject.toml            [project].version
#   - xrpl_camp/__init__.py     __version__
#   - npm/package.json          .version
#
# These are three separate sources of truth for one number, with no
# structural link between them -- exactly the gap that let the live npm
# registry drift to a version (1.3.2) that exists nowhere in git. This
# script is the CI-enforced compensator: it does not fix drift, it makes
# drift impossible to merge unnoticed.
#
# Usage: bash scripts/check-versions.sh

set -euo pipefail

cd "$(dirname "$0")/.."

PYPROJECT_VERSION=$(grep -m1 -E '^version = "[^"]+"' pyproject.toml | sed -E 's/version = "([^"]+)"/\1/')
INIT_VERSION=$(grep -m1 -E '__version__ = "[^"]+"' xrpl_camp/__init__.py | sed -E 's/__version__ = "([^"]+)"/\1/')
NPM_VERSION=$(node -p "require('./npm/package.json').version")

echo "pyproject.toml        [project].version = ${PYPROJECT_VERSION:-<missing>}"
echo "xrpl_camp/__init__.py __version__        = ${INIT_VERSION:-<missing>}"
echo "npm/package.json      .version           = ${NPM_VERSION:-<missing>}"

if [ -z "$PYPROJECT_VERSION" ] || [ -z "$INIT_VERSION" ] || [ -z "$NPM_VERSION" ]; then
  echo "::error::Could not parse one or more version strings -- see blank fields above."
  exit 1
fi

if [ "$PYPROJECT_VERSION" != "$INIT_VERSION" ] || [ "$PYPROJECT_VERSION" != "$NPM_VERSION" ]; then
  echo "::error::Version mismatch -- pyproject.toml=${PYPROJECT_VERSION} xrpl_camp/__init__.py=${INIT_VERSION} npm/package.json=${NPM_VERSION}. All three must move together on every release."
  exit 1
fi

echo "Versions agree: ${PYPROJECT_VERSION}"
