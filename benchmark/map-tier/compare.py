#!/usr/bin/env python3
"""Paired comparison of arms: join per-event rows on event id, print aggregates and deltas.

usage: compare.py <bench-dir> <arm> [<arm> ...]   (expects <bench>/arms/<arm>/rows.jsonl)
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

BENCH = Path(sys.argv[1])
ARMS = sys.argv[2:]
live = json.loads((BENCH / "live.json").read_text())
batched_ids = {r["id"] for r in live if not r["big"]}


def load(arm):
    rows = [json.loads(l) for l in (BENCH / "arms" / arm / "rows.jsonl").read_text().splitlines() if l.strip()]
    return {r["id"]: r for r in rows}


def mean(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 3) if xs else None


def agg(rows):
    present = [r for r in rows if r["present"]]
    git = [r for r in present if r["source"] == "git"]
    wp = [r for r in git if r["pathlike_n"]]
    cands = sum(r["candidates_n"] for r in present)
    return {
        "n": len(rows), "present": len(present), "missing": len(rows) - len(present),
        "template_ok": mean([1.0 if r["template_ok"] else 0.0 for r in present]),
        "violation_rate": round(sum(len(r["violations"]) for r in present) / cands, 3) if cands else None,
        "entity_precision": mean([r["path_hits_n"] / r["pathlike_n"] for r in wp]),
        "truncated_agree": mean([1.0 if r["truncated_agree"] else 0.0 for r in git if r["truncated_agree"] is not None]),
        "bytes": mean([r["bytes"] for r in present]),
        "candidates": mean([r["candidates_n"] for r in present]),
        "rationale_over2": mean([1.0 if r["rationale_n"] > 2 else 0.0 for r in present]),
        "unclear": sum(1 for r in present if r["unclear"]),
    }


data = {a: load(a) for a in ARMS}
ids = [r["id"] for r in live]

print("## Per-arm aggregates (all live events)")
keys = ["n", "present", "missing", "template_ok", "violation_rate", "entity_precision", "truncated_agree", "bytes", "candidates", "rationale_over2", "unclear"]
print("| metric | " + " | ".join(ARMS) + " |")
print("|---|" + "---|" * len(ARMS))
aggs = {a: agg([data[a][i] for i in ids if i in data[a]]) for a in ARMS}
for k in keys:
    print(f"| {k} | " + " | ".join(str(aggs[a][k]) for a in ARMS) + " |")

print("\n## Batched-eligible events only (small events: the ones the batched arms group)")
print("| metric | " + " | ".join(ARMS) + " |")
print("|---|" + "---|" * len(ARMS))
aggs_b = {a: agg([data[a][i] for i in ids if i in batched_ids and i in data[a]]) for a in ARMS}
for k in ["present", "missing", "template_ok", "violation_rate", "entity_precision", "bytes", "candidates"]:
    print(f"| {k} | " + " | ".join(str(aggs_b[a][k]) for a in ARMS) + " |")

if len(ARMS) >= 2:
    a, b = ARMS[0], ARMS[1]
    print(f"\n## Paired deltas {b} minus {a} (events present in both)")
    both = [i for i in ids if data[a].get(i, {}).get("present") and data[b].get(i, {}).get("present")]
    git_both = [i for i in both if data[a][i]["source"] == "git"]
    d_bytes = mean([data[b][i]["bytes"] - data[a][i]["bytes"] for i in both])
    d_cand = mean([data[b][i]["candidates_n"] - data[a][i]["candidates_n"] for i in both])
    wp = [i for i in git_both if data[a][i]["pathlike_n"] and data[b][i]["pathlike_n"]]
    d_prec = mean([data[b][i]["path_hits_n"] / data[b][i]["pathlike_n"] - data[a][i]["path_hits_n"] / data[a][i]["pathlike_n"] for i in wp])
    print(f"- paired events: {len(both)} (git {len(git_both)}); bytes {d_bytes:+}; candidates {d_cand:+}; entity precision {d_prec:+} on {len(wp)} git events with paths")
    worse = [i for i in wp if data[b][i]["path_hits_n"] / data[b][i]["pathlike_n"] < data[a][i]["path_hits_n"] / data[a][i]["pathlike_n"]]
    better = [i for i in wp if data[b][i]["path_hits_n"] / data[b][i]["pathlike_n"] > data[a][i]["path_hits_n"] / data[a][i]["pathlike_n"]]
    print(f"- entity precision: {b} worse on {len(worse)}, better on {len(better)}, tied on {len(wp) - len(worse) - len(better)}")
    v_a = sum(len(data[a][i]["violations"]) for i in both)
    v_b = sum(len(data[b][i]["violations"]) for i in both)
    print(f"- naming violations on paired events: {a}={v_a} {b}={v_b}")
    ta = [i for i in git_both if data[a][i]["truncated_agree"] is False]
    tb = [i for i in git_both if data[b][i]["truncated_agree"] is False]
    print(f"- truncated flag disagreements with the emitter: {a}={len(ta)} {b}={len(tb)}")
