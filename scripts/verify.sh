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
uv run pytest tests/ -v

echo ""
echo "=== Build ==="
uv run --with build python -m build

echo ""
echo "=== Smoke ==="
uv run xrpl-camp --help

echo ""
echo "✓ All checks passed."
