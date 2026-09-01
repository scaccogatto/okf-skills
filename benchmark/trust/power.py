#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""Item selection and power, the step between calibration and measurement (§7, §3.6).

Reads the calibration run (B0 only), keeps the items that demonstrably trap,
derives the heterogeneity proxy from their B0 spread, solves the committed
`(k, n)` rule, and writes the plan the measurement run then executes.

The §7 firewall runs in both directions, which is the point of it. `analyze.py`
refuses to read calibration data, because it selects items and must never enter
a result. This script refuses to read anything *else*, because a selection that
peeked at measurement data would condition on the outcome variable. Neither
guard is a comment asking to be remembered.

The plan is a separate file rather than an edit to `harness.yaml`: harness.yaml
is the pre-registration record and its comments carry the reasoning, so a
programmatic rewrite that dropped them would cost more than it saved.

Run:  uv run benchmark/trust/power.py <calibration/B0.jsonl>
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze import per_item_rates, select_n_and_k  # noqa: E402

TRUST_DIR = Path(__file__).resolve().parent


class CrossContamination(Exception):
    """A path was offered to the wrong side of the §7 firewall."""


def load_calibration(path: str | Path, config: dict, base: str | Path | None = None) -> list[dict]:
    """Read a calibration JSONL, refusing anything outside `calibration.outdir`.

    The inverse of `analyze.load_trials`. Selecting items on measurement runs and
    then comparing arms on those same runs is the §7 bias: it conditions on the
    outcome variable, invisibly, and in our favour.
    """
    p = Path(path).resolve()
    base = Path(base) if base is not None else TRUST_DIR
    outdir = (base / config["calibration"]["outdir"]).resolve()
    if outdir != p and outdir not in p.parents:
        raise CrossContamination(
            f"§7: refusing to select items from {p}, which is outside the calibration "
            f"outdir {outdir}. Item selection may only read calibration data.")
    rows = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def raw_stale_rates(trials: list[dict]) -> dict[str, float]:
    """Per-item RAW stale rate in B0: stale over all trials, `neither` included.

    §7 is explicit that the trap threshold is raw and not conditional. In B0,
    with the base prompt and the forced schema, `neither` should be rare; if it
    is not, that is itself reportable, and a conditional rate here would hide it.
    """
    counts = per_item_rates(trials, "B0")
    rates = {}
    for item, cell in counts.items():
        total = cell["stale"] + cell["fresh"] + cell["neither"]
        rates[item] = cell["stale"] / total if total else 0.0
    return rates


def surviving_items(rates: dict[str, float], min_rate: float) -> list[str]:
    """§7: an item counts only if it traps. The threshold is never lowered post hoc."""
    return sorted(i for i, r in rates.items() if r >= min_rate)


def heterogeneity_proxy(rates: dict[str, float], items: list[str]) -> float:
    """§3.6's declared conservative proxy: the B0 rate spread of surviving items.

    Conservative, argued rather than asserted: at 4 repetitions a per-item rate
    can only be 0, .25, .5, .75 or 1, so the spread is inflated by binomial noise,
    and the >= 50% cut narrows it by range restriction. At 4 reps the noise term
    dominates, so the proxy overstates the true between-item SD and errs toward
    demanding more data.
    """
    if len(items) < 2:
        return 0.0
    return statistics.pvariance([rates[i] for i in items])


def build_plan(calibration: list[dict], config: dict) -> dict:
    cfg = config["analysis"]
    rates = raw_stale_rates(calibration)
    kept = surviving_items(rates, cfg["min_b0_trap_rate"])
    proxy = heterogeneity_proxy(rates, kept)
    k, n = select_n_and_k(cfg["min_effect_pp"], proxy)
    return {
        "repetitions": k,
        "items": kept,
        "required_items": n,
        "underpowered": len(kept) < n,
        "heterogeneity_proxy": proxy,
        "calibration_rates": {i: rates[i] for i in sorted(rates)},
    }


def _print_plan(plan: dict, config: dict) -> None:
    kept, need = len(plan["items"]), plan["required_items"]
    print(f"candidates calibrated: {len(plan['calibration_rates'])}")
    print(f"items surviving the >= {config['analysis']['min_b0_trap_rate']:.0%} raw B0 cut: {kept}")
    print(f"heterogeneity proxy (B0 rate variance): {plan['heterogeneity_proxy']:.4f}")
    print(f"committed selection: k = {plan['repetitions']}, n required = {need}")
    if not plan["underpowered"]:
        return
    # §7 pre-registers this contingency rather than leaving it to the moment:
    # author more candidates and re-calibrate, or run underpowered and say so in
    # the headline. What is not on the list is lowering the threshold.
    print(f"\nUNDERPOWERED: {kept} surviving items, {need} required.", file=sys.stderr)
    print("§7 contingency: author more candidates and re-calibrate, or run "
          "underpowered and say so in the headline, not a footnote.", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Trust benchmark item selection and power (§7, §3.6).")
    ap.add_argument("calibration", type=Path, help="path to the calibration B0 runs.jsonl")
    ap.add_argument("--harness", type=Path, default=TRUST_DIR / "harness.yaml")
    ap.add_argument("--out", type=Path, default=TRUST_DIR / "measurement-plan.yaml")
    args = ap.parse_args(argv)

    config = yaml.safe_load(args.harness.read_text(encoding="utf-8"))
    try:
        calibration = load_calibration(args.calibration, config, base=args.harness.parent)
    except CrossContamination as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    plan = build_plan(calibration, config)
    _print_plan(plan, config)
    args.out.write_text(yaml.safe_dump(plan, sort_keys=False), encoding="utf-8")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
