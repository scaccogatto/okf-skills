#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""Render an Open Knowledge Format (OKF) bundle as a single self-contained,
interactive HTML graph (`viz.html`). No backend, no install on the viewing side,
no data leaves the page — concepts become nodes (coloured by `type` or by any
producer-defined frontmatter field, sized by body length), markdown links and
bundle-internal `sources` become edges, and clicking a node opens a wiki-style
panel with its rendered markdown, OKF v0.2 provenance/trust/lifecycle metadata,
outgoing links, and "Cited by" backlinks.

Features: force/concentric/breadth-first/circle/grid layouts, per-type filter,
free-text search, neighbour highlight, clickable cross-links and backlinks.

Producer-defined frontmatter (§4.1) reaches the page, so a bundle can be coloured
and grouped by its own dimensions — owning team, tier, environment — and searched
by its own identifiers. `--derive-edge` turns a field that names another concept
into an edge, drawn dashed to keep an inference distinct from a written link.
`--vendor` inlines the runtime libraries so the file owes nothing to a network,
and `--report` prints bundle health: orphans, broken links, undefined footnote
references, stale concepts and drafts.

The default layout is force (cose) up to AUTO_COSE_MAX concepts, then the linear
concentric layout — force-directed cost grows roughly quadratically with node
count and freezes the page on large bundles. An explicit --layout always wins.

Run:  uv run okf_visualize.py <bundle-dir> [-o viz.html]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
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
# Bodies were capped at 8 000 characters, which silently dropped the tail of the
# longest concepts — and footnote definitions sit at the bottom, so exactly the
# documents that cite most lost every citation. Raised to a ceiling no real
# concept reaches; a bundle that does can lower it, and any cut now says so.
BODY_MAX = 200_000
FENCE = re.compile(r"^(```|~~~)")
LINK = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


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


def resolve(target: str, path: Path, bundle: Path):
    """Resolve a link/`sources[].resource` to a concept id, or None if it is not
    one (an external URL, an asset, a scope descriptor, an escape from the tree)."""
    t = str(target).split("#", 1)[0]
    if not t.endswith(".md"):
        return None
    if t.startswith("/"):
        return t.lstrip("/")[:-3]
    cand = (path.parent / t).resolve()
    return cand.relative_to(bundle.resolve()).as_posix()[:-3] \
        if cand.is_relative_to(bundle.resolve()) else None


FN_DEF = re.compile(r"^\[\^([^\]]+)\]:", re.M)
FN_REF = re.compile(r"\[\^([^\]]+)\](?!:)")


def undefined_footnotes(body: str):
    """Footnote references the document never defines.

    A bundle carries most of its provenance in footnotes, and a reference with no
    definition renders as bare `[^cluster]` in the middle of a sentence — a
    citation that silently isn't one. Frontmatter validators never see it,
    because it lives in the body.
    """
    defined = set(FN_DEF.findall(body))
    return sorted({ref for ref in FN_REF.findall(body) if ref not in defined})


def is_dangling(target: str, path: Path, bundle: Path) -> bool:
    """Whether an in-body link names a bundle file that is not there.

    Answered against the filesystem, not against the node list, because the two
    disagree in ways that would otherwise be reported as defects: `index.md` is
    a real file that is deliberately not a concept, and an external
    `https://…/notes.md` merely ends in `.md` while naming nothing local. Both
    resolve to a plausible-looking id, and neither is broken.
    """
    t = str(target).split("#", 1)[0]
    if "://" in t or not t.endswith(".md"):
        return False
    fs = (bundle / t.lstrip("/")) if t.startswith("/") else (path.parent / t)
    return not fs.exists()


def read_sources(meta: dict, path: Path, bundle: Path):
    """§5.1 `sources`, flattened for display. `cid` is set when the source is
    itself a concept in this bundle — that derivation is a real graph edge."""
    raw = meta.get("sources")
    out = []
    if not isinstance(raw, list):
        return out
    for src in raw:
        if not isinstance(src, dict):
            continue
        resource = str(src.get("resource", "")).strip()
        # §5.1 — an entry's own `usage_window` overrides the one written once as a
        # sibling of `sources`. A count without its window has no units.
        window = src.get("usage_window", meta.get("usage_window"))
        out.append({
            "title": str(src.get("title") or src.get("id") or resource),
            "resource": resource,
            "cid": resolve(resource, path, bundle) if resource else None,
            "author": str(src.get("author", "")),
            "usage_count": src.get("usage_count"),
            "usage_window": (f"{window.get('from', '?')}→{window.get('to', '?')}"
                             if isinstance(window, dict) else ""),
            "last_modified": str(src.get("last_modified") or ""),
        })
    return out


def read_trust(meta: dict):
    """§5.2 `generated` / `verified`, falling back to a v0.1 `timestamp` (§13.1)."""
    gen = meta.get("generated")
    if isinstance(gen, dict):
        generated = {"by": str(gen.get("by", "")), "at": str(gen.get("at", ""))}
    elif meta.get("timestamp"):
        generated = {"by": "", "at": str(meta["timestamp"])}
    else:
        generated = None
    ver = meta.get("verified")
    # a bare mapping is one verification event (§5.2)
    entries = [ver] if isinstance(ver, dict) else (ver if isinstance(ver, list) else [])
    verified = [{"by": str(e.get("by", "")), "at": str(e.get("at", ""))}
                for e in entries if isinstance(e, dict)]
    return generated, verified


# §4.1 reserves this top-level vocabulary. Everything else a document carries is
# an "other producer-defined key/value pair" — an extension namespace such as
# `acme:` or `wiki:`, which the spec tells consumers to preserve rather than
# reject. Those keys are the only place a bundle records its own dimensions
# (owning team, tier, environment), so a graph that drops them can only ever
# colour by `type`.
OKF_KEYS = frozenset({
    "type", "title", "description", "resource", "tags", "generated", "verified",
    "status", "stale_after", "sources", "usage_window", "runtime", "parameters",
    "computation", "executor", "attester",
})


def read_extensions(meta: dict):
    """Producer-defined frontmatter (§4.1), flattened to dotted scalar paths.

    A nested namespace (`acme: {owner_team: infra}`) becomes `acme.owner_team`, so
    every extension arrives as one flat attribute the viewer can group on
    without knowing any producer's schema in advance.

    Only scalars survive. A list or a deeper structure has no single value to
    colour a node by, and silently picking its first element would invent a fact
    the document never stated.
    """
    out = {}

    def walk(prefix: str, value):
        if isinstance(value, dict):
            for k, v in value.items():
                walk(f"{prefix}.{k}" if prefix else str(k), v)
        elif isinstance(value, bool):
            # YAML round-trips these as `true`/`false`; Python's repr would put
            # `True` in front of a reader who never wrote that.
            out[prefix] = "true" if value else "false"
        elif isinstance(value, (str, int, float)):
            out[prefix] = str(value)

    for key, value in meta.items():
        if key not in OKF_KEYS:
            walk(str(key), value)
    return out


LIBS = (
    ("cytoscape", "https://cdn.jsdelivr.net/npm/cytoscape@3.30.2/dist/cytoscape.min.js"),
    ("marked", "https://cdn.jsdelivr.net/npm/marked@14/marked.min.js"),
    ("dompurify", "https://cdn.jsdelivr.net/npm/dompurify@3.4.12/dist/purify.min.js"),
)
CDN_TAGS = (
    '<script src="https://cdn.jsdelivr.net/npm/cytoscape@3.30.2/dist/cytoscape.min.js"></script>\n'
    '<script src="https://cdn.jsdelivr.net/npm/marked@14/marked.min.js"></script>\n'
    '<script src="https://cdn.jsdelivr.net/npm/dompurify@3.4.12/dist/purify.min.js"'
    ' integrity="sha384-piCcpDdJ7qVeK4Tv8Z6Hpcr3ZBIgP16TxQTPVfsLFdZ5uDgwc3Y8Ho7oUnqf12qu"'
    ' crossorigin="anonymous"></script>'
)


def vendor_libs(cache_dir: Path) -> str:
    """Inline the three runtime libraries so the page owes nothing to a network.

    The default build calls itself self-contained while fetching three scripts
    from a CDN at open time. That page dies behind an air gap, dies under a
    content-security policy, and dies the day a version is unpublished. Inlining
    costs about 700 KB once and makes the file mean what it says.
    """
    import urllib.request

    cache_dir.mkdir(parents=True, exist_ok=True)
    out = []
    for name, url in LIBS:
        cached = cache_dir / f"{name}.js"
        if not cached.exists():
            print(f"fetching {name} …", file=sys.stderr)
            try:
                with urllib.request.urlopen(url, timeout=60) as resp:
                    cached.write_bytes(resp.read())
            except Exception as exc:  # noqa: BLE001 — surfaced, never swallowed
                sys.exit(f"error: --vendor could not fetch {name} from {url}: {exc}\n"
                         f"       place the file at {cached} manually and re-run.")
        source = cached.read_text(encoding="utf-8")
        # The tokenizer, not the JS parser, decides where a script ends: a bare
        # </script> inside a minified bundle would close this one early.
        out.append("<script>" + source.replace("</script>", "<\\/script>") + "</script>")
    return "\n".join(out)


def print_report(nodes, edges, audit) -> None:
    """Bundle health, on stderr so it never lands in a redirected HTML file."""
    written = [e for e in edges if e.get("origin") != "derived"]
    degree = {n["id"]: 0 for n in nodes}
    for edge in written:
        degree[edge["source"]] += 1
        degree[edge["target"]] += 1
    orphans = sorted(nid for nid, deg in degree.items() if deg == 0)
    today = _dt.date.today().isoformat()
    stale = sorted(n["id"] for n in nodes if n["stale_after"] and n["stale_after"] < today)
    draft = sorted(n["id"] for n in nodes if n["status"] == "draft")

    def block(title, items, note=""):
        print(f"\n{title}: {len(items)}{note}", file=sys.stderr)
        for item in items:
            print(f"  {item}", file=sys.stderr)

    print(f"\n— bundle report —\nconcepts: {len(nodes)}  "
          f"written edges: {len(written)}  derived: {audit['derived']}  "
          f"identifier field: {audit['identifier'] or '(none detected)'}", file=sys.stderr)
    block("orphans (no written link in or out)", orphans)
    block("broken links", [f"{d['source']} → {d['target']}" for d in audit["dangling"]],
          "  (§6.1 tolerates these; they may be knowledge not yet written)")
    block("undefined footnote references",
          [f"{n['source']} → [^{n['ref']}]" for n in audit["loose_notes"]])
    block("past stale_after", stale)
    block("status: draft", draft)


def find_identifier_key(nodes):
    """The extension key that behaves like an identifier.

    A key qualifies when every concept carries it and no two concepts share a
    value — the definition of an identifier, discovered rather than configured,
    so no producer's spelling (`acme.id`, `wiki.uid`) is baked in here.
    """
    seen = {}
    for node in nodes:
        for key, value in node["ext"].items():
            seen.setdefault(key, []).append(value)
    best = None
    for key, values in seen.items():
        if len(values) == len(nodes) and len(set(values)) == len(nodes):
            if best is None or len(key) < len(best):
                best = key
    return best


def derive_edges(nodes, derivations):
    """Edges implied by frontmatter that already exists.

    Two sources, both refusing to invent vocabulary:

    * **Exact match** — an extension value equal to some concept's identifier is
      a reference to it. `superseded_by: an-rabbitmq-adoption` names a concept,
      so the graph should show that it does.
    * **Declared joins** — `--derive-edge acme.owner_team=team-{}` for the case
      where a value keys a concept without equalling its id. This stays an
      explicit argument because the transform is a property of one bundle's
      conventions, and guessing it would put edges on the page that no document
      asserts.
    """
    ident = find_identifier_key(nodes)
    if not ident:
        return [], None
    by_ident = {n["ext"][ident]: n["id"] for n in nodes}
    out, seen = [], set()
    for node in nodes:
        for key, value in node["ext"].items():
            if key == ident:
                continue
            candidates = [value] if value in by_ident else []
            for dkey, pattern in derivations:
                if dkey == key:
                    candidates.append(pattern.replace("{}", value))
            for cand in candidates:
                target = by_ident.get(cand)
                if target and target != node["id"] and (node["id"], target, key) not in seen:
                    seen.add((node["id"], target, key))
                    out.append({"source": node["id"], "target": target,
                                "origin": "derived", "label": key})
    return out, ident


def build(bundle: Path, derivations=(), body_max: int = BODY_MAX):
    nodes, edges, seen = [], [], set()
    dangling, loose_notes = [], []
    files = sorted(p for p in bundle.rglob("*.md") if p.is_file() and p.name not in RESERVED)
    ids = {p.relative_to(bundle).with_suffix("").as_posix() for p in files}
    for p in files:
        cid = p.relative_to(bundle).with_suffix("").as_posix()
        try:
            raw = p.read_text(encoding="utf-8").lstrip("﻿")
        except (UnicodeDecodeError, OSError) as exc:
            print(f"warning: skipping {p.relative_to(bundle)}: cannot read file: {exc}", file=sys.stderr)
            ids.discard(cid)
            continue
        meta, body = split_frontmatter(raw)
        body = body.strip()
        generated, verified = read_trust(meta)
        sources = read_sources(meta, p, bundle)
        # Checked against the whole document: definitions live at the bottom, so
        # asking the truncated copy would invent undefined references.
        for ref in undefined_footnotes(body):
            loose_notes.append({"source": cid, "ref": ref})
        nodes.append({
            "id": cid,
            "type": str(meta.get("type", "Untyped")),
            "title": str(meta.get("title", p.stem)),
            "description": str(meta.get("description", "")),
            "tags": meta.get("tags", []) if isinstance(meta.get("tags"), list) else [],
            "group": cid.split("/")[0] if "/" in cid else "(root)",
            "ext": read_extensions(meta),
            "sz": max(24, min(70, 24 + len(body) // 200)),
            "status": str(meta.get("status", "")),
            "stale_after": str(meta.get("stale_after") or ""),
            "generated": generated,
            "verified": verified,
            "sources": sources,
            "body": (body if len(body) <= body_max else
                     body[:body_max] + f"\n\n*— truncated at {body_max:,} characters —*"),
        })
        targets = link_targets(body) + [s["resource"] for s in sources if s["cid"]]
        for t in targets:
            tgt = resolve(t, p, bundle)
            if is_dangling(t, p, bundle):
                # §6.1 calls this tolerable, not invisible: a link to a concept
                # that does not exist may be knowledge not yet written, but the
                # author is the one who should get to decide which it is.
                dangling.append({"source": cid, "target": t})
                continue
            if tgt and tgt in ids and tgt != cid and (cid, tgt) not in seen:
                seen.add((cid, tgt))
                edges.append({"source": cid, "target": tgt, "origin": "link"})
    derived, ident = derive_edges(nodes, derivations)
    # A derived edge that merely restates a written link adds no information and
    # would double the line weight between the same two concepts.
    written = {(e["source"], e["target"]) for e in edges}
    derived = [e for e in derived if (e["source"], e["target"]) not in written]
    return nodes, edges + derived, {"dangling": dangling, "identifier": ident,
                                    "derived": len(derived), "loose_notes": loose_notes}


HTML = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>OKF — __NAME__</title>
<meta property="og:title" content="__OGTITLE__">
<meta property="og:description" content="__OGDESC__">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">
__OGIMAGE__
__LIBS__
<style>
 :root{--bg:#0e0f13;--panel:#16181f;--line:#262a35;--fg:#e6e8ee;--mut:#9aa3b2;--accent:#8ab4ff}
 *{box-sizing:border-box} html,body{margin:0;height:100%;background:var(--bg);color:var(--fg);
   font:14px/1.5 ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
 /* The row must be stated. Left implicit it sizes to `auto`, i.e. to the tallest
    item — a long concept body then stretched #side past the viewport and the page
    grew its own scrollbar on top of the panel's, which in turn forced a spurious
    horizontal one. Pinning the row to 100% keeps the panel scrolling inside. */
 #app{display:grid;grid-template-columns:1fr clamp(400px,34vw,560px);grid-template-rows:100%;height:100vh}
 #cy{width:100%;height:100%}
 #side{border-left:1px solid var(--line);background:var(--panel);overflow:auto;padding:18px}
 header{position:absolute;top:0;left:0;padding:14px 18px;z-index:5;pointer-events:none}
 h1{font-size:15px;margin:0;font-weight:650} .sub{color:var(--mut);font-size:12px;margin-top:2px}
 #bar{position:absolute;top:12px;left:50%;transform:translateX(-50%);z-index:5;display:flex;gap:8px}
 #bar input,#bar select{background:var(--panel);border:1px solid var(--line);color:var(--fg);
   border-radius:8px;padding:8px 10px;outline:none;font-size:13px}
 #search{width:min(300px,32vw)}
 #legend{position:absolute;bottom:14px;left:18px;z-index:5;display:flex;flex-wrap:wrap;gap:6px;max-width:60vw}
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
 .rel{margin:10px 0} .rel h4{margin:0 0 4px;font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--mut)}
 .rel a{display:block;color:var(--accent);cursor:pointer;font-size:13px;padding:1px 0;text-decoration:none}
 .rel a:hover{text-decoration:underline}
 /* The body is the half of this panel people actually read. It gets prose
    treatment: a looser measure, a real heading scale, and tables and code that
    are contained rather than left to burst the panel's width. */
 .body{border-top:1px solid var(--line);padding-top:16px;margin-top:16px;
   font-size:14.5px;line-height:1.68;overflow-wrap:break-word}
 .body>*:first-child{margin-top:0}
 .body h1,.body h2,.body h3,.body h4{line-height:1.3;font-weight:650;margin:1.6em 0 .5em;color:#f2f4f8}
 .body h1{font-size:1.32em} .body h2{font-size:1.18em}
 .body h3{font-size:1.05em} .body h4{font-size:.95em;color:var(--mut)}
 .body h1,.body h2{border-bottom:1px solid var(--line);padding-bottom:.28em}
 .body p{margin:.85em 0}
 .body ul,.body ol{margin:.75em 0;padding-left:1.35em} .body li{margin:.3em 0}
 .body li>ul,.body li>ol{margin:.3em 0}
 .body a{color:var(--accent);text-decoration:none;border-bottom:1px solid #33415c}
 .body a:hover{border-bottom-color:var(--accent)}
 .body blockquote{margin:1em 0;padding:.1em 0 .1em 1em;border-left:3px solid #2f3a4d;color:var(--mut)}
 .body hr{border:0;border-top:1px solid var(--line);margin:1.8em 0}
 .body strong{color:#f2f4f8;font-weight:650}
 /* A wide table must scroll inside its own box; letting it size the panel is
    what pushed a second scrollbar onto the page. */
 .body .tw{overflow-x:auto;margin:1em 0;border:1px solid var(--line);border-radius:8px}
 .body table{border-collapse:collapse;width:100%;font-size:13px}
 .body th{background:#1b1f29;color:#f2f4f8;font-weight:650;text-align:left;white-space:nowrap}
 .body td,.body th{border-bottom:1px solid var(--line);border-right:1px solid var(--line);padding:6px 10px;vertical-align:top}
 .body tr:last-child td{border-bottom:0} .body td:last-child,.body th:last-child{border-right:0}
 .body code{background:#1d2230;border:1px solid #242b3a;padding:.1em .4em;border-radius:4px;
   font:12.5px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
 .body pre{background:#12151d;border:1px solid var(--line);border-radius:8px;padding:12px 14px;
   overflow-x:auto;margin:1em 0} .body pre code{background:none;border:0;padding:0;font-size:12.5px}
 /* Footnotes are the quiet apparatus under the argument, not part of it. */
 .body sup a{border:0;font-size:.78em;padding:0 .12em}
 .body .footnotes{margin-top:2em;padding-top:.8em;border-top:1px solid var(--line);
   font-size:13px;color:var(--mut)}
 .body .footnotes ol{padding-left:1.2em} .body .footnotes li{margin:.35em 0}
 .body .footnotes p{margin:.2em 0}
 .body pre{background:#1d2230;padding:10px;border-radius:8px;overflow:auto} .body img{max-width:100%}
 .empty{color:var(--mut)} a{color:var(--accent)}
 .src{pointer-events:auto;color:var(--accent);margin-left:10px;text-decoration:none} .src:hover{text-decoration:underline}
</style></head><body>
<div id="app"><div id="cy"></div><div id="side"><p class="empty">Click a concept to inspect it.</p></div></div>
<header><h1>__NAME__</h1><div class="sub">__N__ concepts · __E__ links · OKF v0.2__LINK__</div></header>
<div id="bar">
 <input id="search" placeholder="search concepts…">
 <select id="type"><option value="">all types</option></select>
 <select id="colorby" title="colour and group nodes by a frontmatter field"></select>
 <label id="derivedbox" title="edges inferred from frontmatter rather than written as links"><input type="checkbox" id="showderived"> derived</label>
 <select id="layout">
  <option value="cose">force</option><option value="concentric">concentric</option>
  <option value="breadthfirst">breadth-first</option><option value="circle">circle</option><option value="grid">grid</option>
 </select>
</div>
<div id="legend"></div>
<script>
const NODES=__NODES__, EDGES=__EDGES__;
const PALETTE=["#6E56CF","#D97757","#22C55E","#3B82F6","#EAB308","#EC4899","#14B8A6","#F97316","#A855F7","#0EA5E9","#84CC16","#EF4444","#64748B"];
const byId=Object.fromEntries(NODES.map(n=>[n.id,n]));
const outL={}, inL={};
NODES.forEach(n=>{outL[n.id]=[];inL[n.id]=[];});
EDGES.forEach(e=>{outL[e.source].push(e.target);inL[e.target].push(e.source);});
const types=[...new Set(NODES.map(n=>n.type))].sort();
// A field earns a place in the colour-by list only if it actually partitions the
// bundle. One distinct value paints every node identically; a value per node (an
// id, a URL, a health path) is N colours and no signal. The band between is where
// the real axes live — owning team, tier, environment, family.
const DIM_MIN=2, DIM_MAX=24;
const extVals={};
NODES.forEach(n=>{const e=n.ext||{};for(const k in e){(extVals[k]=extVals[k]||new Set()).add(e[k]);}});
const dims=['type',...Object.keys(extVals)
 .filter(k=>extVals[k].size>=DIM_MIN&&extVals[k].size<=DIM_MAX).sort()];
// Nodes missing the current field are not dropped — they group under one explicit
// bucket, so an incomplete field reads as a visible gap instead of a silent one.
const UNSET='(unset)';
let dim='type';
const dimValue=(n,d)=>d==='type'?n.type:(((n.ext||{})[d])||UNSET);
let buckets=[],color={};
function recolour(){buckets=[...new Set(NODES.map(n=>dimValue(n,dim)))].sort();
 color=Object.fromEntries(buckets.map((b,i)=>[b,PALETTE[i%PALETTE.length]]));}
recolour();
const off=new Set();
const cy=cytoscape({container:document.getElementById('cy'),minZoom:.2,maxZoom:1.6,wheelSensitivity:.2,
 elements:[...NODES.map(n=>({data:{...n,c:color[dimValue(n,dim)]}})),...EDGES.map(e=>({data:e}))],
 style:[
  {selector:'node',style:{'background-color':'data(c)','label':'data(title)','color':'#e6e8ee',
   'font-size':10,'text-wrap':'wrap','text-max-width':120,'text-valign':'bottom','text-margin-y':4,
   'text-outline-width':2,'text-outline-color':'#0e0f13','min-zoomed-font-size':6,
   'width':'data(sz)','height':'data(sz)'}},
  {selector:'edge',style:{'width':1.2,'line-color':'#3a4150','target-arrow-color':'#3a4150',
   'target-arrow-shape':'triangle','arrow-scale':.8,'curve-style':'bezier','opacity':.7}},
  // A derived edge is an inference from frontmatter, not a sentence someone
  // wrote. Dashing it keeps that difference legible instead of presenting both
  // as the same kind of claim.
  {selector:'edge[origin="derived"]',style:{'line-style':'dashed','line-color':'#4b5468',
   'target-arrow-color':'#4b5468','opacity':.55}},
  {selector:'.dim',style:{'opacity':.10}},{selector:'.hl',style:{'border-width':3,'border-color':'#fff'}}
 ],
 layout:{name:'__LAYOUT__',animate:false,nodeRepulsion:9000,idealEdgeLength:90,padding:40}});
const side=document.getElementById('side');
const esc=s=>(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function relList(title,arr){if(!arr.length)return'';
 return `<div class="rel"><h4>${title}</h4>${arr.map(id=>`<a data-go="${esc(id)}">${esc((byId[id]||{}).title||id)}</a>`).join('')}</div>`;}
// §5.3 — the trust tier is derived, never stored: no `verified` is unverified,
// `verified` by non-`human:` actors only is machine-confirmed, and any `human:`
// actor makes it human-reviewed. The exact lowercase prefix is the whole key.
// §5.5 — a concept is stale when today >= stale_after; both are YYYY-MM-DD, so
// a string compare is the whole comparison. Advisory signals, not access control.
const TODAY=new Date().toISOString().slice(0,10);
function trustTier(n){const v=n.verified||[];
 if(!v.length)return['t-unverified','unverified'];
 return v.some(e=>(e.by||'').startsWith('human:'))?['t-human','human-reviewed']
                                                  :['t-machine','machine-confirmed'];}
function badges(n){const [cls,label]=trustTier(n),out=[`<span class="badge ${cls}">${label}</span>`];
 if(n.stale_after&&TODAY>=n.stale_after)out.push(`<span class="badge b-stale">stale since ${esc(n.stale_after)}</span>`);
 if(n.status==='deprecated')out.push('<span class="badge b-deprecated">deprecated</span>');
 return `<div class="badges">${out.join('')}</div>`;}
// OKF v0.2 trust (§5.2) + lifecycle (§5.4/§5.5). A v0.1 `timestamp` arrives here
// as generated.at with an empty `by`, so legacy bundles still show a date.
function metaBlock(n){const g=n.generated||{},rows=[];
 if(n.status)rows.push(`<div>status <b>${esc(n.status)}</b></div>`);
 if(g.at||g.by)rows.push(`<div>generated${g.at?` <b>${esc(g.at)}</b>`:''}${g.by?` by ${esc(g.by)}`:''}</div>`);
 (n.verified||[]).forEach(v=>rows.push(`<div>verified${v.at?` <b>${esc(v.at)}</b>`:''}${v.by?` by ${esc(v.by)}`:''}</div>`));
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
// Resolve an in-body markdown link href to a concept id, mirroring build()'s
// resolution: strip #anchor, require .md, absolute strips leading /, relative
// resolves against the current concept's dir. Returns null if it's not a concept.
function resolveHref(cid,href){let t=(href||'').split('#')[0];if(!t.endsWith('.md'))return null;
 let tgt;if(t[0]==='/'){tgt=t.replace(/^\/+/,'').slice(0,-3);}
 else{const base=cid.split('/').slice(0,-1);
  for(const seg of t.slice(0,-3).split('/')){if(seg===''||seg==='.')continue;
   if(seg==='..'){if(!base.length)return null;base.pop();}else base.push(seg);}
  tgt=base.join('/');}
 return byId[tgt]?tgt:null;}
// marked implements no footnotes, so `[^ref]` survives into the rendered page as
// literal text — mid-sentence and inside table cells — and the definitions pile
// up unlabelled at the bottom. Bundles lean on footnotes to carry provenance, so
// this is most of what makes a concept read badly. Definitions are lifted out,
// references numbered in order of first appearance, and the list rebuilt at the
// end with a link back to each call site.
function renderBody(md){
 const defs=new Map(),kept=[],lines=(md||'').split('\n');
 let fence=false;
 for(let i=0;i<lines.length;i++){
  if(/^\s*(```|~~~)/.test(lines[i]))fence=!fence;
  const m=fence?null:lines[i].match(/^\[\^([^\]]+)\]:\s?(.*)$/);
  if(!m){kept.push(lines[i]);continue;}
  const parts=[m[2]];
  // A definition owns the indented lines that follow it.
  while(i+1<lines.length&&/^(\s{2,}|\t)/.test(lines[i+1])&&lines[i+1].trim())parts.push(lines[++i].trim());
  defs.set(m[1],parts.join(' ').trim());}
 if(!defs.size)return marked.parse(kept.join('\n'));
 const order=[];
 let fence2=false;
 const body=kept.map(line=>{
  if(/^\s*(```|~~~)/.test(line)){fence2=!fence2;return line;}
  if(fence2)return line;                       // a reference inside code is code
  return line.replace(/\[\^([^\]]+)\]/g,(all,ref)=>{
   if(!defs.has(ref))return all;               // an undefined reference stays as written
   let i=order.indexOf(ref);if(i<0){order.push(ref);i=order.length-1;}
   return `<sup class="fnref" id="fnref-${i+1}"><a href="#fn-${i+1}">${i+1}</a></sup>`;});
 }).join('\n');
 const html=marked.parse(body);
 if(!order.length)return html;
 const items=order.map((ref,i)=>
  `<li id="fn-${i+1}">${marked.parseInline(defs.get(ref))} <a class="fnback" href="#fnref-${i+1}">↩</a></li>`).join('');
 return html+`<section class="footnotes"><ol>${items}</ol></section>`;}
function show(id){const n=byId[id];if(!n)return;const c=color[n.type];
 side.innerHTML=`<span class="type" style="background:${c}">${esc(n.type)}</span>
 <h2>${esc(n.title)}</h2><div class="desc">${esc(n.description)||'<span class=empty>no description</span>'}</div>
 <div class="tags">${(n.tags||[]).map(t=>`<span class="tag">${esc(t)}</span>`).join('')}</div>
 ${badges(n)}${metaBlock(n)}${srcList(n)}${relList('Links to',outL[id])}${relList('Cited by',inL[id])}
 <div class="body">${n.body?DOMPurify.sanitize(renderBody(n.body)):'<span class=empty>empty body</span>'}</div>`;
 // marked emits a bare <table>; a wide one would stretch the panel and put a
 // second scrollbar on the page, so each gets its own horizontally-scrolling box.
 side.querySelectorAll('.body table').forEach(t=>{if(t.parentElement.classList.contains('tw'))return;
  const w=document.createElement('div');w.className='tw';t.replaceWith(w);w.appendChild(t);});
 // Footnote jumps scroll the panel directly. Left to the browser they would
 // rewrite location.hash, which this page uses to name the selected concept —
 // so a reload after reading a footnote would open nothing.
 side.querySelectorAll('.fnref a,.fnback').forEach(a=>a.onclick=e=>{
  e.preventDefault();
  const t=side.querySelector('#'+CSS.escape(a.getAttribute('href').slice(1)));
  if(t)t.scrollIntoView({behavior:'smooth',block:'center'});});
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
  // Extension values join the haystack: a bundle's own identifier (`acme.id`)
  // is what a reader actually types, and it appears nowhere in title or body.
  const ext=Object.values(d.ext||{}).join(' ');
  const m=(!q||(d.title+' '+d.type+' '+d.description+' '+(d.tags||[]).join(' ')+' '+ext).toLowerCase().includes(q))
        &&(!ty||d.type===ty)&&!off.has(dimValue(d,dim));
  n.style('display',m?'element':'none');}));}
let debounce;
document.getElementById('search').oninput=()=>{clearTimeout(debounce);debounce=setTimeout(applyFilter,150);};
document.getElementById('type').oninput=applyFilter;
const tysel=document.getElementById('type');types.forEach(t=>{const o=document.createElement('option');o.value=t;o.textContent=t;tysel.appendChild(o);});
let curLayout='__LAYOUT__';
document.getElementById('layout').onchange=e=>{const v=e.target.value;
 if(v==='cose'&&NODES.length>__COSEMAX__&&!confirm(`force layout on ${NODES.length} concepts can freeze this tab — run anyway?`)){e.target.value=curLayout;return;}
 curLayout=v;cy.layout({name:v,animate:true,padding:40,nodeRepulsion:9000,idealEdgeLength:90}).run();};
function drawLegend(){document.getElementById('legend').innerHTML=buckets.map(b=>
 `<span class="chip${off.has(b)?' off':''}" data-t="${esc(b)}"><span class="dot" style="background:${color[b]}"></span>${esc(b)} (${NODES.filter(n=>dimValue(n,dim)===b).length})</span>`).join('');
 document.querySelectorAll('#legend .chip').forEach(ch=>ch.onclick=()=>{const t=ch.getAttribute('data-t');
  if(off.has(t)){off.delete(t);ch.classList.remove('off');}else{off.add(t);ch.classList.add('off');}applyFilter();});}
const dimsel=document.getElementById('colorby');
dims.forEach(d=>{const o=document.createElement('option');o.value=d;
 o.textContent=d==='type'?'colour: type':`colour: ${d}`;dimsel.appendChild(o);});
dimsel.onchange=e=>{dim=e.target.value;
 // The old chips named buckets that no longer exist; carrying their hidden state
 // over would silently filter the graph by a dimension the reader just left.
 off.clear();recolour();
 cy.batch(()=>cy.nodes().forEach(n=>n.data('c',color[dimValue(n.data(),dim)])));
 drawLegend();applyFilter();};
drawLegend();
// With no derived edges there is nothing to toggle, and an inert control that
// never does anything reads as a broken one.
const derivedCount=EDGES.filter(e=>e.origin==='derived').length;
function setDerived(on){cy.batch(()=>cy.edges().forEach(ed=>{
 if(ed.data('origin')==='derived')ed.style('display',on?'element':'none');}));}
if(!derivedCount)document.getElementById('derivedbox').style.display='none';
else{
 // Off by default. A field like an owning team is the same value on most of the
 // bundle, so showing it collapses the layout into a few giant stars and buries
 // the written links underneath. It is a lens to reach for, not the first view.
 setDerived(false);
 document.getElementById('derivedbox').title+=` — ${derivedCount} inferred`;
 document.getElementById('showderived').onchange=e=>setDerived(e.target.checked);}
document.getElementById('layout').value='__LAYOUT__';
const Q=new URLSearchParams(location.search),QL=Q.get('layout'),QS=Q.get('select');
if(QL&&[...document.querySelectorAll('#layout option')].some(o=>o.value===QL)){document.getElementById('layout').value=QL;curLayout=QL;cy.layout({name:QL,animate:false,padding:40,nodeRepulsion:9000,idealEdgeLength:90}).run();}
function fromHash(){try{const h=decodeURIComponent((location.hash||'').slice(1));if(h&&byId[h])select(h);}catch(e){}}
addEventListener('hashchange',fromHash);
if(QS&&byId[QS])select(QS);else fromHash();
</script></body></html>"""


def render(bundle: Path, out: Path, title: str | None = None, link: str | None = None,
           layout: str | None = None, og_image: str | None = None,
           max_nodes: int | None = None, derivations=(), vendor: bool = False,
           report: bool = False, body_max: int = BODY_MAX):
    nodes, edges, audit = build(bundle, derivations, body_max)
    if report:
        print_report(nodes, edges, audit)
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
    libs = vendor_libs(out.resolve().parent / ".okf-vendor") if vendor else CDN_TAGS
    subs = {"__LIBS__": libs,
            "__NAME__": name, "__LINK__": src, "__LAYOUT__": layout,
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
    ap.add_argument("--derive-edge", action="append", default=[], metavar="FIELD=PATTERN",
                    help="treat a frontmatter field as a reference to another concept, e.g. "
                         "--derive-edge acme.owner_team=team-{} maps `infra` to the concept whose "
                         "identifier is `team-infra`. Values that already equal an identifier are "
                         "linked automatically and need no pattern. Repeatable.")
    ap.add_argument("--vendor", action="store_true",
                    help="inline cytoscape/marked/dompurify instead of loading them from a CDN, "
                         "so the page works offline and under a strict CSP")
    ap.add_argument("--report", action="store_true",
                    help="print bundle health to stderr: orphans, broken links, stale, drafts")
    ap.add_argument("--max-body", type=int, default=BODY_MAX, metavar="CHARS",
                    help=f"characters of each concept body to embed (default {BODY_MAX:,}); "
                         "a truncated body says so in the panel")
    args = ap.parse_args()
    if not args.bundle.is_dir():
        print(f"error: {args.bundle} is not a directory", file=sys.stderr)
        return 2
    out = args.out or (args.bundle / "viz.html")
    derivations = []
    for spec in args.derive_edge:
        field, sep, pattern = spec.partition("=")
        if not sep or "{}" not in pattern:
            print(f"error: --derive-edge expects FIELD=PATTERN with a {{}} placeholder, got {spec!r}",
                  file=sys.stderr)
            return 2
        derivations.append((field.strip(), pattern.strip()))
    n, e = render(args.bundle, out, title=args.title, link=args.link, layout=args.layout,
                  og_image=args.og_image, max_nodes=args.max_nodes,
                  derivations=derivations, vendor=args.vendor, report=args.report,
                  body_max=args.max_body)
    print(f"rendered {n} concepts, {e} links -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
