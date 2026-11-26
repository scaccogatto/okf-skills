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
# --- shared OKF consumer rules: keep identical in servers/okf_mcp.py and skills/visualize/scripts/okf_visualize.py ---
# §6.1: links are read from the body with code removed first. A fence is a run of
# 3+ backticks or tildes indented at most 3 spaces, closed by a run of the same
# character at least as long, so a shorter fence inside it is content. Same rules
# as okf_validate.strip_code: the three tools must see the same links.
FENCE_RUN = re.compile(r"^ {0,3}(`{3,}|~{3,})")
CODE_SPAN = re.compile(r"(?<!`)(`+)(?!`)((?:(?!\n[ \t]*\n).)+?)(?<!`)\1(?!`)", re.DOTALL)
LINK = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
# §6.1: a link reference definition is a link too. A `[^label]:` line is a
# footnote definition, not a link.
REF_DEF = re.compile(r"^ {0,3}\[([^\]]+)\]:[ \t]*<?([^\s>]+)>?")
SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*:")
# §5 Timestamps: a full-date, or an RFC 3339 date-time that carries an offset.
DATE_ONLY = re.compile(r"\d{4}-\d{2}-\d{2}")
DATE_TIME = re.compile(r"\d{4}-\d{2}-\d{2}[Tt ](?:[01]\d|2[0-3]):\d{2}:\d{2}(\.\d+)?([Zz]|[+-]\d{2}:\d{2})")
VERSION = re.compile(r"([0-9]+)\.([0-9]+)(\..*)?")
# §5.4: the vocabulary. `draft` is not yet reviewed but still current knowledge,
# `deprecated` and any value outside this set are not.
STATUS_VALUES = {"draft", "stable", "deprecated"}
CURRENT_STATUS = {"draft", "stable"}


class UniqueKeyLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate mapping keys at every level (§4, YAML 1.2).
    PyYAML would keep the last value, so a strict reader and this one would see
    different frontmatter."""

    def construct_mapping(self, node, deep=False):
        if isinstance(node, yaml.MappingNode):
            seen = set()
            for key_node, _ in node.value:
                if key_node.tag == "tag:yaml.org,2002:merge":
                    continue  # `<<` is expanded by the parent class, not a real key
                key = self.construct_object(key_node, deep=True)
                try:
                    duplicate = key in seen
                    seen.add(key)
                except TypeError:
                    break  # unhashable key: the parent class reports it
                if duplicate:
                    raise yaml.constructor.ConstructorError(
                        None, None, "duplicate key", key_node.start_mark)
        return super().construct_mapping(node, deep=deep)


def split_frontmatter(text: str):
    """§4: (meta, body), meta None when there is no frontmatter or it is invalid.

    Both delimiters sit at column 0, so an indented `---` inside a block scalar
    does not close the block (#66). An impossible date or a huge int (ValueError,
    #63), runaway nesting (RecursionError), a duplicate key or a non-mapping make
    the file a non-concept here, never a crash. An empty block is an empty mapping."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip() != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            try:
                meta = yaml.load("".join(lines[1:i]), Loader=UniqueKeyLoader)
            except (yaml.YAMLError, ValueError, RecursionError):
                return None, "".join(lines[i + 1:])
            if meta is None:
                meta = {}
            return (meta if isinstance(meta, dict) else None), "".join(lines[i + 1:])
    return None, text


def scalar_text(v) -> str:
    """The text of a scalar, "" for anything else. Never str() a frontmatter list or
    mapping: an alias bomb expands only when it is stringified or serialized."""
    # bool is an int and datetime is a date, so both are covered here
    return str(v) if isinstance(v, (str, int, float, date)) else ""


def shown(v) -> str:
    """scalar_text, with a placeholder for a container so it still shows as set."""
    if isinstance(v, list):
        return "<list>"
    if isinstance(v, dict):
        return "<mapping>"
    return scalar_text(v)


def strip_code(body: str) -> str:
    """The body with fenced blocks and inline code spans removed."""
    kept: list[str] = []
    fence = ""
    for line in body.splitlines():
        m = FENCE_RUN.match(line)
        if fence:
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) \
                    and not line[m.end():].strip():
                fence = ""
            continue
        if m and not (m.group(1)[0] == "`" and "`" in line[m.end():]):
            fence = m.group(1)
            continue
        kept.append(line)
    return CODE_SPAN.sub("", "\n".join(kept))


def link_targets(body: str) -> list[str]:
    """§6.1: inline link targets and reference definitions, code excluded."""
    out = []
    for line in strip_code(body).splitlines():
        out.extend(LINK.findall(line))
        ref = REF_DEF.match(line)
        if ref and not ref.group(1).startswith("^"):
            out.append(ref.group(2))
    return out


def as_list(v) -> list:
    """§11.2 rules 1-2: null, "", [] and {} are absent, one item is a list of one."""
    if is_absent(v):
        return []
    return v if isinstance(v, list) else [v]


def tag_list(meta: dict) -> list[str]:
    """`tags` as text, scalar items only (a nested item has no tag text)."""
    return [t for t in map(scalar_text, as_list(meta.get("tags"))) if t]


def parse_instant(v) -> datetime | None:
    """§5 Timestamps as an aware UTC instant, None when invalid. A date-only value
    is the start of that day in UTC, a date-time needs an offset. PyYAML hands
    over date/datetime objects or strings, so all of them are accepted. The regex
    comes first: `fromisoformat` alone takes `+0000`, `+05` and a minute-only time."""
    try:
        if isinstance(v, datetime):
            return v.astimezone(UTC) if v.utcoffset() is not None else None
        if isinstance(v, date):
            return datetime(v.year, v.month, v.day, tzinfo=UTC)
        if not isinstance(v, str):
            return None
        if DATE_ONLY.fullmatch(v):
            d = date.fromisoformat(v)
            return datetime(d.year, d.month, d.day, tzinfo=UTC)
        if DATE_TIME.fullmatch(v):  # upper(): 3.11 rejects a lowercase `t` or `z`
            return datetime.fromisoformat(v.upper()).astimezone(UTC)
    # Feb 30 and hour 24 raise ValueError. `0001-01-01T00:00:00+05:00` parses but
    # names an instant before year 1 in UTC, so astimezone raises OverflowError.
    except (ValueError, OverflowError):
        pass
    return None


def is_absent(v) -> bool:
    """§11.2 rule 1: null, "", [] and {} read as an absent key."""
    return v is None or v == "" or v == [] or v == {}


def trust(meta: dict) -> tuple[str, list[dict]]:
    """§5.3 trust tier plus every verification event with `by` and `at`, each
    flagged `current`. Only current events count, so an agent rewrite after a
    human review drops the tier back down. A v0.1 `timestamp` stands in for
    `generated.at` only when `generated` is absent (Appendix B)."""
    gen = meta.get("generated")
    if is_absent(gen):
        raw = meta.get("timestamp")
    else:
        raw = gen.get("at") if isinstance(gen, dict) else None
    # §5.3 defines only the absent-`generated` case. A `generated` without `at`
    # records no change time, so no verification can be shown to predate it: every
    # valid event is current. A present but invalid `at` leaves none current.
    bounded = not is_absent(raw)
    floor = parse_instant(raw) if bounded else None
    events = []
    for e in as_list(meta.get("verified")):
        if not isinstance(e, dict):
            continue
        by, at = e.get("by"), e.get("at")
        # §5.2: an event without both `by` and `at` is ignored
        if not (isinstance(by, str) and by.strip()) or is_absent(at):
            continue
        t = parse_instant(at)
        current = t is not None and (not bounded or (floor is not None and t >= floor))
        events.append({"by": by, "at": shown(at), "current": current})
    live = [e["by"] for e in events if e["current"]]
    if not live:
        return "unverified", events
    # `team:` and every other prefix is non-human: only `human:` earns the top tier
    return ("human-reviewed" if any(b.startswith("human:") for b in live)
            else "machine-confirmed"), events


def lifecycle(meta: dict) -> tuple[str, bool]:
    """§5.4: (status, is_current). Absent, null or "" means stable. Only an exact
    vocabulary string counts: `false`, `0`, " stable " or "Stable" keep their raw
    text and are not current."""
    raw = meta.get("status")
    if is_absent(raw):
        return "stable", True
    if isinstance(raw, str) and raw in STATUS_VALUES:
        return raw, raw in CURRENT_STATUS
    return shown(raw), False


def has_type(meta: dict) -> bool:
    """§3.2 rule 1: a concept has a `type` that is a non-empty string."""
    t = meta.get("type")
    return isinstance(t, str) and bool(t.strip())


def declares_legacy(bundle: Path) -> bool:
    """§12.1: the root index declares okf_version 0.2 or earlier, or none."""
    try:
        raw = (bundle / "index.md").read_text(encoding="utf-8").lstrip("﻿")
    except (UnicodeDecodeError, OSError):
        return True
    ver = (split_frontmatter(raw)[0] or {}).get("okf_version")
    if ver is None or ver == "":
        return True
    m = VERSION.fullmatch(scalar_text(ver))
    # a version we cannot read gets the current rules
    return m is not None and (int(m[1]), int(m[2])) <= (0, 2)


def names_bundle_path(value: str, path: Path, bundle: Path, legacy: bool) -> bool:
    """Whether a `resource` / `sources[].resource` value is a bundle path. Both may
    be a scope descriptor or an opaque identifier instead (§4.1, §6.2), such as
    `proj.ds.users` or `all queries in project acme`. A path is rooted or
    dot-relative (`/`, `./`, `../`), or has no whitespace and names an existing
    FILE (a directory does not count) from the file's directory or, in a legacy
    bundle, from the root. Same predicate as okf_validate.names_bundle_path."""
    if value.startswith(("/", "./", "../")):
        return True
    if not value or any(ch.isspace() for ch in value):
        return False
    t = urllib.parse.unquote(value.split("#", 1)[0])
    root = bundle.resolve()

    def is_file(base: Path) -> bool:
        try:
            cand = (base / t).resolve()
        except (OSError, RuntimeError):  # a symlink loop
            return False
        return cand.is_relative_to(root) and cand.is_file()

    return bool(t) and (is_file(path.parent) or (legacy and is_file(root)))


def path_fields(meta: dict, path: Path, bundle: Path, legacy: bool) -> list[str]:
    """§6.2 path fields that can point at a concept (§6.4 graph edges). Only
    string values are paths, and an opaque `resource` / `sources[].resource`
    (names_bundle_path) is none."""
    resources = [meta.get("resource")]
    resources += [e.get("resource") for e in as_list(meta.get("sources"))
                  if isinstance(e, dict)]
    vals = [meta.get("superseded_by"), meta.get("computation")]
    for key in ("executor", "attester"):
        sub = meta.get(key)
        vals.append(sub.get("resource") if isinstance(sub, dict) else None)
    vals += [v for v in resources
             if isinstance(v, str) and names_bundle_path(v.strip(), path, bundle, legacy)]
    return [v.strip() for v in vals if isinstance(v, str) and v.strip()]


def resolve(target: str, path: Path, bundle: Path, legacy: bool = False) -> str | None:
    """§6 resolution of a link or path-field value to a bundle-relative id, or None
    when it is external, not markdown or outside the root. Membership in the
    concept set is the caller's check. `legacy` is the §6.2/§12.1 fallback, which
    only path fields use: a bare value naming no file from the file's directory is
    retried from the bundle root. Existence is any file or directory, concept or
    not, tested on the normalized path (`x/../b.md` needs no `x/`), as the
    validator does. An opaque `resource` never gets here (names_bundle_path)."""
    t = urllib.parse.unquote(target.split("#", 1)[0])
    if not t.endswith(".md") or SCHEME.match(t):
        return None
    root = bundle.resolve()

    def at(base: Path) -> str | None:
        try:
            cand = (base / t.lstrip("/")).resolve()
        except (OSError, RuntimeError):  # a symlink loop
            return None
        return cand.relative_to(root).as_posix()[:-3] if cand.is_relative_to(root) else None

    if t.startswith("/"):
        return at(root)
    local = at(path.parent)
    if legacy and local is not None and not (root / f"{local}.md").exists():
        return at(root)
    return local


def discover(bundle: Path, on_unreadable=None):
    """§3.2: yield (id, path, meta, body) for every concept. Skips reserved files,
    anything with a dot-prefixed component below the root (the root itself may be
    `.okf`), files without a valid, typed frontmatter, and symlinks leaving the root."""
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
        if meta is not None and has_type(meta):
            yield p.relative_to(bundle).with_suffix("").as_posix(), p, meta, body


# --- end shared OKF consumer rules ---


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


def staleness(meta: dict, now: datetime | None = None) -> str:
    """§5.5: "" (no `stale_after`), "fresh", "stale", or "malformed". A value that
    cannot be parsed is never fresh (§11.2)."""
    raw = meta.get("stale_after")
    if is_absent(raw):
        return ""
    t = parse_instant(raw)
    if t is None:
        return "malformed"
    return "stale" if (now or datetime.now(UTC)) >= t else "fresh"


def edges(snap: Snapshot, path: Path, meta: dict, body: str) -> set[str]:
    """§6.4: concepts this one links to (body) or points at (path fields)."""
    found = {resolve(t, path, snap.bundle) for t in link_targets(body)}
    found |= {resolve(t, path, snap.bundle, snap.legacy)
              for t in path_fields(meta, path, snap.bundle, snap.legacy)}
    return found & snap.ids


def card(cid: str, path: Path, meta: dict, snap: Snapshot) -> dict:
    tier, _events = trust(meta)
    status, current = lifecycle(meta)
    raw_sup, title = meta.get("superseded_by"), meta.get("title")
    sup = raw_sup.strip() if isinstance(raw_sup, str) else "" if is_absent(raw_sup) else shown(raw_sup)
    target = resolve(sup, path, snap.bundle, snap.legacy) if isinstance(raw_sup, str) and sup else None
    return {
        "id": cid,
        "type": meta["type"].strip(),
        "title": cid.rsplit("/", 1)[-1] if title is None else shown(title),
        "description": shown(meta.get("description")),
        "status": status,
        # §5.4: false for deprecated and for values outside the vocabulary
        "current": current,
        # §5.4: the replacement's id when it resolves to a concept, else raw
        "superseded_by": target if target in snap.ids else sup,
        "tier": tier,
        "stale_after": shown(meta.get("stale_after")),
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
            tags = " ".join(tag_list(meta))
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
