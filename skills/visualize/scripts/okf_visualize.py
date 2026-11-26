#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6,<7"]
# ///
"""Render an Open Knowledge Format (OKF) bundle as a single self-contained,
interactive HTML graph (`viz.html`). No backend, no install on the viewing side,
no data leaves the page — concepts become nodes (coloured by `type`, sized by
body length), markdown links and bundle-internal `sources` become edges, and
clicking a node opens a wiki-style panel with its rendered markdown, OKF v0.3
provenance/trust/lifecycle metadata, outgoing links, and "Cited by" backlinks.

Features: force/concentric/breadth-first/circle/grid layouts, per-type filter,
free-text search, neighbour highlight, clickable cross-links and backlinks.

The default layout is force (cose) up to AUTO_COSE_MAX concepts, then the linear
concentric layout — force-directed cost grows roughly quadratically with node
count and freezes the page on large bundles. An explicit --layout always wins.

Run:  uv run okf_visualize.py <bundle-dir> [-o viz.html]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
from datetime import UTC, date, datetime
from pathlib import Path

import yaml

RESERVED = {"index.md", "log.md"}
# Force (cose) layout froze the page for ~32 s at ~2k concepts (measured in
# Chrome); the linear layouts load the same bundle in under 2 s. Past this size
# the default switches to concentric, and the in-page layout picker asks before
# running force. An explicit --layout (or ?layout=) still wins.
AUTO_COSE_MAX = 1000
# Above this the page is slow on any layout (23k concepts measured: ~27 s load,
# ~650 MB heap) and reads as a hairball — warn and suggest rendering a subtree.
SCALE_WARN = 5000


def json_for_script(obj) -> str:
    """JSON-encode ``obj`` for safe embedding inside an inline ``<script>``.

    The HTML tokenizer knows nothing about JS string context: a literal
    ``</script>`` in a concept body ends the inline script early (truncating the
    embedded ``NODES``/``EDGES`` and breaking the whole page), and ``<!--`` can
    shift it into the escaped script-data states where even the template's real
    closing tag stops working. Escaping every ``<`` as ``\\u003c`` neutralizes
    ``</script>``, ``<!--`` and ``<script`` in one stroke, and the result stays
    valid JSON *and* JavaScript (``json.dumps`` keeps everything else ASCII via
    the default ``ensure_ascii=True``).
    """
    return json.dumps(obj, default=str).replace("<", "\\u003c")


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
DATE_TIME = re.compile(r"\d{4}-\d{2}-\d{2}[Tt ]\d{2}:\d{2}:\d{2}(\.\d+)?([Zz]|[+-]\d{2}:\d{2})")
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


def stale_at(meta: dict) -> str:
    """§5.5 `stale_after` for the page: "" when absent, "malformed" when invalid
    (never fresh, §11.2), else the instant as a UTC ISO string. Fresh or stale is
    decided in the browser at view time: a page rendered once and opened later
    must not show a frozen verdict."""
    raw = meta.get("stale_after")
    if is_absent(raw):
        return ""
    t = parse_instant(raw)
    return t.isoformat(timespec="milliseconds").replace("+00:00", "Z") if t else "malformed"


def read_sources(meta: dict, path: Path, bundle: Path, ids: set[str], legacy: bool):
    """§5.1 `sources`, flattened for display. `cid` is set when the source is
    itself a concept in this bundle, and that derivation is a real graph edge."""
    out = []
    for src in as_list(meta.get("sources")):  # §11.2: a bare mapping is one item
        if not isinstance(src, dict):
            continue
        raw = src.get("resource")
        resource = raw.strip() if isinstance(raw, str) else ""
        # §5.1: an entry's own `usage_window` overrides the one written once as a
        # sibling of `sources`. A count without its window has no units.
        window = src.get("usage_window", meta.get("usage_window"))
        # an opaque descriptor (names_bundle_path) is shown, never linked
        cid = (resolve(resource, path, bundle, legacy)
               if resource and names_bundle_path(resource, path, bundle, legacy) else None)
        count = src.get("usage_count")
        out.append({
            "title": shown(src.get("title")) or shown(src.get("id")) or resource,
            "resource": resource,
            "cid": cid if cid in ids else None,
            "author": shown(src.get("author")),
            "usage_count": None if count is None else shown(count),
            "usage_window": (f"{shown(window.get('from')) or '?'}→{shown(window.get('to')) or '?'}"
                             if isinstance(window, dict) else ""),
            "last_modified": shown(src.get("last_modified")),
        })
    return out


def read_generated(meta: dict):
    """§5.2 `generated`, falling back to a v0.1 `timestamp` only when `generated`
    is absent (Appendix B), the same rule `trust` applies."""
    gen = meta.get("generated")
    if isinstance(gen, dict):
        return {"by": shown(gen.get("by")), "at": shown(gen.get("at"))}
    if is_absent(gen) and not is_absent(meta.get("timestamp")):
        return {"by": "", "at": shown(meta["timestamp"])}
    return None


def build(bundle: Path):
    nodes, edges, seen = [], [], set()
    warn = lambda p, exc: print(
        f"warning: skipping {p.relative_to(bundle)}: cannot read file: {exc}", file=sys.stderr)
    items = list(discover(bundle, warn))
    ids = {i[0] for i in items}
    legacy = declares_legacy(bundle)
    for cid, p, meta, raw_body in items:
        body = raw_body.strip()
        tier, events = trust(meta)
        status, current = lifecycle(meta)
        raw_sup, title, raw_status = meta.get("superseded_by"), meta.get("title"), meta.get("status")
        sup = raw_sup.strip() if isinstance(raw_sup, str) else "" if is_absent(raw_sup) else shown(raw_sup)
        sup_cid = resolve(sup, p, bundle, legacy) if isinstance(raw_sup, str) and sup else None
        sources = read_sources(meta, p, bundle, ids, legacy)
        nodes.append({
            "id": cid,
            "type": meta["type"].strip(),
            "title": p.stem if title is None else shown(title),
            "description": shown(meta.get("description")),
            "tags": tag_list(meta),
            "group": cid.split("/")[0] if "/" in cid else "(root)",
            "sz": max(24, min(70, 24 + len(body) // 200)),
            # §5.4: only a status that is written is shown, `state` carries the
            # judgement: "" (draft/stable/absent), "deprecated" or "unknown"
            "status": "" if is_absent(raw_status) else status,
            "state": ("" if current else "deprecated" if status == "deprecated" else "unknown"),
            "superseded_by": sup,
            "superseded_cid": sup_cid if sup_cid in ids else None,
            "stale_after": shown(meta.get("stale_after")),
            # §5.5: "" | "malformed" | UTC ISO instant, compared with now in the page
            "stale_at": stale_at(meta),
            # §5.3: the tier and the events, each flagged `current`
            "tier": tier,
            "generated": read_generated(meta),
            "verified": events,
            "sources": sources,
            "body": body[:8000],
        })
        # §6.4: body links, then path fields (with the v0.2 root fallback, §6.2)
        targets = [resolve(t, p, bundle) for t in link_targets(body)]
        targets += [resolve(t, p, bundle, legacy) for t in path_fields(meta, p, bundle, legacy)]
        for tgt in targets:
            if tgt and tgt in ids and tgt != cid and (cid, tgt) not in seen:
                seen.add((cid, tgt))
                edges.append({"source": cid, "target": tgt})
    return nodes, edges


HTML = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>OKF — __NAME__</title>
<meta property="og:title" content="__OGTITLE__">
<meta property="og:description" content="__OGDESC__">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">
__OGIMAGE__
<script src="https://cdn.jsdelivr.net/npm/cytoscape@3.30.2/dist/cytoscape.min.js" integrity="sha384-IWROdLKRsN1UuJywMlWl7/blXQ8GEooN2n7dzTxfEPd7ybYIKCUJ2Ol/1Gpf3YV4" crossorigin="anonymous"></script>
<script src="https://cdn.jsdelivr.net/npm/marked@14.1.4/marked.min.js" integrity="sha384-lqPzN0kmFw9t2syAMwVPM4VbAyqsz/lPyYWbb2Xt6nSPM0WPNrpSWCUBgdcAdgnC" crossorigin="anonymous"></script>
<script src="https://cdn.jsdelivr.net/npm/dompurify@3.4.12/dist/purify.min.js" integrity="sha384-piCcpDdJ7qVeK4Tv8Z6Hpcr3ZBIgP16TxQTPVfsLFdZ5uDgwc3Y8Ho7oUnqf12qu" crossorigin="anonymous"></script>
<style>
 :root{--bg:#0e0f13;--panel:#16181f;--line:#262a35;--fg:#e6e8ee;--mut:#9aa3b2;--accent:#8ab4ff}
 *{box-sizing:border-box} html,body{margin:0;height:100%;background:var(--bg);color:var(--fg);
   font:14px/1.5 ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
 /* The row must be stated. Left implicit it sizes to `auto`, i.e. to the tallest
    item — a long concept body then stretched #side past the viewport and the page
    grew its own scrollbar on top of the panel's, which in turn forced a spurious
    horizontal one. Pinning the row to 100% keeps the panel scrolling inside. */
 #app{display:grid;grid-template-columns:minmax(0,1fr) 6px var(--side-w,400px);grid-template-rows:100%;height:100vh}
 #stage{position:relative;min-width:0;overflow:hidden}
 #cy{position:absolute;inset:0}
 #split{cursor:col-resize;background:var(--line);touch-action:none} #split:hover,#split.drag{background:var(--accent)}
 #side{background:var(--panel);overflow:auto;padding:18px}
 #top{position:absolute;top:0;left:0;right:0;z-index:5;display:flex;flex-wrap:wrap;align-items:flex-start;
   justify-content:space-between;gap:8px 16px;padding:12px 18px;pointer-events:none}
 header{padding-top:2px;min-width:0}
 h1{font-size:15px;margin:0;font-weight:650} .sub{color:var(--mut);font-size:12px;margin-top:2px}
 #bar{display:flex;flex-wrap:wrap;gap:8px;pointer-events:auto;min-width:0}
 #bar input,#bar select{background:var(--panel);border:1px solid var(--line);color:var(--fg);
   border-radius:8px;padding:8px 10px;outline:none;font-size:13px}
 #search{width:240px;max-width:100%}
 #legend{position:absolute;bottom:14px;left:18px;right:18px;z-index:5;display:flex;flex-wrap:wrap;gap:6px}
 .chip{display:flex;align-items:center;gap:6px;background:var(--panel);border:1px solid var(--line);
   border-radius:20px;padding:3px 10px;font-size:12px;color:var(--mut);cursor:pointer;user-select:none}
 .chip.off{opacity:.4} .dot{width:10px;height:10px;border-radius:50%}
 #side h2{font-size:17px;margin:.2em 0} .type{display:inline-block;border-radius:6px;padding:2px 8px;
   font-size:11px;font-weight:600;color:#0e0f13} .desc{color:var(--mut);margin:8px 0 12px}
 .tags{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px}
 .tag{background:#1d2230;border:1px solid var(--line);border-radius:6px;padding:1px 8px;font-size:11px;color:var(--mut)}
 .meta{margin:10px 0;font-size:12px;color:var(--mut)} .meta div{padding:1px 0} .meta b{color:var(--fg);font-weight:600}
 .sig{color:var(--mut)}
 .badges{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0}
 .badge{border-radius:6px;padding:2px 8px;font-size:11px;font-weight:600;border:1px solid}
 .t-unverified{color:#9aa3b2;border-color:#3a4150;background:#1d2230}
 .t-machine{color:#8ab4ff;border-color:#2b4570;background:#141c2b}
 .t-human{color:#4ade80;border-color:#276b45;background:#12211a}
 .b-stale{color:#fca5a5;border-color:#7f2b2b;background:#241416}
 .b-deprecated{color:#fbbf24;border-color:#7a5312;background:#241d10}
 .b-unknown{color:#9aa3b2;border-color:#3a4150;background:#1d2230}
 .rel{margin:10px 0} .rel h4{margin:0 0 4px;font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--mut)}
 .rel a{display:block;color:var(--accent);cursor:pointer;font-size:13px;padding:1px 0;text-decoration:none}
 .rel a:hover{text-decoration:underline}
 .body{border-top:1px solid var(--line);padding-top:12px;margin-top:12px} .body table{border-collapse:collapse;display:block;overflow:auto}
 .body td,.body th{border:1px solid var(--line);padding:4px 8px} .body code{background:#1d2230;padding:1px 5px;border-radius:4px}
 .body pre{background:#1d2230;padding:10px;border-radius:8px;overflow:auto} .body img{max-width:100%}
 .empty{color:var(--mut)} a{color:var(--accent)}
 .src{pointer-events:auto;color:var(--accent);margin-left:10px;text-decoration:none} .src:hover{text-decoration:underline}
</style></head><body>
<div id="app"><div id="stage"><div id="cy"></div>
<div id="top"><header><h1>__NAME__</h1><div class="sub">__N__ concepts · __E__ links · OKF v0.3__LINK__</div></header>
<div id="bar">
 <input id="search" placeholder="search concepts…">
 <select id="type"><option value="">all types</option></select>
 <select id="layout">
  <option value="cose">force</option><option value="concentric">concentric</option>
  <option value="breadthfirst">breadth-first</option><option value="circle">circle</option><option value="grid">grid</option>
 </select>
</div></div>
<div id="legend"></div></div>
<div id="split" role="separator" aria-orientation="vertical" title="drag to resize · double-click to reset"></div><div id="side"><p class="empty">Click a concept to inspect it.</p></div></div>
<script>
const NODES=__NODES__, EDGES=__EDGES__;
const PALETTE=["#6E56CF","#D97757","#22C55E","#3B82F6","#EAB308","#EC4899","#14B8A6","#F97316","#A855F7","#0EA5E9","#84CC16","#EF4444","#64748B"];
const byId=Object.fromEntries(NODES.map(n=>[n.id,n]));
const outL={}, inL={};
NODES.forEach(n=>{outL[n.id]=[];inL[n.id]=[];});
EDGES.forEach(e=>{outL[e.source].push(e.target);inL[e.target].push(e.source);});
const types=[...new Set(NODES.map(n=>n.type))].sort();
const color=Object.fromEntries(types.map((t,i)=>[t,PALETTE[i%PALETTE.length]]));
const off=new Set();
const cy=cytoscape({container:document.getElementById('cy'),minZoom:.2,maxZoom:1.6,wheelSensitivity:.2,
 elements:[...NODES.map(n=>({data:{...n,c:color[n.type]}})),...EDGES.map(e=>({data:e}))],
 style:[
  {selector:'node',style:{'background-color':'data(c)','label':'data(title)','color':'#e6e8ee',
   'font-size':10,'text-wrap':'wrap','text-max-width':120,'text-valign':'bottom','text-margin-y':4,
   'text-outline-width':2,'text-outline-color':'#0e0f13','min-zoomed-font-size':6,
   'width':'data(sz)','height':'data(sz)'}},
  {selector:'edge',style:{'width':1.2,'line-color':'#3a4150','target-arrow-color':'#3a4150',
   'target-arrow-shape':'triangle','arrow-scale':.8,'curve-style':'bezier','opacity':.7}},
  {selector:'.dim',style:{'opacity':.10}},{selector:'.hl',style:{'border-width':3,'border-color':'#fff'}}
 ],
 layout:{name:'__LAYOUT__',animate:false,nodeRepulsion:9000,idealEdgeLength:90,padding:40}});
const side=document.getElementById('side');
const app=document.getElementById('app'),split=document.getElementById('split'),SIDE_KEY='okf-viz-side-w';
let sideW=null,dragFrom=null,relayoutT;
function setSideW(w){sideW=w==null?null:Math.round(Math.max(240,Math.min(w,innerWidth-240)));
 if(sideW==null)app.style.removeProperty('--side-w');else app.style.setProperty('--side-w',sideW+'px');cy.resize();}
function relayout(){clearTimeout(relayoutT);relayoutT=setTimeout(()=>
 cy.layout({name:curLayout,animate:true,padding:40,nodeRepulsion:9000,idealEdgeLength:90}).run(),150);}
try{const w=+localStorage.getItem(SIDE_KEY);if(w){setSideW(w);relayout();}}catch(e){}
split.onpointerdown=e=>{e.preventDefault();split.setPointerCapture(e.pointerId);split.classList.add('drag');dragFrom=sideW;};
split.onpointermove=e=>{if(split.hasPointerCapture(e.pointerId))setSideW(innerWidth-e.clientX-3);};
split.onpointerup=split.onpointercancel=()=>{split.classList.remove('drag');
 if(sideW!==dragFrom)relayout();
 try{if(sideW!=null)localStorage.setItem(SIDE_KEY,sideW);}catch(e){}};
split.ondblclick=()=>{setSideW(null);relayout();try{localStorage.removeItem(SIDE_KEY);}catch(e){}};
addEventListener('resize',()=>{if(sideW!=null)setSideW(sideW);else cy.resize();relayout();});
const esc=s=>(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function relList(title,arr){if(!arr.length)return'';
 return `<div class="rel"><h4>${title}</h4>${arr.map(id=>`<a data-go="${esc(id)}">${esc((byId[id]||{}).title||id)}</a>`).join('')}</div>`;}
// §5.3: the tier is derived in Python at build time (current events only).
// §5.5: staleness is decided here, at view time, against the UTC instant Python
// normalized: a page opened long after it was rendered must not show a frozen
// "fresh". Advisory signals, not access control.
const TIER_CLS={'unverified':'t-unverified','machine-confirmed':'t-machine','human-reviewed':'t-human'};
const staleOf=n=>!n.stale_at?'':n.stale_at==='malformed'?'malformed':Date.now()>=Date.parse(n.stale_at)?'stale':'fresh';
function badges(n){const out=[`<span class="badge ${TIER_CLS[n.tier]||'t-unverified'}">${esc(n.tier)}</span>`],st=staleOf(n);
 if(st==='stale')out.push(`<span class="badge b-stale">stale since ${esc(n.stale_after)}</span>`);
 if(st==='malformed')out.push(`<span class="badge b-stale">stale_after malformed: ${esc(n.stale_after)}</span>`);
 if(n.state==='deprecated')out.push('<span class="badge b-deprecated">deprecated</span>');
 if(n.state==='unknown')out.push(`<span class="badge b-unknown">status: ${esc(n.status)}</span>`);
 return `<div class="badges">${out.join('')}</div>`;}
// OKF v0.3 trust (§5.2) + lifecycle (§5.4/§5.5). A v0.1 `timestamp` arrives here
// as generated.at with an empty `by`, so legacy bundles still show a date. An event
// older than generated.at stays listed as history, never counted in the tier (§5.3).
function metaBlock(n){const g=n.generated||{},rows=[];
 if(n.status)rows.push(`<div>status <b>${esc(n.status)}</b></div>`);
 if(g.at||g.by)rows.push(`<div>generated${g.at?` <b>${esc(g.at)}</b>`:''}${g.by?` by ${esc(g.by)}`:''}</div>`);
 (n.verified||[]).forEach(v=>rows.push(`<div>verified${v.at?` <b>${esc(v.at)}</b>`:''}${v.by?` by ${esc(v.by)}`:''}${v.current?'':' <span class="sig">(verified before the last change)</span>'}</div>`));
 if(n.stale_after)rows.push(`<div>stale after <b>${esc(n.stale_after)}</b></div>`);
 return rows.length?`<div class="meta">${rows.join('')}</div>`:'';}
// Provenance (§5.1). A source may be another concept (graph link), an external
// URL, or a scope descriptor that is not followable at all.
function srcList(n){const s=n.sources||[];if(!s.length)return'';
 return `<div class="rel"><h4>Sources</h4>${s.map(x=>{
  const used=x.usage_count!=null?`used ${x.usage_count}×${x.usage_window?` (${x.usage_window})`:''}`:'';
  const sig=[x.author,used,x.last_modified].filter(Boolean).join(' · ');
  const label=esc(x.title||x.resource)+(sig?` <span class="sig">(${esc(sig)})</span>`:'');
  if(x.cid&&byId[x.cid])return `<a data-go="${esc(x.cid)}">${label}</a>`;
  if(/^https?:\/\//i.test(x.resource))return `<a href="${esc(x.resource)}" target="_blank" rel="noopener">${label}</a>`;
  return `<span class="empty">${label}</span>`;}).join('')}</div>`;}
// Resolve an in-body markdown link href to a concept id, mirroring resolve() (§6):
// strip #fragment, percent-decode, a URI scheme is external, a leading / starts at
// the bundle root, anything else at the current concept's dir. Null when it is not
// a concept (or leaves the root).
function resolveHref(cid,href){let t=(href||'').split('#')[0];
 try{t=decodeURIComponent(t);}catch(e){return null;}
 if(/^[a-z][a-z0-9+.-]*:/i.test(t)||!t.endsWith('.md'))return null;
 const base=t[0]==='/'?[]:cid.split('/').slice(0,-1);
 for(const seg of t.slice(0,-3).split('/')){if(seg===''||seg==='.')continue;
  if(seg==='..'){if(!base.length)return null;base.pop();}else base.push(seg);}
 const tgt=base.join('/');
 return byId[tgt]?tgt:null;}
// §5.4 — a clickable link when the replacement resolves to a concept, else the raw
// value so a dangling pointer is still visible.
function supersededBy(n){if(!n.superseded_by)return'';
 return n.superseded_cid?relList('Superseded by',[n.superseded_cid])
  :`<div class="rel"><h4>Superseded by</h4><span class="empty">${esc(n.superseded_by)}</span></div>`;}
function show(id){const n=byId[id];if(!n)return;const c=color[n.type];
 side.innerHTML=`<span class="type" style="background:${c}">${esc(n.type)}</span>
 <h2>${esc(n.title)}</h2><div class="desc">${esc(n.description)||'<span class=empty>no description</span>'}</div>
 <div class="tags">${(n.tags||[]).map(t=>`<span class="tag">${esc(t)}</span>`).join('')}</div>
 ${badges(n)}${metaBlock(n)}${supersededBy(n)}${srcList(n)}${relList('Links to',outL[id])}${relList('Cited by',inL[id])}
 <div class="body">${n.body?DOMPurify.sanitize(marked.parse(n.body)):'<span class=empty>empty body</span>'}</div>`;
 side.querySelectorAll('[data-go]').forEach(a=>a.onclick=()=>select(a.getAttribute('data-go')));
 side.querySelectorAll('.body a[href]').forEach(a=>{const tgt=resolveHref(id,a.getAttribute('href'));
  if(tgt)a.onclick=e=>{e.preventDefault();select(tgt);};});}
function select(id){const ele=cy.getElementById(id);if(!ele.length)return;show(id);
 cy.elements().removeClass('hl').addClass('dim');const nb=ele.closedNeighborhood();nb.removeClass('dim');ele.addClass('hl');
 cy.animate({center:{eles:ele},duration:250});
 try{if(decodeURIComponent((location.hash||'').slice(1))!==id)location.hash=encodeURIComponent(id);}catch(e){}}
cy.on('tap','node',e=>select(e.target.id()));
cy.on('tap',e=>{if(e.target===cy)cy.elements().removeClass('dim hl');});
function applyFilter(){const q=document.getElementById('search').value.toLowerCase();const ty=document.getElementById('type').value;
 cy.batch(()=>cy.nodes().forEach(n=>{const d=n.data();
  const m=(!q||(d.title+' '+d.type+' '+d.description+' '+(d.tags||[]).join(' ')).toLowerCase().includes(q))
        &&(!ty||d.type===ty)&&!off.has(d.type);
  n.style('display',m?'element':'none');}));}
let debounce;
document.getElementById('search').oninput=()=>{clearTimeout(debounce);debounce=setTimeout(applyFilter,150);};
document.getElementById('type').oninput=applyFilter;
const tysel=document.getElementById('type');types.forEach(t=>{const o=document.createElement('option');o.value=t;o.textContent=t;tysel.appendChild(o);});
let curLayout='__LAYOUT__';
document.getElementById('layout').onchange=e=>{const v=e.target.value;
 if(v==='cose'&&NODES.length>__COSEMAX__&&!confirm(`force layout on ${NODES.length} concepts can freeze this tab — run anyway?`)){e.target.value=curLayout;return;}
 curLayout=v;cy.layout({name:v,animate:true,padding:40,nodeRepulsion:9000,idealEdgeLength:90}).run();};
document.getElementById('legend').innerHTML=types.map(t=>`<span class="chip" data-t="${esc(t)}"><span class="dot" style="background:${color[t]}"></span>${esc(t)} (${NODES.filter(n=>n.type===t).length})</span>`).join('');
document.querySelectorAll('#legend .chip').forEach(ch=>ch.onclick=()=>{const t=ch.getAttribute('data-t');
 if(off.has(t)){off.delete(t);ch.classList.remove('off');}else{off.add(t);ch.classList.add('off');}applyFilter();});
document.getElementById('layout').value='__LAYOUT__';
const Q=new URLSearchParams(location.search),QL=Q.get('layout'),QS=Q.get('select');
if(QL&&[...document.querySelectorAll('#layout option')].some(o=>o.value===QL)){document.getElementById('layout').value=QL;curLayout=QL;cy.layout({name:QL,animate:false,padding:40,nodeRepulsion:9000,idealEdgeLength:90}).run();}
function fromHash(){try{const h=decodeURIComponent((location.hash||'').slice(1));if(h&&byId[h])select(h);}catch(e){}}
addEventListener('hashchange',fromHash);
if(QS&&byId[QS])select(QS);else fromHash();
</script></body></html>"""


def render(bundle: Path, out: Path, title: str | None = None, link: str | None = None,
           layout: str | None = None, og_image: str | None = None,
           max_nodes: int | None = None):
    nodes, edges = build(bundle)
    if max_nodes is not None and len(nodes) > max_nodes:
        sys.exit(f"error: {len(nodes)} concepts exceeds --max-nodes {max_nodes}")
    if layout is None:
        layout = "cose" if len(nodes) <= AUTO_COSE_MAX else "concentric"
        if layout != "cose":
            print(f"note: {len(nodes)} concepts > {AUTO_COSE_MAX} — using the linear 'concentric' "
                  "layout (force freezes the page at this size; pass --layout cose to override)",
                  file=sys.stderr)
    if len(nodes) > SCALE_WARN:
        print(f"warning: {len(nodes)} concepts — the page will load slowly and read as a hairball; "
              f"consider rendering a subtree, e.g. okf_visualize.py {bundle}/<subdir>",
              file=sys.stderr)
    name = title or f"{bundle.resolve().parent.name}/{bundle.name}"
    src = f' <a class="src" href="{link}" target="_blank" rel="noopener">source ↗</a>' if link else ""
    aesc = lambda s: (s or "").replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
    og_title = aesc(f"OKF — {name}")
    og_desc = aesc(f"{len(nodes)} concepts · interactive Open Knowledge Format knowledge graph")
    og_img = (f'<meta property="og:image" content="{aesc(og_image)}">\n'
              f'<meta name="twitter:image" content="{aesc(og_image)}">') if og_image else ""
    subs = {"__NAME__": name, "__LINK__": src, "__LAYOUT__": layout,
            "__COSEMAX__": str(AUTO_COSE_MAX),
            "__OGTITLE__": og_title, "__OGDESC__": og_desc, "__OGIMAGE__": og_img,
            "__N__": str(len(nodes)), "__E__": str(len(edges)),
            "__NODES__": json_for_script(nodes), "__EDGES__": json_for_script(edges)}
    # One pass, longest marker first: substituted content (e.g. a concept body that
    # mentions "__EDGES__") must never itself be rescanned for other markers.
    marker = re.compile("|".join(sorted(map(re.escape, subs), key=len, reverse=True)))
    html = marker.sub(lambda m: subs[m.group(0)], HTML)
    out.write_text(html, encoding="utf-8")
    return len(nodes), len(edges)


def _force_utf8_stdio() -> None:
    """Reconfigure stdout/stderr to UTF-8 so status lines never crash on a
    cp1252 (default Windows) console. `errors="replace"` is a fallback."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


def main() -> int:
    _force_utf8_stdio()
    ap = argparse.ArgumentParser(description="Render an OKF bundle as a self-contained HTML graph.")
    ap.add_argument("bundle", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=None)
    ap.add_argument("-t", "--title", default=None, help="graph title (default: parent/bundle dir name)")
    ap.add_argument("-l", "--link", default=None, help="optional source URL shown in the header")
    ap.add_argument("--layout", default=None,
                    choices=["cose", "concentric", "breadthfirst", "circle", "grid"],
                    help=f"initial graph layout (default: cose, or concentric above {AUTO_COSE_MAX} "
                         "concepts — force layout freezes the page on large bundles)")
    ap.add_argument("--max-nodes", type=int, default=None,
                    help="refuse to render bundles with more concepts than this (useful in CI)")
    ap.add_argument("--og-image", default=None,
                    help="absolute URL for the social-preview image (og:image / twitter:image)")
    args = ap.parse_args()
    if not args.bundle.is_dir():
        print(f"error: {args.bundle} is not a directory", file=sys.stderr)
        return 2
    out = args.out or (args.bundle / "viz.html")
    n, e = render(args.bundle, out, title=args.title, link=args.link, layout=args.layout,
                  og_image=args.og_image, max_nodes=args.max_nodes)
    print(f"rendered {n} concepts, {e} links -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
