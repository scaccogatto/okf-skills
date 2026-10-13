#!/usr/bin/env python3
"""Print paired analyses for the judgment layer: 5 largest commits + 5 session turns.

usage: spotread.py <bench-dir> <armX> <armY>
"""
import json
import sys
from pathlib import Path

B = sys.argv[1]
arms = sys.argv[2:4] if len(sys.argv) >= 4 else ["A-sonnet-solo", "B-haiku-solo"]
events = [json.loads(line) for line in Path(B, "events.jsonl").read_text().splitlines() if line.strip()]
ev = {e["id"]: e for e in events}
live = json.loads(Path(B, "live.json").read_text())
commits = sorted([r["id"] for r in live if r["source"] != "session"],
                 key=lambda i: -sum(f["add"] + f["del"] for f in ev[i]["files"]))
sessions = [r["id"] for r in live if r["source"] == "session"]
for i in commits[:5] + sessions[::14][:5]:
    fn = i.replace(":", "-") + ".md"
    head = ev[i].get("subject") or (ev[i].get("user") or "")[:110].replace("\n", " ")
    print("\n" + "=" * 100 + f"\nEVENT {i} | {head}")
    for arm in arms:
        try:
            body = Path(B, "arms", arm, "analyses", fn).read_text().split("---", 2)[2].strip()
        except (OSError, IndexError):
            body = "<MISSING>"
        print(f"\n--- {arm} ---\n{body}")
