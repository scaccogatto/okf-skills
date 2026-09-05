#!/usr/bin/env python3
"""Ground truth: run the emitter on every live git event and record its declared truncation."""
import json
import subprocess
import sys
from pathlib import Path

BENCH = Path(sys.argv[1])
EMITTER = sys.argv[2]
REPO = sys.argv[3]
SKIP = sys.argv[4:]

live = json.loads((BENCH / "live.json").read_text())
events = {json.loads(l)["id"]: json.loads(l) for l in (BENCH / "events.jsonl").read_text().splitlines() if l.strip()}

truth, detail = {}, {}
for row in live:
    if row["source"] != "git":
        continue
    sha = events[row["id"]]["sha"]
    cmd = ["uv", "run", EMITTER, REPO, "--show", sha]
    for g in SKIP:
        cmd += ["--skip-globs", g]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    last = out.rstrip("\n").splitlines()[-1]
    kv = dict(p.split("=") for p in last.strip("[]").replace("diff: ", "").split())
    truth[row["id"]] = kv["truncated"] == "true"
    detail[row["id"]] = {**kv, "chars": len(out), "lines": out.count("\n")}

(BENCH / "truth.json").write_text(json.dumps(truth, indent=0))
(BENCH / "truth_detail.json").write_text(json.dumps(detail, indent=0))
chars = [d["chars"] for d in detail.values()]
print(json.dumps({
    "git_events": len(truth), "truncated": sum(truth.values()),
    "max_chars": max(chars), "mean_chars": sum(chars) // len(chars),
    "max_lines": max(d["lines"] for d in detail.values()),
}))
