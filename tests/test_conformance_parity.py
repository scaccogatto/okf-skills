#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["mcp>=2,<3", "pyyaml>=6,<7"]
# ///
"""Cross-tool parity: the validator, the MCP server and the visualizer must read a
bundle the same way (OKF v0.3 consumer rules).

Each script keeps its own copy of the helpers (.okf/decisions/self-contained-skills.md),
so nothing but a test like this one stops the copies from drifting. Every case
is a small bundle that once split the tools: the MCP server and the visualizer
must agree exactly (concept set, edges, status, current, tier, staleness), and
the validator's concept count and messages must match the same reading.

Run:  uv run tests/test_conformance_parity.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import time
import unittest
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar, NamedTuple

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "skills" / "validate" / "scripts" / "okf_validate.py"
for sub in ("servers", "skills/visualize/scripts", "skills/validate/scripts"):
    sys.path.insert(0, str(ROOT / sub))
import okf_mcp
import okf_validate
import okf_visualize

V03 = '---\nokf_version: "0.3"\n---\n\n# b\n'


def concept(extra: str = "", body: str = "body", type_: str = "Note") -> str:
    return f"---\ntype: {type_}\ntitle: t\ndescription: d\ntags: [x]\n{extra}---\n\n{body}\n"


def alias_bomb(levels: int) -> str:
    """A nested-alias YAML bomb: 10**levels leaves once stringified, cheap to parse."""
    lines = ["a0: &a0 [x, x, x, x, x, x, x, x, x, x]"]
    lines += [f"a{i}: &a{i} [{', '.join([f'*a{i - 1}'] * 10)}]" for i in range(1, levels)]
    return "\n".join(lines) + "\n"


def view_stale(stale_at: str, now: datetime) -> str:
    """The page's `staleOf` (R12), in Python: the verdict is taken at view time."""
    if stale_at in ("", "malformed"):
        return stale_at
    return "stale" if now >= datetime.fromisoformat(stale_at) else "fresh"


class Reading(NamedTuple):
    mcp: dict     # id -> card, with `stale` evaluated at `now`
    mcp_edges: set
    viz: dict     # id -> node
    viz_edges: set
    report: object  # okf_validate.Report, or the exception it raised
    now: datetime


def read_all(bundle: Path) -> Reading:
    now = datetime.now(UTC)
    snap = okf_mcp.snapshot(bundle)
    cards, m_edges = {}, set()
    for cid, path, meta, body in snap.items:
        cards[cid] = okf_mcp.card(cid, path, meta, snap) | {"stale": okf_mcp.staleness(meta, now)}
        m_edges |= {(cid, t) for t in okf_mcp.edges(snap, path, meta, body) - {cid}}
    nodes, edges = okf_visualize.build(bundle)
    try:
        report = okf_validate.validate(bundle)
    except Exception as exc:  # noqa: BLE001 - a crash is a parity failure, not a test error
        report = exc
    return Reading(cards, m_edges, {n["id"]: n for n in nodes},
                   {(e["source"], e["target"]) for e in edges}, report, now)


class ParityBase(unittest.TestCase):
    index = V03

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.bundle = Path(self._tmp.name)
        self.write("index.md", self.index)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, rel: str, text: str) -> None:
        path = self.bundle / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def read(self) -> Reading:
        r = read_all(self.bundle)
        self.assert_consumers_agree(r)
        return r

    def assert_consumers_agree(self, r: Reading) -> None:
        """MCP == visualizer on everything both expose."""
        self.assertEqual(set(r.mcp), set(r.viz), "concept sets differ")
        self.assertEqual(r.mcp_edges, r.viz_edges, "edges differ")
        for cid, c in r.mcp.items():
            n = r.viz[cid]
            with self.subTest(concept=cid):
                self.assertEqual(c["tier"], n["tier"])
                self.assertEqual(c["current"], n["state"] == "")
                self.assertEqual(c["stale"], view_stale(n["stale_at"], r.now))
                self.assertEqual(c["superseded_by"], n["superseded_cid"] or n["superseded_by"])
                if n["status"]:  # the page only shows a written status
                    self.assertEqual(c["status"], n["status"])

    def validator(self, r: Reading):
        if isinstance(r.report, Exception):
            self.fail(f"validator raised {type(r.report).__name__}: {r.report!s:.200}")
        return r.report

    def assert_validator_count(self, r: Reading) -> None:
        self.assertEqual(self.validator(r).concepts, len(r.mcp),
                         "validator concept count != consumer concept set")

    def messages(self, r: Reading, rel: str, kind: str = "warnings") -> list[str]:
        return [m for m in getattr(self.validator(r), kind) if m.startswith(f"{rel}: ")]


class InvalidFrontmatterParity(ParityBase):
    """R1, R2: invalid frontmatter is a §11.1 error for the validator and a skipped
    file for the consumers, never a crash."""

    CASES: ClassVar[dict[str, str]] = {
        "date": "decided: 2026-02-30\n",
        "int": "n: " + "9" * 5000 + "\n",
        "deep": "n: " + "[" * 3000 + "\n",
        "dup": "status: draft\nstatus: deprecated\n",
        "dupnested": "generated: {by: a, by: b}\n",
    }

    def test_each_invalid_block_is_skipped_and_an_error(self):
        self.write("ok.md", concept())
        for name, extra in self.CASES.items():
            self.write(f"{name}.md", concept(extra))
        r = self.read()
        self.assertEqual(set(r.mcp), {"ok"})
        for name in self.CASES:
            with self.subTest(validator=name):
                self.assertTrue(self.messages(r, f"{name}.md", "errors"),
                                f"validator reports no error for {name}.md")
        with self.subTest(validator="count"):
            self.assert_validator_count(r)

    def test_impossible_date_in_the_root_index(self):
        self.write("index.md", '---\nokf_version: "0.3"\ndecided: 2026-02-30\n---\n\n# b\n')
        self.write("sibling.md", concept())
        self.write("deep/f.md", concept("superseded_by: sibling.md\nstatus: deprecated\n"))
        r = self.read()
        # R7: no readable version is legacy, so the §6.2 root fallback applies
        self.assertIn(("deep/f", "sibling"), r.mcp_edges)
        with self.subTest(validator="index error"):
            self.assertTrue(self.messages(r, "index.md", "errors"))
        with self.subTest(validator="legacy reading"):
            self.assertTrue(any("v0.2 reading" in m for m in self.messages(r, "deep/f.md")))

    def test_indented_delimiter_stays_inside_the_block(self):
        self.write("c.md", "---\ntype: Note\ndescription: |\n  ---\n  more\ntitle: kept\n"
                           "tags: [x]\n---\nbody\n")
        r = self.read()
        self.assertEqual(r.mcp["c"]["title"], "kept")
        self.assertEqual(r.viz["c"]["title"], "kept")
        with self.subTest(validator="count"):
            self.assert_validator_count(r)
            self.assertEqual(self.messages(r, "c.md", "errors"), [])


class TypeParity(ParityBase):
    """R3: only a non-empty string `type` makes a concept."""

    def test_non_string_type(self):
        for i, value in enumerate(("42", "true", "[x]", "{a: b}", '""', '"  "')):
            self.write(f"c{i}.md", f"---\ntype: {value}\ntitle: t\n---\nbody\n")
        self.write("ok.md", concept())
        r = self.read()
        self.assertEqual(set(r.mcp), {"ok"})
        with self.subTest(validator="count"):
            self.assert_validator_count(r)


class StatusParity(ParityBase):
    """R6: only an exact vocabulary string is that status."""

    VALUES: ClassVar[dict[str, str | None]] = {"absent": None, "null": "null", "empty": '""', "draft": "draft",
              "stable": "stable", "deprecated": "deprecated", "false": "false", "zero": "0",
              "padded": '" stable "', "capital": "Stable", "list": "[stable]"}
    CURRENT = frozenset({"absent", "null", "empty", "draft", "stable"})

    def test_status_variants(self):
        for name, raw in self.VALUES.items():
            self.write(f"{name}.md", concept("" if raw is None else f"status: {raw}\n"))
        r = self.read()
        for name in self.VALUES:
            with self.subTest(status=name):
                self.assertEqual(r.mcp[name]["current"], name in self.CURRENT)
        with self.subTest(validator="unknown-status warnings"):
            warned = {name for name in self.VALUES
                      if any("unknown `status`" in m for m in self.messages(r, f"{name}.md"))}
            self.assertEqual(warned, set(self.VALUES) - self.CURRENT - {"deprecated"})


class TimestampParity(ParityBase):
    """R5, R12: one timestamp grammar for every tool."""

    INVALID = ("2099-01-01T00:00Z", "2099-01-01T00:00:00+0000", "2099-01-01T00:00:00+05",
               "2099-01-01T24:00:00Z", "2099-02-30", " 2099-01-01", "2099-01-01T00:00:00")
    VALID = ("2099-01-01", "2099-01-01T00:00:00Z", "2099-01-01t00:00:00z",
             "2099-01-01 00:00:00.5+05:00", "2000-01-01T00:00:00-01:00")

    def test_stale_after_variants(self):
        values = {f"bad{i}": v for i, v in enumerate(self.INVALID)}
        values |= {f"good{i}": v for i, v in enumerate(self.VALID)}
        for name, v in values.items():
            self.write(f"{name}.md", concept(f"stale_after: '{v}'\n"))
        r = self.read()
        for name, v in values.items():
            with self.subTest(stale_after=v):
                self.assertEqual(r.mcp[name]["stale"] == "malformed", name.startswith("bad"))
        with self.subTest(validator="timestamp warnings"):
            warned = {v for name, v in values.items()
                      if any("stale_after" in m and "§5" in m for m in self.messages(r, f"{name}.md"))}
            self.assertEqual(warned, set(self.INVALID))

    def test_verified_at_variants_drive_the_tier(self):
        gen = 'generated: {by: a, at: "2026-01-01T00:00:00Z"}\n'
        for i, v in enumerate(self.INVALID[:3]):
            self.write(f"bad{i}.md", concept(gen + f"verified: {{by: 'human:m', at: '{v}'}}\n"))
        self.write("good.md", concept(gen + "verified: {by: 'human:m', at: '2026-01-02t00:00:00z'}\n"))
        self.write("nogen.md", concept("generated: {by: a}\n"
                                       "verified: {by: 'human:m', at: '2020-01-01'}\n"))
        r = self.read()
        self.assertEqual({c: r.mcp[c]["tier"] for c in r.mcp},
                         {"bad0": "unverified", "bad1": "unverified", "bad2": "unverified",
                          "good": "human-reviewed", "nogen": "human-reviewed"})


class VersionAndResolutionParity(ParityBase):
    """R7, R8, R9"""

    def test_empty_okf_version_is_legacy(self):
        self.write("index.md", '---\nokf_version: ""\n---\n\n# b\n')
        self.write("sibling.md", concept())
        self.write("deep/f.md", concept("status: deprecated\nsuperseded_by: sibling.md\n"))
        r = self.read()
        self.assertIn(("deep/f", "sibling"), r.mcp_edges)
        with self.subTest(validator="legacy reading"):
            self.assertTrue(any("v0.2 reading" in m for m in self.messages(r, "deep/f.md")))

    def test_legacy_fallback_needs_a_missing_file_not_a_missing_concept(self):
        self.write("index.md", '---\nokf_version: "0.2"\n---\n\n# b\n')
        self.write("sibling.md", concept())
        self.write("deep/sibling.md", "# not a concept\n")
        self.write("deep/f.md", concept("status: deprecated\nsuperseded_by: sibling.md\n"))
        r = self.read()
        self.assertNotIn(("deep/f", "sibling"), r.mcp_edges)
        self.assertEqual(r.mcp["deep/f"]["superseded_by"], "sibling.md")
        with self.subTest(validator="no path warning"):
            self.assertFalse([m for m in self.messages(r, "deep/f.md") if "§6.2" in m])

    def test_top_level_resource_is_a_path_field(self):
        self.write("t.md", concept())
        self.write("s.md", concept("resource: /t.md\n"))
        self.write("gone.md", concept("resource: /missing.md\n"))
        r = self.read()
        self.assertIn(("s", "t"), r.mcp_edges)
        with self.subTest(validator="missing resource warned"):
            self.assertTrue([m for m in self.messages(r, "gone.md") if "§6.2" in m])


class LinkParity(ParityBase):
    """R10: links come from the body with code removed, reference definitions included."""

    BODY = ("see `[a](span.md)` and [b](inline.md)\n\n"
            "````\n```\n[c](fence.md)\n```\n````\n\n"
            "[r]: ref.md\n[^f]: foot.md\n")

    def test_edges(self):
        for name in ("span", "fence", "ref", "foot", "inline"):
            self.write(f"{name}.md", concept())
        self.write("src.md", concept(body=self.BODY))
        r = self.read()
        self.assertEqual({t for s, t in r.mcp_edges if s == "src"}, {"inline", "ref"})

    def test_validator_broken_links_follow_the_same_reading(self):
        self.write("src.md", concept(body=self.BODY))  # every target is missing
        r = self.read()
        broken = {m.split("`")[1] for m in self.messages(r, "src.md")
                  if "cross-link target not found" in m}
        with self.subTest(validator="broken links"):
            self.assertEqual(broken, {"inline.md", "ref.md"})


class AliasBombParity(ParityBase):
    """R4: a bomb in any field finishes fast and the concept still renders."""

    FIELDS = ("title", "description", "status", "tags", "stale_after", "superseded_by",
              "resource", "generated", "verified", "sources", "timestamp", "usage_window")

    def test_consumers_finish_fast(self):
        head = "---\ntype: Note\n" + alias_bomb(9)
        for field in self.FIELDS:
            self.write(f"{field}.md", head + f"{field}: *a8\n---\nbody\n")
        self.write("sub.md", head + "generated: {by: *a8, at: *a8}\n"
                                    "verified: {by: *a8, at: *a8}\n"
                                    "sources: [{resource: *a8, author: *a8, usage_count: *a8,"
                                    " usage_window: {from: *a8, to: *a8}, title: *a8}]\n"
                                    "---\nbody\n")
        self.write("type.md", "---\n" + alias_bomb(9) + "type: *a8\n---\nbody\n")
        start = time.monotonic()
        snap = okf_mcp.snapshot(self.bundle)
        cards = [okf_mcp.card(c, p, m, snap) for c, p, m, _b in snap.items]
        nodes, _edges = okf_visualize.build(self.bundle)
        okf_visualize.json_for_script(nodes)
        self.assertLess(time.monotonic() - start, 1.0)
        self.assertEqual({c["id"] for c in cards}, set(self.FIELDS) | {"sub"})
        self.assertEqual({n["id"] for n in nodes}, set(self.FIELDS) | {"sub"})

    def test_validator_finishes_fast(self):
        # Run out of process with a hard timeout: an unsafe str() of 10**8 leaves
        # would otherwise hang the suite and eat gigabytes.
        self.write("c.md", concept(alias_bomb(8) + "status: *a7\n"))
        start = time.monotonic()
        try:
            subprocess.run([sys.executable, str(VALIDATOR), str(self.bundle)],
                           capture_output=True, timeout=3, check=False)
        except subprocess.TimeoutExpired:
            self.fail("validator did not finish within 3 s on an alias bomb in `status`")
        self.assertLess(time.monotonic() - start, 3.0)


class RealBundleParity(ParityBase):
    """This repository's own bundle reads the same in both consumers."""

    def test_repo_bundle(self):
        bundle = ROOT / ".okf"
        if not bundle.is_dir():
            self.skipTest("no .okf bundle in this checkout")
        r = read_all(bundle)
        self.assert_consumers_agree(r)
        self.assert_validator_count(r)


if __name__ == "__main__":
    unittest.main(verbosity=2)
