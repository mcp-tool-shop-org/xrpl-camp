#!/usr/bin/env bash
# Weekly freshness detector for two things a push trigger cannot see, because
# nothing in THIS repo changes when they happen upstream:
#
#   1. SHA-pinned GitHub Actions (.github/workflows/*.yml) that now have a
#      newer tagged release than the version comment next to their pin.
#   2. PyPI dependency ceilings in pyproject.toml (e.g. "xrpl-py>=5.0,<6.0")
#      where the ceiling now excludes a major that has actually shipped.
#
# Read-only: this script never edits a workflow file or pyproject.toml. It
# writes a Markdown report (--out FILE, default stdout) and, when
# GITHUB_OUTPUT is set, a `drift=true|false` output for the calling workflow
# (.github/workflows/freshness-check.yml) to act on. Deciding what to do
# with drift -- open a PR, do nothing -- is the workflow's job, not this
# script's; keeping detection and action separate means this script is safe
# to run by hand at any time for a manual re-pin pass (ad hoc, no side
# effects) as well as on a schedule.
#
# Usage: bash scripts/check-freshness.sh [--out FILE]
# Requires: gh (authenticated), curl, jq -- checked explicitly below so a
# missing local tool is never misreported as "everything is fresh" (empty
# output reading as "no drift" would be exactly the silent-failure class
# this whole audit wave exists to close).

set -euo pipefail

for tool in gh curl jq; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "::error::check-freshness.sh requires '${tool}', which is not on PATH. This is a missing local tool, not a signal that nothing has drifted -- install ${tool} and re-run." >&2
    exit 2
  fi
done

cd "$(dirname "$0")/.."

OUT_FILE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --out) OUT_FILE="${2:?--out requires a file path}"; shift 2 ;;
    *) echo "::error::Unknown argument: $1" >&2; exit 2 ;;
  esac
done

REPORT=$(mktemp)
trap 'rm -f "$REPORT"' EXIT

drift=false

{
  echo "# Freshness check report"
  echo
  echo "Generated $(date -u +%Y-%m-%dT%H:%M:%SZ) by scripts/check-freshness.sh."
  echo "Read-only detector -- nothing here was auto-applied. See each row's own note."
  echo
  echo "## Pinned GitHub Actions"
  echo
} >>"$REPORT"

# --- 1. SHA-pinned GitHub Actions -------------------------------------------

pin_matches=$(grep -ohE 'uses: [A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40} # v[^ ]+' \
  .github/workflows/*.yml | sort -u || true)

if [ -z "$pin_matches" ]; then
  echo "(no SHA-pinned \`uses:\` lines found under .github/workflows/)" >>"$REPORT"
else
  echo "| Action | Pinned | Pinned SHA | Latest | Status |" >>"$REPORT"
  echo "|---|---|---|---|---|" >>"$REPORT"

  while IFS= read -r line; do
    [ -z "$line" ] && continue
    repo_ref=$(echo "$line" | sed -E 's/^uses: ([A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+)@.*/\1/')
    pinned_sha=$(echo "$line" | sed -E 's/^uses: [^@]+@([0-9a-f]{40}).*/\1/')
    pinned_ver=$(echo "$line" | sed -E 's/^.*# (v[^ ]+)$/\1/')

    latest_tag=$(gh api "repos/${repo_ref}/releases/latest" --jq '.tag_name' 2>/dev/null || true)
    if [ -z "$latest_tag" ]; then
      # Some actions tag without cutting a GitHub Release object.
      latest_tag=$(gh api "repos/${repo_ref}/tags" --jq '.[0].name' 2>/dev/null || true)
    fi

    if [ -z "$latest_tag" ]; then
      echo "| ${repo_ref} | ${pinned_ver} | \`${pinned_sha:0:12}\` | ? | could not resolve latest tag via \`gh api\` -- check manually |" >>"$REPORT"
      continue
    fi

    latest_sha=$(gh api "repos/${repo_ref}/commits/${latest_tag}" --jq '.sha' 2>/dev/null || true)

    if [ -z "$latest_sha" ]; then
      echo "| ${repo_ref} | ${pinned_ver} | \`${pinned_sha:0:12}\` | ${latest_tag} | could not resolve tag to a commit SHA -- check manually |" >>"$REPORT"
      continue
    fi

    pinned_sha_lc=$(echo "$pinned_sha" | tr 'A-Z' 'a-z')
    latest_sha_lc=$(echo "$latest_sha" | tr 'A-Z' 'a-z')

    if [ "$pinned_sha_lc" = "$latest_sha_lc" ]; then
      echo "| ${repo_ref} | ${pinned_ver} | \`${pinned_sha:0:12}\` | ${latest_tag} | up to date |" >>"$REPORT"
    else
      echo "| ${repo_ref} | ${pinned_ver} | \`${pinned_sha:0:12}\` | ${latest_tag} (\`${latest_sha:0:12}\`) | **drift** -- review before bumping (a major version bump can change an action's inputs) |" >>"$REPORT"
      drift=true
    fi
  done <<EOF
$pin_matches
EOF
fi

{
  echo
  echo "## pyproject.toml dependency ceilings"
  echo
} >>"$REPORT"

# --- 2. PyPI dependency ceilings --------------------------------------------

# Matches lines shaped like: "xrpl-py>=5.0,<6.0", inside the `dependencies`
# array. Deliberately narrow (this array's own style, not a general TOML/PEP
# 508 parser) -- see pyproject.toml's own comment on why these ceilings
# exist before changing this pattern.
ceiling_matches=$(grep -oE '"[A-Za-z0-9_.-]+>=[0-9.]+,<[0-9.]+"' pyproject.toml || true)

if [ -z "$ceiling_matches" ]; then
  echo "(no \"pkg>=X,<Y\" dependency ceilings found in pyproject.toml)" >>"$REPORT"
else
  echo "| Package | Ceiling | Latest on PyPI | Status |" >>"$REPORT"
  echo "|---|---|---|---|" >>"$REPORT"

  while IFS= read -r dep; do
    [ -z "$dep" ] && continue
    pkg=$(echo "$dep" | sed -E 's/^"([A-Za-z0-9_.-]+)>=.*/\1/')
    ceiling=$(echo "$dep" | sed -E 's/^.*,<([0-9.]+)"$/\1/')
    ceiling_major=${ceiling%%.*}

    latest=$(curl -fsS --max-time 10 "https://pypi.org/pypi/${pkg}/json" 2>/dev/null \
      | jq -r '.info.version // empty' 2>/dev/null || true)

    if [ -z "$latest" ]; then
      echo "| ${pkg} | <${ceiling} | ? | could not reach PyPI JSON API -- check manually |" >>"$REPORT"
      continue
    fi

    latest_major=${latest%%.*}

    if [ "$latest_major" -ge "$ceiling_major" ] 2>/dev/null; then
      echo "| ${pkg} | <${ceiling} | ${latest} | **new major available** -- ceiling deliberately excludes it until a human tests it (see pyproject.toml's own comment on why); this is a notify-only signal, not a suggestion to widen the ceiling automatically |" >>"$REPORT"
      drift=true
    else
      echo "| ${pkg} | <${ceiling} | ${latest} | within ceiling |" >>"$REPORT"
    fi
  done <<EOF
$ceiling_matches
EOF
fi

if [ -n "$OUT_FILE" ]; then
  cp "$REPORT" "$OUT_FILE"
else
  cat "$REPORT"
fi

echo "drift=${drift}"
if [ -n "${GITHUB_OUTPUT:-}" ]; then
  echo "drift=${drift}" >>"$GITHUB_OUTPUT"
fi

exit 0
