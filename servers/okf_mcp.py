#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["mcp>=2", "pyyaml>=6"]
# ///
"""Read-only MCP server over an Open Knowledge Format (OKF) bundle.

Three tools, the shape every other OKF toolkit converged on:
`search_concepts`, `read_concept`, `get_neighbors`. Nothing writes.

For an agent that already has file tools this duplicates Grep and Read — that
is the whole reason the July 2026 map declined to build it. It ships anyway for
category parity, and the reasoning is recorded verbatim in
`.okf/decisions/mcp-server.md` rather than left to be rediscovered.

Bundle directory: first CLI argument, else `$OKF_BUNDLE`, else `./.okf`.

Run:  uv run servers/okf_mcp.py [bundle-dir]
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any

import yaml
from mcp.server.mcpserver import MCPServer

RESERVED = {"index.md", "log.md"}
FENCE = re.compile(r"^(```|~~~)")
LINK = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def split_frontmatter(text: str):
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines(keepends=True)
    if lines[0].strip() != "---":
        return {}, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            try:
                meta = yaml.safe_load("".join(lines[1:i])) or {}
            except yaml.YAMLError:
                meta = {}
            return (meta if isinstance(meta, dict) else {}), "".join(lines[i + 1:])
    return {}, text


def link_targets(text: str):
    out, in_fence = [], False
    for line in text.splitlines():
        if FENCE.match(line.strip()):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.extend(LINK.findall(line))
    return out


def resolve(target: str, path: Path, bundle: Path) -> str | None:
    """Resolve a link or `sources[].resource` to a concept id, or None when it is
    not one (external URL, asset, scope descriptor, escape from the tree)."""
    t = str(target).split("#", 1)[0]
    if not t.endswith(".md"):
        return None
    if t.startswith("/"):
        return t.lstrip("/")[:-3]
    cand = (path.parent / t).resolve()
    return cand.relative_to(bundle.resolve()).as_posix()[:-3] \
        if cand.is_relative_to(bundle.resolve()) else None


def source_resources(meta: dict):
    entries = meta.get("sources")
    if not isinstance(entries, list):
        return []
    return [str(e["resource"]) for e in entries
            if isinstance(e, dict) and e.get("resource")]


# ponytail: the bundle is re-read from disk on every call. Correct on a bundle
# edited mid-session, and fine up to a few thousand concepts; cache on mtime if
# a bundle ever gets big enough to notice.
def concepts(bundle: Path):
    """Every non-reserved concept, as (id, path, meta, body)."""
    if not bundle.is_dir():
        raise ValueError(f"no OKF bundle at {bundle} — set OKF_BUNDLE to one")
    for p in sorted(bundle.rglob("*.md")):
        if not p.is_file() or p.name in RESERVED:
            continue
        try:
            raw = p.read_text(encoding="utf-8").lstrip("﻿")
        except (UnicodeDecodeError, OSError):
            continue
        meta, body = split_frontmatter(raw)
        yield p.relative_to(bundle).with_suffix("").as_posix(), p, meta, body


def card(cid: str, meta: dict) -> dict:
    return {
        "id": cid,
        "type": str(meta.get("type", "Untyped")),
        "title": str(meta.get("title", cid.rsplit("/", 1)[-1])),
        "description": str(meta.get("description", "")),
        "status": str(meta.get("status", "")),
        "stale_after": str(meta.get("stale_after") or ""),
    }


def concept_path(bundle: Path, concept_id: str) -> Path:
    """Bundle-relative id -> file path, refusing anything outside the bundle."""
    root = bundle.resolve()
    p = (root / f"{concept_id.strip().lstrip('/')}.md").resolve()
    if not p.is_relative_to(root) or not p.is_file():
        raise ValueError(f"no such concept: {concept_id}")
    return p


def build(bundle: Path) -> MCPServer:
    mcp = MCPServer("okf")

    @mcp.tool()
    def search_concepts(query: str, limit: int = 20) -> list[dict]:
        """Find concepts in the bundle whose metadata or body matches `query`.

        Case-insensitive substring match over title, description, tags, id and
        body. Matches in metadata rank above matches in the body only.
        """
        q = query.strip().lower()
        if not q:
            raise ValueError("query must not be empty")
        hits = []
        for cid, _p, meta, body in concepts(bundle):
            c = card(cid, meta)
            tags = " ".join(str(t) for t in meta.get("tags", [])
                            if isinstance(meta.get("tags"), list))
            head = f"{cid} {c['title']} {c['description']} {tags}".lower()
            if q in head:
                hits.append((0, c))
            elif q in body.lower():
                hits.append((1, c))
        hits.sort(key=lambda h: (h[0], h[1]["id"]))
        return [c for _rank, c in hits[:max(1, limit)]]

    @mcp.tool()
    def read_concept(concept_id: str) -> str:
        """Return one concept verbatim, frontmatter included.

        `concept_id` is the path inside the bundle without `.md`, as returned by
        `search_concepts` (e.g. `decisions/no-hooks`). `index` and `log` work too.
        """
        return concept_path(bundle, concept_id).read_text(encoding="utf-8")

    @mcp.tool()
    def get_neighbors(concept_id: str) -> dict[str, Any]:
        """Bundle-internal links of a concept, both directions.

        Returns `outgoing` (concepts it links to or cites in `sources`) and
        `incoming` (concepts linking to it). External URLs are not neighbours.
        """
        target = concept_path(bundle, concept_id)
        cid = target.relative_to(bundle.resolve()).with_suffix("").as_posix()
        known = {}
        outgoing, incoming = set(), set()
        for other, p, meta, body in concepts(bundle):
            known[other] = meta
            links = {resolve(t, p, bundle)
                     for t in link_targets(body) + source_resources(meta)}
            links.discard(None)
            links.discard(other)
            if other == cid:
                outgoing = links
            elif cid in links:
                incoming.add(other)
        if cid not in known:
            return {"id": cid, "outgoing": [], "incoming": []}
        return {
            "id": cid,
            "outgoing": [card(t, known[t]) for t in sorted(outgoing) if t in known],
            "incoming": [card(t, known[t]) for t in sorted(incoming)],
        }

    return mcp


def main(argv: list[str]) -> None:
    # A missing bundle is not a startup failure: the plugin ships this server to
    # every project, most of which have no `.okf/` yet. Starting anyway keeps the
    # server list clean and turns the problem into a readable error on first use.
    raw = argv[1] if len(argv) > 1 else os.environ.get("OKF_BUNDLE", ".okf")
    build(Path(raw).expanduser()).run()


if __name__ == "__main__":
    main(sys.argv)
