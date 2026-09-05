#!/usr/bin/env python3
"""Assemble the benchmark Workflow script: meta + injected constants + workflow_body.js.

usage: build_workflow.py <repo-dir> <bench-dir> <out.js> [--today YYYY-MM-DD] [--skip-glob GLOB ...]

<bench-dir> must hold events.jsonl, units_solo.json and units_batched.json (see bench_prep.py).
The agent prompts are the bodies of agents/event-analyzer.md and agents/bundle-weaver.md at
<repo-dir>, injected verbatim (frontmatter stripped), so the run measures the committed files.
"""
import argparse
import json
import re
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("repo_dir")
p.add_argument("bench_dir")
p.add_argument("out")
p.add_argument("--today", default="2026-09-05")
p.add_argument("--skip-glob", action="append", default=["benchmark/*/runs/**", "docs/self.html", "docs/assets/**"])
args = p.parse_args()

repo, bench = Path(args.repo_dir).resolve(), Path(args.bench_dir).resolve()


def body_without_frontmatter(md: str) -> str:
    return re.sub(r"\A---\n.*?\n---\n", "", md, count=1, flags=re.S).strip()


analyzer = body_without_frontmatter((repo / "agents/event-analyzer.md").read_text())
weaver = body_without_frontmatter((repo / "agents/bundle-weaver.md").read_text())
units_solo = json.loads((bench / "units_solo.json").read_text())
units_batched = json.loads((bench / "units_batched.json").read_text())
live_ids = [u[0] for u in units_solo]

P = {
    "repo": str(repo),
    "events": str(bench / "events.jsonl"),
    "emitter": str(repo / "skills/backfill/scripts/okf_backfill_events.py"),
    "validate": str(repo / "skills/validate/scripts/okf_validate.py"),
    "bench": str(bench),
    "skipGlobs": args.skip_glob,
    "today": args.today,
}

meta = """export const meta = {
  name: 'backfill-map-tier-ab',
  description: 'A/B the backfill map phase: analyzer tier (sonnet vs haiku) x dispatch (solo vs batched); weave and finalize each arm',
  phases: [
    { title: 'Map', detail: 'analyzer calls for every arm, interleaved, bounded pool' },
    { title: 'Reduce', detail: 'one sequential weaver chain per arm, arms in parallel' },
    { title: 'Finalize', detail: 'indices, coverage, validator, anti-degeneration checks per arm' },
  ],
}
"""
consts = "\n".join([
    f"const ANALYZER_MD = {json.dumps(analyzer)};",
    f"const WEAVER_MD = {json.dumps(weaver)};",
    f"const UNITS_SOLO = {json.dumps(units_solo)};",
    f"const UNITS_BATCHED = {json.dumps(units_batched)};",
    f"const LIVE_IDS = {json.dumps(live_ids)};",
    f"const P = {json.dumps(P)};",
])
out = Path(args.out)
out.write_text(meta + consts + "\n" + (Path(__file__).parent / "workflow_body.js").read_text())
print(f"wrote {out} ({out.stat().st_size} bytes); solo_units={len(units_solo)} batched_units={len(units_batched)}")
