#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Tests for .github/scripts/changelog_notes.py, which turns the CHANGELOG
section of a version into the body of its GitHub release.

Run:  uv run tests/test_changelog_notes.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".github" / "scripts" / "changelog_notes.py"
sys.path.insert(0, str(SCRIPT.parent))
from changelog_notes import section

CHANGELOG = """# Changelog

Preamble that is not part of any release.

## [Unreleased]

### Added
- Not shipped yet.

## [1.2.0] - 2026-10-13

### Fixed
- **A fix.** With a [link](https://example.com).

### Changed
- A change.

## [1.1.0] — 2026-09-01

### Added
- The previous release.

[1.2.0]: https://example.com/compare/v1.1.0...v1.2.0
"""


class TestSection(unittest.TestCase):
    def test_extracts_only_the_requested_version(self):
        notes = section(CHANGELOG, "1.2.0")
        self.assertTrue(notes.startswith("### Fixed\n"))
        self.assertIn("- A change.", notes)
        self.assertNotIn("previous release", notes)
        self.assertNotIn("Not shipped yet", notes)
        self.assertNotIn("## [", notes)

    def test_last_section_stops_at_link_references(self):
        notes = section(CHANGELOG, "1.1.0")
        self.assertEqual(notes, "### Added\n- The previous release.")

    def test_em_dash_heading_separator_is_accepted(self):
        self.assertIn("previous release", section(CHANGELOG, "1.1.0"))

    def test_version_is_matched_literally(self):
        # `1.2.0` must not match `1x2y0`, nor `1.2.0` match a `1.2.01` heading.
        self.assertIsNone(section("## [1x2y0]\nbody\n", "1.2.0"))
        self.assertIsNone(section("## [1.2.01]\nbody\n", "1.2.0"))

    def test_missing_or_empty_section_is_none(self):
        self.assertIsNone(section(CHANGELOG, "9.9.9"))
        self.assertIsNone(section("## [2.0.0]\n\n## [1.0.0]\nx\n", "2.0.0"))


class TestCli(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(SCRIPT), *args],
                              capture_output=True, text=True, check=False)

    def test_prints_the_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "CHANGELOG.md")
            path.write_text(CHANGELOG, encoding="utf-8")
            r = self.run_cli("1.2.0", str(path))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, section(CHANGELOG, "1.2.0") + "\n")

    def test_fails_when_the_version_has_no_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "CHANGELOG.md")
            path.write_text(CHANGELOG, encoding="utf-8")
            r = self.run_cli("9.9.9", str(path))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("9.9.9", r.stderr)

    def test_current_release_has_notes(self):
        # The release workflow runs this on every version bump; the repo's own
        # CHANGELOG must always yield notes for the version in plugin.json.
        version = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())["version"]
        r = self.run_cli(version, str(ROOT / "CHANGELOG.md"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(r.stdout.strip())


if __name__ == "__main__":
    unittest.main(verbosity=2)
