#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""Unit tests for power.py, the calibration-to-measurement step (§7, §3.6).

Run:  uv run benchmark/trust/tests/test_power.py
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from power import (  # noqa: E402
    CrossContamination, build_plan, heterogeneity_proxy, load_calibration,
    raw_stale_rates, surviving_items,
)

CONFIG = {
    "calibration": {"outdir": "runs/calibration"},
    "analysis": {"min_b0_trap_rate": 0.50, "min_effect_pp": 15},
}


def b0(item: str, grades: list[str]) -> list[dict]:
    return [{"item": item, "shape": "s", "arm": "B0", "rep": i, "grade": g}
            for i, g in enumerate(grades)]


class TestRawRate(unittest.TestCase):
    """§7 is explicit: the trap threshold is raw, not conditional."""

    def test_neither_counts_against_the_raw_rate(self):
        # 2 stale, 1 fresh, 1 neither. Conditional would be 2/3 = 67% and would
        # pass the cut; raw is 2/4 = 50%, which is what §7 asks for.
        rates = raw_stale_rates(b0("i0", ["stale", "stale", "fresh", "neither"]))
        self.assertAlmostEqual(rates["i0"], 0.5)

    def test_an_item_that_never_traps_is_dropped(self):
        trials = b0("keeps", ["stale"] * 4) + b0("drops", ["fresh"] * 4)
        rates = raw_stale_rates(trials)
        self.assertEqual(surviving_items(rates, 0.50), ["keeps"])

    def test_the_threshold_is_inclusive(self):
        rates = raw_stale_rates(b0("i0", ["stale", "stale", "fresh", "fresh"]))
        self.assertEqual(surviving_items(rates, 0.50), ["i0"])


class TestHeterogeneity(unittest.TestCase):
    def test_identical_items_have_no_spread(self):
        rates = {"a": 0.75, "b": 0.75}
        self.assertEqual(heterogeneity_proxy(rates, ["a", "b"]), 0.0)

    def test_a_single_surviving_item_has_no_spread_to_measure(self):
        self.assertEqual(heterogeneity_proxy({"a": 0.75}, ["a"]), 0.0)

    def test_spread_grows_with_dispersion(self):
        tight = heterogeneity_proxy({"a": 0.5, "b": 0.75}, ["a", "b"])
        wide = heterogeneity_proxy({"a": 0.5, "b": 1.0}, ["a", "b"])
        self.assertLess(tight, wide)


class TestPlan(unittest.TestCase):
    def test_k_comes_from_the_empty_cell_floor_not_from_power(self):
        trials = [t for n in range(4) for t in b0(f"i{n}", ["stale"] * 4)]
        plan = build_plan(trials, CONFIG)
        # §3.6: smallest k with 0.5**k <= 1%
        self.assertEqual(plan["repetitions"], 7)

    def test_too_few_surviving_items_is_flagged_not_fixed(self):
        # §7 pre-registers the contingency: author more candidates and
        # re-calibrate, or run underpowered and say so. Never lower the cut.
        trials = [t for n in range(2) for t in b0(f"i{n}", ["stale"] * 4)]
        plan = build_plan(trials, CONFIG)
        self.assertTrue(plan["underpowered"])
        self.assertLess(len(plan["items"]), plan["required_items"])

    def test_every_calibrated_rate_is_reported_not_just_survivors(self):
        trials = b0("keeps", ["stale"] * 4) + b0("drops", ["fresh"] * 4)
        plan = build_plan(trials, CONFIG)
        self.assertEqual(plan["items"], ["keeps"])
        self.assertEqual(sorted(plan["calibration_rates"]), ["drops", "keeps"])


class TestFirewall(unittest.TestCase):
    """§7 runs in both directions: selection reads only calibration, results
    read only measurement. One guard without the other is half a firewall."""

    def test_selection_refuses_a_measurement_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            measurement = base / "runs" / "measurement"
            measurement.mkdir(parents=True)
            path = measurement / "A1.jsonl"
            path.write_text("", encoding="utf-8")
            with self.assertRaises(CrossContamination):
                load_calibration(path, CONFIG, base=base)

    def test_selection_accepts_the_calibration_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            calib = base / "runs" / "calibration"
            calib.mkdir(parents=True)
            path = calib / "B0.jsonl"
            row = {"item": "i0", "shape": "s", "arm": "B0", "rep": 0, "grade": "stale"}
            path.write_text(json.dumps(row) + "\n", encoding="utf-8")
            self.assertEqual(load_calibration(path, CONFIG, base=base), [row])


if __name__ == "__main__":
    unittest.main(verbosity=2)
