#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Pre-registered analysis for the gate benchmark (#48, PROTOCOL.md §6).

Two contrasts, both paired by item and bootstrapped over items:

  write side  gate − nogate, on the end-to-end stale rate
  read side   marked − unmarked (and expired − unmarked), on the same metric

The metric is the RAW stale rate, not #40's conditional one (§6.2): every state
here has a reachable correct answer, because the implementation artifact stating
the current value is present in every corpus, so a refusal is a refusal rather
than an artefact of the design.

Effects are reported as REDUCTIONS: a mechanism that helps produces a positive
number. #40's committed analysis compared a signed contrast against a positive
floor and would have called a perfect result a failure; that defect is why the
direction is tested here before the run rather than after it.
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
from pathlib import Path

MIN_EFFECT = 0.15   # §6.4, an a priori judgment, as in #40
RESAMPLES = 10000


def per_item_stale_rate(rows: list[dict], key: str, value: str) -> dict[str, float]:
    """Raw stale rate per item within one arm or state."""
    counts: dict[str, list[int]] = {}
    for row in rows:
        if row.get(key) != value:
            continue
        item = counts.setdefault(row["item"], [0, 0])
        item[1] += 1
        if row["grade"] == "stale":
            item[0] += 1
    return {item: stale / total for item, (stale, total) in counts.items() if total}


def paired_reduction(rows: list[dict], key: str, treatment: str, control: str) -> tuple[list[str], list[float]]:
    """Per-item reduction in stale rate, control minus treatment.

    Positive means the treatment asserts superseded facts LESS often, which is
    what every mechanism here claims to do.
    """
    t = per_item_stale_rate(rows, key, treatment)
    c = per_item_stale_rate(rows, key, control)
    items = sorted(set(t) & set(c))
    return items, [c[i] - t[i] for i in items]


def bootstrap_ci(values: list[float], resamples: int = RESAMPLES, seed: int = 0) -> tuple[float, float]:
    if not values:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(values)
    means = sorted(statistics.mean(rng.choices(values, k=n)) for _ in range(resamples))
    lo = means[int(0.025 * resamples)]
    hi = means[min(int(0.975 * resamples), resamples - 1)]
    return (lo, hi)


def contrast(rows: list[dict], key: str, treatment: str, control: str, seed: int = 0) -> dict:
    items, diffs = paired_reduction(rows, key, treatment, control)
    point = statistics.mean(diffs) if diffs else 0.0
    ci = bootstrap_ci(diffs, seed=seed)
    return {
        "treatment": treatment,
        "control": control,
        "items": len(items),
        "reduction": point,
        "ci": ci,
        "verdict": ("pass" if ci[0] > 0 and point >= MIN_EFFECT else "fail"),
    }


def refusal_rate(rows: list[dict], key: str, value: str) -> float:
    subset = [r for r in rows if r.get(key) == value]
    return sum(1 for r in subset if r["grade"] == "neither") / len(subset) if subset else 0.0


def analyze(endtoend: list[dict], states: list[dict], seed: int = 0) -> dict:
    return {
        "write_side": contrast(endtoend, "arm", "gate", "nogate", seed),
        "read_side_marked": contrast(states, "state", "stale_marked", "stale_unmarked", seed),
        "read_side_expired": contrast(states, "state", "stale_expired", "stale_unmarked", seed),
        "stale_rates": {
            **{f"arm:{a}": statistics.mean(per_item_stale_rate(endtoend, "arm", a).values() or [0])
                for a in ("nogate", "gate") if per_item_stale_rate(endtoend, "arm", a)},
            **{f"state:{s}": statistics.mean(per_item_stale_rate(states, "state", s).values() or [0])
                for s in ("synced", "stale_unmarked", "stale_expired", "stale_marked")
                if per_item_stale_rate(states, "state", s)},
        },
        "refusal_rates": {
            **{f"arm:{a}": refusal_rate(endtoend, "arm", a) for a in ("nogate", "gate")},
            **{f"state:{s}": refusal_rate(states, "state", s)
                for s in ("synced", "stale_unmarked", "stale_expired", "stale_marked")},
        },
        "spontaneous_sync": {
            arm: statistics.mean([1.0 - r["doc_untouched"] for r in endtoend if r["arm"] == arm])
            for arm in ("nogate", "gate")
            if any(r["arm"] == arm for r in endtoend)
        },
    }


def _load(path: Path | None) -> list[dict]:
    if path is None or not path.is_file():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _fmt(x: float) -> str:
    return f"{x * 100:.1f}pp"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--endtoend", type=Path)
    ap.add_argument("--states", type=Path)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    result = analyze(_load(args.endtoend), _load(args.states), args.seed)
    for name in ("write_side", "read_side_marked", "read_side_expired"):
        c = result[name]
        print(f"{name:20} {c['treatment']} vs {c['control']}: reduction {_fmt(c['reduction'])} "
              f"CI[{_fmt(c['ci'][0])}, {_fmt(c['ci'][1])}]  items={c['items']}  {c['verdict']}")
    print("\nstale rates:", {k: _fmt(v) for k, v in result["stale_rates"].items()})
    print("refusal rates:", {k: _fmt(v) for k, v in result["refusal_rates"].items()})
    print("documentation touched by the writer:",
          {k: _fmt(v) for k, v in result["spontaneous_sync"].items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
