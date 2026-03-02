#!/usr/bin/env bash
# Verify script — lint + test in one command.
# Usage: bash scripts/verify.sh

set -euo pipefail

echo "=== Lint ==="
uv run ruff check .

echo ""
echo "=== Tests ==="
uv run pytest tests/ -v

echo ""
echo "✓ All checks passed."
