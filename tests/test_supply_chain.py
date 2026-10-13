#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6,<7"]
# ///
"""Supply-chain guards for what the plugin pulls in at run time.

- Every third-party <script> the visualizer emits, and every one in the
  committed GitHub Pages demos, is pinned to an exact version and carries
  Subresource Integrity, so a compromised CDN file or a new upstream release
  cannot run in a generated page.
- Every dependency of a shipped PEP 723 script has an upper bound on its major
  version: there is no lockfile, so `uv run` resolves afresh on users' machines
  and an unbounded new major would break every install on the day it lands.

Run:  uv run tests/test_supply_chain.py
"""
from __future__ import annotations

import re
import sys
import tempfile
import tomllib
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "visualize" / "scripts"))
from okf_visualize import render

# A version segment like `name@1.2.3` (an exact release), not `name@1` or `@latest`.
EXACT_NPM_VERSION = re.compile(r"/npm/(?:@[^/@]+/)?[^/@]+@\d+\.\d+\.\d+(?:[-+][^/]*)?/")
SRI = re.compile(r"^sha(?:256|384|512)-[A-Za-z0-9+/]+={0,2}$")
SHIPPED_SCRIPT_DIRS = ("skills", "servers", "hooks")
PEP723 = re.compile(r"^# /// script$\n(?P<body>(?:^#(?: .*)?$\n)+?)^# ///$", re.MULTILINE)
UPPER_BOUND = re.compile(r"<\s*\d")


class _Scripts(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.external: list[dict[str, str | None]] = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            a = dict(attrs)
            if a.get("src"):
                self.external.append(a)


def external_scripts(html: str) -> list[dict[str, str | None]]:
    parser = _Scripts()
    parser.feed(html)
    return parser.external


def script_dependencies(path: Path) -> list[str] | None:
    """The PEP 723 `dependencies` list of a script, or None if it has no block."""
    m = PEP723.search(path.read_text(encoding="utf-8"))
    if m is None:
        return None
    toml = "\n".join(line[2:] if line.startswith("# ") else "" for line in m["body"].splitlines())
    return tomllib.loads(toml).get("dependencies", [])


class TestScriptIntegrity(unittest.TestCase):
    def assert_pinned_with_sri(self, html: str, where: str) -> None:
        scripts = external_scripts(html)
        self.assertTrue(scripts, f"{where}: no external <script src> found, the parser is broken")
        for a in scripts:
            src = a["src"]
            with self.subTest(where=where, src=src):
                self.assertRegex(src, EXACT_NPM_VERSION, "CDN script must pin an exact version")
                self.assertRegex(a.get("integrity") or "", SRI, "CDN script must carry SRI")
                self.assertEqual(a.get("crossorigin"), "anonymous",
                                 "SRI on a cross-origin script needs crossorigin=anonymous")

    def test_generated_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp, "b")
            bundle.mkdir()
            (bundle / "c.md").write_text("---\ntype: Reference\ntitle: t\n---\nbody\n", encoding="utf-8")
            out = Path(tmp, "viz.html")
            render(bundle, out)
            self.assert_pinned_with_sri(out.read_text(encoding="utf-8"), "okf_visualize output")

    def test_committed_pages_demos(self):
        pages = sorted((ROOT / "docs").glob("*.html"))
        self.assertTrue(pages)
        for page in pages:
            self.assert_pinned_with_sri(page.read_text(encoding="utf-8"), str(page.relative_to(ROOT)))


class TestShippedDependencyBounds(unittest.TestCase):
    def test_every_dependency_has_an_upper_bound(self):
        scripts = [p for d in SHIPPED_SCRIPT_DIRS for p in sorted((ROOT / d).rglob("*.py"))]
        checked = 0
        for path in scripts:
            deps = script_dependencies(path)
            if deps is None:
                continue
            checked += 1
            for dep in deps:
                with self.subTest(script=str(path.relative_to(ROOT)), dependency=dep):
                    self.assertRegex(dep, UPPER_BOUND, "bound the major version, e.g. 'mcp>=2,<3'")
        self.assertGreater(checked, 0, "no PEP 723 block found, the parser is broken")


if __name__ == "__main__":
    unittest.main(verbosity=2)
