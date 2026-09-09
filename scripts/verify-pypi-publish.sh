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
# Once the version matches, it also checks that BOTH expected artifacts
# (sdist + wheel, from this job's own `python -m build`) actually landed --
# pypa/gh-action-pypi-publish uploads files from dist/ sequentially, not as
# one atomic transaction, and PyPI creates the release record on the FIRST
# successful file. A partial upload (sdist ships, wheel doesn't, or vice
# versa) would otherwise report OK on version match alone.
#
# Usage: bash scripts/verify-pypi-publish.sh <expected-version>
#
# Bounded retry: PyPI's index can take a short moment to become consistent
# after a successful upload, so this polls rather than checking once, with
# a hard cap on both attempts and per-request time so a stuck network call
# cannot hang the job indefinitely.
#
# Requires: curl, jq -- both ship on ubuntu-latest's default runner image
# (where this script normally runs), but this is also meant to be run by
# hand during manual release recovery (see e.g. the v1.0.6 incident), on
# whatever machine happens to be at hand. Checked explicitly below so a
# missing local tool is never misreported as a PyPI/network failure -- that
# exact misreport was reproduced empirically against this script before this
# check existed: no jq on PATH made a perfectly healthy PyPI look like an
# outage for the full retry budget.

set -euo pipefail

for tool in curl jq; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "::error::verify-pypi-publish.sh requires '${tool}', which is not on PATH. This is a missing local tool, not a PyPI or network problem -- install ${tool} and re-run." >&2
    exit 2
  fi
done

EXPECTED_VERSION="${1:?Usage: verify-pypi-publish.sh <expected-version>}"
PACKAGE="xrpl-camp"
MAX_ATTEMPTS=10
SLEEP_SECONDS=15
CURL_TIMEOUT=10
EXPECTED_ARTIFACT_COUNT=2 # sdist + wheel, per this job's `python -m build`

echo "Verifying PyPI serves ${PACKAGE}==${EXPECTED_VERSION}..."

live_version=""
attempt=1
while [ "$attempt" -le "$MAX_ATTEMPTS" ]; do
  live_version=$(curl -fsS --max-time "$CURL_TIMEOUT" "https://pypi.org/pypi/${PACKAGE}/json" 2>/dev/null \
    | jq -r '.info.version // empty' 2>/dev/null || true)

  if [ "$live_version" = "$EXPECTED_VERSION" ]; then
    echo "Version match: PyPI serves ${PACKAGE}==${live_version}, matches tag v${EXPECTED_VERSION}. Checking artifact completeness..."

    artifact_count=$(curl -fsS --max-time "$CURL_TIMEOUT" "https://pypi.org/pypi/${PACKAGE}/${EXPECTED_VERSION}/json" 2>/dev/null \
      | jq -r '.urls | length' 2>/dev/null || true)
    case "$artifact_count" in
      '' | *[!0-9]*) artifact_count=0 ;;
    esac

    if [ "$artifact_count" -ge "$EXPECTED_ARTIFACT_COUNT" ]; then
      echo "OK: PyPI serves ${PACKAGE}==${live_version} with ${artifact_count} artifact(s) (expected >= ${EXPECTED_ARTIFACT_COUNT}: sdist + wheel)."
      exit 0
    fi

    echo "::error::PyPI reports ${PACKAGE}==${EXPECTED_VERSION} live, but only ${artifact_count}/${EXPECTED_ARTIFACT_COUNT} artifact(s) are present under https://pypi.org/pypi/${PACKAGE}/${EXPECTED_VERSION}/json -- a partial upload (e.g. the sdist shipped but the wheel didn't, or vice versa). pip/pipx can often still install from a lone sdist, but treat this release as INCOMPLETE and investigate. skip-existing is enabled on the publish step, so re-running it is safe and will only upload the missing file(s)."
    exit 1
  fi

  echo "Attempt ${attempt}/${MAX_ATTEMPTS}: PyPI serves '${live_version:-<unreachable>}', tag claims '${EXPECTED_VERSION}'. Retrying in ${SLEEP_SECONDS}s..."
  attempt=$((attempt + 1))
  [ "$attempt" -le "$MAX_ATTEMPTS" ] && sleep "$SLEEP_SECONDS"
done

echo "::error::PyPI publish verification FAILED after ${MAX_ATTEMPTS} attempts over ~$((MAX_ATTEMPTS * SLEEP_SECONDS))s: tag claims version '${EXPECTED_VERSION}' but PyPI serves '${live_version:-<unreachable>}'. The publish step exited 0 but the registry does not reflect the release. Treat this release as NOT shipped to PyPI and investigate (Trusted Publishing config, PyPI status, build contents) before retrying."
exit 1
