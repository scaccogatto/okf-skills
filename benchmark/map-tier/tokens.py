#!/usr/bin/env python3
"""Per-arm token usage from the workflow's agent transcripts (usage blocks on assistant messages).

usage: tokens.py <workflow-transcript-dir>
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

W = Path(sys.argv[1])
ARM_RE = re.compile(r"arms/([A-Z][0-9]?-[a-z]+-[a-z]+)/")
PHASE_KEYS = {"analyses": "map", "okf": "reduce"}

totals = defaultdict(lambda: defaultdict(int))
for f in sorted(W.glob("agent-*.jsonl")):
    arm, phase, model = None, None, None
    usage = defaultdict(int)
    calls = 0
    for line in f.read_text(errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except Exception:
            continue
        msg = rec.get("message") or {}
        if arm is None and rec.get("type") == "user":
            content = msg.get("content")
            text = content if isinstance(content, str) else " ".join(b.get("text", "") for b in content if isinstance(b, dict)) if isinstance(content, list) else ""
            m = ARM_RE.search(text)
            if m:
                arm = m.group(1)
                phase = "finalize" if "finalizing a reconstructed OKF bundle" in text else ("reduce" if "batch " in text and "Fold exactly these live events" in text else "map")
        if rec.get("type") == "assistant":
            u = msg.get("usage") or {}
            if u:
                calls += 1
                model = msg.get("model") or model
                for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
                    usage[k] += int(u.get(k) or 0)
    if arm is None:
        continue
    t = totals[(arm, phase, model)]
    t["agents"] += 1
    t["api_calls"] += calls
    for k, v in usage.items():
        t[k] += v

# Prices per million tokens (USD): input, output, cache read, cache write. Edit if the host differs.
PRICE = {
    "sonnet": (3.0, 15.0, 0.30, 3.75),
    "haiku": (1.0, 5.0, 0.10, 1.25),
}


def price_for(model):
    for k, v in PRICE.items():
        if model and k in model:
            return v
    return None


print("| arm | phase | model | agents | api_calls | input | output | cache_read | cache_write | est_usd |")
print("|---|---|---|---|---|---|---|---|---|---|")
grand = defaultdict(float)
for (arm, phase, model), t in sorted(totals.items()):
    pr = price_for(model)
    usd = None
    if pr:
        usd = (t["input_tokens"] * pr[0] + t["output_tokens"] * pr[1] + t["cache_read_input_tokens"] * pr[2] + t["cache_creation_input_tokens"] * pr[3]) / 1e6
        grand[arm] += usd
    print(f"| {arm} | {phase} | {model} | {t['agents']} | {t['api_calls']} | {t['input_tokens']} | {t['output_tokens']} | {t['cache_read_input_tokens']} | {t['cache_creation_input_tokens']} | {'' if usd is None else f'{usd:.2f}'} |")
print()
for arm, usd in sorted(grand.items()):
    print(f"{arm}: est ${usd:.2f}")
