#!/usr/bin/env bash
# Verify script — lint + test + build + smoke in one command.
# Usage: bash scripts/verify.sh
#
# This is the single source of truth for what "verified" means for this
# repo. ci.yml's lint-and-test job calls this script directly instead of
# re-typing the same commands, so CI and this script can never silently
# drift apart (previously they held two independently hand-maintained
# copies of the same lint+test invocation, and this script itself only
# did lint+test despite SHIP_GATE.md crediting it with build+smoke too).
#
# Requires Git Bash (or another POSIX shell) on Windows. There is no
# PowerShell equivalent of this script today; `set -euo pipefail` and the
# shebang below are bash-specific. Git Bash ships alongside Git for
# Windows, which this studio's tooling already assumes is installed.

set -euo pipefail

echo "=== Lint ==="
uv run ruff check .

echo ""
echo "=== Tests ==="
pytest_args=(tests/ -v)
# ci.yml sets COVERAGE_LEG to 'true' on the one cell whose reports go to
# Codecov. There the suite also measures xrpl_camp's coverage and writes JUnit
# results, both at the root, for the workflow to hand on. Coverage is reported,
# never held: no --cov-fail-under.
if [ "${COVERAGE_LEG:-}" = "true" ]; then
  pytest_args+=(--cov=xrpl_camp --cov-report=term --cov-report=xml:coverage.xml --junitxml=junit.xml)
fi
uv run pytest "${pytest_args[@]}"

echo ""
echo "=== Build ==="
uv run --with build python -m build

echo ""
echo "=== Smoke ==="
uv run xrpl-camp --help

echo ""
echo "✓ All checks passed."
