#!/usr/bin/env bash
# Post-publish compensator for the PyPI publish step in publish.yml.
#
# A publish step can exit 0 while PyPI does not actually end up serving the
# new version -- silent registry-side rejection, a Trusted Publishing
# misconfiguration that no-ops instead of erroring, a step that "succeeds"
# against a build that never actually uploaded. Nothing before this script
# checked reality. This script polls the live registry and fails the job
# loudly, naming both versions, if what shipped does not match what the tag
# claims. A publish that silently no-ops must never again look like success.
#
# Usage: bash scripts/verify-pypi-publish.sh <expected-version>
#
# Bounded retry: PyPI's index can take a short moment to become consistent
# after a successful upload, so this polls rather than checking once, with
# a hard cap on both attempts and per-request time so a stuck network call
# cannot hang the job indefinitely.

set -euo pipefail

EXPECTED_VERSION="${1:?Usage: verify-pypi-publish.sh <expected-version>}"
PACKAGE="xrpl-camp"
MAX_ATTEMPTS=10
SLEEP_SECONDS=15
CURL_TIMEOUT=10

echo "Verifying PyPI serves ${PACKAGE}==${EXPECTED_VERSION}..."

live_version=""
attempt=1
while [ "$attempt" -le "$MAX_ATTEMPTS" ]; do
  live_version=$(curl -fsS --max-time "$CURL_TIMEOUT" "https://pypi.org/pypi/${PACKAGE}/json" 2>/dev/null \
    | jq -r '.info.version // empty' 2>/dev/null || true)

  if [ "$live_version" = "$EXPECTED_VERSION" ]; then
    echo "OK: PyPI serves ${PACKAGE}==${live_version}, matches tag v${EXPECTED_VERSION}."
    exit 0
  fi

  echo "Attempt ${attempt}/${MAX_ATTEMPTS}: PyPI serves '${live_version:-<unreachable>}', tag claims '${EXPECTED_VERSION}'. Retrying in ${SLEEP_SECONDS}s..."
  attempt=$((attempt + 1))
  [ "$attempt" -le "$MAX_ATTEMPTS" ] && sleep "$SLEEP_SECONDS"
done

echo "::error::PyPI publish verification FAILED after ${MAX_ATTEMPTS} attempts over ~$((MAX_ATTEMPTS * SLEEP_SECONDS))s: tag claims version '${EXPECTED_VERSION}' but PyPI serves '${live_version:-<unreachable>}'. The publish step exited 0 but the registry does not reflect the release. Treat this release as NOT shipped to PyPI and investigate (Trusted Publishing config, PyPI status, build contents) before retrying."
exit 1
