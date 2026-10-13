#!/usr/bin/env python3
"""Deterministic benchmark prep: live events, small/big split, 8-event batches, per-arm units."""
import json
import sys
from pathlib import Path

BENCH = Path(sys.argv[1])
SMALL_MAX_LINES = 60
BATCH = 8

events = [json.loads(l) for l in (BENCH / "events.jsonl").read_text().splitlines() if l.strip()]
live = [e for e in events if "skip" not in e]


def is_big(e):
    return e["source"] == "git" and sum(f["add"] + f["del"] for f in e.get("files", [])) > SMALL_MAX_LINES


rows = [{"id": e["id"], "source": e["source"], "big": is_big(e)} for e in live]
(BENCH / "live.json").write_text(json.dumps(rows, indent=0))

small_ids = [r["id"] for r in rows if not r["big"]]
big_ids = [r["id"] for r in rows if r["big"]]
batches = [small_ids[i:i + BATCH] for i in range(0, len(small_ids), BATCH)]

units_solo = [[r["id"]] for r in rows]                      # one unit per event, chronological
units_batched = sorted([[b] for b in big_ids] + batches,      # big alone, small in batches; keep chronology by first id
                       key=lambda u: [r["id"] for r in rows].index(u[0]))
(BENCH / "units_solo.json").write_text(json.dumps(units_solo))
(BENCH / "units_batched.json").write_text(json.dumps(units_batched))

print(json.dumps({
    "events": len(events), "live": len(live),
    "git_live": sum(1 for r in rows if r["source"] == "git"),
    "session_live": sum(1 for r in rows if r["source"] == "session"),
    "big": len(big_ids), "small": len(small_ids), "batches": len(batches),
    "units_solo": len(units_solo), "units_batched": len(units_batched),
    "first_big": big_ids[:1], "first_session": [r["id"] for r in rows if r["source"] == "session"][:1],
}))
