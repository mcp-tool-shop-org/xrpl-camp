"""Version consistency tests for xrpl-camp."""

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
CHANGELOG = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")


def get_pyproject_version() -> str:
    """Read version from pyproject.toml."""
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert match, "version not found in pyproject.toml"
    return match.group(1)


class TestVersionConsistency:
    def test_version_is_semver(self):
        version = get_pyproject_version()
        assert re.match(r"^\d+\.\d+\.\d+", version), f"Not semver: {version}"

    def test_version_gte_1(self):
        version = get_pyproject_version()
        major = int(version.split(".")[0])
        assert major >= 1, f"Expected major >= 1, got {major}"

    def test_changelog_mentions_version(self):
        version = get_pyproject_version()
        assert version in CHANGELOG, f"CHANGELOG missing {version}"
