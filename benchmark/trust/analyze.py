#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""Pre-registered analysis for the trust benchmark (PROTOCOL.md §3, §7, §9).

Every threshold is read from `harness.yaml`; nothing numeric here is a
derivation of its own. `analyze()` implements the primary contrast (§3.1,
A1 - B1 and only that one), the undefined-cell imputation rule (§3.2), the
neither-rate co-criterion (§3.3), the worst-case sensitivity recomputation
(§3.4), the BCa bootstrap over items (§3.6), and the §3.7 pass/fail verdict.

Rates are fractions throughout (0.0-1.0); `min_effect_pp` and `neither_cap_pp`
are converted from percentage points once, on read, never scattered.

Run:  uv run benchmark/trust/analyze.py <runs.jsonl>
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from pathlib import Path
from statistics import NormalDist

import yaml

GRADES = ("stale", "fresh", "neither")


class MissingTrials(Exception):
    """An arm has no trials at all for an item. See `_paired_rates`."""

# §3.6 commits the *rule*, not a harness value: the empty-cell floor (0.5^k <= 1%)
# and the 80% power target are the protocol's own constants, not a runtime knob,
# so they belong here rather than in harness.yaml.
EMPTY_CELL_CEILING = 0.01
POWER_TARGET = 0.80


def _empty_cell() -> dict:
    return {"stale": 0, "fresh": 0, "neither": 0, "conditional_rate": None}


def per_item_rates(trials: list[dict], arm: str) -> dict[str, dict]:
    """Per-item stale/fresh/neither counts and conditional rate, for one arm.

    Conditional rate is stale/(stale+fresh), §3.2's primary metric, defined
    over *committed* answers only, so a `neither`-heavy arm cannot manufacture
    a low rate by simply not answering. `None` when no answer was committed;
    callers apply the §3.2 imputation rule, this function reports raw fact.
    """
    counts: dict[str, dict] = {}
    for t in trials:
        if t["arm"] != arm:
            continue
        cell = counts.setdefault(t["item"], {"stale": 0, "fresh": 0, "neither": 0})
        cell[t["grade"]] += 1
    for cell in counts.values():
        denom = cell["stale"] + cell["fresh"]
        cell["conditional_rate"] = cell["stale"] / denom if denom else None
    return counts


def _imputed_rate(cell: dict) -> tuple[float, bool]:
    """§3.2 undefined-cell rule: zero committed answers imputes to 1.0 (all stale).

    Dropping the item would silently delete the hardest cases from the
    contrast in favour of the hypothesis; imputing as fully stale keeps it in
    and is punitive rather than favourable, on whichever arm it lands on.
    """
    if cell["conditional_rate"] is None:
        return 1.0, True
    return cell["conditional_rate"], False


def _worst_case_rate(cell: dict) -> float:
    """§3.4: every `neither` in A1 counted as `stale`, punitive on A1 only."""
    total = cell["stale"] + cell["fresh"] + cell["neither"]
    if total == 0:
        raise MissingTrials("worst-case rate requested for an item with no trials")
    return (cell["stale"] + cell["neither"]) / total


def _raw_grade_rate(trials: list[dict], arm: str, grade_name: str) -> float:
    """Raw (unconditional) rate of one grade over all trials in an arm."""
    arm_trials = [t for t in trials if t["arm"] == arm]
    if not arm_trials:
        return 0.0
    return sum(t["grade"] == grade_name for t in arm_trials) / len(arm_trials)


def _paired_rates(trials: list[dict], arm_x: str, arm_y: str) -> tuple[list[str], dict, dict]:
    """Imputed per-item rates for a pair of arms, over items present in BOTH.

    An item with trials that all came back `neither` is a refusal, and §3.2 says
    exactly what to do with it. An item with *no trials at all* in an arm is not
    that: it is missing data, a harness or budget failure, and imputing it as
    fully stale would launder a collection bug into an observation. The direction
    is what makes it unacceptable rather than merely untidy: a lost A1 cell
    penalises the treatment, but a lost B1 cell inflates the contrast in favour
    of the hypothesis, and neither would leave a trace in the output. So it
    aborts.
    """
    x_counts = per_item_rates(trials, arm_x)
    y_counts = per_item_rates(trials, arm_y)
    if not x_counts or not y_counts:
        # An arm with no trials whatsoever was not run: a calibration file holds
        # B0 only, and that is a phase, not a loss. Distinct from an arm that ran
        # and dropped some items, which is what the abort below is for.
        return [], {}, {}
    missing = (set(x_counts) ^ set(y_counts))
    if missing:
        raise MissingTrials(
            f"{arm_x}/{arm_y} contrast: no trials at all for {sorted(missing)}. "
            f"This is missing data, not a refusal (§3.2 covers refusals only); "
            f"re-run those cells rather than analysing around them.")
    items = sorted(x_counts)
    x_rates = {i: _imputed_rate(x_counts[i])[0] for i in items}
    y_rates = {i: _imputed_rate(y_counts[i])[0] for i in items}
    return items, x_rates, y_rates


def _descriptive_contrast(trials: list[dict], arm_x: str, arm_y: str) -> dict:
    """§3.1: A0-B0 and B1-B0 carry no confirmatory weight, point estimate only."""
    items, x_rates, y_rates = _paired_rates(trials, arm_x, arm_y)
    if not items:
        return {"point_estimate": None, "confirmatory": False, "items_evaluated": 0}
    diffs = [x_rates[i] - y_rates[i] for i in items]
    return {
        "point_estimate": statistics.mean(diffs),
        "confirmatory": False,
        "items_evaluated": len(items),
    }


def bootstrap_bca(
    paired_diffs: list[float], resamples: int, alpha: float = 0.05, seed: int = 0,
) -> tuple[float, float]:
    """BCa bootstrap CI over items (§3.6), stdlib only, seeded for reproducibility.

    Bias correction z0 comes from the proportion of resamples falling below the
    observed statistic; acceleration `a` comes from a jackknife over items (the
    unit of analysis, per §3.6, not a jackknife over trials).
    """
    n = len(paired_diffs)
    if n == 0:
        return (0.0, 0.0)
    if n == 1:
        return (paired_diffs[0], paired_diffs[0])  # no spread to bootstrap

    rng = random.Random(seed)
    dist = NormalDist()
    observed = statistics.mean(paired_diffs)

    resample_means = sorted(
        statistics.mean(paired_diffs[rng.randrange(n)] for _ in range(n))
        for _ in range(resamples)
    )

    below = sum(m < observed for m in resample_means)
    # clamp away from 0/1: inv_cdf is undefined there, and an all-below/all-above
    # resample set is possible on a small or near-degenerate sample
    p0 = min(max(below / resamples, 1 / (resamples + 1)), resamples / (resamples + 1))
    z0 = dist.inv_cdf(p0)

    total = sum(paired_diffs)
    jack_means = [(total - d) / (n - 1) for d in paired_diffs]
    jack_grand = statistics.mean(jack_means)
    num = sum((jack_grand - jm) ** 3 for jm in jack_means)
    den = 6 * (sum((jack_grand - jm) ** 2 for jm in jack_means) ** 1.5)
    a = num / den if den else 0.0

    def _percentile(z: float) -> float:
        denom = 1 - a * (z0 + z)
        denom = denom if denom else 1e-9  # degenerate acceleration: fall back rather than crash
        return dist.cdf(z0 + (z0 + z) / denom)

    p_lo = _percentile(dist.inv_cdf(alpha / 2))
    p_hi = _percentile(dist.inv_cdf(1 - alpha / 2))
    idx_lo = min(max(int(p_lo * resamples), 0), resamples - 1)
    idx_hi = min(max(int(p_hi * resamples), 0), resamples - 1)
    return resample_means[idx_lo], resample_means[idx_hi]


def _verdict(invalid: bool, ci: tuple[float, float], point_estimate: float,
             min_effect: float, co_criterion_holds: bool) -> str:
    """§3.7 falsification: CI includes zero, point estimate below floor, or the
    cap breached, all fail the claim; an invalidated undefined-cell rate
    overrides everything else rather than being adjusted (§3.2)."""
    if invalid:
        return "invalid"
    ci_includes_zero = ci[0] <= 0 <= ci[1]
    if ci_includes_zero or point_estimate < min_effect or not co_criterion_holds:
        return "fail"
    return "pass"


def analyze(trials: list[dict], config: dict, seed: int = 0) -> dict:
    cfg = config["analysis"]
    min_effect = cfg["min_effect_pp"] / 100
    neither_cap = cfg["neither_cap_pp"] / 100
    max_undef_rate = cfg["max_undefined_cell_rate"]
    resamples = cfg["bootstrap_resamples"]

    items, a1_rates, b1_rates = _paired_rates(trials, "A1", "B1")
    a1_counts = per_item_rates(trials, "A1")
    b1_counts = per_item_rates(trials, "B1")
    a1_undefined = {i for i in items if a1_counts.get(i, _empty_cell())["conditional_rate"] is None}
    b1_undefined = {i for i in items if b1_counts.get(i, _empty_cell())["conditional_rate"] is None}

    # §3.2: report per arm, never aggregated. Imputing on A1 penalises the
    # treatment, imputing on B1 inflates the contrast in its favour.
    undefined_counts = {"A1": len(a1_undefined), "B1": len(b1_undefined)}
    undefined_rate = ({arm: n / len(items) for arm, n in undefined_counts.items()}
                       if items else {"A1": 0.0, "B1": 0.0})
    # §3.2 invalidates on "affected items", which is the set of items affected in
    # either arm, not the worse of the two per-arm rates. The union is the
    # stricter reading and the one the sentence says; the per-arm split above is
    # for reporting, which §3.2 requires to stay unaggregated.
    affected = a1_undefined | b1_undefined
    affected_rate = len(affected) / len(items) if items else 0.0
    invalid = affected_rate > max_undef_rate

    paired_diffs = [a1_rates[i] - b1_rates[i] for i in items]
    point_estimate = statistics.mean(paired_diffs) if paired_diffs else 0.0
    ci = bootstrap_bca(paired_diffs, resamples, seed=seed) if paired_diffs else (0.0, 0.0)

    neither_rates = {"A1": _raw_grade_rate(trials, "A1", "neither"),
                      "B1": _raw_grade_rate(trials, "B1", "neither")}
    co_criterion_holds = neither_rates["A1"] <= neither_rates["B1"] + neither_cap

    worst_a1_rates = {i: _worst_case_rate(a1_counts.get(i, _empty_cell())) for i in items}
    worst_diffs = [worst_a1_rates[i] - b1_rates[i] for i in items]
    worst_case = {
        "point_estimate": statistics.mean(worst_diffs) if worst_diffs else 0.0,
        "ci": bootstrap_bca(worst_diffs, resamples, seed=seed) if worst_diffs else (0.0, 0.0),
        "note": "§3.4: every A1 `neither` counted as `stale`",
    }

    b1_exclusion = None
    if b1_undefined:
        kept = [i for i in items if i not in b1_undefined]
        excl_diffs = [a1_rates[i] - b1_rates[i] for i in kept]
        b1_exclusion = {
            "excluded_items": sorted(b1_undefined),
            "point_estimate": statistics.mean(excl_diffs) if excl_diffs else 0.0,
            "ci": bootstrap_bca(excl_diffs, resamples, seed=seed) if excl_diffs else (0.0, 0.0),
        }

    return {
        "items_evaluated": len(items),
        "primary_contrast": {"arms": ["A1", "B1"], "point_estimate": point_estimate,
                              "ci": ci, "confirmatory": True},
        "worst_case": worst_case,
        "neither_rates": neither_rates,
        "co_criterion_holds": co_criterion_holds,
        "undefined_cell_counts": undefined_counts,
        "undefined_cell_rate": undefined_rate,
        "undefined_affected_rate": affected_rate,
        "invalid": invalid,
        "b1_side_exclusion": b1_exclusion,
        "descriptive": {
            "A0_minus_B0": _descriptive_contrast(trials, "A0", "B0"),
            "B1_minus_B0": _descriptive_contrast(trials, "B1", "B0"),
        },
        # Rev 9, after the measurement run. `point_estimate` is A1 − B1 on the
        # conditional STALE rate, so the claim of §2 predicts a NEGATIVE number:
        # the treatment asserts superseded facts less often. §3.7's floor ("the
        # point estimate is below 15pp") is a floor on the effect size, i.e. on
        # the reduction, and the committed code compared the signed contrast
        # against it — which would have called a perfect result a failure. The
        # reduction is reported and tested here; the signed contrast is left
        # exactly as it was so both are on the record. This changes no verdict on
        # this run: §3.2 invalidates it before any of it is consulted.
        "effect_pp": -point_estimate,
        "verdict": _verdict(invalid, (-ci[1], -ci[0]), -point_estimate, min_effect,
                             co_criterion_holds),
    }


def select_k() -> int:
    """§3.6: smallest k with 0.5**k <= 1%, the empty-cell floor, not a power fit."""
    k = 1
    while 0.5 ** k > EMPTY_CELL_CEILING:
        k += 1
    return k


def power_n(k: int, min_effect_pp: float, heterogeneity: float,
            power_target: float = POWER_TARGET, alpha: float = 0.05) -> int:
    """§3.6 closed-form conservative bound: smallest n with power >= target at k reps.

    Per-item variance is the binomial worst case (p(1-p) <= 0.25) at k reps; the
    paired-diff variance sums both arms' worst case plus the declared
    heterogeneity term, with correlation between arms assumed zero (the pairing
    can only help, so zero is conservative).
    """
    effect = min_effect_pp / 100
    diff_var_per_item = 2 * (0.25 / k) + heterogeneity
    z_alpha = NormalDist().inv_cdf(1 - alpha / 2)
    n = 1
    while True:
        se = (diff_var_per_item / n) ** 0.5
        if NormalDist().cdf(effect / se - z_alpha) >= power_target:
            return n
        n += 1


def select_n_and_k(min_effect_pp: float, heterogeneity: float,
                    power_target: float = POWER_TARGET, alpha: float = 0.05) -> tuple[int, int]:
    """§3.6 committed selection order: k from the empty-cell floor, n solved after."""
    k = select_k()
    return k, power_n(k, min_effect_pp, heterogeneity, power_target, alpha)


def load_trials(path: str | Path, config: dict, base: str | Path | None = None) -> list[dict]:
    """Read a JSONL run file. Refuses anything under `calibration.outdir` (§7):
    calibration data selects items and feeds the §3.6 heterogeneity proxy, and
    must never enter a result, enforced here rather than left to memory.

    `base` is the directory `calibration.outdir` is relative to (the harness
    file's own directory). Resolving it against the caller's cwd instead would
    let the guard be walked around by running the script from elsewhere, which
    is not much of a guard.
    """
    p = Path(path).resolve()
    base = Path(base) if base is not None else Path(__file__).parent
    outdir = (base / config["calibration"]["outdir"]).resolve()
    if p == outdir or outdir in p.parents:
        raise ValueError(
            f"§7 discard rule: refusing to load {p}, which is under the calibration "
            f"outdir {outdir}, which is discarded entirely before measurement")
    trials = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                trials.append(json.loads(line))
    return trials


def _fmt_pp(rate: float) -> str:
    return f"{rate * 100:.1f}pp"


def _print_report(result: dict) -> None:
    print(f"items evaluated: {result['items_evaluated']}")
    pc = result["primary_contrast"]
    print(f"primary contrast (A1 - B1): {_fmt_pp(pc['point_estimate'])} "
          f"CI[{_fmt_pp(pc['ci'][0])}, {_fmt_pp(pc['ci'][1])}]")
    wc = result["worst_case"]
    print(f"worst case: {_fmt_pp(wc['point_estimate'])} "
          f"CI[{_fmt_pp(wc['ci'][0])}, {_fmt_pp(wc['ci'][1])}]  ({wc['note']})")
    print(f"neither rates: A1={_fmt_pp(result['neither_rates']['A1'])} "
          f"B1={_fmt_pp(result['neither_rates']['B1'])}  "
          f"co-criterion holds: {result['co_criterion_holds']}")
    print(f"undefined cells: A1={result['undefined_cell_counts']['A1']} "
          f"B1={result['undefined_cell_counts']['B1']} "
          f"(affected {_fmt_pp(result['undefined_affected_rate'])} of items)  "
          f"invalid: {result['invalid']}")
    if result["b1_side_exclusion"]:
        excl = result["b1_side_exclusion"]
        print(f"B1-side exclusion ({len(excl['excluded_items'])} items): "
              f"{_fmt_pp(excl['point_estimate'])} "
              f"CI[{_fmt_pp(excl['ci'][0])}, {_fmt_pp(excl['ci'][1])}]")
    for label, key in (("A0-B0", "A0_minus_B0"), ("B1-B0", "B1_minus_B0")):
        est = result["descriptive"][key]["point_estimate"]
        shown = "not run" if est is None else _fmt_pp(est)
        print(f"descriptive {label}: {shown} (no confirmatory weight)")
    print(f"verdict: {result['verdict']}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Trust benchmark pre-registered analysis (§3).")
    ap.add_argument("runs", type=Path, help="path to a measurement runs.jsonl")
    ap.add_argument("--harness", type=Path, default=Path(__file__).parent / "harness.yaml")
    ap.add_argument("--seed", type=int, default=0, help="bootstrap resampler seed")
    args = ap.parse_args()

    config = yaml.safe_load(args.harness.read_text(encoding="utf-8"))
    try:
        trials = load_trials(args.runs, config, base=args.harness.parent)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    result = analyze(trials, config, seed=args.seed)
    _print_report(result)
    return 0 if result["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
