#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""Tests for the gate benchmark's harness and analysis (#48).

The direction tests exist because #40's committed analysis had its effect sign
inverted and no test exercised it: a treatment that removed every wrong answer
would have been reported as a failure, and the defect surfaced only when a real
result arrived. Here they run before the measurement, not after it.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

GATE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GATE_DIR))

from analyze import analyze, contrast, per_item_stale_rate  # noqa: E402
from pipeline import (  # noqa: E402
    AGENTS_MD,
    STATES,
    WRITER_DOC_STALE_AFTER,
    artifact_text,
    build_consumer_command,
    build_writer_command,
    doc_for_state,
    grade_writer,
    selected_items,
    writer_doc,
    writer_prompt,
)
from pipeline import WriterRun  # noqa: E402
import pipeline as gate_run  # noqa: E402
sys.path.insert(0, str(GATE_DIR.parent / "trust"))
from run import load_harness, parsed_meta  # noqa: E402

HARNESS = load_harness()


def rows(key, value, item, stale, total):
    return [{"item": item, key: value, "grade": "stale" if i < stale else "fresh"}
            for i in range(total)]


class TestEffectDirection(unittest.TestCase):
    def test_a_mechanism_that_helps_reports_a_positive_reduction(self):
        data = []
        for n in range(10):
            data += rows("state", "stale_unmarked", f"i{n}", 8, 8)
            data += rows("state", "stale_marked", f"i{n}", 0, 8)
        c = contrast(data, "state", "stale_marked", "stale_unmarked")
        self.assertAlmostEqual(c["reduction"], 1.0)
        self.assertEqual(c["verdict"], "pass")

    def test_a_mechanism_that_harms_reports_a_negative_reduction(self):
        data = []
        for n in range(10):
            data += rows("state", "stale_unmarked", f"i{n}", 0, 8)
            data += rows("state", "stale_marked", f"i{n}", 8, 8)
        c = contrast(data, "state", "stale_marked", "stale_unmarked")
        self.assertAlmostEqual(c["reduction"], -1.0)
        self.assertEqual(c["verdict"], "fail")

    def test_no_difference_fails_rather_than_passing_on_a_wide_ci(self):
        data = []
        for n in range(10):
            data += rows("state", "stale_unmarked", f"i{n}", 4, 8)
            data += rows("state", "stale_marked", f"i{n}", 4, 8)
        c = contrast(data, "state", "stale_marked", "stale_unmarked")
        self.assertEqual(c["reduction"], 0.0)
        self.assertEqual(c["verdict"], "fail")

    def test_an_effect_below_the_floor_fails_even_with_a_clean_ci(self):
        data = []
        for n in range(20):
            data += rows("state", "stale_unmarked", f"i{n}", 8, 8)
            data += rows("state", "stale_marked", f"i{n}", 7, 8)  # 12.5pp, under 15
        c = contrast(data, "state", "stale_marked", "stale_unmarked")
        self.assertLess(c["reduction"], 0.15)
        self.assertEqual(c["verdict"], "fail")

    def test_pairing_uses_only_items_present_in_both(self):
        data = rows("state", "stale_unmarked", "shared", 8, 8) + \
                rows("state", "stale_marked", "shared", 0, 8) + \
                rows("state", "stale_unmarked", "orphan", 8, 8)
        c = contrast(data, "state", "stale_marked", "stale_unmarked")
        self.assertEqual(c["items"], 1)


class TestCorpusStates(unittest.TestCase):
    def setUp(self):
        self.item = selected_items()[0]

    def test_every_stale_state_still_states_the_superseded_value(self):
        for state in ("stale_unmarked", "stale_expired", "stale_marked"):
            self.assertIn(self.item.f_old, doc_for_state(self.item, state, HARNESS["today"]))

    def test_states_differ_only_in_lifecycle_frontmatter(self):
        bodies = {state: doc_for_state(self.item, state, HARNESS["today"]).split("---\n")[-1]
                  for state in ("stale_unmarked", "stale_expired", "stale_marked")}
        self.assertEqual(len(set(bodies.values())), 1)

    def test_the_marked_state_is_deprecated_and_the_expired_one_is_not(self):
        expired = parsed_meta(doc_for_state(self.item, "stale_expired", HARNESS["today"]))
        marked = parsed_meta(doc_for_state(self.item, "stale_marked", HARNESS["today"]))
        self.assertEqual(expired["status"], "stable")
        self.assertEqual(marked["status"], "deprecated")
        for meta in (expired, marked):
            self.assertNotIn("verified", meta)
            self.assertLess(str(meta["stale_after"]), HARNESS["today"])

    def test_the_implementation_artifact_states_the_current_value(self):
        self.assertIn(self.item.f_new, artifact_text(self.item, self.item.f_new))
        self.assertIn(self.item.question.strip(), artifact_text(self.item, self.item.f_new))


class TestWriterStage(unittest.TestCase):
    def setUp(self):
        self.item = selected_items()[0]

    def test_the_document_the_writer_meets_carries_no_staleness_signal(self):
        meta = parsed_meta(writer_doc(self.item))
        self.assertEqual(meta["status"], "stable")
        self.assertNotIn("verified", meta)
        self.assertGreater(str(meta["stale_after"]), HARNESS["today"])

    def test_only_the_gate_arm_mentions_the_conventions_file(self):
        root = Path("/tmp/x")
        self.assertIn("AGENTS.md", writer_prompt(self.item, "gate", root))
        self.assertNotIn("AGENTS.md", writer_prompt(self.item, "nogate", root))

    def test_the_gate_states_the_rule_it_is_named_for(self):
        self.assertIn("not finished until", AGENTS_MD)

    def test_writer_grading_reads_files_not_claims(self):
        repo = gate_run.build_writer_repo(self.item, "nogate")
        run = WriterRun(item=self.item, arm="nogate", rep=0, root=repo,
                        prompt=writer_prompt(self.item, "nogate", repo))
        untouched = grade_writer(run)
        self.assertTrue(untouched["doc_untouched"])
        self.assertFalse(untouched["impl_updated"])
        (repo / "config" / "settings.yaml").write_text(
            artifact_text(self.item, self.item.f_new), encoding="utf-8")
        self.assertTrue(grade_writer(run)["impl_updated"])


class TestFrozenInvocation(unittest.TestCase):
    """Both stages inherit #40's isolation, which it paid twice to discover."""

    def test_both_commands_are_isolated_and_advisor_free(self):
        import json as _json
        for command in (build_writer_command(HARNESS, "x"), build_consumer_command(HARNESS, "x")):
            self.assertIn("--safe-mode", command)
            settings = _json.loads(command[command.index("--settings") + 1])
            self.assertEqual(settings["advisorModel"], "none")
            self.assertIs(settings["advisor"], False)
            self.assertEqual(command[command.index("--model") + 1], HARNESS["model"])

    def test_only_the_writer_may_edit(self):
        consumer = build_consumer_command(HARNESS, "x")
        self.assertNotIn("Edit", consumer)
        self.assertNotIn("Write", consumer)
        writer = build_writer_command(HARNESS, "x")
        self.assertIn("Edit", writer)


class TestAnalyzeShape(unittest.TestCase):
    def test_analyze_reports_both_sides_without_crossing_them(self):
        endtoend = [{"item": "i0", "arm": "gate", "grade": "fresh", "doc_untouched": False},
                    {"item": "i0", "arm": "nogate", "grade": "stale", "doc_untouched": True}]
        states = rows("state", "stale_unmarked", "i0", 1, 1) + rows("state", "stale_marked", "i0", 0, 1)
        result = analyze(endtoend, states)
        self.assertEqual(result["write_side"]["items"], 1)
        self.assertEqual(result["read_side_marked"]["items"], 1)
        self.assertAlmostEqual(result["spontaneous_sync"]["nogate"], 0.0)
        self.assertAlmostEqual(result["spontaneous_sync"]["gate"], 1.0)


if __name__ == "__main__":
    unittest.main()
