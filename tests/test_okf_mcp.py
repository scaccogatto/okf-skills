#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["mcp>=2", "pyyaml>=6"]
# ///
"""Unit tests for okf_mcp.py — the read-only MCP server (issue #41).

Tools are exercised through FastMCP's own dispatch, so a rename or a signature
that the SDK cannot expose fails here rather than at connect time.

Run:  uv run tests/test_okf_mcp.py
"""
from __future__ import annotations

import asyncio
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "servers"))
from okf_mcp import build  # noqa: E402

CONCEPT = ('---\ntype: Decision\ntitle: {title}\ndescription: {desc}\n'
           'tags: [adr]\nstatus: {status}\n---\n\n{body}\n')


def call(mcp, name, **args):
    """Dispatch a tool the way a client would, and decode its structured result."""
    result = asyncio.run(mcp.call_tool(name, args))
    data = result.structured_content
    if data is None:  # unstructured fallback: one text block
        return result.content[0].text
    # The SDK wraps a non-dict return value under a synthetic "result" key.
    return data["result"] if set(data) == {"result"} else data


class ServerTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.bundle = Path(self._tmp.name)
        (self.bundle / "decisions").mkdir()
        (self.bundle / "index.md").write_text(
            '---\nokf_version: "0.2"\n---\n\n# b\n\n* [a](decisions/alpha.md)\n',
            encoding="utf-8")
        (self.bundle / "decisions" / "alpha.md").write_text(
            CONCEPT.format(title="Alpha", desc="the first one", status="active",
                           body="links to [beta](beta.md) and [out](https://x.test)"),
            encoding="utf-8")
        (self.bundle / "decisions" / "beta.md").write_text(
            CONCEPT.format(title="Beta", desc="second", status="deprecated",
                           body="mentions parsnip in the body only"),
            encoding="utf-8")
        self.mcp = build(self.bundle)

    def tearDown(self):
        self._tmp.cleanup()

    def test_three_tools_are_exposed(self):
        names = {t.name for t in asyncio.run(self.mcp.list_tools())}
        self.assertEqual(names, {"search_concepts", "read_concept", "get_neighbors"})

    def test_search_matches_metadata_and_body(self):
        self.assertEqual([c["id"] for c in call(self.mcp, "search_concepts", query="alpha")],
                         ["decisions/alpha"])
        self.assertEqual([c["id"] for c in call(self.mcp, "search_concepts", query="parsnip")],
                         ["decisions/beta"])

    def test_search_ranks_metadata_above_body(self):
        # "second" is Beta's description and appears nowhere in Alpha; add a body
        # hit in Alpha and the metadata match must still come first.
        (self.bundle / "decisions" / "alpha.md").write_text(
            CONCEPT.format(title="Alpha", desc="the first one", status="active",
                           body="this is the second paragraph"), encoding="utf-8")
        self.assertEqual([c["id"] for c in call(self.mcp, "search_concepts", query="second")],
                         ["decisions/beta", "decisions/alpha"])

    def test_search_honours_limit_and_rejects_empty(self):
        self.assertEqual(len(call(self.mcp, "search_concepts", query="e", limit=1)), 1)
        with self.assertRaises(Exception):
            call(self.mcp, "search_concepts", query="   ")

    def test_read_returns_frontmatter_verbatim(self):
        text = call(self.mcp, "read_concept", concept_id="decisions/beta")
        self.assertTrue(text.startswith("---\ntype: Decision"))
        self.assertIn("parsnip", text)

    def test_read_reaches_reserved_files(self):
        self.assertIn("okf_version", call(self.mcp, "read_concept", concept_id="index"))

    def test_read_refuses_escaping_the_bundle(self):
        with self.assertRaises(Exception):
            call(self.mcp, "read_concept", concept_id="../../etc/passwd")
        with self.assertRaises(Exception):
            call(self.mcp, "read_concept", concept_id="decisions/nope")

    def test_neighbors_both_directions_and_no_external_links(self):
        alpha = call(self.mcp, "get_neighbors", concept_id="decisions/alpha")
        self.assertEqual([c["id"] for c in alpha["outgoing"]], ["decisions/beta"])
        self.assertEqual(alpha["incoming"], [])
        beta = call(self.mcp, "get_neighbors", concept_id="decisions/beta")
        self.assertEqual([c["id"] for c in beta["incoming"]], ["decisions/alpha"])
        self.assertEqual(beta["outgoing"], [])
        self.assertEqual(beta["incoming"][0]["status"], "active")


class NoBundleTest(unittest.TestCase):
    """The plugin installs into projects with no bundle: the server must still
    start, and say what is missing on first use."""

    def test_missing_bundle_is_a_tool_error_not_a_startup_failure(self):
        mcp = build(Path("definitely-not-a-bundle"))
        self.assertEqual({t.name for t in asyncio.run(mcp.list_tools())},
                         {"search_concepts", "read_concept", "get_neighbors"})
        with self.assertRaises(Exception) as ctx:
            call(mcp, "search_concepts", query="anything")
        self.assertIn("OKF_BUNDLE", str(ctx.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
