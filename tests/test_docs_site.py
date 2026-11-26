#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Checks for the GitHub Pages site in docs/.

- Every internal href or src in docs/*.html resolves to a file in docs/
  (a #fragment is allowed, and is not checked).
- Every page has a non-empty <title>.
- No hand-written page contains an em-dash. The two generated graph pages
  (`make docs` output) are exempt: their text comes from the bundles.

Run:  uv run tests/test_docs_site.py
"""
from __future__ import annotations

import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

DOCS = Path(__file__).resolve().parents[1] / "docs"
GENERATED_PAGES = ("demo.html", "self.html")
EM_DASH = "—"


class _Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.refs: list[str] = []
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        for key, value in attrs:
            if key in ("href", "src") and value:
                self.refs.append(value)

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def parse(page: Path) -> _Page:
    parser = _Page()
    parser.feed(page.read_text(encoding="utf-8"))
    return parser


def internal_target(page: Path, ref: str) -> Path | None:
    """The local file a reference points at, or None for external and fragment-only refs."""
    parts = urlsplit(ref)
    if parts.scheme or parts.netloc or not parts.path:
        return None
    return (page.parent / unquote(parts.path)).resolve()


PAGES = sorted(DOCS.glob("*.html"))


class TestDocsSite(unittest.TestCase):
    def test_pages_exist(self):
        self.assertIn(DOCS / "index.html", PAGES)
        for name in GENERATED_PAGES:
            self.assertIn(DOCS / name, PAGES)

    def test_internal_links_resolve(self):
        for page in PAGES:
            for ref in parse(page).refs:
                target = internal_target(page, ref)
                if target is None:
                    continue
                with self.subTest(page=page.name, ref=ref):
                    self.assertTrue(target.is_relative_to(DOCS.resolve()), "link leaves docs/")
                    self.assertTrue(target.is_file(), "target file does not exist")

    def test_every_page_has_a_title(self):
        for page in PAGES:
            with self.subTest(page=page.name):
                self.assertTrue(parse(page).title.strip())

    def test_no_em_dash_in_hand_written_pages(self):
        for page in PAGES:
            if page.name in GENERATED_PAGES:
                continue
            with self.subTest(page=page.name):
                self.assertNotIn(EM_DASH, page.read_text(encoding="utf-8"))

    def test_internal_target_helper(self):
        page = DOCS / "index.html"
        self.assertIsNone(internal_target(page, "https://example.com/a.html"))
        self.assertIsNone(internal_target(page, "#quickstart"))
        self.assertEqual(internal_target(page, "start.html#ci"), (DOCS / "start.html").resolve())


if __name__ == "__main__":
    unittest.main()
