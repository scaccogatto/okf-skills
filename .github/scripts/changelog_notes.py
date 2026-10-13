#!/usr/bin/env python3
"""Print the CHANGELOG.md section of one version, for use as release notes.

CI requires a `## [<version>]` entry for every version bump, and that prose is
the release's only description. release.yml feeds this script's output to
`gh release create --notes-file`, so the entry reaches the release page.

Usage:  changelog_notes.py <version> [CHANGELOG.md]
Exits non-zero when the version has no section or the section is empty.

Standard library only: it runs on the bare Actions runner, before any setup.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# The next release heading, or the Keep a Changelog link references at the end.
_SECTION_END = re.compile(r"^(?:## |\[[^\]]+\]:\s)", re.MULTILINE)


def section(changelog: str, version: str) -> str | None:
    """The body of `## [version]` (heading excluded), stripped, or None."""
    heading = re.compile(rf"^## \[{re.escape(version)}\][^\n]*\n", re.MULTILINE)
    start = heading.search(changelog)
    if start is None:
        return None
    rest = changelog[start.end():]
    end = _SECTION_END.search(rest)
    body = (rest[:end.start()] if end else rest).strip()
    return body or None


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3):
        print(__doc__, file=sys.stderr)
        return 2
    version = argv[1]
    path = Path(argv[2] if len(argv) == 3 else "CHANGELOG.md")
    notes = section(path.read_text(encoding="utf-8"), version)
    if notes is None:
        print(f"error: {path} has no non-empty '## [{version}]' section", file=sys.stderr)
        return 1
    print(notes)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
