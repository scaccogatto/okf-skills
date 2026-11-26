#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["mcp>=2,<3", "pyyaml>=6,<7"]
# ///
"""Unit tests for okf_mcp.py, the read-only MCP server (issue #41).

Tools are exercised through FastMCP's own dispatch, so a rename or a signature
that the SDK cannot expose fails here rather than at connect time.

Run:  uv run tests/test_okf_mcp.py
"""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "servers"))
from mcp.server.mcpserver.exceptions import ToolError
from okf_mcp import as_list, build

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
            '---\nokf_version: "0.3"\n---\n\n# b\n\n* [a](decisions/alpha.md)\n',
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
        with self.assertRaisesRegex(ToolError, "must not be empty"):
            call(self.mcp, "search_concepts", query="   ")

    def test_read_returns_frontmatter_verbatim(self):
        text = call(self.mcp, "read_concept", concept_id="decisions/beta")
        self.assertTrue(text.startswith("---\ntype: Decision"))
        self.assertIn("parsnip", text)

    def test_read_reaches_reserved_files(self):
        self.assertIn("okf_version", call(self.mcp, "read_concept", concept_id="index"))

    def test_read_refuses_escaping_the_bundle(self):
        with self.assertRaisesRegex(ToolError, "no such concept"):
            call(self.mcp, "read_concept", concept_id="../../etc/passwd")
        with self.assertRaisesRegex(ToolError, "no such concept"):
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
        # Every tool must name the real problem: "no such concept" would point at
        # the id the caller passed instead of at the absent bundle.
        for name, args in [("search_concepts", {"query": "anything"}),
                           ("read_concept", {"concept_id": "index"}),
                           ("get_neighbors", {"concept_id": "index"})]:
            with self.subTest(tool=name), self.assertRaises(Exception) as ctx:
                call(mcp, name, **args)
            self.assertIn("OKF_BUNDLE", str(ctx.exception))


def write(bundle: Path, rel: str, text: str) -> None:
    path = bundle / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def concept(extra: str = "", body: str = "body", type_: str = "Note") -> str:
    return f"---\ntype: {type_}\n{extra}---\n\n{body}\n"


class V03Base(unittest.TestCase):
    version = "0.3"

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.bundle = Path(self._tmp.name)
        header = f'---\nokf_version: "{self.version}"\n---\n' if self.version else ""
        write(self.bundle, "index.md", header + "\n# b\n")
        self.mcp = build(self.bundle)

    def tearDown(self):
        self._tmp.cleanup()

    def cards(self, query="x"):
        return {c["id"]: c for c in call(self.mcp, "search_concepts", query=query, limit=100)}

    def out(self, cid):
        return {c["id"] for c in call(self.mcp, "get_neighbors", concept_id=cid)["outgoing"]}


class DiscoveryTest(V03Base):
    """§3.2"""

    def test_only_typed_markdown_is_a_concept(self):
        write(self.bundle, "typed.md", concept("title: x\n"))
        write(self.bundle, "README.md", "# no frontmatter x\n")
        write(self.bundle, "untyped.md", "---\ntitle: x\n---\nx\n")
        write(self.bundle, "emptytype.md", '---\ntype: ""\n---\nx\n')
        self.assertEqual(set(self.cards()), {"typed"})

    def test_dot_components_below_the_root_are_not_part_of_the_bundle(self):
        write(self.bundle, ".hidden.md", concept("title: x\n"))
        write(self.bundle, ".drafts/a.md", concept("title: x\n"))
        write(self.bundle, "ok/.cache/b.md", concept("title: x\n"))
        write(self.bundle, "ok/c.md", concept("title: x\n"))
        self.assertEqual(set(self.cards()), {"ok/c"})

    def test_a_dot_named_bundle_root_is_fine(self):
        root = self.bundle / ".okf"
        write(root, "a.md", concept("title: x\n"))
        hits = call(build(root), "search_concepts", query="x")
        self.assertEqual([c["id"] for c in hits], ["a"])

    def test_symlinks_leaving_the_root_are_not_followed(self):
        with tempfile.TemporaryDirectory() as outside:
            write(Path(outside), "secret.md", concept("title: x\n"))
            write(Path(outside), "dir/inner.md", concept("title: x\n"))
            os.symlink(Path(outside) / "secret.md", self.bundle / "link.md")
            os.symlink(Path(outside) / "dir", self.bundle / "linkdir")
            write(self.bundle, "real.md", concept("title: x\n"))
            self.assertEqual(set(self.cards()), {"real"})


class ResolutionTest(V03Base):
    """§6, §6.4"""

    def test_percent_decoding_fragments_schemes_and_root_paths(self):
        write(self.bundle, "my concept.md", concept("title: x\n"))
        write(self.bundle, "top.md", concept("title: x\n"))
        write(self.bundle, "a/src.md", concept(
            "title: x\n",
            "[a](../my%20concept.md#sec) [b](/top.md) [c](https://h.test/top.md) "
            "[d](../../outside.md)"))
        self.assertEqual(self.out("a/src"), {"my concept", "top"})

    def test_path_fields_are_graph_edges(self):
        for name in ("new", "comp", "exec", "att", "src"):
            write(self.bundle, f"{name}.md", concept("title: x\n"))
        write(self.bundle, "m/all.md", concept(
            "title: x\nsuperseded_by: ../new.md\ncomputation: /comp.md\n"
            "executor: {resource: /exec.md}\nattester: {resource: ../att.md}\n"
            "sources:\n  - {resource: ../src.md}\n  - {resource: 'https://e.test/x'}\n"))
        self.assertEqual(self.out("m/all"), {"new", "comp", "exec", "att", "src"})

    def test_bare_mapping_sources_is_one_item(self):
        write(self.bundle, "t.md", concept("title: x\n"))
        write(self.bundle, "s.md", concept("title: x\nsources: {resource: /t.md}\n"))
        self.assertEqual(self.out("s"), {"t"})

    def test_legacy_root_fallback_only_for_path_fields_in_old_bundles(self):
        for version, expected in (("0.2", {"sibling"}), ("", {"sibling"}), ("0.3", set())):
            with self.subTest(version=version):
                self.version = version
                self.tearDown()  # release the bundle the previous setUp created
                self.setUp()
                write(self.bundle, "sibling.md", concept("title: x\n"))
                write(self.bundle, "deep/f.md", concept("title: x\nsuperseded_by: sibling.md\n"))
                write(self.bundle, "deep/g.md", concept("title: x\n", "[l](sibling.md)"))
                self.assertEqual(self.out("deep/f"), expected)
                self.assertEqual(self.out("deep/g"), set())  # body links never fall back


class TrustTest(V03Base):
    """§5.3, §5.2, §11.2"""

    def tier(self, extra):
        write(self.bundle, "c.md", concept("title: x\n" + extra))
        return self.cards()["c"]["tier"]

    def test_tiers_from_current_events_only(self):
        gen = 'generated: {by: a, at: "2026-06-20T00:00:00Z"}\n'
        self.assertEqual(self.tier(gen), "unverified")
        self.assertEqual(self.tier(gen + 'verified: {by: "process:n", at: "2026-06-21T00:00:00Z"}\n'),
                         "machine-confirmed")
        self.assertEqual(self.tier(gen + 'verified: {by: "team:fin", at: "2026-06-21T00:00:00Z"}\n'),
                         "machine-confirmed")
        self.assertEqual(self.tier(gen + 'verified:\n  - {by: "process:n", at: "2026-06-21T00:00:00Z"}\n'
                                         '  - {by: "human:m", at: "2026-06-22T00:00:00Z"}\n'),
                         "human-reviewed")

    def test_a_human_review_before_the_last_change_does_not_count(self):
        gen = 'generated: {by: a, at: "2026-06-20T12:00:00Z"}\n'
        self.assertEqual(self.tier(gen + 'verified: {by: "human:m", at: "2026-06-20T11:59:59Z"}\n'),
                         "unverified")
        # equal instants are current, and offsets are compared as instants
        self.assertEqual(self.tier(gen + 'verified: {by: "human:m", at: "2026-06-20T13:00:00+01:00"}\n'),
                         "human-reviewed")

    def test_no_generated_means_every_parseable_event_is_current(self):
        self.assertEqual(self.tier('verified: {by: "human:m", at: "2020-01-01"}\n'), "human-reviewed")

    def test_date_only_is_start_of_day_utc_and_native_yaml_values_work(self):
        gen = "generated: {by: a, at: 2026-06-20}\n"  # native date
        self.assertEqual(self.tier(gen + 'verified: {by: "human:m", at: "2026-06-20"}\n'), "human-reviewed")
        self.assertEqual(self.tier(gen + 'verified: {by: "human:m", at: "2026-06-19"}\n'), "unverified")
        self.assertEqual(self.tier(gen + 'verified: {by: "human:m", at: 2026-06-21 08:00:00+00:00}\n'),
                         "human-reviewed")

    def test_events_without_by_or_at_or_an_offset_are_not_current(self):
        gen = 'generated: {by: a, at: "2026-06-20T00:00:00Z"}\n'
        for event in ('{at: "2026-06-21T00:00:00Z"}', '{by: "human:m"}',
                      '{by: "human:m", at: "2026-06-21T00:00:00"}', '{by: "human:m", at: soon}'):
            with self.subTest(event=event):
                self.assertEqual(self.tier(gen + f"verified: {event}\n"), "unverified")

    def test_unusable_verified_values_are_absent(self):
        for value in ("null", '""', "[]", "[1, 2]"):
            with self.subTest(value=value):
                self.assertEqual(self.tier(f"verified: {value}\n"), "unverified")


class LifecycleTest(V03Base):
    """§5.4, §5.5, §11.2"""

    def card(self, extra):
        write(self.bundle, "c.md", concept("title: x\n" + extra))
        return self.cards()["c"]

    def test_stale_states(self):
        self.assertEqual(self.card("")["stale"], "")
        for empty in ("null", '""'):
            self.assertEqual(self.card(f"stale_after: {empty}\n")["stale"], "")
        self.assertEqual(self.card('stale_after: "2999-01-01T00:00:00Z"\n')["stale"], "fresh")
        self.assertEqual(self.card('stale_after: "2000-01-01T00:00:00Z"\n')["stale"], "stale")
        self.assertEqual(self.card("stale_after: 2000-01-01\n")["stale"], "stale")
        self.assertEqual(self.card('stale_after: "2999-01-01T00:00:00"\n')["stale"], "malformed")
        self.assertEqual(self.card("stale_after: someday\n")["stale"], "malformed")

    def test_status_absent_is_stable_and_unknown_is_not_current(self):
        c = self.card("")
        self.assertEqual((c["status"], c["current"]), ("stable", True))
        c = self.card("status: draft\n")
        self.assertEqual((c["status"], c["current"]), ("draft", True))
        for raw in ("deprecated", "active", "Stable"):
            c = self.card(f"status: {raw}\n")
            self.assertEqual((c["status"], c["current"]), (raw, False))

    def test_superseded_by_is_an_id_when_it_resolves_else_raw(self):
        write(self.bundle, "d/new.md", concept("title: x\n"))
        write(self.bundle, "d/old.md", concept("title: x\nstatus: deprecated\nsuperseded_by: new.md\n"))
        write(self.bundle, "d/gone.md", concept("title: x\nsuperseded_by: /nowhere.md\n"))
        cards = self.cards()
        self.assertEqual(cards["d/old"]["superseded_by"], "d/new")
        self.assertEqual(cards["d/gone"]["superseded_by"], "/nowhere.md")
        self.assertEqual(cards["d/new"]["superseded_by"], "")

    def test_scalar_tags_are_one_tag(self):
        write(self.bundle, "t.md", concept("tags: red, green\n"))
        self.assertEqual([c["id"] for c in call(self.mcp, "search_concepts", query="red, green")], ["t"])
        self.assertEqual(as_list("red, green"), ["red, green"])
        self.assertEqual(as_list(None) + as_list("") + as_list([]), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
