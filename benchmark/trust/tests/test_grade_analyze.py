#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""Unit tests for grade.py and analyze.py (trust benchmark, §9 / §3 / §7).

Run:  uv run benchmark/trust/tests/test_grade_analyze.py
"""
from __future__ import annotations

import statistics
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from grade import extract_answer, grade, normalize  # noqa: E402
from analyze import (  # noqa: E402
    MissingTrials, analyze, bootstrap_bca, load_trials, per_item_rates, power_n,
    select_k,
)

F_OLD = "384 KiB"
F_NEW = "112 KiB"


def trial(item: str, arm: str, grade_val: str, rep: int = 0) -> dict:
    """A minimal trial matching the shared JSONL contract."""
    return {
        "item": item, "shape": "limit-changed", "arm": arm, "rep": rep,
        "answer": grade_val, "grade": grade_val, "response_id": f"msg_{item}_{arm}_{rep}",
        "model": "claude-opus-5", "usage": {}, "request": {},
    }


class TestGraderFidelity(unittest.TestCase):
    """§9: encode each adversarial case named in the protocol as one test."""

    def test_both_values_in_narrative_with_correct_in_field_grades_fresh(self):
        text = f"It was {F_OLD}, now it's {F_NEW}.\n\nANSWER: {F_NEW}"
        self.assertEqual(grade(text, F_OLD, F_NEW), "fresh")

    def test_both_values_in_prose_with_correct_one_in_field(self):
        text = f"Some say {F_OLD}, others say {F_NEW}, hard to tell.\nANSWER: {F_NEW}"
        self.assertEqual(grade(text, F_OLD, F_NEW), "fresh")

    def test_f_old_quoted_to_reject_it_grades_fresh(self):
        text = (f'The old value "{F_OLD}" is no longer correct.\n'
                f"ANSWER: {F_NEW}")
        self.assertEqual(grade(text, F_OLD, F_NEW), "fresh")

    def test_numeric_formatting_variants_all_match(self):
        for variant in ("384 KiB", "384KiB", "384 kib", "`384 KiB`", " 384  KiB ", "384 KiB."):
            self.assertEqual(grade(f"ANSWER: {variant}", F_OLD, F_NEW), "stale", variant)

    def test_missing_answer_line_grades_neither(self):
        self.assertEqual(grade(f"I believe it is {F_NEW}.", F_OLD, F_NEW), "neither")

    def test_multiple_answer_lines_take_the_last(self):
        text = f"ANSWER: {F_OLD}\nOn reflection,\nANSWER: {F_NEW}"
        self.assertEqual(grade(text, F_OLD, F_NEW), "fresh")
        self.assertEqual(extract_answer(text), F_NEW)

    def test_unrelated_value_grades_neither(self):
        self.assertEqual(grade("ANSWER: 7 furlongs", F_OLD, F_NEW), "neither")

    def test_normalize_strips_quotes_backticks_and_trailing_period(self):
        self.assertEqual(normalize('"384 KiB".'), normalize("384 kib"))
        # The digit-unit gap is no longer collapsed in `normalize` (rev 7: that
        # collapse hid the "1024 tasks" case); the equivalence is asserted where
        # it is now decided, at the grade.
        self.assertEqual(grade("ANSWER: `384 KiB`", "384KiB", "112 KiB"), "stale")


class TestEffectDirection(unittest.TestCase):
    """Rev 9: the claim predicts A1's conditional stale rate BELOW B1's, so the
    effect §3.7 thresholds is the reduction. The committed code compared the
    signed contrast against the floor, which turns a perfect result into a
    failure; no test exercised it until a run produced one."""

    def _trials(self, a1_stale, b1_stale, items=12, reps=8):
        rows = []
        for n in range(items):
            for arm, stale in (("A1", a1_stale), ("B1", b1_stale)):
                for rep in range(reps):
                    rows.append({"item": f"i{n}", "arm": arm, "rep": rep,
                                  "grade": "stale" if rep < stale else "fresh"})
        return rows

    def test_treatment_that_removes_every_stale_answer_is_not_called_a_failure(self):
        result = analyze(self._trials(a1_stale=0, b1_stale=8), CONFIG)
        self.assertLess(result["primary_contrast"]["point_estimate"], 0)
        self.assertAlmostEqual(result["effect_pp"], 1.0)
        self.assertEqual(result["verdict"], "pass")

    def test_treatment_that_makes_it_worse_fails(self):
        result = analyze(self._trials(a1_stale=8, b1_stale=0), CONFIG)
        self.assertAlmostEqual(result["effect_pp"], -1.0)
        self.assertEqual(result["verdict"], "fail")

    def test_no_difference_fails(self):
        result = analyze(self._trials(a1_stale=4, b1_stale=4), CONFIG)
        self.assertEqual(result["effect_pp"], 0.0)
        self.assertEqual(result["verdict"], "fail")


class TestGraderUnitAndArticleTolerance(unittest.TestCase):
    """§9, rev 7. Calibration produced answers that assert the value exactly and
    grade `neither` on wording: "1024 tasks" against a value of "1024", "the
    client" against "client". The tolerance is one trailing word and a leading
    article, and no more than that."""

    def test_one_trailing_unit_word_still_matches(self):
        self.assertEqual(grade("ANSWER: 1024 tasks", "1024", "384"), "stale")
        self.assertEqual(grade("ANSWER: 104 shards", "192", "104"), "fresh")

    def test_attributive_hyphen_is_not_a_difference(self):
        self.assertEqual(
            grade("ANSWER: the higher-priority task", "higher priority", "earlier submission"),
            "stale")

    def test_leading_article_is_not_a_difference(self):
        self.assertEqual(grade("ANSWER: the client", "gateway", "client"), "fresh")

    def test_two_trailing_words_do_not_match(self):
        # "1024 tasks per lane" is a sentence starting to explain, and an
        # explanation is where the other value tends to appear.
        self.assertEqual(grade("ANSWER: 1024 tasks per lane", "1024", "384"), "neither")

    def test_a_hedge_naming_both_values_is_still_neither(self):
        self.assertEqual(
            grade("ANSWER: 1024 tasks, though the current limit is 384", "1024", "384"),
            "neither")

    def test_an_answer_matching_both_values_is_neither(self):
        # One value being a prefix of the other must not be resolved by
        # whichever the grader happens to test first.
        self.assertEqual(grade("ANSWER: 384 KiB", "384", "384 KiB"), "neither")


class TestPerItemRates(unittest.TestCase):
    def test_conditional_rate_ignores_neither(self):
        trials = [trial("i1", "A1", "stale"), trial("i1", "A1", "stale"),
                  trial("i1", "A1", "fresh"), trial("i1", "A1", "neither")]
        rates = per_item_rates(trials, "A1")
        self.assertAlmostEqual(rates["i1"]["conditional_rate"], 2 / 3)

    def test_zero_committed_answers_is_undefined_not_zero(self):
        trials = [trial("i1", "A1", "neither"), trial("i1", "A1", "neither")]
        rates = per_item_rates(trials, "A1")
        self.assertIsNone(rates["i1"]["conditional_rate"])


CONFIG = {
    "analysis": {
        "min_effect_pp": 15,
        "neither_cap_pp": 10,
        "max_undefined_cell_rate": 0.10,
        "bootstrap_resamples": 500,
    },
    "calibration": {"outdir": "runs/calibration"},
}


class TestAnalyze(unittest.TestCase):
    def test_all_neither_a1_item_is_imputed_to_one_and_stays_in(self):
        # a single item, all-neither in A1: the §3.2 undefined-cell rule keeps
        # it in the contrast with conditional rate imputed to 1.0
        trials = (
            [trial("i1", "A1", "neither")] * 4 +
            [trial("i1", "B1", "stale")] * 1 + [trial("i1", "B1", "fresh")] * 3
        )
        result = analyze(trials, CONFIG, seed=1)
        self.assertEqual(result["items_evaluated"], 1)
        self.assertAlmostEqual(result["primary_contrast"]["point_estimate"], 1.0 - 0.25)
        self.assertEqual(result["undefined_cell_counts"], {"A1": 1, "B1": 0})

    def test_imputation_counts_are_split_per_arm_not_aggregated(self):
        trials = (
            [trial("i1", "A1", "neither")] * 4 + [trial("i1", "B1", "stale")] * 4 +
            [trial("i2", "A1", "stale")] * 4 + [trial("i2", "B1", "neither")] * 4
        )
        result = analyze(trials, CONFIG, seed=1)
        self.assertEqual(result["undefined_cell_counts"], {"A1": 1, "B1": 1})

    def test_co_criterion_boundary_holds_at_exactly_the_cap(self):
        # 10 trials/arm on one item: neither_A1=20%, neither_B1=10% -> diff is
        # exactly the 10pp cap, and the rule is <=, so it must still hold
        trials = (
            [trial("i1", "A1", "stale")] * 8 + [trial("i1", "A1", "neither")] * 2 +
            [trial("i1", "B1", "stale")] * 9 + [trial("i1", "B1", "neither")] * 1
        )
        result = analyze(trials, CONFIG, seed=1)
        self.assertTrue(result["co_criterion_holds"])

    def test_co_criterion_breach_just_past_the_cap(self):
        trials = (
            [trial("i1", "A1", "stale")] * 7 + [trial("i1", "A1", "neither")] * 3 +
            [trial("i1", "B1", "stale")] * 9 + [trial("i1", "B1", "neither")] * 1
        )
        result = analyze(trials, CONFIG, seed=1)
        self.assertFalse(result["co_criterion_holds"])

    def test_worst_case_recomputation_counts_a1_neither_as_stale(self):
        # A1: 2 stale, 2 neither -> conditional rate 1.0 but worst-case counts
        # the neithers as stale too: (2+2)/4 = 1.0, same here; use a case where
        # committed answers exist to show the two diverge
        trials = (
            [trial("i1", "A1", "stale")] * 1 + [trial("i1", "A1", "fresh")] * 1 +
            [trial("i1", "A1", "neither")] * 2 + [trial("i1", "B1", "fresh")] * 4
        )
        result = analyze(trials, CONFIG, seed=1)
        # ordinary conditional rate: 1/(1+1) = 0.5
        self.assertAlmostEqual(result["primary_contrast"]["point_estimate"], 0.5)
        # worst case: (1 stale + 2 neither)/4 = 0.75, strictly worse for A1
        self.assertAlmostEqual(result["worst_case"]["point_estimate"], 0.75)
        self.assertGreater(result["worst_case"]["point_estimate"],
                            result["primary_contrast"]["point_estimate"])

    def test_undefined_cell_rate_above_ceiling_is_invalid(self):
        # 2 of 10 items undefined in A1 = 20% > 10% ceiling
        trials = []
        for n in range(10):
            item = f"i{n}"
            if n < 2:
                trials += [trial(item, "A1", "neither")] * 4
            else:
                trials += [trial(item, "A1", "stale")] * 4
            trials += [trial(item, "B1", "fresh")] * 4
        result = analyze(trials, CONFIG, seed=1)
        self.assertTrue(result["invalid"])
        self.assertEqual(result["verdict"], "invalid")

    def test_undefined_cell_rate_at_or_below_ceiling_is_not_invalid(self):
        trials = []
        for n in range(20):
            item = f"i{n}"
            if n < 2:  # 2/20 = 10%, at the ceiling
                trials += [trial(item, "A1", "neither")] * 4
            else:
                trials += [trial(item, "A1", "stale")] * 4
            trials += [trial(item, "B1", "fresh")] * 4
        result = analyze(trials, CONFIG, seed=1)
        self.assertFalse(result["invalid"])

    def test_b1_side_exclusion_recomputes_without_b1_undefined_items(self):
        trials = (
            # i1: B1 all-neither -> imputed 1.0 on B1, inflates the contrast in
            # A1's favour; the §3.2 rule requires an exclusion recomputation
            [trial("i1", "A1", "stale")] * 4 + [trial("i1", "B1", "neither")] * 4 +
            [trial("i2", "A1", "stale")] * 4 + [trial("i2", "B1", "fresh")] * 4
        )
        result = analyze(trials, CONFIG, seed=1)
        self.assertIsNotNone(result["b1_side_exclusion"])
        self.assertEqual(result["b1_side_exclusion"]["excluded_items"], ["i1"])
        # excluding i1 leaves only i2: A1 rate 1.0, B1 rate 0.0 -> diff 1.0
        self.assertAlmostEqual(result["b1_side_exclusion"]["point_estimate"], 1.0)

    def test_no_b1_side_exclusion_when_no_b1_imputation_occurred(self):
        trials = [trial("i1", "A1", "stale")] * 4 + [trial("i1", "B1", "fresh")] * 4
        result = analyze(trials, CONFIG, seed=1)
        self.assertIsNone(result["b1_side_exclusion"])


class TestLoadTrials(unittest.TestCase):
    def test_refuses_the_calibration_outdir(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            calib = root / "runs" / "calibration"
            calib.mkdir(parents=True)
            path = calib / "runs.jsonl"
            path.write_text('{"item":"i1","arm":"B0","grade":"stale"}\n', encoding="utf-8")
            config = {"calibration": {"outdir": str(calib)}}
            with self.assertRaises(ValueError) as ctx:
                load_trials(path, config)
            self.assertIn("§7", str(ctx.exception))

    def test_reads_a_measurement_path_fine(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "runs" / "calibration").mkdir(parents=True)
            path = root / "runs" / "measurement" / "runs.jsonl"
            path.parent.mkdir(parents=True)
            path.write_text('{"item":"i1","arm":"B0","grade":"stale"}\n', encoding="utf-8")
            config = {"calibration": {"outdir": str(root / "runs" / "calibration")}}
            trials = load_trials(path, config)
            self.assertEqual(len(trials), 1)


class TestBootstrapBca(unittest.TestCase):
    def test_ci_brackets_a_known_synthetic_mean(self):
        rng_source = statistics.NormalDist(mu=0.20, sigma=0.05)
        # deterministic synthetic "items": evenly spaced quantiles of a normal
        # with a known mean, so the true mean is exactly recoverable
        n = 60
        data = [rng_source.inv_cdf((i + 0.5) / n) for i in range(n)]
        lo, hi = bootstrap_bca(data, resamples=2000, seed=42)
        self.assertLess(lo, 0.20)
        self.assertGreater(hi, 0.20)

    def test_degenerate_single_item_returns_the_point(self):
        self.assertEqual(bootstrap_bca([0.3], resamples=100, seed=0), (0.3, 0.3))


class TestPower(unittest.TestCase):
    def test_selected_k_meets_the_empty_cell_floor(self):
        k = select_k()
        self.assertEqual(k, 7)
        self.assertLessEqual(0.5 ** k, 0.01)
        self.assertGreater(0.5 ** (k - 1), 0.01)

    def test_power_n_increases_with_smaller_effect(self):
        n_big_effect = power_n(k=7, min_effect_pp=15, heterogeneity=0.01)
        n_small_effect = power_n(k=7, min_effect_pp=5, heterogeneity=0.01)
        self.assertGreater(n_small_effect, n_big_effect)



class TestMissingData(unittest.TestCase):
    """An arm that ran and lost items is a collection failure, not a refusal.

    §3.2 imputes an item whose answers all came back `neither`. It says nothing
    about an item with no trials at all, and treating the two alike would launder
    a harness or budget failure into a maximally-stale observation, in a
    direction that favours the hypothesis whenever the loss lands on B1.
    """

    def test_item_missing_from_one_primary_arm_aborts(self):
        trials = [trial("i0", "A1", "fresh"), trial("i1", "A1", "fresh"),
                  trial("i0", "B1", "stale")]
        with self.assertRaises(MissingTrials) as ctx:
            analyze(trials, CONFIG, seed=1)
        self.assertIn("i1", str(ctx.exception))

    def test_an_arm_absent_entirely_is_a_phase_not_a_loss(self):
        # A calibration file holds B0 only; the descriptive contrasts that need
        # the missing arms report "not run" instead of aborting the whole report.
        trials = [trial("i0", "A1", "fresh"), trial("i0", "B1", "stale"),
                  trial("i1", "A1", "fresh"), trial("i1", "B1", "stale")]
        result = analyze(trials, CONFIG, seed=1)
        self.assertIsNone(result["descriptive"]["A0_minus_B0"]["point_estimate"])
        self.assertEqual(result["descriptive"]["A0_minus_B0"]["items_evaluated"], 0)


class TestInvalidationSet(unittest.TestCase):
    """§3.2 invalidates on the items affected in *either* arm, not per-arm."""

    def test_union_across_arms_trips_the_ceiling_that_neither_arm_trips_alone(self):
        # 10 items, 1 undefined in A1 and 1 (a different one) in B1: each arm is
        # at 10%, which does not exceed the 10% ceiling, but the union is 20%.
        trials = []
        for n in range(10):
            item = f"i{n}"
            for arm in ("A1", "B1"):
                undefined = (arm == "A1" and n == 0) or (arm == "B1" and n == 1)
                g = "neither" if undefined else "stale"
                trials.append(trial(item, arm, g))
        result = analyze(trials, CONFIG, seed=1)
        self.assertEqual(result["undefined_cell_counts"], {"A1": 1, "B1": 1})
        self.assertAlmostEqual(result["undefined_cell_rate"]["A1"], 0.1)
        self.assertAlmostEqual(result["undefined_affected_rate"], 0.2)
        self.assertTrue(result["invalid"])
        self.assertEqual(result["verdict"], "invalid")


class TestCalibrationGuardIsCwdIndependent(unittest.TestCase):
    """§7's discard rule has to hold wherever the script is run from."""

    def test_relative_outdir_resolves_against_the_harness_not_the_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            calib = base / "runs" / "calibration"
            calib.mkdir(parents=True)
            path = calib / "runs.jsonl"
            path.write_text("", encoding="utf-8")
            config = {"calibration": {"outdir": "runs/calibration"}}
            with self.assertRaises(ValueError):
                load_trials(path, config, base=base)

if __name__ == "__main__":
    unittest.main(verbosity=2)
