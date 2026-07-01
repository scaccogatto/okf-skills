#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""Render an Open Knowledge Format (OKF) bundle as a single self-contained,
interactive HTML graph (`viz.html`). No backend, no install on the viewing side,
no data leaves the page — concepts become nodes (coloured by `type`, sized by
body length), markdown links become edges, and clicking a node opens a wiki-style
panel with its rendered markdown, outgoing links, and "Cited by" backlinks.

Features: force/concentric/breadth-first/circle/grid layouts, per-type filter,
free-text search, neighbour highlight, clickable cross-links and backlinks.

Run:  uv run okf_visualize.py <bundle-dir> [-o viz.html]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

RESERVED = {"index.md", "log.md"}
FENCE = re.compile(r"^(```|~~~)")
LINK = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def json_for_script(obj) -> str:
    """JSON-encode ``obj`` for safe embedding inside an inline ``<script>``.

    ``json.dumps`` produces valid JSON but does not escape ``</``. When a concept
    body contains a literal ``</script>`` (common in docs that show HTML/JS
    snippets), the browser's HTML tokenizer closes the inline ``<script>`` at
    that point — truncating the embedded ``NODES``/``EDGES`` data and breaking the
    whole page. Escaping ``</`` -> ``<\\/`` is valid JSON/JS yet invisible to the
    tokenizer. ``<!--`` and the U+2028/U+2029 separators (illegal in JS string
    literals) are neutralized for the same reason.
    """
    return (
        json.dumps(obj, default=str)
        .replace("</", "<\\/")
        .replace("<!--", "<\\!--")
        .replace(" ", "\\u2028")
        .replace(" ", "\\u2029")
    )


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


def build(bundle: Path):
    nodes, edges, seen = [], [], set()
    files = sorted(p for p in bundle.rglob("*.md") if p.is_file() and p.name not in RESERVED)
    ids = {p.relative_to(bundle).with_suffix("").as_posix() for p in files}
    for p in files:
        cid = p.relative_to(bundle).with_suffix("").as_posix()
        meta, body = split_frontmatter(p.read_text(encoding="utf-8").lstrip("﻿"))
        body = body.strip()
        nodes.append({
            "id": cid,
            "type": str(meta.get("type", "Untyped")),
            "title": str(meta.get("title", p.stem)),
            "description": str(meta.get("description", "")),
            "tags": meta.get("tags", []) if isinstance(meta.get("tags"), list) else [],
            "group": cid.split("/")[0] if "/" in cid else "(root)",
            "sz": max(24, min(70, 24 + len(body) // 200)),
            "body": body[:8000],
        })
        for t in link_targets(body):
            t = t.split("#", 1)[0]
            if not t.endswith(".md"):
                continue
            if t.startswith("/"):
                tgt = t.lstrip("/")[:-3]
            else:
                tgt = (p.parent / t).resolve().relative_to(bundle.resolve()).as_posix()[:-3] \
                    if (p.parent / t).resolve().is_relative_to(bundle.resolve()) else None
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
<script src="https://cdn.jsdelivr.net/npm/cytoscape@3.30.2/dist/cytoscape.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/marked@14/marked.min.js"></script>
<style>
 :root{--bg:#0e0f13;--panel:#16181f;--line:#262a35;--fg:#e6e8ee;--mut:#9aa3b2;--accent:#8ab4ff}
 *{box-sizing:border-box} html,body{margin:0;height:100%;background:var(--bg);color:var(--fg);
   font:14px/1.5 ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
 #app{display:grid;grid-template-columns:1fr 400px;height:100vh}
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
 .rel{margin:10px 0} .rel h4{margin:0 0 4px;font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--mut)}
 .rel a{display:block;color:var(--accent);cursor:pointer;font-size:13px;padding:1px 0;text-decoration:none}
 .rel a:hover{text-decoration:underline}
 .body{border-top:1px solid var(--line);padding-top:12px;margin-top:12px} .body table{border-collapse:collapse;display:block;overflow:auto}
 .body td,.body th{border:1px solid var(--line);padding:4px 8px} .body code{background:#1d2230;padding:1px 5px;border-radius:4px}
 .body pre{background:#1d2230;padding:10px;border-radius:8px;overflow:auto} .body img{max-width:100%}
 .empty{color:var(--mut)} a{color:var(--accent)}
 .src{pointer-events:auto;color:var(--accent);margin-left:10px;text-decoration:none} .src:hover{text-decoration:underline}
</style></head><body>
<div id="app"><div id="cy"></div><div id="side"><p class="empty">Click a concept to inspect it.</p></div></div>
<header><h1>__NAME__</h1><div class="sub">__N__ concepts · __E__ links · OKF v0.1__LINK__</div></header>
<div id="bar">
 <input id="search" placeholder="search concepts…">
 <select id="type"><option value="">all types</option></select>
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
const esc=s=>(s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
function relList(title,arr){if(!arr.length)return'';
 return `<div class="rel"><h4>${title}</h4>${arr.map(id=>`<a data-go="${esc(id)}">${esc((byId[id]||{}).title||id)}</a>`).join('')}</div>`;}
function show(id){const n=byId[id];if(!n)return;const c=color[n.type];
 side.innerHTML=`<span class="type" style="background:${c}">${esc(n.type)}</span>
 <h2>${esc(n.title)}</h2><div class="desc">${esc(n.description)||'<span class=empty>no description</span>'}</div>
 <div class="tags">${(n.tags||[]).map(t=>`<span class="tag">${esc(t)}</span>`).join('')}</div>
 ${relList('Links to',outL[id])}${relList('Cited by',inL[id])}
 <div class="body">${n.body?marked.parse(n.body):'<span class=empty>empty body</span>'}</div>`;
 side.querySelectorAll('[data-go]').forEach(a=>a.onclick=()=>select(a.getAttribute('data-go')));}
function select(id){const ele=cy.getElementById(id);if(!ele.length)return;show(id);
 cy.elements().removeClass('hl').addClass('dim');const nb=ele.closedNeighborhood();nb.removeClass('dim');ele.addClass('hl');
 cy.animate({center:{eles:ele},duration:250});
 try{if(decodeURIComponent((location.hash||'').slice(1))!==id)location.hash=encodeURIComponent(id);}catch(e){}}
cy.on('tap','node',e=>select(e.target.id()));
cy.on('tap',e=>{if(e.target===cy)cy.elements().removeClass('dim hl');});
function applyFilter(){const q=document.getElementById('search').value.toLowerCase();const ty=document.getElementById('type').value;
 cy.nodes().forEach(n=>{const d=n.data();
  const m=(!q||(d.title+' '+d.type+' '+d.description+' '+(d.tags||[]).join(' ')).toLowerCase().includes(q))
        &&(!ty||d.type===ty)&&!off.has(d.type);
  n.style('display',m?'element':'none');});}
document.getElementById('search').oninput=applyFilter;
document.getElementById('type').oninput=applyFilter;
const tysel=document.getElementById('type');types.forEach(t=>{const o=document.createElement('option');o.value=t;o.textContent=t;tysel.appendChild(o);});
document.getElementById('layout').onchange=e=>{cy.layout({name:e.target.value,animate:true,padding:40,
 nodeRepulsion:9000,idealEdgeLength:90}).run();};
document.getElementById('legend').innerHTML=types.map(t=>`<span class="chip" data-t="${esc(t)}"><span class="dot" style="background:${color[t]}"></span>${esc(t)} (${NODES.filter(n=>n.type===t).length})</span>`).join('');
document.querySelectorAll('#legend .chip').forEach(ch=>ch.onclick=()=>{const t=ch.getAttribute('data-t');
 if(off.has(t)){off.delete(t);ch.classList.remove('off');}else{off.add(t);ch.classList.add('off');}applyFilter();});
document.getElementById('layout').value='__LAYOUT__';
const Q=new URLSearchParams(location.search),QL=Q.get('layout'),QS=Q.get('select');
if(QL&&[...document.querySelectorAll('#layout option')].some(o=>o.value===QL)){document.getElementById('layout').value=QL;cy.layout({name:QL,animate:false,padding:40,nodeRepulsion:9000,idealEdgeLength:90}).run();}
function fromHash(){try{const h=decodeURIComponent((location.hash||'').slice(1));if(h&&byId[h])select(h);}catch(e){}}
addEventListener('hashchange',fromHash);
if(QS&&byId[QS])select(QS);else fromHash();
</script></body></html>"""


def render(bundle: Path, out: Path, title: str | None = None, link: str | None = None,
           layout: str = "cose", og_image: str | None = None):
    nodes, edges = build(bundle)
    name = title or f"{bundle.resolve().parent.name}/{bundle.name}"
    src = f' <a class="src" href="{link}" target="_blank" rel="noopener">source ↗</a>' if link else ""
    aesc = lambda s: (s or "").replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
    og_title = aesc(f"OKF — {name}")
    og_desc = aesc(f"{len(nodes)} concepts · interactive Open Knowledge Format knowledge graph")
    og_img = (f'<meta property="og:image" content="{aesc(og_image)}">\n'
              f'<meta name="twitter:image" content="{aesc(og_image)}">') if og_image else ""
    html = (HTML.replace("__NAME__", name).replace("__LINK__", src).replace("__LAYOUT__", layout)
            .replace("__OGTITLE__", og_title).replace("__OGDESC__", og_desc).replace("__OGIMAGE__", og_img)
            .replace("__N__", str(len(nodes))).replace("__E__", str(len(edges)))
            .replace("__NODES__", json_for_script(nodes)).replace("__EDGES__", json_for_script(edges)))
    out.write_text(html, encoding="utf-8")
    return len(nodes), len(edges)


def main() -> int:
    ap = argparse.ArgumentParser(description="Render an OKF bundle as a self-contained HTML graph.")
    ap.add_argument("bundle", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=None)
    ap.add_argument("-t", "--title", default=None, help="graph title (default: parent/bundle dir name)")
    ap.add_argument("-l", "--link", default=None, help="optional source URL shown in the header")
    ap.add_argument("--layout", default="cose",
                    choices=["cose", "concentric", "breadthfirst", "circle", "grid"],
                    help="initial graph layout (default: cose)")
    ap.add_argument("--og-image", default=None,
                    help="absolute URL for the social-preview image (og:image / twitter:image)")
    args = ap.parse_args()
    if not args.bundle.is_dir():
        print(f"error: {args.bundle} is not a directory", file=sys.stderr)
        return 2
    out = args.out or (args.bundle / "viz.html")
    n, e = render(args.bundle, out, title=args.title, link=args.link, layout=args.layout,
                  og_image=args.og_image)
    print(f"rendered {n} concepts, {e} links -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
