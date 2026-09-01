#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["mcp>=2"]
# ///
"""End-to-end test for the MCP server (issue #41).

`test_okf_mcp.py` dispatches tools in-process, so it never touches the two things
that decide whether the plugin actually works for a user: the stdio transport,
and the command in `.mcp.json`. This one spawns the server exactly as Claude Code
would — the command and args are read from `.mcp.json`, not restated here, so a
typo in the wiring fails the build — and drives it with the SDK's own client.

The bundle under test is this repository's own `.okf/`, reached the way the
shipped config reaches it: no argument, cwd at the plugin root.

Run:  uv run tests/test_okf_mcp_e2e.py
"""
from __future__ import annotations

import asyncio
import json
import sys
import unittest
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
TIMEOUT = 180  # uv may resolve and build the environment on the first run


def server_params() -> StdioServerParameters:
    """The shipped `.mcp.json` entry, resolved into something spawnable."""
    config = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))
    servers = config["mcpServers"]
    assert list(servers) == ["bundle"], f"unexpected servers in .mcp.json: {list(servers)}"
    entry = servers["bundle"]
    expand = lambda s: s.replace("${CLAUDE_PLUGIN_ROOT}", str(ROOT))  # noqa: E731
    return StdioServerParameters(
        command=expand(entry["command"]),
        args=[expand(a) for a in entry.get("args", [])],
        env={**entry.get("env", {}), "PATH": __import__("os").environ["PATH"]},
        cwd=str(ROOT),
    )


async def session_probe() -> dict:
    async with stdio_client(server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            tools = await session.list_tools()
            hits = await session.call_tool("search_concepts", {"query": "validator"})
            concept = await session.call_tool(
                "read_concept", {"concept_id": "decisions/mcp-server"})
            neighbors = await session.call_tool(
                "get_neighbors", {"concept_id": "components/validator"})
            missing = await session.call_tool("read_concept", {"concept_id": "nope"})
            return {
                "protocol": init.protocol_version,
                "server": init.server_info.name,
                "tools": sorted(t.name for t in tools.tools),
                "schemas": {t.name: t.input_schema for t in tools.tools},
                "hits": [c["id"] for c in hits.structured_content["result"]],
                "concept": concept.structured_content["result"],
                "neighbors": neighbors.structured_content,
                "missing_is_error": missing.is_error,
                "missing_text": missing.content[0].text if missing.content else "",
            }


class EndToEnd(unittest.TestCase):
    """One spawn, many assertions: starting the server is the slow part."""

    @classmethod
    def setUpClass(cls):
        cls.probe = asyncio.run(asyncio.wait_for(session_probe(), TIMEOUT))

    def test_handshake_completes(self):
        self.assertEqual(self.probe["server"], "okf")
        self.assertRegex(self.probe["protocol"], r"^\d{4}-\d{2}-\d{2}$")

    def test_the_three_tools_are_advertised_with_their_arguments(self):
        self.assertEqual(self.probe["tools"],
                         ["get_neighbors", "read_concept", "search_concepts"])
        self.assertIn("query", self.probe["schemas"]["search_concepts"]["properties"])
        self.assertIn("concept_id", self.probe["schemas"]["read_concept"]["properties"])

    def test_default_bundle_is_the_plugin_root_okf(self):
        # No argument in .mcp.json: the server must find ./.okf from its cwd.
        self.assertIn("components/validator", self.probe["hits"])

    def test_read_concept_returns_the_file_verbatim(self):
        self.assertTrue(self.probe["concept"].startswith("---\ntype: Decision"))
        self.assertIn("search_concepts", self.probe["concept"])

    def test_neighbors_cross_the_wire_as_structured_data(self):
        ids = {c["id"] for c in self.probe["neighbors"]["incoming"]}
        self.assertIn("skills/validate", ids)

    def test_an_anticipated_failure_reaches_the_client_readably(self):
        # A crash would arrive as "Error executing tool read_concept" instead.
        self.assertTrue(self.probe["missing_is_error"])
        self.assertIn("no such concept", self.probe["missing_text"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
