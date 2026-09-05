#!/usr/bin/env python3
"""Deterministic per-analysis metrics for the map-phase benchmark.

usage: metrics.py <events.jsonl> <analyses-dir> [--truth truth.json] [--rows rows.jsonl]

Prints an aggregate JSON summary. With --rows, writes one row per expected live event
(paired comparisons across arms join on event id).
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

SECTIONS = ["# Claim", "# Entities", "# Rationale", "# Candidate concepts"]
KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
FORBIDDEN = re.compile(
    r"^(feat|fix|chore|docs|refactor|test|style|perf|ci|build|merge-pull-request|merge)(-|$)"
    r"|^(changes?|updates?|tasks?|feature|misc|improvements?|work)$"
)
PATHLIKE = re.compile(r"/|\.[A-Za-z0-9]{1,6}$")


def parse(md: str):
    fm, body = {}, md
    if md.startswith("---\n"):
        end = md.find("\n---\n", 4)
        if end != -1:
            for line in md[4:end].splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    fm[k.strip()] = v.strip()
            body = md[end + 5:]
    sections, current, stray = {}, None, 0
    for line in body.splitlines():
        if line.startswith("# "):
            current = line.strip()
            sections.setdefault(current, [])
            continue
        if not line.strip():
            continue
        if current is None or not line.startswith("- "):
            stray += 1
            continue
        sections[current].append(line[2:].strip())
    return fm, sections, stray


def entity_token(bullet: str) -> str:
    tok = bullet.split(":", 1)[0].strip().strip("`*")
    return tok


def candidate_name(bullet: str):
    m = re.match(r"`([^`]+)`", bullet)
    return m.group(1) if m else bullet.split(":", 1)[0].strip()


def path_in_event(tok: str, files: list[str]) -> bool:
    t = tok.strip("/")
    return any(f == t or f.startswith(t + "/") or f.endswith("/" + t) or Path(f).name == t for f in files)


def analyse(event: dict, md: str | None, truth: dict):
    eid = event["id"]
    row = {"id": eid, "source": event["source"], "present": md is not None}
    if md is None:
        return row
    fm, sections, stray = parse(md)
    names = [candidate_name(b) for b in sections.get("# Candidate concepts", [])]
    violations = [n for n in names if not KEBAB.match(n) or FORBIDDEN.search(n)]
    ents = [entity_token(b) for b in sections.get("# Entities", [])]
    pathlike = [e for e in ents if PATHLIKE.search(e)]
    files = [f["path"] for f in event.get("files", [])]
    hits = [p for p in pathlike if path_in_event(p, files)] if event["source"] == "git" else []
    trunc = fm.get("truncated", "").lower() == "true"
    row.update({
        "bytes": len(md),
        "template_ok": (set(sections) == set(SECTIONS) and stray == 0
                        and all(k in fm for k in ("event_id", "source", "timestamp", "truncated"))),
        "stray_lines": stray,
        "claim_n": len(sections.get("# Claim", [])),
        "entities_n": len(ents),
        "rationale_n": len(sections.get("# Rationale", [])),
        "candidates_n": len(names),
        "violations": violations,
        "truncated": trunc,
        "truncated_truth": truth.get(eid),
        "truncated_agree": (truth.get(eid) == trunc) if eid in truth else None,
        "pathlike_n": len(pathlike),
        "path_hits_n": len(hits),
        "path_misses": [p for p in pathlike if p not in hits] if event["source"] == "git" else [],
        "unclear": "[UNCLEAR]" in md,
    })
    return row


def mean(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 3) if xs else None


def main():
    args = sys.argv[1:]
    events_path, analyses_dir = Path(args[0]), Path(args[1])
    truth = json.loads(Path(args[args.index("--truth") + 1]).read_text()) if "--truth" in args else {}
    rows_out = Path(args[args.index("--rows") + 1]) if "--rows" in args else None

    events = [json.loads(l) for l in events_path.read_text().splitlines() if l.strip()]
    live = [e for e in events if "skip" not in e]
    rows = []
    for e in live:
        f = analyses_dir / (e["id"].replace(":", "-") + ".md")
        rows.append(analyse(e, f.read_text() if f.exists() else None, truth))

    present = [r for r in rows if r["present"]]
    git_rows = [r for r in present if r["source"] == "git"]
    with_paths = [r for r in git_rows if r["pathlike_n"]]
    cand_total = sum(r["candidates_n"] for r in present)
    summary = {
        "expected": len(live), "present": len(present), "missing_n": sum(1 for r in rows if not r["present"]), "missing_sample": [r["id"] for r in rows if not r["present"]][:5],
        "template_ok_rate": mean([1.0 if r["template_ok"] else 0.0 for r in present]),
        "stray_lines_total": sum(r["stray_lines"] for r in present),
        "bytes_mean": mean([r["bytes"] for r in present]),
        "candidates_mean": mean([r["candidates_n"] for r in present]),
        "violation_rate": round(sum(len(r["violations"]) for r in present) / cand_total, 3) if cand_total else None,
        "violations_total": sum(len(r["violations"]) for r in present),
        "rationale_over2_rate": mean([1.0 if r["rationale_n"] > 2 else 0.0 for r in present]),
        "truncated_reported": sum(1 for r in present if r["truncated"]),
        "truncated_truth": sum(1 for v in truth.values() if v) if truth else None,
        "truncated_agree_rate": mean([1.0 if r["truncated_agree"] else 0.0 for r in git_rows if r["truncated_agree"] is not None]),
        "entity_precision_mean": mean([r["path_hits_n"] / r["pathlike_n"] for r in with_paths]),
        "entity_pathlike_mean": mean([r["pathlike_n"] for r in git_rows]),
        "unclear_n": sum(1 for r in present if r["unclear"]),
    }
    if rows_out:
        rows_out.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
