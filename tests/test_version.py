"""Version consistency across every surface that ships a number.

The suite this replaces checked pyproject.toml against itself: all three tests
sourced the version from `get_pyproject_version()` and then asserted it was
semver, had major >= 1, and appeared somewhere in CHANGELOG.md. Four surfaces
are hand-synchronised in this repo and exactly one was read.

The production consequence was real and measured: repo at 1.3.1, the live npm
registry serving 1.3.2 — a version that exists nowhere in git — and PyPI
serving 1.1.0. A learner who ran `npx @mcptoolshop/xrpl-camp` and a learner who
ran `pipx install xrpl-camp` were not running the same product.

`scripts/check-versions.sh` enforces three of these in CI. This file exists
alongside it rather than instead of it: it runs on Windows, where developers do
not necessarily have bash, and it adds the two surfaces the script does not
cover (the installed distribution's metadata, and the CHANGELOG's TOP entry).
"""

from __future__ import annotations

import json
import re
from importlib.metadata import version as dist_version
from pathlib import Path

import pytest

import xrpl_camp

ROOT = Path(__file__).parent.parent
CHANGELOG = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


def pyproject_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert match, "version not found in pyproject.toml"
    return match.group(1)


def init_version() -> str:
    text = (ROOT / "xrpl_camp" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert match, "__version__ not found in xrpl_camp/__init__.py"
    return match.group(1)


def npm_version() -> str:
    return json.loads(
        (ROOT / "npm" / "package.json").read_text(encoding="utf-8"),
    )["version"]


ALL_SURFACES = {
    "pyproject.toml [project].version": pyproject_version,
    "xrpl_camp/__init__.py __version__": init_version,
    "npm/package.json .version": npm_version,
    "xrpl_camp.__version__ (imported)": lambda: xrpl_camp.__version__,
}


# ---------------------------------------------------------------------------
# Every surface agrees
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("label", sorted(ALL_SURFACES))
def test_every_surface_reports_the_same_version(label):
    """Bump one, forget another, and this goes red — which is the whole point."""
    assert ALL_SURFACES[label]() == pyproject_version(), (
        f"{label} disagrees with pyproject.toml. All surfaces must move "
        f"together on every release."
    )


def test_the_installed_distribution_matches_the_source_tree():
    """Catches a stale editable install serving a version the source does not."""
    assert dist_version("xrpl-camp") == pyproject_version()


@pytest.mark.parametrize("label", sorted(ALL_SURFACES))
def test_every_surface_is_semver(label):
    value = ALL_SURFACES[label]()
    assert SEMVER.match(value), f"{label} is not semver: {value!r}"


def test_version_is_at_least_1_0_0():
    assert int(pyproject_version().split(".")[0]) >= 1


# ---------------------------------------------------------------------------
# The npm launcher must not reintroduce a hardcoded copy
# ---------------------------------------------------------------------------


def test_the_npm_launcher_derives_its_version_rather_than_duplicating_it():
    """`npm/bin/xrpl-camp.js` used to carry a fourth hand-synced literal.

    It picked the GitHub release asset to download, so a stale one pointed
    users at a build that did not match the package they installed. It now
    reads `require("../package.json").version`; a literal reappearing here is
    the regression.
    """
    js = (ROOT / "npm" / "bin" / "xrpl-camp.js").read_text(encoding="utf-8")

    assert 'require("../package.json")' in js or "require('../package.json')" in js
    code = "\n".join(
        line for line in js.splitlines() if not line.strip().startswith("//")
    )
    hardcoded = re.findall(r'\b(?:version|tag)\s*:\s*["\']([^"\']+)["\']', code)
    assert hardcoded == [], (
        f"npm/bin/xrpl-camp.js hardcodes {hardcoded}; it must derive both the "
        f"version and the release tag from package.json"
    )


# ---------------------------------------------------------------------------
# The CHANGELOG's TOP entry, not merely a mention
# ---------------------------------------------------------------------------


def _changelog_versions() -> list[str]:
    return re.findall(r"^##\s*\[?v?([0-9][^\]\s]*)\]?", CHANGELOG, re.MULTILINE)


def test_the_changelog_top_entry_is_the_current_version():
    """"Appears somewhere in CHANGELOG.md" passes for every past release."""
    entries = _changelog_versions()
    assert entries, "no version headings found in CHANGELOG.md"
    assert entries[0] == pyproject_version(), (
        f"CHANGELOG's newest entry is {entries[0]}, but the package is "
        f"{pyproject_version()}"
    )


def test_the_changelog_has_no_duplicate_entries():
    entries = _changelog_versions()
    assert len(entries) == len(set(entries)), (
        f"duplicate CHANGELOG entries: "
        f"{sorted({v for v in entries if entries.count(v) > 1})}"
    )
