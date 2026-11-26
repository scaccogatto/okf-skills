#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["mcp>=2,<3", "pyyaml>=6,<7"]
# ///
"""Read-only MCP server over an Open Knowledge Format (OKF) bundle.

Three tools, the shape every other OKF toolkit converged on:
`search_concepts`, `read_concept`, `get_neighbors`. Nothing writes.

For an agent that already has file tools this duplicates Grep and Read, which
is the whole reason the July 2026 map declined to build it. It ships anyway for
category parity, and the reasoning is recorded verbatim in
`.okf/decisions/mcp-server.md` rather than left to be rediscovered.

Consumer rules follow OKF v0.3: §3.2 discovery (typed frontmatter only), §6
resolution, §5.3 trust tiers from current events only, §5.4/§5.5 lifecycle. Each
card carries `tier`, `stale`, `current` and `superseded_by` so an agent can
discount stale or retired knowledge itself.

Bundle directory: first CLI argument, else `$OKF_BUNDLE`, else `./.okf`.

Run:  uv run servers/okf_mcp.py [bundle-dir]
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, NamedTuple

import yaml
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

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


SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*:")
DATE_ONLY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# §5.4: the vocabulary. `draft` is not yet reviewed but still current knowledge,
# `deprecated` and any value outside this set are not.
CURRENT_STATUS = {"draft", "stable"}


def as_list(v) -> list:
    """§11.2 rules 1-2: null, "" and [] are absent, one item is a list of one."""
    if v is None or v == "" or v == []:
        return []
    return v if isinstance(v, list) else [v]


def parse_instant(v) -> datetime | None:
    """§5 Timestamps as an aware UTC instant, None when invalid. A date-only value
    is the start of that day in UTC, a date-time without an offset is invalid.
    PyYAML hands over date/datetime objects or strings, so all of them are accepted."""
    if isinstance(v, datetime):
        return v.astimezone(UTC) if v.tzinfo else None
    if isinstance(v, date):
        return datetime(v.year, v.month, v.day, tzinfo=UTC)
    if not isinstance(v, str):
        return None
    s = v.strip()
    if DATE_ONLY.match(s):
        s += "T00:00:00+00:00"
    try:
        t = datetime.fromisoformat(s)  # 3.11 takes `Z` and the space separator
    except ValueError:
        return None
    return t.astimezone(UTC) if t.tzinfo else None


def trust(meta: dict) -> tuple[str, list[dict]]:
    """§5.3 trust tier plus every well-formed verification event, each flagged
    `current`. Only current events count, so an agent rewrite after a human review
    drops the tier back down. A v0.1 `timestamp` stands in for `generated.at`
    (Appendix B)."""
    gen = meta.get("generated")
    raw = gen.get("at") if isinstance(gen, dict) else meta.get("timestamp")
    floor = parse_instant(raw) if raw not in (None, "") else None
    events = []
    for e in as_list(meta.get("verified")):
        # §5.2: an event without both `by` and `at` is ignored.
        if not isinstance(e, dict) or not e.get("by") or e.get("at") in (None, ""):
            continue
        t = parse_instant(e["at"])
        if t is None:
            current = False  # unparseable cannot be shown to postdate the change
        elif raw in (None, ""):
            current = True
        else:  # a malformed generated.at leaves nothing provably current
            current = floor is not None and t >= floor
        events.append({"by": str(e["by"]), "at": str(e["at"]), "current": current})
    live = [e["by"] for e in events if e["current"]]
    if not live:
        return "unverified", events
    # `team:` and every other prefix is non-human: only `human:` earns the top tier
    return ("human-reviewed" if any(b.startswith("human:") for b in live)
            else "machine-confirmed"), events


def staleness(meta: dict, now: datetime | None = None) -> str:
    """§5.5: "" (no `stale_after`), "fresh", "stale", or "malformed". A value that
    cannot be parsed is never fresh (§11.2)."""
    raw = meta.get("stale_after")
    if raw is None or raw == "" or raw == []:
        return ""
    t = parse_instant(raw)
    if t is None:
        return "malformed"
    return "stale" if (now or datetime.now(UTC)) >= t else "fresh"


def lifecycle(meta: dict) -> tuple[str, bool]:
    """§5.4: (status, is_current). Absent means stable, an unknown value keeps
    its raw text and is not current."""
    status = str(meta.get("status") or "").strip() or "stable"
    return status, status in CURRENT_STATUS


def has_type(meta: dict) -> bool:
    """§3.2 rule 1: a concept has a non-empty `type`."""
    t = meta.get("type")
    return t is not None and bool(str(t).strip())


def declares_legacy(bundle: Path) -> bool:
    """§12.1: the root index declares okf_version 0.2 or earlier, or none."""
    try:
        raw = (bundle / "index.md").read_text(encoding="utf-8").lstrip("﻿")
    except (UnicodeDecodeError, OSError):
        return True
    ver = split_frontmatter(raw)[0].get("okf_version")
    if ver is None or ver == "":
        return True
    try:
        return tuple(int(x) for x in str(ver).split(".")[:2]) <= (0, 2)
    except ValueError:
        return False  # a version we cannot read gets the current rules


def path_fields(meta: dict) -> list[str]:
    """§6.2 path fields that can point at a concept (§6.4 graph edges)."""
    vals = [meta.get("superseded_by"), meta.get("computation")]
    for key in ("executor", "attester"):
        sub = meta.get(key)
        vals.append(sub.get("resource") if isinstance(sub, dict) else None)
    vals += [e.get("resource") for e in as_list(meta.get("sources"))
             if isinstance(e, dict)]
    return [str(v).strip() for v in vals if v is not None and str(v).strip()]


def resolve(target: str, path: Path, bundle: Path, ids: set[str] | None = None,
            legacy: bool = False) -> str | None:
    """§6 resolution of a link or path-field value to a bundle-relative id, or None
    when it is external, an asset or outside the root. Membership in the concept
    set is the caller's check, except for the `legacy` fallback (§6.2, §12.1),
    which only path fields use: a bare value that is not a concept from the file's
    directory is retried from the bundle root."""
    t = urllib.parse.unquote(str(target).split("#", 1)[0])
    if not t.endswith(".md") or SCHEME.match(t):
        return None
    root = bundle.resolve()

    def at(base: Path) -> str | None:
        cand = (base / t.lstrip("/")).resolve()
        return cand.relative_to(root).as_posix()[:-3] if cand.is_relative_to(root) else None

    if t.startswith("/"):
        return at(root)
    found = at(path.parent)
    if legacy and ids is not None and found not in ids:
        alt = at(root)
        return alt if alt in ids else found
    return found


def discover(bundle: Path, on_unreadable=None):
    """§3.2: yield (id, path, meta, body) for every concept. Skips reserved files,
    anything with a dot-prefixed component below the root (the root itself may be
    `.okf`), files without a typed frontmatter, and symlinks leaving the root."""
    root = bundle.resolve()
    for p in sorted(bundle.rglob("*.md")):
        if (p.name in RESERVED or not p.is_file()
                or any(part.startswith(".") for part in p.relative_to(bundle).parts)
                or not p.resolve().is_relative_to(root)):
            continue
        try:
            raw = p.read_text(encoding="utf-8").lstrip("﻿")
        except (UnicodeDecodeError, OSError) as exc:
            if on_unreadable:
                on_unreadable(p, exc)
            continue
        meta, body = split_frontmatter(raw)
        if has_type(meta):
            yield p.relative_to(bundle).with_suffix("").as_posix(), p, meta, body


class Snapshot(NamedTuple):
    """One read of the bundle: everything a tool needs to resolve links and build
    cards without touching the disk twice."""
    bundle: Path
    items: list  # (id, path, meta, body)
    ids: set
    legacy: bool


# ponytail: the bundle is re-read from disk on every call. Correct on a bundle
# edited mid-session, and fine up to a few thousand concepts; cache on mtime if
# a bundle ever gets big enough to notice.
def snapshot(bundle: Path) -> Snapshot:
    if not bundle.is_dir():
        raise ToolError(f"no OKF bundle at {bundle}; set OKF_BUNDLE to one")
    items = list(discover(bundle))
    return Snapshot(bundle, items, {i[0] for i in items}, declares_legacy(bundle))


def edges(snap: Snapshot, path: Path, meta: dict, body: str) -> set[str]:
    """§6.4: concepts this one links to (body) or points at (path fields)."""
    found = {resolve(t, path, snap.bundle) for t in link_targets(body)}
    found |= {resolve(t, path, snap.bundle, snap.ids, snap.legacy)
              for t in path_fields(meta)}
    return found & snap.ids


def card(cid: str, path: Path, meta: dict, snap: Snapshot) -> dict:
    tier, _events = trust(meta)
    status, current = lifecycle(meta)
    sup = str(meta.get("superseded_by") or "").strip()
    target = resolve(sup, path, snap.bundle, snap.ids, snap.legacy) if sup else None
    return {
        "id": cid,
        "type": str(meta["type"]).strip(),
        "title": str(meta.get("title", cid.rsplit("/", 1)[-1])),
        "description": str(meta.get("description", "")),
        "status": status,
        # §5.4: false for deprecated and for values outside the vocabulary
        "current": current,
        # §5.4: the replacement's id when it resolves to a concept, else raw
        "superseded_by": target if target in snap.ids else sup,
        "tier": tier,
        "stale_after": str(meta.get("stale_after") or ""),
        # "" | "fresh" | "stale" | "malformed" (§5.5)
        "stale": staleness(meta),
    }


def concept_path(bundle: Path, concept_id: str) -> Path:
    """Bundle-relative id -> file path, refusing anything outside the bundle."""
    # Checked first: without it, a project with no bundle at all reports every id
    # as a missing concept, which points at the wrong problem.
    if not bundle.is_dir():
        raise ToolError(f"no OKF bundle at {bundle}; set OKF_BUNDLE to one")
    root = bundle.resolve()
    p = (root / f"{concept_id.strip().lstrip('/')}.md").resolve()
    if not p.is_relative_to(root) or not p.is_file():
        raise ToolError(f"no such concept: {concept_id}")
    return p


def plugin_version() -> str:
    """The version the plugin manifest declares, read rather than restated: a
    second copy of it here is one more thing to forget on a release."""
    manifest = Path(__file__).resolve().parents[1] / ".claude-plugin" / "plugin.json"
    try:
        return str(json.loads(manifest.read_text(encoding="utf-8"))["version"])
    except (OSError, ValueError, KeyError):
        return ""  # running from outside the plugin tree is not an error


def build(bundle: Path) -> MCPServer:
    mcp = MCPServer("okf", version=plugin_version())

    @mcp.tool()
    def search_concepts(query: str, limit: int = 20) -> list[dict]:
        """Find concepts in the bundle whose metadata or body matches `query`.

        Case-insensitive substring match over title, description, tags, id and
        body. Matches in metadata rank above matches in the body only. Deprecated
        concepts and unknown statuses are still returned, with `current: false`.
        """
        q = query.strip().lower()
        if not q:
            raise ToolError("query must not be empty")
        snap = snapshot(bundle)
        hits = []
        for cid, path, meta, body in snap.items:
            c = card(cid, path, meta, snap)
            # §11.2: a scalar `tags` is one tag, never split at commas
            tags = " ".join(str(t) for t in as_list(meta.get("tags")))
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

        Returns `outgoing` (concepts it links to, or points at
        through `sources`, `superseded_by` and the other path fields) and
        `incoming` (concepts linking to it). External URLs are not neighbours.
        """
        target = concept_path(bundle, concept_id)
        cid = target.relative_to(bundle.resolve()).with_suffix("").as_posix()
        snap = snapshot(bundle)
        by_id = {i[0]: i for i in snap.items}
        if cid not in by_id:  # reserved file or not a concept (§3.2)
            return {"id": cid, "outgoing": [], "incoming": []}
        graph = {other: edges(snap, p, meta, body) - {other}
                 for other, p, meta, body in snap.items}
        pick = lambda ids: [card(t, by_id[t][1], by_id[t][2], snap) for t in sorted(ids)]
        return {
            "id": cid,
            "outgoing": pick(graph[cid]),
            "incoming": pick(o for o, out in graph.items() if cid in out),
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
